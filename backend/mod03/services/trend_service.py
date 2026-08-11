"""
Trend feeder. Wraps trends_html.fetch_trends() with a cache tier so a
transient scrape failure during a live demo degrades to the last good
result rather than an empty screen. The tier is reported to the UI so
nobody is misled about how fresh the data is.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# trends_html is a proper module of this package after the merge, so it is
# imported normally rather than via a sys.path insert.
from backend.mod03 import trends_html  # noqa: E402

from backend.mod03.utils.config import settings  # noqa: E402
from backend.core.logging import get_logger  # noqa: E402
from backend.mod03.services.scoring import evaluate  # noqa: E402

log = get_logger("trends")

_cache: dict = {"trends": None, "fetched_at": None, "region": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_feed(force: bool = False) -> dict:
    region = settings.trend_region
    ttl = timedelta(minutes=settings.trend_cache_minutes)

    fresh_enough = (
        not force
        and _cache["trends"]
        and _cache["region"] == region
        and _cache["fetched_at"]
        and _now() - _cache["fetched_at"] < ttl
    )
    if fresh_enough:
        age = int((_now() - _cache["fetched_at"]).total_seconds())
        log.info("serving cached trends | region=%s | age=%ss | count=%d",
                 region, age, len(_cache["trends"]))
        return _build(region, _cache["trends"], _cache["fetched_at"], "cache",
                      f"Served from cache, under {settings.trend_cache_minutes} min old")

    log.info("fetching live trends | region=%s | force=%s", region, force)
    try:
        started = _now()
        names = trends_html.fetch_trends(region)
        took = (_now() - started).total_seconds()
        _cache.update({"trends": names, "fetched_at": _now(), "region": region})
        log.info("live fetch ok | count=%d | %.2fs", len(names), took)
        log.debug("trend names: %s", names)
        return _build(region, names, _cache["fetched_at"], "live",
                      "Scraped live from trends24")
    except Exception as e:  # noqa: BLE001
        log.error("live fetch failed | %s: %s", type(e).__name__, e)
        if _cache["trends"]:
            log.warning("FALLBACK to cached trends | count=%d | cached_at=%s",
                        len(_cache["trends"]), _cache["fetched_at"])
            return _build(
                region, _cache["trends"], _cache["fetched_at"], "cache",
                f"Live scrape failed ({type(e).__name__}), serving last good result",
            )
        log.critical("no cached trends available — request will fail")
        raise


def _build(region: str, names: list[str], fetched_at: datetime,
           tier: str, note: str) -> dict:
    scored = [evaluate(n) for n in names]
    bands: dict[str, int] = {}
    for t in scored:
        bands[t["band"]] = bands.get(t["band"], 0) + 1
    log.info("scored %d trends | %s", len(scored),
             ", ".join(f"{k}={v}" for k, v in sorted(bands.items())))
    for t in scored:
        # Per-trend detail at DEBUG — fifty lines an INFO trace does not need,
        # but exactly what you want when a score looks wrong.
        log.debug("  %-28s %-20s %3d %-12s %s", t["name"][:28], t["category"],
                  t["score"], t["band"], t["rationale"])
    # Highest relevance first; blocked items sink to the bottom.
    scored.sort(key=lambda t: (t["band"] == "blocked", -t["score"]))
    return {
        "region": region,
        "fetched_at": fetched_at,
        "tier": tier,
        "tier_note": note,
        "trends": scored,
    }


def find(name: str) -> dict | None:
    feed = get_feed()
    for t in feed["trends"]:
        if t["name"].lower() == name.lower():
            return t
    return None


def neighbours_of(name: str, limit: int = 6) -> list[str]:
    feed = get_feed()
    return [t["name"] for t in feed["trends"] if t["name"] != name][:limit]
