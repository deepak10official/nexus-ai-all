"""Optional Redis-backed cache for persona votes.

Caching is entirely optional. When ``REDIS_URL`` is configured and the ``redis``
package is importable, votes are memoised by a hash of ``(persona_id, post,
model)``. Every failure degrades gracefully to "no cache".
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from backend.mod02.utils.config import Settings, get_settings
from backend.mod02.utils.schemas import PersonaVote


class VoteCache:
    """Thin wrapper around Redis with a no-op fallback."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = None
        if self._settings.caching_enabled:
            self._client = self._connect()

    def _connect(self):
        try:
            import redis  # type: ignore
        except ImportError:
            return None
        try:
            client = redis.Redis.from_url(
                self._settings.redis_url, decode_responses=True
            )
            client.ping()
            return client
        except Exception:
            return None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _key(self, persona_id: str, post: str, model: str) -> str:
        digest = hashlib.sha256(
            f"{persona_id}::{model}::{post}".encode("utf-8")
        ).hexdigest()
        return f"vote:{digest}"

    def get(self, persona_id: str, post: str, model: str) -> Optional[PersonaVote]:
        if not self._client:
            return None
        try:
            raw = self._client.get(self._key(persona_id, post, model))
        except Exception:
            return None
        if not raw:
            return None
        try:
            return PersonaVote.model_validate(json.loads(raw))
        except Exception:
            return None

    def set(self, persona_id: str, post: str, model: str, vote: PersonaVote) -> None:
        if not self._client:
            return
        try:
            self._client.setex(
                self._key(persona_id, post, model),
                self._settings.cache_ttl_seconds,
                vote.model_dump_json(),
            )
        except Exception:
            pass
