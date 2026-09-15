# Lenny Growth Assistant — RAG Architecture & Infrastructure

The Lenny Growth Assistant is a RAG-powered product advisor built over 30 landmark transcript episodes of Lenny's Podcast.

---

## Technical Stack & Architecture

- **Backend:** FastAPI (Python 3.11), SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Database & Vector Store:** Managed Supabase PostgreSQL with `pgvector` HNSW cosine similarity index (768-dim)
- **Embedding Layer:** Abstracted provider pattern (`Ollama` local default, `Nomic Atlas` cloud fallback, 768-dim guard contract)
- **LLM Layer:** Groq (`llama-3.3-70b-versatile`) or Ollama (`qwen2.5:3b`)
- **Agent Microservice:** Node.js sidecar running Pi Coding Agent framework (`@mariozechner/pi-coding-agent`) for Ship 30 essays and HTML/CSS visual artifacts
- **Frontend:** Vite, React 18, TypeScript, TailwindCSS

---

## Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local CLI / test execution)
- Node.js 18+ (for frontend / sidecar)
- Ollama (running locally with `nomic-embed-text`) OR a `NOMIC_API_KEY` for cloud embeddings

### 2. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```
Fill in your Supabase connection strings from the Supabase Dashboard:
- `DB_TARGET="supabase"`
- `DATABASE_URL="postgresql+asyncpg://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres"`
- `ALEMBIC_DATABASE_URL="postgresql://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres"`
- `SUPABASE_SSL_REQUIRED="true"`

### 3. Run Schema Migrations
Apply Alembic migrations to target database:
```bash
cd backend
alembic upgrade head
```

### 4. Ingest Transcript Corpus
Ingest and embed the 30 landmark transcript episodes:
```bash
cd backend
python -m app.ingestion.ingest --refresh
```

### 5. Launch Application
To launch with Docker Compose against Supabase:
```bash
docker compose up --build
```

To run completely offline with local Postgres container fallback:
```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

---

## Verification & Testing

Run full backend test suite:
```bash
cd backend
python -m pytest tests/ --ignore=tests/test_schema_parity.py -v
```

Run schema parity verification against active database:
```bash
cd backend
SUPABASE_TEST_URL="postgresql+asyncpg://..." python -m pytest tests/test_schema_parity.py -v
```

---

## Troubleshooting Common Supabase Errors

1. **`asyncpg.exceptions.InvalidAuthorizationSpecificationError: sslmode is not supported`**
   - *Fix*: Do not append `?sslmode=require` to `DATABASE_URL`. `asyncpg` handles TLS via `connect_args={"ssl": ssl_context}`.
2. **`asyncpg.exceptions.PreparedProtocolError: prepared statement "..." already exists`**
   - *Fix*: Set `SUPABASE_POOL_MODE="transaction"` in `.env`. This sets `statement_cache_size=0` and generates unique prepared statement names.
3. **`pgvector type undefined`**
   - *Fix*: Ensure migration 002 ran: `CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;` and `search_path=public,extensions` is set.
