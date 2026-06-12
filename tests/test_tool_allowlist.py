"""The agent's allow-list must stay in exact sync with the registered tools.

A registered tool missing from ALLOWED_TOOLS is silently unreachable by the live
BRAIN loop (this is the bug that left render_card / track_* / recall_about
uncallable); a name in ALLOWED_TOOLS that isn't registered is dead config. Pure
import test — no API key, no DB.
"""
from __future__ import annotations

from donna_runtime.config import ALLOWED_TOOLS, TOOL_NAMESPACE
from donna_runtime.tools import DONNA_TOOLS


def test_allowlist_matches_registered_tools():
    registered = {f"mcp__{TOOL_NAMESPACE}__{t.name}" for t in DONNA_TOOLS}
    allowed = set(ALLOWED_TOOLS)
    assert allowed == registered, {
        "registered_but_not_allowed": sorted(registered - allowed),
        "allowed_but_not_registered": sorted(allowed - registered),
    }


def test_allowlist_has_no_duplicates():
    assert len(ALLOWED_TOOLS) == len(set(ALLOWED_TOOLS))


def test_both_terminators_are_callable():
    # send_burst (reply) and render_card (decision card) must both be reachable,
    # or the proactive "end with render_card" instructions can't be honored.
    for name in ("mcp__donna__send_burst", "mcp__donna__render_card"):
        assert name in ALLOWED_TOOLS
