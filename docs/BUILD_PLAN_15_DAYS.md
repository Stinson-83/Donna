# Donna — Build Roadmap: WhatsApp + Lightweight Web Dashboard, Then the Full App

## The sequencing decision

Ship the **core product first** = **WhatsApp** (chat + proactive nudges + action
approvals) **plus a lightweight, read-mostly web dashboard** ("her brain exposed" — what
matters now, schedule, watches, beliefs) that each user opens via a **per-user link Donna
sends them in WhatsApp.** The two surfaces share one memory.

**Only after this is in users' hands** do we build the **full interactive app** (Phase 2)
— and the lightweight dashboard *grows into* it (same components, same endpoints), so it's
additive UI, not a re-platform.

The **browser capability (Kimi WebBridge)** is a **feature track**, not a surface — it
slots in *after* the core ship and is **off the critical path** for Phase 1 (its design +
Phase 0 are already done; full plan in `docs_v2/BROWSER_CAPABILITY_ARCHITECTURE.md`).

## What already exists (so Phase 1 is assemble + wire, not rebuild)

- **WhatsApp** ✅ — Meta Cloud API inbound webhook + outbound channel, cards → reply buttons, OAuth onboarding; the whole brain already delivers to WhatsApp.
- **Dashboard data** ✅ — live per-user endpoints already serve everything a dashboard needs: `/today`, `/watchbar`, `/cards` (+ `/cards/action`), `/library/*` (todos, trackers, people, documents, connected), `/watches`, `/cognition/graph` (beliefs).
- **Dashboard UI** ✅ — `webapp/` already has `TodayPage`, `WatchBar`, `Drawer` (the Library), `BeliefsPage`, `Card`, and the `useRemote` data hook; `api.js` already supports a real backend (`VITE_MOCK=0`, `VITE_API_BASE` → Railway).
- **Cross-surface actions** ✅ — a card tap on the web dashboard resolves through the **same gate + executors** as a WhatsApp tap (`resolve_card_action(..., surface="app")`).
- **THE ONE REAL GAP** ⚠️ — **per-user auth.** Today identity is client-side `localStorage` and the API trusts an unauthenticated `user` param (the code itself notes "real secure auth is the Tier-2 upgrade"). A public dashboard cannot ship on that. This is the main net-new piece.

**The invariant for every change:** new capability = a deterministic detector / tool /
provider / hook feeding the *same* single reasoning loop; nothing skips the L0/L1/L2 gate.
Prompt-affecting changes are bracketed by smoke-evals + a per-turn cost check.

---

# PHASE 1 — WhatsApp + Lightweight Web Dashboard (~12 days)

Two parallel tracks converging on a first-cohort ship.

## Track A — WhatsApp completeness (the conversational + action surface)

### A1 — Proactive compliance (the top WhatsApp risk) · Days 1–3
- **Goal:** "she texts first" works within Meta's rules.
- **How:** Meta requires an approved **message template** to initiate outside the 24-hour customer-care window. Add a delivery template layer: inside 24h → normal freeform; outside 24h → an approved opener template that re-opens the session, then the content. Route the morning brief, watch fires, and tiered delivery through it. **Submit the templates for approval on Day 1** (review latency is the schedule risk).
- **Test:** 24h-window branch; existing tiered-delivery + morning-brief tests stay green.

### A2 — In-chat onboarding + the "open your dashboard" card · Days 3–5
- **Goal:** a new user goes from "hi" to a working Donna, and gets their dashboard link, without leaving WhatsApp.
- **How:** first-message → timezone confirm (already prompted) → connect Gmail/Calendar via OAuth CTA cards (`onboarding.py`) → Donna sends the **per-user magic-link** (from B1) as an "open your dashboard" CTA.
- **Test:** scripted onboarding on fake inbound; consent cards resolve; the dashboard link is per-user and valid.

## Track B — The lightweight web dashboard (read-mostly "her brain")

### B1 — Per-user auth / magic link (the real gap) · Days 1–4
- **Goal:** each user sees only *their* dashboard, opened from a WhatsApp link.
- **How:** a signed, expiring **magic-link token** Donna mints per user; the dashboard exchanges it for a short session; a backend **token-verify dependency** replaces the unauthenticated `user` param and resolves `user_id`. No cross-user access by tampering a query param.
- **Test:** token verifies → correct user; tampered/expired token → rejected; no data leakage across users.

### B2 — Assemble the read-mostly dashboard subset · Days 4–7
- **Goal:** a fast, focused web view of what Donna sees and believes — not the whole app.
- **How:** assemble `TodayPage` + `WatchBar` + the Library `Drawer` + `BeliefsPage` from the existing `webapp/`, wired to the real endpoints (`VITE_MOCK=0`, authed user from B1). **Strip** Live chat, Plan, and the full Memory constellation → those are Phase 2. Keep card **actions** (they resolve through the existing gate). Prioritize/paginate via the attention ranker so the view stays light.
- **Test:** dashboard renders real per-user data from `/today` `/watchbar` `/library` `/cognition`; a card action from the web resolves identically to WhatsApp.

### B3 — Deploy + link from WhatsApp · Days 7–9
- **Goal:** a live URL each user can open.
- **How:** deploy the static dashboard + the API (the webapp already references a Railway `VITE_API_BASE`); Donna's "open your dashboard" card (A2) carries the per-user magic link; confirm a web tap on a decision card lands the same effect as a WhatsApp tap.
- **Test:** end-to-end open-link → authed dashboard → tap a card → effect through the gate.

## Converge — security pass, polish, ship to first cohort · Days 9–12
- **Security:** auth-isolation test (no reading another user by token manipulation); rate limits; secrets/tokens never logged.
- **Polish:** the WhatsApp dashboard *summary* command ("what's up") as a chat fallback for the link; empty-state and loading states on the web.
- **Ship:** onboard the first cohort.

### Phase 1 — definition of done
A user **chats + gets compliant proactive nudges + approves actions on WhatsApp**, and
**opens a per-user link to a live, read-mostly web dashboard** of what Donna sees and
believes — card taps on either surface flow through the same gate. **Two surfaces, one
memory.** Full suite green; per-turn cost unchanged; per-user data provably isolated.

---

# FEATURE TRACK (after the core ship, parallelizable) — Browser capability (Kimi)

Off the Phase-1 critical path. When the core is stable: read-only `browser_task` +
`browser_watch` (mock-first via `FakeBrowserProvider`) → acting (`submit`→L1,
`pay/sign/delete`→L0, idempotent) → swap in real Kimi behind an env flag (CI stays on the
fake). Approvals surface as WhatsApp/web cards. This is the "past the API frontier"
unlock — watch and act on any logged-in, no-API site. Full plan:
`docs_v2/BROWSER_CAPABILITY_ARCHITECTURE.md`.

---

# PHASE 2 — The Full App (after Phase 1 is in users' hands)

Build the rich interactive app as a **second surface over the same brain** — no new
intelligence; the memory, beliefs, season layer, and gate are all shared. Everything
learned during the WhatsApp + dashboard phase is already there when the app opens.

- **The full interactive dashboard** — the lightweight web view grows up: live updates, the full Library, richer cards.
- **Live / Plan / Chat tabs** — understanding-first, not a message log.
- **Full Beliefs constellation + Memory** — the parked `MemoryConstellation` + evidence trails, real-backed.
- **The "why" affordance** — tap a card → the evidence / season that raised it.
- **Ambient moments** — push notifications, lock-screen / dynamic-island recall.
- **Real auth** — Clerk + backend JWT replaces the magic-link tier (the code already anticipates this swap).
- **Then, same spine:** ambient voice, more channels (Slack/SMS/calls), vertical depth — per `DONNA_FEATURES_AND_ROADMAP.md`.

---

## Risk register

- **Meta template approval latency** — the top WhatsApp risk; submit templates Day 1.
- **Web auth/security** — the #1 Phase-1 risk (per-user data behind a public URL): signed/expiring tokens, scoped, isolation-tested. Do **not** expose the unauthenticated `user` param publicly.
- **Scope creep** — keep the dashboard **read-mostly + card actions**; resist rebuilding the full app in Phase 1 (that's Phase 2).
- **Kimi access** — off the critical path; the core ships without it.
