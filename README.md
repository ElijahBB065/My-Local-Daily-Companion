# 🧭 Local Daily Companion

A bright, friendly Streamlit app for everyday city life: a Home page, a
Transit tab, an Air Quality tab, and several personal features layered on
top:

0. **🏠 Home page** — the default view on launch. Log in or sign up (both
   entirely optional — every feature works as a guest) and see a
   personalized "Welcome Back" dashboard with your saved city's instant
   Daily Briefing, a quick transit-status chip, and an air-quality chip,
   without re-entering anything.
1. **🚌 Transit Accessibility & Delay Tracker** — next-arrival boards, a
   station-to-station **trip planner** (pick an origin and destination and
   get an estimated travel time, active delay, and accessibility status for
   both stations, with the option to save it as one of your daily routes),
   delay patterns, elevator/escalator status, and community-flagged
   accessibility issues for **18 real U.S. cities** and their real transit
   systems.
2. **🌬️ Air Quality & Asthma Hazard Alerts** — current AQI, PM2.5, PM10, and
   Ozone levels with a plain-language Asthma Hazard Risk indicator and
   actionable recommendations, using live OpenAQ data when a key is
   configured and a realistic simulation otherwise.
3. **📮 Dynamic ZIP code lookup** — type **any** real 5-digit ZIP in a
   supported metro area, not just the featured neighborhoods in the
   dropdown, and every transit and air-quality simulation retunes itself to
   that exact ZIP.
4. **📌 Saved Locations** — save the current city/ZIP under a label like
   "Home," "Work," or "School" in the sidebar, then jump back to it with
   one click.
5. **🩺 Personal Sensitivity Profile** — toggle on Asthma / Sensitive
   Respiratory and/or Wheelchair / Stroller Access Required, and the app
   shows custom warning (or reassurance) badges right on the main
   dashboard whenever today's AQI or elevator status actually affects you.
   Logged-in users can save these toggles as their defaults.
6. **📰 Daily Briefing** — one friendly sentence at the very top of the
   dashboard, combining right-now transit and air-quality status, e.g.
   *"Good morning! Transit is running smoothly, but limit long outdoor
   runs today due to elevated AQI."*
7. **🌼 Pollen Index** — a simulated daily pollen reading (0-12 scale,
   matching Pollen.com/National Allergy Bureau conventions) following a
   real seasonal curve — tree pollen in spring, grass in early summer,
   ragweed in late summer/fall, mostly mold in winter — deterministic per
   city, ZIP, and calendar day.
8. **⚡ "Your Day Is Clear" outlook banner** — the very first thing on the
   dashboard: one bold, color-coded verdict (green "clear," amber
   "caution," red "hazard") rolled up from transit + air quality + pollen,
   built to be readable in under three seconds, backed by three matching
   vivid status tiles for Transit / Air Quality / Pollen underneath it.
9. **🔔 Daily Briefing Preferences & one-click export** — an opt-in morning
   reminder setting in the sidebar, a **"Download Daily Commute Calendar
   Event"** button that produces a real, importable `.ics` file (repeats
   daily, with a 15-minute-before alarm, today's actual briefing in the
   description), and a paste-ready plain-text daily summary via a
   one-click copy icon.
10. **🏘️ Local Community Hub** (Tab 3) — a town/neighborhood-specific
    message board. You're automatically routed to your own saved
    town/neighborhood's community; if it doesn't exist yet, one click
    creates it. Residents post across four categories (Transit/Road
    Delays, Air Quality/Pollen Spotting, Local Infrastructure Issues,
    General Town Chat) and upvote ("Me Too") the posts that matter most. A
    side panel shows the top 3 crowd-reported issues alongside this run's
    own official transit/AQI/pollen alerts, and a searchable list lets you
    browse and join other towns' communities without changing your saved
    city/ZIP.

Every city switch instantly updates the local time shown, the transit
board, and the air-quality reading — there's nothing to refresh separately.

## ⚠️ Keep all files in sync

`app.py`, `cities.py`, `transit.py`, `air_quality.py`, `accounts.py`,
`homepage.py`, `user_profile.py`, `briefing.py`, `outlook.py`, `pollen.py`,
`exports.py`, `community.py`, and `charts.py` are **always delivered
together as one matched set** and import from each
other — most importantly, several of them do `from cities import ...` at
their own top level. Uploading a newer `app.py` to GitHub next to an
**older** `cities.py` (e.g. from an earlier version of this project that
didn't yet have `now_in_city`, `lookup_neighborhood`, or `is_valid_zip`)
will raise an `ImportError` on startup, because Python's
`from module import a, b, c` fails as a whole if even *one* of those names
doesn't exist in `module` yet — even though `a` and `b` might be there.

**When you update this project, replace every file at once**, not just
the one(s) you asked about — grab the full delivery (the zip) rather than
mixing individual files from different messages/versions.

As a safety net, `app.py` now also handles this gracefully on its own: if
`cities.py` (or any other file above) is missing or out of sync, you'll
see a clear on-screen message telling you exactly what to fix instead of
a raw Python traceback, and if `cities.py` merely lacks one of the three
newer helper functions, `app.py` defines a working equivalent internally
so the app keeps running rather than crashing. Updating `cities.py` (and
everything else) to the latest version, together, is still the right
long-term fix.

## 🐛 Fixed: a crash on the first login click (StreamlitAPIException)

Logging in used to crash on the very first click with a
`StreamlitAPIException` — clicking "Log In" a second time appeared to
"work," but only because the crash had already happened silently and the
page was showing stale/default data, not because anything was actually
fixed.

**Root cause:** Streamlit refuses to let you write to
`st.session_state[key]` if the widget with that `key` has *already been
drawn earlier in the same script run* — it raises `StreamlitAPIException:
... cannot be modified after widget ... is instantiated`. The sidebar's
city and ZIP widgets render near the top of every run; the Home page's
login form renders further down, *after* them. The old login handler
called `accounts.apply_account_to_session(...)` directly from inside that
form — writing straight into the sidebar's city/ZIP/profile widget keys
after those widgets had already been drawn in that same run. Same root
cause, same fix, also applied to the sidebar's "go to this saved
location" button, which had the identical latent bug (just not yet
clicked in a way that surfaced it).

**The fix defers those writes to the start of the *next* run, before any
widget exists yet:**

- A button click (login, or "go to" a saved location) now just records
  *intent* — `accounts.queue_apply_on_next_run(username)` or
  `user_profile.queue_location_apply(loc)` — both of which only touch a
  plain, non-widget session key, then calls `st.rerun()`.
- At the very top of `app.py`, *before* the sidebar creates any widget,
  `accounts.consume_pending_apply(...)` and
  `user_profile.consume_pending_location(...)` check for a queued
  request and apply it right there — safe, because no widget has been
  instantiated yet this run.
- A related interaction bug turned up while testing this fix: applying a
  saved city+ZIP *together* was immediately being mistaken by the
  sidebar's own "reset ZIP when you switch cities" logic for a plain user
  city switch, which then wiped the just-applied ZIP back to that city's
  generic default a moment later. Fixed by having the apply functions
  also update the same "last city ZIP was set for" tracker
  (`ZIP_CITY_CONTEXT_KEY`) the reset logic checks.

`homepage.render_homepage()` (and `render_logged_in()` specifically) also
got a defensive pass per this fix: every value it receives — city,
neighborhood, ZIP, the briefing text, the transit/AQI dictionaries, even
the current-time object — is normalized to a safe default if it's
`None`/empty/the wrong type, so a missing or not-yet-ready piece renders
as a slightly less complete page instead of a `KeyError`/`TypeError`.

This was caught with a test that replays the exact failure sequence:
render the sidebar (simulating its widgets already existing this run),
queue a login/location apply, confirm the queue never touches a widget
key mid-script, run again, and confirm the queued city/ZIP/profile (and
only those) land correctly on the next run — including the "applied
together" case that exposed the ZIP-reset interaction above.

## 🏠 Home page & accounts

Launching the app now lands you on a **Home page** first, not straight into
the dashboard. Logged out, it's a short pitch for the app plus three tabs:
**Log In**, **Sign Up**, and **Continue as Guest** — an account is never
required, and every feature (including saving locations, the sensitivity
profile, and the trip planner) works fully for a guest exactly as before.

Signing up (just a username and password) logs you in immediately with a
starter profile. Once logged in, a **"💾 Save city/ZIP/profile as my
defaults"** button appears in the sidebar — click it any time your
dashboard is set up the way you like, and from then on your Home page shows
a personalized **"Welcome back"** dashboard: your saved city's Daily
Briefing, a transit-status chip (smooth / minor / major delays, elevator
outage count), an air-quality chip (AQI + category), and any transit routes
you've starred from the trip planner (Tab 1 → "Plan a trip" → "⭐ Save this
as one of my daily routes" once logged in) — all pulled from the exact same
computation the full dashboard uses, so the two views never disagree. A
"🧭 Open my full dashboard →" button on the Home page (and a "🏠 Home" /
"🧭 Dashboard" toggle in the sidebar at all times) switches between the two
views.

**Please read before you rely on this for anything real:** accounts here
are a demo login, not a production auth system. They live only in
`st.session_state` — in server-side memory, for the current session only.
That means signing up and logging back in works great *within* one browser
session (which is what makes the "log in → instantly personalized" flow
demoable end to end), but accounts do **not** survive an app restart and
are **not** shared across different browsers, devices, or users. Passwords
are stored in plain text in that same in-memory store — completely fine
for trying out the feature, but never reuse a real password here. See
"Extending it" below for the real-database upgrade path.

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

## 🐛 Fixed: a session-state crash when picking a ZIP code

An earlier version kept the sidebar's ZIP selection as a **list index**
(e.g. `1` meaning "the second ZIP in this city's list") in
`st.session_state`, guarded by:

```python
if st.session_state.get(ZIP_KEY, 0) >= len(zip_options):
    st.session_state[ZIP_KEY] = 0
```

That comparison assumes whatever's sitting in `ZIP_KEY` is always an
`int`. The moment anything else wrote a ZIP **string** into that same slot
instead — a saved location, or (once accounts were added) a saved
account default — the comparison became `"10001" >= 3`, which Python
can't evaluate between a `str` and an `int`, and the app crashed with:

```
TypeError: '>=' not supported between instances of 'str' and 'int'
```

**The fix removes the index scheme entirely.** `ZIP_KEY` now always holds
a plain ZIP-code *string* (e.g. `"10001"`), validated on every read with
`cities.is_valid_zip()` — a strict type + format check (`isinstance(x,
str) and x.isdigit() and len(x) == 5`) — instead of a bare numeric
comparison. Anything that isn't a valid 5-digit string (an old int index,
`None`, an empty string, a stray float) is caught and safely replaced with
that city's first featured ZIP, with a one-line notice instead of a crash.
This is also what makes typing in *any* ZIP code possible (see below) —
the fix and the new feature share the same root change. It's covered by an
automated regression test that specifically re-injects the old crash
shape (an int, `None`, a too-long string, etc.) directly into session
state and confirms `app.py` runs clean every time.

## 📮 Dynamic ZIP code lookup

The sidebar now has two ways to pick a ZIP: a **"✨ Featured
neighborhood"** dropdown (the same curated, real neighborhoods as before),
and a **"📍 Or type any 5-digit ZIP code"** text box. Type in any real ZIP
within the selected city's metro area and:

- **Air quality** re-simulates specifically for that ZIP — `air_quality.py`
  already seeded its simulated PM2.5/PM10/Ozone curve from `(city, zip)`
  together (`stable_seed(city, zip_code)`), so this worked correctly for
  any ZIP as soon as the UI could accept one.
- **Transit** now does the same: `transit.get_current_seed(city, zip_code)`
  folds the ZIP into the arrivals/accessibility seed, so different ZIPs in
  the same city see a slightly different (but internally consistent)
  simulated snapshot rather than an identical one city-wide.
- The **neighborhood name** shown is the real, curated one for a featured
  ZIP; for any other real ZIP, the app shows an honest generic label (e.g.
  "ZIP 10099 area") with a one-line note explaining that this demo doesn't
  ship a full ZIP-to-neighborhood directory — rather than inventing a
  neighborhood name it doesn't actually know. The city's real transit
  system and real coordinates are still used either way.
- Switching cities resets the ZIP field to that city's first featured ZIP,
  so you never end up looking at, say, a Chicago ZIP while the sidebar
  still says "New York, NY."

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
- If you're logged in, a **"⭐ Save this as one of my daily routes"** button
  saves the route to your account (up to 8) — they show up both here (as
  quick "▶️" apply buttons for that city) and on your Home page.

This runs on a **curated, simplified subset** of each city's real lines and
stations (`transit.py`'s `line_sequences`) — enough real transfer points to
demonstrate meaningful routing (e.g. NYC's Times Sq-42 St, Union Sq-14 St,
and Atlantic Ave-Barclays Ctr; DC's Metro Center and L'Enfant Plaza;
Chicago's Clark/Lake), but **not the complete official system map**. If you
pick a real station pair this demo's simplified network doesn't happen to
connect (directly or with one transfer), the app says so plainly rather than
guessing — that's expected and by design, not a bug.

## ⚡ Today's Outlook, Pollen Index, and one-click export

The dashboard's original small "🧭 Local Daily Companion" header banner has
been replaced by a bigger, bolder **outlook banner** — the actual "aha"
moment of the page. It answers one question — *should I even worry about
today?* — before you've looked at a single tab, using the same colors a
transit or health app uses for status: bright green for "go," amber for
"keep an eye out," red for "take it slow."

**How the verdict is computed (`outlook.py`):** transit's delay level, the
AQI category, and today's pollen category are each mapped onto the same
three-tier scale (good / caution / hazard), and the overall banner shows
the *worst* of the three — a single hazard (a major delay, unhealthy air,
extreme pollen) drives the headline, not an average that could quietly
bury it. The subtext line underneath is built from the same real numbers,
e.g. *"Air quality is great · 0 transit delays · Pollen is low."* Three
matching vivid tiles just below the banner break the same verdict out by
category (🚌 Transit / 🌬️ Air Quality / 🌼 Pollen), each independently
color-coded, so a single rough spot is visible even when the other two are
fine. This exact same banner + tiles also appear on a logged-in user's
personalized Home page — never a separate, possibly-contradicting verdict.

**🌼 Pollen Index (`pollen.py`):** there's no broadly available free
real-time pollen API the way OpenAQ covers air quality, so — same honesty
pattern as the rest of this app — pollen is clearly-labeled **simulated**
data. It isn't random noise: the baseline follows a realistic Northern
Hemisphere seasonal curve (tree pollen peaks in spring, grass in early
summer, ragweed/weed pollen in late summer/early fall, mostly mold
spores in winter) and is deterministic per city + ZIP + calendar day, so
it reads as "today's forecast" rather than reshuffling on every page
reload — but it genuinely changes from one real day to the next, which is
the honest behavior for something that does vary daily in real life. Uses
the same 0-12 scale as real pollen indices (Pollen.com / the National
Allergy Bureau).

**🔔 Daily Briefing Preferences:** a "Remind me every morning" toggle plus
a preferred time, in the sidebar. **Read this note in the app itself, not
just here:** a browser tab running Streamlit cannot push a real
notification to your phone or send an email while it isn't open — that
would need a real backend with its own scheduler and a push/email
provider, which this project intentionally doesn't have (no fake "sent!"
toast that nothing backs up). What this setting *actually* does: it
decides whether the Home page shows a morning-reminder framing, and it
pre-fills the time used by the calendar export below, so the exported
event fires at the time you actually asked for, every day, once it's in
your own calendar app.

**📤 Save or share today's outlook:** an expander on the dashboard with two
real, working exports (`exports.py`), both built from the exact same
numbers as the banner above them — nothing here is a placeholder:

- **⬇️ Download Daily Commute Calendar Event (.ics)** — a real RFC 5545
  calendar file (`VCALENDAR`/`VEVENT`/`VALARM`) that repeats daily
  (`RRULE:FREQ=DAILY`) at your preferred reminder time, with a 15-minute
  advance alarm and today's actual Daily Briefing sentence in the event
  description. Import it into Google Calendar, Apple Calendar, or Outlook
  and your own calendar app handles the real, recurring alarm from there.
- **📋 Copy today's summary** — a plain-text block (via `st.code()`'s
  built-in copy icon) with today's headline, transit/AQI/pollen numbers,
  and the full Daily Briefing sentence, ready to paste into a text message
  or note.

## 🏘️ Local Community Hub (Tab 3)

A third tab alongside Transit and Air Quality: a **town/neighborhood-specific
message board**, keyed by the same (city, neighborhood) pair the sidebar
already resolves from your selected city/ZIP (`cities.lookup_neighborhood`)
— so a community is always named after somewhere real and specific (e.g.
"Chelsea Community" in New York, NY), not a generic city-wide bucket.

**Automatic routing + creation (`community.py`):** opening the tab
routes you straight to your own saved town's community if one already
exists — no picker, no extra click. If it doesn't exist yet, you'll see a
one-click **"➕ Create `<neighborhood>` Community"** button instead of a
dead end; creating it seeds a friendly welcome post so it's never a blank
page, and makes you its first member automatically.

**Message board:** a post form lets any resident (logged in, or a stable
per-session guest identity like `Guest-a1b2c` if not — accounts are
optional everywhere in this app, and the Community Hub is no exception)
post to one of four categories:

- 🚌 Transit / Road Delays
- 🌬️ Air Quality / Pollen Spotting
- 🛠️ Local Infrastructure Issues (a broken elevator, a flooded street, etc.)
- 💬 General Town Chat

A category filter narrows the feed, and every post carries a **"👍 Me Too"**
button — clicking it upvotes (and clicking again un-votes) using your own
stable identity, so double-voting isn't possible and your own vote is
remembered across reruns within the session.

**Community & Alert Digest side panel:** next to the message board, a
digest shows the **top 3 crowd-reported issues** for that town (ranked by
upvote count, General Chat excluded since it isn't really an "issue") right
alongside **this run's own official alerts** — the same already-computed
transit delay/elevator-outage, AQI, and pollen readings the outlook banner
uses elsewhere on the page, never re-fetched or re-simulated separately, so
the digest can't disagree with the rest of the dashboard.

**Browse & join other towns:** a "🔍 Browse or join other town communities"
section lets you search across every community anyone has created this
session by name/city and either **view** one (without changing your own
saved city/ZIP) or **join** it — a "↩️ Back to my town" button always
returns you to your own community's view.

**Please read before you rely on this for anything real:** exactly like
accounts, saved locations, and transit's own community reports elsewhere
in this app, communities and their posts live only in `st.session_state`
— server-side memory, for this session only. That's enough to demo
"post an issue → it appears → someone else upvotes it" end to end within
one browser tab, but there's no real database, nothing is shared across
different browsers/devices/users, and a restart clears every community.
See "Extending it" below for the natural persistence upgrade path (the
same small-SQLite approach already suggested for accounts and saved
locations would work here too — one `communities` table, one `posts`
table with a foreign key, one `upvotes` table keyed by post + user).

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
- **Pollen Index.** There's no broadly available free real-time pollen API
  the way OpenAQ covers air quality, so this is always clearly-labeled
  simulated data, following a realistic seasonal curve per city/ZIP/day —
  see "Today's Outlook, Pollen Index, and one-click export" above.

Community-flagged accessibility reports, saved locations, your sensitivity
profile, and user accounts (including saved routes) are all real user
input, held only in the browser session (they reset when the app
restarts) — this was a deliberate scope choice to keep the demo
dependency-free (see "Extending it" below for how to make any of them
persistent).

## Project structure

```
local_daily_companion/
├── app.py                 # Streamlit entrypoint — sidebar, view switching, wires everything together
├── homepage.py            # Home view — logged-out pitch/login/signup, or logged-in "Welcome back" dashboard
├── accounts.py            # Session-only user accounts: sign up / log in, saved defaults & routes
├── cities.py              # Shared registry: 18 real U.S. cities, coordinates, ZIPs, IANA timezones,
│                          #   ZIP validation/lookup (cities.is_valid_zip / lookup_neighborhood)
├── transit.py             # Tab 1 — real agencies/lines/stations, routing, simulated live data, reports
├── air_quality.py         # Tab 2 — OpenAQ integration, EPA AQI math, simulated fallback
├── user_profile.py        # Saved locations + sensitivity profile + personal alert badges + notification prefs
├── briefing.py            # Daily Briefing sentence builder (pure logic, easy to unit-test)
├── outlook.py             # Rolls transit+AQI+pollen into one good/caution/hazard verdict (pure logic)
├── pollen.py              # Simulated daily Pollen Index, seasonal curve, per city/ZIP/day
├── exports.py             # .ics calendar event + plain-text daily summary builders (pure logic)
├── community.py           # Tab 3 — town/neighborhood message board, upvotes, community digest panel
├── charts.py              # Plotly chart builders
├── requirements.txt
└── .streamlit/config.toml # Custom theme
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

- **Persist community reports, saved locations, profile toggles, or user
  accounts across restarts:** all of these currently live in
  `st.session_state` (`accessibility_reports` in `transit.py`;
  `saved_locations` and each `profile_toggle_*` key in `user_profile.py`;
  the whole `accounts_store` dict in `accounts.py`). Swapping any of them
  for a small SQLite database via Python's built-in `sqlite3` module is a
  natural next step if you want them to survive an app restart, or to be
  visible across different users' sessions rather than just your own
  browser tab. For accounts specifically, that upgrade should also add
  real password hashing (e.g. `hashlib.pbkdf2_hmac` or `bcrypt`) in place
  of `accounts.py`'s current plain-text, in-memory demo storage — see that
  module's docstring for the exact spots to change (`sign_up`/`log_in`
  compare `account["password"]` directly today).
- **Add a real ZIP-to-neighborhood directory:** `cities.lookup_neighborhood()`
  only recognizes each city's small curated list today; a free ZIP
  centroid dataset (e.g. the US Census Bureau's ZCTA gazetteer) would let
  you resolve any real ZIP to an actual neighborhood/lat-lon instead of the
  current honest "ZIP {code} area" placeholder, and would let `air_quality.py`
  fetch OpenAQ readings from that ZIP's own coordinates instead of the
  city-wide ones.
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
earlier pass and re-verified here.

This pass added the same rigor for the session-state crash fix, dynamic
ZIP lookup, and the Home page/account system: an automated test
re-injects the exact historical bug shape (an `int`, `None`, a too-long
string, and other non-ZIP values) directly into `st.session_state`'s ZIP
slot and runs the full `app.py` script end to end, confirming no
`TypeError` anywhere, in both the Home and Dashboard views; sign-up,
login with correct and incorrect credentials, duplicate-username
rejection, saving preferences, and saving/replacing/removing routes were
each exercised directly against `accounts.py`; and the full app was run
across all 18 cities × guest/logged-in × Home/Dashboard (72 combinations)
plus several custom, unfeatured ZIP codes, with no crash in any
combination. Still, since the actual Streamlit/Plotly rendering, the live
OpenAQ request/response shape, and the real `st.context.timezone` browser
API couldn't be exercised for real, give the app a look after your first
`streamlit run` and a quick OpenAQ key test if you add one.*

*This same offline harness was extended for the visual overhaul, Pollen
Index, outlook banner, and export features: `pollen.simulate_pollen()` was
checked for determinism (same city/ZIP/day → identical reading), for
tracking the intended seasonal curve (spring tree pollen reads higher than
winter mold, for example), and for tailoring differently across ZIPs;
`outlook.compute_outlook()` was checked against known-good, known-bad, and
known-mixed transit/AQI/pollen combinations to confirm the "worst of the
three tiers wins" rule and that missing data reads as caution rather than
crashing or silently reading as "all clear"; `exports.build_commute_ics()`
was checked for a valid `VCALENDAR`/`VEVENT`/`VALARM` structure, the daily
`RRULE`, CRLF line endings, and correct RFC 5545 escaping of commas/newlines
in the description; and the full `app.py` was re-run across all 18 cities,
both views, and both notification-preference states with the new banner,
tiles, and export section wired in, with no crash in any combination.*

*The Community Hub got the same treatment: `community.py`'s core logic —
deterministic community ids per (city, neighborhood), idempotent creation
(no duplicate welcome posts or accidental extra members from a second
"create" call), category validation and empty-text rejection on posts,
per-identity upvote toggling (including against nonexistent community/post
ids, which fail gracefully rather than raising), the "top 3 issues exclude
chat" rule, and `official_alerts()`'s output for both an all-clear and a
multi-alert scenario — was unit-tested directly. The full `app.py` was then
re-run with the Community Hub as a third tab across all 18 cities plus a
logged-in flow, confirming visiting the dashboard never silently
auto-creates a community (creation is one explicit click), that a
logged-in user is auto-joined to their OWN already-existing town community
on a later visit with no extra click, and that browsing/joining OTHER
towns' communities never disturbs your own saved city/ZIP.*
