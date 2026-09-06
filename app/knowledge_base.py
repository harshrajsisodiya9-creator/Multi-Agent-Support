"""Document loaders and local vector-store operations."""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document

from app.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class FAQSplitter:
    """Creates one retrieval chunk per FAQ, beginning at a `Q:` line."""

    @staticmethod
    def split_documents(documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        current_lines: list[str] = []
        current_metadata: dict = {}

        for document in documents:
            for line in document.page_content.splitlines():
                if line.startswith("Q:"):
                    if current_lines:
                        chunks.append(
                            Document(
                                page_content="\n".join(current_lines).strip(),
                                metadata=current_metadata,
                            )
                        )
                    current_lines = [line]
                    current_metadata = dict(document.metadata)
                elif current_lines:
                    # Answer content belongs to the most recent question, even
                    # if it continues onto the next PDF page/document segment.
                    current_lines.append(line)

        if current_lines:
            chunks.append(
                Document(
                    page_content="\n".join(current_lines).strip(),
                    metadata=current_metadata,
                )
            )
        return chunks


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
        self.splitter = FAQSplitter()

    async def ingest(self, path: Path) -> int:
        """Index one document, replacing an earlier copy with the same filename."""
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Unsupported document type")
        # Loaders and splitters are synchronous/CPU-bound, so keep them off the event loop.
        documents = await asyncio.to_thread(self._load, path)
        for document in documents:
            document.metadata["filename"] = path.name
        chunks = await asyncio.to_thread(self.splitter.split_documents, documents)

        # Gracefully handle the case where no FAQ entries were found, which can happen
        #  if the user uploads a document that doesn't follow the expected format.
        if not chunks:
            logger.warning(
                "No FAQ entries found in document %s. Each question must start with 'Q:' at the beginning of a line.",
                path.name,
            )
            raise ValueError(
                "No FAQ entries found. Each question must start with 'Q:' at the beginning of a line."
            )
        await self.store.adelete(where={"filename": path.name})
        try:
            await self.store.aadd_documents(chunks)
        except Exception:
            logger.exception("Failed to add documents to vector store")
            raise
        return len(chunks)

    async def search(self, query: str) -> list[Document]:
        try:
            return await self.store.asimilarity_search(query, k=settings.retrieval_k)
        except Exception:
            logger.exception("Knowledge base search failed")
            raise

    @staticmethod
    def _load(path: Path) -> list[Document]:
        if path.suffix.lower() == ".pdf":
            return PyPDFLoader(str(path)).load()
        return TextLoader(str(path), autodetect_encoding=True).load()
