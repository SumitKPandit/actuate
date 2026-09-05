"""Local embedding and pgvector retrieval for grounded agent context."""

from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.vector import EMBEDDING_DIMENSIONS, KnowledgeChunk

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_TEXT_LENGTH = 8_000
MAX_SEARCH_RESULTS = 20


@lru_cache
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_LENGTH:
        raise ValueError("text must be non-empty and at most 8000 characters")

    embedding = _embedding_model().encode(text, normalize_embeddings=True).tolist()
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise RuntimeError("embedding model returned an unexpected dimension")
    return embedding


async def add_knowledge_chunk(
    session: AsyncSession,
    *,
    source: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeChunk:
    if not isinstance(source, str) or not source.strip() or len(source) > 255:
        raise ValueError("source must be non-empty and at most 255 characters")

    chunk = KnowledgeChunk(
        source=source.strip(),
        content=content.strip(),
        metadata_json=metadata,
        embedding=embed_text(content),
    )
    session.add(chunk)
    await session.flush()
    return chunk


async def search_knowledge(
    session: AsyncSession,
    *,
    query: str,
    limit: int = 5,
) -> list[KnowledgeChunk]:
    if not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_SEARCH_RESULTS}")

    query_embedding = embed_text(query)
    statement = (
        select(KnowledgeChunk)
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return list((await session.scalars(statement)).all())
