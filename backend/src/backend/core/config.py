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
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )


settings = Settings()
