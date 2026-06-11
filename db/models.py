import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(type_, compiler, **kw):  # type: ignore[no-untyped-def]
    """Let the Postgres JSONB columns create on SQLite (offline/local dev).
    SQLite stores them as JSON text; behavior is identical for our usage."""
    return "JSON"


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    phone: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    profession: Mapped[str | None] = mapped_column(String, nullable=True)
    timezone: Mapped[str] = mapped_column(String, default="Asia/Singapore")
    wake_time: Mapped[str | None] = mapped_column(String, nullable=True)
    sleep_time: Mapped[str | None] = mapped_column(String, nullable=True)
    conversation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_goals: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"tz_done": False, "watch_done": False},
    )
    onboarding_node: Mapped[str | None] = mapped_column(String, nullable=True)  # current playbook node_id
    facts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    living_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    voice_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_model_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    has_google: Mapped[bool] = mapped_column(Boolean, default=False)
    has_github: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    notify_channel: Mapped[str] = mapped_column(String, nullable=False, default="auto")  # auto | app | whatsapp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    wa_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_proactive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DeviceToken(Base):
    """A push target for one of a user's devices (FCM/APNs registration token).

    One user can have many devices. Keyed on the resolved User.id (UUID) so the
    proactive path — which works in UUIDs — can find where to ping. Tokens are
    upserted on every app launch and pruned when FCM reports them unregistered."""
    __tablename__ = "device_tokens"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String, default="android")  # android | ios | web
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ProceduralRule(Base):
    __tablename__ = "procedural_rules"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Observation(Base):
    """Single tracking table for all countable/measurable user events.

    event_time = when it happened (may differ from created_at)
    tags       = indexed metadata {meal_type: lunch, source: whatsapp}
    fields     = measured values {item: mee pok, calories: 520}
    enriched   = async-populated {protein_g: 18, nutrition_source: usda}
    lineage    = ["whatsapp_capture", "nlp_extraction", "nutrition_api"]

    Types: meal | expense | mood | habit | weight | sleep | exercise | academic | task | custom
    """
    __tablename__ = "observations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    instance_id: Mapped[str] = mapped_column(String, ForeignKey("donna_instances.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    enriched: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String, default="whatsapp")
    lineage: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_obs_user_type_time", "user_id", "type", "event_time"),
        Index("idx_obs_user_time", "user_id", "event_time"),
        Index("idx_obs_user_instance", "user_id", "instance_id"),
    )


class SchemaRegistry(Base):
    """Census of what observation types exist per user. Perceive reads this as structured_state."""
    __tablename__ = "schema_registry"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    schema_name: Mapped[str] = mapped_column(String, nullable=False)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    auto_created: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OpenLoop(Base):
    """Unresolved threads from past conversations."""
    __tablename__ = "open_loops"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String, default="active")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Fact(Base):
    """Bi-temporal facts about the user or their entities.

    Two time axes:
      t_valid_*    — when the fact was true in the real world
      t_recorded_* — when we learned / stopped believing the fact

    A "current belief" row has t_valid_to = NULL and t_recorded_to = NULL.
    Superseded rows close out their t_recorded_to and set superseded_by.
    To correct a historical fact, close t_valid_to and insert a new row
    with the corrected t_valid_from.
    """

    __tablename__ = "facts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    predicate: Mapped[str] = mapped_column(String, nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    object_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String, default="chat", nullable=False)
    t_valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    t_valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    t_recorded_from: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    t_recorded_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("facts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_facts_user_subj_pred", "user_id", "subject", "predicate"),
        Index("idx_facts_user_valid_from", "user_id", "t_valid_from"),
        Index("idx_facts_user_recorded_from", "user_id", "t_recorded_from"),
    )


class CalendarEntry(Base):
    """Synced calendar events from Google Calendar (via Composio)."""
    __tablename__ = "calendar_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    google_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_cal_user_start", "user_id", "start_time"),
    )


class Document(Base):
    """Tracks documents uploaded via WhatsApp. Extracted text is stored in extracted_text;
    a short summary episode is ingested into Graphiti for proactive recall."""
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    supermemory_doc_id: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String, default="whatsapp")
    processing_status: Mapped[str] = mapped_column(String, default="processing")  # processing | ready | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_docs_user_created", "user_id", "created_at"),
        Index("idx_docs_user_status", "user_id", "processing_status"),
    )


class DonnaSchedule(Base):
    """Scheduled message to fire at a specific time.

    origin: "user" = user explicitly asked ("remind me at 5pm")
            "donna" = Donna proactively scheduled (good luck before interview, etc.)

    If origin=user and the schedule fires late (server was down), the compose
    directive should include an apology. If origin=donna, just skip silently.
    """
    __tablename__ = "donna_schedule"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    fire_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    origin: Mapped[str] = mapped_column(String, nullable=False, default="donna")  # "user" | "donna"
    recurrence: Mapped[str | None] = mapped_column(String, nullable=True)  # None=one-shot, "daily", "weekdays", "weekly"
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)  # pending | running | done | failed | skipped
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_schedule_fire", "fire_at", "fired"),
        Index("idx_schedule_status_fire", "status", "fire_at"),
    )


class DonnaInstance(Base):
    """A real feature Donna is running for a specific user.

    Combines a primitive (verb) + connector (sense) + user-specific config
    into a living feature with its own lifecycle.

    Examples:
        Track(meals) via whatsapp_manual — config: {type: "meal"}
        Watch(aura PRs) via github — config: {repo: "anthropics/aura"}
        Schedule(vitamins) via whatsapp_manual — config: {recurrence: "daily"}
    """
    __tablename__ = "donna_instances"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    primitive: Mapped[str] = mapped_column(String, nullable=False)      # track, schedule, watch, remember, compose
    connector: Mapped[str] = mapped_column(String, nullable=False)      # whatsapp_manual, google_calendar, github, weather
    label: Mapped[str] = mapped_column(String, nullable=False)          # user-facing: "meals", "morning briefing", "coffees"
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # primitive-specific (legacy)
    spec: Mapped[dict | None] = mapped_column(JSONB, nullable=True)      # full InstanceSpec JSON (new shape; dispatcher uses this)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active, paused, offered, declined
    offered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger_last_fire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger_last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger_locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger_locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    trigger_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_inst_user_status", "user_id", "status"),
        Index("idx_inst_user_primitive", "user_id", "primitive"),
        Index("idx_inst_status_trigger_lock", "status", "trigger_locked_at"),
    )


class RunTrace(Base):
    """Persistent record of a perceive/act turn or a spec fire.

    kind='turn'      → perceive + triage + act for one inbound message
    kind='spec_fire' → a single Runner.fire invocation

    payload shape is defined in the plan (Phase 1.3 / 1.4).
    """
    __tablename__ = "run_traces"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)               # 'turn' | 'spec_fire'
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)  # turn_id or instance_id
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    # 'running' | 'ok' | 'error' | 'skipped' | 'orphaned'
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)       # one-liner for list view
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_traces_user_started", "user_id", "started_at"),
        Index("idx_traces_user_kind_started", "user_id", "kind", "started_at"),
    )


class OAuthToken(Base):
    """Stores OAuth tokens for third-party integrations (Google, etc.)."""
    __tablename__ = "oauth_tokens"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)   # "google", "microsoft", etc.
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_oauth_user_provider", "user_id", "provider", unique=True),
    )


class InboundMessage(Base):
    """Durable inbox for WhatsApp inbound messages.

    Every parsed inbound message is persisted before dispatch so a crashed
    or redeployed replica can replay unprocessed rows on startup. Status
    transitions: queued → processed (success) | failed (non-cancel exception).
    Cancelled pipelines leave rows as 'queued' so the restart picks them up.

    body stores the minimal WA envelope needed to re-parse on replay:
        {"message": <raw message dict>, "value": <raw value dict>}
    """
    __tablename__ = "inbound_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    phone: Mapped[str] = mapped_column(String, nullable=False, index=True)
    wa_message_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    body: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_inbound_status_phone_received", "status", "phone", "received_at"),
    )


class UserSession(Base):
    """Maps Donna user_id → most-recent Claude Agent SDK session_id.

    The SDK carries conversation history on its side keyed by session_id;
    resuming a session reinstates the full transcript so the brain sees prior
    turns without stuffing them into the prompt. This table is the durable,
    cross-replica replacement for the old local JSON file.
    """
    __tablename__ = "user_sessions"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ImageToolEvent(Base):
    """One row per image-tool invocation outcome — drives caps + observability.

    status values: sent | denied_cooldown | denied_cap | failed_provider | failed_safety
    """
    __tablename__ = "image_tool_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("idx_image_events_user_created", "user_id", "created_at"),
    )


class Integration(Base):
    """Per-user, per-product integration state. Source of truth for the
    [INTEGRATIONS] context block; populated by Composio webhook flow."""
    __tablename__ = "integrations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    product: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    composio_connection_id: Mapped[str | None] = mapped_column(String, nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        Index(
            "uq_integrations_user_provider_product",
            "user_id", "provider", "product",
            unique=True,
        ),
    )


class EmailMessage(Base):
    """Local mirror of Gmail messages. Body stored only when label-router
    classified the message as 'full'. Bodies for 'metadata' rows are lazy-
    fetched on demand via read_gmail_thread."""
    __tablename__ = "email_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    gmail_message_id: Mapped[str] = mapped_column(String, nullable=False)
    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    from_address: Mapped[str] = mapped_column(String, nullable=False)
    from_name: Mapped[str | None] = mapped_column(String, nullable=True)
    to_addresses: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    cc_addresses: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_stored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    labels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_important: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ingest_depth: Mapped[str] = mapped_column(String, nullable=False)
    internal_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index(
            "uq_email_user_msg",
            "user_id", "gmail_message_id",
            unique=True,
        ),
        Index("idx_emails_user_date", "user_id", "internal_date"),
        Index("idx_emails_user_thread", "user_id", "thread_id"),
        Index(
            "idx_emails_user_important",
            "user_id", "is_important",
            postgresql_where=sa.text("is_important"),
        ),
    )


class ProactivePing(Base):
    """One row per proactive ping fired. Drives rate limiting + cooldowns.

    source values: 'email' | (future) 'open_loop_age' | 'world_delta' | ...
    suppressed_reason is null when actually fired; set when this row recorded
    a suppression decision instead.
    """
    __tablename__ = "proactive_pings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    message_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    fired_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    suppressed_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("idx_pings_user_fired", "user_id", "fired_at"),
    )


class Card(Base):
    """Persistence wrapper around a DonnaCard payload (donna-design-spec).

    payload    = the validated DonnaCard (version, intent, theme, blocks[]) sent
                 to every surface. Owned by donna-design-spec/schema/card.schema.json.
    action_map = SERVER-ONLY: action_id -> {kind, tool, args, tier}. Never sent to
                 the client; the wire only carries opaque action_ids.
    state      = drives DonnaCard.theme (pending -> dark/light; acted/expired/
                 dismissed -> settled). See donna-design-spec/INTEGRATION.md.
    id         = the DonnaCard.card_id (stable across surfaces so a tap on any
                 surface resolves the same card).
    """
    __tablename__ = "cards"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    intent: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action_map: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    # pending | acted | dismissed | expired | superseded
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acted_action_id: Mapped[str | None] = mapped_column(String, nullable=True)
    acted_surface: Mapped[str | None] = mapped_column(String, nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    card_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_cards_user_state", "user_id", "state"),
        Index("idx_cards_user_created", "user_id", "created_at"),
    )


class FinanceAccount(Base):
    """A user's bank/card account — Donna's CACHED model of it, synced from a
    finance integration. `balance` is a cached fact the proactive runner diffs
    against upcoming bills; it is not a real ledger. Money is Float for the
    sandbox (production should use integer minor units)."""
    __tablename__ = "finance_accounts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    account_type: Mapped[str] = mapped_column(String, nullable=False)  # current | savings | credit_card
    institution: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. HDFC
    masked_number: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    balance_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_finacct_user_type", "user_id", "account_type"),
    )


class Bill(Base):
    """An upcoming/recurring payment Donna watches. auto_pay bills near their
    due_date drive the low_balance_vs_bill check (proactive_runner §5)."""
    __tablename__ = "bills"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    account_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("finance_accounts.id"), nullable=True
    )  # the account it auto-debits from
    biller: Mapped[str] = mapped_column(String, nullable=False)  # e.g. AWS
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    auto_pay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="upcoming")  # upcoming | paid | overdue
    source: Mapped[str] = mapped_column(String, default="manual")
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_bills_user_due", "user_id", "due_date"),
        Index("idx_bills_user_status", "user_id", "status"),
    )


class FinanceTransaction(Base):
    """A movement on an account. The transfer executor writes these in the
    sandbox; in production they would sync from the bank."""
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String, ForeignKey("finance_accounts.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    direction: Mapped[str] = mapped_column(String, nullable=False)  # debit | credit
    merchant: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_txn_user_occurred", "user_id", "occurred_at"),
        Index("idx_txn_account", "account_id"),
    )


class Watch(Base):
    """A standing situation Donna monitors for the user (proactive_runner.md).

    Evaluated only when due (next_check <= now), with an adaptive cadence
    (compute_next_check). Each watch_type has an evaluator that does a cheap
    deterministic diff against last_known_state and only surfaces (wakes the
    BRAIN loop) on a material change. This is what backs the dashboard's
    'watching' list and makes 'keep an eye on X' actually function.
    """
    __tablename__ = "watches"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    watch_type: Mapped[str] = mapped_column(String, nullable=False)   # reply | bill | generic | ...
    subject_key: Mapped[str] = mapped_column(String, nullable=False)  # who/what (sender, bill id, topic)
    title: Mapped[str] = mapped_column(String, nullable=False)        # human label for the watching list
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active | fired | retired
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_check: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_known_state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    stable_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("uq_watch_user_type_subject", "user_id", "watch_type", "subject_key", unique=True),
        Index("idx_watch_status_next", "status", "next_check"),
        Index("idx_watch_user_status", "user_id", "status"),
    )


class Goal(Base):
    """What the user is trying to achieve — a first-class part of the User Model
    (user_model.md Layer 1). Goals give meaning: the loop prioritizes events,
    notifications, and actions against active goals. Learned from explicit
    statements ('i want to raise funding') or inferred from behavior."""
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False, default="personal")
    # career | health | relationships | financial | personal | other
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1 = highest
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    # active | achieved | paused | dropped
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    source: Mapped[str] = mapped_column(String, nullable=False, default="chat")  # chat | inferred | onboarding
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_goals_user_status", "user_id", "status"),
    )
