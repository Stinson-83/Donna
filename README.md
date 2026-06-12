# Donna — your personal chief of staff

Donna is not a chatbot and not an "AI assistant." She is a **personal chief of staff**: she watches your life, remembers what matters, notices problems before you do, prepares things before you ask, and texts you first when something deserves your attention. The goal is one feeling:

> **You spend less mental energy managing your life, because Donna is already on top of it.**

She lives across **two places that share one memory**: **WhatsApp** (text her like a person) and the **Donna app** (open it to *see what she believes about your life* — not a dashboard of buttons, but her understanding laid out). Anything you tell her on one shows up on the other. It's one mind, two doors.

This README explains, in plain language, **what she can do, how all the pieces fit together, and how information flows** — both when she's replying to you and when she reaches out first. A companion document, [`README_TECHNICAL.md`](./README_TECHNICAL.md), explains the same system for engineers.

---

## 1. What Donna does for you

Think of the best executive assistant you can imagine. Donna is built to do that job across every part of your life:

| Area | What she does | Example |
|---|---|---|
| **Communication** | Watches your email, spots what's important, drafts replies | "Sequoia replied about the term sheet — they want an answer today. Want me to draft it?" |
| **Schedule** | Reads your calendar, catches clashes and overload | "Your 3pm demo overlaps your 1:1 with Raghav by 30 minutes." |
| **Money** | Tracks bills and spending, flags risk and waste | "Your AWS bill auto-debits tomorrow and you're ₹4,200 short." · "You're paying for Spotify twice." |
| **Travel** | Tracks flights; understands the knock-on effects | "SQ516 is delayed to 9:40pm — your airport pickup and the dinner after are both affected." |
| **People** | Remembers who matters, birthdays, preferences | "Mom's birthday is Saturday. You usually call. She likes lilies." |
| **To-dos & errands** | Tracks admin tasks with deadlines, reminds before they slip | "Renew your passport — it's due in two weeks." |
| **Goals** | Knows what you're working toward, and weighs everything against it | An investor email matters *more* because you're fundraising. |
| **Preparation** | Gets you ready before something happens | The night before a meeting: who it's with, the last thread, the open question you didn't answer. |

She doesn't just *find problems* — she brings you a **decision**, not a notification. Not "flight delayed," but "flight delayed, here's what it breaks, here's the one fix, tap to do it."

---

## 2. The two ways she works

Everything Donna does is one of two flows. Understanding these two is understanding the whole product.

### Flow A — Reactive: *you talk, she answers*

This is the obvious one. You message her (on WhatsApp or in the app) and she replies — but the reply is the *end* of real work, not a canned answer.

```
You send a message
        │
        ▼
She figures out what you actually mean
        │
        ▼
She gathers what she needs   ← looks up your memory, calendar, the email thread, etc.
        │
        ▼
She decides what matters and what to do
        │
        ▼
She replies in her voice  — and may quietly do things too
   (set a reminder, draft an email, start watching something, update what she knows about you)
```

The reply is short. The work behind it is not. One message in, one thoughtful answer out — plus any quiet side-effects (a reminder set, a fact remembered, a watch created).

### Flow B — Proactive: *she notices, she texts first*

This is what makes her a chief of staff instead of a search box. **Donna does not wait to be asked.** In the background, on a steady heartbeat, she checks your life for things that matter:

```
A heartbeat ticks (continuously, on its own)
        │
        ▼
She runs her checks  — is a bill about to bounce? a deadline near? a flight delayed?
                       did the investor finally reply? is your calendar a mess today?
        │
        ▼
Something deserves attention
        │
        ▼
She works out *why it matters and what to do about it*
        │
        ▼
She reaches out  — but only on ONE surface, and only if it's actually worth interrupting you
```

Two important rules keep this from becoming spam:

- **One buzz, never two.** A proactive message reaches you on a single surface (the app *or* WhatsApp, by your preference) — never both. You can set which one you prefer.
- **Interruptions stay rare.** Each thing she finds has a priority. Truly urgent things (a bill about to bounce, a cancelled flight) buzz your phone. Lower-priority things (a duplicate subscription) **just appear quietly** on your dashboard — no buzz. She protects your attention on purpose.

---

## 3. How she stays on top of everything

A few systems work together to make the proactive magic feel inevitable:

- **Memory.** Everything you tell her becomes durable knowledge — not a chat log, but *what she's learned*: facts, patterns, preferences, and **beliefs about you** (each with a confidence and the evidence behind it). This is the core of the product. It compounds: she gets more useful every day.
- **Watches.** Anything unresolved can become a *watch* — "tell me when the investor replies," "track this flight," "keep an eye on Tokyo flight prices." She checks them on her own, more often as a deadline nears, and tells you the moment something changes. You never have to remember to check.
- **The Morning Brief.** Once a day, in your morning, she pulls together the few things that actually matter — "good morning, three things matter today…" — instead of pinging you about each separately.
- **The Watch Bar.** A live strip at the top of the app showing *what matters most right now*, reordering itself as priorities shift — like a Dynamic Island for your life.
- **Cross-connection.** The "how did she catch that?" trick. When one thing changes (a flight moves), she walks the connected things (the pickup tied to it, the dinner after) and tells you the *consequence*, not just the event.
- **Learning.** Every time you act on or dismiss one of her cards, she learns. Dismiss enough "heads-up" cards and she gets more selective. She gets sharper from how you respond.

---

## 4. When she acts *for* you

Donna can do things, not just suggest them — but with guardrails that match the risk. Every action falls into one of three levels:

| Level | Rule | What happens | Examples |
|---|---|---|---|
| 🟢 **Auto** | Low-risk, reversible, easy to explain | She does it, then tells you | Add a calendar event, set a reminder, log a meal, start a watch, draft (not send) a reply |
| 🟡 **Confirm** | Acts toward someone else as you, or not easily undone | She prepares it; **your tap** does it | Send an email as you, make a reservation, cancel a non-critical subscription |
| 🔴 **Approve** | Money, legal, or irreversible | **Always** an explicit approval card, every time | Transfer money, pay a bill, book a paid trip, cancel something critical, delete data |

She can never "talk her way" past these. Moving money is *always* a red-level approval — she shows you a filled-in card and waits for your tap. Nothing happens until you say so.

---

## 5. Where you see her

**WhatsApp** — just text her. Replies, heads-ups, and approval prompts all come through as messages.

**The Donna app** has three tabs plus a drawer:

- **Dashboard** — what needs you right now: the "what matters now" strip, the cards waiting on you, what she's watching, your day.
- **Live** — the conversation with her.
- **History** — the full transcript across *both* WhatsApp and the app, in order.
- **The Library drawer** (the menu) — "everything she's holding for you": your People, Documents, Trackers (watches), To-dos, Connected accounts, and Settings (including which surface she reaches you on).

> There's also a **Memory** view (what she believes about you, as a constellation of evidence and beliefs) and a **Beliefs** view — both are **parked** right now (the data is being collected in the background, the screens just aren't shown yet).

---

## 6. What's fully working vs. what's a placeholder

Honesty matters here. The **thinking engine is real**; some of the **real-world "rails"** (actually moving money, actually booking a cab) are deliberately stubbed because they need live third-party accounts — but they're built to swap in.

### ✅ Real and working
- **Her brain** — the single reasoning loop that interprets, decides, and acts. (Needs an AI key to run live.)
- **Memory** — what she learns and believes about you, across both surfaces.
- **Watches** — standing things she monitors, checked on an adaptive schedule.
- **All the "noticing" engines** — bill-about-to-bounce, subscription waste, schedule clashes, deadline reminders, flight changes, the morning brief, the watch bar, cross-connection, goal-weighting, learning-from-feedback. These are real logic, fully tested.
- **The decision cards + the approval levels** (auto / confirm / approve).
- **Reading your email and calendar** (via a connected Google account).
- **Web answers** (weather, prices, current events) when she needs the real world.
- **Drafting and sending an email as you**, and **creating real calendar events**.

### 🟡 Built, but the real-world rail is stubbed (pluggable)
These work as a *real engine* but don't touch a live third-party service yet — they need an account to be connected:
- **Moving money** (a transfer) — recorded safely, but no real bank transfer happens.
- **Booking a restaurant or a cab** — these create a **real calendar event/reminder** for you, but don't actually reserve the table or hail the car (no OpenTable/Grab account connected).
- **Ordering flowers** — stubbed (no florist connected).
- **Live flight data** — the flight-tracking engine is real, but it needs a flight-data provider plugged in to get live status.

### 🎬 Demo / placeholder (frontend only)
- **The app ships in "demo mode" by default** so it runs with no backend — every screen shows realistic sample data for one example person (a founder named *aarav* building *poke*, raising from *Sequoia*, moving to *Waterloo*). Flip one setting to point it at the real backend and the screens fill with *your* data instead.
- **The Memory constellation and the "areas" index** are still sample visuals (the real data path exists but isn't wired to them yet).
- **The Memory and Beliefs tabs** are parked (built, not shown).

---

## 7. The one-line summary

You live your life. Donna watches the parts that are easy to drop — email, money, calendar, travel, people, deadlines — learns how *you* operate, connects the dots across all of them, and reaches out at the right moment with a decision you can act on in one tap. A static assistant remembers. Donna **understands**.

For how all of this is built, see [`README_TECHNICAL.md`](./README_TECHNICAL.md).
