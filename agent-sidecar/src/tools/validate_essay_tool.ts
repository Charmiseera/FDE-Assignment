import { defineTool, type ToolDefinition } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { validateEssay } from "./generate_ship30_essay.js";

export const validateEssayTool: ToolDefinition = defineTool({
  name: "validate_essay",
  label: "Validate Essay",
  description:
    "Validates structural constraints of a Ship 30/30 essay draft (word count 1,063–1,438, >=2 subheadings, bold emphasis, explicit takeaway section). Returns passed status and unmet criteria.",
  parameters: Type.Object({
    draft: Type.String({ description: "The complete markdown draft of the essay to validate" }),
  }),
  execute: async (_toolCallId, params: { draft: string }) => {
    try {
      const result = validateEssay(params.draft);
      const output = {
        passed: result.passed,
        word_count: result.word_count,
        subheadings_count: result.subheadings_count,
        has_bold: result.has_bold,
        has_takeaway: result.has_takeaway,
        issues: result.unmet_criteria,
      };

      console.log(`[Pi:tool_call] validate_essay word_count=${result.word_count}`);
      console.log(`[Pi:tool_result] validate_essay passed=${result.passed}`);

      return {
        content: [{ type: "text", text: JSON.stringify(output, null, 2) }],
        details: output,
      };
    } catch (err: any) {
      const errorOutput = {
        passed: false,
        word_count: 0,
        issues: [`Tool execution error: ${err?.message || err}`],
      };
      return {
        content: [{ type: "text", text: JSON.stringify(errorOutput) }],
        details: errorOutput,
      };
    }
  },
});
