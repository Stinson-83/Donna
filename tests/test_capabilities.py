"""The Capability Layer — Phase 0 (docs_v2/BROWSER_CAPABILITY_ARCHITECTURE.md).

Two guarantees:
1. CONSISTENCY — the capability registry stays pinned to the live tool/executor
   catalog, so it cannot silently drift (the same discipline as test_tool_allowlist).
2. ROUTER — the deterministic provider-resolution rules hold (prefer API over
   browser, consent gating, ambiguity only when consequential).

Pure import test — no API key, no DB.
"""
from __future__ import annotations

from backend.cards.executors import EXECUTORS
from donna_runtime.capabilities import (
    CAPABILITY_GUIDE,
    CAPABILITY_TOOLS,
    INTERNAL_EXECUTORS,
    INTERNAL_TOOLS,
    PROVIDERS,
    Capability,
    Provider,
    ProviderKind,
    Status,
    capability_of,
    resolve,
)
from donna_runtime.tools import DONNA_TOOLS

CATALOG = {t.name for t in DONNA_TOOLS}


# ── consistency: the registry mirrors reality ────────────────────────────────

def test_capability_map_partitions_the_live_catalog():
    assert CAPABILITY_TOOLS <= CATALOG                       # every tagged tool is real
    assert CAPABILITY_TOOLS.isdisjoint(INTERNAL_TOOLS)
    assert CAPABILITY_TOOLS | INTERNAL_TOOLS == CATALOG      # exact partition, nothing dropped


def test_planned_tools_are_not_yet_in_the_catalog():
    planned = {t for p in PROVIDERS if p.status is Status.PLANNED for t in p.tools}
    assert planned == {"browser_task", "browser_watch"}      # Kimi's tools, declared not built
    assert planned.isdisjoint(CATALOG)


def test_registered_executors_exist_and_are_fully_covered():
    live = {e for p in PROVIDERS if p.status is not Status.PLANNED for e in p.executors}
    assert live <= set(EXECUTORS)                            # every tagged executor is real
    assert set(EXECUTORS) == live | INTERNAL_EXECUTORS       # exact partition (incl. context taps)


def test_guide_covers_every_capability():
    assert set(CAPABILITY_GUIDE) == set(Capability)


# ── the Exa guarantee: Information Retrieval is NOT replaced by Browser ───────

def test_information_retrieval_stays_exa_and_is_distinct_from_browser():
    for t in ("web_search", "agentic_web_search", "research"):
        assert capability_of(t) is Capability.INFORMATION_RETRIEVAL
    # browser tools are PLANNED -> absent from the live index -> can't shadow Exa
    assert capability_of("browser_task") is None
    guide = CAPABILITY_GUIDE[Capability.BROWSER_INTERACTION]["avoid_when"]
    assert "Exa" in guide and "rail of last resort" in guide


# ── router: consent gating ───────────────────────────────────────────────────

def test_router_needs_consent_then_binds_when_connected():
    r = resolve(Capability.COMMUNICATION)                    # gmail not connected
    assert r.status == "needs_consent"
    assert {p.name for p in r.needs_consent} == {"composio_gmail"}

    r2 = resolve(Capability.COMMUNICATION, connected={"composio_gmail"})
    assert r2.status == "bound" and r2.provider.name == "composio_gmail"


def test_router_browser_interaction_unavailable_in_phase_0():
    # Kimi is PLANNED (not built) -> not "blocked on consent", simply unavailable.
    assert resolve(Capability.BROWSER_INTERACTION).status == "unavailable"


def test_router_binds_single_provider():
    r = resolve(Capability.SCHEDULING, connected={"composio_calendar"})
    assert r.status == "bound" and r.provider.name == "composio_calendar"


# ── router: prefer a real API over driving a browser ─────────────────────────

def test_router_prefers_api_over_browser_fallback():
    reg = (
        Provider("api_ride", Capability.TRANSPORTATION, ProviderKind.API, reliability=0.9),
        Provider("kimi", Capability.BROWSER_INTERACTION, ProviderKind.BROWSER,
                 fallback_for=(Capability.TRANSPORTATION,)),
    )
    r = resolve(Capability.TRANSPORTATION, registry=reg)
    assert r.status == "bound" and r.provider.name == "api_ride"


def test_router_falls_back_to_browser_when_no_api():
    reg = (
        Provider("kimi", Capability.BROWSER_INTERACTION, ProviderKind.BROWSER,
                 fallback_for=(Capability.TRANSPORTATION,)),
    )
    r = resolve(Capability.TRANSPORTATION, registry=reg)
    assert r.status == "bound" and r.provider.name == "kimi"


# ── router: ambiguity only when consequential AND a genuine tie ──────────────

def test_router_surfaces_options_only_on_consequential_tie():
    reg = (
        Provider("a", Capability.TRANSPORTATION, ProviderKind.API, reliability=0.9),
        Provider("b", Capability.TRANSPORTATION, ProviderKind.API, reliability=0.9),
    )
    tie = resolve(Capability.TRANSPORTATION, registry=reg, consequential=True)
    assert tie.status == "ambiguous" and {p.name for p in tie.options} == {"a", "b"}

    # a learned preference breaks the tie -> bind, no question
    pref = resolve(Capability.TRANSPORTATION, registry=reg, consequential=True, preferences={"a": 1.0})
    assert pref.status == "bound" and pref.provider.name == "a"

    # non-consequential -> bind the top silently even on a tie
    assert resolve(Capability.TRANSPORTATION, registry=reg).status == "bound"
