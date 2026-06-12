# Donna — Investor Demo Script

**Goal:** make investors *feel the future*. The reaction we engineer is not "cool app" — it's:

> *"oh my god she caught that. how did she catch that."*

**Format:** 75–85 seconds · 9 product moments · 100% phone-screen UI · no humans, no environments · time-of-day stamps as the only overlay · single piano underneath. Built on `docs_v2/donna-demo-v2.md`; this document adds the **technical pre-conditions** for each moment so the demo is reproducible and every "magic" beat is backed by real, seeded state.

**Protagonist:** *Mira* — a founder in Singapore raising a round, mid-relocation, with a life that's quietly on fire. She is never shown. The phone tells the whole story.

**The conceit:** the demo is **one curated day, on day 247**. Donna already knows Mira deeply. Every specific number, name, and time on screen is the proof of that memory — it is read from pre-seeded state, not invented live. The day is compressed: each moment is *triggered on cue* by the demo harness (§ Driving the demo), but each renders through the **real product surfaces** (the same dashboard, cards, watch bar, and resolution path a real user gets).

---

## Pre-seed manifest (what must exist before the lights go down)

Seed this once; the whole 9-moment day plays against it. This is the comprehensive answer to *"what backend state / memories / watches / integrations must already exist"* — the moments reference it.

### Identity & integrations (all pre-connected EXCEPT Grab)
- **User:** Mira · timezone Asia/Singapore · `notify_channel = auto` (app installed + WhatsApp number) · onboarded 247 days ago.
- **Connected:** Google **Gmail** + **Calendar** (Composio, OAuth done) · **banking** (HDFC current + savings, balances synced) · **OpenTable** · **FNP** (flowers) · **Spotify** + **Apple Music** (subscriptions visible) · **WhatsApp Business** + **FCM push**.
- **Deliberately NOT connected:** **Grab** — Moment 6 demonstrates the live consent flow.

### Living Profile & relationships (the `living_profile` + facts + cognition beliefs)
- **Goal:** "raise the round" (category financial, priority 1, active) → seeds a **fundraising context** (Context Layer).
- **Focus window:** `set_focus("fundraising", 10 days)` — so the season-of-life weighting is visibly on.
- **Relationships:** *Aniroodh* (brother, frequent), *Ishaan* (partner), *Priya* (cofounder), *Ravi* (a hire, in negotiation), *Pavithra* (landlord/room), *Kartik* (advisor), *Mom* — birthday **Saturday**, **prefers lilies**.
- **Beliefs (cognition):** "you call mom around noon on her birthday" (high confidence, from history) · "you avoid outreach when the story feels weak" · "Grab Standard is your usual ride" · "you prefer Apple Music."

### Memories (episodic + facts the moments recall)
- Aniroodh's text, last Tuesday: *"the pad see ew, mira. you have to."* → **Lotus Thai, Holland Village**.
- Mira told Ishaan she'd take him to Lotus Thai **Saturday**.
- The **Sequoia** term-sheet thread (in Gmail), partner replied **Tuesday**, awaiting Mira's answer.
- Mom's flower preference (lilies), card-note style ("love, mira").

### Watches (active, with cadence; the "watching" list)
- `reply` · **sequoia partner reply** — waiting since Tuesday · importance high (lifted by fundraising context).
- `web` · **tokyo flights below ₹38k**.
- `reply` · **pavithra response on the room**.
- `reply` · **priya q3 deck feedback**.
- `bill` (implicit via finance) · **AWS auto-pay** — watched until cleared.

### Calendar (today, Thu Apr 18)
9:30 call with Ravi (offer negotiation) · 11:00 dentist (Holland Village) · 14:00 Priya 1:1 (deck owed) · 16:00 Kartik (rescheduled) · 19:30 gym (3rd skip this week) · 22:00 call mom (postponed 4 days).

### Finance (domain tables)
- **HDFC current** ₹43,000 · **HDFC savings** ₹120,000.
- **Bills:** AWS ₹47,200 auto-pay in 4 days (current account ₹4,200 short) · electric (auto-pay tomorrow, covered).
- **Subscriptions:** Spotify ₹229/mo, renews tomorrow, **2 uses this month** (low usage signal) · Apple Music (active, the real driver).

### Admin / tasks & logistics
- Mom's birthday Saturday · Avu's wedding RSVP (deadline Monday) · q3 deck (owed to Priya).

### Lifetime metrics (the moat, for Moment 9)
- **247 days with Donna · 1,847 things caught · 94% delivered on time.**

> Everything below either reads from this manifest or writes a new row that the next moment reads. That's the point: the demo is a chain, not nine islands.

---

## The 9 moments

---

### MOMENT 1 — 7:30am · The dashboard reveal `[5s]`

**What the user sees** — The Donna app opens to the **Dashboard** tab. A slow vertical scroll reveals density: a pinned **"what matters now"** strip, then *watching · 4*, *scheduled · 6*, *logistics · 5*, ending on **"she's holding 23 things for you."**

**What Donna says** — *(silent; the dashboard speaks)*. The watch-bar chips, in priority order set by the fundraising context: **sequoia partner reply** · **aws bill · ₹4,200 short** · **tokyo flights ↓** · **mom's birthday · sat**.

**Backend state required** — `Card` rows (pending), `Watch` rows (active), `CalendarEntry` (today), `Bill` + `FinanceAccount`, `OpenLoop`/tasks, the `holding` count. Served by **`/today` · `/watchbar` · `/watches` · `/cards` · `/library`**.

**Memories required** — the full relationship + goal set (so names render); the fundraising **context** (so the bar is ordered investor-first, not chronologically).

**Watches required** — all four in §pre-seed (sequoia, tokyo flights, pavithra, priya).

**Integrations assumed** — Gmail + Calendar + banking (so the rows are real, not typed).

**UI that appears** — Dashboard tab · the Watch Bar (`rank_attention`) · the three sections · the "holding 23" pulse line.

**Actions that occur** — Read-only. The **`rank_attention` ranker** orders the bar live (goal + context weighting). *Proves: this is not a chatbot — she's already holding a real life, ranked by what matters today.*

---

### MOMENT 2 — 8:42am · The flagged email `[7s]` 🔥

**What the user sees** — A **WhatsApp** notification on the lock screen. Tap → opens Donna in WhatsApp: a 3-line summary of the Sequoia email and three reply buttons.

**What Donna says** —
> heads up. sequoia partner replied to your thread.
> they want your answer by EOD. the term sheet expires tomorrow at noon.
> *tap to see the email + draft a reply.*

Buttons: `[ accept the terms ]` `[ counter on valuation ]` `[ ask for 48 more hours ]`

**Backend state required** — the ingested `EmailMessage` (Sequoia thread); the **importance score** crossing threshold (label + known-sender + **goal_match** + **context_match** = fundraising); a rendered **`Card`** (intent `heads_up`, theme dark) with an `action_map` of `reopen` prompts (each button re-enters the loop to draft).

**Memories required** — the Sequoia thread + the relationship (partner) + the fundraising goal/context (this is *why* it scored high and surfaced first).

**Watches required** — the **sequoia partner reply** watch — its firing is what produced this.

**Integrations assumed** — **Gmail** (ingest + later send), WhatsApp, FCM.

**UI that appears** — WhatsApp push → the heads_up card (header "needs your eye", body with **bold** facts, two-to-three action buttons), projected to the WhatsApp surface.

**Actions that occur** — `proactive_email_trigger` → `email_importance.score_email` → BRAIN loop → `render_card`. A tap = `reopen` → the loop drafts the chosen reply (Gmail `send_email`, L1). *Proves: she doesn't just notify — she reads, ranks, summarizes, and pre-drafts.*

---

### MOMENT 3 — 10:15am · The saved missed payment `[7s]` 🔥

**What the user sees** — A WhatsApp ping with an **approval card**: the AWS bill, the shortfall, a proposed transfer. Mira taps **yes, transfer**. Donna confirms the new balance and says she'll keep watching.

**What Donna says** —
> your aws bill auto-debits in 4 days. ₹47,200.
> your hdfc current account is ₹4,200 short.
> transfer ₹5,000 from savings now?

`[ yes, transfer ]` `[ pause auto-pay ]` `[ remind me tomorrow ]` → on tap:
> done. ₹5,000 moved. balance now ₹52,000. i'll keep watching the bill until it clears.

**Backend state required** — `Bill` (AWS, auto-pay, due in 4d) + `FinanceAccount` (current ₹43,000, savings) → **`detect_low_balance_vs_bill`** returns a shortfall → a **critical**-tier `Card` (intent `approval`, **L0** money gate). The tap runs the `transfer` executor (writes a `FinanceTransaction`).

**Memories required** — which account pays which bill (the debit/fund mapping).

**Watches required** — the **AWS bill** watch (and it continues post-transfer: "i'll keep watching").

**Integrations assumed** — **banking** (balances + the transfer rail; sandboxed ledger in the build).

**UI that appears** — WhatsApp push → approval card with a **delta** block (₹43k → ₹48k, "after"); footer "won't move anything until you tap."

**Actions that occur** — `maybe_surface_finance` → critical card → tap → `transfer` (L0, the tap *is* the authorization) → balance updates → watch persists. *Proves: she does math on your money against the future, and acts only with your tap.*

---

### MOMENT 4 — 1:42pm · The tracker check-in `[8s]` 🔥

**What the user sees** — A WhatsApp ping asking what she had for lunch. Mira types *"biryani and sweet lassi."* Donna logs it and lands the accountability line.

**What Donna says** —
> what did you have for lunch? updating your tracker.

*(Mira: "biryani and sweet lassi")*
> logged. ~1,840 cal so far. ~600 left for dinner.
> heads up — this is day 3 you've crossed your monday goal.
> want me to suggest a lighter dinner around 7?

**Backend state required** — a calorie/health goal + prior `Observation` rows (this week's meals) so "day 3" is a real count; the meal logged as a new `Observation` with a calorie estimate.

**Memories required** — the daily calorie target; the running total; the 3-day streak of crossing it (pattern over observations).

**Watches required** — none (this is a scheduled proactive check, not a watch).

**Integrations assumed** — none beyond WhatsApp (health is self-reported).

**UI that appears** — pure WhatsApp text exchange (no card).

**Actions that occur** — `maybe_checkin_meal` (waking-window, deduped) → BRAIN loop → `log_observation` (meal + calories) → reports total vs goal + the streak. *Proves: she initiates, does the math, and holds you accountable — the $200/mo coach line, for free.*

---

### MOMENT 5 — 2:30pm · Dynamic Island recall while scrolling Instagram `[12s]`

**What the user sees** — Instagram scrolling. A long-press on the **Dynamic Island** opens a waveform. Mira asks (voice; text shown). The island shimmers a search, expands into a recall card **over Instagram still scrolling**, Donna offers to book, Mira says "yeah," and the island collapses to a booked confirmation.

**What Donna says** —
> *(card)* LOTUS THAI · holland village — aniroodh texted you last tuesday: "the pad see ew, mira. you have to." you said you'd take ishaan there saturday.
> *(voice)* want me to book a table for two, saturday 8pm?

*(Mira: "yeah")* → island: `booked · 8pm saturday · 2 people · OpenTable`

**Backend state required** — the recall path (`recall_about` / `recall`) over episodic memory; a **`Card`** (intent `tracker`/`info`) rendered into the ambient island; the `book_restaurant` executor (writes a **real calendar event** as the artifact).

**Memories required** — **two** that collide: Aniroodh's casual text ("pad see ew") *and* the side-plan ("take Ishaan Saturday"). Both seeded as episodic memories with timestamps — the timestamps are the proof.

**Watches required** — none.

**Integrations assumed** — **OpenTable** (booking) + Google **Calendar** (the booking lands there) + **ambient voice** surface (the island).

**UI that appears** — Dynamic Island (waveform → recall card → booking animation → collapsed confirmation), composited over a live Instagram feed.

**Actions that occur** — voice query → `recall_about("lotus thai" / "aniroodh")` → recall card → confirm → `book_restaurant` (L1) → calendar event. *Proves: memory of a throwaway mention days ago + a side conversation, executed agentically, without leaving the app she was in. No one else does this.*

---

### MOMENT 6 — 4:00pm · The Live tab agentic centerpiece `[16s]` ⭐

**What the user sees** — Open Donna → **Live** tab. Mira: *"book me a cab to changi t1 at 5:30am tomorrow."* Donna needs Grab access → a **consent card** slides up → tap **allow** → OAuth flashes → **three interactive ride cards** appear, the middle one marked **recommended · matches your usual** → tap **book** → confirmation → a hard cut shows the **Dashboard** gain a new *5:15am · changi cab* row in real time.

**What Donna says** —
> need access to your grab to book. one tap to allow?

*(after allow, the 3 ride cards; then on book:)*
> booked. driver assigned 5:00am. reminder set for 5:15am. i'll watch for delays.

**Backend state required** — the **consent gate** (Grab not connected → `consent_integration` card) → OAuth → an **options `Card`** (3 rides, one flagged "recommended") → `book_ride` executor (writes a calendar reminder) → a new `CalendarEntry`/schedule row → the dashboard re-reads it (cross-surface sync).

**Memories required** — the **ride preference belief** ("Grab Standard is your usual") — that's the "matches your usual" tag, the memory flex inside an action flow.

**Watches required** — a **delay watch** is created on booking ("i'll watch for delays") — Travel/flight-style monitoring on the ride.

**Integrations assumed** — **Grab** (connected *live*, on stage) + Calendar.

**UI that appears** — Live tab · consent card (intent `consent_integration`) · OAuth flash · options card (3 tappable rides) · confirmation · Dashboard updating.

**Actions that occur** — request → consent gate (L1 + missing scope) → OAuth → options card → tap book → `book_ride` (the tap is the trigger) → schedule + delay-watch → dashboard sync. *Proves: the whole product works end-to-end — Live surface, JIT consent, JIT cards, agentic execution, memory, cross-surface sync. This is the segment that closes the room.*

---

### MOMENT 7 — 6:15pm · The cross-connection `[9s]` 🔥

**What the user sees** — A WhatsApp ping that braids **four** memories into one decision: mom's birthday, the Saturday Lotus Thai plan (from Moment 5), mom's lily preference, and the "you always call her at noon" pattern. Mira taps **yes, send lilies**; Donna orders them, writes the card note, and adds the noon-call reminder.

**What Donna says** —
> mom's birthday is saturday. you have lotus thai at 8pm with ishaan.
> her favorites: lilies. fnp delivers by 10am.
> send ₹1,899 bouquet in the morning?

`[ yes, send lilies ]` `[ different flowers ]` `[ i'll handle it ]` → on tap:
> done. ₹1,899. delivery saturday 9-10am. card note: "happy birthday ma. love, mira."
> adding a reminder to call her at noon — you usually do.

**Backend state required** — `maybe_surface_birthday` (mom's date, lead window) → **cross-connection** (`find_connections`) ties the birthday to the Saturday plan booked in Moment 5 → an **L0** approval `Card` (money: flowers) → `order_flowers` executor → a `schedule` reminder (noon call).

**Memories required** — mom's birthday (relationship), **lilies** (preference fact), the **Saturday plan** (the row Moment 5 wrote — the demo's chain made visible), and the **belief** "you call mom around noon on her birthday."

**Watches required** — none new; this reads the calendar + the just-created Saturday booking.

**Integrations assumed** — **FNP** (flowers, sandboxed) + Calendar + WhatsApp.

**UI that appears** — WhatsApp push → approval card (money) → confirmation with the card-note quoted back → a new scheduled reminder.

**Actions that occur** — birthday check → cross-connect → L0 card → tap → `order_flowers` + `schedule` (noon call). *Proves: she connects information across unrelated domains — the "how does she know what i usually do?" beat. Memory isn't storage; it's understanding.*

---

### MOMENT 8 — 7:48pm · The unsubscribe `[6s]` 🔥

**What the user sees** — A WhatsApp ping flagging Spotify: renews tomorrow, used twice this month, redundant with Apple Music. Mira taps **cancel**; Donna cancels, states the saving, and records the preference she learned.

**What Donna says** —
> spotify renews tomorrow. ₹229.
> you used it twice this month. apple music handles the rest.
> cancel?

`[ cancel ]` `[ keep it ]` `[ remind me next month ]` → on tap:
> cancelled. ₹229/mo saved. i'll remember you preferred apple music.

**Backend state required** — **`detect_waste`** over `FinanceTransaction` history finds the low-use / duplicate-service subscription → an **L1** `Card` (cancel) → the cancel rail → **`form_belief`** writes "prefers Apple Music" (the learning beat).

**Memories required** — Spotify charge history + the **2-uses-this-month** usage signal + the existence of Apple Music (the redundancy).

**Watches required** — none (waste runs on the tick).

**Integrations assumed** — **Spotify** (subscription state) + Apple Music (usage), WhatsApp.

**UI that appears** — WhatsApp push → cancel card (L1) → confirmation.

**Actions that occur** — `maybe_surface_waste` → L1 card → tap cancel → cancel + `form_belief` (learning). *Proves: she audits what you never audit, and she gets smarter from your choice — the cancel teaches her.*

---

### MOMENT 9 — 11:02pm · The day closes + the moat `[10s]`

**What the user sees** — Dashboard → scroll to **TODAY · DONE (8)**: every win from the day, time-stamped. Then **STILL HOLDING (3)**. Then a final scroll reveals the lifetime counter: **247 days · 1,847 caught · 94% on time.** End card: italic serif rust **donna**, *"she texts first."*

**What Donna says** — *(silent; the numbers say everything)*.

**Backend state required** — the resolved `Card` rows from Moments 2–8 (state `acted`), surfaced as the **Done** list with timestamps; the still-active watches/loops as **Still Holding**; the **lifetime metrics** (from the metrics store) for the moat counter.

**Memories required** — the full day's chain (each Done line is a real resolution the demo produced), plus the 247-day aggregate.

**Watches required** — the three still-open: **pavithra room** · **ravi offer** · **priya q3 deck final**.

**Integrations assumed** — all of the above (the Done list spans every integration touched today).

**UI that appears** — Dashboard "Done" + "Still Holding" sections · the lifetime-stats panel · the end card.

**Actions that occur** — read-only projection of the day + the moat metric. *Proves: 8 concrete wins today — and 1,847 before. The longer she runs, the more she knows. Switching away costs everything.*

---

## The moments × proof matrix

| Capability (real engine) | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Memory (the product) | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Proactive ("texts first") | | ● | ● | ● | | | ● | ● | |
| Cross-connection | ● | ● | ● | ● | ● | | ● | ● | |
| Context / season-of-life weighting | ● | ● | | | | | | | |
| Watches + adaptive cadence | ● | ● | ● | | | ● | | | ● |
| JIT decision cards (the gate, made UI) | | ● | ● | | ● | ● | ● | ● | |
| Agentic execution | | ● | ● | | ● | ● | ● | ● | |
| Consent gate (L0/L1/L2) | | ● | ● | | ● | ● | ● | ● | |
| Live tab | | | | | | ● | | | |
| Dynamic Island / ambient voice | | | | | ● | | | | |
| Cross-surface sync (app ↔ WhatsApp) | ● | ● | ● | ● | | ● | ● | ● | ● |
| Learning from feedback | | | | | | ● | | ● | |
| The moat (compounding) | | | | | | | | | ● |

Memory is in all nine — *because memory is the product.* Every other capability appears in 3+ moments.

---

## Driving the demo (how each beat fires on cue)

The demo is a **scripted playback of real surfaces over pre-seeded state** — not a live 24-hour wait and not faked screens. A demo harness fires each moment's trigger on the operator's cue:

1. **Seed** the manifest (one script) → identity, integrations marked connected, memories, beliefs, watches, calendar, finance, subscriptions, metrics.
2. **Each proactive moment (M2, M3, M4, M7, M8)** is fired by invoking its real trigger (`proactive_email_trigger`, `maybe_surface_finance`, `maybe_checkin_meal`, `maybe_surface_birthday`, `maybe_surface_waste`) — which renders a **real card** through the **real loop** and delivers it to the WhatsApp/app surface. The "8:42am / 10:15am" stamps are overlays; the firing is on cue.
3. **Each interactive moment (M2, M3, M5, M6, M7, M8)** resolves through the **real card-action path** (`resolve_card_action` + the L0/L1/L2 gate) so taps do real things and write the rows Moment 9 reads.
4. **M1 and M9** are read-only renders of the seeded + accumulated state.

### Real vs staged rails (be honest internally; seamless on screen)
- **Real on stage:** the loop, memory/recall, importance + context weighting, watches, card rendering + the consent gate, Gmail send, **calendar event creation** (so Lotus Thai + the cab reminder are real artifacts), `form_belief` learning, the dashboard/watch-bar/Done projections.
- **Sandboxed (pluggable; staged confirmation):** the **money transfer**, **OpenTable**/**Grab**/**FNP** third-party bookings, and **live flight/ride delay feeds** — the engine is real, the external rail is stubbed. On screen they show the same confirmation; internally they write a ledger row / a calendar artifact / a recorded intent. *(See `README_TECHNICAL.md` §7.)* For the live Grab OAuth in M6, use the real Composio consent flow against a sandbox app.

---

## Production notes (condensed from `donna-demo-v2.md`)

- **Visual:** phone full-bleed or in a clean iPhone mockup; paper-toned (#FBF7F5) background; italic-serif rust time-stamps top-right (~1s fade-in per moment); hard cuts + a subtle paper-fold transition. Dashboard moments (1, 9) get smooth vertical scroll moves.
- **Audio:** single piano + light strings (not corporate uplift). WhatsApp chimes *are* the percussion. Dynamic-Island sound for M5. Donna's **voice only on M5** (warm, low, lowercase).
- **Copy law (where the demo lives or dies):** every Donna line is **lowercase**, has **specific numbers / names / times**, sounds like a friend not a system, opens proactive beats with **"heads up,"** never uses em dashes, never apologizes or overpromises.
- **Pace:** ~8s/moment average; M6 breathes at ~16s; M1 lands at ~5s; total **75–85s**.

## If you shoot only one
**Moment 4 (the tracker check-in).** Most unexpectedly viral ("she asked what i ate??"), easiest to prototype (pure WhatsApp text), cuttable as an 8-second teaser, and it tests the WhatsApp-surface look before you build the Live-tab footage. If it lands, build the rest.

---

## Why investors lean in

Eight concrete, life-saving wins in 75 seconds — the missed Sequoia email, the bounced auto-pay, the health honesty, the days-old restaurant mention, the 5am cab in 8 seconds, the mom's-flowers cross-connection, the ₹229 nobody audits — and then the reveal: **1,847 more, over 247 days.** The product isn't "an AI assistant." It's a chief of staff whose value **compounds**: the longer she runs, the more she knows, the deeper the moat, the higher the switching cost. The viewer leaves holding their phone, thinking *"how do i get this."*

**End card:** paper · italic serif rust **donna** · *"she texts first."* · hold 2s · cut.
