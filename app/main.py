"""FastAPI entry point for the client knowledge chatbot."""

import asyncio
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import (
    CORSMiddleware,  # not needed since we are using proxy from shopify, but keeping it for local testing
)

from app.chat_service import ChatService
from app.config import settings
from app.graph.graph import graph
from app.knowledge_base import SUPPORTED_EXTENSIONS, KnowledgeBase
from app.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

from app.schemas import ChatRequest, ChatResponse, IngestResponse

app = FastAPI(title="Client Knowledge Chatbot", version="0.1.0")


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
async def chat(request: ChatRequest) -> ChatResponse:
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503, detail="GROQ_API_KEY has not been configured."
        )

    if not request.message or request.message.strip() == "":
        raise HTTPException(status_code=400, detail="The 'message' field is required.")

    logger.info(f"Received chat request: {request.message}")

    response = await graph.ainvoke({"question": request.message})

    logger.info("Graph execution completed.")

    return response["final_response"]
