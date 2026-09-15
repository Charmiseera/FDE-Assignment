# Quickstart Validation Guide: Pi Coding Agent Tool-Calling

**Branch**: `001-pi-agent-tool-calling` | **Date**: 2026-09-13

---

## Prerequisites

- `agent-sidecar` Node.js dependencies installed: `npm install` in `agent-sidecar/`
- `GROQ_API_KEY` set in `agent-sidecar/.env` or environment
- TypeScript compiles cleanly: `npm run build` exits 0

---

## Scenario 1: Essay agent invokes `validate_essay` tool (SC-001)

**What to verify**: Pi agent initializes, generates an essay draft, calls `validate_essay`, receives a structured result, and returns a markdown artifact. Log output must contain `[Pi:tool_call] validate_essay`.

```bash
# From agent-sidecar/ directory — start sidecar
npm start

# In a second terminal, send a ship30_essay request
curl -s -X POST http://localhost:4000/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "request_type": "ship30_essay",
    "context_chunks": [
      {
        "source_file": "episodes/elena-verna/transcript.md",
        "episode_title": "How to Build a PLG Motion",
        "chunk_text": "The key to product-led growth is making the product itself the primary driver of acquisition, retention, and expansion. Companies like Slack and Dropbox grew primarily through their product experience rather than traditional sales."
      }
    ],
    "conversation": [
      { "role": "user", "content": "Turn this into a Ship 30/30 essay" }
    ]
  }' | jq .
```

**Expected sidecar stdout** (order may vary):
```
[Pi:session] Creating Pi agent session for ship30_essay
[Pi:tool_call] validate_essay { draft: "<N chars>" }
[Pi:tool_result] validate_essay { passed: false|true, word_count: <N>, issues: [...] }
[Pi:session] Pi agent session complete, attempt_count=<1|2>
```

**Expected response shape**:
```json
{
  "content": "I've drafted a Ship 30/30 essay...",
  "citations": [{ "source_file": "...", "episode_title": "..." }],
  "artifact": {
    "type": "markdown",
    "title": "<essay title>",
    "content": "<full markdown>",
    "metadata": {
      "validation_status": { "passed": true|false, "word_count": <N>, "unmet_criteria": [] }
    }
  }
}
```

---

## Scenario 2: HTML agent invokes `render_check` tool (SC-002)

**What to verify**: Pi agent initializes with `render_check`, generates HTML, calls the tool, and returns a valid HTML artifact. Log output must contain `[Pi:tool_call] render_check`.

```bash
curl -s -X POST http://localhost:4000/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "request_type": "html_artifact",
    "context_chunks": [
      {
        "source_file": "episodes/brian-chesky/transcript.md",
        "episode_title": "How Airbnb Rebuilt",
        "chunk_text": "Airbnb completely rebuilt its product strategy during COVID by focusing on its core hosts and reinventing the host experience before worrying about guests."
      }
    ],
    "conversation": [
      { "role": "user", "content": "Create an HTML dashboard of this" }
    ]
  }' | jq .
```

**Expected sidecar stdout**:
```
[Pi:session] Creating Pi agent session for html_artifact
[Pi:tool_call] render_check { html: "<N chars>" }
[Pi:tool_result] render_check { valid: true|false, issues: [...] }
[Pi:session] Pi agent session complete, attempt_count=<1|2>
```

**Expected response**: `artifact.type === "html"` and `artifact.content` starts with `<!DOCTYPE html`.

---

## Scenario 3: Grounded Q&A bypasses Pi entirely (SC-003)

**What to verify**: No `[Pi:tool_call]` log lines appear for a standard Q&A request.

```bash
curl -s -X POST http://localhost:4000/run \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "request_type": "answer",
    "context_chunks": [
      {
        "source_file": "episodes/elena-verna/transcript.md",
        "episode_title": "How to Build a PLG Motion",
        "chunk_text": "Product-led growth means the product drives acquisition."
      }
    ],
    "conversation": [
      { "role": "user", "content": "What is PLG?" }
    ]
  }' | jq .
```

**Expected**: No `[Pi:` lines in sidecar stdout. Response has `artifact: null`.

---

## Scenario 4: Build verification (no regressions)

```bash
# In agent-sidecar/
npm run build
# Expected: exit 0, no TypeScript errors

# Run existing unit tests
npm test
# Expected: all pass
```

---

## Scenario 5: Existing test suite (FastAPI)

```bash
# In backend/
pytest tests/test_api.py -v
# Expected: all existing tests pass — no changes to sessions.py or schemas
```

---

## Failure Modes to Verify

| Failure | Expected behavior |
|---|---|
| `GROQ_API_KEY` not set | Pi session init fails → `502 PROVIDER_ERROR` response |
| Agent tool throws exception | Tool returns `{ valid: false, issues: ["Tool error: ..."] }` — no 500 |
| Agent uses >2 LLM turns | Harness calls `session.abort()` → returns last draft with disclaimer |
| `answer` request hits Pi code path | Should never happen — verify no `createAgentSession` call in answer branch |
