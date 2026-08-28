from typing import Literal, TypedDict

from app.schemas import ChatResponse


class ChatState(TypedDict, total=False):
    question: str

    route: Literal["rag", "order", "both", "out_of_scope"] | None
    rag_query: str | None
    order_query: str | None

    rag_response: ChatResponse | None
    order_response: dict | None

    final_response: ChatResponse | None
