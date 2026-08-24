"""
app.py
Local Daily Companion -- Streamlit entrypoint.

PIVOT: this project used to be a general "daily companion" covering
transit accessibility/delays AND air quality/pollen. It is now a
focused Biomedical Health & Respiratory Dashboard -- every transit
subway/train/bus/delay/elevator-outage feature has been removed. The
app's one job is now the Personalized Respiratory Health & Bio-Hazard
outlook, built from:

  - Air Quality (air_quality.py) -- a live OpenAQ reading (EPA AQI math)
    with a clearly-labeled simulated fallback.
  - Environmental / Pollen (pollen.py) -- Open-Meteo's free Air Quality
    API for PM2.5/PM10 and (where the underlying CAMS pollen model has
    coverage) live ragweed/grass/birch/olive pollen counts, folded
    together with the AQI via a documented "worst signal wins" rule.
  - A Dynamic Asthma & Allergen Risk Score (compute_respiratory_hazard()
    below) -- collapses that combined signal into exactly three tiers,
    LOW / MODERATE / HIGH RISK, and shifts the effective threshold based
    on the user's own sensitivity profile (Not Sensitive / Mild
    Allergies / Severe Asthma), set in the sidebar.

Three cards make up the main screen: (1) the Overall Respiratory Hazard
Score, a large color badge with actionable advice; (2) Dominant Airborne
Triggers, a clean column breakdown of PM2.5, PM10, and named pollen
species; (3) a compact Sensitivity & Symptom Log summary, with the full
interactive selector and log living in the sidebar.

...plus several personal features carried over from before:
  - A Home page (login/sign-up, or a personalized "Welcome Back" dashboard
    for a logged-in user) -- see homepage.py / accounts.py
  - Saved Locations (Home / Work / School-style presets) in the sidebar
  - Dynamic ZIP code entry: type ANY real 5-digit ZIP in a supported metro
    area, not just the featured ones, and every reading tailors itself
    to that exact ZIP (see cities.lookup_neighborhood / is_valid_zip)

ABOUT "RIGHT NOW": nothing in this app is cached or frozen to a fixed
date. Every timestamp shown is computed fresh on every rerun from the
SELECTED CITY'S OWN LOCAL TIME (via cities.now_in_city(), which converts
the real current instant into that city's real IANA timezone with
zoneinfo) -- not raw server time, which on most cloud hosts is UTC and
matches no real place.

ABOUT ACCOUNTS: logging in is entirely optional -- every feature works for
a guest with no account. Accounts (accounts.py) live only in this
session's memory, the same honest scope choice already used for community
reports and saved locations; see accounts.py's docstring and the README.

ABOUT HONESTY: this app never invents a reading it doesn't have. Open-Meteo's
pollen model is European (CAMS) and typically has no coverage for U.S.
cities -- when that's the case, the Dominant Airborne Triggers card says
so plainly instead of making up a ragweed/grass/birch/olive number, and
the hazard score falls back to PM2.5/PM10 + the Air Quality Index instead.
"""

from datetime import timedelta

import streamlit as st

# --------------------------------------------------------------------------
# Import the rest of this project defensively.
#
# app.py, cities.py, air_quality.py, accounts.py, homepage.py, pollen.py,
# user_profile.py, exports.py, community.py, and feedback.py are all
# delivered together as a MATCHED SET and import from each other -- most
# importantly, several of them (accounts.py, user_profile.py,
# air_quality.py) do `from cities import ...` at their own top level. That
# means dropping a newer app.py next to an older/incomplete cities.py (or
# a folder that's simply missing cities.py) can raise an ImportError from
# INSIDE one of those other files, not from this file's own import line --
# so the whole block is wrapped here, not just app.py's own `import cities`.
#
# CITY_NAMES and get_city are load-bearing -- there's no safe way to
# reconstruct 18 cities' worth of real coordinates/timezones/ZIPs if
# they're missing, so that failure gets a clear, friendly stop instead of
# a raw traceback. now_in_city / lookup_neighborhood / is_valid_zip
# (cities.py) and render_status_tile / render_hazard_score_card /
# render_airborne_triggers_card (homepage.py) are all newer additions
# added after their modules' original functions already existed; if a
# deployment ever ends up with a newer file next to an older one that's
# missing one of these, app.py defines its own equivalent fallback further
# below so the app keeps working rather than crashing outright with an
# AttributeError. Updating every file to the latest matching version
# together is still the right long-term fix -- see the README's "Keep all
# files in sync" note.
#
# NOTE ON transit.py / briefing.py / outlook.py: these files may still
# exist on disk from before the Biomedical Health pivot, but app.py no
# longer imports or calls into any of them -- transit tracking is gone
# entirely, and briefing.py/outlook.py both unconditionally wove transit
# language into their output with no way to turn it off, which would mean
# fabricating transit content in an app that no longer has any transit
# data. This file builds its own respiratory-only briefing and hazard
# score locally instead (see compute_respiratory_hazard() below).
# --------------------------------------------------------------------------
try:
    import accounts
    import air_quality
    import community
    import exports
    import feedback
    import homepage
    import pollen
    import user_profile
    import cities as _cities_mod
    from user_profile import PROFILE_KEY_PREFIX
    CITY_NAMES = _cities_mod.CITY_NAMES
    get_city = _cities_mod.get_city
except (ImportError, AttributeError) as e:
    st.set_page_config(page_title="Respiratory Health Dashboard", page_icon="🫁", layout="wide")
    st.error(
        "⚠️ **Setup problem:** this project's files don't match up -- "
        f"one of them failed to import (`{e}`).\n\n"
        "`app.py`, `cities.py`, `air_quality.py`, `accounts.py`, `homepage.py`, "
        "`user_profile.py`, `pollen.py`, `exports.py`, `community.py`, and `feedback.py` are "
        "delivered together and depend on each other, so please make sure **all** of them are "
        "the matching set from the same delivery, sitting in the same folder, then restart the "
        "app. See the README's \"Keep all files in sync\" note for details."
    )
    st.stop()
    raise

if hasattr(_cities_mod, "now_in_city"):
    now_in_city = _cities_mod.now_in_city
else:
    from datetime import datetime as _datetime
    try:
        from zoneinfo import ZoneInfo as _ZoneInfo
    except ImportError:  # pragma: no cover -- stdlib since Python 3.9
        _ZoneInfo = None

    def now_in_city(city_name: str):
        """Fallback for an older cities.py that doesn't define this yet --
        same behavior as the current cities.now_in_city(): convert the
        real current instant into the city's own IANA timezone if one is
        on record, else fall back to plain server time rather than crash."""
        tz_name = get_city(city_name).get("timezone")
        if tz_name and _ZoneInfo is not None:
            try:
                return _datetime.now(_ZoneInfo(tz_name))
            except Exception:
                pass
        return _datetime.now()

if hasattr(_cities_mod, "is_valid_zip"):
    is_valid_zip = _cities_mod.is_valid_zip
else:
    def is_valid_zip(zip_code) -> bool:
        """Fallback for an older cities.py -- same strict check as the
        current cities.is_valid_zip()."""
        return isinstance(zip_code, str) and zip_code.isdigit() and len(zip_code) == 5

if hasattr(_cities_mod, "lookup_neighborhood"):
    lookup_neighborhood = _cities_mod.lookup_neighborhood
else:
    def lookup_neighborhood(city_name: str, zip_code: str) -> dict:
        """Fallback for an older cities.py -- same behavior as the current
        cities.lookup_neighborhood(): match a featured ZIP's real
        neighborhood name, or an honest generic label otherwise."""
        city_info = get_city(city_name)
        if is_valid_zip(zip_code):
            for z in city_info.get("zips", []):
                if z["zip"] == zip_code:
                    return {"neighborhood": z["neighborhood"], "known": True}
            return {"neighborhood": f"ZIP {zip_code} area", "known": False}
        return {"neighborhood": "Unknown area", "known": False}

# render_status_tile / render_hazard_score_card / render_airborne_triggers_card
# were added to homepage.py during the Biomedical Health pivot. If a
# DEPLOYMENT ever ends up with a newer app.py sitting next to an OLDER
# homepage.py (e.g. only app.py got re-uploaded to GitHub, or a hosting
# platform's file cache lagged behind a partial update), calling
# homepage.render_hazard_score_card(...) directly would raise
# AttributeError and crash the whole dashboard, exactly like the
# CITY_NAMES/get_city mismatch this same pattern already guards against
# above. Same fix: define a local equivalent here and use IT instead of
# reaching into `homepage` directly, so a mismatched file pair degrades to
# "still works, just from the fallback copy" instead of a blank crashed
# page. Keeping homepage.py up to date is still the right long-term fix --
# see the README's "Keep all files in sync" note.
if hasattr(homepage, "render_status_tile"):
    render_status_tile = homepage.render_status_tile
else:
    def render_status_tile(label: str, value: str, note: str, tier: str = "caution", compact: bool = False):
        """Fallback for an older homepage.py -- same behavior as the
        current homepage.render_status_tile()."""
        tier = tier if tier in ("good", "caution", "hazard") else "caution"
        badge_text = {"good": "🟢 On track", "caution": "🟡 Worth a glance", "hazard": "🔴 Needs attention"}[tier]
        style = "min-height:104px; padding:14px 16px;" if compact else ""
        value_style = "font-size:1.3rem;" if compact else ""
        st.markdown(
            f"""
            <div class="status-tile" style="{style}">
                <div class="tile-label">{label}</div>
                <div class="tile-value" style="{value_style}">{value}</div>
                <span class="tile-badge tile-badge-{tier}">{badge_text}</span>
                <div class="tile-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

_FALLBACK_HAZARD_TIER_STYLE = {
    "low": {"gradient": "linear-gradient(120deg, #065f46 0%, #10b981 100%)", "text": "#ffffff", "emoji": "🟢", "label": "LOW RISK"},
    "moderate": {"gradient": "linear-gradient(120deg, #92400e 0%, #f59e0b 100%)", "text": "#ffffff", "emoji": "🟡", "label": "MODERATE RISK"},
    "high": {"gradient": "linear-gradient(120deg, #7f1d1d 0%, #ef4444 100%)", "text": "#ffffff", "emoji": "🔴", "label": "HIGH RISK"},
}

if hasattr(homepage, "render_hazard_score_card"):
    render_hazard_score_card = homepage.render_hazard_score_card
else:
    def render_hazard_score_card(hazard: dict, city: str = None, compact: bool = False):
        """Fallback for an older homepage.py -- same behavior as the
        current homepage.render_hazard_score_card()."""
        hazard = hazard if isinstance(hazard, dict) else {}
        tier = hazard.get("tier") if hazard.get("tier") in _FALLBACK_HAZARD_TIER_STYLE else "moderate"
        style = _FALLBACK_HAZARD_TIER_STYLE[tier]
        advice = hazard.get("advice") or "Check back later for today's respiratory outlook."
        city_bit = f" · {city}" if city else ""
        st.markdown(
            f"""
            <div class="outlook-banner" style="background:{style['gradient']}; color:{style['text']}">
                <div class="outlook-eyebrow">Overall Respiratory Hazard Score{city_bit}</div>
                <h1>{style['emoji']} {style['label']}</h1>
                <p class="outlook-sub">{advice}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

if hasattr(homepage, "render_airborne_triggers_card"):
    render_airborne_triggers_card = homepage.render_airborne_triggers_card
else:
    def render_airborne_triggers_card(aqi_reading: dict = None, pollen_reading: dict = None, pollen_detail: dict = None):
        """Fallback for an older homepage.py -- a simplified version of
        the current homepage.render_airborne_triggers_card()."""
        aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
        pollen_reading = pollen_reading if isinstance(pollen_reading, dict) else {}
        st.markdown("##### 🫁 Dominant Airborne Triggers")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="stat-label">PM2.5</div>', unsafe_allow_html=True)
            pm25 = aqi_reading.get("pm25")
            st.markdown(f'<div class="stat-value">{f"{pm25:.1f} µg/m³" if isinstance(pm25, (int, float)) else "No data"}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="stat-label">PM10</div>', unsafe_allow_html=True)
            pm10 = aqi_reading.get("pm10")
            st.markdown(f'<div class="stat-value">{f"{pm10:.1f} µg/m³" if isinstance(pm10, (int, float)) else "No data"}</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="stat-label">Dominant allergen</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{pollen_reading.get("dominant_allergen") or "Not available"}</div>', unsafe_allow_html=True)

st.set_page_config(
    page_title="Respiratory Health Dashboard",
    page_icon="🫁",
    layout="wide",
    initial_sidebar_state="expanded",
)

CITY_KEY = "selected_city_key"
ZIP_KEY = "selected_zip_code_key"  # always holds a plain ZIP-code STRING, e.g. "10001" -- see the
                                    # sidebar section below for why this used to be an index and crashed
ZIP_CITY_CONTEXT_KEY = "_zip_city_context"  # tracks "which city was ZIP_KEY last set for" -- used
                                              # below to reset the ZIP when the user picks a NEW city,
                                              # without also wiping out a ZIP that was just applied
                                              # TOGETHER with a city change (a saved location / account
                                              # login) -- see accounts.apply_account_to_session() and
                                              # user_profile.apply_location()
SENSITIVITY_KEY = "respiratory_sensitivity_profile"
SYMPTOM_LOG_KEY = "symptom_log_entries"

if "view" not in st.session_state:
    st.session_state.view = "home"  # the Home page is the default view on launch

# --------------------------------------------------------------------------
# Apply any pending "switch to this account/saved location" request queued
# by a button click on a PREVIOUS run (login on the Home page, or "go to"
# a saved location in the sidebar) -- BEFORE this run creates the
# city/ZIP/profile widgets below.
# --------------------------------------------------------------------------
accounts.consume_pending_apply(CITY_KEY, ZIP_KEY, PROFILE_KEY_PREFIX, ZIP_CITY_CONTEXT_KEY)
user_profile.consume_pending_location(CITY_KEY, ZIP_KEY, ZIP_CITY_CONTEXT_KEY)

# --------------------------------------------------------------------------
# Styling -- a sleek, medical-grade digital health dashboard: a flat, clean
# off-white canvas, rounded floating white cards with a hairline border and
# one soft shadow, generous padding, and color communicated through
# high-contrast badge pills (green/yellow/red) rather than loud full-bleed
# fills. A single vivid gradient is reserved for the ONE "look here first"
# moment per page -- the Overall Respiratory Hazard Score card -- so that
# moment reads instantly as the most important thing on the screen.
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        --card-border: #EEF2F6;
        --card-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
        --card-radius: 18px;
        --accent-grad: linear-gradient(120deg, #0f172a 0%, #0f766e 55%, #10b981 100%);
        background: #F8FAFC;
    }
    .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1080px; }
    h1, h2, h3 { letter-spacing: -0.01em; color: #0f172a; }

    /* -- Consistent button/input/divider rhythm across every page -- one
       shared shape language instead of each widget using Streamlit's raw
       defaults. Buttons are pill-shaped with a subtle hover lift;
       primaryColor in .streamlit/config.toml drives the emerald fill on
       "primary" buttons (Log In, Sign Up, Save, etc.) so we don't have to
       chase Streamlit's internal button markup across versions with CSS. -- */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        border-radius: 999px;
        font-weight: 700;
        padding: 0.5rem 1.25rem;
        border-color: var(--card-border);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.10);
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="select"] > div {
        border-radius: 10px !important;
    }
    hr { margin: 0.6rem 0 !important; opacity: 0.10; }
    div[data-testid="stExpander"] {
        border-radius: var(--card-radius);
        border: 1px solid var(--card-border) !important;
        box-shadow: none;
    }
    div[data-testid="column"] { padding: 0 8px; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--card-radius) !important;
        border-color: var(--card-border) !important;
        box-shadow: var(--card-shadow);
    }

    /* -- Simple pill-style tabs -- */
    div[data-baseweb="tab-list"] {
        gap: 4px;
        background: #F1F5F9;
        padding: 5px;
        border-radius: 999px;
    }
    div[data-baseweb="tab"] {
        border-radius: 999px !important;
        padding: 7px 18px !important;
        font-weight: 700;
    }
    div[data-baseweb="tab-highlight"] { background: transparent !important; }
    div[data-baseweb="tab"][aria-selected="true"] { background: #ffffff; }

    /* -- The single bold gradient moment per page: the Home page hero,
       and (below) the dashboard's Overall Respiratory Hazard Score card.
       Kept short on purpose -- one headline, one supporting line. -- */
    .hero-banner {
        background: var(--accent-grad);
        border-radius: var(--card-radius);
        padding: 30px 34px;
        margin-bottom: 20px;
        color: #ffffff;
    }
    .hero-banner h1 { color: #ffffff; margin-bottom: 8px; font-size: 2.1rem; line-height: 1.15; font-weight: 800; }
    .hero-banner p { color: rgba(255,255,255,0.9); margin: 0; font-size: 1rem; max-width: 600px; line-height: 1.5; }

    /* -- The Overall Respiratory Hazard Score banner -- the very first
       thing on the dashboard, color-coded LOW (green) / MODERATE (yellow)
       / HIGH RISK (red). Colors are set inline per-render via
       style="background:...", this just handles layout/shape. -- */
    .outlook-banner {
        border-radius: var(--card-radius);
        padding: 26px 30px;
        margin-bottom: 18px;
    }
    .outlook-banner .outlook-eyebrow {
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.09em;
        font-weight: 800; opacity: 0.85; margin-bottom: 8px;
    }
    .outlook-banner h1 { margin: 0 0 6px 0; font-size: 1.9rem; line-height: 1.15; }
    .outlook-banner .outlook-sub { font-size: 1rem; font-weight: 600; margin: 0; }

    /* -- Calm, scannable status tiles -- plain white cards with a bold
       number and a small color-coded badge pill, instead of a loud
       full-color background. -- */
    .status-tile {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        padding: 20px 22px;
        min-height: 128px;
        box-shadow: var(--card-shadow);
    }
    .status-tile .tile-label {
        font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em;
        font-weight: 700; color: #64748b; margin-bottom: 10px;
    }
    .status-tile .tile-value { font-size: 1.7rem; font-weight: 800; color: #0f172a; line-height: 1.15; }
    .status-tile .tile-note { font-size: 0.85rem; color: #64748b; margin-top: 10px; line-height: 1.45; }

    /* -- Small color-coded badge pill -- the app's ONE way of signaling
       good/caution/hazard, reused by the status tiles and the Dominant
       Airborne Triggers card so the whole app shares one color language
       instead of each card inventing its own. -- */
    .tile-badge {
        display: inline-block; margin-top: 6px; padding: 4px 12px;
        border-radius: 999px; font-size: 0.78rem; font-weight: 700;
    }
    .tile-badge-good    { background: rgba(16, 163, 74, 0.12); color: #0f7a3d; }
    .tile-badge-caution { background: rgba(217, 119, 6, 0.14); color: #92600a; }
    .tile-badge-hazard  { background: rgba(220, 38, 38, 0.12); color: #b91c1c; }

    .stat-label {
        font-size: 0.75rem; font-weight: 700; color: #64748b;
        text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;
    }
    .stat-value { font-size: 1.05rem; font-weight: 700; color: #0f172a; line-height: 1.4; }

    .briefing-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        padding: 18px 24px;
        margin-bottom: 16px;
        box-shadow: var(--card-shadow);
    }
    .briefing-card .briefing-label {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #64748b; font-weight: 700; margin-bottom: 4px;
    }
    .briefing-card .briefing-text { font-size: 1.1rem; font-weight: 600; color: #0f172a; line-height: 1.4; }
    .briefing-card .briefing-time { font-size: 0.78rem; color: #94a3b8; margin-top: 6px; }

    .alerts-heading { font-size: 1rem; font-weight: 700; color: #0f172a; margin: 4px 0 8px 0; }
    .alert-card {
        background: color-mix(in srgb, var(--accent, #898781) 9%, #ffffff);
        border: 1px solid var(--card-border);
        border-left: 6px solid var(--accent, #898781);
        border-radius: var(--card-radius);
        padding: 12px 18px;
        margin-bottom: 10px;
        box-shadow: var(--card-shadow);
    }
    .alert-card .alert-top { font-weight: 700; font-size: 0.98rem; color: #0f172a; }
    .alert-card .alert-body { font-size: 0.88rem; color: #334155; margin-top: 4px; line-height: 1.5; }

    .companion-banner {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        padding: 14px 20px;
        margin-bottom: 16px;
        color: #0f172a;
        font-size: 0.92rem;
        line-height: 1.5;
        box-shadow: var(--card-shadow);
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-left: 5px solid var(--accent, #898781);
        border-radius: var(--card-radius);
        padding: 16px 20px;
        margin-bottom: 12px;
        min-height: 108px;
        box-shadow: var(--card-shadow);
    }
    .metric-card .mc-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; font-weight: 700; }
    .metric-card .mc-value { font-size: 1.65rem; font-weight: 800; color: #0f172a; line-height: 1.15; }
    .metric-card .mc-note { font-size: 0.8rem; color: #64748b; margin-top: 6px; }

    .aqi-hero {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-top: 4px solid var(--accent, #0f766e);
        border-radius: var(--card-radius);
        padding: 22px 26px;
        margin-bottom: 16px;
        text-align: center;
        box-shadow: var(--card-shadow);
    }
    .aqi-hero .aqi-hero-value { font-size: 3rem; font-weight: 800; color: var(--accent, #0f172a); line-height: 1; }
    .aqi-hero .aqi-hero-label { font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-top: 6px; }
    .aqi-hero .aqi-hero-sub { font-size: 0.88rem; color: #64748b; margin-top: 4px; }

    .risk-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-left: 6px solid var(--accent, #898781);
        border-radius: var(--card-radius);
        padding: 16px 20px;
        margin: 14px 0 6px 0;
        box-shadow: var(--card-shadow);
    }
    .risk-card .risk-top { font-size: 1.1rem; color: #0f172a; margin-bottom: 4px; }
    .risk-card .risk-advice { font-size: 0.92rem; color: #334155; line-height: 1.5; }

    .report-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-left: 5px solid var(--accent, #898781);
        border-radius: var(--card-radius);
        padding: 12px 18px;
        margin-bottom: 8px;
        box-shadow: var(--card-shadow);
    }
    .report-card .rc-top { display: flex; justify-content: space-between; font-weight: 600; color: #0f172a; }
    .report-card .rc-details { font-size: 0.85rem; color: #334155; margin-top: 4px; }
    .report-card .rc-meta { font-size: 0.75rem; color: #94a3b8; margin-top: 6px; }

    /* -- Sidebar Sensitivity & Symptom Log widget -- */
    .symptom-entry {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.82rem;
        color: #334155;
        box-shadow: var(--card-shadow);
    }
    .symptom-entry .se-time { font-size: 0.72rem; color: #94a3b8; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Dynamic Asthma & Allergen Risk Score -- collapses pollen.py's existing
# five-tier hazard category (Low / Moderate / High / Very High / Extreme,
# itself already the "worst signal wins" combination of live PM2.5, PM10,
# pollen, and the Air Quality Index -- see pollen.py) into exactly three
# tiers: LOW (Green) / MODERATE (Yellow) / HIGH RISK (Red). The user's own
# sensitivity profile shifts the effective severity UP before bucketing,
# so someone who says they have Severe Asthma sees a more cautious score
# on the same real-world conditions than someone who isn't sensitive at
# all -- a real "dynamically update their risk threshold" behavior, not
# just a label change.
# --------------------------------------------------------------------------
_SEVERITY_INDEX = {"Low": 0, "Moderate": 1, "High": 2, "Very High": 3, "Extreme": 4}
SENSITIVITY_LEVELS = ["Not Sensitive", "Mild Allergies", "Severe Asthma"]
_SENSITIVITY_SHIFT = {"Not Sensitive": 0, "Mild Allergies": 1, "Severe Asthma": 2}
_TIER_ADVICE = {
    "low": "Air quality and pollen levels are favorable for respiratory health today. "
           "Enjoy normal outdoor activity.",
    "moderate": "Sensitive individuals should limit prolonged outdoor exertion, keep windows closed "
                "during peak hours, and keep allergy medication or a rescue inhaler within reach.",
    "high": "Keep windows closed and limit outdoor exposure today. Carry your rescue inhaler, and "
            "consider a mask outdoors if you have asthma or severe allergies.",
}


def compute_respiratory_hazard(pollen_category: str, sensitivity: str) -> dict:
    """The Dynamic Asthma & Allergen Risk Score. Never raises: an unknown
    category or sensitivity value degrades to a cautious "moderate"
    default instead of crashing the dashboard."""
    base = _SEVERITY_INDEX.get(pollen_category, 1)
    shift = _SENSITIVITY_SHIFT.get(sensitivity, 0)
    shifted = min(base + shift, 4)
    if shifted <= 1:
        tier = "low"
    elif shifted == 2:
        tier = "moderate"
    else:
        tier = "high"
    return {
        "tier": tier,
        "advice": _TIER_ADVICE[tier],
        "sensitivity": sensitivity,
        "raw_category": pollen_category,
    }


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🫁 Respiratory Health Dashboard")
    st.caption("Your city's air, decoded for your lungs.")

    def _go_to(view_name: str):
        # A plain on_click callback -- Streamlit runs this BEFORE the script
        # reruns, so it's always safe to write straight to st.session_state
        # here (even to a widget-bound key) with no extra rerun/queueing
        # needed.
        st.session_state.view = view_name

    nav_l, nav_r = st.columns(2, gap="small")
    with nav_l:
        st.button("🏠 Home", use_container_width=True, on_click=_go_to, args=("home",),
                   type="primary" if st.session_state.view == "home" else "secondary")
    with nav_r:
        st.button("🫁 Dashboard", use_container_width=True, on_click=_go_to, args=("app",),
                   type="primary" if st.session_state.view == "app" else "secondary")

    if accounts.is_logged_in():
        st.caption(f"👤 Logged in as **{accounts.current_user()}**")
    st.divider()

    city = st.selectbox("🏙️ Choose your city", options=CITY_NAMES, key=CITY_KEY)
    try:
        city_info = get_city(city) or {}
    except Exception:
        city_info = {}
    if not city_info.get("zips"):
        # get_city() is a pure local lookup and should never actually fail, but if it
        # somehow returns something incomplete -- or even raises -- fall back to the first
        # known city rather than letting a missing "zips"/"lat"/"lon" key crash the sidebar.
        try:
            city_info = get_city(CITY_NAMES[0]) or {}
        except Exception:
            city_info = {}
        if not city_info.get("zips"):
            city_info = {
                "state": "", "lat": 0.0, "lon": 0.0, "timezone": "UTC",
                "zips": [{"zip": "00000", "neighborhood": "Unknown area"}],
            }

    # ------------------------------------------------------------------
    # ZIP code entry. ZIP_KEY holds a plain ZIP-code STRING (never a list
    # index) -- see accounts.py / user_profile.py for the full history of
    # why that matters.
    # ------------------------------------------------------------------
    zip_options = city_info["zips"]
    featured_zip_values = [z["zip"] for z in zip_options]
    featured_labels = {z["zip"]: f"{z['zip']} — {z['neighborhood']}" for z in zip_options}

    if st.session_state.get(ZIP_CITY_CONTEXT_KEY) != city:
        st.session_state[ZIP_KEY] = featured_zip_values[0]
        st.session_state.pop("featured_zip_pick", None)
        st.session_state[ZIP_CITY_CONTEXT_KEY] = city
    elif not is_valid_zip(st.session_state.get(ZIP_KEY)):
        st.session_state[ZIP_KEY] = featured_zip_values[0]

    def _apply_featured_zip():
        st.session_state[ZIP_KEY] = st.session_state["featured_zip_pick"]

    st.selectbox(
        "✨ Featured neighborhood", options=featured_zip_values,
        format_func=lambda z: featured_labels.get(z, z),
        key="featured_zip_pick", on_change=_apply_featured_zip,
    )
    st.text_input(
        "📍 Or type any 5-digit ZIP code", key=ZIP_KEY, max_chars=5,
        help="Works for any real ZIP in this metro area, not just the featured list above -- "
             "air-quality and pollen readings are tailored to the exact ZIP you enter.",
    )

    raw_zip = st.session_state.get(ZIP_KEY, "")
    if is_valid_zip(raw_zip):
        selected_zip_code = raw_zip
    else:
        st.caption(f"⚠️ '{raw_zip}' isn't a valid 5-digit ZIP — using {featured_zip_values[0]} for now.")
        selected_zip_code = featured_zip_values[0]

    try:
        zip_lookup = lookup_neighborhood(city, selected_zip_code) or {}
    except Exception:
        zip_lookup = {}
    zip_lookup.setdefault("neighborhood", f"ZIP {selected_zip_code} area")
    zip_lookup.setdefault("known", False)
    selected_zip = {"zip": selected_zip_code, "neighborhood": zip_lookup["neighborhood"]}
    if not zip_lookup["known"]:
        st.caption(
            f"ℹ️ {selected_zip_code} isn't one of {city.split(',')[0]}'s featured ZIPs — this demo "
            "doesn't ship a full ZIP-to-neighborhood directory, so the readings below are simulated "
            f"and tailored to this exact ZIP using {city}'s real coordinates."
        )

    # -- Real, city-local time (not server/UTC time) -----------------------
    try:
        city_now = now_in_city(city)
    except Exception:
        from datetime import datetime as _dt
        city_now = _dt.now()
    try:
        browser_tz = st.context.timezone
    except Exception:
        browser_tz = None
    city_tz_name = city_info.get("timezone", "")
    try:
        tz_abbr = f" {city_now:%Z}".rstrip()
    except Exception:
        tz_abbr = ""
    st.caption(f"🕒 Local time in {city.split(',')[0]}: **{city_now:%I:%M %p}{tz_abbr}** ({city_tz_name})")
    if browser_tz and city_tz_name and browser_tz != city_tz_name:
        st.caption(
            f"Your browser is set to `{browser_tz}` — the times shown throughout this app "
            f"reflect **{city}'s** own local time above, not your browser's, in case you're "
            "checking in on a different city than the one you're in."
        )

    st.divider()
    # Saved locations keeps its own internal expander ("➕ Save current
    # location"), so it has to stay OUTSIDE any other expander below --
    # Streamlit doesn't allow nesting one expander inside another.
    user_profile.render_saved_locations_sidebar(
        current_city=city, current_zip=selected_zip["zip"], current_neighborhood=selected_zip["neighborhood"],
        city_key=CITY_KEY, zip_key=ZIP_KEY, zip_city_context_key=ZIP_CITY_CONTEXT_KEY,
    )

    st.divider()
    # --------------------------------------------------------------------
    # Symptom Log & Sensitivity Selector -- the clean interactive sidebar
    # widget requested for the Biomedical Health pivot: pick a sensitivity
    # profile (shifts the Dynamic Asthma & Allergen Risk Score's effective
    # threshold -- see compute_respiratory_hazard() above), and log
    # symptoms as they happen during this session.
    # --------------------------------------------------------------------
    st.markdown("#### 🩺 Sensitivity & Symptom Log")
    if SENSITIVITY_KEY not in st.session_state:
        st.session_state[SENSITIVITY_KEY] = SENSITIVITY_LEVELS[0]
    sensitivity_profile = st.selectbox(
        "Your sensitivity profile",
        options=SENSITIVITY_LEVELS,
        key=SENSITIVITY_KEY,
        help="Shifts your personal risk threshold -- 'Severe Asthma' flags MODERATE/HIGH risk sooner "
             "than the same real-world air quality would for someone who isn't sensitive.",
    )
    shift = _SENSITIVITY_SHIFT.get(sensitivity_profile, 0)
    st.caption(f"Risk threshold shifted +{shift} level{'s' if shift != 1 else ''} for this profile.")

    if SYMPTOM_LOG_KEY not in st.session_state:
        st.session_state[SYMPTOM_LOG_KEY] = []

    with st.expander("📝 Log a symptom"):
        symptom_text = st.text_input("What are you noticing?", placeholder="Wheezing, tight chest, itchy eyes…", key="symptom_text_input")
        symptom_severity = st.select_slider("Severity", options=["Mild", "Moderate", "Severe"], key="symptom_severity_input")

        def _log_symptom():
            text = st.session_state.get("symptom_text_input", "").strip()
            if text:
                st.session_state[SYMPTOM_LOG_KEY].insert(0, {
                    "text": text,
                    "severity": st.session_state.get("symptom_severity_input", "Mild"),
                    "time": city_now,
                })
                st.session_state["symptom_text_input"] = ""

        st.button("➕ Log symptom", use_container_width=True, on_click=_log_symptom)

        if st.session_state[SYMPTOM_LOG_KEY]:
            st.caption(f"{len(st.session_state[SYMPTOM_LOG_KEY])} entr{'y' if len(st.session_state[SYMPTOM_LOG_KEY]) == 1 else 'ies'} this session:")
            for entry in st.session_state[SYMPTOM_LOG_KEY][:5]:
                try:
                    time_str = f"{entry['time']:%I:%M %p}"
                except Exception:
                    time_str = ""
                st.markdown(
                    f'<div class="symptom-entry">{entry["severity"]} — {entry["text"]}'
                    f'<div class="se-time">{time_str}</div></div>',
                    unsafe_allow_html=True,
                )

            def _clear_log():
                st.session_state[SYMPTOM_LOG_KEY] = []

            st.button("🗑️ Clear log", use_container_width=True, on_click=_clear_log)
        else:
            st.caption("No symptoms logged yet this session.")

    def _log_out_and_go_home():
        accounts.log_out()
        st.session_state.view = "home"

    # Everything below this point is secondary to the core "pick a city,
    # see today's outlook" flow -- grouped into one collapsed section so
    # the sidebar's primary job (location + sensitivity) isn't buried
    # under it.
    with st.expander("⚙️ More options"):
        user_profile.render_notification_preferences()

        if accounts.is_logged_in():
            st.divider()
            st.markdown("**👤 Your account**")
            st.caption(accounts.storage_mode_label())
            if st.button("💾 Save city/ZIP as my defaults", use_container_width=True):
                saved_ok = accounts.save_preferences(accounts.current_user(), city, selected_zip["zip"], user_profile.get_profile())
                if saved_ok:
                    st.success("Saved — you'll see this instantly on your Home page from now on.")
                else:
                    st.error("Couldn't save your defaults right now — please try again in a moment.")
            st.button("Log out", use_container_width=True, key="sidebar_logout", on_click=_log_out_and_go_home)

        st.divider()
        st.caption(
            f"{len(CITY_NAMES)} real cities. Some readings are simulated where a live feed isn't "
            "available for your location — each card and tab says which."
        )

    st.divider()
    feedback_identity = accounts.current_user() if accounts.is_logged_in() else community.get_guest_id()
    feedback.render_feedback_widget(feedback_identity)

# --------------------------------------------------------------------------
# Compute "right now" once per run -- shared by the hazard score, both main
# cards, the Home page, and the dashboard tabs, so every part of the page
# agrees with every other part, and a live Open-Meteo/OpenAQ call never
# happens more than once per rerun for the same purpose.
# --------------------------------------------------------------------------
try:
    aqi_reading = air_quality.get_current_reading(
        city=city, zip_code=selected_zip["zip"], lat=city_info.get("lat"), lon=city_info.get("lon"), now=city_now,
    )
except Exception:
    # A COMPLETE fallback shape, matching every key air_quality.render_air_quality_tab()
    # reads -- a partial fallback dict here would just trade one crash (the live/simulated
    # reading failing) for another (a KeyError inside the tab trying to read a pm25/hourly/
    # etc. key this dict never had), which defeats the whole point of falling back gracefully.
    import pandas as _pd
    aqi_reading = {
        "aqi": None, "label": "No data", "color": "#898781", "emoji": "❔",
        "pm25": None, "pm10": None, "o3_ppb": None, "sub_indices": {}, "dominant": None,
        "risk": air_quality.asthma_risk(None), "source": "unavailable",
        "source_badge": "⚠️ Air quality data is temporarily unavailable for this city/ZIP.",
        "hourly": _pd.DataFrame({"hour": [], "pm25": [], "pm10": [], "o3_ppb": [], "aqi": [], "dominant": []}),
        "current_hour": city_now.hour if hasattr(city_now, "hour") else 0,
        "as_of": city_now,
    }

try:
    # Live Open-Meteo PM2.5/pollen reading when possible, gracefully folding
    # in the AQI we already computed above when live pollen counts aren't
    # available for this location (the normal case for U.S. cities -- see
    # pollen.py's docstring) -- falls all the way back to the fully
    # simulated reading if the live call fails outright.
    pollen_reading = pollen.get_environmental_reading(
        city, selected_zip["zip"], city_info.get("lat"), city_info.get("lon"), now=city_now, aqi_reading=aqi_reading,
    )
except Exception:
    pollen_reading = {"value": None, "category": "No data", "color": "#898781", "emoji": "❔",
                       "dominant_allergen": "", "advice": "Pollen data is unavailable right now.",
                       "action": "Check back later for an update.", "source": "unavailable", "as_of": city_now}

try:
    # A second, direct look at Open-Meteo's raw pollen fields JUST for the
    # four named species (ragweed/grass/birch/olive) the Dominant Airborne
    # Triggers card breaks out individually. pollen_reading above already
    # made ONE live call and folded pollen into a single category + a
    # named dominant allergen -- this call reuses the same free, keyless
    # endpoint (pollen.fetch_open_meteo_environmental) to also get each
    # species' own number for that card, without pollen.py itself needing
    # to change shape. None/missing values are the honest, EXPECTED
    # result for most U.S. cities (Open-Meteo's pollen model is CAMS/
    # Europe-only) -- the card says so rather than guessing.
    _raw_env = pollen.fetch_open_meteo_environmental(city_info.get("lat"), city_info.get("lon"), target_hour=city_now.hour if hasattr(city_now, "hour") else None)
    pollen_detail = (_raw_env or {}).get("pollen")
    if isinstance(pollen_detail, dict):
        pollen_detail = {pollen.POLLEN_FIELDS.get(k, k): v for k, v in pollen_detail.items()
                          if pollen.POLLEN_FIELDS.get(k) in ("Ragweed", "Grass", "Birch", "Olive")}
except Exception:
    pollen_detail = None

# --------------------------------------------------------------------------
# The Dynamic Asthma & Allergen Risk Score -- one overall LOW / MODERATE /
# HIGH RISK verdict, computed once and shared by the banner below AND the
# Home page, so they can never contradict each other.
# --------------------------------------------------------------------------
hazard = compute_respiratory_hazard(pollen_reading.get("category"), sensitivity_profile)

# --------------------------------------------------------------------------
# Daily Respiratory Briefing -- one honest sentence built locally from just
# the air quality + pollen/particulate readings this app actually has, so
# it never claims anything about transit (which this app no longer tracks).
# --------------------------------------------------------------------------
_aqi_label = (aqi_reading.get("label") or "unavailable").lower()
_pollen_category = (pollen_reading.get("category") or "unavailable").lower()
briefing_text = (
    f"Air quality in {city} is {_aqi_label} and today's respiratory hazard is {hazard['tier'].upper()} "
    f"({_pollen_category} particulate/pollen conditions). {hazard['advice']}"
)

# --------------------------------------------------------------------------
# Home view vs. Dashboard view
# --------------------------------------------------------------------------
if st.session_state.view == "home":
    homepage.render_homepage(
        city=city, neighborhood=selected_zip["neighborhood"], zip_code=selected_zip["zip"],
        briefing_text=briefing_text, hazard=hazard, aqi_reading=aqi_reading,
        pollen_reading=pollen_reading, pollen_detail=pollen_detail, city_now=city_now,
        symptom_log_count=len(st.session_state.get(SYMPTOM_LOG_KEY, [])),
    )
    st.stop()

# --------------------------------------------------------------------------
# Card #1 -- Overall Respiratory Hazard Score. The very first thing on the
# dashboard: whatever today's verdict is, a first-time visitor should be
# able to read it in the time it takes the page to load.
# --------------------------------------------------------------------------
render_hazard_score_card(hazard, city=city)

# --------------------------------------------------------------------------
# Card #2 -- Dominant Airborne Triggers: PM2.5, PM10, and named pollen
# species (ragweed/grass/birch/olive) in clean visual columns.
# --------------------------------------------------------------------------
render_airborne_triggers_card(aqi_reading, pollen_reading, pollen_detail)

# --------------------------------------------------------------------------
# Card #3 -- compact Sensitivity & Symptom Log summary (the full
# interactive selector and log itself lives in the sidebar, per the
# "clean interactive sidebar widget" design).
# --------------------------------------------------------------------------
log_count = len(st.session_state.get(SYMPTOM_LOG_KEY, []))
st.markdown(
    f"""
    <div class="metric-card" style="--accent:#0f766e;">
        <div class="mc-label">🩺 Sensitivity & Symptom Log</div>
        <div class="mc-value" style="font-size:1.3rem;">{sensitivity_profile}</div>
        <div class="mc-note">{log_count} symptom entr{'y' if log_count == 1 else 'ies'} logged this session — manage in the sidebar</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Daily Briefing card -- the one-sentence version with the exact timestamp.
# --------------------------------------------------------------------------
try:
    briefing_tz = f" {city_now:%Z}".rstrip()
except Exception:
    briefing_tz = ""
st.markdown(
    f"""
    <div class="briefing-card">
        <div class="briefing-label">📰 Daily Respiratory Briefing</div>
        <div class="briefing-text">{briefing_text}</div>
        <div class="briefing-time">As of {city_now:%A, %B %d, %Y — %I:%M %p}{briefing_tz} · {city}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Personal alert -- only shown when today's real hazard tier actually calls
# for one, worded around the user's own sensitivity profile.
# --------------------------------------------------------------------------
if hazard["tier"] in ("moderate", "high"):
    accent = {"moderate": "#d4b106", "high": "#d03b3b"}[hazard["tier"]]
    icon = "🟡" if hazard["tier"] == "moderate" else "🔴"
    st.markdown('<div class="alerts-heading">🔔 Your Personal Alert</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="alert-card" style="--accent:{accent}">
            <div class="alert-top">{icon} {hazard['tier'].upper()} respiratory risk — {sensitivity_profile} profile</div>
            <div class="alert-body">{hazard['advice']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------
# Save or share today's outlook -- a calendar file for a recurring morning
# reminder, or a paste-ready text summary. Both built from the exact same
# values as everything above.
# --------------------------------------------------------------------------
with st.expander("📤 Save or share today's outlook"):
    notify_prefs = user_profile.get_notification_prefs()
    st.caption(
        "Downloads a daily-repeating calendar event with today's briefing in the description, or "
        "gives you a paste-ready text summary — see \"Daily Briefing Preferences\" in the sidebar "
        "to set your preferred reminder time first."
    )
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        st.markdown("**📅 Calendar event**")
        try:
            reminder_time = notify_prefs["time"]
            event_start = city_now.replace(
                hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0
            )
            if event_start <= city_now:
                event_start = event_start + timedelta(days=1)
            ics_content = exports.build_commute_ics(
                city=city,
                event_title=f"Daily Respiratory Briefing — {city}",
                description=briefing_text,
                start_local=event_start,
            )
            st.download_button(
                "⬇️ Download Daily Respiratory Briefing Calendar Event (.ics)",
                data=ics_content,
                file_name="daily_respiratory_briefing.ics",
                mime="text/calendar",
                use_container_width=True,
            )
            st.caption(f"Repeats daily at {reminder_time.strftime('%I:%M %p')} once imported into your calendar app.")
        except Exception as e:  # noqa: BLE001
            st.caption(f"Calendar export unavailable right now ({e}).")

    with export_col2:
        st.markdown("**📋 Copy today's summary**")
        try:
            aqi_val = aqi_reading.get("aqi")
            aqi_str = f"AQI {aqi_val}" if aqi_val is not None else "AQI unavailable"
            summary_lines = [
                f"{city} ({selected_zip['zip']}) — {city_now.strftime('%A, %B %d — %I:%M %p')}",
                f"Respiratory Hazard: {hazard['tier'].upper()} (profile: {sensitivity_profile})",
                "",
                f"Air quality: {aqi_reading.get('label', 'No data')} ({aqi_str})",
                f"Pollen/particulate: {pollen_reading.get('category', 'No data')} — "
                f"{pollen_reading.get('dominant_allergen', '')}".rstrip(" —"),
                "",
                briefing_text,
                "",
                "Sent from Respiratory Health Dashboard",
            ]
            st.code("\n".join(summary_lines), language=None)
            st.caption("Use the copy icon in the corner above to copy this to your clipboard.")
        except Exception as e:  # noqa: BLE001
            st.caption(f"Summary export unavailable right now ({e}).")

tab_air, tab_community = st.tabs([
    "🌬️ Air Quality & Respiratory Details", "🏘️ Community Hub",
])

with tab_air:
    try:
        air_quality.render_air_quality_tab(
            city=city,
            zip_code=selected_zip["zip"],
            neighborhood=selected_zip["neighborhood"],
            lat=city_info["lat"],
            lon=city_info["lon"],
            reading=aqi_reading,
        )
    except Exception as e:  # noqa: BLE001
        st.error("Something went wrong loading air quality data for this city. Try refreshing or picking a different city.")
        st.caption(f"Technical detail: {e}")

with tab_community:
    try:
        community.render_community_tab(
            city=city,
            neighborhood=selected_zip["neighborhood"],
            zip_code=selected_zip["zip"],
            aqi_reading=aqi_reading,
            pollen_reading=pollen_reading,
            logged_in_user=accounts.current_user() if accounts.is_logged_in() else None,
            now=city_now,
        )
    except Exception as e:  # noqa: BLE001
        st.error("Something went wrong loading the Community Hub for this town. Try refreshing or picking a different city.")
        st.caption(f"Technical detail: {e}")
