"""Document loaders and local vector-store operations."""

import asyncio

from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class KnowledgeBase:
    def __init__(self) -> None:
        settings.documents_dir.mkdir(parents=True, exist_ok=True)
        settings.vectorstore_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings = FastEmbedEmbeddings()
        self.store = Chroma(
            collection_name="client_knowledge",
            embedding_function=self.embeddings,
            persist_directory=str(settings.vectorstore_dir),
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )

    async def ingest(self, path: Path) -> int:
        """Index one document, replacing an earlier copy with the same filename."""
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Unsupported document type")
        # Loaders and splitters are synchronous/CPU-bound, so keep them off the event loop.
        documents = await asyncio.to_thread(self._load, path)
        for document in documents:
            document.metadata["filename"] = path.name
        chunks = await asyncio.to_thread(self.splitter.split_documents, documents)
        await self.store.adelete(where={"filename": path.name})
        if chunks:
            await self.store.aadd_documents(chunks)
        return len(chunks)

    async def search(self, query: str) -> list[Document]:
        return await self.store.asimilarity_search(query, k=settings.retrieval_k)

    @staticmethod
    def _load(path: Path) -> list[Document]:
        if path.suffix.lower() == ".pdf":
            return PyPDFLoader(str(path)).load()
        return TextLoader(str(path), autodetect_encoding=True).load()
