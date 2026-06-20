# Donna — Backend API Contract

The seam between the **backend (ours)** and the **UI (yours)**. Every screen is fed
by one of these endpoints. Build presentational components against these exact
shapes; we own where the data comes from. Field names here are the source of
truth — match them and there's no translation layer.

- **Base URL:** `https://donna-ai.up.railway.app` (prod) / `http://localhost:8000` (local)
- **Identity:** every call carries the stable app id. Reads pass it as a query
  param `?user=<id>`; writes pass it in the JSON body as `user`. One id flows
  through chat, beliefs, memory, and plan — it's one person's mind. Demo id is
  `demo-aarav`.
- **Empty states are real.** A new user has no beliefs/plan/memory yet. List
  endpoints return `[]`; the plan returns `{ "empty": true }`. Design a
  loading / empty / error state for **every** component — most users start empty
  and *build* their model over time.
- **No auth yet.** Endpoints trust the `user` value (beta-grade identity). Real
  auth (Clerk + JWT) is a separate pass; it won't change these shapes, only add
  an `Authorization` header.

---

## READ — Cognition screens

### `GET /cognition/plan?user=<id>` — the Plan (home) screen
The day's thesis + the one thing that matters + why. Returns `{ "empty": true }`
when there's no plan yet.
```json
{
  "date": "tuesday, jun 10",
  "thesis": "today is about the raise,",
  "thesisCoda": "everything else can wait.",
  "because": ["antler is in 16 hours", "your deck still feels flat", "you think best before noon"],
  "decision": {
    "considered": ["prep the deck", "chase intros", "rest"],
    "chose": "lock the deck this morning",
    "because": "you overprepare when uncertain, and certainty buys calm"
  },
  "calendar": [
    { "time": "09:00", "title": "deck rework", "tone": "peak" },
    { "time": "14:00", "title": "lunch with priya", "tone": "normal" }
  ],
  "openLoops": [ { "id": "ol_1", "text": "text luca back", "meta": "2 days" } ],
  "nudge": "start with the HARP slide, not market size.",
  "nudgeBelief": "you lead strongest with the problem",
  "whisper": "you've done harder things than this."
}
```
> `calendar[].tone` is `"peak"` for the day's key event, else `"normal"`.

### `GET /cognition/beliefs?user=<id>` — the Beliefs screen (the moat)
Array of beliefs, each with confidence + evidence. `[]` when none.
```json
[
  {
    "id": "b_1",
    "subject": "work_stress",
    "confidence": 72,
    "delta": "+4",
    "up": true,
    "strengthened": "2 days ago",
    "statement": "you deprioritize exercise when work intensifies",
    "consequence": "i stopped nudging workouts during crunch weeks",
    "evidence": ["skipped the gym 3 nights, blamed a brutal work week", "..."],
    "counter": ["ran on saturday despite a deadline"],
    "history": [60, 64, 68, 72],
    "strengthenedBy": "skipped the gym 3 nights this week",
    "reasoning": "consistent across the last month",
    "related": ["work", "health"]
  }
]
```
- `confidence` is `0–100`. `history` is the confidence sparkline (oldest→newest).
- `delta` is a signed string (`"+4"` / `"-6"`) or `null`; `up` is the boolean.
- `consequence` / `counter` may be `null`. `evidence` / `related` may be `[]`.

### `GET /cognition/beliefs/{id}?user=<id>` — one belief, expanded
Same shape as above **plus**:
```json
{
  "supporting_memory_ids": ["m_1", "m_2"],
  "contradicting_memory_ids": [],
  "actions_influenced": ["muted workout nudges"],
  "confidence_history": [ { "conf": 60, "at": "2026-05-01T...", "reason": "formed" }, { "conf": 72, "at": "...", "reason": "from conversation" } ]
}
```
Returns `{ "error": "not found" }` for a bad id.

### `GET /cognition/belief-history?user=<id>` — "i changed my mind"
```json
[
  {
    "id": "rev_1",
    "from": { "statement": "you avoid outreach when busy", "conf": 58 },
    "to":   { "statement": "you avoid outreach when the story feels weak", "conf": 71 },
    "why": "the pattern held even on calm weeks"
  }
]
```

### `GET /cognition/questions?user=<id>` — "things i'm still figuring out"
```json
[
  { "id": "q_1", "confidence": 61, "question": "does stress come from reviews or lost sleep?", "status": "evidence supports both", "leaning": null }
]
```

### `GET /cognition/memory?user=<id>&limit=12` — the Memory screen "recent"
```json
[
  {
    "id": "m_1",
    "summary": "skipped the gym 3 nights, blamed a brutal work week",
    "confidence": "high",
    "when": "2 days ago",
    "source": "Donna App",
    "supports": ["you deprioritize exercise when work intensifies"]
  }
]
```
> `confidence` is `"high" | "medium" | "low"` (not a number). `when` is relative
> text. `supports` lists the belief statements this memory is evidence for.

### `GET /cognition/memory/{id}?user=<id>` — one memory, expanded
```json
{
  "id": "m_1", "content": "...", "source": "Donna App", "source_type": "donna_app",
  "source_ref": null, "when": "2 days ago", "topics": ["work","health"],
  "entities": ["gym"], "supports": ["you deprioritize exercise when work intensifies"]
}
```

### `GET /cognition/graph?user=<id>` — the memory constellation
```json
{
  "nodes": [ { "id": "n_1", "label": "priya", "kind": "person", "weight": 1.0, "supports": { "belief": "you trust priya on pricing", "confidence": 70 } } ],
  "edges": [ { "src": "n_1", "dst": "n_2", "relation": "mentions", "weight": 0.5 } ]
}
```
> `kind` ∈ `person | project | goal | pattern`. `supports` is `null` for nodes
> that don't anchor a belief. Belief nodes themselves are internal and not returned.

### `GET /cognition/open-loops?user=<id>`
```json
[ { "id": "ol_1", "text": "text luca back", "meta": "2 days", "source": "Donna App", "priority": 0.5 } ]
```

### `GET /cognition/reasoning/{chain_id}` — a reasoning chain
```json
{ "id": "rc_1", "root_decision": "lock the deck this morning", "steps": ["..."], "belief_ids": ["b_1"], "confidence": 0.8 }
```

---

## CHAT

### `POST /chat` — non-streaming (mock/fallback)
Request: `{ "message": "how's my week looking", "user": "demo-aarav" }`
Response: `{ "user_id": "<uuid>", "reply": [ <bubble>, ... ] }`

### `POST /chat/stream` — streaming (default). Server-Sent Events.
Same request body. Response is `text/event-stream`. Three event types:
```
event: status            ← ephemeral "what she's doing" line
data: {"text":"looking that up"}

event: bubble            ← one message, in her real burst pacing
data: {"type":"text","text":"your week is heavy. three deadlines stacked thu–fri."}

event: done
data: {"user_id":"<uuid>"}
```
Render: show "thinking…" / the latest `status` until `done`; append each `bubble`
as it arrives.

### Bubble types (the `reply[]` items and `bubble` events)
Discriminated on `type`:
```jsonc
{ "type": "text", "text": "..." }
{ "type": "cta", "text": "...", "buttons": [ { "id": "...", "title": "..." } ] }
{ "type": "cta_url", "text": "...", "display_text": "open", "url": "https://..." }
{ "type": "list", "text": "...", "button_label": "pick", "sections": [ { "title": "...", "rows": [ { "id": "...", "title": "..." } ] } ] }
{ "type": "image", "url": "https://...", "caption": "..." }
{ "type": "audio", "url": "https://..." }
{ "type": "document", "url": "https://...", "filename": "...", "caption": "..." }
{ "type": "delay", "seconds": 1.5 }   // streaming honors this server-side; non-stream clients pause
```

---

## WRITE — capture & feedback

### `POST /cognition/journal` — leave a thought (journal / quick capture)
Request: `{ "user": "demo-aarav", "text": "...", "topics": ["..."], "entities": ["..."] }` (topics/entities optional)
Response: `{ "ok": true, "memory_id": "m_9", "observations": 1, "beliefs_touched": ["work_stress"], "questions_open": 2 }`

### `POST /cognition/voice` — same shape as journal (transcript in)

### `POST /cognition/feedback` — agree/disagree with a belief
Request: `{ "user": "demo-aarav", "belief_id": "b_1", "signal": "agree" }` (`signal`: `"agree" | "disagree"`)
Response: `{ "ok": true, "confidence": 76 }`

### `POST /push/register` — device push token
Request: `{ "user": "demo-aarav", "token": "<fcm-token>", "platform": "android" }`
Response: `{ "ok": true, "user_id": "<uuid>" }`

### `POST /push/test` — fire a test notification
Request: `{ "user": "demo-aarav", "title": "donna", "body": "..." }` (title/body optional)
Response: `{ "ok": true, "configured": true, "delivered": 1 }`

---

## Health
`GET /health` → `{ "status": "ok" }`

---

## For the UI engineer — how to consume this

Build **presentational components** that take these shapes as props and render —
no `fetch`, no routing, no data layer (we own those). Suggested TS interfaces:

```ts
interface Belief {
  id: string; subject: string; confidence: number;       // 0–100
  delta: string | null; up: boolean; strengthened: string;
  statement: string; consequence: string | null;
  evidence: string[]; counter: string[] | null;
  history: number[]; strengthenedBy: string; reasoning: string; related: string[];
}
interface PlanResponse {
  empty?: true;
  date: string; thesis: string; thesisCoda: string; because: string[];
  decision: { considered: string[]; chose: string; because: string };
  calendar: { time: string; title: string; tone: "peak" | "normal" }[];
  openLoops: { id: string; text: string; meta: string }[];
  nudge: string; nudgeBelief: string | null; whisper: string;
}
interface Memory { id: string; summary: string; confidence: "high"|"medium"|"low"; when: string; source: string; supports: string[]; }
interface Question { id: string; confidence: number; question: string; status: string; leaning: string | null; }
type Bubble =
  | { type: "text"; text: string }
  | { type: "cta"; text: string; buttons: { id: string; title: string }[] }
  | { type: "image"; url: string; caption: string }
  | { type: "delay"; seconds: number };
  // ...and cta_url / list / audio / document above
```

Deliver each component with **loading, empty, and error** states (empty is the
common case for new users), in a Storybook with mock props in these exact shapes.
Then integration is "swap the mock for our live data" — nothing else.

*Source of truth in code: `backend/cognition/api/routes.py` (cognition),
`api/chat.py` (chat), `api/push.py` (push). If a shape here ever disagrees with
the code, the code wins — tell us and we'll fix the doc.*
