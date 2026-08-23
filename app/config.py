from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 4
    documents_dir: Path = PROJECT_DIR / "data" / "documents"
    vectorstore_dir: Path = PROJECT_DIR / "data" / "vectorstore"


settings = Settings()
