import logging
from typing import Any, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.chat_history import Message
from app.config import settings
from app.graph.state import ChatState

logger = logging.getLogger(__name__)


class RouterDecision(BaseModel):
    route: Literal[
        "rag",
        "order",
        "both",
        "out_of_scope",
    ] = Field(description=("The capability required to answer the user's request."))

    rag_query: str | None = Field(
        default=None,
        description=(
            "A focused query for the store knowledge base. "
            "Only provide this when RAG is required."
        ),
    )

    order_query: dict[str, str] | None = Field(
        default=None,
        description=(
            "A focused request for order information. "
            "Only provide this when order access is required."
            "The format is dict with order and email keys, e.g. {'order': '12345', 'email':"
        ),
    )


SYSTEM_PROMPT = """
You are the routing agent for a store customer-support chatbot.
If conversation history is not provided, you must route the request based on the user's question alone.
If you have are provided with a conversation history, use it to understand the context of the user's request.
If the conversation history has order number and email address, you must preserve them in the order_query field.

The chatbot has only these capabilities:

1. RAG
- Store policies
- Returns
- Exchanges
- Refunds
- Other store information contained in the knowledge base

2. ORDER
- Customer order information
- Order status
- Order details

3. BOTH
Use this when the request requires both knowledge-base information
and information about a specific order

4. OUT_OF_SCOPE
Use this for requests unrelated to:
- the store
- store policies
- returns
- exchanges
- refunds
- orders
Your job is to route the request, NOT answer it.

When RAG is required:
- Create a focused search query for the knowledge base.
- Preserve the meaning of the customer's question.
- Do not invent information.

When order access is required:
- Create a focused order-information request.
- Preserve order number and email address from the customer.

When both are required:
- Provide a focused search query excluding customer and order details for the knowledge base in the rag_query field.
- Fetch order number and email from the query and provide it in the order_query field.

When the request is out of scope:
- Just provide the route as "out_of_scope" and do not provide any other fields.
"""


def format_history(history: list[Message] | None) -> str:
    if not history:
        return "(no prior messages)"
    lines = [f"{turn['role']}: {turn['content']}" for turn in history]
    return "\n".join(lines)


class RouterNode:
    def __init__(self) -> None:
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            google_api_key=settings.gemini_api_key,
            temperature=0,
        )

        self.llm = llm.with_structured_output(RouterDecision)

    async def __call__(self, state: ChatState) -> dict[str, Any]:
        formatted_history = format_history(state.get("history") or [])
        try:
            decision: RouterDecision = await self.llm.ainvoke(
                [
                    (
                        "system",
                        f"{SYSTEM_PROMPT}\n\nConversation history:\n{formatted_history}",
                    ),
                    ("human", state["question"]),  # type: ignore
                ]
            )  # type: ignore
        except Exception:
            logger.exception("Router LLM call failed")
            raise

        logger.info(f"Route decided: {decision.route}")
        return {
            "route": decision.route,
            "rag_query": decision.rag_query,
            "order_query": decision.order_query,
        }
