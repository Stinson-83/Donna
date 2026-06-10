# Donna — YC Pitch & Demo Brief

Everything you need to talk through the product on camera: the story, how it
works, the full stack, what's real vs staged, the demo script, and what's next.
Read top to bottom once; keep the **Demo script** and **Q&A** sections open while
recording.

---

## 1. The one-liner

> **Donna is a belief-native AI companion. She doesn't just remember what you
> say — she forms opinions about your life, shows her reasoning, and changes her
> mind as evidence accumulates.**

She lives across two surfaces that share one memory: **WhatsApp** (where you
already talk) and the **Donna app** (where you go to *see what she believes about
your life*).

The line that should land with a YC partner:
> *"This isn't another chatbot. It's a persistent thinking partner that's
> building a model of a person."*

## 2. The insight / why now

- Every AI assistant today is **stateless and opinion-less**. ChatGPT forgets
  you between sessions; even "memory" features are a flat list of facts. None of
  them form a *view* of you or take a position.
- Two things just became true: (1) LLMs are finally good enough to reason over
  long-lived personal context, and (2) the memory/graph infrastructure to store
  it cheaply matured (vector stores, graph DBs, episodic memory).
- The wedge: **WhatsApp**. No app to download, no behavior change — you text her
  like a friend. The app is the second surface you open to *understand yourself*,
  not to send another message.
- The product thesis, in four words: **conversation is the interface;
  understanding is the product.**

## 3. What Donna is — the surfaces

The app has **four screens**, deliberately ordered so chat is *not* the home.
You open the app to understand your life, not to type.

| Screen | Question it answers | What's on it |
|---|---|---|
| **Plan** (home) | "what matters today, and *why*?" | a daily thesis, the one event that matters + the causal "because" chain, open loops, the shape of the day, a nudge tied to a belief |
| **Chat** | she synthesizes, she doesn't retrieve | streaming replies, live "what she's doing" status, memory-aware, calm (Messages + Journal + Claude, not a chatbot) |
| **Beliefs** (the moat) | "what does Donna currently believe is true?" | a living list of beliefs, each with a confidence %, a sparkline of how confidence moved, the evidence behind it, a "why i think this" expansion, and an "i changed my mind" revision log. Plus **open questions** — things she's still figuring out, with split evidence |
| **Memory** | "what does Donna know?" | the memory constellation (graph), recent memories with confidence + source, areas (career/projects/relationships/…) |

Plus a floating **capture** action on every screen — leave a thought, a journal
entry, or a voice note. It writes straight into her model.

The key UX idea: **every memory is evidence; beliefs are the product.** Memory is
what happened. Beliefs are what she *thinks is true*, and they drive her
recommendations.

## 4. The core differentiator — belief-native cognition (the moat)

This is the part to slow down on in the pitch. It's not a prompt trick; there's a
real engine. When anything enters her world (a chat message, a journal entry, an
important email), this pipeline runs (`backend/cognition/`):

```
input (chat / journal / voice / email)
  → observations    extract atomic evidence ("worked late 4 nights this week")
  → confidence       a deterministic engine scores how strongly evidence supports a claim
  → beliefs          recompute the belief for that subject; confidence moves up/down
  → revisions        if a belief flips, log "i used to think X, now Y, because…"
  → questions        when evidence is split, surface an open question (competing hypotheses)
  → planning         beliefs drive the daily plan, nudges, and open loops
  → graph            memories and beliefs link into a navigable relationship graph
```

Concretely, in the codebase:
- `pipeline.ingest()` is the single entry point every surface calls.
- `observations/service.py` turns raw input into evidence rows.
- `confidence/engine.py` is the scoring math — beliefs have **calibrated
  confidence**, not vibes.
- `beliefs/service.py` does `recompute_subject` / `recompute_all`, journals every
  change, and attaches a **consequence** (the recommendation each belief changed).
- `questions/service.py::detect_from_beliefs` produces the "still figuring out"
  list from split evidence.
- `planning/service.py::build_plan` turns beliefs into the day.

Why this is a moat: **the belief graph is per-user and compounding.** Every week
of use makes her model of *you* sharper and harder to replicate. Switching cost
isn't your data export — it's the accumulated *understanding*. A competitor can
copy the UI in a weekend; they can't copy six months of your belief history.

## 5. Tech stack (full)

**Frontend / app**
- React 18 + Vite 5 + Tailwind 3. Editorial design system (Instrument Serif +
  Inter, a Morning/Night theme).
- **Capacitor 8** wraps the same web build into a native **Android APK** (and
  iOS-ready for when there's a Mac). Plugins: splash, status bar, keyboard, app,
  push-notifications.
- Streaming chat over **SSE** (`fetch` + `ReadableStream`), with a mock mode so
  the UI runs with no backend.

**The BRAIN (conversational runtime)** — `donna_runtime/`
- A **single tool-use loop** on the **Claude Agent SDK**. No LangGraph, no
  pipeline framework. Main model: **Haiku 4.5** (cheap, fast; Sonnet/Opus only in
  justified subagents).
- Capabilities are **tools** (retrieval / action / dashboard / terminators /
  subagents); deterministic side-effects are **hooks** (PreToolUse guards,
  PostToolUse memory writes). Every tool description has a when-to-use *and*
  when-NOT-to-use clause.
- Per-turn cost target: **under $0.01** on Haiku with caching.

**Memory (the BRAIN's nine backends)**
- Graphiti entity graph on **FalkorDB**, Supermemory (episodic + document
  chunks), and **Postgres** for procedural rules, observations, open loops, the
  Living Profile, chat history, and a Google-synced calendar.

**The cognition engine (the app's understanding layer)** — `backend/cognition/`
- The deterministic belief/observation/question/plan engine from §4, on Postgres.
  Feature-hash embeddings for memory recall. This is what the Plan/Beliefs/Memory
  screens read, and what chat writes to.

**Backend / API** — FastAPI + uvicorn, async SQLAlchemy + asyncpg.
- `POST /chat` and `POST /chat/stream` (drives the same BRAIN as WhatsApp),
  `/cognition/*` (beliefs, plan, memory, questions, graph, journal),
  `/push/register` + `/push/test`, `/webhooks/composio` (email/calendar ingest),
  the WhatsApp webhook.

**Integrations**
- **WhatsApp** via Meta Cloud API (HMAC-verified webhook).
- **Composio** (Svix "Standard Webhooks") for **Gmail + Google Calendar** —
  signature-verified, deduped, feeds proactive triggers.
- **Exa** for web search, **fal** for image generation, **ElevenLabs** (TTS) +
  **Deepgram** (STT) for voice.
- **FCM** for push (wired, dormant until a Firebase project is added).

**Infrastructure**
- **Railway** (Docker) for the backend, **Supabase** Postgres 17, **FalkorDB**
  for the graph. ngrok only for local webhook testing.

## 6. How it all connects (the data flow)

```
        WhatsApp  ─┐                          ┌─►  send_burst → WhatsApp out
                   │                          │
  Donna app chat  ─┼─►  Ingress (deterministic)  ─►  BRAIN loop (Claude Agent SDK, Haiku)
                   │         │                        │  tools: recall / act / dashboard
  Composio (Gmail) ┘         │                        │  hooks: guards + memory writes
   proactive trigger         │                        └─►  push (FCM) for proactive pings
                             │
                             └─►  cognition.ingest()  ─►  observations → confidence → beliefs
                                                              → questions → plan → graph
                                                                    │
                                  Plan / Beliefs / Memory screens ◄─┘  (read /cognition/*)
```

The magic seam for the demo: **a chat message runs the BRAIN *and* updates the
belief model.** Both surfaces (WhatsApp + app) hit the same loop and the same
memory, keyed to **one identity** — so what you say on WhatsApp shows up as
evidence in the app, and vice versa.

## 7. What's real vs staged vs dormant (be honest on camera)

YC partners probe demos hard. Know exactly what's live so you never get caught.

**Real and working:**
- The full app (4 screens), built into a real Android APK pointing at the live
  Railway backend.
- Streaming chat against the real BRAIN (Claude Agent SDK + Haiku).
- The cognition engine: chat/journal **actually** creates observations and moves
  belief confidence — this is not faked.
- WhatsApp ↔ app shared memory and one unified identity.
- Composio Gmail ingestion → proactive trigger (signature-verified, deduped).

**Staged for the demo (by design):**
- There's a **seeded demo user** (`demo-aarav`) with rich pre-built beliefs,
  plan, and memory so the screens look alive on first open. A brand-new user
  starts empty (with honest empty states) and *builds* their model live — show
  *both*: the seeded user for the "wow," a fresh message for the "it's real."

**Dormant (built, not yet switched on):**
- **Push notifications** — fully wired (FCM + device registration + proactive
  hook), lights up after a 3-step Firebase setup (`docs/PUSH_SETUP.md`).
- **Secure auth** — today it's lightweight client-owned identity (good for a
  controlled beta), *not* authenticated. Real auth (Clerk + backend JWT
  verification) is the next pass. Don't claim multi-tenant security yet.
- **iOS build** — code is ready; needs a Mac to compile.

## 8. Demo script (for the video — ~2.5 min)

Record the APK on a real phone (or scrcpy mirror). Beat by beat:

1. **Open on Plan (5s).** "I didn't open a dashboard. Donna's telling me what
   matters today — and *why*." Point at the "because" chain. *Sets the thesis:
   understanding, not chat.*
2. **Beliefs tab (30s).** Scroll the beliefs. "She has *opinions* about me, each
   with a confidence score and the evidence behind it." Tap **"why i think this"**
   on one — show evidence, counter-evidence, the confidence sparkline. Scroll to
   **open questions**: "and she's honest about what she's still unsure of." Then
   **"i changed my mind"**: "she revises beliefs as evidence shifts." *This is the
   moat — spend the most time here.*
3. **Memory tab (15s).** Show the constellation. "Every memory is evidence, and
   it links to the beliefs it supports."
4. **The live moment (40s).** Go to Chat. Send something new and personal — e.g.
   *"i've been skipping the gym because work's been brutal this week."* Show the
   **streaming** reply + the live status line. Then **go back to Beliefs/Memory**
   and show the new evidence/belief shift. "I just told her one thing, and her
   model of me updated. That's the product." *This is the killer beat — chat
   changed the beliefs.*
5. **WhatsApp unity (20s, optional).** "And it's the same Donna on WhatsApp — same
   memory, same beliefs. I text her like a friend; the app is where I go to see
   what she's figured out."
6. **Close (10s).** "Every week of use makes her model of me sharper. That's the
   moat — you can copy the interface, you can't copy six months of understanding."

Tips: pre-seed `demo-aarav` so the screens are rich; rehearse the live message so
the belief shift is visible; keep her voice in frame (lowercase, blunt, no filler
— it's part of the brand).

## 9. Future work / roadmap

**Near term (pre-launch)**
- **Secure auth** (Clerk + JWT verification on every endpoint) — required before
  multi-user public release.
- **Activate push** (Firebase project + service account) so proactive pings
  reach phones.
- **True token-level streaming** of her reasoning (today: live tool-status +
  paced bursts).
- **iOS build** + TestFlight (needs a Mac).

**Product depth**
- Richer proactive "noticing" layer (multi-source, learning-aware) beyond the
  single email trigger.
- Belief → action loop: let beliefs trigger concrete offers (book the thing,
  draft the message) with agency controls.
- Memory graph as a first-class explorable surface.
- Calendar/Gmail/more via Composio; voice notes end-to-end (Deepgram in, ElevenLabs out).

**Infra / trust**
- Per-user data isolation + encryption story (it's a personal-life product —
  privacy *is* the trust).
- Evals gate on every merge (already a project rule).
- Cost monitoring to hold the sub-$0.01/turn target at scale.

## 10. Likely YC questions — and crisp answers

- **"How is this different from ChatGPT memory?"** ChatGPT stores facts; Donna
  forms *beliefs* — calibrated, evidence-backed positions that change her
  recommendations and that she'll revise. It's a model of *you*, not a notepad.
- **"What's the moat? Can't OpenAI do this?"** The moat is the compounding,
  per-user belief graph. The UI is copyable; six months of accumulated
  understanding of one person isn't. WhatsApp-native distribution is the wedge.
- **"Why WhatsApp?"** Zero friction, zero new behavior — 2B+ people already live
  there. The app is the high-intent second surface, not the acquisition surface.
- **"Is the belief stuff real or a prompt?"** Real engine: observations →
  confidence scoring → belief recompute → revision journal. Offer to show a chat
  message move a confidence score live.
- **"What's left to be a real product?"** Auth, push activation, and the proactive
  noticing layer. The cognitive core and both surfaces already work.
- **"Privacy?"** It's the whole trust model; per-user isolation + encryption is
  on the near-term roadmap, ahead of public multi-user launch.

---

*Sources of truth in the repo: `docs/PRODUCT.md` (product definition),
`CLAUDE.md` (architecture & non-negotiables), `backend/cognition/` (the belief
engine), `donna_runtime/` (the BRAIN), `docs/PUSH_SETUP.md` (push).*
