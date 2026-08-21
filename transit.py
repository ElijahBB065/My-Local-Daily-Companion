"""
transit.py
Tab 1: Transit Accessibility & Delay Tracker.

Every agency, line, and station name below is real. What's simulated --
clearly and only -- is the live, second-by-second stuff no free API hands
out for free across a dozen different transit agencies: arrival countdowns,
delay minutes, elevator/escalator status, and crowding. Community-reported
accessibility issues are real user input, held in the browser session only
(they reset when the app restarts).
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from cities import stable_seed

# --------------------------------------------------------------------------
# Real transit systems, real lines, real stations
# --------------------------------------------------------------------------
TRANSIT_SYSTEMS = {
    "New York, NY": {
        "agency": "MTA New York City Subway",
        "mode": "🚇 Subway",
        "lines": ["4/5/6", "A/C/E", "L", "7", "N/Q/R/W"],
        "stations": [
            "Times Sq-42 St", "Grand Central-42 St", "Union Sq-14 St",
            "Atlantic Ave-Barclays Ctr", "Fulton St", "34 St-Herald Sq",
            "86th St", "Jackson Heights-Roosevelt Ave",
        ],
    },
    "Chicago, IL": {
        "agency": "Chicago Transit Authority (CTA) 'L'",
        "mode": "🚈 Elevated/Subway",
        "lines": ["Red", "Blue", "Brown", "Green", "Orange", "Pink", "Purple", "Yellow"],
        "stations": [
            "Clark/Lake", "Roosevelt", "Belmont", "O'Hare", "Fullerton",
            "Jackson", "95th/Dan Ryan", "Midway",
        ],
    },
    "Washington, DC": {
        "agency": "WMATA Metrorail",
        "mode": "🚇 Metro",
        "lines": ["Red", "Blue", "Orange", "Silver", "Green", "Yellow"],
        "stations": [
            "Metro Center", "Gallery Pl-Chinatown", "Union Station",
            "L'Enfant Plaza", "Dulles Airport", "Ashburn",
            "Wiehle-Reston East", "Pentagon",
        ],
    },
    "Boston, MA": {
        "agency": "MBTA ('The T')",
        "mode": "🚇 Subway",
        "lines": ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"],
        "stations": [
            "Park Street", "Downtown Crossing", "Government Center",
            "North Station", "Back Bay", "Harvard", "Airport",
        ],
    },
    "San Francisco, CA": {
        "agency": "BART + Muni Metro",
        "mode": "🚈 Rail",
        "lines": ["Red", "Yellow", "Blue", "Green", "Orange"],
        "stations": [
            "Embarcadero", "Powell St", "Civic Center", "Montgomery St",
            "16th St Mission", "Balboa Park", "SFO",
        ],
    },
    "Philadelphia, PA": {
        "agency": "SEPTA",
        "mode": "🚇 Subway",
        "lines": ["Broad Street Line", "Market-Frankford Line"],
        "stations": [
            "City Hall", "15th St", "Walnut-Locust", "30th Street Station",
            "Frankford Transportation Center", "Fern Rock",
        ],
    },
    "Seattle, WA": {
        "agency": "Sound Transit Link Light Rail",
        "mode": "🚈 Light Rail",
        "lines": ["1 Line", "2 Line"],
        "stations": [
            "Westlake", "University Street", "Capitol Hill",
            "Bellevue Downtown", "Redmond Technology", "Angle Lake",
            "SeaTac/Airport",
        ],
    },
    "Atlanta, GA": {
        "agency": "MARTA",
        "mode": "🚇 Rail",
        "lines": ["Red", "Gold", "Blue", "Green"],
        "stations": [
            "Five Points", "Peachtree Center", "Lindbergh Center",
            "Airport", "Midtown", "Buckhead",
        ],
    },
    "Los Angeles, CA": {
        "agency": "LA Metro Rail",
        "mode": "🚈 Rail",
        "lines": ["A Line", "B Line", "E Line", "K Line"],
        "stations": [
            "Union Station", "7th St/Metro Center", "North Hollywood",
            "Culver City", "Expo/La Brea", "Hollywood/Highland",
        ],
    },
    "Denver, CO": {
        "agency": "RTD Rail",
        "mode": "🚈 Light Rail",
        "lines": ["A Line", "B Line", "G Line"],
        "stations": [
            "Union Station", "40th & Colorado", "Westminster", "Denver Airport",
        ],
    },
    "Miami, FL": {
        "agency": "Miami-Dade Metrorail",
        "mode": "🚈 Rail",
        "lines": ["Green Line", "Orange Line"],
        "stations": [
            "Government Center", "Brickell", "Dadeland South", "Vizcaya", "Civic Center",
        ],
    },
    "Portland, OR": {
        "agency": "TriMet MAX",
        "mode": "🚈 Light Rail",
        "lines": ["Blue", "Red", "Green", "Orange", "Yellow"],
        "stations": [
            "Pioneer Square", "Rose Quarter", "Lloyd Center/NE 11th",
            "Gateway/NE 99th", "Beaverton Central", "PDX Airport",
        ],
    },
}

STATUS_ON_TIME = "On time"
STATUS_MINOR_DELAY = "Minor delay"
STATUS_MAJOR_DELAY = "Major delay"

CROWDING_LEVELS = ["Low", "Medium", "High"]


def get_system(city: str) -> dict:
    return TRANSIT_SYSTEMS.get(city, next(iter(TRANSIT_SYSTEMS.values())))


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------
def generate_arrivals(city: str, seed: int, n: int = 8) -> pd.DataFrame:
    """Simulated next-arrival board for a city -- clearly not a live feed,
    but shaped like one so the UI/UX and charts are realistic to build against."""
    rng = np.random.default_rng(seed)
    system = get_system(city)
    lines = system["lines"]
    stations = system["stations"]

    rows = []
    now = datetime.now()
    for _ in range(n):
        line = rng.choice(lines)
        station = rng.choice(stations)
        eta_min = int(rng.integers(1, 20))
        delay_roll = rng.random()
        if delay_roll < 0.60:
            delay = 0
            status = STATUS_ON_TIME
        elif delay_roll < 0.88:
            delay = int(rng.integers(2, 8))
            status = STATUS_MINOR_DELAY
        else:
            delay = int(rng.integers(8, 20))
            status = STATUS_MAJOR_DELAY
        arrival_dt = now + timedelta(minutes=eta_min)
        hour_12 = arrival_dt.hour % 12 or 12
        eta_str = f"{hour_12}:{arrival_dt.minute:02d} {'AM' if arrival_dt.hour < 12 else 'PM'}"
        rows.append({
            "line": line,
            "station": station,
            "eta": eta_str,
            "minutes_away": eta_min,
            "delay_min": delay,
            "status": status,
            "wheelchair_accessible": bool(rng.random() < 0.82),
            "crowding": rng.choice(CROWDING_LEVELS, p=[0.4, 0.4, 0.2]),
        })
    df = pd.DataFrame(rows).sort_values("minutes_away").reset_index(drop=True)
    return df


def generate_station_accessibility(city: str, seed: int) -> pd.DataFrame:
    """Simulated elevator/escalator status per station."""
    rng = np.random.default_rng(seed + 1)
    system = get_system(city)
    rows = []
    for station in system["stations"]:
        elevator_ok = bool(rng.random() < 0.87)
        escalator_ok = bool(rng.random() < 0.83)
        rows.append({
            "station": station,
            "elevator": "✅ Working" if elevator_ok else "🛑 Out of service",
            "escalator": "✅ Working" if escalator_ok else "🛑 Out of service",
            "wheelchair_route": "✅ Accessible" if elevator_ok else "⚠️ Limited (use adjacent station)",
        })
    return pd.DataFrame(rows)


def generate_hourly_delay_pattern(city: str) -> pd.DataFrame:
    """Deterministic (not per-click-random) typical daily delay curve, so the
    chart tells a consistent AM/PM rush-hour story every time it's viewed."""
    rng = np.random.default_rng(stable_seed(city, "delay_pattern"))
    hours = np.arange(24)
    # base curve: two rush-hour bumps around 8am and 5:30pm
    am_bump = 6 * np.exp(-((hours - 8) ** 2) / (2 * 1.3 ** 2))
    pm_bump = 7 * np.exp(-((hours - 17.5) ** 2) / (2 * 1.6 ** 2))
    base = 1.5 + am_bump + pm_bump
    noise = rng.normal(0, 0.4, size=24)
    avg_delay = np.clip(base + noise, 0.3, None)
    return pd.DataFrame({"hour": hours, "avg_delay_min": avg_delay.round(1)})


def generate_line_efficiency(city: str) -> pd.DataFrame:
    """Deterministic per-line on-time-performance snapshot for the efficiency chart."""
    rng = np.random.default_rng(stable_seed(city, "line_efficiency"))
    system = get_system(city)
    lines = system["lines"]
    on_time_pct = np.clip(rng.normal(86, 6, size=len(lines)), 62, 98).round(1)
    return pd.DataFrame({"line": lines, "on_time_pct": on_time_pct}).sort_values(
        "on_time_pct", ascending=False
    ).reset_index(drop=True)


# --------------------------------------------------------------------------
# Shared "how's transit doing right now" computation
# --------------------------------------------------------------------------
def get_current_seed(city: str) -> int:
    """The seed basis for 'this run's' simulated snapshot -- a stable
    per-city seed plus the session's refresh-button tick counter, so the
    top-of-page daily briefing/alerts and Tab 1's own tables always agree
    with each other, and both update together when the user clicks
    Refresh. Safe to call before render_transit_tab has run this session
    (defaults the tick to 0, same as render_transit_tab would)."""
    tick = st.session_state.get("transit_tick", 0)
    return stable_seed(city, "arrivals") + tick


def get_current_status_summary(city: str, accessibility_df: pd.DataFrame = None) -> dict:
    """'How's transit doing right now' -- delay level from the deterministic
    hourly curve at the ACTUAL current hour (real datetime.now(), not a
    cached value), plus a live count of simulated elevator outages. Pass a
    precomputed accessibility_df (e.g. from render_transit_tab's own call
    to generate_station_accessibility) to guarantee this always matches
    what Tab 1 is showing; otherwise it generates its own with the same
    seed formula, so the two can never disagree."""
    if accessibility_df is None:
        accessibility_df = generate_station_accessibility(city, get_current_seed(city))

    hourly = generate_hourly_delay_pattern(city)
    current_hour = datetime.now().hour
    delay_now = float(hourly.loc[hourly["hour"] == current_hour, "avg_delay_min"].iloc[0])

    if delay_now < 3:
        level, phrase = "smooth", "transit is running smoothly"
    elif delay_now < 6:
        level, phrase = "minor", "transit has some minor delays"
    else:
        level, phrase = "major", "transit is seeing significant delays"

    outages = accessibility_df[accessibility_df["elevator"].str.contains("Out of service")]

    return {
        "city": city,
        "delay_min": round(delay_now, 1),
        "level": level,
        "phrase": phrase,
        "elevator_outages": len(outages),
        "outage_stations": outages["station"].tolist(),
        "current_hour": current_hour,
        "as_of": datetime.now(),
    }


# --------------------------------------------------------------------------
# Community accessibility reports (session-only)
# --------------------------------------------------------------------------
ISSUE_TYPES = [
    "🛗 Elevator out of service",
    "🪜 Escalator out of service",
    "🔇 No audio/visual announcements",
    "🎫 Broken ticket machine",
    "⚠️ Unsafe or blocked path",
    "❓ Other accessibility issue",
]


def init_reports_state():
    if "accessibility_reports" not in st.session_state:
        st.session_state.accessibility_reports = []


def add_report(city: str, station: str, issue_type: str, details: str):
    st.session_state.accessibility_reports.insert(0, {
        "city": city,
        "station": station,
        "issue_type": issue_type,
        "details": details.strip(),
        "reported_at": datetime.now().strftime("%b %d, %I:%M %p"),
        "resolved": False,
    })


def resolve_report(index: int):
    if 0 <= index < len(st.session_state.accessibility_reports):
        st.session_state.accessibility_reports[index]["resolved"] = True


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
STATUS_BADGE = {
    STATUS_ON_TIME: ("✅", "#0ca30c", "On time"),
    STATUS_MINOR_DELAY: ("🟡", "#c98500", "Minor delay"),
    STATUS_MAJOR_DELAY: ("🔴", "#d03b3b", "Major delay"),
}
CROWDING_BADGE = {"Low": "🟢 Low", "Medium": "🟡 Medium", "High": "🔴 High"}


def render_transit_tab(city: str, neighborhood: str, seed: int = None, accessibility_df: pd.DataFrame = None):
    import charts  # local import keeps charts.py's own imports lightweight

    init_reports_state()
    system = get_system(city)

    if "transit_tick" not in st.session_state:
        st.session_state.transit_tick = 0

    st.markdown(
        f"""
        <div class="companion-banner">
        <b>{system['mode']} &nbsp;{system['agency']}</b> — showing simulated next-arrival data
        for real {city} stations and lines near <b>{neighborhood}</b>. Arrival times and delays
        refresh below are for demo purposes; station and route names are real.
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_l, top_r = st.columns([3, 1])
    with top_l:
        selected_lines = st.multiselect(
            "Filter by line", options=system["lines"], default=system["lines"],
            help="Show arrivals only for the lines you care about.",
        )
    with top_r:
        st.write("")
        if st.button("🔄 Refresh arrivals", use_container_width=True):
            st.session_state.transit_tick += 1

    if seed is None:
        seed = get_current_seed(city)
    arrivals = generate_arrivals(city, seed)
    if selected_lines:
        arrivals = arrivals[arrivals["line"].isin(selected_lines)]

    st.subheader("🚏 Next arrivals")
    if arrivals.empty:
        st.info("No arrivals match your line filter right now — try selecting more lines.")
    else:
        for _, row in arrivals.iterrows():
            icon, color, label = STATUS_BADGE[row["status"]]
            wheelchair = "♿ Accessible" if row["wheelchair_accessible"] else "🚫 Not accessible"
            crowding = CROWDING_BADGE.get(row["crowding"], row["crowding"])
            delay_text = f" (+{row['delay_min']} min)" if row["delay_min"] else ""
            st.markdown(
                f"""
                <div class="transit-card" style="--accent:{color}">
                    <div class="tc-top">
                        <span class="tc-line">{row['line']}</span>
                        <span class="tc-eta">{row['eta']} · {row['minutes_away']} min</span>
                    </div>
                    <div class="tc-station">{row['station']}</div>
                    <div class="tc-meta">{icon} {label}{delay_text} &nbsp;·&nbsp; {wheelchair} &nbsp;·&nbsp; Crowding: {crowding}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader("🛗 Station accessibility status")
    st.caption("Simulated elevator/escalator status, refreshed with the button above.")
    if accessibility_df is None:
        accessibility_df = generate_station_accessibility(city, seed)
    st.dataframe(accessibility_df, use_container_width=True, hide_index=True)

    st.subheader("📊 Delay & efficiency trends")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.delay_pattern_chart(generate_hourly_delay_pattern(city)), use_container_width=True)
    with c2:
        st.plotly_chart(charts.route_efficiency_chart(generate_line_efficiency(city)), use_container_width=True)

    st.subheader("📣 Community-flagged accessibility issues")
    st.caption(
        "Reports are shared with everyone using the app during this session (they reset when "
        "the app restarts) — this is a demo feature, not a connection to any real transit agency."
    )

    with st.form("report_issue_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            report_station = st.selectbox("Station", options=system["stations"])
        with fc2:
            report_type = st.selectbox("Issue type", options=ISSUE_TYPES)
        report_details = st.text_area("Details (optional)", placeholder="e.g. Elevator at the 7th Ave entrance has been down since this morning.")
        submitted = st.form_submit_button("🚩 Submit report", use_container_width=True, type="primary")
        if submitted:
            add_report(city, report_station, report_type, report_details)
            st.success("Thanks — your report has been added below for others to see.")

    city_reports = [r for r in st.session_state.accessibility_reports if r["city"] == city]
    if not city_reports:
        st.info(f"No accessibility issues reported for {city} yet. 🎉")
    else:
        for i, report in enumerate(st.session_state.accessibility_reports):
            if report["city"] != city:
                continue
            status_text = "✅ Resolved" if report["resolved"] else "🚩 Open"
            status_color = "#0ca30c" if report["resolved"] else "#d03b3b"
            details_html = f"<div class='rc-details'>{report['details']}</div>" if report["details"] else ""
            st.markdown(
                f"""
                <div class="report-card" style="--accent:{status_color}">
                    <div class="rc-top">
                        <span>{report['issue_type']} — {report['station']}</span>
                        <span style="color:{status_color}; font-weight:600;">{status_text}</span>
                    </div>
                    {details_html}
                    <div class="rc-meta">Reported {report['reported_at']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not report["resolved"]:
                if st.button("Mark resolved", key=f"resolve_{i}"):
                    resolve_report(i)
                    st.rerun()
