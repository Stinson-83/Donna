"""Image generation + hosting for the `image` tool.

Generates an image from a composed prompt via fal and returns a publicly
fetchable URL (fal hosts the result), which the delivery layer references as a
WhatsApp image `{"link": url}`. Degrades by raising typed errors the tool
catches:

  - ImageSafetyError   -> prompt/content blocked (safety filter)
  - ImageUploadError   -> generation ok but no usable hosted asset
  - ImageProviderError -> provider not configured / timeout / failure

`generate_and_upload` is the only entrypoint the tool calls.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)


class ImageProviderError(Exception):
    """Provider unavailable, unconfigured, timed out, or returned an error."""


class ImageSafetyError(Exception):
    """Prompt or generated content was rejected by a safety filter."""


class ImageUploadError(Exception):
    """Image generated but could not be turned into a usable hosted asset."""


@dataclass
class ImageResult:
    media_id: str  # public https URL; WA fetches it via {"link": url}


# Cheap local pre-filter so we never spend a provider call on obviously
# disallowed prompts. The provider's own safety filter is the real backstop.
_BANNED_TERMS = (
    "nsfw", "nude", "naked", "porn", "explicit sexual", "child", "gore",
)


async def generate_and_upload(prompt: str, wa=None) -> ImageResult:
    """Generate an image for `prompt` and return a hosted URL.

    `wa` (a WhatsAppChannel) is accepted for the alternate path where bytes are
    uploaded straight to WhatsApp media; the default fal path hosts the image
    itself, so it is currently unused.
    """
    low = (prompt or "").lower()
    if any(term in low for term in _BANNED_TERMS):
        raise ImageSafetyError("prompt blocked by local safety filter")

    if not settings.fal_key:
        raise ImageProviderError("image provider not configured (FAL_KEY missing)")
    os.environ.setdefault("FAL_KEY", settings.fal_key)

    try:
        import fal_client
    except ImportError as exc:  # pragma: no cover - depends on env
        raise ImageProviderError("fal-client not installed") from exc

    try:
        result = await fal_client.subscribe_async(
            settings.fal_image_model,
            arguments={"prompt": prompt, "num_images": 1},
        )
    except Exception as exc:
        msg = str(exc).lower()
        if any(k in msg for k in ("nsfw", "safety", "content policy", "blocked")):
            raise ImageSafetyError(str(exc)) from exc
        raise ImageProviderError(str(exc)) from exc

    images = (result or {}).get("images") or []
    url = images[0].get("url") if images and isinstance(images[0], dict) else None
    if not url:
        raise ImageUploadError("provider returned no image url")
    return ImageResult(media_id=str(url))
