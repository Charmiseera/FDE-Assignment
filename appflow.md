# APP_FLOW.md — The Lenny Growth Assistant

> **Note on scope:** This document supplements `design.md` and `architecture.md`. Per the PRD (Section 6, Out of Scope), this app has no accounts, authentication, or purchase flow — it's a single-user, locally-run conversational tool. Sections of the requested template that assume auth/e-commerce/marketing flows are marked **N/A** below with the reasoning, rather than filled with flows that don't exist in this system.

---

## 1. Entry Points

- **Direct URL access:** `http://localhost:<port>` (or the deployed host) — the only real entry point. This is a locally-run evaluation tool, not a public product.
- **Deep links (email, notifications):** N/A — no notification system or shareable session links in this version (see PRD Out of Scope, item 6: no cross-session personalization/sharing infrastructure).
- **OAuth/social login:** N/A — no authentication in this version (PRD Out of Scope, item 1).
- **Search engines:** N/A — not a publicly indexed product.
- **Marketing campaigns:** N/A — internal/evaluation tool, not marketed.

The single real entry point: a user opens the app URL and lands directly on the main chat screen — no login wall, no landing page funnel.

---

## 2. Core User Flows

The template's "required flows" are adapted below to what this app actually has.

### 2.1 First-Load Experience (replaces "onboarding/registration")

**Happy path**
1. **Screen:** Main Chat Screen (empty state)
2. **UI elements:** Session sidebar (empty, "New Chat" button), empty chat panel with a prompt placeholder ("Ask a product or growth question…"), provider badge (e.g., "Running on: Ollama (llama3.1:8b)"), empty Artifact Viewer pane (collapsed or placeholder).
3. **User action:** Types a question and presses Enter / clicks Send.
4. **System response:** A new session is created automatically on first message (no explicit "create session" step needed); message appears in the chat; assistant response streams in below it.
5. **Validation rules:** Message cannot be empty or whitespace-only — Send button is disabled until valid input exists.
6. **Next state:** Chat Screen — Active Session (populated).
7. **Success criteria:** User has a session with at least one exchanged message pair, visible in the sidebar with an auto-generated title (e.g., first few words of the question).

**Error states**
- Backend unreachable on load → banner: *"Can't connect to the assistant backend. Check that the server is running."* with a retry button.
- Provider misconfigured (e.g., `LLM_PROVIDER=groq` but no `GROQ_API_KEY`) → badge shows "Provider unavailable" and chat input is disabled with an inline message explaining why, rather than allowing a request that will fail.

**Edge cases**
- User refreshes the page mid-response → in-progress response is lost (not persisted until complete); on reload, the last completed exchange is shown; a note documents this as a known MVP limitation.
- User opens the app in two browser tabs → each tab can hold a different active session; no real-time sync between tabs in this version.

### 2.2 Main Feature Flow A — Grounded Q&A with Follow-up

**Happy path**
1. **Screen:** Chat Screen — Active Session
2. **UI elements:** Message input, message list, citation chips under assistant responses.
3. **User action:** Sends a product/growth question.
4. **System response:** Retrieval runs → assistant streams an answer → citation chip(s) appear under the response, each labeled with episode/source.
5. **Validation rules:** None beyond non-empty input; no topic restriction is enforced client-side (grounding/refusal happens server-side based on retrieval).
6. **Next state:** User sends a follow-up; system resolves pronouns/context from session history.
7. **Success criteria:** Answer is cited; follow-up correctly uses prior context (per PRD Success Metric 4).

**Error states**
- No relevant transcript content found → assistant responds explicitly: *"I couldn't find anything in the transcripts that addresses this — try asking about [nearest supported topic area]."* No citation chip is shown, and no fabricated answer is returned.
- Model/provider timeout → chat shows a stalled-response indicator, then: *"The assistant didn't respond in time. You can try again."* with a retry action; the user's message remains in the input history (not lost).
- Backend/database error mid-request → error bubble in place of the assistant response: *"Something went wrong generating this response."* with retry; the user's own message stays visible and undamaged.

**Edge cases**
- User sends a new message before the previous response finishes → previous request either completes and appends normally, or the UI queues the new message until the in-flight one resolves (documented choice — pick one and state it in `architecture.md`).
- User navigates to a different session mid-response → in-flight response either completes silently in the background and appears when the user returns, or is cancelled — document whichever behavior is implemented.
- Session left idle for a long period → no explicit session expiry in this version (no auth/session tokens to expire); the session data persists in the database indefinitely.

### 2.3 Main Feature Flow B — Ship 30/30 Essay Generation

**Happy path**
1. **Screen:** Chat Screen — Active Session (with prior grounded discussion)
2. **UI elements:** Message input; a "Generate Ship 30/30 Essay" affordance (button or recognized natural-language request).
3. **User action:** Requests an essay based on the conversation so far.
4. **System response:** Assistant runs the Ship 30/30 skill against grounded context, validates structure/length, and returns the essay as a rendered Markdown artifact.
5. **Validation rules:** Server-side structural validation (word count range, hook, subheadings, takeaway) before the draft is shown — see `architecture.md` for the retry-on-validation-failure loop.
6. **Next state:** Artifact Viewer pane opens/populates with the essay; chat shows a short confirmation message plus a link to the artifact.
7. **Success criteria:** Essay renders in the Artifact Viewer within the time-to-draft target (PRD Success Metric 3).

**Error states**
- Not enough grounded material in the conversation to write a full essay → assistant declines with a specific reason: *"There isn't enough grounded discussion yet to write a full essay — try asking a bit more about [topic] first."*
- Structural validation fails twice (e.g., can't reach target length) → assistant returns its best draft with an explicit disclaimer noting which criteria weren't fully met, rather than silently failing or looping forever.

**Edge cases**
- User requests a second essay in the same session on a different sub-topic → creates a new artifact rather than overwriting the first; both are retrievable from the session's artifact history.

### 2.4 Main Feature Flow C — Artifact Generation & Viewing (HTML/Markdown)

**Happy path**
1. **Screen:** Chat Screen — Active Session
2. **UI elements:** Message input; Artifact Viewer pane (side-by-side on desktop).
3. **User action:** Requests a Markdown doc or HTML snippet (e.g., a comparison table).
4. **System response:** Artifact renders in the isolated viewer pane immediately.
5. **Validation rules:** N/A for user input; system-side sanitization/sandboxing is the safeguard (see `architecture.md` security section).
6. **Next state:** User can toggle between rendered view and raw source.
7. **Success criteria:** Artifact renders correctly and cannot access app cookies/storage/parent DOM (PRD Scenario 3).

**Error states**
- Malformed generation output → viewer shows a fallback message (*"This artifact couldn't be rendered — view raw source instead"*) rather than a blank or broken pane.

**Edge cases**
- User requests an artifact with no prior conversation in the session → allowed if the request is self-contained; otherwise the assistant asks a clarifying question.

### 2.5 "Account Management" — N/A

Not applicable in this version: there are no user accounts, profiles, or settings tied to identity (PRD Out of Scope, item 1). The closest equivalent is **session management** (covered in 2.1) and a **provider configuration view** (read-only display of the active model/provider, set via `.env`, not editable in-app in this version).

### 2.6 Error Recovery (general, cross-cutting)

- **Backend down at any point:** persistent banner across the app: *"Lost connection to the backend."* with automatic reconnect attempts and a manual retry button. Chat input is disabled while disconnected, re-enabled on reconnect.
- **Database unreachable:** health check surfaces this; new messages fail with a clear error rather than silently not saving; existing loaded messages in the current view remain visible (client-side state isn't wiped).
- **Local model (Ollama) not running while selected:** clear, specific message: *"Ollama isn't reachable at [configured URL]. Start Ollama and try again."* — not a generic 500.

---

## 3. Navigation Map

```
/ (Main Chat Screen)
├── Sidebar
│   ├── "New Chat" action → creates and switches to a new empty session
│   └── Session list → clicking a session loads it in the main panel
├── Chat Panel (active session)
│   ├── Message list (scrollable, citation chips inline)
│   └── Message input (send action)
├── Artifact Viewer (contextual pane, populated when an artifact exists for the session)
│   ├── Rendered view (default)
│   └── Raw source view (toggle)
└── Provider Badge (header) → optionally opens a read-only info panel showing active provider/model
```

No authentication gating anywhere — every route/pane is accessible by default, since there's a single implicit user per running instance.

---

## 4. Screen Inventory

| Screen/State | Route | Access | Purpose | Key elements | Actions → leads to | State variants |
|---|---|---|---|---|---|---|
| Main Chat Screen | `/` | Public (local instance) | Primary interface for chat + artifacts | Sidebar, chat panel, artifact pane, provider badge | Send message → new exchange in same screen; New Chat → new session; select session → loads that session | Empty (no sessions), loading (streaming response), error (backend/provider down), populated (normal) |
| Session (loaded) | `/` (client-side state, not a distinct route in MVP) | Public | View/continue a specific conversation | Full message history, citations | Send follow-up; request essay/artifact | Loading, populated, error-on-send |
| Artifact Viewer (pane) | N/A (embedded, not routed) | Public | Render generated Markdown/HTML | Rendered content, raw-source toggle | Toggle view; (P1) export/download | Empty/placeholder, loading, rendered, render-failed |
| Provider Info (modal/panel) | N/A (embedded) | Public | Show which model/provider is active | Provider name, model name, connection status | Close | Connected, unreachable |

The screen count is intentionally small — this is a single-page conversational app, not a multi-route product, and padding this table with routes that don't exist would misrepresent the system.

---

## 5. Decision Points (IF-THEN)

```
IF user sends an empty or whitespace-only message
THEN disable Send / reject client-side, no request sent to backend

IF configured LLM_PROVIDER requires an API key AND the key is missing or invalid
THEN disable chat input and show "Provider unavailable" state (do not attempt the request)

IF retrieval returns zero chunks above the similarity threshold
THEN respond with an explicit no-grounding message; do NOT call the generation step with an empty-context prompt that could hallucinate

IF a Ship 30/30 essay draft fails structural validation (word count / required sections)
THEN retry generation once with corrective feedback
ELSE (fails again) return the draft with an explicit disclaimer of which criteria weren't met

IF the backend health check reports the database as unreachable
THEN show a persistent connection-error banner and disable message sending

IF the backend health check reports the configured local model (Ollama) as unreachable
THEN show a specific "local model unreachable" message distinct from the generic backend-down banner

IF a generated artifact is HTML
THEN render it only inside a sandboxed iframe with no allow-same-origin
ELSE (Markdown) render through a safe Markdown renderer with no raw-HTML passthrough

IF a user requests an artifact with no relevant prior conversation context
THEN check whether the request is self-contained; if not, ask a clarifying question instead of generating from nothing
```

---

## 6. Error Handling

| Error type | Display | User actions available | System recovery |
|---|---|---|---|
| 404 (unknown route) | Simple "Page not found" screen — rare in this SPA since almost everything is state, not routes | Link back to Main Chat Screen | N/A (client-side redirect) |
| 500 / backend exception | Inline error bubble in the chat where the response would have gone | Retry the same message | Backend logs the exception with request context; user's own message is preserved, not lost |
| Network offline | Persistent top banner: "You're offline" or "Can't reach the backend" | Manual retry; automatic reconnect polling | Reconnect banner clears automatically once connectivity returns |
| Permission denied | N/A — no permission tiers in this version | — | — |
| Form validation failure (empty message) | Send button stays disabled; no error dialog needed for something this minor | Type a valid message | N/A |

---

## 7. Responsive Behavior

- **Desktop:** Chat panel and Artifact Viewer shown side-by-side; sidebar always visible.
- **Tablet:** Sidebar collapses to a toggleable drawer; chat and artifact panes remain side-by-side if width allows, otherwise stack.
- **Mobile:** Single-column stack — sidebar becomes a slide-over drawer accessed via a menu icon; Artifact Viewer appears **below** the chat (not hidden behind a separate tab) when an artifact exists, so it's never fully inaccessible, per the design principle in `design.md`.

---

## 8. Animations & Transitions

Kept deliberately minimal — this is a utility tool, not a marketing product, and excess motion would work against the "fast, trustworthy" feel the PRD's personas need:

- **Message appearance:** simple fade/slide-in (~150ms) as new messages are added; no bounce or decorative motion.
- **Assistant response:** streamed token-by-token with no artificial delay beyond actual generation time.
- **Artifact pane open:** slide-in from the side (~200ms ease-out) on desktop/tablet; on mobile, the pane simply appears inline below the chat as the layout is already stacked.
- **Sidebar drawer (mobile/tablet):** standard slide-over with a dim overlay, dismissible by tapping outside or an explicit close action.
- **Loading states:** a lightweight typing/streaming indicator, not a full-screen spinner, to keep the interface feeling responsive rather than blocking.