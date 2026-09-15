"""
RAG retriever — vector similarity search over the chunks table.

Per architecture.md data-flow:
  1. Embed user query via embed_query_with_fallback() from embeddings.py.
     Primary: Ollama nomic-embed-text (768-dim).
     Fallback: Nomic Atlas API (768-dim, same family) when configured.
     Both failing: returns None → grounded-refusal path fires (never 500).
  2. HNSW cosine similarity search using pgvector (<=> operator).
  3. Return top-k chunks whose similarity exceeds the threshold.
  4. If nothing clears the threshold, return [] → grounded-refusal downstream.

Task-type prefixes (Option A, Phase 5 re-ingest required):
  embed_query_with_fallback adds "search_query: " prefix internally.
  ingest.py adds "search_document: " prefix for indexed chunks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import embed_query_with_fallback, EMBEDDING_DIM

logger = structlog.get_logger()

DEFAULT_TOP_K = 5
SIMILARITY_THRESHOLD = 0.60


@dataclass
class RetrievedChunk:
    source_file: str
    episode_title: str
    chunk_text: str
    similarity: float


async def embed_query(query: str) -> Optional[list[float]]:
    """
    Public embed_query shim — delegates to embed_query_with_fallback.

    Preserved for backward compatibility with existing tests and the sessions
    endpoint. Returns None on all failure paths.
    """
    return await embed_query_with_fallback(query)


async def retrieve_chunks(
    db: AsyncSession,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[RetrievedChunk]:
    """
    Embed the query, run HNSW cosine search, return chunks above threshold.

    Returns an empty list when:
    - All embedding providers fail (embedding is None), or
    - No chunk scores above the similarity threshold.
    Either case triggers the grounded-refusal response downstream.
    """
    embedding = await embed_query(query)
    if embedding is None:
        return []

    # pgvector cosine distance operator: <=>
    # similarity = 1 - cosine_distance, consistent with 0.60 threshold
    sql = text(
        """
        SELECT
            source_file,
            episode_title,
            chunk_text,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM chunks
        WHERE 1 - (embedding <=> CAST(:embedding AS vector)) >= :threshold
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    try:
        result = await db.execute(
            sql,
            {
                "embedding": str(embedding),
                "threshold": threshold,
                "top_k": top_k,
            },
        )
        rows = result.fetchall()
    except Exception as exc:
        logger.error("retrieval_query_failed", error=str(exc))
        return []

    return [
        RetrievedChunk(
            source_file=row.source_file,
            episode_title=row.episode_title,
            chunk_text=row.chunk_text,
            similarity=float(row.similarity),
        )
        for row in rows
    ]
