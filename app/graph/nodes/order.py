from typing import Any

from app.graph.state import ChatState


class OrderNode:
    async def __call__(self, state: ChatState) -> dict[str, Any]:
        return {
            "order_response": {
                "answer": (
                    f"Order information:\n Order has been delivered on 2026-08-20"
                    f"Received query: {state['order_query']}"  # type: ignore
                )
            }
        }
