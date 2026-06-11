# Architecture Decision — The Donna v2 Runtime

**Status:** Accepted · locked 2026-06-11
**Scope:** Governs `donna_runtime/`, the event/workflow/watch layer, and how every other `docs_v2/*` file is interpreted.
**Authority:** This document is canonical. Where any other doc (including `CLAUDE.md` or the rest of `docs_v2/`) reads as contradicting it, this document wins. It resolves the §2 conflict raised in the docs_v2 review.

---

## 1. The conflict this resolves

Two architectures were in the repo at once:

**v1 (`CLAUDE.md`):** a single Claude Agent SDK tool-use loop ("the BRAIN"). No pre-computed briefs, no second framework, no chained LLM calls outside the loop. Haiku main model. Under $0.01 per reactive turn.

**v2 (`docs_v2/`):** `Event Bus → Workflow → Context Assembly Engine → Agent → ~25 Engines (sequential) → Decision Engine → Action`.

Read literally, these contradict. If the ~25 engines are LLM calls in a pipeline, every event costs 10–20× a single turn and adds seconds of latency — which breaks the cost rule **and** makes the real-time demo moments (the Dynamic Island recall, the Live-tab ride booking) physically impossible. v1's bans ("no Perceive-Act", "no pre-computed situational briefs", "no chained LLM calls") exist precisely to prevent that pipeline.

This decision keeps the **best of both**: v2's durable event/workflow/watch machinery, wrapped around v1's single reasoning loop.

---

## 2. The decision, in one sentence

> **Reasoning happens in exactly one place — a single Claude Agent SDK tool-use loop (the BRAIN). Everything in `docs_v2` that sounds like a second reasoning layer is either deterministic machinery *around* the loop, or folded *into* the loop's prompt and tools.**

The v2 docs describe **responsibilities**, not **components**. "Importance Engine," "Cross-Connection Engine," "Decision Engine" name *jobs that must get done* — they do **not** license a separate LLM call per job. Section 6 maps every named engine to its real home.

---

## 3. The seven locks

1. **One reasoning site.** The BRAIN loop (Haiku 4.5, SDK tool-use) is the only place an LLM interprets meaning, weighs importance, connects facts, or chooses an action. There is no "engine pipeline" of LLM calls.

2. **Durability wraps the loop; it never replaces it.** The Event Bus, Router, Workflow runner, Watch system, and Scheduler are **deterministic code**. Their job is to decide *when* the loop runs and *with what stimulus* — never to reason on the loop's behalf.

3. **Context Assembly is pure retrieval.** It runs DB and graph **queries**, not an LLM. It attaches the triggering stimulus plus cheap structured pointers. It does not summarize, narrate, or pre-digest. (This is what reconciles it with v1's "no situational brief" — see §5.)

4. **Engines are reclassified, not built as written.** Each v2 engine becomes one of: a deterministic service, a tool, a PreToolUse/PostToolUse hook, a prompt section, a retrieval query, or a declared subagent. See the table in §6. The default is *deterministic or folded-in*; an LLM call is the rare, justified exception.

5. **A strict per-event LLM budget.** One triggering event ⇒ **exactly one BRAIN loop invocation** (which may span several internal tool turns) **plus at most one async, cheap memory-extraction call**. No per-engine calls. If you find yourself adding a second synchronous LLM call to the request path, you are rebuilding the banned pipeline — stop.

6. **Workflows are deterministic process and state.** A workflow selects context, invokes the loop once, persists durable state (`pending/running/waiting/completed/failed/cancelled`), handles retries/compensation, and may chain follow-up workflows. A workflow contains **zero prompt logic** beyond assembling the stimulus envelope.

7. **Side-effects are hooks; gates are PreToolUse.** Memory writes, dashboard projection, and action auditing are PostToolUse hooks. Safety tiering and consent/permission checks are **PreToolUse hooks that can block** — they are deterministic guards, not LLM judgments.

---

## 4. The canonical request path

This replaces every "Event → … → Engines → … → Action" diagram in `docs_v2`. It is the single path every moment in the demo flows through.

```text
Integration / Scheduler / Watch / User action
        │
        ▼
INGRESS  (deterministic)            normalize · dedup · idempotency key
        │
        ▼
events table  +  Event Bus          persisted fact, then routed
        │
        ▼
ROUTER  (deterministic dict)        event_type → workflow
        │
        ▼
WORKFLOW RUNNER  (durable state)    selects which context to assemble
        │
        ▼
CONTEXT ASSEMBLY  (retrieval only)  stimulus + standing pointers, NO llm
        │
        ▼
┌──────────────────────────────────────────────┐
│  BRAIN LOOP   (Haiku 4.5, the ONLY reasoning) │
│   cached system prompt = Living Profile /      │
│       User Model snapshot                      │
│   tools: retrieval · action · dashboard ·      │
│          terminators · subagent                │
│   PreToolUse hooks: Safety gate · Consent gate │  ← can block
│   PostToolUse hooks: memory write · dashboard  │
│          projection · action audit             │
└──────────────────────────────────────────────┘
        │
        ▼
TERMINATOR  (send_burst · stay_silent · offer · schedule · create_watch · take_action)
        │
        ▼
EGRESS  (deliver to surface)  +  async MEMORY EXTRACTION (one cheap call)
        │
        ▼
User Model update  (deterministic write; periodic cheap distillation)
```

Proactive moments ("she texts first") enter at the top via Scheduler or Watch, not via a user message, and run the **same** loop with `mode="proactive"`.

---

## 5. The crux: reconciling the two "forbidden" rules

Two v1 bans appear to forbid what v2 wants. They don't — once the terms are made precise.

### "Never pre-generate a situational brief before the loop."

What is banned: **an LLM** that reads the event + memory and writes a narrative briefing that is then fed to the loop. That is Perceive-Act; it doubles cost and smears responsibility.

What is allowed: **deterministic retrieval** that fetches structured rows/graph nodes and places them in the prompt as raw context. A SQL row is not a brief. Context Assembly (§3) is retrieval, so it is allowed.

### "Never inject memory into context without a tool call."

This is about **three tiers of context**, and the ban only applies to the third:

| Tier | What | How it enters the loop | LLM? |
|---|---|---|---|
| **Standing** | Living Profile / User Model snapshot (identity, decision style, top relationships, active goals) | Cached system prompt. Stable, never auto-reloaded mid-turn. | No |
| **Trigger** | The stimulus: the event payload + cheap deterministic pointers it touches (sender's relationship row, the matching open watch, open commitments on this entity) | Attached by Context Assembly when invoking the loop | No |
| **Deep recall** | Anything semantic or open-ended ("what did Anirudh say about restaurants", "past investor threads") | The loop **must call `recall_*` tools** | No (search), reasoning by loop |

The ban means: **deep/semantic memory is never pre-stuffed — the agent must choose to recall it.** The standing profile and the trigger stimulus are not "memory injection"; they are the cached identity and the stimulus itself. This preserves prompt caching (cost), keeps the loop in control of what it pulls, and still lets v2's Context Assembly do its job.

**Rule of thumb:** if it's stable identity → system prompt. If it's the thing that just happened → trigger envelope. If the agent has to *go find it* → a tool. Never run an LLM to produce any of these.

---

## 6. Engine reclassification table

Every engine named in `engines.md`, mapped to its real home. "LLM?" answers whether this engine, by itself, makes a synchronous model call on the request path. The answer is almost always **no** — the one reasoning call is the BRAIN loop, which subsumes every "folded" engine.

| v2 Engine | Reclassified as | LLM on path? |
|---|---|---|
| Context Assembly | Retrieval service (DB + graph queries) | No |
| Goal | Retrieval (`recall_goals`) + prompt; judgment is the loop | No |
| Relationship | Retrieval (`recall_relationship`) + prompt; importance is a stored int | No |
| Preference | Retrieval (`recall_preferences`) + extraction hook | No |
| Pattern | Retrieval (`recall_patterns`) + extraction hook | No |
| Commitment | Retrieval + deterministic state; new commitments via extraction hook | No |
| Watch | Deterministic CRUD service + tools (`create/update/retire_watch`) | No |
| Dynamic Check | **Deterministic function** — `next_check = f(importance, urgency, deadline, change_rate)` | No |
| Importance | **Deterministic scoring heuristic** (goal-match, relationship importance, deadline proximity, risk, $ impact) → tier; loop may override | No |
| Cross-Connection | **Folded into BRAIN reasoning** (this *is* the "magic"); hard cases → `dig_deeper` subagent | No |
| Preparation | Scheduler-triggered workflow → BRAIN loop; heavy gathering → `compile_brief` subagent | No |
| Conflict | Deterministic overlap pre-filter (calendar math) + BRAIN for resolution | No |
| Recommendation | **Folded into BRAIN** — it's the loop's output | No |
| Opportunity | **Folded into BRAIN**, triggered by watch/event | No |
| Risk | Deterministic **detectors** emit signals/events (low balance, deadline near); severity is the loop | No |
| Safety | **Deterministic gate** (PreToolUse hook): action risk tier → auto / ask / block | No |
| Consent | **Deterministic gate** (PreToolUse hook): permission + scope check | No |
| Notification | **Deterministic policy service**: quiet-hours, batching, interrupt budget, notify/delay/bundle/ignore | No |
| Memory Extraction | **Async, post-turn, cheap-model** call — the one allowed extra LLM | Async only |
| User Model | Deterministic write of extracted memories; **periodic** cheap distillation of identity/decision-style (batch, off-path) | Off-path only |
| Dashboard | **Deterministic projection** of watches/commitments/schedule/actions → `dashboard_sections` | No |
| Decision | **The BRAIN loop itself**, choosing a terminator tool (`NOTIFY_NOW/SCHEDULE/CREATE_WATCH/TAKE_ACTION/PREPARE/IGNORE` = which terminator it calls) | (it *is* the loop) |

Total synchronous LLM calls on the request path: **one** (the BRAIN loop). Everything else is deterministic, retrieval, a hook, or folded into that one loop.

---

## 7. Cost & model budget (binding)

- **Per event:** 1 BRAIN loop (N internal tool turns, cached prompt) + ≤1 async extraction call. Nothing else.
- **Main model:** Haiku 4.5 for the loop. **Sonnet** only for declared upgrade cases (high-stakes drafting, ambiguous high-impact decisions). **Opus** only inside a justified, declared subagent.
- **Extraction / distillation:** cheap model, always async, never blocks delivery.
- **Target:** under $0.01 per reactive turn with caching.
- **If a turn costs more, the cause is one of:** wrong model, **a per-engine LLM call sneaking back onto the path** (the failure this ADR exists to prevent), loop hitting `max_turns`, `tool_search` over a small catalog, or bloated tool descriptions. Diagnose and fix at that layer — do **not** add a pipeline stage.

---

## 8. What stays banned

- LangGraph / LangChain, or any second framework wrapping the SDK.
- Perceive-Act in any form.
- An LLM that pre-digests context into a brief before the loop.
- More than one synchronous LLM call per event on the request path (i.e., engines-as-LLM-pipeline).
- Pre-stuffing deep/semantic memory without a `recall_*` tool call.
- A workflow that contains prompt/reasoning logic instead of delegating it to the loop.

---

## 9. What this unblocks

- **Cost & latency hold**, so the real-time moments (Dynamic Island recall, Live-tab booking) are achievable.
- **Durability arrives**: events are persisted/replayable, watches survive restarts, workflows recover, proactive triggers have a home — all the v2 machinery, none of the v2 cost.
- **One place to reason** means one place to evaluate, debug, and improve behavior — consistent with v1's "diagnose at the layer, don't add a stage."
- The v2 docs become **buildable as written, once read through §6** — no doc needs to be rewritten, only reinterpreted via this mapping.

---

## 10. Resolved follow-on decisions (locked 2026-06-11)

The three items this ADR originally deferred are now decided.

### 10.1 Memory backends — keep all nine

All nine backends in `CLAUDE.md` ("Memory layers") remain active: Graphiti (FalkorDB), Supermemory (episodic), Supermemory (doc chunks), procedural rules, observations, open loops, user facts / Living Profile, chat messages, calendar. `docs_v2/memory_system.md` and `database_schema.md` describe only the two **primary** stores (Graphiti + Postgres) and are therefore **partial** — read them as the conceptual layering (Raw → Working → Long-Term → User OS), not as the full backend list. Nothing is removed now; revisit for redundancy only after the spine runs and real retrieval patterns reveal dead weight.

Budget implication (§7 unchanged): the retrieval engines (Goal/Relationship/Preference/Pattern/Commitment) and `recall_*` tools query *across* these backends through the retrieval layer. More backends = wider **deterministic** retrieval, not more LLM calls.

### 10.2 Event Bus — Postgres `LISTEN/NOTIFY` over a durable outbox

The `events` table is the source of truth and the durable queue. `LISTEN/NOTIFY` is only the **low-latency wake-up signal**, never the delivery guarantee (NOTIFY is fire-and-forget, lost if no listener is connected, ~8 KB payload cap). The pattern:

- **Persist then notify.** Ingress writes the event row in a transaction, then `NOTIFY donna_events, '<event_id>'`. The payload carries only id/type; consumers read the row.
- **Workers LISTEN *and* poll.** Each worker LISTENs for latency and polls for unclaimed rows on a short interval, so a NOTIFY missed while a worker was down is still picked up. Claim with `SELECT … FOR UPDATE SKIP LOCKED` or a `status` transition.
- **Dedup.** Unique idempotency key on `events` (`source` + provider event id) — duplicate webhooks collide on insert and drop.
- **Ordering.** Per-entity order via monotonic `id`/`created_at`; sequence-dependent workflows read in that order.
- **Fan-out.** One event → many workflows. Track per-consumer progress (a cursor / processed-marker per `(event_id, consumer)`) so each consumer group advances independently, at-least-once.
- **Replay.** Re-read rows to re-emit; consumers must be idempotent (they are, via action idempotency keys — §10.3).

This replaces the current `.donna/events.jsonl`. No external broker (Redis/Kafka) for v2; revisit only if throughput outgrows a single Postgres.

### 10.3 Execution policy — observe freely, act narrowly, approve anything consequential

Donna **always** auto-observes, understands, prepares, and recommends. She **executes** only through a deterministic agency gate (the Safety + Consent engines = a PreToolUse hook that can block). Three tiers:

| Tier | Rule | Gate behavior | Examples |
|---|---|---|---|
| **L2 — auto** | low-risk **and** reversible **and** easily explainable | execute, then report | create/move a calendar event, set a reminder, log a meal, create/update a watch, draft (not send) a reply, compile a briefing, send Donna's own proactive message |
| **L1 — confirm** | medium-risk, or acts toward a third party as the user, or not trivially reversible | propose via card, execute on tap | send an email/message as the user, make a restaurant reservation, cancel a **non-critical** subscription |
| **L0 — approve** | money · legal consequences · irreversible commitments | **hard-gated**: never auto; explicit approval card every time | transfer funds, make a payment or anything that charges a card, book a flight or paid ride, cancel a **critical** service, sign/send legal documents, delete data |

Rules:
- The tier is computed **deterministically** by the Safety engine from the tool + its arguments (e.g. `take_action(transfer, …)` and `book_ride(… charges card …)` are L0 regardless of amount). The BRAIN loop cannot talk its way past the gate.
- **Consent is orthogonal and also required.** Even an L1/L2 action needs the relevant integration connected with sufficient scope (the consent/OAuth card in demo M6). Missing scope ⇒ block + request access.
- L0/L1 surface as **interactive cards** (the JIT-card system, still to be specced). The buttons in demo M2/M3/M6/M7/M8 *are* this gate made visible: the agent proposes a pre-filled, explainable card; the user's **tap** is the execution trigger.
- The policy and the demo agree exactly: log lunch = L2 auto; send ₹5,000 / book the cab / send ₹1,899 flowers = L0 approval card; cancel Spotify = L1 confirm.

With these locked, the §4 spine can be built end to end. The remaining net-new system (the JIT card + Delivery layer) is the natural next spec — it is where §10.3's gate becomes UI.
