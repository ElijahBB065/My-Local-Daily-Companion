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

from datetime import datetime, time

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
# Daily Briefing Preferences (morning reminder + export defaults)
# --------------------------------------------------------------------------
NOTIFY_ENABLED_KEY = "notify_morning_enabled"
NOTIFY_TIME_KEY = "notify_morning_time"
DEFAULT_NOTIFY_TIME = time(7, 30)


def render_notification_preferences():
    """A morning-reminder toggle + preferred time, in the sidebar.

    HONESTY NOTE: a browser tab running Streamlit has no way to push a real
    notification to your phone or send an email while it isn't open --
    that needs a backend with its own scheduler and a push/email provider,
    which this project doesn't have. Rather than fake a "notification
    sent!" toast that nothing backs up, this setting does two real things
    instead: it decides whether the homepage greets you with a morning
    reminder banner, and it pre-fills the reminder time used when you build
    the calendar file below in "Save or share today's outlook" -- so the
    .ics event actually fires at the time you asked for, every day, once
    it's in your own calendar app.
    """
    st.markdown("#### 🔔 Daily Briefing Preferences")
    st.checkbox(
        "Remind me every morning", value=False, key=NOTIFY_ENABLED_KEY,
        help="Controls the in-app morning reminder and the default time for the calendar export below — "
             "see the note under Export for why this app can't send a real push notification or email.",
    )
    if st.session_state.get(NOTIFY_ENABLED_KEY):
        st.time_input("Remind me at", value=DEFAULT_NOTIFY_TIME, key=NOTIFY_TIME_KEY)
        st.caption(
            "No real push or email goes out from here — download the daily calendar event below and "
            "your own calendar app will handle the actual alarm at this time, every day."
        )


def get_notification_prefs() -> dict:
    """{'enabled': bool, 'time': datetime.time} -- reads straight from the
    widgets above, so there's exactly one source of truth."""
    return {
        "enabled": bool(st.session_state.get(NOTIFY_ENABLED_KEY, False)),
        "time": st.session_state.get(NOTIFY_TIME_KEY, DEFAULT_NOTIFY_TIME),
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


def apply_location(loc: dict, city_key: str, zip_key: str, zip_city_context_key: str = None):
    """Push a saved location into the sidebar's own city/ZIP widget state
    (by key) so those widgets pick it up automatically on the next rerun.

    ZIP_KEY holds a plain ZIP-code STRING (e.g. "10001"), never a list
    index -- storing anything else here is exactly what used to cause a
    `'>=' not supported between instances of 'str' and 'int'` crash when a
    stray string and an index-based comparison collided. Since ZIP_KEY is
    always a string now, applying a saved location is just this one line.

    IMPORTANT -- widget-key ordering: Streamlit raises a
    StreamlitAPIException ("... cannot be modified after widget ... is
    instantiated") if `st.session_state[key]` is written AFTER the widget
    with that key has already been drawn in the SAME script run. Call this
    function directly only from a point that runs BEFORE the city/ZIP
    widgets are created. From a button click inside
    render_saved_locations_sidebar() below -- which runs AFTER those
    widgets, later in the same sidebar block -- use queue_location_apply()
    instead, which defers this exact call to the start of the NEXT run via
    consume_pending_location().

    `zip_city_context_key`, when given, is also set to the applied city.
    app.py's sidebar resets ZIP_KEY to a generic default whenever it
    notices the selected city doesn't match that context key (i.e. "the
    user just switched cities") -- without also updating it here, applying
    a saved location's city+ZIP together would immediately look like
    exactly that kind of plain city switch and get the freshly applied ZIP
    wiped back to the new city's default a moment later.
    """
    st.session_state[city_key] = loc["city"]
    st.session_state[zip_key] = loc["zip"]
    if zip_city_context_key:
        st.session_state[zip_city_context_key] = loc["city"]


# --------------------------------------------------------------------------
# Deferred apply -- see the big warning in apply_location() above.
# --------------------------------------------------------------------------
PENDING_LOCATION_KEY = "_pending_location_apply"


def queue_location_apply(loc: dict):
    """Record that this saved location should be pushed onto the sidebar's
    city/ZIP widget keys at the START of the next script run, before those
    widgets exist. Call this (not apply_location directly) from the "go to
    this location" button below, then call `st.rerun()`."""
    st.session_state[PENDING_LOCATION_KEY] = loc


def consume_pending_location(city_key: str, zip_key: str, zip_city_context_key: str = None) -> bool:
    """Call this ONCE, at the very top of app.py, before any sidebar
    widget is created. Applies (and clears) a pending
    queue_location_apply() request, if any. Returns True if one was
    applied."""
    loc = st.session_state.pop(PENDING_LOCATION_KEY, None)
    if loc:
        apply_location(loc, city_key, zip_key, zip_city_context_key)
        return True
    return False


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
                queue_location_apply(loc)
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
