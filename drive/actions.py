"""Grimsby's fixed list of actions: what each one needs, what it does to him, where it happens.

relief : how much each need drops over the whole action (needs run 0..1)
side   : needs that grow from doing it
energy : energy change per tick while doing it
ticks  : how long it takes (sleep is open-ended, see engine.wake_up)
fail   : chance it goes wrong in the simulation (live, the real outcome decides: a search without results,
         an SVG that will not parse, Derek not being there, Pino not answering)
Where an action can happen is in world/places.json (each place lists its actions; see world.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    name: str
    doing: str
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
    Action("search", "looking something up", 3,
           {"curiosity": 0.55, "quiet": 0.05}, energy=-0.025, fail=0.15, min_energy=-0.5),
    Action("read_back", "re-reading old diary pages", 2,
           {"curiosity": 0.20, "quiet": 0.25, "expression": 0.10}, energy=-0.005),
    Action("diary", "writing in his diary", 3,
           {"expression": 0.50, "quiet": 0.25}, energy=-0.015, fail=0.03),
    Action("draw", "drawing something", 4,
           {"expression": 0.55}, energy=-0.03, fail=0.12, min_energy=-0.4, mood_ok=0.03),
    Action("wander", "having a look around", 2,          # the flight there is part of it (see engine)
           {"curiosity": 0.25, "social": 0.20}, side={"quiet": 0.08}, energy=-0.02, min_energy=-0.6),
    Action("pigeons", "keeping an eye on the pigeons", 3,
           {"social": 0.45}, side={"quiet": 0.15}, energy=-0.02, fail=0.25, min_energy=-0.6),
    Action("neighbour", "checking on Pino next door", 1,
           {"social": 0.35, "curiosity": 0.20}, energy=-0.005, fail=0.10, per_real_day=3, min_gap_hours=4),
    Action("sit", "sitting still", 2,
           {"rest": 0.08, "quiet": 0.40}, energy=+0.05),
    Action("tidy", "tidying his hoard", 3,
           {"quiet": 0.20, "expression": 0.15}, energy=-0.01, mood_ok=0.03),
    Action("sleep", "asleep", 0,
           {"rest": 0.07, "quiet": 0.04}, energy=+0.05),   # sleep relief/energy are per tick
    Action("idle", "watching the world go by", 1,
           {"quiet": 0.02, "rest": 0.02}, energy=+0.02),
]}

SLEEP_MIN_REST = 0.55          # sleepy enough to go to sleep by day
SLEEP_MIN_REST_NIGHT = 0.12    # ...and at night
SLEEP_EXHAUSTED = -0.5         # or when energy is this low
SLEEP_NIGHT_PULL = 0.30        # night makes sleep more attractive
RISE_ASLEEP_SHARE = 0.25       # asleep, needs other than rest rise at this share of their speed
IDLE_SCORE = 0.08              # an action has to beat doing nothing

# How places feel lives in world/places.json now (feel, feel_for), hidden from him like before.
