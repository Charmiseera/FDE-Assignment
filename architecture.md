# architecture.md — The Lenny Growth Assistant

> This is the authoritative architecture document (supersedes `BACKEND_STRUCTURE.md`). It reconciles the conflicts found across the original PRD/app-flow/frontend/backend/tech-stack drafts. Resolved decisions are called out explicitly wherever a conflict existed, so a reader isn't left guessing which draft "won."

---

## Resolved decisions (read this first)

| Decision point | Resolution | Why |
|---|---|---|
| Cloud LLM provider | **Groq** | Matches the original backend draft; assignment allows any cloud provider ("such as Anthropic or OpenAI" is illustrative, not exhaustive). |
| Agent framework | **Pi Coding Agent** | Assignment mandates Claude Agent SDK *or* Pi Coding Agent. Claude Agent SDK is Claude-only and incompatible with a Groq-backed agent loop; Pi has native first-class Groq support. |
| Pi/Python integration | **Node sidecar service**, called over internal HTTP | Pi Coding Agent is a Node/TypeScript harness with no Python binding. Rather than shelling out to a CLI per request (fragile for structured, streaming, multi-turn use), Pi runs as its own lightweight containerized service with custom tools, and FastAPI calls it internally. This is a documented cross-language service boundary, not a workaround. |
| Vector index | **HNSW** | Was already correct in the DDL; an earlier draft's prose incorrectly said `ivfflat`. |
| Rate limiting | **Implemented** (`slowapi`, 20 req/min/session) | An earlier draft called this N/A; kept in because it's cheap insurance against runaway Groq spend during a live demo, at negligible complexity cost. |
| Artifact sandbox | **Scripts allowed, isolated** (`sandbox="allow-scripts"`, no `allow-same-origin`) | The PRD's own security test (Scenario 3) requires a malicious script to *execute* but be unable to reach cookies/parent — that only works if scripts are allowed to run at all. |
| Dataset Scope | **303 Episodes total, 30 Index-Backed Landmark Episodes Default** | Verified ChatPRD repository clone contains exactly 303 episodes. Top 30 selected based on occurrence across core topic index files. |

---

## Architecture Overview

- **Pattern:** Modular monolith (FastAPI) + one auxiliary service (the Pi agent sidecar). Not full microservices — the sidecar exists solely because Pi is a separate-language runtime, not because of a scaling need.
- **Authentication strategy:** None — single implicit user per running instance (see PRD Out of Scope #1).
- **Data flow:**
  ```
  User message (frontend)
      → POST /api/v1/sessions/{id}/messages
      → [validate input]
      → [embed query via Ollama (nomic-embed-text)]
      → [pgvector HNSW similarity search over chunks]
      → [if no chunks above threshold] → return grounded-refusal response
      → [request routing]:
            - Standard Q&A: processed directly via Groq/Ollama from FastAPI.
            - Ship 30/30 Skill & HTML Artifacts: POST http://agent-sidecar:4000/run
      → [persist message + response + citations + artifact (if any) to Postgres]
      → response returned to frontend
  ```
- **Caching strategy:** No Redis. Only cache: embedding-skip on unchanged chunks during re-ingestion (via `content_hash`, a plain Postgres column check — not a cache store).

---

## ADR-004: Agent Microservice Sidecar Scope Boundary & Database Isolation

- **Scope Boundary & Tool-Calling Architecture:**
  - Standard grounded Q&A requests (`request_type === "answer"`) route directly from FastAPI to Groq/Ollama via direct `generateText()` calls, bypassing the Pi agent framework entirely. This is an intentional, permanent design decision: retrieval/grounding must be deterministic and metric-critical, not subject to agent tool-calling indeterminism.
  - The `agent-sidecar` microservice initializes stateless `@mariozechner/pi-coding-agent` agent sessions with registered custom tools for complex, rule-validated output skills:
    1. **Ship 30 for 30 Atomic Essays**: Uses Pi agent session with `validate_essay` tool (TypeBox schema: `{ draft: Type.String() }`). The agent generates drafts, calls the tool to check structural constraints (word count 1,063–1,438, >=2 subheadings, bold emphasis, takeaway), and self-corrects based on tool feedback. The attempt harness enforces a 2-attempt safety cap via `session.abort()`.
    2. **HTML/CSS Visual Artifacts**: Uses Pi agent session with `render_check` tool (TypeBox schema: `{ html: Type.String() }`). The agent self-corrects malformed HTML (`<!DOCTYPE html>`, `<body>`, `<title>`, balanced container tags) before returning.
- **Database & Security Isolation (Verified):**
  - The `agent-sidecar` (`server.ts`) contains **zero database driver libraries, zero ORM modules, and zero database connection credentials**.
  - All SQL queries, vector searches, and session/message persistence occur exclusively inside FastAPI. The sidecar acts purely as a stateless compute service over internal HTTP (`http://agent-sidecar:4000`).

---

## Ingestion & Transcript Topic Selection Criteria

- **Verified Corpus Size:** Exactly **303 episodes** present in `episodes/{guest}/transcript.md`.
- **Top-N Selection Rationale:**
  Selected episodes are drawn from cross-referencing the ChatPRD repository's own topic index files:
  `index/product-management.md`, `index/product-led-growth.md`, `index/retention.md`, `index/leadership.md`, `index/ai.md`, and `index/power.md`.
  Episodes with the highest co-occurrence across these core indices (such as Naomi Gleit, Tamar Yehoshua, Elena Verna, Brian Chesky, Noah Weiss, and Dylan Field) are selected as the default **30 landmark episodes**.
  This maximizes topical coverage relevant to PM and growth evaluation queries while keeping local embedding time bounded (~15 mins vs ~5 hours for all 303 episodes).

---

## HTML/CSS Artifact Intent Disambiguation Heuristic

- **Classification Logic:**
  - Artifact keywords: `html`, `css`, `landing page`, `component`, `dashboard`, `visual artifact`, `mockup`.
  - Question markers: `what`, `how`, `why`, `which`, or ending with `?`.
  - If a user prompt contains artifact keywords BUT is phrased as a question (e.g. *"What CSS frameworks are mentioned in the transcripts?"*), it is treated as a standard Q&A request.
  - If a user prompt contains artifact keywords AND is phrased as a directive/command (e.g. *"Create an HTML landing page component for this retention framework"*), it routes to `html_artifact`.
  - **Ambiguity Fallback:** If prompt intent remains genuinely ambiguous, the assistant asks a short one-line clarifying question: *"Would you like a grounded explanation from the transcripts, or a rendered interactive HTML artifact?"*

---

## Database Schema

All tables use UUID primary keys and `created_at` timestamps. `updated_at` omitted where rows are append-only (messages, artifacts).

### `sessions`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Session identifier |
| title | VARCHAR(200) | NULL | Auto-generated from first message |
| provider_at_creation | VARCHAR(20) | NOT NULL | `groq` or `ollama` — which was active at session start |
| user_metadata | JSONB | NOT NULL, DEFAULT '{}' | Reserved, empty in this version (no user identity) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

Index: `id` (PK), `created_at` (sidebar ordering).

### `messages`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| session_id | UUID | NOT NULL, FK → sessions(id) ON DELETE CASCADE | |
| role | VARCHAR(10) | NOT NULL, CHECK IN ('user','assistant') | |
| content | TEXT | NOT NULL | |
| provider_used | VARCHAR(20) | NULL | `groq` / `ollama`, NULL for user messages |
| citations | JSONB | NOT NULL, DEFAULT '[]' | `[{chunk_id, source_file, episode_title}]` |
| artifact_id | UUID | NULL, FK → artifacts(id) ON DELETE SET NULL | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

Index: `(session_id, created_at)` — hot path is "all messages for session X in order."

### `chunks`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| source_file | VARCHAR(255) | NOT NULL | |
| episode_title | VARCHAR(255) | NOT NULL | |
| chunk_index | INTEGER | NOT NULL | |
| chunk_text | TEXT | NOT NULL | |
| content_hash | VARCHAR(64) | NOT NULL | SHA-256, skips re-embedding unchanged chunks |
| embedding | VECTOR(768) | NOT NULL | `nomic-embed-text` dimension |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

Constraint: UNIQUE `(source_file, chunk_index)` — idempotent re-ingestion upsert key.

```sql
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
```

### `artifacts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| session_id | UUID | NOT NULL, FK → sessions(id) ON DELETE CASCADE | |
| type | VARCHAR(20) | NOT NULL, CHECK IN ('markdown','html') | |
| content | TEXT | NOT NULL | Raw artifact source — kept 100% clean/publish-ready; validation problems never get written into this field |
| title | VARCHAR(200) | NULL | |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | Structured side-channel data about the artifact, e.g. `{"validation_status": {"passed": false, "word_count": 1050, "unmet_criteria": ["too short"]}}` for a Ship 30/30 essay that failed structural validation after its one retry. The frontend renders this as a warning banner in the Artifact Viewer — never merges it into `content`. |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

Index: `session_id`.

**FK direction is intentionally one-way:** `messages.artifact_id → artifacts.id` (nullable, `ON DELETE SET NULL`) is the only link between the two tables. `artifacts` does **not** carry a `message_id` back-reference — a bidirectional FK would create an insert-ordering problem (each row would need the other's ID before either can be created) for no benefit, since `session_id` already scopes an artifact to its conversation.

**Tables deliberately not included:** `users` (no auth), auth-token storage (no auth layer), junction tables (no many-to-many relationships in this model).

---

## API Endpoints

Base path: `/api/v1`.

### `POST /api/v1/sessions`
Creates a session. Body `{}`. Returns `201 { success, data: { session_id, created_at } }`. Errors: `500`.

### `GET /api/v1/sessions`
Lists sessions, most recent first. Returns `200 { success, data: [{ session_id, title, created_at }] }`.

### `GET /api/v1/sessions/{session_id}/messages`
Full message history. `404` if session doesn't exist.

### `POST /api/v1/sessions/{session_id}/messages`
Send a message, get a grounded response.
- Validation: `content` non-empty after trim, max 4,000 chars.
- Response `200`:
  ```json
  { "success": true, "data": {
      "message_id": "uuid", "content": "...",
      "citations": [{ "source_file": "ep123.txt", "episode_title": "..." }],
      "artifact_id": null, "provider_used": "groq"
  }}
  ```
- Errors: `400 VALIDATION_ERROR`, `404 NOT_FOUND`, `502 PROVIDER_ERROR` (Groq/Ollama/sidecar unreachable), `500 INTERNAL_ERROR`.
- Rate limit: 20 requests/minute/session (`slowapi`) — returns `429 RATE_LIMITED`.

### `GET /api/v1/health`
```json
{ "success": true, "data": {
    "database": "ok",
    "configured_provider": "groq",
    "provider_reachable": true,
    "ollama_reachable": true,
    "agent_sidecar_reachable": true
}}
```
Returns `503` if the database is down. Provider/sidecar unreachability is reported but doesn't itself 503 the health check (session/history reads still work).

### `GET /api/v1/config`
```json
{ "success": true, "data": { "llm_provider": "groq", "model": "llama-3.3-70b-versatile", "embedding_model": "nomic-embed-text" } }
```

### Ingestion — not an HTTP endpoint
CLI-only: `python -m app.ingestion.ingest --refresh`. Not exposed over HTTP — no reason for an unauthenticated public endpoint to trigger re-embedding work.

---

## Authentication & Authorization — N/A, with reasoning
No auth. Single operator per instance (PRD Out of Scope #1). If this became multi-tenant, the addition point is a `users` table + bearer-token gate on `/api/v1/*` + `user_id` FK on `sessions` — schema doesn't need restructuring for that later.

## Data Validation
- Message content: non-empty after trim, max 4,000 chars.
- User content never rendered as HTML — plain text/Markdown-escaped. Raw HTML only ever renders inside the sandboxed Artifact Viewer, and only for assistant-generated artifacts.

## Error Handling
```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "content must not be empty" } }
```
| Code | HTTP | When |
|---|---|---|
| VALIDATION_ERROR | 400 | Empty/oversized content |
| NOT_FOUND | 404 | Session doesn't exist |
| PROVIDER_ERROR | 502 | Groq, Ollama, or the agent sidecar unreachable/errored |
| RATE_LIMITED | 429 | >20 req/min on a session |
| INTERNAL_ERROR | 500 | Database or unhandled exception |

## Rate Limiting
`slowapi` sliding-window limiter, 20 requests/minute per session, on `POST /api/v1/sessions/{id}/messages`. Sized to catch a runaway loop or accidental spam during the demo, not to withstand adversarial load — documented as such, not oversold as production-grade protection.

## Caching Strategy
Only the ingestion-time embedding skip (`content_hash` column check). No Redis, no response caching — every question re-runs retrieval and generation.

## Database Migrations
Alembic, autogenerated then hand-reviewed before `alembic upgrade head`. No manual schema edits against a running database.

## Backup & Recovery — N/A for this version
Disposable, regeneratable data (chunks re-ingestible from source; chat history has no continuity requirement for a demo). Post-MVP: managed Postgres backups (Supabase/Railway both offer these at the platform level).

## API Versioning
`/api/v1/` from day one, no v2 planned. Costs nothing now, avoids a breaking migration later.

## Security

- **CORS:** explicit allow-list via `CORS_ORIGINS` (default `http://localhost:5173` only), `allow_credentials=False`, methods restricted to `GET`/`POST`.
- **Artifact rendering (the assignment's explicit security requirement):**
  - Server-side: HTML sanitized via `nh3` (Rust-backed, strips unexpected script/event-handler patterns where they'd interfere with sandboxing — not a substitute for the sandbox itself).
  - Client-side: rendered in a `sandbox="allow-scripts"` iframe with `allow-same-origin` **withheld**. Scripts inside the artifact execute, but the frame has no access to the parent's cookies, `localStorage`, DOM, or ability to navigate the top-level page — this is what makes PRD Scenario 3's test (malicious script runs but can't exfiltrate anything) actually true.
  - Markdown artifacts render through a safe Markdown renderer with no raw-HTML passthrough (`react-markdown`, no `dangerouslySetInnerHTML`).
- **Data at rest:** TLS terminated at the hosting platform (Vercel/Railway) if deployed beyond local Docker; local Docker Postgres has no at-rest encryption configured, and the README does not claim otherwise.

## Deployment Topology

Docker Compose, five services on one host:
```
frontend (Vite/React) ── backend (FastAPI) ── postgres (pgvector)
                              │
                              └── agent-sidecar (Node/Pi) ── groq (external) / ollama (container)
```
No Kubernetes, no serverless — a long-lived Ollama process rules out serverless regardless, and one developer building in a short window gets no benefit from microservice-style network boundaries beyond the one forced by Pi's language runtime.

---

## ADR-005: Managed Supabase Postgres Vector DB & Dual-Provider Embedding Architecture

- **Context & Motivation:**
  The initial stack used a local `pgvector/pgvector:pg16` Docker container for Postgres/vector storage. For production scalability, zero-downtime persistence, and cloud hosting capability, the database target was migrated to Supabase managed PostgreSQL.
- **Key Architecture Decisions:**
  1. **Single Migration Tooling (Alembic):** Retained Alembic as the single source of schema truth (`backend/alembic/versions/002_supabase_prep.py`). Avoided dual DDL tools.
  2. **Connection & Pooling Configuration:**
     - Uses Supabase Session Mode Pooler (IPv4, port 5432) as primary backend engine.
     - Disables `sslmode` in `DATABASE_URL` string to satisfy `asyncpg` strict parameter rules; supplies `ssl.SSLContext` via SQLAlchemy `connect_args`.
     - Transaction mode (port 6543) support sets `statement_cache_size=0` and custom `prepared_statement_name_func` to avoid prepared statement collision traps.
     - CLI ingestion uses `NullPool` short-lived engine to prevent pool exhaustion during batching.
  3. **Row-Level Security (RLS) & Schema Parity:**
     - Vector extension placed explicitly in `extensions` schema with `search_path=public,extensions`.
     - RLS enabled across all core tables (`sessions`, `messages`, `chunks`, `artifacts`).
  4. **Embedding Provider Abstraction (`embeddings.py`):**
     - Primary: Ollama `nomic-embed-text` (768-dim, local).
     - Fallback: Nomic Atlas Cloud API (768-dim) when configured and primary is unreachable.
     - Dimension Guard: Decorator enforces strict 768-dim output contract; failure triggers grounded refusal downstream (never HTTP 500).
     - Provenance tracking: `embedding_model` column on `chunks` table records source model per chunk.
