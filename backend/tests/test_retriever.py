"""
Tests for the RAG retriever (app/rag/retriever.py).

All tests are fully mocked — no live Ollama or Postgres required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.retriever import (
    embed_query,
    retrieve_chunks,
    RetrievedChunk,
    SIMILARITY_THRESHOLD,
)


# ── embed_query ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_embed_query_returns_vector_on_success():
    fake_embedding = [0.1] * 768
    with patch("app.rag.retriever.embed_query_with_fallback", AsyncMock(return_value=fake_embedding)):
        result = await embed_query("what is activation?")
    assert result == fake_embedding
    assert len(result) == 768


@pytest.mark.asyncio
async def test_embed_query_returns_none_on_ollama_failure():
    with patch("app.rag.retriever.embed_query_with_fallback", AsyncMock(return_value=None)):
        result = await embed_query("what is activation?")
    assert result is None


# ── retrieve_chunks ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retrieve_chunks_returns_results_above_threshold():
    fake_embedding = [0.5] * 768
    fake_row = MagicMock()
    fake_row.source_file = "ep001.txt"
    fake_row.episode_title = "PLG Episode"
    fake_row.chunk_text = "Activation is the moment..."
    fake_row.similarity = 0.82

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [fake_row]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.rag.retriever.embed_query", return_value=fake_embedding):
        chunks = await retrieve_chunks(mock_db, "what is activation?")

    assert len(chunks) == 1
    assert isinstance(chunks[0], RetrievedChunk)
    assert chunks[0].source_file == "ep001.txt"
    assert chunks[0].similarity == 0.82


@pytest.mark.asyncio
async def test_retrieve_chunks_returns_empty_when_embedding_fails():
    mock_db = AsyncMock()
    with patch("app.rag.retriever.embed_query", return_value=None):
        chunks = await retrieve_chunks(mock_db, "some query")
    assert chunks == []
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_chunks_returns_empty_when_db_fails():
    fake_embedding = [0.5] * 768
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("db error"))

    with patch("app.rag.retriever.embed_query", return_value=fake_embedding):
        chunks = await retrieve_chunks(mock_db, "activation metrics")

    assert chunks == []


@pytest.mark.asyncio
async def test_retrieve_chunks_returns_empty_when_no_rows():
    fake_embedding = [0.5] * 768
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.rag.retriever.embed_query", return_value=fake_embedding):
        chunks = await retrieve_chunks(mock_db, "random out-of-corpus question")

    assert chunks == []
