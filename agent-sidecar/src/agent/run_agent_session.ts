import {
  createAgentSession,
  AuthStorage,
  ModelRegistry,
  SessionManager,
  type ToolDefinition,
  type AgentSessionEvent,
} from "@mariozechner/pi-coding-agent";

export interface LoggedToolCall {
  toolName: string;
  input: Record<string, any>;
  output: any;
}

export interface AgentRunOptions {
  tools: ToolDefinition[];
  prompt: string;
  provider?: string;
  model?: string;
}

export interface AgentRunResult {
  content: string;
  toolCalls: LoggedToolCall[];
  attemptCount: number;
}

export async function runAgentSession(options: AgentRunOptions): Promise<AgentRunResult> {
  const provider = options.provider || "groq";
  const modelId = options.model || "openai/gpt-oss-120b";

  const authStorage = AuthStorage.inMemory();
  const apiKey = process.env.GROQ_API_KEY;
  if (apiKey) {
    authStorage.setRuntimeApiKey(provider, apiKey);
  }

  const modelRegistry = ModelRegistry.inMemory(authStorage);
  const model = modelRegistry.find(provider, modelId);

  const toolCalls: LoggedToolCall[] = [];
  let attemptCount = 0;

  try {
    const { session } = await createAgentSession({
      model,
      authStorage,
      modelRegistry,
      customTools: options.tools,
      noTools: "builtin",
      sessionManager: SessionManager.inMemory(),
    });

    const unsubscribe = session.subscribe((event: AgentSessionEvent) => {
      if (event.type === "tool_execution_start") {
        const toolName = (event as any).toolName || (event as any).name || "unknown";
        console.log(`[Pi:tool_call] ${toolName}`, (event as any).args || (event as any).input || {});
      } else if (event.type === "tool_execution_end") {
        const toolName = (event as any).toolName || (event as any).name || "unknown";
        const result = (event as any).result || (event as any).output;
        console.log(`[Pi:tool_result] ${toolName}`, result);
        toolCalls.push({
          toolName,
          input: (event as any).args || (event as any).input || {},
          output: result,
        });
      } else if (event.type === "turn_end") {
        attemptCount++;
        console.log(`[Pi:session] Turn ${attemptCount} complete`);
        if (attemptCount >= 2 && session.isStreaming) {
          console.log(`[Pi:session] Safety cap reached (2 attempts max). Aborting session.`);
          void session.abort();
        }
      }
    });

    try {
      console.log(`[Pi:session] Starting prompt for model ${provider}/${modelId}`);
      await session.prompt(options.prompt);

      // Extract text content from the last assistant message in session
      let content = "";
      const msgs = (session as any).agent?.state?.messages || (session as any).messages || [];
      for (let i = msgs.length - 1; i >= 0; i--) {
        const msg = msgs[i];
        if (msg.role === "assistant") {
          if (typeof msg.content === "string") {
            content = msg.content;
          } else if (Array.isArray(msg.content)) {
            content = msg.content
              .filter((c: any) => c.type === "text")
              .map((c: any) => c.text)
              .join("");
          }
          if (content.trim()) break;
        }
      }

      return {
        content,
        toolCalls,
        attemptCount: Math.max(attemptCount, 1),
      };
    } finally {
      unsubscribe();
    }
  } catch (error: any) {
    console.error("[Sidecar] Pi agent session error:", error);
    const err = new Error(`Pi session execution failed: ${error?.message || error}`);
    (err as any).statusCode = 502;
    throw err;
  }
}
