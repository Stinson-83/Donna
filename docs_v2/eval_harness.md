# Eval Harness — making "never a notification machine" a number

**Status:** Spec · 2026-06-11
**Depends on:** `architecture_decision.md` (§7 budget, §10.3 gate), `proactive_runner.md` (the thresholds this tunes), `metrics.md` (the online counterpart), `cards_and_delivery.md` (Egress intercept point), `vision.md` (the failure modes this measures).
**Fills:** the review gap — there is no precision target for proactive behavior, yet `vision.md`'s entire anti-pattern list ("notification machine", "guilt machine", "spam engine") is about false positives, and `CLAUDE.md` says "never merge without running evals." This makes the proactive product measurable **before** behavior is built on it.

---

## 1. The thing being measured

`vision.md` is blunt: "if Donna constantly interrupts the user, Donna has failed" and "if Donna creates more work than she removes, Donna has failed." That is a quality bar with no number. This harness gives it one.

The naive instinct is a single "proactive precision" number. That is a **trap**: you can drive precision to 1.0 by never speaking. So "never a notification machine" is actually **three numbers held together**:

1. **Precision** — when she interrupts, is each interrupt *worthy*? (guards against spam)
2. **Volume** — even if each is worthy, are there too many per day? (guards against death-by-a-thousand-worthy-pings)
3. **Recall** — of the things she *should* have caught, did she? (guards against the opposite failure — silence/uselessness)

A build is only "not a notification machine" if precision and volume are good **and** recall hasn't collapsed to buy them. The harness always reports all three.

---

## 2. Why proactive eval is hard (and the unit that solves it)

A request-response model is evaluated on prompts. Donna is triggered by **world events**, and the "right answer" is often "stay silent." So the unit of evaluation is a **scenario fixture**:

```text
fixture = ( world , trigger , expected )
  world    : a seeded User Model + domain tables + memory graph (a believable life)
  trigger  : an event injected into the bus (new_email, low_balance_vs_bill,
             watch_due, lunch_checkin, birthday_lead, …)
  expected : the labelled correct behaviour
```

```json
{
  "id": "fix_aws_bill_short",
  "world_ref": "worlds/founder_sg_in.json",
  "trigger": { "event_type": "low_balance_vs_bill", "payload": {...} },
  "expected": {
    "should_notify": true,
    "importance_tier": "high",
    "action_tier": "L0",
    "surface": ["whatsapp", "push"],
    "must_mention": ["aws", "47,200", "4,200 short"],
    "must_not_fabricate": true,
    "expected_terminator": "send_burst|offer"
  }
}
```

Crucially, the fixture set must contain **negatives** — events whose correct outcome is `should_notify: false` (a marketing email, a balance that's actually fine, a birthday 3 months out, an investor who said "no rush"). Precision is meaningless without them.

---

## 3. What the harness runs

It runs the **real path** (event → router → workflow → BRAIN loop → terminator → gate), intercepting at **Egress** so nothing is actually delivered, and captures the decision:

```text
seed world into an isolated DB  →  inject trigger  →  run the real stack
        →  intercept at Egress, capture:
             did she notify?  which terminator?  importance tier?  action tier?
             surface?  message text?  facts cited?  action proposed?
        →  score against `expected` (§5)
```

Two infra tiers:
- **Pure-logic evals** (no bus, no DB): the §10.3 gate classifier and the Importance scorer are deterministic functions — evaluate them directly, fast, no fixtures-as-world needed.
- **Full-path scenario evals**: seed an **isolated database** per fixture (ephemeral Postgres schema or per-fixture transaction rollback) and run the real workflow + loop. (Run standalone seed scripts against a throwaway DB carefully — see the project's SQLite test-env note — so the harness doesn't hang.)

---

## 4. The "worth interrupting" rubric (the crux)

Precision and recall both hinge on one judgment: *was this interrupt worthy?* That judgment must be concrete and fixed, or it gets gamed. An interrupt is **worthy** iff **all** hold:

1. **Unprompted** — about something the user did not just ask about (service requests aren't catches).
2. **Time- or risk-bearing** — acting late carries a real cost (a fee, a missed deadline, a lost option).
3. **Plausibly-missed** — the user likely didn't already know / would plausibly forget.
4. **Actionable** — there is a decision or action, not a bare FYI.

**Not worthy:** marketing/newsletters, FYIs with no action, anything with no deadline that can wait, things the user clearly already handled, redundant nags about an unchanged situation. This rubric is the judge's instruction (§6) and the labeller's guide.

---

## 5. The metrics (dimensions + targets)

| Metric | Definition | Scored by | Target |
|---|---|---|---|
| **Proactive precision** | worthy interrupts / total interrupts (FP = notified a should-stay-silent fixture) | judge + labels | **≥ 0.95** |
| **Interrupt volume** | proactive pings / user / day distribution (post quiet-hours/budget) | deterministic | within budget; p95 ≤ a small N |
| **Proactive recall** | caught / should-have-caught (FN = silent on a should_notify fixture) | judge + labels | **≥ 0.85**, must not collapse |
| **P/R operating curve** | precision vs recall as Importance + material-change thresholds sweep | deterministic sweep | pick the operating point here |
| **Triage calibration** | assigned importance tier vs label (confusion matrix over Critical…Ignore) | deterministic | off-by-≥2 tiers ≈ 0 |
| **Action-gate safety** | §10.3 tier assigned vs correct tier | **deterministic** | **under-gating (L0/L1 action run as L2) = 0, zero-tolerance** |
| **Grounding / anti-fabrication** | every fact she cites is supported by the seeded world | deterministic claim-check | fabrication rate **= 0** |
| **Cost / budget** | tokens per fixture; assert exactly **one** loop invocation + ≤1 extraction (no engine-pipeline) | deterministic | < $0.01 reactive; one-loop assertion passes |
| **Latency** | wall-clock on realtime fixtures (M5/M6) | deterministic | under the realtime bar |

Two of these are **hard gates**, not targets: **action-gate under-gating** and **fabrication** must be **zero** — an auto-executed money action or an invented "mom likes lilies" is a trust-ending failure, worse than any precision miss. A build that fails either does not merge regardless of every other number.

---

## 6. Labeling: golden set + validated LLM judge

- **Golden set** — a human-labelled ground truth (~100–300 fixtures: every demo moment M1–M9 + screenshots as positives, plus hand-authored adversarial negatives). Small, high-quality, the source of truth.
- **LLM-as-judge** — a strong model (Opus) scoring the **subjective** dims (worth-interrupting per §4 rubric, tone/voice) at scale over generated fixtures. The judge is **offline eval infrastructure, not the per-turn path** — using Opus here does **not** violate the ADR cost discipline (which governs production turns).
- **Judge must be validated** against the golden set before it's trusted: judge↔human agreement ≥ a threshold (e.g. κ ≥ 0.8). If they diverge, the rubric or the judge prompt is wrong — fix before scaling.
- **Objective dims** (tier match, fabrication, cost, gate, volume) are scored **deterministically**, never by the judge.

---

## 7. Where fixtures come from

| Source | What | When |
|---|---|---|
| **Hand-authored demo** | M1–M9 + screenshots → positive fixtures | now (pre-build) |
| **Adversarial negatives** | should-stay-silent cases (marketing, covered bill, far-off birthday, "no rush") | now |
| **Perturbations** | golden fixtures with varied times/amounts/relationships | generated |
| **Replayed production** | sampled real events (the event store is replayable, per ADR/`event_system.md`), labelled | once live |
| **Regression fixtures** | every production false-interrupt a user dismissed, every miss a user flagged → a permanent fixture | continuous |

The replay path is a direct dividend of the durable event store: production mistakes become permanent tests.

---

## 8. How it runs

- **CI gate** (`CLAUDE.md`: "never merge without running evals"). A merge may not regress precision/recall/volume below targets, and **must** pass the two zero-tolerance gates. Cheap subset on every PR; full set nightly.
- **Threshold-tuning sweep** — this is where `proactive_runner.md`'s deferred "material change" thresholds and the Importance cutoffs get set: sweep them, plot the P/R curve (§5), choose the operating point that holds precision ≥ 0.95 at the best achievable recall. **Tune here, not in the runner.**
- **Regression suite** — the growing fixture set from §7 runs forever; a fixed bug stays fixed.

---

## 9. Closed loop with the live metrics

The harness is the **offline proxy**; `metrics.md` is the **online truth**. They form a loop:

```text
eval harness  →  predicts precision/recall  →  ship at the chosen threshold
                                                      ↓
   metrics.md convert-rate (caught_converted / caught) measures it in the wild
                                                      ↓
   low conversion  →  the live "worth interrupting" bar was too low
                                                      ↓
   raise the rubric / threshold  →  re-tune in the harness  →  re-ship
```

A persistently low online convert-rate means the offline rubric is too generous — tighten §4, regenerate labels, re-sweep. The harness predicts; production grades; the gap retrains the harness.

---

## 10. Anti-Goodhart / honesty

Same trust principle as `metrics.md`. Three rules so the harness can't lie to us:

- **Never report precision without recall and volume.** A precision win bought by silence is a regression, and the triple makes that visible.
- **The rubric is honest** — "would a busy person thank her, or be annoyed?" — not "did she technically notify about a true fact."
- **Negatives are first-class** — the should-stay-silent set is maintained as carefully as the positives; if it shrinks, precision inflates for free.

---

## 11. Deterministic vs LLM

| Part | LLM? |
|---|---|
| Running the fixture (the stack under test) | the system's normal one loop / fixture |
| Gate / Importance / volume / cost / fabrication scoring | no (deterministic) |
| Worth-interrupting & tone scoring | **yes — offline Opus judge**, not the per-turn path |
| Threshold sweep | no |

The only LLM the harness *adds* is the offline judge, which is explicitly outside the production cost budget.

---

## 12. Out of scope / open

- **Voice-moment eval** (M5) needs the voice gateway first; its fixtures attach later.
- **Multi-turn conversational eval** (a back-and-forth, not a single trigger) is a later extension; this spec covers single-trigger proactive decisions, which is where "notification machine" lives.
- **Human-label tooling** (the interface labellers use) is an infra detail, not specified here.
