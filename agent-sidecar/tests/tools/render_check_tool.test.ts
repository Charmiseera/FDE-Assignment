import { describe, it, expect } from "vitest";
import { renderCheckTool, checkHtmlStructure } from "../../src/tools/render_check_tool.js";

describe("renderCheckTool definition and HTML structural checks", () => {
  it("defines correct tool name and label", () => {
    expect(renderCheckTool.name).toBe("render_check");
    expect(renderCheckTool.label).toBe("Render Check");
  });

  it("passes for valid HTML5 document", () => {
    const validHtml = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Growth Dashboard</title>
  <style>body { font-family: sans-serif; }</style>
</head>
<body>
  <main>
    <section>
      <div><h1>Retention Metrics</h1></div>
    </section>
  </main>
</body>
</html>
    `.trim();

    const result = checkHtmlStructure(validHtml);
    expect(result.valid).toBe(true);
    expect(result.issues).toHaveLength(0);
  });

  it("fails when <!DOCTYPE html> is missing", () => {
    const html = `
<html>
<head><title>Dashboard</title></head>
<body><div>Hello</div></body>
</html>
    `.trim();

    const result = checkHtmlStructure(html);
    expect(result.valid).toBe(false);
    expect(result.issues.some((i) => i.includes("<!DOCTYPE html>"))).toBe(true);
  });

  it("fails when container tags are unbalanced", () => {
    const html = `
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
  <div>
    <div>Unclosed inner div
  </div>
</body>
</html>
    `.trim();

    const result = checkHtmlStructure(html);
    expect(result.valid).toBe(false);
    expect(result.issues.some((i) => i.includes("Unclosed tag mismatch"))).toBe(true);
  });

  it("returns valid=true via tool execute() for clean HTML", async () => {
    const validHtml = `<!DOCTYPE html><html><head><title>Test</title></head><body><div>Ok</div></body></html>`;
    const toolResult = await renderCheckTool.execute("call_1", { html: validHtml }, undefined, undefined, undefined);
    expect(toolResult.details.valid).toBe(true);
    expect(toolResult.content[0].type).toBe("text");
  });
});
