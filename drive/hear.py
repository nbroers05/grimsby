"""Whistles (WERELD.md step 4): a visitor presses E somewhere on the island. If he is awake and it was close,
he hears it: a `noticed` event, a fright (arousal up), and it is on his mind for a moment. Nothing else: a whistle
is only a sound at a place, it never starts an action.

The site writes every whistle to Supabase (table whistles, supabase/whistles.sql); cloud.fetch_whistles reads the
new ones each tick.
"""

from __future__ import annotations

import math
from datetime import datetime

from . import attend, learn, world

HEAR_RADIUS = 25.0             # metres on the island (real metres: the 3D world, not FEEL_SCALE)
HEAR_SAL = 0.5                 # working-memory salience of a whistle
FRIGHT_GAP = 3                 # at most one fright per this many ticks, however many whistle


def nearest_place(x: float, z: float) -> str:
    return min(world.places().values(), key=lambda p: math.hypot(p["x"] - x, p["z"] - z))["id"]


def hear(s: dict, whistles: list[dict], here: tuple[float, float], real: datetime, feed) -> list[dict]:
    """Of these whistles, which does he hear? Applies the fright once. Returns what he heard."""
    d = s.get("doing")
    if d and (d["action"] == "sleep" or d.get("travel", 0) > 0):
        return []                                  # asleep he hears nothing; flying, the wind is louder
    heard = [w for w in whistles if math.hypot(w["x"] - here[0], w["z"] - here[1]) <= HEAR_RADIUS]
    if not heard:
        return []
    if s["ticks"] - s.get("fright_tick", -99) >= FRIGHT_GAP:
        learn.jolt(s, learn.AROUSAL_FRIGHT)
        s["fright_tick"] = s["ticks"]
    where = world.words(nearest_place(heard[-1]["x"], heard[-1]["z"]))
    many = "Someone whistled" if len(heard) == 1 else f"Someone whistled {len(heard)} times"
    feed(s, "noticed", f"{many} {where}. I nearly dropped everything.", real)
    attend.consider(s, [attend.item("seen:whistle", "seen", "a whistle", "someone just whistled close by, it made "
                                    "you jump", HEAR_SAL)])
    return heard
