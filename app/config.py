from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    routing_model: str = "gemini-3.5-flash-lite"
    generation_model: str = "openai/gpt-oss-20b"
    final_model: str = "qwen/qwen3.8-27b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    retrieval_k: int = 4
    documents_dir: Path = PROJECT_DIR / "data" / "documents"
    vectorstore_dir: Path = PROJECT_DIR / "data" / "vectorstore"
    access_token: str | None = None
    shop_domain: str | None = None


settings = Settings()
