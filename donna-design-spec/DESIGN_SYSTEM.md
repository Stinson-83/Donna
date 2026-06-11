# Donna Design System v1.0 — Lock Document

The reference HTML files in `/reference` are the pixel truth. This document is the
*law* behind them — the rules that let a renderer produce correct UI from payloads
it has never seen. If code and this document disagree, this document wins.

---

## 1. The semantic laws (non-negotiable)

**Law 1 — Color means initiative.**
- **Espresso (dark) surfaces** = Donna's moments: she caught something, she needs
  you, she's present (Talk button, voice session, proactive approval cards,
  Dynamic Island). Dark cards carry grain texture and tilt `-0.4deg`.
- **White/light surfaces** = informational: trackers, files, consent forms, rows.
- **Sunk translucent surfaces** = settled: confirmations, receipts. Inset shadow,
  tilt `+0.3deg`.
- In History only: **bubble color means surface** — rust = in app, WhatsApp green
  = WhatsApp. Donna's WhatsApp replies get the sage tint (`wa.tint`).

**Law 2 — Depth means state, never decoration.**
`elevation.needsYou` (highest) → `elevation.raised` → `elevation.low` →
`elevation.settled` (sunk). A resolved card must visually *sink*.

**Law 3 — Garamond is rationed.**
EB Garamond appears only as: nav titles, hero numerals (times, prices), and the
`d` mark. Always upright, 500–600. Italic exists nowhere except the wordmark.
Red Hat Text carries all other text. Violating this is the #1 way the app
starts looking like AI slop.

**Law 4 — Donna's voice.**
lowercase. no em dashes. no exclamation marks. no emoji. max one question per
message. facts in **bold**. UI labels (buttons, eyebrows, keys) are normal
sentence/title case — the voice rule applies to *her words*, not chrome.

**Law 5 — Rust is the only accent on light surfaces; copper is the only accent
on dark surfaces.** Green is reserved for success/confirmation and WhatsApp
identity. Amber for time-sensitive heads-ups. Danger red appears only on the
end-call control.

**Law 6 — Motion is rationed.**
Allowed: button press travel (1.5px), drawer slide, working dots, shimmer on
working text, voice waveforms, the breathing live dot, the morphing call form.
Forbidden: entrance animation theater, parallax, spinners. Always respect
`prefers-reduced-motion`.

**Law 7 — Proof lines.**
Cards that claim work was done must show evidence in a footer: who replied,
when last checked, what the source was. ("whatsapp sent · aniroodh replied
'got it' at 8:51"). This is a product rule expressed as a design rule.

---

## 2. Screen anatomy (reference files)

| Screen | File | Notes |
|---|---|---|
| Live tab | `live-tab-v6.html` | Donna speaks in free prose (no bubble); user in rust bubbles; Talk button; full voice session overlay with mid-call card |
| Live states ×6 | `live-states.html` | proactive / tracker / consent / voice / documents / all-clear |
| History tab | `history-v3.html` | iMessage-clean stream; color = surface; swipe-left reveals time+surface; system lines; call rows |
| Dashboard | `dashboard-v3.html` | Today view: hero slot, tracker+graph, day rail, heads up, todos, pulse; drawer for Library sub-menus |
| Island + lock | `island-lockscreen.html` | 3 island states, Live Activity, actionable notification (native Swift package, not WebView) |

## 3. Component inventory (hand-built, never generated)

Primitives: `Bubble` (in/out × app/wa), `VoicePill`, `PhotoBubble`, `FileRow`,
`SystemLine`, `CallRow`, `DonnaProse`, `Composer`, `TalkButton`, `TabBar`,
`Drawer`, `NavTitle`, `StatusChip`, `WorkingIndicator`, `PulseLine`.

Card system: `Card` (theme shell: dark/light/settled + grain + tilt + elevation)
rendering blocks: `HeaderBlock`, `BodyBlock`, `DeltaBlock`, `KeyValuesBlock`,
`StepsBlock`, `ScopesBlock`, `FileBlock`, `GraphBlock`, `ActionsBlock`,
`FooterBlock`.

Dashboard: `HeroSlot`, `DayRail`, `TodoList`, `HeadsUpRow`, `LibraryRow`
(+ peeks: `AvatarStack`, `SheetFan`, `Sparkline`, `ServiceDots`).

Voice: `CallScreen`, `MorphForm`, `CallControls`, `MidCallCard`, `MiniSessionPill`.

Every component ships with loading / **empty** / error states (per the delivery
spec). Empty states are designed, not left blank.

## 4. The generative contract

Donna never generates markup. She emits a `DonnaCard` payload
(`schema/card.schema.json`) through the `render_card` tool. The client's `Card`
renderer maps blocks → block components. Theme defaults derive from `intent`
(approval → dark, tracker/info/consent → light, confirmation → settled) but the
payload may override.

Validation is backend-side (Pydantic, `schema/models.py`). Invalid payload →
plain text message fallback. Never render a broken card. `action_id`s are opaque
and resolve identically from the app, a notification, or the Island —
`card_id` is the join key.

## 5. What "done" looks like

A gallery route rendering: all six mock payloads from `/mocks` through the real
`Card` renderer, every primitive in its three states, and the History swipe
working on a real Android WebView. When the six mocks render pixel-equal to the
reference HTML, the system is locked.
