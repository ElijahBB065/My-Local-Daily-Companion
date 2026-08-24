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
7. **🌼 Environmental Health & Pollen Outlook** — tries a real, live
   PM2.5/pollen reading from the free Open-Meteo Air Quality API first;
   gracefully estimates an Asthma Hazard Level from PM2.5 + AQI when live
   pollen counts aren't available for your location (the normal case for
   U.S. cities); and falls back to a fully simulated seasonal reading
   (0-12 scale, matching Pollen.com/National Allergy Bureau conventions)
   if the live call fails outright. One clean card shows the Asthma Hazard
   Level, the Dominant Airborne Allergen, and a one-sentence Recommended
   Action — see "Live pollen & PM2.5 via Open-Meteo" below.
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
11. **🔒 Real account security & persistence** — signing up now hashes your
    password (PBKDF2-HMAC-SHA256, a unique random salt per account, 100,000
    iterations) and saves it to a small local database file, so an account
    you create survives closing the browser tab, reopening the app days
    later, or the app server restarting — log in with the same
    username/password again and again and it just works. See "Accounts:
    security & persistence" below for exactly how this works and its
    honest limits.
12. **💬 Send Feedback / Bug Report** — a small expander at the very bottom
    of the sidebar, always available, logged in or as a guest. Pick a
    category, type what you noticed, and it's saved to this session's
    feedback log — plus an optional link to a Google Form for pilot
    testers who want their note to actually reach the maintainer. See
    "Feedback widget" below.

Every city switch instantly updates the local time shown, the transit
board, and the air-quality reading — there's nothing to refresh separately.

## ⚠️ Keep all files in sync

`app.py`, `cities.py`, `transit.py`, `air_quality.py`, `accounts.py`,
`homepage.py`, `user_profile.py`, `briefing.py`, `outlook.py`, `pollen.py`,
`exports.py`, `community.py`, `feedback.py`, and `charts.py` are **always
delivered together as one matched set** and import from each
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

## 🔒 Accounts: security & persistence

This was rebuilt for the Week 1 pilot freeze so accounts behave like a real
(if small) auth system, not a demo:

- **Passwords are hashed, never stored in plain text.** Each account gets
  its own random 16-byte salt (`secrets.token_bytes`), and the password is
  run through `hashlib.pbkdf2_hmac("sha256", ..., 100_000 iterations)`
  before it ever touches disk. Logging in re-hashes the entered password
  with that same salt and compares the two hashes with `hmac.compare_digest`
  (a constant-time comparison, so the check itself can't leak timing
  information about how much of the password matched).
- **Accounts persist across restarts.** Sign-up writes to a small local
  SQLite database file (`accounts.db`, created automatically the first time
  the app runs — plain Python `sqlite3`, no extra dependency to install).
  Close the tab, restart the server, come back tomorrow — your account,
  saved city/ZIP/profile defaults, and saved routes are all still there,
  and you log in with the exact same username and password every time.
  (Being *logged in* is still a per-browser-session thing, the same way a
  normal website's session cookie works — but the account and its data
  underneath that login are durable now.)
- **`accounts.db` is never something you should commit to GitHub** — it
  holds real (hashed) pilot-tester credentials. The included `.gitignore`
  already excludes it.
- **Automatic fallback if the filesystem can't be written to.** Some free
  hosting tiers run on a read-only or ephemeral filesystem. If
  `accounts.db` can't be created, the app detects this once at startup and
  falls back to the old in-memory-only behavior automatically — the app
  never crashes because of it, it just quietly loses persistence for that
  deployment. Either way, the sidebar and Sign Up tab show an honest,
  accurate one-line status (`accounts.storage_mode_label()`) telling you
  which mode is active, so nothing here overpromises.
- **Usernames are case-insensitive.** "Alice" and "alice" are the same
  account for both login and duplicate-signup checks.
- **Login failures don't reveal which part was wrong.** A wrong password
  and a username that doesn't exist both show the identical message
  ("That username/password combination isn't recognized.") — this is a
  deliberate anti-enumeration measure so someone probing the login form
  can't tell which usernames are real.
- **Still worth knowing:** this is `hashlib`/`sqlite3` from Python's own
  standard library, chosen specifically to avoid adding a new dependency
  for a pilot. It's a real, solid step up from plain-text/in-memory
  storage — genuinely fine for a small pilot — but a larger production
  deployment would typically move to a dedicated password-hashing library
  (`bcrypt` or `argon2-cffi`) and a hosted database (Postgres, etc.) rather
  than a single local SQLite file. `accounts.py`'s docstring notes exactly
  where to make that swap if/when you need it.

## 💬 Feedback widget

A "💬 Send Feedback / Report a Bug" expander sits at the very bottom of the
sidebar on every view, for logged-in users and guests alike. Pick a
category (bug, confusing, idea, compliment, other), type a note, and
submit — it's appended to this session's feedback log
(`feedback.get_feedback()`) with a timestamp and your identity (your
username, or your guest ID if you're not logged in — the same identity
`community.py` already uses, so a guest's feedback and their community
posts are traceably the same person within a session). A divider below the
form also shows a link to a Google Form, for pilot testers whose feedback
should actually reach you between sessions.

**Read this before pilot launch:** the placeholder URL in `feedback.py`
(`GOOGLE_FORM_URL`) needs to be replaced with your own real Google Form
link before real pilot testers use it — right now it's a visible
placeholder, not a working form. Feedback submitted through the in-app
widget itself is session-only (like the rest of this app's user-generated
content) and isn't emailed or saved anywhere durable yet; if you want that
feedback to persist and reach you automatically, the natural upgrade is to
have `submit_feedback()` write into the same SQLite database `accounts.py`
already sets up (one more small table), rather than only `st.session_state`.

## 🎨 A minimalist redesign

An earlier pass gave the Home page a bold gradient hero with a row of badge
tags, a three-card live preview stack, AND a three-column feature grid
below it — taken together, it read as busy rather than clean. This pass
dialed that back deliberately: fewer distinct blocks, more whitespace, and
color used sparingly enough that it still means something when it appears.

- **One bold moment per page, not several.** Every page gets exactly one
  vivid gradient element — the Home page's hero card, or the Dashboard's
  outlook banner — and it's kept to a single headline plus one supporting
  line. Everything else on the page is a plain white card, so that one
  moment actually reads as "look here first" instead of competing with
  four other colorful things.
- **Calm status tiles.** The old Transit/Air Quality/Pollen tiles used to
  be fully filled with a saturated green/amber/red gradient. They're now
  plain white cards with a bold dark number and a small color-coded badge
  pill (🟢/🟡/🔴) — the same information, communicated with a lot less
  visual noise. The same badge system is reused by the new Environmental
  Health card below, so the whole app has exactly one way of signaling
  "good / worth a glance / needs attention," not a different color
  language per card.
- **Fewer, calmer cards overall.** Every card across the app — status
  tiles, the briefing card, the Community Hub's post and digest cards —
  now shares one flat off-white canvas (`#F8FAFC`), a hairline `#EEF2F6`
  border, an 18px radius, and one soft, subtle shadow, instead of each
  card mixing its own border/shadow/radius. Buttons are pill-shaped with a
  gentle hover lift, and `.streamlit/config.toml`'s `primaryColor` matches
  the emerald accent so Streamlit's own "primary" button fill (Log In,
  Sign Up, Save) stays in sync automatically, without fragile
  version-specific CSS chasing Streamlit's internal button markup.
- **A collapsible sidebar.** The sidebar used to stack city/ZIP selection,
  saved locations, the sensitivity profile, notification preferences, the
  account section, and two paragraphs of "about this app" text all as
  permanently-visible sections. City/ZIP and saved locations (the things
  you touch every visit) stay visible; the sensitivity profile,
  notification preferences, account actions, and the "about" caption are
  now grouped into one collapsed **"⚙️ More options"** expander, so the
  sidebar's primary job — picking where you are — isn't buried under
  settings you set once and forget.
- **The Home page, simplified.** Logged out, you get the hero, a
  "Get started" card (Log In / Sign Up / Guest tabs in a real
  `st.container(border=True)` card) next to a compact two-tile "right now
  in `<city>`" snapshot, and the Environmental Health & Pollen Outlook
  card below — that's it. The earlier three-card preview stack, the
  three-column feature grid, and the community post preview were cut:
  they demoed the same handful of ideas the tiles and the environmental
  card already show, just repeated in more boxes.

`st.container(border=True)` needs a reasonably recent Streamlit
(`requirements.txt` already pins `streamlit>=1.43`, well past when this
landed); if an older Streamlit is ever installed instead, the auth card
and the Environmental Health card both fall back to a plain, unbordered
container rather than crashing the page over a styling nicety.

## 🌼 Live pollen & PM2.5 via Open-Meteo, and the Environmental Health card

The Pollen Index used to be 100% simulated (see "What's real, and what's
simulated" below for why — there's no broadly available free real-time
pollen API). This pass adds a real, keyless integration with
[Open-Meteo's Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
(`pollen.fetch_open_meteo_environmental()`), which is tried FIRST on every
run before falling back to anything simulated.

**Please read this honest caveat before assuming a "PM2.5 estimate" badge
means something is broken:** Open-Meteo's pollen fields (alder, birch,
grass, mugwort, olive, ragweed) come from a European (CAMS) model and are
typically `null` for locations outside Europe — which is every one of this
app's 18 U.S. cities. A live call for a U.S. city will almost always come
back with real PM2.5/PM10 (those readings ARE global) and no pollen counts
at all. That's the expected, common case here, not a bug — and it's
exactly the scenario `pollen.estimate_hazard_from_pm()` exists to handle:

1. **Live pollen counts exist for this location** (rare here, but used
   directly when present) — the highest-reading pollen type becomes the
   Dominant Airborne Allergen, and the Asthma Hazard Level is the *worse*
   of that pollen category and the already-computed Air Quality Index
   (same "worst signal wins" rule `outlook.py` already uses elsewhere).
2. **Live call succeeds, no pollen counts returned** (the normal case for
   every city in this app) — the Asthma Hazard Level is estimated from the
   live PM2.5 reading (bucketed with the same EPA breakpoints
   `air_quality.py`'s own AQI math uses) and the AQI, again taking the
   worse of the two. The Dominant Airborne Allergen is honestly reported
   as the AQI's own dominant pollutant (PM2.5, PM10, or Ozone) rather than
   invented.
3. **The live call fails outright** (no network, timeout, bad response) —
   falls all the way back to the original fully-simulated seasonal
   `pollen.simulate_pollen()` reading, exactly as before this feature
   existed. Nothing about this integration can newly crash the app: every
   step is wrapped so a bad response, a timeout, or missing coordinates
   degrades to the next fallback instead of raising.

**🌼 Environmental Health & Pollen Outlook card:** one clean card with
three columns — **Asthma Hazard Level** (a colored badge: 🟢 Low, 🟡
Moderate/High, 🔴 Very High/Extreme), **Dominant Airborne Allergen**, and
a one-sentence **Recommended Action** for sensitive groups — plus a small
caption disclosing exactly which of the three cases above produced this
reading. It appears once on the Dashboard (replacing the old separate
Pollen tile, so the same information isn't shown in two places) and once
on the Home page for both guests and logged-in users, all calling the same
`homepage.render_environmental_card()` function so there's exactly one
implementation of this card, not several drifting copies.

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
e.g. *"Air quality is great · 0 transit delays · Pollen is low."* Two
matching status tiles just below the banner break the verdict out by
category (🚌 Transit / 🌬️ Air Quality), each with its own color-coded
badge, so a rough spot is visible even when the other is fine; the
Environmental Health & Pollen Outlook card handles the pollen/hazard side
in more detail (see below) rather than repeating it in a third tile. This
same banner + tiles + card also appear on a logged-in user's personalized
Home page — never a separate, possibly-contradicting verdict.

**🌼 Pollen & environmental hazard (`pollen.py`):** tries a real, live
PM2.5/pollen reading from Open-Meteo's free Air Quality API first, falls
back to estimating a hazard level from PM2.5 + AQI when live pollen counts
aren't available (the normal case for U.S. cities), and falls back further
to a fully simulated seasonal reading if the live call fails outright —
see "Live pollen & PM2.5 via Open-Meteo" below for the full breakdown. The
simulated fallback still follows a realistic Northern Hemisphere seasonal
curve (tree pollen peaks in spring, grass in early summer, ragweed/weed
pollen in late summer/early fall, mostly mold spores in winter),
deterministic per city + ZIP + calendar day, using the same 0-12 scale as
real pollen indices (Pollen.com / the National Allergy Bureau).

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

**Please read before you rely on this for anything real:** unlike user
accounts (which now persist — see "Accounts: security & persistence"
above), communities and their posts still live only in
`st.session_state` — server-side memory, for this session only. That's
enough to demo "post an issue → it appears → someone else upvotes it" end
to end within one browser tab, but there's no real database, nothing is
shared across different browsers/devices/users, and a restart clears
every community. See "Extending it" below for the natural persistence
upgrade path (the same SQLite approach already used for accounts would
work here too — one `communities` table, one `posts` table with a foreign
key, one `upvotes` table keyed by post + user).

## 🧹 Week 1 code freeze: bug sweep, UI polish, rerun optimization

A final pass across every file before the pilot build, covering three
things:

**Defensive error handling.** Every `st.session_state` read that used to
index a dict directly (`d["key"]`) now reads with a safe default
(`d.get("key", ...)`) throughout `app.py`, `air_quality.py`, `transit.py`,
`community.py`, and `homepage.py`. Every external or dynamic call that can
fail for reasons outside this app's control — the live OpenAQ request, a
ZIP-to-neighborhood lookup, resolving the selected city's data — is
wrapped in its own `try/except` with a friendly, on-brand fallback UI
state, close to where the call happens rather than one big catch-all
around an entire tab, so a single failing piece degrades gracefully
instead of taking the whole page down with a raw red traceback. Each
fallback dict was checked to include every key its consumer actually
reads — a partial fallback is its own latent bug (see the dedicated test
note above, which caught exactly this in a first draft of this pass).

**UI alignment & clean layout.** Buttons, form-submit buttons, and
download buttons share one consistent rounded shape and weight; text
inputs, text areas, and dropdowns share the same corner radius; dividers,
expanders, and column padding all follow one consistent spacing rhythm
instead of Streamlit's mismatched defaults — across the Home page,
Dashboard, and Community Hub alike. This is what "doesn't look
AI-generated" comes down to in practice: one deliberate, consistent visual
language everywhere, not a special case per page.

**Rerun optimization.** Several buttons that used to do
`if st.button(...): st.session_state[...] = value; st.rerun()` — nav
toggles, log out, applying a saved route or saved location, resolving a
report, upvoting a community post — now use Streamlit's `on_click`
callback instead. A callback runs and finishes *before* the next script
pass starts, so the state change is already in place by the time the page
redraws — no stale intermediate frame, no flicker, no need to click twice
for a change to "stick." Login and Sign Up were deliberately **left**
using the previous queue-and-rerun pattern instead of `on_click`, because
those forms need to show a conditional inline success/error message tied
to that exact submission, which a callback can't cleanly render in place —
see the code comment right above the login form in `homepage.py` for the
full reasoning.

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
- **Pollen & environmental hazard**, but only as a *fallback*, same pattern
  as air quality: tries a live PM2.5/pollen reading from the free
  Open-Meteo Air Quality API first. Real pollen counts specifically are
  usually unavailable for U.S. locations (Open-Meteo's pollen model is
  European-only today), in which case the hazard level is honestly
  estimated from live PM2.5 + AQI instead of showing nothing — only if the
  live call fails outright does this fall back to a fully simulated,
  clearly-labeled seasonal reading. See "Live pollen & PM2.5 via
  Open-Meteo" above for the full breakdown.

Community-flagged accessibility reports, saved locations, and your
sensitivity profile toggles are all real user input, held only in the
browser session (they reset when the app restarts) — this was a
deliberate scope choice to keep the demo dependency-free (see "Extending
it" below for how to make any of them persistent). **User accounts are the
one exception:** since the Week 1 polish pass, accounts (including saved
routes and saved defaults) persist in a local SQLite database and survive
an app restart — see "Accounts: security & persistence" above.

## Project structure

```
local_daily_companion/
├── app.py                 # Streamlit entrypoint — sidebar, view switching, wires everything together
├── homepage.py            # Home view — logged-out pitch/login/signup, or logged-in "Welcome back" dashboard
├── accounts.py            # User accounts: hashed passwords, SQLite persistence, saved defaults & routes
├── feedback.py            # Sidebar "Send Feedback / Bug Report" widget + session feedback log
├── cities.py              # Shared registry: 18 real U.S. cities, coordinates, ZIPs, IANA timezones,
│                          #   ZIP validation/lookup (cities.is_valid_zip / lookup_neighborhood)
├── transit.py             # Tab 1 — real agencies/lines/stations, routing, simulated live data, reports
├── air_quality.py         # Tab 2 — OpenAQ integration, EPA AQI math, simulated fallback
├── user_profile.py        # Saved locations + sensitivity profile + personal alert badges + notification prefs
├── briefing.py            # Daily Briefing sentence builder (pure logic, easy to unit-test)
├── outlook.py             # Rolls transit+AQI+pollen into one good/caution/hazard verdict (pure logic)
├── pollen.py              # Live Open-Meteo pollen/PM2.5 + hazard estimate, simulated fallback
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

- **Persist community reports, saved locations, or profile toggles across
  restarts:** these still live in `st.session_state`
  (`accessibility_reports` in `transit.py`; `saved_locations` and each
  `profile_toggle_*` key in `user_profile.py`). User accounts already made
  this jump (see "Accounts: security & persistence" above) via a small
  SQLite database through Python's built-in `sqlite3` module — the same
  pattern (one table per concept, keyed by username or community id) is
  the natural next step for these too, if you want them to survive an app
  restart or be visible across different users' sessions rather than just
  one browser tab.
- **Persist feedback submissions:** `feedback.py`'s in-app widget currently
  logs to `st.session_state` only — see "Feedback widget" above for the
  suggested SQLite upgrade path.
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

*The Week 1 code-freeze/polish pass got its own dedicated tests on top of
all of the above. `accounts.py`'s rewrite was verified end to end: hashed
passwords are never plain text and are never returned by `get_account()`;
two identical passwords for two different accounts produce two different
hashes (per-account salting is real); correct-password and wrong-password
logins behave correctly, and a wrong password and a nonexistent username
produce the exact same generic failure message; usernames match and
reject duplicates case-insensitively; accounts, saved preferences, and
saved routes all survive `st.session_state.clear()` (a genuine persistence
proof, not just an in-memory check); and the in-memory fallback mode was
separately exercised (with `PERSISTENT_STORAGE_AVAILABLE` temporarily
forced off) to confirm it never touches the real database file and still
behaves identically from the outside. A separate defensive-sweep test
confirmed `air_quality.render_air_quality_tab()` survives a minimal,
`None`, or empty reading dict without a `KeyError`; that the full `app.py`
survives `cities.lookup_neighborhood()` and `cities.get_city()` both
raising an exception (simulating a ZIP lookup or city-data failure) with a
friendly fallback instead of a raw traceback; and that `feedback.py`'s
submit/list logic works and correctly rejects whitespace-only submissions.
One real bug was caught by this last test before delivery: a
newly-added "defensive" fallback in `app.py` itself — falling back to the
first city's data if the selected city's lookup failed — wasn't wrapped in
its own `try/except`, so a broken `get_city()` could still crash through
the fallback path. Fixed by wrapping that fallback call too and adding one
further hardcoded last-resort city dict beneath it, on the principle that
a fallback which can itself throw isn't actually a fallback. All 8 test
files (covering every pass described in this README) were re-run clean
together immediately before this delivery.*

*The Home page visual overhaul got a ninth dedicated test file on top of
all of the above, confirming `render_logged_out()` survives being called
with every argument missing (the very first run's shape, before a city is
even resolved) and with deliberately wrong types (a string where a dict
was expected, a list where a dict was expected) without crashing, and that
the full `app.py` Home view ran clean across all 18 cities for a
logged-out visitor. (This test file was rewritten again for the
minimalist redesign pass below, since several of the functions it
originally covered — the three-card preview stack, the community post
preview, the three-column feature grid — no longer exist.)*

*The minimalist redesign and Open-Meteo integration added two more
dedicated test files. One exercises `pollen.py`'s new live-data path
directly, with `requests.get` monkeypatched to simulate: a successful
response with real pollen counts (confirms the highest-reading pollen
type is correctly chosen as the dominant allergen); a successful response
with pollen entirely absent, the realistic case for every U.S. city this
app covers (confirms the PM2.5/AQI-based estimate kicks in and correctly
takes the WORSE of the two); a network failure and a malformed response
(both confirmed to return `None` cleanly, never raise); and
`get_environmental_reading()`'s full three-case fallback chain end to end,
including with no coordinates at all. Separately, this sandbox has no
outbound network access to arbitrary hosts (the same limitation noted
below for PyPI/OpenAQ), so a real call to Open-Meteo was also attempted
with the actual `requests` library during development — it failed with a
connection error exactly as expected, which is itself a live confirmation
that the graceful-fallback path this feature depends on works against a
genuine failure, not just a simulated one.

The other new test file rewrote the Home-page coverage for the redesign:
it confirms `render_environmental_card()` survives every hazard category
(including unrecognized and missing categories), every reading `source`
string, and non-dict input; that `render_status_tile()` survives every
tier including invalid ones; and that the full `app.py` runs clean across
all 18 cities in BOTH the Home view and the Dashboard view with the new
two-tile-plus-environmental-card layout. All 10 test files were re-run
together immediately before this delivery.*
