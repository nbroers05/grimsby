"""Needs and feeling. Pure numbers, no LLM.

Needs run from 0 (met) to 1 (pressing) and creep up every tick at their own speed.
Mood and energy run from -1 to 1.
"""

from __future__ import annotations

NEEDS = ("rest", "curiosity", "social", "expression", "quiet", "hunger")

# rise per tick (one tick = 90 real seconds = 12 world minutes)
RISE = {
    "rest": 0.008,
    "curiosity": 0.020,
    "social": 0.012,
    "expression": 0.016,
    "quiet": 0.014,
    "hunger": 0.013,          # Pino's fullness, the other way round: empty after ~60 ticks (12 world hours)
}
REST_TIRED = 0.030        # extra rest rise per tick at energy -1 (scales linearly)
REST_NIGHT = 0.012        # extra rest rise per tick during world night
ENERGY_AWAKE = -0.004     # being awake costs a little energy on top of what actions cost
ENERGY_HUNGRY = -0.006    # ...and more on an empty stomach
MOOD_BASELINE = -0.05     # he is a crow of dry temperament
MOOD_PULL = 0.03          # share of the distance to the baseline mood that closes every tick
MOOD_PRESSING = 0.012     # mood drop per tick for each need above PRESSING
PRESSING = 0.75


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def fresh() -> dict:
    return {"needs": {n: 0.0 for n in NEEDS}, "mood": 0.0, "energy": 0.5}


def rise(s: dict, night: bool, asleep: bool) -> None:
    """Needs creep up. Asleep, everything but rest rises at a quarter of the speed."""
    for n in NEEDS:
        s["needs"].setdefault(n, 0.3)          # a need added later (hunger) starts half-way, not at zero
        r = RISE[n]
        if n == "rest":
            r += REST_TIRED * max(0.0, -s["energy"]) + (REST_NIGHT if night else 0.0)
            if asleep:
                r = 0.0
        elif asleep:
            r *= 0.25          # = actions.RISE_ASLEEP_SHARE
        s["needs"][n] = clamp(s["needs"][n] + r, 0.0, 1.0)
    if not asleep:
        hungry = ENERGY_HUNGRY if s["needs"]["hunger"] > PRESSING else 0.0
        s["energy"] = clamp(s["energy"] + ENERGY_AWAKE + hungry, -1.0, 1.0)


def drift_mood(s: dict) -> None:
    s["mood"] += (MOOD_BASELINE - s["mood"]) * MOOD_PULL
    pressing = sum(1 for v in s["needs"].values() if v > PRESSING)
    s["mood"] = clamp(s["mood"] - MOOD_PRESSING * pressing, -1.0, 1.0)


def relieve(s: dict, relief: dict, share: float) -> float:
    """Lower needs by `share` of the action's relief. Returns how much need was actually met."""
    met = 0.0
    for n, amount in relief.items():
        before = s["needs"][n]
        s["needs"][n] = clamp(before - amount * share, 0.0, 1.0)
        met += before - s["needs"][n]
    return met


def burden(s: dict, side: dict, share: float) -> None:
    """Some actions make another need grow (being social makes him want quiet)."""
    for n, amount in side.items():
        s["needs"][n] = clamp(s["needs"][n] + amount * share, 0.0, 1.0)
