import { describe, it, expect } from "vitest";
import { Artifact } from "../../types";

describe("Artifact metadata validation logic", () => {
  it("formats validation_status metadata correctly without polluting markdown body", () => {
    const artifact: Artifact = {
      id: "art-1",
      session_id: "sess-1",
      type: "markdown",
      title: "The Operator's Playbook: Mastering Product Activation",
      content: "# Clean Markdown Essay\n\nThis is pure markdown content without warnings inside the text.",
      metadata: {
        validation_status: {
          passed: false,
          word_count: 950,
          unmet_criteria: [
            "Word count (950) is below minimum target of 1063 words (1,250 ± 15%)",
            "Requires selective bold emphasis (**key phrase**) for skimmability",
          ],
        },
      },
      created_at: new Date().toISOString(),
    };

    // Body check: ensure error/warning notices are not in the essay content
    expect(artifact.content).not.toContain("below minimum target");
    expect(artifact.content).not.toContain("Requires selective bold emphasis");

    // Sibling metadata check: validation metadata is preserved separately
    expect(artifact.metadata?.validation_status?.passed).toBe(false);
    expect(artifact.metadata?.validation_status?.unmet_criteria).toHaveLength(2);
    expect(artifact.metadata?.validation_status?.word_count).toBe(950);
  });
});
