# Donna — Trial Readiness Status

Honest verified-vs-pending map for the week-long investor trial. Companion to
`PRE_TRIAL_CHECKLIST.md` (which lists the *actions*); this lists what is *proven*.

Last updated: 2026-06-19. Prod: 4 Railway services (Donna/api, donna-proactive,
donna-reminders, falkordb) — all Online; `/health` 200; brain replies.

Legend: ✅ verified live in prod · 🟡 built + unit-tested, not yet run against a
real connected user/data · ⏳ blocked on the founder's WhatsApp app · ❌ not built.

---

## ✅ Verified live in prod (empirical)

- All 4 services online; `/health` 200; reactive brain turn returns a real reply.
- New-user auto-creation on first message; onboarding (timezone confirm) fires.
- Schema self-heals on boot (`create_all` + column reconciler).
- Stale-session retry (observed firing in logs after a redeploy).
- Supermemory episodic write (`POST /v3/documents 200`).
- **FalkorDB graph**: connected, episode ingest + entity/edge extraction
  (`IS_COFOUNDER_WITH` edge observed), persistent volume attached. All 9 memory
  backends now live.
- Situation-brief refresh runs for every user each proactive tick (~20h throttle).
- Composio connect links generate for **Gmail + Calendar** (`ok:true`, real URLs);
  Gmail ingestion live for the dev account.
- Brain boots clean with the 22-tool catalog; capability registry consistent.
- **522 unit/integration tests green.**

## 🟡 Built + unit-tested — NOT yet exercised with a real connected user + data

Pass tests, but have never run against a live inbox / calendar / phone:

- Gmail read tools returning an *actual* inbox; `read_gmail_thread` full bodies.
- `create_calendar_event` making a *real* event; `send_email` via a real card tap.
- Reminders firing on time and **delivering over WhatsApp**.
- Watches (reply/web) firing; proactive checks surfacing (morning brief, finance,
  waste, schedule health, due tasks, birthdays, interests).
- Voice notes (ElevenLabs TTS), with text fallback.
- L0/L1/L2 agency gate on real card taps.
- Onboarding end-to-end: connect Google → 30-day backfill → dashboard card.

→ These flip to ✅ once a real Google account is connected and a real WhatsApp
session exists.

## ⏳ Blocked on the founder's WhatsApp app (cannot be tested until done)

- **The real WhatsApp round-trip is unproven.** All testing used `/chat`, which
  bypasses Meta. Inbound webhook → Donna → outbound delivery to a phone has never
  run. ← single most important untested path.
- **`donna_reopen` template** not created/approved → **all proactive outreach
  outside the 24h window has no delivery path** (queues, then expires after 7d).
  Biggest functional hole for a mostly-silent trial week. Submit early (1–3d review).
- Permanent System User token (temp token dies in 24h).
- `WHATSAPP_APP_SECRET` unset → inbound signature verification off (security).
- Investor's real Google OAuth grant (a human step).

## ❌ Not built (deferred — WhatsApp-first pivot)

- The lightweight **web dashboard** (build-plan B2/B3). The magic-link auth *core*
  exists (`api/auth.py`, signed tokens, `/auth/exchange`), but the dashboard
  endpoints aren't gated to require it and the frontend hash-exchange isn't wired.
  Fine if the trial is WhatsApp-only; not ready if the investor should open a dashboard.

## Residual risks (won't block, but real)

- No full email **search** by sender/query — only recent-24h + thread-by-id.
- Token revoke mid-trial is silent (no re-auth prompt).
- Open loops are capture-only (no proactive "did you do X?" follow-up).
- FalkorDB is passwordless on the Railway private network.

---

## Bottom line

The engine is solid and the **reactive core is prod-proven**. "All use cases tested"
is **not** yet true, for two structural reasons: the real WhatsApp delivery path needs
the founder's app to exist, and most feature paths need a connected Google account +
real data, which only happens once a real person is on it.

### Path to "actually verified" (short)
1. Create the Meta app + connect the webhook → run the **first real WhatsApp message test**.
2. Generate the permanent token; submit `donna_reopen` for approval (do this first — review latency).
3. Connect one Google account → verify connect → ingest → read → act with real data (flips most 🟡 → ✅).
4. Set `WHATSAPP_APP_SECRET`.
