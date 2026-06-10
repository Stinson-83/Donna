"""Outbound voice-note synthesis.

Called by `send_burst` after the outbound buffer is built. If the buffer
contains a VoiceResponseMarker (the model flagged the turn for audio), the
text bubbles are concatenated, synthesized via ElevenLabs, uploaded to the WA
media endpoint, and the whole buffer is replaced in place with a single
AudioMessage. On any failure — voice disabled, no key, TTS/upload error — the
marker is stripped and the original text bubbles are delivered instead.

The marker MUST never survive this call: the WhatsApp renderer has no branch
for it and would raise.
"""
from __future__ import annotations

import logging

import httpx

from config import settings
from delivery.messages import AudioMessage, TextMessage, VoiceResponseMarker
from delivery.whatsapp import WhatsAppChannel

from .hooks import _OUTBOUND_BUFFER

logger = logging.getLogger(__name__)

_ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


async def maybe_synthesize_voice() -> None:
    buffer = _OUTBOUND_BUFFER.get()
    if not buffer:
        return
    if not any(isinstance(m, VoiceResponseMarker) for m in buffer):
        return

    audio: AudioMessage | None = None
    try:
        audio = await _try_make_audio(buffer)
    except Exception:
        logger.exception("voice_synth: synthesis failed, falling back to text")
        audio = None

    if audio is not None:
        buffer[:] = [audio]
    else:
        # Drop the marker so the renderer never sees it; keep the text bubbles.
        buffer[:] = [m for m in buffer if not isinstance(m, VoiceResponseMarker)]


async def _try_make_audio(buffer: list) -> AudioMessage | None:
    if not settings.donna_voice_enabled or not settings.elevenlabs_api_key:
        return None

    script = " ".join(
        m.body.strip()
        for m in buffer
        if isinstance(m, TextMessage) and m.body and m.body.strip()
    ).strip()
    if not script:
        return None
    script = script[: settings.donna_voice_max_chars]

    audio_bytes = await _elevenlabs_tts(script)
    if not audio_bytes:
        return None

    media_id = await WhatsAppChannel().upload_media(
        audio_bytes, "audio/mpeg", "voice.mp3"
    )
    if not media_id:
        return None
    return AudioMessage(url=media_id)


async def _elevenlabs_tts(text: str) -> bytes | None:
    url = _ELEVEN_URL.format(voice_id=settings.elevenlabs_voice_id)
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_model_id,
        "voice_settings": {"speed": settings.elevenlabs_voice_speed},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content
    except Exception:
        logger.exception("voice_synth: elevenlabs request failed")
        return None
