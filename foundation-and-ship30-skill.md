# Task Plan: Foundation & Ship 30/30 Essay Generation (Step 4.2)

- **Task Slug:** `foundation-and-ship30-skill`
- **Goal:** Implement the full monorepo foundation (Phases 1–3) and Step 4.2 (Ship 30/30 Essay Generation Skill) end-to-end for The Lenny Growth Assistant.
- **Reference Docs:** [prd.md](file:///d:/FDE/prd.md), [appflow.md](file:///d:/FDE/appflow.md), [techstack.md](file:///d:/FDE/techstack.md), [frontend.md](file:///d:/FDE/frontend.md), [backend.md](file:///d:/FDE/backend.md), [implementation.md](file:///d:/FDE/implementation.md).

---

## Breakdown & Milestones

### Phase 1: Monorepo Foundation & Database (Steps 1.1 - 1.3)
- [x] Scaffold `backend/`, `frontend/`, `agent-sidecar/`, `data/transcripts/`.
- [x] Create `docker-compose.yml` with `postgres` (pgvector:pg16), `ollama`, `backend`, `agent-sidecar`, `frontend` (all with healthchecks; sidecar internal only).
- [x] Create `.env.example` and `.env` with Groq / Ollama toggles and sidecar config.
- [x] Write SQLAlchemy models (`Session`, `Message`, `Chunk`, `Artifact`) matching schema (`sessions.updated_at`, `artifacts.metadata` JSONB, one-way FK, `messages.citations` JSONB, pgvector HNSW index).
- [x] Write initial Alembic migration `001_initial_schema.py`.
- [x] Pin `backend/requirements.txt` verbatim from `techstack.md` §8.

### Phase 2: Design System & Core Components (Steps 2.1 - 2.2)
- [x] Configure Tailwind CSS with Ink, Signal Teal, and Paper token palettes.
- [x] Setup IBM Plex Sans/Mono and Source Serif typography.
- [x] Build core UI components: `Button`, `Card`, `Alert`.

### Phase 3: Session Management & Model Provider Toggle (Steps 3.1 - 3.2)
- [x] Implement FastAPI endpoints: `POST /api/v1/sessions`, `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}/messages`, `GET /api/v1/config`, `GET /api/v1/health`.
- [x] Build frontend `SessionSidebar` (New Chat + session list) and `Header` Provider Badge.

### Phase 4: Step 4.2 Ship 30/30 Essay Generation & Artifact Viewer
- [x] Scaffold Node.js Express sidecar with `@mariozechner/pi-coding-agent` (no CORS, internal network only).
- [x] Implement `agent-sidecar/src/tools/generate_ship30_essay.ts` and `validateEssay()`.
- [x] Implement retry-once loop and disclaimer metadata (`validation_status: { passed: boolean, unmet_criteria: [] }`).
- [x] Add sidecar `POST /run` handling for `request_type: "ship30_essay"`.
- [x] Wire `POST /api/v1/sessions/{id}/messages` to route essay generation requests to the sidecar and save generated `Artifact`.
- [x] Build `ArtifactViewer` pane in frontend with Markdown rendering, raw source toggle, and editorial disclaimer `Alert` banner for unmet criteria.
- [x] Add test suite in `agent-sidecar/tests/` (3/3 passing) and frontend Vitest suite (1/1 passing).
