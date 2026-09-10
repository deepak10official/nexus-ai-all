"""Application configuration loaded from environment variables.

The default provider is ``groq`` (fast hosted inference, needs ``GROQ_API_KEY``).
Set ``LLM_PROVIDER=ollama`` to run locally without a key, or
``LLM_PROVIDER=anthropic`` with an ``ANTHROPIC_API_KEY`` to use Claude.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _load_dotenv() -> None:
    """Best-effort load of a local .env file without a hard dependency.

    Minimal parser: ``KEY=VALUE`` lines, ignoring blanks and ``#`` comments, and
    never overriding a value already present in the real environment.
    """

    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


Provider = Literal["anthropic", "ollama", "groq"]

PROVIDERS = ("anthropic", "ollama", "groq")

STRUCTURED_METHODS = ("function_calling", "json_schema", "json_mode")


class Settings(BaseModel):
    """Typed view over the process environment."""

    provider: Provider = Field(default="groq")

    # Groq (default cloud provider, needs GROQ_API_KEY)
    groq_api_key: Optional[str] = None
    groq_model: str = "qwen/qwen3.6-27b"
    groq_vision_model: str = "qwen/qwen3.8-27b"  # vision-capable model for image analysis
    # Skip the <think> phase on reasoning models (qwen3 etc.). Left on, thinking
    # eats the whole max_tokens budget and structured votes come back empty.
    # Set GROQ_REASONING=true to re-enable it (raise LLM_MAX_TOKENS too).
    groq_reasoning: bool = False
    # Five personas voting at once easily trips the free tier's tokens-per-minute
    # limit; the SDK honours the API's retry-after, so extra retries just make
    # the round slower instead of losing votes to a 429.
    groq_max_retries: int = 5

    # Ollama (local provider, no API key needed)
    ollama_model: str = "qwen3-vl:2b"#"qwen3.6:27b"
    ollama_base_url: str = "http://localhost:11434"
    # Disable the <think> phase on reasoning models so structured JSON output is
    # reliable and fast. Set OLLAMA_REASONING=true to re-enable it.
    ollama_reasoning: bool = False

    # Anthropic (optional cloud provider)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Generation controls
    temperature: float = 0.7
    max_tokens: int = 1024

    # How the vote schema is enforced. "function_calling" (the default) asks the
    # model to call a tool; some models answer in prose instead and the provider
    # returns `tool_use_failed`. "json_schema" / "json_mode" ask for raw JSON,
    # which qwen-class models tend to produce far more reliably.
    structured_output_method: Literal["function_calling", "json_schema", "json_mode"] = (
        "function_calling"
    )
    # Attempts per persona per round when structured output fails. Votes run
    # sequentially by default, so keep this small: every retry adds a full LLM
    # round-trip to the panel's total time.
    persona_max_attempts: int = 2

    # Voting rules
    # Fan the five personas out on a thread pool instead of voting one at a
    # time. Much faster, but hits provider rate limits harder.
    panel_parallel: bool = False
    panel_size: int = 15
    approval_threshold: float = 60.0  # percentage (0-100) of approvals needed
    max_revision_rounds: int = 2

    # Optional Redis cache (Upstash or local)
    redis_url: Optional[str] = None
    cache_ttl_seconds: int = 60 * 60 * 24  # 24h

    @property
    def caching_enabled(self) -> bool:
        return bool(self.redis_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build and cache a ``Settings`` instance from the environment."""

    _load_dotenv()

    def _int(name: str, default: int) -> int:
        try:
            return int(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    def _float(name: str, default: float) -> float:
        try:
            return float(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    def _bool(name: str) -> bool:
        return os.environ.get(name, "false").strip().lower() in ("1", "true", "yes")

    def _method() -> str:
        raw = os.environ.get("STRUCTURED_OUTPUT_METHOD", "function_calling")
        raw = raw.strip().lower()
        return raw if raw in STRUCTURED_METHODS else "function_calling"

    provider = os.environ.get("LLM_PROVIDER", "groq").strip().lower()
    if provider not in PROVIDERS:
        provider = "groq"

    return Settings(
        provider=provider,  # type: ignore[arg-type]
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        groq_model=os.environ.get("GROQ_MODEL", "qwen/qwen3.6-27b"),
        groq_vision_model=os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"),
        groq_reasoning=_bool("GROQ_REASONING"),
        groq_max_retries=_int("GROQ_MAX_RETRIES", 5),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "qwen3.6:27b"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_reasoning=_bool("OLLAMA_REASONING"),
        temperature=_float("LLM_TEMPERATURE", 0.7),
        max_tokens=_int("LLM_MAX_TOKENS", 1024),
        structured_output_method=_method(),
        persona_max_attempts=max(1, _int("PERSONA_MAX_ATTEMPTS", 2)),
        panel_parallel=_bool("PANEL_PARALLEL"),
        panel_size=_int("PANEL_SIZE", 15),
        approval_threshold=_float("APPROVAL_THRESHOLD", 60.0),
        max_revision_rounds=_int("MAX_REVISION_ROUNDS", 2),
        redis_url=os.environ.get("REDIS_URL"),
        cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 60 * 60 * 24),
    )
