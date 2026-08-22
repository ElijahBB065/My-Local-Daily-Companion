"""
pollen.py
A simulated daily Pollen Index, rounding out the "how should I plan my
day" picture alongside real transit and EPA-formula air quality data.

There's no broadly available free real-time pollen API in the way OpenAQ
covers air quality, so -- same honesty pattern as the rest of this app --
this is clearly-labeled SIMULATED data. It isn't random noise, though: the
base level follows a realistic Northern Hemisphere seasonal curve (tree
pollen peaks in spring, grass in early summer, ragweed/weed in late
summer/early fall, mostly mold in winter), and it's deterministic per
city + ZIP + calendar day, so it reads as "today's forecast" rather than
reshuffling every time the page reloads -- but it DOES change from one
real day to the next, which is the honest behavior for something that
genuinely varies daily in real life (unlike, say, a transit line's typical
delay pattern, which is stable shape-wise).

Uses the same 0-12 scale as real pollen indices (e.g. Pollen.com / the
National Allergy Bureau).
"""

from datetime import datetime

import numpy as np

from cities import stable_seed

POLLEN_CATEGORIES = [
    (2.4, "Low", "#0ca30c", "🟢"),
    (4.8, "Moderate", "#d4b106", "🟡"),
    (7.2, "High", "#e8720c", "🟠"),
    (9.6, "Very High", "#d03b3b", "🔴"),
    (12.01, "Extreme", "#7e0023", "🟤"),
]

# month -> (dominant allergen, seasonal base level on the 0-12 scale)
_MONTH_PROFILE = {
    1: ("Mold spores", 1.5), 2: ("Mold spores", 1.8),
    3: ("Tree pollen", 6.5), 4: ("Tree pollen", 8.0),
    5: ("Grass pollen", 6.5), 6: ("Grass pollen", 5.5), 7: ("Grass pollen", 3.5),
    8: ("Ragweed / weed pollen", 6.0), 9: ("Ragweed / weed pollen", 7.0), 10: ("Ragweed / weed pollen", 5.0),
    11: ("Mold spores", 2.5), 12: ("Mold spores", 1.5),
}

ADVICE = {
    "Low": "Great day to be outside, even with seasonal allergies.",
    "Moderate": "Mild symptoms are possible if you're sensitive -- keep antihistamines handy.",
    "High": "Consider limiting long outdoor stretches if allergies affect you.",
    "Very High": "Sensitive folks should minimize outdoor time and keep windows closed.",
    "Extreme": "Best kept mostly indoors today if allergies affect you -- a rough day to be out.",
}


def _category_for(value: float) -> tuple:
    for cutoff, label, color, emoji in POLLEN_CATEGORIES:
        if value <= cutoff:
            return label, color, emoji
    return POLLEN_CATEGORIES[-1][1:]


def simulate_pollen(city: str, zip_code: str, now: datetime = None) -> dict:
    """Today's simulated pollen reading for this city/ZIP -- deterministic
    per (city, zip, calendar day) so it holds steady across reruns on the
    same day but moves with the real season and the real date."""
    now = now or datetime.now()
    allergen, base = _MONTH_PROFILE[now.month]
    seed = stable_seed(city, zip_code or "", "pollen", now.strftime("%Y-%m-%d"))
    rng = np.random.default_rng(seed)
    value = float(np.clip(base + rng.normal(0, 1.3), 0.0, 12.0))
    category, color, emoji = _category_for(value)
    return {
        "value": round(value, 1),
        "category": category,
        "color": color,
        "emoji": emoji,
        "dominant_allergen": allergen,
        "advice": ADVICE[category],
        "source": "simulated",
        "as_of": now,
    }
