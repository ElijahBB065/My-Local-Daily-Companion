"""
transit.py
Tab 1: Transit Accessibility & Delay Tracker.

Every agency, line, and station name below is real. What's simulated --
clearly and only -- is the live, second-by-second stuff no free API hands
out for free across nearly twenty different transit agencies: arrival
countdowns, delay minutes, elevator/escalator status, and crowding.
Community-reported accessibility issues are real user input, held in the
browser session only (they reset when the app restarts).

ROUTING: `line_sequences` gives each line's real stations in real
geographic order -- enough to compute a station-to-station route (direct,
or with one transfer) the way a rider actually would. This is a
deliberately SIMPLIFIED SUBSET of each system's real map (a handful of
lines and their major/transfer stations), not the full official system --
see get_route()'s docstring and the in-app disclaimer. Every station and
line name used is still real.

TIMEZONE: every function that needs "right now" takes an explicit `now`
parameter (a timezone-aware datetime in the selected city's own local
time, from cities.now_in_city()). Callers that don't pass one get a plain
datetime.now() so this module still works standalone, but app.py always
supplies the real city-local time.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from cities import stable_seed

# --------------------------------------------------------------------------
# Real transit systems, real lines, real stations
#
# `stations` = the full set shown on the accessibility board / report form.
# `line_sequences` = a curated, real subset of lines with their stations in
# real geographic order, used for station-to-station routing.
# --------------------------------------------------------------------------
TRANSIT_SYSTEMS = {
    "New York, NY": {
        "agency": "MTA New York City Subway",
        "mode": "🚇 Subway",
        "lines": ["4/5/6", "A/C/E", "L", "7", "N/Q/R/W"],
        "stations": [
            "Times Sq-42 St", "Grand Central-42 St", "Union Sq-14 St",
            "Atlantic Ave-Barclays Ctr", "Fulton St", "34 St-Herald Sq",
            "86th St", "Jackson Heights-Roosevelt Ave", "Bedford Ave",
        ],
        "line_sequences": {
            "4/5/6": ["86th St", "Grand Central-42 St", "Union Sq-14 St", "Fulton St", "Atlantic Ave-Barclays Ctr"],
            "A/C/E": ["Jackson Heights-Roosevelt Ave", "Times Sq-42 St", "Fulton St"],
            "L": ["Union Sq-14 St", "Bedford Ave"],
            "7": ["Times Sq-42 St", "Grand Central-42 St", "Jackson Heights-Roosevelt Ave"],
            "N/Q/R/W": ["34 St-Herald Sq", "Union Sq-14 St", "Atlantic Ave-Barclays Ctr"],
        },
    },
    "Chicago, IL": {
        "agency": "Chicago Transit Authority (CTA) 'L'",
        "mode": "🚈 Elevated/Subway",
        "lines": ["Red", "Blue", "Brown", "Green", "Orange", "Pink"],
        "stations": [
            "Howard", "Clark/Lake", "Roosevelt", "Belmont", "O'Hare", "Fullerton",
            "Jackson", "95th/Dan Ryan", "Midway",
        ],
        "line_sequences": {
            "Red": ["Howard", "Belmont", "Fullerton", "Jackson", "Roosevelt", "95th/Dan Ryan"],
            "Blue": ["O'Hare", "Clark/Lake", "Jackson"],
            "Brown": ["Belmont", "Fullerton", "Clark/Lake"],
            "Green": ["Clark/Lake", "Roosevelt"],
            "Orange": ["Midway", "Clark/Lake", "Roosevelt"],
            "Pink": ["Clark/Lake"],
        },
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
        "line_sequences": {
            "Red": ["Union Station", "Gallery Pl-Chinatown", "Metro Center"],
            "Blue": ["Pentagon", "L'Enfant Plaza", "Metro Center"],
            "Orange": ["Metro Center", "L'Enfant Plaza"],
            "Silver": ["Ashburn", "Dulles Airport", "Wiehle-Reston East", "Metro Center", "L'Enfant Plaza"],
            "Green": ["Gallery Pl-Chinatown", "L'Enfant Plaza"],
            "Yellow": ["Gallery Pl-Chinatown", "L'Enfant Plaza", "Pentagon"],
        },
    },
    "Boston, MA": {
        "agency": "MBTA ('The T')",
        "mode": "🚇 Subway",
        "lines": ["Red", "Orange", "Blue", "Green-B", "Green-C", "Green-D", "Green-E"],
        "stations": [
            "Park Street", "Downtown Crossing", "Government Center",
            "North Station", "Back Bay", "Harvard", "Airport",
        ],
        "line_sequences": {
            "Red": ["Harvard", "Park Street", "Downtown Crossing"],
            "Orange": ["North Station", "Downtown Crossing", "Back Bay"],
            "Blue": ["Government Center", "Airport"],
            "Green-B": ["North Station", "Government Center", "Park Street"],
            "Green-C": ["North Station", "Government Center", "Park Street"],
            "Green-D": ["North Station", "Government Center", "Park Street"],
            "Green-E": ["North Station", "Government Center", "Park Street"],
        },
    },
    "San Francisco, CA": {
        "agency": "BART + Muni Metro",
        "mode": "🚈 Rail",
        "lines": ["Red", "Yellow", "Blue", "Green", "Orange"],
        "stations": [
            "Embarcadero", "Powell St", "Civic Center", "Montgomery St",
            "16th St Mission", "Balboa Park", "SFO",
        ],
        "line_sequences": {
            "Red": ["Civic Center", "Powell St", "Montgomery St", "Embarcadero", "SFO"],
            "Yellow": ["Embarcadero", "Montgomery St", "Powell St", "Civic Center", "16th St Mission", "Balboa Park", "SFO"],
            "Blue": ["Embarcadero", "Montgomery St", "Powell St", "Civic Center", "16th St Mission", "Balboa Park"],
            "Green": ["Embarcadero", "Montgomery St", "Powell St", "Civic Center", "16th St Mission", "Balboa Park"],
            "Orange": ["Embarcadero", "Montgomery St", "Powell St", "Civic Center", "16th St Mission", "Balboa Park"],
        },
    },
    "Philadelphia, PA": {
        "agency": "SEPTA",
        "mode": "🚇 Subway",
        "lines": ["Broad Street Line", "Market-Frankford Line"],
        "stations": [
            "City Hall", "15th St", "Walnut-Locust", "30th Street Station",
            "Frankford Transportation Center", "Fern Rock",
        ],
        "line_sequences": {
            "Broad Street Line": ["Fern Rock", "City Hall", "Walnut-Locust"],
            "Market-Frankford Line": ["30th Street Station", "City Hall", "Frankford Transportation Center"],
        },
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
        "line_sequences": {
            "1 Line": ["Angle Lake", "SeaTac/Airport", "Westlake", "University Street", "Capitol Hill"],
            "2 Line": ["Bellevue Downtown", "Redmond Technology"],
        },
    },
    "Atlanta, GA": {
        "agency": "MARTA",
        "mode": "🚇 Rail",
        "lines": ["Red", "Gold", "Blue", "Green"],
        "stations": [
            "Five Points", "Peachtree Center", "Lindbergh Center",
            "Airport", "Midtown", "Buckhead",
        ],
        "line_sequences": {
            "Red": ["Airport", "Five Points", "Peachtree Center", "Midtown", "Lindbergh Center", "Buckhead"],
            "Gold": ["Airport", "Five Points", "Peachtree Center", "Midtown", "Lindbergh Center"],
            "Blue": ["Five Points"],
            "Green": ["Five Points"],
        },
    },
    "Los Angeles, CA": {
        "agency": "LA Metro Rail",
        "mode": "🚈 Rail",
        "lines": ["A Line", "B Line", "E Line", "K Line"],
        "stations": [
            "Union Station", "7th St/Metro Center", "North Hollywood",
            "Culver City", "Expo/La Brea", "Hollywood/Highland", "Expo/Crenshaw",
        ],
        "line_sequences": {
            "A Line": ["Union Station", "7th St/Metro Center"],
            "B Line": ["Union Station", "7th St/Metro Center", "Hollywood/Highland", "North Hollywood"],
            "E Line": ["7th St/Metro Center", "Expo/Crenshaw", "Expo/La Brea", "Culver City"],
            "K Line": ["Expo/Crenshaw"],
        },
    },
    "Denver, CO": {
        "agency": "RTD Rail",
        "mode": "🚈 Light Rail",
        "lines": ["A Line", "B Line", "G Line"],
        "stations": [
            "Union Station", "40th & Colorado", "Westminster", "Denver Airport",
        ],
        "line_sequences": {
            "A Line": ["Union Station", "40th & Colorado", "Denver Airport"],
            "B Line": ["Union Station", "Westminster"],
            "G Line": ["Union Station"],
        },
    },
    "Miami, FL": {
        "agency": "Miami-Dade Metrorail",
        "mode": "🚈 Rail",
        "lines": ["Green Line", "Orange Line"],
        "stations": [
            "Government Center", "Brickell", "Dadeland South", "Vizcaya", "Civic Center",
        ],
        "line_sequences": {
            "Green Line": ["Dadeland South", "Vizcaya", "Brickell", "Government Center", "Civic Center"],
            "Orange Line": ["Dadeland South", "Vizcaya", "Brickell", "Government Center", "Civic Center"],
        },
    },
    "Portland, OR": {
        "agency": "TriMet MAX",
        "mode": "🚈 Light Rail",
        "lines": ["Blue", "Red", "Green", "Orange", "Yellow"],
        "stations": [
            "Pioneer Square", "Rose Quarter", "Lloyd Center/NE 11th",
            "Gateway/NE 99th", "Beaverton Central", "PDX Airport",
        ],
        "line_sequences": {
            "Blue": ["Beaverton Central", "Pioneer Square", "Rose Quarter", "Lloyd Center/NE 11th", "Gateway/NE 99th"],
            "Red": ["PDX Airport", "Gateway/NE 99th", "Lloyd Center/NE 11th", "Rose Quarter", "Pioneer Square"],
            "Green": ["Pioneer Square", "Rose Quarter", "Lloyd Center/NE 11th", "Gateway/NE 99th"],
            "Orange": ["Pioneer Square"],
            "Yellow": ["Pioneer Square", "Rose Quarter"],
        },
    },
    "Minneapolis, MN": {
        "agency": "Metro Transit (METRO)",
        "mode": "🚈 Light Rail",
        "lines": ["Blue Line", "Green Line"],
        "stations": [
            "Target Field", "Nicollet Mall", "MSP Airport Terminal 1", "Mall of America",
            "Stadium Village", "Union Depot",
        ],
        "line_sequences": {
            "Blue Line": ["Target Field", "Nicollet Mall", "MSP Airport Terminal 1", "Mall of America"],
            "Green Line": ["Target Field", "Nicollet Mall", "Stadium Village", "Union Depot"],
        },
    },
    "Dallas, TX": {
        "agency": "DART Rail",
        "mode": "🚈 Light Rail",
        "lines": ["Red Line", "Blue Line", "Green Line", "Orange Line"],
        "stations": [
            "Union Station", "West End", "Akard", "Pearl/Arts District",
            "Cityplace/Uptown", "Mockingbird Station",
        ],
        "line_sequences": {
            "Red Line": ["Union Station", "West End", "Akard", "Pearl/Arts District", "Cityplace/Uptown", "Mockingbird Station"],
            "Blue Line": ["Union Station", "West End", "Akard", "Pearl/Arts District", "Cityplace/Uptown", "Mockingbird Station"],
            "Green Line": ["West End", "Akard", "Pearl/Arts District"],
            "Orange Line": ["West End", "Akard", "Pearl/Arts District"],
        },
    },
    "Baltimore, MD": {
        "agency": "Baltimore Metro SubwayLink + Light RailLink",
        "mode": "🚇 Metro / Light Rail",
        "lines": ["Metro SubwayLink", "Light RailLink"],
        "stations": [
            "Owings Mills", "Lexington Market", "Charles Center", "Johns Hopkins Hospital",
            "Hunt Valley", "Penn Station", "Camden Yards", "BWI Airport",
        ],
        "line_sequences": {
            "Metro SubwayLink": ["Owings Mills", "Lexington Market", "Charles Center", "Johns Hopkins Hospital"],
            "Light RailLink": ["Hunt Valley", "Penn Station", "Lexington Market", "Camden Yards", "BWI Airport"],
        },
    },
    "San Diego, CA": {
        "agency": "MTS Trolley",
        "mode": "🚈 Light Rail",
        "lines": ["Blue Line", "Orange Line", "Green Line"],
        "stations": [
            "Old Town Transit Center", "Santa Fe Depot", "America Plaza",
            "Gaslamp Quarter", "12th & Imperial Transit Center", "San Diego State University",
        ],
        "line_sequences": {
            "Blue Line": ["Old Town Transit Center", "Santa Fe Depot", "America Plaza", "Gaslamp Quarter", "12th & Imperial Transit Center"],
            "Orange Line": ["America Plaza", "Santa Fe Depot", "Gaslamp Quarter", "12th & Imperial Transit Center"],
            "Green Line": ["Old Town Transit Center", "12th & Imperial Transit Center", "San Diego State University"],
        },
    },
    "Charlotte, NC": {
        "agency": "CATS LYNX Blue Line",
        "mode": "🚈 Light Rail",
        "lines": ["Blue Line"],
        "stations": [
            "I-485/South", "Scaleybark", "Charlotte Transportation Center", "7th Street", "Parkwood",
        ],
        "line_sequences": {
            "Blue Line": ["I-485/South", "Scaleybark", "Charlotte Transportation Center", "7th Street", "Parkwood"],
        },
    },
    "Houston, TX": {
        "agency": "METRORail",
        "mode": "🚈 Light Rail",
        "lines": ["Red Line", "Green Line", "Purple Line"],
        "stations": [
            "Main Street Square", "Museum District", "Texas Medical Center Transit Center",
            "NRG Park", "Theater District", "Convention District",
        ],
        "line_sequences": {
            "Red Line": ["Main Street Square", "Museum District", "Texas Medical Center Transit Center", "NRG Park"],
            "Green Line": ["Main Street Square", "Theater District", "Convention District"],
            "Purple Line": ["Main Street Square", "Theater District", "Convention District"],
        },
    },
}

STATUS_ON_TIME = "On time"
STATUS_MINOR_DELAY = "Minor delay"
STATUS_MAJOR_DELAY = "Major delay"

CROWDING_LEVELS = ["Low", "Medium", "High"]

AVG_MINUTES_PER_STOP = 2.4
TRANSFER_PENALTY_MIN = 6.0


def get_system(city: str) -> dict:
    return TRANSIT_SYSTEMS.get(city, next(iter(TRANSIT_SYSTEMS.values())))


def get_routable_stations(city: str) -> list:
    """All stations that appear in this city's line_sequences (i.e. the
    ones the routing feature can actually plan a trip between) -- a subset
    of the full station list shown on the accessibility board."""
    system = get_system(city)
    seen = []
    for seq in system.get("line_sequences", {}).values():
        for st_name in seq:
            if st_name not in seen:
                seen.append(st_name)
    return seen or system["stations"]


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------
def generate_arrivals(city: str, seed: int, n: int = 8, now: datetime = None) -> pd.DataFrame:
    """Simulated next-arrival board for a city -- clearly not a live feed,
    but shaped like one so the UI/UX and charts are realistic to build
    against. `now` should be the city's own local time (cities.now_in_city)
    so arrival clock times shown match the city you're looking at, not the
    server's."""
    rng = np.random.default_rng(seed)
    system = get_system(city)
    lines = system["lines"]
    stations = system["stations"]
    now = now or datetime.now()

    rows = []
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
# Station-to-station routing
# --------------------------------------------------------------------------
def _station_index_map(line_sequences: dict) -> dict:
    return {line: {name: i for i, name in enumerate(seq)} for line, seq in line_sequences.items()}


def get_route(city: str, origin: str, destination: str, seed: int, now: datetime = None) -> dict:
    """Plan a trip between two real stations using this city's curated,
    simplified line map (see TRANSIT_SYSTEMS[...]["line_sequences"]).

    This is deliberately a SIMPLIFIED SUBSET of each system's real lines
    and stations for demo purposes -- not the complete official transit
    map -- so not every real station pair will resolve to a route here.
    When that happens, the result says so plainly (`found: False`) instead
    of guessing at a route that isn't backed by real, curated data.

    Routing logic:
      1. Same station -> trivial "you're already there" result.
      2. A line that serves both stations -> direct route; travel time is
         the number of stops apart, times an average minutes-per-stop.
      3. Otherwise, look for a single transfer: a station shared between
         one of the origin's lines and one of the destination's lines,
         picking whichever transfer minimizes total stops. A flat transfer
         penalty (walking/waiting to change lines) is added.
      4. If no direct or single-transfer path exists in this simplified
         network, report that plainly.

    A route-specific delay is layered on top of the deterministic hourly
    delay curve (evaluated at the given local hour) plus a small amount of
    per-route randomness, seeded deterministically so refreshing without
    clicking "Refresh arrivals" doesn't reshuffle it.
    """
    system = get_system(city)
    line_sequences = system.get("line_sequences", {})
    now = now or datetime.now()

    if origin == destination:
        return {
            "found": True, "direct": True, "origin": origin, "destination": destination,
            "lines_used": [], "transfer_station": None, "stops": 0,
            "travel_minutes": 0.0, "delay_minutes": 0.0, "total_minutes": 0.0,
            "note": "You're already there! 🎉",
        }

    idx = _station_index_map(line_sequences)
    origin_lines = [ln for ln, stations in idx.items() if origin in stations]
    dest_lines = [ln for ln, stations in idx.items() if destination in stations]

    rng = np.random.default_rng((stable_seed(city, origin, destination, "route") + (seed % 100_000)) % (2**32))

    def _delay_for(lines_used):
        hourly = generate_hourly_delay_pattern(city)
        hour = now.hour
        base = float(hourly.loc[hourly["hour"] == hour, "avg_delay_min"].iloc[0])
        jitter = float(rng.normal(0, 1.0))
        return round(max(0.0, base + jitter), 1)

    # 1) Direct: a line that covers both stations
    shared = [ln for ln in origin_lines if ln in dest_lines]
    if shared:
        best_line, best_stops = None, None
        for ln in shared:
            stops = abs(idx[ln][destination] - idx[ln][origin])
            if best_stops is None or stops < best_stops:
                best_line, best_stops = ln, stops
        travel = best_stops * AVG_MINUTES_PER_STOP
        delay = _delay_for([best_line])
        return {
            "found": True, "direct": True, "origin": origin, "destination": destination,
            "lines_used": [best_line], "transfer_station": None, "stops": best_stops,
            "travel_minutes": round(travel, 1), "delay_minutes": delay,
            "total_minutes": round(travel + delay, 1),
            "note": f"Direct on the {best_line} — no transfer needed.",
        }

    # 2) One transfer: a station shared between an origin-line and a dest-line
    best = None  # (origin_line, dest_line, transfer_station, stops)
    for lo in origin_lines:
        for ld in dest_lines:
            if lo == ld:
                continue
            common = set(idx[lo]) & set(idx[ld])
            for transfer in common:
                stops = abs(idx[lo][transfer] - idx[lo][origin]) + abs(idx[ld][destination] - idx[ld][transfer])
                if best is None or stops < best[3]:
                    best = (lo, ld, transfer, stops)

    if best:
        lo, ld, transfer, stops = best
        travel = stops * AVG_MINUTES_PER_STOP + TRANSFER_PENALTY_MIN
        delay = _delay_for([lo, ld])
        return {
            "found": True, "direct": False, "origin": origin, "destination": destination,
            "lines_used": [lo, ld], "transfer_station": transfer, "stops": stops,
            "travel_minutes": round(travel, 1), "delay_minutes": delay,
            "total_minutes": round(travel + delay, 1),
            "note": f"Take the {lo} to {transfer}, then transfer to the {ld}.",
        }

    return {
        "found": False, "direct": False, "origin": origin, "destination": destination,
        "lines_used": [], "transfer_station": None, "stops": None,
        "travel_minutes": None, "delay_minutes": None, "total_minutes": None,
        "note": (
            "This demo's simplified, curated line map doesn't connect these two stations "
            "directly or with a single transfer. In the real system there's almost certainly "
            "a route -- it's just outside this app's simplified subset of lines/stations."
        ),
    }


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


def get_current_status_summary(city: str, accessibility_df: pd.DataFrame = None, now: datetime = None) -> dict:
    """'How's transit doing right now' -- delay level from the deterministic
    hourly curve at the ACTUAL current hour IN THIS CITY'S OWN LOCAL TIME
    (pass `now` from cities.now_in_city(city); a bare datetime.now() would
    be server time, e.g. UTC, which has nothing to do with any real city's
    rush hour), plus a live count of simulated elevator outages. Pass a
    precomputed accessibility_df (e.g. from render_transit_tab's own call
    to generate_station_accessibility) to guarantee this always matches
    what Tab 1 is showing; otherwise it generates its own with the same
    seed formula, so the two can never disagree."""
    now = now or datetime.now()
    if accessibility_df is None:
        accessibility_df = generate_station_accessibility(city, get_current_seed(city))

    hourly = generate_hourly_delay_pattern(city)
    current_hour = now.hour
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
        "as_of": now,
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


def add_report(city: str, station: str, issue_type: str, details: str, now: datetime = None):
    now = now or datetime.now()
    st.session_state.accessibility_reports.insert(0, {
        "city": city,
        "station": station,
        "issue_type": issue_type,
        "details": details.strip(),
        "reported_at": now.strftime("%b %d, %I:%M %p"),
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


def _accessibility_lookup(accessibility_df: pd.DataFrame, station: str) -> dict:
    match = accessibility_df[accessibility_df["station"] == station]
    if match.empty:
        return {"elevator": "❔ No data", "escalator": "❔ No data", "wheelchair_route": "❔ No data"}
    row = match.iloc[0]
    return {"elevator": row["elevator"], "escalator": row["escalator"], "wheelchair_route": row["wheelchair_route"]}


def render_transit_tab(city: str, neighborhood: str, seed: int = None, accessibility_df: pd.DataFrame = None,
                        now: datetime = None):
    import charts  # local import keeps charts.py's own imports lightweight

    init_reports_state()
    system = get_system(city)
    now = now or datetime.now()

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
    arrivals = generate_arrivals(city, seed, now=now)
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

    if accessibility_df is None:
        accessibility_df = generate_station_accessibility(city, seed)

    # ----------------------------------------------------------------
    # Trip planner: origin -> destination routing
    # ----------------------------------------------------------------
    st.subheader("🗺️ Plan a trip: station-to-station route")
    st.caption(
        "Pick a real origin and destination station to see an estimated travel time, any active "
        "delay along the way, and accessibility status at both ends. This uses a **simplified "
        "subset** of each system's real lines/stations for the demo — not every real station "
        "pair is covered yet (see the note below if yours isn't)."
    )
    routable_stations = get_routable_stations(city)
    if len(routable_stations) < 2:
        st.info("Not enough curated stations for this city yet to plan a route.")
    else:
        rc1, rc2 = st.columns(2)
        with rc1:
            origin_station = st.selectbox("🚏 Origin station", options=routable_stations, key=f"route_origin_{city}")
        with rc2:
            default_dest_idx = 1 if len(routable_stations) > 1 else 0
            destination_station = st.selectbox(
                "🏁 Destination station", options=routable_stations,
                index=default_dest_idx, key=f"route_dest_{city}",
            )

        route = get_route(city, origin_station, destination_station, seed, now=now)

        if not route["found"]:
            st.warning(route["note"])
        else:
            lines_str = " → ".join(route["lines_used"]) if route["lines_used"] else "—"
            delay = route["delay_minutes"] or 0
            if delay >= 6:
                accent, delay_badge = "#d03b3b", f"🔴 +{delay} min active delay"
            elif delay >= 3:
                accent, delay_badge = "#c98500", f"🟡 +{delay} min minor delay"
            else:
                accent, delay_badge = "#0ca30c", "✅ No significant delay"

            transfer_text = f" via {route['transfer_station']}" if route["transfer_station"] else ""
            st.markdown(
                f"""
                <div class="transit-card" style="--accent:{accent}">
                    <div class="tc-top">
                        <span class="tc-line">{origin_station} → {destination_station}</span>
                        <span class="tc-eta">~{route['total_minutes']} min</span>
                    </div>
                    <div class="tc-station">{route['note']}</div>
                    <div class="tc-meta">
                        {"Direct" if route["direct"] else "1 transfer" + transfer_text} on {lines_str}
                        &nbsp;·&nbsp; {route['stops']} stop(s) &nbsp;·&nbsp; {delay_badge}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            acc_o = _accessibility_lookup(accessibility_df, origin_station)
            acc_d = _accessibility_lookup(accessibility_df, destination_station)
            ac1, ac2 = st.columns(2)
            with ac1:
                st.markdown(
                    f"""
                    <div class="metric-card" style="--accent:#2a78d6">
                        <div class="mc-label">🚏 {origin_station}</div>
                        <div class="mc-value" style="font-size:1.05rem;">{acc_o['elevator']}</div>
                        <div class="mc-note">Escalator: {acc_o['escalator']} &nbsp;·&nbsp; {acc_o['wheelchair_route']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with ac2:
                st.markdown(
                    f"""
                    <div class="metric-card" style="--accent:#4a3aa7">
                        <div class="mc-label">🏁 {destination_station}</div>
                        <div class="mc-value" style="font-size:1.05rem;">{acc_d['elevator']}</div>
                        <div class="mc-note">Escalator: {acc_d['escalator']} &nbsp;·&nbsp; {acc_d['wheelchair_route']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.subheader("🛗 Station accessibility status")
    st.caption("Simulated elevator/escalator status, refreshed with the button above.")
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
            add_report(city, report_station, report_type, report_details, now=now)
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
