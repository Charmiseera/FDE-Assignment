import express, { Request, Response } from "express";
import Groq from "groq-sdk";
import { runAgentSession } from "./agent/run_agent_session.js";
import { validateEssayTool } from "./tools/validate_essay_tool.js";
import { renderCheckTool } from "./tools/render_check_tool.js";
import { validateEssay } from "./tools/generate_ship30_essay.js";

const app = express();
app.use(express.json({ limit: "2mb" }));

import fs from "fs";
import path from "path";

// Fallback .env loader for local development
function loadEnv() {
  const envPaths = [path.resolve(".env"), path.resolve("../.env")];
  for (const p of envPaths) {
    if (fs.existsSync(p)) {
      const content = fs.readFileSync(p, "utf-8");
      for (const line of content.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const eqIdx = trimmed.indexOf("=");
        if (eqIdx !== -1) {
          const key = trimmed.slice(0, eqIdx).trim();
          let val = trimmed.slice(eqIdx + 1).trim();
          if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
            val = val.slice(1, -1);
          }
          if (!process.env[key]) {
            process.env[key] = val;
          }
        }
      }
    }
  }
}
loadEnv();

const PORT = process.env.PORT || 4000;
const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
const GROQ_API_KEY = process.env.GROQ_API_KEY || "";

app.get("/health", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    service: "agent-sidecar",
    timestamp: new Date().toISOString()
  });
});

interface ContextChunk {
  source_file: string;
  episode_title: string;
  chunk_text: string;
}

interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
}

interface RunRequest {
  provider?: "groq" | "ollama";
  model?: string;
  context_chunks?: ContextChunk[];
  conversation?: ConversationTurn[];
  request_type?: "answer" | "ship30_essay" | "html_artifact" | "artifact";
}

// ── build grounded-answer prompt ────────────────────────────────────────────

function buildAnswerPrompt(
  chunks: ContextChunk[],
  conversation: ConversationTurn[]
): string {
  const context = chunks
    .map((c, i) => `[Source ${i + 1}: ${c.episode_title} (${c.source_file})]\n${c.chunk_text}`)
    .join("\n\n---\n\n");

  const history = conversation
    .slice(-6) // last 3 turns for multi-turn context
    .map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`)
    .join("\n");

  return `You are the Lenny Growth Assistant — a knowledgeable AI that answers product and growth questions drawing on Lenny's Podcast transcripts.

Rules:
1. Prioritize the provided Context below as your primary source. Quote and synthesize from it.
2. Cite sources inline naturally (e.g. "In the episode with Elena Verna...", "According to [Episode Title]...").
3. If the context addresses the question only partially, synthesize what IS there and note any gaps.
4. Only say you lack information if the context is completely unrelated to the question.
5. Be concise and direct. Product managers are busy.

Context (from Lenny's Podcast transcripts):
${context}

Conversation history:
${history}

Answer the user's question using the transcript context above:`;
}

function buildEssayPrompt(
  chunks: ContextChunk[],
  conversation: ConversationTurn[]
): string {
  const context = chunks
    .map((c) => `[${c.episode_title}]\n${c.chunk_text}`)
    .join("\n\n---\n\n");

  const substantiveTurn = [...conversation]
    .reverse()
    .find(
      (m) =>
        m.role === "user" &&
        !m.content.toLowerCase().includes("essay") &&
        !m.content.toLowerCase().includes("ship 30")
    );
  const topic = substantiveTurn?.content || "Product Activation and Retention Frameworks";

  return `Write a comprehensive, structured Ship 30/30 atomic essay on "${topic}" strictly grounded in the Lenny's Podcast excerpts below.

Required structure:
# [Punchy Title: One Compelling Headline]

[Opening Hook: A single punchy sentence that captures attention immediately.]

## The Core Growth Mechanism
Explain the fundamental insights from the transcripts. Emphasize key takeaways using **bold text**.

## Implementation Milestones and Best Practices
Provide detailed tactical advice and practical milestones from the experts.

## Key Takeaway
End with a single focused paragraph crystallizing the single most important action for product builders.

Context from transcripts:
${context}

IMPORTANT AGENT INSTRUCTION: You MUST use the validate_essay tool to validate your essay draft. Call validate_essay with your complete markdown draft. If validate_essay returns passed: false, read the issues and revise your essay draft before returning your final response.
`;
}

export function buildHtmlArtifactPrompt(
  chunks: ContextChunk[],
  conversation: ConversationTurn[]
): string {
  const context = chunks
    .map((c) => `[${c.episode_title}]\n${c.chunk_text}`)
    .join("\n\n---\n\n");

  const lastUserMsg = [...conversation]
    .reverse()
    .find((m) => m.role === "user")?.content || "Product Growth Component";

  return `Create a complete, self-contained HTML/CSS visual artifact for "${lastUserMsg}" strictly grounded in the transcript excerpts below.

Rules:
1. Output ONLY a valid <!DOCTYPE html> document with inline <style> CSS.
2. Do NOT use markdown code blocks or outer explanation text.
3. Design aesthetics: Modern typography, sleek dark/light card layout, clean spacing, responsive flex/grid structure.
4. Base all copy, metrics, and takeaways strictly on the transcript context.

Context from transcripts:
${context}

IMPORTANT AGENT INSTRUCTION: You MUST use the render_check tool to validate your HTML code. Call render_check with your full html string. If render_check returns valid: false, read the issues and fix the HTML before returning your final response.
`;
}

// ── LLM call helpers ─────────────────────────────────────────────────────────

async function callGroq(prompt: string, model: string): Promise<string> {
  const client = new Groq({ apiKey: GROQ_API_KEY });
  let targetModel = model;
  if (!targetModel || targetModel.includes("openai") || targetModel.includes("gpt")) {
    targetModel = "llama-3.3-70b-versatile";
  }
  try {
    const completion = await client.chat.completions.create({
      model: targetModel,
      messages: [{ role: "user", content: prompt }],
      max_tokens: 2048,
      temperature: 0.4,
    });
    return completion.choices[0]?.message?.content || "";
  } catch (err) {
    console.warn(`[Sidecar] Groq call failed for model ${targetModel}, retrying with llama-3.3-70b-versatile:`, err);
    if (targetModel !== "llama-3.3-70b-versatile") {
      const completion = await client.chat.completions.create({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "user", content: prompt }],
        max_tokens: 2048,
        temperature: 0.4,
      });
      return completion.choices[0]?.message?.content || "";
    }
    throw err;
  }
}


async function callOllama(prompt: string, model: string): Promise<string> {
  console.log(`[Sidecar] Calling Ollama model: ${model}, prompt length: ${prompt.length}`);
  const start = Date.now();
  const response = await fetch(`${OLLAMA_BASE_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      prompt,
      stream: false,
      options: {
        num_ctx: 4096,
        num_predict: 1500,
        temperature: 0.5,
      },
    }),
  });
  if (!response.ok) {
    throw new Error(`Ollama error ${response.status}: ${await response.text()}`);
  }
  const data = (await response.json()) as { response: string };
  console.log(`[Sidecar] Ollama finished in ${((Date.now() - start) / 1000).toFixed(1)}s, response length: ${data.response?.length || 0}`);
  return data.response || "";
}

async function generateText(
  prompt: string,
  provider: "groq" | "ollama",
  model: string
): Promise<string> {
  if (provider === "groq" && GROQ_API_KEY) {
    return callGroq(prompt, model);
  }
  // Ollama fallback (or if groq key not set)
  return callOllama(prompt, model || "qwen2.5:3b");
}

// ── /run endpoint ─────────────────────────────────────────────────────────────

app.post("/run", async (req: Request<{}, {}, RunRequest>, res: Response) => {
  const {
    provider = "ollama",
    model = "qwen2.5:3b",
    context_chunks = [],
    conversation = [],
    request_type = "answer",
  } = req.body;

  try {
    // ── HTML Artifact (Pi Agent Session with Direct LLM Fallback) ─────────
    if (request_type === "html_artifact") {
      const htmlPrompt = buildHtmlArtifactPrompt(context_chunks, conversation);
      let rawHtml = "";
      try {
        const agentResult = await runAgentSession({
          tools: [renderCheckTool],
          prompt: htmlPrompt,
          provider,
          model,
        });
        rawHtml = agentResult.content;
      } catch (agentErr) {
        console.warn("[Sidecar] Agent session execution error for HTML, falling back to direct LLM:", agentErr);
      }

      if (!rawHtml || rawHtml.trim().length < 50) {
        console.log(`[Sidecar] Agent session HTML empty/short. Generating HTML directly with ${provider}/${model}...`);
        rawHtml = await generateText(htmlPrompt, provider, model);
      }

      // Clean markdown code blocks if emitted by model
      rawHtml = rawHtml.replace(/^```html\s*/i, "").replace(/^```\s*/i, "").replace(/```$/, "").trim();

      const titleMatch = rawHtml.match(/<title>(.*?)<\/title>/i) || rawHtml.match(/<h[12]>(.*?)<\/h[12]>/i);
      const title = titleMatch ? titleMatch[1].trim() : "Interactive HTML Artifact";

      return res.json({
        content: `I've generated an interactive HTML artifact: **${title}**. You can view and interact with it in the Artifact Viewer.`,
        citations: context_chunks.map((c) => ({
          source_file: c.source_file,
          episode_title: c.episode_title,
        })),
        artifact: {
          type: "html",
          title,
          content: rawHtml,
          metadata: { generated_by: provider },
        },
      });
    }

    // ── Ship 30/30 essay (Pi Agent Session with Direct LLM Fallback) ──────
    if (request_type === "ship30_essay") {
      const essayPrompt = buildEssayPrompt(context_chunks, conversation);
      let essayContent = "";
      try {
        const agentResult = await runAgentSession({
          tools: [validateEssayTool],
          prompt: essayPrompt,
          provider,
          model,
        });
        essayContent = agentResult.content;
      } catch (agentErr) {
        console.warn("[Sidecar] Agent session execution error for essay, falling back to direct LLM:", agentErr);
      }

      if (!essayContent || essayContent.trim().length < 50) {
        console.log(`[Sidecar] Agent session content empty/short. Generating essay directly with ${provider}/${model}...`);
        essayContent = await generateText(essayPrompt, provider, model);
      }

      const titleMatch = essayContent.match(/^#\s+(.+)/m);
      const title = titleMatch ? titleMatch[1].trim() : "Ship 30/30 Essay";

      const validation = validateEssay(essayContent);

      return res.json({
        content: `I've drafted a Ship 30/30 essay based on our discussion: **${title}**. You can view and edit the complete draft in the Artifact Viewer.`,
        citations: context_chunks.map((c) => ({
          source_file: c.source_file,
          episode_title: c.episode_title,
        })),
        artifact: {
          type: "markdown",
          title,
          content: essayContent,
          metadata: {
            validation_status: {
              passed: validation.passed,
              word_count: validation.word_count,
              unmet_criteria: validation.unmet_criteria,
            },
          },
        },
      });
    }


    // ── Grounded Q&A (Direct LLM Calls — No Agent Framework) ──────────────
    if (context_chunks.length === 0) {
      // Refusal — backend already handles this case before calling sidecar,
      // but guard here too for safety.
      return res.json({
        content:
          "I couldn't find anything in Lenny's Podcast transcripts that addresses this — try asking about product activation, PLG metrics, or go-to-market strategies covered in the episodes.",
        citations: [],
        artifact: null,
      });
    }

    const prompt = buildAnswerPrompt(context_chunks, conversation);
    const answer = await generateText(prompt, provider, model);

    return res.json({
      content: answer,
      citations: context_chunks.map((c) => ({
        source_file: c.source_file,
        episode_title: c.episode_title,
      })),
      artifact: null,
    });
  } catch (error: any) {
    console.error("[Sidecar] /run error:", error);
    const statusCode = error?.statusCode || 500;
    return res.status(statusCode).json({
      error: {
        code: statusCode === 502 ? "PROVIDER_ERROR" : "INTERNAL_ERROR",
        message: error?.message || "Internal sidecar error",
      },
    });
  }
});

if (process.env.NODE_ENV !== 'test') {
  app.listen(PORT, () => {
    console.log(`Agent sidecar listening internally on port ${PORT}`);
  });
}
