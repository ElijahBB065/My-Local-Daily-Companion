"""
community.py
Tab 3: Local Community Hub -- town/neighborhood-specific message boards
where residents post updates across a few categories and upvote ("Me Too")
the ones that matter, plus a digest panel blending the crowd's top issues
with this run's own official transit/AQI/pollen readings.

HONESTY NOTE -- same pattern as accounts.py, transit.py's community reports,
and user_profile.py's saved locations: everything here lives ONLY in
`st.session_state`, in server-side memory, for this session. That's enough
to demo "post an issue -> see it appear -> someone else upvotes it" within
one browser tab, but there's no real database and nothing here is shared
across different browsers, devices, or actual users. A real deployment
would swap COMMUNITIES_KEY's dict for a small database table (see the
README's "Extending it" section) so posts and communities survive a
restart and are visible to everyone, not just your own session.

A "community" is keyed by (city, neighborhood) -- e.g. "Chelsea Community"
in New York, NY -- so it lines up with the exact neighborhood the sidebar
already resolves from the selected city/ZIP (cities.lookup_neighborhood).
Whoever is logged in (or a stable per-session guest id if not) can create
their own town's community if it doesn't exist yet, post to it, upvote
other residents' posts, or browse and join OTHER towns' communities from a
searchable list without changing their own saved city/ZIP.
"""

import uuid
from datetime import datetime

import streamlit as st

COMMUNITIES_KEY = "communities_store"
GUEST_ID_KEY = "_community_guest_id"
VIEW_OVERRIDE_KEY = "_community_view_override"

CATEGORIES = [
    {"key": "transit", "label": "🚌 Transit / Road Delays", "color": "#2a78d6"},
    {"key": "air_pollen", "label": "🌬️ Air Quality / Pollen Spotting", "color": "#1baf7a"},
    {"key": "infrastructure", "label": "🛠️ Local Infrastructure Issues", "color": "#e8720c"},
    {"key": "chat", "label": "💬 General Town Chat", "color": "#4a3aa7"},
]
CATEGORY_KEYS = [c["key"] for c in CATEGORIES]
CATEGORY_LABELS = {c["key"]: c["label"] for c in CATEGORIES}
CATEGORY_COLORS = {c["key"]: c["color"] for c in CATEGORIES}


# --------------------------------------------------------------------------
# State + identity
# --------------------------------------------------------------------------
def init_community_state():
    if COMMUNITIES_KEY not in st.session_state:
        st.session_state[COMMUNITIES_KEY] = {}


def _slugify(text: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in (text or ""))
    return "-".join(cleaned.split()) or "town"


def community_id_for(city: str, neighborhood: str) -> str:
    """A stable id for the (city, neighborhood) pair -- this is what makes
    routing "automatic": the same city/neighborhood a user's profile
    already resolves to (via cities.lookup_neighborhood) always maps to
    the same community, with no separate community-picker step needed."""
    return _slugify(f"{neighborhood}-{city}")


def get_guest_id() -> str:
    """A stable per-session id for anyone posting/upvoting without an
    account -- so a guest's own upvote toggles correctly across reruns
    (and doesn't silently count as a different person every rerun), while
    still being honest that it's a session-only guest identity, not a
    real account."""
    if GUEST_ID_KEY not in st.session_state:
        st.session_state[GUEST_ID_KEY] = f"Guest-{uuid.uuid4().hex[:5]}"
    return st.session_state[GUEST_ID_KEY]


def current_identity(logged_in_user: str = None) -> str:
    return logged_in_user or get_guest_id()


# --------------------------------------------------------------------------
# Communities
# --------------------------------------------------------------------------
def get_community(community_id: str) -> dict:
    init_community_state()
    return st.session_state[COMMUNITIES_KEY].get(community_id)


def list_communities() -> list:
    init_community_state()
    return sorted(st.session_state[COMMUNITIES_KEY].values(), key=lambda c: c["name"].lower())


def create_community(city: str, neighborhood: str, created_by: str, now: datetime = None) -> str:
    """Create (or silently return) the community for this city/neighborhood,
    with a friendly welcome post so a brand-new community isn't just a
    blank page -- same "discoverable, not empty" pattern used for the
    default saved location in user_profile.py."""
    init_community_state()
    cid = community_id_for(city, neighborhood)
    if cid in st.session_state[COMMUNITIES_KEY]:
        return cid
    now = now or datetime.now()
    st.session_state[COMMUNITIES_KEY][cid] = {
        "id": cid,
        "name": f"{neighborhood} Community",
        "city": city,
        "neighborhood": neighborhood,
        "created_by": created_by,
        "members": {created_by},
        "posts": [],
    }
    add_post(
        cid, author="Local Daily Companion", category="chat",
        text=f"Welcome to the {neighborhood} Community! This is the very first post here — "
             "share a transit delay, an air quality/pollen observation, a local infrastructure "
             "issue, or just say hello.",
        now=now,
    )
    return cid


def join_community(community_id: str, identity: str) -> bool:
    community = get_community(community_id)
    if not community:
        return False
    community["members"].add(identity)
    return True


def is_member(community_id: str, identity: str) -> bool:
    community = get_community(community_id)
    return bool(community and identity in community["members"])


# --------------------------------------------------------------------------
# Posts + upvotes
# --------------------------------------------------------------------------
def add_post(community_id: str, author: str, category: str, text: str, now: datetime = None) -> bool:
    community = get_community(community_id)
    text = (text or "").strip()
    if not community or not text or category not in CATEGORY_KEYS:
        return False
    now = now or datetime.now()
    community["posts"].insert(0, {
        "id": uuid.uuid4().hex,
        "category": category,
        "author": author,
        "text": text,
        "timestamp": now,
        "upvotes": set(),
    })
    return True


def toggle_upvote(community_id: str, post_id: str, identity: str) -> bool:
    """Returns the post's new upvoted-by-this-identity state (True/False)."""
    community = get_community(community_id)
    if not community:
        return False
    for post in community.get("posts", []):
        if post.get("id") == post_id:
            upvotes = post.setdefault("upvotes", set())
            if identity in upvotes:
                upvotes.discard(identity)
                return False
            upvotes.add(identity)
            return True
    return False


def top_issues(community_id: str, n: int = 3) -> list:
    """The top N crowd-reported ISSUES (excludes General Town Chat, which
    isn't really an 'issue') by upvote count, ties broken by most recent."""
    community = get_community(community_id)
    if not community:
        return []
    issue_posts = [p for p in community.get("posts", []) if p.get("category") != "chat"]
    return sorted(issue_posts, key=lambda p: (len(p.get("upvotes", set())), p.get("timestamp")), reverse=True)[:n]


def official_alerts(transit_status: dict = None, aqi_reading: dict = None, pollen_reading: dict = None) -> list:
    """Short, plain-language alert strings from this run's ALREADY-COMPUTED
    official readings (the same transit_status/aqi_reading/pollen_reading
    app.py hands to the outlook banner) -- never re-fetched or re-simulated
    here, so the digest panel can't disagree with the rest of the page."""
    alerts = []
    transit_status = transit_status or {}
    aqi_reading = aqi_reading or {}
    pollen_reading = pollen_reading or {}

    level = transit_status.get("level")
    if level == "major":
        alerts.append(f"🔴 Transit: significant delays ({transit_status.get('delay_min', '—')} min avg).")
    elif level == "minor":
        alerts.append(f"🟡 Transit: minor delays ({transit_status.get('delay_min', '—')} min avg).")
    outages = transit_status.get("elevator_outages", 0) or 0
    if outages:
        alerts.append(f"🛗 {outages} elevator outage{'s' if outages != 1 else ''} reported right now.")

    aqi_label = aqi_reading.get("label")
    if aqi_label and aqi_label not in ("Good", "No data"):
        alerts.append(f"🌬️ Air quality: {aqi_label} (AQI {aqi_reading.get('aqi', '—')}).")

    pollen_category = pollen_reading.get("category")
    if pollen_category and pollen_category not in ("Low", "No data"):
        alerts.append(f"🌼 Pollen: {pollen_category} — {pollen_reading.get('dominant_allergen', '')}".rstrip(" —"))

    return alerts


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
def _post_card(post: dict, community_id: str, identity: str):
    post_id = post.get("id", "")
    category = post.get("category", "chat")
    color = CATEGORY_COLORS.get(category, "#898781")
    label = CATEGORY_LABELS.get(category, "General")
    upvotes = post.get("upvotes", set())
    upvoted = identity in upvotes
    count = len(upvotes)
    try:
        ts = f"{post['timestamp']:%b %d — %I:%M %p}"
    except Exception:
        ts = ""

    st.markdown(
        f"""
        <div class="report-card" style="--accent:{color}">
            <div class="rc-top"><span>{label}</span><span>{post.get('author', 'Someone')}</span></div>
            <div class="rc-details">{post.get('text', '')}</div>
            <div class="rc-meta">{ts}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    btn_col, _ = st.columns([1, 4], gap="small")
    with btn_col:
        btn_label = f"✅ Me Too · {count}" if upvoted else f"👍 Me Too · {count}"
        # on_click keeps the upvote feeling instant -- one state transition per click,
        # no intermediate render of the pre-toggle count.
        st.button(btn_label, key=f"upvote_{community_id}_{post_id}", use_container_width=True,
                   on_click=toggle_upvote, args=(community_id, post_id, identity))


def _digest_item(text: str, accent: str = "#898781"):
    st.markdown(
        f"""
        <div class="alert-card" style="--accent:{accent}">
            <div class="alert-body">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_create_prompt(city: str, neighborhood: str, identity: str, now: datetime = None):
    st.markdown(
        f"""
        <div class="companion-banner">
        📭 There's no <b>{neighborhood} Community</b> yet for {city} — be the first to start it, or
        browse other towns' communities below.
        </div>
        """,
        unsafe_allow_html=True,
    )

    def _create_and_clear_override():
        create_community(city, neighborhood, created_by=identity, now=now)
        st.session_state.pop(VIEW_OVERRIDE_KEY, None)

    st.button(f"➕ Create {neighborhood} Community", type="primary", on_click=_create_and_clear_override)


def render_browse_and_join(active_id: str, identity: str, default_label: str):
    with st.expander("🔍 Browse or join other town communities"):
        communities = list_communities()
        if not communities:
            st.caption("No communities exist yet across any town — create yours above to be the first.")
            return
        search = st.text_input(
            "Search by town or neighborhood name", key="community_search",
            placeholder="e.g. Glen Ridge, Chelsea, Denver...",
        )
        search_lower = search.strip().lower()
        for community in communities:
            name = community.get("name", "Unnamed Community")
            c_city = community.get("city", "")
            c_id = community.get("id", "")
            haystack = f"{name} {c_city} {community.get('neighborhood', '')}".lower()
            if search_lower and search_lower not in haystack:
                continue
            member_count = len(community.get("members", set()))
            post_count = len(community.get("posts", []))
            is_active = c_id == active_id
            view_col, join_col, meta_col = st.columns([2, 2, 3], gap="small")
            with view_col:
                st.button(
                    f"{'📍 Viewing' if is_active else '👀 View'} — {name}",
                    key=f"view_{c_id}", use_container_width=True, disabled=is_active,
                    on_click=lambda cid=c_id: st.session_state.__setitem__(VIEW_OVERRIDE_KEY, cid),
                )
            with join_col:
                already = identity in community.get("members", set())
                st.button(
                    "🤝 Joined" if already else "🤝 Join",
                    key=f"join_{c_id}", use_container_width=True, disabled=already,
                    on_click=lambda cid=c_id: join_community(cid, identity),
                )
            with meta_col:
                st.caption(f"{c_city} · {member_count} member(s) · {post_count} post(s)")

        if st.session_state.get(VIEW_OVERRIDE_KEY):
            st.button(f"↩️ Back to my town ({default_label})", on_click=lambda: st.session_state.pop(VIEW_OVERRIDE_KEY, None))


def render_message_board(community: dict, identity: str):
    community_id = community.get("id", "")
    members = community.get("members", set())
    posts_all = community.get("posts", [])
    st.markdown(f"#### 📋 {community.get('name', 'Community')} message board")
    st.caption(f"{len(members)} member(s) · {len(posts_all)} post(s) this session.")

    with st.form(f"new_post_{community_id}", clear_on_submit=True):
        category = st.selectbox(
            "Category", options=CATEGORY_KEYS, format_func=lambda k: CATEGORY_LABELS[k],
        )
        text = st.text_area("What's going on?", placeholder="e.g. Elevator at Main St station has been out since 8am...")
        submitted = st.form_submit_button("📮 Post to the community", use_container_width=True, type="primary")
        if submitted:
            if add_post(community_id, author=identity, category=category, text=text):
                st.success("Posted!")
                st.rerun()
            else:
                st.warning("Write something before posting.")

    filter_choice = st.radio(
        "Filter", options=["All"] + CATEGORY_KEYS, horizontal=True,
        format_func=lambda k: "All" if k == "All" else CATEGORY_LABELS[k],
        key=f"community_filter_{community_id}",
    )
    posts = posts_all if filter_choice == "All" else [p for p in posts_all if p.get("category") == filter_choice]

    if not posts:
        st.caption("No posts in this category yet — be the first.")
    for post in posts:
        _post_card(post, community_id, identity)


def render_digest(community: dict, transit_status: dict, aqi_reading: dict, pollen_reading: dict):
    st.markdown("#### 📊 Community & Alert Digest")

    st.markdown("**🔥 Top crowd-reported issues**")
    issues = top_issues(community.get("id", ""), n=3)
    if not issues:
        _digest_item("No crowd-reported issues yet — the community's first reports will show up here.", "#898781")
    else:
        for post in issues:
            category = post.get("category", "chat")
            text = post.get("text", "")
            label = CATEGORY_LABELS.get(category, "General")
            snippet = text if len(text) <= 90 else text[:87] + "…"
            upvote_count = len(post.get("upvotes", set()))
            _digest_item(f"{label} · 👍 {upvote_count}<br>{snippet}", CATEGORY_COLORS.get(category, "#898781"))

    st.markdown("**📡 Official alerts right now**")
    alerts = official_alerts(transit_status, aqi_reading, pollen_reading)
    if not alerts:
        _digest_item("✅ No official transit, air quality, or pollen alerts right now.", "#0ca30c")
    else:
        for a in alerts:
            _digest_item(a, "#c98500")


def render_community_tab(city: str, neighborhood: str, zip_code: str = None, transit_status: dict = None,
                          aqi_reading: dict = None, pollen_reading: dict = None, logged_in_user: str = None,
                          now: datetime = None):
    """Entry point called from app.py's third tab. `city`/`neighborhood` are
    the SAME values already resolved in the sidebar from the user's saved
    profile/ZIP -- that's what makes routing to "your" community automatic,
    with no separate community picker required. transit_status/aqi_reading/
    pollen_reading are the SAME already-computed dicts the outlook banner
    uses, threaded through here only to build the digest panel, never
    re-fetched or re-simulated."""
    init_community_state()
    identity = current_identity(logged_in_user)
    default_id = community_id_for(city, neighborhood)
    active_id = st.session_state.get(VIEW_OVERRIDE_KEY) or default_id

    st.markdown(
        f"""
        <div class="companion-banner">
        🏘️ <b>Local Community Hub</b> — a message board for {neighborhood} residents to report transit
        delays, air quality/pollen sightings, and local infrastructure issues, upvote the ones that
        matter, and chat. Posts here are visible to everyone in this browser session — see the note in
        the README for how this would connect to a real, shared community backend.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_id != default_id:
        st.info(f"You're browsing another town's community. Your own saved town's community is **{neighborhood} Community**.")

    active_community = get_community(active_id)
    if active_community is None and active_id == default_id:
        render_create_prompt(city, neighborhood, identity, now=now)
        render_browse_and_join(active_id, identity, default_label=neighborhood)
        return
    if active_community is None:
        # A view override pointed at a community that no longer exists (shouldn't normally happen) --
        # fall back to the user's own town instead of showing a dead end.
        st.session_state.pop(VIEW_OVERRIDE_KEY, None)
        st.rerun()
        return

    if not is_member(active_id, identity) and active_id == default_id:
        # Auto-join residents to their OWN town's community -- no extra click needed for the
        # community that's automatically theirs; joining OTHER towns still requires a click
        # (see render_browse_and_join), which is what makes "join" a meaningful action there.
        join_community(active_id, identity)

    board_col, digest_col = st.columns([2, 1], gap="medium")
    with board_col:
        try:
            render_message_board(active_community, identity)
        except Exception:
            st.warning("The message board is temporarily unavailable — your posts and upvotes are safe, try refreshing.")
    with digest_col:
        try:
            render_digest(active_community, transit_status, aqi_reading, pollen_reading)
        except Exception:
            st.warning("The digest panel is temporarily unavailable.")

    render_browse_and_join(active_id, identity, default_label=neighborhood)
