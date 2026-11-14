"""One tick of Grimsby's life, decided entirely in code.

Per tick: needs rise, mood drifts, the current action progresses; when nothing is going on he picks the
next action by utility:

    score = sum(need * relief for each need the action meets)
          + belief bonus ("drawing on the windmill cheers me up")
          + a little noise
          - a small penalty for doing the same thing again, or a lot lately

`outcome(action_name, place)` decides whether an action worked. The simulation rolls dice; live, it is the real result.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Callable

from . import beliefs, clock, needs
from .actions import ACTIONS, PLACE_FEEL, IDLE_SCORE, SLEEP_EXHAUSTED, SLEEP_NIGHT_PULL, SLEEP_MIN_REST, SLEEP_MIN_REST_NIGHT, Action

NOISE = 0.06
REPEAT_PENALTY = 0.08          # same as the last action
LATELY_PENALTY = 0.03          # per time it was done in the last LATELY actions
LATELY = 8
FAIL_MOOD = -0.10
OK_MOOD = 0.01
MET_MOOD = 0.08                # mood gain per unit of need met (shrinks as mood nears 1)
PLACE_NOISE = 0.015
SLEEP_MAX_TICKS = 60           # 60 ticks = 12 world hours = 1.5 real hours


def new_state() -> dict:
    s = needs.fresh()
    s.update({"doing": None, "history": [], "done_at": {}})
    return s


def allowed(a: Action, s: dict, real: datetime) -> bool:
    if s["energy"] < a.min_energy:
        return False
    if a.name == "sleep":
        r = s["needs"]["rest"]
        return (r >= (SLEEP_MIN_REST_NIGHT if clock.is_night(real) else SLEEP_MIN_REST)
                or s["energy"] <= SLEEP_EXHAUSTED)
    times = [datetime.fromisoformat(t) for t in s["done_at"].get(a.name, [])]
    if a.per_real_day and sum(1 for t in times if real - t < timedelta(days=1)) >= a.per_real_day:
        return False
    if a.min_gap_hours and times and real - times[-1] < timedelta(hours=a.min_gap_hours):
        return False
    return True


def belief_bonus(a: Action, s: dict) -> float:
    return beliefs.bonus(s, a.name)


PLACE_PULL = 25.0              # how strongly beliefs steer the choice of place


def pick_place(a: Action, s: dict, rng: random.Random) -> str:
    if len(a.places) == 1:
        return a.places[0]
    weights = [math.exp(PLACE_PULL * beliefs.bonus(s, a.name, p)) for p in a.places]
    return rng.choices(a.places, weights=weights)[0]


def score(a: Action, s: dict, real: datetime, rng: random.Random) -> float:
    if a.name == "idle":
        return IDLE_SCORE + rng.uniform(0, NOISE)
    if a.name == "sleep":
        base = s["needs"]["rest"] * 1.0 + s["needs"]["quiet"] * 0.2 + max(0.0, -s["energy"]) * 0.5
        base += SLEEP_NIGHT_PULL if clock.is_night(real) else 0.0
    else:
        base = sum(s["needs"][n] * r for n, r in a.relief.items())
    recent = [h for h in s["history"] if h not in ("idle", "sleep")][-LATELY:]
    penalty = LATELY_PENALTY * recent.count(a.name)
    if recent and recent[-1] == a.name:
        penalty += REPEAT_PENALTY
    return base + belief_bonus(a, s) + rng.uniform(0, NOISE) - penalty


def choose(s: dict, real: datetime, rng: random.Random) -> tuple[Action, list]:
    options = [(score(a, s, real, rng), a) for a in ACTIONS.values() if allowed(a, s, real)]
    options.sort(key=lambda x: -x[0])
    return options[0][1], [(a.name, round(sc, 3)) for sc, a in options[:4]]


def wake_up(s: dict, real: datetime) -> bool:
    d = s["doing"]
    if d["ticks"] >= SLEEP_MAX_TICKS:
        return True
    rested = s["needs"]["rest"] < 0.05 and s["energy"] > 0.6
    return rested and not clock.is_night(real)


def start(a: Action, s: dict, real: datetime, rng: random.Random, outcome: Callable[[str, str], bool]) -> None:
    place = pick_place(a, s, rng)
    s["doing"] = {"action": a.name, "place": place, "ticks": 0, "ok": outcome(a.name, place), "met": 0.0,
                  "since": real.isoformat(timespec="seconds")}
    s["history"].append(a.name)
    s["history"] = s["history"][-50:]
    s["done_at"].setdefault(a.name, []).append(real.isoformat(timespec="seconds"))
    s["done_at"][a.name] = s["done_at"][a.name][-10:]


def progress(s: dict, real: datetime, rng: random.Random) -> dict | None:
    """Advance the current action one tick. Returns a finished-action record when it ends."""
    d = s["doing"]
    a = ACTIONS[d["action"]]
    d["ticks"] += 1
    if a.name == "sleep":
        d["met"] += needs.relieve(s, a.relief, 1.0)
        s["energy"] = needs.clamp(s["energy"] + a.energy, -1, 1)
        if not wake_up(s, real):
            return None
    else:
        share = (1.0 if d["ok"] else 0.3) / a.ticks          # a failed try still scratches the itch a bit
        d["met"] += needs.relieve(s, a.relief, share)
        needs.burden(s, a.side, 1.0 / a.ticks)
        s["energy"] = needs.clamp(s["energy"] + a.energy, -1, 1)
        if d["ticks"] < a.ticks:
            return None
    # finished
    before = s["mood"]
    if d["ok"]:
        gain = (OK_MOOD + a.mood_ok + MET_MOOD * d["met"]) * (1 - s["mood"])
        s["mood"] = needs.clamp(s["mood"] + gain, -1, 1)
    else:
        s["mood"] = needs.clamp(s["mood"] + FAIL_MOOD, -1, 1)
    if a.name not in ("sleep", "idle"):          # how the place itself felt; this is what beliefs pick up
        feel = PLACE_FEEL.get((a.name, d["place"]), 0.0) + PLACE_FEEL.get(d["place"], 0.0)
        s["mood"] = needs.clamp(s["mood"] + feel + rng.uniform(-PLACE_NOISE, PLACE_NOISE), -1, 1)
    done = {"action": a.name, "place": d["place"], "ok": d["ok"], "ticks": d["ticks"], "met": round(d["met"], 3),
            "dmood": round(s["mood"] - before, 4)}
    s["doing"] = None
    return done


def tick(s: dict, real: datetime, rng: random.Random, outcome: Callable[[str, str], bool]) -> dict:
    """One tick. Returns what happened (for the feed, the LLM and the simulation)."""
    night = clock.is_night(real)
    asleep = bool(s["doing"] and s["doing"]["action"] == "sleep")
    needs.rise(s, night, asleep)
    needs.drift_mood(s)
    event = {"finished": None, "started": None, "top": None}
    if s["doing"]:
        event["finished"] = progress(s, real, rng)
    if not s["doing"]:
        a, top = choose(s, real, rng)
        start(a, s, real, rng, outcome)
        event["started"], event["top"] = a.name, top
    return event
