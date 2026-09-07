"""
The content-generation agent.

LCEL chain: prompt | llm | parser

Structured output uses PydanticOutputParser rather than
.with_structured_output(). Free-tier models on OpenRouter often lack
reliable tool-calling, and native structured output fails hard on them.
Format instructions in the prompt plus a parse-and-retry loop works across
far more models, which matters when the free NVIDIA tier rotates.
"""

import json
import re
import time

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from backend.mod03.utils.config import settings
from backend.core.logging import get_logger
from backend.mod03.utils.schemas import SocialPost
from backend.mod03.prompts.prompts import build_prompt

MAX_ATTEMPTS = 2

log = get_logger("agent")


class AgentError(RuntimeError):
    """Surfaced to the UI verbatim. Real errors, no silent fallbacks."""


def _llm() -> ChatOpenAI:
    if not settings.configured:
        raise AgentError(
            "OPENROUTER_API_KEY is not set. Add it to backend/.env and restart."
        )
    return ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0.8,
        # Reasoning models burn a lot of tokens thinking before they answer.
        # 800 was too tight — generation was truncated mid-thought and never
        # reached the JSON. Give it room.
        max_tokens=3000,
        timeout=120,
        # OpenRouter-specific: switch the reasoning trace off entirely. A
        # 260-character social post does not need chain-of-thought, and the
        # trace is what was crowding out the actual answer.
        extra_body={"reasoning": {"enabled": False}},
        default_headers={
            # OpenRouter uses these for attribution on free-tier requests.
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "MOD03 National Trend Radar",
        },
    )


def _salvage_json(text: str) -> dict | None:
    """
    Models wrap JSON in fences, or narrate before emitting it. Dig it out.

    Reasoning models in particular put a long think-aloud trace first, so we
    scan for balanced brace spans and try the LAST one — the answer comes
    after the reasoning, not before it.
    """
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    for block in reversed(fenced):
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    # Walk the string tracking brace depth to find complete objects.
    spans, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append(text[start : i + 1])

    for span in reversed(spans):
        try:
            parsed = json.loads(span)
            if isinstance(parsed, dict) and "post_text" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def generate_post(
    hashtag: str,
    score: int,
    band: str,
    rationale: str,
    neighbours: list[str],
    region: str,
    language_label: str = "English",
    category: str = "Other",
    reference_captions: list[str] | None = None,
) -> tuple[SocialPost, str, int]:
    """Returns (post, model_name, latency_ms). Raises AgentError on failure."""
    parser = PydanticOutputParser(pydantic_object=SocialPost)
    prompt = build_prompt()
    llm = _llm()
    chain = prompt | llm

    # Ground the draft in real captions when we have them; otherwise the
    # block collapses to an empty string and the prompt is unchanged.
    if reference_captions:
        from backend.mod03.prompts.prompts import REFERENCE_TEMPLATE

        numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(reference_captions, 1))
        reference_block = REFERENCE_TEMPLATE.format(captions=numbered)
    else:
        reference_block = ""

    inputs = {
        "hashtag": hashtag,
        "region": region,
        "reference_block": reference_block,
        "score": score,
        "band": band,
        "rationale": rationale,
        "language_label": language_label,
        "category": category,
        "neighbours": ", ".join(neighbours[:6]) or "none captured",
        "format_instructions": parser.get_format_instructions(),
    }

    log.info(
        "drafting | hashtag=%s | score=%s | band=%s | lang=%s | category=%s",
        hashtag, score, band, language_label, category,
    )
    log.debug("scoring rationale: %s", rationale)
    log.debug("neighbouring trends: %s", inputs["neighbours"])

    started = time.perf_counter()
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            log.debug("attempt %d/%d -> %s", attempt, MAX_ATTEMPTS,
                      settings.openrouter_model)
            raw = chain.invoke(inputs)
            text = raw.content if hasattr(raw, "content") else str(raw)

            log.debug("raw response (%d chars): %s", len(text), text[:600])

            try:
                post = parser.parse(text)
            except OutputParserException:
                log.warning(
                    "strict JSON parse failed on attempt %d — attempting salvage",
                    attempt,
                )
                salvaged = _salvage_json(text)
                if salvaged is None:
                    log.error("salvage found no usable JSON in the response")
                    raise
                log.info("salvage succeeded — recovered JSON from prose")
                post = SocialPost.model_validate(salvaged)

            # Enforce the two non-negotiable hashtags even if the model
            # dropped one. Cheaper than another round trip.
            tags = list(post.hashtags)
            for required in (hashtag, "#BharatConnect"):
                if not any(t.lower() == required.lower() for t in tags):
                    log.warning("model omitted required hashtag %s — injected",
                                required)
                    tags.append(required)
            post.hashtags = tags

            latency = int((time.perf_counter() - started) * 1000)
            log.info(
                "draft ok | attempt=%d | %dms | %d chars | tone=%s | tags=%s",
                attempt, latency, len(post.post_text), post.tone,
                ", ".join(post.hashtags),
            )
            log.debug("post_text: %s", post.post_text)
            log.debug("image_prompt: %s", post.image_prompt)
            log.debug("risk_notes: %s", post.risk_notes)
            return post, settings.openrouter_model, latency

        except Exception as e:  # noqa: BLE001 — surfaced to the caller
            last_error = e
            log.warning("attempt %d/%d failed | %s: %s",
                        attempt, MAX_ATTEMPTS, type(e).__name__, e)
            if attempt == MAX_ATTEMPTS:
                break
            delay = 2 * attempt
            log.info("backing off %ss before retry", delay)
            time.sleep(delay)
            time.sleep(2 * attempt)  # back off before retrying

    # Full technical detail goes to the server log for whoever is running
    # the demo; the UI gets a message a stakeholder can read.
    log.error(
        "generation failed after %d attempts using '%s' | %s: %s",
        MAX_ATTEMPTS, settings.openrouter_model,
        type(last_error).__name__, last_error,
    )
    raise AgentError(
        "Could not create a draft right now. The writing service did not "
        "return a usable response after two attempts. Try again, or pick "
        "another trend."
    )
