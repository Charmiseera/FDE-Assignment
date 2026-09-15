# Demo Video Recording Script — Lenny Growth Assistant
**Target Duration:** 2:30 – 3:00 Minutes  
**Camera:** Enabled throughout (Picture-in-Picture on upper-right corner of screen)  
**Platform:** YouTube (Unlisted or Public)

---

## Pre-Recording Checklist
1. All three services running:
   - Frontend: `http://localhost:5173`
   - Backend: `http://localhost:8000/docs`
   - Sidecar: `http://localhost:4000/health`
2. Browser open at `http://localhost:5173` with a clean session.
3. Ollama running locally in terminal (`ollama list` shows `qwen2.5:3b` and `nomic-embed-text`).
4. Screen recorder set to capture entire screen + webcam overlay in corner.

---

## Detailed Scene-by-Scene Script

### Scene 1: Introduction & Problem Statement (0:00 – 0:35)
**Visual:** Webcam front & center (or large PIP overlay). Browser showing The Lenny Growth Assistant homepage.

**Spoken Script:**
> *"Hi everyone, my name is [Your Name], and this is my submission for the Forward Deployed Engineer take-home assessment: The Lenny Growth Assistant.*
>
> *Product managers and growth leaders spend hundreds of hours listening to podcasts like Lenny's, searching for tactical frameworks. But standard conversational AI often hallucinates generic startup advice rather than giving real, expert-grounded truth.*
>
> *To solve this, I built the Lenny Growth Assistant — a grounded operator workbench that combines pgvector semantic search over 30 landmark transcript episodes, seamless switching between local and cloud LLMs, and an autonomous coding agent that synthesizes discussions into publish-ready Ship 30/30 essays and visual artifacts."*

---

### Scene 2: Grounded Q&A, Citations & In-Flight Stop Button (0:35 – 1:15)
**Visual:** Screen recording focused on the chat panel at `http://localhost:5173`.

**Actions to Perform:**
1. Click the suggested prompt: *"What is Elena Verna's advice on B2B product-led growth?"*.
2. Point cursor to the streaming response and source citations.
3. Type an off-topic query: *"How do I bake a chocolate cake?"*.
4. Show the immediate grounded refusal response.
5. Click *"How do PLG leaders define activation?"*, and while the loading dots animate, click the red **[■ Stop]** button.

**Spoken Script:**
> *"Let’s look at the product in action. First, our Grounded Q&A engine.*
>
> *I’ll click a prompt asking for Elena Verna’s advice on B2B growth. The backend converts the query into a 768-dimensional vector using nomic-embed-text, performs an HNSW cosine similarity search in Postgres, and generates an answer that cites the exact episode and transcript excerpts.*
>
> *Notice how strict our grounding is: if I ask an out-of-domain question like 'How do I bake a chocolate cake?', the system immediately refuses to answer without hallucinating.*
>
> *We've also added an in-flight Stop button powered by an AbortController, allowing operators to cancel requests instantly without hanging the UI."*

---

### Scene 3: Ship 30/30 Essay & Sandboxed Artifact Viewer (1:15 – 1:55)
**Visual:** Click the "Generate Ship 30/30 Essay" button, then click "View Generated Artifact" to open the right-side split pane.

**Actions to Perform:**
1. Click the quick-action button: **"Generate Ship 30/30 Essay"**.
2. Wait 2 seconds for generation.
3. Click the newly appeared **"View Generated Artifact"** button.
4. Scroll through the rendered essay in the right pane: highlight the headline, bold takeaways, subheadings, and GFM markdown tables.
5. Toggle between **"Rendered"** and **"Raw"**, then click the **Copy** icon.

**Spoken Script:**
> *"Now let’s look at our advanced agent capability: the Ship 30/30 Atomic Essay generator.*
>
> *With one click, the system prompts our Pi Coding Agent sidecar microservice. The agent uses custom tool calling — running our validate_essay tool in a self-correction loop to guarantee the essay has a single compelling headline, at least two subheadings, bold emphasis, and an explicit key takeaway.*
>
> *When I click 'View Generated Artifact', the split pane opens smoothly. Notice the editorial typography and our custom GitHub-Flavored Markdown table styling. Operators can switch between the rich rendered view and raw markdown, or copy the complete draft to their clipboard with one click."*

---

### Scene 4: Local Ollama Demonstration & Technical Trade-Off (1:55 – 2:40)
**Visual:** Move cursor to top header, click "Local", show the badge switch to `Ollama (Local) • qwen2.5:3b`.

**Actions to Perform:**
1. Click the **"Local"** button in the header bar.
2. Show that the active badge updates to `Ollama (Local) • qwen2.5:3b`.
3. Send a quick question: *"What is an activation metric?"*.

**Spoken Script:**
> *"A core requirement of this system is offline autonomy. In the header, I can toggle between Cloud mode — powered by Groq's openai/gpt-oss-120b — and Local mode, powered by Ollama running qwen2.5:3b.*
>
> *Everything — from 768-dim embeddings to vector retrieval and chat generation — can run 100% locally and privately without internet connectivity.*
>
> *This brings us to an important technical trade-off I made during architecture design:*
>
> *Instead of embedding the agent loop directly inside Python, I architected the agent as a standalone Node.js sidecar service running the Pi Coding Agent framework, communicating with FastAPI over an internal HTTP contract.*
>
> *The trade-off here was accepting a small JSON HTTP serialization hop between services in exchange for complete language and security isolation. The Pi Coding Agent excels at TypeScript tool definitions and streaming state, while FastAPI excels at async database pooling and pgvector queries. Crucially, the sidecar holds zero database credentials, preventing cross-language ORM drift and eliminating credential leakage risks."*

---

### Scene 5: Conclusion & Wrap-Up (2:40 – 3:00)
**Visual:** Return camera to full view or highlight terminal running test suites.

**Spoken Script:**
> *"To ensure enterprise reliability, the codebase includes 35 passing backend pytest tests, 12 passing sidecar vitest tests, and a fully typed, production-built frontend.*
>
> *All deliverables — including the PRD, architecture specification, UI design document, and sanitized agent trajectory logs — are included in the repository.*
>
> *Thank you for your time, and I look forward to discussing the implementation!"*
