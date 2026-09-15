# Supabase Infrastructure Migration — Session Log

**Branch:** `feat/supabase-migration`  
**Engineer / Agent:** Senior Backend Infrastructure Engineer  
**Task:** Surgical migration of PostgreSQL vector database to managed Supabase with dual-provider embedding fallback.

---

## 1. Initial Recon & Verification
Before executing code edits, a complete audit of the codebase was conducted against the initial specifications:
- Verified models path: `backend/app/db/models.py` (not `backend/app/models.py`).
- Verified endpoints path: `backend/app/api/v1/endpoints/sessions.py` and `health.py`.
- Identified existing Alembic setup (`alembic/versions/001_initial_schema.py`). Decision made to keep Alembic as single source of truth rather than adding Supabase CLI migrations.
- Flagged Nomic embedding task-type prefix absence and missing HNSW parameters in raw DDL.

---

## 2. Phase Execution Summary

### Phase 1: Schema Migrations, RLS, and Parity
- Created migration `002_supabase_prep.py`:
  - `CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;`
  - `ALTER TABLE chunks ADD COLUMN embedding_model TEXT;`
  - Enabled Row-Level Security (RLS) on `sessions`, `messages`, `chunks`, `artifacts`.
  - Re-created HNSW index explicitly with `WITH (m=16, ef_construction=64)`.
- Created `test_schema_parity.py` to verify ORM models against live database catalog.
- **Commit:** `01c5500c`

### Phase 2: Connection Layer & Connection Pooling
- Built `backend/app/db/connection.py`:
  - `build_engine_kwargs()`: URL cleaner that strips `sslmode` for `asyncpg` compatibility and constructs `ssl.SSLContext` in `connect_args`.
  - Transaction mode support: sets `statement_cache_size=0` and unique `prepared_statement_name_func` to avoid prepared statement conflicts over Supabase Transaction Pooler (port 6543).
  - Explicit `search_path=public,extensions` for pgvector type resolution.
- Updated `backend/app/db/session.py` with `make_cli_engine()` returning `NullPool` for ingestion.
- Updated `/api/v1/health` endpoint with DB query latency timing and target/pool metadata.
- **Commit:** `9fdc65ee` | Gate 2: 27 passed

### Phase 3: Embedding Provider Abstraction & Fallback
- Created `backend/app/rag/embeddings.py`:
  - `EmbeddingProvider` Abstract Base Class.
  - `OllamaEmbedder`: local primary provider (768-dim).
  - `NomicAtlasEmbedder`: cloud fallback provider (768-dim) when `NOMIC_API_KEY` is present.
  - `@dim_guard`: decorator enforcing strict 768-dimension vector output contract.
  - `assert_embedding_dimension_at_startup()` check.
- Updated `retriever.py` and `ingest.py` to use `embed_query_with_fallback()`.
- Added `embedding_model` provenance tracking column during ingestion.
- Added 8 unit tests in `test_embeddings.py`.
- **Commit:** `56a0953` | Gate 3: 35 passed

### Phase 4: Compose Rewrite & Configuration
- Updated `docker-compose.yml` to remove local PostgreSQL service, routing backend directly to Supabase via `.env`.
- Created `docker-compose.local.yml` to preserve single-command local offline fallback with `pgvector/pgvector:pg16` container (`DB_TARGET=local`).
- Documented all connection modes, SSL settings, and embedding options in `.env.example`.
- **Commit:** `ab56e04` | Gate 4: 35 passed

### Phase 5 & 6: Verification, Verification Gate, and Documentation
- Ran full test suite across connection, schema, embedding fallback, retriever, and session API endpoints.
- Updated `architecture.md` with **ADR-005: Managed Supabase Postgres Vector DB & Dual-Provider Embedding Architecture**.
- Finalized `README.md`, `MIGRATION_NOTES.md`, and session transcript.

---

## 3. Final Gate Status
- **Test Suite:** 35 / 35 tests PASSED (0 failures)
- **Git Commits:** 4 clean sequential commits on `feat/supabase-migration`
- **Secrets Audit:** 0 credentials committed; `.env` listed in `.gitignore`
