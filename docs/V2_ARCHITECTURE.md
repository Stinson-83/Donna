# Donna V2 — Backend Architecture

The single source of truth for how V2 (`donna-demo-v2.md`) is built on the
backend. V2 is a **proactive, agentic life-agent**: she texts first, she takes
action, she remembers across months. Two app surfaces — **Dashboard** (what she's
holding) and **Live** (agentic action) — plus **WhatsApp** (proactive pings) and
**Dynamic Island** (iOS, later).

The product feeling we build toward: *"she caught that — how did she catch that."*

---

## 1. The core principle — one loop, many tools, many triggers, few subagents

The 9 moments are **not 9 agents.** They are one agent (Donna) exercising
different tools, started by different triggers. What varies:

- **What starts it** — a user message (Live/WhatsApp) *or* an event (email
  arrived, bill due, it's 1:42pm). → a **trigger**, not an agent.
- **What she does** — book a ride, transfer money, log a meal, draft a reply. →
  a **tool**, not an agent.
- **What never changes** — her memory, her voice, her judgement. → the **one loop**.

```
ONE loop (Donna's reasoning)   ── donna_runtime/  (already built on the Claude Agent SDK)
   + MANY tools                ── one per capability
   + MANY triggers             ── one per proactive source
   + a FEW subagents           ── only for heavy, isolatable jobs (research, high-stakes drafting)
```

**Do not build a framework on top of the SDK.** The Claude Agent SDK *is* the
agentic framework — the `query` loop does multi-step reasoning internally. Our job
is to organize capabilities *around* that loop, never to wrap it in an
orchestrator/router (that path reinvents LangGraph and is explicitly forbidden in
`CLAUDE.md`). "A framework per moment" collapses into **good folder structure for
tools + triggers + integrations.**

We do **not** start from scratch. `donna_runtime/` already is a working SDK agent
(loop, `@tool` MCP server, hooks, `mode="proactive"`, sessions, memory, WhatsApp
delivery, Composio OAuth, tracing). We keep the engine, retire the old UI and the
belief-native framing, and build V2 as new tools/triggers/integrations on top.

## 2. The mental model — how everything connects

Every moment, reactive or proactive, flows through the same spine:

```
 EVENT                              or   USER MESSAGE (Live tab / WhatsApp)
 (email arrives, bill due, 1:42pm)
        │                                       │
        ▼                                       ▼
   TRIGGER (detect + score)  ───────────────►  THE LOOP  (Donna, SDK)
   backend/triggers/*                          donna_runtime/  (mode = proactive | reactive)
                                                   │  reasons, recalls memory
                                                   ▼
                                               TOOLS  (book_ride, transfer, log_meal, draft_reply)
                                                   │
                                                   ▼
                                          INTEGRATION ADAPTER  (Mock now → Real later)
                                               backend/integrations/{grab,bank,fnp,opentable}.py
                                                   │
                                 ┌─────────────────┼──────────────────┐
                                 ▼                 ▼                  ▼
                            ACTIONS LOG        DASHBOARD            SURFACE
                          "1,847 caught"   watching/scheduled/   WhatsApp CTA /
                          backend/actions   logistics/done       Live card / push
                                            backend/dashboard
```

Reactive (Live tab) and proactive (triggers) **both route through the one loop**.
Triggers + surfaces are the I/O; tools + adapters are the hands; the loop is the
brain. The **actions log** and **dashboard** are the shared state both proactive
catches and agentic actions write to.

## 3. The two patterns that make it scale

Every one of the 9 moments is built from these. Get them right once; the rest is
copy-fill-ship.

### a. Integration adapter (mock ↔ real)
Every external action (Grab, OpenTable, FNP, bank, Spotify) implements one small
interface with a **Mock** and a **Real** implementation, chosen by config. The
*tool* and the *agent* never change when we go demo → production — we swap the
adapter. This is what lets us ship the demo on mocks and go real later.

```python
# backend/integrations/base.py
class RideAdapter(Protocol):
    async def quotes(self, frm, to, when) -> list[RideQuote]: ...
    async def book(self, quote_id) -> Booking: ...

# grab.py provides MockGrab (canned, convincing) and RealGrab (live API).
# get_ride_adapter() returns one based on settings — the tool calls the interface.
```

External APIs we will **mock for the demo** (no clean agent API exists): Grab,
OpenTable, FNP flowers, HDFC transfers, Spotify cancel. **Real now:** Gmail +
Calendar (via Composio). The mock returns a convincing confirmation and logs to
the actions feed, so the dashboard updates for real.

### b. Trigger / producer (proactivity)
Each proactive source is a small module that **detects an event, scores it, and
invokes the loop in `mode="proactive"`** with the event as context. A scheduler
(`backend/triggers/heartbeat.py`, run by the existing worker process) drives the
time-of-day ones — the "she texts first" heartbeat that produces the day arc.

```python
# backend/triggers/bill_watcher.py
async def check(user_id):
    bill = await find_due_soon(user_id)
    if bill and short_on_balance(bill):
        await run_proactive(user_id, trigger=Trigger("bill", bill))  # → the loop
```

## 4. Project structure (target)

`KEEP` = spine, unchanged. `NEW` = build for V2. `RETIRED` = moved to `archive/`.

```
donna_runtime/          KEEP   the SDK engine: brain, runner, options, hooks, prompt
  tools.py                     existing tools (split into tools/ package incrementally)
  tools/                NEW      actions.py (book_ride, transfer, send_gift, cancel_sub, draft_reply)
                                 trackers.py (log_meal + calorie math)
  subagents/            NEW      heavy isolatable jobs only (research, high-stakes drafting)

donna/                  KEEP   attention engine → powers the dashboard "watching" section

backend/
  memory/               KEEP   recall / episodic / graph — memory cross-connection (M5, M7)
  integrations/         KEEP+NEW  Composio (real) + leaf adapters:
    base.py             NEW      adapter Protocols (Ride/Reservation/Gift/Payment/Subscription)
    grab.py opentable.py fnp.py bank.py   NEW  Mock + Real impls
  triggers/             NEW    proactive producers:
    email_watcher.py             M2 (from proactive_email_trigger)
    bill_watcher.py              M3
    tracker_prompter.py          M4
    subscription_watcher.py      M8
    calendar_watcher.py          M7 cross-connection
    heartbeat.py                 the time-of-day scheduler ("she texts first")
  dashboard/            NEW    aggregation: watching / scheduled / logistics / done + stats
  actions/              NEW    the actions log ("1,847 things caught") + agentic helpers
  cognition/            KEEP   memory/observations/trackers engine (beliefs UI retired, engine reused)

api/                    KEEP+NEW  add /dashboard, /live (chat), /consent ; keep webhooks
delivery/  db/  ingress/  KEEP
scripts/                KEEP   CLI/dev entry points + the worker that runs triggers
```

New DB models (in `db/models.py` or `backend/cognition/store.py`): `Obligation`
(logistics — bills/renewals/deadlines), `Action` (the audit log), `Tracker`.

## 5. Build order — vertical slices, not all 9 at once

Build **one moment end-to-end through the real spine**, prove the architecture,
then the rest are copies of the pattern.

1. **Moment 4 — tracker check-in (FIRST).** Exercises the *entire* spine —
   trigger (1:42pm) → proactive loop → tool (`log_meal` + calorie math) → memory
   ("day 3 over goal") → WhatsApp surface — with **no external integration**. The
   V2 doc itself says shoot this first. Validates everything except the adapter.
2. **Moment 3 — bill watcher / payment.** Adds the **Integration adapter** pattern
   (mock bank) + consent. After this, the mock↔real seam is proven.
3. **Moment 6 — Live tab cab booking.** Adds **consent cards + JIT interactive
   cards** + the Live surface. The investor centerpiece.
4. **Moments 1 & 9 — dashboard + day-close stats.** The aggregation surface +
   actions log; mostly reads, once the writes from 1–3 exist.
5. **Moments 2, 7, 8 — email flag, cross-connection, unsubscribe.** Each is now
   "new trigger + new tool + new mock adapter," copy-fill-ship.
6. **Moment 5 — Dynamic Island.** iOS-native (Live Activities) — out of reach on
   Android/Capacitor; a UI mockup for the video until there's an iOS build.

## 6. What was retired in the V2 cleanup

| Item | Disposition | Why |
|---|---|---|
| `dashboard/` (Next.js frontend) | → `archive/v1/` | superseded; teammate builds the V2 frontend fresh |
| `docs/PRODUCT.md`, `dashboard-research.md`, `dashboard-sprint-notes.md`, `codebase-mind-map.md` | → `archive/v1/` | belief-native v1 product/UI specs, superseded by `donna-demo-v2.md` |
| `donna-debug.apk`, `donna_traces.jsonl`, `donna_gate.jsonl` | deleted | untracked local build/trace artifacts |
| `webapp/` belief-native `src/` UI | deprecated, kept | its Capacitor/Android shell is reused; the teammate's V2 frontend drops into it, replacing `src/` |

**Kept (the V2 spine):** `donna_runtime`, `donna` (attention), `backend`
(memory/integrations/cognition), `delivery`, `db`, `ingress`, `api`, `scripts`,
and the dev CLIs (`chat_donna.py`, `donna.py`, `stream_donna.py`).

The cognition belief *engine* is kept (memory/observations/trackers are reused by
V2); only the belief-native *UI and framing* are retired. The `form_belief` tool
and the demo seed remain valid.
