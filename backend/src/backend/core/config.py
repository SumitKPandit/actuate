"""Application settings loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration.

    Values can be overridden via environment variables or a `.env` file
    in `backend/` (e.g. `APP_NAME`, `API_V1_PREFIX`, `CORS_ORIGINS`).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Actuate API"
    app_version: str = "0.1.0"
    description: str = "Agentic Intelligence & Reporting Layer for Enterprise Mobility"
    environment: str = "development"
    debug: bool = False

    api_v1_prefix: str = "/api/v1"

    # Comma-separated origins allowed in addition to localhost defaults.
    # e.g. CORS_ORIGINS="https://app.example.com,https://admin.example.com"
    cors_origins: str = ""

    def get_cors_origins(self) -> list[str]:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        if self.cors_origins.strip():
            origins += [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # De-duplicate while preserving order.
        return list(dict.fromkeys(origins))


settings = Settings()
