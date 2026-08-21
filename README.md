# 🧭 Local Daily Companion

A bright, friendly Streamlit app with two tabs for everyday city life, plus
personal features layered on top:

1. **🚌 Transit Accessibility & Delay Tracker** — next-arrival boards, a
   station-to-station **trip planner** (pick an origin and destination and
   get an estimated travel time, active delay, and accessibility status for
   both stations), delay patterns, elevator/escalator status, and
   community-flagged accessibility issues for **18 real U.S. cities** and
   their real transit systems.
2. **🌬️ Air Quality & Asthma Hazard Alerts** — current AQI, PM2.5, PM10, and
   Ozone levels with a plain-language Asthma Hazard Risk indicator and
   actionable recommendations, using live OpenAQ data when a key is
   configured and a realistic simulation otherwise.
3. **📌 Saved Locations** — save the current city/ZIP under a label like
   "Home," "Work," or "School" in the sidebar, then jump back to it with
   one click.
4. **🩺 Personal Sensitivity Profile** — toggle on Asthma / Sensitive
   Respiratory and/or Wheelchair / Stroller Access Required, and the app
   shows custom warning (or reassurance) badges right on the main
   dashboard whenever today's AQI or elevator status actually affects you.
5. **📰 Daily Briefing** — one friendly sentence at the very top of the app,
   combining right-now transit and air-quality status, e.g. *"Good
   morning! Transit is running smoothly, but limit long outdoor runs
   today due to elevated AQI."*

Every city switch instantly updates the local time shown, the transit
board, and the air-quality reading — there's nothing to refresh separately.

## Does this use TODAY's real date/time — in the right city's timezone?

Yes, and this is the one area that got a real fix worth calling out. Earlier
versions used the *server's* clock (`datetime.now()`), which on a cloud host
is normally UTC — technically "real," but not New York's or Seattle's actual
local time. Now, every time-sensitive value in the app is computed from
`cities.now_in_city(selected_city)`, which converts the real current instant
into that **specific city's own local time** using Python's standard-library
`zoneinfo` module and each city's real IANA timezone (e.g.
`America/New_York`, `America/Los_Angeles`, `America/Denver`,
`America/Chicago`). Switch the sidebar from New York to Los Angeles and every
clock on the page jumps by the real 3-hour offset — it isn't cosmetic.

That includes:

- The sidebar's own "🕒 Local time in `<city>`" readout, shown in that
  city's real local time with its timezone abbreviation (e.g. "3:45 PM
  EDT").
- The Daily Briefing's greeting ("Good morning" / "Good afternoon" / "Good
  evening") and its "As of [date/time]" line.
- Which hour of the simulated 24-hour AQI/delay curve counts as "right
  now" (marked on both trend charts) — this is computed from the **city's**
  local hour, not the server's.
- Transit arrival countdowns ("4 min away · 9:47 PM") and the trip
  planner's route delay estimate.
- Every report and saved-location timestamp.

As a secondary, informational signal, the sidebar also reads your
**browser's** reported timezone (via Streamlit's `st.context.timezone`,
where available) and shows a one-line note if it differs from the selected
city's timezone — e.g. if you're in Denver but checking on New York's
transit. Streamlit's browser-timezone API can be unreliable across some app
reloads, so the app never depends on it for anything functional; the
city's own IANA timezone (via `zoneinfo`) is always the authoritative source
for every clock, chart, and timestamp in the app.

The one thing that's intentionally **stable**, not live-random, is the
*shape* of a simulated day for a given city — e.g. "the Red Line's delays
peak around 5:30pm local time" looks the same today as it did an hour ago,
so the charts don't reshuffle confusingly on every page reload. What always
tracks the real clock is which point *within* that shape is "now," plus
every literal date/time shown anywhere in the UI. (Live OpenAQ readings,
when a key is configured, are of course genuinely live — a fresh
HTTP request on every rerun, not simulated at all.)

A Streamlit app only recomputes when you interact with it or reload the
page — there's no background auto-refresh — so "right now" means "as of
your last page load/interaction," which the "As of ..." timestamp in the
Daily Briefing always makes explicit.

## 🗺️ Station-to-station trip planner

Tab 1 now includes a "Plan a trip" section: pick a real **origin** and
**destination** station from dropdowns, and the app computes:

- Whether the trip is **direct** (one line covers both stations) or needs
  **one transfer** (a shared station between an origin-line and a
  destination-line), estimating stops and travel time for either case.
- An **active delay estimate** for that specific route, layered on top of
  the same deterministic hourly delay curve used elsewhere in the tab, so
  it's internally consistent rather than independently random.
- **Accessibility status** (elevator/escalator/wheelchair route) at *both*
  the origin and destination stations side by side.

This runs on a **curated, simplified subset** of each city's real lines and
stations (`transit.py`'s `line_sequences`) — enough real transfer points to
demonstrate meaningful routing (e.g. NYC's Times Sq-42 St, Union Sq-14 St,
and Atlantic Ave-Barclays Ctr; DC's Metro Center and L'Enfant Plaza;
Chicago's Clark/Lake), but **not the complete official system map**. If you
pick a real station pair this demo's simplified network doesn't happen to
connect (directly or with one transfer), the app says so plainly rather than
guessing — that's expected and by design, not a bug.

## What's real, and what's simulated (read this first)

Every **city, transit agency, rail line, and station name** in this app is
real — MTA subway lines in New York, CTA 'L' lines in Chicago, WMATA
Metrorail in DC, and so on for all 18 cities (see the full list below).
Every city's **timezone** is also its real IANA timezone.

<details>
<summary><strong>Full list of the 18 cities and their real transit agencies</strong></summary>

| City | Agency |
|---|---|
| New York, NY | MTA New York City Subway |
| Chicago, IL | Chicago Transit Authority (CTA) 'L' |
| Washington, DC | WMATA Metrorail |
| Boston, MA | MBTA ("The T") |
| San Francisco, CA | BART + Muni Metro |
| Philadelphia, PA | SEPTA |
| Seattle, WA | Sound Transit Link Light Rail |
| Atlanta, GA | MARTA |
| Los Angeles, CA | LA Metro Rail |
| Denver, CO | RTD Rail |
| Miami, FL | Miami-Dade Metrorail |
| Portland, OR | TriMet MAX |
| Minneapolis, MN | Metro Transit (METRO) |
| Dallas, TX | DART Rail |
| Baltimore, MD | Baltimore Metro SubwayLink + Light RailLink |
| San Diego, CA | MTS Trolley |
| Charlotte, NC | CATS LYNX Blue Line |
| Houston, TX | METRORail |

</details>

What's **simulated**, and clearly labeled as such in the UI:

- **Transit arrival times, delay minutes, elevator/escalator status, and
  crowding.** No single free API provides live real-time data across
  eighteen different U.S. transit agencies, so Tab 1 generates realistic,
  clearly-labeled demo data shaped like a real arrivals board (per the
  project brief, this was an explicit, accepted design choice). The
  station-to-station trip planner's travel-time and delay estimates are
  likewise simulated, built from real, curated line/station data (see
  "Station-to-station trip planner" above).
- **Air quality**, but only as a *fallback*: Tab 2 tries a live reading
  from the [OpenAQ](https://openaq.org/) API first, using the real
  coordinates of your selected city. It only falls back to a realistic
  simulated reading if no API key is configured, or if the live request
  fails for any reason (no nearby station, network issue, timeout).
  Every AQI number — live or simulated — is computed with the EPA's real,
  current (2024-revised) AQI breakpoint formula, not a made-up scale.

Community-flagged accessibility reports, saved locations, and your
sensitivity profile are all real user input, held only in the browser
session (they reset when the app restarts) — this was a deliberate scope
choice to keep the demo dependency-free (see "Extending it" below for how
to make any of them persistent).

## Project structure

```
local_daily_companion/
├── app.py             # Streamlit entrypoint — sidebar, tabs, theming, wires everything together
├── cities.py           # Shared registry: 18 real U.S. cities, coordinates, ZIPs, IANA timezones
├── transit.py           # Tab 1 — real agencies/lines/stations, routing, simulated live data, reports
├── air_quality.py        # Tab 2 — OpenAQ integration, EPA AQI math, simulated fallback
├── user_profile.py        # Saved locations + sensitivity profile + personal alert badges
├── briefing.py              # Daily Briefing sentence builder (pure logic, easy to unit-test)
├── charts.py                 # Plotly chart builders
├── requirements.txt
└── .streamlit/config.toml       # Custom theme
```

### How the personal features fit together

`app.py` computes the selected city's **local time** once per page load
(`cities.now_in_city(city)`), then computes that city's "right now" transit
status and air-quality reading **once** using that same local time
(`transit.get_current_status_summary()` and `air_quality.get_current_reading()`),
then hands all of that to four consumers: the Daily Briefing
(`briefing.build_daily_briefing()`), the Personal Alerts
(`user_profile.render_personal_alerts()`), and the two tabs themselves.
That's a deliberate design choice, not just tidiness — it guarantees the
briefing banner, the alert badges, and the tab content always agree with
each other and all show the *same* city-local clock, and it means a live
OpenAQ request only ever fires once per rerun instead of once per place
it's used.

## Running it

Requires Python 3.9+ (for the standard-library `zoneinfo` module used for
timezone conversion — `tzdata` in requirements.txt supplies the IANA
timezone database on platforms, like some Windows installs, that don't
ship one system-wide).

```bash
cd local_daily_companion
python3 -m venv venv
source venv/bin/activate          # on Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will open the app in your browser (usually http://localhost:8501).
It runs immediately with **zero configuration** — no API key required.

## Adding a live OpenAQ API key (optional)

By default, Tab 2 uses realistic simulated air-quality data. To switch to
**live** readings:

1. Register for a free key at
   [explore.openaq.org/register](https://explore.openaq.org/register).
2. Create a file at `.streamlit/secrets.toml` in this project folder (this
   file is gitignored by convention — never commit it) with:
   ```toml
   OPENAQ_API_KEY = "your-key-here"
   ```
   Alternatively, set an `OPENAQ_API_KEY` environment variable before
   running `streamlit run app.py`.
3. Restart the app. When a nearby station has recent data, you'll see a
   green "Live reading from OpenAQ" badge at the top of Tab 2 instead of
   the simulated-data badge. If a key is present but a particular city has
   no nearby reporting station (or the request fails for any reason), the
   app automatically and silently falls back to the simulation — it will
   never crash or show a blank screen because of this.

## Troubleshooting

- **"No module named streamlit/plotly/etc."** — make sure you activated
  your virtual environment and ran `pip install -r requirements.txt`.
- **Air quality tab always shows "Simulated demo data."** — this is
  expected with no API key configured. Follow the steps above to add one.
- **A city shows a live badge but seems to be missing a pollutant.** —
  not every OpenAQ station reports every pollutant. The app fills in
  what it has and marks anything missing as "N/A" rather than guessing.
- This project was built and reviewed in an environment without live
  access to PyPI or the OpenAQ API, so if you hit an unexpected error on
  first run, check `air_quality.py`'s `fetch_live_readings()` function
  first — it's the most version/response-shape-sensitive part of the
  code. Every non-UI function (city data, transit simulation, EPA AQI
  math, the simulated fallback) was independently unit-tested against
  known reference values before delivery; see the note at the bottom of
  this README.

## Extending it

- **Persist community reports, saved locations, or profile toggles across
  restarts:** all three currently live in `st.session_state`
  (`accessibility_reports` in `transit.py`; `saved_locations` and each
  `profile_toggle_*` key in `user_profile.py`). Swapping any of them for a
  small SQLite file via Python's built-in `sqlite3` module is a natural
  next step if you want them to survive an app restart, or to be visible
  across different users' sessions rather than just your own browser tab.
- **Add live hourly AQI history:** `air_quality.py` currently uses OpenAQ
  only for the *current* reading. OpenAQ's
  `/v3/sensors/{id}/measurements/hourly` endpoint can provide a real
  24-hour history to replace the simulated trend line when a live key is
  configured.
- **Add more cities:** add an entry to `CITIES` in `cities.py` (name,
  state, lat/lon, real IANA `timezone`, a few real ZIP codes) and a
  matching entry to `TRANSIT_SYSTEMS` in `transit.py` (real agency, lines,
  stations, and — if you want the new city to support the trip planner — a
  `line_sequences` dict of each line's real stations in real order, with at
  least one station shared between two lines so a transfer route exists).
  Both `CITIES` and `TRANSIT_SYSTEMS` are keyed by the same city name string.
- **Make the trip planner cover more of a system:** `line_sequences` is
  intentionally a small, curated subset per city (a handful of lines and
  their major/transfer stations) rather than a full official map — extend
  any city's entry with more real lines/stations from that agency's actual
  route map to widen the set of station pairs `transit.get_route()` can
  resolve.
- **Real transit feeds:** several agencies (e.g., MTA, WMATA, MBTA)
  publish free GTFS-realtime feeds. Swapping `transit.generate_arrivals()`
  for a real GTFS-realtime client per agency is the natural upgrade path
  if you want genuinely live arrivals for one or two flagship cities.

---

*Development note: this app was built and tested in a sandboxed environment
without live internet access to install Streamlit/Plotly or reach the
OpenAQ API directly. Every piece of non-UI logic — the EPA AQI
interpolation formula, the simulated data generators, the OpenAQ
fallback's error handling, the Daily Briefing sentence builder across
every transit/AQI/greeting combination, the saved-locations save/replace/
apply/remove flow, the station-to-station routing engine, the timezone
conversion for every city, and all tabs' and helpers' full render
functions — was verified with a dedicated offline test harness (stub
Streamlit/Plotly modules) across all 18 cities before delivery. That
harness specifically checked: every city resolves to a distinct, correct
IANA timezone and `now_in_city()` returns timezone-aware datetimes (not
server/UTC time); the same real instant produces different, correct local
hours and greetings for cities in different timezones (e.g. New York vs.
Los Angeles); the routing engine correctly finds direct routes, one-transfer
routes, and reports "not found" honestly for uncovered station pairs, and
returns byte-for-byte identical results for identical inputs (determinism);
and every "as of now"/"current hour" value used for AQI and transit
matches the selected city's own local clock, not the server's. One real
bug (a floating-point edge case in the AQI breakpoint lookup, where
PM2.5 = 9.1 could round to a value that fell through every bracket and
silently returned AQI 301 instead of 51) was caught and fixed in an
earlier pass and re-verified here. Still, since the actual Streamlit/Plotly
rendering, the live OpenAQ request/response shape, and the real
`st.context.timezone` browser API couldn't be exercised for real, give the
app a look after your first `streamlit run` and a quick OpenAQ key test if
you add one.*
