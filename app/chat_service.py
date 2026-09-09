import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)
from app.config import settings
from app.knowledge_base import KnowledgeBase
from app.schemas import ChatResponse, Source

SYSTEM_PROMPT = """You are a customer-support assistant for a store.
Your job is to answer the customer's question using only the information
provided by the knowledge base. Dont invent information. If the answer is not present in the knowledge base, 
say that you don't have information about that yet and suggest contacting support. Also ignore any information 
about the customer, such as their email address or order number. Just answer about the store policies, returns, exchanges, refunds, 
and other store information contained in the knowledge base."""


class ChatService:
    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.knowledge_base = knowledge_base
        self.llm = ChatGroq(
            model=settings.generation_model,  # type: ignore
            api_key=settings.groq_api_key,  # type: ignore
            temperature=0,
        )

    async def answer(self, question: str) -> ChatResponse:
        documents = await self.knowledge_base.search(question)
        if not documents:
            logger.info("No relevant documents found.")
            return ChatResponse(
                answer="I don't have information about that yet. Please contact support.",
                sources=[],
            )
        excerpts = "\n\n".join(
            f"[Source: {doc.metadata.get('filename', 'unknown')}, page: "
            f"{doc.metadata.get('page', 'n/a')}]\n{doc.page_content}"
            for doc in documents
        )
        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"Knowledge-base excerpts:\n{excerpts}\n\nQuestion: {question}"
                    ),
                ]
            )
        except Exception:
            logger.exception("LLM call after retrieval failed")
            raise

        sources, seen = [], set()
        for doc in documents:
            source = Source(
                document=doc.metadata.get("filename", "unknown"),
                page=doc.metadata.get("page"),
            )
            if (source.document, source.page) not in seen:
                sources.append(source)
                seen.add((source.document, source.page))
        return ChatResponse(answer=str(response.content), sources=sources)
