# Donna — Pre-Trial Checklist (week-long investor trial)

Goal: one investor uses Donna on WhatsApp for ~1 week, and across that week Donna
**(1)** captures important info from conversations, **(2)** does tasks she's assigned,
and **(3)** shows proactiveness ("she texts first").

Status legend: `[x]` done/verified · `[ ]` to do · `[~]` optional

---

## Already done + verified in prod (2026-06-17)

- [x] **Three Railway services live**, one image, role-switched by `DONNA_PROCESS_ROLE`:
  - `Donna` (api) — webhook + brain — https://donna-ai.up.railway.app
  - `donna-proactive` (proactive) — "she texts first" tick, sweeping cleanly
  - `donna-reminders` (reminders) — fires DonnaSchedule rows (poll 5s)
- [x] **Reactive path proven** — live `/chat` turn returned a real reasoned reply (brain runs on the bundled SDK CLI; no node needed).
- [x] **Schema self-heals on boot** — `create_tables()` now runs `create_all` + a column reconciler (fixed prod crashes on `users.notify_channel`, `open_loops.*`).
- [x] **Stale-session crash fixed** — `donna_turn` retries from a fresh session when a resumed session is gone after a redeploy (verified firing in prod).
- [x] **Supermemory episodic memory works in prod** — `POST api.supermemory.ai/v3/documents → 200` on a real turn.
- [x] **Webhook endpoint passes Meta's verification handshake** (`GET /webhook` → echoes challenge, HTTP 200).

---

## THE SHORT LIST — ranked by trial impact

### 1. Permanent WhatsApp token  ⛔ CRITICAL (or the trial dies on day 1)
The test-number token from "API Setup" **expires in 24h**. Before the trial starts, replace it with a non-expiring **System User** token.

- [ ] Create your own Meta app + free test number (see "WhatsApp app setup" below).
- [ ] Generate a **System User** token: business.facebook.com → **Business Settings** → **Users → System Users** → Add → assign the app → **Generate token** with scopes `whatsapp_business_messaging` + `whatsapp_business_management` → **never expires**.
- [ ] Paste it to me → I set `WHATSAPP_TOKEN` on all three Railway services + redeploy.

### 2. Composio webhook + investor connects Google  ⭐ BIGGEST LEVER
Powers real Gmail/Calendar **tasks** AND most **proactiveness** (calendar/email tables only fill from Composio ingest). Without it, Donna only sees what's typed to her.

- [x] **Composio webhook registered + firing** — verified live (real Gmail ingestion in prod logs for the dev account).
- [x] **Gmail + Calendar auth configs exist** — Gmail was set up; the missing `googlecalendar` config was created (`ac_Xl6dIjazfJ36`, composio-managed).
- [x] **Connect-link generation fixed** — the SDK's deprecated `toolkits.authorize` was replaced with the v3 `/connected_accounts/link` REST call; both Gmail + Calendar now mint real links in prod.
- [ ] During onboarding, the investor taps the **"connect Google"** card and authorizes Gmail + Calendar (the one human step — standard Google consent).
- [ ] Verify after they grant: a calendar event / email shows up in Donna's tables (onboarding backfill runs on `connection.complete`).

### 3. `donna_reopen` template — created + approved  ⚠️ (or proactive outreach after silence fails)
Outside the 24h window, Meta only delivers an approved template. A week trial is mostly outside-24h, so proactive "she texts first on day 3" needs this.

- [ ] In your new WABA → **WhatsApp Manager → Message Templates → Create**:
  - Name: `donna_reopen`
  - Category: **Utility**
  - Language: English
  - Body: `hey, been a while. anything on your mind?`
  - No header/footer/buttons, no variables.
- [ ] Submit and wait for approval (1–3 days — **submit early**).
- [ ] Confirm `WHATSAPP_REOPEN_TEMPLATE=donna_reopen` on Railway (default already set).
- How it works: outside 24h Donna sends this nudge + queues the real message; when the investor replies, the queued content flushes as freeform before the brain runs.

### 4. FalkorDB / graph memory  [~] OPTIONAL
Entity-graph memory is OFF in prod (`FALKORDB_HOST=localhost`). Degrades gracefully — facts still land in the living profile + episodes. Fix only if you want richer relationship-graph reasoning during the trial.

- [~] Add a managed FalkorDB/Redis (Railway template or external) → set `FALKORDB_HOST/PORT/USERNAME/PASSWORD` on the services.

---

## WhatsApp app setup (the prerequisite for 1–3)

Create an app **you control** (the current "Unofficial: Propel" credentials can't be configured — no access).

1. **developers.facebook.com** → log in (your FB account) → **My Apps → Create App**.
2. Name `Donna` → **Other** → type **Business** → Create.
3. Dashboard → **Add products → WhatsApp → Set up** (create a Business portfolio if prompted).
4. **WhatsApp → API Setup** — copy these **3 values** and paste them to me:
   - [ ] **Phone number ID** (the test sender)
   - [ ] **WhatsApp Business Account ID**
   - [ ] **Access token** (temp 24h now; swap to the System User token from item 1 before the trial)
5. **API Setup → Manage phone number list** → add + verify your demo recipient numbers (up to 5: you + the investor).
6. **WhatsApp → Configuration → Webhook → Edit**:
   - Callback URL: `https://donna-ai.up.railway.app/webhook`
   - Verify token: `skill2goodhonestly` (already matches Railway)
   - **Verify and save** → **Manage** webhook fields → enable **messages**.

### Railway env to swap once you paste the 3 values (I'll do this)
- `WHATSAPP_TOKEN` (permanent, item 1)
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_BUSINESS_ACCOUNT_ID`
- (keep `WHATSAPP_VERIFY_TOKEN=skill2goodhonestly`)
- across **all three** services, then redeploy.

---

## Final smoke test before handing it to the investor
- [ ] Investor's number messages the test sender → Donna replies (user auto-created).
- [ ] Investor connects Google → a calendar event/email appears in Donna's view.
- [ ] Assign a task ("remind me at 3pm", "track my water") → it fires / persists.
- [ ] Tell Donna a durable fact → next-day recall returns it (Supermemory).
- [ ] Force a proactive moment (or wait for a real one) → arrives; after 24h silence the `donna_reopen` template delivers.
- [ ] Optional security: set `WHATSAPP_APP_SECRET` (from your new app's Basic settings) → inbound signature verification on.

---

## Owner split
- **You (dashboard, only you can):** create the app, get the 3 values, allowlist numbers, set the webhook, generate the System User token, submit the template, connect Google.
- **Me (infra):** swap Railway env + redeploy, register the Composio webhook, provision FalkorDB (optional), verify each step in prod.
