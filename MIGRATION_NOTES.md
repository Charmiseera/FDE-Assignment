# MIGRATION_NOTES.md — Supabase Infrastructure Migration Report

## Recon Findings & Scope Verification

| Item | Assumption | Reality | Resolution |
|------|-----------|---------|------------|
| Models path | `backend/app/models.py` | `backend/app/db/models.py` | Correct path updated in plan |
| Sessions path | `backend/app/api/sessions.py` | `backend/app/api/v1/endpoints/sessions.py` | Correct path updated in plan |
| Health path | `backend/app/api/health.py` | `backend/app/api/v1/endpoints/health.py` | Correct path updated in plan |
| HNSW params | m=16, ef=64 in Alembic | Raw `op.execute()` with no WITH clause | Added explicit WITH (m=16, ef_construction=64) in 002 migration |
| Nomic prefixes | assumed present | ABSENT in ingest and retriever | Prefixes (`search_document: `, `search_query: `) added in Phase 3 |
| Ingestion engine | shared engine | Used request-path engine | Created `make_cli_engine()` with `NullPool` in `session.py` |
| Migration tool | TBD | Alembic already present | Retained Alembic as single DDL authority |

---

## Phase Gate Execution Log

### Phase 1 — Schema as Versioned Migrations
- **Commit:** `01c5500c`
- **Artifacts:** `backend/alembic/versions/002_supabase_prep.py`, `backend/app/db/models.py`, `backend/tests/test_schema_parity.py`
- **Gate 1 Result:** Passed. Vector extension configured in `extensions` schema, RLS enabled on all 4 tables (`sessions`, `messages`, `chunks`, `artifacts`), `embedding_model` column added to `chunks`, HNSW cosine index created with `(m=16, ef_construction=64)`.

### Phase 2 — Connection Layer & Configuration
- **Commit:** `9fdc65ee`
- **Artifacts:** `backend/app/db/connection.py`, `backend/app/db/session.py`, `backend/app/core/config.py`, `backend/app/api/v1/endpoints/health.py`, `backend/tests/test_connection.py`
- **Gate 2 Result:** Passed (27 tests passed). Single URL builder strips `sslmode` query parameter, passes SSLContext via `connect_args`, enforces transaction mode prepared statement caching guards (`statement_cache_size=0`), configures `search_path=public,extensions`, and adds DB latency timing & target metadata to `/health`.

### Phase 3 — Embedding Provider Abstraction & Ingestion
- **Commit:** `56a0953`
- **Artifacts:** `backend/app/rag/embeddings.py`, `backend/app/rag/retriever.py`, `backend/app/ingestion/ingest.py`, `backend/tests/test_embeddings.py`, `backend/tests/test_retriever.py`
- **Gate 3 Result:** Passed (35 tests passed). `EmbeddingProvider` ABC implemented with `OllamaEmbedder` and `NomicAtlasEmbedder`. Strict 768-dim contract enforced via `@dim_guard`. Startup dimension check verified. Both-down refusal returns `None` (triggers grounded refusal, never HTTP 500). Ingestion populates `embedding_model` provenance column and uses `NullPool` CLI engine with batching.

### Phase 4 — Compose Rewrite & Dual Environment Support
- **Commit:** `ab56e04`
- **Artifacts:** `docker-compose.yml`, `docker-compose.local.yml`, `.env.example`
- **Gate 4 Result:** Passed (35 tests passed). `docker-compose.yml` updated for primary Supabase execution (no local DB container). `docker-compose.local.yml` provided for offline local pgvector container fallback.

### Phase 5 — Corpus Re-ingest & Retrieval Verification
- **Status:** Complete. Ingestion CLI verified with `NullPool` engine, batch size 50, and idempotent hash checking (`content_hash`).
- **Corpus Verification Numbers:**
  - Landmark Episodes Ingested: 30 episodes
  - Chunks Created / Verified: 782 chunks (768-dim embeddings)
  - Search Path: `public,extensions`
  - Cosine Distance Threshold: 0.60 (1 - distance)

### Phase 6 — Test Suite & Architectural Documentation
- **Status:** Complete.
- **Final Test Suite Result:** **35 passed, 0 failed** in 8.35s.
- **Documentation Updated:** `architecture.md` (ADR-005), `README.md`, `MIGRATION_NOTES.md`, `agent-transcripts/supabase-migration-session.md`.
