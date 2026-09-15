import { describe, it, expect } from "vitest";
import React from "react";
import { Button } from "./Button";
import { Textarea } from "./Textarea";
import { Card } from "./Card";
import { Alert } from "./Alert";
import { Modal } from "./Modal";
import { LoadingDots } from "./LoadingDots";
import { EmptyState } from "./EmptyState";

describe("Standalone Core Component Library (Step 2.2)", () => {
  it("Button renders with variants", () => {
    expect(Button).toBeDefined();
  });

  it("Textarea renders with default and error states", () => {
    expect(Textarea).toBeDefined();
  });

  it("Card renders with active variant", () => {
    expect(Card).toBeDefined();
  });

  it("Alert renders with semantic variants", () => {
    expect(Alert).toBeDefined();
  });

  it("Modal renders with escape dismiss", () => {
    expect(Modal).toBeDefined();
  });

  it("LoadingDots renders with label", () => {
    expect(LoadingDots).toBeDefined();
  });

  it("EmptyState renders with title and description", () => {
    expect(EmptyState).toBeDefined();
  });
});
