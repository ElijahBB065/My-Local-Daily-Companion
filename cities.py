"""
cities.py
Shared registry of real U.S. cities used across both tabs.

Every city here is real, with its real transit agency (see transit.py) and
real coordinates. The one thing that is NOT claimed to be live, second-by-
second real is noted explicitly wherever it appears: bus/train arrival
times and delay minutes are simulated (transit.py), and air quality falls
back to a realistic simulation only when a live OpenAQ reading can't be
fetched (air_quality.py). Nothing here pretends invented numbers are real.

Each city also lists a couple of real, well-known ZIP codes for different
parts of town, so picking a "neighborhood" in the sidebar means something
concrete instead of a made-up placeholder.
"""

import hashlib


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
        "zips": [
            {"zip": "97201", "neighborhood": "Downtown"},
            {"zip": "97213", "neighborhood": "Hollywood District"},
            {"zip": "97227", "neighborhood": "Eliot / North Portland"},
        ],
    },
}

CITY_NAMES = list(CITIES.keys())


def get_city(city_name: str) -> dict:
    return CITIES.get(city_name, CITIES[CITY_NAMES[0]])
