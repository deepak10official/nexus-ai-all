"""
Language detection for trend names.

Deliberately script-based rather than statistical. Trend names are one to
three words long — far too short for statistical language ID to be
reliable, and a wrong guess is worse than an honest one. Unicode block
detection is deterministic and cannot be wrong about which script it saw.

The honest caveat, surfaced in the UI: script is not language. Devanagari
is shared by Hindi, Marathi, Nepali, Sanskrit and others, so a Devanagari
trend is reported as "Hindi (Devanagari)" on the reasonable assumption
that India-region trends in that script are usually Hindi. Do not treat
the code as a verified language tag.
"""

import re

# Unicode blocks for the scripts that actually appear in Indian trends.
SCRIPT_RANGES: list[tuple[str, str, str, int, int]] = [
    # (code, label, script, start, end)
    ("hi", "Hindi (Devanagari)", "Devanagari", 0x0900, 0x097F),
    ("bn", "Bengali", "Bengali", 0x0980, 0x09FF),
    ("pa", "Punjabi (Gurmukhi)", "Gurmukhi", 0x0A00, 0x0A7F),
    ("gu", "Gujarati", "Gujarati", 0x0A80, 0x0AFF),
    ("or", "Odia", "Odia", 0x0B00, 0x0B7F),
    ("ta", "Tamil", "Tamil", 0x0B80, 0x0BFF),
    ("te", "Telugu", "Telugu", 0x0C00, 0x0C7F),
    ("kn", "Kannada", "Kannada", 0x0C80, 0x0CFF),
    ("ml", "Malayalam", "Malayalam", 0x0D00, 0x0D7F),
    ("ur", "Urdu (Arabic)", "Arabic", 0x0600, 0x06FF),
]

# Romanised Hindi/Hinglish markers. A trend written in Latin script but
# lexically Hindi ("#KisanAndolan", "#SarkarKaFaisla") should not be
# labelled English — the scorer needs to know to try Hindi keywords too.
ROMANISED_HINDI = [
    "bharat", "sarkar", "chunav", "andolan", "bandh", "mahila", "kisan",
    "yuva", "vikas", "yojana", "adhikar", "samman", "seva", "desh",
    "janata", "neta", "paisa", "rupaye", "bijli", "pani",
    "vyapar", "shiksha", "swasthya", "khel", "dharm", "tyohar",
    "namaskar", "dhanyavad", "zindabad", "murdabad",
]


def detect(text: str) -> dict:
    """
    Returns {code, label, script, confidence}.

    confidence is "high" for script detection (deterministic), "low" for
    the romanised-Hindi heuristic (a guess from a small word list).
    """
    counts: dict[tuple[str, str, str], int] = {}

    for ch in text:
        cp = ord(ch)
        for code, label, script, lo, hi in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[(code, label, script)] = counts.get((code, label, script), 0) + 1
                break

    if counts:
        (code, label, script), _n = max(counts.items(), key=lambda kv: kv[1])
        return {
            "code": code,
            "label": label,
            "script": script,
            "confidence": "high",
        }

    # Latin script — English, or romanised Indian language?
    flat = re.sub(r"[\s_\-#]+", "", text.lower())
    if any(marker in flat for marker in ROMANISED_HINDI):
        return {
            "code": "hi-Latn",
            "label": "Hindi (romanised)",
            "script": "Latin",
            "confidence": "low",
        }

    return {"code": "en", "label": "English", "script": "Latin", "confidence": "high"}


def is_indic(lang: dict) -> bool:
    """True when the scorer should also try its Hindi keyword lists."""
    return lang["code"] not in ("en",)
