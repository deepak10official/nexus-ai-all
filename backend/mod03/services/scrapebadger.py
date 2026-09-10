"""ScrapeBadger trend feeder — the fallback when trends24 is unreachable.

trends24 is a scrape of a third-party page: free, but it goes slow or dark
without warning and there is nothing we can do about it from here. ScrapeBadger
is a paid API over Twitter's own place-trends endpoint, so it is used as the
second source rather than the first: cheaper to stay on the scraper while it
works, and this keeps the demo alive when it does not.

    GET https://scrapebadger.com/v1/twitter/trends/place/{woeid}
    headers: {"x-api-key": ...}

Locations are addressed by WOEID (Yahoo's Where-On-Earth ID, which Twitter
adopted and never replaced). India is 23424848; worldwide is 1.
"""

from __future__ import annotations

import time

import requests

from backend.core.logging import get_logger
from backend.mod03.utils.config import settings

log = get_logger("trends.scrapebadger")

# Region name -> WOEID. The app is configured by region name everywhere else,
# so the mapping lives here rather than leaking numeric ids into the config.
WOEID_BY_REGION: dict[str, int] = {
    "india": 23424848,
    "worldwide": 1,
    "united-states": 23424977,
    "united-kingdom": 23424975,
}


class ScrapeBadgerError(RuntimeError):
    """Raised when the fallback cannot produce a usable trend list."""


def woeid_for(region: str) -> int:
    """Resolve a region name to a WOEID.

    An explicit TREND_WOEID always wins, so an unmapped region can be used
    without a code change.
    """

    override = getattr(settings, "trend_woeid", 0)
    if override:
        return int(override)

    key = (region or "").strip().lower().replace(" ", "-")
    if key in WOEID_BY_REGION:
        return WOEID_BY_REGION[key]

    raise ScrapeBadgerError(
        f"No WOEID known for region '{region}'. Set TREND_WOEID in .env "
        f"(India is 23424848), or use one of: {', '.join(WOEID_BY_REGION)}."
    )


def _extract_names(payload) -> list[str]:
    """Pull trend names out of the response.

    The documented shape is ``{"data": [{"name": ...}, ...]}``, but this also
    accepts the nested and bare-list variants that trend APIs commonly return,
    so a small change in their envelope does not take the fallback down with
    it — the whole point of this module is to be the thing that still works.
    """

    def names_from(items) -> list[str]:
        out = []
        for item in items or []:
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                name = item.get("name") or item.get("trend") or item.get("query")
            else:
                name = None
            if name and isinstance(name, str):
                out.append(name.strip())
        return out

    if isinstance(payload, list):
        # Bare list, or Twitter v1.1 style [{"trends": [...]}]
        if payload and isinstance(payload[0], dict) and "trends" in payload[0]:
            return names_from(payload[0]["trends"])
        return names_from(payload)

    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return names_from(data)
        if isinstance(data, dict) and isinstance(data.get("trends"), list):
            return names_from(data["trends"])
        if isinstance(payload.get("trends"), list):
            return names_from(payload["trends"])

    return []


def is_configured() -> bool:
    return bool(getattr(settings, "scrapebadger_api_key", ""))


def fetch_trends(
    region: str = "india",
    timeout: int = 30,
    attempts: int = 2,
) -> list[str]:
    """Return trend names for ``region``. Raises ScrapeBadgerError on failure."""

    api_key = getattr(settings, "scrapebadger_api_key", "")
    if not api_key:
        raise ScrapeBadgerError(
            "SCRAPEBADGER_API_KEY is not set — fallback source unavailable."
        )

    woeid = woeid_for(region)
    base = getattr(settings, "scrapebadger_base_url", "https://scrapebadger.com")
    url = f"{base.rstrip('/')}/v1/twitter/trends/place/{woeid}"
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    last_exc: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            log.info("fetching from ScrapeBadger | region=%s | woeid=%s", region, woeid)
            r = requests.get(url, headers=headers, timeout=timeout)

            if r.status_code in (401, 403):
                # Auth problems never fix themselves on a retry.
                raise ScrapeBadgerError(
                    f"ScrapeBadger rejected the API key (HTTP {r.status_code}). "
                    "Check SCRAPEBADGER_API_KEY in .env."
                )
            if r.status_code == 429:
                raise ScrapeBadgerError("ScrapeBadger rate limit reached (HTTP 429).")
            r.raise_for_status()

            names = _extract_names(r.json())
            if not names:
                raise ScrapeBadgerError(
                    "ScrapeBadger returned no trends — the response shape may "
                    "have changed; check _extract_names()."
                )

            log.info("ScrapeBadger ok | count=%d", len(names))
            return names

        except ScrapeBadgerError:
            raise  # already explanatory, and not worth retrying
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt < attempts:
                log.warning(
                    "ScrapeBadger attempt %d/%d failed (%s) — retrying",
                    attempt, attempts, type(exc).__name__,
                )
                time.sleep(1.0)

    raise ScrapeBadgerError(
        f"ScrapeBadger unreachable after {attempts} attempts: "
        f"{type(last_exc).__name__}: {last_exc}"
    )
