# Implementation Plan: Pi Coding Agent Tool-Calling Integration

**Branch**: `001-pi-agent-tool-calling` | **Date**: 2026-09-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-pi-agent-tool-calling/spec.md`

---

## Summary

Wire `@mariozechner/pi-coding-agent` tool-calling into the `agent-sidecar` for two specific request types: `ship30_essay` and `html_artifact`. Both flows will initialize a stateless Pi `AgentSession` per request, register a custom validation tool, send the generation prompt, allow the agent to self-correct via tool-calling, and return the result through the existing `/run` response contract (unchanged). The grounded Q&A path (`answer`) remains direct LLM calls with no Pi involvement, preserving ADR-004. Two new TypeScript tool files are created; `server.ts` gains new agent-dispatch branches; `generate_ship30_essay.ts` is refactored so its validation logic is reused inside the tool `execute()` function. `architecture.md` ADR-004 is updated to name the two tools.

---

## Technical Context

**Language/Version**: TypeScript 5.6 (ESM, `"type": "module"` in `package.json`)

**Primary Dependencies**:
- `@mariozechner/pi-coding-agent@^0.73.1` — already installed
- `typebox` — already installed as transitive dep (flat, not `@sinclair/typebox`)
- `express@4.21.2`, `groq-sdk@^0.9.1` — existing, unchanged

**Storage**: N/A — sidecar has zero DB access (ADR-004)

**Testing**: `vitest@2.1.8` (existing). New unit tests for tool `execute()` functions.

**Target Platform**: Node.js ESM process, internal Docker container

**Performance Goals**: No new latency target — the Pi agent session adds 1–2 extra network round-trips to Groq on top of the existing single LLM call. Acceptable for essay/artifact paths (user-initiated, not time-critical).

**Constraints**:
- Pi agent session MUST NOT reuse state across requests (stateless per invocation)
- `noTools: "builtin"` MUST be set to prevent Pi's filesystem tools from running
- External `/run` HTTP contract MUST remain identical (no FastAPI changes)
- Hard 2-attempt cap enforced by harness

**Scale/Scope**: 2 new source files, 1 refactored file, 1 modified file, 1 doc update.

---

## Constitution Check

*Constitution is unpopulated template — no project-specific gates defined. No violations to check.*

✅ Gate passed (trivially) — no constraints from constitution.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-pi-agent-tool-calling/
├── plan.md              ← this file
├── spec.md
├── research.md          ← Phase 0 (complete)
├── data-model.md        ← Phase 1 (complete)
├── quickstart.md        ← Phase 1 (complete)
├── contracts/
│   └── run-endpoint.md  ← Phase 1 (complete)
├── checklists/
│   └── requirements.md
└── tasks.md             ← Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (files changed by this feature)

```text
agent-sidecar/
├── src/
│   ├── server.ts                            [MODIFY] — add Pi agent branches
│   ├── tools/
│   │   ├── generate_ship30_essay.ts         [MODIFY] — extract validateEssay reuse; keep fn
│   │   ├── validate_essay_tool.ts           [NEW]    — Pi ToolDefinition for validate_essay
│   │   └── render_check_tool.ts             [NEW]    — Pi ToolDefinition for render_check
│   └── agent/
│       └── run_agent_session.ts             [NEW]    — shared Pi session runner helper
└── tests/
    └── tools/
        ├── validate_essay_tool.test.ts      [NEW]    — unit tests for tool execute()
        └── render_check_tool.test.ts        [NEW]    — unit tests for tool execute()

architecture.md                              [MODIFY] — update ADR-004 to name tools
```

**Structure Decision**: Single sidecar project; no new services, no new databases, no new packages. All Pi SDK usage is confined to `agent-sidecar/src/`. The new `agent/` subdirectory groups Pi-specific orchestration code away from route-level logic.

---

## Complexity Tracking

*No constitution violations — table not applicable.*

---

## Proposed Changes

### agent-sidecar/src/tools/

#### [NEW] `validate_essay_tool.ts`
- Imports `defineTool` from `@mariozechner/pi-coding-agent`
- Imports `Type` from `typebox` for schema definition
- Imports `validateEssay` from `./generate_ship30_essay.js` (reuses existing logic)
- Defines schema: `Type.Object({ draft: Type.String() })`
- `execute()`: calls `validateEssay(params.draft)`, maps result to `{ passed, word_count, issues }`, logs `[Pi:tool_call]` and `[Pi:tool_result]`, returns `{ content: [{ type: "text", text: JSON.stringify(result) }], details: result }`
- Exports `validateEssayTool: ToolDefinition`

#### [NEW] `render_check_tool.ts`
- Imports `defineTool` from `@mariozechner/pi-coding-agent`
- Imports `Type` from `typebox`
- Defines `checkHtmlStructure(html: string)`: validates `<!DOCTYPE html>`, `<body>`, `<title>`, balanced `<div>`/`</div>` counts
- Defines schema: `Type.Object({ html: Type.String() })`
- `execute()`: calls `checkHtmlStructure(params.html)`, logs `[Pi:tool_call]` and `[Pi:tool_result]`, returns `{ content: [{ type: "text", text: JSON.stringify(result) }], details: result }`
- Exports `renderCheckTool: ToolDefinition`

#### [MODIFY] `generate_ship30_essay.ts`
- `validateEssay()` function: **unchanged** (existing validation logic stays; tool just calls it)
- `generateShip30EssayWithRetry()`: **deleted** (this imperative retry wrapper is replaced by the Pi agent session in `server.ts`)
- `EssayGenerationOutput` interface: **kept** (still used in `/run` response construction)

---

### agent-sidecar/src/agent/

#### [NEW] `run_agent_session.ts`
- Imports `createAgentSession`, `AuthStorage`, `ModelRegistry`, `SessionManager` from `@mariozechner/pi-coding-agent`
- Exports `runAgentSession(options: AgentRunOptions): Promise<AgentRunResult>`:
  - Creates `AuthStorage.inMemory()` and calls `authStorage.setRuntimeApiKey("groq", GROQ_API_KEY)` if key is set
  - Creates `ModelRegistry.inMemory(authStorage)` and resolves `registry.find(provider, modelId)`
  - Calls `createAgentSession({ model, authStorage, customTools: options.tools, noTools: "builtin", sessionManager: SessionManager.inMemory() })`
  - Subscribes to events; emits `[Pi:session]`, `[Pi:tool_call]`, `[Pi:tool_result]` logs
  - Enforces 2-turn cap: listens for `TurnEndEvent`; if `turnCount >= 2 && session.isStreaming` → calls `session.abort()`
  - Calls `session.prompt(options.prompt)` and awaits `agent_end` event via Promise
  - Extracts final assistant text from `session.messages`
  - Calls `session.dispose()` in `finally` block
  - Returns `{ content: string, toolCalls: LoggedToolCall[], attemptCount: number }`

---

### agent-sidecar/src/server.ts

#### [MODIFY] `server.ts`
- Remove import of `generateShip30EssayWithRetry` (deleted from source)
- Add import of `runAgentSession` from `./agent/run_agent_session.js`
- Add import of `validateEssayTool` from `./tools/validate_essay_tool.js`
- Add import of `renderCheckTool` from `./tools/render_check_tool.js`
- **`html_artifact` branch**: replace `generateText(htmlPrompt, ...)` call with `runAgentSession({ tools: [renderCheckTool], prompt: htmlPrompt, provider, model })`; parse `result.content` for title as before; keep existing response shape.
- **`ship30_essay` branch**: replace `generateShip30EssayWithRetry(...)` with `runAgentSession({ tools: [validateEssayTool], prompt: basePrompt, provider, model })`; extract `title` from markdown as before; keep existing response shape including `metadata.validation_status`.
- **`answer` branch**: **no change** — still calls `generateText(buildAnswerPrompt(...), ...)` directly.
- Error handling: catch `SESSION_INIT_ERROR` from `runAgentSession` and return `502` instead of `500`.

---

### architecture.md

#### [MODIFY] ADR-004 section
- Update "Ship 30 for 30 Atomic Essays" bullet to add: "Uses Pi agent session with `validate_essay` tool (TypeBox schema: `{ draft: string }`). The agent drives validation and self-correction; the harness enforces a 2-attempt safety cap via `session.abort()`."
- Update "HTML/CSS Visual Artifacts" bullet to add: "Uses Pi agent session with `render_check` tool (TypeBox schema: `{ html: string }`). The agent self-corrects malformed HTML before returning."
- Add explicit statement: "Standard grounded Q&A (`request_type=answer`) bypasses the Pi agent session entirely and calls `generateText()` directly. This is an intentional, permanent design decision: retrieval/grounding must be deterministic and metric-critical."

---

## Verification Plan

### Automated Tests

```bash
# TypeScript compile — must exit 0
cd agent-sidecar && npm run build

# Unit tests (vitest)
npm test
# New test files:
# - tests/tools/validate_essay_tool.test.ts
# - tests/tools/render_check_tool.test.ts

# Backend tests (no sidecar changes affect FastAPI contracts)
cd ../backend && pytest tests/test_api.py -v
```

### Manual Verification

Follow [quickstart.md](quickstart.md):
1. Scenario 1 → check `[Pi:tool_call] validate_essay` in stdout
2. Scenario 2 → check `[Pi:tool_call] render_check` in stdout
3. Scenario 3 → confirm NO `[Pi:` lines for `answer` requests
4. Scenario 4 → `npm run build` exits 0
5. Scenario 5 → `pytest` all green

---

## Open Questions

None. All technical unknowns resolved in [research.md](research.md).
