from langgraph.graph import END, START, StateGraph

from app.chat_service import ChatService
from app.graph.nodes.finalagent import ResponseNode
from app.graph.nodes.order import OrderNode
from app.graph.nodes.RAG import RAGNode
from app.graph.nodes.refusal import RefusalNode
from app.graph.nodes.router import RouterNode
from app.graph.state import ChatState
from app.knowledge_base import KnowledgeBase


def route_after_decsion(state: ChatState):
    route = state.get("route")

    if route == "rag":
        return ["RAGAgent"]
    elif route == "order":
        return ["OrderAgent"]
    elif route == "both":
        return ["RAGAgent", "OrderAgent"]

    return ["RefusalAgent"]


builder = StateGraph(ChatState)

builder.add_node("RouteAgent", RouterNode())
builder.add_node(
    "RAGAgent", RAGNode(chat_service=ChatService(knowledge_base=KnowledgeBase()))
)
builder.add_node("OrderAgent", OrderNode())
builder.add_node("RefusalAgent", RefusalNode())
builder.add_node("ResponseAgent", ResponseNode())
builder.add_edge(START, "RouteAgent")
builder.add_conditional_edges(
    "RouteAgent",
    route_after_decsion,
)
builder.add_edge("RAGAgent", "ResponseAgent")
builder.add_edge("OrderAgent", "ResponseAgent")
builder.add_edge("ResponseAgent", END)
builder.add_edge("RefusalAgent", END)

graph = builder.compile()
