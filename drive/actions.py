"""Grimsby's fixed list of actions: what each one needs, what it does to him, where it happens.

relief : how much each need drops over the whole action (needs run 0..1)
side   : needs that grow from doing it
energy : energy change per tick while doing it
ticks  : how long it takes (sleep is open-ended, see engine.wake_up)
fail   : chance it goes wrong in the simulation (live, the real outcome decides: a search without results,
         an SVG that will not parse, Derek not being there, Pino not answering)
places : POI categories from world/poi.json (must be in SPOT_CATEGORIES of world/build_world.py), or "home"
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    name: str
    doing: str
    places: tuple[str, ...]
    ticks: int
    relief: dict
    side: dict = field(default_factory=dict)
    energy: float = 0.0
    fail: float = 0.0
    min_energy: float = -1.0       # too tired below this
    per_real_day: int = 0          # 0 = no limit
    min_gap_hours: float = 0.0     # real hours between two goes
    mood_ok: float = 0.0           # extra mood when it works, beyond what meeting needs gives


ACTIONS: dict[str, Action] = {a.name: a for a in [
    Action("search", "looking something up at the library", ("library",), 3,
           {"curiosity": 0.55, "quiet": 0.05}, energy=-0.025, fail=0.15, min_energy=-0.5),
    Action("read_back", "re-reading old diary pages", ("home",), 2,
           {"curiosity": 0.20, "quiet": 0.25, "expression": 0.10}, energy=-0.005),
    Action("diary", "writing in his diary on a park bench", ("bench",), 3,
           {"expression": 0.50, "quiet": 0.25}, energy=-0.015, fail=0.03),
    Action("draw", "drawing something", ("church", "windmill", "artwork", "fountain"), 4,
           {"expression": 0.55}, energy=-0.03, fail=0.12, min_energy=-0.4, mood_ok=0.03),
    Action("wander", "flying about town", ("bench", "church", "windmill", "artwork", "fountain", "library"), 3,
           {"curiosity": 0.25, "social": 0.20}, side={"quiet": 0.08}, energy=-0.03, min_energy=-0.6),
    Action("pigeons", "keeping an eye on the pigeons by the fountain", ("fountain", "artwork"), 3,
           {"social": 0.45}, side={"quiet": 0.15}, energy=-0.02, fail=0.25, min_energy=-0.6),
    Action("neighbour", "checking on Pino next door", ("home",), 1,
           {"social": 0.35, "curiosity": 0.20}, energy=-0.005, fail=0.10, per_real_day=3, min_gap_hours=4),
    Action("sit", "sitting still on the station roof", ("home",), 2,
           {"rest": 0.08, "quiet": 0.40}, energy=+0.05),
    Action("tidy", "tidying his hoard", ("home",), 3,
           {"quiet": 0.20, "expression": 0.15}, energy=-0.01, mood_ok=0.03),
    Action("sleep", "asleep on the station roof", ("home",), 0,
           {"rest": 0.07, "quiet": 0.04}, energy=+0.05),   # sleep relief/energy are per tick
    Action("idle", "watching the trains go by", ("home",), 1,
           {"quiet": 0.02, "rest": 0.02}, energy=+0.02),
]}

SLEEP_MIN_REST = 0.55          # sleepy enough to go to sleep by day
SLEEP_MIN_REST_NIGHT = 0.12    # ...and at night
SLEEP_EXHAUSTED = -0.5         # or when energy is this low
SLEEP_NIGHT_PULL = 0.30        # night makes sleep more attractive
RISE_ASLEEP_SHARE = 0.25       # asleep, needs other than rest rise at this share of their speed
IDLE_SCORE = 0.08              # an action has to beat doing nothing

# How places feel, hidden in the world. He does not know these numbers; his beliefs have to find them out
# (and may get them wrong: noise makes superstitions possible). Keys: a place category, or (action, place).
PLACE_FEEL = {
    "windmill": 0.02,                 # wind, a view, nobody about
    "fountain": -0.01,                # pigeons, children, wet
    ("draw", "windmill"): 0.02,
    ("diary", "bench"): 0.01,
    ("pigeons", "fountain"): -0.02,   # Derek's territory
    ("wander", "church"): 0.015,
}

