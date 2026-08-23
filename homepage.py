"""
homepage.py
The Home view -- the default screen when the app launches.

Logged OUT: a short, friendly pitch for the app plus Log In / Sign Up
forms, and a "Continue as Guest" escape hatch (an account is never
required -- every feature works fine without logging in, exactly as
before this feature was added).

Logged IN: a personalized "Welcome Back" dashboard built from the user's
OWN saved home city and ZIP -- an instant Daily Briefing, a quick transit
status chip, and an air-quality summary chip -- computed the same way as
the main dashboard's own briefing (see app.py's "compute once" section),
so nothing here can ever disagree with the full dashboard. No settings
need re-entering.
"""

import streamlit as st

import accounts


def _status_tile(label: str, value_str: str, note: str, tier: str = "caution"):
    """Same vivid color-coded tile used on the main dashboard (see
    outlook.py / app.py's status-tile CSS) -- scaled down slightly so four
    fit comfortably in a row here."""
    tier = tier if tier in ("good", "caution", "hazard") else "caution"
    st.markdown(
        f"""
        <div class="status-tile tile-{tier}" style="min-height:104px; padding:14px 16px;">
            <div class="tile-label">{label}</div>
            <div class="tile-value" style="font-size:1.3rem;">{value_str}</div>
            <div class="tile-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_logged_out():
    st.markdown(
        """
        <div class="hero-banner">
            <h1>🧭 Welcome to Local Daily Companion</h1>
            <p>Real transit systems, real air-quality math, real U.S. cities — one friendly daily
            briefing. Sign up to save your city, ZIP, and routes, or jump right in as a guest.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="companion-banner">
        🚌 <b>Track real transit systems</b> across 18 U.S. cities, plan station-to-station trips,
        and check elevator/accessibility status &nbsp;·&nbsp;
        🌬️ <b>Check real air-quality math</b> (EPA's own AQI formula) and a plain-language Asthma
        Hazard Risk for any ZIP code in a supported metro area &nbsp;·&nbsp;
        📰 <b>One Daily Briefing</b> that combines both into a single friendly sentence, in your
        city's own local time.
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup, tab_guest = st.tabs(["🔑 Log In", "🆕 Sign Up", "👋 Continue as Guest"])

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
                help="Demo login only — please never reuse a real password here.",
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

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        level = transit_status.get("level")
        level_label = {"smooth": "Smooth", "minor": "Minor delays", "major": "Major delays"}.get(level, "Unknown")
        outages = transit_status.get("elevator_outages", 0)
        _status_tile("🚌 Transit", level_label, f"{outages} elevator outage(s) reported", tiers.get("transit"))
    with c2:
        aqi_val = aqi_reading.get("aqi")
        _status_tile(
            "🌬️ Air quality", f"{aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'}",
            aqi_reading.get("label", "No data"), tiers.get("aqi"),
        )
    with c3:
        pollen_val = pollen_reading.get("value")
        _status_tile(
            "🌼 Pollen", f"{pollen_reading.get('emoji', '❔')} {pollen_val if pollen_val is not None else '—'}",
            pollen_reading.get("category", "No data"), tiers.get("pollen"),
        )
    saved_routes = account.get("saved_routes", []) if account else []
    with c4:
        st.markdown(
            f"""
            <div class="metric-card" style="min-height:104px; padding:14px 16px; --accent:#4a3aa7;">
                <div class="mc-label">⭐ Saved routes</div>
                <div class="mc-value" style="font-size:1.3rem;">{len(saved_routes)}</div>
                <div class="mc-note">Quick trips saved from the trip planner</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        render_logged_out()
