from typing import Any

from app.graph.state import ChatState
from app.schemas import ChatResponse

REFUSAL_MESSAGE = (
    "I can only help with store policies, returns, exchanges, refunds, and orders."
)


class RefusalNode:
    def __call__(self, state: ChatState) -> dict[str, Any]:
        return {
            "final_response": ChatResponse(
                answer=REFUSAL_MESSAGE,
                sources=[],
            )
        }
