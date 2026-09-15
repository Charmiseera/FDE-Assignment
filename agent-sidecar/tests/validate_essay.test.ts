import { describe, it, expect } from "vitest";
import { validateEssay } from "../src/tools/generate_ship30_essay.js";

describe("validateEssay structural checks", () => {
  const generateWords = (count: number) =>
    Array(count).fill("growth").join(" ");

  it("passes for a valid Ship 30/30 essay within word range with required elements", () => {
    // 1,150 words (in [1063, 1438]), 2 subheadings, bold text, takeaway
    const content = `
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

    const result = validateEssay(content);
    expect(result.passed).toBe(true);
    expect(result.unmet_criteria).toHaveLength(0);
    expect(result.word_count).toBeGreaterThanOrEqual(1063);
    expect(result.word_count).toBeLessThanOrEqual(1438);
    expect(result.subheadings_count).toBeGreaterThanOrEqual(2);
    expect(result.has_bold).toBe(true);
    expect(result.has_takeaway).toBe(true);
  });

  it("fails when word count is too short", () => {
    // Only ~150 words
    const shortContent = `
# Activation Overview

${generateWords(100)}

## Key Steps
**Activation steps** must be tested.

## Metrics
${generateWords(40)}

Takeaway: Measure early and iterate often.
    `.trim();

    const result = validateEssay(shortContent);
    expect(result.passed).toBe(false);
    expect(result.unmet_criteria.some((c) => c.includes("below minimum target"))).toBe(true);
  });

  it("fails when subheadings are missing", () => {
    // 1,150 words, has bold and takeaway, but ZERO subheadings
    const noHeadingsContent = `
# Activation Without Structure

${generateWords(550)}
We noticed that **early friction causes steep dropoff** among self-serve users.
${generateWords(600)}

Takeaway: Never ignore onboarding telemetry.
    `.trim();

    const result = validateEssay(noHeadingsContent);
    expect(result.passed).toBe(false);
    expect(result.unmet_criteria.some((c) => c.includes("subheadings"))).toBe(true);
  });
});
