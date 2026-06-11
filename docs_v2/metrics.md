# Metrics Store — the moat made tangible

**Status:** Spec · 2026-06-11
**Depends on:** `architecture_decision.md` (PostToolUse side-effect hooks, deterministic-only), `cards_and_delivery.md` (delivery receipts), `proactive_runner.md` (the nightly rollup is a scheduled task).
**Fills:** the review gap "no metrics store / no definition of caught / on-time." This powers the demo's two highest-leverage beats: M1's "she's holding 23 things for you" and M9's moat card — "247 DAYS WITH DONNA / 1,847 things caught / 94% delivered on time."

---

## 1. Why this matters more than it looks

The closing line of the demo — *"1,847 things caught. the longer she's with me, the more she knows. i can't switch away"* — is the moat made visible. These numbers are shown **to the user**, so they are a **trust surface**. vision.md is emphatic that trust > intelligence. Therefore:

> **Every metric definition must be honest and fixed.** A "catch" that's really spam, or an "on-time %" that quietly excludes the misses, destroys the exact trust the number is meant to build. Definitions are pinned here and not gamed.

---

## 2. The numbers to produce

From the demo:

| Surface | Number | Kind |
|---|---|---|
| M1 dashboard | "she's holding **23** things for you" | live count |
| M9 done | "TODAY · DONE (**8**)" | windowed count (today) |
| M9 holding | "STILL HOLDING (**3**)" | live count |
| M9 moat | "**247** DAYS WITH DONNA" | derived (now − onboarded) |
| M9 moat | "**1,847** things caught" | lifetime ledger sum |
| M9 moat | "**94%** delivered on time" | lifetime ratio |
| M8/M9 | "₹229/mo saved" / cumulative savings | ledger sum (money) |

Three computation shapes: **live counts** (current open state), **windowed counts** (today/this week), **lifetime aggregates** (the moat).

---

## 3. Definitions (pinned)

| Metric | Definition | Counted when |
|---|---|---|
| **caught** | a proactive intervention Donna surfaced about something the user did **not** initiate (a watch escalation, a scheduled nudge, a cross-connection) **that reached the user** | a proactive message/card is **delivered** (not merely generated). Sub-metric `caught_converted` = the user acted on it. |
| **delivered on time** | of items **Donna owned** that had a deadline (a reminder to fire, a commitment to complete, an action to execute), the fraction resolved at/before deadline | on completion: `on_time` if `completed_at ≤ deadline`, else `late` |
| **on-time %** | `on_time / (on_time + late)` over the lifetime window | derived from the two above |
| **holding** | currently-open items Donna is carrying: active `watches` + open `commitments` + `pending` cards + future not-yet-done `scheduled_tasks` she'll act on | live query, no ledger |
| **done today** | items that moved to a terminal "done/acted/sent/booked" state in the user-local day | windowed query over `actions` / `cards` / `commitments` |
| **days with Donna** | `today − users.created_at`, in days | derived |
| **saved (money)** | concrete, attributable savings: a cancelled unused subscription, a prevented bounce/late fee | ledger row with a ₹ value at the moment of the saving action |

Notes that keep these honest:
- **caught is counted at delivery, not generation** — a heads-up the Notification policy suppressed (quiet hours, over budget) is not a catch; nothing reached the user.
- **caught excludes user-initiated turns** — answering "book me a cab" is service, not a catch. Only the unprompted matters (that's the moat).
- **on-time denominator includes the misses** — `late` is in the denominator. 94% means 6% were genuinely late, shown honestly.
- **saved requires attribution** — only countable, defensible savings (a real ₹ figure), never vague "value."

---

## 4. Architecture — ledger + live + rollup

A hybrid, each shape served by the cheapest correct source:

```text
LEDGER  (metric_events — append-only, source of truth, replayable/auditable per ADR)
   every metric-worthy moment appends one typed row.
        │
        ├──► LIVE COUNTS        holding / done-today: queried directly off the
        │                       operational tables (watches/commitments/cards) — they
        │                       ARE the current state; no ledger needed.
        │
        └──► NIGHTLY ROLLUP     metric_rollup: lifetime totals + windowed counters,
                                materialized from the ledger by a scheduled task
                                (proactive_runner §7) so M1/M9 read O(1), not a heavy scan.
```

- **Ledger** is authoritative and replayable: if a definition changes, recompute the rollup from the ledger.
- **Live counts** never go through the ledger — "holding 23" is a `COUNT` over open rows, always current, can't drift.
- **Rollup** exists only so the dashboard reads are instant; it's a cache of the ledger, rebuildable any time.

---

## 5. Where ledger rows come from (deterministic hooks)

`metric_events` rows are appended by **PostToolUse / Egress side-effect hooks** (ADR — deterministic side-effects, no LLM):

| Hook point | Appends |
|---|---|
| proactive card/message **delivered** (delivery receipt, cards_and_delivery §10) | `caught` |
| user **acts** on a proactive card | `caught_converted` |
| a deadlined commitment/reminder **completes** | `delivered_on_time` or `delivered_late` (compare `completed_at` vs deadline) |
| subscription cancelled / bounce prevented (with ₹) | `saved` (value = ₹) |

These fire from the same deterministic hook layer that writes memory and projects the dashboard — never an LLM, never a separate pass.

---

## 6. The nightly rollup job

The rollup is **a recurring `scheduled_task` driven by the proactive runner** (proactive_runner §7) — this is where the two specs interlock:

```text
daily, ~per user local midnight:
  recompute metric_rollup from metric_events for that user:
    lifetime_caught        = count(kind=caught)
    on_time, late          = count(kind=delivered_on_time/late)
    on_time_pct            = on_time / (on_time + late)
    lifetime_saved         = sum(value where kind=saved)
    days_with_donna        = today − created_at
  write metric_rollup row.
```

Intra-day, the dashboard can read the last rollup + add today's live deltas (cheap) so the numbers feel current without a heavy recompute on every app open.

---

## 7. Schema (extends `database_schema.md`)

```sql
metric_events           -- append-only ledger; source of truth
  id            UUID PK
  user_id       UUID
  kind          TEXT     -- caught | caught_converted | delivered_on_time
                         -- | delivered_late | saved
  value         NUMERIC NULL   -- e.g. ₹ for saved
  ref_type      TEXT     -- watch | card | commitment | action | subscription
  ref_id        UUID     -- the source entity (for audit/drill-down)
  occurred_at   TIMESTAMP
  metadata      JSONB

metric_rollup           -- materialized cache for instant dashboard reads
  user_id            UUID PK
  days_with_donna    INTEGER
  lifetime_caught    INTEGER
  caught_converted   INTEGER
  on_time            INTEGER
  late               INTEGER
  on_time_pct        NUMERIC
  lifetime_saved     NUMERIC
  computed_at        TIMESTAMP
```

Live counts need no schema — they're queries:

```sql
-- holding (M1 "23", M9 "3")
SELECT
  (SELECT count(*) FROM watches      WHERE user_id=$1 AND status='active')
+ (SELECT count(*) FROM commitments  WHERE user_id=$1 AND status='open')
+ (SELECT count(*) FROM cards        WHERE user_id=$1 AND state='pending')
+ (SELECT count(*) FROM scheduled_tasks WHERE user_id=$1 AND status='pending' AND task_type IN (...));

-- done today (M9 "8") — user-local day bounds
SELECT count(*) FROM actions
WHERE user_id=$1 AND created_at >= $local_midnight AND action_type IN ('sent','booked','transferred','cancelled','logged',...);
```

---

## 8. Relationship to `insights`

`database_schema.md` already has an `insights` table ("Spending Increased", "Flight Price Dropped"). Metrics ≠ insights:

- **Metrics** = quantitative counters/ratios (this doc). Deterministic. Shown as the moat numbers.
- **Insights** = narrative observations, possibly produced by the loop. May *cite* a metric ("you've crossed your goal 3 days running" — M4) but live in `insights`.

A metric can feed an insight; an insight never defines a metric.

---

## 9. Demo coverage

| Moment | Source |
|---|---|
| M1 "holding 23" | live holding query |
| M9 "DONE (8)" | done-today query |
| M9 "STILL HOLDING (3)" | live holding query (open subset) |
| M9 "247 days" | `metric_rollup.days_with_donna` |
| M9 "1,847 caught" | `metric_rollup.lifetime_caught` |
| M9 "94% on time" | `metric_rollup.on_time_pct` |
| M8/M9 savings | `sum(metric_events.value where kind=saved)` |

Every number traces to a ledger row or a live count — auditable, honest, no estimation.

---

## 10. Deterministic vs LLM

Entirely deterministic. Ledger appends are hooks; live counts are SQL; the rollup is arithmetic on a scheduled task. **No LLM touches the metrics path.** (An `insight` *about* a metric may cost one loop — but that's the insights path, §8, not this one.)

---

## 11. Out of scope / open

- **Definition tuning of "caught"** is product-sensitive; if the convert-rate (`caught_converted / caught`) is low, the bar for "caught" should rise — that's a product call, made by editing §3, then recomputing the rollup from the ledger.
- **Cross-user / global analytics** (cohort retention, aggregate moat) is a separate analytics concern; this spec is per-user, user-facing.
- **Backfill** for users predating the ledger: seed `metric_events` by replaying historical `events`/`actions` (the event store is replayable per ADR), then rebuild the rollup.
