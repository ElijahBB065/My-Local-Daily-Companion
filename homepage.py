"""
homepage.py
The Home view -- the default screen when the app launches.

PIVOT (Biomedical Health & Respiratory Dashboard): this app no longer
tracks transit at all. Every card on this page is now about one thing --
today's respiratory / bio-hazard picture for the selected city -- built
from app.py's Personalized Respiratory Health & Bio-Hazard engine (PM2.5,
PM10, and live pollen where Open-Meteo has coverage, folded into a
3-tier LOW / MODERATE / HIGH RISK score that also accounts for the
user's own sensitivity profile).

Logged OUT: a short hero pitch, a "Get started" card with Log In / Sign
Up / Guest tabs, a compact snapshot of today's Overall Respiratory
Hazard Score, and the Dominant Airborne Triggers breakdown -- an account
is never required, every feature works fine without logging in.

Logged IN: a personalized "Welcome Back" dashboard built from the user's
OWN saved home city and ZIP, with the same two respiratory cards,
computed the same way as the main dashboard (see app.py's "compute
once" section), so nothing here can ever disagree with the full
dashboard.
"""

import streamlit as st

import accounts


def render_status_tile(label: str, value: str, note: str, tier: str = "caution", compact: bool = False):
    """A calm, scannable status tile -- a bold number plus a small
    color-coded badge pill. Generic (not tied to any one data source), so
    it's reused wherever this app needs a quick "here's one number and how
    worried to be about it" readout -- today that's the Air Quality tile."""
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


# --------------------------------------------------------------------------
# Overall Respiratory Hazard Score -- the single "look here first" verdict
# for the whole app, computed once in app.py (see compute_respiratory_hazard)
# and rendered here as a large color badge with actionable health advice.
# --------------------------------------------------------------------------
_HAZARD_TIER_STYLE = {
    "low": {"gradient": "linear-gradient(120deg, #065f46 0%, #10b981 100%)", "text": "#ffffff",
            "badge": "good", "emoji": "🟢", "label": "LOW RISK"},
    "moderate": {"gradient": "linear-gradient(120deg, #92400e 0%, #f59e0b 100%)", "text": "#ffffff",
                 "badge": "caution", "emoji": "🟡", "label": "MODERATE RISK"},
    "high": {"gradient": "linear-gradient(120deg, #7f1d1d 0%, #ef4444 100%)", "text": "#ffffff",
             "badge": "hazard", "emoji": "🔴", "label": "HIGH RISK"},
}


def render_hazard_score_card(hazard: dict, city: str = None, compact: bool = False):
    """Card #1 -- Overall Respiratory Hazard Score: a large color badge
    (LOW / MODERATE / HIGH RISK) plus one sentence of actionable health
    advice tailored to the user's sensitivity profile. `hazard` is the
    dict built by app.py's compute_respiratory_hazard() --
    {"tier": "low"|"moderate"|"high", "advice": str, "sensitivity": str,
    "source_note": str}. Defensive: any missing/malformed field degrades
    to a safe "moderate/unknown" placeholder rather than crashing.
    """
    hazard = hazard if isinstance(hazard, dict) else {}
    tier = hazard.get("tier") if hazard.get("tier") in _HAZARD_TIER_STYLE else "moderate"
    style = _HAZARD_TIER_STYLE[tier]
    advice = hazard.get("advice") or "Check back later for today's respiratory outlook."
    sensitivity = hazard.get("sensitivity") or "Not Sensitive"
    city_bit = f" · {city}" if city else ""

    if compact:
        st.markdown(
            f"""
            <div class="outlook-banner" style="background:{style['gradient']}; color:{style['text']}; padding:18px 20px;">
                <div class="outlook-eyebrow">Respiratory Hazard Score{city_bit}</div>
                <h1 style="font-size:1.4rem;">{style['emoji']} {style['label']}</h1>
                <p class="outlook-sub" style="font-weight:500;">{advice}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="outlook-banner" style="background:{style['gradient']}; color:{style['text']}">
            <div class="outlook-eyebrow">Overall Respiratory Hazard Score{city_bit} · Profile: {sensitivity}</div>
            <h1>{style['emoji']} {style['label']}</h1>
            <p class="outlook-sub">{advice}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Dominant Airborne Triggers -- clean visual columns breaking down PM2.5,
# PM10, and live pollen (ragweed / grass / birch / olive, the four species
# the user asked to see) via Open-Meteo. Honest about coverage: Open-Meteo's
# pollen model is European (CAMS) and typically has no data for U.S. cities
# -- when that's the case, each pollen column says so plainly instead of
# inventing a number.
# --------------------------------------------------------------------------
_NAMED_POLLEN_SPECIES = [("ragweed_pollen", "Ragweed"), ("grass_pollen", "Grass"),
                          ("birch_pollen", "Birch"), ("olive_pollen", "Olive")]


def _pm_badge_tier(value, thresholds):
    if value is None:
        return "caution", "No data"
    for cutoff, tier, tag in thresholds:
        if value <= cutoff:
            return tier, tag
    return thresholds[-1][1], thresholds[-1][2]


_PM25_BADGES = [(9.0, "good", "Good"), (35.4, "caution", "Moderate"), (55.4, "caution", "Elevated"), (150.4, "hazard", "High")]
_PM10_BADGES = [(54.0, "good", "Good"), (154.0, "caution", "Moderate"), (254.0, "caution", "Elevated"), (354.0, "hazard", "High")]


def render_airborne_triggers_card(aqi_reading: dict = None, pollen_reading: dict = None, pollen_detail: dict = None):
    """Card #2 -- Dominant Airborne Triggers: clean visual columns for
    PM2.5, PM10, and the four named pollen species, each with its own
    color-coded badge. `pollen_detail` is the optional raw
    {"Ragweed": value, "Grass": value, ...} dict (µg/m³-ish concentration
    from Open-Meteo) app.py fetches alongside the main pollen_reading --
    when it's None or a species has no live reading, that column says so
    honestly rather than guessing a number.
    """
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    pollen_reading = pollen_reading if isinstance(pollen_reading, dict) else {}
    pollen_detail = pollen_detail if isinstance(pollen_detail, dict) else {}

    try:
        box = st.container(border=True)
    except TypeError:
        box = st.container()

    with box:
        st.markdown("##### 🫁 Dominant Airborne Triggers")
        pm25, pm10 = aqi_reading.get("pm25"), aqi_reading.get("pm10")
        pm25_tier, pm25_tag = _pm_badge_tier(pm25, _PM25_BADGES)
        pm10_tier, pm10_tag = _pm_badge_tier(pm10, _PM10_BADGES)

        col_pm25, col_pm10 = st.columns(2)
        with col_pm25:
            st.markdown('<div class="stat-label">PM2.5 · Fine particulates</div>', unsafe_allow_html=True)
            value_str = f"{pm25:.1f} µg/m³" if isinstance(pm25, (int, float)) else "No data"
            st.markdown(f'<div class="stat-value">{value_str}</div>', unsafe_allow_html=True)
            st.markdown(f'<span class="tile-badge tile-badge-{pm25_tier}">{pm25_tag}</span>', unsafe_allow_html=True)
        with col_pm10:
            st.markdown('<div class="stat-label">PM10 · Coarse particulates</div>', unsafe_allow_html=True)
            value_str = f"{pm10:.1f} µg/m³" if isinstance(pm10, (int, float)) else "No data"
            st.markdown(f'<div class="stat-value">{value_str}</div>', unsafe_allow_html=True)
            st.markdown(f'<span class="tile-badge tile-badge-{pm10_tier}">{pm10_tag}</span>', unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Pollen — Ragweed · Grass · Birch · Olive</div>', unsafe_allow_html=True)

        if pollen_detail:
            p_cols = st.columns(4)
            for (field, label), p_col in zip(_NAMED_POLLEN_SPECIES, p_cols):
                val = pollen_detail.get(label)
                with p_col:
                    st.markdown(f"**{label}**")
                    if val is None:
                        st.caption("No live reading")
                    else:
                        st.markdown(f'<div class="stat-value">{val:.1f} grains/m³</div>', unsafe_allow_html=True)
            st.caption(
                "Live pollen counts come from Open-Meteo's CAMS model, which mainly covers Europe -- "
                "a 'No live reading' column above is expected for most U.S. locations, not an error."
            )
        else:
            dominant = pollen_reading.get("dominant_allergen") or "particulate matter"
            st.caption(
                f"Live ragweed/grass/birch/olive pollen counts aren't available for this location right now "
                f"(Open-Meteo's pollen model mainly covers Europe). The hazard score below instead uses "
                f"PM2.5/PM10 and today's dominant airborne factor: **{dominant}**."
            )


def render_logged_out(city: str = None, neighborhood: str = None, zip_code: str = None,
                       hazard: dict = None, aqi_reading: dict = None, pollen_reading: dict = None,
                       pollen_detail: dict = None, city_now=None, **_extra_kwargs):
    """The logged-out landing page: a short hero, a two-column split (a
    'get started' auth card next to a compact Respiratory Hazard Score
    snapshot), and the full Dominant Airborne Triggers card. Every
    optional value is normalized defensively since a guest can land here
    before the rest of app.py's "compute once" section has anything
    meaningful to hand over (e.g. the very first run before a city is even
    resolved).
    """
    hazard = hazard if isinstance(hazard, dict) else {}
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    city_label = (city or "your city").split(",")[0] if city else "your city"

    st.markdown(
        f"""
        <div class="hero-banner">
            <h1>Your air. Your lungs. Decoded daily.</h1>
            <p>A personalized Respiratory Health & Bio-Hazard outlook for {city_label} -- live PM2.5, PM10,
            and pollen data folded into one clear LOW / MODERATE / HIGH risk score for your own sensitivity
            profile. Sign up to save your spots, or jump right in as a guest.</p>
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
        render_hazard_score_card(hazard, city=None, compact=True)

    render_airborne_triggers_card(aqi_reading, pollen_reading, pollen_detail)


def render_logged_in(username: str, city: str = None, neighborhood: str = None, zip_code: str = None,
                      briefing_text: str = None, hazard: dict = None, aqi_reading: dict = None,
                      pollen_reading: dict = None, pollen_detail: dict = None, city_now=None,
                      symptom_log_count: int = 0, **_extra_kwargs):
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
    briefing_text = briefing_text or "Your daily respiratory briefing will appear here once your city and ZIP are set."
    hazard = hazard if isinstance(hazard, dict) else {}
    aqi_reading = aqi_reading if isinstance(aqi_reading, dict) else {}
    pollen_reading = pollen_reading if isinstance(pollen_reading, dict) else {}
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

    st.markdown(
        f"""
        <div class="hero-banner">
            <h1>👋 Welcome back, {username}!</h1>
            <p>Here's your respiratory outlook for your saved city — {city}{location_detail},
            {time_str}{tz_suffix}.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="briefing-card">
            <div class="briefing-label">📰 Your Daily Respiratory Briefing</div>
            <div class="briefing-text">{briefing_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_hazard_score_card(hazard, city=city)

    c1, c2 = st.columns(2, gap="small")
    with c1:
        aqi_val = aqi_reading.get("aqi")
        aqi_tiers = {"low": "good", "moderate": "caution", "high": "hazard"}
        render_status_tile(
            "🌬️ Air quality", f"{aqi_reading.get('emoji', '❔')} {aqi_val if aqi_val is not None else '—'}",
            aqi_reading.get("label", "No data"), aqi_tiers.get(hazard.get("tier"), "caution"), compact=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card" style="min-height:104px; padding:14px 16px; --accent:#0f766e;">
                <div class="mc-label">📝 Symptom log entries</div>
                <div class="mc-value" style="font-size:1.3rem;">{symptom_log_count}</div>
                <div class="mc-note">Logged this session — manage in the sidebar</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    render_airborne_triggers_card(aqi_reading, pollen_reading, pollen_detail)

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
                     hazard=None, aqi_reading=None, pollen_reading=None, pollen_detail=None,
                     city_now=None, symptom_log_count=0, **_extra_kwargs):
    """Entry point called from app.py. Branches on login state; the caller
    supplies the SAME hazard/aqi_reading/pollen_reading/pollen_detail
    objects already computed once for the main dashboard, so the homepage
    and the dashboard can never show conflicting numbers.

    Note: this function no longer needs city_key/zip_key/profile_key_prefix
    -- applying a just-logged-in account's saved defaults onto those
    widget keys is queued (accounts.queue_apply_on_next_run) and processed
    at the very top of app.py's NEXT run instead of during this render;
    see that function's docstring for why.

    `**_extra_kwargs` (here and on render_logged_in/render_logged_out
    above) is a deliberate safety net, NOT dead code: it means a NEWER
    app.py that starts passing one more keyword argument than THIS
    homepage.py currently knows about degrades to "that one extra value is
    quietly ignored" instead of "TypeError: got an unexpected keyword
    argument, whole Home page crashes." app.py's own call site has the
    matching half of this fix -- it introspects this function's actual
    signature before calling, so the reverse mismatch (a NEWER app.py
    next to an OLDER homepage.py missing a newer parameter entirely) also
    degrades gracefully instead of crashing. See the README's "Keep all
    files in sync" note -- updating both files together is still the
    right long-term fix, this is a safety net, not a substitute for it.
    """
    if accounts.is_logged_in():
        render_logged_in(
            accounts.current_user(), city, neighborhood, zip_code, briefing_text,
            hazard, aqi_reading, pollen_reading, pollen_detail, city_now, symptom_log_count,
        )
    else:
        render_logged_out(
            city, neighborhood, zip_code, hazard, aqi_reading, pollen_reading, pollen_detail, city_now,
        )
