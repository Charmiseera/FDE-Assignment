import { defineTool, type ToolDefinition } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";

export interface HtmlCheckResult {
  valid: boolean;
  issues: string[];
}

export function checkHtmlStructure(html: string): HtmlCheckResult {
  const issues: string[] = [];
  const trimmed = html.trim();

  // Check DOCTYPE
  if (!/^<!DOCTYPE\s+html>/i.test(trimmed)) {
    issues.push("HTML document must start with <!DOCTYPE html>");
  }

  // Check <body> tag
  if (!/<body[\s>]/i.test(trimmed) || !/<\/body>/i.test(trimmed)) {
    issues.push("HTML document must contain <body> and </body> tags");
  }

  // Check <title> tag
  if (!/<title>.*?<\/title>/i.test(trimmed)) {
    issues.push("HTML document must contain a <title> element");
  }

  // Tag count balance check helper
  const checkBalancedTag = (tagName: string) => {
    const openRegex = new RegExp(`<${tagName}[\\s>]`, "gi");
    const closeRegex = new RegExp(`</${tagName}>`, "gi");
    const openCount = (trimmed.match(openRegex) || []).length;
    const closeCount = (trimmed.match(closeRegex) || []).length;
    if (openCount !== closeCount) {
      issues.push(
        `Unclosed tag mismatch for <${tagName}>: ${openCount} opening vs ${closeCount} closing tags`
      );
    }
  };

  checkBalancedTag("div");
  checkBalancedTag("section");
  checkBalancedTag("main");

  return {
    valid: issues.length === 0,
    issues,
  };
}

export const renderCheckTool: ToolDefinition = defineTool({
  name: "render_check",
  label: "Render Check",
  description:
    "Validates the structure of a generated HTML visual artifact (DOCTYPE declaration, <body>, <title>, and balanced container tags). Returns valid status and structural issues.",
  parameters: Type.Object({
    html: Type.String({ description: "The complete HTML string to validate" }),
  }),
  execute: async (_toolCallId, params: { html: string }) => {
    try {
      const result = checkHtmlStructure(params.html);

      console.log(`[Pi:tool_call] render_check html_length=${params.html.length}`);
      console.log(`[Pi:tool_result] render_check valid=${result.valid}`);

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        details: result,
      };
    } catch (err: any) {
      const errorOutput: HtmlCheckResult = {
        valid: false,
        issues: [`Tool execution error: ${err?.message || err}`],
      };
      return {
        content: [{ type: "text", text: JSON.stringify(errorOutput) }],
        details: errorOutput,
      };
    }
  },
});
