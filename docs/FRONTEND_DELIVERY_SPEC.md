# Frontend Delivery Spec

What to build and how to hand it off so it drops straight into our mobile app and
I can wire real data behind it without a rewrite. Read this once before you start
— the stack and the data boundary are non-negotiable; everything else is yours.

You own: **features, UI, components, all states, design tokens, and the mock data
shapes.** I own: **the backend, real data, identity, and agentic workflows.**

---

## 1. Stack — match it exactly (not "compatible", the *same*)

- **React 18 + Vite 5 + Tailwind 3, plain `.jsx`.** Same versions as our repo.
- ❌ No Next.js, Vue, Svelte, Angular, React Native, or Flutter.
- ❌ No heavy component library that fights Tailwind (MUI, Chakra, Ant). Tailwind
  + your own components only.
- Why: our app is already this stack wrapped in Capacitor. If you ship the same
  stack, your code *is* the app — I paste it in. Anything else is a port.

## 2. Build output — must be a static bundle

- It must `vite build` into a **static `dist/`** (plain HTML/CSS/JS).
- ❌ **No SSR, no server-side rendering, no runtime Node server, no API routes.**
  The app runs inside a mobile WebView with no server — if it needs a server to
  render, it cannot ship. (This is the #1 thing that breaks mobile packaging.)
- Assets must load by **relative paths**, not absolute `/` or a hardcoded host.

## 3. Data boundary — the part that makes this integrable

This is the most important section. Get it right and integration is trivial.

- **Components are presentational: props in, render out.** A component never calls
  `fetch`, never knows about a backend, never imports a data layer.
  `<BeliefCard belief={...} onExpand={...} />`, not a `<BeliefsScreen>` that fetches
  itself.
- **All data goes through ONE module** (e.g. `src/api/`) that, for now, returns
  **mock data**. When I build the real backend, I replace the inside of that one
  module — your components don't change.
- **Every feature ships with its mock, and you document the shape of that mock.**
  This is how I know what backend to build. For each feature, give me the example
  JSON (or a TS interface) your components consume — clear, stable, descriptive
  field names. Example:
  ```ts
  // the shape my <GoalCard> expects — backend, please provide this
  interface Goal { id: string; title: string; progress: number; due: string; why: string }
  ```
  Some features will need backend that **doesn't exist yet** — that's expected.
  Your mock *is the spec* for it. I'll build the backend to your shape.
- ❌ No global state library, no router coupling inside components, no assumptions
  about where data comes from. Keep it swappable.

## 4. Mobile / WebView safety

- Respect **safe-area insets** (`env(safe-area-inset-top/bottom)`) — notches and
  home bars.
- **Touch targets ≥ ~44px.** No hover-only interactions.
- No desktop-only or `window`/`document`-only assumptions that break in a WebView.
- Test it at phone width, not just desktop.

## 5. Design tokens — one source of truth

- Define **your own** design — colors, type scale, spacing, radii, shadows — as
  **CSS variables + a Tailwind theme config**, never hex values scattered across
  components. (There is no existing design to match; this is a fresh start.)
- This keeps the whole app themeable from one place.

## 6. Every component has three states

Loading, **empty**, and error. Empty is the common case — a new user has no data
yet, so design "nothing here yet" states deliberately. Don't leave them to me.

---

## What to deliver

1. The app (or component library) in the stack above, `vite build`-able to `dist/`.
2. A **Storybook** (or a simple `/demo` route) showing each component with mock
   props, including its loading / empty / error states.
3. For each feature, the **data shape it needs** (example JSON or TS interface) —
   centralize the mocks (e.g. `src/mocks/`) so the shapes are easy to find. This
   is what I turn into backend.
4. A short README: how to install and run it.

## The one-line version

> Same React 18 + Vite + Tailwind `.jsx` stack as the repo, building to a static
> `dist/` (no SSR), with presentational components fed by a single mock-able data
> module — and for every feature, hand me the mock's data shape so I can build the
> backend to match.
