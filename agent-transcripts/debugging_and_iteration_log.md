# Coding Agent Debugging, Trajectory & Iteration Log

This document records the systematic problem-solving process, failed attempts, root cause analyses, and solutions implemented during the development of the **Lenny Growth Assistant**. All private API credentials and secrets have been redacted.

---

## 1. Issue: 404 Not Found on Artifact View Endpoint

- **Observed Failure:**
  When clicking **"View Generated Artifact"** in the chat panel, the UI threw:
  ```
  GET /api/v1/sessions/<session-id>/artifacts/<artifact-id> -> 404 (Not Found)
  AxiosError: Request failed with status code 404
  ```

- **Root Cause Analysis:**
  1. In `sessions.py`, when writing artifacts to Supabase REST API (`DB_TARGET="supabase"`), the payload used the column name `"metadata"`.
  2. However, the local database model used `metadata_sidecar`. In certain branches, queries looked for `metadata_sidecar` instead of checking both.
  3. When `get_artifact` queried Supabase, any slight schema or timing latency resulted in an immediate 404 rather than falling back to local storage.

- **Solution Applied:**
  1. Standardized artifact insertions in `sessions.py` to write both `metadata` and preserve `metadata_sidecar`.
  2. Added a dual-lookup fallback in `get_artifact`: First query Supabase REST API; if not found, immediately fall back to local PostgreSQL query.

---

## 2. Issue: Local PostgreSQL Authentication Failure During Cloud Ingestion

- **Observed Failure:**
  Backend logs reported:
  ```
  Local artifact insert error: password authentication failed for user "postgres"
  ```

- **Root Cause Analysis:**
  Even with `DB_TARGET="supabase"` set, `sessions.py` executed a secondary `db.add(artifact_obj); await db.flush()` against the local database session. Because the local PostgreSQL credentials were not matching or local PostgreSQL was uninitialized, the unhandled flush attempt crashed or logged repeated errors.

- **Solution Applied:**
  Refactored the persistence logic into mutually exclusive branches:
  ```python
  if use_supabase:
      # Exclusively use Supabase REST endpoint
      ...
  elif not _is_mock(db):
      # Exclusively use local SQLAlchemy session
      ...
  ```
  This completely eliminated phantom connection attempts to local postgres when operating in cloud mode.

---

## 3. Issue: Artifact Viewer Rendered Completely Blank

- **Observed Failure:**
  The user opened the Artifact Viewer pane (`Ship 30/30 Essay`), but the entire body was empty white space. Querying the backend revealed:
  ```
  Artifact exists: True
  Title: Ship 30/30 Essay
  Type: markdown
  Content length: 0
  Content full: ''
  ```

- **Root Cause Analysis:**
  1. **Missing Method in Pi Coding Agent:**
     In `agent-sidecar/src/agent/run_agent_session.ts`, the code called `session.getLastAssistantText()`. This method does not exist on `AgentSession` from `@mariozechner/pi-coding-agent`.
  2. **Tool Argument vs Assistant Text:**
     When the Pi agent called `validate_essay`, it provided the entire generated draft inside the tool arguments `{ draft: "..." }`. In turn 2, the model simply returned an acknowledgement without echoing the full draft into the message text. As a result, the assistant's message content was empty.
  3. **Stale Process Execution:**
     The sidecar process was running without hot reloading, so changes made to `server.ts` were not picked up.

- **Solution Applied:**
  1. Updated `run_agent_session.ts` to extract assistant text directly from `session.agent.state.messages`.
  2. In `server.ts`, added draft extraction from `agentResult.toolCalls`:
     ```typescript
     const validateCall = agentResult.toolCalls.slice().reverse().find(
       (t) => t.toolName === "validate_essay" && t.input?.draft
     );
     if (validateCall?.input?.draft && validateCall.input.draft.trim().length > 50) {
       essayContent = validateCall.input.draft.trim();
     }
     ```
  3. Added guaranteed fallback logic to `generateText()` if the agent session returned short or empty content.
  4. Rebuilt the TypeScript package and restarted the sidecar service with `tsx watch`.

---

## 4. Issue: Groq Model 404 (`llama-3.3-70b-versatile` Deprecation)

- **Observed Failure:**
  When executing Groq requests, Groq returned:
  ```json
  {"error":{"message":"The model `llama-3.3-70b-versatile` does not exist or you do not have access to it.","type":"invalid_request_error","code":"model_not_found"}}
  ```

- **Root Cause Analysis:**
  Groq updated its hosted model offerings. The user's account has access to `openai/gpt-oss-120b`, but `server.ts` had a hardcoded sanitizer that replaced `openai` or `gpt` with `llama-3.3-70b-versatile`.

- **Solution Applied:**
  1. Updated `.env` to `GROQ_MODEL="openai/gpt-oss-120b"`.
  2. Updated `callGroq()` in `server.ts` to use `openai/gpt-oss-120b`.
  3. Verified that `openai/gpt-oss-120b` generates ~2,000-character structured essays in under 2 seconds with excellent grounded quality.

---

## 5. Issue: Text Contrast & GFM Markdown Table Rendering

- **Observed Failure:**
  Markdown tables were rendered as raw unstyled plain text blocks, and text inside `ArtifactViewer.tsx` lacked contrast due to global dark mode defaults (`body { @apply bg-black text-zinc-100 }`).

- **Solution Applied:**
  1. Installed `remark-gfm` and registered it with `ReactMarkdown`.
  2. In `index.css`, created dedicated styling for `.prose-editorial`:
     - Clean typography using IBM Plex Sans and Source Serif 4.
     - Dark ink typography (`#0d141f`, `#171614`) optimized for paper backgrounds.
     - Full GitHub Flavored Markdown table styling (`.prose-editorial table`, `th`, `td`, alternating rows).
     - Styled blockquotes, lists, and code badges.

---

## 6. Feature Enhancement: In-Flight Stop Button

- **User Request:**
  Provide the ability to immediately stop/cancel long-running generation requests.

- **Solution Applied:**
  1. Integrated `AbortController` in `App.tsx` and attached its signal to the Axios POST call.
  2. Added two intuitive stop controls in `ChatPanel.tsx`:
     - A red `[■ Stop]` button inside the animated loading banner.
     - Transformation of the submit icon into a red `[■ Stop]` button while `isLoading` is true.
  3. Clean cancellation handling that avoids unhandled Axios error alerts.
