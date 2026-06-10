# Donna — Product Definition

Donna is a **memory-native AI companion** that lives across **WhatsApp** and the
**Donna app**. Both surfaces share the same memory, context, goals, observations,
and ongoing conversations.

The app is **not** a dashboard. It contains a full chat experience, but chat is
intentionally **not** the default screen. You open the app to **understand your
life**, not just to send messages.

> Conversation is the interface. **Understanding is the product.**

A YC judge should immediately feel: *"This isn't another chatbot. This is a
persistent thinking partner."*

## Product hierarchy

1. Understanding
2. Reflection
3. Memory
4. Conversation

Most AI apps prioritize conversation. Donna prioritizes understanding.

## Belief-native

Donna is moving from *memory-native* to **belief-native**. Memory is what
happened; **beliefs are what Donna thinks is true** — and beliefs are the
product. Memory is merely evidence. Observations become evidence, evidence
strengthens beliefs, and beliefs drive recommendations. The goal feeling: *"this
thing is building a model of a person."*

## Primary navigation

1. **Plan** — "what matters today?" (default home) — and *why* it matters
2. **Chat** — Donna synthesizes and reasons, she doesn't just retrieve
3. **Beliefs** — "things Donna currently believes" (the moat)
4. **Memory** — the constellation; every memory supports a belief

Plus a persistent **floating capture** action (new chat / voice note / quick
capture / journal entry) — capturing a thought for Donna.

---

## Page 1 — Plan (default home)

"What matters today?" The hero experience. Communicates *Donna understands me*,
not *Donna can answer questions*.

Components: daily thesis · hero card · open loops · calendar shape · tracker grid
· nudge · whisper · footer.

## Page 2 — Chat

The second most important screen. Feels different from ChatGPT/Claude — calm,
personal, memory-aware, relationship-oriented. Think **Apple Messages + Journal
+ Claude.**

Features: full history · voice notes · image uploads · long-term memory
references · context cards inline · suggested follow-ups · reactions.

Inline cards (surface occasionally to reinforce persistence):
- **Memory Reference** — "you mentioned this 3 weeks ago"
- **Context** — "related to your YC application"
- **Pattern** — "i've noticed a recurring theme"
- **Open Loop** — "still unresolved"

Avoid: generic chatbot look, bright AI-assistant branding, heavy sidebars.

## Page 3 — Memory

"What Donna knows." Sections: Career · Projects · Relationships · Health · Goals
· Preferences · Recent Memories. Each memory: summary · confidence · timeline ·
related memories · source conversation.

**Memory Graph View** — a beautiful relationship visualization of how memories
connect. A major differentiator.

## Page — Beliefs (the moat)

"Things Donna currently believes." A living list of evolving beliefs, each with
a confidence score, the evidence it's built on, the memories it connects to, and
when it was last strengthened. Confidence changes over time (shown as a live
history sparkline); evidence accumulates; beliefs evolve. Each belief carries a
**consequence** (the recommendation it changed), an expandable **"why i think
this"** (evidence, counter-evidence, confidence history, strengthening event,
reasoning), and an **"i changed my mind"** log of revisions.

Donna also holds **open questions** — *"things i'm still figuring out"* — competing
hypotheses with split evidence (e.g. *does stress come from reviews or lost
sleep? evidence supports both, ~61%*). Questions graduate into beliefs when they
resolve; beliefs fall back to questions when they stop holding. She speaks with
calibrated uncertainty ("current hypothesis…", "i might be wrong, but…",
"evidence is mixed") — thoughtful, not omniscient. A continuously learning
system, not memory software. (Signals are gone — observations now live as
evidence inside beliefs.)

---

## WhatsApp ↔ App synchronization

Conversations feel unified. The app may say *"we were discussing your YC
application yesterday"* about a WhatsApp thread, and each message shows its
**source** (WhatsApp or Donna App). The memory system is shared; users never
feel like they're talking to two separate assistants.
