# Donna v2

Belief-native AI companion. She/her. Thinking partner with persistent memory, living across **two surfaces that share one memory**: WhatsApp and the Donna app. The app is understanding-first (Plan / Chat / Beliefs / Memory), not a dashboard — you open it to see what Donna believes about your life, not just to message. Memory is evidence; **beliefs are the product**; Donna forms opinions, notices patterns, and shows her reasoning. Conversation is the interface. Full product definition: `docs/PRODUCT.md`.

## Non-negotiables

> **Canonical architecture: `docs_v2/architecture_decision.md`.** It reconciles this file with `docs_v2/` and wins on any conflict. Read it before changing the runtime.

- Reasoning happens in exactly ONE place: a single Claude Agent SDK tool-use loop (the BRAIN). The deterministic event/workflow/watch/scheduler machinery from `docs_v2` wraps the loop — it never reasons on the loop's behalf. No LangGraph. No Perceive-Act. No engine-pipeline of LLM calls.
- Main model: Haiku 4.5. Sonnet only for specific upgrade cases. Opus only inside justified subagents.
- Living Profile lives in the cached system prompt. Never auto-reloaded mid-turn.
- Every capability is a tool. Every deterministic side-effect is a hook. Integrations via MCP.
- One synchronous LLM call per event on the request path (the BRAIN loop) plus at most one async memory-extraction call. No chained LLM calls outside the loop unless inside a declared subagent.

## Voice

- She/her pronouns. Always.
- Lowercase register. No em dashes. No semicolons.
- Blunt. High-agency. No filler.
- Never "I understand" or "Great question."
- When the user is anxious: acknowledge briefly, then be useful. Do not perform empathy.
- When the user is wrong: say so.
- When she does not know: say so. Do not fabricate.

## Architecture (layered)

Canonical path (full version + rationale in `docs_v2/architecture_decision.md`):

Event source (integration / scheduler / watch / user) → Ingress (deterministic: normalize, dedup, idempotency)
→ events table + Event Bus (Postgres LISTEN/NOTIFY over a durable outbox) → Router (deterministic event_type→workflow) → Workflow runner (durable state)
→ Context Assembly (retrieval only, NO llm)
→ BRAIN loop (SDK tool-use, Haiku — the ONLY reasoning site)
→ tools: retrieval | action | dashboard | terminators | subagent
→ hooks: PreToolUse guards (Safety + Consent gates, can block) | PostToolUse side-effects (memory write, dashboard projection, audit)
→ Terminator → Egress (deliver to surface + async memory extraction)

The ~25 "engines" in `docs_v2/engines.md` are NOT separate LLM calls. Each is a deterministic service, a tool, a hook, a prompt section, a retrieval query, or folded into the BRAIN loop. See the reclassification table in the ADR §6.

Context tiers: Standing (Living Profile, cached system prompt) · Trigger (the event + cheap pointers, attached deterministically) · Deep recall (semantic memory, ONLY via recall_* tools). Never run an LLM to build any of these.

Proactive triggers invoke the same loop with `mode="proactive"`.

## Tool categories

1. Retrieval — recall_*, read_*, list_*
2. Action — update_*, schedule_*, track, log_*
3. Dashboard — add_insight_card, flag_attention, update_living_profile
4. Terminators — send_burst, stay_silent, offer
5. Meta / subagent — dig_deeper, compile_brief, draft_high_stakes_message

Every tool description includes when-to-use AND when-NOT-to-use clauses.

## Agency levels (execution gate — full policy in `docs_v2/architecture_decision.md` §10.3)

A deterministic Safety+Consent gate (PreToolUse hook) classifies every action by tool+args. The loop proposes; the gate enforces; on an L0/L1 card the user's tap is the execution trigger. Consent (integration connected + scoped) is required on top, at every tier.

- **L2 auto** — low-risk, reversible, explainable: execute then report. Calendar event, reminder, meal log, watch, draft, Donna's own message.
- **L1 confirm** — acts toward a third party as the user, or not trivially reversible: propose via card, execute on tap. Send email/message as user, restaurant reservation, cancel non-critical subscription.
- **L0 approve** — money, legal, or irreversible: hard-gated, explicit approval card every time. Transfer/pay/charge a card, book paid travel, cancel a critical service, legal docs, delete data.

## Memory layers (nine backends, all active)

1. Graphiti (entities + graph, FalkorDB)
2. Supermemory (episodic)
3. Supermemory (document chunks)
4. Procedural rules (Postgres, three tiers)
5. Observations (Postgres)
6. Open loops (Postgres)
7. User facts / Living Profile (Postgres JSONB)
8. Chat messages (Postgres)
9. Calendar (Postgres synced from Google)

## Directory layout

- `api/` — FastAPI server; entrypoint `uvicorn api.main:app` (via `bin/start.sh`)
- `backend/` — memory system (the nine backends), db models, web/search
- `donna_runtime/` — BRAIN loop, tools, hooks, context builder
- `ingress/` — inbound normalization · `delivery/` — outbound delivery · `db/` — schema/alembic
- `bin/` — role-switching entrypoint (`api` | `reminders`) · `scripts/` — ops (schedule worker, seeding, stress)
- `webapp/` — live frontend
- `tests/` — pytest suite · `evals/` — eval fixtures (`day_scenarios`)
- `docs/` — v1 specs · `docs_v2/` — v2 specs (canonical architecture: `docs_v2/architecture_decision.md`)

## Never do

- Never rebuild Perceive-Act.
- Never add LangGraph or LangChain.
- Never wrap the SDK in a second framework.
- Never put more than one synchronous LLM call per event on the request path (no engine-as-LLM pipeline — ADR §6).
- Never pre-generate a situational brief before the loop. (An *LLM* digest is banned; deterministic retrieval of rows/nodes into the prompt is not — ADR §5.)
- Never inject *deep/semantic* memory into context without a tool call. (Standing profile + trigger stimulus are allowed; anything the agent must go find is a recall_* tool — ADR §5.)
- Never call Donna an "AI assistant."
- Never use em dashes in her voice.
- Never ship a tool without when-NOT-to-use in its description.
- Never merge without running evals.
- Never read or import from archive/.

## Cost discipline

Per-turn cost on Haiku with caching should be under $0.01 for reactive turns. If higher: wrong model, tool_search on small catalog, loop hitting max_turns, or bloated descriptions. Diagnose the cause.

## How to work here

When adding a tool:
1. Write the tool description first (when-to-use + when-NOT-to-use + schema)
2. Decide agency level (L0 / L1 / L2)
3. Decide render target (WhatsApp / dashboard / internal state)
4. Implement in donna_runtime/tools.py (or tool_logic.py for pure logic)
5. Add a unit test
6. Update primitives.md

When fixing a behavior:
1. Diagnose: tool-description problem, system-prompt problem, or missing-tool problem
2. Fix at the diagnosed layer. Do not add a pipeline stage.

When unsure: stop and ask. Do not invent framework abstractions.