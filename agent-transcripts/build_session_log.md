# Agent Build Transcript & Trajectory Log

## Overview
This document logs the agent trajectory, technical decisions, and validation steps executed during the implementation of the **Lenny Growth Assistant**.

---

## 1. Foundation & Infrastructure (Phases 1–3)
- **Containerization**: Configured 5-service `docker-compose.yml`:
  - `postgres` (pgvector 16 with HNSW cosine similarity index)
  - `ollama` (local generation + nomic-embed-text)
  - `agent-sidecar` (Express + Pi Coding Agent harness on internal network port 4000)
  - `backend` (FastAPI with async SQLAlchemy, Pydantic v2, and Alembic migrations)
  - `frontend` (React + Vite + Tailwind CSS + Lucide icons)
- **Database Migrations**: Authored clean sync Alembic migration creating the 4 core tables:
  - `sessions`, `messages`, `chunks`, `artifacts`
  - Explicit vector extension and HNSW index: `CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);`
- **Data Ingestion**: Implemented `app/ingestion/ingest.py` (chunk size: 500 words, 50-word overlap, SHA-256 content deduplication).

---

## 2. Core Features (Phase 4)
- **Grounded Conversational Q&A**:
  - Embedding queries with `nomic-embed-text` (768-dim).
  - Cosine distance query in pgvector with tuned threshold (`0.50`).
  - Strict grounded refusal: queries outside the transcript corpus (e.g. recipe questions) return zero citations and an explicit refusal message without calling the LLM or sidecar.
- **Ship 30/30 Atomic Essay Skill (Step 4.2)**:
  - Structured tool in `agent-sidecar/src/tools/generate_ship30_essay.ts`.
  - Structural validation enforcing hook, $\ge 2$ subheadings, bold phrases, and a closing key takeaway.
  - Automatic retry loop with corrective feedback.
  - Metadata isolation: validation status recorded cleanly in `metadata.validation_status`.
- **In-App Artifact Viewer & Security Sandbox (Step 4.3)**:
  - Desktop split pane (`45%` screen width) and responsive mobile stack.
  - Raw vs. Rendered toggle with clipboard copying.
  - Sandboxed iframe `<iframe sandbox="allow-scripts">` where `allow-same-origin` is omitted to isolate parent origin and cookies.

---

## 3. Automated Verification & Test Results (Phase 5)
- **Backend Unit Tests**: 18 passed (92% coverage on `sessions.py`, 98% on `retriever.py`, 100% on `config.py`).
- **Frontend Unit Tests**: 8 passed (Core components + ArtifactViewer).
- **Sidecar Tests**: 3 passed (`validateEssay()` test fixtures).
- **Automated E2E Suite (`scripts/run_e2e_tests.ps1`)**: 10 passed, 0 failed across all 7 PRD scenarios.

---

## 4. Security Verification
- Scrubbed all code and configuration files. No hardcoded secrets or API keys committed.
