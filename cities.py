"""
cities.py
Shared registry of real U.S. cities used across both tabs.

Every city here is real, with its real transit agency (see transit.py), real
coordinates, and its real IANA timezone. The one thing that is NOT claimed to
be live, second-by-second real is noted explicitly wherever it appears:
bus/train arrival times and delay minutes are simulated (transit.py), and air
quality falls back to a realistic simulation only when a live OpenAQ reading
can't be fetched (air_quality.py). Nothing here pretends invented numbers are
real.

Each city also lists a couple of real, well-known ZIP codes for different
parts of town, so picking a "neighborhood" in the sidebar means something
concrete instead of a made-up placeholder.

TIMEZONES: every city carries its real IANA timezone identifier (e.g.
"America/New_York"). now_in_city() is the one place the whole app should ever
ask "what time is it right now" -- it converts the server's clock into that
city's own local time using Python's stdlib zoneinfo, so the app always shows
YOUR selected city's real local time, not the server's (which, on most cloud
hosts, is UTC and has nothing to do with any real place).
"""

import hashlib
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover -- stdlib since Python 3.9; requirements.txt pins 3.9+
    ZoneInfo = None


def stable_seed(*parts) -> int:
    """A reproducible seed derived from the given parts.

    Python's built-in hash() is randomized per-process (PYTHONHASHSEED) for
    security reasons, so `hash("Chicago, IL")` gives a DIFFERENT number every
    time the app restarts -- which would make "today's typical delay curve"
    or "today's typical AQI shape" for a given city silently reshuffle on
    every restart instead of staying stable. hashlib is not salted, so this
    gives the same seed every time for the same inputs.
    """
    key = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % (2**32)


CITIES = {
    "New York, NY": {
        "state": "NY",
        "lat": 40.7128,
        "lon": -74.0060,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "10001", "neighborhood": "Chelsea / Midtown"},
            {"zip": "11201", "neighborhood": "Brooklyn Heights"},
            {"zip": "10451", "neighborhood": "South Bronx"},
        ],
    },
    "Chicago, IL": {
        "state": "IL",
        "lat": 41.8781,
        "lon": -87.6298,
        "timezone": "America/Chicago",
        "zips": [
            {"zip": "60601", "neighborhood": "The Loop"},
            {"zip": "60614", "neighborhood": "Lincoln Park"},
            {"zip": "60649", "neighborhood": "South Shore"},
        ],
    },
    "Washington, DC": {
        "state": "DC",
        "lat": 38.9072,
        "lon": -77.0369,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "20001", "neighborhood": "Shaw / Mount Vernon Triangle"},
            {"zip": "20009", "neighborhood": "Adams Morgan"},
            {"zip": "20020", "neighborhood": "Anacostia"},
        ],
    },
    "Boston, MA": {
        "state": "MA",
        "lat": 42.3601,
        "lon": -71.0589,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "02108", "neighborhood": "Beacon Hill"},
            {"zip": "02118", "neighborhood": "South End"},
            {"zip": "02125", "neighborhood": "Dorchester"},
        ],
    },
    "San Francisco, CA": {
        "state": "CA",
        "lat": 37.7749,
        "lon": -122.4194,
        "timezone": "America/Los_Angeles",
        "zips": [
            {"zip": "94102", "neighborhood": "Civic Center / Tenderloin"},
            {"zip": "94110", "neighborhood": "Mission District"},
            {"zip": "94122", "neighborhood": "Sunset District"},
        ],
    },
    "Philadelphia, PA": {
        "state": "PA",
        "lat": 39.9526,
        "lon": -75.1652,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "19102", "neighborhood": "Center City"},
            {"zip": "19104", "neighborhood": "University City"},
            {"zip": "19140", "neighborhood": "North Philadelphia"},
        ],
    },
    "Seattle, WA": {
        "state": "WA",
        "lat": 47.6062,
        "lon": -122.3321,
        "timezone": "America/Los_Angeles",
        "zips": [
            {"zip": "98101", "neighborhood": "Downtown"},
            {"zip": "98105", "neighborhood": "University District"},
            {"zip": "98118", "neighborhood": "Columbia City"},
        ],
    },
    "Atlanta, GA": {
        "state": "GA",
        "lat": 33.7490,
        "lon": -84.3880,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "30303", "neighborhood": "Downtown"},
            {"zip": "30306", "neighborhood": "Virginia-Highland"},
            {"zip": "30314", "neighborhood": "Vine City / Westside"},
        ],
    },
    "Los Angeles, CA": {
        "state": "CA",
        "lat": 34.0522,
        "lon": -118.2437,
        "timezone": "America/Los_Angeles",
        "zips": [
            {"zip": "90012", "neighborhood": "Downtown / Civic Center"},
            {"zip": "90028", "neighborhood": "Hollywood"},
            {"zip": "90802", "neighborhood": "Long Beach"},
        ],
    },
    "Denver, CO": {
        "state": "CO",
        "lat": 39.7392,
        "lon": -104.9903,
        "timezone": "America/Denver",
        "zips": [
            {"zip": "80202", "neighborhood": "LoDo / Union Station"},
            {"zip": "80205", "neighborhood": "Five Points"},
            {"zip": "80219", "neighborhood": "Westwood"},
        ],
    },
    "Miami, FL": {
        "state": "FL",
        "lat": 25.7617,
        "lon": -80.1918,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "33131", "neighborhood": "Brickell"},
            {"zip": "33125", "neighborhood": "Little Havana"},
            {"zip": "33150", "neighborhood": "Liberty City"},
        ],
    },
    "Portland, OR": {
        "state": "OR",
        "lat": 45.5152,
        "lon": -122.6784,
        "timezone": "America/Los_Angeles",
        "zips": [
            {"zip": "97201", "neighborhood": "Downtown"},
            {"zip": "97213", "neighborhood": "Hollywood District"},
            {"zip": "97227", "neighborhood": "Eliot / North Portland"},
        ],
    },
    "Minneapolis, MN": {
        "state": "MN",
        "lat": 44.9778,
        "lon": -93.2650,
        "timezone": "America/Chicago",
        "zips": [
            {"zip": "55401", "neighborhood": "North Loop / Downtown"},
            {"zip": "55414", "neighborhood": "Prospect Park / U of M"},
            {"zip": "55407", "neighborhood": "Powderhorn"},
        ],
    },
    "Dallas, TX": {
        "state": "TX",
        "lat": 32.7767,
        "lon": -96.7970,
        "timezone": "America/Chicago",
        "zips": [
            {"zip": "75201", "neighborhood": "Downtown"},
            {"zip": "75204", "neighborhood": "Uptown"},
            {"zip": "75217", "neighborhood": "Pleasant Grove"},
        ],
    },
    "Baltimore, MD": {
        "state": "MD",
        "lat": 39.2904,
        "lon": -76.6122,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "21201", "neighborhood": "Downtown / Mount Vernon"},
            {"zip": "21211", "neighborhood": "Hampden"},
            {"zip": "21217", "neighborhood": "Upton / Reservoir Hill"},
        ],
    },
    "San Diego, CA": {
        "state": "CA",
        "lat": 32.7157,
        "lon": -117.1611,
        "timezone": "America/Los_Angeles",
        "zips": [
            {"zip": "92101", "neighborhood": "Downtown / Gaslamp Quarter"},
            {"zip": "92103", "neighborhood": "Hillcrest"},
            {"zip": "92113", "neighborhood": "Southeastern San Diego"},
        ],
    },
    "Charlotte, NC": {
        "state": "NC",
        "lat": 35.2271,
        "lon": -80.8431,
        "timezone": "America/New_York",
        "zips": [
            {"zip": "28202", "neighborhood": "Uptown"},
            {"zip": "28203", "neighborhood": "South End / Dilworth"},
            {"zip": "28206", "neighborhood": "NoDa"},
        ],
    },
    "Houston, TX": {
        "state": "TX",
        "lat": 29.7604,
        "lon": -95.3698,
        "timezone": "America/Chicago",
        "zips": [
            {"zip": "77002", "neighborhood": "Downtown"},
            {"zip": "77030", "neighborhood": "Texas Medical Center"},
            {"zip": "77009", "neighborhood": "Near Northside"},
        ],
    },
}

CITY_NAMES = list(CITIES.keys())


def get_city(city_name: str) -> dict:
    return CITIES.get(city_name, CITIES[CITY_NAMES[0]])


def now_in_city(city_name: str) -> datetime:
    """THE single source of truth for 'what time is it right now' anywhere
    in this app. Converts the real current instant into the selected city's
    own real local timezone using the stdlib zoneinfo database -- so a user
    in Los Angeles checking on New York sees New York's actual local time,
    and the app never shows raw server time (typically UTC on cloud hosts,
    which matches no user's or city's clock). Falls back to naive
    datetime.now() only if zoneinfo/tzdata is somehow unavailable, so a
    timezone-database hiccup never crashes the app -- it just quietly loses
    the timezone conversion for that one render.
    """
    tz_name = get_city(city_name).get("timezone")
    if tz_name and ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now()


# --------------------------------------------------------------------------
# ZIP code lookup -- lets a user type ANY real 5-digit ZIP for the selected
# metro area, not just the handful of "featured" ones listed per city above.
# --------------------------------------------------------------------------
def is_valid_zip(zip_code) -> bool:
    """True only for a plain 5-digit ZIP string. Deliberately type-strict --
    this is the single choke point that keeps a non-string/non-ZIP value
    (an int index, None, an empty string, etc.) from ever propagating into
    a comparison or a lookup elsewhere in the app."""
    return isinstance(zip_code, str) and zip_code.isdigit() and len(zip_code) == 5


def lookup_neighborhood(city_name: str, zip_code: str) -> dict:
    """Resolve a ZIP to a neighborhood name for the given city.

    This app ships a small, curated list of real, well-known ZIPs per city
    (see CITIES[...]["zips"]) with real neighborhood names. Typing in any
    OTHER real 5-digit ZIP for that city's metro area is fully supported --
    transit.py and air_quality.py both key their simulations off the exact
    ZIP string you enter (see stable_seed usage) -- but this demo doesn't
    ship a full ZIP-to-neighborhood geocoding database, so an unfeatured
    ZIP gets an honest generic label rather than an invented neighborhood
    name. Returns {"neighborhood": str, "known": bool}.
    """
    city_info = get_city(city_name)
    if is_valid_zip(zip_code):
        for z in city_info["zips"]:
            if z["zip"] == zip_code:
                return {"neighborhood": z["neighborhood"], "known": True}
        return {"neighborhood": f"ZIP {zip_code} area", "known": False}
    return {"neighborhood": "Unknown area", "known": False}
