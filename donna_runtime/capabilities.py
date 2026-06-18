"""The Capability Layer — Phase 0 (scaffolding).

Spec: docs_v2/BROWSER_CAPABILITY_ARCHITECTURE.md.

A *capability* is a deterministic abstraction above tools. Donna's BRAIN loop
reasons about WHICH CAPABILITY it needs (folded into its normal tool choice — not
a new LLM call); this module resolves WHICH PROVIDER serves it (consent,
preference, availability, prefer-API-over-browser). That is metadata + a pure
router — the same species as the deterministic event_type→workflow Router. It adds
ZERO reasoning sites.

Phase 0 is pure scaffolding: NOTHING dispatches through this yet, so there is ZERO
behavior change. The live @tool descriptions and the loop's tool dispatch are
untouched. This is the structure Phase 1+ (Kimi WebBridge) plugs into, plus a
consistency test that pins the registry to the real tool/executor catalog so it
cannot silently drift.

Binding rules carried from the doc:
- Information Retrieval (Exa) is NOT replaced by Browser Interaction. They are
  distinct capabilities with a deterministic boundary (see CAPABILITY_GUIDE).
- A real API provider always beats driving a browser (`resolve` prefers non-BROWSER).
- No credential/secret ever appears here — a provider declares a consent
  *requirement*, never a credential.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

__all__ = [
    "Capability", "ProviderKind", "Status", "Provider", "Resolution",
    "PROVIDERS", "CAPABILITY_TOOLS", "INTERNAL_TOOLS", "INTERNAL_EXECUTORS",
    "CAPABILITY_GUIDE", "providers_for", "resolve", "capability_of",
    "tools_by_capability",
]


# ── taxonomy ──────────────────────────────────────────────────────────────────

class Capability(str, Enum):
    """The ten capability categories (doc §4). Two are *modalities* of reaching the
    world (how), seven are *domains* (what), and one is the *commit rail*."""
    INFORMATION_RETRIEVAL = "information_retrieval"   # modality: read the open web / memory
    BROWSER_INTERACTION = "browser_interaction"       # modality: operate a logged-in site
    COMMUNICATION = "communication"
    SCHEDULING = "scheduling"
    TRANSPORTATION = "transportation"
    TRAVEL = "travel"
    FINANCE = "finance"
    DOCUMENT_HANDLING = "document_handling"
    FILE_MANAGEMENT = "file_management"
    ACTION_EXECUTION = "action_execution"             # the commit rail (executors + gate)


class ProviderKind(str, Enum):
    RETRIEVAL = "retrieval"   # read-only knowledge (web or memory)
    API = "api"               # a real API integration — PREFERRED over a browser
    BROWSER = "browser"       # browser automation — the fallback rail of last resort
    INTERNAL = "internal"     # a Donna-internal mechanic surfaced as a tool
    EXECUTION = "execution"   # the commit rail itself (executor registry + L0/L1/L2 gate)


class Status(str, Enum):
    LIVE = "live"             # built and connectable today
    SANDBOX = "sandbox"       # engine is real, the third-party rail is stubbed
    PLANNED = "planned"       # declared, not built yet (e.g. Kimi's tools)


@dataclass(frozen=True)
class Provider:
    """One way to serve a capability. `tools` are loop-callable tool names; `executors`
    are card-tap executor names. `fallback_for` lists domain capabilities this provider
    can back when no API provider is connected (the browser-as-last-resort rail)."""
    name: str
    capability: Capability
    kind: ProviderKind
    status: Status = Status.LIVE
    tools: tuple[str, ...] = ()
    executors: tuple[str, ...] = ()
    requires_consent: bool = False
    consent_kind: str | None = None        # "oauth" | "per_portal_credential"
    default_agency: str = "L2"             # baseline tier; the gate refines per-action
    cost: str = "low"                      # low | medium | high
    reliability: float = 0.9               # 0..1 prior, the router's last tie-break
    fallback_for: tuple[Capability, ...] = ()


# ── the registry (deterministic state — one row per provider) ────────────────
#
# Phase 0 declares every provider that exists in the codebase today, tagged
# accurately, plus Kimi WebBridge as PLANNED so the router's prefer-API / fallback
# / needs-consent paths are real and tested. Tool/executor names are validated
# against the live catalog by test_capabilities.

PROVIDERS: tuple[Provider, ...] = (
    # 1 · Information Retrieval — TWO providers, neither replaces the other.
    Provider("exa", Capability.INFORMATION_RETRIEVAL, ProviderKind.RETRIEVAL,
             tools=("web_search", "agentic_web_search", "research"),
             cost="low", reliability=0.85),
    Provider("memory_recall", Capability.INFORMATION_RETRIEVAL, ProviderKind.RETRIEVAL,
             tools=("recall", "recall_about", "read_connections"),
             cost="low", reliability=0.9),

    # 2 · Browser Interaction — Kimi WebBridge, the primary (and only) provider.
    #     PLANNED in Phase 0; also the browser fallback rail for the domains below.
    Provider("kimi_webbridge", Capability.BROWSER_INTERACTION, ProviderKind.BROWSER,
             status=Status.PLANNED,
             tools=("browser_task", "browser_watch"),
             requires_consent=True, consent_kind="per_portal_credential",
             default_agency="L1", cost="high", reliability=0.7,
             fallback_for=(
                 Capability.COMMUNICATION, Capability.SCHEDULING, Capability.TRANSPORTATION,
                 Capability.TRAVEL, Capability.FINANCE, Capability.DOCUMENT_HANDLING,
                 Capability.FILE_MANAGEMENT,
             )),

    # 3 · Communication — Gmail via Composio (read tools + send executor).
    Provider("composio_gmail", Capability.COMMUNICATION, ProviderKind.API,
             tools=("list_gmail_recent", "read_gmail_thread"),
             executors=("send_email",),
             requires_consent=True, consent_kind="oauth",
             default_agency="L1", cost="low", reliability=0.95),

    # 4 · Scheduling — Google Calendar via Composio (read + create tools; bookings ride on it).
    Provider("composio_calendar", Capability.SCHEDULING, ProviderKind.API,
             tools=("check_calendar", "create_calendar_event"),
             requires_consent=True, consent_kind="oauth",
             default_agency="L2", cost="low", reliability=0.95),

    # 5 · Transportation — ride rail (engine real, third-party rail sandboxed).
    Provider("ride_rail", Capability.TRANSPORTATION, ProviderKind.API, status=Status.SANDBOX,
             executors=("book_ride",),
             requires_consent=True, consent_kind="oauth",
             default_agency="L0", cost="medium", reliability=0.8),

    # 6 · Travel — reservations rail (creates a real calendar event, reservation stubbed).
    Provider("reservations_rail", Capability.TRAVEL, ProviderKind.API, status=Status.SANDBOX,
             executors=("book_restaurant",),
             requires_consent=True, consent_kind="oauth",
             default_agency="L1", cost="low", reliability=0.85),

    # 7 · Finance — bank rail (ledger real, bank rail sandboxed).
    Provider("bank_rail", Capability.FINANCE, ProviderKind.API, status=Status.SANDBOX,
             executors=("transfer",),
             requires_consent=True, consent_kind="oauth",
             default_agency="L0", cost="low", reliability=0.9),

    # 10 · Action Execution — the commit rail: every world-write executor lands here
    #      through the L0/L1/L2 gate. Always present (it IS the gate), no consent of
    #      its own; the domain providers above say which executor does what.
    Provider("execution_gate", Capability.ACTION_EXECUTION, ProviderKind.EXECUTION,
             executors=("send_email", "transfer", "book_restaurant", "book_ride", "order_flowers"),
             requires_consent=False, default_agency="L2", cost="low", reliability=1.0),
)


# Loop tools that are Donna-internal mechanics (cognition/state/terminators), NOT a
# way of reaching the external world — intentionally outside the capability map. The
# consistency test asserts CAPABILITY_TOOLS ∪ INTERNAL_TOOLS == the live catalog.
INTERNAL_TOOLS: frozenset[str] = frozenset({
    "remember", "watch", "schedule", "track_goal", "track_interest", "set_focus",
    "track_task", "track_flight", "form_belief", "image", "send_burst", "render_card",
})

# Executors that are internal handlers (not world-commit actions): the Context-Layer
# confirmation taps. They are in EXECUTORS but belong to no capability.
INTERNAL_EXECUTORS: frozenset[str] = frozenset({"confirm_context", "decline_context"})


# Capability-framed guidance (the when-to-use / when-NOT text, doc §5). Phase 0 stores
# it here for a later phase to surface to the prompt; it is NOT injected anywhere now,
# so it changes no behavior. The Exa-vs-Browser boundary is the load-bearing entry.
CAPABILITY_GUIDE: dict[Capability, dict] = {
    Capability.INFORMATION_RETRIEVAL: {
        "summary": "Read what the open web publishes, or recall from memory. Stateless, read-only.",
        "use_when": "you need to KNOW something the public web already publishes, or recall stored knowledge.",
        "avoid_when": "the fact lives behind a login, or you need to ACT on a site — that is Browser Interaction.",
    },
    Capability.BROWSER_INTERACTION: {
        "summary": "Operate a specific logged-in site as the user (Kimi WebBridge): portal logins, "
                   "application tracking, navigation, form filling, multi-step browser workflows.",
        "use_when": "you must read a fact behind the user's login, or DO something inside a site that has no API.",
        "avoid_when": "the question is answerable from the open web (use Information Retrieval / Exa), or a "
                      "real API exists for the task (prefer the API — a browser is the rail of last resort).",
    },
    Capability.COMMUNICATION: {"summary": "Send/observe messages (Gmail; WhatsApp delivery)."},
    Capability.SCHEDULING: {"summary": "Read/write the calendar; reminders."},
    Capability.TRANSPORTATION: {"summary": "Book/track rides."},
    Capability.TRAVEL: {"summary": "Flights, reservations, trip logistics."},
    Capability.FINANCE: {"summary": "Balances, transfers, payments (gated, mostly L0)."},
    Capability.DOCUMENT_HANDLING: {"summary": "Read/generate documents and paperwork."},
    Capability.FILE_MANAGEMENT: {"summary": "Store/organize/retrieve files."},
    Capability.ACTION_EXECUTION: {"summary": "Commit a consequential action through the L0/L1/L2 gate."},
}


# ── derived indices ───────────────────────────────────────────────────────────

def _live(p: Provider) -> bool:
    return p.status is not Status.PLANNED


#: every loop tool that a (non-planned) provider surfaces — the external-world tools.
CAPABILITY_TOOLS: frozenset[str] = frozenset(
    t for p in PROVIDERS if _live(p) for t in p.tools
)


def tools_by_capability() -> dict[Capability, tuple[str, ...]]:
    """capability → its live loop tools (for future capability-framed prompt assembly)."""
    out: dict[Capability, list[str]] = {}
    for p in PROVIDERS:
        if _live(p) and p.tools:
            out.setdefault(p.capability, []).extend(p.tools)
    return {k: tuple(v) for k, v in out.items()}


def capability_of(tool_name: str) -> Capability | None:
    """The capability a live loop tool serves, or None (internal / planned / unknown)."""
    for p in PROVIDERS:
        if _live(p) and tool_name in p.tools:
            return p.capability
    return None


# ── the Router (pure function over the registry — no LLM, doc §7.2) ──────────

@dataclass(frozen=True)
class Resolution:
    capability: Capability
    status: str                                  # bound | ambiguous | needs_consent | unavailable
    provider: Provider | None = None             # set when status == "bound"
    options: tuple[Provider, ...] = ()           # set when status == "ambiguous"
    needs_consent: tuple[Provider, ...] = ()     # connectable providers blocked on consent


def providers_for(
    capability: Capability, *, registry: Sequence[Provider] = PROVIDERS
) -> tuple[Provider, ...]:
    """Every provider that can serve a capability: the direct providers plus any
    browser fallback declared for it."""
    direct = [p for p in registry if p.capability is capability]
    fallback = [p for p in registry if capability in p.fallback_for]
    return tuple(direct + fallback)


def _available(p: Provider, connected) -> bool:
    if p.status is Status.PLANNED:
        return False
    if p.requires_consent and p.name not in connected:
        return False
    return True


def resolve(
    capability: Capability,
    *,
    connected=frozenset(),
    preferences: dict[str, float] | None = None,
    consequential: bool = False,
    registry: Sequence[Provider] = PROVIDERS,
) -> Resolution:
    """Bind a capability to a provider, deterministically (doc §7.2):

    1. gather direct + browser-fallback providers
    2. drop those that are planned or lack consent (blocked-on-consent surfaced)
    3. PREFER a non-browser (API/retrieval) provider over the browser fallback
    4. one viable → bind; else rank by learned preference then reliability, and only
       surface an options card when the choice is consequential AND a genuine tie.
    """
    preferences = preferences or {}
    cands = providers_for(capability, registry=registry)
    available = [p for p in cands if _available(p, connected)]
    blocked = tuple(
        p for p in cands
        if p.status is not Status.PLANNED and p.requires_consent and p.name not in connected
    )
    if not available:
        return Resolution(capability, "needs_consent" if blocked else "unavailable",
                          needs_consent=blocked)

    # prefer-API: the browser is the rail of last resort
    non_browser = [p for p in available if p.kind is not ProviderKind.BROWSER]
    pool = non_browser or available

    if len(pool) == 1:
        return Resolution(capability, "bound", provider=pool[0], needs_consent=blocked)

    ranked = sorted(pool, key=lambda p: (preferences.get(p.name, 0.0), p.reliability), reverse=True)
    tie = preferences.get(ranked[0].name, 0.0) == preferences.get(ranked[1].name, 0.0)
    if consequential and tie:
        return Resolution(capability, "ambiguous", options=tuple(ranked), needs_consent=blocked)
    return Resolution(capability, "bound", provider=ranked[0], needs_consent=blocked)
