# Integration Contract — design spec ↔ Donna backend

How the `DonnaCard` design contract binds to the v2 backend (`docs_v2/`). The design
spec owns the **payload, rendering, and surface projection**; the backend owns
**persistence, the action gate, idempotency, and transport**. This file is the seam.

Authoritative on the backend side: `docs_v2/architecture_decision.md` (the gate is
§10.3), `docs_v2/cards_and_delivery.md` (tables + tap→execute workflow + delivery).

---

## 1. `render_card` — how a card is born

The BRAIN loop (single SDK tool-use loop, `donna_runtime/`) emits a card by calling
the **`render_card`** tool with a `DonnaCard` payload (`schema/card.schema.json`).

```
loop decides to surface a card
  → render_card(payload)
  → backend validates with schema/models.py (Pydantic)
       invalid  → discard card, send body text as a plain message (never a broken card)
       valid    → persist (cards row) + project to surfaces (SURFACES.md) + deliver
```

`render_card` is the design-spec name for the `propose_card` terminator in
`cards_and_delivery.md`. The model never generates markup — only this payload.

`schema/models.py` is the **backend twin** and should be vendored into the backend
(imported by the `render_card` tool) and kept checked against `card.schema.json` in CI
(drift control, per README).

---

## 2. `action_id` resolution = the agency gate (the part the design spec left to backend)

`action_id` is opaque on the wire. The backend keeps a private resolution map per card:

```
action_id → { kind, tool, args, tier }
   kind : execute | reopen | consent | dismiss | snooze
   tier : L2 (auto-ok) | L1 (confirm) | L0 (approve)   ← §10.3, backend-only, NEVER on the payload
```

When a user taps an action **on any surface**:

```
tap (app | notification | island)  → card_action event { card_id, action_id, surface }
  1. card still pending?            no → reject: "already handled" / "expired"
  2. re-run the §10.3 gate on {tool,args} with CURRENT state   (never trust a stale tier)
       gate blocks (scope missing / world changed) → reject + explain ("reconnect gmail", "bill already cleared")
  3. execute {tool,args} with idempotency_key = (card_id, action_id)   ← double-tap / retry / two-surface = once
  4. card → settled (theme flips), notification dismissed, History gains a system line
  5. propagate state to every surface holding this card_id
```

**Frontend consequence:** a tap can come back **rejected**, not just confirmed. The UI
must handle: `already_handled`, `expired`, `superseded`, `needs_reconnect`. These are
not errors — they are the gate doing its job.

The card's *existence* is the approval for L0/L1 actions. There is no separate
"are you sure" — tapping the primary action IS the authorization.

---

## 3. `intent` ↔ agency tier (default action semantics)

Tier lives on the resolution map (§2), not the payload, but each intent has typical tiers:

| intent | typical action tiers |
|---|---|
| `approval` | primary action is **L0/L1** (the card is the approval). `reply_send` mock → `a_send_reply` is L1 |
| `heads_up` | actions carry their own tier: `a_draft_reply` is **L2 reopen** (drafts, sends nothing); `a_dismiss` is dismiss |
| `consent_integration` | `a_oauth_*` is the **consent/OAuth** flow; on success, resume the origin workflow |
| `tracker` | a booking action (`a_book_*`) is **L0/L1**; the tracker itself is passive |
| `confirmation` | terminal, **no actions** (post-execution receipt) |
| `document`, `info` | **L2/none** (view/download) |

---

## 4. `card.state` ↔ `theme` (lifecycle the design lock implies)

The backend `cards.state` drives the design's theme transitions (`SURFACES.md` resolution flow):

| backend state | theme | surface effect |
|---|---|---|
| `pending` | `dark` (needs-you) / `light` (info) | live, in dashboard hero / notification / island |
| `acted` | `settled` | hero slot releases, notification dismissed, History system line |
| `expired` | `settled` | footer "expired · she'll re-ask if it matters" |
| `dismissed` | `settled` | quiet sink |
| `superseded` | (replaced) | a fresh card supersedes; Donna may re-raise |

---

## 5. M2 in this idiom (the moment we build first)

Chosen rendering: **binary draft idiom** (not 3 reply buttons — honors the max-2 Actions law).

```
gmail event (sequoia reply, "answer by EOD")
  → email workflow → BRAIN loop → render_card( mocks/heads_up.json )
       intent heads_up · [ Draft a reply (L2 reopen) ] [ Not now (dismiss) ]
       delivered: push (lock screen) + WhatsApp + Live
  → user taps "Draft a reply"
       a_draft_reply_sequoia is L2 reopen → re-invoke the loop → it drafts ONE stance
       → render_card( mocks/reply_send.json )
            intent approval · [ Send (L1) ] [ Edit ]
  → user taps "Send"
       a_send_reply_sequoia is L1 → gate (gmail scope present?) → send reply, idempotent
       → render_card( confirmation )  + dashboard "sequoia reply sent ✓"
```

New mocks added for this: `mocks/heads_up.json`, `mocks/reply_send.json`. Both validate
against `card.schema.json` and `schema/models.py`.

---

## 6. Open seam items

- **`options` intent** is in the enum but unused and unmocked. Reserve it for a future
  multi-choice block, or drop it from the enum — don't ship an intent with no validated example.
- **Dashboard taxonomy** differs between `reference/dashboard-v3.html` (hero/tracker/day-rail/
  heads-up/todos/pulse/library) and the demo M1 + `docs_v2/domain_schema.md §9`
  (watching/scheduled/logistics/holding/done). Reconcile when M1 is built, not before.
- **`heads_up` theme**: defaulted to `light` in `models.py THEME_DEFAULTS`, but the M2 mock
  overrides to `dark` (it is the flagship "she caught something" moment, Law 1). Confirm the
  default vs override intent with the design owner.
