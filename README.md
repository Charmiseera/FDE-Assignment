# Lenny Growth Assistant — Grounded Operator Workbench

A production-grade, retrieval-augmented product advisor and operator workbench grounded strictly in 30 landmark transcript episodes of **Lenny's Podcast**.

The assistant answers product and growth questions with verified inline citations, enforces grounded refusals for out-of-domain queries, transforms discussions into structured **Ship 30/30 Atomic Essays** using the **Pi Coding Agent** framework, generates interactive HTML artifacts, and provides an in-app sandboxed **Artifact Viewer** with GitHub-Flavored Markdown table rendering.

---

## 1. Deliverables Index

| # | Deliverable | File / Location | Status |
|---|---|---|---|
| **1** | Public GitHub repository | Clean project structure, no secrets committed | Ready |
| **2** | `README.md` | Architecture, setup, local/cloud models, tests, troubleshooting | **This document** |
| **3** | `PRD` | Users, problem, metrics, scope, flows, acceptance criteria | [`prd.md`](./prd.md) |
| **4** | `design.md` | UI/UX principles, IA, interaction states, accessibility, responsive behavior | [`design.md`](./design.md) |
| **5** | `architecture.md` | Schema, API endpoints, boundaries, ingestion/retrieval, agent routing, topology | [`architecture.md`](./architecture.md) |
| **6** | Agent transcripts | Dedicated log folder including failed attempts and corrections | [`agent-transcripts/`](./agent-transcripts/) |
| **7** | Automated & Manual Tests | Automated test suites (backend, sidecar, frontend) + UI manual test plan | Section 7 below |
<<<<<<< HEAD
| **8** | Demo video | 2–3 minute recording with camera enabled, local Ollama, and technical trade-off | [`scripts/DEMO_SCRIPT.md`](./scripts/DEMO_SCRIPT.md) |

=======
>>>>>>> 503beab974790ed07e7e47e813504bd99229ddc0
---

## 2. Architecture Overview

- **FastAPI Modular Backend (Python 3.11):** Implements async endpoints for session management, message handling, grounded RAG retrieval, and configuration.
- **Database & Vector Store:** Managed Supabase PostgreSQL with `pgvector` HNSW cosine similarity index (768-dimensional vectors).
- **Embedding Layer:** Abstracted dual-provider pattern (`Ollama` local default with `nomic-embed-text`, cloud fallback to Nomic Atlas API).
- **LLM Layer:** Seamless toggle between Local (`Ollama` with `qwen2.5:3b`) and Cloud (`Groq` with `openai/gpt-oss-120b`).
- **Pi Coding Agent Sidecar (Node.js/TypeScript):** Dedicated microservice running `@mariozechner/pi-coding-agent` with custom tool definitions (`validate_essay`, `render_check`) and self-correction loops.
- **Frontend Workbench (React 18 + Vite + Tailwind CSS):** Clean editorial aesthetic with session sidebar, streaming chat, live provider switching, active in-flight request cancellation (`Stop` button), and split-pane Artifact Viewer.

```
┌─────────────────────────────────────────────────────────────┐
│              Frontend Client (React + Vite)                 │
│    - Chat & Q&A      - In-flight Stop     - Artifact Viewer │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend                          │
│  - Session Orchestration       - RAG Cosine Retrieval       │
│  - Grounded Refusal Filter     - Provider Toggle            │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │ Internal HTTP
┌──────────────▼─────────────┐   ┌─────────────▼──────────────┐
│   PostgreSQL + pgvector    │   │      Agent Sidecar         │
│   (Supabase Managed / DB)  │   │  (@mariozechner/pi-coding) │
│ - 768-dim HNSW Vector Idx  │   │ - validate_essay tool      │
│ - Sessions & Messages      │   │ - render_check tool        │
└────────────────────────────┘   └────────────────────────────┘
```

---

## 3. Prerequisites

- **Python 3.11+**
- **Node.js 18+** and `npm`
- **Docker & Docker Compose** (optional for containerized deployment)
- **Ollama** installed and running locally (`ollama serve`)
- (Optional for Cloud Mode) **Groq API Key** (`GROQ_API_KEY`)

---

## 4. Environment Variables Reference

Create a `.env` file in the root directory (or copy `.env.example`):

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `DB_TARGET` | `supabase` | `supabase` for cloud managed DB or `local` for local Postgres |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async connection string for FastAPI application |
| `ALEMBIC_DATABASE_URL` | `postgresql://...` | Sync connection string used by Alembic migrations |
| `SUPABASE_SSL_REQUIRED` | `true` | Enables TLS verification for Supabase pooler connections |
| `LLM_PROVIDER` | `ollama` | Default active model provider (`ollama` or `groq`) |
| `GROQ_API_KEY` | `gsk_...` | Groq API Key for cloud inference |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | High-speed cloud reasoning model hosted on Groq |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint of local Ollama daemon |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local generation model |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | 768-dimensional local embedding model |
| `AGENT_SIDECAR_URL` | `http://localhost:4000` | Address of internal Pi Agent microservice |
| `RATE_LIMIT_PER_MINUTE` | `20` | Per-session sliding rate limit |

---

## 5. Model Setup

### Local Models (Ollama)
Ensure Ollama is running, then pull the required models:
```bash
# Pull local embedding model (768-dim)
ollama pull nomic-embed-text

# Pull local inference model
ollama pull qwen2.5:3b
```

### Cloud Models (Groq)
Obtain a free API key from [Groq Console](https://console.groq.com) and set it in `.env`:
```env
GROQ_API_KEY="gsk_..."
GROQ_MODEL="openai/gpt-oss-120b"
```

---

## 6. Running the Application

### Option A: Local Development (Recommended)

1. **Start the Agent Sidecar (Port 4000):**
   ```bash
   cd agent-sidecar
   npm install
   npx tsx watch src/server.ts
   ```

2. **Start the FastAPI Backend (Port 8000):**
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Start the Frontend (Port 5173):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

### Option B: Docker Compose

```bash
# Build and start all services (Backend, Frontend, Sidecar)
docker compose up --build
```

---

## 7. Testing & Verification

### Automated Backend Tests (pytest)
Runs 35 tests covering API routes, vector retrieval, embeddings, session persistence, and error envelopes:
```bash
cd backend
python -m pytest tests/ --ignore=tests/test_schema_parity.py -v
```
*Result: 35 passed in ~6.8s.*

### Automated Agent Sidecar Tests (vitest)
Runs 12 unit tests verifying the Pi Coding Agent tools (`validate_essay`, `render_check`) and prompt builders:
```bash
cd agent-sidecar
npm test
```
*Result: 4 test files passed, 12 tests passed.*

### Frontend Production Build & TypeScript Verification
```bash
cd frontend
npm run build
```
*Result: `tsc -b && vite build` passed with zero errors.*

<<<<<<< HEAD
### Manual UI Verification Plan

1. **Grounded Q&A Flow:**
   - Ask: *"What is Elena Verna's advice on B2B product-led growth?"*
   - Verify: Response streams back with numbered sources citing Elena Verna's episode.
2. **Grounded Refusal Filter:**
   - Ask: *"How do I bake a chocolate cake?"*
   - Verify: System immediately returns a refusal stating the question is not covered in Lenny's Podcast transcripts; no hallucinations.
3. **In-Flight Cancellation (`Stop` Button):**
   - Click a quick-prompt button. While *"Consulting transcripts..."* appears, click the red **[■ Stop]** button.
   - Verify: Request is aborted cleanly via `AbortController`, spinner disappears, and chat adds `*(Generation stopped by user)*`.
4. **Ship 30/30 Essay Generation & Artifact Viewer:**
   - Click **"Generate Ship 30/30 Essay"**.
   - Verify: Assistant responds with essay summary and renders a **"View Generated Artifact"** button.
   - Click **"View Generated Artifact"**: The right-hand pane slides open displaying the structured essay with title, bold text, subheadings, GFM tables, and a **Key Takeaway** section.
5. **Local vs. Cloud Toggle:**
   - In the header, toggle between **Local (Ollama)** and **Cloud (Groq)**.
   - Verify: The active badge updates immediately and requests route through the selected model.

=======
>>>>>>> 503beab974790ed07e7e47e813504bd99229ddc0
---

## 8. Troubleshooting

1. **Artifact displays empty or 404:**
   - Verify that `agent-sidecar` is running on port 4000 (`http://localhost:4000/health`).
   - The system includes automatic draft extraction from `toolCalls` and dual database lookup fallbacks.
2. **Groq Model Not Found (404):**
   - Ensure `GROQ_MODEL="openai/gpt-oss-120b"` in `.env`.
3. **CORS Errors (`blocked by CORS policy`):**
   - Confirm backend is running on `http://localhost:8000` with `CORS_ORIGINS="http://localhost:5173"`.
4. **Ollama Connection Refused:**
   - Start Ollama in a separate terminal: `ollama serve`.

<<<<<<< HEAD
=======
---
>>>>>>> 503beab974790ed07e7e47e813504bd99229ddc0
