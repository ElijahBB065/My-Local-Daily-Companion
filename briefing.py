"""
briefing.py
Builds the one-sentence "Daily Briefing" shown at the very top of the app,
combining right-now transit status and right-now air quality into a single
friendly sentence. Pure logic, no Streamlit dependency, so it's easy to
unit-test on its own.

The greeting and every status word are derived from whatever transit_status
/ aqi_reading the caller passes in -- which app.py always computes fresh
from datetime.now() on every run (see transit.get_current_status_summary
and air_quality.get_current_reading). Nothing here is cached or frozen to
a fixed date; reload the app at any moment and the sentence reflects that
moment's real hour and real simulated/live conditions.
"""

from datetime import datetime

TRANSIT_CLAUSES = {
    "smooth": "transit is running smoothly",
    "minor": "transit has some minor delays",
    "major": "transit is seeing significant delays",
}

AQI_CLAUSES = {
    "Good": "air quality is great today",
    "Moderate": "air quality is okay today, though it's worth keeping an eye on if you're sensitive to it",
    "Unhealthy for Sensitive Groups": "air quality is a bit elevated today, so consider limiting long outdoor activity",
    "Unhealthy": "air quality is unhealthy today, so it's best to keep outdoor time short",
    "Very Unhealthy": "air quality is very unhealthy today, so try to stay indoors when you can",
    "Hazardous": "air quality is hazardous today, so staying indoors is your best bet",
    "No data": "air quality data isn't available right now",
}

GOOD_AQI_LABELS = {"Good"}


def time_greeting(now: datetime = None) -> str:
    """A greeting based on the ACTUAL current hour -- pass `now` only for
    testing; in the app this always defaults to datetime.now()."""
    now = now or datetime.now()
    hour = now.hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def build_daily_briefing(transit_status: dict, aqi_reading: dict, profile: dict = None, now: datetime = None) -> str:
    """One friendly sentence combining transit + air quality, e.g.:
    'Good morning! Transit is running smoothly, but limit long outdoor
    runs today due to elevated AQI.'
    """
    profile = profile or {}
    greeting = time_greeting(now)

    transit_ok = transit_status.get("level") == "smooth"
    aqi_label = aqi_reading.get("label", "No data")
    aqi_ok = aqi_label in GOOD_AQI_LABELS

    transit_clause = TRANSIT_CLAUSES.get(transit_status.get("level"), "transit status is unavailable right now")
    aqi_clause = AQI_CLAUSES.get(aqi_label, "air quality data isn't available right now")

    if profile.get("asthma") and aqi_label not in GOOD_AQI_LABELS and aqi_label != "No data":
        aqi_clause += " — especially with your asthma profile"

    connector = "and" if (transit_ok and aqi_ok) else "but"
    # Capitalize only the first clause -- it opens the sentence.
    transit_clause = transit_clause[0].upper() + transit_clause[1:]

    return f"{greeting}! {transit_clause}, {connector} {aqi_clause}."
