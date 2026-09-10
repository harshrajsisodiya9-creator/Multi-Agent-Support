"""FastAPI entry point for the client knowledge chatbot."""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import (
    CORSMiddleware,  # not needed since we are using proxy from shopify, but keeping it for local testing
)

from app.chat_history import chat_store, start_cleanup_loop
from app.chat_service import ChatService
from app.config import settings
from app.graph.graph import graph
from app.graph.state import ChatState
from app.knowledge_base import SUPPORTED_EXTENSIONS, KnowledgeBase
from app.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

from app.schemas import ChatRequest, ChatResponse, IngestResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    # Start the cleanup loop in the background
    asyncio.create_task(start_cleanup_loop())
    yield


app = FastAPI(title="Client Knowledge Chatbot", version="0.1.0", lifespan=lifespan)


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()


def get_chat_service(kb: KnowledgeBase = Depends(get_knowledge_base)) -> ChatService:
    return ChatService(kb)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/documents", response_model=IngestResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...), kb: KnowledgeBase = Depends(get_knowledge_base)
) -> IngestResponse:
    filename = Path(file.filename or "document").name
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT, and Markdown documents are supported.",
        )
    destination = settings.documents_dir / filename
    content = await file.read()
    await asyncio.to_thread(destination.write_bytes, content)
    chunks = await kb.ingest(destination)
    return IngestResponse(filename=filename, chunks_indexed=chunks)


@app.post("/chat", response_model=ChatResponse)
@app.post("/chat/", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503, detail="GROQ_API_KEY has not been configured."
        )

    if not request.message or request.message.strip() == "":
        raise HTTPException(status_code=400, detail="The 'message' field is required.")

    # Shopify App Proxy provides this for logged-in customers
    customer_id = http_request.query_params.get("logged_in_customer_id")

    logger.info(f"Received chat request: {request.message}, customer_id: {customer_id}")

    history = chat_store.get_history(customer_id) if customer_id else []
    response = await graph.ainvoke(
        ChatState(question=request.message, history=history, customer_id=customer_id)
    )
    if customer_id:
        chat_store.add_turn(
            customer_id, request.message, response["final_response"].answer
        )
    logger.info("Graph execution completed.")

    return response["final_response"]
