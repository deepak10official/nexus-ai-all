"""Image description service for the Persona Panel.

Sends an image (base64-encoded) to the vision model and returns a structured
text description. This description is cached in PanelState and shared across
all persona agents — calling the vision model once instead of 15 times.
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.messages import HumanMessage

from backend.mod02.model.factory import build_vision_model
from backend.mod02.utils.config import Settings, get_settings
from backend.core.logging import get_logger

log = get_logger("vision")

_DESCRIBE_PROMPT = """\
You are reviewing a marketing image that accompanies a financial social media post for Indian consumers.

The post text is:
\"\"\"
{post_text}
\"\"\"

Describe this image in detail for a review panel. Cover:
1. **Visual content**: What does the image show? (people, objects, scenes, graphics)
2. **Text in image**: Any text, numbers, logos, or disclaimers visible in the image.
3. **Tone & style**: Is it professional, casual, alarming, exciting, trustworthy?
4. **Relevance**: How does the image relate to the post text?
5. **Concerns**: Any potentially misleading elements, exaggerated claims visualised, inappropriate imagery, or missing disclaimers?

Be factual and specific. Write 3-6 sentences."""


import base64
import os
from pathlib import Path

# Generated files output directory (shared with FastAPI /generated mount)
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "mod03" / "generated"


def resolve_image_b64(
    image_b64: Optional[str] = None,
    image_url: Optional[str] = None,
) -> Optional[str]:
    """Resolve base64 image data from either a base64 string or a /generated/ URL."""
    if image_b64:
        return image_b64
    if not image_url:
        return None

    # Handle local /generated/... paths
    rel = image_url.strip()
    if rel.startswith("/generated/"):
        rel = rel[len("/generated/"):]
    elif rel.startswith("generated/"):
        rel = rel[len("generated/"):]
    else:
        return None

    local_path = OUTPUT_DIR / rel
    if local_path.is_file():
        try:
            with open(local_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        except Exception as exc:
            log.warning("Could not read image file %s: %s", local_path, exc)
            return None
    return None


def describe_image(
    image_b64: str,
    post_text: str,
    settings: Optional[Settings] = None,
) -> str:
    """Send the image to the vision model and return a text description.

    Parameters
    ----------
    image_b64:
        Base64-encoded image data (JPEG, PNG, or WebP).
    post_text:
        The accompanying post text for context.
    settings:
        App settings (for model config).

    Returns
    -------
    str
        A text description of the image suitable for injection into persona
        prompts as ``image_context``.
    """

    settings = settings or get_settings()
    llm = build_vision_model(settings)

    prompt_text = _DESCRIBE_PROMPT.format(post_text=post_text.strip())

    # Build multimodal message with text + image
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            },
        ]
    )

    log.info("Describing image with vision model (%s)...", settings.groq_vision_model)
    started = time.perf_counter()
    try:
        response = llm.invoke([message])
        description = response.content.strip()
    except Exception as exc:
        log.warning("Vision model failed (%s); using fallback description.", exc)
        description = (
            "An image accompanies this post but could not be analysed automatically. "
            "Review it visually for any misleading or inappropriate content."
        )

    elapsed = time.perf_counter() - started
    log.info("Image described in %.1fs (%d chars)", elapsed, len(description))
    return description

