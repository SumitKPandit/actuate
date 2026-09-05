from backend.core.database import is_postgres_url
from backend.models.vector import EMBEDDING_DIMENSIONS, KnowledgeChunk


def test_knowledge_chunk_uses_the_selected_embedding_dimension() -> None:
    assert EMBEDDING_DIMENSIONS == 384
    assert str(KnowledgeChunk.__table__.c.embedding.type) == "VECTOR(384)"


def test_pgvector_extension_is_only_enabled_for_postgres() -> None:
    assert is_postgres_url("postgresql+asyncpg://user:pass@db:5432/actuate")
    assert not is_postgres_url("sqlite+aiosqlite:///./actuate.db")
