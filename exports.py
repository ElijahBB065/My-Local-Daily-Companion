"""
exports.py
Two ways to walk away with today's outlook instead of just reading it on
screen: a downloadable calendar event (.ics) you can drop straight into
Google Calendar / Apple Calendar / Outlook, and a plain-text daily summary
formatted to paste into a text message or note.

Neither of these talks to a real calendar or messaging API -- that would
need OAuth against Google/Outlook/etc, well outside what a session-only
demo app can honestly promise. Both are built from the SAME
already-computed values as the rest of the page (the outlook verdict, the
daily briefing sentence, the transit/AQI/pollen readings), so what's in the
file or the copy block always matches what's on screen -- nothing here is
a placeholder.

Pure logic, no Streamlit dependency, so both functions are easy to
unit-test on their own (same pattern as briefing.py / outlook.py).
"""

import uuid
from datetime import datetime, timedelta, timezone


def _ics_timestamp(dt: datetime) -> str:
    """Format a datetime as a UTC-based iCalendar timestamp (...Z). A
    tz-aware datetime converts cleanly; a naive one is treated as already
    being UTC rather than guessing -- there's no reliable way to know what
    timezone a naive datetime meant, and guessing wrong silently shifts
    someone's actual commute reminder by hours."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def build_commute_ics(city: str, event_title: str, description: str, start_local: datetime,
                       duration_minutes: int = 30, alarm_minutes_before: int = 15) -> str:
    """A valid RFC 5545 .ics file: one VEVENT, repeating daily, with a
    reminder alarm. `start_local` should be a tz-aware datetime (e.g. from
    cities.now_in_city(city), rolled forward to the desired reminder time)
    so the event lands on the right real-world hour regardless of what
    timezone the ZIP/city happens to be in.
    """
    now_utc = datetime.now(timezone.utc)
    start_utc = start_local
    end_utc = start_local + timedelta(minutes=duration_minutes)

    uid = f"{uuid.uuid4()}@local-daily-companion"
    # \n, commas, and semicolons all need escaping inside a DESCRIPTION value.
    safe_description = (
        description.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )
    safe_title = event_title.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Local Daily Companion//Daily Commute Briefing//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_ics_timestamp(now_utc)}",
        f"DTSTART:{_ics_timestamp(start_utc)}",
        f"DTEND:{_ics_timestamp(end_utc)}",
        f"SUMMARY:{safe_title}",
        f"DESCRIPTION:{safe_description}",
        "RRULE:FREQ=DAILY",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Time to check your daily briefing",
        f"TRIGGER:-PT{alarm_minutes_before}M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    # RFC 5545 lines are terminated with CRLF -- several calendar apps
    # (Outlook especially) are strict about this.
    return "\r\n".join(lines) + "\r\n"


def build_shareable_summary(city: str, zip_code: str, outlook: dict, briefing_text: str,
                             transit_status: dict, aqi_reading: dict, pollen_reading: dict,
                             now: datetime = None) -> str:
    """A short, plain-text block meant for st.code()'s built-in copy icon --
    paste-ready for a text message, note, or email, no markdown or HTML in
    it. Pulled from the exact same computed values as the on-screen banner
    and tiles, so what gets shared always matches what's on screen."""
    now = now or datetime.now()
    try:
        date_str = now.strftime("%A, %B %d — %I:%M %p")
    except Exception:
        date_str = ""

    transit_status = transit_status or {}
    aqi_reading = aqi_reading or {}
    pollen_reading = pollen_reading or {}

    delay = transit_status.get("delay_min")
    delay_str = f"{delay} min avg delay" if delay is not None else "delay data unavailable"
    outages = transit_status.get("elevator_outages", 0) or 0

    aqi_val = aqi_reading.get("aqi")
    aqi_str = f"AQI {aqi_val}" if aqi_val is not None else "AQI unavailable"

    pollen_val = pollen_reading.get("value")
    pollen_str = f"{pollen_val}/12" if pollen_val is not None else "unavailable"

    lines = [
        f"{city} ({zip_code}) — {date_str}",
        f"{outlook.get('headline', '')}",
        "",
        f"Transit: {transit_status.get('level', 'unknown').title()} — {delay_str}, "
        f"{outages} elevator outage{'s' if outages != 1 else ''}",
        f"Air quality: {aqi_reading.get('label', 'No data')} ({aqi_str})",
        f"Pollen: {pollen_reading.get('category', 'No data')} ({pollen_str}) — "
        f"{pollen_reading.get('dominant_allergen', '')}".rstrip(" —"),
        "",
        briefing_text or "",
        "",
        "Sent from Local Daily Companion",
    ]
    return "\n".join(lines)
