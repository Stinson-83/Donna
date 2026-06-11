# Proactive Runner & Scheduler — the "she texts first" engine

**Status:** Spec · 2026-06-11
**Depends on:** `architecture_decision.md` (§4 path, §6 Watch/Dynamic-Check/Notification engines, §10.2 LISTEN/NOTIFY outbox, §10.3 gate), `cards_and_delivery.md` (Notification policy, delivery), `event_system.md` (Watcher + Scheduler event sources).
**Fills:** the review gap "no worker drives watches/scheduled_tasks." This is the loop that makes Donna proactive — the source of every moment the user didn't initiate (M2/M3/M4/M7/M8/M9).

---

## 1. What this is

Donna's tagline is "she texts first." Something has to *wake her up* when there is no user message. That something is the **Proactive Runner**: a deterministic background worker that continuously asks "is anything due to be evaluated right now?" and, when yes, **emits an event** into the bus.

It is the implementation of `event_system.md`'s Source Type 3 (Watchers) and Type 4 (Scheduler).

> **The runner dispatches; it never reasons.** It fires events. The workflow and the BRAIN loop do the thinking (ADR §2). The runner contains zero prompt logic and makes zero LLM calls. This is what keeps 24/7 proactivity affordable.

---

## 2. Core principle: three gates between a tick and a text

The danger (vision.md): "never a notification machine." Proactivity must not become spam. The safeguard is that a tick is far from a text — three independent gates sit between them:

```text
TICK (runner)            emits an internal event        — cheap, 24/7, never disturbs the user
   ↓
WORKFLOW + BRAIN LOOP    decides IF this is worth saying — terminator: send_burst vs stay_silent
   ↓
NOTIFICATION POLICY      decides WHEN/WHETHER to deliver — quiet hours · interrupt budget · batching
   ↓
the user hears from her  — only if all three agree
```

Gate 1 is free (internal events). Gate 2 is the one loop (per event, per ADR budget). Gate 3 is deterministic policy (cards_and_delivery §8). "She texts first" is gate-1 firing constantly; "she isn't annoying" is gates 2–3 filtering hard.

---

## 3. What the runner sweeps

Two tables, both already in `database_schema.md`:

1. **`watches`** — ongoing situations to monitor. Each has a `next_check`. When `now ≥ next_check`, the watch is *due*.
2. **`scheduled_tasks`** — future one-shot or recurring executions (reminders, the 11pm summary, the lunch check-in, birthday lead-time). When `now ≥ execute_at`, the task is *due*.

The runner claims due rows, acts on them, and re-arms or completes them.

---

## 4. The tick loop

```text
every TICK_INTERVAL (≈30s; fine enough for the tightest cadence of "every 5 min"):
  claim due rows  (FOR UPDATE SKIP LOCKED) from watches WHERE next_check ≤ now()
                  and scheduled_tasks WHERE execute_at ≤ now() AND status='pending'
  for each watch:        run Watch Evaluation (§5)
  for each task:         fire the task's event, then complete or reschedule (§9)
```

- **Claim-before-act.** `SELECT … FOR UPDATE SKIP LOCKED` lets multiple runner instances share the load with no double-processing and no leader election (same pattern as the event-bus consumers, ADR §10.2).
- **Advance before emit.** A claimed watch's `next_check` (or task's `status`) is advanced **in the same transaction** as the claim, before the event is emitted, so a crash mid-emit can't double-fire. The emitted event also carries an idempotency key `(watch_id, scheduled_check_ts)` so the bus dedups a retry.
- **Fixed interval, adaptive cadence.** The tick is a simple fixed interval; the *per-watch* cadence is encoded in each `next_check` by the Dynamic Check policy (§6). A 30s tick easily serves a 5-min watch and a daily watch from the same loop.

---

## 5. Watch evaluation — the cost-critical part

When a watch wakes, **we do not run the BRAIN loop.** That would mean an LLM call every 15 minutes for a flight watch — unaffordable and pointless. Evaluation is two layers:

```text
Watch due
  ↓
LAYER 1 — deterministic diff (NO llm)
  fetch current state of the watched thing (from cache the integration webhooks keep warm,
  or a cheap read), compare to watch.last_known_state.
  ↓
  Material change?
    NO  → update last_checked_at, recompute next_check (§6), DONE.    ← the common case, ~free
    YES → update last_known_state, emit a DOMAIN event
          (low_balance_vs_bill | flight_delayed | subscription_renewing | deadline_near | …)
          ↓
LAYER 2 — the domain event routes to its workflow → ONE BRAIN loop (ADR §4)
          which decides what (if anything) to tell the user.
```

The vast majority of ticks end at Layer 1 with no event and no LLM. Layer 2 — the expensive part — only runs on a real, material change. "Material" is a deterministic threshold per watch type (balance crosses the shortfall line; flight status string changes; renewal date enters the lead window; deadline crosses a notify threshold).

This is the literal implementation of `workflows.md`'s "Has Something Changed? If No: recalc next_check. If Yes: Emit Event."

---

## 6. Dynamic Check — concrete cadence policy

The Dynamic Check engine (ADR §6, a deterministic function) sets `next_check` after every evaluation. `engines.md` left the formula hand-wavy; here it is concretely:

```text
base cadence by time-to-deadline:
   > 30 days   → every 24h
   7–30 days   → every 12h
   1–7 days    → every 3h
   < 24 hours  → every 30 min
   < 2 hours   → every 5 min

then modulate:
   importance high   → halve the interval (check more)
   importance low    → double it
   recent change     → halve (volatile, watch closer)
   N stable checks   → back off (×1.5 each, capped at base)   ← avoid pointless polling
   no deadline       → fixed by watch_type default (e.g. finance daily, relationship daily)

next_check = clamp(now + modulated_interval, min=5min, max=24h)
```

Pure arithmetic, no LLM. The "trip in 6 months → daily, trip tomorrow → every 15 min" example from `engines.md` falls straight out of this.

---

## 7. Where proactive triggers come from

Three creators of watches/scheduled_tasks — all cheap, none require the user to ask:

1. **The BRAIN loop, via tools.** During any turn the loop may call `create_watch` / `schedule`. *Investor: "we'll get back Friday"* → loop creates a `waiting_for_reply` watch. This is the reasoning-driven source.

2. **Recurring system schedules.** Per-user recurring `scheduled_tasks` seeded at onboarding / from config: the **11pm daily summary** (M9), the **lunch check-in** (M4), the morning dashboard refresh, the **metrics nightly rollup** (drives `metrics.md`). Stored with a recurrence rule + user timezone.

3. **Lead-time derivation (deterministic pass).** A periodic job scans structured dates and creates lead-time watches/tasks **without the loop**: birthdays in `relationships` → "order gift" lead window (M7 flowers Friday for a Saturday birthday); bill due dates → finance watch (M3); subscription renewal dates → renewal watch (M8); flight dates → travel watch. This is what makes M3/M7/M8 proactive — Donna derives the trigger from data the integrations already gave her.

---

## 8. Anti-spam: quiet hours, interrupt budget, batching

Gate 3 (§2) is the Notification policy (cards_and_delivery §8), deterministic, applied at delivery:

- **Quiet hours** — per user, in their timezone (`users.timezone`). A non-urgent proactive message generated at 2am is **held** until the morning window; an L0/urgent one (fraud, flight in 2h) may override. The 11pm summary (M9) is explicitly inside the allowed window; the lunch check (M4) fires at lunchtime-local.
- **Interrupt budget** — a per-user/day cap on proactive interruptions. Over budget → low/medium items are **bundled** into the next digest instead of pinging individually. Critical items always pass.
- **Batching** — multiple low-importance items in a window coalesce into one message ("3 things for you this morning") rather than three buzzes.
- **De-dup** — the same situation must not nag twice; a watch that already notified holds until its state *changes again* (tracked via `last_known_state`).

The runner emits freely; this gate is where "texts first" stays "welcome," not "noisy."

---

## 9. Reliability

- **Misfire policy (one-shot tasks).** Each `scheduled_task` carries a `misfire_policy`: `catch_up` (fire late, e.g. the 11pm summary you missed → send at 11:40), or `skip_if_missed` (a 1:42pm lunch nudge at 4pm is pointless → skip, maybe log). On runner downtime + restart, overdue tasks are resolved by their policy, not blindly fired.
- **Catch-up without thundering herd.** On restart the runner finds all overdue rows; it processes them in claim batches (SKIP LOCKED) so multiple instances share the backlog and nothing stampedes.
- **Idempotency.** Advance-before-emit + an event idempotency key per `(watch_id, check_ts)` / `(task_id, occurrence)` means a race or retry fires once.
- **Multi-instance.** Run N runners; SKIP LOCKED makes them cooperative. No leader.
- **Timezone correctness.** All recurring/quiet-hours math is in user-local time. "Call mom at noon," lunch check, quiet hours all resolve per `users.timezone`.

---

## 10. Schema (extends `database_schema.md`)

Mostly additive columns on existing tables.

```sql
watches  (add)
  last_checked_at   TIMESTAMP
  last_known_state  JSONB        -- for the deterministic diff (§5)
  stable_checks     INTEGER      -- consecutive no-change checks → cadence backoff (§6)
  cadence_policy    JSONB        -- overrides / watch_type defaults
  -- existing: next_check, importance, deadline, status, metadata

scheduled_tasks  (add)
  recurrence        TEXT NULL    -- rrule/cron; NULL = one-shot
  timezone          TEXT         -- resolve recurrence + quiet hours in user-local
  misfire_policy    TEXT         -- catch_up | skip_if_missed
  idempotency_key   TEXT         -- per occurrence
  -- existing: execute_at, task_type, payload, status

user_settings  (new — or columns on user_model)
  user_id           UUID
  quiet_hours       JSONB        -- {start, end} in tz
  interrupt_budget  INTEGER      -- max proactive pings/day before bundling
  channels          JSONB        -- per-surface opt-in
```

No new bus or queue — it rides the §10.2 events table + LISTEN/NOTIFY.

---

## 11. Demo coverage

| Moment | Trigger path |
|---|---|
| **M2** sequoia | email is inbound (webhook), but its "answer by EOD / term sheet expires noon" makes the loop create a deadline watch → runner escalates as the deadline nears |
| **M3** AWS bill | lead-time derivation creates a finance watch on the bill due date → Layer-1 diff detects balance < bill → `low_balance_vs_bill` → loop → approval card |
| **M4** lunch | recurring `scheduled_task` at lunchtime-local → `health_checkin` event → loop asks "what did you have?" |
| **M7** mom's flowers | birthday in `relationships` → lead-time watch fires Friday → cross-connection in the loop (dinner Saturday, likes lilies) → approval card |
| **M8** Spotify | renewal-date watch enters lead window → `subscription_renewing` → loop (usage low, Apple Music preferred) → confirm card |
| **M9** day close | recurring `scheduled_task` at 11pm-local → `daily_summary` event → summary workflow → dashboard + the moat card (`metrics.md`) |

Every proactive moment is one runner-emitted event → one loop. None polls an LLM.

---

## 12. Deterministic vs LLM

| Step | LLM? |
|---|---|
| Tick, claim, advance | no |
| Watch Layer-1 diff | no |
| Dynamic Check / next_check | no |
| Lead-time derivation | no |
| Quiet hours / budget / batching | no |
| Watch Layer-2 (on material change) | one loop, per event |
| Recurring task firing | no (the *workflow* it triggers may run one loop) |

The runner itself is 100% deterministic. LLM cost is incurred only when a real change or a scheduled moment routes into a workflow — exactly the ADR budget.

---

## 13. Out of scope / open

- **Integration polling vs webhooks.** Layer-1 diffs prefer a webhook-kept-warm cache; which sources are push (Gmail, calendar) vs pull (banking) is an integration detail, not a runner change.
- **Precision tuning.** The "material change" thresholds and interrupt budget defaults are the levers for the proactive-precision eval (review's missing eval harness) — tune there, not in the runner.
- **Per-surface quiet hours** beyond a single window is a settings refinement.
