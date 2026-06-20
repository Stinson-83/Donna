# Browser Capability Architecture — Capabilities over Tools

**Status:** Proposed · 2026-06-16
**Scope:** Introduces a **Capability Layer** above Donna's tool/integration catalog and adds **Browser Interaction** (provider: **Kimi WebBridge**) as a first-class capability. Governs how browser-driven sensing and action fit the Event System, Workflows, Watchers, Integrations, the Execution gate, and the Ambient model.
**Authority:** Subordinate to `docs_v2/architecture_decision.md` (the ADR). Where this reads as contradicting the ADR's seven locks, the ADR wins. This doc *realizes* the latent "Capability Layer" already named in `docs_v2/integrations.md` (§"Capability Layer", §"Integration Selection") and the capabilities-not-tools framing in `CLAUDE.md`.

---

## 1. The problem

Donna's catalog has grown one tool at a time: `web_search`, `agentic_web_search`, `research` (Exa), `send_email`, `book_ride`, `transfer`, `track_flight`, `check_calendar`, … (see `donna_runtime/tools.py`, `backend/cards/executors.py`). The BRAIN loop reasons directly over **named tools**. Two things break at scale:

1. **No abstraction over providers.** "Book a ride" is hard-wired to `book_ride`. When a second transport provider arrives, every prompt and gate rule that mentioned the tool has to change. `integrations.md` already calls this out: *"Integrations should never be treated as tools. They should be treated as capabilities… Donna should reason about capabilities, not APIs."*

2. **A hard ceiling at the API frontier.** Today Donna can only observe/act where an integration exists (Composio: Gmail + Calendar). The vast majority of a user's digital life — application portals, government trackers, utility accounts, no-API SaaS dashboards — is **dark**. There is no browser-automation layer in the runtime at all (confirmed: zero `kimi`/`browser`/`playwright` references outside the demo recorder).

The fix is one layer and one provider: a **Capability Layer** that lets Donna reason about *what kind of thing it needs to do* and resolve *which provider does it* deterministically; and **Kimi WebBridge** as the Browser Interaction provider that reaches everything behind a login.

---

## 2. The decision, in one sentence

> **A capability is a deterministic abstraction above tools. The BRAIN loop reasons about *which capability* it needs (folded into its normal tool choice — not a new call); a deterministic Capability Registry + Router resolves *which provider* serves it (consent, preference, availability); the Execution gate tiers the action. Kimi WebBridge is the primary Browser Interaction provider. No second reasoning site is added.**

The Capability Layer is **metadata + routing**, exactly like the existing deterministic `event_type → workflow` Router. It never interprets meaning. "Determine the capability, then select the tool" is **not** a perceive-act pre-pass; it is how the one loop already picks tools, made legible by capability framing, with the mechanical provider-resolution lifted into deterministic code.

---

## 3. Reconciling with the ADR (no second reasoning site)

The ADR's Lock 1 is absolute: *reasoning happens in exactly one place.* A capability layer must not become a "classify the request → route" LLM stage (that is the banned Perceive-Act pipeline, ADR §8). It doesn't, because the work splits cleanly:

| Question | Who answers it | LLM? |
|---|---|---|
| *What am I trying to do?* (the capability) | The **BRAIN loop**, as part of choosing a tool — same reasoning it already does | The one loop |
| *Which provider serves that capability here?* | The **Capability Router** — deterministic filter over the registry (consent + availability + learned preference + prefer-API-over-browser) | No |
| *Is this action allowed, and how?* | The **Execution gate** (PreToolUse hook), deterministic tier L0/L1/L2 | No |
| *How do I click through this specific page?* | **Inside Kimi WebBridge** — provider-internal, off Donna's request path | Provider-internal |

The last row is the subtle one. Kimi does its own page-level micro-reasoning ("which field is the passport number"). That is **allowed and does not violate Lock 1**, for the same reason Exa's `/answer` doing its own internal retrieval-and-synthesis is allowed: *Donna's one reasoning site is about the user's life and decisions, not about how to operate a webpage.* The provider's internal cognition is a black-box capability, off-path, billed and bounded by the provider — identical in status to Exa's ranking or a flight API's routing. The per-event budget (ADR §7: one BRAIN loop + ≤1 async extraction) is unchanged: a `browser_task` is **one tool call** from the loop's perspective, however many clicks happen inside it.

**Rule of thumb, mirroring the ADR §5 rule:** if it's "what does this mean / what should I do" → the loop. If it's "which connected provider, given consent and preference" → the registry/router (deterministic). If it's "how to drive the page" → inside the provider. Never add a model call to the path to answer the middle question.

---

## 4. The capability taxonomy

Ten capability categories. They are not all the same *shape* — naming that honestly keeps the model coherent:

- **Modalities of reaching the world** — *how* Donna touches reality: **Information Retrieval** (read the open web), **Browser Interaction** (operate a specific site as the user). These two are the heart of this doc and must stay distinct (§5).
- **Domains** — *what* part of life: **Communication, Scheduling, Transportation, Travel, Finance, Document Handling, File Management**. A domain capability is usually served by an API provider when one exists, and by Browser Interaction as the fallback rail when none does.
- **The commit rail** — **Action Execution**: the cross-cutting capability of *committing a consequential action through the §10.3 gate*. Every write from any domain (send the email, submit the form, pay the bill) terminates here.

### 4.1 Categories → current Donna providers

| # | Capability | Today's provider(s) | Status |
|---|---|---|---|
| 1 | **Information Retrieval** | Exa (`web_search`, `agentic_web_search`, `research`); `recall_*` over the nine memory backends | ✅ live |
| 2 | **Browser Interaction** | **Kimi WebBridge** (`browser_task`, `browser_watch`) | 🆕 this doc |
| 3 | **Communication** | Gmail via Composio (`send_email` executor + ingest); WhatsApp delivery; *(browser fallback for no-API channels)* | ✅ / 🆕 fallback |
| 4 | **Scheduling** | Google Calendar via Composio (`check_calendar`, `_calendar_event`, `schedule`, calendar watch) | ✅ live |
| 5 | **Transportation** | `book_ride` (sandbox); *(Uber/Grab API or browser fallback)* | 🟡 sandbox |
| 6 | **Travel** | `track_flight` + flight watch; `book_restaurant`; *(airline/visa/hotel portals via browser)* | 🟡 / 🆕 fallback |
| 7 | **Finance** | `transfer` (sandbox), finance detectors/waste; *(bank/biller portals via browser)* | 🟡 / 🆕 fallback |
| 8 | **Document Handling** | `Document` model + chunk-recall + `read_gmail_thread`; *(Drive API or portal download via browser)* | 🟡 |
| 9 | **File Management** | `Document` storage (`storage_path`); *(Drive/Dropbox CRUD)* | 🟡 |
| 10 | **Action Execution** | the executor registry + the L0/L1/L2 gate (`backend/cards/gate.py`, `executors.py`) | ✅ live |

Browser Interaction is special: it is both its own capability **and** the universal fallback rail for any domain capability whose preferred API provider is absent. That is what makes it the single highest-leverage addition.

---

## 5. The crux: Information Retrieval ≠ Browser Interaction

The user's constraint is explicit: **Browser Interaction must not replace Information Retrieval. Exa stays.** This is the most important boundary in the doc; getting it wrong makes Kimi cannibalize a cheaper, better tool.

| | **Information Retrieval** (Exa) | **Browser Interaction** (Kimi WebBridge) |
|---|---|---|
| Question it answers | "What does the web *publish* about X?" | "Do something *inside a specific account/portal* that has no API." |
| State | Stateless, anonymous | Stateful, **authenticated as the user** |
| Side effects | None — read only | Navigates, fills, submits — **acts** |
| Auth | None | Per-portal credential grant (consent) |
| Cost / latency | Cheap, sub-second | Expensive, multi-second, flaky |
| Gate tier | Always L2 | L2 (read) / L1 (submit) / L0 (pay·sign·delete) |
| Examples | "current SWE salary bands", "what is a DS-160", flight prices, news | log into the visa portal, track an application's status, fill+submit a form, pay a utility bill on its site |

**The selection rule (deterministic, baked into the capability descriptions):**

> Need to *know* something the open web already publishes → **Information Retrieval (Exa)**.
> Need to *operate* a specific logged-in site → **Browser Interaction (Kimi WebBridge)**.
> Need to *read a fact that only exists behind your login* (your application's status, your bank balance on a no-API bank) → **Browser Interaction in read-only mode** (L2), never Exa.

The loop never "upgrades" an Exa lookup to a browser session for cost reasons, and never drops to Exa when the fact lives behind a login. The capability descriptions encode both the when-to-use and the when-NOT-to-use (per `CLAUDE.md`'s tool-description law), so the loop's own reasoning lands on the right modality.

---

## 6. Kimi WebBridge — the Browser Interaction provider

Kimi WebBridge is a cloud browser-agent: given a goal, a target site, and scoped credentials, it logs in, navigates, fills forms, runs multi-step flows, and extracts structured state — for sites with **no API**.

The five named use cases map to one capability:

- **portal logins** — establish/refresh an authenticated session on a site.
- **application tracking** — read a status page behind login, return structured state.
- **website navigation** — reach a specific page/flow.
- **form filling** — populate a form from the User Model + documents.
- **multi-step browser workflows** — chain the above into a durable process (the headline).

### 6.1 One capability-grained tool, not a click API

Donna exposes Browser Interaction to the loop as **one high-level tool**, not a `click`/`type`/`scroll` micro-API:

```
browser_task(goal, site, mode, inputs?, effect, idempotency_key?, consent_ref)
  goal:    natural-language objective ("read my visa application status")
  site:    registered portal id (consent + credentials resolved by ref, never inline)
  mode:    "read"  | "act"
  effect:  "read" | "submit" | "pay" | "sign" | "delete"   ← the gate keys off this
  inputs:  structured fields the loop assembled (for form-fill), never raw secrets
  returns: { status, extracted: {...}, evidence: [screenshots/urls], steps_log }
```

This is deliberate. A click-by-click tool would (a) drag the BRAIN loop into page micro-reasoning — the wrong reasoning site and a budget blow-up (N tool turns per page) — and (b) couple the prompt to DOM details. A capability-grained tool keeps the loop reasoning about *outcomes* ("operate the portal to do X") while Kimi owns the *mechanics*. Same shape as `research`: one call, rich internal work, structured result.

`browser_watch` is the read-only, recurring sibling (§8.3).

---

## 7. The Capability Registry + Router

`integrations.md` already prescribes a registry (`{name, category, permissions, capabilities, status}`) and a four-step selection (*what capability → which providers → best for the user → permitted → execute*). We formalize both.

### 7.1 Registry schema (deterministic state, one row per provider)

```json
{
  "provider": "kimi_webbridge",
  "capability": "browser_interaction",
  "verbs": ["portal_login", "navigate", "form_fill", "extract", "multi_step"],
  "consent": { "kind": "per_portal_credential", "scope": "per-site", "revocable": true },
  "default_agency": "L1",         // baseline tier; the gate refines per-effect from args
  "reliability": 0.7,             // priors for the router's tie-break
  "cost": "high",
  "status": "connected | pending | revoked | error",
  "preference_signal": 0.0        // learned, from Cap-20 feedback (which provider the user keeps)
}
```

API providers (Composio Gmail/Calendar, a future Uber API) are rows under their domain capability with `cost: low`, `reliability` high. Kimi rows sit under `browser_interaction` **and** are eligible as the fallback for any domain capability with no connected API provider.

### 7.2 The Router (deterministic — no LLM)

```text
loop chooses a capability (its own reasoning)
        │
        ▼
CAPABILITY ROUTER  (pure function over the registry)
  1. providers = registry[capability] ∪ browser_fallback(capability)
  2. drop providers without consent/connection            → if none: emit a consent card
  3. prefer an API provider over Browser Interaction       (lower cost, higher reliability)
  4. break ties by learned preference_signal (Cap 20)
        │
        ├── exactly one viable provider → bind it, the loop calls its tool
        └── genuinely ambiguous + consequential → surface an options card (the user picks)
        ▼
EXECUTION GATE (§10.3)  tiers the concrete action  → L2 auto / L1 card / L0 approve
```

Step 3 is the rule that protects Exa and keeps browser use rare: **a real API always beats driving a browser.** Donna reads Gmail via the API, not by logging into mail.google.com; she only reaches for Kimi when no API exists. Browser Interaction is the rail of last resort, by policy.

The Router is the same species as the existing `event_type → workflow` dict: rules, counts, lookups. It is *not* a place where meaning is interpreted.

---

## 8. How Browser Interaction fits each subsystem

### 8.1 Event System

Browser Interaction is both an **event producer** and an **event consumer**, and it respects every Event System invariant (events are facts, not interpretations; dedup; ordering; replay — `event_system.md`).

- **Producer:** a `browser_watch` observing a portal emits a fact when the page state changes:
  ```json
  { "event_type": "portal_state_changed", "source": "kimi_webbridge",
    "payload": { "site": "ceac.state.gov", "field": "status",
                 "from": "Submitted", "to": "Interview Scheduled" } }
  ```
  No importance in the event (ADR; `event_system.md` §Event Priority). The *meaning* ("your visa moved forward — act now") is the loop's job when the event routes to a workflow.
- **Consumer:** a `browser_task` is the **action a workflow runs as a consequence** of an event (event `visa_slot_opened` → workflow → `browser_task` books the slot).
- **Dedup:** idempotency key on `(site, field, new_value)` so a re-scrape of an unchanged page never re-emits (mirrors the Bus's `source + provider-event-id` dedup, ADR §10.2).
- **Routing:** `portal_state_changed → Browser/Domain Workflow` lives in the same deterministic Router table as `new_email → Email Workflow`.

### 8.2 Workflows

Multi-step browser flows are the headline, and they are a perfect fit for the ADR's Lock 6 (*workflows are deterministic process + state, zero prompt logic*). A **browser workflow** is a durable run (`pending/running/waiting/completed/failed/cancelled`) whose steps are `browser_task`s interleaved with gate pauses:

```text
WORKFLOW: submit_visa_form (durable)
  step 1  assemble        → BRAIN loop fills answers from User Model + documents (reasoning)
  step 2  browser_task    → Kimi fills the form  (mode=act, effect=submit, NOT yet submitted)
  step 3  GATE (L1)       → render a card showing exactly what will be submitted; WAIT for tap
  step 4  browser_task    → Kimi submits          (effect=submit, idempotency_key)
  step 5  confirm         → extract confirmation #, store as Document, close the loop
  on failure → retry step with backoff; compensation = leave draft saved, surface "couldn't submit"
```

Key properties, all ADR-aligned:
- **The workflow holds state and sequences steps; it does not reason.** The loop is invoked only at decision points (step 1 assemble; interpreting a fired watch). Kimi executes mechanical steps. The gate enforces the pause at step 3.
- **Retries + idempotency are first-class** because browser submits are flaky *and* not trivially reversible. Every consequential `browser_task` carries an idempotency key; on retry the executor first checks "did this already land?" before re-submitting (§8.5).
- **Human-in-the-loop is a workflow `waiting` state**, surfaced as an L1/L0 card; the user's tap resumes the run. This is the §10.3 gate made into a workflow pause.
- A **tracking** workflow is the recurring variant: schedule → `browser_watch` (read) → diff → on change, invoke the loop → maybe spawn an action workflow. Long-lived, durable across restarts.

### 8.3 Watchers

`browser_watch` becomes a new `watch_type` beside `reply | web | flight | generic` (`backend/proactive/watches.py`). It is the single biggest unlock: **watch any site that has a login and no API.**

- **Evaluator:** runs a read-only `browser_task(mode=read)` against the portal, diffs the extracted state against `last_known_state` (the same diff-on-change discipline the existing `web` watch uses against Exa URLs), fires **only on genuine change**, and re-arms (or retires) via the existing `rearm_watch` machinery.
- **Adaptive cadence:** reuses `compute_next_check(importance, deadline, stable_checks, recent_change)` unchanged — browser watches are *expensive*, so backing off on stable pages matters more here than anywhere. Clamp the floor higher (e.g. ≥30 min) since each check spins a browser.
- **Context-weighted (ties into the Context Layer):** a `job_search` season raises cadence on application-portal watches; a `travel` season raises cadence on a visa-portal watch — via the `context_weight` cadence bump already wired into `compute_next_check`. The §6.3 retrieval pointers (`## RELEVANT NOW`) surface the portal watch to the loop. Browser watching inherits the whole adaptive-attention layer for free.
- **Fires into the same proactive loop:** `[SYSTEM TRIGGER: watch_fired]` with the diff as stimulus, `mode="proactive"` — identical to every other watch. The loop decides whether it's worth interrupting (tiered delivery applies).

### 8.4 Integrations — consent and credentials (the hard part)

Browser Interaction is the **most sensitive consent surface in the system**: it means Donna can act inside the user's real accounts, often with username/password rather than scoped OAuth. The design must be conservative.

- **Per-portal credential grant.** Consent is *per site*, explicit, scoped, and revocable — never a blanket "Donna can browse as me." It reuses the existing consent-card flow (`resolution.py` `kind=="consent"`), extended from OAuth-only to a credential grant: *"Connect your CEAC visa portal so I can track and act on it?"*
- **Prefer real auth.** Where a portal supports OAuth / passkey / API token, use that (broker via Composio if available). Username/password is the last resort.
- **Vault, never the prompt.** Secrets live in a secrets vault (the `OAuthToken`/secret-storage pattern), referenced by `consent_ref`. They are **never** placed in the loop's context, the tool args, the event payload, screenshots, or logs. `browser_task` receives a *reference*, and Kimi resolves it server-side at session time.
- **Registry citizen.** Kimi is a first-class integration row (§7.1) with its own lifecycle (`Connect → Authenticate → Observe → Generate Events → Support Workflows → Perform Actions`, per `integrations.md`). It is the *primary* Browser Interaction provider; the schema admits future browser-agent providers under the same capability, selected by the same deterministic Router.
- **Boundary with Composio.** Composio = API integrations (OAuth APIs, webhooks). Kimi = the no-API long tail. They never compete for the same job: the Router's prefer-API rule (§7.2 step 3) sends Gmail to Composio and the visa portal to Kimi. Composio is backend-only today; Kimi follows the same posture — a backend integration that surfaces a small, gated tool set to the loop, not a raw browser handed to Claude.

### 8.5 Execution Layer

Browser actions flow through the existing deterministic §10.3 gate (`backend/cards/gate.py`). The gate must classify a `browser_task` **from its args alone** (it cannot reason), keying off the declared `effect`:

| `effect` | Tier | Why | Gate behavior |
|---|---|---|---|
| `read` | **L2** | reversible, no third-party effect | auto-run, then report |
| `submit` | **L1** | acts toward a third party as the user; not trivially reversible | propose a **pre-filled card** showing exactly what will be filled/submitted; execute on tap |
| `pay` | **L0** | moves money | hard-gated approval card every time |
| `sign` / `delete` | **L0** | legal / irreversible | hard-gated approval card every time |

Concrete additions to `gate.py`:
- `_L0_TOOLS ∪= { "browser_pay", "browser_sign", "browser_delete" }` *and* a rule: `browser_task` with `effect ∈ {pay, sign, delete}` → L0; with money-arg hints present → L0 (reusing `_MONEY_ARG_KEYS`).
- `_L1_TOOLS ∪= { "browser_submit" }` *and*: `browser_task` with `effect == submit` → L1.
- default (`effect == read`) → L2, via the existing fall-through.

Plus the non-negotiables already in §10.3:
- **Consent is orthogonal and also required.** No `browser_task` without the portal connected + the standing credential grant. Missing → block + emit the consent card.
- **The tap is the execution trigger.** An L1 browser submit is an `execute`-kind card action wired to a `browser_task` executor in the registry (alongside `send_email`), resolved by `resolution.py`. The card *is* the gate made visible; the filled form is shown before submit.
- **Idempotency for not-trivially-reversible actions.** Every L1/L0 `browser_task` carries an `idempotency_key`; the executor checks "already submitted?" before acting on a retry (browser flakiness makes this mandatory, not optional). `ok=False` leaves the card pending for a safe retry; `ok=True` settles it — the existing executor contract.

### 8.6 Ambient Donna

The ambient model (`Ambient_Donna.md`: reality-first, watch-don't-wait, decision-surfaces-not-info, JIT) is today bounded by the API frontier — Donna is "already on top of it" only where Gmail/Calendar reach. **Browser Interaction extends the entire ambient loop into the long tail of no-API services.**

- **Observe** now includes any site with a login → `browser_watch`.
- **Detect change → Decide → Deliver** runs unchanged on browser-sourced events; the loop reasons, the gate guards, the decision lands as a card.
- The feeling generalizes past the API frontier: *"your visa moved to interview-scheduled — I booked the earliest slot that fits your calendar and added it; here's the confirmation"* — **observed** via `browser_watch`, **acted** via a `browser_task` workflow, **surfaced** as one decision card, **consequential steps tap-gated**.
- It stays capability-shaped end to end: the user thinks the *outcome* ("keep my application on track"), never the mechanism. Donna's loop determines the capability (Browser Interaction), the Router binds Kimi, the gate keeps the submit/pay tap-gated. "She just does it" — now everywhere the user has an account, not only where a vendor shipped an API.

This is also where Browser Interaction compounds with the just-shipped **Context Layer**: a `job_search` or `travel` season raises the cadence and priority of the relevant portal watches and floats them onto the watch bar — so Donna leans her (expensive) browser attention exactly where the user's life currently is.

---

## 9. Worked example — application tracking, end to end

A single thread exercising all six subsystems and the capability split:

1. **Integrations / consent.** User: "keep an eye on my Swiss visa application." Donna needs Browser Interaction; Kimi isn't connected to that portal → **consent card** ("Connect the CEAC portal?"). Tap → credential grant stored in the vault, `consent_ref` issued.
2. **Watchers.** Donna creates a `browser_watch(site=ceac, mode=read)`. Cadence is adaptive; the active `travel` context tightens it; it shows on the watch bar via the `## RELEVANT NOW` pointers.
3. **Information Retrieval stays Exa.** When the user asks "what documents does a Swiss visa need?", that's a *published-web* question → **Exa** (`agentic_web_search`), **not** a browser session. The boundary holds.
4. **Event System.** The watch's read-only `browser_task` extracts `status: "Interview Scheduled"` (was "Submitted") → emits `portal_state_changed` → routes to the Travel/Browser workflow. Dedup on `(ceac, status, "Interview Scheduled")`.
5. **Workflows + the loop.** The workflow assembles context and invokes the BRAIN loop (the one reasoning site): it connects the new status to the user's calendar and the trip dates (Cross-Connection), decides the earliest interview slot that fits, and proposes booking it.
6. **Execution Layer.** Booking the slot is a `browser_task(effect=submit)` → **L1**. Donna renders a pre-filled card ("Book the 9:40 slot on the 22nd?"). Tap → the `browser_task` executor runs with an idempotency key, submits, extracts the confirmation, stores it as a `Document`, closes the open loop.
7. **Ambient.** The user never logged into anything. They thought "keep it on track"; Donna observed behind the login, decided, and acted — with the one consequential step tap-gated. If the portal had instead demanded a fee, step 6 would be `effect=pay` → **L0**, an explicit approval card.

---

## 10. Binding rules (mirroring the ADR)

1. **One reasoning site, unchanged.** The Capability Layer adds **zero** synchronous LLM calls to Donna's request path. Capability *choice* is folded into the loop; provider *resolution* is the deterministic Router; page *mechanics* are provider-internal (Kimi), off-path — exactly as Exa's internals are.
2. **Capabilities are deterministic metadata + routing.** The registry and Router are pure functions over state. No model interprets "what capability" in a separate pass (that is the banned Perceive-Act).
3. **Exa is not replaced.** Information Retrieval and Browser Interaction are distinct capabilities with a deterministic boundary (§5). Browser Interaction never serves a published-web lookup; Exa never serves a behind-login fact.
4. **Prefer API over browser, always.** The Router binds a real API provider before Browser Interaction whenever both can serve a capability. Browser Interaction is the rail of last resort.
5. **Browser writes go through the §10.3 gate, by effect.** `read`→L2, `submit`→L1, `pay`/`sign`/`delete`→L0. Consent (per-portal) is orthogonal and also required. The loop cannot talk past the gate.
6. **Capability-grained, not click-grained.** Donna exposes `browser_task` / `browser_watch`, never a raw click API to the loop. Page micro-reasoning stays inside the provider.
7. **Secrets never touch the path.** Credentials live in a vault, referenced by `consent_ref`; never in prompt, args, events, screenshots, or logs.
8. **Idempotency for every consequential browser action.** L1/L0 `browser_task`s are keyed and retry-safe.

### What stays banned
- A browser handed directly to the BRAIN loop as a click/type/scroll micro-API.
- A "classify the user's request into a capability" LLM pre-pass (Perceive-Act).
- Using Browser Interaction where an API exists, or to answer a published-web question.
- Storing or logging portal credentials in any path-visible surface.
- A workflow that reasons instead of delegating reasoning to the loop.

---

## 11. Build phasing (honest about net-new vs existing)

| Phase | What | Touches |
|---|---|---|
| 0 | **Capability Registry + Router** (deterministic), capability tags on existing tools, capability-framed descriptions (when-to-use / when-NOT) | `donna_runtime/` catalog, a new `capabilities` registry; **no behavior change** — pure refactor of how tools are presented/selected |
| 1 | **Kimi WebBridge integration**: connect/consent (per-portal credential grant + vault), `browser_task(mode=read)` only (L2) | `backend/integrations/`, consent card, secrets vault |
| 2 | **`browser_watch`** watch_type + read-only evaluator + diff + cadence; events into the Bus | `backend/proactive/watches.py`, event Router |
| 3 | **Action**: `browser_task(mode=act)`, gate additions (`browser_submit`→L1, `browser_pay/sign/delete`→L0), `browser_task` executor + idempotency | `backend/cards/gate.py`, `executors.py`, `resolution.py` |
| 4 | **Browser workflows**: durable multi-step (assemble → fill → gate → submit → confirm), retries/compensation | the workflow runner |
| 5 | **Ambient compounding**: context-weighted browser-watch cadence, retrieval pointers, tiered delivery for portal events | already wired via the Context Layer — mostly config |

Phases 0–2 deliver value (capability framing + read-only portal tracking) with **no write risk**; the gate-sensitive action work (3–4) lands behind the existing L0/L1/L2 machinery.

---

## 12. Open questions

- **Vault choice & key custody** for username/password portals (vs. brokering through Composio where OAuth exists).
- **Kimi failure semantics** surfaced to the loop: how much of `steps_log`/evidence to attach as stimulus without bloating context or leaking secrets.
- **Cost governance**: a browser session is orders of magnitude pricier than a Haiku turn — a per-user browser-action budget / rate limit, separate from the LLM budget.
- **Provider portability**: keeping the `browser_task` contract provider-neutral so a second Browser Interaction provider drops into the registry without prompt changes.
- **Legal/ToS posture** of automating third-party portals as the user — per-portal allowlist vs. open-ended.
