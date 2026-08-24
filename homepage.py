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
import community


def _feature_card(icon: str, title: str, body: str):
    """One card in the logged-out landing page's 3-column feature grid --
    replaces the old single paragraph of stacked raw text with something
    that actually looks like a product's feature grid."""
    st.markdown(
        f"""
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _community_preview(city: str, neighborhood: str) -> dict:
    """A real crowd-reported post for the visitor's own town if one already
    exists (so a returning visitor sees genuine local activity), or an
    honestly-labeled example post otherwise -- never a real post dressed up
    as fake, and never a fake post dressed up as real. Defensive by design:
    community lookups can fail (bad city/neighborhood, community.py not
    fully initialized yet on a guest's very first run) without taking the
    whole Home page down with it.
    """
    top = []
    try:
        community_id = community.community_id_for(city, neighborhood)
        if community.get_community(community_id):
            top = community.top_issues(community_id, n=1)
    except Exception:
        top = []

    if top:
        post = top[0]
        upvotes = post.get("upvotes", set())
        count = len(upvotes) if isinstance(upvotes, (set, list, tuple)) else 0
        return {
            "badge": "LIVE POST",
            "category_label": community.CATEGORY_LABELS.get(post.get("category"), "💬 General Town Chat"),
            "text": post.get("text") or "",
            "count": count,
            "author": post.get("author") or "A neighbor",
        }
    return {
        "badge": "EXAMPLE",
        "category_label": "🛠️ Local Infrastructure Issues",
        "text": "Elevator at the Main St station has been out since Tuesday — anyone know if it's being fixed?",
        "count": 12,
        "author": "Guest-3f8a1",
    }


def _preview_stack(city: str, neighborhood: str, transit_status: dict, aqi_reading: dict, tiers: dict):
    """Three elevated 'here's what you get' cards shown to a logged-out
    visitor, right next to the login form -- an AQI reading, a transit
    delay pill, and a community post. The AQI and transit cards use the
    SAME already-computed reading app.py hands to the dashboard for
    whatever city is currently selected in the sidebar, so a guest sees
    genuinely live numbers, not a mocked-up placeholder, before ever
    creating an account.
    """
    transit_status = transit_status if isinstance(transit_status, dict) else {}
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    tiers = tiers if isinstance(tiers, dict) else {}
    city_label = (city or "your city").split(",")[0] if city else "your city"

    aqi_val = aqi_reading.get("aqi")
    aqi_color = aqi_reading.get("color") or "#0f766e"
    st.markdown(
        f"""
        <div class="preview-card">
            <div class="preview-eyebrow">
                <span>🌬️ Air Quality</span>
                <span><span class="preview-live-dot"></span>Live · {city_label}</span>
            </div>
            <div style="font-size:2.1rem; font-weight:800; color:{aqi_color}; line-height:1;">
                {aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'}
            </div>
            <div style="font-weight:700; color:#0f172a; margin-top:6px;">{aqi_reading.get('label', 'No data yet')}</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:2px;">{neighborhood or city_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    level = transit_status.get("level")
    level_label = {"smooth": "Smooth", "minor": "Minor delays", "major": "Major delays"}.get(level, "Checking…")
    tier = tiers.get("transit") if tiers.get("transit") in ("good", "caution", "hazard") else "caution"
    outages = transit_status.get("elevator_outages", 0) or 0
    delay_min = transit_status.get("delay_min")
    delay_note = f"{delay_min} min avg delay" if delay_min is not None else "Pick a city to see live delays"
    st.markdown(
        f"""
        <div class="preview-card">
            <div class="preview-eyebrow">
                <span>🚌 Transit</span>
                <span><span class="preview-live-dot"></span>Live · {city_label}</span>
            </div>
            <span class="delay-pill pill-{tier}">🚌 {level_label}</span>
            <div style="font-size:0.85rem; color:#64748b; margin-top:10px;">
                {delay_note} · {outages} elevator outage{'s' if outages != 1 else ''} reported
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    preview = _community_preview(city, neighborhood)
    st.markdown(
        f"""
        <div class="preview-card">
            <div class="preview-eyebrow">
                <span>🏘️ Community Hub</span>
                <span>{preview['badge']}</span>
            </div>
            <div style="font-weight:700; color:#0f172a; font-size:0.92rem;">{preview['category_label']}</div>
            <div style="font-size:0.92rem; color:#334155; margin-top:6px; line-height:1.45;">
                &ldquo;{preview['text']}&rdquo;
            </div>
            <div style="font-size:0.78rem; color:#94a3b8; margin-top:10px;">👍 {preview['count']} · {preview['author']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def render_logged_out(city: str = None, neighborhood: str = None, zip_code: str = None,
                       transit_status: dict = None, aqi_reading: dict = None, pollen_reading: dict = None,
                       outlook_data: dict = None, city_now=None):
    """The logged-out landing page: a bold gradient hero card, a two-column
    split (a styled 'get started' auth card next to a live feature-preview
    stack), then a three-column feature grid -- replacing the old single
    banner + wall of text with cards doing the visual work, per the Week 1
    visual overhaul. Every optional value is normalized defensively, same
    pattern as render_logged_in below, since a guest can land here before
    the rest of app.py's "compute once" section has anything meaningful to
    hand over (e.g. the very first run before a city is even resolved).
    """
    outlook_data = outlook_data if isinstance(outlook_data, dict) else {}
    tiers = outlook_data.get("tiers", {})
    city_label = (city or "your city").split(",")[0] if city else "your city"

    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="hero-eyebrow">🧭 Local Daily Companion</div>
            <h1>Your city, decoded every morning.</h1>
            <p>Real transit systems, real EPA air-quality math, real U.S. cities — one instant
            daily briefing for {city_label}. Sign up to save your spots and routes, or jump
            right in as a guest — every feature works either way.</p>
            <div class="hero-badges">
                <span class="hero-badge">🚌 18 real transit systems</span>
                <span class="hero-badge">🌬️ Live EPA air-quality math</span>
                <span class="hero-badge">🏘️ Local community boards</span>
                <span class="hero-badge">🔒 Secure, persistent accounts</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_auth, col_preview = st.columns([1, 1.05], gap="large")

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

    with col_preview:
        _preview_stack(city, neighborhood, transit_status, aqi_reading, tiers)

    st.write("")
    st.markdown("#### Everything in one place")
    feat_l, feat_m, feat_r = st.columns(3, gap="medium")
    with feat_l:
        _feature_card(
            "🚌", "Track real transit",
            "Next arrivals, delay patterns, and elevator/accessibility status across 18 real "
            "U.S. transit systems, plus a station-to-station trip planner.",
        )
    with feat_m:
        _feature_card(
            "🌬️", "Real air-quality math",
            "Live OpenAQ readings where available, EPA's own AQI formula otherwise, and a "
            "plain-language Asthma Hazard Risk for any ZIP code you type in.",
        )
    with feat_r:
        _feature_card(
            "📰", "One daily briefing",
            "Transit, air quality, and pollen rolled into a single friendly sentence and a "
            "color-coded outlook — always in your city's own local time.",
        )


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

    c1, c2, c3, c4 = st.columns(4, gap="small")
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
        render_logged_out(
            city, neighborhood, zip_code, transit_status, aqi_reading, pollen_reading,
            outlook_data, city_now,
        )
