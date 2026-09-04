"""Actuate backend package — exposes the FastAPI app and CLI entrypoint."""

from backend.app import app, create_app

__all__ = ["app", "create_app", "main"]


def main() -> None:
    """Run the API with uvicorn (`uv run backend` or `uv run uvicorn backend.app:app`)."""
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
