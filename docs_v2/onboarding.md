# Onboarding & Cold-Start — bootstrapping the moat

**Status:** Spec · 2026-06-11
**Depends on:** `domain_schema.md` (the tables this fills), `user_model.md` (the 8 layers this seeds), `architecture_decision.md` (§6/§10.1 bounded distillation passes), `proactive_runner.md` (seeds watches + recurring schedules), `cards_and_delivery.md` (consent flow), `integrations.md` (OAuth philosophy).
**Fills:** the review gap — `users.onboarding_status` exists with no flow. The User Model is the moat but is empty on day 1. This is how day 0 starts.

---

## 1. The cold-start problem

Donna's value is understanding; understanding comes from history; on day 1 there is none. The demo's specificity — "Grab Standard 95%", "mom likes lilies", "you usually call her at noon" — is the *matured* state after months. Onboarding has to credibly start that arc without an interrogation.

> **The insight: the user already has years of signal in their connected accounts.** Onboarding does not ask the user to describe their life — it **mines the digital life they already have**, then confirms lightly. vision.md: preferences "should be learned, not manually configured."

So onboarding is **mostly deterministic backfill + a few bounded extraction passes + a short in-character conversation** — not a settings wizard.

---

## 2. Shape: one flow, run per integration

Onboarding is **not a one-time event** — it is a per-integration backfill. The first run (account creation + first connect) is just the first instance. When the user connects Grab mid-life (demo M6), the same machinery runs a scoped backfill for that one source. The phases below describe the first run; later connects re-enter at Phase 1 for the new source only.

`users.onboarding_status`: `pending → connecting → backfilling → confirming → active`.

---

## 3. Phase 0 — account + first connect

- Create `users` (email, **timezone** — required for all scheduling/quiet-hours math).
- Connect the first integration (Gmail or Calendar — highest signal) via the **consent card** (cards_and_delivery §4), scoped and explained (integrations.md OAuth philosophy).
- `onboarding_status = connecting`.

---

## 4. Phase 1 — deterministic backfill (no LLM)

For each connected integration, a sync worker runs a **bounded historical sync** into the domain tables. Tracked by a cursor table so it resumes and re-runs incrementally:

```sql
integration_syncs
  id UUID PK
  user_id UUID
  integration_id UUID
  sync_type TEXT          -- backfill | incremental
  status TEXT             -- pending | running | done | failed
  cursor TEXT             -- provider pagination cursor
  range_start TIMESTAMP   -- backfill window start
  range_end TIMESTAMP
  items_synced INTEGER
  last_run TIMESTAMP
```

What each source backfills (deterministic ingestion, upsert by `external_id`):

| Source | Window | Fills |
|---|---|---|
| Calendar | past 3–6 mo + all future | `calendar_events` |
| Gmail | past 6–12 mo, structured only | `contacts` (frequent senders), `subscriptions` (receipts), `bills`, candidate commitments |
| Bank | recent | `finance_accounts`, `balances`, `transactions` → recurring → `subscriptions` |
| Health | recent | `health_logs`, seed `nutrition_daily` |

**This is bulk ingestion with zero LLM.** It does not store full email bodies — it extracts structured facts (a receipt → a `subscription` row; a sender → a `contact`). `onboarding_status = backfilling`.

`integration_syncs` then flips to `incremental` and becomes the **ongoing** sync state the runner relies on for warm caches (`domain_schema.md §1`).

---

## 5. Phase 2 — bounded extraction passes (the few allowed LLM calls)

This is where backfilled data becomes **understanding**. Per ADR §6/§10.1, reasoning is the loop or **declared, periodic, cheap, async distillation** — never per-item. Onboarding runs the **first instance** of those passes: a small, fixed set (≈5–8 total, cheap model, async), each operating over **aggregates**, not raw rows.

Critically — **NOT** "run an LLM over 10,000 emails." The bulk is already structured by Phase 1; these passes reason over the *summary*:

| Pass | Input (aggregate) | Output (seeded, low confidence) | LLM? |
|---|---|---|---|
| Relationship seeding | `contacts` + comms volume/recency/channel | `relationships` (importance scored deterministically; type labelled by one pass) | 1 pass for labels |
| Goal inference | calendar/email signal summary (fundraising threads, portals) | candidate `goals` → confirm in Phase 3 | 1 pass |
| Preference seeding | `transactions`/bookings frequency (Grab Standard 95%, Apple Music) | `preferences` w/ confidence | mostly deterministic |
| Pattern seeding | calendar/comms timing (calls mom ~noon, works 9–12) | `patterns` | deterministic |
| Identity distillation | the above, summarized | `user_model` (life_context, decision_style draft, summary) | 1 pass |

Most are **deterministic frequency analysis**; only a few need a cheap pass to *label* (relationship type, goal phrasing, identity summary). This is the ADR's "periodic cheap distillation" — onboarding just runs it for the first time. Bounded count = bounded cost; no per-email explosion.

**Everything seeded here starts at low/moderate confidence.** The memory confidence system (`memory_system.md`) raises it as the first weeks confirm. Onboarding gets the ball rolling honestly — it does not fake the 247-day certainty.

---

## 6. Phase 3 — light conversational confirmation (she texts first)

Donna now reaches out **in character** (lowercase, blunt, useful) to confirm the highest-value inferences and set goals — conversation as the interface, not a form. `onboarding_status = confirming`.

Examples (each a card or a quick reply):
- "you email three people way more than anyone else: priya, ravi, your mom. who's who?" → confirms `relationships`.
- "looks like you're fundraising right now. want me to treat investor stuff as top priority?" → confirms a `goal`.
- "you call your mom most days around noon. want me to keep an eye on her birthday and nudge you?" → confirms a `pattern`, seeds a relationship watch.

This is bounded (a handful of high-value confirmations), and it doubles as the **first "she gets me" moment** — the inferred specifics prove the backfill worked. When Donna is unsure, she says so (vision.md). The user can correct; corrections write straight to the User Model at high confidence.

---

## 7. Phase 4 — seed watches, schedules, go live

Deterministic, no LLM:
- **Lead-time derivation** (`proactive_runner.md §7`) scans the now-populated domain tables → creates initial `watches`: upcoming `bills` (M3), `subscriptions` near renewal (M8), `relationships` with birthdays (M7), calendar deadlines (M2-style).
- **Recurring `scheduled_tasks`** seeded: the 11pm daily summary (M9), a lunch check-in timed to their eating pattern (M4), morning dashboard, the nightly metrics rollup (`metrics.md`).
- **Metrics ledger** starts at day 0 (`metric_rollup.days_with_donna = 0`).
- `onboarding_status = active`.

On the user's **first dashboard open, M1 is already populated** — real watches, real scheduled events, real logistics — because Phases 1–4 filled the tables. That first non-empty dashboard is the onboarding payoff.

---

## 8. User Model coverage

Onboarding seeds layers 1–7 of `user_model.md` (Goals, Relationships, Preferences, Patterns, Commitments, Decision-style, Life-context) at low/moderate confidence. **Layer 8 (Identity)** is left thin — it emerges over weeks; onboarding writes only a first-draft `summary`. This matches the doc's "Identity is the highest abstraction, emerges over time."

---

## 9. Privacy & trust

Backfilling email + bank is maximally sensitive.
- **Consent per integration**, scoped, transparent (the consent card states exactly what Donna will read).
- Backfill respects the granted scope and is **explained** ("i read your last 6 months of calendar and receipts to get started").
- Token storage + encryption-at-rest is the still-open **token-vault/security** decision — onboarding is a primary consumer of it and should not ship to real accounts until it lands.

---

## 10. Cost

| Phase | LLM cost |
|---|---|
| 1 backfill | **zero** (deterministic ingestion of thousands of items) |
| 2 extraction | **bounded** — ~5–8 cheap async passes over aggregates, once |
| 3 confirmation | a few loop turns (user is replying) |
| 4 seed/go-live | zero |

The discipline that keeps onboarding affordable is the same as the whole system: **deterministic bulk, bounded reasoning.** Mining the digital life is free; distilling it is a fixed handful of cheap passes.

---

## 11. Demo coverage

| Demo specificity | Source |
|---|---|
| M1 dashboard non-empty on first open | Phases 1–4 |
| M3 AWS bill known proactively | Gmail/bank backfill → `bills` → lead-time watch |
| M7 "mom likes lilies", "you call her at noon" | backfill (contacts/comms) + Phase-2 pattern seeding + Phase-3 confirm; "lilies" likely an accumulated memory post-onboarding |
| M5 "aniroodh's restaurant rec last tuesday" | accumulated memory (post-onboarding), not backfill — onboarding starts the stream that captures it |
| M6 "Grab Standard, matches your usual" | preference seeding (transactions) maturing over use |

Onboarding makes the **first day** credible; the **moat** is the months after, captured by the same memory loop onboarding kicks off.

---

## 12. Out of scope / open

- **Backfill window sizes** (3 vs 12 months) are tunable per source; defaults above.
- **Re-onboarding / disconnect** (user revokes Gmail): scope the affected tables, mark stale, stop the relevant watches — a lifecycle detail for the integration layer.
- **Token vault / encryption** (§9) blocks real-account onboarding and is tracked in the review's open list.
