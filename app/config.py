"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pdfembedding"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    pdf_storage_path: str = "/data/pdfs"

    # OpenAI
    openai_api_key: str = ""

    # OCR (Gemini or DeepSeek)
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    ocr_provider: str = "gemini"  # or "deepseek"

    # Embedding settings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Chunking settings
    chunk_size: int = 512
    chunk_overlap: int = 50

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
