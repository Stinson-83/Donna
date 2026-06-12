"""Scenario runner — drive the demo from demo_scenarios.yaml, shot by shot.

For each shot it: prints the operator cue (time · screen · narrator · donna line ·
user action), STAGES the surface (records the notification + persists the card),
SIMULATES the user action (a tap resolves the card — running the real sandboxed
executor for execute-kinds), records Donna's confirming reply, and VERIFIES the
`expected` block. So the demo becomes an executable storyboard over the seeded DB.

Modes:
  scripted (default) — settle cards directly + run the safe (sandboxed) executors.
                       No LLM, no OAuth. The rehearsal/CI path.
  live               — route through the real proactive triggers + resolve_card_action
                       (needs the full stack: API key, integrations).

Run:
  python demo_run.py --seed                 # seed Mira, then play all 23 shots (fast)
  python demo_run.py --step                 # pause for <enter> between shots
  python demo_run.py --realtime             # honor each shot's duration
  python demo_run.py --only shot_6          # one shot
  python demo_run.py --mode live --seed     # the real stack
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("demo_run")

C = {"hdr": "\033[1m", "ok": "\033[32m", "bad": "\033[31m", "vo": "\033[36m", "dim": "\033[2m", "end": "\033[0m"} \
    if os.environ.get("NO_COLOR") is None else {k: "" for k in ("hdr", "ok", "bad", "vo", "dim", "end")}


def load_scenarios(path: str = "demo_scenarios.yaml") -> tuple[str, list[tuple[str, dict]]]:
    import yaml

    with open(path) as f:
        doc = yaml.safe_load(f)
    user = doc.get("user", "demo-mira")
    shots = doc.get("shots", {})
    ordered = sorted(shots.items(), key=lambda kv: int(kv[0].split("_")[1]))
    return user, ordered


# ── backend helpers (lazy session import so the test fixture is honored) ─────
def _build_card(user_id: str, spec: dict):
    from db.models import Card

    h = spec.get("header") or {}
    blocks = [{"type": "header", "label": h.get("label"), "ref": h.get("ref")}]
    if spec.get("body"):
        blocks.append({"type": "body", "text": spec["body"]})
    actions = spec.get("actions") or []
    if actions:
        blocks.append({"type": "actions", "actions": [{"label": a["label"], "action_id": a["id"]} for a in actions]})
    payload = {"version": 1, "card_id": spec["id"], "intent": spec["intent"], "theme": "dark", "blocks": blocks}
    action_map = {}
    for a in actions:
        m = {"kind": a["kind"]}
        for k in ("tool", "args", "prompt", "provider"):
            if a.get(k) is not None:
                m[k] = a[k]
        action_map[a["id"]] = m
    return Card(id=spec["id"], user_id=user_id, intent=spec["intent"], payload=payload, action_map=action_map, state="pending")


async def _persist_card(user_id: str, spec: dict) -> None:
    from sqlalchemy import select

    from db.models import Card
    from db.session import async_session

    async with async_session() as s:
        exists = (await s.execute(select(Card.id).where(Card.id == spec["id"]))).scalar_one_or_none()
        if exists is None:
            s.add(_build_card(user_id, spec))
            await s.commit()


async def _record_msg(user_id: str, role: str, text: str, proactive: bool) -> None:
    from db.models import ChatMessage
    from db.session import async_session

    async with async_session() as s:
        s.add(ChatMessage(user_id=user_id, role=role, content=text, is_proactive=proactive))
        await s.commit()


async def _get_card(card_id: str):
    from sqlalchemy import select

    from db.models import Card
    from db.session import async_session

    async with async_session() as s:
        return (await s.execute(select(Card).where(Card.id == card_id))).scalar_one_or_none()


async def _settle(card_id: str, action_id: str, state: str) -> None:
    from db.models import Card, utcnow
    from db.session import async_session

    async with async_session() as s:
        c = await s.get(Card, card_id)
        if c is not None and c.state == "pending":
            c.state = state
            c.acted_action_id = action_id
            c.acted_surface = "app"
            c.acted_at = utcnow()
            await s.commit()


async def _holding(user_id: str) -> int:
    from sqlalchemy import func, select

    from db.models import Card, OpenLoop, Watch
    from db.session import async_session

    async with async_session() as s:
        w = (await s.execute(select(func.count(Watch.id)).where(Watch.user_id == user_id, Watch.status == "active"))).scalar_one()
        c = (await s.execute(select(func.count(Card.id)).where(Card.user_id == user_id, Card.state == "pending"))).scalar_one()
        loop = (await s.execute(select(func.count(OpenLoop.id)).where(OpenLoop.user_id == user_id, OpenLoop.status == "active"))).scalar_one()
    return int(w) + int(c) + int(loop)


# ── tap resolution ───────────────────────────────────────────────────────────
async def _tap(user_id: str, card_id: str, action_id: str, mode: str) -> str:
    if mode == "live":
        from backend.cards.resolution import resolve_card_action

        res = await resolve_card_action(user_id, f"{card_id}:{action_id}", surface="app")
        return res.status

    card = await _get_card(card_id)
    spec = (card.action_map or {}).get(action_id, {}) if card else {}
    kind = (spec.get("kind") or "").lower()
    # run the real sandboxed executor for an execute-kind that has one (transfer ->
    # ledger, book_* -> calendar). cancel_subscription has no executor -> scripted.
    if kind == "execute" and spec.get("tool"):
        try:
            from backend.cards.executors import EXECUTORS

            ex = EXECUTORS.get(spec["tool"])
            if ex is not None:
                await ex(user_id, spec.get("args") or {})
        except Exception as e:
            log.debug("executor %s soft-failed (sandbox): %s", spec.get("tool"), e)
    settled = "dismissed" if kind in ("dismiss", "snooze") else "acted"
    await _settle(card_id, action_id, settled)
    return "handled"


# ── one shot ─────────────────────────────────────────────────────────────────
async def run_shot(user_id: str, sid: str, shot: dict, ctx: dict, mode: str) -> tuple[bool, list]:
    donna = shot.get("donna") or {}
    ua = shot.get("user_action") or {}

    # 1. cue
    at = shot.get("at") or ""
    print(f"\n{C['hdr']}▸ {sid} · {shot.get('title','')}{C['end']}  {C['dim']}{at} · {shot.get('screen','')}{C['end']}")
    if shot.get("vo"):
        print(f"  {C['vo']}VO  {shot['vo']}{C['end']}")

    # 2. stage Donna's opening (notification + card), shown before the user acts
    note = (donna.get("notification") or {}).get("text")
    if note:
        await _record_msg(user_id, "donna", note, proactive=True)
        ctx["last_donna"] = note
        print(f"  donna  {note}")
    if donna.get("card"):
        await _persist_card(user_id, donna["card"])
        ctx["last_card"] = donna["card"]["id"]
        print(f"  card   [{donna['card']['intent']}] {donna['card'].get('header',{}).get('ref','')}")

    # 3. user action — text is recorded; a `target` resolves a card action (a tap,
    # or a voice/typed confirmation of a single-action card like "yeah").
    if ua.get("text"):
        await _record_msg(user_id, "user", ua["text"], proactive=False)
        print(f"  user   \"{ua['text']}\"")
    if ua.get("target"):
        status = await _tap(user_id, ctx.get("last_card"), ua["target"], mode)
        print(f"  user   {ua.get('type', 'tap')} [{ua['target']}] -> {status}")
    elif ua.get("type") in ("scroll", "longpress"):
        print(f"  user   {ua['type']}")

    # 4. Donna's confirming reply (after the action)
    if donna.get("reply"):
        await _record_msg(user_id, "donna", donna["reply"], proactive=False)
        ctx["last_donna"] = donna["reply"]
        print(f"  donna  {donna['reply']}")

    # 5. verify
    ok, checks = await _verify(user_id, shot, ctx)
    for label, passed in checks:
        mark = f"{C['ok']}✓{C['end']}" if passed else f"{C['bad']}✗{C['end']}"
        print(f"  {mark} {label}")
    return ok, checks


async def _verify(user_id: str, shot: dict, ctx: dict) -> tuple[bool, list]:
    exp = shot.get("expected") or {}
    checks: list[tuple[str, bool]] = []
    if "notification" in exp:
        want = exp["notification"]["text"].lower()
        checks.append((f'donna says ~ "{exp["notification"]["text"]}"', want in (ctx.get("last_donna") or "").lower()))
    if "card" in exp and ctx.get("last_card"):
        card = await _get_card(ctx["last_card"])
        checks.append((f'card intent = {exp["card"]["intent"]}', bool(card) and card.intent == exp["card"]["intent"]))
    if "state" in exp and ctx.get("last_card"):
        card = await _get_card(ctx["last_card"])
        checks.append((f'card state = {exp["state"]}', bool(card) and card.state == exp["state"]))
    if "holding" in exp:
        h = await _holding(user_id)
        checks.append((f'holding = {exp["holding"]} (got {h})', h == exp["holding"]))
    if "screen" in exp:
        checks.append((f'open screen: {exp["screen"]}', True))  # operator cue
    return all(p for _, p in checks) if checks else True, checks


# ── orchestrator ─────────────────────────────────────────────────────────────
async def run(path: str = "demo_scenarios.yaml", *, mode: str = "scripted", step: bool = False,
              realtime: bool = False, only: str | None = None, seed: bool = False) -> dict:
    if seed:
        import demo_seed

        log.info("seeding demo state...")
        await demo_seed.seed(user_id="demo-mira")

    user_id, shots = load_scenarios(path)
    ctx: dict = {}
    passed = failed = 0
    for sid, shot in shots:
        if only and sid != only:
            continue
        ok, _ = await run_shot(user_id, sid, shot, ctx, mode)
        passed += ok
        failed += (not ok)
        if step:
            input(f"  {C['dim']}[enter] for next shot{C['end']}")
        elif realtime:
            await asyncio.sleep(shot.get("duration_s", 0))
    print(f"\n{C['hdr']}done · {passed} shots verified · {failed} with mismatches{C['end']}")
    return {"passed": passed, "failed": failed}


def main() -> None:
    ap = argparse.ArgumentParser(description="Donna demo scenario runner")
    ap.add_argument("--scenarios", default="demo_scenarios.yaml")
    ap.add_argument("--mode", choices=["scripted", "live"], default="scripted")
    ap.add_argument("--seed", action="store_true", help="seed the demo state first")
    ap.add_argument("--step", action="store_true", help="pause for <enter> between shots")
    ap.add_argument("--realtime", action="store_true", help="honor each shot's duration")
    ap.add_argument("--only", help="run a single shot, e.g. shot_6")
    args = ap.parse_args()
    asyncio.run(run(args.scenarios, mode=args.mode, step=args.step, realtime=args.realtime, only=args.only, seed=args.seed))


if __name__ == "__main__":
    main()
