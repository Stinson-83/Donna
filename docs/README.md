# Docs index

A map of every doc in the repo, so the ~45 files aren't a maze. **Canonical** docs
are the source of truth; **working notes** are point-in-time and may be stale.

## If you're new, read in this order (≈30 min)
1. [`/README.md`](../README.md) — what Donna is, in plain language (product).
2. [`/README_TECHNICAL.md`](../README_TECHNICAL.md) — how it's built (the one architectural
   rule, the request path, the repo map §9, how to run §10).
3. [`docs_v2/architecture_decision.md`](../docs_v2/architecture_decision.md) — **the ADR**,
   the canonical architecture. Wins over everything on any conflict.
4. [`PRODUCT.md`](./PRODUCT.md) — the full product definition.
5. Then pick a subsystem below and read its spec next to the code.

---

## Canonical — architecture & product
| Doc | What it is |
|---|---|
| [`docs_v2/architecture_decision.md`](../docs_v2/architecture_decision.md) | **The ADR.** One reasoning site (the BRAIN loop); everything else deterministic. Authoritative. |
| [`docs_v2/vision.md`](../docs_v2/vision.md) | Product vision / north star. |
| [`PRODUCT.md`](./PRODUCT.md) | Full product definition (what she does, the two surfaces, the voice). |
| [`/CLAUDE.md`](../CLAUDE.md) | Non-negotiables, voice rules, directory layout, "never do" guardrails. |

## Subsystem specs (read next to the code)
| Doc | Subsystem | Code |
|---|---|---|
| [`docs_v2/memory_system.md`](../docs_v2/memory_system.md) | The nine memory backends + retrieval | `backend/memory/` |
| [`docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md`](../docs_v2/CONTEXT_INTELLIGENCE_ARCHITECTURE.md) | The "season of life" context layer | `backend/knowledge/context.py` |
| [`docs_v2/event_system.md`](../docs_v2/event_system.md) | Event bus / ingress / router | `ingress/`, `api/` |
| [`docs_v2/proactive_runner.md`](../docs_v2/proactive_runner.md) | "She texts first" tick + checks | `backend/proactive/` |
| [`docs_v2/cards_and_delivery.md`](../docs_v2/cards_and_delivery.md) | Cards, the L0/L1/L2 gate, delivery | `backend/cards/`, `delivery/` |
| [`docs_v2/integrations.md`](../docs_v2/integrations.md) | Gmail/Calendar via Composio | `backend/integrations/` |
| [`docs_v2/user_model.md`](../docs_v2/user_model.md) | Living profile / user facts | `backend/memory/user_facts/` |
| [`docs_v2/onboarding.md`](../docs_v2/onboarding.md) | First-run + account connect + backfill | `backend/onboarding/` |
| [`docs_v2/workflows.md`](../docs_v2/workflows.md) · [`engines.md`](../docs_v2/engines.md) | Workflow runner; the "engines" reclassification | — |
| [`docs_v2/BROWSER_CAPABILITY_ARCHITECTURE.md`](../docs_v2/BROWSER_CAPABILITY_ARCHITECTURE.md) | Capability layer (Exa vs browser) | `donna_runtime/capabilities.py` |
| [`docs_v2/database_schema.md`](../docs_v2/database_schema.md) · [`domain_schema.md`](../docs_v2/domain_schema.md) | DB + domain schema | `db/models.py` |
| [`docs_v2/eval_harness.md`](../docs_v2/eval_harness.md) · [`metrics.md`](../docs_v2/metrics.md) · [`moment_mapping.md`](../docs_v2/moment_mapping.md) | Evals, metrics, moment mapping | `evals/` |
| [`memory.md`](./memory.md) | Memory (v1 notes) | `backend/memory/` |
| [`codebase-mind-map.md`](./codebase-mind-map.md) | A code-level map of the repo | — |

## Operations / deploy
| Doc | What it is |
|---|---|
| [`deployment.md`](./deployment.md) · [`deploy.md`](./deploy.md) | How it deploys (Railway: 3 services off one image). |
| [`PUSH_SETUP.md`](./PUSH_SETUP.md) | FCM / push-notification setup. |
| [`PRE_TRIAL_CHECKLIST.md`](./PRE_TRIAL_CHECKLIST.md) | The go-live checklist (WhatsApp app, token, template, Google connect). |
| [`TRIAL_READINESS_STATUS.md`](./TRIAL_READINESS_STATUS.md) | Honest verified-vs-pending map for the trial. |

## API / frontend contracts
| Doc | What it is |
|---|---|
| [`API_CONTRACT.md`](./API_CONTRACT.md) | The dashboard/app HTTP API shapes. |
| [`FRONTEND_DELIVERY_SPEC.md`](./FRONTEND_DELIVERY_SPEC.md) | Frontend delivery spec. |

## Planning / roadmap / status
| Doc | What it is |
|---|---|
| [`DONNA_FEATURES_AND_ROADMAP.md`](./DONNA_FEATURES_AND_ROADMAP.md) | Unified feature catalog + phased roadmap. |
| [`BUILD_PLAN_15_DAYS.md`](./BUILD_PLAN_15_DAYS.md) | WhatsApp-first → dashboard → app build plan. |
| [`COVERAGE.md`](./COVERAGE.md) · [`OPEN_QUESTIONS.md`](./OPEN_QUESTIONS.md) | Coverage tracker; open questions. |
| [`YC_PITCH_BRIEF.md`](./YC_PITCH_BRIEF.md) | Pitch brief. |

## Working notes / research (point-in-time; may be stale)
`dashboard-research.md` · `dashboard-sprint-notes.md` · `donna-context-and-eval-playbook.md` ·
`temporal-brief-implementation-results.md` · `temporal-memory-strategy-plans.md` ·
`timezone-audit.md` · `V2_ARCHITECTURE.md` (superseded by `docs_v2/architecture_decision.md`) ·
`research/` · `superpowers/`
