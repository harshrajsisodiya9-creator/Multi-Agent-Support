import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.graph.state import ChatState
from app.schemas import ChatResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the final response assistant for a store
customer-support chatbot.

Your job is to answer the customer's question using only the information
provided by the previous support capabilities.

Available information may come from:
- The store knowledge base
- Shopify order information

Rules:
- Do not invent information.
- Do not claim information that is not present in the provided results.
- If information is missing, clearly say that you do not have it.
- Keep the response concise and helpful.
- Do not mention internal tools, agents, RAG, MCP, or the routing process.
- Keep plain text only, no markdown, bold, no asterisks
"""


class ResponseNode:
    def __init__(self) -> None:
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,  # type: ignore
            temperature=0,
        )

    async def __call__(self, state: ChatState) -> dict[str, Any]:
        if state.get("route") == "rag":
            logger.info("Generating final response using RAG response only.")
            return {
                "final_response": ChatResponse(
                    answer=state["rag_response"].answer,  # type: ignore
                    sources=state["rag_response"].sources,  # type: ignore
                )
            }

        rag_response = state.get("rag_response")
        order_response = state.get("order_response")

        context_parts = []

        if rag_response:
            context_parts.append(f"Knowledge-base response: {rag_response.answer}")

        if order_response:
            context_parts.append(f"Order information: {order_response}")

        context = "\n\n".join(context_parts)

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"Customer question:\n{state['question']}\n\n"  # type: ignore
                            f"Available information:\n{context}"
                        )
                    ),
                ]
            )

        except Exception:
            logger.exception("Final response LLM call failed")
            raise

        sources = []

        if rag_response:
            sources = rag_response.sources

        return {
            "final_response": ChatResponse(
                answer=str(response.content),
                sources=sources,
            )
        }
