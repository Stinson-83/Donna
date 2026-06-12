# Donna — Demo Dataset (the seed behind the demo)

The complete, internally-consistent fictional user that makes every moment in [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md) real. This is the **seed manifest** — load it once and the 9-moment day plays against it, each "magic" line read from this state, not invented live.

Structured to map onto the actual backend models (see [`README_TECHNICAL.md`](./README_TECHNICAL.md) §5–7), and every row is tagged with the **moment(s)** it supports. No code — this is the data design.

> **Note:** all people, the company, the fund partner, and contact details are **fictional** and illustrative. Fund names are used only as scenario flavour, with fictional partners and addresses.

---

## 0. The user, in one breath

**Mira Sharma**, 29 — founder & CEO of **Marble** (a developer-infrastructure startup), based in **Singapore** (Holland Village), originally from Bengaluru. She is **mid-raise** (Series A, Sequoia leading) and **mid-relocation** (sorting a new flat). She banks in India (HDFC). She has been with Donna for **247 days**.

Her life this week is quietly on fire: a term sheet expiring, a key hire to close, a deck she owes her cofounder, a mom's birthday she keeps almost-forgetting, a health goal she keeps blowing past, and a 5am flight Friday. Donna holds all of it.

| Field | Value | Model |
|---|---|---|
| name | Mira Sharma | `User.name` |
| timezone | Asia/Singapore | `User.timezone` |
| notify_channel | `auto` (app installed + WhatsApp +65…) | `User.notify_channel` |
| onboarded | 247 days ago | — |
| home base | Singapore · Holland Village | living profile |

### Integrations (all connected EXCEPT Grab)
| Integration | State | Used in |
|---|---|---|
| Google **Gmail** | connected (OAuth) | M1, M2 |
| Google **Calendar** | connected | M1, M5, M6, M7, M9 |
| **Banking** (HDFC current + savings) | connected, balances synced | M1, M3 |
| **OpenTable** | connected | M5 |
| **FNP** (flowers) | connected | M7 |
| **Spotify** + **Apple Music** | connected (subscription + usage visible) | M8 |
| **WhatsApp Business** + **FCM push** | connected | M2, M3, M4, M7, M8 |
| **Grab** | **NOT connected** | M6 (live consent) |

---

## 1. Goals  → `goals` table + the Context Layer

| # | Goal (title) | Category | Priority | Status | Supports |
|---|---|---|---|---|---|
| G1 | **close the Series A** | financial | 1 | active | M1 (ranking), M2 (email matters more) |
| G2 | **stay under ~1,900 cal/day, drop 4kg before the move** | health | 2 | active | M4 (the tracker) |
| G3 | **get the new flat sorted** | personal | 3 | active | the Pavithra thread, "the move" |

**Focus window (declared):** `set_focus("fundraising", 10 days)` — high-confidence, expiring. → an active **fundraising context** that visibly orders the dashboard investor-first (M1) and lifts investor email (M2). *(Context Layer.)*

---

## 2. Relationships  → `living_profile.biography.relationships`

| Name | Relation | Importance | Frequency | Email/contact | Birthday | Notes / prefs | Supports |
|---|---|---|---|---|---|---|---|
| **Aniroodh Sharma** | brother | 90 | weekly | aniroodh@… | — | the family foodie; sends restaurant recs | M5, M7 |
| **Ishaan** | partner | 92 | daily | ishaan@… | — | the Saturday Lotus Thai plan is with him | M5, M7 |
| **Priya Menon** | cofounder / CTO | 95 | daily | priya@marble.dev | — | owed the q3 deck; you defer to her on pricing | M1, M2(deck), M9 |
| **Ravi Iyer** | Head-of-Eng candidate | 70 | this week | ravi@… | — | offer out; 9:30 negotiation call | M1 |
| **Pavithra** | landlord (new flat) | 60 | this week | pavithra@… | — | awaiting her reply on the room | M1, G3 |
| **Kartik Shah** | advisor | 65 | monthly | kartik@… | — | 4pm, rescheduled from yesterday | M1 |
| **Mom — Anjali Sharma** | mother | 96 | weekly | anjali@… / +91… | **Sat 20 Apr** | **prefers lilies**; you call her ~noon on her birthday | M7 |
| **Avu** | close friend | 55 | — | — | — | wedding; RSVP due Monday | M1 (logistics) |

---

## 3. Investor relationships  → relationships + `emails` + watches

| Fund | Partner (fictional) | Stage | State | Supports |
|---|---|---|---|---|
| **Sequoia** (lead) | Aanya Rao | term sheet out | **replied Tuesday; awaiting Mira's answer; expires Fri noon** | M2 (the flagged email), the sequoia watch |
| **Lightfield Capital** | Theo Vance | follow | soft-circled; in-person Friday in KL | the Friday flight / M6 cab |
| **Tasman Ventures** | Marisol Kee | follow | slow, leaning pass | inbox realism / pipeline |

**Fundraising narrative (for internal consistency):** Sequoia's term sheet landed last week, the partner replied Tuesday with the final terms, and it **expires Friday at noon**. Mira flies to KL Friday morning to lock the Lightfield follow in person — which is why she needs a **5:30am Changi cab** (M6). She must answer Sequoia **by EOD Thursday** (M2), then fly Friday.

---

## 4. Memories (episodic)  → memory backends (Supermemory episodic + Graphiti)

Each carries a **timestamp** — the timestamps are the proof of memory the demo leans on.

| # | Memory | When | Supports |
|---|---|---|---|
| MEM1 | Aniroodh texted: *"the pad see ew, mira. you have to."* → **Lotus Thai, Holland Village** | last Tuesday | M5 |
| MEM2 | Mira told Ishaan she'd **take him to Lotus Thai on Saturday** | last week | M5, M7 |
| MEM3 | The **Sequoia term-sheet thread** (summary + the final terms) | last week → Tue | M2 |
| MEM4 | Mom's birthday is **Saturday**; her favourites are **lilies** | stored months ago | M7 |
| MEM5 | This week's meals (Mon/Tue/Wed each **over** the ~1,900 goal) | this week | M4 |
| MEM6 | Mira usually books **Grab Standard** for airport runs | from past trips | M6 ("matches your usual") |

---

## 5. Beliefs (cognition)  → `backend/cognition` (form_belief writes these)

| # | Belief | Confidence | Evidence | Supports |
|---|---|---|---|---|
| B1 | **you call mom around noon on her birthday** | high (0.9) | past birthdays in chat + calendar | M7 ("you usually do") |
| B2 | **Grab Standard is your usual ride** | med-high (0.81) | prior airport bookings | M6 |
| B3 | **you avoid outreach when the story feels weak** | high (0.84) | delayed investor intros | background depth (M2 framing) |
| B4 | **you prefer Apple Music** | *written during M8* (weak prior before) | Spotify 2 uses vs Apple Music daily | M8 (the learning beat) |

---

## 6. Preferences  → facts

- mom → **lilies** · music → **Apple Music** · airport ride → **Grab Standard** · comms → blunt over polite, lowercase, "heads up" openers · card-note voice → *"love, mira."*

---

## 7. Commitments  → `open_loops` (some with `due_date` = admin tasks)

| # | Commitment | Due | Status | Supports |
|---|---|---|---|---|
| C1 | **answer Sequoia on the term sheet** | EOD Thursday | open | M2 |
| C2 | **send Priya the q3 deck** | today | open | M1, M9 |
| C3 | **reply to Pavithra on the room** | — | open | M1, G3 |
| C4 | **RSVP to Avu's wedding** | Mon 22 Apr | open (deadline-bearing task) | M1 |
| C5 | **call mom** (postponed 4 days) | — | open | M1; becomes the birthday-noon reminder (M7) |
| C6 | **gym** (skipped 2×, 3rd skip looming) | tonight 19:30 | open | M1 |

---

## 8. Watches  → `watches` table (active, adaptive cadence)

| # | type | subject_key | title | importance | since | Supports |
|---|---|---|---|---|---|---|
| W1 | reply | sequoia | **sequoia partner reply** | 90 (lifted by fundraising context) | Tuesday | M1, M2 |
| W2 | web | tokyo flights | **tokyo flights below ₹38k** | 55 | — | M1 |
| W3 | reply | pavithra | **pavithra response on the room** | 60 | Monday | M1 |
| W4 | reply | priya deck | **q3 deck feedback from priya** | 65 | yesterday | M1 |
| W5 | finance | aws bill | **AWS auto-pay (watch until cleared)** | 85 | — | M3 |

*(M6 creates a 6th watch live: a **delay watch** on the Friday cab. Not pre-seeded.)*

---

## 9. Calendar events  → `calendar_entries` (Google synced)

**Today — Thursday, 18 April**
| Time | Title | Note | Supports |
|---|---|---|---|
| 09:30 | call with **Ravi** | offer negotiation | M1 |
| 11:00 | **dentist** | Holland Village | M1 |
| 14:00 | **Priya 1:1** | you owe her the deck | M1, C2 |
| 16:00 | **Kartik** | rescheduled from yesterday | M1 |
| 19:30 | **gym** | 3rd skip this week | M1, C6 |
| 22:00 | **call mom** | postponed 4 days | M1, C5 |

**Coming up**
| When | Title | Note | Supports |
|---|---|---|---|
| Fri 19, 07:10 | **flight SIN → KUL (Changi T1)** | KL — in-person with Lightfield | M6 (the 5:30am cab) |
| Sat 20, all-day | **Mom's birthday** | lilies; noon call | M7 |
| *created in M5* | Sat 20, 20:00 **Lotus Thai · table for 2** | with Ishaan, via OpenTable | M5 → read by M7 |
| *created in M6* | Fri 19, 05:30 **Changi cab** | Grab Standard | M6 → shown on dashboard |

---

## 10. Emails  → `email_messages` (Gmail ingest; importance-scored)

The inbox needs **noise to rank against** — that's what makes the Sequoia flag impressive.

| # | From | Subject | Received | Importance signals | Outcome |
|---|---|---|---|---|---|
| E1 | **Aanya Rao** (Sequoia) | Re: Marble — term sheet (final) | **Tue** | important label + known sender + **goal_match** + **context_match** (fundraising) → **high** | **M2 flags it** |
| E2 | Priya Menon | q3 deck — your pass? | yesterday | open-loop match | the W4 watch |
| E3 | Pavithra | the room — a few questions | Mon | known sender | the W3 watch |
| E4 | Theo Vance (Lightfield) | Friday in KL — confirming 11am | Tue | known sender, fundraising context | confirms the Friday trip |
| E5 | AWS Billing | Your upcoming charges | Mon | low | feeds M3 (bill context) |
| E6 | a SaaS newsletter | "10 ways to…" | today | **low (ignored)** | proves selective ranking |
| E7 | a cold recruiter | "Senior role at…" | today | medium, not surfaced | proves selective ranking |

---

## 11. Subscriptions  → `transactions` history + subscription state

| # | Service | Cost | Renews | Usage this month | Supports |
|---|---|---|---|---|---|
| S1 | **Spotify** | ₹229/mo | **tomorrow (Fri 19)** | **2 plays** | **M8 (cancel)** |
| S2 | **Apple Music** | ₹99/mo | active | daily (primary) | M8 (the redundancy) |
| S3 | Notion | ₹800/mo | 24th | active | waste-detector realism |
| S4 | Figma | ₹1,200/mo | 1st | active | realism |
| S5 | iCloud+ 200GB | ₹219/mo | 9th | active | realism (duplicate-storage candidate) |
| S6 | Google One 200GB | ₹210/mo | 12th | unused | a *second* waste signal in reserve |

*(S1/S2 are the demo's cancel beat; S5/S6 are a duplicate-storage pair held in reserve for a longer cut.)*

---

## 12. Finance  → `finance_accounts` + `bills` + `transactions`

**Accounts**
| Account | Type | Balance | Supports |
|---|---|---|---|
| HDFC ••4471 | current | **₹43,000** | M3 (the shortfall) |
| HDFC ••9920 | savings | **₹1,20,000** | M3 (the fund source) |

**Bills**
| Biller | Amount | Auto-pay | Account | State | Supports |
|---|---|---|---|---|---|
| **AWS** | **₹47,200** | **Mon 22 Apr (in 4 days)** | current ••4471 | **₹4,200 short** | **M3** |
| Electric | ₹1,940 | Fri 19 Apr (tomorrow) | current ••4471 | covered | M1 logistics |

**Recent transactions (for the waste + spike detectors):** monthly Spotify ₹229 (×6), Apple Music ₹99 (×6), AWS, Notion/Figma/iCloud, plus everyday spend (~₹240/wk coffee creeping up — feeds the M4 "spend" tracker + a future spike).

**Demo-time write:** M3 moves **₹5,000** savings → current (`transfer`, L0) → current becomes **₹52,000** (the demo says "₹52,000" — i.e. ₹47k + buffer; the seed leaves headroom for that exact line).

---

## 13. Travel plans  → calendar + watches

- **Fri 19 Apr, 07:10** flight **SIN → KUL** from **Changi T1** — the KL investor trip → **the reason for the 5:30am cab (M6)**.
- **Tokyo trip** (personal, with Ishaan, tentatively May) — being **price-watched < ₹38k** (W2) → the M1 watch chip.

---

## 14. Lifetime metrics  → metrics store (the moat)

| Metric | Value | Supports |
|---|---|---|
| days with Donna | **247** | M9 |
| things caught | **1,847** | M9 |
| delivered on time | **94%** | M9 |

---

## 15. Coverage map — every moment is fed

| Moment | Pulls from |
|---|---|
| **M1** dashboard | W1–W5 · all calendar (today) · bills · C2–C6 · S1 · G1+focus (ordering) · holding count |
| **M2** sequoia email | E1 · MEM3 · W1 · G1 + fundraising context (goal_match + context_match) |
| **M3** missed payment | AWS bill · HDFC current/savings · W5 |
| **M4** tracker | G2 · MEM5 (Mon/Tue/Wed over goal) · today's breakfast+lunch |
| **M5** dynamic island | MEM1 + MEM2 · Aniroodh + Ishaan · OpenTable + Calendar → writes the Sat 20:00 booking |
| **M6** live cab | Fri 07:10 flight · B2 (Grab usual) · Grab consent (not connected) · Calendar → writes the 05:30 row + delay watch |
| **M7** cross-connection | Mom (birthday + lilies, MEM4) · the **Sat booking from M5** · B1 (noon call) · FNP → writes flowers + noon reminder |
| **M8** unsubscribe | S1 vs S2 · transaction history · → writes B4 (Apple Music pref) |
| **M9** day close + moat | the resolved cards of M2–M8 (Done) · W3, Ravi, W4 (Still Holding) · lifetime metrics |

---

## 16. Consistency checklist (the timeline holds)

- **Today = Thursday 18 Apr.** Term sheet **expires Fri 19 noon** → Mira answers Sequoia **EOD Thu** (M2), flies Fri 07:10 (cab 05:30, M6), term sheet still valid until Fri noon. ✓
- **AWS** auto-pays **Mon 22** = "in 4 days" from Thu. ✓ · **Electric** + **Spotify** renew **Fri 19** = "tomorrow." ✓ · **Avu RSVP** due **Mon 22**. ✓
- **Mom's birthday Sat 20** sits *after* the **Sat 20:00 Lotus Thai** booking made in M5 — so M7 can truthfully braid the birthday with the just-booked Saturday plan. ✓
- **Fundraising context** (G1 + the focus window) is *why* the Sequoia email outranks the newsletter/recruiter (M2) and *why* the dashboard leads investor-first (M1). ✓
- Every **Done** line in M9 corresponds to a card the demo actually resolved earlier; every **Still Holding** line is a watch/loop left deliberately open (Pavithra, Ravi, Priya's final deck). ✓

**One person. One week. Every number traceable.** Load this seed and the demo is true.
