"""Unit coverage for the previously-missing capability modules:
voice_intent, compose_image_prompt, image_client, voice_synth, the
voice_response -> VoiceResponseMarker wiring, WA media refs, and the
backend.web search/pipeline degrade paths.
"""
from __future__ import annotations

import pytest

from delivery.messages import AudioMessage, TextMessage, VoiceResponseMarker
from delivery.whatsapp import _media_ref
from donna_runtime import image_client, voice_synth
from donna_runtime.hooks import _OUTBOUND_BUFFER
from donna_runtime.tool_logic import _build_outbound, compose_image_prompt
from donna_runtime.voice_intent import detect_voice_request


# ── voice_intent ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text,expected",
    [
        ("can you send a voice note", True),
        ("say it out loud", True),
        ("talk to me", True),
        ("what's the weather", False),
        ("", False),
        (None, False),
    ],
)
def test_detect_voice_request(text, expected):
    assert detect_voice_request(text) is expected


# ── compose_image_prompt ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_compose_image_prompt_wraps_intent():
    prompt = await compose_image_prompt("u1", "a cozy reading nook")
    assert "cozy reading nook" in prompt
    assert "no watermark" in prompt


@pytest.mark.asyncio
async def test_compose_image_prompt_rejects_empty():
    with pytest.raises(ValueError):
        await compose_image_prompt("u1", "  ")


# ── voice_response wiring + media refs ────────────────────────────────────────
def test_build_outbound_voice_response_marker():
    assert isinstance(_build_outbound({"type": "voice_response"}), VoiceResponseMarker)


def test_media_ref_link_vs_id():
    assert _media_ref("https://cdn.example/x.jpg") == {"link": "https://cdn.example/x.jpg"}
    assert _media_ref("9876543210") == {"id": "9876543210"}


# ── voice_synth ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_voice_synth_replaces_buffer_with_audio(monkeypatch):
    async def fake_tts(_text):
        return b"AUDIO_BYTES"

    async def fake_upload(self, content, mime_type, filename="media"):
        return "MID123"

    monkeypatch.setattr(voice_synth, "_elevenlabs_tts", fake_tts)
    monkeypatch.setattr("delivery.whatsapp.WhatsAppChannel.upload_media", fake_upload)
    monkeypatch.setattr(voice_synth.settings, "donna_voice_enabled", True)
    monkeypatch.setattr(voice_synth.settings, "elevenlabs_api_key", "key")

    buf = [VoiceResponseMarker(), TextMessage(body="hey there")]
    token = _OUTBOUND_BUFFER.set(buf)
    try:
        await voice_synth.maybe_synthesize_voice()
    finally:
        _OUTBOUND_BUFFER.reset(token)
    assert len(buf) == 1
    assert isinstance(buf[0], AudioMessage)
    assert buf[0].url == "MID123"


@pytest.mark.asyncio
async def test_voice_synth_strips_marker_on_fallback(monkeypatch):
    # No key -> cannot synthesize. Marker must still be removed (the WA renderer
    # has no branch for it), and the text bubble must survive.
    monkeypatch.setattr(voice_synth.settings, "donna_voice_enabled", True)
    monkeypatch.setattr(voice_synth.settings, "elevenlabs_api_key", "")

    buf = [VoiceResponseMarker(), TextMessage(body="hi")]
    token = _OUTBOUND_BUFFER.set(buf)
    try:
        await voice_synth.maybe_synthesize_voice()
    finally:
        _OUTBOUND_BUFFER.reset(token)
    assert not any(isinstance(m, VoiceResponseMarker) for m in buf)
    assert buf == [TextMessage(body="hi")]


@pytest.mark.asyncio
async def test_voice_synth_noop_without_marker():
    buf = [TextMessage(body="hi")]
    token = _OUTBOUND_BUFFER.set(buf)
    try:
        await voice_synth.maybe_synthesize_voice()
    finally:
        _OUTBOUND_BUFFER.reset(token)
    assert buf == [TextMessage(body="hi")]


# ── image_client ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_image_client_safety_prefilter():
    with pytest.raises(image_client.ImageSafetyError):
        await image_client.generate_and_upload("an explicit sexual scene")


@pytest.mark.asyncio
async def test_image_client_unconfigured_raises_provider_error(monkeypatch):
    monkeypatch.setattr(image_client.settings, "fal_key", "")
    with pytest.raises(image_client.ImageProviderError):
        await image_client.generate_and_upload("a cat on a sofa")


# ── backend.web degrade paths ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_web_search_degrades_without_key(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    import backend.config as c

    c.get_settings.cache_clear()
    from backend.web.pipeline import run_web_research
    from backend.web.search import agentic_search, search_web

    assert (await search_web("x"))["status"] == "degraded"
    assert (await agentic_search("x"))["status"] == "degraded"
    answer, trace = await run_web_research("x")
    assert answer.answer == ""
    assert trace.merged_count == 0
    assert "reason" in answer.metadata
