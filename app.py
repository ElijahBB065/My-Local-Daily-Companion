"""
app.py
Local Daily Companion -- Streamlit entrypoint.

Default Home view, plus two dashboard tabs:
  1. Transit Accessibility & Delay Tracker (with a station-to-station trip planner)
  2. Air Quality & Asthma Hazard Alerts

...plus several personal features:
  - A Home page (login/sign-up, or a personalized "Welcome Back" dashboard
    for a logged-in user) -- see homepage.py / accounts.py
  - Saved Locations (Home / Work / School-style presets) in the sidebar
  - A Personal Sensitivity Profile (asthma, wheelchair/stroller access)
    that drives custom warning badges on the main dashboard
  - A one-sentence Daily Briefing banner combining transit + air quality
  - Dynamic ZIP code entry: type ANY real 5-digit ZIP in a supported metro
    area, not just the featured ones, and every simulation tailors itself
    to that exact ZIP (see cities.lookup_neighborhood / is_valid_zip)

Every city, transit agency, line, and station name is real. Live transit
arrivals aren't available from a single free API across eighteen agencies,
so Tab 1 uses clearly-labeled simulated arrival/delay data shaped like a
real one. Tab 2 tries a live OpenAQ reading first and only falls back to
a realistic simulation if no API key is configured or the request fails
for any reason -- the app never crashes, it just tells you which kind of
data you're looking at.

ABOUT "RIGHT NOW": nothing in this app is cached or frozen to a fixed
date. The daily briefing's greeting, the AQI "current hour" marker, the
transit delay-right-now estimate, and every timestamp shown are computed
fresh on every rerun from the SELECTED CITY'S OWN LOCAL TIME (via
cities.now_in_city(), which converts the real current instant into that
city's real IANA timezone with zoneinfo) -- not raw server time, which on
most cloud hosts is UTC and matches no real place. Reload the page a
minute from now (or tomorrow) and everything reflects that exact moment,
in that city's own clock. The one thing that's intentionally stable is the
*shape* of a simulated day (e.g. "CTA Red Line delays peak around 5:30pm")
-- that's deterministic per city so the charts don't reshuffle confusingly
on every restart, but which hour of that shape counts as "now" always
tracks the real, city-local clock.

ABOUT ACCOUNTS: logging in is entirely optional -- every feature works for
a guest with no account. Accounts (accounts.py) live only in this
session's memory, the same honest scope choice already used for community
reports and saved locations; see accounts.py's docstring and the README.
"""

from datetime import timedelta

import streamlit as st

# --------------------------------------------------------------------------
# Import the rest of this project defensively.
#
# app.py, cities.py, transit.py, air_quality.py, accounts.py, homepage.py,
# user_profile.py, briefing.py, and charts.py are all delivered together
# as a MATCHED SET and import from each other -- most importantly, several
# of them (accounts.py, user_profile.py, transit.py, air_quality.py) do
# `from cities import ...` at their own top level. That means dropping a
# newer app.py next to an older/incomplete cities.py (or a folder that's
# simply missing cities.py) can raise an ImportError from INSIDE one of
# those other files, not from this file's own import line -- so the whole
# block is wrapped here, not just app.py's own `import cities`.
#
# CITY_NAMES and get_city are load-bearing -- there's no safe way to
# reconstruct 18 cities' worth of real coordinates/timezones/ZIPs if
# they're missing, so that failure gets a clear, friendly stop instead of
# a raw traceback. now_in_city / lookup_neighborhood / is_valid_zip are
# newer additions (timezone support + dynamic ZIP lookup) added after
# CITY_NAMES/get_city already existed; if cities.py has the former but not
# the latter, app.py defines its own equivalent fallback further below so
# the app keeps working rather than crashing outright. Updating cities.py
# (and every other file) to the latest matching version is still the right
# long-term fix -- see the README's "Keep all files in sync" note.
# --------------------------------------------------------------------------
try:
    import accounts
    import air_quality
    import briefing
    import community
    import exports
    import feedback
    import homepage
    import outlook
    import pollen
    import transit
    import user_profile
    import cities as _cities_mod
    from user_profile import PROFILE_KEY_PREFIX
    CITY_NAMES = _cities_mod.CITY_NAMES
    get_city = _cities_mod.get_city
except (ImportError, AttributeError) as e:
    st.set_page_config(page_title="Local Daily Companion", page_icon="🧭", layout="wide")
    st.error(
        "⚠️ **Setup problem:** this project's files don't match up -- "
        f"one of them failed to import (`{e}`).\n\n"
        "`app.py`, `cities.py`, `transit.py`, `air_quality.py`, `accounts.py`, `homepage.py`, "
        "`user_profile.py`, `briefing.py`, `outlook.py`, `pollen.py`, `exports.py`, `community.py`, "
        "`feedback.py`, and `charts.py` are delivered together and depend on each other, so please "
        "make sure **all** of them are the matching set from the same delivery, sitting in the same "
        "folder, then restart the app. See the README's \"Keep all files in sync\" note for details."
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

st.set_page_config(
    page_title="Local Daily Companion",
    page_icon="🧭",
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

if "view" not in st.session_state:
    st.session_state.view = "home"  # the Home page is the default view on launch

# --------------------------------------------------------------------------
# Apply any pending "switch to this account/saved location" request queued
# by a button click on a PREVIOUS run (login on the Home page, or "go to"
# a saved location in the sidebar) -- BEFORE this run creates the
# city/ZIP/profile widgets below.
#
# Why this has to happen here, this early: Streamlit raises a
# StreamlitAPIException ("... cannot be modified after widget ... is
# instantiated") if `st.session_state[key]` is written AFTER the widget
# with that key has already been drawn in the SAME script run. The Home
# page's login form and the sidebar's saved-locations "go" button both
# render AFTER the sidebar's city/ZIP widgets in a normal top-to-bottom
# run, so writing directly to those keys from inside either of them used
# to crash the app on the very first click (fixed by queuing the request
# there and applying it here instead, at the top of the NEXT run, before
# any widget exists yet). See accounts.queue_apply_on_next_run() and
# user_profile.queue_location_apply() for the queuing side of this.
# --------------------------------------------------------------------------
accounts.consume_pending_apply(CITY_KEY, ZIP_KEY, PROFILE_KEY_PREFIX, ZIP_CITY_CONTEXT_KEY)
user_profile.consume_pending_location(CITY_KEY, ZIP_KEY, ZIP_CITY_CONTEXT_KEY)

# --------------------------------------------------------------------------
# Styling -- a clean, modern "web app" system: a soft off-white/slate canvas
# with crisp, elevated white cards floating on top of it, one consistent
# pill-shaped button/tab language, and a bold deep-slate-to-emerald gradient
# reserved for the handful of "look here first" moments (the hero banner,
# the outlook banner, primary buttons). Shared tokens (--card-border,
# --card-shadow, --card-radius, --accent-grad) keep every card/button across
# every page speaking the same visual language instead of a per-page
# one-off style, which is what keeps a hand-built app from reading as a
# pile of mismatched Streamlit defaults.
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        --card-border: #E2E8F0;
        --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        --card-radius: 16px;
        --accent-grad: linear-gradient(120deg, #0f172a 0%, #0f766e 55%, #10b981 100%);
        background: linear-gradient(180deg, #F8FAFC 0%, #EDF2F7 100%);
        background-attachment: fixed;
    }
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1180px; }
    h1, h2, h3 { letter-spacing: -0.01em; color: #0f172a; }

    /* -- Consistent button/input/divider rhythm across every page -- one
       shared shape language instead of each widget using Streamlit's raw
       defaults, so the whole app reads as one designed product. Buttons are
       pill-shaped with a soft lift-and-glow on hover; primaryColor in
       .streamlit/config.toml drives the vibrant emerald fill on "primary"
       buttons (Log In, Sign Up, Save, etc.) so we don't have to chase
       Streamlit's internal button markup across versions with CSS. -- */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        border-radius: 999px;
        font-weight: 700;
        padding: 0.55rem 1.35rem;
        border-color: var(--card-border);
        transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.14);
        filter: brightness(1.04);
    }
    .stButton > button:active, .stDownloadButton > button:active, .stFormSubmitButton > button:active {
        transform: translateY(0);
        filter: brightness(0.98);
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="select"] > div {
        border-radius: 10px !important;
    }
    hr { margin: 0.7rem 0 !important; opacity: 0.14; }
    div[data-testid="stExpander"] {
        border-radius: var(--card-radius);
        border: 1px solid var(--card-border) !important;
        box-shadow: var(--card-shadow);
    }
    div[data-testid="column"] { padding: 0 8px; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--card-radius) !important;
        box-shadow: var(--card-shadow);
    }

    /* -- Pill-style tabs (Log In / Sign Up / Continue as Guest, and the
       Transit / Air Quality / Community Hub tabs) instead of Streamlit's
       plain underlined default. -- */
    div[data-baseweb="tab-list"] {
        gap: 6px;
        background: #eef2f7;
        padding: 6px;
        border-radius: 999px;
        border: 1px solid var(--card-border);
    }
    div[data-baseweb="tab"] {
        border-radius: 999px !important;
        padding: 8px 20px !important;
        font-weight: 700;
    }
    div[data-baseweb="tab-highlight"] { background: transparent !important; }
    div[data-baseweb="tab"][aria-selected="true"] {
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    }

    /* -- Branding hero card (Home page, and other lightweight headers) --
       deep slate fading into a vibrant emerald/teal accent, large callout
       type, and a row of structured badge tags underneath the tagline. -- */
    .hero-banner {
        background: var(--accent-grad);
        border-radius: 22px;
        padding: 34px 38px;
        margin-bottom: 22px;
        color: #ffffff;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.22);
    }
    .hero-banner .hero-eyebrow {
        font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em;
        font-weight: 800; color: rgba(255,255,255,0.75); margin-bottom: 10px;
    }
    .hero-banner h1 { color: #ffffff; margin-bottom: 10px; font-size: 2.5rem; line-height: 1.12; font-weight: 800; }
    .hero-banner p { color: rgba(255,255,255,0.92); margin: 0; font-size: 1.08rem; max-width: 640px; line-height: 1.55; }
    .hero-badges { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
    .hero-badge {
        background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.3);
        color: #ffffff;
        padding: 7px 16px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        white-space: nowrap;
    }

    /* -- Elevated "feature preview" cards (Home page, logged-out) -- */
    .preview-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        box-shadow: var(--card-shadow);
        padding: 18px 20px;
        margin-bottom: 14px;
    }
    .preview-eyebrow {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
        font-weight: 800; color: #64748b; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .preview-live-dot {
        display: inline-block; width: 7px; height: 7px; border-radius: 50%;
        background: #10b981; margin-right: 5px; box-shadow: 0 0 0 3px rgba(16,185,129,0.18);
    }
    .delay-pill {
        display: inline-flex; align-items: center; gap: 8px;
        padding: 8px 16px; border-radius: 999px; font-weight: 700; font-size: 0.95rem;
    }
    .pill-good    { background: rgba(16,185,129,0.12); color: #067a55; }
    .pill-caution { background: rgba(240,162,2,0.14); color: #8a5a00; }
    .pill-hazard  { background: rgba(185,28,28,0.12); color: #b91c1c; }

    .feature-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        box-shadow: var(--card-shadow);
        padding: 20px 20px;
        min-height: 148px;
    }
    .feature-card .feature-icon { font-size: 1.5rem; margin-bottom: 8px; }
    .feature-card .feature-title { font-weight: 800; font-size: 1.02rem; color: #0f172a; margin-bottom: 6px; }
    .feature-card .feature-body { font-size: 0.88rem; color: #475569; line-height: 1.5; }

    /* -- The "Aha" outlook banner -- the very first thing on the dashboard,
       color-coded by today's overall verdict (see outlook.py). Colors are
       set inline per-render via style="background:...;color:...", these
       rules just handle layout/shape. -- */
    .outlook-banner {
        border-radius: 22px;
        padding: 28px 32px;
        margin-bottom: 18px;
        box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
    }
    .outlook-banner .outlook-eyebrow {
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.09em;
        font-weight: 800; opacity: 0.85; margin-bottom: 8px;
    }
    .outlook-banner h1 { margin: 0 0 8px 0; font-size: 2.05rem; line-height: 1.15; }
    .outlook-banner .outlook-sub { font-size: 1.05rem; font-weight: 700; margin: 0; }
    .outlook-banner .outlook-lead { font-size: 0.92rem; opacity: 0.9; margin-top: 8px; }

    /* -- Vivid, color-coded status tiles (Transit / AQI / Pollen) -- */
    .status-tile {
        border-radius: 18px;
        padding: 18px 20px;
        min-height: 132px;
        margin-bottom: 12px;
        box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
    }
    .status-tile .tile-label {
        font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.06em;
        font-weight: 800; opacity: 0.85; margin-bottom: 8px;
    }
    .status-tile .tile-value { font-size: 1.65rem; font-weight: 800; line-height: 1.2; }
    .status-tile .tile-note { font-size: 0.84rem; margin-top: 8px; opacity: 0.92; line-height: 1.4; }
    .tile-good    { background: linear-gradient(135deg, #12a454 0%, #0d9488 100%); color: #ffffff; }
    .tile-caution { background: linear-gradient(135deg, #f7c948 0%, #f0a202 100%); color: #3d2a00; }
    .tile-hazard  { background: linear-gradient(135deg, #e64848 0%, #b91c1c 100%); color: #ffffff; }

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

    .transit-card {
        background: #ffffff;
        border: 1px solid var(--card-border);
        border-left: 6px solid var(--accent, #0f766e);
        border-radius: var(--card-radius);
        padding: 14px 20px;
        margin-bottom: 10px;
        box-shadow: var(--card-shadow);
    }
    .transit-card .tc-top { display: flex; justify-content: space-between; font-weight: 700; font-size: 1.05rem; color: #0f172a; }
    .transit-card .tc-eta { color: #0f766e; font-weight: 800; }
    .transit-card .tc-station { font-size: 0.95rem; color: #0f172a; margin-top: 2px; }
    .transit-card .tc-meta { font-size: 0.82rem; color: #64748b; margin-top: 6px; }

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
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧭 Local Daily Companion")
    st.caption("Your city, your commute, your air.")

    def _go_to(view_name: str):
        # A plain on_click callback -- Streamlit runs this BEFORE the script
        # reruns, so it's always safe to write straight to st.session_state
        # here (even to a widget-bound key) with no extra rerun/queueing
        # needed: the callback finishes, then the one automatic rerun that
        # follows any widget interaction picks up the new value. That's a
        # single state transition per click, with nothing rendered in
        # between using the stale value.
        st.session_state.view = view_name

    nav_l, nav_r = st.columns(2, gap="small")
    with nav_l:
        st.button("🏠 Home", use_container_width=True, on_click=_go_to, args=("home",),
                   type="primary" if st.session_state.view == "home" else "secondary")
    with nav_r:
        st.button("🧭 Dashboard", use_container_width=True, on_click=_go_to, args=("app",),
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
        # This fallback call is wrapped too: "the fallback itself might fail" is exactly the
        # kind of edge case a defensive sweep is supposed to close, not just move one level
        # deeper. A last-resort hardcoded shape keeps every downstream .get() call satisfied
        # even if cities.py itself is completely unavailable.
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
    # index). Earlier code kept an INDEX in this same slot and compared it
    # with `>= len(zip_options)` to guard against a shorter ZIP list after
    # switching cities -- but anything that ever wrote a ZIP STRING into
    # that slot instead (a saved location, a saved account default) made
    # that comparison crash with `TypeError: '>=' not supported between
    # instances of 'str' and 'int'`. Standardizing on "ZIP_KEY is always a
    # string, always validated with is_valid_zip()" removes that whole
    # class of bug AND is what makes "type any real ZIP code" possible.
    # ------------------------------------------------------------------
    zip_options = city_info["zips"]
    featured_zip_values = [z["zip"] for z in zip_options]
    featured_labels = {z["zip"]: f"{z['zip']} — {z['neighborhood']}" for z in zip_options}

    if st.session_state.get(ZIP_CITY_CONTEXT_KEY) != city:
        # City changed since ZIP_KEY was last set -- reset to that city's
        # first featured ZIP rather than carrying over a ZIP that belongs
        # to a different city. NOTE: a saved-location/account apply that
        # sets city AND zip together also updates ZIP_CITY_CONTEXT_KEY to
        # match (see accounts.apply_account_to_session /
        # user_profile.apply_location), specifically so THIS branch does
        # NOT fire and clobber a just-applied ZIP with the new city's
        # generic default the moment that city change is noticed here.
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
             "transit and air-quality simulations are tailored to the exact ZIP you enter.",
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
            "doesn't ship a full ZIP-to-neighborhood directory, so transit and air-quality data "
            f"below is simulated and tailored to this exact ZIP using {city}'s real transit "
            "system and coordinates."
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
    user_profile.render_saved_locations_sidebar(
        current_city=city, current_zip=selected_zip["zip"], current_neighborhood=selected_zip["neighborhood"],
        city_key=CITY_KEY, zip_key=ZIP_KEY, zip_city_context_key=ZIP_CITY_CONTEXT_KEY,
    )

    st.divider()
    user_profile.render_profile_toggles()

    st.divider()
    user_profile.render_notification_preferences()

    def _log_out_and_go_home():
        accounts.log_out()
        st.session_state.view = "home"

    if accounts.is_logged_in():
        st.divider()
        st.markdown("#### 👤 Your account")
        st.caption(accounts.storage_mode_label())
        if st.button("💾 Save city/ZIP/profile as my defaults", use_container_width=True):
            saved_ok = accounts.save_preferences(accounts.current_user(), city, selected_zip["zip"], user_profile.get_profile())
            if saved_ok:
                st.success("Saved — you'll see this instantly on your Home page from now on.")
            else:
                st.error("Couldn't save your defaults right now — please try again in a moment.")
        st.button("Log out", use_container_width=True, key="sidebar_logout", on_click=_log_out_and_go_home)

    st.divider()
    st.caption(
        f"**{len(CITY_NAMES)} real cities, real transit agencies, real station names.** Live "
        "arrival times and air-quality readings use clearly-labeled simulated "
        "or fallback data where a live feed isn't available — see each tab "
        "for details."
    )
    st.caption("Built with Streamlit, Plotly, and the OpenAQ API.")

    st.divider()
    feedback_identity = accounts.current_user() if accounts.is_logged_in() else community.get_guest_id()
    feedback.render_feedback_widget(feedback_identity)

# --------------------------------------------------------------------------
# Compute "right now" once per run -- shared by the briefing, the personal
# alerts, and both tabs, so every part of the page agrees with every other
# part, and a live OpenAQ call never happens more than once per rerun.
# --------------------------------------------------------------------------
profile = user_profile.get_profile()

try:
    transit_seed = transit.get_current_seed(city, selected_zip["zip"])
    accessibility_now = transit.generate_station_accessibility(city, transit_seed)
    transit_status = transit.get_current_status_summary(city, accessibility_now, now=city_now)
except Exception:
    transit_seed, accessibility_now = None, None
    transit_status = {"level": "smooth", "phrase": "transit status is unavailable right now",
                       "elevator_outages": 0, "outage_stations": [], "delay_min": None}

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
    pollen_reading = pollen.simulate_pollen(city, selected_zip["zip"], now=city_now)
except Exception:
    pollen_reading = {"value": None, "category": "No data", "color": "#898781", "emoji": "❔",
                       "dominant_allergen": "", "advice": "Pollen data is unavailable right now.",
                       "source": "simulated", "as_of": city_now}

# --------------------------------------------------------------------------
# Daily Briefing text -- built once, shared by the Home page and the
# dashboard's own briefing banner below, so the two views can never
# disagree with each other.
# --------------------------------------------------------------------------
briefing_text = briefing.build_daily_briefing(transit_status, aqi_reading, profile, now=city_now)

# --------------------------------------------------------------------------
# The "Aha" outlook -- one overall good/caution/hazard verdict rolling up
# transit + AQI + pollen, computed once and shared by the banner below AND
# the three status tiles, so they can never contradict each other.
# --------------------------------------------------------------------------
try:
    today_outlook = outlook.compute_outlook(transit_status, aqi_reading, pollen_reading)
except Exception:
    today_outlook = {
        "tier": "caution", "headline": outlook.HEADLINES["caution"], "lead": "",
        "subtext": "Some of today's data is unavailable right now.",
        "colors": outlook.TIER_COLORS["caution"], "tiers": {"transit": "caution", "aqi": "caution", "pollen": "caution"},
    }

# --------------------------------------------------------------------------
# Home view vs. Dashboard view
# --------------------------------------------------------------------------
if st.session_state.view == "home":
    homepage.render_homepage(
        city=city, neighborhood=selected_zip["neighborhood"], zip_code=selected_zip["zip"],
        briefing_text=briefing_text, transit_status=transit_status, aqi_reading=aqi_reading,
        pollen_reading=pollen_reading, outlook_data=today_outlook, city_now=city_now,
    )
    st.stop()

# --------------------------------------------------------------------------
# The "Aha" banner -- the very first thing on the dashboard. Whatever
# today's overall verdict is, a first-time visitor should be able to read
# it in the time it takes the page to load, before looking at a single tab.
# --------------------------------------------------------------------------
colors = today_outlook["colors"]
st.markdown(
    f"""
    <div class="outlook-banner" style="background:{colors['gradient']}; color:{colors['text']}">
        <div class="outlook-eyebrow">Today's Outlook · {city}</div>
        <h1>{today_outlook['headline']}</h1>
        <p class="outlook-sub">{today_outlook['subtext']}</p>
        <p class="outlook-lead" style="color:{colors['sub_text']}">{today_outlook['lead']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Three vivid, color-coded status tiles -- Transit / Air Quality / Pollen --
# scannable well under 3 seconds, each tinted by its OWN tier from
# today_outlook["tiers"] (not just the overall banner's tier), so a single
# rough spot never gets visually buried by two good ones.
# --------------------------------------------------------------------------
tiers = today_outlook["tiers"]
tile_l, tile_m, tile_r = st.columns(3)
with tile_l:
    level_label = {"smooth": "Smooth", "minor": "Minor delays", "major": "Major delays"}.get(
        transit_status.get("level"), "Unavailable"
    )
    delay_min = transit_status.get("delay_min")
    outages = transit_status.get("elevator_outages", 0) or 0
    note = f"{delay_min} min avg delay" if delay_min is not None else "Delay data unavailable"
    note += f" · {outages} elevator outage{'s' if outages != 1 else ''}"
    st.markdown(
        f"""
        <div class="status-tile tile-{tiers['transit']}">
            <div class="tile-label">🚌 Transit</div>
            <div class="tile-value">{level_label}</div>
            <div class="tile-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with tile_m:
    aqi_val = aqi_reading.get("aqi")
    st.markdown(
        f"""
        <div class="status-tile tile-{tiers['aqi']}">
            <div class="tile-label">🌬️ Air Quality</div>
            <div class="tile-value">{aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'} · {aqi_reading.get('label', 'No data')}</div>
            <div class="tile-note">{aqi_reading['risk']['advice'] if aqi_reading.get('risk') else 'No advice available.'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with tile_r:
    pollen_val = pollen_reading.get("value")
    st.markdown(
        f"""
        <div class="status-tile tile-{tiers['pollen']}">
            <div class="tile-label">🌼 Pollen</div>
            <div class="tile-value">{pollen_reading.get('emoji', '❔')} {pollen_val if pollen_val is not None else '—'} · {pollen_reading.get('category', 'No data')}</div>
            <div class="tile-note">{pollen_reading.get('advice', 'No advice available.')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------
# Dashboard's own Daily Briefing card -- kept as a smaller, secondary detail
# below the bold outlook banner above, for anyone who wants the one-sentence
# version with the exact timestamp.
# --------------------------------------------------------------------------
try:
    briefing_tz = f" {city_now:%Z}".rstrip()
except Exception:
    briefing_tz = ""
st.markdown(
    f"""
    <div class="briefing-card">
        <div class="briefing-label">📰 Daily Briefing</div>
        <div class="briefing-text">{briefing_text}</div>
        <div class="briefing-time">As of {city_now:%A, %B %d, %Y — %I:%M %p}{briefing_tz} · {city}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Personal alerts (only shown for profile toggles the user turned on)
# --------------------------------------------------------------------------
user_profile.render_personal_alerts(city, profile, aqi_reading, transit_status, now=city_now)

# --------------------------------------------------------------------------
# Save or share today's outlook -- a calendar file for a recurring morning
# reminder, or a paste-ready text summary. Both built from the exact same
# values as everything above, via exports.py.
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
                event_title=f"Daily Commute Briefing — {city}",
                description=briefing_text,
                start_local=event_start,
            )
            st.download_button(
                "⬇️ Download Daily Commute Calendar Event (.ics)",
                data=ics_content,
                file_name="daily_commute_briefing.ics",
                mime="text/calendar",
                use_container_width=True,
            )
            st.caption(f"Repeats daily at {reminder_time.strftime('%I:%M %p')} once imported into your calendar app.")
        except Exception as e:  # noqa: BLE001
            st.caption(f"Calendar export unavailable right now ({e}).")

    with export_col2:
        st.markdown("**📋 Copy today's summary**")
        try:
            summary_text = exports.build_shareable_summary(
                city=city, zip_code=selected_zip["zip"], outlook=today_outlook, briefing_text=briefing_text,
                transit_status=transit_status, aqi_reading=aqi_reading, pollen_reading=pollen_reading, now=city_now,
            )
            st.code(summary_text, language=None)
            st.caption("Use the copy icon in the corner above to copy this to your clipboard.")
        except Exception as e:  # noqa: BLE001
            st.caption(f"Summary export unavailable right now ({e}).")

tab_transit, tab_air, tab_community = st.tabs([
    "🚌 Transit Accessibility & Delays", "🌬️ Air Quality & Asthma Alerts", "🏘️ Community Hub",
])

with tab_transit:
    try:
        transit.render_transit_tab(
            city, selected_zip["neighborhood"], seed=transit_seed, accessibility_df=accessibility_now,
            now=city_now, zip_code=selected_zip["zip"],
            logged_in_user=accounts.current_user() if accounts.is_logged_in() else None,
        )
    except Exception as e:  # noqa: BLE001 -- last-resort guard so a bad render never blanks the whole app
        st.error("Something went wrong loading the transit tracker for this city. Try refreshing or picking a different city.")
        st.caption(f"Technical detail: {e}")

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
            transit_status=transit_status,
            aqi_reading=aqi_reading,
            pollen_reading=pollen_reading,
            logged_in_user=accounts.current_user() if accounts.is_logged_in() else None,
            now=city_now,
        )
    except Exception as e:  # noqa: BLE001
        st.error("Something went wrong loading the Community Hub for this town. Try refreshing or picking a different city.")
        st.caption(f"Technical detail: {e}")
