# Context Intelligence Architecture — The Adaptive Layer

**Status:** Proposed
**Scope:** Defines the Context Layer that sits across `donna_runtime/`, the proactive/watch machinery, retrieval, scoring, delivery, and the dashboard.
**Authority:** Subordinate to `architecture_decision.md` (the ADR). The ADR's seven locks bind this document — wherever a tempting "context engine" reads like a second reasoning site or an LLM pipeline, the ADR wins and this doc is wrong. Synthesizes `Ambient_Donna.md` (reality-first, JIT, watch-don't-wait) and `Adaptive_Context_System.md` (situational intelligence) into the existing spine.

---

## 1. The problem

A person is not in one state. Over a year the same user is traveling, fundraising, sitting exams, interviewing, launching, planning a wedding, recovering from illness — often several at once. A world-class chief of staff does not need to be told "we are now in Travel Mode"; they read the situation and adjust what they watch, prepare, surface, and interrupt with.

A static Donna treats every event the same way forever. An adaptive Donna weighs the **same event differently depending on the season of life** the user is in. An investor email is critical during a raise and deferrable during a family emergency. That difference is the Context Layer's entire job.

The failure mode to avoid is **manual modes**: Travel Mode / Focus Mode toggles that the user must remember to flip on and off. Donna infers; she does not ask to be configured. (She may *confirm* — §8 — which is not the same thing.)

---

## 2. Core principle: stable model, dynamic layer — both deterministic

Two stores, two cadences:

| | **User Model** (Standing) | **Context Layer** (Dynamic) |
|---|---|---|
| Holds | goals, preferences, relationships, habits, decision style, values | what's happening *now*, what deserves attention, which phase of life |
| Changes | slowly (a goal lasts months) | frequently (a context onsets and decays in days/weeks) |
| Home | Living Profile / `living_profile` JSONB → cached system prompt | a new `contexts` store → recomputed on the tick, surfaced as cheap pointers + a prompt section |
| Authority | identity | situational weighting |

**The architectural lock.** The Context Layer is *not* a new reasoning site and adds *zero* synchronous LLM calls to the request path (ADR §3.1, §7). It is **deterministic state plus a set of weights and filters** that modulate the knobs Donna already has:

- the priority scorers (`backend/knowledge/attention.py::rank_attention`, `email_importance.score_email`, watch `importance`),
- the watch cadence (`compute_next_check`),
- the delivery tiering (`backend/integrations/delivery_policy.py`),
- retrieval (Context Assembly pointers + `recall_*` bias),
- the Standing prompt (a `## CONTEXT` section beside the existing `## GOALS` block).

Context is to the *situation* what goals are to *importance* — and goals already ship as a deterministic term in those scorers (Cap 7). Context is the same shape, one level up: a weight, not a brain.

---

## 3. What a context is

A context is a **probabilistic, time-bounded belief** that the user is currently in a particular phase, with an evidence trail. It is a row, not a mode flag.

```
Context {
  type            travel | fundraising | job_search | exam | launch | family | health | wedding | custom
  confidence      0.0–1.0   (signal strength; never assumed, always estimated)
  state           candidate | active | confirmed | decaying | closed
  evidence        the deterministic signals that raised it (event ids, counts, the booking, the goal)
  domains         the attention domains it amplifies / damps (e.g. travel ↑ logistics, ↓ routine work)
  onset_at        when it began
  expires_at      a horizon (a trip's return date) or null
  decay           how confidence falls as signals lapse
  source          inferred | focus_window (explicit declaration) | confirmed_by_user
}
```

Three properties the rest of the system depends on:

1. **Multiple, simultaneous.** Never assume a single mode. A user can be `travel` + `fundraising` + `family` at once; their domain weights compose (§6.1).
2. **Probabilistic.** Low confidence → a *subtle* nudge to weights. High confidence → strong weighting, and if implications are significant, a confirmation (§8). Donna estimates; she does not assume.
3. **Lifecycle, not on/off.** A context onsets, strengthens, decays, and closes as evidence accumulates and lapses (§9). A flight lands → `travel` decays → its amplifications fade on their own. No user de-activation.

---

## 4. Where the Context Layer sits in the spine

The ADR §4 request path is unchanged. The Context Layer is a **deterministic service that reads accumulated signals and writes Context State**, feeding three consumption points — none of which is a new model call.

```text
            signals (deterministic, already produced):
            calendar bookings · email/thread patterns · goals ·
            focus-window declarations · risk detectors · fired watches ·
            location/time · the ONE loop's side-effects · async extraction tags
                          │
                          ▼
            CONTEXT ENGINE  (deterministic aggregation, on the tick)
              rules + counts + decay  →  Context State (the `contexts` store)
                          │
        ┌─────────────────┼──────────────────────────────┐
        ▼                 ▼                               ▼
  (a) SCORING KNOBS   (b) CONTEXT ASSEMBLY           (c) STANDING PROMPT
  context term in     attaches active contexts +     a `## CONTEXT` section
  importance /        context-relevant pointers      (cached, refreshed on a
  attention /         to the trigger envelope        cadence, never mid-turn)
  cadence / delivery  (retrieval only, no llm)       → the loop's situational view
```

**Inference is deterministic, and the fuzzy part rides systems that already exist.** The Context Engine never runs a dedicated "classify my life phase" LLM pass (that would be the banned pipeline, ADR §8). It aggregates from:

- **Deterministic signal rules** — a flight + hotel booking ⇒ `travel` candidate; ≥N emails on recruiter domains in a window ⇒ `job_search` candidate; an active goal of category `financial`/`career` ⇒ a standing context prior; a calendar titled "exam"/"final" ⇒ `exam`.
- **The one BRAIN loop's side-effects** — the loop is *already* reasoning over each event; when it recognizes "this is an investor thread" it can emit a context signal via a PostToolUse hook / a lightweight `note_context` terminator. No extra call; it's a by-product of the turn that already happened.
- **The one async extraction call** (ADR §6, the only allowed extra LLM) — post-turn, it can tag context alongside the memories it already extracts.
- **Explicit focus windows** (§7) — the highest-confidence signal, free.

The Engine's job is to *aggregate and decay* these into confidences. That is arithmetic, not reasoning.

---

## 5. Every system required for adaptive behavior

Mapped in the ADR's reclassification style. "LLM on path?" is **no** for all of them — context is deterministic state + weights; the single reasoning call is unchanged.

| Context subsystem | Reclassified as | LLM on path? |
|---|---|---|
| **Signal Collection** | Deterministic emitters on existing sources (calendar/email/goals/detectors/focus declarations) → context-signal rows | No |
| **Context Engine** | Deterministic aggregation: signal rules + counts + decay → confidences, on the proactive tick | No |
| **Context Store** | New `contexts` table (dynamic state), distinct from `living_profile` (stable) | No |
| **Confidence model** | Deterministic score from signal strength + recency; thresholds for candidate/active/confirmed | No |
| **Confirmation** | Folded into the BRAIN loop — a heads_up/options card the loop emits when confidence crosses a threshold *and* implications are significant (§8) | (it *is* the loop) |
| **Focus Windows** | Deterministic declarations → high-confidence, time-bounded contexts (a tool writes the row) | No |
| **Context-aware prioritization** | A **context term** added to `rank_attention` + importance scorers, beside the goal term | No |
| **Context-aware watches** | Context-driven watch *derivation* (travel ⇒ flight/reservation watches) + a cadence bump in `compute_next_check` | No |
| **Context-aware retrieval** | Context Assembly attaches context pointers; `recall_*` queries biased toward active-context entities | No |
| **Context-aware dashboard** | The watch bar / `dashboard_sections` reorder by the context-weighted priority | No |
| **Context-aware preparation** | The prep stimulus carries active contexts → the loop prepares the right things | No |
| **Context-aware delivery** | A **context modifier** on `delivery_policy` tiers (focus domain ↑, off-focus ↓) | No |
| **Context in the prompt** | A cached `## CONTEXT` Standing section so recommendations align (folded, like Cross-Connection) | No |
| **Dynamic reprioritization** | The tick recomputes Context State and therefore every weight downstream | No |
| **Context lifecycle / decay** | Deterministic decay + close on lapsed evidence | No |
| **Context learning** | Async extraction adjusts context priors; feedback (Cap 20) tunes confirmation thresholds | Async only |

Total added synchronous LLM calls on the request path: **zero**. (ADR §7 budget holds.)

---

## 6. How context permeates each layer

Context is not isolated; it touches every layer (the `Adaptive_Context_System.md` mandate). Each integration is an extension of a system that already exists — context contributes a **weight or a filter**, never a decision.

### 6.1 Prioritization — the central effect
The same event, weighed by situation. Context contributes an additive term to the existing scorers exactly as goals do (Cap 7):
- `rank_attention` (the watch bar) and `email_importance.score_email` gain `+context_weight(item, active_contexts)`: an item whose domain matches an amplified context is lifted; an item in a damped domain is lowered.
- Composition across simultaneous contexts: take the **max amplification** and the **max damping** across active contexts, scaled by each context's confidence — so a low-confidence context only nudges, and `fundraising` + `family` can pull the same investor email in opposite directions, with the stronger-confidence context winning.
- The loop may still override (ADR §6, Importance) — context sets the prior, the one reasoning site has final say.

### 6.2 Watches — what to monitor, how often
- **Derivation:** an active `travel` context deterministically *proposes* the watches that situation needs (flight status, gate, reservation, document expiry) — the same pattern as interests → web-watches already shipped (`maybe_watch_interests`). Contexts carry a watch-template set; the Engine tops up missing watches idempotently.
- **Cadence:** `compute_next_check` takes a context-importance bump, so context-relevant watches poll more often and off-context ones back off. Intelligent attention allocation = where the polling budget goes.
- **Decay:** when `travel` closes, its derived watches retire on their own.

### 6.3 Memory retrieval — what context attaches and what the loop pulls
- **Context Assembly** (ADR Trigger tier) attaches *context-relevant standing pointers* to the stimulus: in `travel` context, the trip's reservations/documents ride along as cheap pointers; in `fundraising`, the open investor threads and the round's commitments. This stays pure retrieval — pointers, not a brief (ADR §5).
- **Deep recall bias:** the `## CONTEXT` prompt section tells the loop which way to lean when it chooses `recall_*` queries (recall about *this investor* during a raise, not the user's whole address book). Context shapes *what the agent goes looking for*; it never pre-stuffs semantic memory (ADR §5 ban intact).

### 6.4 Dashboard ordering — a surface that reorganizes around now
The dashboard and the Dynamic Watch Bar already sort by the attention ranker; once that ranker carries the context term (§6.1), the surface **reorganizes itself** with no extra wiring: travel watches float during a trip, investor watches during a raise, deadlines during exams. The dashboard projection (ADR §6, deterministic) reads the context-weighted order. "The dashboard should feel alive" = the ranker is context-aware.

### 6.5 Recommendations — folded into the one loop
Recommendations are the loop's output (ADR §6). The loop sees active contexts in its cached `## CONTEXT` Standing section, so its recommendations align with the season of life — aggressive investor prioritization during a raise, fewer social suggestions during exams — *without* a recommendation engine. Same mechanism as goals already shaping the loop's judgment.

### 6.6 Notifications & delivery — context shifts the interrupt bar
The tiered-delivery policy (`delivery_policy.py`) gains a **context modifier**:
- Inside a focus window, off-focus domains drop a tier (more "held" — they land on the dashboard/bar, no buzz), and the focus domain may rise a tier.
- Travel context damps routine work pings and non-urgent subscriptions; amplifies travel-critical ones.
This is the deterministic Notification policy of ADR §6, now situation-aware. Interrupts stay rare *and* relevant.

### 6.7 Preparation — context-shaped briefs
The Preparation engine (the scheduled pre-event brief, already shipped) takes active contexts in its stimulus, so it prepares the *right* things: travel context → logistics, boarding, local info; exam context → study schedule, deadlines; fundraising → the meeting brief and the round's open commitments. Preparation "always aligns with context" because the stimulus carries it.

### 6.8 Opportunity & risk detection — context gates the detectors
Deterministic detectors (ADR §6, Risk) are gated/weighted by context: a `travel` context activates price-drop and gate-change detection and raises document-expiry severity; an `exam` context raises deadline-risk weighting. Context decides which detectors are worth running and how loudly their signals score.

---

## 7. Focus Windows — explicit priority, still not a mode

Inference is primary, but the user may *declare* priority: "for the next 14 days, fundraising is my highest priority"; "this semester, prioritize academics." These are **intentional priority declarations**, not modes:

- A declaration writes a context row with `source = focus_window`, high confidence, and an explicit `expires_at`.
- It feeds the *same* weights as an inferred context (§6) — there is no separate code path, so a declared focus and an inferred situation compose naturally.
- It expires on its own at the horizon; the user never deactivates it.

A focus window is the cheapest, highest-confidence way to bias the whole system, and it requires no toggle to remember.

---

## 8. Confidence & confirmation

Context is probabilistic; the system's behavior scales with confidence so it stays adaptive without overreacting:

| Confidence | Behavior |
|---|---|
| low (candidate) | weights nudge subtly; nothing surfaced; keep gathering evidence |
| medium (active) | weights apply at scaled strength; dashboard/cadence shift; no interruption to confirm |
| high + significant implications | the loop emits a **confirmation** — "it looks like you're traveling to Singapore next week; want me to prioritize logistics and hold non-urgent pings during the trip?" |

Confirmation is **contextual alignment, not mode switching**: it's an ordinary card the loop produces (folded, ADR §6), triggered deterministically when confidence crosses a threshold *and* the implied changes are large enough to be worth a question. A `yes` writes `state = confirmed` (and teaches the prior, §9). Silence leaves the inferred weighting in place at its estimated confidence — Donna still adapts, just without asserting.

---

## 9. Dynamic reprioritization & lifecycle

Context is never static. The proactive tick (the runner that already sweeps checks and watches) gains a **Context Engine pass** that, each cycle, deterministically:

- ingests new signals, raises/strengthens candidate contexts;
- **decays** confidence where evidence has lapsed (no booking activity, the trip's return date passed, the exam date is behind us);
- closes contexts that fall below a floor, retiring their derived watches and releasing their weights;
- asks the standing questions — *what matters most now? has the situation changed? has a deadline approached? has a new goal or major life event landed?* — as deterministic re-scores, not as an LLM pass.

Because every downstream weight (§6) reads live Context State, recomputing context **rebalances the entire system at once** — priorities, cadence, dashboard order, delivery bar, prep focus — which is the "continuously reorganize around current priorities" the ambient model demands.

**Learning (Cap 20 extension).** The async extraction call adjusts context priors over time (which signals reliably predicted a real context for *this* user), and card-feedback tunes the confirmation threshold (a user who dismisses confirmations gets fewer; one who acts gets asked earlier). The Context Layer gets more accurate the longer Donna runs.

---

## 10. Budget & non-negotiables (binding)

- **Zero added synchronous LLM calls.** Context inference is deterministic aggregation; refinement rides the one BRAIN loop's side-effects and the one async extraction call. The ADR §7 budget (1 loop + ≤1 async per event, < $0.01/reactive turn) is unchanged.
- **One reasoning site.** The loop still decides; context only sets priors and filters. A "Context Engine" that interprets meaning with its own model is the banned pipeline (ADR §8) — do not build it.
- **No modes, no toggles** as the primary mechanism. Inference first; focus windows for explicit intent; confirmation, not configuration.
- **Standing vs dynamic stay separate.** Context never mutates the stable User Model directly; it is its own store with its own decay. (A repeatedly-confirmed context *may* feed a slow User-Model distillation off-path — e.g. "this user travels monthly" becomes a habit — but that is the periodic batch job, never the request path.)
- **Pointers, never briefs.** Context Assembly attaches structured context pointers; it never pre-generates a narrative (ADR §5).

---

## 11. The desired experience

The user should feel: *Donna understands what season of life I'm in. She knows what I'm focused on and what deserves my attention right now. She adapts naturally — I never configure her. She already knows, or notices and asks intelligently.*

Architecturally, that feeling is the sum of one deterministic store and a context term threaded through scorers, cadence, retrieval, the dashboard, preparation, and delivery — with the single BRAIN loop still the only thing that reasons. A static assistant remembers. An adaptive chief of staff understands the situation and rebalances around it. The Context Layer is how Donna understands — without a second brain, and without a single extra model call on the path.
