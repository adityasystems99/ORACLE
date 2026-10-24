"""Application configuration management with Pydantic BaseSettings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for ORACLE backend."""

    # Core Application
    APP_NAME: str = "ORACLE"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Persistence Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
    GRAPH_PERSIST_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "knowledge_graph.json"
    CHROMA_PERSIST_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "chroma_db"
    EVENTS_PERSIST_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "events.json"
    REPORTS_PERSIST_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "reports.json"

    # LLM Settings
    LLM_PROVIDER: Literal["mock", "openai", "anthropic", "gemini", "ollama"] = "mock"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 2048

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Ingestion Settings
    INGESTION_INTERVAL_MINUTES: int = 30
    MAX_ITEMS_PER_FEED: int = 25
    REQUEST_TIMEOUT_SECONDS: int = 15
    USER_AGENT: str = "ORACLE-IntelligenceCopilot/1.0 (+https://github.com/oracle-copilot)"

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"

    # Autonomous Scheduler & Monitoring
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TICK_SECONDS: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    settings = Settings()
    # Ensure data directory exists
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings
