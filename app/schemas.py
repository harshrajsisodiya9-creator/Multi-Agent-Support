from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class Source(BaseModel):
    document: str
    page: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class IngestResponse(BaseModel):
    filename: str
    chunks_indexed: int
