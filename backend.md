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
      → [else] → POST http://agent-sidecar:4000/run
            (payload: retrieved chunks, conversation history, active provider = groq | ollama)
            → Pi Coding Agent loop, custom tools:
                - answer_from_context   (default path)
                - generate_ship30_essay (Ship 30/30 skill)
                - generate_artifact     (Markdown/HTML)
            → sidecar calls Groq or Ollama directly per LLM_PROVIDER, streams tokens back
      → [persist message + response + citations + artifact (if any) to Postgres]
      → response streamed back to frontend
  ```
- **Caching strategy:** No Redis. Only cache: embedding-skip on unchanged chunks during re-ingestion (via `content_hash`, a plain Postgres column check — not a cache store).

---

## Agent Layer — Pi Coding Agent (Node sidecar)

- **Why a sidecar:** Pi Coding Agent (`@mariozechner/pi-coding-agent`) is Node/TypeScript with no Python SDK. Running it as its own container avoids brittle subprocess/CLI scraping and keeps the agent loop's tool-calling, streaming, and provider-switching logic inside the runtime Pi was actually built for.
- **Service:** `agent-sidecar` — minimal Express/Fastify HTTP wrapper around a Pi `Agent` instance, exposing:
  - `POST /run` — takes `{ provider, model, context_chunks, conversation, request_type }`, returns a streamed response (SSE) proxied back through FastAPI to the frontend.
  - `GET /health` — reports sidecar liveness + which provider it's currently configured against, folded into the main `/api/v1/health` response.
- **Custom tools (replacing Pi's default read/write/edit/bash):**
  - `answer_from_context` — grounded Q&A using only the chunks passed in; must refuse if context is insufficient.
  - `generate_ship30_essay` — encodes the Ship 30/30 structural rules (hook, ~1,250 words, subheadings, bold emphasis, takeaway) as a Pi skill, with the retry-once-then-disclaimer validation loop from `APP_FLOW.md` §2.3.
  - `generate_artifact` — emits Markdown or a complete HTML/CSS snippet; HTML output is treated as untrusted downstream (see Security).
- **Provider routing:** Pi's `models.json` registers two provider entries — `groq` (API key) and `ollama` (local, OpenAI-compatible endpoint at `http://ollama:11434/v1`). `LLM_PROVIDER` env var picked up by FastAPI is passed through to the sidecar per-request; no code change needed to switch.
- **Network isolation:** the sidecar is **not** exposed outside the Docker Compose internal network — only `backend` can reach it. It never talks to the frontend or the public internet directly except outbound to Groq/Ollama.
- **Failure handling:** if the sidecar is unreachable, `/run` calls fail fast with a `502 PROVIDER_ERROR`, surfaced by the frontend exactly as an LLM-provider failure (no separate UI state needed for "sidecar down" vs. "provider down" — from the user's perspective they're the same failure mode).

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