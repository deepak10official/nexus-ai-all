"""Standalone check for the trend-source fallback chain.

Run from the project root:

    python test_fallback.py            # test both sources independently
    python test_fallback.py --chain    # test the real get_feed() chain
    python test_fallback.py --force    # simulate trends24 being down

Nothing here is imported by the app — it is a throwaway diagnostic you can
delete once you are satisfied the fallback works.
"""

from __future__ import annotations

import sys
import time

# Load .env exactly the way the app does.
from backend.mod03.utils.config import settings


def line(char: str = "-") -> None:
    print(char * 72)


def show(label: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------- config ----

def check_config() -> bool:
    line("=")
    print("1. CONFIGURATION")
    line("=")

    sb_key = getattr(settings, "scrapebadger_api_key", "")
    show("TREND_REGION", bool(settings.trend_region), settings.trend_region)
    show(
        "SCRAPEBADGER_API_KEY",
        bool(sb_key),
        f"set ({len(sb_key)} chars)" if sb_key else "MISSING — fallback disabled",
    )

    woeid_override = getattr(settings, "trend_woeid", 0)
    if woeid_override:
        show("TREND_WOEID", True, f"override = {woeid_override}")
    else:
        try:
            from backend.mod03.services.scrapebadger import woeid_for

            show("TREND_WOEID", True, f"resolved from region = {woeid_for(settings.trend_region)}")
        except Exception as exc:
            show("TREND_WOEID", False, str(exc))
            return False

    return bool(sb_key)


# --------------------------------------------------------------- sources ----

def check_trends24() -> bool:
    line("=")
    print("2. PRIMARY SOURCE — trends24")
    line("=")

    from backend.mod03 import trends_html

    started = time.perf_counter()
    try:
        names = trends_html.fetch_trends(settings.trend_region)
        took = time.perf_counter() - started
        show("fetch", True, f"{len(names)} trends in {took:.1f}s")
        print(f"       first 5: {names[:5]}")
        return True
    except Exception as exc:
        took = time.perf_counter() - started
        show("fetch", False, f"{type(exc).__name__} after {took:.1f}s")
        print(f"       {str(exc)[:120]}")
        return False


def check_scrapebadger() -> bool:
    line("=")
    print("3. FALLBACK SOURCE — ScrapeBadger")
    line("=")

    from backend.mod03.services import scrapebadger

    if not scrapebadger.is_configured():
        show("configured", False, "no API key — nothing to test")
        return False

    started = time.perf_counter()
    try:
        names = scrapebadger.fetch_trends(settings.trend_region)
        took = time.perf_counter() - started
        show("fetch", True, f"{len(names)} trends in {took:.1f}s")
        print(f"       first 5: {names[:5]}")
        return True
    except Exception as exc:
        took = time.perf_counter() - started
        show("fetch", False, f"{type(exc).__name__} after {took:.1f}s")
        print(f"       {str(exc)[:200]}")
        return False


def show_raw_response() -> None:
    """Print the raw API envelope — useful if parsing returns nothing."""

    import json

    import requests

    from backend.mod03.services.scrapebadger import woeid_for

    key = getattr(settings, "scrapebadger_api_key", "")
    if not key:
        print("  no API key set")
        return

    woeid = woeid_for(settings.trend_region)
    url = f"https://scrapebadger.com/v1/twitter/trends/place/{woeid}"
    try:
        r = requests.get(url, headers={"x-api-key": key}, timeout=30)
        print(f"  HTTP {r.status_code}")
        body = r.json()
        pretty = json.dumps(body, ensure_ascii=False, indent=2)
        print("  " + "\n  ".join(pretty.splitlines()[:30]))
        if len(pretty.splitlines()) > 30:
            print("  ... (truncated)")
    except Exception as exc:
        print(f"  request failed: {type(exc).__name__}: {exc}")


# ----------------------------------------------------------------- chain ----

def check_chain(force_primary_failure: bool = False) -> None:
    """Exercise the real get_feed() the app uses."""

    line("=")
    print("4. FULL CHAIN — trend_service.get_feed()")
    if force_primary_failure:
        print("   (trends24 monkeypatched to fail, to force the fallback)")
    line("=")

    from backend.mod03.services import trend_service

    if force_primary_failure:
        # Simulate the outage without touching .env or the hosts file.
        from backend.mod03 import trends_html

        def _boom(*_a, **_kw):
            raise ConnectionError("simulated trends24 outage")

        trends_html.fetch_trends = _boom
        trend_service._cache.update({"trends": None, "fetched_at": None, "region": None})

    started = time.perf_counter()
    try:
        feed = trend_service.get_feed(force=True)
        took = time.perf_counter() - started
        tier = feed["tier"]
        source = {
            "live": "trends24 (primary)",
            "api": "ScrapeBadger (fallback)",
            "cache": "cache (last resort)",
        }.get(tier, tier)

        show("get_feed", True, f"tier={tier} -> {source}, {took:.1f}s")
        print(f"       note : {feed['tier_note']}")
        print(f"       count: {len(feed['trends'])} scored trends")
        for t in feed["trends"][:3]:
            print(f"       - {t['name']}  score={t['score']} band={t['band']}")

        if force_primary_failure and tier != "api":
            print()
            print("  !! Expected tier='api' but got '%s'." % tier)
            print("     The fallback did not run — check the log above.")
    except Exception as exc:
        took = time.perf_counter() - started
        show("get_feed", False, f"{type(exc).__name__} after {took:.1f}s")
        print(f"       {str(exc)[:200]}")


# ------------------------------------------------------------------ main ----

def main() -> None:
    args = set(sys.argv[1:])

    print()
    print("TREND SOURCE FALLBACK CHECK")

    if "--raw" in args:
        line("=")
        print("RAW SCRAPEBADGER RESPONSE")
        line("=")
        show_raw_response()
        print()
        return

    has_key = check_config()

    if "--chain" in args or "--force" in args:
        check_chain(force_primary_failure="--force" in args)
    else:
        primary_ok = check_trends24()
        fallback_ok = check_scrapebadger()

        line("=")
        print("SUMMARY")
        line("=")
        if primary_ok and fallback_ok:
            print("  Both sources work. The chain will use trends24 and fall")
            print("  back to ScrapeBadger only when it has to.")
        elif primary_ok and not fallback_ok:
            print("  Primary works, fallback does NOT.")
            print("  You are fine today but unprotected when trends24 fails.")
            if has_key:
                print("  Run with --raw to see what the API actually returned.")
        elif fallback_ok:
            print("  Primary is down, fallback works — the chain will serve")
            print("  trends from ScrapeBadger. This is the design working.")
        else:
            print("  Neither source is reachable. Check network access.")

        print()
        print("  Next: python test_fallback.py --force")
        print("        (simulates a trends24 outage and runs the real chain)")

    print()


if __name__ == "__main__":
    main()
