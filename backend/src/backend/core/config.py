"""Application settings loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration (override via env or `backend/.env`).

    Local default is SQLite (zero setup). When deployed, set
    `DATABASE_URL` to PostgreSQL, e.g.
    `postgresql+asyncpg://user:pass@host:5432/actuate`.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Actuate API"
    database_url: str = "sqlite+aiosqlite:///./actuate.db"


settings = Settings()
