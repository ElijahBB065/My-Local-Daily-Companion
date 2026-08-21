"""
app.py
Local Daily Companion -- Streamlit entrypoint.

Two tabs:
  1. Transit Accessibility & Delay Tracker
  2. Air Quality & Asthma Hazard Alerts

...plus three personal features that sit above both tabs:
  - Saved Locations (Home / Work / School-style presets) in the sidebar
  - A Personal Sensitivity Profile (asthma, wheelchair/stroller access)
    that drives custom warning badges on the main dashboard
  - A one-sentence Daily Briefing banner combining transit + air quality

Every city, transit agency, line, and station name is real. Live transit
arrivals aren't available from a single free API across a dozen agencies,
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
"""

import streamlit as st

import air_quality
import briefing
import transit
import user_profile
from cities import CITY_NAMES, get_city, now_in_city

st.set_page_config(
    page_title="Local Daily Companion",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

CITY_KEY = "selected_city_key"
ZIP_KEY = "selected_zip_idx_key"

# --------------------------------------------------------------------------
# Styling -- bright, playful, card-based
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.6rem; max-width: 1150px; }
    h1, h2, h3 { letter-spacing: -0.01em; }

    .hero-banner {
        background: linear-gradient(120deg, #2a78d6 0%, #4a3aa7 55%, #1baf7a 100%);
        border-radius: 18px;
        padding: 22px 28px;
        margin-bottom: 20px;
        color: #ffffff;
    }
    .hero-banner h1 { color: #ffffff; margin-bottom: 4px; font-size: 1.9rem; }
    .hero-banner p { color: rgba(255,255,255,0.92); margin: 0; font-size: 1rem; }

    .briefing-card {
        background: linear-gradient(120deg, #fff8e6 0%, #eef4fc 100%);
        border: 1px solid rgba(11,11,11,0.08);
        border-radius: 16px;
        padding: 16px 22px;
        margin-bottom: 16px;
    }
    .briefing-card .briefing-label {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: #52514e; font-weight: 700; margin-bottom: 4px;
    }
    .briefing-card .briefing-text { font-size: 1.15rem; font-weight: 600; color: #0b0b0b; line-height: 1.4; }
    .briefing-card .briefing-time { font-size: 0.78rem; color: #898781; margin-top: 6px; }

    .alerts-heading { font-size: 1rem; font-weight: 700; color: #0b0b0b; margin: 4px 0 8px 0; }
    .alert-card {
        background: color-mix(in srgb, var(--accent, #898781) 9%, #fcfcfb);
        border: 1px solid rgba(11,11,11,0.08);
        border-left: 6px solid var(--accent, #898781);
        border-radius: 14px;
        padding: 12px 18px;
        margin-bottom: 10px;
    }
    .alert-card .alert-top { font-weight: 700; font-size: 0.98rem; color: #0b0b0b; }
    .alert-card .alert-body { font-size: 0.88rem; color: #33322f; margin-top: 4px; line-height: 1.5; }

    .companion-banner {
        background: #eef4fc;
        border: 1px solid rgba(42,120,214,0.25);
        border-radius: 12px;
        padding: 12px 18px;
        margin-bottom: 16px;
        color: #0b0b0b;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    .metric-card {
        background: #fcfcfb;
        border: 1px solid rgba(11,11,11,0.10);
        border-left: 5px solid var(--accent, #898781);
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 12px;
        min-height: 108px;
    }
    .metric-card .mc-label { font-size: 0.75rem; color: #52514e; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; font-weight: 700; }
    .metric-card .mc-value { font-size: 1.65rem; font-weight: 800; color: #0b0b0b; line-height: 1.15; }
    .metric-card .mc-note { font-size: 0.8rem; color: #52514e; margin-top: 6px; }

    .transit-card {
        background: #fcfcfb;
        border: 1px solid rgba(11,11,11,0.08);
        border-left: 6px solid var(--accent, #2a78d6);
        border-radius: 14px;
        padding: 12px 18px;
        margin-bottom: 10px;
    }
    .transit-card .tc-top { display: flex; justify-content: space-between; font-weight: 700; font-size: 1.05rem; color: #0b0b0b; }
    .transit-card .tc-eta { color: #2a78d6; font-weight: 800; }
    .transit-card .tc-station { font-size: 0.95rem; color: #0b0b0b; margin-top: 2px; }
    .transit-card .tc-meta { font-size: 0.82rem; color: #52514e; margin-top: 6px; }

    .aqi-hero {
        background: #fcfcfb;
        border: 2px solid var(--accent, #2a78d6);
        border-radius: 18px;
        padding: 20px 26px;
        margin-bottom: 16px;
        text-align: center;
    }
    .aqi-hero .aqi-hero-value { font-size: 3rem; font-weight: 800; color: var(--accent, #0b0b0b); line-height: 1; }
    .aqi-hero .aqi-hero-label { font-size: 1.15rem; font-weight: 700; color: #0b0b0b; margin-top: 6px; }
    .aqi-hero .aqi-hero-sub { font-size: 0.88rem; color: #52514e; margin-top: 4px; }

    .risk-card {
        background: #fcfcfb;
        border: 1px solid rgba(11,11,11,0.10);
        border-left: 6px solid var(--accent, #898781);
        border-radius: 14px;
        padding: 14px 20px;
        margin: 14px 0 6px 0;
    }
    .risk-card .risk-top { font-size: 1.1rem; color: #0b0b0b; margin-bottom: 4px; }
    .risk-card .risk-advice { font-size: 0.92rem; color: #33322f; line-height: 1.5; }

    .report-card {
        background: #fcfcfb;
        border: 1px solid rgba(11,11,11,0.08);
        border-left: 5px solid var(--accent, #898781);
        border-radius: 12px;
        padding: 10px 16px;
        margin-bottom: 8px;
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
    st.divider()

    city = st.selectbox("🏙️ Choose your city", options=CITY_NAMES, key=CITY_KEY)
    city_info = get_city(city)

    zip_options = city_info["zips"]
    zip_labels = [f"{z['zip']} — {z['neighborhood']}" for z in zip_options]
    if st.session_state.get(ZIP_KEY, 0) >= len(zip_options):
        st.session_state[ZIP_KEY] = 0  # guard against a shorter ZIP list after switching cities
    zip_choice_idx = st.selectbox(
        "📍 Neighborhood / ZIP code", options=range(len(zip_options)),
        format_func=lambda i: zip_labels[i], key=ZIP_KEY,
    )
    selected_zip = zip_options[zip_choice_idx]

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
    transit_seed = transit.get_current_seed(city)
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

# --------------------------------------------------------------------------
# Daily Briefing banner
# --------------------------------------------------------------------------
briefing_text = briefing.build_daily_briefing(transit_status, aqi_reading, profile, now=city_now)
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
# Header
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-banner">
        <h1>🧭 Local Daily Companion</h1>
        <p>🚌 Transit &amp; accessibility, and 🌬️ air quality &amp; asthma alerts for {city}.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_transit, tab_air = st.tabs(["🚌 Transit Accessibility & Delays", "🌬️ Air Quality & Asthma Alerts"])

with tab_transit:
    try:
        transit.render_transit_tab(
            city, selected_zip["neighborhood"], seed=transit_seed, accessibility_df=accessibility_now,
            now=city_now,
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
