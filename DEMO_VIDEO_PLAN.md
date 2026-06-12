# Donna — Investor Demo · Shot-by-Shot Video Plan

**The cut:** a **narrated 2–3 minute investor demo** (~2:47, 23 shots). This is the *narrated* cut — distinct from the 75s no-narrator product film in `docs_v2/donna-demo-v2.md`. A calm narrator carries the pitch; the phone carries the proof.

**Two voice layers** (keep them visually + tonally distinct):
- **VO (narrator):** the investor pitch — measured, confident, third-person. *(this is the "Voiceover narration" field below.)*
- **Donna (on screen):** her in-product voice — lowercase, specific, friendly, "heads up" openers. Shown as WhatsApp/UI text (and one spoken line in M5).

**Protagonist:** *Mira* — never shown. 100% phone-screen UI. **Persona, data, and every number come from [`DEMO_DATASET.md`](./DEMO_DATASET.md) / [`DEMO_SEED_DATA.json`](./DEMO_SEED_DATA.json).** Treatment: paper-toned (#FBF7F5) bg, phone full-bleed or in a clean mockup, italic-serif rust time-stamps top-right, hard cuts + a subtle paper-fold, single piano + light strings under the narrator.

**Runtime budget:** Cold open 0:13 · M2 0:18 · M3 0:16 · M4 0:16 · M5 0:22 · M6 0:28 · M7 0:18 · M8 0:12 · M9 0:16 · Close 0:08 → **≈ 2:47**.

---

## COLD OPEN  ·  0:00–0:13

### SHOT 1 — The hook · 0:00–0:04 `(4s)`
- **Screen:** black → paper. Italic serif rust **donna** wordmark fades in, holds.
- **User action:** none.
- **Donna action:** none.
- **VO (narrator):** *"Imagine the best chief of staff in the world. Now imagine she never sleeps, never forgets — and texts you first."*
- **Backend:** none (title card).

### SHOT 2 — Dashboard reveal · 0:04–0:13 `(9s)` · *7:30am*
- **Screen:** Donna app opens to **Dashboard**; slow vertical scroll past *watching · 4 · scheduled · 6 · logistics · 5*, landing on **"she's holding 23 things for you."**
- **User action:** none (auto-scroll camera move).
- **Donna action:** the watch bar sits investor-first: *sequoia partner reply · aws ₹4,200 short · q3 deck · tokyo flights · mom's birthday.*
- **VO:** *"This is one Thursday in a founder's life. Twenty-three open threads — a term sheet, a bill about to bounce, a deck she owes, a mom's birthday. She's holding all of it."*
- **Backend:** `/today` + `/watchbar` (`rank_attention`, goal + **fundraising context** ordering) + the seed (`watches` ×4, `calendar` today, `bills`, `holding=23`). **All from `DEMO_SEED_DATA.json`.**

---

## MOMENT 2 — The flagged email  ·  0:13–0:31  · *8:42am*

### SHOT 3 — The lock-screen ping · 0:13–0:19 `(6s)`
- **Screen:** WhatsApp notification slides onto the lock screen.
- **User action:** glances; thumb hovers.
- **Donna action:** *"heads up. sequoia partner replied to your thread. they want your answer by EOD. the term sheet expires tomorrow at noon."*
- **VO:** *"Eight forty-two a.m. Out of a full inbox, she surfaces exactly one email."*
- **Backend:** `proactive_email_trigger` fired by the **`e_sequoia`** ingest; `email_importance` crosses threshold via *important-label + known-sender + goal_match + context_match* — outranking the seeded newsletter/recruiter; `render_card`. The **`w_sequoia`** reply-watch is what was waiting.

### SHOT 4 — Summary + reply options · 0:19–0:27 `(8s)`
- **Screen:** tap → Donna in WhatsApp: a 3-line summary of the term-sheet email + three reply buttons.
- **User action:** taps the notification; reads.
- **Donna action:** shows `[ accept the terms ] [ counter on valuation ] [ ask for 48 more hours ]`.
- **VO:** *"She read it, ranked it against everything else, and pre-drafted the three answers a founder would actually consider."*
- **Backend:** the `heads_up` card payload (summary blocks + `action_map` of `reopen` prompts). Summary + drafts pre-generated against the static thread.

### SHOT 5 — The draft · 0:27–0:31 `(4s)`
- **Screen:** tap **counter on valuation** → a tight drafted reply appears → "sent."
- **User action:** taps one button.
- **Donna action:** drafts the counter in her voice; on confirm: *"sent."*
- **VO:** *"One tap. The thing that could've cost her the round — handled before nine."*
- **Backend:** tap → `reopen` → loop drafts → Gmail `send_email` (real engine; demo sends to a test inbox). L1.

---

## MOMENT 3 — The saved payment  ·  0:31–0:47  · *10:15am*

### SHOT 6 — The shortfall card · 0:31–0:39 `(8s)`
- **Screen:** WhatsApp ping → an **approval card**: AWS bill, the shortfall, a proposed transfer with a balance delta.
- **User action:** reads.
- **Donna action:** *"your aws bill auto-debits in 4 days. ₹47,200. your hdfc current account is ₹4,200 short. transfer ₹5,000 from savings now?"* + `[ yes, transfer ] [ pause auto-pay ] [ remind me tomorrow ]`.
- **VO:** *"Nobody watches their balance against an auto-debit four days out. She does."*
- **Backend:** `maybe_surface_finance` → `detect_low_balance_vs_bill` over **`bill_aws`** (₹47,200, due +4d) vs **`acct_current`** (₹43,000) → **critical** L0 approval card.

### SHOT 7 — Transfer + keep watching · 0:39–0:47 `(8s)`
- **Screen:** tap **yes, transfer** → confirmation.
- **User action:** taps yes.
- **Donna action:** *"done. ₹5,000 moved. balance now ₹52,000. i'll keep watching the bill until it clears."*
- **VO:** *"Math on her money, an action with consent, and she keeps watching. That's a bounce fee she'll never see."*
- **Backend:** `transfer` executor (L0; **sandboxed ledger** — no real money) → balance update; the AWS watch persists.

---

## MOMENT 4 — The tracker check-in  ·  0:47–1:03  · *1:42pm*

### SHOT 8 — She asks first · 0:47–0:53 `(6s)`
- **Screen:** WhatsApp ping.
- **User action:** none yet.
- **Donna action:** *"what did you have for lunch? updating your tracker."*
- **VO:** *"This is the part no app does — she starts the conversation."*
- **Backend:** `maybe_checkin_meal` (waking-window, deduped) against goal **`g_health`**.

### SHOT 9 — Logged + the honest line · 0:53–1:03 `(10s)`
- **Screen:** user types *"biryani and sweet lassi"* → Donna replies in real time.
- **User action:** types the reply.
- **Donna action:** *"logged. ~1,840 cal so far. ~600 left for dinner. heads up — this is day 3 you've crossed your monday goal. want me to suggest a lighter dinner around 7?"*
- **VO:** *"She does the math — and she's honest with you. Day three. The accountability you'd pay a coach two hundred a month for."*
- **Backend:** `log_observation` (meal + a pre-set calorie estimate for the scripted input); the "day 3" streak is **real** over the seeded **`obs_mon/tue/wed`** observations.

---

## MOMENT 5 — Dynamic Island recall  ·  1:03–1:25  · *2:30pm* ⭐

### SHOT 10 — Long-press, mid-scroll · 1:03–1:08 `(5s)`
- **Screen:** **Instagram** feed scrolling. Long-press on the **Dynamic Island**; a thin waveform opens.
- **User action:** long-presses the island while scrolling Instagram.
- **Donna action:** waveform listening.
- **VO:** *"She lives everywhere you do — even inside another app."*
- **Backend:** ambient-voice surface (the island — a scripted overlay; the recall behind it is real).

### SHOT 11 — The recall over Instagram · 1:08–1:17 `(9s)`
- **Screen:** *(voice, text shown)* "donna, what was the restaurant aniroodh kept telling me about?" → search shimmer → a recall card expands **over Instagram still scrolling**.
- **User action:** speaks the query.
- **Donna action:** card: *"LOTUS THAI · holland village. aniroodh texted you last tuesday: 'the pad see ew, mira. you have to.' you said you'd take ishaan there saturday."*
- **VO:** *"A throwaway text from days ago. A side-plan she overheard. She kept both."*
- **Backend:** `recall_about("lotus thai" / "aniroodh")` over the seeded episodic **`mem_lotus`** + **`mem_saturday`** (the timestamps are the proof).

### SHOT 12 — Book it · 1:17–1:25 `(8s)`
- **Screen:** Donna offers; Mira answers; the island shows a booking animation, then collapses to a confirmation. Instagram still scrolling throughout.
- **User action:** *"yeah."*
- **Donna action:** *(spoken)* "want me to book a table for two, saturday 8pm?" → island: `booked · 8pm saturday · 2 people · OpenTable`.
- **VO:** *"Memory, and execution — without ever leaving the app she was in."*
- **Backend:** `book_restaurant` (L1; OpenTable **mocked**, **real calendar event written** — the row M7 reads).

---

## MOMENT 6 — The Live tab centerpiece  ·  1:25–1:53  · *4:00pm* ⭐

### SHOT 13 — The ask · 1:25–1:31 `(6s)`
- **Screen:** open Donna → **Live** tab (conversational, active). Mira types/speaks.
- **User action:** *"book me a cab to changi t1 at 5:30am tomorrow."*
- **Donna action:** *"need access to your grab to book. one tap to allow?"*
- **VO:** *"This is the Live tab — where you ask, and she acts."*
- **Backend:** Live chat loop; Grab **not connected** in the seed → consent required.

### SHOT 14 — Just-in-time consent · 1:31–1:38 `(7s)`
- **Screen:** a **consent card** slides up (what Donna will be able to do) → tap **allow** → a brief OAuth flash → card slides away.
- **User action:** taps **allow**.
- **Donna action:** requests scope; on grant, proceeds.
- **VO:** *"Consent, exactly when it's needed — not a settings menu she'll never open."*
- **Backend:** `consent_integration` card (real); Grab OAuth **mocked flash** (or Composio sandbox).

### SHOT 15 — Interactive ride cards · 1:38–1:47 `(9s)`
- **Screen:** three ride cards appear; the middle marked **recommended · matches your usual**. Mira taps **book** on Standard.
- **User action:** taps **book** on Grab Standard.
- **Donna action:** surfaces the options; flags the one that matches her history.
- **VO:** *"Options, in line — and she already knows which one is hers."*
- **Backend:** options card (rides **pre-generated**; no real Grab API); the *"matches your usual"* tag is **real memory** (belief **`b_grab`**).

### SHOT 16 — Execute + sync · 1:47–1:53 `(6s)`
- **Screen:** confirmation in Live → **hard cut** to Dashboard gaining a new **5:15am · changi cab** row in real time.
- **User action:** none.
- **Donna action:** *"booked. driver assigned 5:00am. reminder set for 5:15am. i'll watch for delays."*
- **VO:** *"Booked, reminded, monitored — and the dashboard updates itself. The whole product, in one breath."*
- **Backend:** `book_ride` (L1; **sandboxed** → real calendar reminder + a **delay watch**); **real cross-surface sync** (`/today` re-reads the write).

---

## MOMENT 7 — The cross-connection  ·  1:53–2:11  · *6:15pm* ⭐

### SHOT 17 — Four memories collide · 1:53–2:03 `(10s)`
- **Screen:** WhatsApp ping braiding the birthday, the Saturday booking from M5, mom's lilies, and the noon-call pattern.
- **User action:** reads.
- **Donna action:** *"mom's birthday is saturday. you have lotus thai at 8pm with ishaan. her favorites: lilies. fnp delivers by 10am. send ₹1,899 bouquet in the morning?"* + `[ yes, send lilies ] [ different flowers ] [ i'll handle it ]`.
- **VO:** *"Her mom's birthday. The Saturday she just booked. The flowers her mom loves. Four memories, one decision. This is where investors lean in."*
- **Backend:** `maybe_surface_birthday` (mom's date) → `find_connections` ties it to the **Saturday Lotus Thai row written in M5** + the lilies fact (**`mem_mom_lilies`**) + belief **`b_mom_noon`** → L0 money card.

### SHOT 18 — Sent + the pattern · 2:03–2:11 `(8s)`
- **Screen:** tap **yes, send lilies** → confirmation with the card note quoted; a new noon reminder.
- **User action:** taps yes.
- **Donna action:** *"done. ₹1,899. delivery saturday 9-10am. card note: 'happy birthday ma. love, mira.' adding a reminder to call her at noon — you usually do."*
- **VO:** *"'You usually do.' That's not storage. That's understanding."*
- **Backend:** `order_flowers` (L0; FNP **mocked**) + `schedule` (noon reminder).

---

## MOMENT 8 — The unsubscribe  ·  2:11–2:23  · *7:48pm*

### SHOT 19 — The audit · 2:11–2:17 `(6s)`
- **Screen:** WhatsApp ping flagging Spotify.
- **User action:** reads.
- **Donna action:** *"spotify renews tomorrow. ₹229. you used it twice this month. apple music handles the rest. cancel?"* + `[ cancel ] [ keep it ] [ remind me next month ]`.
- **VO:** *"She audits the things you never do."*
- **Backend:** `maybe_surface_waste` → `detect_waste` over the seeded **`txn_spot_*`** vs **`txn_apple_*`** (duplicate music service + 2 uses) → L1 cancel card.

### SHOT 20 — Cancelled + learned · 2:17–2:23 `(6s)`
- **Screen:** tap **cancel** → confirmation.
- **User action:** taps cancel.
- **Donna action:** *"cancelled. ₹229/mo saved. i'll remember you preferred apple music."*
- **VO:** *"And she gets smarter from every choice you make."*
- **Backend:** cancel (L1; **sandboxed**) + `form_belief` writes **`b_applemusic`** (the learning).

---

## MOMENT 9 — The day closes + the moat  ·  2:23–2:39  · *11:02pm*

### SHOT 21 — Today, done · 2:23–2:31 `(8s)`
- **Screen:** Dashboard → scroll to **TODAY · DONE (8)** — every win, time-stamped — then **STILL HOLDING (3)**.
- **User action:** none (scroll).
- **Donna action:** the day's resolved cards, listed.
- **VO:** *"Eight things, handled, in a single day."*
- **Backend:** `/cards` + `/today` projection of the cards resolved across M2–M8 (**state `acted`**); the 3 still-open watches/loops.

### SHOT 22 — The moat · 2:31–2:39 `(8s)`
- **Screen:** scroll reveals **247 DAYS WITH DONNA · 1,847 THINGS CAUGHT · 94% DELIVERED ON TIME.**
- **User action:** none.
- **Donna action:** none.
- **VO:** *"And eighteen hundred more before it. The longer she runs, the more she knows — and the harder she is to leave. That's the moat."*
- **Backend:** the lifetime metrics (**seeded** — `dashboard.lifetime`).

---

## CLOSE  ·  2:39–2:47

### SHOT 23 — End card · 2:39–2:47 `(8s)`
- **Screen:** paper. Italic serif rust **donna**. Below: *"she texts first."* Hold 2s. Cut.
- **User action:** none.
- **Donna action:** the wordmark.
- **VO:** *"Donna. She doesn't wait to be asked. **She texts first.**"*
- **Backend:** none (end card).

---

## Production notes

- **Narrator:** warm, low, unhurried, certain. Pitch register — *never* reads Donna's lines. Leave 0.5–1s of silence after each Donna beat before the next VO so her line lands.
- **Donna's voice (audible) only in M5** — the Dynamic Island invites it. Everywhere else she is read as on-screen text.
- **Music:** single piano + light strings, low under the VO; the WhatsApp chimes are the percussion — let them ring. A small lift under M6 (the centerpiece) and again under M9 (the moat reveal).
- **Time-stamps:** italic serif rust, top-right, ~1s fade-in at each moment.
- **Transitions:** hard cut + subtle paper-fold between moments; the dashboard moments (Shot 2, 21–22) get smooth vertical scroll camera moves; M16's app→dashboard cut must be *instant* (the sync is the point).
- **Copy law (the demo lives or dies here):** every Donna line is lowercase, has specific numbers/names/times, sounds like a friend, opens proactive beats with "heads up," no em dashes, no apologies.
- **Pace:** ~7s/shot average; M6 (the centerpiece) and M5 breathe; cold open + close are tight. **Total ≈ 2:47** — trim Shot 5 / Shot 19 first if you need to land under 2:40.

## Two-minute cut (if required)
Drop Shot 1 (open cold on the dashboard), compress M4 to one shot, and trim M8 to a single 5s beat → **≈ 2:05**. Never cut **M5, M6, M7** (recall · centerpiece · cross-connection) — they are the demo.
