"""
Embedding provider abstraction.

EMBEDDING_DIM=768 is a hard contract:
  - Asserted at startup via assert_embedding_dim_configured()
  - Asserted per-batch/per-call in embed_texts() and embed_query()
  - Wrong dimensions raise EmbeddingDimError loudly — never truncated or padded

Provider selection:
  1. OllamaEmbedder (default) — local Ollama nomic-embed-text
  2. NomicAtlasEmbedder (cloud fallback) — Nomic Atlas API, native 768-dim,
     same model family as the local Ollama model so fallback vectors land in
     a comparable vector space (preferred per §5 Phase 3 spec).
     ADR: Nomic Atlas is preferred over OpenAI text-embedding-3-small because
     OpenAI embeds into a different vector space — mixing would degrade
     retrieval and require a full re-ingest. Nomic native 768 avoids this.

Task-type prefixes (Option A, confirmed by user):
  Nomic models expect "search_document: " prefix for indexed chunks and
  "search_query: " prefix for query-time embeddings. The same prefixes are
  also accepted by the Ollama build of nomic-embed-text (per Nomic docs).
  Adding prefixes changes the vector space — a full --refresh re-ingest is
  required after this change (executed in Phase 5).

Fallback semantics:
  - Ollama tried first when EMBEDDING_PROVIDER=ollama
  - Cloud fallback only when EMBEDDING_FALLBACK_ENABLED=true AND key is set
    AND Ollama fails
  - Both failing: embed_query() returns None → existing grounded-refusal fires
  - Each call logs which provider served it
"""
from __future__ import annotations

import abc
import json
import urllib.request
import urllib.error
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Hard contract — never change without a full corpus re-ingest
EMBEDDING_DIM: int = 768


class EmbeddingDimError(ValueError):
    """Raised when a provider returns vectors with the wrong dimension."""


def _assert_dim(vectors: list[list[float]], provider: str) -> None:
    """Raise loudly if any vector has wrong dimension."""
    for i, v in enumerate(vectors):
        if len(v) != EMBEDDING_DIM:
            raise EmbeddingDimError(
                f"Provider '{provider}' returned dim={len(v)} at index {i}; "
                f"expected EMBEDDING_DIM={EMBEDDING_DIM}. "
                f"Never truncate or pad — change the provider or re-configure."
            )


def assert_embedding_dim_configured() -> None:
    """
    Startup assertion: EMBEDDING_DIM setting matches the hard constant.
    Call from app lifespan or CLI entry point.
    """
    if settings.EMBEDDING_DIM != EMBEDDING_DIM:
        raise EmbeddingDimError(
            f"EMBEDDING_DIM={settings.EMBEDDING_DIM} in config but "
            f"the codebase hard-contracts {EMBEDDING_DIM}. "
            f"Update config to match or re-configure the provider."
        )
    logger.info("embedding_dim_ok", dim=EMBEDDING_DIM)


class EmbeddingProvider(abc.ABC):
    """Abstract embedding provider interface."""

    @abc.abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a list of texts. Raises EmbeddingDimError on dim mismatch."""

    @abc.abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Return embedding for a single query string."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Human-readable provider/model identifier for provenance logging."""


class OllamaEmbedder(EmbeddingProvider):
    """
    Embedding via local Ollama.

    Uses nomic-embed-text with task-type prefixes:
      - search_document: <text>  for indexed chunks
      - search_query: <text>     for query-time embeddings
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        import ollama as _ollama
        self._ollama = _ollama
        self._base_url = base_url or settings.OLLAMA_BASE_URL
        self._model = model or settings.OLLAMA_EMBEDDING_MODEL

    @property
    def model_name(self) -> str:
        return f"ollama/{self._model}"

    def _client(self):
        return self._ollama.Client(host=self._base_url)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed document texts with search_document: prefix."""
        prefixed = [f"search_document: {t}" for t in texts]
        client = self._client()
        result = []
        for text in prefixed:
            resp = client.embeddings(model=self._model, prompt=text)
            result.append(resp["embedding"])
        _assert_dim(result, self.model_name)
        return result

    def embed_query(self, text: str) -> list[float]:
        """Embed a query with search_query: prefix."""
        prefixed = f"search_query: {text}"
        client = self._client()
        resp = client.embeddings(model=self._model, prompt=prefixed)
        vec = resp["embedding"]
        _assert_dim([vec], self.model_name)
        return vec


class NomicAtlasEmbedder(EmbeddingProvider):
    """
    Cloud embedding via Nomic Atlas API (nomic-embed-text-v1.5).

    Native 768-dim output. Same model family as the local Ollama nomic-embed-text,
    so fallback vectors land in a comparable vector space. Preferred over
    OpenAI text-embedding-3-small which embeds into a different vector space
    and would require a full re-ingest if mixed with Ollama-embedded chunks.

    Requires NOMIC_API_KEY to be set.
    """

    NOMIC_API_URL = "https://api-atlas.nomic.ai/v1/embedding/text"
    MODEL = "nomic-embed-text-v1.5"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.NOMIC_API_KEY
        if not self._api_key:
            raise ValueError("NOMIC_API_KEY is required for NomicAtlasEmbedder")

    @property
    def model_name(self) -> str:
        return f"nomic-atlas/{self.MODEL}"

    def _call_api(self, texts: list[str], task_type: str) -> list[list[float]]:
        payload = json.dumps({
            "texts": texts,
            "model": self.MODEL,
            "task_type": task_type,
            "dimensionality": EMBEDDING_DIM,
        }).encode()
        req = urllib.request.Request(
            self.NOMIC_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["embeddings"]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed document texts with search_document task type."""
        result = self._call_api(texts, task_type="search_document")
        _assert_dim(result, self.model_name)
        return result

    def embed_query(self, text: str) -> list[float]:
        """Embed a query with search_query task type."""
        result = self._call_api([text], task_type="search_query")
        vecs = result
        _assert_dim(vecs, self.model_name)
        return vecs[0]


def get_embedder() -> EmbeddingProvider:
    """
    Return the configured primary embedder (always OllamaEmbedder by default).
    Raises if configuration is unusable.
    """
    if settings.EMBEDDING_PROVIDER == "nomic":
        return NomicAtlasEmbedder()
    return OllamaEmbedder()


async def embed_query_with_fallback(text: str) -> Optional[list[float]]:
    """
    Embed a query string, with automatic fallback to the cloud provider.

    Fallback semantics:
      1. Try primary provider (Ollama by default)
      2. If it fails AND EMBEDDING_FALLBACK_ENABLED=true AND NOMIC_API_KEY set:
         try NomicAtlasEmbedder
      3. If both fail: return None (triggers grounded-refusal path, never 500)

    Logs which provider served each call.
    """
    primary = get_embedder()
    try:
        vec = primary.embed_query(text)
        logger.info("embedding_served", provider=primary.model_name, source="primary")
        return vec
    except Exception as primary_err:
        logger.warning(
            "embedding_primary_failed",
            provider=primary.model_name,
            error=str(primary_err),
        )

    # Attempt fallback
    if settings.EMBEDDING_FALLBACK_ENABLED and settings.NOMIC_API_KEY:
        try:
            fallback = NomicAtlasEmbedder()
            vec = fallback.embed_query(text)
            logger.info("embedding_served", provider=fallback.model_name, source="fallback")
            return vec
        except Exception as fallback_err:
            logger.error(
                "embedding_fallback_failed",
                provider="nomic-atlas",
                error=str(fallback_err),
            )
    else:
        logger.warning(
            "embedding_fallback_skipped",
            reason="EMBEDDING_FALLBACK_ENABLED=false or NOMIC_API_KEY not set",
        )

    logger.error("embedding_both_providers_failed", query_len=len(text))
    return None
