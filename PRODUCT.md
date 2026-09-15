# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vite + React 18 + Tailwind CSS 3 + TypeScript (Frontend), FastAPI / Python (Backend), Node / TypeScript (Agent Sidecar)

## Users

Product managers, growth operators, and founder-writers looking to turn verified transcript knowledge into publishable writing, essays, and visual artifacts.

## Product Purpose

The Lenny Growth Assistant provides grounded, evidence-backed answers, Ship 30/30 essays, and interactive HTML artifacts derived from transcript data. Success means turning dense knowledge into high-craft, publishable material with clear source citations.

## Positioning

Grounded, citation-first knowledge tool combining deterministic LLM Q&A with Pi Agent tool-calling validation for essays and HTML artifacts.

## Operating Context

Single-page application with a dual-pane operator layout: Sidebar for session management, Chat pane for interaction, and a side-by-side Artifact Viewer for long-form reading and HTML renders.

## Capabilities and Constraints

- Grounded Q&A with direct citation chips
- Ship 30/30 essay generation with structural validation (word count 1063–1438, subheadings, bold emphasis, takeaway)
- Interactive HTML artifact generation validated via render-check tools
- Strict evidence-over-confidence requirement: no uncited claims or decorative fluff

## Brand Commitments

- Visual Identity: "Operator's workbench" — precise, editorial, trustworthy
- Color Palette: Ink Navy (#1C2E48 primary), Signal Teal (#1E7F73 accent), Paper Neutral (#FAF9F7 background)
- Typography: IBM Plex Sans (UI Chrome), Source Serif 4 (Long-form reading), IBM Plex Mono (Code & Citations)

## Evidence on Hand

- `DESIGN.md`: Complete design system tokens, components, and layout specs
- `specs/001-pi-agent-tool-calling/spec.md`: Feature specifications & acceptance criteria
- `frontend/package.json`: Component library and frontend stack definition

## Product Principles

1. Evidence over confidence — citations and provider states are always visible.
2. Reading comes first — long-form content receives serif-quality typography and 65ch line lengths.
3. One accent, spent deliberately — Signal Teal marks citations and primary actions exclusively.
4. Calm failure — errors and empty states explain clearly without apologetic or vague spinners.
5. Restraint in motion — user-triggered micro-interactions only; no distracting entrance animations.

## Accessibility & Inclusion

Targeting WCAG AA compliance with high-contrast text ratios, explicit focus rings, keyboard navigation, and `prefers-reduced-motion` support.
