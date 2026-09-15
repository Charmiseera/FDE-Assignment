# PRD: The Lenny Growth Assistant

**Context**
- **Target Users:** Product managers, growth leads, and founder-operators who follow Lenny's Podcast for tactical PM/growth guidance.
- **Main Problem:** The knowledge in Lenny's Podcast is valuable but locked inside hours of long-form transcripts — people either skim once and forget, or avoid searching altogether because it's slow and un-cited.
- **Unique Value:** A conversational assistant grounded strictly in the transcript corpus that answers precisely with source citations, and can turn that grounded knowledge directly into publish-ready written content and rendered artifacts — collapsing "research → answer → content" into one flow.

---

## 1. Problem Statement

Product and growth practitioners treat Lenny's Podcast as a primary source of tactical, operator-tested advice, but the format works against reuse: insights are scattered across hundreds of hours of transcripts with no reliable way to search by topic, verify a claim's source, or convert a remembered idea into something shareable. Today, a PM who half-remembers "someone on Lenny's talked about activation metrics for PLG" has no fast way to find the exact episode, confirm what was actually said, or turn that insight into a LinkedIn post or internal memo without manually re-listening or guessing. The result is under-utilized knowledge: good advice exists, but retrieval friction keeps it from being applied.

## 2. Goals & Objectives

1. **Grounded retrieval**: Enable a user to get a cited, transcript-grounded answer to a product/growth question in under 15 seconds of interaction (not counting typing time), for at least 80% of in-scope questions.
2. **Content conversion**: Let a user turn any grounded conversation into a publish-ready Ship 30/30-style essay (~1,250 words) in a single request, with zero manual reformatting needed before sharing.
3. **Trust through citation**: Ensure 100% of factual claims in assistant answers are attributable to a specific transcript source, with zero fabricated citations.
4. **Deployment accessibility**: Allow an evaluator or client engineer with no ML background to run the full system locally, using only documented steps, in under 15 minutes.
5. **Cost-flexible operation**: Allow the client to run the assistant entirely on a local model with no per-query cloud cost, while retaining the option to switch to a faster cloud model without any code changes.

## 3. Success Metrics

1. **Citation coverage**: ≥95% of assistant answers that make a factual claim include at least one valid, verifiable transcript citation.
2. **Grounded-refusal accuracy**: 100% of questions with no supporting transcript content receive an explicit "I don't have grounding for this" response rather than a fabricated answer.
3. **Time-to-draft**: Median time from "request a Ship 30/30 essay" to a complete, formatted draft is under 3 minutes.
4. **Session continuity**: ≥90% of follow-up questions within a session correctly use prior conversation context (measured via manual test scenarios, see Section 7).
5. **Setup success rate**: A fresh evaluator can go from `git clone` to a working chat response in ≤15 minutes following only the README, on first attempt.

## 4. Target Personas

### Persona 1 — "Growth PM Priya"
- **Demographics:** 31, Senior Product Manager at a Series B SaaS company, 6 years in PM roles.
- **Pain points:** Needs tactical, operator-validated answers fast (e.g., "how do other PLG companies structure activation metrics?") but doesn't have time to search podcast transcripts or re-listen to 90-minute episodes. Distrusts generic AI answers without sources she can check with her team.
- **Goals:** Get a quick, defensible answer she can bring into a planning meeting, with a source she can point to if challenged.
- **Technical proficiency:** Comfortable with SaaS tools and basic AI chat products; not a developer, has no interest in prompts, models, or infrastructure.

### Persona 2 — "Founder-Writer Marcus"
- **Demographics:** 27, solo founder of an early-stage B2B tool, writes a weekly newsletter and posts on LinkedIn to build an audience.
- **Pain points:** Wants to publish consistently but struggles to turn scattered ideas into a finished, well-structured essay; has read the Ship 30/30 guide but finds it hard to apply consistently under time pressure.
- **Goals:** Go from "a rough idea sparked by something Lenny's guest said" to a polished, on-brand essay draft in minutes, without hiring a ghostwriter.
- **Technical proficiency:** Non-technical; expects a simple, chat-like experience with no configuration required to get value.

## 5. Features & Requirements

### P0 — Must-Have (MVP)

**Feature: Grounded Conversational Q&A**
- *Description:* Users ask product/growth questions and receive answers sourced strictly from the transcript corpus, with follow-up questions preserving context.
- *User story:* As a growth PM, I want to ask a product question and get a cited answer, so that I can trust and reuse it without re-verifying it myself.
- *Acceptance criteria:*
  1. A question with clear transcript support returns an answer citing the specific episode/source.
  2. A question with no transcript support returns an explicit "not covered in the available material" response, never a fabricated answer.
  3. A follow-up question referencing "it" or "that" correctly resolves to the prior turn's topic.
  4. Each new chat starts with no memory of prior unrelated sessions.
  5. Response is returned or visibly streaming within 5 seconds under normal load.
- *Success metric:* ≥95% citation coverage on claims (Metric 1); 100% refusal accuracy on unsupported questions (Metric 2).

**Feature: Session Management**
- *Description:* Users can start new chats and switch between past sessions, each with independent, persisted context.
- *User story:* As a user, I want to start a fresh conversation without old context bleeding in, so that unrelated topics don't confuse the assistant.
- *Acceptance criteria:*
  1. "New chat" creates an isolated session with no prior message history.
  2. Reopening a past session restores its full message history in order.
  3. Messages, timestamps, and session metadata persist across app restarts.
  4. Two concurrent sessions never share or leak context between each other.
- *Success metric:* Session continuity metric (Metric 4) ≥90%.

**Feature: Ship 30/30 Essay Generation**
- *Description:* Converts a grounded conversation into a ~1,250-word essay following Ship 30/30 writing principles (strong hook, skimmable structure, specific takeaway).
- *User story:* As a founder-writer, I want to turn a grounded discussion into a publish-ready essay, so that I can post it with minimal editing.
- *Acceptance criteria:*
  1. Output word count falls within 1,250 words ± 15%.
  2. Output contains a distinct hook, at least two subheadings, selective bold emphasis, and one clearly stated takeaway.
  3. All factual claims in the essay trace back to retrieved transcript content.
  4. Requesting the essay again on the same topic produces a structurally valid essay each time (not just once).
- *Success metric:* Time-to-draft (Metric 3) under 3 minutes; structural validity on 100% of generated essays.

**Feature: Artifact Generation & Viewer**
- *Description:* On request, the assistant produces a Markdown or HTML/CSS artifact rendered in a dedicated viewer alongside the chat, not as raw code or a redirect.
- *User story:* As a user, I want to see a generated document or snippet rendered visually next to my conversation, so that I can evaluate it without leaving the app.
- *Acceptance criteria:*
  1. Requesting an artifact produces a rendered preview, not a code block, within the same screen as the chat.
  2. Users can view the underlying raw source on demand.
  3. A generated HTML artifact cannot access or modify anything outside its own rendered frame (no cookie, storage, or parent-page access).
  4. Artifact history is retrievable for the session it was created in.
- *Success metric:* Zero artifact-related security incidents in manual testing (Section 7, Scenario 3).

**Feature: Local/Cloud Model Toggle**
- *Description:* The client can run the assistant fully offline on a local model, or switch to a cloud model, via configuration only.
- *User story:* As an evaluator, I want to run the assistant without any cloud dependency, so that I can test it without incurring cost or needing external accounts.
- *Acceptance criteria:*
  1. The system runs end-to-end with only a local model configured, no cloud API key present.
  2. Switching the configured provider requires no code changes.
  3. The active provider is visibly displayed to the user.
  4. If a cloud provider is misconfigured or unreachable, the user sees a clear, non-crashing error message.
- *Success metric:* Setup success rate (Metric 5) ≥ target on local-only path.

### P1 — Should-Have

- **Conversation search/browse**: search across past session titles/content. *User story:* As a returning user, I want to find a past conversation by topic, so I don't have to scroll through every session. *Acceptance criteria:* keyword search returns matching sessions; empty search state is handled; search covers session titles and message content. *Success metric:* search returns a relevant result in ≥90% of test queries against known session content.
- **Citation deep-link**: clicking a citation shows the exact source excerpt. *Acceptance criteria:* clicking any citation displays the referenced transcript excerpt without leaving the chat; missing-source case shows a graceful fallback. *Success metric:* 100% of citations resolve to a visible excerpt or an explicit "source unavailable" state, never a silent failure.
- **Artifact export**: download a generated artifact as a file. *Acceptance criteria:* Markdown and HTML artifacts can both be downloaded; filename reflects content topic. *Success metric:* 100% of generated artifacts are downloadable without corruption.

### P2 — Nice-to-Have (future)

- Multi-user accounts and authentication
- Usage analytics dashboard for the client team
- Support for ingesting additional podcasts/newsletters beyond Lenny's
- Voice input for questions
- Collaborative multi-user artifact editing

## 6. Explicitly Out of Scope

1. Multi-user authentication, roles, or permissions (single-user/local evaluation only in this version).
2. Ingesting or supporting any content source other than the specified Lenny's transcript repository.
3. Real-time transcript ingestion from new podcast episodes as they're published (ingestion is a manual/scheduled refresh, not a live pipeline).
4. Fine-tuning or training a custom model — the system uses off-the-shelf hosted or local models only.
5. Mobile native apps (iOS/Android) — web-responsive only.
6. Long-term memory or personalization across sessions beyond what's stored in a given session's history.
7. Billing, usage quotas, or monetization features.
8. Multi-language support — English transcripts and English responses only.
9. A general-purpose chatbot mode unrelated to product/growth/Lenny's content.
10. Enterprise-grade access controls, audit logging for compliance, or SSO.

## 7. User Scenarios

### Scenario 1 — Grounded question with a follow-up
**Context:** Priya is preparing for a roadmap review and wants a quick, defensible answer on activation metrics.
1. Priya opens a new chat and asks, "How do PLG companies typically define activation?"
2. The assistant retrieves relevant transcript excerpts, answers with 2-3 concrete definitions, and cites the specific episodes each came from.
3. Priya asks a follow-up: "Which of those applies best to a B2B tool with a long sales cycle?"
4. The assistant resolves "those" to the prior answer's list, narrows to the relevant option(s), and still cites sources.
**Expected outcome:** Priya leaves with a cited answer to reference in her meeting.
**Edge cases:** If the follow-up references something never mentioned, the assistant asks for clarification rather than guessing. If retrieval returns nothing relevant to the follow-up, the assistant says so explicitly instead of reusing the prior answer's sources incorrectly.

### Scenario 2 — Turning a conversation into a Ship 30/30 essay
**Context:** Marcus has been discussing onboarding friction with the assistant and wants to publish his takeaway.
1. Marcus asks several grounded questions about onboarding best practices.
2. He then says, "Turn this into a Ship 30/30 essay."
3. The assistant generates a ~1,250-word essay with a hook, subheadings, bold emphasis, and a clear takeaway, grounded in the same sources discussed.
4. The essay renders in the Artifact Viewer beside the chat.
**Expected outcome:** Marcus can copy or export a ready-to-post draft.
**Edge cases:** If the conversation so far doesn't contain enough grounded material for a full essay, the assistant says so and suggests what to discuss further before generating. If the first draft fails internal structure checks (e.g., too short), the system regenerates before returning it to the user, rather than returning a malformed draft.

### Scenario 3 — Requesting an HTML artifact (security case)
**Context:** A user asks for a simple interactive comparison table as an HTML artifact.
1. User: "Create an HTML snippet comparing these two frameworks as a table."
2. Assistant generates HTML and renders it in the Artifact Viewer.
3. As a deliberate test, the manual test plan includes requesting an artifact containing a script that attempts to read cookies or navigate the parent page.
**Expected outcome:** The table renders correctly for the legitimate request; in the security test, the malicious script executes only inside its isolated frame and cannot access cookies, local storage, or the parent page, and cannot navigate the browser away from the app.
**Edge cases:** Malformed HTML still renders without crashing the viewer; an artifact request with no prior conversation context still succeeds if the request is self-contained.

## 8. Non-Functional Requirements

- **Performance:** First response token/content should begin appearing within 5 seconds under normal conditions on the local model; cloud mode should be as fast or faster. Retrieval (before generation begins) should complete in under 1 second for the given corpus size.
- **Security:** Generated HTML/artifact content must be isolated such that it cannot access the host application's cookies, local storage, or DOM, and cannot navigate the top-level page. No user-entered content is ever executed as backend code.
- **Accessibility:** Interactive elements are keyboard-navigable; interface meets WCAG 2.1 AA color contrast; all controls have accessible labels; citation and artifact content is readable by screen readers.
- **Reliability:** The system degrades gracefully (clear error states, no crashes) when the database, local model service, or cloud provider is unavailable.
- **Scalability:** The MVP must comfortably support a single evaluator running multiple concurrent sessions; it is not required to support production-scale concurrent multi-tenant load in this version.

## 9. Dependencies, Constraints & Assumptions

**Dependencies**
- The specified Lenny's Podcast/Newsletter transcript repository as the sole knowledge source.
- Availability of at least one cloud model provider and one locally runnable model, both reachable from the evaluator's machine.
- A relational database instance for persistence, reachable from the running application.

**Constraints**
- Must be runnable entirely on a single evaluator's machine without requiring paid infrastructure.
- Must not require the evaluator to have any AI/ML background to operate.
- Timeline constraint: this version must be complete and demonstrable within the take-home assignment window.

**Assumptions** *(made because the original brief left these open)*
1. "Users" in this version means a single evaluator/operator, not a multi-tenant customer base — so no auth system is assumed necessary yet.
2. The transcript repository's content is treated as static for the ingestion pipeline's purposes within the assignment window; "refresh" means a manually triggered re-ingestion, not a live sync.
3. "Grounded" is interpreted strictly: if the corpus doesn't address a question, the correct behavior is an explicit refusal rather than a best-effort general-knowledge answer.
4. A single well-supported local model is sufficient to demonstrate the local/cloud toggle requirement; broad multi-model compatibility is not required.
5. "Success" for this assignment is evaluator trust and comprehension, not real end-user adoption data, since there is no live user base during the assignment period.

## 10. Timeline

**MVP (this submission)**
- Includes: all P0 features (grounded Q&A, sessions, Ship 30/30 skill, artifact generation + viewer, local/cloud toggle), core deployment readiness (setup docs, env config, health checks, basic tests).
- Milestone target: complete and submitted by **15/09/26 EOD**, per assignment deadline.

**V1.0 (illustrative future roadmap, post-evaluation)**
- Includes: P1 features (conversation search, citation deep-linking, artifact export), expanded automated test coverage, and a hardening pass on observability and error handling based on real usage.
- Notional target: 4-6 weeks after an evaluation decision to proceed, pending real usage data to prioritize P2 items.

---

## 11. Risks & Trade-offs *(required by the engagement brief)*

- **Hallucination risk:** Mitigated by strict grounding rules and an explicit refusal path when retrieval confidence is low — but no grounding approach eliminates this risk entirely; occasional over-confident phrasing remains possible and should be monitored.
- **Latency:** Local models are slower than cloud models; this is disclosed to the user via the visible provider badge rather than hidden.
- **Local-model quality gap:** The local model may handle tool-calling or nuanced instructions less reliably than the cloud model; where this creates a meaningful capability gap (e.g., in agentic tool use), it's documented rather than silently degraded.
- **Cost:** Cloud provider usage has a per-query cost; local mode has none but trades off latency/quality — this is a deliberate, disclosed trade-off, not an oversight.
- **Data leakage / artifact rendering:** Untrusted generated HTML is isolated from the host application; this is treated as a security-critical requirement, not an afterthought, given Section 4.3's explicit security expectation.`
- **Single-source scope:** Restricting to one transcript corpus limits usefulness outside PM/growth topics — an intentional scope choice to keep grounding reliable rather than diluting it with unrelated content.