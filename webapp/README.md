# Donna — demo web app

A polished, mobile-first chat UI (Donna brand) wired to the backend `/chat`
endpoint. No WhatsApp/Meta needed — it talks straight to the brain over HTTP.

## Run it RIGHT NOW — no backend, no API key, no database

The app ships in **mock mode** (`VITE_MOCK=1`, the default), so you can run and
polish the whole UI with zero setup. Donna's replies are scripted but use the
exact same bubble shapes as the real brain.

```bash
cd webapp
npm install
npm run dev          # http://localhost:5173 — a "demo mode" pill shows in the header
```

This is all you need for design/polish work. When you get an Anthropic key,
flip to the real brain (next section).

## Connect the real brain (when you have a key)

Two backend options — pick one:

**A. SQLite (no Docker/Postgres needed):**
```bash
# from repo root
export ANTHROPIC_API_KEY=sk-ant-...
export DATABASE_URL="sqlite+aiosqlite:///./donna.db"
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000     # tables auto-create in donna.db
```

**B. Full stack (Postgres + optional FalkorDB):**
```bash
docker compose up -d
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn api.main:app --reload --port 8000
```

Then point the app at it:
```bash
cd webapp
cp .env.example .env          # set VITE_MOCK=0  (VITE_API_BASE defaults to localhost:8000)
npm run dev
```

Open `http://localhost:5173`, then use your browser's **mobile device view**
(Chrome DevTools → toggle device toolbar, pick iPhone) to see it as a phone.
On desktop it already renders inside a phone frame.

## Deploy (shareable link for judges)

- Push the repo to GitHub, import `webapp/` into **Vercel** (framework: Vite).
- Set env `VITE_API_BASE` to your deployed backend (Railway) URL.
- Vercel gives you a public URL judges open on their own phones. CORS is already
  open on the backend.

## How it talks to the backend

`POST {VITE_API_BASE}/chat` with `{ "message": string, "user": string }` →
`{ "user_id": string, "reply": Bubble[] }`. Bubble types: `text`, `cta`,
`cta_url`, `list`, `image`, `audio`, `delay` (delay paces the typing animation).

A stable `user` id is kept in `localStorage` so Donna's memory persists across
the session. Clear it (or use a fresh browser/incognito) to demo a new user.

## Structure (drop Claude-designed components in here)

```
src/
  App.jsx                 orchestration + staggered typing reveal
  api.js                  sendChat() — the one network call
  components/
    PhoneFrame.jsx        device frame
    Bubble.jsx            renders every bubble type
    Composer.jsx          input + send
    TypingDots.jsx        "donna is typing"
```

To restyle with a Claude-generated design, replace the components in
`src/components/` — keep the `sendChat()` contract and the bubble `type`
switch in `Bubble.jsx`.
