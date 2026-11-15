"""Brain v3, phase 1: learning from surprise. Pure numbers, no LLM.

1. Prediction error (dopamine-like). Per "action@place" (and "action@*") an expected value V. Before an action
   starts, V is stored as his expectation; afterwards outcome = dmood + 0.5 * met, delta = outcome - V, and
   V += ALPHA * delta. Beliefs and facts are the wording of V (beliefs.py).
2. Habituation and novelty. Per stimulus ("place:<id>", "topic:<text>") a habituation h from 0 to 1: +0.2 per
   encounter, slowly back down every tick. What he is used to gives less: relief x (1 - 0.5 h). A place he has
   never been to (or not for a long time) gives a novelty bonus on curiosity.
3. Emotion on two axes. Valence is his mood (-1..1); arousal (0..1) goes up with surprise, travel, visitors and
   frights, down with sitting still and sleep. Performance follows an inverted U (Yerkes-Dodson): searching and
   drawing work best at middling arousal. Code picks an emotion word from valence x arousal; the model only
   ever gets that word.

Everything lives in the character's own state (state["character_id"]), so a second character gets its own.
"""

from __future__ import annotations

from datetime import datetime

# ---- prediction error
ALPHA = 0.15                   # learning rate
ALPHA_REPLAY = 0.0             # learning rate when a memory is replayed in his sleep (phase 2, sleep.py). Off: at
                               # 0.05 V moved ~0.01 per night and 6 seeds x 1000 ticks showed no visible change
                               # (same 48 action@place, shares within 2 points). Code kept; the replay choice stays.
MET_WEIGHT = 0.5               # outcome = dmood + MET_WEIGHT * met
VALUE_PULL = 0.5               # utility per unit of V above his average (beliefs.bonus); 0.8 makes him repetitive
VALUE_PULL_MAX = 0.08          # ...capped, so learning steers but needs still decide

# ---- habituation and novelty
HAB_STEP = 0.2                 # h += this per encounter
HAB_DECAY = 0.006              # h -= this per tick (an encounter fades in ~33 ticks = 7 world hours)
HAB_RELIEF = 0.5               # relief x (1 - HAB_RELIEF * h)
NOVEL_HOURS = 6.0              # real hours away before a place is fully new again (= 2 world days)
NOVEL_PULL = 0.12              # choice bonus: x novelty x curiosity need
NOVEL_RELIEF = 0.15            # curiosity met on arriving somewhere new, x novelty
NO_HAB = ("sleep", "idle")

# ---- arousal
AROUSAL_START = 0.3
AROUSAL_REST = 0.35            # where it drifts to while he is up and about
AROUSAL_STILL = 0.2            # ...while sitting still or idling
AROUSAL_SLEEP = 0.08           # ...while asleep
AROUSAL_DRIFT = 0.08           # share of the distance to that target closed per tick
AROUSAL_SURPRISE = 0.35        # += |delta| x this when an action ends
AROUSAL_TRAVEL = 0.02          # per tick of flying
AROUSAL_NOVEL = 0.05           # arriving somewhere new, x novelty
AROUSAL_VISITOR = 0.1          # a visitor's note
AROUSAL_FRIGHT = 0.35          # a fright (a whistle, later)
STILL = ("sit", "idle")
YD_ACTIONS = ("search", "draw")
YD_BEST = 0.5                  # best arousal for performance
YD_DEPTH = 0.0                 # performance at arousal 0 or 1 = 1 - YD_DEPTH. Off: at 0.45 it changed nothing
                               # visible in the sim (~0.3 extra failures per 300 ticks). Try again once visitors
                               # and frights (WERELD 3-4) make arousal swing harder.

EMOTIONS = [                    # (min arousal, min valence, word); first match wins, top to bottom
    (0.6, 0.15, "excited"), (0.6, -0.15, "keyed up"), (0.6, -2, "agitated"),
    (0.3, 0.15, "content"), (0.3, -0.15, "even"), (0.3, -2, "irritable"),
    (0.0, 0.15, "calm"), (0.0, -0.15, "drowsy"), (0.0, -2, "listless"),
]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def setup(s: dict, character_id: str = "grimsby") -> None:
    """New fields for brain v3; old states get them on load."""
    s.setdefault("character_id", character_id)
    s.setdefault("values", {})
    s.setdefault("habit", {})
    s.setdefault("visits", {})
    s.setdefault("arousal", AROUSAL_START)


# ---------------------------------------------------------------- 1. prediction error

def value(s: dict, key: str) -> float:
    return s.get("values", {}).get(key, {}).get("V", 0.0)


def known(s: dict, key: str) -> bool:
    return s.get("values", {}).get(key, {}).get("n", 0) > 0


def average(s: dict) -> float:
    """His overall expectation: the mean V over actions (action@*), weighted by how often he did them."""
    vals = [v for k, v in s.get("values", {}).items() if k.endswith("@*") and v.get("n")]
    tot = sum(v["n"] for v in vals)
    return sum(v["V"] * v["n"] for v in vals) / tot if tot else 0.0


def learn(s: dict, done: dict, real: datetime) -> float:
    """After an action: update V for action@place and action@*. Returns delta (the prediction error)."""
    outcome = done["dmood"] + MET_WEIGHT * done["met"]
    delta = None
    for key in (f"{done['action']}@{done['place']}", f"{done['action']}@*"):
        v = s["values"].setdefault(key, {"V": 0.0, "n": 0, "fail": 0.0, "var": 0.0})
        d = outcome - v["V"]
        if delta is None:
            delta = d                                   # the place-specific surprise is the one he feels
        v["V"] = round(v["V"] + ALPHA * d, 5)
        v["var"] = round((1 - ALPHA) * (v.get("var", 0.0) + ALPHA * d * d), 6)   # how much outcomes vary (phase 3)
        v["n"] = round(v["n"] + 1, 3)
        v["fail"] = round(v.get("fail", 0.0) + (0 if done["ok"] else 1), 3)
        v["last"] = real.isoformat(timespec="seconds")
    done["outcome"], done["delta"] = round(outcome, 4), round(delta, 4)
    return delta


def replay(s: dict, key: str, outcome: float) -> float | None:
    """Phase 2: in a dream an old outcome comes back and V learns from it once more, more softly. Only V moves
    (the evidence count does not: nothing new happened). Returns the replayed prediction error."""
    v = s.get("values", {}).get(key)
    if not v:
        return None
    d = outcome - v["V"]
    v["V"] = round(v["V"] + ALPHA_REPLAY * d, 5)
    return d


def night_fade(s: dict, fade: float) -> None:
    """Evidence counts fade at night (V itself stays: it already weighs recent outcomes more)."""
    for v in s.get("values", {}).values():
        v["n"] = round(v["n"] * fade, 3)
        v["fail"] = round(v.get("fail", 0.0) * fade, 3)


def value_bonus(s: dict, action: str, place: str | None) -> float:
    """Utility from what he has learned: V of action@place above his average. Unknown = no push either way."""
    key = f"{action}@{place}" if place else f"{action}@*"
    if not known(s, key):
        key = f"{action}@*"
        if not known(s, key):
            return 0.0
    return clamp(VALUE_PULL * (value(s, key) - average(s)), -VALUE_PULL_MAX, VALUE_PULL_MAX)


# ---------------------------------------------------------------- 2. habituation and novelty

def habit(s: dict, stimulus: str) -> float:
    return s.get("habit", {}).get(stimulus, 0.0)


def encounter(s: dict, stimulus: str) -> None:
    s["habit"][stimulus] = round(min(1.0, habit(s, stimulus) + HAB_STEP), 4)


def decay_habits(s: dict) -> None:
    h = s.get("habit", {})
    for k in list(h):
        h[k] = round(h[k] - HAB_DECAY, 4)
        if h[k] <= 0:
            del h[k]


def relief_factor(s: dict, action: str, place: str) -> float:
    if action in NO_HAB:
        return 1.0
    return 1.0 - HAB_RELIEF * habit(s, "place:" + place)


def novelty(s: dict, place: str, real: datetime) -> float:
    last = s.get("visits", {}).get(place)
    away = 1.0 if not last else min(1.0, (real - datetime.fromisoformat(last)).total_seconds() / 3600 / NOVEL_HOURS)
    return away * (1.0 - habit(s, "place:" + place))


def novelty_pull(s: dict, place: str, real: datetime) -> float:
    return NOVEL_PULL * novelty(s, place, real) * s["needs"]["curiosity"]


def arrive(s: dict, place: str, action: str, real: datetime) -> float:
    """On arrival: novelty meets curiosity, then the place becomes a bit more familiar. Returns novelty."""
    nov = novelty(s, place, real)
    if action not in NO_HAB:
        s["needs"]["curiosity"] = clamp(s["needs"]["curiosity"] - NOVEL_RELIEF * nov, 0.0, 1.0)
        s["arousal"] = clamp(s["arousal"] + AROUSAL_NOVEL * nov, 0.0, 1.0)
        encounter(s, "place:" + place)
    s["visits"][place] = real.isoformat(timespec="seconds")
    return nov


# ---------------------------------------------------------------- 3. arousal and emotion

def arousal_tick(s: dict, doing: dict | None, flying: bool) -> None:
    a = s.get("arousal", AROUSAL_START)
    target = AROUSAL_REST
    if not flying and doing and doing["action"] == "sleep":
        target = AROUSAL_SLEEP
    elif not flying and doing and doing["action"] in STILL:
        target = AROUSAL_STILL
    a += (target - a) * AROUSAL_DRIFT
    if flying:
        a += AROUSAL_TRAVEL
    s["arousal"] = round(clamp(a, 0.0, 1.0), 4)


def surprise(s: dict, delta: float) -> None:
    s["arousal"] = round(clamp(s.get("arousal", AROUSAL_START) + AROUSAL_SURPRISE * abs(delta), 0.0, 1.0), 4)


def jolt(s: dict, amount: float) -> None:
    """Visitors (AROUSAL_VISITOR) and frights (AROUSAL_FRIGHT)."""
    s["arousal"] = round(clamp(s.get("arousal", AROUSAL_START) + amount, 0.0, 1.0), 4)


def performance(s: dict) -> float:
    """Inverted U: 1 at YD_BEST, 1 - YD_DEPTH at the extremes."""
    a = s.get("arousal", AROUSAL_START)
    return 1.0 - YD_DEPTH * ((a - YD_BEST) / 0.5) ** 2


def emotion(s: dict) -> str:
    a, v = s.get("arousal", AROUSAL_START), s["mood"]
    for min_a, min_v, word in EMOTIONS:
        if a >= min_a and v >= min_v:
            return word
    return "even"


def public(s: dict) -> dict:
    """For mind.json: the data the future 'brain scan' tab will draw (not shown on the site yet)."""
    vals = {k: {"V": round(v["V"], 3), "n": round(v["n"], 1)} for k, v in s.get("values", {}).items() if v.get("n")}
    return {"emotion": emotion(s), "valence": round(s["mood"], 3), "arousal": round(s.get("arousal", 0), 3),
            "average": round(average(s), 3), "values": vals,
            "habit": {k: round(h, 2) for k, h in s.get("habit", {}).items() if h >= 0.05}}
