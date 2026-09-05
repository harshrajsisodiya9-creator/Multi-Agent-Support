import logging
from typing import Any, Literal

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

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


SYSTEM_PROMPT = """You are the routing agent for a store customer-support chatbot.

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
- Preserve any order number or relevant details from the customer.

When both are required:
- Provide both a focused RAG query and an order query.

When the request is out of scope:
- Provide a short refusal explaining that the assistant only handles
  store policies, returns, exchanges, refunds, and orders.
"""


class RouterNode:
    def __init__(self) -> None:
        llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,  # type: ignore
            temperature=0,
        )

        self.llm = llm.with_structured_output(RouterDecision)

    async def __call__(self, state: ChatState) -> dict[str, Any]:
        try:
            decision: RouterDecision = await self.llm.ainvoke(
                [
                    ("system", SYSTEM_PROMPT),
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
