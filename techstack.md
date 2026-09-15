# TECH_STACK.md — The Lenny Growth Assistant

> Supersedes the earlier draft. Changes from that draft are called out inline as **[CHANGED]**.

## App Context
- **Type:** Full-stack conversational AI product + artifact viewer
- **Scale:** MVP, single-tenant demo
- **Team size:** 1 (solo, agent-assisted)
- **Timeline:** MVP due 15/09/26 EOD

---

## 1. STACK OVERVIEW

**Architecture pattern: Modular monolith + one auxiliary Node service.** **[CHANGED — was "modular monolith, one container"]**

FastAPI app (`api/`, `rag/`, `db/`, `core/`) plus a small **Node/TypeScript agent sidecar** hosting Pi Coding Agent, because Pi has no Python binding. This is the one deliberate exception to "single language, single container" — driven by a hard runtime constraint (the assignment's required agent framework choice), not a scaling decision.

**Deployment:** Docker Compose, `docker compose up` brings up **five** services: `backend`, `frontend`, `postgres`, `ollama`, `agent-sidecar`. **[CHANGED — was four services]**

**Why not microservices otherwise:** same reasoning as before — no benefit at MVP scale for the FastAPI/Postgres/retrieval pieces, which stay in one process.
**Why not serverless:** long-lived Ollama process rules it out; unrelated to the sidecar decision.

---

## 2. FRONTEND STACK
*(unchanged from original draft — no conflicts found here)*

| Decision | Choice |
|---|---|
| Framework | React 18.3.1 |
| Language | TypeScript 5.6.3 |
| Build tool | Vite 6.0.7 |
| Styling | Tailwind CSS 3.4.17 |
| State management | Zustand 5.0.2 |
| Form handling | React Hook Form 7.54.2 |
| HTTP client | Axios 1.7.9 (+ native `EventSource`/`fetch` for SSE) |
| Routing | React Router 6.28.1 |
| UI components | shadcn/ui on Radix UI primitives |

See original rationale sections — none of these were in conflict across drafts.

---

## 3. BACKEND STACK

| Decision | Choice |
|---|---|
| Runtime | Python 3.11.10 |
| Framework | FastAPI 0.115.6 |
| ASGI server | Uvicorn 0.32.1 (`[standard]`) |
| Database | PostgreSQL 16.4 + pgvector extension |
| ORM / migrations | SQLAlchemy 2.0.36 (async) + Alembic 1.14.0 |
| DB driver | asyncpg 0.30.0 (+ psycopg2-binary for Alembic offline mode) |
| Vector index | **HNSW** **[CHANGED — earlier draft said ivfflat, contradicting its own DDL]** |
| Caching | Not included at MVP scope |
| Cloud LLM client | **`groq` Python SDK** **[CHANGED — was `anthropic` SDK]** |
| Agent framework | **Pi Coding Agent, via Node sidecar** **[CHANGED — was unspecified / raw SDK]** |
| Local LLM client | `ollama` Python client 0.4.4 (used for embeddings; chat generation for local mode also routes through the sidecar for a consistent agent loop) |
| Config / validation | Pydantic 2.10.4 + pydantic-settings 2.7.0 |
| Logging | structlog 24.4.0 |
| Rate limiting | **`slowapi` 0.1.9, 20 req/min/session** **[CHANGED — earlier backend draft said N/A; kept from tech-stack draft]** |
| Authentication | None |
| File storage | Local filesystem (`data/transcripts/`) |

### Groq Python SDK **[NEW SECTION]**
- **Docs:** https://console.groq.com/docs/quickstart
- **License:** Apache-2.0
- **Reason:** Official client for the chosen cloud provider; used for both direct calls where needed and as the model backend registered in Pi's `models.json` for cloud-mode agent runs.
- **Alternatives considered:** Anthropic SDK — rejected in favor of Groq per the resolved provider decision (Groq was already load-bearing in the backend's data-flow diagram and DB schema; standardizing on it avoids a second cloud SDK/credential to manage).

### Pi Coding Agent (Node sidecar) **[NEW SECTION]**
- **Package:** `@mariozechner/pi-coding-agent`
- **Docs:** https://pi.dev/docs
- **License:** MIT
- **Reason:** The assignment mandates either the Claude Agent SDK or Pi Coding Agent for the agent layer. Claude Agent SDK is Claude-only and incompatible with a Groq-backed loop; Pi has native first-class Groq support (and Ollama via an OpenAI-compatible custom provider entry), so it's the only one of the two options that actually fits the provider decision.
- **Integration:** runs as its own container (`agent-sidecar/`), a minimal Express HTTP wrapper around a Pi `Agent` instance with three custom tools (`answer_from_context`, `generate_ship30_essay`, `generate_artifact`) replacing Pi's default file/bash tools. FastAPI calls it over the internal Docker network only — never exposed publicly.
- **Alternatives considered:** shelling out to the `pi` CLI as a subprocess per request — rejected, fragile for a stateful, streaming, multi-turn conversational loop compared to a proper long-lived HTTP service.

### PostgreSQL 16.4 + pgvector
- Same reasoning as before (single DB for relational + vector data, avoids a second vector-store dependency). **HNSW** is used consistently with the schema DDL in `architecture.md` — sufficient for a corpus of tens of episodes / thousands of chunks; no tuning parameter to babysit the way `ivfflat`'s list count would need.

### Rate limiting — `slowapi` 0.1.9
- **Reason:** Cheap insurance against runaway Groq API spend if something loops or a demo goes sideways. Sized to catch accidents, not to withstand adversarial load — documented as such rather than oversold.

*(SQLAlchemy, Alembic, asyncpg, Pydantic, structlog sections unchanged from the original draft — no conflicts.)*

---

## 4. AGENT SIDECAR STACK **[NEW SECTION]**

| Decision | Choice |
|---|---|
| Runtime | Node.js 20 LTS |
| Language | TypeScript 5.6 |
| HTTP framework | Express 4.21 (minimal — two routes, no need for anything heavier) |
| Agent | `@mariozechner/pi-coding-agent` |
| Provider config | `models.json` — `groq` (API key) + `ollama` (OpenAI-compatible local endpoint) |

Kept intentionally tiny: this service's only job is hosting the Pi agent loop and its three custom tools, then streaming responses back to FastAPI over SSE.

---

## 5. DATABASE SCHEMA
Unchanged migration/seeding/backup/pooling strategy from the original draft — no conflicts there. See `architecture.md` for the actual table definitions (that document is now authoritative for schema).

---

## 6. DEVOPS & INFRASTRUCTURE
Unchanged (Git trunk-based, GitHub Actions CI, Vercel/Railway/Supabase for the optional hosted demo, structlog + `/api/v1/health` for observability), with one addition: CI's Docker Compose smoke boot now also asserts `agent-sidecar` reports healthy, not just `backend`/`postgres`/`ollama`.

**Testing** (unchanged): Pytest 8.3.4 + pytest-asyncio + httpx (backend); Vitest 2.1.8 + RTL (frontend); Playwright 1.49.1 (E2E). Add: a small Vitest/Jest suite for the sidecar's tool-calling logic, since it's now a real service with its own behavior to verify, not just a documented option.

---

## 7. ENVIRONMENT VARIABLES **[CHANGED]**

```env
# --- Database ---
DATABASE_URL="postgresql+asyncpg://lenny:lenny@localhost:5432/lenny_growth"
ALEMBIC_DATABASE_URL="postgresql://lenny:lenny@localhost:5432/lenny_growth"

# --- LLM Provider Toggle ---
LLM_PROVIDER="ollama"                     # "groq" | "ollama" — switches the active provider, no code change
GROQ_API_KEY=""                           # Required only if LLM_PROVIDER=groq; never commit a real value
GROQ_MODEL="llama-3.3-70b-versatile"      # Cloud model identifier
OLLAMA_BASE_URL="http://ollama:11434"     # Local Ollama server address (Docker service name)
OLLAMA_MODEL="llama3.1:8b"                # Local chat model tag; must be pulled before first use
OLLAMA_EMBEDDING_MODEL="nomic-embed-text" # Embedding model; used regardless of LLM_PROVIDER

# --- Agent sidecar ---
AGENT_SIDECAR_URL="http://agent-sidecar:4000"  # Internal-only; not reachable from outside Docker network

# --- App ---
APP_ENV="development"
LOG_LEVEL="INFO"
CORS_ORIGINS="http://localhost:5173"

# --- Rate limiting ---
RATE_LIMIT_PER_MINUTE="20"                # slowapi limit per session on the messages endpoint

# --- Feature flags ---
ENABLE_SHIP30_SKILL="true"
ENABLE_HTML_ARTIFACTS="true"
```

---

## 8. DEPENDENCIES LOCK **[CHANGED — backend requirements + new sidecar package.json]**

```txt
# Backend (requirements.txt)
fastapi==0.115.6
uvicorn[standard]==0.32.1
sqlalchemy[asyncio]==2.0.36
alembic==1.14.0
asyncpg==0.30.0
psycopg2-binary==2.9.10
pgvector==0.3.6
pydantic==2.10.4
pydantic-settings==2.7.0
groq==0.13.0
ollama==0.4.4
structlog==24.4.0
slowapi==0.1.9
nh3==0.2.19
python-multipart==0.0.20
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
pytest-cov==6.0.0
ruff==0.8.4
```

```json
// agent-sidecar/package.json (excerpt)
{
  "dependencies": {
    "@mariozechner/pi-coding-agent": "^1.0.0",
    "express": "4.21.2"
  },
  "devDependencies": {
    "typescript": "5.6.3",
    "vitest": "2.1.8",
    "@types/express": "5.0.0"
  }
}
```

Frontend `package.json` dependency list unchanged from the original draft.

---

## 9. SECURITY CONSIDERATIONS **[artifact section changed]**

*(Auth, password hashing, token expiry sections unchanged — all N/A, no accounts in scope.)*

**CORS:** unchanged — explicit allow-list, `allow_credentials=False`, `GET`/`POST` only.

**Rate limiting:** `slowapi`, 20 req/min/session on `POST /api/v1/sessions/{id}/messages` — implemented, not deferred (see architecture.md's Resolved Decisions table for why this overrides the earlier "N/A" draft).

**Artifact rendering security [CHANGED]:**
- Server-side: `nh3` sanitization pass on generated HTML.
- Client-side: `sandbox="allow-scripts"` iframe, **`allow-same-origin` withheld**. Scripts execute inside the frame — this is required for the PRD's Scenario 3 test to make sense (a malicious script must run to demonstrate it can't exfiltrate anything) — but the frame cannot read cookies, `localStorage`, or the parent DOM, and cannot navigate the top-level page.
- This is a change from the earlier draft, which withheld `allow-scripts` entirely (safer in isolation, but silently breaks interactive HTML artifacts and doesn't match the PRD's own test scenario).

**Data encryption:** unchanged — TLS at the hosting platform layer if deployed beyond local Docker; local Docker Postgres has no at-rest encryption, documented as such rather than implied otherwise.

---

## 10. VERSION UPGRADE POLICY
Unchanged from original draft.