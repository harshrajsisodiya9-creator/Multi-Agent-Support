from typing import Any

from app.chat_service import ChatService
from app.graph.state import ChatState


class RAGNode:
    def __init__(self, chat_service: ChatService) -> None:
        self.chat_service = chat_service

    async def __call__(self, state: ChatState) -> dict[str, Any]:
        response = await self.chat_service.answer(state["rag_query"])  # type: ignore
        return {"rag_response": response}
