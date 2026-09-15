# Contract: Sidecar /run Endpoint (Unchanged External Contract)

**Branch**: `001-pi-agent-tool-calling` | **Date**: 2026-09-13

This feature does **not change the external HTTP contract** of the `/run` endpoint. FastAPI calls it with the same payload; the response shape is identical. The only change is the internal implementation path for `ship30_essay` and `html_artifact` request types.

---

## POST /run (Internal — FastAPI → agent-sidecar:4000)

### Request

```json
{
  "provider": "groq" | "ollama",
  "model": "string",
  "context_chunks": [
    {
      "source_file": "string",
      "episode_title": "string",
      "chunk_text": "string"
    }
  ],
  "conversation": [
    { "role": "user" | "assistant", "content": "string" }
  ],
  "request_type": "answer" | "ship30_essay" | "html_artifact" | "artifact"
}
```

### Response (success — unchanged shape)

```json
{
  "content": "string",
  "citations": [
    { "source_file": "string", "episode_title": "string" }
  ],
  "artifact": {
    "type": "markdown" | "html",
    "title": "string",
    "content": "string",
    "metadata": {
      "validation_status": {
        "passed": true | false,
        "word_count": 1234,
        "unmet_criteria": []
      }
    }
  } | null
}
```

### Response (error — unchanged shape)

```json
{
  "error": {
    "code": "INTERNAL_ERROR" | "PROVIDER_ERROR" | "SESSION_INIT_ERROR",
    "message": "string"
  }
}
```

> [!IMPORTANT]
> **The JSON contract above is frozen.** No field may be added, renamed, or removed without a corresponding FastAPI change. `sessions.py` on the FastAPI side parses `artifact`, `content`, and `citations` by key; shape changes would cause silent data loss.

---

## Tool Contract: `validate_essay`

Internal to the Pi agent session. The LLM sees this as a callable tool.

```typescript
// Tool name (as seen by LLM)
name: "validate_essay"

// Input (TypeBox schema)
{ draft: string }

// Output (as JSON string in TextContent returned to model)
{
  passed: boolean,
  word_count: number,
  issues: string[]   // empty when passed: true
}
```

---

## Tool Contract: `render_check`

Internal to the Pi agent session. The LLM sees this as a callable tool.

```typescript
// Tool name (as seen by LLM)
name: "render_check"

// Input (TypeBox schema)
{ html: string }

// Output (as JSON string in TextContent returned to model)
{
  valid: boolean,
  issues: string[]   // empty when valid: true
}
```

---

## Log Contract (Observability)

The following log lines MUST appear in sidecar stdout for SC-001 and SC-002 compliance:

```
[Pi:tool_call] validate_essay { draft: "<N chars>" }
[Pi:tool_result] validate_essay { passed: false, word_count: 1021, issues: ["..."] }
[Pi:tool_call] render_check { html: "<N chars>" }
[Pi:tool_result] render_check { valid: true, issues: [] }
```

These are emitted by subscribing to the `AgentSessionEvent` stream and filtering for `CustomToolCallEvent` and `CustomToolResultEvent` event types.
