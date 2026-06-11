# Cards & Delivery — The Interaction and Transport Layer

**Status:** Spec · 2026-06-11
**Depends on:** `architecture_decision.md` (§4 Egress, §10.2 outbox, §10.3 execution gate). This doc fills the largest demo-critical gap from the docs_v2 review: the interactive-card system and the outbound delivery/realtime transport, neither of which existed in `docs_v2`.
**Extends:** `database_schema.md` (new tables in §12), reconciles the thin `notifications` table.

> **Card payload is canonical in the design spec, not here.** The card *payload* — its shape, blocks, intents, rendering, and surface projection — is the **`DonnaCard`** block model in `donna-design-spec/` (`schema/card.schema.json` + `schema/models.py`). This doc's `card_type` → DonnaCard `intent`; this doc's `options[]` → the `Actions` block **plus a server-side `action_id → {kind, tool, args, tier}` map** (never put tool/args on the wire); this doc's `body` → DonnaCard `blocks`. What stays canonical **here**: the tables, the tap→gate→execute workflow, idempotency, lifecycle/state, and the delivery transport — none of which the design spec covers. The seam is `donna-design-spec/INTEGRATION.md`.

---

## 1. Where this sits

The ADR's canonical path ends at **Egress → deliver to surface**. This doc specifies that ending and the return trip:

```text
BRAIN loop → Terminator (send_burst / offer / propose_card)
        → persist message + card  → Notification policy (route/quiet-hours/batch)
        → per-surface Deliverers (WhatsApp · push · app realtime · dashboard)
        → user sees it
        → user taps a card option (any surface)
        → card_action event → Ingress → Card Action Workflow → deterministic execute
        → result message + dashboard update (back through Egress)
```

Two systems, one doc, because they are the same loop: **cards are how Donna proposes and the user authorizes; delivery is how that proposal reaches the user and the authorization comes back.**

---

## 2. Core model

Three objects.

- **Message** — a unit of communication *from* Donna (or logged *from* the user). The text burst ("heads up. sequoia partner replied…"). May carry one or more cards. Also the canonical chat/conversation log (this is memory-layer 8, `chat messages`).
- **Card** — a structured, interactive proposal attached to a message or standalone. Reply options, an approval, a consent prompt, a list of ride choices.
- **Option** — a button on a card. Carries an **action** that fires on tap.

### The one principle that makes this coherent

> **A card is the §10.3 execution gate made visible.** An L0/L1 action is never executed silently — it is rendered as a card, and the user's tap is the execution trigger. The buttons in demo M2/M3/M6/M7/M8 are not UI decoration; each is an agency-gated action awaiting authorization.

Corollary (cost): **a button tap is a deterministic execute, not a new reasoning turn.** The BRAIN loop already reasoned when it produced the card and pre-filled the action. Honoring a tap runs no LLM — unless the option is explicitly a *re-reason* option (§5), which re-opens the loop with the user's choice as input. This keeps the ADR's per-event budget intact: proposing a card is part of the one loop invocation; acting on it is free.

---

## 3. Object model

```text
Message
 ├─ id, user_id, direction (out|in), surface_origin
 ├─ role (donna|user), body (text)
 ├─ in_reply_to (message_id?)
 └─ cards[]  (0..n)

Card
 ├─ id, user_id, message_id
 ├─ card_type (approval|confirm|consent|reply_options|choice_list|info)
 ├─ tier (L0|L1|L2|none)          ← the agency tier this card authorizes
 ├─ title, body (JSONB: rich lines, e.g. the email summary / bill math)
 ├─ state (pending|acted|dismissed|expired|superseded)
 ├─ expires_at (nullable)          ← time-bound cards (term sheet EOD, bill clears)
 ├─ bound_action (JSONB, nullable) ← the primary pre-filled action (for approval/confirm)
 ├─ options[] (JSONB array)
 ├─ acted_option_id, acted_at, acted_surface
 └─ metadata (JSONB)

Option (inside card.options[])
 ├─ id, label, style (primary|recommended|destructive|secondary)
 └─ action { kind, ... }           ← see §5
```

Options live as a JSONB array on the card (cards are small, always read whole). A normalized `card_options` table is optional and only worth it if you need per-option analytics queries.

---

## 4. Card types

| card_type | Tier | Bound to | Demo |
|---|---|---|---|
| **approval** | L0 | one consequential action; options = approve / alternative / reject | M3 transfer ₹5,000 · M6 book ride · M7 send ₹1,899 flowers |
| **confirm** | L1 | one medium action; options = do it / alternative / not now | M8 cancel Spotify |
| **consent** | n/a | an integration connect (OAuth); options = allow / not now | M6 CONNECT GRAB |
| **reply_options** | per-option | drafted stances for an email/message; each option sends a draft (L1) or re-reasons | M2 accept / counter / ask 48h |
| **choice_list** | per-row | a ranked list where each row is its own bound action | M6 the 3 ride cards (each "book" = L0) |
| **info** | none | nothing; optional ack/dismiss | M1/M9 dashboard insight cards |

`info` cards are non-interactive and render only to the dashboard. Everything else is interactive and gate-bound.

---

## 5. Option action kinds

Every option's `action` is one of:

| kind | On tap | LLM? | Example |
|---|---|---|---|
| **execute** | run `{tool, args}` deterministically through the gate | no | `[yes, transfer]` → `transfer(₹5000, savings→current, idem=…)` |
| **reopen** | re-invoke the BRAIN loop with `{prompt}` + the user's choice as new input | yes (one loop) | `[counter on valuation]` → loop drafts a counter → emits a new send card |
| **consent** | start the OAuth/connect flow for `{provider, scopes}`; on completion resume the origin workflow | no | `[allow]` → Grab OAuth → `integration_connected` event |
| **dismiss** | mark card dismissed, no action | no | `[not now]` / `[i'll handle it]` |
| **snooze** | re-schedule the proposal for `{when}` via the scheduler | no | `[remind me tomorrow]` |

This is what lets one card mix fast pre-filled actions with "let me think about it" options without violating the single-loop rule. M2 is the canonical mix: `accept` = execute a pre-drafted send (L1); `counter` = reopen (needs drafting); `ask 48h` = execute a pre-drafted send (L1).

---

## 6. Card lifecycle

```text
            ┌──────────── superseded (newer card replaces this proposal)
            │
created → pending ─┬─ tap execute/consent ─→ acted
            │      ├─ tap dismiss ──────────→ dismissed
            │      └─ tap snooze ───────────→ (new card scheduled), this → dismissed
            │
            └─ expires_at passes / world changed ─→ expired
```

- **expires_at** is mandatory for time-bound proposals (M2 term-sheet EOD, M3 bill auto-debits in 4 days). A scheduler sweep flips lapsed `pending` cards to `expired`.
- **superseded**: when state changes invalidate a live card (balance changed, bill already cleared), the workflow issues a fresh card and marks the old one `superseded` — never leave two live proposals for the same action.
- A card is **acted at most once** (idempotency, §7).

---

## 7. The tap → execution path (the critical flow)

This is the most important flow in this doc. A tap from **any** surface normalizes to one `card_action` event and runs one deterministic workflow — no second reasoning turn for `execute` options.

```text
User taps option (WhatsApp button | app | island)
        ↓ surface-specific inbound (webhook / websocket / http)
INGRESS → normalize → card_action event { card_id, option_id, surface }
        ↓ (events table + NOTIFY, per ADR §10.2)
CARD ACTION WORKFLOW (deterministic):
  1. Load card. If state != pending → reject + explain ("already handled" / "expired").   ← idempotency + freshness
  2. Resolve option. If kind = reopen → invoke BRAIN loop, done. If dismiss/snooze → apply, done.
  3. For execute/consent: RE-RUN the §10.3 gate on bound action with CURRENT state.        ← never trust stored tier blindly
       - Safety tier still permits? Consent/scope still present? World still valid
         (e.g. bill not already paid, balance still short)?
       - If not → mark superseded, emit a fresh card or an explanation. STOP.
  4. Execute {tool, args} with an idempotency_key derived from (card_id, option_id).        ← exactly-once side effect
  5. Record: card.state=acted, actions row, tool_executions row, card_actions audit row.
  6. Emit result → confirmation message + dashboard projection (back through Egress).
  7. Propagate card state to ALL surfaces holding this card (§9).                            ← cross-surface sync
```

Key guarantees:
- **Idempotent execute.** The idempotency key on the action means a double-tap, a retried webhook, or a tap-from-two-surfaces executes the side effect once. (Mandatory for L0 money/booking actions.)
- **Re-check at tap, not just at propose.** The gate is the authority at execution time. A stale card (the AWS bill already cleared) is caught here and explained, not blindly executed.
- **No LLM for `execute`.** Honoring an approval is pure orchestration. Only `reopen` spends a loop.

---

## 8. Surfaces & rendering

One logical message+card renders to multiple surfaces. Each surface has constraints and a renderer.

| Surface | Renders | Interactive? | Realtime in | Constraints |
|---|---|---|---|---|
| **WhatsApp** | text + buttons / list | yes (reply buttons, list rows) | webhook | ≤3 quick-reply buttons; >3 options → list message (≤10 rows) or numbered fallback; rich `body` flattens to text |
| **App — Chat / Live tab** | full rich cards (ride list, consent slide-up) | yes | WebSocket/SSE | full fidelity; the action surface |
| **App — Dashboard** | sections + `info` cards | no (view) | WebSocket/SSE | live-synced (M6 "updates instantly"); projection only |
| **Push (APNs/FCM)** | title + body, deep link | tap deep-links to card | — | lock-screen "heads up" (M2); not the card itself, a pointer to it |
| **Dynamic Island / Live Activity** | ephemeral card + voice | yes (inline) + TTS/STT | streaming | iOS only; low-latency; ephemeral lifecycle (M5) |

**Surface routing is deterministic** — the Notification engine (ADR §6, policy not LLM) chooses surface(s) from: importance/tier, current user activity, quiet hours, interrupt budget. Examples:
- L0 urgent approval (sequoia EOD) → WhatsApp + push.
- L2 auto result ("done. ₹5,000 moved.") → the surface the user is on + dashboard.
- `info` insight → dashboard only, never a push.

**Body fidelity:** `card.body` is structured (JSONB lines). Rich surfaces render it natively; WhatsApp/push flatten it to text. Author once, render per surface.

---

## 9. Cross-surface identity & realtime sync

The product promise is "two surfaces that share one memory." A card has **one canonical id and one state**, regardless of how many surfaces show it.

- Tap "transfer" on WhatsApp → card → `acted` → the app's rendering of that same card must immediately reflect `acted` (button disabled, confirmation shown).
- Mechanism: state changes write the `cards` row, then `NOTIFY donna_realtime, '<user_id>:<card_id>'`. A **WebSocket gateway** holds per-user app connections, LISTENs on that channel, and fans the change out to that user's connected clients.
- The dashboard is the same mechanism: a projection writes `dashboard_sections`, NOTIFY, gateway pushes the delta (M6 "new row in scheduled… instantly").

This reuses the ADR §10.2 LISTEN/NOTIFY-over-outbox pattern for *outbound realtime*, exactly as the event bus uses it for *inbound events*.

---

## 10. Delivery pipeline (Egress)

Outbound delivery is durable and retryable — it uses the same persist-then-notify outbox as the event bus.

```text
Terminator persists: messages row (+ cards rows)
        ↓
Notification policy: which surface(s)?  (deterministic)
        ↓
deliveries rows created (one per surface, status=queued, idempotency_key)
        ↓  NOTIFY donna_deliveries
Per-surface Deliverer workers (LISTEN + poll, claim SKIP LOCKED):
   WhatsApp Deliverer → Composio/WhatsApp Business send
   Push Deliverer     → APNs / FCM
   Realtime Deliverer → WebSocket gateway (LISTEN/NOTIFY fanout)
   Dashboard Projector→ dashboard_sections write → realtime
        ↓
Record receipt: status queued→sent→delivered→read | failed(+retry/backoff)
```

- **At-least-once + idempotent send.** Each `deliveries` row has an idempotency key (and the provider's message id once sent) so a retried worker never double-sends a WhatsApp message.
- **Retry/backoff** on `failed`; a dead-letter after N attempts surfaces as an internal alert.
- **Receipts** feed the dashboard metrics ("94% delivered on time") and the Notification engine's budget.

---

## 11. Inbound normalization

Taps and replies arrive differently per surface but normalize to **one** event so the Card Action Workflow is surface-agnostic:

| Source | Raw | Normalized |
|---|---|---|
| WhatsApp button reply | webhook (button payload = `card_id:option_id`) | `card_action` event |
| WhatsApp free text | webhook (message) | `user_message` event → BRAIN loop |
| App button tap | WebSocket/HTTP `{card_id, option_id}` | `card_action` event |
| App chat message | WebSocket/HTTP | `user_message` event → BRAIN loop |
| Island tap / voice | gateway | `card_action` / `user_message` event |
| OAuth callback | provider redirect | `integration_connected` event → resume origin workflow |

Encode `card_id:option_id` into WhatsApp button payloads so a button reply round-trips to the exact option without guessing.

---

## 12. Schema additions

Extends `database_schema.md`. Supersedes the thin `notifications` table (push-only) with the richer `messages` + `deliveries` pair.

```sql
-- canonical comms log (also memory-layer 8: chat messages)
messages
  id UUID PK
  user_id UUID
  direction TEXT            -- out | in
  role TEXT                 -- donna | user
  surface_origin TEXT       -- whatsapp | app | island | system
  body TEXT
  in_reply_to UUID NULL
  created_at TIMESTAMP

cards                        -- persistence wrapper around a DonnaCard payload
  id UUID PK                 -- == DonnaCard.card_id
  user_id UUID
  message_id UUID NULL
  intent TEXT               -- DonnaCard.intent: approval|confirmation|heads_up|consent_integration|tracker|document|options|info
  payload JSONB             -- the validated DonnaCard (version, intent, theme, blocks[]) sent to surfaces
  action_map JSONB          -- SERVER-ONLY: action_id → {kind,tool,args,tier}; never sent to the client
  state TEXT                -- pending|acted|dismissed|expired|superseded  (drives DonnaCard.theme, see INTEGRATION.md §4)
  expires_at TIMESTAMP NULL
  acted_action_id TEXT NULL -- which Actions-block action_id was tapped
  acted_surface TEXT NULL
  acted_at TIMESTAMP NULL
  metadata JSONB
  created_at TIMESTAMP

-- per-surface outbound transport (outbox; generalizes old notifications table)
deliveries
  id UUID PK
  message_id UUID
  surface TEXT              -- whatsapp|push|app|dashboard|island
  provider TEXT
  status TEXT               -- queued|sent|delivered|read|failed
  provider_message_id TEXT NULL
  idempotency_key TEXT UNIQUE
  attempts INTEGER
  error TEXT NULL
  created_at TIMESTAMP
  updated_at TIMESTAMP

-- audit of taps (links a tap to the executed action)
card_actions
  id UUID PK
  card_id UUID
  user_id UUID
  action_id TEXT               -- the DonnaCard Actions-block action_id tapped
  surface TEXT
  result_action_id UUID NULL   -- → actions.id (the executed side effect)
  created_at TIMESTAMP
```

Reuses existing tables: `actions` (the executed side effect), `tool_executions` (audit), `events` (the `card_action` / `user_message` / `integration_connected` events), `dashboard_sections` (projection target). `notifications` is folded into `messages` + `deliveries`; migrate any references.

---

## 13. Demo walkthroughs (coverage proof)

**M2 — flagged email (push → WhatsApp card → reply).**
Email event → Email workflow → BRAIN loop produces: message ("heads up. sequoia…") + `reply_options` card [accept(execute L1 send) · counter(reopen) · ask 48h(execute L1 send)], expires_at = EOD. Notification policy → push (lock screen) + WhatsApp. User taps "ask 48h" on WhatsApp → `card_action` → gate (L1 send, Gmail scope present) → send pre-drafted reply, idempotent → card acted → confirmation + dashboard "sequoia reply sent ✓".

**M3 — saved auto-payment (L0 approval).**
Finance watch fires `low_balance_vs_bill` → Finance workflow → loop produces approval card (tier L0, bound_action `transfer(₹5000, savings→current)`), body = the bill math, options [yes transfer · pause auto-pay · remind tomorrow(snooze)]. Tap "yes" → gate re-checks (still short? bill not cleared?) → execute transfer idempotently → "done. ₹5,000 moved. balance ₹52,000" → keeps the bill watch. If the bill had already cleared between propose and tap, step 3 catches it → card superseded + explanation.

**M6 — Live tab ride (consent → choice_list → L0 book → instant dashboard).**
"book me a cab…" → Live Tab workflow → loop needs Grab → emits **consent** card [allow · not now]. Tap allow → OAuth → `integration_connected` resumes the workflow → loop fetches options → **choice_list** card with 3 rides, each row `book`(execute L0), Standard marked recommended ("matches your usual" from preferences). Tap book on Standard → gate (L0, scope present) → book idempotently → confirmation + **dashboard projector** writes new `scheduled` row → NOTIFY → WebSocket pushes it to the open app instantly.

All three run **one loop each** (plus free deterministic taps), honoring the ADR budget.

---

## 14. Deterministic vs LLM (budget check)

| Step | LLM? |
|---|---|
| Propose card (part of the loop's turn) | the one loop |
| Notification routing / quiet-hours / batching | no (policy) |
| Per-surface render | no |
| Delivery + receipts | no |
| Realtime sync | no |
| Tap → `execute` / `consent` / `dismiss` / `snooze` | **no** |
| Tap → `reopen` | one loop (new event) |
| Gate re-check at tap | no (deterministic) |

The whole interaction-and-transport layer is deterministic except where an option explicitly asks Donna to think again. Consistent with ADR §5/§7.

---

## 15. Out of scope / open

- **WhatsApp interactive limits** (3 buttons / list rows) may force a list-vs-buttons choice per card at render time — a renderer detail, not a model change.
- **Voice gateway** (STT/TTS for the Island, M5) — client vs server boundary to be specced with the voice workflow; this doc only commits that the Island is a surface backed by the same card object.
- **Push token storage** joins the broader token-vault/security decision (still open from the review).
- **Read receipts → metrics** ("94% delivered on time", "1,847 caught") need the metrics store (separate gap from the review).
