# Donna — Features & Roadmap (one unified catalog)

Every capability Donna has and is building, woven into one list — not split into
"can do" vs "will do." Each entry says the **goal** (what the user gets) and
**how it works** (the intuitive mechanism in the backend that reaches that goal).
A phased build roadmap follows at the end.

**Status legend:** ✅ live & tested · 🟡 engine live, third-party rail sandboxed (or UI parked) · 🔜 next (architected, building) · 🧭 later (designed, not started)

**The one rule everything obeys:** reasoning happens in exactly *one* place — a single Claude Agent SDK tool-use loop (the BRAIN, on Haiku 4.5). Everything below is either that loop, a *deterministic service that decides when the loop runs and with what*, a *tool the loop can call*, or a *hook that fires around it*. There is no second AI making decisions anywhere. That is why a full chief-of-staff costs ~a penny per turn.

---

## 1 · How she thinks (the foundation)

- **One-brain reasoning loop** ✅ — *Goal:* behave like a person with judgment, cheaply. *How:* one LLM call per event interprets meaning, weighs importance, connects facts, and picks an action by calling a tool; the standing profile is cached so repeat turns are near-free.
- **Nine-backend memory** ✅ — *Goal:* remember everything that might matter, in the right shape. *How:* an entity/graph store (FalkorDB), episodic + document-chunk stores (Supermemory), procedural rules, observations, open loops, the Living Profile, chat, and calendar — all read on demand through `recall_*` tools, never pre-stuffed into the prompt.
- **Belief graph / cognition** ✅ — *Goal:* hold *opinions* about you, not just a transcript. *How:* evidence accrues on a subject; a deterministic aggregator turns corroboration/contradiction into a stated belief with a confidence and polarity, shown in the app as her reasoning.
- **Living Profile / User Model** ✅ — *Goal:* a stable sense of who you are that frames every turn. *How:* identity, decision style, top relationships, and active goals live in the cached system prompt; updated off the request path by a periodic distillation, never reloaded mid-turn.
- **The season-of-life context layer** ✅ — *Goal:* a *different* sense of "what matters" for each phase of your life, switched automatically. *How:* a separate store of probabilistic, decaying "seasons" (travel, fundraising, exams, job-search…) inferred by arithmetic over signals you already produce (calendar, watches, goals, inbox-thread density) combined with a noisy-or; one weighting function then nudges prioritization, email scoring, watch cadence, delivery, and the prompt — so recomputing the season rebalances the whole system at once. When a significant season turns confident she asks once ("looks like you're traveling — prioritize logistics?"); a tap pins it.
- **The capability layer** ✅ (Phase 0) — *Goal:* reason about *what kind of thing to do* instead of memorizing tools. *How:* a deterministic registry tags every tool/integration with a capability; a pure router resolves which provider serves it (consent + preference + *prefer a real API over driving a browser*). The loop picks the capability; the router picks the provider; no extra reasoning.

## 2 · How she notices (awareness)

- **Event system** ✅ — *Goal:* react to change instead of being asked. *How:* every change (an email, a calendar shift, a watcher firing, a scheduled tick) becomes a fact in an events table; a deterministic router maps `event_type → workflow`; the workflow assembles context and wakes the loop. Persisted, deduped, replayable.
- **Active watch system** ✅ — *Goal:* keep an eye on anything unresolved. *How:* a watch (reply / web-topic / flight / generic today; **browser next** 🔜) stores what to monitor; a sweep re-checks it on an *adaptive cadence* (`next_check = f(importance, deadline, stability, recent change)`), diffs against last-known state, and only fires the loop on a genuine change.
- **Proactive engine — "she texts first"** ✅ — *Goal:* be already on top of it. *How:* a runner ticks ~11 cheap deterministic checks (finances, subscription waste, schedule conflicts/overload, upcoming-event prep, due admin tasks, meals, birthdays, interests, season refresh, season confirmation) plus the watch sweep; each stays silent until it clears a bar, then hands a `[SYSTEM TRIGGER]` to the same loop in proactive mode.
- **Cross-connection intelligence** ✅ — *Goal:* the "how did she catch that?" move. *How:* when an event shifts (a meeting moves), a deterministic pass walks the connection set (people, conflicts, neighbors, open loops) and, if something is genuinely affected, hands the loop one stimulus to propose a single coordinated fix.
- **Opportunity & risk detection** ✅ — *Goal:* surface the good and the dangerous before you notice. *How:* deterministic detectors emit signals — interests become web-watches, finance waste/savings, deadline/doc-expiry/payment risk — and the loop decides severity and whether to interrupt.

## 3 · How she decides what matters (prioritization)

- **Importance scoring + the watch bar** ✅ — *Goal:* never spam you; lead with what counts now. *How:* a deterministic ranker scores every pending card, active watch, and due task by goal-match, relationship weight, deadline proximity, and the season weight — the dashboard's "what matters now" strip reads that order.
- **Goals drive prioritization** ✅ — *Goal:* weigh things by *why* they matter to you. *How:* active goals contribute keyword/relevance weight into the same scorers (an investor email matters more while fundraising is a goal).
- **Tiered contextual delivery** ✅ — *Goal:* interrupt rarely, and only relevantly. *How:* a delivery policy maps an item to critical/high/medium/low; critical interrupts, low is "held" (lands on the dashboard, no buzz); the season layer shifts the tier (focus-relevant up, off-focus down) without ever lowering a critical.
- **Morning brief** ✅ — *Goal:* every day starts with Donna. *How:* once per morning, a deterministic composer gathers the day's finance/schedule/deadline/top-watch items, goal-ranks them, and stays silent on an empty day.
- **Structured decision support** 🟡→🔜 — *Goal:* "here are the 3 options and the trade-off." *How today:* options cards + on-demand research. *Next:* a deterministic compare builder (flights/tools/plans → options + trade-offs table) the loop fills.

## 4 · What she handles (domains)

- **Communication** ✅ (email) / 🧭 (more channels) — *Goal:* understand and act on your conversations. *How:* Gmail is ingested and scored for importance; she can draft and send, set reply-watches, and escalate; **Slack / SMS / calls** 🧭 plug into the same ingest→importance→reply spine as new producers.
- **Scheduling** ✅ — *Goal:* protect and coordinate your time. *How:* real Google Calendar read/create/move, plus deterministic conflict and overload detection; **focus-time protection and multi-party coordination** 🧭 extend the same calendar-math layer.
- **Relationships** ✅ / 🧭 — *Goal:* treat people as relationships, not contacts. *How:* relationships + preferences live in the Living Profile; birthday lead-times prep gifts/calls; **neglected-relationship nudges and first-class gift/style fields** 🧭 add new detectors over the same store.
- **Travel** 🟡 — *Goal:* movement that never surprises you. *How:* a real flight-watch engine (status/delay → moves the calendar event → flags the downstream consequence in one message); **trains, hotels, and itinerary building** 🧭 add provider adapters; airline/visa portals come via **browser interaction** 🔜.
- **Finance** ✅ / 🟡 — *Goal:* protect you from money surprises. *How:* real detectors for shortfall and waste (duplicate charges, price creep, spending spikes) from transactions; the **bank transfer rail** 🟡 is engine-real but sandboxed pending a real rail.
- **Health** 🟡 — *Goal:* gentle accountability to your goals. *How:* meal check-ins log and total against a goal today; **exercise, sleep, and habit tracking** 🧭 are new observation types + check-ins on the same loop.
- **Personal ops / admin** ✅ — *Goal:* nothing with a deadline ever slips. *How:* an admin task is an open loop with a due date and category; a deterministic deadline check surfaces the most urgent one and helps you finish it.
- **Documents & files** 🟡 — *Goal:* understand your paperwork and find it later. *How:* uploaded docs are stored and chunk-indexed for recall; deadlines inside them become tasks; **generation (drafts, forms, briefs) and Drive/Dropbox file CRUD** 🧭 add write tools.
- **Commitments** ✅ — *Goal:* track what you owe and who's waiting on you. *How:* open loops + reply-watches + due tasks; **a dedicated extractor on every inbound message** 🔜 will catch commitments without relying on the loop noticing.

## 5 · How she acts (execution)

- **Three-tier execution gate** ✅ — *Goal:* act usefully without ever doing something irreversible behind your back. *How:* a deterministic classifier reads the tool + arguments and assigns L2 (auto, reversible — log, draft), L1 (confirm — send as you, on a tap), or L0 (approve every time — money, legal, irreversible); the loop cannot talk past it, and your tap *is* the execution trigger.
- **Action executors** ✅ / 🟡 — *Goal:* turn a tap into a real-world effect. *How:* a registry runs the tapped action server-side (send the email is real via Gmail; transfer / book-ride / book-restaurant / order-flowers are engine-real but rail-sandboxed 🟡), settling the card only on success and idempotent on retry.
- **Capability router dispatch** ✅→🔜 — *Goal:* pick the right hands for the job. *How:* the loop names a capability; the deterministic router binds a provider (preferring a real API; falling back to the browser only when none exists); the gate then tiers the concrete action.
- **Browser interaction — acting past the API frontier** 🔜 — *Goal:* log in and act on *any* site you have an account on, even with no API (portal logins, application tracking, navigation, form filling, multi-step flows). *How:* a browser-agent provider (**Kimi WebBridge**) exposes one capability-grained tool the loop calls with a goal + target site + an *effect* (read/submit/pay); page mechanics happen inside the provider (off Donna's reasoning path, like web-search internals); a read is L2, a submit L1, a payment L0; credentials live in a vault, never in the prompt. The capability layer that makes this drop in cleanly is already shipped.

## 6 · Where she lives (surfaces)

- **WhatsApp + app, one memory** ✅ — *Goal:* talk to her where you already are. *How:* both surfaces drive the same loop and the same nine memory backends; a card renders identically as WhatsApp buttons or app UI from one payload.
- **The dashboard — "her brain exposed"** ✅ — *Goal:* open the app to see what she *believes*, not to message. *How:* a deterministic projection of watches, schedule, commitments, trackers, and the attention bar; a Library drawer exposes everything she's holding (people, documents, trackers, to-dos, connections).
- **Beliefs & Memory views** 🟡 — *Goal:* show her reasoning and her knowledge of you. *How:* both are backend-live and real-data-backed; the UI is built but currently parked — resurfacing is frontend wiring 🔜.
- **Information retrieval (web)** ✅ — *Goal:* real-world answers instead of "go check an app." *How:* Exa-backed single-shot search, synthesized answers, and deep research — kept strictly distinct from browser interaction (published web vs. behind-your-login).
- **Illustration** ✅ — *Goal:* a hand-drawn image when it helps. *How:* an image tool generates on demand.
- **Ambient voice** 🧭 — *Goal:* open the app and she *tells* you what matters. *How:* a voice gateway over the same awareness layer (the watch bar / brief become spoken) — the biggest net-new surface; the awareness it speaks already exists.

## 7 · How she gets better (learning)

- **Continuous learning from feedback** ✅ — *Goal:* every tap teaches her. *How:* card intent + outcome aggregate into learned preferences that raise/lower future proactive bars and tune thresholds (e.g. someone who dismisses confirmations gets asked less).
- **Async memory extraction** ✅ — *Goal:* convert each turn into durable memory without slowing the reply. *How:* one cheap post-turn call extracts preferences/relationships/goals/commitments off the request path.
- **Periodic User-Model distillation** ✅ — *Goal:* let stable habits harden into identity. *How:* an off-path batch slowly folds repeatedly-confirmed patterns ("travels monthly") into the Living Profile — never on the request path.

---

## Build roadmap — how we get to everything not yet ✅

Each phase says, intuitively, how the backend reaches the goal. Sequenced so value lands early and risky (write/irreversible) work sits behind machinery that already exists.

**Now → Next (architected, building)**

1. **Browser interaction, read-only** 🔜 — *Goal:* watch and read any logged-in site. *How:* connect **Kimi WebBridge** as the Browser Interaction provider behind a per-site credential grant (vaulted, consent-carded); ship a read-only `browser_task` (always L2) and a `browser_watch` watch-type whose evaluator scrapes a portal, diffs the state, and fires the loop on change — inheriting the season layer's cadence weighting for free. *Unlocks:* application tracking, visa/portal status, no-API account monitoring.
2. **Browser interaction, acting** 🔜 — *Goal:* fill and submit on your behalf, safely. *How:* add `browser_task` in act mode with an `effect` arg; teach the gate `submit → L1`, `pay/sign/delete → L0`; route the tap through a browser executor with an idempotency key (browser submits are flaky and not reversible). *Unlocks:* form filling, multi-step browser workflows as durable runs that pause at the gate.
3. **Un-sandbox the rails** 🟡→✅ — *Goal:* actually move money / hail the car / make the booking. *How:* swap the stubbed executors for real provider rails (bank/UPI, Uber/Grab, OpenTable, a florist) behind the existing L0/L1 gate — the engines and gating are already real, this is integration work.
4. **Resurface Beliefs & Memory tabs** 🟡→✅ — *Goal:* make "beliefs are the product" visible. *How:* mount the built, real-data-backed views and wire the constellation to the cognition graph — frontend only.
5. **Dedicated commitment extractor** 🔜 — *Goal:* never miss "I'll get back to you Friday." *How:* a deterministic pass on every inbound message that proposes open-loops/reply-watches, instead of relying on the loop to notice.

**Later (designed, not started)**

6. **More channels** 🧭 — *Goal:* across your whole digital life. *How:* Slack / SMS / call-awareness become new event producers feeding the same ingest → importance → reply spine; no new reasoning.
7. **Ambient voice** 🧭 — *Goal:* she speaks what matters. *How:* a voice gateway renders the existing brief/watch-bar awareness as audio and accepts spoken turns into the same loop.
8. **Vertical depth** 🧭 — *Goal:* go deep where breadth isn't enough. *How:* add domain objects on the same spine — health trackers (new observation types), trains/hotels/itineraries (provider adapters), a study-schedule builder, an application/interview pipeline, a fundraising-pipeline object (stages, investors, next-actions).
9. **Specific chief-of-staff behaviors** 🧭 — *Goal:* the moves a great human CoS makes. *How:* deterministic detectors/tools over existing data — focus-time protection (defend deep-work blocks), multi-party availability coordination, neglected-relationship nudges, document generation, and structured decision-compare — each feeding the one loop.

**The invariant across every phase:** new capability = a new deterministic detector, tool, provider, or hook feeding the *same* single reasoning loop. We never add a second place that reasons, and we never let an action skip the L0/L1/L2 gate. That keeps the cost (~a penny per turn) and the trust model intact no matter how wide the surface grows.
