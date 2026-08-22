"""
outlook.py
Rolls transit + air quality + pollen into ONE overall "how's today looking"
verdict -- the plain-language read a first-time visitor should get in under
three seconds, before they've looked at a single number.

Pure logic, no Streamlit dependency (same pattern as briefing.py) so it's
easy to unit-test on its own. app.py calls compute_outlook() once, right
alongside its other "compute once per run" values, and both the headline
banner and the three status tiles render straight from what it returns --
so nothing on the page can ever show a "day is clear" headline next to a
tile calling out a major delay.

The three inputs already carry their own tier somewhere inside them
(transit_status["level"], aqi_reading["label"], pollen_reading["category"])
-- this module's only job is mapping each of those onto the same
good/caution/hazard scale and taking the worst of the three, since a single
hazard anywhere (a major delay, unhealthy air, extreme pollen) is what
should drive the headline, not an average that could paper over it.
"""

TIER_ORDER = ["good", "caution", "hazard"]  # index = severity rank, higher = worse

HEADLINES = {
    "good": "Your Day Is Clear — Go",
    "caution": "Keep An Eye Out Today",
    "hazard": "Take It Slow Today",
}

SUBTEXT_LEAD = {
    "good": "Nothing standing between you and your plans.",
    "caution": "Mostly fine, but a couple of things are worth a glance.",
    "hazard": "At least one thing today needs real attention before you head out.",
}

# Deep, saturated gradient per tier for the banner -- these intentionally
# don't reuse the softer pastel card colors elsewhere on the page; the
# banner is meant to read instantly from across the room.
TIER_COLORS = {
    "good": {
        "gradient": "linear-gradient(120deg, #0ca34a 0%, #16a34a 55%, #0d9488 100%)",
        "text": "#ffffff",
        "sub_text": "rgba(255,255,255,0.92)",
    },
    "caution": {
        "gradient": "linear-gradient(120deg, #f2b705 0%, #f59e0b 55%, #ea8a06 100%)",
        "text": "#2b1d00",
        "sub_text": "rgba(43,29,0,0.82)",
    },
    "hazard": {
        "gradient": "linear-gradient(120deg, #dc2626 0%, #b91c1c 55%, #7f1d1d 100%)",
        "text": "#ffffff",
        "sub_text": "rgba(255,255,255,0.92)",
    },
}


def _transit_tier(transit_status: dict) -> str:
    level = (transit_status or {}).get("level")
    if level == "smooth":
        return "good"
    if level == "minor":
        return "caution"
    if level == "major":
        return "hazard"
    return "caution"  # unavailable data reads as "worth a glance", not "all clear"


def _aqi_tier(aqi_reading: dict) -> str:
    label = (aqi_reading or {}).get("label")
    if label == "Good":
        return "good"
    if label in ("Moderate", "Unhealthy for Sensitive Groups"):
        return "caution"
    if label in ("Unhealthy", "Very Unhealthy", "Hazardous"):
        return "hazard"
    return "caution"  # "No data" -- same reasoning as transit above


def _pollen_tier(pollen_reading: dict) -> str:
    category = (pollen_reading or {}).get("category")
    if category == "Low":
        return "good"
    if category in ("Moderate", "High"):
        return "caution"
    if category in ("Very High", "Extreme"):
        return "hazard"
    return "caution"


def _transit_fragment(transit_status: dict, tier: str) -> str:
    outages = (transit_status or {}).get("elevator_outages", 0) or 0
    if tier == "good":
        return "0 transit delays"
    level = (transit_status or {}).get("level")
    if level == "major":
        base = "significant transit delays"
    elif level == "minor":
        base = "minor transit delays"
    else:
        base = "transit status unavailable"
    if outages:
        base += f" · {outages} elevator outage{'s' if outages != 1 else ''}"
    return base


def _aqi_fragment(aqi_reading: dict) -> str:
    label = (aqi_reading or {}).get("label", "No data")
    if label == "No data":
        return "Air quality data unavailable"
    return f"Air quality is {label.lower()}"


def _pollen_fragment(pollen_reading: dict) -> str:
    category = (pollen_reading or {}).get("category")
    if not category:
        return "Pollen data unavailable"
    return f"Pollen is {category.lower()}"


def compute_outlook(transit_status: dict, aqi_reading: dict, pollen_reading: dict) -> dict:
    """The single source of truth for the "Aha" banner. Returns:
        tier      -- 'good' | 'caution' | 'hazard', the worst of the three inputs
        headline  -- short, bold verdict for that tier
        subtext   -- one line stitching the three real fragments together,
                     e.g. "Air quality is great · 0 transit delays · Pollen is low"
        colors    -- TIER_COLORS[tier], ready to drop into the banner's CSS
        tiers     -- {'transit': ..., 'aqi': ..., 'pollen': ...} so callers
                     (the three status tiles) can color each one individually
                     without re-deriving the same logic a second time
    """
    tiers = {
        "transit": _transit_tier(transit_status),
        "aqi": _aqi_tier(aqi_reading),
        "pollen": _pollen_tier(pollen_reading),
    }
    overall = max(tiers.values(), key=TIER_ORDER.index)

    fragments = [
        _aqi_fragment(aqi_reading),
        _transit_fragment(transit_status, tiers["transit"]),
        _pollen_fragment(pollen_reading),
    ]
    subtext = " · ".join(fragments)

    return {
        "tier": overall,
        "headline": HEADLINES[overall],
        "lead": SUBTEXT_LEAD[overall],
        "subtext": subtext,
        "colors": TIER_COLORS[overall],
        "tiers": tiers,
    }
