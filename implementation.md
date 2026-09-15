# IMPLEMENTATION_PLAN.md — The Lenny Growth Assistant

> **A note on scope vs. the standard template:** this plan follows the requested structure but adapts two things to reality. (1) There is **no Authentication System phase** — the PRD explicitly excludes accounts/auth (`PRD.md` §6, item 1), so that phase is replaced with **Session Management & Provider Toggle**, which is this app's actual foundational P0 layer. (2) Durations are in **hours across a 3-day window**, not weeks — the assignment is due 15/09/26 EOD and today is 13/09/26, which is also consistent with `tech_stack.md`'s own "48-hour solo build" framing. Padding this with week-scale milestones would misrepresent the real timeline.

---

## OVERVIEW

- **Project name:** The Lenny Growth Assistant
- **MVP target date:** **15/09/26 EOD** (submission deadline, per the assignment brief)
- **Available window:** ~48 hours, solo, agent-assisted (Sun Sep 13 → Tue Sep 15 EOD)
- **Build philosophy:** documentation-first. `PRD.md` → `APP_FLOW.md` → `FRONTEND_GUIDELINES.md` (design.md) → `architecture.md` → `tech_stack.md` were reconciled and locked *before* any code, specifically so that mid-build decisions (schema, provider, agent framework) don't get re-litigated under time pressure. Every step below cites which doc it implements, so a fresh evaluator — or a future version of the builder — can trace any line of code back to a decision.
- **Tech stack:** per `tech_stack.md` — FastAPI/Python backend, React/Vite/TS frontend, Postgres+pgvector, Ollama (local) + Groq (cloud) behind a shared `ModelProvider` interface, Pi Coding Agent running as a Node sidecar, Docker Compose (5 services).

---

## PHASE 1: PROJECT SETUP & FOUNDATION
**Total estimate: ~4 hours — Day 1, morning**

### Step 1.1 — Initialize Project Structure
**Duration:** 45 min
**Goal:** A monorepo skeleton matching `architecture.md`'s deployment topology (5 services).

**Tasks:**
```bash
mkdir lenny-growth-assistant && cd lenny-growth-assistant
git init
mkdir -p backend/app/{api,rag,db,core,ingestion} \
         frontend/src/{components,pages,store} \
         agent-sidecar/src \
         docs data/transcripts scripts .github/workflows
touch README.md .env.example .gitignore docker-compose.yml
mv PRD.md APP_FLOW.md FRONTEND_GUIDELINES.md architecture.md tech_stack.md docs/
cat > .gitignore <<'EOF'
.env
__pycache__/
.venv/
node_modules/
*.pyc
dist/
.pytest_cache/
data/transcripts/*.txt
!data/transcripts/.gitkeep
EOF
git add . && git commit -m "chore: initial project scaffold"
```

**Success criteria:**
- [ ] `backend/`, `frontend/`, `agent-sidecar/`, `docs/` all exist with the subfolders above
- [ ] `docs/` contains all 5 reconciled documents
- [ ] `git log --oneline` shows the initial commit
- [ ] `.env` is git-ignored, `.env.example` is not

**Reference:** `architecture.md` → Deployment Topology

---

### Step 1.2 — Environment Setup
**Duration:** 1 hour
**Goal:** Reproducible Python + Node + Ollama environment.

**Tasks:**
```bash
# Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # exact pinned list from tech_stack.md §8

# Frontend
cd ../frontend
npm create vite@6.0.7 . -- --template react-ts
npm install react-router-dom@6.28.1 zustand@5.0.2 react-hook-form@7.54.2 \
  axios@1.7.9 react-markdown@9.0.1 dompurify@3.2.3 clsx@2.1.1 \
  tailwind-merge@2.5.5 lucide-react@0.468.0
npm install -D tailwindcss@3.4.17 postcss@8.4.49 autoprefixer@10.4.20

# Agent sidecar
cd ../agent-sidecar
npm init -y
npm install express@4.21.2 @mariozechner/pi-coding-agent
npm install -D typescript@5.6.3 @types/express@5.0.0 vitest@2.1.8
npx tsc --init

# Local models (mandatory demo path)
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Create `.env.example` with the **exact** contents from `tech_stack.md` §7 (Groq/Ollama toggle, `AGENT_SIDECAR_URL`, rate-limit var, feature flags). Then:
```bash
cp .env.example .env   # leave GROQ_API_KEY blank for the local-only demo path
```

**Success criteria:**
- [ ] `source backend/.venv/bin/activate && pip show fastapi` succeeds
- [ ] `cd frontend && npm run dev` serves on `:5173`
- [ ] `cd agent-sidecar && npx tsc --version` runs
- [ ] `ollama list` shows both `llama3.1:8b` and `nomic-embed-text`

**Reference:** `tech_stack.md` §7 (env vars), §8 (dependency lock)

---

### Step 1.3 — Database Setup
**Duration:** 1.5 hours
**Goal:** Postgres + pgvector running in Docker, schema migrated via Alembic.

**Tasks:**
1. Add to `docker-compose.yml`:
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: lenny
      POSTGRES_PASSWORD: lenny
      POSTGRES_DB: lenny_growth
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lenny"]
      interval: 5s
      retries: 5
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]
volumes:
  pgdata:
  ollama_data:
```
2. `docker compose up -d postgres ollama`
3. `cd backend && alembic init alembic`
4. Point `alembic/env.py` at `settings.ALEMBIC_DATABASE_URL` (sync driver) from `pydantic-settings`.
5. Write SQLAlchemy models for `sessions`, `messages`, `chunks`, `artifacts` exactly per `architecture.md` → Database Schema (types, constraints, FKs).
6. `alembic revision --autogenerate -m "initial schema"`
7. **Hand-review** the generated migration — per `tech_stack.md`'s migration strategy, autogenerate is a draft, not a final migration.
8. Add to the migration, before the table creates: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`
9. Add the HNSW index explicitly (autogenerate won't produce this correctly):
```python
op.execute("CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)")
```
10. `alembic upgrade head`

**Success criteria:**
- [ ] `docker compose ps` shows `postgres` healthy
- [ ] `psql $ALEMBIC_DATABASE_URL -c '\dt'` lists 4 tables
- [ ] `psql $ALEMBIC_DATABASE_URL -c '\d chunks'` shows the HNSW index and `VECTOR(768)` column
- [ ] `alembic current` shows exactly one clean revision at head

**Reference:** `architecture.md` → Database Schema; `tech_stack.md` §5

---

## PHASE 2: DESIGN SYSTEM IMPLEMENTATION
**Total estimate: ~3 hours — Day 1, early afternoon**

### Step 2.1 — Setup Design Tokens
**Duration:** 1 hour

`tailwind.config.js`, values pulled directly from `FRONTEND_GUIDELINES.md`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink:   { 50:"#EEF1F6",100:"#D7DEEA",200:"#B0BFD6",300:"#8AA0C1",400:"#5C7BA5",
                 500:"#34547E",600:"#263F60",700:"#1C2E48",800:"#141F32",900:"#0D141F" },
        signal:{ 50:"#EAF6F4",100:"#C9EAE4",500:"#1E7F73",700:"#114D46" },
        paper: { 50:"#FAF9F7",100:"#F2F0EC",200:"#E4E1DA",300:"#CFCBC1",400:"#A7A295",
                 500:"#7D786C",600:"#5C584E",700:"#423F38",800:"#2A2824",900:"#171614" },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        serif: ["Source Serif 4", "serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        none:"0", sm:"0.25rem", base:"0.375rem", md:"0.5rem", lg:"0.75rem", xl:"1rem",
      },
    },
  },
};
```
Import IBM Plex Sans / Source Serif 4 / IBM Plex Mono via a self-hosted `@font-face` (avoid a runtime Google Fonts dependency for the local-demo requirement).

**Success criteria:**
- [ ] `bg-ink-700`, `text-signal-500`, `font-serif` all render the correct values in a throwaway test div
- [ ] Fonts load with no network request when offline (self-hosted)

### Step 2.2 — Build Core Components
**Duration:** 2 hours

**Components (from `FRONTEND_GUIDELINES.md` → Component Library), build in this order (bottom-up: most reused first):**
1. `Button` (Primary/Secondary/Outline/Ghost/Danger × sm/md/lg)
2. `Textarea` (default/error/disabled states)
3. `Card` (session list item, default + active/selected)
4. `Alert` (error/info/success/warning)
5. `Modal` (focus trap, Escape/overlay/close-button dismiss)
6. `LoadingDots` (streaming indicator) + `Skeleton`
7. `EmptyState`

**Testing approach:** Vitest + React Testing Library per component — render each variant, assert correct class application and `role`/`aria-*` attributes; one `jest-axe` pass per component for the AA contrast/keyboard-nav requirements in `FRONTEND_GUIDELINES.md` → Accessibility Guidelines.

**Success criteria:**
- [ ] All 7 components render in an isolated test harness (Storybook optional — a `/dev/components` route is sufficient for a 48-hour build)
- [ ] `npm run test` passes for all component tests
- [ ] `jest-axe` reports zero violations on each

---

## PHASE 3: SESSION MANAGEMENT & LLM PROVIDER TOGGLE
*(Replaces the generic template's "Authentication" phase — see note at top of document.)*
**Total estimate: ~5 hours — Day 1, evening**

### Step 3.1 — Backend: Session & Config Endpoints
**Duration:** 2.5 hours

**Tasks:**
1. Implement `ModelProvider` interface (`app/core/providers.py`) with `GroqProvider` and `OllamaProvider` implementations, selected by `settings.LLM_PROVIDER` — per `architecture.md` → Agent Layer.
2. Implement endpoints exactly per `architecture.md` → API Endpoints:
   - `POST /api/v1/sessions`
   - `GET /api/v1/sessions`
   - `GET /api/v1/sessions/{id}/messages`
   - `GET /api/v1/config`
   - `GET /api/v1/health` (database + provider + Ollama + sidecar reachability)
3. Add `slowapi` rate limiter (20 req/min/session) on the messages route stub (full behavior lands in Phase 4).
4. Structured error envelope (`{success, error: {code, message}}`) per `architecture.md` → Error Handling.

**Test with an API client:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions
curl http://localhost:8000/api/v1/sessions
curl http://localhost:8000/api/v1/config
curl http://localhost:8000/api/v1/health
```

**Success criteria:**
- [ ] All 5 endpoints return the exact response shapes in `architecture.md`
- [ ] `GET /api/v1/health` returns `503` when Postgres is stopped (`docker compose stop postgres`), `200` otherwise
- [ ] Switching `LLM_PROVIDER=groq`↔`ollama` in `.env` and restarting changes `GET /api/v1/config`'s response with **no code change**

### Step 3.2 — Frontend: Session Sidebar & Provider Badge
**Duration:** 2.5 hours

Implement exactly `APP_FLOW.md` → §2.1 First-Load Experience:
- Sidebar with "New Chat" (Outline button) + session list (Card components)
- Provider badge in header, reading `GET /api/v1/config`
- Empty state on first load; error banner if backend unreachable, with retry
- Disabled chat input + "Provider unavailable" message if the configured provider can't be reached — **do not attempt a request that will fail**, per `APP_FLOW.md`'s decision table

**Success criteria:**
- [ ] Loading the app with no backend running shows the "Can't connect to the assistant backend" banner with a working retry button
- [ ] Stopping Ollama while `LLM_PROVIDER=ollama` disables the chat input with the specific unreachable message (not a generic error)
- [ ] "New Chat" creates a session and it appears in the sidebar immediately

---

## PHASE 4: CORE FEATURES
**Total estimate: ~14–16 hours — Day 2, full day**

### Step 4.1 — Grounded Conversational Q&A (RAG)
**Duration:** ~8 hours (largest single feature)

**Database work:** `chunks` table already exists (Phase 1.3) — no new tables.

**Ingestion (CLI-only, per `architecture.md`):**
```bash
python -m app.ingestion.ingest --dir data/transcripts --refresh
```
1. Clone/read the transcript repo into `data/transcripts/`.
2. Chunk each transcript (~500–800 tokens, ~15% overlap), tagging `source_file`, `episode_title`, `chunk_index`.
3. Compute `content_hash` (SHA-256); skip re-embedding unchanged chunks on refresh.
4. Embed via Ollama (`nomic-embed-text`), upsert on `(source_file, chunk_index)`.

**API/Agent integration:**
1. `POST /api/v1/sessions/{id}/messages`: validate → embed query → pgvector HNSW cosine search with a similarity threshold → if zero chunks pass threshold, return the explicit grounded-refusal response **without calling generation** (per `architecture.md`'s decision table — never generate from empty context).
2. Otherwise, call `agent-sidecar`'s `POST /run` with `{provider, context_chunks, conversation, request_type: "answer"}`; sidecar's `answer_from_context` tool generates the response and citations.
3. Persist user + assistant messages with citations JSON.

**Frontend:**
- Message list with streamed rendering, citation chips under assistant messages (Signal Teal, per design tokens)
- Follow-up handling: pass full session history to the sidecar each turn so pronoun resolution works

**Testing:**
- `pytest`: retrieval returns correct top-k for a known query; refusal path triggers when threshold isn't met; citation JSON shape is valid
- Manual: one known-topic question (should cite), one out-of-corpus question (should refuse explicitly, no fabricated citation)

**Success criteria:**
- [ ] A question with clear transcript support returns a cited answer (PRD Feature: Grounded Q&A, AC1)
- [ ] A question with no support returns the explicit refusal, never a fabricated answer (AC2)
- [ ] A follow-up using "it"/"that" resolves correctly (AC3)
- [ ] Response begins streaming within 5s under normal local conditions (PRD NFR: Performance)

---

### Step 4.2 — Ship 30/30 Essay Generation Skill
**Duration:** ~3 hours

1. Read the Ship 30/30 guide; encode its principles as a **structured** Pi tool (`generate_ship30_essay`) in `agent-sidecar/src/tools/` — not an unstructured one-off prompt, per the assignment's explicit requirement.
2. Structural validator (`validateEssay()`): word count within 1,250 ±15%, ≥2 subheadings, ≥1 bold-emphasis run, one identifiable takeaway sentence.
3. Retry-once-with-corrective-feedback loop on validation failure; if it fails twice, return the draft with an explicit disclaimer of which criteria weren't met — per `APP_FLOW.md` §2.3.
4. Frontend: "Generate Ship 30/30 Essay" affordance in the chat, opens the Artifact Viewer with the rendered Markdown essay.

**Testing:**
- Unit test `validateEssay()` against 3 fixtures: a valid essay, a too-short one, one missing subheadings.
- Manual: request an essay after a grounded discussion; confirm it renders correctly in the Artifact Viewer.

**Success criteria:**
- [ ] Essay word count falls within 1,250 ± 15% (PRD AC1)
- [ ] Output has a hook, ≥2 subheadings, bold emphasis, and a clear takeaway (AC2)
- [ ] Requesting a second essay on a different sub-topic creates a new artifact, not an overwrite (PRD Scenario 2 edge case)

---

### Step 4.3 — Artifact Generation & In-App Viewer
**Duration:** ~3–4 hours

**Backend:**
- `generate_artifact` tool (Markdown or HTML) in the sidecar
- Server-side `nh3` sanitization pass on any HTML before it's persisted/returned

**Frontend:**
- Artifact Viewer pane (side-by-side desktop, below-chat mobile, per `FRONTEND_GUIDELINES.md` layout patterns)
- HTML renders inside `<iframe sandbox="allow-scripts">` — **`allow-same-origin` deliberately omitted** (per `architecture.md`'s resolved security decision)
- Markdown renders via `react-markdown` with no raw-HTML passthrough
- Raw/rendered source toggle

**Testing — security test is mandatory, per the assignment's explicit security expectation:**
```
Manual test: request an HTML artifact containing:
  <script>fetch('/steal?c=' + document.cookie)</script>
Expected: script executes inside the iframe (visible in devtools if instrumented),
but cannot read the parent's document.cookie, localStorage, or navigate window.top.
```

**Success criteria:**
- [ ] A legitimate HTML artifact (e.g., a comparison table) renders correctly
- [ ] The malicious-script test above cannot exfiltrate cookies or navigate the parent page (PRD Scenario 3)
- [ ] Malformed generated HTML shows the "couldn't be rendered — view raw source" fallback, not a blank/broken pane

---

## PHASE 5: TESTING & REFINEMENT
**Total estimate: ~5–6 hours — Day 3, morning**

### Step 5.1 — Unit Tests
| Layer | Tool | What to test | Coverage target |
|---|---|---|---|
| Backend | Pytest + pytest-asyncio + httpx | Retrieval scoring/threshold, refusal logic, essay validator, endpoint contracts, error envelope shape | ≥70% on `app/rag`, `app/api` |
| Frontend | Vitest + React Testing Library | Core components (Button, Card, Modal, Alert), chat input validation, ArtifactViewer raw/rendered toggle | ≥60% on `src/components` |
| Agent sidecar | Vitest | Tool dispatch routing, provider selection logic, essay structural validator | ≥60% on `src/tools` |

```bash
cd backend && pytest --cov=app --cov-report=term-missing
cd frontend && npm run test -- --coverage
cd agent-sidecar && npx vitest run --coverage
```

### Step 5.2 — Integration / E2E Tests (Playwright)
1. New chat → grounded question → citation chip appears
2. Follow-up question resolves prior context correctly
3. Out-of-corpus question → explicit refusal, zero citations
4. Generate Ship 30/30 essay → structural checks pass, renders in Artifact Viewer
5. Generate HTML artifact → security test (script isolated, no cookie/parent access)
6. Stop the `ollama` container mid-session → UI shows the specific "Ollama unreachable" message, not a generic 500
7. Toggle `LLM_PROVIDER`, restart stack → provider badge updates with no code change

```bash
npx playwright test
```

**Manual test plan (UI, per assignment deliverable #7):** documented as a numbered checklist in `README.md`, covering the 7 flows above plus responsive breakpoints (mobile/tablet/desktop) and keyboard-only navigation of the full chat flow.

---

## PHASE 6: DEPLOYMENT
**Total estimate: ~4 hours — Day 3, afternoon**

### Step 6.1 — "Staging": Clean-Clone Smoke Test
Since this is a locally-run evaluation tool (no real staging tier), staging = proving a **fresh clone works from documented steps alone**:
```bash
cd /tmp && git clone <repo-url> fresh-eval && cd fresh-eval
cp .env.example .env
docker compose up -d
sleep 20
curl -f http://localhost:8000/api/v1/health
open http://localhost:5173
```
**Success criteria:**
- [ ] Fresh clone → working chat response in ≤15 minutes, following only `README.md` (PRD Success Metric 5)
- [ ] `docker compose up` brings up all 5 services with no manual intervention beyond `.env` copy

### Step 6.2 — Submission Packaging
1. Final `README.md` pass: architecture overview, prerequisites, install, env vars, local **and** cloud model setup, run commands, tests, troubleshooting.
2. Clean `agent-transcripts/` folder of any secrets/API keys before committing.
3. Record the 2–3 min demo video (camera on): problem framing → product walkthrough → local Ollama demo → one technical trade-off explained (e.g., the Node sidecar boundary, or HNSW vs. ivfflat). Upload to YouTube.
4. `git grep -i -E "api[_-]?key|secret|password" -- . ':!*.md'` — confirm no committed secrets.
5. Push to a **public** GitHub repo.
6. Submit via the form: https://forms.gle/LgotDHNVxW1mbzNE7

**Rollback plan:** if a last-hour change breaks the smoke test, `git revert` the offending commit rather than debugging under deadline pressure — the last known-good commit is always what gets submitted.

---

## MILESTONES & TIMELINE

### Milestone 1: Foundation Complete
**Target:** End of Day 1 (Sep 13, EOD)
- [ ] Phases 1–3 complete
- [ ] Docker Compose brings up all 5 services
- [ ] Sessions can be created/listed; provider badge reflects `.env`
- [ ] Design tokens + 7 core components implemented and tested

### Milestone 2: Core Features Complete
**Target:** End of Day 2 (Sep 14, EOD)
- [ ] Phase 4 complete — all 5 P0 features from `PRD.md` functional end-to-end
- [ ] Ingestion pipeline has run against the real transcript repo
- [ ] Artifact security test passes manually

### Milestone 3: MVP Submission-Ready
**Target:** Day 3 (Sep 15, before EOD)
- [ ] Phases 5–6 complete
- [ ] Clean-clone smoke test passes
- [ ] Demo video recorded and uploaded
- [ ] Repo pushed, secrets scrubbed, form submitted

---

## RISK MITIGATION

### Technical Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Schema changes mid-build (e.g., citation shape needs a field) | Medium — Alembic churn | Every schema change goes through a reviewed Alembic revision, never a hand edit; keep migrations small and single-purpose |
| Node↔Python sidecar boundary adds a new failure mode | Medium | Sidecar failures surface as the same `502 PROVIDER_ERROR` the frontend already handles for Groq/Ollama — no new UI state needed |
| Groq rate limits / cost during testing | Low–Medium | `slowapi` cap (20/min/session) + local Ollama as the default `.env` provider so iterative testing doesn't burn Groq quota |
| pgvector HNSW build time on ingestion | Low | Corpus is tens of episodes / thousands of chunks — HNSW build is seconds, not minutes, at this scale |
| Artifact XSS / sandbox escape | High if mishandled | Defense in depth: `nh3` server-side sanitization + `sandbox="allow-scripts"` with `allow-same-origin` withheld; explicit manual security test before submission (Phase 4.3) |
| Local model (Ollama) quality gap on tool-calling for RAG citations | Medium | Keep the `answer_from_context` tool's expected output schema simple (plain JSON citations list) so weaker local models can still comply reliably |

### Timeline Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Only ~48 hours available | High | Plan is hour-scoped, not week-scoped; Phase 4 (core features) gets the largest single block (Day 2) since it's graded most heavily |
| Scope creep (P1/P2 features) | High | P1/P2 features are explicitly out of this plan — see Post-MVP Roadmap; any P1 attempted before all P0s are done is a scheduling error |
| Dual-stack (Python + Node) setup friction eating Day 1 | Medium | Phase 1.2 pins exact versions from `tech_stack.md` to avoid dependency-resolution debugging mid-build |
| Video recording left to the last hour | Medium | Script the video's 4 beats (problem, product, local Ollama, trade-off) during Phase 6.1 while the smoke test runs, so recording itself is a 15-minute task, not an open-ended one |
| Ingestion against the real transcript repo takes longer than expected | Medium | Start ingestion (Step 4.1) early in Day 2, running in the background while building the API/UI around it |

---

## SUCCESS CRITERIA

MVP is successful when:
- [ ] All 5 P0 features from `PRD.md` are implemented and pass their acceptance criteria
- [ ] All flows in `APP_FLOW.md` (§2.1–2.6) work as specified, including error states
- [ ] UI matches `FRONTEND_GUIDELINES.md` design tokens and component patterns
- [ ] Backend test coverage ≥70% on `rag`/`api`; frontend/sidecar ≥60%
- [ ] Retrieval completes in <1s; first token appears within 5s locally (PRD NFR: Performance)
- [ ] WCAG 2.1 AA contrast + full keyboard navigation verified on the core chat flow
- [ ] A fresh evaluator reaches a working response in ≤15 minutes using only `README.md`
- [ ] The HTML artifact security test (PRD Scenario 3) passes
- [ ] All 8 required deliverables are present: repo, README, PRD, design.md, architecture.md, agent transcripts, tests, demo video

---

## POST-MVP ROADMAP

**P1 (from `PRD.md`):**
- Conversation search/browse across session titles and content
- Citation deep-link (click a citation → see the source excerpt inline)
- Artifact export/download (Markdown + HTML)

**Other post-MVP work:**
- User feedback loop: log "no grounding found" rate and citation-click-through as real usage signals once there's an actual user base
- Performance optimization: response caching evaluation (currently deliberately uncached — revisit only if real latency data justifies it)
- Analytics: per-episode citation frequency, essay-generation success rate
- Hardening pass on observability (e.g., request tracing across backend → sidecar → provider)

**P2 (from `PRD.md`, unscheduled):**
- Multi-user accounts and authentication
- Usage analytics dashboard
- Additional podcast/newsletter ingestion sources
- Voice input
- Collaborative multi-user artifact editing