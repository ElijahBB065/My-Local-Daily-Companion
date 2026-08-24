"""
homepage.py
The Home view -- the default screen when the app launches.

Logged OUT: a short, minimal pitch for the app, a "Get started" card with
Log In / Sign Up / Guest tabs, a quick "right now" snapshot for whatever
city is selected in the sidebar, and the Environmental Health & Pollen
Outlook card -- an account is never required, every feature works fine
without logging in.

Logged IN: a personalized "Welcome Back" dashboard built from the user's
OWN saved home city and ZIP -- an instant Daily Briefing, transit/air
quality tiles, and the same Environmental Health & Pollen Outlook card --
computed the same way as the main dashboard (see app.py's "compute once"
section), so nothing here can ever disagree with the full dashboard.

DESIGN NOTE (Week 2 simplification pass): an earlier version of this page
had a full gradient hero with a row of badge tags, a three-card live
preview stack, AND a three-column feature grid below it -- it looked
busy. This version keeps exactly one bold moment per page (the hero, or
the outlook banner for a logged-in user) and otherwise favors a small
number of calm, scannable cards over stacked prose or repeated cards
saying similar things.
"""

import streamlit as st

import accounts


def render_status_tile(label: str, value: str, note: str, tier: str = "caution", compact: bool = False):
    """A calm, scannable status tile -- a bold number plus a small
    color-coded badge pill, shared by the main dashboard (app.py) and both
    Home page views below, so there's exactly one visual definition of
    "how we show a status" across the whole app. `compact=True` shrinks it
    slightly for rows of 3-4 tiles instead of 2."""
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


_HAZARD_TIER = {"Low": "good", "Moderate": "caution", "High": "caution", "Very High": "hazard", "Extreme": "hazard"}
_HAZARD_BADGE_EMOJI = {"good": "🟢", "caution": "🟡", "hazard": "🔴"}
_SOURCE_NOTES = {
    "open-meteo (live pollen)": "🟢 Live pollen reading via Open-Meteo.",
    "open-meteo (PM2.5 estimate)": (
        "🟡 Live PM2.5 reading via Open-Meteo — real pollen counts aren't available for this "
        "location, so the hazard level is estimated from PM2.5 and today's Air Quality Index."
    ),
    "simulated": "🧪 Simulated seasonal estimate — Open-Meteo's live reading wasn't available right now.",
    "unavailable": "⚠️ Environmental data is temporarily unavailable.",
}


def render_environmental_card(pollen_reading: dict, aqi_reading: dict = None):
    """The Environmental Health & Pollen Outlook card: one clean card,
    three columns -- Asthma Hazard Level, Dominant Airborne Allergen, and
    a one-sentence Recommended Action for sensitive groups. Built from
    pollen.get_environmental_reading()'s live Open-Meteo reading (used
    directly when real pollen counts exist for this location), its
    PM2.5 + AQI based estimate (the normal case for U.S. cities, where
    Open-Meteo's pollen model doesn't have coverage), or its fully
    simulated fallback if the live API call failed outright -- see
    pollen.py for the full three-case breakdown. Every field is read
    defensively so a partial or malformed reading degrades to safe
    placeholders instead of crashing this card.
    """
    pollen_reading = pollen_reading if isinstance(pollen_reading, dict) else {}
    category = pollen_reading.get("category") or "No data"
    tier = _HAZARD_TIER.get(category, "caution")
    badge_text = f"{_HAZARD_BADGE_EMOJI[tier]} {category}"
    dominant = pollen_reading.get("dominant_allergen") or "Not available right now"
    action = pollen_reading.get("action") or "Check back later for an update."
    source = pollen_reading.get("source", "simulated")
    source_note = _SOURCE_NOTES.get(source, f"🟢 Live reading via Open-Meteo ({source}).")

    try:
        env_box = st.container(border=True)
    except TypeError:
        env_box = st.container()

    with env_box:
        st.markdown("##### 🌼 Environmental Health & Pollen Outlook")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="stat-label">Asthma Hazard Level</div>', unsafe_allow_html=True)
            st.markdown(f'<span class="tile-badge tile-badge-{tier}">{badge_text}</span>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="stat-label">Dominant Airborne Allergen</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{dominant}</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="stat-label">Recommended Action</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-value">{action}</div>', unsafe_allow_html=True)
        st.caption(source_note)


def render_logged_out(city: str = None, neighborhood: str = None, zip_code: str = None,
                       transit_status: dict = None, aqi_reading: dict = None, pollen_reading: dict = None,
                       outlook_data: dict = None, city_now=None):
    """The logged-out landing page: a short hero, a two-column split (a
    'get started' auth card next to a compact live status snapshot), and
    the Environmental Health & Pollen Outlook card. Every optional value
    is normalized defensively since a guest can land here before the rest
    of app.py's "compute once" section has anything meaningful to hand
    over (e.g. the very first run before a city is even resolved).
    """
    transit_status = transit_status if isinstance(transit_status, dict) else {}
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    outlook_data = outlook_data if isinstance(outlook_data, dict) else {}
    tiers = outlook_data.get("tiers", {})
    city_label = (city or "your city").split(",")[0] if city else "your city"

    st.markdown(
        f"""
        <div class="hero-banner">
            <h1>Your city, decoded every morning.</h1>
            <p>Real transit systems, real EPA air-quality math, and a live environmental health
            outlook for {city_label} — sign up to save your spots, or jump right in as a guest.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_auth, col_status = st.columns([1, 1], gap="large")

    with col_auth:
        # st.container(border=True) gives us a real, native elevated card
        # that native widgets (tabs, forms) can sit INSIDE -- unlike a
        # <div> opened via st.markdown, which can't wrap widgets rendered
        # by later, separate Streamlit calls. Older Streamlit releases
        # without the `border` kwarg fall back to a plain container rather
        # than crashing the whole Home page over a styling nicety.
        try:
            auth_box = st.container(border=True)
        except TypeError:
            auth_box = st.container()

        with auth_box:
            st.markdown("#### Get started")
            tab_login, tab_signup, tab_guest = st.tabs(["🔑 Log In", "🆕 Sign Up", "👋 Guest"])

            with tab_login:
                with st.form("login_form", clear_on_submit=False):
                    u = st.text_input("Username", key="login_username")
                    p = st.text_input("Password", type="password", key="login_password")
                    submitted = st.form_submit_button("Log In", use_container_width=True, type="primary")
                    if submitted:
                        ok, msg = accounts.log_in(u, p)
                        if ok:
                            # Don't push this account's saved city/ZIP/profile onto
                            # the sidebar's widget keys HERE -- by the time this
                            # form's submit code runs, the sidebar (and its
                            # city/ZIP widgets) has ALREADY rendered earlier in
                            # this same script run, and Streamlit raises a
                            # StreamlitAPIException ("... cannot be modified after
                            # widget ... is instantiated") if you write to a
                            # widget's session_state key after that widget has
                            # already been drawn this run. Queuing it instead defers
                            # the actual write to the very top of app.py's NEXT
                            # run, before any widget exists yet -- see
                            # accounts.queue_apply_on_next_run().
                            #
                            # (Simpler on_click callbacks are used elsewhere in this
                            # app for the same ordering hazard -- see user_profile's
                            # saved-location buttons -- but a login form specifically
                            # needs to show a conditional success/error message tied
                            # to this exact submit, which an on_click callback can't
                            # cleanly render inline. This queue+rerun is the one
                            # extra step that buys us that inline message.)
                            accounts.queue_apply_on_next_run(u.strip())
                            st.session_state["view"] = "home"
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            with tab_signup:
                with st.form("signup_form", clear_on_submit=False):
                    u = st.text_input("Choose a username", key="signup_username")
                    p = st.text_input(
                        "Choose a password", type="password", key="signup_password",
                        help="Real password security (hashed + salted) -- see the README -- but "
                             "still never reuse a password from a real account here.",
                    )
                    submitted = st.form_submit_button("Sign Up", use_container_width=True, type="primary")
                    if submitted:
                        ok, msg = accounts.sign_up(u, p)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                st.caption(accounts.storage_mode_label())

            with tab_guest:
                st.write("No account needed — just pick a city and ZIP in the sidebar and go.")

                def _go_to_dashboard():
                    st.session_state["view"] = "app"

                st.button("👉 Take me to the dashboard", use_container_width=True, type="primary", on_click=_go_to_dashboard)

    with col_status:
        st.markdown(f"#### Right now in {city_label}")
        level_label = {"smooth": "Smooth", "minor": "Minor delays", "major": "Major delays"}.get(
            transit_status.get("level"), "Checking…"
        )
        outages = transit_status.get("elevator_outages", 0) or 0
        delay_min = transit_status.get("delay_min")
        note = f"{delay_min} min avg delay" if delay_min is not None else "Pick a city to see live delays"
        note += f" · {outages} elevator outage{'s' if outages != 1 else ''}"
        render_status_tile("🚌 Transit", level_label, note, tiers.get("transit"), compact=True)

        aqi_val = aqi_reading.get("aqi")
        value = f"{aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'} · {aqi_reading.get('label', 'No data')}"
        aqi_note = aqi_reading["risk"]["advice"] if aqi_reading.get("risk") else "No advice available yet."
        render_status_tile("🌬️ Air Quality", value, aqi_note, tiers.get("aqi"), compact=True)

    render_environmental_card(pollen_reading, aqi_reading)


def render_logged_in(username: str, city: str = None, neighborhood: str = None, zip_code: str = None,
                      briefing_text: str = None, transit_status: dict = None, aqi_reading: dict = None,
                      pollen_reading: dict = None, outlook_data: dict = None, city_now=None):
    """Renders the personalized 'Welcome back' dashboard.

    Defensive by design: this is called with values computed earlier in
    app.py's own script run, which should always be populated by the time
    this runs -- but a first-ever run, a mid-refactor edit, or some other
    unforeseen ordering hiccup could hand this None/empty values instead
    of real ones. Every value below is normalized to a safe default rather
    than trusted blindly, so a missing piece degrades to a slightly less
    complete-looking page instead of a KeyError/TypeError crash.
    """
    account = accounts.get_account(username)

    city = city or "your saved city"
    neighborhood = neighborhood or ""
    zip_code = zip_code or ""
    briefing_text = briefing_text or "Your daily briefing will appear here once your city and ZIP are set."
    transit_status = transit_status if isinstance(transit_status, dict) else {}
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    pollen_reading = pollen_reading if isinstance(pollen_reading, dict) else {}
    outlook_data = outlook_data if isinstance(outlook_data, dict) else {}
    tiers = outlook_data.get("tiers", {})
    if city_now is None:
        from datetime import datetime
        city_now = datetime.now()

    try:
        tz_suffix = f" {city_now:%Z}".rstrip()
    except Exception:
        tz_suffix = ""
    try:
        time_str = f"{city_now:%I:%M %p}"
    except Exception:
        time_str = "—"

    detail_bits = [b for b in (neighborhood, zip_code) if b]
    location_detail = f" ({', '.join(detail_bits)})" if detail_bits else ""

    if outlook_data.get("headline"):
        colors = outlook_data.get("colors", {"gradient": "linear-gradient(120deg, #2a78d6, #4a3aa7)", "text": "#ffffff", "sub_text": "rgba(255,255,255,0.9)"})
        st.markdown(
            f"""
            <div class="outlook-banner" style="background:{colors['gradient']}; color:{colors['text']}">
                <div class="outlook-eyebrow">Welcome back, {username} · {city}</div>
                <h1>{outlook_data['headline']}</h1>
                <p class="outlook-sub">{outlook_data.get('subtext', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="hero-banner">
                <h1>👋 Welcome back, {username}!</h1>
                <p>Here's what's happening right now in your saved city — {city}{location_detail},
                {time_str}{tz_suffix}.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="briefing-card">
            <div class="briefing-label">📰 Your Daily Briefing</div>
            <div class="briefing-text">{briefing_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        level = transit_status.get("level")
        level_label = {"smooth": "Smooth", "minor": "Minor delays", "major": "Major delays"}.get(level, "Unknown")
        outages = transit_status.get("elevator_outages", 0)
        render_status_tile("🚌 Transit", level_label, f"{outages} elevator outage(s) reported", tiers.get("transit"), compact=True)
    with c2:
        aqi_val = aqi_reading.get("aqi")
        render_status_tile(
            "🌬️ Air quality", f"{aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'}",
            aqi_reading.get("label", "No data"), tiers.get("aqi"), compact=True,
        )
    saved_routes = account.get("saved_routes", []) if account else []
    with c3:
        st.markdown(
            f"""
            <div class="metric-card" style="min-height:104px; padding:14px 16px; --accent:#0f766e;">
                <div class="mc-label">⭐ Saved routes</div>
                <div class="mc-value" style="font-size:1.3rem;">{len(saved_routes)}</div>
                <div class="mc-note">Quick trips saved from the trip planner</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    render_environmental_card(pollen_reading, aqi_reading)

    if saved_routes:
        st.markdown("#### ⭐ Your saved routes")
        for r in saved_routes:
            st.caption(f"**{r.get('label', 'Saved route')}** — {r.get('city', '')}")

    st.write("")

    def _open_dashboard():
        st.session_state["view"] = "app"

    def _log_out():
        accounts.log_out()

    st.button("🧭 Open my full dashboard →", use_container_width=True, type="primary", on_click=_open_dashboard)

    st.divider()
    st.caption(accounts.storage_mode_label())
    st.button("Log out", key="home_logout", on_click=_log_out)


def render_homepage(city=None, neighborhood=None, zip_code=None, briefing_text=None,
                     transit_status=None, aqi_reading=None, pollen_reading=None,
                     outlook_data=None, city_now=None):
    """Entry point called from app.py. Branches on login state; the caller
    supplies the SAME transit_status/aqi_reading/pollen_reading/outlook_data
    objects already computed once for the main dashboard, so the homepage
    and the dashboard can never show conflicting numbers.

    Note: this function no longer needs city_key/zip_key/profile_key_prefix
    -- applying a just-logged-in account's saved defaults onto those
    widget keys is queued (accounts.queue_apply_on_next_run) and processed
    at the very top of app.py's NEXT run instead of during this render;
    see that function's docstring for why.
    """
    if accounts.is_logged_in():
        render_logged_in(
            accounts.current_user(), city, neighborhood, zip_code, briefing_text,
            transit_status, aqi_reading, pollen_reading, outlook_data, city_now,
        )
    else:
        render_logged_out(
            city, neighborhood, zip_code, transit_status, aqi_reading, pollen_reading,
            outlook_data, city_now,
        )
