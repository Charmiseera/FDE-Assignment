# FRONTEND_GUIDELINES.md — The Lenny Growth Assistant

> **Relationship to other docs:** This is the visual/component design system. `design.md` (the assignment's required deliverable) should cover UX principles, information architecture, and state rationale — this file is the token- and component-level implementation of those decisions, referenced from `design.md` rather than duplicating it.

**App Context**
- **Style:** "Operator's workbench" — precise, editorial, trustworthy. Not a generic SaaS dashboard and not a marketing site. The product's real job is turning verified transcript knowledge into publishable writing, so the visual language borrows from research/writing tools (clear hierarchy, generous reading width, restrained chrome) rather than consumer-app polish.
- **Brand colors:** None supplied by the client brief — defined below as a deliberate choice, not a default.
- **Target audience:** Product managers and founder-writers (see PRD personas) — comfortable with software, impatient with decoration, reading dense text for extended stretches.

---

## Design Principles

1. **Evidence over confidence.** Citations, sources, and provider state are always visible, never hidden behind a tooltip or footnote — this is a grounded tool, and the UI should look like it knows the difference between "answered" and "answered with backup."
2. **Reading comes first.** Long-form content (answers, essays, artifacts) gets generous line length and serif-quality reading treatment; UI chrome stays quiet around it.
3. **One accent, spent deliberately.** A single accent color marks the things that matter (citations, active state, primary actions) — nothing else competes for attention.
4. **Calm failure.** Errors and empty states explain what happened and what to do next, in plain language — no apologetic tone, no vague spinners forever.
5. **Restraint in motion.** Only user-triggered transitions; no decorative entrance animations.

---

## Design Tokens

### Color Palette

**Primary — "Ink" (navy).** Used for primary actions, active navigation state, and headings. Chosen over a generic SaaS blue/purple to read as serious and editorial rather than "AI startup."

| Token | Hex | Usage |
|---|---|---|
| ink-50 | #EEF1F6 | subtle backgrounds, selected-row tint |
| ink-100 | #D7DEEA | hover backgrounds on light surfaces |
| ink-200 | #B0BFD6 | borders on ink-colored elements |
| ink-300 | #8AA0C1 | disabled ink-button text |
| ink-400 | #5C7BA5 | secondary icons |
| ink-500 | #34547E | — reserved, rarely used directly |
| ink-600 | #263F60 | primary button hover |
| ink-700 | #1C2E48 | **primary button background**, headings |
| ink-800 | #141F32 | primary button active/pressed |
| ink-900 | #0D141F | high-emphasis text on light backgrounds |

**Accent — "Signal Teal".** The one deliberate accent, per Design Principle 3. Used *only* for citations, links, and the active-session indicator — nowhere else, so it retains meaning.

| Token | Hex | Usage |
|---|---|---|
| signal-50 | #EAF6F4 | citation chip background |
| signal-100 | #C9EAE4 | citation chip hover |
| signal-500 | #1E7F73 | **citation chip text/border**, links, active-tab underline |
| signal-700 | #114D46 | pressed/active state of accent elements |

**Neutral — "Paper".** A warm-toned gray scale (not pure gray, not cream-orange cliché) for backgrounds, text, and structure.

| Token | Hex | Usage |
|---|---|---|
| paper-50 | #FAF9F7 | app background |
| paper-100 | #F2F0EC | card/panel background, sidebar background |
| paper-200 | #E4E1DA | borders, dividers |
| paper-300 | #CFCBC1 | disabled borders |
| paper-400 | #A7A295 | placeholder text |
| paper-500 | #7D786C | secondary/muted text |
| paper-600 | #5C584E | body text (secondary emphasis) |
| paper-700 | #423F38 | body text (primary) |
| paper-800 | #2A2824 | strong emphasis text |
| paper-900 | #171614 | rarely used — near-black, reserved for code blocks |

**Semantic colors** — deliberately distinct from the Signal Teal accent so status and "this is grounded" meaning never get confused.

| Purpose | Light (bg) | Base | Dark (text on light) |
|---|---|---|---|
| Success | #E7F3EA | #1F7A44 | #14532D |
| Warning | #FBF0DE | #B4791A | #7A5211 |
| Error | #F7E7E7 | #B23A3A | #7A2626 |
| Info | #E6EFF8 | #2C6FA8 | #1E4E77 |

### Typography

- **UI sans-serif:** IBM Plex Sans — chosen for its engineered, slightly technical character that fits an "operator tool" rather than a consumer app; used for all interface chrome, buttons, labels, navigation.
- **Long-form reading serif:** Source Serif 4 — used specifically for assistant answers, essays, and Markdown artifacts. This is a content-driven choice (Design Principle 2): the moment a user is reading grounded, substantial writing, the typography should feel like reading, not like software.
- **Monospace:** IBM Plex Mono — used narrowly for citation source filenames/episode IDs and raw artifact source view, where exact characters matter.

| Token | Size (rem) | Line height | Typical use |
|---|---|---|---|
| text-xs | 0.75rem | 1.4 | citation metadata, timestamps |
| text-sm | 0.875rem | 1.5 | UI labels, secondary text |
| text-base | 1rem | 1.6 | chat UI body text |
| text-lg | 1.125rem | 1.6 | section headers within chat |
| text-xl | 1.25rem | 1.4 | session title, modal headers |
| text-2xl | 1.5rem | 1.3 | page-level headers (rare — this is a single-page app) |
| text-3xl | 1.875rem | 1.25 | essay/artifact display title |
| text-4xl | 2.25rem | 1.2 | reserved, unused in MVP — no marketing hero exists |

Long-form reading content (essays, artifacts) uses `text-base`–`text-lg` in Source Serif 4 with a max reading width of **65ch**, per the skill guidance of keeping line length under 80 characters — this is the one place in the app where line-length discipline matters most.

Font weights: 400 (regular, body), 500 (medium, UI labels/buttons), 600 (semibold, headings/active nav), 700 (bold, used only for the essay skill's "selective bold emphasis" inside generated content — not used in UI chrome, keeping bold meaningful).

### Spacing Scale (Tailwind-compatible)

| Token | rem | px | Usage |
|---|---|---|---|
| space-0 | 0 | 0 | — |
| space-1 | 0.25rem | 4px | icon-to-label gaps |
| space-2 | 0.5rem | 8px | inline spacing, chip padding |
| space-3 | 0.75rem | 12px | input padding (vertical) |
| space-4 | 1rem | 16px | component padding (default) |
| space-5 | 1.25rem | 20px | card padding |
| space-6 | 1.5rem | 24px | section spacing within a panel |
| space-8 | 2rem | 32px | panel-to-panel gaps (chat ↔ artifact viewer) |
| space-10 | 2.5rem | 40px | — |
| space-12 | 3rem | 48px | major layout margins (desktop) |
| space-16 | 4rem | 64px | outer page margin on wide viewports |

### Border Radius

Deliberately *not* uniform across all components (a flagged generic-AI tell) — radius signals a component's role:

| Token | rem | Usage |
|---|---|---|
| radius-none | 0 | dividers, table cells |
| radius-sm | 0.25rem | citation chips, badges |
| radius-base | 0.375rem | buttons, inputs |
| radius-md | 0.5rem | cards, message bubbles |
| radius-lg | 0.75rem | modals, the artifact viewer panel |
| radius-xl | 1rem | reserved, unused in MVP |
| radius-full | 9999px | avatars (if added later), the provider status dot |

### Shadows

Used sparingly — only for elements that visually float above the page (modals, dropdowns), never applied decoratively to every card, per Design Principle 5.

| Token | Value |
|---|---|
| shadow-sm | 0 1px 2px rgba(23, 22, 20, 0.06) |
| shadow-base | 0 1px 3px rgba(23, 22, 20, 0.08), 0 1px 2px rgba(23, 22, 20, 0.04) |
| shadow-md | 0 4px 8px rgba(23, 22, 20, 0.10) |
| shadow-lg | 0 10px 20px rgba(23, 22, 20, 0.12) |
| shadow-xl | 0 20px 32px rgba(23, 22, 20, 0.14) |

---

## Layout System

- **Container max-width:** 1440px on desktop, full-bleed below that.
- **Columns:** two-region layout (Sidebar + Main), where Main splits into Chat and Artifact Viewer when an artifact is present — not a traditional 12-column marketing grid, since this is an app shell, not a content site.
- **Gutter:** `space-6` (24px) between Sidebar/Main and between Chat/Artifact Viewer.

### Breakpoints

| Name | Min-width | Layout behavior |
|---|---|---|
| sm (mobile) | 0 | Single column, sidebar as drawer, artifact stacks below chat |
| md (tablet) | 768px | Sidebar as drawer, chat + artifact side-by-side if both active |
| lg (desktop) | 1024px | Sidebar persistent, chat + artifact side-by-side |
| xl (wide desktop) | 1440px | Same as lg, with wider reading max-width for artifacts (up to 65ch, not full panel width) |

### Common layout patterns

**App shell (desktop, lg+):**
```jsx
<div className="flex h-screen bg-paper-50">
  <aside className="w-64 shrink-0 bg-paper-100 border-r border-paper-200">{/* Sidebar */}</aside>
  <main className="flex flex-1 min-w-0">
    <section className="flex-1 min-w-0 flex flex-col">{/* Chat */}</section>
    {hasArtifact && (
      <section className="w-[45%] shrink-0 border-l border-paper-200 bg-paper-50">{/* Artifact Viewer */}</section>
    )}
  </main>
</div>
```

**Centered long-form reading content (essay/artifact display):**
```jsx
<div className="mx-auto max-w-[65ch] px-6 py-8 font-serif text-paper-800">
  {/* essay content */}
</div>
```

**Mobile stack (sm):**
```jsx
<div className="flex flex-col h-screen bg-paper-50">
  <header className="flex items-center justify-between p-4 border-b border-paper-200">{/* menu + provider badge */}</header>
  <section className="flex-1 overflow-y-auto">{/* Chat */}</section>
  {hasArtifact && <section className="border-t border-paper-200">{/* Artifact Viewer, inline below */}</section>}
</div>
```

---

## Component Library

### Buttons

Variants: Primary, Secondary, Outline, Ghost, Danger. Sizes: sm, md, lg.

```jsx
// Primary — main actions (Send, Generate Essay)
<button className="inline-flex items-center gap-2 rounded-base bg-ink-700 px-4 py-2 text-sm font-medium text-paper-50
  hover:bg-ink-600 active:bg-ink-800
  disabled:bg-paper-300 disabled:text-paper-500 disabled:cursor-not-allowed
  focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-700">
  Send
</button>

// Secondary — lower-emphasis confirm actions
<button className="inline-flex items-center gap-2 rounded-base bg-paper-100 px-4 py-2 text-sm font-medium text-ink-700
  hover:bg-paper-200 active:bg-paper-300
  focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-700">
  Save
</button>

// Outline — secondary emphasis with visible boundary (New Chat)
<button className="inline-flex items-center gap-2 rounded-base border border-paper-300 bg-transparent px-4 py-2 text-sm font-medium text-paper-700
  hover:bg-paper-100
  focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-700">
  New Chat
</button>

// Ghost — tertiary, icon-only or inline actions (toggle raw/rendered view)
<button className="inline-flex items-center gap-2 rounded-base px-3 py-1.5 text-sm text-paper-600
  hover:bg-paper-100 hover:text-paper-800
  focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-700">
  View source
</button>

// Danger — destructive actions (delete session)
<button className="inline-flex items-center gap-2 rounded-base bg-transparent px-4 py-2 text-sm font-medium text-[#B23A3A]
  hover:bg-[#F7E7E7]
  focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B23A3A]">
  Delete session
</button>
```

Sizes (apply to any variant): `sm` → `px-3 py-1.5 text-xs`; `md` (default, shown above) → `px-4 py-2 text-sm`; `lg` → `px-5 py-2.5 text-base`.

Loading state: replace label with a small inline spinner + "Sending…", keep button disabled, preserve button width (set a `min-w`) so the layout doesn't jump.

**Accessibility:** every button has a visible 2px focus outline (`focus-visible:outline`), never `outline-none` without a replacement; icon-only buttons require `aria-label`.

### Input Fields

Variants: Text, Textarea (the chat input is a textarea, not a single-line input, since messages can be long).

```jsx
// Default textarea (chat input)
<textarea
  className="w-full resize-none rounded-base border border-paper-300 bg-paper-50 px-4 py-3 text-base text-paper-800
    placeholder:text-paper-400
    focus:border-ink-600 focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-ink-200
    disabled:bg-paper-100 disabled:text-paper-400 disabled:cursor-not-allowed"
  placeholder="Ask a product or growth question…"
/>

// Error state
<textarea className="w-full resize-none rounded-base border border-[#B23A3A] bg-[#F7E7E7]/40 px-4 py-3 text-base text-paper-800
  focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#B23A3A]" />
<p className="mt-1 text-xs text-[#7A2626]">Message can't be empty.</p>

// Disabled (provider unavailable)
<textarea disabled className="w-full resize-none rounded-base border border-paper-200 bg-paper-100 px-4 py-3 text-base text-paper-400 cursor-not-allowed"
  placeholder="Provider unavailable — check configuration" />
```

**Accessibility:** every input has a visually-present or `sr-only` label tied via `htmlFor`/`id`; error text is linked via `aria-describedby`.

### Cards

Used for session list items and artifact history entries — not for generic content boxing (avoiding the "everything is a rounded card" default).

```jsx
// Default session card
<div className="rounded-md border border-paper-200 bg-paper-50 p-4 hover:bg-paper-100 cursor-pointer">
  <p className="text-sm font-medium text-paper-800 truncate">How do PLG companies define activation?</p>
  <p className="mt-1 text-xs text-paper-500">2 hours ago</p>
</div>

// Active/selected session card
<div className="rounded-md border border-signal-500 bg-signal-50 p-4">
  <p className="text-sm font-medium text-ink-800 truncate">How do PLG companies define activation?</p>
  <p className="mt-1 text-xs text-signal-700">2 hours ago</p>
</div>
```

No shadow on cards by default (Design Principle 5) — differentiation comes from border/background, not elevation.

### Modals

Used sparingly — provider info panel, delete-confirmation.

```jsx
<div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40" role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div className="w-full max-w-md rounded-lg bg-paper-50 p-6 shadow-lg
    animate-[fadeSlideUp_180ms_ease-out]">
    <h2 id="modal-title" className="text-lg font-semibold text-ink-800">Active provider</h2>
    {/* content */}
  </div>
</div>
```

- **Animation:** fade + 8px slide-up, 180ms ease-out — one deliberate entrance, not per-element staggering.
- **Close behavior:** Escape key, click on overlay, or explicit close button — all three, since any single method alone frustrates some users.
- **Focus trap:** focus moves to the modal on open, is trapped within it (Tab cycles internal elements only), and returns to the triggering element on close.

### Alerts / Toasts

```jsx
// Error alert (inline, e.g. failed message send)
<div className="flex items-start gap-3 rounded-base border border-[#B23A3A]/30 bg-[#F7E7E7] p-3 text-sm text-[#7A2626]" role="alert">
  <AlertCircleIcon className="h-4 w-4 shrink-0 mt-0.5" />
  <div>
    <p className="font-medium">The assistant didn't respond in time.</p>
    <button className="mt-1 text-xs font-medium underline underline-offset-2">Try again</button>
  </div>
</div>

// Info banner (connection status)
<div className="flex items-center gap-2 rounded-base border border-[#2C6FA8]/30 bg-[#E6EFF8] px-3 py-2 text-sm text-[#1E4E77]" role="status">
  <InfoIcon className="h-4 w-4" /> Reconnecting to backend…
</div>
```

Success/Warning follow the same structure with their respective semantic tokens. Dismissible variants add a ghost close button (`×`, `aria-label="Dismiss"`) in the top-right of the alert.

### Navigation

- **Header:** minimal — app name (left), provider badge (right). No marketing nav, since there's nothing to navigate to outside the app shell.
- **Sidebar:** session list, "New Chat" as an Outline button pinned at top, scrollable list below.
- **Mobile menu:** sidebar becomes a slide-over drawer triggered by a hamburger icon in the header; overlay dims the rest of the app.
- **Active states:** current session uses the Signal Teal card treatment above; no other nav has "active" states in this single-page app.

### Forms

The only real form in this app is the chat input itself (no multi-field forms, no registration). Validation messaging follows the Input Fields error-state pattern above. No multi-step form patterns apply.

### Loading States

```jsx
// Streaming response indicator (preferred over a spinner — Design Principle 4/5)
<div className="flex gap-1 px-4 py-3">
  <span className="h-1.5 w-1.5 rounded-full bg-paper-400 animate-bounce [animation-delay:-0.3s]" />
  <span className="h-1.5 w-1.5 rounded-full bg-paper-400 animate-bounce [animation-delay:-0.15s]" />
  <span className="h-1.5 w-1.5 rounded-full bg-paper-400 animate-bounce" />
</div>

// Skeleton (session list, initial load only)
<div className="space-y-2 p-2">
  {[1,2,3].map(i => <div key={i} className="h-14 rounded-md bg-paper-100 animate-pulse" />)}
</div>
```

No progress bars in this app — no operation has a meaningfully measurable percentage-complete state.

### Empty States

```jsx
// No sessions yet
<div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
  <MessageSquareIcon className="h-8 w-8 text-paper-400" />
  <p className="text-sm text-paper-600">No conversations yet.</p>
  <button className="rounded-base bg-ink-700 px-4 py-2 text-sm font-medium text-paper-50 hover:bg-ink-600">Start a new chat</button>
</div>

// No grounding found (in-chat, not a page-level empty state)
<div className="rounded-md border border-paper-200 bg-paper-100 p-4 text-sm text-paper-600">
  Nothing in the transcripts addresses this directly. Try asking about onboarding, pricing, or activation instead.
</div>
```

---

## Accessibility Guidelines

- **WCAG target:** AA.
- **Color contrast:** minimum 4.5:1 for body text; all token pairs above (e.g., `paper-700` text on `paper-50` background) meet this — verify any new pairing with a contrast checker before shipping it.
- **Keyboard navigation:** every interactive element reachable via Tab in a logical order; chat input focused by default on load; Escape closes modals/drawers.
- **Screen reader considerations:** streaming assistant responses use `aria-live="polite"` on the message container so new content is announced without interrupting; citation chips have accessible text (not just an icon).
- **Focus indicators:** visible 2px outline (`focus-visible:outline-2`) on every interactive element — never removed without a replacement.
- **Form accessibility:** labels tied to inputs via `htmlFor`; error messages linked via `aria-describedby`; the chat textarea has an `sr-only` label even though it's visually implied by placeholder text.
- **Semantic HTML:** `<button>` for actions, `<nav>` for the sidebar, `role="dialog"`/`aria-modal` for modals, `role="alert"` for errors, `role="status"` for non-urgent updates.

---

## Animation Guidelines

- **Default duration:** 200ms for micro-interactions (hover, focus); 180ms for modal/drawer entrances.
- **Easing:** `ease-out` for entrances, `ease-in-out` for toggles.
- **What to animate:** `transform` and `opacity` only, for performance — never animate `width`/`height`/`top` directly.
- **`prefers-reduced-motion`:** all non-essential transitions (drawer slide, modal fade) are disabled via `motion-reduce:transition-none`; the streaming-dots indicator is replaced with a static "Thinking…" label under reduced motion.
- **Loading animations:** the three-dot bounce (above) for active generation; skeleton pulse only on true first-load, not on every navigation.
- **Micro-interactions:** button hover/active state changes only — no decorative hover effects on cards beyond the background tint already specified.

---

## Icon System

- **Library:** Lucide React — consistent stroke-based icon set, fits the "precise workbench" tone better than filled/rounded icon sets.
- **Sizes:** 16px (inline with text, e.g. citation icons), 20px (buttons, list items), 24px (empty-state illustrations, header icons).
- **Stroke width:** 1.75 (Lucide default is 2 — slightly thinner reads more editorial, less consumer-app).
- **Color application:** icons inherit `currentColor` from their text context by default; status icons (alerts) use their semantic color token directly.

---

## State Indicators

Covered inline above (Loading States, Empty States, Alerts). Success confirmation (e.g., artifact saved) uses the success alert pattern with an auto-dismiss after 4 seconds, paired with a manual dismiss button for accessibility (auto-dismiss alone fails users who need more time to read it).

---

## Responsive Design

- **Approach:** mobile-first Tailwind classes (`base` styles for mobile, `md:`/`lg:` overrides for larger breakpoints).
- **Touch targets:** minimum 44×44px for all tappable elements on mobile, including icon-only buttons (pad the tap area even if the icon itself is 20px).
- **Responsive typography:** base sizes hold across breakpoints (this isn't a marketing site with a giant hero); only the reading max-width for artifacts adjusts (full-width on mobile within padding, 65ch cap from `md` up).
- **Responsive spacing:** panel gutters reduce from `space-8` (desktop) to `space-4` (mobile) to conserve width.

---

## Performance Guidelines

- **Image optimization:** N/A in MVP — no user-uploaded or hero images in this app; if avatars or episode artwork are added later, use `next/image` or equivalent lazy-loaded, sized images at that point.
- **Code splitting:** the Artifact Viewer (and any Markdown/HTML rendering libraries) is lazy-loaded, since a fresh session with no artifacts shouldn't pay that bundle cost upfront.
- **Lazy loading:** session history beyond the most recent N sessions loads on scroll/demand rather than all at once.
- **Critical CSS:** Tailwind's production build already purges unused classes — no additional critical-CSS extraction needed at this scale.

---

## Browser Support

- **Supported browsers:** last 2 versions of Chrome, Firefox, Safari, Edge.
- **Progressive enhancement:** the chat and artifact viewer are the core experience and require JavaScript (this is not a content site that needs a no-JS fallback).
- **Polyfills:** none anticipated — target browsers all support the CSS/JS features used (flexbox, CSS custom properties, `fetch`, `aria-live`).