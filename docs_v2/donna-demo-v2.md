# Donna Demo — V2

## The reset

**Product only. No environments. No humans.** Every frame is phone screen UI. Time-of-day overlays establish the day arc — *the product itself tells the story*.

The viewer’s reaction we’re optimizing for:

> *“oh my god she caught that. how did she catch that.”*

Not “cool app.” That feeling — the one where someone realizes the product just saved them from a fuckup they didn’t see coming.

-----

## Format

- **Runtime:** 75-85 seconds
- **Structure:** 9 product moments. Most are 6-10 seconds. One anchor moment (Live tab) is 15-18s.
- **Footage:** 100% phone screen UI. Either full-bleed or in a clean phone mockup. No real environments. No humans.
- **Time-of-day overlays:** small italic serif timestamps in the corner (8:42am, 1:42pm, etc.) — these establish the day arc using *only* product UI.
- **No narrator.** Subtle piano under everything.
- **Hard cuts between moments.** Each moment self-contained.

-----

## The 9 moments

Each moment is a real thing a real busy person desperately needs. No abstract feature demos. Every line donna says is hyper-specific — numbers, names, exact times. That specificity is the proof of memory.

-----

### MOMENT 1 — 7:30am · The dashboard reveal [5s]

**Screen:** donna app opens. Dashboard tab loads. Camera does a slow vertical scroll revealing the dashboard density.

```
TODAY · thursday, april 18

watching · 4
  ○ tokyo flights · below ₹38k
  ○ pavithra response on the room
  ○ sequoia partner reply · waiting since tuesday
  ○ q3 deck feedback from priya

scheduled · 6
  □ 9:30am  call with ravi (offer negotiation)
  □ 11:00am dentist · holland village
  □ 02:00pm priya 1:1 · you owe her the deck
  □ 04:00pm kartik (rescheduled from yesterday)
  □ 07:30pm gym · 3rd skip this week
  □ 10:00pm call mom (you've been postponing 4 days)

logistics · 5
  ◇ electric bill · auto-pay tomorrow · balance ok
  ◇ aws bill · auto-pay in 4 days · balance ₹4,200 short
  ◇ mom's birthday · saturday
  ◇ avu's wedding rsvp · deadline monday
  ◇ spotify renews tomorrow · ₹229 · used 2x this month

she's holding 23 things for you
```

**Why this opens:** In 5 seconds, the viewer sees that donna isn’t a chatbot. She’s tracking a real life — with real shit at stake (an offer to negotiate, a partner waiting for reply, a gym goal being missed, a mom call being postponed). The viewer reads three lines and thinks *“that’s me.”*

-----

### MOMENT 2 — 8:42am · The flagged email [7s] 🔥

**Screen:** WhatsApp notification slides onto the lock screen.

> **donna** · 8:42am
> heads up. sequoia partner replied to your thread.
> they want your answer by EOD. the term sheet expires tomorrow at noon.
> *tap to see the email + draft a reply.*

Tap. Opens donna in WhatsApp. The chat shows:

- A compressed summary of the email (3 lines)
- Three reply buttons:
  
  ```
  [ accept the terms ]
  [ counter on valuation ]
  [ ask for 48 more hours ]
  ```

**Why this hits:** Every founder, every operator has had this exact moment of opening their inbox at noon and realizing they missed something critical. Donna doesn’t just notify — she summarizes the email and pre-drafts the response options. The viewer thinks *“FUCK, this would have saved me.”*

-----

### MOMENT 3 — 10:15am · The saved missed payment [7s] 🔥

**Screen:** WhatsApp ping.

> **donna**
> your aws bill auto-debits in 4 days. ₹47,200.
> your hdfc current account is ₹4,200 short.
> transfer ₹5,000 from savings now?
> 
> ```
> [ yes, transfer ]
> [ pause auto-pay ]
> [ remind me tomorrow ]
> ```

User taps “yes, transfer.” Donna:

> done. ₹5,000 moved. balance now ₹52,000.
> i’ll keep watching the bill until it clears.

**Why this hits:** Nobody monitors their bank balance against upcoming auto-debits. Donna does. This single moment shows: she has access to email/banking, she does math on the user’s behalf, she takes action with consent, she keeps watching. The viewer thinks *“this would have saved me from a bounce fee.”*

-----

### MOMENT 4 — 1:42pm · The tracker check-in [8s] 🔥

**Screen:** WhatsApp ping.

> **donna**
> what did you have for lunch? updating your tracker.

User taps reply, types: *“biryani and sweet lassi”*

Donna replies in real time:

> logged. ~1,840 cal so far. ~600 left for dinner.
> heads up — this is day 3 you’ve crossed your monday goal.
> want me to suggest a lighter dinner around 7?

**Why this hits:** This is the “she’s actually tracking shit” moment. Most fitness apps need you to remember to open them and log. Donna asks. The “day 3 of being over” line is brutal and useful — it’s the kind of accountability you’d pay $200/mo for a coach to deliver. Specific calorie numbers prove she’s actually doing the math.

-----

### MOMENT 5 — 2:30pm · Dynamic Island while scrolling Instagram [12s]

**Screen:** Instagram feed visible, scrolling slowly. User long-presses the dynamic island. Dynamic island animates open with a thin waveform.

Voice (text shown on screen for the demo):

> *“donna, what was the restaurant aniroodh kept telling me about?”*

Dynamic island animates a search shimmer, then expands to a card *while Instagram is still scrolling underneath*:

```
LOTUS THAI · holland village
aniroodh texted you last tuesday:
"the pad see ew, mira. you have to."

you said you'd take ishaan there saturday.
```

Donna’s voice (text shown):

> *want me to book a table for two, saturday 8pm?*

User: *“yeah.”*

Dynamic island shows booking animation, then collapses to:

```
booked · 8pm saturday · 2 people · OpenTable
```

Instagram is still scrolling the whole time.

**Why this hits:** No other AI does this. The viewer sees:

- Memory of a casual mention from days ago
- Memory of a side conversation about Saturday plans
- Real-time agentic execution
- Never leaving the app they were already in

The viewer thinks *“i want this on my phone tomorrow.”*

-----

### MOMENT 6 — 4:00pm · The Live tab agentic centerpiece [16s] ⭐

**Screen:** Open donna app. Tap **Live tab.** Different feel — conversational, active.

User types (or speaks):

> *“book me a cab to changi t1 at 5:30am tomorrow.”*

Donna response in Live tab:

> need access to your grab to book. one tap to allow?

**Consent card slides up from bottom:**

```
┌─────────────────────────────────┐
│  CONNECT GRAB                    │
│                                  │
│  donna will be able to:          │
│  · book rides on your behalf     │
│  · pay via your saved card       │
│                                  │
│  [ allow ]    [ not now ]        │
└─────────────────────────────────┘
```

Tap **allow.** OAuth flow flashes briefly. Card slides away.

Live tab now shows **3 interactive ride cards:**

```
┌─────────────────────────────────┐
│  GRAB PREMIUM       25 min      │
│  $42 · arrives 5:15am            │
│  [ book ]                        │
├─────────────────────────────────┤
│  GRAB STANDARD      28 min  ✓   │
│  $28 · arrives 5:12am            │
│  recommended · matches your usual│
│  [ book ]                        │
├─────────────────────────────────┤
│  GRAB SHARE         35 min      │
│  $18 · arrives 5:08am            │
│  [ book ]                        │
└─────────────────────────────────┘
```

User taps **book** on Standard. Confirmation in Live:

> booked. driver assigned 5:00am.
> reminder set for 5:15am.
> i’ll watch for delays.

Quick cut: dashboard updates in real time. New row in **scheduled**: *5:15am · changi cab*.

**Why this hits:** This is the demo’s centerpiece. In 16 seconds the viewer sees:

- Live tab (the action surface)
- Real-time conversation
- Just-in-time consent UI
- Just-in-time interactive cards
- Agentic execution
- Memory (“matches your usual”)
- Cross-surface sync (dashboard updates instantly)

This is the segment that closes investors. *“Holy shit, the whole product works.”*

-----

### MOMENT 7 — 6:15pm · The cross-connection [9s] 🔥

**Screen:** WhatsApp ping.

> **donna**
> mom’s birthday is saturday. you have lotus thai at 8pm with ishaan.
> her favorites: lilies. fnp delivers by 10am.
> send ₹1,899 bouquet in the morning?
> 
> ```
> [ yes, send lilies ]
> [ different flowers ]
> [ i'll handle it ]
> ```

User taps “yes, send lilies.” Donna:

> done. ₹1,899. delivery saturday 9-10am.
> card note: “happy birthday ma. love, mira.”
> adding a reminder to call her at noon — you usually do.

**Why this hits:** Three memories collide:

- Mom’s birthday (calendar)
- The Saturday plans (from moment 5)
- Mom’s preferences (lilies — from somewhere donna stored months ago)
- The pattern that mira always calls mom around noon on birthdays

The viewer reads “you usually do” and feels the depth of donna’s memory. *“How does she know what i usually do?”*

-----

### MOMENT 8 — 7:48pm · The unsubscribe moment [6s] 🔥

**Screen:** WhatsApp ping.

> **donna**
> spotify renews tomorrow. ₹229.
> you used it twice this month. apple music handles the rest.
> cancel?
> 
> ```
> [ cancel ]
> [ keep it ]
> [ remind me next month ]
> ```

Tap cancel. Donna:

> cancelled. ₹229/mo saved.
> i’ll remember you preferred apple music.

**Why this hits:** Nobody audits their own subscriptions. Donna does. Specific number (₹229), specific usage detail (twice this month), specific preference learned (apple music). The viewer thinks *“how many subscriptions am i paying for and not using?”*

-----

### MOMENT 9 — 11:02pm · The day closes + the moat reveal [10s]

**Screen:** Open donna app. Dashboard tab. Scroll to the bottom — “today · closed” section.

```
TODAY · DONE  (8)
  ✓ sequoia reply sent · 9:14am
  ✓ aws balance topped up · 10:18am
  ✓ lunch logged · biryani + lassi
  ✓ lotus thai booked · saturday 8pm
  ✓ changi cab booked · 5:30am tomorrow
  ✓ mom's flowers ordered · lilies
  ✓ spotify cancelled · ₹229/mo saved
  ✓ priya q3 deck draft sent

STILL HOLDING  (3)
  ○ pavithra room response
  ○ ravi offer negotiation
  ○ q3 deck final from priya
```

Then the screen scrolls to reveal the bottom:

```
247 DAYS WITH DONNA
1,847 things caught
94% delivered on time
```

Final beat: italic serif rust **donna** wordmark, *“she texts first.”*

**Why this closes:** The viewer just watched 8 specific wins in a single day. Then they see — there have been 1,847 more. The moat made tangible. *“The longer she’s with me, the more she knows. I can’t switch away from this.”*

-----

## Why this is 10/10 vs the 4/10 version

|4/10 version                                     |10/10 version                                            |
|-------------------------------------------------|---------------------------------------------------------|
|Real environments (MRT, café)                    |100% phone screens                                       |
|Live action protagonist (Mira walks, talks, eats)|No human ever shown                                      |
|Soft narrative flow                              |Hard rapid-fire wins                                     |
|“She helps you through your day”                 |“Holy shit, she caught the sequoia email”                |
|Generic features                                 |9 specific, life-saving moments                          |
|5 segments × 15s                                 |9 moments × ~8s + one anchor at 16s                      |
|Gentle voiceover-style text overlays             |Time-of-day stamps as the only overlay                   |
|“She remembers” (abstract)                       |“₹229 spotify. used twice this month. cancel?” (concrete)|

The difference: every line donna says has *numbers, names, exact times.* That specificity is what proves the memory. The viewer doesn’t have to take our word for it — the proof is in every line of UI text.

-----

## The 9 moments × features matrix

|Feature         |M1 |M2 |M3 |M4 |M5 |M6 |M7 |M8 |M9 |
|----------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
|Proactive       |   |●  |●  |●  |   |   |●  |●  |   |
|Dynamic Island  |   |   |   |   |●  |   |   |   |   |
|Relationships   |●  |●  |   |   |●  |   |●  |   |●  |
|Memory          |●  |●  |●  |●  |●  |●  |●  |●  |●  |
|Cross-connection|●  |●  |●  |●  |●  |   |●  |●  |   |
|Dashboard       |●  |   |   |   |   |   |   |   |●  |
|Live tab        |   |   |   |   |   |●  |   |   |   |
|Real-time convo |   |   |●  |●  |●  |●  |●  |●  |   |
|JIT UI          |   |●  |●  |   |●  |●  |●  |●  |   |
|Agentic         |   |●  |●  |   |●  |●  |●  |●  |●  |
|WhatsApp surface|   |●  |●  |●  |   |   |●  |●  |   |
|Logistics       |●  |   |●  |●  |   |●  |●  |   |●  |
|Consent cards   |   |   |   |   |   |●  |   |   |   |

Every feature appears in 3+ moments. Memory is in all 9 — because memory IS the product.

-----

## Production notes — V2

### Visual treatment

- Phone screen prominent, full-bleed or framed in a clean iPhone mockup
- Background of the video itself: paper-toned (#FBF7F5) to match the deck design system
- Time-of-day overlay: italic serif rust, top-right corner, fades in for ~1s at the start of each moment
- Transitions between moments: hard cut + subtle paper-fold animation
- The dashboard moments (1 and 9) get smooth vertical scroll camera moves

### Audio

- Single piano + light strings underneath. NOT corporate uplift. NOT epic build.
- WhatsApp notification chimes ARE the percussion — let them land
- Dynamic island animation sound for moment 5
- Optional: donna’s voice (warm, low, brand-voice lowercase) only on moment 5 — and only because the dynamic island invites it

### Text on screen (donna’s WhatsApp / UI text)

This is where the demo lives or dies. Every line must:

- Be lowercase
- Have specific numbers / names / times
- Sound like a friend, not a system
- Use “heads up” as the proactive opener (it’s perfect)
- Never use em dashes
- Never apologize, never overpromise

### Pace

- Average ~8s per moment
- Moment 6 (Live tab) gets ~16s — it must breathe
- Moment 1 (dashboard) gets ~5s — let the eye land
- Hard cuts between every moment
- Total: 75-85s

-----

## What makes the viewer feel “I NEED this”

The math:

```
moment 2  — saved from missing the sequoia email
moment 3  — saved from a bounced auto-payment  
moment 4  — caught at being lazy with my health
moment 5  — remembered a casual restaurant mention from days ago
moment 6  — booked a 5am cab in 8 seconds
moment 7  — remembered my mom's flower preference, saved me from forgetting
moment 8  — saved me ₹229/month i wasn't using
moment 9  — i can see the 1,847-thing history. switching costs me everything.
```

That’s 8 concrete wins in 75 seconds. The viewer leaves with their phone in their hand thinking *“how do i get this.”*

-----

## What I cut and why

- **Anniversary card draft moment** — too similar to mom’s flowers (moment 7). Pick one cross-connection beat, not two.
- **Screenshot-to-memory moment** — visually weak as product-only. Hard to convey “saved screenshot.”
- **Calendar conflict resolution** — Live tab moment (6) implicitly demonstrates dashboard sync, so we don’t need a separate moment for calendar.
- **The morning brief** — collapsed into the dashboard reveal (moment 1). One product surface, not two.
- **“What was i supposed to do today” voice query** — implicit in the dashboard. Don’t double-show.

Every cut moment had merit. The discipline: 9 moments is already dense. Don’t bloat.

-----

## What I’d shoot first

If you only have time for ONE moment to test the visual approach:

**Moment 4: The tracker check-in.**

Reasons:

1. It’s the most unexpectedly viral moment (“she asked what i ate??”)
1. Easiest to prototype (pure WhatsApp UI + text)
1. Can be cut as a 8-second teaser on its own
1. Hits the *“holy shit she’s actually tracking shit”* reaction hardest
1. Tests whether the WhatsApp surface visual approach works before you build the Live tab footage

If that single moment lands → build the rest.

-----

## End card

Paper. Italic serif rust **donna**. Below: *“she texts first.”*

Hold 2 seconds. Cut.