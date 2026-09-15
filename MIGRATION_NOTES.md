# MIGRATION_NOTES.md — Supabase Migration

## Recon Findings

| Item | Assumption | Reality |
|------|-----------|---------|
| models path | backend/app/models.py | backend/app/db/models.py |
| sessions path | backend/app/api/sessions.py | backend/app/api/v1/endpoints/sessions.py |
| health path | backend/app/api/health.py | backend/app/api/v1/endpoints/health.py |
| HNSW params | m=16, ef=64 in Alembic | Raw op.execute() with no WITH clause; defaults match but not explicit |
| Nomic prefixes | assumed present | ABSENT in both ingest.py and retriever.py |
| Ingestion engine | separate CLI engine | Imports AsyncSessionLocal from session.py (request-path engine) |
| Migration tool | TBD | Alembic already present with 001_initial_schema.py |

## Pre-Migration Findings (Unrelated - logged, not fixed unless asked)

| Finding | File | Severity |
|---------|------|----------|
| GROQ_MODEL default mismatch | config.py:L20 vs .env.example | Low (Appendix A) |
| Frontend API_BASE hardcoded | frontend/src/App.tsx:L9 | Low (Appendix A) |
| build_session_log.md says threshold 0.50, code uses 0.60 | build_session_log.md | Low (Appendix A) |

## Phase Gate Results

### Phase 1 — Schema as versioned migrations
Status: IN PROGRESS
Files changed:
  - backend/alembic/versions/002_supabase_prep.py [NEW]
  - backend/app/db/models.py [MODIFIED — added embedding_model column]
  - backend/tests/test_schema_parity.py [NEW]
  - backend/supabase/README.md [NEW]
  - MIGRATION_NOTES.md [NEW]
Gate 1: PENDING — awaiting Supabase project connection strings from user

### Phase 2 — PENDING
### Phase 3 — PENDING
### Phase 4 — PENDING
### Phase 5 — PENDING
### Phase 6 — PENDING

## Numbers (filled after Phase 5)
- Episode count: TBD
- Chunk count: TBD
- Ingest wall-clock: TBD
- HNSW index build time: TBD
- pgvector version: TBD
- search_path: TBD
