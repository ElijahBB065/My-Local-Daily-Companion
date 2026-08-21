"""
user_profile.py
Personal features: saved locations (Home/Work/School-style presets) and a
personal sensitivity profile (asthma, wheelchair/stroller access) that
drives custom warning badges on the main dashboard.

Everything here lives in st.session_state -- same session-only pattern as
the community accessibility reports in transit.py, so it resets when the
app restarts (see README for how to make either of these persistent with
a small SQLite file, if you want that later).
"""

from datetime import datetime

import streamlit as st

from cities import CITY_NAMES, get_city

# --------------------------------------------------------------------------
# Sensitivity profile
# --------------------------------------------------------------------------
SENSITIVITY_OPTIONS = [
    {
        "key": "asthma",
        "label": "🌬️ Asthma / Sensitive Upper Respiratory",
        "help": "We'll add a personal AQI warning on days that could aggravate asthma or respiratory sensitivity.",
    },
    {
        "key": "wheelchair",
        "label": "♿ Wheelchair / Stroller Access Required",
        "help": "We'll flag it up top whenever a station elevator is currently down in your city.",
    },
]
PROFILE_KEY_PREFIX = "profile_toggle_"


def render_profile_toggles():
    st.markdown("#### 🩺 Personal Sensitivity Profile")
    st.caption("Turn on anything that applies to you — we'll flag it if today's conditions are relevant.")
    for opt in SENSITIVITY_OPTIONS:
        st.checkbox(opt["label"], value=False, help=opt["help"], key=PROFILE_KEY_PREFIX + opt["key"])


def get_profile() -> dict:
    """{'asthma': bool, 'wheelchair': bool} -- reads straight from each
    checkbox's own widget state, so there's exactly one source of truth."""
    return {
        opt["key"]: bool(st.session_state.get(PROFILE_KEY_PREFIX + opt["key"], False))
        for opt in SENSITIVITY_OPTIONS
    }


# --------------------------------------------------------------------------
# Saved locations
# --------------------------------------------------------------------------
PRESET_EMOJI = {"Home": "🏠", "Work": "💼", "School": "🎓"}


def _default_saved_locations() -> list:
    """One friendly example so the feature is discoverable on a first
    visit, rather than a silently-empty section. Fully editable/removable."""
    first_city = CITY_NAMES[0]
    first_zip = get_city(first_city)["zips"][0]
    return [{
        "label": "Home",
        "city": first_city,
        "zip": first_zip["zip"],
        "neighborhood": first_zip["neighborhood"],
    }]


def init_locations_state():
    if "saved_locations" not in st.session_state:
        st.session_state.saved_locations = _default_saved_locations()


def save_location(label: str, city: str, zip_code: str, neighborhood: str):
    label = label.strip() or "Saved spot"
    # replace any existing entry with the same label rather than duplicating
    st.session_state.saved_locations = [
        loc for loc in st.session_state.saved_locations if loc["label"] != label
    ]
    st.session_state.saved_locations.append({
        "label": label, "city": city, "zip": zip_code, "neighborhood": neighborhood,
    })


def remove_location(label: str):
    st.session_state.saved_locations = [
        loc for loc in st.session_state.saved_locations if loc["label"] != label
    ]


def apply_location(loc: dict, city_key: str, zip_key: str):
    """Push a saved location into the sidebar's own city/ZIP widget state
    (by key) so those widgets pick it up automatically on the next rerun."""
    st.session_state[city_key] = loc["city"]
    zips = get_city(loc["city"])["zips"]
    idx = next((i for i, z in enumerate(zips) if z["zip"] == loc["zip"]), 0)
    st.session_state[zip_key] = idx


def render_saved_locations_sidebar(current_city: str, current_zip: str, current_neighborhood: str,
                                    city_key: str, zip_key: str):
    init_locations_state()
    st.markdown("#### 📌 Saved Locations")

    if not st.session_state.saved_locations:
        st.caption("No saved locations yet — add one below.")

    for loc in list(st.session_state.saved_locations):
        emoji = PRESET_EMOJI.get(loc["label"], "📍")
        go_col, del_col = st.columns([5, 1])
        with go_col:
            city_short = loc["city"].split(",")[0]
            if st.button(
                f"{emoji} {loc['label']} — {loc['neighborhood']}, {city_short}",
                key=f"loc_go_{loc['label']}", use_container_width=True,
            ):
                apply_location(loc, city_key, zip_key)
                st.rerun()
        with del_col:
            if st.button("✕", key=f"loc_del_{loc['label']}", help=f"Remove '{loc['label']}'"):
                remove_location(loc["label"])
                st.rerun()

    with st.expander("➕ Save current location"):
        st.caption(f"Will save: {current_neighborhood}, {current_city} ({current_zip})")
        label = st.text_input("Label", placeholder="Home, Work, School…", key="new_location_label")
        if st.button("💾 Save this location", use_container_width=True):
            if label.strip():
                save_location(label, current_city, current_zip, current_neighborhood)
                st.rerun()
            else:
                st.warning("Give it a label first, e.g. \"Home\".")


# --------------------------------------------------------------------------
# Personal alert badges (main dashboard)
# --------------------------------------------------------------------------
def _alert_card(icon_and_title: str, body: str, accent: str):
    st.markdown(
        f"""
        <div class="alert-card" style="--accent:{accent}">
            <div class="alert-top">{icon_and_title}</div>
            <div class="alert-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_personal_alerts(city: str, profile: dict, aqi_reading: dict, transit_status: dict, now: datetime = None):
    """Custom warning badges for the main dashboard -- only shown for
    profile toggles the user has actually turned on, and only worded as a
    warning when today's real conditions actually call for one. Reads
    aqi_reading/transit_status computed once in app.py, so this always
    matches the numbers shown in the two tabs below. `now` should be the
    selected city's own local time (cities.now_in_city), not the server's."""
    if not any(profile.values()):
        return
    now = now or datetime.now()

    st.markdown('<div class="alerts-heading">🔔 Your Personal Alerts</div>', unsafe_allow_html=True)

    if profile.get("asthma"):
        risk = aqi_reading["risk"]
        aqi_val = aqi_reading["aqi"]
        if risk["level"] in ("High", "Severe"):
            _alert_card(
                f"🌬️ Asthma Alert — {aqi_reading['label']} air quality",
                f"AQI is {aqi_val} in {city} right now. {risk['advice']}",
                risk["color"],
            )
        elif risk["level"] == "Moderate":
            _alert_card(
                "🌬️ Asthma Note — Moderate air quality",
                f"AQI is {aqi_val} in {city}. {risk['advice']}",
                risk["color"],
            )
        else:
            _alert_card(
                "🌬️ ✅ Air quality looks good",
                f"AQI is {aqi_val} in {city} — a fine day for outdoor activity with your asthma profile.",
                "#0ca30c",
            )

    if profile.get("wheelchair"):
        n = transit_status["elevator_outages"]
        if n > 0:
            stations = transit_status["outage_stations"]
            shown = ", ".join(stations[:4])
            more = f", and {n - 4} more" if n > 4 else ""
            _alert_card(
                f"🛗 Accessibility Alert — {n} elevator outage{'s' if n != 1 else ''}",
                f"{shown}{more} currently {'show' if n != 1 else 'shows'} an elevator out of service in {city}. "
                "Plan an alternate accessible route where possible.",
                "#d03b3b",
            )
        else:
            _alert_card(
                "🛗 ✅ Full accessibility looks good",
                f"No elevator outages reported right now across {city} stations.",
                "#0ca30c",
            )

    try:
        tz_suffix = f" {now:%Z}".rstrip()
    except Exception:
        tz_suffix = ""
    st.caption(
        f"Alerts reflect conditions as of {now:%I:%M %p}{tz_suffix} local time in {city} — "
        "refresh the page any time for the latest."
    )
