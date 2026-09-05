"""Application settings loaded from environment."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Backend configuration (override via env or `backend/.env`).

    Local default is SQLite (zero setup). When deployed, set
    `DATABASE_URL` to PostgreSQL, e.g.
    `postgresql+asyncpg://user:pass@host:5432/actuate`.
    """

    model_config = SettingsConfigDict(env_file=str(_BACKEND_ROOT / ".env"), extra="ignore")

    app_name: str = "Actuate API"
    database_url: str = "sqlite+aiosqlite:///./actuate.db"
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    sarvam_api_key: str | None = None
    sarvam_model: str = "sarvam-105b"
    sarvam_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    sarvam_max_retries: int = Field(default=0, ge=0, le=2)


settings = Settings()
