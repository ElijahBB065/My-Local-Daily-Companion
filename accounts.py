"""
accounts.py
User accounts: sign up / log in, and each account's saved defaults (home
city, default ZIP, sensitivity profile, saved transit routes) so a
returning user gets a personalized "Welcome Back" homepage without
re-entering anything.

SECURITY: passwords are never stored in plain text. Signing up generates a
random per-account salt (`secrets.token_bytes`) and stores only a salted
PBKDF2-HMAC-SHA256 hash of the password (100,000 iterations) -- the same
family of algorithm real systems use for password storage, built entirely
from Python's standard library so this project stays dependency-free (a
dedicated library like `bcrypt` or `argon2` would be the natural next step
for a real production system -- see "Extending it" in the README). The
plaintext password is never written to session state, a database file, or
a log line. Logging in compares hashes with `hmac.compare_digest` (a
constant-time comparison) rather than `==`, so response timing can't leak
information about how much of a password guess was correct.

PERSISTENCE: accounts are stored in a small local SQLite database file
(`accounts.db`, created automatically next to this file) using only the
standard-library `sqlite3` module. That means signing up once and logging
back in with the SAME username and password now works ACROSS app restarts
and across different browser sessions on the same running app instance --
not just within one browser tab's memory, which is how earlier versions of
this project worked.

HONEST LIMITS -- please read before a real pilot:
  * Being "logged in" is still tied to your current browser session
    (`st.session_state`), exactly like a session cookie -- closing the tab
    logs you out. What now genuinely persists is the ACCOUNT itself: your
    username, password, and saved preferences survive both that and a
    server restart, so logging back in with the same credentials works.
  * If this app is deployed somewhere with an ephemeral or read-only
    filesystem (some free hosting tiers wipe local files on every
    redeploy, or don't allow writing one at all), `accounts.db` won't
    survive a redeploy either. This module detects that automatically at
    startup (`PERSISTENT_STORAGE_AVAILABLE`) and falls back to the old
    session-only, in-memory behavior instead of crashing -- the sidebar
    shows a one-line, honest note about which mode is active.
  * This still isn't enterprise-grade auth: there's no email verification,
    password reset flow, or login rate-limiting, and HTTPS enforcement is
    your hosting provider's job, not this app's. See the README's
    "Extending it" section for the real upgrade path (a managed auth
    provider, or `bcrypt`/`argon2` plus a proper multi-user database).
"""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone

import streamlit as st

from cities import CITY_NAMES, get_city

ACCOUNTS_KEY = "accounts_store"  # only used as the in-memory fallback store, see PERSISTENT_STORAGE_AVAILABLE
CURRENT_USER_KEY = "current_username"
MAX_SAVED_ROUTES = 8
MIN_USERNAME_LEN = 2
MAX_USERNAME_LEN = 32
MIN_PASSWORD_LEN = 6
PBKDF2_ITERATIONS = 100_000

# Overridable via an environment variable so a test suite (or a deployment
# that wants the database on a specific persistent volume) can point this
# somewhere other than "next to this file" without editing code.
_DB_PATH = os.environ.get(
    "LOCAL_DAILY_COMPANION_ACCOUNTS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts.db"),
)


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------
def _new_salt() -> bytes:
    return secrets.token_bytes(16)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS).hex()


def _passwords_match(password: str, salt_hex: str, expected_hash: str) -> bool:
    try:
        candidate = _hash_password(password, bytes.fromhex(salt_hex))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected_hash)


# --------------------------------------------------------------------------
# Storage backend -- SQLite on disk when the filesystem allows it, a plain
# session_state dict (the old behavior) when it doesn't. Decided once, at
# import time, so every function below can just check the one flag.
# --------------------------------------------------------------------------
def _try_init_db() -> bool:
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                username TEXT PRIMARY KEY,
                username_lower TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                home_city TEXT NOT NULL,
                default_zip TEXT NOT NULL,
                asthma INTEGER NOT NULL DEFAULT 0,
                wheelchair INTEGER NOT NULL DEFAULT 0,
                saved_routes TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


PERSISTENT_STORAGE_AVAILABLE = _try_init_db()


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH, timeout=5)


def storage_mode_label() -> str:
    """A one-line, honest status for the sidebar/account section."""
    if PERSISTENT_STORAGE_AVAILABLE:
        return "🔒 Accounts are saved to this app's local database — log back in any time with the same username/password."
    return ("⚠️ Running in memory-only mode this session (the hosting environment's filesystem isn't writable) — "
            "accounts here won't survive an app restart. See the README for details.")


# --------------------------------------------------------------------------
# Session state (the "who's currently logged in" flag is ALWAYS per-browser-
# session, in st.session_state, regardless of storage backend -- exactly
# like a session cookie on a real site logging you out when you close the
# tab, even though your account/password are safely stored server-side)
# --------------------------------------------------------------------------
def init_accounts_state():
    if not PERSISTENT_STORAGE_AVAILABLE and ACCOUNTS_KEY not in st.session_state:
        st.session_state[ACCOUNTS_KEY] = {}
    if CURRENT_USER_KEY not in st.session_state:
        st.session_state[CURRENT_USER_KEY] = None


def current_user():
    """The logged-in username, or None if nobody's logged in."""
    init_accounts_state()
    return st.session_state[CURRENT_USER_KEY]


def is_logged_in() -> bool:
    return current_user() is not None


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------
def _resolve_username(username: str):
    """Case-insensitive lookup of the canonical stored username -- so
    logging in as 'Alice' matches an account created as 'alice', which is
    friendlier and more forgiving than most people expect a demo app to
    be. Returns None if no account matches."""
    lower = (username or "").strip().lower()
    if not lower:
        return None
    if PERSISTENT_STORAGE_AVAILABLE:
        try:
            with _connect() as conn:
                row = conn.execute(
                    "SELECT username FROM accounts WHERE username_lower = ?", (lower,)
                ).fetchone()
            return row[0] if row else None
        except Exception:
            return None
    init_accounts_state()
    for stored in st.session_state[ACCOUNTS_KEY]:
        if stored.lower() == lower:
            return stored
    return None


def _username_taken(username: str) -> bool:
    return _resolve_username(username) is not None


def get_account(username: str) -> dict:
    """The account dict for `username`, or None if it doesn't exist.
    Shape is always {'home_city', 'default_zip', 'profile', 'saved_routes',
    'created_at'} regardless of which storage backend is active, and never
    includes the password hash -- nothing outside this module needs it."""
    if not username:
        return None
    if PERSISTENT_STORAGE_AVAILABLE:
        try:
            with _connect() as conn:
                row = conn.execute(
                    "SELECT home_city, default_zip, asthma, wheelchair, saved_routes, created_at "
                    "FROM accounts WHERE username = ?",
                    (username,),
                ).fetchone()
        except Exception:
            return None
        if not row:
            return None
        home_city, default_zip, asthma, wheelchair, saved_routes_json, created_at = row
        try:
            saved_routes = json.loads(saved_routes_json) if saved_routes_json else []
        except (TypeError, ValueError):
            saved_routes = []
        return {
            "home_city": home_city, "default_zip": default_zip,
            "profile": {"asthma": bool(asthma), "wheelchair": bool(wheelchair)},
            "saved_routes": saved_routes, "created_at": created_at,
        }

    init_accounts_state()
    record = st.session_state[ACCOUNTS_KEY].get(username)
    if not record:
        return None
    return {
        "home_city": record.get("home_city"), "default_zip": record.get("default_zip"),
        "profile": dict(record.get("profile", {})), "saved_routes": list(record.get("saved_routes", [])),
        "created_at": record.get("created_at"),
    }


# --------------------------------------------------------------------------
# Sign up / log in / log out
# --------------------------------------------------------------------------
def sign_up(username: str, password: str) -> tuple:
    """Create a new account and log in as it. Returns (ok, message)."""
    init_accounts_state()
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return False, "Please enter both a username and a password."
    if not (MIN_USERNAME_LEN <= len(username) <= MAX_USERNAME_LEN):
        return False, f"Username should be {MIN_USERNAME_LEN}-{MAX_USERNAME_LEN} characters."
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Password should be at least {MIN_PASSWORD_LEN} characters."
    if _username_taken(username):
        return False, f"'{username}' is already taken — try logging in instead, or pick another username."

    home_city = CITY_NAMES[0]
    default_zip = get_city(home_city)["zips"][0]["zip"]
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    salt = _new_salt()
    password_hash = _hash_password(password, salt)

    if PERSISTENT_STORAGE_AVAILABLE:
        try:
            with _connect() as conn:
                conn.execute(
                    "INSERT INTO accounts (username, username_lower, password_hash, salt, home_city, "
                    "default_zip, asthma, wheelchair, saved_routes, created_at) VALUES (?,?,?,?,?,?,0,0,'[]',?)",
                    (username, username.lower(), password_hash, salt.hex(), home_city, default_zip, created_at),
                )
        except sqlite3.IntegrityError:
            return False, f"'{username}' is already taken — try logging in instead, or pick another username."
        except Exception:
            return False, "Couldn't create your account right now — please try again in a moment."
        st.session_state[CURRENT_USER_KEY] = username
        return True, f"Welcome, {username}! Your account has been created and saved."

    st.session_state[ACCOUNTS_KEY][username] = {
        "password_hash": password_hash, "salt": salt.hex(),
        "home_city": home_city, "default_zip": default_zip,
        "profile": {"asthma": False, "wheelchair": False},
        "saved_routes": [], "created_at": created_at,
    }
    st.session_state[CURRENT_USER_KEY] = username
    return True, f"Welcome, {username}! Your account is ready for this session (see the sidebar note on saving accounts)."


def log_in(username: str, password: str) -> tuple:
    """Returns (ok, message). Deliberately gives the same generic failure
    message whether the username doesn't exist or the password is wrong,
    so a failed attempt can't be used to discover which usernames exist."""
    init_accounts_state()
    generic_failure = "That username/password combination isn't recognized."
    canonical = _resolve_username(username)
    if not canonical:
        return False, generic_failure
    password = password or ""

    if PERSISTENT_STORAGE_AVAILABLE:
        try:
            with _connect() as conn:
                row = conn.execute(
                    "SELECT password_hash, salt FROM accounts WHERE username = ?", (canonical,)
                ).fetchone()
        except Exception:
            return False, "Login is temporarily unavailable — please try again in a moment."
        if not row or not _passwords_match(password, row[1], row[0]):
            return False, generic_failure
    else:
        record = st.session_state[ACCOUNTS_KEY].get(canonical)
        if not record or not _passwords_match(password, record.get("salt", ""), record.get("password_hash", "")):
            return False, generic_failure

    st.session_state[CURRENT_USER_KEY] = canonical
    return True, f"Welcome back, {canonical}!"


def log_out():
    st.session_state[CURRENT_USER_KEY] = None


# --------------------------------------------------------------------------
# Saved preferences / routes
# --------------------------------------------------------------------------
def save_preferences(username: str, city: str, zip_code: str, profile: dict) -> bool:
    """Persist the user's preferred home city, default ZIP, and sensitivity
    profile onto their account (to disk, when persistent storage is
    available)."""
    if not get_account(username):
        return False
    profile = profile or {}
    asthma = int(bool(profile.get("asthma")))
    wheelchair = int(bool(profile.get("wheelchair")))

    if PERSISTENT_STORAGE_AVAILABLE:
        try:
            with _connect() as conn:
                conn.execute(
                    "UPDATE accounts SET home_city=?, default_zip=?, asthma=?, wheelchair=? WHERE username=?",
                    (city, zip_code, asthma, wheelchair, username),
                )
            return True
        except Exception:
            return False

    record = st.session_state[ACCOUNTS_KEY].get(username)
    if not record:
        return False
    record["home_city"] = city
    record["default_zip"] = zip_code
    record["profile"] = {"asthma": bool(asthma), "wheelchair": bool(wheelchair)}
    return True


def _write_saved_routes(username: str, routes: list) -> bool:
    if PERSISTENT_STORAGE_AVAILABLE:
        try:
            with _connect() as conn:
                conn.execute("UPDATE accounts SET saved_routes=? WHERE username=?", (json.dumps(routes), username))
            return True
        except Exception:
            return False
    record = st.session_state[ACCOUNTS_KEY].get(username)
    if not record:
        return False
    record["saved_routes"] = routes
    return True


def add_saved_route(username: str, city: str, origin: str, destination: str, label: str = "") -> bool:
    """Save a daily transit route (origin -> destination for a given city)
    to the user's account, keeping the most recent MAX_SAVED_ROUTES."""
    account = get_account(username)
    if not account:
        return False
    label = (label or "").strip() or f"{origin} → {destination}"
    routes = [r for r in account["saved_routes"] if r.get("label") != label]
    routes.insert(0, {"label": label, "city": city, "origin": origin, "destination": destination})
    routes = routes[:MAX_SAVED_ROUTES]
    return _write_saved_routes(username, routes)


def remove_saved_route(username: str, label: str) -> bool:
    account = get_account(username)
    if not account:
        return False
    routes = [r for r in account["saved_routes"] if r.get("label") != label]
    return _write_saved_routes(username, routes)


# --------------------------------------------------------------------------
# Applying an account's saved defaults onto the sidebar's own widget state
# --------------------------------------------------------------------------
def apply_account_to_session(username: str, city_key: str, zip_key: str, profile_key_prefix: str,
                              zip_city_context_key: str = None):
    """Push a just-logged-in (or just-signed-up) user's saved preferences
    into the sidebar's own widget state (by key) -- see
    user_profile.apply_location() for the identical pattern used by saved
    locations.

    IMPORTANT -- widget-key ordering: Streamlit raises a
    StreamlitAPIException ("... cannot be modified after widget ... is
    instantiated") if `st.session_state[key]` is written AFTER the widget
    with that key has already been drawn in the SAME script run. Call this
    function directly only from a point in app.py that runs BEFORE the
    city/ZIP/profile widgets are created (i.e. before `with st.sidebar:`).
    From anywhere else -- most notably the Home page's login form, which
    renders AFTER the sidebar -- use queue_apply_on_next_run() instead,
    which defers this exact call to the start of the NEXT run via
    consume_pending_apply().

    `zip_city_context_key`, when given, is also set to the applied
    home_city, for the same "don't let the sidebar's own city-changed
    reset immediately wipe this ZIP back out" reason documented in
    user_profile.apply_location().
    """
    account = get_account(username)
    if not account:
        return
    st.session_state[city_key] = account["home_city"]
    st.session_state[zip_key] = account["default_zip"]
    st.session_state[profile_key_prefix + "asthma"] = bool(account["profile"].get("asthma", False))
    st.session_state[profile_key_prefix + "wheelchair"] = bool(account["profile"].get("wheelchair", False))
    if zip_city_context_key:
        st.session_state[zip_city_context_key] = account["home_city"]


PENDING_APPLY_KEY = "_pending_account_username"


def queue_apply_on_next_run(username: str):
    """Record that `username`'s saved city/ZIP/profile should be pushed
    onto the sidebar's widget keys at the START of the next script run,
    before those widgets exist. Call this (not apply_account_to_session
    directly) from anywhere that might run after the sidebar has already
    rendered this turn -- e.g. the Home page's login form -- then call
    `st.rerun()`. app.py calls consume_pending_apply() once, at the very
    top of every run, to actually perform the deferred write."""
    st.session_state[PENDING_APPLY_KEY] = username


def consume_pending_apply(city_key: str, zip_key: str, profile_key_prefix: str,
                           zip_city_context_key: str = None) -> bool:
    """Call this ONCE, at the very top of app.py, before any sidebar
    widget is created. Applies (and clears) a pending
    queue_apply_on_next_run() request, if any. Returns True if a pending
    request was found and applied."""
    username = st.session_state.pop(PENDING_APPLY_KEY, None)
    if username and get_account(username):
        apply_account_to_session(username, city_key, zip_key, profile_key_prefix, zip_city_context_key)
        return True
    return False
