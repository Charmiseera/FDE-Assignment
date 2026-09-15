# Tasks: Pi Coding Agent Tool-Calling Integration

**Input**: Design documents from `specs/001-pi-agent-tool-calling/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [contracts/run-endpoint.md](contracts/run-endpoint.md), [quickstart.md](quickstart.md)

---

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no shared state)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`) - required for User Story phases
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify dependencies and prepare agent-sidecar environment

- [x] T001 Verify `@mariozechner/pi-coding-agent` dependency in `agent-sidecar/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Pi agent session execution runner that MUST be complete before user story routes can be wired

**⚠️ CRITICAL**: User story route wiring in `server.ts` depends on this foundational helper

- [x] T002 Implement shared Pi agent session runner helper in `agent-sidecar/src/agent/run_agent_session.ts`

**Checkpoint**: Foundation ready - Pi agent session runner available for user story tool integration

---

## Phase 3: User Story 1 — Ship 30/30 Essay Validated by Agent Tool (Priority: P1) 🎯 MVP

**Goal**: Wire Pi Coding Agent session with `validate_essay` tool for `ship30_essay` requests, enabling agent-driven validation and self-correction.

**Independent Test**: Send `ship30_essay` request to `POST /run`, verify sidecar logs contain `[Pi:tool_call] validate_essay` and `[Pi:tool_result] validate_essay`, and response contains a markdown essay artifact.

### Tests for User Story 1

- [x] T003 [P] [US1] Create unit test suite for `validate_essay` tool in `agent-sidecar/tests/tools/validate_essay_tool.test.ts`

### Implementation for User Story 1

- [x] T004 [P] [US1] Refactor `agent-sidecar/src/tools/generate_ship30_essay.ts` to export `validateEssay()` for tool reuse and remove `generateShip30EssayWithRetry()`
- [x] T005 [P] [US1] Implement `validate_essay` Pi ToolDefinition in `agent-sidecar/src/tools/validate_essay_tool.ts`
- [x] T006 [US1] Wire `ship30_essay` route branch in `agent-sidecar/src/server.ts` to use `runAgentSession` with `validateEssayTool`
- [x] T007 [US1] Execute unit tests for `validate_essay_tool` and verify Scenario 1 quickstart flow for `ship30_essay`

**Checkpoint**: User Story 1 fully functional and testable independently (MVP ready!)

---

## Phase 4: User Story 2 — HTML Artifact Validated by Agent Tool (Priority: P2)

**Goal**: Wire Pi Coding Agent session with `render_check` tool for `html_artifact` requests, enabling agent-driven structural validation of generated HTML.

**Independent Test**: Send `html_artifact` request to `POST /run`, verify sidecar logs contain `[Pi:tool_call] render_check` and `[Pi:tool_result] render_check`, and response contains a valid HTML artifact.

### Tests for User Story 2

- [x] T008 [P] [US2] Create unit test suite for `render_check` tool in `agent-sidecar/tests/tools/render_check_tool.test.ts`

### Implementation for User Story 2

- [x] T009 [P] [US2] Implement `render_check` Pi ToolDefinition in `agent-sidecar/src/tools/render_check_tool.ts` with HTML structural validator
- [x] T010 [US2] Wire `html_artifact` route branch in `agent-sidecar/src/server.ts` to use `runAgentSession` with `renderCheckTool`
- [x] T011 [US2] Execute unit tests for `render_check_tool` and verify Scenario 2 quickstart flow for `html_artifact`

**Checkpoint**: User Stories 1 and 2 both work independently with real Pi agent tool-calling

---

## Phase 5: User Story 3 — Grounded Q&A Remains Unaffected (Priority: P1)

**Goal**: Ensure grounded Q&A requests (`request_type === "answer"`) bypass the Pi agent framework entirely, retaining direct LLM calls per ADR-004.

**Independent Test**: Send `answer` request to `POST /run`, verify zero `[Pi:tool_call]` log entries and direct LLM response returned.

### Implementation for User Story 3

- [x] T012 [US3] Verify `answer` route branch in `agent-sidecar/src/server.ts` retains direct `generateText` pipeline with zero Pi session overhead
- [x] T013 [US3] Execute Scenario 3 quickstart verification confirming Q&A bypasses agent framework completely

**Checkpoint**: All three user stories functional and verified without regressions

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates, TypeScript compilation, and comprehensive test suite execution across backend and sidecar

- [x] T014 [P] Update `architecture.md` ADR-004 section to document `validate_essay` and `render_check` tools and restate Q&A bypass decision
- [x] T015 [P] Run TypeScript build `npm run build` and sidecar test suite `npm test` in `agent-sidecar/`
- [x] T016 Run full backend pytest test suite in `backend/tests/test_api.py` to confirm zero contract or API regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS route wiring in Phase 3 & 4
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion (MVP priority P1)
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion (Priority P2)
- **User Story 3 (Phase 5)**: Depends on Phase 3 route changes in `server.ts` to verify non-interference
- **Polish (Phase 6)**: Depends on completion of all user stories

### User Story Dependencies

- **US1 (Ship 30 Essay)**: Independent after Phase 2
- **US2 (HTML Artifact)**: Independent after Phase 2
- **US3 (Grounded Q&A)**: Verifies non-interference with `server.ts` modifications

### Parallel Opportunities

- T003, T004, and T005 (in US1) can be developed in parallel as they touch different files (`tests/tools/validate_essay_tool.test.ts`, `src/tools/generate_ship30_essay.ts`, `src/tools/validate_essay_tool.ts`)
- T008 and T009 (in US2) can be developed in parallel (`tests/tools/render_check_tool.test.ts`, `src/tools/render_check_tool.ts`)
- T014 and T015 (in Polish) can run in parallel

---

## Parallel Execution Example: User Story 1

```bash
# Launch parallel implementation files for US1:
Task T003: Create unit test suite in agent-sidecar/tests/tools/validate_essay_tool.test.ts
Task T004: Refactor existing essay helper in agent-sidecar/src/tools/generate_ship30_essay.ts
Task T005: Create validate_essay tool in agent-sidecar/src/tools/validate_essay_tool.ts

# Once T002, T004, and T005 are complete, wire route:
Task T006: Wire ship30_essay branch in agent-sidecar/src/server.ts
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) & Phase 2 (Foundational session runner `run_agent_session.ts`)
2. Complete Phase 3 (User Story 1: `validate_essay_tool.ts` + `server.ts` wiring)
3. **STOP & VALIDATE**: Test `ship30_essay` via `agent-sidecar` unit tests and Scenario 1 quickstart curl

### Incremental Delivery

1. Setup + Foundational -> Session runner ready
2. User Story 1 -> Ship 30 essay tool-calling complete (MVP!)
3. User Story 2 -> HTML artifact tool-calling complete
4. User Story 3 -> Q&A bypass verified
5. Polish -> ADR-004 updated + full test suites passing
