"""
Image generation for drafted posts.

Two stages, deliberately separate:

  1. FLUX generates a clean image via the Hugging Face Inference API.
     The prompt explicitly asks for NO text in the image.

  2. Pillow composites the "Bharat Connect" wordmark into the bottom-right
     corner afterwards.

Why not let FLUX render the wordmark? Because diffusion models cannot place
exact text at an exact position reliably — you get "Bharat Connedt",
drifting placement, and different type every run. A brand lockup has to be
pixel-identical every time. Compositing is deterministic, correctly spelt,
and costs about a millisecond.

Local inference (diffusers/FluxPipeline) was considered and rejected: ~24GB
of weights and a serious GPU, versus one HTTP call here.
"""

import io
import re
import time
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from backend.mod03.utils.config import settings
from backend.core.logging import get_logger

log = get_logger("image")

# 16:9, the standard single-image aspect for X. FLUX wants multiples of 16.
WIDTH, HEIGHT = 1200, 672  # 675 rounded to a multiple of 16

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "generated"
OUTPUT_DIR.mkdir(exist_ok=True)

WORDMARK = "Bharat Connect"

# Fonts to try, in order. Windows first since that is where this runs, then
# Linux distributions, then whatever Pillow bundles. A brand lockup in the
# bitmap fallback font looks amateurish, so the search is worth the lines.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuisb.ttf",     # Segoe UI Semibold
    "C:/Windows/Fonts/segoeuib.ttf",      # Segoe UI Bold
    "C:/Windows/Fonts/arialbd.ttf",       # Arial Bold
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


class ImageError(RuntimeError):
    """Surfaced to the UI verbatim. No silent placeholder images."""


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    # Last resort. Legible, but not brand-quality — the caller warns.
    return ImageFont.load_default()


def _has_truetype() -> bool:
    return not isinstance(_load_font(24), ImageFont.ImageFont)


def add_wordmark(img: Image.Image) -> Image.Image:
    """
    Composite 'Bharat Connect' into the bottom-right corner.

    A soft dark scrim goes underneath first. Without it the wordmark
    disappears on light images — and 'usually legible' is not acceptable
    for a brand mark that ships on every post.
    """
    img = img.convert("RGB")
    w, h = img.size

    font_size = max(22, int(h * 0.045))
    font = _load_font(font_size)

    pad_x = int(w * 0.028)
    pad_y = int(h * 0.045)

    # Measure the text so the scrim fits it rather than guessing.
    probe = ImageDraw.Draw(img)
    box = probe.textbbox((0, 0), WORDMARK, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]

    # Scrim: a blurred rounded rectangle on its own layer, so it reads as a
    # soft vignette rather than a hard label.
    scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    margin = int(font_size * 0.9)
    sd.rounded_rectangle(
        [
            w - pad_x - tw - margin,
            h - pad_y - th - margin,
            w - pad_x + margin // 2,
            h - pad_y + margin,
        ],
        radius=int(font_size * 0.6),
        fill=(0, 0, 0, 118),
    )
    scrim = scrim.filter(ImageFilter.GaussianBlur(int(font_size * 0.45)))
    img = Image.alpha_composite(img.convert("RGBA"), scrim)

    # The wordmark itself, with a subtle shadow for edge definition.
    d = ImageDraw.Draw(img)
    x = w - pad_x - tw - box[0]
    y = h - pad_y - th - box[1]
    d.text((x + 2, y + 2), WORDMARK, font=font, fill=(0, 0, 0, 150))
    d.text((x, y), WORDMARK, font=font, fill=(255, 255, 255, 245))

    # A short accent rule under the mark — reads as considered branding
    # rather than a watermark slapped on top.
    rule_y = h - pad_y + int(font_size * 0.35)
    d.line(
        [(w - pad_x - tw, rule_y), (w - pad_x, rule_y)],
        fill=(255, 154, 60, 230),
        width=max(2, font_size // 12),
    )

    return img.convert("RGB")


# Clauses that ask the diffusion model to draw lettering. A trailing
# "no text" suffix does NOT neutralise an explicit positive request —
# FLUX obeys the instruction and renders something like "#Blherat
# Connect" across the frame, misspelt, colliding with the real composited
# wordmark. So any sentence asking for text is removed before the brief
# ever reaches the model.
_TEXT_REQUEST = re.compile(
    r"\b("
    r"text|texts|word|words|letter|lettering|letters|typography|font|fonts|"
    r"caption|captions|title|titles|headline|slogan|tagline|"
    r"logo|logos|wordmark|watermark|signage|sign board|signboard|"
    r"written|writing|spelled|spelt|inscribed|engraved|"
    r"says|saying|reads|reading|displaying the name"
    r")\b",
    re.IGNORECASE,
)


def sanitise_brief(image_prompt: str) -> tuple[str, list[str]]:
    """
    Strips any sentence that asks for rendered text.

    Returns (cleaned_brief, removed_sentences). The removed list is
    surfaced to the reviewer so an edited brief that silently lost a
    clause is visible rather than mysterious.
    """
    parts = re.split(r"(?<=[.!?])\s+", image_prompt.strip())
    kept, removed = [], []
    for part in parts:
        if not part.strip():
            continue
        if _TEXT_REQUEST.search(part):
            removed.append(part.strip())
        else:
            kept.append(part.strip())

    cleaned = " ".join(kept).strip()
    # If sanitising removed everything, fall back to a neutral scene so we
    # still produce something rather than sending an empty prompt.
    if not cleaned:
        cleaned = (
            "An everyday Indian scene connected to paying household bills, "
            "documentary photography, no people facing camera"
        )
    return cleaned, removed


def readable_hashtag(hashtag: str) -> str:
    """#TakeIndiaForward -> 'take india forward'. Gives the diffusion model
    the actual words rather than an opaque token it will try to render."""
    raw = hashtag.lstrip("#").replace("_", " ").replace("-", " ")
    # lowercase/digit -> uppercase:  takeIndia -> take India
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw)
    # acronym -> word:  AIDevelopment -> AI Development
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    # letter -> digit:  Fold8 -> Fold 8
    spaced = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def post_subject(post_text: str, limit: int = 160) -> str:
    """
    Distil the copy into a scene cue.

    Hashtags and handles are stripped deliberately — leaving them in
    encourages the model to render them as visible text, which is the exact
    failure the composited wordmark exists to avoid.
    """
    txt = re.sub(r"[#@][\w\u0900-\u097F]+", "", post_text)
    txt = re.sub(r"https?://\S+", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip(" .,–—-")
    if len(txt) > limit:
        cut = txt[:limit]
        txt = cut[: cut.rfind(" ")] if " " in cut else cut
    return txt


def _build_prompt(image_prompt: str, hashtag: str = "", post_text: str = "") -> str:
    """
    Assemble the final diffusion prompt.

    The brief from the writing step carries the creative idea. This function
    guarantees the three anchors are present regardless — a reviewer can
    hand-edit the brief and unknowingly strip the connection to the trend or
    the payment moment, and the image should still land.

    Structure follows what actually works on FLUX: subject and composition
    first, then specifics, then style, then camera, then negatives. Detail
    early carries the most weight.
    """
    topic = readable_hashtag(hashtag)
    subject = post_subject(post_text)
    brief = image_prompt.strip().rstrip(".")

    parts = [
        "A cinematic, premium digital illustration for a social media post"
        + (f" about {topic} and Bharat Connect." if topic else " for Bharat Connect."),
        brief + ".",
    ]

    if topic:
        parts.append(
            f"The world of {topic} must be visibly present in the frame and "
            "immediately recognisable — not a generic backdrop that would "
            "suit any subject."
        )

    parts.append(
        "Ground the scene in a real Indian payment moment for NPCI's Bharat "
        "Connect, the national bill-payment system: a phone held up at a "
        "kirana shop counter, a QR code scanned at a roadside stall, a "
        "farmer completing a FASTag recharge on a smartphone, a family "
        "settling the month's bills at a kitchen table, or a small-town "
        "agent point. The act of paying is visible, never merely implied."
    )

    if subject:
        parts.append(f"The specific moment being illustrated: {subject}.")

    parts.append(
        "Layered composition with clear foreground, midground and "
        "background. Warm Indian sunlight with soft connecting light "
        "trails. Subtle saffron, white and green accents used sparingly. "
        "Clean modern fintech aesthetic, premium brand photography feel, "
        "rich colour grading, shallow depth of field, highly detailed, "
        "uncluttered."
    )

    if settings.wordmark_in_prompt:
        # Opt-in only. Left available for comparison, but the composited
        # mark is still applied on top, so expect two wordmarks and expect
        # the model's one to be misspelt.
        parts.append(
            'Elegant text "Bharat Connect" placed clearly in the bottom '
            "right corner in white with a soft glow."
        )
        parts.append(
            "Negative: no other text anywhere, no watermarks, no distorted "
            "hands, no extra fingers."
        )
    else:
        parts.append(
            "Composition note: keep the lower right corner visually quiet "
            "and free of detail — reserved empty space where the Bharat "
            "Connect brand mark is placed after rendering."
        )
        parts.append(
            "Negative: no text, no words, no letters, no numbers, no "
            "typography, no captions, no logos, no watermarks, no signage, "
            "no readable screens, no distorted hands, no extra fingers."
        )

    return " ".join(parts)


def generate_image(image_prompt: str, hashtag: str, post_text: str = "") -> dict:
    """
    Returns {filename, url, model, latency_ms, warning}.
    Raises ImageError with the real reason on failure.
    """
    log.info("image requested | hashtag=%s", hashtag)
    log.debug("brief as written: %s", image_prompt)

    image_prompt, stripped = sanitise_brief(image_prompt)
    if stripped:
        log.warning("stripped %d text-requesting clause(s) from brief: %s",
                    len(stripped), " | ".join(stripped))
    if not settings.hf_token.strip():
        raise ImageError(
            "HF_TOKEN is not set. Add it to backend/.env and restart uvicorn. "
            "Create a token at https://huggingface.co/settings/tokens"
        )

    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise ImageError(
            "huggingface_hub is not installed. Run: pip install -r requirements.txt"
        ) from e

    client = InferenceClient(
        provider=settings.hf_provider,
        api_key=settings.hf_token,
    )

    final_prompt = None
    started = time.perf_counter()
    try:
        # BUG FIX: hashtag and post_text were accepted by _build_prompt but
        # never passed here, so the trend/NPCI/copy anchoring silently did
        # nothing at runtime.
        final_prompt = _build_prompt(image_prompt, hashtag, post_text)
        log.info("generating | %s via %s | %dx%d | %d prompt chars",
                 settings.image_model, settings.hf_provider,
                 WIDTH, HEIGHT, len(final_prompt))
        log.debug("final prompt: %s", final_prompt)

        image = client.text_to_image(
            final_prompt,
            model=settings.image_model,
            width=WIDTH,
            height=HEIGHT,
        )
    except Exception as e:  # noqa: BLE001 — the real reason goes to the UI
        log.error("generation failed | %s via %s | %s: %s",
                  settings.image_model, settings.hf_provider,
                  type(e).__name__, e)
        if final_prompt:
            log.debug("prompt that failed: %s", final_prompt)
        raise ImageError(
            f"Image generation failed using '{settings.image_model}' via "
            f"provider '{settings.hf_provider}': {type(e).__name__}: {e}"
        ) from e

    if not isinstance(image, Image.Image):
        # Some provider/version combinations return raw bytes.
        try:
            image = Image.open(io.BytesIO(image))
        except Exception as e:  # noqa: BLE001
            raise ImageError(f"Unexpected response type from provider: {e}") from e

    # Providers do not always honour width/height exactly.
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)

    branded = add_wordmark(image)

    safe_tag = "".join(c for c in hashtag if c.isalnum())[:24] or "trend"
    filename = f"{safe_tag}-{uuid.uuid4().hex[:8]}.png"
    branded.save(OUTPUT_DIR / filename, "PNG", optimize=True)

    latency = int((time.perf_counter() - started) * 1000)

    warning = None
    if not _has_truetype():
        warning = (
            "No TrueType font found, so the wordmark used Pillow's bitmap "
            "fallback and will look rough. Install a system font or point "
            "FONT_CANDIDATES in imagegen.py at one."
        )

    log.info("image ok | %s | %dx%d | %dms | wordmark applied bottom-right",
             filename, branded.width, branded.height, latency)

    return {
        "filename": filename,
        "url": f"/generated/{filename}",
        "width": branded.width,
        "height": branded.height,
        # Sentences stripped from the brief because they asked for rendered
        # text. Surfaced to the reviewer so an edit that silently lost a
        # clause is visible rather than mysterious.
        "removed_from_brief": stripped,
        # Operator-only — logged by the caller, not sent to the browser.
        "model": settings.image_model,
        "provider": settings.hf_provider,
        "latency_ms": latency,
        "warning": warning,
    }
