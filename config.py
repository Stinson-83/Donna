from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = ""
    database_url_direct: str = ""
    supermemory_api_key: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    # No default: a deploy that forgets to set this fails webhook verification
    # closed rather than accepting a well-known public token.
    whatsapp_verify_token: str = ""
    # Meta App Secret — used to verify the X-Hub-Signature-256 HMAC on inbound
    # webhooks. When set, POST /webhook rejects any unsigned/mis-signed body.
    whatsapp_app_secret: str = ""
    relay_url: str = ""
    founder_phone: str = ""
    # Per-phone dev re-routing. When both are set, webhooks whose `from`
    # matches DEV_PHONE_NUMBERS (comma-separated, no `+`) are forwarded to
    # DEV_RELAY_URL while the rest still process on this instance. Lets a
    # single prod webhook URL serve both prod traffic and a developer's
    # local tunnel without flipping the Meta dashboard each session.
    dev_relay_url: str = ""
    dev_phone_numbers: str = ""

    # Audio: ElevenLabs TTS (outbound voice notes) + Deepgram STT (inbound).
    # When DONNA_VOICE_ENABLED is false the voice_response marker is stripped
    # and Donna falls back to text. Inbound voice notes still transcribe.
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "WAhoMTNdLdMoq1j3wf3I"
    elevenlabs_model_id: str = "eleven_flash_v2_5"
    elevenlabs_voice_speed: float = 1.2                 # 0.7 (slowest) – 1.2 (fastest); 1.0 = default
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"
    donna_voice_enabled: bool = True
    donna_voice_max_chars: int = 600                    # hard cap per turn (cost + WA voice-note ux)

    # Image generation (fal). When unset, the image tool degrades to text.
    fal_key: str = ""
    fal_image_model: str = "fal-ai/flux/schnell"

    # Composio: SDK-managed OAuth + webhook ingest for Google integrations.
    composio_api_key: str = ""
    composio_webhook_secret: str = ""

    # Push notifications (Firebase Cloud Messaging, HTTP v1). When unset, push
    # is a silent no-op. fcm_service_account_json is the service-account JSON
    # (inline string OR a path to the .json); project id defaults to its
    # project_id when fcm_project_id is blank.
    fcm_service_account_json: str = ""
    fcm_project_id: str = ""

    # Web-dashboard auth (the magic-link layer). AUTH_SECRET signs the magic +
    # session tokens; if unset, an ephemeral per-process dev secret is used (dev
    # only — tokens won't survive a restart or multiple workers). REQUIRE_AUTH=1
    # makes the dashboard endpoints reject the unauthenticated ?user= fallback,
    # so a public deploy serves only token-verified per-user data. DASHBOARD_BASE_URL
    # is where the magic link points (the deployed dashboard origin).
    auth_secret: str = ""
    require_auth: bool = False
    dashboard_base_url: str = ""

    # Meta 24h session-window compliance (A1). When Donna wants to send proactively
    # and the user hasn't messaged in the last 23h, she sends this fixed-text template
    # to reopen the conversation window, then queues the actual content for delivery
    # when the user replies. Template must be UTILITY category, no variables needed.
    whatsapp_reopen_template: str = "donna_reopen"


settings = Settings()
