import { describe, it, expect } from "vitest";
import { validateEssayTool } from "../../src/tools/validate_essay_tool.js";

describe("validateEssayTool definition and execution", () => {
  const generateWords = (count: number) => Array(count).fill("growth").join(" ");

  it("defines correct tool name and parameter schema", () => {
    expect(validateEssayTool.name).toBe("validate_essay");
    expect(validateEssayTool.description).toContain("Ship 30/30");
  });

  it("returns passed=true for valid essay draft", async () => {
    const validContent = `
# How to Master Product Activation

${generateWords(300)}

## Finding the AHA Moment

${generateWords(400)}
This is **critical for long term retention** across your cohort.

## Structuring the Milestone Metrics

${generateWords(450)}

### Core Takeaway
The key takeaway is that activation must be tied directly to value delivery, not just feature discovery.
    `.trim();

    const result = await validateEssayTool.execute("call_1", { draft: validContent }, undefined, undefined, undefined);
    expect(result.details.passed).toBe(true);
    expect(result.details.issues).toHaveLength(0);
    expect(result.content[0].type).toBe("text");
    const json = JSON.parse((result.content[0] as any).text);
    expect(json.passed).toBe(true);
    expect(json.word_count).toBeGreaterThanOrEqual(1063);
  });

  it("returns passed=false with issues for failing draft", async () => {
    const shortContent = `
# Activation Overview

${generateWords(100)}

## Key Steps
**Activation steps** must be tested.

## Metrics
${generateWords(40)}

Takeaway: Measure early and iterate often.
    `.trim();

    const result = await validateEssayTool.execute("call_2", { draft: shortContent }, undefined, undefined, undefined);
    expect(result.details.passed).toBe(false);
    expect(result.details.issues.length).toBeGreaterThan(0);
    const json = JSON.parse((result.content[0] as any).text);
    expect(json.passed).toBe(false);
  });
});
