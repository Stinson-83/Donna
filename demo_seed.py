"""Demo Seeding Framework — make every DEMO_VIDEO_PLAN.md moment occur immediately.

Populates the runtime DB for the fictional, fully-trained user **Mira** so the
9-moment demo plays against real state: user model + relationships, goals, the
fundraising context, episodic memories + beliefs (cognition), commitments, watches,
calendar, the inbox (with noise to rank against), finance (accounts/bills/txns),
meal observations, notifications/chat + device token, travel, and the dashboard
projection (watches/calendar/bills/loops -> the "holding" count + the watch bar).

Data mirrors DEMO_DATASET.md / DEMO_SEED_DATA.json. **All timestamps are anchored to
NOW at run time** (so "auto-debit in 4 days", "birthday saturday", "renews tomorrow"
are always relative) — which is why every proactive moment can fire the instant you
seed. Idempotent: re-running wipes Mira's prior rows and reseeds.

Run (against $DATABASE_URL):
    python demo_seed.py
    DEMO_NOW=2026-04-18T07:30:00 python demo_seed.py   # pin the demo "now"

Proactive moments (M2/M3/M4/M7/M8) still FIRE on cue via their real triggers — this
seed just guarantees the state + clears the proactive-ping dedup so nothing is held.
The cards (M2-M8) render live; they are not pre-seeded.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("demo_seed")

USER_ID = "demo-mira"
PHONE = "+6580000000"


def _now() -> datetime:
    raw = os.environ.get("DEMO_NOW")
    if raw:
        return datetime.fromisoformat(raw).replace(tzinfo=None, microsecond=0)
    return datetime.utcnow().replace(microsecond=0)


# ── relationships (living_profile.biography.relationships) ───────────────────
# `_email` + `frequency` let the email importance scorer recognize a known sender.
def _relationships() -> list[dict]:
    return [
        {"name": "Aniroodh Sharma", "relation": "brother", "importance": 90, "frequency": "weekly", "_email": "aniroodh@example.com", "notes": "family foodie; recommends restaurants; texted about lotus thai"},
        {"name": "Ishaan", "relation": "partner", "importance": 92, "frequency": "daily", "_email": "ishaan@example.com", "notes": "the saturday lotus thai plan is with him"},
        {"name": "Priya Menon", "relation": "cofounder / cto", "importance": 95, "frequency": "daily", "_email": "priya@marble.dev", "notes": "owed the q3 deck; you defer to her on pricing"},
        {"name": "Ravi Iyer", "relation": "head-of-eng candidate", "importance": 70, "frequency": "weekly", "_email": "ravi@example.com", "notes": "offer out; 9:30 negotiation"},
        {"name": "Pavithra", "relation": "landlord (new flat)", "importance": 60, "frequency": "weekly", "_email": "pavithra@example.com", "notes": "awaiting reply on the room"},
        {"name": "Kartik Shah", "relation": "advisor", "importance": 65, "frequency": "monthly", "_email": "kartik@example.com", "notes": "4pm, rescheduled"},
        {"name": "Anjali Sharma", "relation": "mother", "importance": 96, "frequency": "weekly", "_email": "anjali@example.com", "birthday": "<MOM_BDAY>", "notes": "prefers lilies; you call her around noon on her birthday"},
        {"name": "Avu", "relation": "close friend", "importance": 55, "frequency": "rare", "notes": "wedding; rsvp due monday"},
        {"name": "Aanya Rao", "relation": "investor (sequoia partner)", "importance": 80, "frequency": "weekly", "_email": "aanya@sequoia.example.com", "notes": "leading the round; term sheet out"},
    ]


# ── reset (idempotency) ──────────────────────────────────────────────────────
async def _reset(s, user_id: str) -> None:
    from sqlalchemy import delete

    from db.models import (Bill, CalendarEntry, Card, ChatMessage, Context, DeviceToken,
                           DonnaInstance, EmailMessage, FinanceAccount, FinanceTransaction,
                           Goal, Observation, OpenLoop, ProactivePing, User, Watch)

    for model in (FinanceTransaction, Bill, FinanceAccount, Observation, DonnaInstance,
                  Watch, OpenLoop, CalendarEntry, EmailMessage, Context, Goal,
                  DeviceToken, ChatMessage, ProactivePing, Card):
        await s.execute(delete(model).where(model.user_id == user_id))
    await s.execute(delete(User).where(User.id == user_id))
    await s.flush()


# ── populate ─────────────────────────────────────────────────────────────────
async def _user(s, user_id: str, now: datetime) -> None:
    from db.models import DeviceToken, User

    rels = _relationships()
    mom_bday = (now + timedelta(days=2)).strftime("%m-%d")  # saturday, MM-DD for the birthday check
    for r in rels:
        if r.get("birthday") == "<MOM_BDAY>":
            r["birthday"] = mom_bday
    s.add(User(
        id=user_id, phone=PHONE, name="Mira Sharma", timezone="Asia/Singapore",
        notify_channel="auto", onboarding_complete=True,
        living_profile={
            "biography": {
                "summary": "founder & ceo of marble (developer-infrastructure). singapore, from bengaluru. mid series-a raise (sequoia leading), mid-relocation. banks in india (hdfc).",
                "relationships": rels,
                "interests": ["tokyo travel", "thai food", "fundraising"],
            },
            "preferences": {"music": "apple music", "airport_ride": "grab standard", "mom_flowers": "lilies", "comms": "blunt, lowercase, 'heads up' openers"},
        },
    ))
    s.add(DeviceToken(user_id=user_id, token="demo-fcm-token", platform="android"))


async def _goals(s, user_id: str, now: datetime) -> int:
    from db.models import Goal

    goals = [
        Goal(user_id=user_id, title="close the series a", description="sequoia leading; lightfield follow soft-circled", category="financial", priority=1, status="active", confidence=0.9, source="chat"),
        Goal(user_id=user_id, title="stay under ~1900 cal/day, drop 4kg before the move", category="health", priority=2, status="active", confidence=0.8, source="chat"),
        Goal(user_id=user_id, title="get the new flat sorted", category="personal", priority=3, status="active", confidence=0.7, source="inferred"),
    ]
    for g in goals:
        s.add(g)
    return len(goals)


async def _context(s, user_id: str, now: datetime) -> int:
    from db.models import Context

    s.add(Context(
        user_id=user_id, kind="fundraising", confidence=0.9, state="active", source="focus_window",
        evidence={"declared": "fundraising is my priority for the next two weeks"},
        domains={"amplify": ["investor", "investors", "fundraise", "raise", "round", "seed", "series",
                             "term sheet", "valuation", "diligence", "pitch", "data room", "sequoia"], "damp": []},
        onset_at=now - timedelta(days=6), last_signal_at=now, expires_at=now + timedelta(days=10),
    ))
    return 1


async def _commitments(s, user_id: str, now: datetime) -> int:
    from db.models import OpenLoop

    demo = [
        ("answer sequoia on the term sheet", "decision", now.replace(hour=23, minute=59)),
        ("send priya the q3 deck", "work", now.replace(hour=18, minute=0)),
        ("reply to pavithra on the room", "admin", None),
        ("rsvp to avu's wedding", "rsvp", now + timedelta(days=4)),
        ("call mom (postponed 4 days)", "relationship", None),
        ("gym tonight — 3rd skip this week looming", "health", now.replace(hour=19, minute=30)),
    ]
    # background backlog so the "holding 23" pulse is real (4 watches + 19 loops = 23)
    background = [
        "renew laptop warranty", "reply to the design contractor", "expense the SFO trip",
        "review the SOC2 checklist", "follow up with the bank on the FD", "book the dentist follow-up",
        "send the board update draft", "reply to the angel who intro'd lightfield",
        "update the data room with the april numbers", "schedule the all-hands",
        "renew the .dev domain", "thank-you note to kartik", "confirm avu's gift",
    ]
    n = 0
    for content, cat, due in demo:
        s.add(OpenLoop(user_id=user_id, content=content, status="active", category=cat, due_date=due))
        n += 1
    for content in background:
        s.add(OpenLoop(user_id=user_id, content=content, status="active"))
        n += 1
    return n


async def _watches(s, user_id: str, now: datetime) -> int:
    from db.models import Watch

    watches = [
        Watch(user_id=user_id, watch_type="reply", subject_key="sequoia", title="sequoia partner reply",
              status="active", importance=90, deadline=now + timedelta(days=1, hours=4),
              next_check=now - timedelta(minutes=30), created_at=now - timedelta(days=2), last_known_state={}),
        Watch(user_id=user_id, watch_type="web", subject_key="tokyo flights below 38000", title="tokyo flights below ₹38k",
              status="active", importance=55, next_check=now + timedelta(hours=3), created_at=now - timedelta(days=14),
              last_known_state={"seen_urls": ["https://example.com/sin-nrt-1", "https://example.com/sin-nrt-2"]}),
        Watch(user_id=user_id, watch_type="reply", subject_key="pavithra", title="pavithra response on the room",
              status="active", importance=60, next_check=now + timedelta(hours=2), created_at=now - timedelta(days=3), last_known_state={}),
        Watch(user_id=user_id, watch_type="reply", subject_key="priya deck", title="q3 deck feedback from priya",
              status="active", importance=65, next_check=now + timedelta(hours=5), created_at=now - timedelta(days=1), last_known_state={}),
    ]
    for w in watches:
        s.add(w)
    return len(watches)


async def _calendar(s, user_id: str, now: datetime) -> int:
    from db.models import CalendarEntry

    d = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def at(day_off, h, m=0):
        return d + timedelta(days=day_off, hours=h, minutes=m)

    events = [
        ("call with ravi — offer negotiation", at(0, 9, 30), at(0, 10, 0), None, "g_ravi"),
        ("dentist", at(0, 11, 0), at(0, 11, 45), "Holland Village", "g_dentist"),
        ("priya 1:1 — you owe her the deck", at(0, 14, 0), at(0, 14, 45), None, "g_priya"),
        ("kartik (advisor) — rescheduled", at(0, 16, 0), at(0, 16, 30), None, "g_kartik"),
        ("gym", at(0, 19, 30), at(0, 20, 30), None, "g_gym"),
        ("call mom (postponed 4 days)", at(0, 22, 0), at(0, 22, 30), None, "g_callmom"),
        ("SQ112 flight SIN -> KUL (Changi T1) — lightfield in KL", at(1, 7, 10), at(1, 8, 15), "Changi Airport T1", "g_flight"),
        ("Mom's birthday", at(2, 0, 0), at(2, 23, 59), None, "g_mom_bday"),
    ]
    for title, start, end, loc, gid in events:
        s.add(CalendarEntry(user_id=user_id, title=title, start_time=start, end_time=end, location=loc, google_event_id=gid))
    return len(events)


async def _emails(s, user_id: str, now: datetime) -> int:
    from db.models import EmailMessage

    def msg(mid, thread, frm, name, subj, snip, days_ago, hours_ago=0, important=False, labels=None):
        return EmailMessage(
            user_id=user_id, gmail_message_id=mid, thread_id=thread, from_address=frm, from_name=name,
            to_addresses=[], cc_addresses=[], subject=subj, snippet=snip, body_text=snip, body_stored=True,
            labels=labels or ["INBOX"], is_important=important, is_starred=False, is_sent=False,
            ingest_depth="full", internal_date=now - timedelta(days=days_ago, hours=hours_ago),
        )

    emails = [
        msg("m_sequoia", "th_sequoia", "aanya@sequoia.example.com", "Aanya Rao", "Re: Marble — term sheet (final)",
            "here are the final terms. we'd want your answer by EOD; the sheet expires tomorrow at noon.", 2, important=True, labels=["INBOX", "IMPORTANT"]),
        msg("m_priya", "th_priya", "priya@marble.dev", "Priya Menon", "q3 deck — your pass?", "left comments on slides 4-9. need your pass before the 2pm.", 1),
        msg("m_pavithra", "th_pavithra", "pavithra@example.com", "Pavithra", "the room — a few questions", "can you confirm the move-in date and the deposit?", 3),
        msg("m_lightfield", "th_lightfield", "theo@lightfield.example.com", "Theo Vance", "Friday in KL — confirming 11am", "see you friday 11am. excited to dig into the numbers.", 2),
        msg("m_aws", "th_aws", "no-reply@aws.amazon.example.com", "AWS Billing", "Your upcoming charges", "estimated charges this cycle INR 47,200, auto-debiting in 4 days.", 3),
        msg("m_news", "th_news", "digest@somesaas.example.com", "SaaS Weekly", "10 ways to scale your infra", "this week in infra...", 0, hours_ago=2, labels=["INBOX", "CATEGORY_PROMOTIONS"]),
        msg("m_recruiter", "th_recruiter", "talent@bigco.example.com", "A Recruiter", "Senior role at BigCo", "your profile is a strong match...", 0, hours_ago=1),
    ]
    for e in emails:
        s.add(e)
    return len(emails)


async def _finance(s, user_id: str, now: datetime) -> dict:
    from db.models import Bill, FinanceAccount, FinanceTransaction

    current = FinanceAccount(id="acct_current", user_id=user_id, account_type="current", institution="HDFC",
                             masked_number="••4471", currency="INR", balance=43000, balance_synced_at=now)
    savings = FinanceAccount(id="acct_savings", user_id=user_id, account_type="savings", institution="HDFC",
                             masked_number="••9920", currency="INR", balance=120000, balance_synced_at=now)
    s.add_all([current, savings])
    s.add_all([
        Bill(user_id=user_id, account_id="acct_current", biller="AWS", amount=47200, currency="INR",
             due_date=now + timedelta(days=4), auto_pay=True, status="upcoming"),
        Bill(user_id=user_id, account_id="acct_current", biller="SP Group (electric)", amount=1940, currency="INR",
             due_date=now + timedelta(days=1), auto_pay=True, status="upcoming"),
    ])
    # recurring subs (Spotify + Apple Music) -> the waste/duplicate-service signal (M8)
    txns = 0
    for month in (1, 2, 3):
        s.add(FinanceTransaction(user_id=user_id, account_id="acct_current", amount=229, currency="INR",
                                 direction="debit", merchant="Spotify", category="subscription",
                                 occurred_at=now - timedelta(days=30 * month)))
        s.add(FinanceTransaction(user_id=user_id, account_id="acct_current", amount=99, currency="INR",
                                 direction="debit", merchant="Apple Music", category="subscription",
                                 occurred_at=now - timedelta(days=30 * month)))
        txns += 2
    s.add(FinanceTransaction(user_id=user_id, account_id="acct_current", amount=38, currency="INR",
                             direction="debit", merchant="Common Man Coffee", category="food",
                             occurred_at=now - timedelta(days=1)))
    txns += 1
    return {"accounts": 2, "bills": 2, "transactions": txns}


async def _observations(s, user_id: str, now: datetime) -> int:
    """3-day meal streak over the goal + today's earlier meals (M4 'day 3' line)."""
    from db.models import DonnaInstance, Observation

    inst_id = "demo-meal-tracker"
    s.add(DonnaInstance(id=inst_id, user_id=user_id, primitive="tracker", connector="manual", label="meal tracker", status="active"))
    await s.flush()
    meals = [
        ("thali + dessert", 2150, now - timedelta(days=1)),
        ("pizza night", 2300, now - timedelta(days=2)),
        ("burgers", 2050, now - timedelta(days=3)),
        ("dosa + filter coffee", 640, now - timedelta(hours=5)),
        ("samosa + chai", 580, now - timedelta(hours=2)),
    ]
    for item, cal, when in meals:
        s.add(Observation(user_id=user_id, instance_id=inst_id, type="meal", event_time=when,
                          fields={"item": item, "calories": cal}, source="whatsapp"))
    return len(meals)


async def _notifications(s, user_id: str, now: datetime) -> int:
    """Prior cross-surface chat (the History tab + 'day 247' feel). The proactive-ping
    table was cleared in _reset, so M2/M3/M4/M7/M8 are NOT deduped and fire immediately."""
    from db.models import ChatMessage

    history = [
        ("donna", "balance is S$31,240, clears the requirement with room. filed a copy to your permit folder.", False),
        ("user", "remind raghav about the demo at 3", False),
        ("donna", "done. i'll nudge him at 2:30 and tell you if he doesn't confirm.", False),
        ("donna", "your SQ112 friday is at 7:10 from t1. you'll want a 5:30 cab.", True),
    ]
    base = now - timedelta(days=1)
    for i, (role, content, proactive) in enumerate(history):
        s.add(ChatMessage(user_id=user_id, role=role, content=content, is_proactive=proactive,
                          created_at=base + timedelta(minutes=i * 7)))
    return len(history)


async def _cognition(user_id: str, now: datetime) -> dict:
    """Beliefs + episodic memories in the cognition store (separate from db.models).
    Best-effort: the store + its tables must exist (real run). Supports M5 recall +
    M7 'you usually call mom at noon' + the (parked) Memory/Beliefs surfaces."""
    out = {"beliefs": 0, "memories": 0}
    try:
        from backend.cognition.store import Belief, Memory, async_session as cog_session
        from sqlalchemy import delete

        beliefs = [
            ("mom", "you call mom around noon on her birthday", 0.9),
            ("rides", "grab standard is your usual airport ride", 0.81),
            ("outreach", "you avoid outreach when the story feels weak", 0.84),
            ("music", "you prefer apple music", 0.4),
        ]
        memories = [
            ("aniroodh texted: 'the pad see ew, mira. you have to.' -> lotus thai, holland village", "whatsapp", now - timedelta(days=4), ["aniroodh", "lotus thai"], ["food", "lotus thai"]),
            ("mira said she'd take ishaan to lotus thai on saturday", "donna_app", now - timedelta(days=5), ["ishaan", "lotus thai"], ["plans", "saturday"]),
            ("sequoia term-sheet thread — final terms, awaiting mira's answer; expires fri noon", "gmail", now - timedelta(days=2), ["sequoia", "aanya rao"], ["fundraising"]),
            ("mom's favourite flowers are lilies", "chat", now - timedelta(days=120), ["mom"], ["family", "preferences"]),
        ]
        async with cog_session() as cs:
            await cs.execute(delete(Belief).where(Belief.user_id == user_id))
            await cs.execute(delete(Memory).where(Memory.user_id == user_id))
            for subj, stmt, conf in beliefs:
                cs.add(Belief(user_id=user_id, subject=subj, statement=stmt, confidence=conf, status="active"))
                out["beliefs"] += 1
            for content, src, when, ents, tops in memories:
                cs.add(Memory(user_id=user_id, content=content, source=src, source_type=src, created_at=when,
                              importance=0.7, entities=ents, topics=tops))
                out["memories"] += 1
            await cs.commit()
    except Exception as e:
        log.warning("cognition seed skipped (store unavailable): %s", e)
    return out


# ── orchestrator ─────────────────────────────────────────────────────────────
async def seed(user_id: str = USER_ID, now: datetime | None = None) -> dict:
    now = now or _now()
    from db.session import async_session

    summary: dict = {"user_id": user_id, "now": now.isoformat()}
    async with async_session() as s:
        await _reset(s, user_id)
        await _user(s, user_id, now)
        summary["goals"] = await _goals(s, user_id, now)
        summary["contexts"] = await _context(s, user_id, now)
        summary["commitments"] = await _commitments(s, user_id, now)
        summary["watches"] = await _watches(s, user_id, now)
        summary["calendar"] = await _calendar(s, user_id, now)
        summary["emails"] = await _emails(s, user_id, now)
        summary["finance"] = await _finance(s, user_id, now)
        summary["observations"] = await _observations(s, user_id, now)
        summary["notifications"] = await _notifications(s, user_id, now)
        await s.commit()
    summary["cognition"] = await _cognition(user_id, now)
    # the dashboard "holding" pulse = active watches + pending cards + active open loops
    summary["holding"] = summary["watches"] + 0 + summary["commitments"]
    summary["lifetime_metrics"] = {"days_with_donna": 247, "things_caught": 1847, "delivered_on_time_pct": 94}
    return summary


def main() -> None:
    s = asyncio.run(seed())
    log.info("seeded user=%s @ %s", s["user_id"], s["now"])
    for k in ("goals", "contexts", "commitments", "watches", "calendar", "emails", "observations", "notifications"):
        log.info("  %-14s %s", k, s[k])
    log.info("  finance        %s", s["finance"])
    log.info("  cognition      %s", s["cognition"])
    log.info("  holding (dashboard pulse) = %s", s["holding"])
    log.info("  lifetime moat metrics = %s (presentation values)", s["lifetime_metrics"])
    log.info("done. proactive moments (M2/M3/M4/M7/M8) fire on cue via their real triggers; pings are cleared so nothing is held.")


if __name__ == "__main__":
    main()
