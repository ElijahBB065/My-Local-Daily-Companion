"""
air_quality.py
Tab 2: Air Quality & Asthma Hazard Alerts.

Tries a real, live reading from the OpenAQ v3 API first. OpenAQ now
requires a free API key on every request (no more anonymous access), so
if no key is configured -- or the request fails for any reason: no key,
network error, timeout, no nearby station, unexpected response shape --
this falls back to a clearly-labeled, realistic simulation instead of
crashing or silently showing nothing.

AQI math uses the EPA's current (2024-revised) breakpoint tables, so
whether the numbers come from OpenAQ or from the simulator, the AQI
category assigned to them is the same real formula the government uses.
Source: EPA AQS breakpoint tables, https://aqs.epa.gov/aqsweb/documents/codetables/aqi_breakpoints.csv
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

from cities import stable_seed

OPENAQ_BASE_URL = "https://api.openaq.org/v3"
REQUEST_TIMEOUT = 6  # seconds -- fail fast and fall back rather than hang the UI
INK_MUTED_FALLBACK = "#898781"

# --------------------------------------------------------------------------
# EPA AQI breakpoints (2024-revised) -- (conc_low, conc_high, aqi_low, aqi_high)
# --------------------------------------------------------------------------
PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]
PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 604, 301, 500),
]
OZONE_BREAKPOINTS_PPB = [  # 8-hour ozone, parts per billion
    (0, 54, 0, 50),
    (55, 70, 51, 100),
    (71, 85, 101, 150),
    (86, 105, 151, 200),
    (106, 200, 201, 300),
]

# Official EPA AQI category colors (softened slightly for on-screen legibility)
AQI_CATEGORIES = [
    (50, "Good", "#0ca30c", "🟢"),
    (100, "Moderate", "#d4b106", "🟡"),
    (150, "Unhealthy for Sensitive Groups", "#e8720c", "🟠"),
    (200, "Unhealthy", "#d03b3b", "🔴"),
    (300, "Very Unhealthy", "#8f3f97", "🟣"),
    (500, "Hazardous", "#7e0023", "🟤"),
]


def _interpolate(conc: float, breakpoints) -> int:
    """EPA linear interpolation within a breakpoint table.

    Brackets are matched by their UPPER bound only (first bracket whose `hi`
    covers `conc`), not by `lo <= conc <= hi`. A value like PM2.5 = 9.1
    rounds to a float that can land a hair below the literal 9.1 boundary
    (e.g. 9.099999999999998) -- with a strict `lo <= conc <= hi` check that
    value satisfies NEITHER the "0.0-9.0" bracket (9.0999... > 9.0) NOR the
    "9.1-35.4" bracket (9.0999... < 9.1), falls through every bracket, and
    hits the "must be above the whole table" fallback -- silently reporting
    a borderline-Moderate reading as AQI 301 (Hazardous). Matching on `hi`
    alone (with a tiny epsilon) closes that gap.
    """
    conc = max(conc, 0)
    for lo, hi, aqi_lo, aqi_hi in breakpoints:
        if conc <= hi + 1e-9:
            return round(((aqi_hi - aqi_lo) / (hi - lo)) * (conc - lo) + aqi_lo)
    # above the table's top bracket entirely -- cap at the worst category
    # rather than extrapolating into meaningless territory
    return breakpoints[-1][3]


def aqi_category(aqi: int) -> tuple:
    """Return (label, color, emoji) for a given overall AQI value."""
    for max_aqi, label, color, emoji in AQI_CATEGORIES:
        if aqi <= max_aqi:
            return label, color, emoji
    return AQI_CATEGORIES[-1][1], AQI_CATEGORIES[-1][2], AQI_CATEGORIES[-1][3]


def compute_aqi(pm25: float = None, pm10: float = None, o3_ppb: float = None) -> dict:
    """Compute the overall AQI as the MAX of available sub-indices (the real
    EPA convention -- the worst pollutant of the moment determines the AQI)."""
    sub_indices = {}
    if pm25 is not None:
        sub_indices["PM2.5"] = _interpolate(pm25, PM25_BREAKPOINTS)
    if pm10 is not None:
        sub_indices["PM10"] = _interpolate(pm10, PM10_BREAKPOINTS)
    if o3_ppb is not None:
        sub_indices["Ozone"] = _interpolate(o3_ppb, OZONE_BREAKPOINTS_PPB)

    if not sub_indices:
        return {"aqi": None, "dominant": None, "sub_indices": {}}

    dominant = max(sub_indices, key=sub_indices.get)
    return {"aqi": sub_indices[dominant], "dominant": dominant, "sub_indices": sub_indices}


# --------------------------------------------------------------------------
# Live OpenAQ v3 fetch (best-effort; returns None on ANY failure)
# --------------------------------------------------------------------------
def get_api_key() -> str:
    """Look for an OpenAQ API key in Streamlit secrets, then the environment.
    Missing is expected and fine -- it just means we use the simulator."""
    try:
        if "OPENAQ_API_KEY" in st.secrets:
            return st.secrets["OPENAQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("OPENAQ_API_KEY", "")


def fetch_live_readings(lat: float, lon: float, api_key: str) -> dict:
    """Best-effort live PM2.5 / PM10 / Ozone reading from the nearest OpenAQ
    station within 25km. Returns None on ANY problem so the caller can fall
    back to the simulator without ever crashing the app."""
    if not api_key:
        return None

    headers = {"X-API-Key": api_key}
    try:
        loc_resp = requests.get(
            f"{OPENAQ_BASE_URL}/locations",
            headers=headers,
            params={"coordinates": f"{lat},{lon}", "radius": 25000, "limit": 5},
            timeout=REQUEST_TIMEOUT,
        )
        loc_resp.raise_for_status()
        locations = loc_resp.json().get("results", [])
        if not locations:
            return None

        location = locations[0]
        location_id = location.get("id")
        station_name = location.get("name", "Nearby station")

        # map sensor id -> parameter name (pm25 / pm10 / o3)
        sensor_param = {}
        for sensor in location.get("sensors", []):
            param_name = (sensor.get("parameter") or {}).get("name", "")
            sensor_param[sensor.get("id")] = param_name

        latest_resp = requests.get(
            f"{OPENAQ_BASE_URL}/locations/{location_id}/latest",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        latest_resp.raise_for_status()
        readings = latest_resp.json().get("results", [])
        if not readings:
            return None

        values = {}
        for r in readings:
            param = sensor_param.get(r.get("sensorsId"))
            if param and r.get("value") is not None:
                values[param] = r["value"]

        if not values:
            return None

        return {
            "station_name": station_name,
            "pm25": values.get("pm25"),
            "pm10": values.get("pm10"),
            "o3_ppb": (values.get("o3") * 1000) if values.get("o3") is not None else None,
            "source": "live",
        }
    except (requests.exceptions.RequestException, ValueError, KeyError, TypeError):
        return None


# --------------------------------------------------------------------------
# Realistic simulated fallback
# --------------------------------------------------------------------------
def _neighborhood_seed(city: str, zip_code: str) -> int:
    return stable_seed(city, zip_code)


def simulate_hourly_aqi(city: str, zip_code: str) -> pd.DataFrame:
    """24-hour simulated PM2.5 / PM10 / Ozone curve with realistic shapes:
    PM2.5/PM10 bump during AM/PM traffic rush hours, ozone builds through
    the afternoon as sunlight drives photochemical formation and fades
    at night. Deterministic per city+ZIP so it doesn't jump around on
    every unrelated widget interaction, and gently varies by neighborhood."""
    rng = np.random.default_rng(_neighborhood_seed(city, zip_code))
    hours = np.arange(24)

    pm25_baseline = rng.uniform(6, 16)
    am_bump = 5 * np.exp(-((hours - 8) ** 2) / (2 * 1.5 ** 2))
    pm_bump = 6 * np.exp(-((hours - 18) ** 2) / (2 * 1.8 ** 2))
    pm25 = np.clip(pm25_baseline + am_bump + pm_bump + rng.normal(0, 1.3, 24), 2, None)

    pm10 = np.clip(pm25 * rng.uniform(1.3, 1.7) + rng.normal(0, 3, 24), pm25, None)

    o3_baseline = rng.uniform(12, 22)
    o3_curve = 30 * np.exp(-((hours - 15) ** 2) / (2 * 3.5 ** 2))
    o3 = np.clip(o3_baseline + o3_curve + rng.normal(0, 2.5, 24), 3, None)

    rows = []
    for h, p25, p10, oz in zip(hours, pm25, pm10, o3):
        result = compute_aqi(pm25=p25, pm10=p10, o3_ppb=oz)
        rows.append({"hour": int(h), "pm25": round(p25, 1), "pm10": round(p10, 1),
                      "o3_ppb": round(oz, 1), "aqi": result["aqi"], "dominant": result["dominant"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Asthma hazard risk
# --------------------------------------------------------------------------
def asthma_risk(aqi: int) -> dict:
    if aqi is None:
        return {
            "level": "Unknown", "emoji": "❔", "color": "#898781",
            "advice": "No air quality data available right now.",
        }
    if aqi <= 50:
        return {
            "level": "Low", "emoji": "🟢", "color": "#0ca30c",
            "advice": "Great day for outdoor sports and activities — air quality poses little to no risk.",
        }
    if aqi <= 100:
        return {
            "level": "Moderate", "emoji": "🟡", "color": "#d4b106",
            "advice": "Generally fine for outdoor plans. If you have asthma, keep your rescue inhaler "
                       "handy during longer or more intense outdoor exertion.",
        }
    if aqi <= 150:
        return {
            "level": "High", "emoji": "🟠", "color": "#e8720c",
            "advice": "If you have asthma or another respiratory condition, consider shorter or lighter "
                       "outdoor activity today, and keep quick-relief medication with you.",
        }
    return {
        "level": "Severe", "emoji": "🔴", "color": "#d03b3b",
        "advice": "Consider moving activities indoors, or wear a well-fitted N95/KN95 mask outside. "
                   "This is a good day to follow your asthma action plan closely.",
    }


DISCLAIMER = (
    "This tool gives general, non-personalized guidance based on public air-quality index "
    "categories — it isn't medical advice. If you or a family member has asthma, follow your "
    "personal asthma action plan and talk to a doctor about what air quality levels mean for you."
)


def _fmt(value, unit: str, decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f} {unit}"


def _metric_card(label: str, value_str: str, note: str, accent: str = "#2a78d6"):
    st.markdown(
        f"""
        <div class="metric-card" style="--accent:{accent}">
            <div class="mc-label">{label}</div>
            <div class="mc-value">{value_str}</div>
            <div class="mc-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Shared "what's the air like right now" computation
# --------------------------------------------------------------------------
def get_current_reading(city: str, zip_code: str, lat: float, lon: float, now: datetime = None) -> dict:
    """The single source of truth for 'right now' air quality -- tries a
    live OpenAQ reading, falls back to the simulator, and always uses the
    CITY'S OWN LOCAL TIME (pass `now` from cities.now_in_city(city)) so the
    reading's "current hour" reflects that city's actual local hour, not
    the server's (no caching, no frozen dates -- just the right clock).
    Called once per app run from app.py and shared by the daily briefing,
    the personal alerts, and the Air Quality tab itself, so all three
    always agree with each other and a live API call never happens more
    than once per rerun."""
    now = now or datetime.now()
    api_key = get_api_key()
    live = fetch_live_readings(lat, lon, api_key) if api_key else None

    hourly = simulate_hourly_aqi(city, zip_code)
    current_hour = now.hour  # the city's own local wall-clock hour, every call
    sim_now = hourly.iloc[current_hour]

    if live and (live.get("pm25") is not None or live.get("pm10") is not None or live.get("o3_ppb") is not None):
        pm25_val, pm10_val, o3_val = live.get("pm25"), live.get("pm10"), live.get("o3_ppb")
        result = compute_aqi(pm25=pm25_val, pm10=pm10_val, o3_ppb=o3_val)
        source = "live"
        source_badge = f"🟢 <b>Live reading</b> from OpenAQ — nearest station: {live['station_name']}"
    else:
        pm25_val, pm10_val, o3_val = float(sim_now["pm25"]), float(sim_now["pm10"]), float(sim_now["o3_ppb"])
        result = compute_aqi(pm25=pm25_val, pm10=pm10_val, o3_ppb=o3_val)
        source = "simulated"
        source_badge = (
            "🧪 <b>Simulated demo data</b> — add an OpenAQ API key in Streamlit secrets to switch "
            "this to a live reading (see README)."
        )

    aqi_val = result["aqi"]
    label, color, emoji = aqi_category(aqi_val) if aqi_val is not None else ("No data", INK_MUTED_FALLBACK, "❔")
    risk = asthma_risk(aqi_val)

    return {
        "city": city, "zip_code": zip_code, "lat": lat, "lon": lon,
        "pm25": pm25_val, "pm10": pm10_val, "o3_ppb": o3_val,
        "aqi": aqi_val, "label": label, "color": color, "emoji": emoji,
        "sub_indices": result["sub_indices"], "dominant": result["dominant"],
        "risk": risk, "source": source, "source_badge": source_badge,
        "hourly": hourly, "current_hour": current_hour,
        "as_of": now,
    }


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
def render_air_quality_tab(city: str, zip_code: str, neighborhood: str, lat: float, lon: float, reading: dict = None):
    import charts  # local import keeps charts.py's own imports lightweight

    try:
        if reading is None:
            reading = get_current_reading(city, zip_code, lat, lon)
    except Exception:
        reading = None
    reading = reading if isinstance(reading, dict) else {}

    # Every field below is read with .get() and a sensible default -- this function can be
    # handed an incomplete fallback dict (e.g. from app.py's own exception handler when the
    # live/simulated reading itself failed), and it should degrade to "No data" placeholders
    # rather than raise a KeyError on top of whatever already went wrong upstream.
    aqi_val = reading.get("aqi")
    label = reading.get("label", "No data")
    color = reading.get("color", INK_MUTED_FALLBACK)
    emoji = reading.get("emoji", "❔")
    risk = reading.get("risk") or asthma_risk(None)
    source_badge = reading.get("source_badge", "🧪 Air quality data unavailable right now.")

    st.markdown(f'<div class="companion-banner">{source_badge}</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="aqi-hero" style="--accent:{color}">
            <div class="aqi-hero-value">{emoji} {aqi_val if aqi_val is not None else "—"}</div>
            <div class="aqi-hero-label">{label} · Air Quality Index</div>
            <div class="aqi-hero-sub">{neighborhood}, {city} &nbsp;({zip_code})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        _metric_card("PM2.5", _fmt(reading.get("pm25"), "µg/m³"), "Fine particles — traffic, smoke, industry", "#2a78d6")
    with c2:
        _metric_card("PM10", _fmt(reading.get("pm10"), "µg/m³"), "Coarser dust & pollen particles", "#4a3aa7")
    with c3:
        _metric_card("Ozone (O₃)", _fmt(reading.get("o3_ppb"), "ppb", 0), "Forms in sunlight — usually worst midafternoon", "#1baf7a")

    st.markdown(
        f"""
        <div class="risk-card" style="--accent:{risk.get('color', INK_MUTED_FALLBACK)}">
            <div class="risk-top">{risk.get('emoji', '❔')} Asthma Hazard Risk: <b>{risk.get('level', 'Unknown')}</b></div>
            <div class="risk-advice">{risk.get('advice', 'No advice available right now.')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(DISCLAIMER)
    as_of = reading.get("as_of")
    if as_of is not None:
        try:
            tz_suffix = f" {as_of:%Z}".rstrip()
            st.caption(f"📅 As of {as_of:%A, %B %d, %Y — %I:%M %p}{tz_suffix} local time in {city}.")
        except Exception:
            pass

    hourly = reading.get("hourly")
    if hourly is not None and not hourly.empty:
        st.subheader("📈 Trends")
        st.caption(
            "Shows a typical simulated daily shape (AM/PM traffic bumps for particulates, an "
            "afternoon peak for ozone) with today's current reading marked."
        )
        try:
            st.plotly_chart(
                charts.aqi_trend_chart(hourly, reading.get("current_hour", 0)), use_container_width=True
            )
            if reading.get("sub_indices"):
                st.plotly_chart(charts.pollutant_breakdown_chart(reading["sub_indices"]), use_container_width=True)
        except Exception:
            st.caption("Trend charts are temporarily unavailable.")
