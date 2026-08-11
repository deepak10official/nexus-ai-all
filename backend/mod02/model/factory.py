"""Chat-model factory.

Groq is the default provider (hosted, needs ``GROQ_API_KEY``); local Ollama and
Anthropic Claude are available via ``LLM_PROVIDER=ollama`` / ``anthropic``.
Provider SDKs are imported lazily so the package never hard-depends on one you
are not using.
"""

from __future__ import annotations

from typing import Optional

from backend.mod02.utils.config import Settings, get_settings
from backend.core.logging import get_logger

log = get_logger("model")


class LLMConfigError(RuntimeError):
    """Raised when the requested provider is not usable (e.g. missing key)."""


def build_groq_model(settings: Settings, temperature: float):
    """Create a Groq-hosted chat model."""

    if not settings.groq_api_key:
        raise LLMConfigError(
            "GROQ_API_KEY is not set. Set it in your environment or .env file, "
            "or use the local provider with LLM_PROVIDER=ollama."
        )
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:  # pragma: no cover - env dependent
        raise LLMConfigError(
            "langchain-groq is not installed. Run `pip install langchain-groq`."
        ) from exc

    log.info(
        "Building GROQ model '%s' (reasoning=%s, temp=%.2f)",
        settings.groq_model,
        settings.groq_reasoning,
        temperature,
    )
    # ``reasoning_effort="none"`` skips the <think> phase on thinking models
    # (e.g. qwen3). Left on, thinking burns the whole max_tokens budget and the
    # structured vote comes back empty. When it is enabled, "hidden" at least
    # keeps the raw thinking out of the answer text.
    extra = (
        {"reasoning_format": "hidden"}
        if settings.groq_reasoning
        else {"reasoning_effort": "none"}
    )
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=settings.max_tokens,
        max_retries=settings.groq_max_retries,
        **extra,
    )


def build_ollama_model(settings: Settings, temperature: float):
    """Create a local Ollama chat model."""

    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover - env dependent
        raise LLMConfigError(
            "langchain-ollama is not installed. Run `pip install langchain-ollama`."
        ) from exc

    log.info(
        "Building OLLAMA model '%s' (base_url=%s, reasoning=%s, temp=%.2f)",
        settings.ollama_model,
        settings.ollama_base_url,
        settings.ollama_reasoning,
        temperature,
    )
    # ``reasoning=False`` disables the <think> phase on thinking models
    # (e.g. qwen3). Without this, structured-output (JSON schema) responses can
    # come back empty because the model spends its budget "thinking".
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        num_predict=settings.max_tokens,
        reasoning=settings.ollama_reasoning,
    )


def build_anthropic_model(settings: Settings, temperature: float):
    """Create an Anthropic Claude chat model."""

    if not settings.anthropic_api_key:
        raise LLMConfigError(
            "ANTHROPIC_API_KEY is not set. Set it in your environment or .env "
            "file, or use the default local provider with LLM_PROVIDER=ollama."
        )
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:  # pragma: no cover - env dependent
        raise LLMConfigError(
            "langchain-anthropic is not installed. Run "
            "`pip install langchain-anthropic`."
        ) from exc

    log.info(
        "Building ANTHROPIC model '%s' (temp=%.2f)",
        settings.anthropic_model,
        temperature,
    )
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=temperature,
        max_tokens=settings.max_tokens,
    )


def build_chat_model(settings: Optional[Settings] = None, *, temperature: Optional[float] = None):
    """Create a LangChain chat model based on the configured provider.

    Parameters
    ----------
    settings:
        Resolved application settings. Falls back to ``get_settings()``.
    temperature:
        Optional per-call override (personas use a little variance; the reviser
        can be run cooler for more deterministic edits).
    """

    settings = settings or get_settings()
    temp = settings.temperature if temperature is None else temperature

    if settings.provider == "groq":
        return build_groq_model(settings, temp)
    if settings.provider == "ollama":
        return build_ollama_model(settings, temp)
    if settings.provider == "anthropic":
        return build_anthropic_model(settings, temp)
    raise LLMConfigError(f"Unknown provider: {settings.provider!r}")


def agent_memory_model(settings: Settings | None = None):
    """Placeholder — not implemented yet."""
    raise NotImplementedError("agent_memory_model is not implemented yet.")
    