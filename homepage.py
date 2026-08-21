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


def _quick_chip(label: str, value_str: str, note: str, accent: str):
    st.markdown(
        f"""
        <div class="metric-card" style="--accent:{accent}">
            <div class="mc-label">{label}</div>
            <div class="mc-value" style="font-size:1.35rem;">{value_str}</div>
            <div class="mc-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_account_and_go_home(username: str, city_key: str, zip_key: str, profile_key_prefix: str):
    accounts.apply_account_to_session(username, city_key, zip_key, profile_key_prefix)
    st.session_state["view"] = "home"


def render_logged_out(city_key: str, zip_key: str, profile_key_prefix: str):
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
                    _apply_account_and_go_home(u.strip(), city_key, zip_key, profile_key_prefix)
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
        st.caption(
            "Accounts here live only in this browser session's memory (no real database, no "
            "password hashing) — perfect for trying out the personalization features, not for a "
            "real password. See the README for how to wire up real persistent accounts."
        )

    with tab_guest:
        st.write("No account needed — just pick a city and ZIP in the sidebar and go.")
        if st.button("👉 Take me to the dashboard", use_container_width=True, type="primary"):
            st.session_state["view"] = "app"
            st.rerun()


def render_logged_in(username: str, city: str, neighborhood: str, zip_code: str, briefing_text: str,
                      transit_status: dict, aqi_reading: dict, city_now):
    account = accounts.get_account(username)
    try:
        tz_suffix = f" {city_now:%Z}".rstrip()
    except Exception:
        tz_suffix = ""

    st.markdown(
        f"""
        <div class="hero-banner">
            <h1>👋 Welcome back, {username}!</h1>
            <p>Here's what's happening right now in your saved city — {city} ({neighborhood},
            {zip_code}), {city_now:%I:%M %p}{tz_suffix}.</p>
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

    c1, c2, c3 = st.columns(3)
    with c1:
        level = transit_status.get("level")
        level_label = {"smooth": "✅ Smooth", "minor": "🟡 Minor delays", "major": "🔴 Major delays"}.get(level, "❔ Unknown")
        accent = {"smooth": "#0ca30c", "minor": "#c98500", "major": "#d03b3b"}.get(level, "#898781")
        outages = transit_status.get("elevator_outages", 0)
        _quick_chip("🚌 Transit right now", level_label, f"{outages} elevator outage(s) reported", accent)
    with c2:
        aqi_val = aqi_reading.get("aqi")
        _quick_chip(
            "🌬️ Air quality", f"{aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'}",
            aqi_reading.get("label", "No data"), aqi_reading.get("color", "#898781"),
        )
    with c3:
        saved_routes = account["saved_routes"] if account else []
        _quick_chip("⭐ Saved routes", str(len(saved_routes)),
                    "Quick trips saved from the trip planner", "#4a3aa7")

    if account and account["saved_routes"]:
        st.markdown("#### ⭐ Your saved routes")
        for r in account["saved_routes"]:
            st.caption(f"**{r['label']}** — {r['city']}")

    st.write("")
    if st.button("🧭 Open my full dashboard →", use_container_width=True, type="primary"):
        st.session_state["view"] = "app"
        st.rerun()

    st.divider()
    if st.button("Log out", key="home_logout"):
        accounts.log_out()
        st.rerun()


def render_homepage(city_key: str, zip_key: str, profile_key_prefix: str, city=None, neighborhood=None,
                     zip_code=None, briefing_text=None, transit_status=None, aqi_reading=None, city_now=None):
    """Entry point called from app.py. Branches on login state; the caller
    supplies the SAME transit_status/aqi_reading/briefing_text objects
    already computed once for the main dashboard, so the homepage and the
    dashboard can never show conflicting numbers."""
    if accounts.is_logged_in():
        render_logged_in(
            accounts.current_user(), city, neighborhood, zip_code, briefing_text,
            transit_status, aqi_reading, city_now,
        )
    else:
        render_logged_out(city_key, zip_key, profile_key_prefix)
