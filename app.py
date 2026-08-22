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
    import exports
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
        "`user_profile.py`, `briefing.py`, `outlook.py`, `pollen.py`, `exports.py`, and `charts.py` "
        "are delivered together and depend on each other, so please make sure **all** of them are "
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
# Styling -- a calmer, transit-map-inspired light backdrop with crisp white
# cards floating on top of it. The background texture is two very faint
# repeating diagonal line sets (a nod to overlapping subway lines on a
# system map) rather than a flat white page -- subtle enough to disappear
# once real content is on screen, but enough to keep the page from feeling
# like a bare form.
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #eef1f6;
        background-image:
            repeating-linear-gradient(120deg, rgba(42,120,214,0.05) 0px, rgba(42,120,214,0.05) 1.5px, transparent 1.5px, transparent 46px),
            repeating-linear-gradient(60deg, rgba(27,175,122,0.045) 0px, rgba(27,175,122,0.045) 1.5px, transparent 1.5px, transparent 64px),
            repeating-linear-gradient(0deg, rgba(74,58,167,0.03) 0px, rgba(74,58,167,0.03) 1.5px, transparent 1.5px, transparent 80px);
        background-attachment: fixed;
    }
    .block-container { padding-top: 1.6rem; max-width: 1180px; }
    h1, h2, h3 { letter-spacing: -0.01em; }

    /* -- Branding banner (Home page, and other lightweight headers) -- */
    .hero-banner {
        background: linear-gradient(120deg, #2a78d6 0%, #4a3aa7 55%, #1baf7a 100%);
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 20px;
        color: #ffffff;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
    }
    .hero-banner h1 { color: #ffffff; margin-bottom: 4px; font-size: 1.9rem; }
    .hero-banner p { color: rgba(255,255,255,0.92); margin: 0; font-size: 1rem; }

    /* -- The "Aha" outlook banner -- the very first thing on the dashboard,
       color-coded by today's overall verdict (see outlook.py). Colors are
       set inline per-render via style="background:...;color:...", these
       rules just handle layout/shape. -- */
    .outlook-banner {
        border-radius: 18px;
        padding: 26px 30px;
        margin-bottom: 18px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.16);
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
        border-radius: 16px;
        padding: 18px 20px;
        min-height: 132px;
        margin-bottom: 12px;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.10);
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
        border: 1px solid rgba(15,23,42,0.06);
        border-radius: 16px;
        padding: 16px 22px;
        margin-bottom: 16px;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.06);
    }
    .briefing-card .briefing-label {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #52514e; font-weight: 700; margin-bottom: 4px;
    }
    .briefing-card .briefing-text { font-size: 1.1rem; font-weight: 600; color: #0b0b0b; line-height: 1.4; }
    .briefing-card .briefing-time { font-size: 0.78rem; color: #898781; margin-top: 6px; }

    .alerts-heading { font-size: 1rem; font-weight: 700; color: #0b0b0b; margin: 4px 0 8px 0; }
    .alert-card {
        background: color-mix(in srgb, var(--accent, #898781) 9%, #ffffff);
        border: 1px solid rgba(15,23,42,0.06);
        border-left: 6px solid var(--accent, #898781);
        border-radius: 14px;
        padding: 12px 18px;
        margin-bottom: 10px;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
    }
    .alert-card .alert-top { font-weight: 700; font-size: 0.98rem; color: #0b0b0b; }
    .alert-card .alert-body { font-size: 0.88rem; color: #33322f; margin-top: 4px; line-height: 1.5; }

    .companion-banner {
        background: #eef4fc;
        border: 1px solid rgba(42,120,214,0.2);
        border-radius: 14px;
        padding: 12px 18px;
        margin-bottom: 16px;
        color: #0b0b0b;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid rgba(15,23,42,0.07);
        border-left: 5px solid var(--accent, #898781);
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 12px;
        min-height: 108px;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
    }
    .metric-card .mc-label { font-size: 0.75rem; color: #52514e; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; font-weight: 700; }
    .metric-card .mc-value { font-size: 1.65rem; font-weight: 800; color: #0b0b0b; line-height: 1.15; }
    .metric-card .mc-note { font-size: 0.8rem; color: #52514e; margin-top: 6px; }

    .transit-card {
        background: #ffffff;
        border: 1px solid rgba(15,23,42,0.06);
        border-left: 6px solid var(--accent, #2a78d6);
        border-radius: 14px;
        padding: 12px 18px;
        margin-bottom: 10px;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
    }
    .transit-card .tc-top { display: flex; justify-content: space-between; font-weight: 700; font-size: 1.05rem; color: #0b0b0b; }
    .transit-card .tc-eta { color: #2a78d6; font-weight: 800; }
    .transit-card .tc-station { font-size: 0.95rem; color: #0b0b0b; margin-top: 2px; }
    .transit-card .tc-meta { font-size: 0.82rem; color: #52514e; margin-top: 6px; }

    .aqi-hero {
        background: #ffffff;
        border: 2px solid var(--accent, #2a78d6);
        border-radius: 18px;
        padding: 20px 26px;
        margin-bottom: 16px;
        text-align: center;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.07);
    }
    .aqi-hero .aqi-hero-value { font-size: 3rem; font-weight: 800; color: var(--accent, #0b0b0b); line-height: 1; }
    .aqi-hero .aqi-hero-label { font-size: 1.15rem; font-weight: 700; color: #0b0b0b; margin-top: 6px; }
    .aqi-hero .aqi-hero-sub { font-size: 0.88rem; color: #52514e; margin-top: 4px; }

    .risk-card {
        background: #ffffff;
        border: 1px solid rgba(15,23,42,0.07);
        border-left: 6px solid var(--accent, #898781);
        border-radius: 14px;
        padding: 14px 20px;
        margin: 14px 0 6px 0;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
    }
    .risk-card .risk-top { font-size: 1.1rem; color: #0b0b0b; margin-bottom: 4px; }
    .risk-card .risk-advice { font-size: 0.92rem; color: #33322f; line-height: 1.5; }

    .report-card {
        background: #ffffff;
        border: 1px solid rgba(15,23,42,0.06);
        border-left: 5px solid var(--accent, #898781);
        border-radius: 14px;
        padding: 10px 16px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .report-card .rc-top { display: flex; justify-content: space-between; font-weight: 600; color: #0b0b0b; }
    .report-card .rc-details { font-size: 0.85rem; color: #33322f; margin-top: 4px; }
    .report-card .rc-meta { font-size: 0.75rem; color: #898781; margin-top: 6px; }
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

    nav_l, nav_r = st.columns(2)
    with nav_l:
        if st.button("🏠 Home", use_container_width=True,
                      type="primary" if st.session_state.view == "home" else "secondary"):
            st.session_state.view = "home"
            st.rerun()
    with nav_r:
        if st.button("🧭 Dashboard", use_container_width=True,
                      type="primary" if st.session_state.view == "app" else "secondary"):
            st.session_state.view = "app"
            st.rerun()

    if accounts.is_logged_in():
        st.caption(f"👤 Logged in as **{accounts.current_user()}**")
    st.divider()

    city = st.selectbox("🏙️ Choose your city", options=CITY_NAMES, key=CITY_KEY)
    city_info = get_city(city)

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

    zip_lookup = lookup_neighborhood(city, selected_zip_code)
    selected_zip = {"zip": selected_zip_code, "neighborhood": zip_lookup["neighborhood"]}
    if not zip_lookup["known"]:
        st.caption(
            f"ℹ️ {selected_zip_code} isn't one of {city.split(',')[0]}'s featured ZIPs — this demo "
            "doesn't ship a full ZIP-to-neighborhood directory, so transit and air-quality data "
            f"below is simulated and tailored to this exact ZIP using {city}'s real transit "
            "system and coordinates."
        )

    # -- Real, city-local time (not server/UTC time) -----------------------
    city_now = now_in_city(city)
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
        city_key=CITY_KEY, zip_key=ZIP_KEY,
    )

    st.divider()
    user_profile.render_profile_toggles()

    st.divider()
    user_profile.render_notification_preferences()

    if accounts.is_logged_in():
        st.divider()
        st.markdown("#### 👤 Your account")
        if st.button("💾 Save city/ZIP/profile as my defaults", use_container_width=True):
            accounts.save_preferences(accounts.current_user(), city, selected_zip["zip"], user_profile.get_profile())
            st.success("Saved — you'll see this instantly on your Home page from now on.")
        if st.button("Log out", use_container_width=True, key="sidebar_logout"):
            accounts.log_out()
            st.session_state.view = "home"
            st.rerun()

    st.divider()
    st.caption(
        f"**{len(CITY_NAMES)} real cities, real transit agencies, real station names.** Live "
        "arrival times and air-quality readings use clearly-labeled simulated "
        "or fallback data where a live feed isn't available — see each tab "
        "for details."
    )
    st.caption("Built with Streamlit, Plotly, and the OpenAQ API.")

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
        city=city, zip_code=selected_zip["zip"], lat=city_info["lat"], lon=city_info["lon"], now=city_now,
    )
except Exception:
    aqi_reading = {"aqi": None, "label": "No data", "color": "#898781", "emoji": "❔",
                    "risk": air_quality.asthma_risk(None), "source_badge": "", "as_of": city_now}

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

tab_transit, tab_air = st.tabs(["🚌 Transit Accessibility & Delays", "🌬️ Air Quality & Asthma Alerts"])

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
