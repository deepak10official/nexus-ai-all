"""Environment-backed settings. Nothing secret is hardcoded."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-nano-9b-v2:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Ask the image model to render "Bharat Connect" itself, in addition to
    # the composited wordmark. OFF by default and it should stay off:
    # diffusion models cannot spell reliably, and the earlier result was
    # "#Blherat Connect" burned into the image next to the correct mark.
    # Exposed only so the behaviour can be compared side by side.
    wordmark_in_prompt: bool = False

    # Logging. See backend/utils/logging.py for how these are applied.
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_to_file: bool = True
    log_to_console: bool = True

    trend_region: str = "india"
    trend_cache_minutes: int = 30

    # Image generation (Hugging Face Inference Providers)
    hf_token: str = ""
    # "auto" lets Hugging Face route to whichever provider is currently
    # serving the model. Hardcoding one (e.g. "fal-ai") breaks when that
    # provider drops the model or is down.
    hf_provider: str = "auto"
    # FLUX.1-dev gives better fidelity; FLUX.1-schnell is Apache-2.0 and
    # roughly 10x faster. Swap freely — same API, one string.
    image_model: str = "black-forest-labs/FLUX.1-dev"

    @property
    def configured(self) -> bool:
        return bool(self.openrouter_api_key.strip())

    @property
    def image_configured(self) -> bool:
        return bool(self.hf_token.strip())

    @property
    def image_licence(self) -> str:
        """Surfaced in the UI so nobody ships a demo asset commercially by
        accident. FLUX.1-dev is non-commercial; schnell is Apache-2.0."""
        m = self.image_model.lower()
        if "schnell" in m:
            return "Apache-2.0 — commercial use permitted"
        if "dev" in m:
            return "FLUX.1 [dev] Non-Commercial — prototype/demo only"
        return "Check the model card before commercial use"


settings = Settings()
