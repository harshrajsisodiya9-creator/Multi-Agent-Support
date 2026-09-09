from typing import Literal, TypedDict

from app.chat_history import Message
from app.schemas import ChatResponse


class ChatState(TypedDict, total=False):
    question: str
    history: list[Message]
    route: Literal["rag", "order", "both", "out_of_scope"] | None
    rag_query: str | None
    order_query: dict[str, str] | None
    rag_response: ChatResponse | None
    order_response: dict | None
    customer_id: str | None
    final_response: ChatResponse | None
