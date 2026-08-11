"""
BBPS Relevance Score (0-100) and the off-limits filter.

Deliberately rule-based rather than an LLM call: a stakeholder can read
this file and see exactly why a trend scored what it did, and compliance
can audit the blocklist line by line. Bands come from the MOD03 spec.

The blocklist runs BEFORE scoring. A blocked trend never reaches the LLM,
regardless of how relevant it looks.

KNOWN LIMITATION — read before shipping:
Hashtags concatenate words (#RamMandir), so word boundaries often do not
exist, and naive substring matching produces false positives ("ram" inside
"Akram"). The matcher below uses word boundaries for short ASCII terms plus
a leading-prefix allowance, which handles the common cases but is not
airtight. Treat this list as a first pass that a human curates, not as a
compliance control. Government-programme hashtags in particular sit on a
genuinely ambiguous line between "civic" and "political" and need an
explicit allowlist decision from the brand team.
"""

import re

from backend.mod03.utils.categories import classify
from backend.mod03.utils.language import detect as detect_language

# ───────────────────────── off-limits (spec) ─────────────────────────

BLOCKLIST = {
    "political": [
        "bjp", "congress", "aap", "tmc", "dmk", "aiadmk", "brs", "trs",
        "shivsena", "ncp", "rjd", "jdu", "bsp", "cpim", "cpi",
        "modi", "rahul", "kejriwal", "mamata", "yogi", "amitshah",
        "election", "chunav", "मतदान", "चुनाव", "सरकार",
        "minister", "parliament", "sansad", "संसद", "govt",
    ],
    "religious": [
        "hindu", "muslim", "islam", "christian", "sikh", "jain", "buddh",
        "temple", "mosque", "church", "mandir", "masjid", "puja", "namaz",
        "ram", "allah", "jesus", "hanukkah", "diwali", "eid", "christmas",
        "godmorning", "जय", "श्री", "भगवान",
    ],
    "protest": [
        "protest", "andolan", "आंदोलन", "bandh", "strike", "dharna",
        "morcha", "मार्च", "agitation", "boycott", "resign", "arrest",
    ],
    "security": [
        "terror", "attack", "blast", "army", "military", "border",
        "pakistan", "martyr", "encounter", "naxal", "defence", "defense",
    ],
    "competitor": [
        "hdfc", "icici", "axis", "kotak", "sbi", "paytm", "phonepe",
        "gpay", "googlepay", "amazonpay", "mobikwik", "freecharge",
        "razorpay", "billdesk", "payu", "airtelmoney", "jiopay",
    ],
}

# ───────────────────────── relevance signals ─────────────────────────
# Each category has a base score. A trend takes the highest base it hits,
# then earns a bonus for every ADDITIONAL category it touches. That rewards
# trends relevant along several axes at once, which is what actually makes
# a reactive post work.

CATEGORIES: dict[str, tuple[int, list[str]]] = {
    "core": (80, [
        "bbps", "bharatconnect", "bharat connect", "billpay", "billpayment",
        "bill payment", "recharge", "utility bill",
        # Hindi
        "बिलभुगतान", "बिल भुगतान", "रिचार्ज", "भारतकनेक्ट",
    ]),
    "payments": (72, [
        "upi", "digitalpayment", "payment", "fintech", "npci", "rupay",
        "wallet", "cashless", "autopay", "emandate", "transaction",
        # Hindi
        "यूपीआई", "भुगतान", "पेमेंट", "डिजिटलपेमेंट", "नकदरहित", "लेनदेन",
    ]),
    "digital-india": (68, [
        "digitalindia", "digital india", "ondc", "financialinclusion",
        "aadhaar", "atmanirbhar", "startupindia", "msme", "ruralindia",
        # Hindi
        "डिजिटलइंडिया", "डिजिटल इंडिया", "आधार", "आत्मनिर्भर",
        "वित्तीयसमावेशन",
    ]),
    "finance": (58, [
        "finance", "banking", "rbi", "emi", "insurance", "loan", "savings",
        "gst", "invoice", "electricity", "broadband", "fastag", "dth",
        "water bill", "gas bill", "subscription", "premium", "tax",
        # Hindi
        "बैंक", "बीमा", "बिजली", "पानी", "गैस", "कर्ज", "किस्त", "टैक्स",
        "चालान", "वित्त",
    ]),
    "india-context": (25, [
        "india", "indian", "bharat", "भारत", "इंडिया", "देश", "desi",
    ]),
}

# Sector adjacency.
#
# A trend can be squarely in Bharat Connect's world without containing any
# payments keyword — #SensexToday, #Nifty50, #TechLayoffs. Previously those
# were classified correctly as Business & Finance or Technology and then
# scored 0, because the keyword lists only knew about bill payments. The
# classifier and the scorer disagreed.
#
# These floors bridge the two: a trend whose CATEGORY is adjacent to the
# brand's sector earns a base score even with no keyword hit. Payments
# keywords still score higher, so genuinely on-topic trends still outrank
# merely sector-adjacent ones.
SECTOR_FLOORS = {
    "Business & Finance": 62,
    "Technology": 60,
}

EXTRA_CATEGORY_BONUS = 8
MAX_CATEGORY_BONUS = 24
HASHTAG_BONUS = 5

# Entertainment and sport rarely fit a payments brand and burn reviewer
# time. Penalised, not blocked.
DILUTION = {
    "ipl": -25, "cricket": -20, "bollywood": -25, "trailer": -25,
    "boxoffice": -25, "biggboss": -30, "fifa": -25, "worldcup": -15,
    "episode": -20, "teaser": -25, "boxing": -20,
}

BANDS = [(80, "auto_draft"), (60, "review"), (40, "monitor"), (0, "ignore")]

BAND_LABELS = {
    "auto_draft": "Auto-draft immediately",
    "review": "Draft, flag for human review",
    "monitor": "Monitor only, no draft",
    "ignore": "Below threshold, ignored",
    "blocked": "Off-limits, never drafted",
}

# The action the pipeline takes, driven entirely by the band. Kept
# separate from the band so the UI can show "what it is" and "what
# happens next" as two distinct columns.
BAND_ACTIONS = {
    "auto_draft": "AUTO_DRAFT",
    "review": "HUMAN_REVIEW",
    "monitor": "MONITOR",
    "ignore": "IGNORE",
    "blocked": "BLOCKED",
}

BAND_RANGES = {
    "auto_draft": "80-100",
    "review": "60-79",
    "monitor": "40-59",
    "ignore": "0-39",
    "blocked": "n/a",
}


def _flatten(text: str) -> str:
    """#Digital_India-2026 -> 'digitalindia2026'."""
    return re.sub(r"[\s_\-#.,!?'\"]+", "", text.lower())


def _matches(term: str, raw: str, flat: str) -> bool:
    """
    Short ASCII terms collide badly inside concatenated hashtags, so they
    need either a real word boundary or a leading-prefix match:
        'ram' vs 'Naveed Akram' -> no match  (correct)
        'ram' vs '#RamMandir'   -> match     (correct)
    Longer and non-ASCII terms use substring on the flattened form, since
    collisions are unlikely and Devanagari has no reliable word boundaries
    inside hashtags.
    """
    t = term.lower()
    if t.isascii() and len(t) < 5:
        if re.search(rf"\b{re.escape(t)}\b", raw):
            return True
        return flat.startswith(_flatten(t))
    return _flatten(t) in flat


def check_blocked(name: str) -> tuple[bool, str | None, str | None]:
    raw, flat = name.lower(), _flatten(name)
    for category, terms in BLOCKLIST.items():
        for term in terms:
            if _matches(term, raw, flat):
                return True, category, term
    return False, None, None


def score_trend(name: str, topic_category: str | None = None) -> tuple[int, str]:
    raw, flat = name.lower(), _flatten(name)

    hit_bases: list[int] = []
    hits: list[str] = []

    for cat, (base, terms) in CATEGORIES.items():
        matched = next((t for t in terms if _matches(t, raw, flat)), None)
        if matched:
            hit_bases.append(base)
            hits.append(f"{cat}:{matched}")

    # Sector floor applies whether or not keywords hit, so a business or
    # technology trend is never silently ignored.
    floor = SECTOR_FLOORS.get(topic_category or "")
    if floor:
        hit_bases.append(floor)
        hits.append(f"sector:{topic_category.lower()}")

    if not hit_bases:
        penalty = sum(w for t, w in DILUTION.items() if _matches(t, raw, flat))
        note = "no BBPS-adjacent signals"
        if penalty:
            note += f", off-territory content ({penalty})"
        return 0, note

    score = max(hit_bases)
    extra = min((len(hit_bases) - 1) * EXTRA_CATEGORY_BONUS, MAX_CATEGORY_BONUS)
    if extra:
        score += extra
        hits.append(f"+{extra} across {len(hit_bases)} categories")

    if name.startswith("#"):
        score += HASHTAG_BONUS
        hits.append(f"+{HASHTAG_BONUS} joinable hashtag")

    for term, weight in DILUTION.items():
        if _matches(term, raw, flat):
            score += weight
            hits.append(f"{weight} off-territory:{term}")

    return max(0, min(100, score)), ", ".join(hits)


def band_for(score: int) -> str:
    for threshold, key in BANDS:
        if score >= threshold:
            return key
    return "ignore"


def evaluate(name: str) -> dict:
    """
    Full pipeline for one trend, in order:
        1. detect language (so Hindi keywords are in play)
        2. classify category (runs even for blocked trends — a stakeholder
           still wants to see WHAT was blocked, not just that it was)
        3. off-limits check
        4. relevance score and band
        5. action, derived from the band
    """
    lang = detect_language(name)
    cat = classify(name)

    blocked, blocked_cat, term = check_blocked(name)
    if blocked:
        return {
            "name": name,
            "is_hashtag": name.startswith("#"),
            "language": lang["code"],
            "language_label": lang["label"],
            "script": lang["script"],
            "language_confidence": lang["confidence"],
            "category": cat["category"],
            "category_key": cat["key"],
            "score": 0,
            "band": "blocked",
            "action": BAND_ACTIONS["blocked"],
            "band_range": BAND_RANGES["blocked"],
            "rationale": f"Off-limits: {blocked_cat} (matched '{term}')",
            "blocked_reason": blocked_cat,
        }

    score, rationale = score_trend(name, cat["category"])
    band = band_for(score)
    return {
        "name": name,
        "is_hashtag": name.startswith("#"),
        "language": lang["code"],
        "language_label": lang["label"],
        "script": lang["script"],
        "language_confidence": lang["confidence"],
        "category": cat["category"],
        "category_key": cat["key"],
        "score": score,
        "band": band,
        "action": BAND_ACTIONS[band],
        "band_range": BAND_RANGES[band],
        "rationale": rationale,
        "blocked_reason": None,
    }
