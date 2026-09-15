# Data Model: Pi Coding Agent Tool-Calling Integration

**Branch**: `001-pi-agent-tool-calling` | **Date**: 2026-09-13

---

## Entities

This feature introduces no new database tables (the sidecar has zero DB access by ADR-004). All entities are **in-process, per-request runtime objects** with no persistence.

---

### 1. `PiAgentSession` (runtime)

A per-request Pi Coding Agent session created by `createAgentSession()`. Lives for the duration of one `/run` request and is disposed immediately after the final response is extracted.

| Field | Type | Description |
|---|---|---|
| `session` | `AgentSession` | The Pi SDK session handle. Exposes `.prompt()`, `.subscribe()`, `.messages`, `.isStreaming`, `.abort()`, `.dispose()` |
| `authStorage` | `AuthStorage` | In-memory auth storage seeded with Groq API key via `setRuntimeApiKey("groq", key)` |
| `modelRegistry` | `ModelRegistry` | In-memory model registry backed by the same `authStorage`. Used to resolve the named model. |
| `customTools` | `ToolDefinition[]` | The registered tools for this session (`validate_essay` for essays, `render_check` for HTML) |
| `noTools` | `"builtin"` | Disables Pi's default filesystem tools (read, bash, edit, write) |

**Lifecycle**: Created → `prompt()` called → events emitted → `dispose()` called. Not reused across requests.

---

### 2. `ValidateEssayInput` (tool parameter schema)

Input schema for the `validate_essay` tool. Defined with TypeBox.

| Field | Type | Constraints |
|---|---|---|
| `draft` | `string` | The full markdown content of the essay draft. Required. |

---

### 3. `ValidateEssayResult` (tool result)

Returned by the `validate_essay` tool to the Pi agent as a JSON string in `TextContent`.

| Field | Type | Description |
|---|---|---|
| `passed` | `boolean` | `true` if all 4 structural constraints are met |
| `word_count` | `number` | Actual word count of the draft |
| `issues` | `string[]` | Human-readable list of unmet constraints. Empty when `passed: true`. |

**Constraints evaluated** (reuses existing `validateEssay()` logic):
- Word count between 1,063 and 1,438 (1,250 ± 15%)
- At least 2 `##` or `###` subheadings
- At least one `**bold**` emphasis span
- Identifiable takeaway keyword (takeaway / the bottom line / key insight / core lesson)

---

### 4. `RenderCheckInput` (tool parameter schema)

Input schema for the `render_check` tool. Defined with TypeBox.

| Field | Type | Constraints |
|---|---|---|
| `html` | `string` | The full HTML string to validate. Required. |

---

### 5. `RenderCheckResult` (tool result)

Returned by the `render_check` tool to the Pi agent as a JSON string in `TextContent`.

| Field | Type | Description |
|---|---|---|
| `valid` | `boolean` | `true` if the HTML passes all structural checks |
| `issues` | `string[]` | Human-readable list of structural problems. Empty when `valid: true`. |

**Checks performed**:
- Starts with `<!DOCTYPE html>` (case-insensitive)
- Contains a `<body>` element
- Contains a `<title>` element
- No unclosed major tags (heuristic: `<div>` count matches `</div>` count; same for `<p>`, `<section>`, `<main>`)

---

### 6. `AgentRunResult` (internal response type)

Returned by the new `runEssayWithAgent()` / `runHtmlWithAgent()` helpers to the `/run` handler.

| Field | Type | Description |
|---|---|---|
| `content` | `string` | Final assistant text (last assistant message in session) |
| `toolCalls` | `{ name: string; input: object; output: object }[]` | Logged tool invocations for observability |
| `attemptCount` | `number` | Number of LLM turns completed (1 or 2) |

---

## State Transitions: Essay Agent Turn Sequence

```
[/run request arrives, request_type=ship30_essay]
        │
        ▼
createAgentSession({ customTools: [validate_essay], noTools: "builtin" })
        │
        ▼
session.prompt(buildEssayPrompt(...))   ← Turn 1
        │
        ├── Agent generates draft
        │
        ├── Agent calls validate_essay({ draft })
        │       └── Tool returns { passed, word_count, issues }
        │
        ├─ if passed=true → agent emits final answer → agent_end event
        │
        └─ if passed=false AND attemptCount < 2
                  └── Agent self-corrects, generates revised draft
                          └── agent_end event (harness enforces cap via abort if turn 3 starts)
        │
        ▼
Extract last assistant message → dispose session → return response
```

---

## Validation Rules (inherited from existing code, unchanged)

| Rule | Implementation |
|---|---|
| Word count 1,063–1,438 | `validateEssay()` in `generate_ship30_essay.ts` — **reused as-is** |
| ≥ 2 subheadings | Same |
| ≥ 1 bold span | Same |
| Takeaway keyword | Same |
| Valid HTML structure | New `checkHtmlStructure()` function in new `render_check_tool.ts` |
