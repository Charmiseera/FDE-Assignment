# Feature Specification: Pi Coding Agent Tool-Calling Integration

**Feature Branch**: `001-pi-agent-tool-calling`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "Wire real Pi Coding Agent tool-calling into the agent-sidecar for the Ship 30/30 essay and HTML artifact flows. The grounded Q&A path stays as deterministic direct LLM calls — no agent framework involvement. Replace imperative retry/validation logic with Pi agent sessions that have validate_essay and render_check tools registered; the agent decides when to call them and whether to revise output."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ship 30/30 Essay Validated by Agent Tool (Priority: P1)

A user asks the system to generate a Ship 30/30 essay. The system invokes a Pi agent session with a `validate_essay` tool registered. The agent drafts the essay, calls the tool to check structural requirements (word count, subheadings, bold, takeaway), reads the result, and decides whether to revise. The final validated essay is returned as an artifact.

**Why this priority**: This is the primary compliance requirement — the assignment mandates using Pi Coding Agent tool-calling, and the essay path is the most clearly rule-bound output that benefits from it.

**Independent Test**: Can be tested by sending a ship-30-essay request to `POST /sessions/{id}/messages` and observing that (a) sidecar logs show Pi agent invoking the `validate_essay` tool and receiving a structured result, and (b) the response contains a markdown artifact.

**Acceptance Scenarios**:

1. **Given** a valid session and grounded context chunks, **When** `request_type === "ship30_essay"` is sent to the sidecar `/run` endpoint, **Then** the Pi agent is initialized with `validate_essay` as a registered custom tool, a prompt is sent, and the agent's tool call to `validate_essay` is logged before the final artifact is returned.

2. **Given** the agent's first draft fails validation (word count outside 1,063–1,438, fewer than 2 subheadings, no bold, or no takeaway), **When** the tool returns `{ passed: false, issues: [...] }`, **Then** the agent receives the tool result and decides to revise the draft (up to the harness-enforced cap of 2 attempts total), not Python/TypeScript code making that decision.

3. **Given** the agent has exhausted 2 LLM attempts and the draft still fails, **When** the harness detects the attempt cap, **Then** the artifact is returned with `validation_status.passed = false` and the unmet criteria listed — the user sees a warning banner in the Artifact Viewer.

---

### User Story 2 — HTML Artifact Validated by Agent Tool (Priority: P2)

A user requests an HTML dashboard or visual artifact. The system invokes a Pi agent session with a `render_check` tool registered. The agent generates HTML, calls the tool to verify the output is well-formed HTML with a proper document structure, reads the result, and self-corrects if the check fails before returning the artifact.

**Why this priority**: Ensures the HTML artifact path also uses real tool-calling, and prevents malformed HTML from reaching the frontend iframe.

**Independent Test**: Can be tested by sending an `html_artifact` request and observing that the sidecar logs show the `render_check` tool being called by the Pi agent with the generated HTML as input, and a structured `{ valid: bool, issues: string[] }` result returned to the agent.

**Acceptance Scenarios**:

1. **Given** an `html_artifact` request with grounded context, **When** the Pi agent generates HTML, **Then** it calls `render_check` before finalizing output, and the tool result is logged with `{ valid, issues }`.

2. **Given** the generated HTML is malformed (missing `<!DOCTYPE html>`, no `<body>`, or tag mismatch), **When** `render_check` returns `{ valid: false, issues: [...] }`, **Then** the agent attempts to correct the HTML before returning (up to 2 attempts total enforced by the harness).

3. **Given** the final HTML passes `render_check`, **When** the artifact is persisted, **Then** `artifact.type === "html"` and the content is a valid `<!DOCTYPE html>` document renderable in the sandboxed iframe.

---

### User Story 3 — Grounded Q&A Remains Unaffected (Priority: P1)

Grounded Q&A requests continue to use direct deterministic LLM calls with no Pi agent involvement. This is an explicit ADR-004 design constraint: retrieval/grounding must be deterministic and metric-critical, not subject to agent tool-calling indeterminism.

**Why this priority**: Regression risk — breaking the Q&A path would break the primary use case of the application.

**Independent Test**: Send a normal question (no essay/artifact keywords) and verify no Pi agent session is created, no tool calls are logged, and the response path is the existing `buildAnswerPrompt → generateText` flow.

**Acceptance Scenarios**:

1. **Given** a question routed as `request_type === "answer"`, **When** the sidecar `/run` handler processes it, **Then** no `createAgentSession` call is made, and the response comes directly from `generateText(buildAnswerPrompt(...))`.

2. **Given** the grounded refusal path (no chunks above similarity threshold), **When** FastAPI returns a canned refusal before calling the sidecar, **Then** the sidecar `/run` endpoint is never invoked at all.

---

### Edge Cases

- What happens when the Pi agent session fails to initialize (bad API key, model unavailable)? → The harness must catch this, log the error, and fall back to returning a `502 PROVIDER_ERROR` — never a silent partial response.
- What happens if the agent enters an unexpected tool-calling loop (calls `validate_essay` more than twice)? → The harness enforces a hard cap of 2 total LLM attempts; if exceeded, the last draft is returned with a disclaimer.
- What if `validate_essay` or `render_check` throws an exception during execution? → The tool must catch internally and return `{ passed: false, issues: ["Tool execution error: <message>"] }` so the agent can handle it gracefully without crashing the session.
- What if the Groq API key is not set and Ollama is configured instead? → Pi agent must be initialized with the same provider resolution logic used by the existing `generateText()` function.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The sidecar MUST initialize a Pi Coding Agent session with `validate_essay` as a registered custom tool when `request_type === "ship30_essay"`.
- **FR-002**: The sidecar MUST initialize a Pi Coding Agent session with `render_check` as a registered custom tool when `request_type === "html_artifact"`.
- **FR-003**: The `validate_essay` tool MUST accept a `draft` string and return `{ passed: boolean, word_count: number, issues: string[] }` to the agent as a structured tool result.
- **FR-004**: The `render_check` tool MUST accept an `html` string and return `{ valid: boolean, issues: string[] }` to the agent as a structured tool result.
- **FR-005**: The harness MUST enforce a maximum of 2 total LLM attempts as a safety backstop, regardless of what the agent decides — the agent's tool-calling drives the retry, but the harness prevents runaway loops.
- **FR-006**: Tool invocations (name, input, output) MUST be logged at `[Sidecar]` level so the tool-calling event is observable in server logs without any frontend changes.
- **FR-007**: The `request_type === "answer"` path MUST NOT use Pi agent sessions — it remains direct LLM calls with no agent framework involvement.
- **FR-008**: The `/run` endpoint response contract (content, citations, artifact shape) MUST remain unchanged — no FastAPI or frontend changes are required.
- **FR-009**: `architecture.md` ADR-004 MUST be updated to name the two registered tools and explicitly restate the Q&A bypass decision.
- **FR-010**: The `@mariozechner/pi-coding-agent` package (already present in `package.json` at `^0.73.1`) MUST be the tool-calling framework — no other agent SDK may be introduced.

### Key Entities

- **Pi Agent Session**: A stateless, per-request Pi `AgentSession` created via `createAgentSession({ customTools: [...], noTools: "builtin" })`. Created fresh per sidecar `/run` invocation; not shared across requests.
- **`validate_essay` tool**: Custom Pi `ToolDefinition` with TypeBox schema `{ draft: Type.String() }`. Returns `{ passed, word_count, issues }` as text content to the model.
- **`render_check` tool**: Custom Pi `ToolDefinition` with TypeBox schema `{ html: Type.String() }`. Returns `{ valid, issues }` as text content to the model.
- **Attempt Harness**: The wrapping TypeScript logic around the agent session that counts LLM turns and enforces the 2-attempt cap as a safety backstop only.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `ship30_essay` request produces sidecar logs containing `[Pi:tool_call] validate_essay` and `[Pi:tool_result] validate_essay` entries, proving the agent called the tool (not TypeScript code).
- **SC-002**: An `html_artifact` request produces sidecar logs containing `[Pi:tool_call] render_check` and `[Pi:tool_result] render_check` entries.
- **SC-003**: An `answer` request produces no `[Pi:tool_call]` log entries — confirming Q&A bypasses the agent framework entirely.
- **SC-004**: The existing test suite (`backend/tests/test_api.py`, `agent-sidecar/tests/`) continues to pass after the change — no regressions in grounded-refusal, citation, or session management behavior.
- **SC-005**: `architecture.md` ADR-004 names both registered tools (`validate_essay`, `render_check`) and explicitly states that Q&A bypasses the agent framework by design.

---

## Assumptions

- `@mariozechner/pi-coding-agent` `^0.73.1` is already installed in `agent-sidecar/node_modules/` — no fresh `npm install` is needed.
- Pi agent sessions can be driven programmatically using `createAgentSession({ customTools, noTools: "builtin" })` and `session.prompt(text)` with an event listener for `message_end` to capture the final assistant text — confirmed from reading the SDK type definitions.
- The `noTools: "builtin"` option disables Pi's built-in file system tools (read, bash, edit, write), leaving only the two registered custom tools visible to the model — this prevents the agent from accidentally calling unintended filesystem operations.
- Provider resolution (Groq vs Ollama) is passed into the Pi agent session via the same environment variables and settings already used by `generateText()`.
- The essay `validateEssay()` and HTML structure validation logic (existing TypeScript functions) are reused as the implementation inside the tool `execute()` functions — they are not deleted, just promoted to be called through the Pi tool interface.
- Mobile/streaming UI changes are out of scope for this feature.
