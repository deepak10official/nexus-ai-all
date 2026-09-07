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


# ---------------------------------------------------------------------------
# Caption-level English detection
#
# ``detect()`` above is built for trend names: one to three words, where
# "whichever script has the most characters wins" is a sound rule. Captions
# break that rule badly. A Gujarati caption ending in English hashtags
# ("18 વર્ષથી ઓછી ઉંમરના પણ upi વાપરી શકશે . #Banking #BankingTips #UPI")
# can carry more Latin characters than Gujarati ones, so a max-count vote
# would call it English.
#
# So captions are judged differently: strip everything that is not prose —
# hashtags, @mentions, URLs, emoji, digits, punctuation — then reject if any
# meaningful non-Latin script remains. A genuinely English caption has
# essentially zero Devanagari.
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HASHTAG_RE = re.compile(r"[#＃][^\s#＃]+")
_MENTION_RE = re.compile(r"@[A-Za-z0-9._]+")

# Any codepoint inside a known Indic/Arabic block.
_NON_LATIN_RANGES = [(lo, hi) for _c, _l, _s, lo, hi in SCRIPT_RANGES]

# Proportion of prose that may be non-Latin before a caption is rejected.
# Not zero: a single stray character (a name, a quoted word) should not
# disqualify an otherwise English caption.
_NON_LATIN_TOLERANCE = 0.05


def caption_prose(text: str) -> str:
    """Strip a caption down to the part that actually carries language.

    Hashtags are removed because they are routinely English on non-English
    posts — they are tags, not prose, and including them is what makes naive
    detection fail.
    """

    if not text:
        return ""
    out = _URL_RE.sub(" ", text)
    out = _HASHTAG_RE.sub(" ", out)
    out = _MENTION_RE.sub(" ", out)
    # Keep letters and spaces only: drops emoji, digits and punctuation
    # without needing to enumerate emoji blocks.
    out = "".join(ch if (ch.isalpha() or ch.isspace()) else " " for ch in out)
    return re.sub(r"\s+", " ", out).strip()


def _non_latin_ratio(prose: str) -> float:
    letters = [ch for ch in prose if ch.isalpha()]
    if not letters:
        return 0.0
    hits = 0
    for ch in letters:
        cp = ord(ch)
        for lo, hi in _NON_LATIN_RANGES:
            if lo <= cp <= hi:
                hits += 1
                break
    return hits / len(letters)


def is_english_caption(text: str, min_words: int = 3) -> tuple[bool, str]:
    """Is this caption usable English prose? Returns (verdict, reason).

    The reason is returned so a rejection can be logged and explained rather
    than silently dropping someone's post from the reference set.
    """

    prose = caption_prose(text)
    if not prose:
        return False, "no prose (hashtags/emoji only)"

    words = prose.split()
    if len(words) < min_words:
        # Too short to judge. Excluded deliberately: a two-word caption adds
        # nothing as drafting context anyway.
        return False, f"too short ({len(words)} words)"

    ratio = _non_latin_ratio(prose)
    if ratio > _NON_LATIN_TOLERANCE:
        return False, f"non-Latin script ({ratio:.0%} of letters)"

    flat = re.sub(r"[\s_\-]+", "", prose.lower())
    for marker in ROMANISED_HINDI:
        if marker in flat:
            return False, f"romanised Hindi ('{marker}')"

    return True, "English"


def english_captions(items: list[dict], caption_key: str = "caption") -> list[dict]:
    """Keep only the items whose caption reads as English prose."""

    return [it for it in items if is_english_caption(it.get(caption_key) or "")[0]]
