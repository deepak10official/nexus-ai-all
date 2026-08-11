"""
Category classification for trends.

Same design philosophy as scoring.py: rule-based and auditable, not an LLM
call. A stakeholder can read this file and see exactly why a hashtag was
filed under Politics. It also runs in microseconds, which matters when
every scan classifies fifty trends.

Each category carries English AND Devanagari keyword sets, so a Hindi
hashtag classifies as accurately as an English one. Categories are scored
by weight rather than first-match, so a trend touching several categories
lands in the strongest rather than whichever was checked first.
"""

import re

# (label, accent-key for the UI, keywords)
CATEGORIES: dict[str, tuple[str, list[str]]] = {
    "Business & Finance": ("finance", [
        # English
        "bank", "finance", "financial", "economy", "economic", "market",
        "stock", "sensex", "nifty", "rupee", "gdp", "budget", "tax", "gst",
        "investment", "invest", "loan", "emi", "insurance", "premium",
        "payment", "upi", "fintech", "wallet", "transaction", "bill",
        "billpay", "recharge", "npci", "rbi", "rupay", "ipo", "startup",
        "business", "trade", "revenue", "inflation", "cashless", "fastag",
        "electricity", "broadband", "dth", "utility", "postpaid", "prepaid",
        "creditcard", "debitcard", "netbanking", "mutualfund",
        # Markets and corporate finance
        "sensex", "nifty", "bse", "nse", "share", "shares", "equity",
        "trading", "trader", "dividend", "portfolio", "bull", "bear",
        "pennystock", "smallcap", "midcap", "largecap", "bluechip",
        "earnings", "quarterly", "profit", "merger", "acquisition",
        "valuation", "funding", "venture", "unicorn", "gdp", "fdi",
        "commodity", "bullion", "forex", "bond", "yield", "repo",
        # Hindi
        "शेयर", "बाजार", "मुनाफा", "निवेशक", "सोना",
        # Hindi
        "बैंक", "वित्त", "अर्थव्यवस्था", "बाजार", "रुपया", "बजट", "कर",
        "टैक्स", "निवेश", "कर्ज", "बीमा", "भुगतान", "पेमेंट", "बिल",
        "रिचार्ज", "व्यापार", "महंगाई", "यूपीआई",
    ]),
    "Technology": ("tech", [
        "tech", "technology", "ai", "artificial", "software", "app",
        "digital", "internet", "cyber", "data", "cloud", "startup",
        "smartphone", "android", "iphone", "google", "chip", "semiconductor",
        "crypto", "blockchain", "5g", "6g", "innovation", "ondc", "aadhaar",
        # Indian IT and consumer tech, which trend constantly
        "infosys", "wipro", "tcs", "hcl", "techm", "zoho", "jio",
        "galaxy", "pixel", "oneplus", "realme", "xiaomi", "laptop",
        "gadget", "chatgpt", "gemini", "llm", "chip", "gpu", "saas",
        "cloudcomputing", "cybersecurity", "datacentre", "datacenter",
        "automation", "robotics", "quantum", "developer", "coding",
        "तकनीक", "डिजिटल", "इंटरनेट", "मोबाइल", "ऐप", "साइबर",
    ]),
    "Sports": ("sport", [
        "cricket", "ipl", "match", "test", "odi", "t20", "wicket", "innings",
        "football", "fifa", "hockey", "kabaddi", "olympic", "tournament",
        "worldcup", "series", "score", "captain", "bowler", "batsman",
        "tennis", "badminton", "athletics", "medal", "champion", "league",
        "खेल", "क्रिकेट", "मैच", "फुटबॉल", "हॉकी", "विकेट", "टीम",
    ]),
    "Entertainment": ("ent", [
        "film", "movie", "cinema", "bollywood", "tollywood", "trailer",
        "teaser", "song", "music", "album", "actor", "actress", "boxoffice",
        "netflix", "series", "episode", "biggboss", "celebrity", "star",
        "release", "review", "ott", "singer", "dance", "show",
        "फिल्म", "सिनेमा", "गाना", "संगीत", "अभिनेता", "बॉलीवुड", "शो",
    ]),
    "Politics": ("pol", [
        "election", "vote", "poll", "party", "minister", "parliament",
        "government", "govt", "cabinet", "opposition",
        "campaign", "manifesto", "constituency", "assembly", "sansad",
        "chunav", "sarkar", "neta", "bjp", "congress", "modi", "rahul",
        "चुनाव", "सरकार", "मंत्री", "संसद", "पार्टी", "राजनीति", "मतदान",
        "नेता", "विपक्ष",
    ]),
    "Government & Policy": ("gov", [
        "scheme", "yojana", "subsidy", "welfare", "ministry", "department",
        "digitalindia", "डिजिटलइंडिया", "atmanirbhar", "makeinindia",
        "startupindia",
        "swachh", "ayushman", "pension", "ration", "census", "reform",
        "योजना", "सब्सिडी", "मंत्रालय", "विभाग", "सुधार", "पेंशन",
    ]),
    "Health": ("health", [
        "health", "hospital", "doctor", "medical", "medicine", "vaccine",
        "disease", "covid", "dengue", "fever", "patient", "surgery",
        "mental", "fitness", "nutrition", "ayush", "wellness",
        "स्वास्थ्य", "अस्पताल", "डॉक्टर", "दवा", "बीमारी", "टीका",
    ]),
    "Education": ("edu", [
        "education", "school", "college", "university", "exam", "result",
        "student", "teacher", "admission", "neet", "jee", "upsc", "cbse",
        "scholarship", "syllabus", "board", "degree", "iit", "nit",
        "शिक्षा", "स्कूल", "कॉलेज", "परीक्षा", "छात्र", "शिक्षक", "परिणाम",
    ]),
    "Religion & Culture": ("rel", [
        "temple", "mandir", "mosque", "masjid", "church", "festival",
        "diwali", "holi", "eid", "christmas", "navratri", "puja", "prayer",
        "yatra", "tyohar", "dharm", "spiritual", "tradition", "heritage",
        "मंदिर", "मस्जिद", "त्योहार", "पूजा", "दिवाली", "होली", "धर्म",
        "यात्रा", "जय", "श्री",
    ]),
    "News & Current Affairs": ("news", [
        "breaking", "news", "update", "report", "alert", "live", "today",
        "weather", "rain", "flood", "cyclone", "earthquake", "accident",
        "protest", "andolan", "strike", "bandh", "crime", "police", "court",
        "verdict", "arrest", "investigation",
        "समाचार", "खबर", "मौसम", "बारिश", "बाढ़", "पुलिस", "अदालत",
        "आंदोलन", "हड़ताल",
    ]),
}

DEFAULT_CATEGORY = "Other"
DEFAULT_KEY = "other"


def _flatten(text: str) -> str:
    return re.sub(r"[\s_\-#.,!?'\"]+", "", text.lower())


def _hit(term: str, raw: str, flat: str) -> bool:
    """Mirrors scoring._matches — short ASCII terms need a boundary or a
    leading-prefix match, everything else is substring on the flattened
    form. Keeps 'ai' out of 'Chennai' and 'test' out of 'Contest'."""
    t = term.lower()
    if t.isascii() and len(t) < 5:
        if re.search(rf"\b{re.escape(t)}\b", raw):
            return True
        return flat.startswith(_flatten(t))
    return _flatten(t) in flat


def classify(name: str) -> dict:
    """
    Returns {category, key, matched, alternatives}.

    Scores every category by how many of its keywords match, then takes
    the strongest. Ties break toward the category with the longer matched
    keyword, since longer matches are more specific and less accidental.
    """
    raw, flat = name.lower(), _flatten(name)

    scores: dict[str, tuple[int, int, str]] = {}
    for label, (_key, terms) in CATEGORIES.items():
        matched = [t for t in terms if _hit(t, raw, flat)]
        if matched:
            longest = max(matched, key=len)
            scores[label] = (len(matched), len(longest), longest)

    if not scores:
        return {
            "category": DEFAULT_CATEGORY,
            "key": DEFAULT_KEY,
            "matched": None,
            "alternatives": [],
        }

    ranked = sorted(scores.items(), key=lambda kv: (kv[1][0], kv[1][1]), reverse=True)
    top_label, (_count, _len, top_term) = ranked[0]

    return {
        "category": top_label,
        "key": CATEGORIES[top_label][0],
        "matched": top_term,
        "alternatives": [label for label, _ in ranked[1:3]],
    }
