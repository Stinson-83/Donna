# Donna — Responsibilities Coverage

A living checklist of what Donna can do today vs. the full scope in **`Donna_Responsibilities.md`** (the "what a world-class chief of staff handles" spec). Update this as features land.

**Legend:** ✅ built & tested · 🟡 partial / works via general primitives, no dedicated feature · ❌ missing
**Last updated:** 2026-06-16 · against `main`

**The architectural test** (from the responsibilities doc): *"Is this something a world-class chief of staff would reasonably handle?"* Most 🟡 rows are deliberate — a study deadline and a visa renewal are both just *a task with a due date*; an investor reply and a flight are both just *a watch*. The general engine covers the examples without a bespoke feature per vertical. The real gaps are **channels**, **real-world rails**, and a handful of **specific behaviors**.

---

## Coverage map (21 responsibility areas)

| # | Responsibility | Status | Where it stands · key files |
|---|---|---|---|
| 1 | **Communication** | 🟡 | Email fully real: ingest + `email_importance.py` + draft/`send_email` + reply-watches + escalate. **Missing: Slack / Discord / SMS / calls.** |
| 2 | **Scheduling** | ✅🟡 | `schedule_health.py` (conflict + overload), deadlines, real calendar create/move. **Missing: focus-time protection, multi-party coordination, optimization.** |
| 3 | **Relationships** | ✅🟡 | `living_profile.relationships` + birthday prep (`checks.py`) + `recall_about`. **Missing: neglected-relationship nudge, first-class gift/style fields.** |
| 4 | **Travel** | 🟡 | Flights real engine (`travel/flights.py`, feed sandboxed) + cross-connection. **Missing: trains, hotels, itineraries.** |
| 5 | **Financial** | ✅ | `finance/detector.py` (shortfall, critical) + `finance/waste.py` (duplicate/price-creep/spike). Bank rail sandboxed. |
| 6 | **Health** | 🟡 | Meal check-in only (`checks.py`). **Missing: exercise, sleep, habit tracking.** |
| 7 | **Academic** | 🟡 | Generic (tasks + calendar + deadlines). **Missing: study-schedule builder, progress tracking.** |
| 8 | **Career** | 🟡 | Generic (tasks + watches + interview prep). **Missing: application/interview pipeline.** |
| 9 | **Startup** | 🟡 | Goals + investor reply-watches + meeting prep + cross-connection. **Missing: fundraising-pipeline object.** |
| 10 | **Goals** | ✅ | `knowledge/goals.py` — weights email/watch/attention prioritization + the loop's GOALS prompt block. |
| 11 | **Commitments** | ✅🟡 | Open loops + reply-watches + due tasks. Auto-extraction relies on the loop, not a dedicated miner. |
| 12 | **Documents** | ✅🟡 | `Document` model + Library detail + chunk-recall + deadline-as-task. **Missing: generation.** |
| 13 | **Administrative** | ✅ | Personal-ops: `knowledge/tasks.py` (due-date tasks) + `maybe_surface_due_task`. *Doing* the renewal is manual. |
| 14 | **Memory** | ✅ | Nine backends + cognition beliefs; relevant-time `recall`/`recall_about`. |
| 15 | **Watches** | ✅ | `proactive/watches.py` — reply/web/flight/generic, adaptive cadence. The moat. |
| 16 | **Opportunity** | 🟡 | Interests→web-watch + finance savings (waste). **Missing: general opportunity engine.** |
| 17 | **Risk** | ✅🟡 | Deadlines, payments, travel, doc-expiry covered. Neglected-relationship risk = birthdays only. |
| 18 | **Preparation** | ✅ | `proactive/prepare.py` — night-before / morning-of brief. |
| 19 | **Decision support** | 🟡 | `research` + options cards + the loop. **Missing: structured compare/tradeoff.** |
| 20 | **Execution** | ✅🟡 | L0/L1/L2 gate real (`cards/gate.py`); `send_email` + calendar real; transfer/booking/flowers **sandboxed**. |
| 21 | **Ambient** | ✅ | Runner (9 checks + watch sweep), Morning Brief, Watch Bar (`attention.py`), tiered delivery, learning. |

---

## Gaps backlog (actionable)

### A. Channels — "across your whole digital life"
- [ ] Slack ingest + importance + reply
- [ ] Discord
- [ ] SMS
- [ ] Call awareness (transcripts / missed-call follow-ups)

### B. Real-world execution rails (sandboxed → real)
The engine around each is real; only the third-party account is stubbed (`backend/cards/executors.py`, `backend/travel/flights.py`).
- [ ] Money transfer → real bank/UPI rail (today: writes a ledger row, L0-gated)
- [ ] Restaurant booking → OpenTable (today: real calendar event, no reservation)
- [ ] Ride booking → Grab/Uber (today: real calendar reminder, no car)
- [ ] Flowers/orders → a florist/commerce rail
- [ ] Live flight feed → inject an AeroDataBox/FlightAware provider (`set_flight_provider`)

### C. Vertical depth (currently handled by general primitives)
- [ ] Health: exercise + sleep + habit trackers (today: meals only)
- [ ] Travel: trains, hotels, itinerary builder (today: flights only)
- [ ] Academic: study-schedule builder, progress tracking
- [ ] Career: application/interview pipeline
- [ ] Startup: fundraising-pipeline object (stages, investors, next-actions)

### D. Specific chief-of-staff behaviors
- [ ] Focus-time protection (defend deep-work blocks)
- [ ] Multi-party scheduling / availability coordination
- [ ] Neglected-relationship nudge (beyond birthdays)
- [ ] Document generation (drafts, briefs, forms)
- [ ] Structured decision-compare (flights/hotels/tools — options + tradeoffs)
- [ ] Dedicated commitment extractor on every inbound message

### E. Frontend / surfaced state
- [ ] Resurface the **Memory** tab (backend live, UI parked) + wire the constellation to `/cognition/graph` and back the "areas" index with a real source
- [ ] Surface the **Beliefs** tab (built, real-backed via `useRemote`, unmounted)

### F. Context / Adaptive layer (`docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md`) — IN PROGRESS
- [x] **Slice 1**: the `contexts` store + deterministic engine (infer/decay/focus windows) + `context_weight`; wired into **prioritization** (rank_attention / Watch Bar), **email importance**, the **`## CONTEXT` prompt block**, and the **tick refresh**; `set_focus` tool. (`backend/knowledge/context.py`, `db.models.Context`, migration 0012)
- [x] **Slice 2**: context modifier on **watch cadence** (relevant watches check sooner) + the **delivery tier** (focus-relevant surfaces interrupt; off-focus surfaces during a declared focus go quiet; critical unmoved). (`watches.py`, `notify.py`, `delivery_policy.shift_tier`)
- [x] **Slice 3**: **confirmation cards** — when an inferred *significant* season (travel / fundraising / exam / job-search / launch / wedding) crosses the confidence threshold, a deterministic tick check asks once via the loop; a tap pins (`source=confirmed`) or damps (declined + sticky) the season with no second LLM call. Confirmed seasons decay+close when their signal lapses; silence leaves the inferred weighting in place. (`context.confirmable_context`/`confirm_context_kind`/`decline_context_kind`, `proactive/context_confirm.py`, `cards/executors.confirm_context`/`decline_context`)
- [x] **Slice 3b**: **context-aware retrieval pointers** — Context Assembly attaches a `## RELEVANT NOW` block to the per-turn (Trigger-tier) context: for the top active seasons, cheap title/ref pointers to the watches she's running, open commitments, and upcoming events that match the season's domain. Pointers, never a brief (ADR §5); zero LLM; the loop still does deep recall via `recall_*`. (`context.context_pointers`/`render_context_pointers`, wired in `donna_runtime/context_builder.render_turn_context`)
- [x] **Slice 3c**: **richer signal inference** — `_infer` now aggregates across all the signals the system already produces (upcoming calendar generalized to every season, active watches, goals, and recent inbound **email/thread density** — the "≥N recruiter threads ⇒ job_search" rule), each emitting a per-season prior combined via **noisy-or** (corroborating signals can cross the confirm bar; a lone weak one only nudges), capped below a user confirmation. (`backend/knowledge/context._infer`)

---

## Architectural health

Every responsibility maps cleanly onto the existing spine (**memory · watches · engines · the L0/L1/L2 gate · the one BRAIN loop**). Nothing in the backlog requires a second reasoning site or an engine-as-LLM pipeline — new verticals are new deterministic detectors/tools feeding the same loop. The proactive/ambient layer is real. So this passes the structural sanity check: the gaps are **breadth + rails**, not foundations.

## How to maintain this file
When a feature lands: flip its row to ✅ with the file pointer, check off the backlog item(s), and bump *Last updated*. When a new responsibility is proposed, apply the doc's test — *would a world-class chief of staff handle it?* — and if yes, add a row.
