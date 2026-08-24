"""
pollen.py
A simulated daily Pollen Index, rounding out the "how should I plan my
day" picture alongside real transit and EPA-formula air quality data.

There's no broadly available free real-time pollen API in the way OpenAQ
covers air quality, so -- same honesty pattern as the rest of this app --
this is clearly-labeled SIMULATED data. It isn't random noise, though: the
base level follows a realistic Northern Hemisphere seasonal curve (tree
pollen peaks in spring, grass in early summer, ragweed/weed in late
summer/early fall, mostly mold in winter), and it's deterministic per
city + ZIP + calendar day, so it reads as "today's forecast" rather than
reshuffling every time the page reloads -- but it DOES change from one
real day to the next, which is the honest behavior for something that
genuinely varies daily in real life (unlike, say, a transit line's typical
delay pattern, which is stable shape-wise).

Uses the same 0-12 scale as real pollen indices (e.g. Pollen.com / the
National Allergy Bureau).
"""

from datetime import datetime

import numpy as np
import requests

from cities import stable_seed

OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_TIMEOUT = 6  # seconds -- fail fast and fall back rather than hang the UI

# Open-Meteo's raw pollen field name -> a friendly display label
POLLEN_FIELDS = {
    "alder_pollen": "Alder", "birch_pollen": "Birch", "grass_pollen": "Grass",
    "mugwort_pollen": "Mugwort", "olive_pollen": "Olive", "ragweed_pollen": "Ragweed",
}

POLLEN_CATEGORIES = [
    (2.4, "Low", "#0ca30c", "🟢"),
    (4.8, "Moderate", "#d4b106", "🟡"),
    (7.2, "High", "#e8720c", "🟠"),
    (9.6, "Very High", "#d03b3b", "🔴"),
    (12.01, "Extreme", "#7e0023", "🟤"),
]

# month -> (dominant allergen, seasonal base level on the 0-12 scale)
_MONTH_PROFILE = {
    1: ("Mold spores", 1.5), 2: ("Mold spores", 1.8),
    3: ("Tree pollen", 6.5), 4: ("Tree pollen", 8.0),
    5: ("Grass pollen", 6.5), 6: ("Grass pollen", 5.5), 7: ("Grass pollen", 3.5),
    8: ("Ragweed / weed pollen", 6.0), 9: ("Ragweed / weed pollen", 7.0), 10: ("Ragweed / weed pollen", 5.0),
    11: ("Mold spores", 2.5), 12: ("Mold spores", 1.5),
}

ADVICE = {
    "Low": "Great day to be outside, even with seasonal allergies.",
    "Moderate": "Mild symptoms are possible if you're sensitive -- keep antihistamines handy.",
    "High": "Consider limiting long outdoor stretches if allergies affect you.",
    "Very High": "Sensitive folks should minimize outdoor time and keep windows closed.",
    "Extreme": "Best kept mostly indoors today if allergies affect you -- a rough day to be out.",
}


def _category_for(value: float) -> tuple:
    for cutoff, label, color, emoji in POLLEN_CATEGORIES:
        if value <= cutoff:
            return label, color, emoji
    return POLLEN_CATEGORIES[-1][1:]


def simulate_pollen(city: str, zip_code: str, now: datetime = None) -> dict:
    """Today's simulated pollen reading for this city/ZIP -- deterministic
    per (city, zip, calendar day) so it holds steady across reruns on the
    same day but moves with the real season and the real date."""
    now = now or datetime.now()
    allergen, base = _MONTH_PROFILE[now.month]
    seed = stable_seed(city, zip_code or "", "pollen", now.strftime("%Y-%m-%d"))
    rng = np.random.default_rng(seed)
    value = float(np.clip(base + rng.normal(0, 1.3), 0.0, 12.0))
    category, color, emoji = _category_for(value)
    return {
        "value": round(value, 1),
        "category": category,
        "color": color,
        "emoji": emoji,
        "dominant_allergen": allergen,
        "advice": ADVICE[category],
        "action": ACTION_FOR_SENSITIVE_GROUPS[category],
        "source": "simulated",
        "as_of": now,
    }


# --------------------------------------------------------------------------
# Live Open-Meteo Air Quality & Pollen integration
#
# HONEST CAVEAT, please read before assuming this is broken: Open-Meteo's
# pollen fields (alder/birch/grass/mugwort/olive/ragweed) are produced by a
# European (CAMS) model and are typically NULL for locations outside
# Europe -- which is every city this app covers. A live call for a U.S.
# city will almost always come back with real PM2.5/PM10 (those ARE global)
# and no pollen counts at all. That's not a bug to chase -- it's exactly
# the "missing pollen" case estimate_hazard_from_pm() below exists to
# handle gracefully, by estimating an Asthma Hazard Level from PM2.5 and
# the already-computed AQI instead. If Open-Meteo ever does return real
# counts for a location, they're used directly instead of the estimate.
# --------------------------------------------------------------------------
ACTION_FOR_SENSITIVE_GROUPS = {
    "Low": "Sensitive groups can enjoy outdoor time as usual today.",
    "Moderate": "Sensitive groups should keep quick-relief or allergy medication on hand.",
    "High": "Sensitive groups should shorten or lighten outdoor activity today.",
    "Very High": "Sensitive groups should limit outdoor time and keep windows closed.",
    "Extreme": "Sensitive groups should stay mostly indoors and follow their action plan.",
}

_LEVEL_ORDER = ["Low", "Moderate", "High", "Very High", "Extreme"]
_CATEGORY_STYLE = {label: (color, emoji) for _, label, color, emoji in POLLEN_CATEGORIES}
_CATEGORY_MIDPOINT = {"Low": 1.2, "Moderate": 3.6, "High": 6.0, "Very High": 8.4, "Extreme": 10.8}

# Approximate live-pollen severity bands (grains/m³) -- deliberately coarse
# and applied the same way across all six pollen types. Real region-specific
# pollen thresholds vary by plant; this app doesn't have room to model six
# separate scales, so this is clearly labeled an approximation, same honesty
# pattern as the rest of the app's "what's real vs. simulated" disclosures.
_LIVE_POLLEN_THRESHOLDS = [(9.99, "Low"), (49.99, "Moderate"), (149.99, "High"), (499.99, "Very High")]

# PM2.5 (µg/m³) bucketed with the SAME EPA breakpoints air_quality.py's own
# AQI math uses, just expressed directly as hazard levels for this card.
_PM25_HAZARD_THRESHOLDS = [(9.0, "Low"), (35.4, "Moderate"), (55.4, "High"), (150.4, "Very High")]

_AQI_LABEL_TO_LEVEL = {
    "Good": "Low", "Moderate": "Moderate", "Unhealthy for Sensitive Groups": "High",
    "Unhealthy": "Very High", "Very Unhealthy": "Extreme", "Hazardous": "Extreme",
}


def _bucket(value: float, thresholds: list) -> str:
    for cutoff, label in thresholds:
        if value <= cutoff:
            return label
    return "Extreme"


def _worse(level_a: str, level_b: str) -> str:
    """The more severe of two hazard levels -- same 'worst signal wins'
    rule outlook.py already uses to roll up transit/AQI/pollen, so this
    card's badge can never quietly under-call a real risk."""
    if not level_a:
        return level_b
    if not level_b:
        return level_a
    return level_a if _LEVEL_ORDER.index(level_a) >= _LEVEL_ORDER.index(level_b) else level_b


def estimate_hazard_from_pm(pm25: float = None, aqi_label: str = None) -> str:
    """Fallback Asthma Hazard Level for when no live pollen count is
    available (the normal case for U.S. cities -- see the caveat above).
    Buckets PM2.5 with the same EPA breakpoints the AQI math already uses,
    then takes the WORSE of that and the already-computed AQI category, so
    the hazard badge never disagrees with the Air Quality tab. Never
    raises: a missing/unusable pm25 just reads as a cautious "Moderate"
    default rather than crashing the card or silently claiming "Low."
    """
    pm_level = _bucket(pm25, _PM25_HAZARD_THRESHOLDS) if pm25 is not None else "Moderate"
    aqi_level = _AQI_LABEL_TO_LEVEL.get(aqi_label)
    return _worse(pm_level, aqi_level)


def fetch_open_meteo_environmental(lat: float, lon: float, target_hour: int = None) -> dict:
    """Best-effort live PM2.5/PM10 + pollen reading from Open-Meteo's free,
    keyless air-quality API (no API key or Streamlit secret needed).
    Returns None on ANY problem -- no coordinates, network error, timeout,
    unexpected response shape -- so the caller can fall back to the fully
    simulated reading without ever crashing the app."""
    if lat is None or lon is None:
        return None
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "pm2_5,pm10," + ",".join(POLLEN_FIELDS.keys()),
                "forecast_days": 1,
            },
            timeout=OPEN_METEO_TIMEOUT,
        )
        resp.raise_for_status()
        hourly = resp.json().get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            return None
        idx = target_hour if isinstance(target_hour, int) and 0 <= target_hour < len(times) else 0

        def _at(field):
            series = hourly.get(field) or []
            return series[idx] if idx < len(series) else None

        return {
            "pm25": _at("pm2_5"),
            "pm10": _at("pm10"),
            "pollen": {label: _at(field) for field, label in POLLEN_FIELDS.items()},
            "source": "open-meteo",
        }
    except (requests.exceptions.RequestException, ValueError, KeyError, TypeError, IndexError):
        return None


def get_environmental_reading(city: str, zip_code: str, lat: float, lon: float,
                               now: datetime = None, aqi_reading: dict = None) -> dict:
    """The single source of truth for the Environmental Health & Pollen
    Outlook card, AND a drop-in replacement for simulate_pollen() as the
    app's main 'pollen_reading' -- same return shape either way (value /
    category / color / emoji / dominant_allergen / advice / action /
    source / as_of), so outlook.py, briefing.py, exports.py, and the
    dashboard's existing Pollen tile all keep working unmodified no matter
    which of the three paths below actually ran:

      1. Live Open-Meteo pollen counts exist for this location (rare for
         this app's U.S. cities, but used directly when present) -- the
         highest-reading pollen type becomes the dominant allergen, and the
         hazard is the worse of its category and the AQI's.
      2. Live Open-Meteo call succeeds but returns no pollen counts (the
         normal case here) -- the hazard is estimated from the live PM2.5
         reading and the AQI via estimate_hazard_from_pm(), and the
         dominant "allergen" is honestly reported as the AQI's own
         dominant pollutant (PM2.5 / PM10 / Ozone) rather than invented.
      3. The live call fails outright (no network, timeout, bad response)
         -- falls all the way back to the existing fully-simulated
         simulate_pollen(), same as before this feature existed.
    """
    now = now or datetime.now()
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    aqi_label = aqi_reading.get("label")

    try:
        live = fetch_open_meteo_environmental(lat, lon, target_hour=now.hour)
    except Exception:
        live = None

    if live is None:
        # No live reading at all -- fully simulated, exactly as before this
        # feature existed, just also folded against the real/simulated AQI
        # so the hazard badge can't disagree with the Air Quality tab.
        reading = simulate_pollen(city, zip_code, now=now)
        reading["category"] = _worse(reading["category"], _AQI_LABEL_TO_LEVEL.get(aqi_label))
        color, emoji = _CATEGORY_STYLE.get(reading["category"], (reading["color"], reading["emoji"]))
        reading["color"], reading["emoji"] = color, emoji
        reading["action"] = ACTION_FOR_SENSITIVE_GROUPS[reading["category"]]
        return reading

    real_pollen = {label: v for label, v in (live.get("pollen") or {}).items() if v is not None}

    if real_pollen:
        dominant_allergen = max(real_pollen, key=real_pollen.get)
        pollen_level = _bucket(real_pollen[dominant_allergen], _LIVE_POLLEN_THRESHOLDS)
        category = _worse(pollen_level, _AQI_LABEL_TO_LEVEL.get(aqi_label))
        source = "open-meteo (live pollen)"
    else:
        dominant_allergen = f"{aqi_reading.get('dominant') or 'PM2.5'} (fine particulates)"
        category = estimate_hazard_from_pm(live.get("pm25"), aqi_label)
        source = "open-meteo (PM2.5 estimate)"

    color, emoji = _CATEGORY_STYLE.get(category, ("#898781", "❔"))
    return {
        "value": _CATEGORY_MIDPOINT.get(category, 5.0),
        "category": category,
        "color": color,
        "emoji": emoji,
        "dominant_allergen": dominant_allergen,
        "advice": ADVICE.get(category, "No advice available right now."),
        "action": ACTION_FOR_SENSITIVE_GROUPS.get(category, "Check back later for an update."),
        "source": source,
        "as_of": now,
    }
