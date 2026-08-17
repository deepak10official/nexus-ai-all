"""
Trend scraper for X/Twitter India, via trends24.in.

This is the original Trendshtml.py, refactored so the agent can import
fetch_trends() instead of shelling out. Still runnable standalone:

    python trends_html.py
"""

import json

import time

import requests

from backend.core.logging import get_logger
from bs4 import BeautifulSoup

log = get_logger("trends.scrape")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Charset": "utf-8",
}


def parse_latest(html: str) -> list[str]:
    """
    trends24 renders one card per time slice, newest first. Scope to the
    first card so we get 'right now' rather than 24 hours merged together.
    """
    soup = BeautifulSoup(html, "html.parser")

    card = soup.select_one(".trend-card__list") or soup.find("ol")
    if card:
        names = [a.get_text(strip=True) for a in card.select("a")]
        names = [n for n in names if n]
        if names:
            return names

    # Fallback if class names change: every plausible anchor, deduped.
    seen, names = set(), []
    for a in soup.select("a"):
        txt = a.get_text(strip=True)
        if txt and txt not in seen and 1 < len(txt) < 80:
            seen.add(txt)
            names.append(txt)
    return names


def fetch_trends(
    region: str = "india",
    timeout: int = 45,
    attempts: int = 2,
) -> list[str]:
    """Raise on failure — the caller decides how to degrade.

    trends24 is often slow rather than down, so a single short timeout reports
    an outage that is really just latency. One retry with a longer window
    recovers most of those without making a real failure much slower.
    """

    url = f"https://trends24.in/{region}/"
    last_exc: Exception | None = None

    for attempt in range(1, max(1, attempts) + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            break
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < attempts:
                log.warning(
                    "trends24 attempt %d/%d failed (%s) — retrying",
                    attempt, attempts, type(exc).__name__,
                )
                time.sleep(1.5)
    else:
        raise last_exc  # every attempt failed

    # THE fix for broken Hindi. When a server omits charset from the
    # Content-Type header, requests falls back to ISO-8859-1 per the old
    # HTTP spec, and every Devanagari byte gets decoded as Latin-1 —
    # भारत arrives as à¤­à¤¾à¤°à¤¤. Forcing UTF-8 before touching .text
    # fixes it at the source. apparent_encoding (chardet) is the fallback
    # if the page ever genuinely is not UTF-8.
    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "latin-1", "ascii"):
        r.encoding = r.apparent_encoding or "utf-8"

    trends = parse_latest(r.text)
    if not trends:
        raise ValueError(f"Parsed zero trends from {url} — page structure changed")
    return trends


if __name__ == "__main__":
    items = fetch_trends()
    tags = [t for t in items if t.startswith("#")]
    print(f"{len(items)} trends, {len(tags)} hashtags\n")
    for t in items:
        print(" ", t)
    with open("hashtags.json", "w", encoding="utf-8") as f:
        json.dump({"hashtags": tags, "all": items}, f, ensure_ascii=False, indent=2)
