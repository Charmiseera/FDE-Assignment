"""
Tests for the embedding provider abstraction (app/rag/embeddings.py).

All tests run without a live Ollama or Nomic Atlas connection.
"""
import pytest
from unittest.mock import MagicMock, patch


# ── dimension guard ───────────────────────────────────────────────────────────

def test_dim_guard_raises_on_wrong_dimension():
    """EmbeddingDimError raised when provider returns wrong-dimension vector."""
    from app.rag.embeddings import _assert_dim, EmbeddingDimError
    wrong_dim_vecs = [[0.1] * 1536]  # OpenAI 1536-dim
    with pytest.raises(EmbeddingDimError, match="dim=1536"):
        _assert_dim(wrong_dim_vecs, "test-provider")


def test_dim_guard_passes_on_correct_dimension():
    """No error raised when vector has correct 768 dimensions."""
    from app.rag.embeddings import _assert_dim
    correct_vecs = [[0.1] * 768]
    _assert_dim(correct_vecs, "test-provider")  # should not raise


def test_startup_assertion_passes_when_dim_matches():
    """assert_embedding_dim_configured passes when config EMBEDDING_DIM == 768."""
    from app.rag.embeddings import assert_embedding_dim_configured
    from app.core.config import settings
    original = settings.EMBEDDING_DIM
    try:
        settings.EMBEDDING_DIM = 768
        assert_embedding_dim_configured()  # should not raise
    finally:
        settings.EMBEDDING_DIM = original


def test_startup_assertion_fails_on_wrong_dim():
    """assert_embedding_dim_configured raises EmbeddingDimError on mismatch."""
    from app.rag.embeddings import assert_embedding_dim_configured, EmbeddingDimError
    from app.core.config import settings
    original = settings.EMBEDDING_DIM
    try:
        settings.EMBEDDING_DIM = 1536
        with pytest.raises(EmbeddingDimError):
            assert_embedding_dim_configured()
    finally:
        settings.EMBEDDING_DIM = original


# ── fallback selection ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_primary_provider_succeeds_no_fallback():
    """When primary (Ollama) succeeds, fallback is never called."""
    from app.rag.embeddings import embed_query_with_fallback

    fake_vec = [0.1] * 768

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = fake_vec
    mock_embedder.model_name = "ollama/nomic-embed-text"

    with patch("app.rag.embeddings.get_embedder", return_value=mock_embedder),          patch("app.rag.embeddings.NomicAtlasEmbedder") as mock_nomic:
        result = await embed_query_with_fallback("what is activation?")

    assert result == fake_vec
    mock_nomic.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_used_when_primary_fails_and_key_set():
    """Cloud fallback is invoked when Ollama fails and key is configured."""
    from app.rag.embeddings import embed_query_with_fallback
    from app.core.config import settings

    fake_vec = [0.2] * 768

    mock_primary = MagicMock()
    mock_primary.embed_query.side_effect = ConnectionError("Ollama unreachable")
    mock_primary.model_name = "ollama/nomic-embed-text"

    mock_fallback = MagicMock()
    mock_fallback.embed_query.return_value = fake_vec
    mock_fallback.model_name = "nomic-atlas/nomic-embed-text-v1.5"

    original_enabled = settings.EMBEDDING_FALLBACK_ENABLED
    original_key = settings.NOMIC_API_KEY
    try:
        settings.EMBEDDING_FALLBACK_ENABLED = True
        settings.NOMIC_API_KEY = "test-key-not-real"

        with patch("app.rag.embeddings.get_embedder", return_value=mock_primary),              patch("app.rag.embeddings.NomicAtlasEmbedder", return_value=mock_fallback):
            result = await embed_query_with_fallback("what is PLG?")

        assert result == fake_vec
    finally:
        settings.EMBEDDING_FALLBACK_ENABLED = original_enabled
        settings.NOMIC_API_KEY = original_key


@pytest.mark.asyncio
async def test_both_providers_down_returns_none():
    """When both Ollama and Nomic fail, embed_query_with_fallback returns None."""
    from app.rag.embeddings import embed_query_with_fallback
    from app.core.config import settings

    mock_primary = MagicMock()
    mock_primary.embed_query.side_effect = ConnectionError("Ollama unreachable")
    mock_primary.model_name = "ollama/nomic-embed-text"

    mock_fallback = MagicMock()
    mock_fallback.embed_query.side_effect = Exception("Nomic API error")
    mock_fallback.model_name = "nomic-atlas/nomic-embed-text-v1.5"

    original_enabled = settings.EMBEDDING_FALLBACK_ENABLED
    original_key = settings.NOMIC_API_KEY
    try:
        settings.EMBEDDING_FALLBACK_ENABLED = True
        settings.NOMIC_API_KEY = "test-key-not-real"

        with patch("app.rag.embeddings.get_embedder", return_value=mock_primary),              patch("app.rag.embeddings.NomicAtlasEmbedder", return_value=mock_fallback):
            result = await embed_query_with_fallback("what is PLG?")

        assert result is None
    finally:
        settings.EMBEDDING_FALLBACK_ENABLED = original_enabled
        settings.NOMIC_API_KEY = original_key


@pytest.mark.asyncio
async def test_fallback_skipped_when_disabled():
    """Fallback is not invoked when EMBEDDING_FALLBACK_ENABLED=false."""
    from app.rag.embeddings import embed_query_with_fallback
    from app.core.config import settings

    mock_primary = MagicMock()
    mock_primary.embed_query.side_effect = ConnectionError("Ollama unreachable")
    mock_primary.model_name = "ollama/nomic-embed-text"

    original_enabled = settings.EMBEDDING_FALLBACK_ENABLED
    original_key = settings.NOMIC_API_KEY
    try:
        settings.EMBEDDING_FALLBACK_ENABLED = False
        settings.NOMIC_API_KEY = ""

        with patch("app.rag.embeddings.get_embedder", return_value=mock_primary),              patch("app.rag.embeddings.NomicAtlasEmbedder") as mock_nomic_cls:
            result = await embed_query_with_fallback("query")

        assert result is None
        mock_nomic_cls.assert_not_called()
    finally:
        settings.EMBEDDING_FALLBACK_ENABLED = original_enabled
        settings.NOMIC_API_KEY = original_key
