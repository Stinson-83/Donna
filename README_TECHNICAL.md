# Donna — Technical README

Engineering companion to [`README.md`](./README.md). This document explains how the system is built: the architecture, the request path, every engine/tool/hook, the memory layers, the integrations, what's real vs. sandboxed, and how to run and test it.

The **canonical, authoritative** architecture spec is [`docs_v2/architecture_decision.md`](./docs_v2/architecture_decision.md) (the ADR). Where this README and the ADR disagree, the ADR wins. The adaptive/context layer design is in [`docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md`](./docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md). Product definition is in [`CLAUDE.md`](./CLAUDE.md).

---

## 1. The one architectural rule that explains everything

> **Reasoning happens in exactly ONE place: a single Claude Agent SDK tool-use loop (the BRAIN). Everything else is deterministic machinery around that loop — never a second LLM call.**

The product reads like it has "~25 engines" (Importance, Cross-Connection, Decision, Notification…). **None of them is an LLM call.** Each is reclassified as one of: a deterministic service, a tool, a hook, a prompt section, or a retrieval query — and folded into or around the one loop. (Full reclassification table: ADR §6.)

Consequences that fall out of this rule:
- **One synchronous LLM call per event** (the BRAIN loop), plus at most **one async, cheap memory-extraction call** after. No engine pipeline.
- **Main model: Haiku 4.5** (`claude-haiku-4-5-20251001`). Sonnet only for declared upgrade cases; Opus only inside a justified subagent.
- **Cost target: < $0.01 per reactive turn** with prompt caching.
- The "engines" are deterministic and individually unit-testable; the loop is the only place meaning is interpreted, importance weighed, facts connected, or actions chosen.

---

## 2. The request path (the spine)

Both flows below run the **same** BRAIN loop. The only difference is what wakes it.

```
 Event source: integration webhook · scheduler tick · watch · user message
        │
        ▼
 INGRESS              normalize · dedup · idempotency key            (deterministic)
        │
        ▼
 events table + Event Bus   (Postgres LISTEN/NOTIFY over a durable outbox; ADR §10.2)
        │
        ▼
 ROUTER              event_type → workflow                          (deterministic dict)
        │
        ▼
 CONTEXT ASSEMBLY    attach the stimulus + cheap pointers, NO LLM   (pure retrieval)
        │
        ▼
 ┌──────────────────────────────────────────────────────────┐
 │  BRAIN LOOP  (Haiku 4.5, Claude Agent SDK)  — ONLY reasoning │
 │   cached system prompt = identity + Living Profile          │
 │   tools: retrieval · action · live-lookup · terminators     │
 │   PreToolUse hooks:  Safety gate · Consent gate  (can BLOCK) │
 │   PostToolUse hooks: memory write · dashboard · audit       │
 └──────────────────────────────────────────────────────────┘
        │
        ▼
 TERMINATOR          send_burst (reply) | render_card (decision card)
        │
        ▼
 EGRESS              deliver to surface  +  async memory extraction (one cheap call)
```

- **Reactive** enters at the top via a user message (`POST /chat`).
- **Proactive** enters via the scheduler/watch tick and runs the loop with `mode="proactive"`.

### Reactive flow (you → Donna), concretely
`api/chat.py` → resolve identity → enrich state → **context assembly** (`donna_runtime/context_builder.py`, retrieval only) → **`donna_runtime/brain.donna_turn`** (the SDK loop) → tools execute under PreToolUse gates → loop ends with a terminator → outbound delivered on the surface you messaged from → async memory extraction + a parallel ingest into the cognition model.

### Proactive flow (Donna → you), concretely
`backend/proactive/runner.py` ticks: for every active user, run the **9 checks** + sweep due **watches**. A deterministic detector decides *whether* to fire; if it does, it builds a `[SYSTEM TRIGGER: …]` stimulus and calls the **same loop** in proactive mode. The loop reasons and renders a card/burst. Delivery is **tiered + single-surface** (see §6).

---

## 3. The BRAIN loop & its tools

- Loop: `donna_runtime/brain.py` (`donna_turn`). Options/MCP server assembly: `donna_runtime/options.py`. System prompt: `donna_runtime/prompt.py`. Config + the tool allow-list: `donna_runtime/config.py`.
- Tools are registered as an in-process MCP server (`DONNA_TOOLS` in `donna_runtime/tools.py`). The allow-list (`ALLOWED_TOOLS`) must stay in exact sync with the registered set — guarded by `tests/test_tool_allowlist.py`.

**The 18 tools, by category** (each tool's description carries its own when-to-use **and** when-NOT-to-use):

| Category | Tools | Purpose |
|---|---|---|
| **Retrieval** (read) | `recall`, `recall_about`, `read_connections`, `check_calendar` | Semantic memory, everything-about-one-entity, what an event touches, calendar |
| **Action** (write) | `remember`, `watch`, `schedule`, `track_goal`, `track_interest`, `track_task`, `track_flight`, `form_belief`, `image` | Store facts/loops, create watches/reminders, goals, interests→web-watches, admin tasks, flight tracking, beliefs, image gen |
| **Live lookup** | `web_search`, `agentic_web_search`, `research` | Real-world facts via Exa (single / multi-source / deep) |
| **Terminators** | `send_burst`, `render_card` | End the turn: a spoken reply, or an interactive decision card |

The loop never returns prose to the user except through a terminator. `render_card` is how the L0/L1/L2 gate becomes a tappable UI surface.

---

## 4. The engines (all deterministic; all tested)

These are the "noticing" and "ranking" services. **No LLM in any of them** — they emit signals/stimuli; the loop does the reasoning. Each has unit tests in `backend/tests/integrations/`.

| Engine | File | What it does |
|---|---|---|
| **Finance — shortfall** | `backend/finance/detector.py`, `trigger.py` | Auto-pay bill due soon + paying account short → L0 transfer-approval stimulus |
| **Finance — waste** | `backend/finance/waste.py` | Recurring-charge derivation → double-charge / duplicate-service / price-creep / spending-spike |
| **Schedule health** | `backend/proactive/schedule_health.py` | Calendar overlap (conflict) + back-to-back overload, all-day banners excluded |
| **Preparation** | `backend/proactive/prepare.py` | Night-before / morning-of brief for the soonest un-prepped event |
| **Cross-connection** | `backend/knowledge/connections.py` (+ `proactive/cross_connect.py`) | `find_connections`: conflicts / temporal neighbors (old-time-aware) / shared-entity links; fires on a calendar time-shift |
| **Attention ranker** | `backend/knowledge/attention.py` | One goal-weighted priority score across pending cards + watches + due tasks → the Watch Bar (`/watchbar`) |
| **Morning Brief** | `backend/proactive/morning_brief.py` | Composes the top ranked items into one daily, waking-hours, once/day delivery |
| **Goals → prioritization** | `backend/knowledge/goals.py` | `relevant_goals`/`goal_keywords`: a goal-relevance term added to email importance + watch importance |
| **Learning from feedback** | `backend/knowledge/feedback.py` | Aggregates card `intent`+`state` (acted/dismissed) → learned-preferences prompt block + raises the proactive-email bar |
| **Watches** | `backend/proactive/watches.py` | CRUD + adaptive `compute_next_check`; evaluators: reply / web / flight / generic; `sweep_due_watches` |
| **Email importance** | `backend/integrations/email_importance.py` | Pure scorer (label, sender, open-loop match, **goal match**) → proactive-email threshold |
| **Tiered delivery** | `backend/integrations/delivery_policy.py` + `notify.py` | Priority → interrupt vs. quiet; single-surface (no double-buzz) |

**The proactive tick** (`backend/proactive/runner.py`) runs these 9 checks each cycle + the watch sweep:
`morning_brief · finance_shortfall · finance_waste · schedule_health · prepare · due_task · meal_checkin · birthday · watch_interests` → `sweep_due_watches`.

---

## 5. Memory (nine backends) + cognition

The "Living Profile / User Model" is the **standing** context (cached system prompt). Deep memory is pulled **only via `recall_*` tools** (never pre-stuffed). Three context tiers: Standing (profile) · Trigger (the event + cheap pointers) · Deep recall (tool calls). See ADR §5.

**Nine backends** (all active; ADR §10.1):
1. Graphiti (entities + graph, FalkorDB) · 2. Supermemory (episodic) · 3. Supermemory (document chunks) · 4. Procedural rules (Postgres, three tiers) · 5. Observations · 6. Open loops · 7. User facts / Living Profile (Postgres JSONB) · 8. Chat messages · 9. Calendar (synced from Google).

**Cognition (the beliefs subsystem)** — `backend/cognition/`. Mounted at `/cognition/*` (`api/main.py`). It is the "beliefs are the product" engine:
- **Write path is live:** the BRAIN's `form_belief` tool writes observations → recomputes beliefs → detects questions; every chat/journal/voice message ingests into it (`api/chat.py`, `pipeline.ingest`).
- **Belief formation lives in the loop** (`form_belief`), not a keyword miner. The legacy deterministic miner is retired to opt-in (`mine=True`, used only for seeding/tests) — see `backend/cognition/pipeline.py`.
- Read endpoints (`/cognition/beliefs`, `/questions`, `/memory`, `/graph`, `/plan`, …) back the (currently parked) Memory/Beliefs UI.

---

## 6. Execution gate & delivery

**Agency gate (ADR §10.3)** — a deterministic PreToolUse hook classifies every action by tool+args. The loop proposes; the gate enforces; the user's tap on an L0/L1 card is the execution trigger. Files: `backend/cards/gate.py` (classify), `resolution.py` (resolve a tap), `executors.py` (the rails).

| Tier | Rule | Trigger |
|---|---|---|
| **L2 auto** | low-risk, reversible, explainable | execute then report |
| **L1 confirm** | acts toward a third party as the user / not trivially reversible | propose card → execute on tap |
| **L0 approve** | money / legal / irreversible | hard-gated approval card every time |

**Tiered, single-surface delivery** (`backend/integrations/delivery_policy.py`, `notify.py`):
- `critical`/`high` → interrupt (push or WhatsApp send). `medium`/`low` → **held** (no buzz; the card still persists on the dashboard + watch bar).
- A proactive message reaches the user on **exactly one** surface (app push if installed, else WhatsApp), ordered by the user's `notify_channel` preference (`auto | app | whatsapp`). No double-buzz.

---

## 7. Integrations & what's real vs. sandboxed

Config + secrets: `config.py` (Pydantic settings; env-driven). A missing key degrades to a safe no-op, never a crash.

| Integration | Status | Needs |
|---|---|---|
| **Anthropic (the BRAIN)** | Real | API key |
| **Composio → Gmail** | Real: ingest + importance + `send_email` | `composio_api_key` + user OAuth |
| **Composio → Google Calendar** | Real: ingest + event creation | same |
| **Exa → web** (`web_search`/`agentic_web_search`/`research`) | Real | Exa key |
| **FCM push** | Real, else silent no-op | `fcm_service_account_json` |
| **WhatsApp Business** | Real, else no-op | `whatsapp_token` + IDs |
| **Postgres** (domain + memory tables) | Real | DB URL |
| **Graphiti/FalkorDB, Supermemory** | Real | service URLs/keys |

**Action executors** (`backend/cards/executors.py`) — the honest boundary. The *engine* is real; some third-party *rails* are sandboxed pluggable stubs:
- `send_email` → **REAL** (Composio Gmail send).
- `book_restaurant` / `book_ride` → write a **REAL Google Calendar event/reminder**; the reservation/ride rail (OpenTable/Grab) is **not connected** — the calendar entry is the real artifact.
- `transfer` → **sandbox** (writes a `transactions` ledger row; does not move real money). L0-gated.
- `order_flowers` → **sandbox** (no florist rail).
- **Flight status** (`backend/travel/flights.py`) → real engine, **no live feed by default**: `get_flight_status` returns `None` until `set_flight_provider()` injects an adapter (AeroDataBox/FlightAware) or a fixture.

---

## 8. Frontend

`webapp/` — React 18 + Vite + Tailwind + Capacitor (mobile shell). Design tokens from `donna-design-spec`.

- **Tabs:** Dashboard (`TodayPage`) · Live (`LivePage`) · History (`HistoryPage`). **Memory** and **Beliefs** pages are built but **parked** (not in the nav).
- **Library drawer** (`components/Drawer.jsx`): People / Documents / Trackers / To-dos / Connected + Settings, with detail screens backed by `/library/*`.
- **Watch Bar** (`components/WatchBar.jsx`): pinned "what matters now" strip, backed by `/watchbar`.
- **API clients:** `src/cards.js` (cards/watches/today/history/library/watchbar/settings), `src/cognition.js` (beliefs/memory/plan — for the parked screens).
- **MOCK switch:** `src/api.js` — `MOCK = import.meta.env.VITE_MOCK !== '0'`. **Default is MOCK ON**: every client returns bundled fixtures so the UI runs with no backend. Set `VITE_MOCK=0` (+ `VITE_API_BASE`) to hit the live API; each `useRemote(realFetcher, mockFallback)` then swaps to live data when the backend returns any.
  - Mock fixtures: `src/data/mockData.js` (Memory/Plan/Beliefs/chat) and the `MOCK_*` constants in `src/cards.js`. The demo persona is one consistent person (*aarav · poke · Sequoia · Raghav · Aniroodh · the Waterloo move*).
  - Still mock-only (no live wire yet): the Memory **constellation** and **"areas"** index. The `/cognition/graph` shape (`{nodes:[{id,label,kind,weight,supports:{belief,confidence}}], edges:[…]}`) is ready for that wire-up.

---

## 9. Repository layout

```
api/            FastAPI server (entrypoint: uvicorn api.main:app) — chat, cards, watches,
                today, history, library, watchbar, settings, push, onboarding, cognition routes
donna_runtime/  the BRAIN: brain.py (loop) · tools.py (18 tools) · prompt.py · config.py ·
                options.py · context_builder.py · hooks.py (Pre/PostToolUse gates)
backend/
  proactive/    runner.py (the tick) · checks.py · watches.py · prepare.py ·
                schedule_health.py · cross_connect.py · morning_brief.py
  finance/      detector.py (shortfall) · waste.py · trigger.py
  knowledge/    goals.py · connections.py · attention.py · feedback.py · tasks.py · interests.py
  cards/        gate.py · resolution.py · executors.py · projection.py · service.py · models.py
  integrations/ composio_client.py · gmail/calendar ingest · email_importance.py ·
                notify.py · delivery_policy.py · push.py
  travel/       flights.py (flight watch + pluggable status provider)
  cognition/    the beliefs subsystem (store, pipeline, beliefs, observations, questions, api)
  memory/       the nine-backend memory system + retrieval
  tests/        pytest suites (backend/tests/integrations is the green suite)
db/             SQLAlchemy models + session ; backend/db/migrations (alembic)
ingress/        inbound normalization   ·   delivery/   outbound (whatsapp)
webapp/         React + Vite frontend
docs_v2/        canonical specs (architecture_decision.md is authoritative)
bin/  scripts/  ops entrypoints (api | reminders), schedule worker, seeding
```

---

## 10. Running it

**Backend (real mode):**
```bash
# env: ANTHROPIC_API_KEY, DATABASE_URL, COMPOSIO_API_KEY, EXA key, (optional) FCM/WhatsApp
pip install -r requirements.txt
uvicorn api.main:app --reload          # or: bin/start.sh
python scripts/<schedule worker>       # the proactive tick / reminders worker (role: reminders)
docker-compose up                      # Postgres + services
```

**Frontend:**
```bash
cd webapp
npm install
npm run dev                            # MOCK mode by default — runs with no backend
# to hit the real API:  VITE_MOCK=0 VITE_API_BASE=http://localhost:8000 npm run dev
npm run build
```

**Tests** (the integration suite is the source of truth — ~193 green):
```bash
python -m pytest backend/tests/integrations -q
python -m pytest tests/test_tool_allowlist.py -q     # allow-list ↔ registered-tools guard
```
> Env note: this repo's `.venv` lacks pytest and a ROS plugin can break collection — run via a full Python with `env -u PYTHONPATH python -m pytest …`.

---

## 11. The "never do" list (architecture guardrails)

From `CLAUDE.md` / the ADR — violating these reintroduces the banned engine-pipeline:
- Never add a **second synchronous LLM call** on the request path (no engine-as-LLM pipeline).
- Never **pre-generate an LLM situational brief** before the loop. Deterministic retrieval of rows/nodes is fine; an LLM digest is not.
- Never inject **deep/semantic memory** without a `recall_*` tool call.
- Never add LangGraph/LangChain or wrap the SDK in a second framework. Never rebuild Perceive-Act.
- Never ship a tool without a when-NOT-to-use clause. Never merge without running the suite.
- Keep `ALLOWED_TOOLS` in sync with `DONNA_TOOLS` (guard test enforces it).

---

## 12. What's done vs. open (current state)

**Done & tested:** the full reactive + proactive spine; all 9 proactive checks + watch sweep; the engines in §4; the L0/L1/L2 gate; cards + tiered single-surface delivery; goals-weighting; learning-from-feedback; the cognition write path; the app's Dashboard/Live/History + Library drawer + Watch Bar.

**Sandboxed (pluggable rails):** money transfer, restaurant/ride/flowers third-party booking, live flight feed. The engine around each is real; only the external rail is stubbed.

**Parked / not wired:** the Memory + Beliefs tabs (backend live, UI unmounted); the Memory constellation + "areas" index (mock-only, `/cognition/graph` ready). The Context/Adaptive layer (`docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md`) is **specced, not built**.
