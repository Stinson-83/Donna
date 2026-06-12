# Donna — Demo Build Priority (P0 / P1 / P2)

For each moment in [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md), every component is classified to **minimize engineering while maximizing demo credibility**.

| | Meaning | Build cost |
|---|---|---|
| **P0** | **Must be real functionality** — realness is the *proof* (the "how did she catch that"); faking it would collapse the thesis if probed | usually **already built** (see ✅) → ~0 new eng |
| **P1** | **Can be mocked** — a UI/rail that looks real but the third-party side is stubbed (these are *already* sandboxed in the build) | small (a confirmation string) |
| **P2** | **Can be pre-generated** — static content seeded ahead and shown on cue | already done via `DEMO_SEED_DATA.json` |

> **The headline:** the P0 surface *is* the engine this repo already ships. The only genuinely net-new build for the demo is the **Dynamic Island overlay (M5)** + a thin **demo harness** to fire triggers on cue. Everything else is seed + script + existing code.

---

## Per-moment classification

### M1 — Dashboard reveal
| Component | Pri | Built? | Why |
|---|---|---|---|
| Dashboard data (watches/calendar/bills/tasks/holding=23) | **P2** | ✅ seed | Static morning state — comes straight from `DEMO_SEED_DATA.json` |
| Watch-bar **ordering** (investor-first via goal + context) | **P0** | ✅ `rank_attention` | "She knows what matters *today*" — the one beat that proves it's not a list. Real at ~0 cost |
| The app render (Dashboard tab, sections) | **P0** | ✅ frontend | Real UI already exists |

### M2 — Flagged email
| Component | Pri | Built? | Why |
|---|---|---|---|
| **Why it surfaced** (importance scorer beats the newsletter/recruiter via label+sender+goal+context) | **P0** | ✅ `email_importance` | The soul of the moment — "she caught the *one* that mattered." Faking = the thesis is fake |
| The card render + tap → reopen → draft | **P0** | ✅ cards + gate | The decision-surface path is the product |
| Email body / 3-line summary / 3 reply options | **P2** | ✅ seed | Same email every run — pre-generate the summary + drafts |
| WhatsApp push chrome | **P1** | — | Mock the lock-screen banner (FCM is real but unnecessary on stage) |
| Actually sending the reply | **P1** | (`send_email` real) | Don't email a real partner live — mock "sent" or send to a test inbox |

### M3 — Saved missed payment
| Component | Pri | Built? | Why |
|---|---|---|---|
| Shortfall **detection** (bill vs balance math, in 4 days) | **P0** | ✅ `detect_low_balance_vs_bill` | "She does math on my money against the future" — the proof |
| Approval card (L0) + tap-to-execute | **P0** | ✅ cards + gate | The consent model, made visible |
| The actual **transfer** | **P1** | (sandboxed ledger) | No real money moves — mock the confirmation. *The build already stubs this* |
| New balance "₹52,000" + "i'll keep watching" | **P2 / P0** | ✅ | Balance is pre-set (P2); the watch persisting is real + trivial |

### M4 — Tracker check-in
| Component | Pri | Built? | Why |
|---|---|---|---|
| The proactive **ask** ("what did you have for lunch") | **P0** | ✅ `maybe_checkin_meal` | "She initiates" — the unexpected-virality beat |
| Logging + the **"day 3 over goal"** streak (math over seeded meals) | **P0** | ✅ `log_observation` + seed | The accountability line is computed from real seeded observations |
| Calorie estimate for "biryani and sweet lassi" | **P2** | — | For a scripted input, pre-set the number (the only "AI guess" — bake it) |

### M5 — Dynamic Island recall ⭐ (memory thesis)
| Component | Pri | Built? | Why |
|---|---|---|---|
| The **recall** (Aniroodh's text + the Saturday plan, days old) | **P0** | ✅ `recall_about` | **The single most important real beat.** Memory of a throwaway mention IS the product. Never fake this |
| The **Dynamic Island UI + ambient voice** | **P1** | ❌ new | The *only* meaningful net-new build — a scripted island overlay + TTS/pre-recorded voice. The surface is mocked; the recall behind it is real |
| The restaurant booking | **P1** | (sandboxed → real calendar event) | OpenTable mocked; the **calendar event is real** (cheap) and is what M7 reads |

### M6 — Live tab cab ⭐ (the centerpiece — "the whole product works")
| Component | Pri | Built? | Why |
|---|---|---|---|
| Consent card (Grab not connected) | **P0** | ✅ `consent_integration` card | JIT consent is a core differentiator — render it real |
| Grab **OAuth** round-trip | **P1** | — | Mock the flash (or use a real Composio sandbox app). Don't build a live Grab integration for a demo |
| 3 ride cards + **"recommended · matches your usual"** | **P1 / P0** | (options mocked, memory real) | The ride options are pre-generated (no real Grab API); the *"matches your usual"* tag is real memory (belief B2) applied to them |
| `book_ride` execution | **P1** | (sandboxed → calendar reminder + delay watch) | No real dispatch — mock confirmation |
| **Cross-surface sync** (dashboard gains the 5:15am row instantly) | **P0** | ✅ cards/calendar → `/today` | The "holy shit it all connects" anchor. **Keep this real** — it's cheap and it's the closer |

### M7 — Cross-connection (mom's flowers) ⭐ (the moat beat)
| Component | Pri | Built? | Why |
|---|---|---|---|
| The **braid** (birthday + the Saturday booking from M5 + lilies + "you usually call at noon") | **P0** | ✅ `find_connections` + birthday check + belief B1 | **"How does she know what i usually do?"** — the moat made tangible. Faking this kills the depth narrative |
| The flowers order | **P1** | (sandboxed FNP) | Mock the confirmation |
| Noon-call reminder | **P0** | ✅ `schedule` | Real + cheap |

### M8 — Unsubscribe
| Component | Pri | Built? | Why |
|---|---|---|---|
| Waste **detection** (Spotify 2-use vs Apple Music duplicate) | **P0** | ✅ `detect_waste` over seeded txns | "She audits what i never audit" — the proof |
| The cancel | **P1** | (sandboxed) | No real Spotify-cancel API — mock confirmation |
| **Learning** (`form_belief` "prefers Apple Music") | **P0** | ✅ `form_belief` | "She gets smarter from my choice" — real + cheap |

### M9 — Day close + the moat
| Component | Pri | Built? | Why |
|---|---|---|---|
| **Done** list (the resolved cards from M2-M8) | **P0** | ✅ `/cards`/`/today` projection | If the demo ran live, these are real resolved rows — the chain made visible. (P2 if staged) |
| **Lifetime metrics** (247 days · 1,847 caught · 94%) | **P2** | seed | Inherently pre-generated — you can't accrue 247 real days. The moat number is seeded |

---

## The rollup

### P0 — the minimum real surface (and it's already built)
The non-negotiable real beats, all shipping in this repo (**~0 new engineering**):
1. **Selective importance ranking** — M1 ordering, M2 catching the right email (`rank_attention`, `email_importance` + goal/context weighting).
2. **The decision-card path** — render + L0/L1/L2 gate + tap-resolution (M2, M3, M6, M7, M8).
3. **Recall** of a days-old casual mention (M5, `recall_about`).
4. **Cross-connection braid** (M7, `find_connections` + belief).
5. **Waste detection** (M8, `detect_waste`) and the **financial shortfall math** (M3).
6. **Cross-surface sync** — a tap writes a row, the dashboard reflects it instantly (M6).
7. **Learning** (M8 `form_belief`), **scheduling** (M7), and the **proactive initiation** + streak math (M4).

> These are P0 *because they are the thesis* — memory, noticing, connecting, and acting. They're also exactly what's already built, so "make it real" costs nothing extra.

### P1 — mock these (already sandboxed; they're rails, not the product)
Every **third-party execution rail**: money transfer, OpenTable booking, Grab OAuth + dispatch, FNP flowers, Spotify cancel, live ride/flight delay feeds. Plus the **WhatsApp/FCM push chrome**. Investors *expect* these to be sandboxed in a demo; faking the confirmation costs nothing and the build already stubs them (see `README_TECHNICAL.md` §7). The one **non-trivial P1** is the **Dynamic Island overlay (M5)**.

### P2 — pre-generate / seed
Everything static: the **whole dataset** (`DEMO_SEED_DATA.json`), email bodies + summaries + reply drafts, the ride options, the scripted-meal calorie estimate, and the **lifetime moat metrics**. Already produced.

---

## What to actually build for the demo (the entire eng budget)

1. **A thin demo harness** — fires each moment's *real* trigger on cue (`proactive_email_trigger`, `maybe_surface_finance`, `maybe_surface_waste`, `maybe_surface_birthday`, `maybe_checkin_meal`) so real cards render through the real loop with the time-stamp overlays. *(small)*
2. **A seed loader** — writes `DEMO_SEED_DATA.json` into the real tables. *(small)*
3. **The Dynamic Island overlay (M5)** — the only meaningful net-new UI; can even be a pre-rendered motion clip if time is short. *(medium, optional-to-fake)*
4. **Confirmation strings for the sandboxed rails** — ensure each stubbed executor's "done" text matches the script. *(trivial)*

Everything else is the **existing engine + the seed**.

## Risk note — what you must NOT fake
The beats where a probing investor ("ask it something else") would expose a fake — and which are therefore P0, *and* already real, so just use them: **M5 recall · M7 cross-connection · M2 selective ranking · M6 cross-surface sync.** These four *are* the differentiation. Faking the **rails** (M3/M5/M6/M7/M8 executions) is safe and expected; faking the **intelligence** is the one thing that loses the room.
