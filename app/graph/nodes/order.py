import logging

logger = logging.getLogger(__name__)
from typing import Any

import httpx

from app.config import settings
from app.graph.state import ChatState

ORDER_QUERY = """
query FindOrder($query: String!) {
  orders(first: 1, query: $query) {
    edges {
      node {
        id
        name
        email
        displayFulfillmentStatus
        displayFinancialStatus
        createdAt
        totalPriceSet { shopMoney { amount currencyCode } }
        lineItems(first: 10) {
          edges { node { title quantity } }
        }
        fulfillments {
          trackingInfo { number url }
        }
      }
    }
  }
}
"""


class OrderNode:
    def __init__(self):
        self.url = f"https://{settings.shop_domain}/admin/api/2025-01/graphql.json"
        self.headers = {
            "X-Shopify-Access-Token": settings.access_token,
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(timeout=10)

    async def __call__(self, state: ChatState) -> dict[str, Any]:
        order_query = state.get("order_query")
        order_number = order_query.get("order_number") if order_query else None
        email = order_query.get("email") if order_query else None
        if not order_number or not email:
            return {
                "order_response": {
                    "found": False,
                    "error": "Missing order number or email",
                }
            }
        try:
            resp = await self.client.post(
                self.url,
                json={
                    "query": ORDER_QUERY,
                    "variables": {"query": f"name:#{order_number} AND email:{email}"},
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()
            orders = data.get("data", {}).get("orders", {}).get("edges", [])
            if not orders:
                return {
                    "order_response": {
                        "found": False,
                        "error": "No such order for the given email",
                    }
                }
            logger.info(f"Order found: {orders[0]['node']}")
            return {"order_response": {"found": True, "order": orders[0]["node"]}}
        except Exception as e:
            logger.exception("Order lookup on shopify failed")
            return {"order_response": {"found": False, "error": str(e)}}
