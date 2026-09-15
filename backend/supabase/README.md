# Supabase Setup

This project uses hosted Supabase for Postgres + pgvector.

## Prerequisites

- A Supabase project created at https://supabase.com
- Project database password in hand (from Project Settings > Database)
- Python 3.11+, pip, and the backend requirements installed

## 1. Create the project

Create a new project in the Supabase dashboard. Once provisioned (takes ~2 min):

## 2. Configure connection strings

Go to **Project Settings > Database > Connect** and locate:

- **Session-mode pooler** (recommended for this app):
  - Host: `aws-0-<region>.pooler.supabase.com`
  - Port: `5432`
  - Username: `postgres.<project-ref>`

Fill your `.env` file (at the repo root):

```
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:[PWD]@aws-0-<region>.pooler.supabase.com:5432/postgres
ALEMBIC_DATABASE_URL=postgresql://postgres.<ref>:[PWD]@aws-0-<region>.pooler.supabase.com:5432/postgres
DB_TARGET=supabase
SUPABASE_POOL_MODE=session
```

**Do not add `?sslmode=require`** to the URL — TLS is configured via `SUPABASE_SSL_REQUIRED=true`
(see backend/app/db/connection.py). Adding sslmode to an asyncpg URL raises at connect time (Trap T2).

## 3. Apply migrations

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, initial schema
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_supabase_prep, supabase_prep
```

## 4. Verify

```bash
SUPABASE_TEST_URL="postgresql://postgres.<ref>:[PWD]@aws-0-<region>.pooler.supabase.com:5432/postgres" \
  pytest backend/tests/test_schema_parity.py -v
```

## 5. Ingest transcripts

```bash
docker compose up --build
docker exec lenny_backend python -m app.ingestion.ingest --limit 30
```

## Rollback

Point `DB_TARGET=local` and run the local compose profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

The Supabase project is unaffected. Run `alembic downgrade 001_initial_schema` against Supabase
only if you explicitly want to undo RLS and the embedding_model column.

## Connection mode reference

| Mode | URL pattern | Port | IPv4 | Prepared stmts |
|------|-------------|------|------|----------------|
| Session pooler (default) | `postgres.<ref>@pooler-host:5432` | 5432 | ✅ | ✅ |
| Transaction pooler | `postgres.<ref>@pooler-host:6543` | 6543 | ✅ | ❌ |
| Direct | `postgres@db.<ref>.supabase.co:5432` | 5432 | ⚠️ IPv6 only | ✅ |
