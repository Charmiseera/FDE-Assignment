# Research: Pi Coding Agent Tool-Calling Integration

**Branch**: `001-pi-agent-tool-calling` | **Date**: 2026-09-13

---

## Research Tasks Resolved

All unknowns from Technical Context resolved from reading SDK type definitions and inspecting the installed package (`@mariozechner/pi-coding-agent@0.73.1` at `agent-sidecar/node_modules/`).

---

## Decision 1: Pi SDK entry point for programmatic use

**Question**: Which Pi SDK surface do we use for one-shot, per-request agent invocations inside Express?

**Decision**: Use `createAgentSession(options)` from `@mariozechner/pi-coding-agent` — the lowest-level SDK path that creates a fully managed `AgentSession` without filesystem side-effects.

**Rationale**:
- `createAgentSession` supports `customTools`, `noTools: "builtin"`, and an explicit `model` parameter — exactly what we need.
- `runPrintMode` (the higher-level helper) takes an `AgentSessionRuntime` (a heavier object that manages session switching/forking), which is overkill for stateless per-request use.
- `createAgentSession` returns `{ session }` directly; we subscribe via `session.subscribe(listener)` and call `session.prompt(text)` to fire a turn. We wait for the `turn_end` or `agent_end` event, extract the last assistant message text from `session.messages`, then `session.dispose()`.

**Alternatives considered**:
- `runPrintMode` — requires constructing `AgentSessionRuntime`; adds ~40 lines of boilerplate; designed for CLI output modes (stdout), not in-process result capture.
- `createAgentSessionRuntime` — needed for session switching/forking features (interactive TUI); not relevant here.

---

## Decision 2: Tool schema library (TypeBox)

**Question**: What schema library does `ToolDefinition.parameters` require?

**Decision**: TypeBox, importable from `typebox` (flat import, not `@sinclair/typebox`). Already present as a transitive dep in `agent-sidecar/node_modules/typebox/`.

**Rationale**: `ToolDefinition<TParams extends TSchema>` in the Pi SDK uses `@mariozechner/pi-agent-core` which re-exports TypeBox's `TSchema` and `Static`. The `types.d.ts` imports `type { Static, TSchema } from "typebox"`. Confirmed `typebox` exists at `node_modules/typebox`.

**Pattern**:
```typescript
import { Type } from "typebox";
const schema = Type.Object({ draft: Type.String() });
```

---

## Decision 3: Tool result format (how text is returned to the model)

**Question**: What does the `execute()` function return, and how does the agent see the result?

**Decision**: Return `{ content: [{ type: "text", text: JSON.stringify(result) }], details: result }`. The `content` array is what the LLM reads; `details` is for logging/rendering only.

**Rationale**: `AgentToolResult<T>` is `{ content: (TextContent | ImageContent)[], details: T, terminate?: boolean }`. `TextContent` is `{ type: "text", text: string }`. Returning the validation result as a JSON string in `text` is the standard pattern — the LLM reads it as text and decides whether to revise.

---

## Decision 4: Provider/API key injection into Pi sessions

**Question**: How do we pass the Groq API key to Pi without writing to `~/.pi/agent/auth.json`?

**Decision**: Use `AuthStorage.inMemory()` with `setRuntimeApiKey("groq", GROQ_API_KEY)`, then pass it to `createAgentSession({ authStorage })`. Pi's `getApiKey()` priority: runtime override → stored → env var. The runtime override path requires no disk writes and is per-request safe.

**Rationale**: `AuthStorage` has `static inMemory(data?: AuthStorageData): AuthStorage` and `setRuntimeApiKey(provider: string, apiKey: string): void` — confirmed from `auth-storage.d.ts`. This avoids file I/O and credential leakage between concurrent requests.

**Provider ID**: Pi uses `"groq"` as the Groq provider ID (based on built-in model registry — confirmed by `modelRegistry.find("groq", ...)` signature).

---

## Decision 5: How to find the right model for Pi sessions

**Question**: How do we tell Pi to use `llama-3.1-8b-instant` (or whatever the sidecar's configured model is)?

**Decision**: Use `ModelRegistry.inMemory(authStorage)` then `registry.find("groq", modelId)` to get a `Model` object, then pass `{ model }` to `createAgentSession`. If the model is not found in the built-in registry, fall back to passing no explicit model (Pi will pick the first available from the configured auth).

**Rationale**: `ModelRegistry.inMemory()` creates a registry with built-in models loaded but no file I/O. `find(provider, modelId)` returns `Model<Api> | undefined`. If undefined, omit the `model` option and let Pi auto-select from `getAvailable()`.

---

## Decision 6: Capturing the agent's final text response

**Question**: How do we get the final assistant text out of the Pi session after `session.prompt()` resolves?

**Decision**: Subscribe to agent session events before calling `prompt()`. Listen for `type === "agent_end"` (from `AgentEndEvent` in the extension types). After that event fires, read `session.messages` and find the last message with `role === "assistant"`, then extract its text content.

**Confirmed event types** (from `core/extensions/types.d.ts`):
- `AgentStartEvent` / `AgentEndEvent` — fired when agent loop starts/ends
- `TurnStartEvent` / `TurnEndEvent` — fired per LLM turn (including intermediate tool-calling turns)
- `CustomToolCallEvent` / `CustomToolResultEvent` — fired when a custom tool is invoked/returns

**Logging hook**: Subscribe to `CustomToolCallEvent` and `CustomToolResultEvent` to emit the `[Pi:tool_call]` and `[Pi:tool_result]` log lines required by SC-001/SC-002.

---

## Decision 7: Attempt harness placement

**Question**: Where does the 2-attempt cap live — inside the tool, inside the agent prompt, or in the outer Express handler?

**Decision**: The outer harness in `server.ts` passes a prompt with attempt-tracking context. The Pi agent session handles a single "task" per request (one `prompt()` call). The agent may call the tool 0, 1, or 2 times internally per turn sequence; the harness is a **timeout/abort safety net only**, not the primary retry driver.

**Rationale**: This is the cleanest split: the agent drives validation-and-revision via tool-calling (fulfilling the assignment requirement); the harness provides a hard upper-bound abort via `session.abort()` if the agent's turn count exceeds 2 and it's still streaming. This uses `session.isStreaming` and an attempt counter on the `TurnEndEvent` listener.

---

## Decision 8: `noTools: "builtin"` disables file system tools

**Question**: Will Pi's built-in bash/read/write/edit tools interfere with the sidecar (which has no DB access by design)?

**Decision**: Pass `noTools: "builtin"` to `createAgentSession`. This disables the default `read`, `bash`, `edit`, `write` tools, leaving only our `customTools`. Confirmed from SDK docs: `"builtin": disable the default built-in tools but keep extension/custom tools enabled`.

---

## No open NEEDS CLARIFICATION items.

All technical unknowns resolved from direct SDK inspection. No external research required.
