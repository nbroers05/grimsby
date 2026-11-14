"""One tick of Grimsby's life, decided entirely in code.

Per tick: needs rise, mood drifts, the current action progresses; when nothing is going on he picks the
next action by utility:

    score = sum(need * relief for each need the action meets)
          + the best place for it: belief bonus ("drawing on the windmill cheers me up") - cost of getting there
          + a little noise
          - a small penalty for doing the same thing again, or a lot lately

He is always at a place (s["at"], see world.py). An action somewhere else starts with travel ticks (energy
per km); only on arrival does `outcome(action_name, place)` run: whether it worked. The simulation rolls dice;
live, it is the real result.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Callable

from . import beliefs, clock, needs, world
from .actions import ACTIONS, IDLE_SCORE, SLEEP_EXHAUSTED, SLEEP_NIGHT_PULL, SLEEP_MIN_REST, SLEEP_MIN_REST_NIGHT, Action

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
    s.update({"doing": None, "history": [], "done_at": {}, "at": world.HOME, "world_version": 1})
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


PLACE_PULL = 25.0              # how strongly beliefs and distance steer the choice of place


def place_values(a: Action, s: dict) -> dict[str, float]:
    """For every place this action can happen: what he believes about it minus the cost of getting there."""
    here = s.get("at", world.HOME)
    return {p: beliefs.bonus(s, a.name, p) - world.travel_cost(here, p, s["energy"])
            for p in world.places_for(a.name, here)}


def pick_place(a: Action, s: dict, rng: random.Random) -> str:
    vals = place_values(a, s)
    places = list(vals)
    if len(places) == 1:
        return places[0]
    best = max(vals.values())
    weights = [math.exp(PLACE_PULL * (vals[p] - best)) for p in places]
    return rng.choices(places, weights=weights)[0]


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
    vals = place_values(a, s)
    return base + (max(vals.values()) if vals else 0.0) + rng.uniform(0, NOISE) - penalty


def choose(s: dict, real: datetime, rng: random.Random) -> tuple[Action, list]:
    here = s.get("at", world.HOME)
    options = [(score(a, s, real, rng), a) for a in ACTIONS.values()
               if allowed(a, s, real) and world.places_for(a.name, here)]
    options.sort(key=lambda x: -x[0])
    return options[0][1], [(a.name, round(sc, 3)) for sc, a in options[:4]]


def wake_up(s: dict, real: datetime) -> bool:
    d = s["doing"]
    if d["ticks"] >= SLEEP_MAX_TICKS:
        return True
    rested = s["needs"]["rest"] < 0.05 and s["energy"] > 0.6
    return rested and not clock.is_night(real)


def start(a: Action, s: dict, real: datetime, rng: random.Random) -> None:
    place = pick_place(a, s, rng)
    here = s.get("at", world.HOME)
    s["doing"] = {"action": a.name, "place": place, "from": here, "travel": world.travel_ticks(here, place),
                  "ticks": 0, "ok": None, "met": 0.0, "since": real.isoformat(timespec="seconds")}
    s["history"].append(a.name)
    s["history"] = s["history"][-50:]
    s["done_at"].setdefault(a.name, []).append(real.isoformat(timespec="seconds"))
    s["done_at"][a.name] = s["done_at"][a.name][-10:]


def arrive(s: dict, outcome: Callable[[str, str], bool]) -> None:
    """At the place: now the action really happens, and the world says whether it works."""
    d = s["doing"]
    s["at"] = d["place"]
    d["ok"] = outcome(d["action"], d["place"])


def fly(s: dict) -> bool:
    """One tick of travel. Returns True on arrival."""
    d = s["doing"]
    km = world.km(d["from"], d["place"]) / max(1, world.travel_ticks(d["from"], d["place"]))
    s["energy"] = needs.clamp(s["energy"] - world.ENERGY_PER_KM * km, -1, 1)
    d["travel"] -= 1
    return d["travel"] <= 0


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
        feel = world.feel(a.name, d["place"])
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
    event = {"finished": None, "started": None, "arrived": None, "top": None}
    d = s["doing"]
    if d and d.get("travel", 0) > 0:
        if fly(s):
            arrive(s, outcome)
            event["arrived"] = d["action"]
        return event
    if d:
        event["finished"] = progress(s, real, rng)
    if not s["doing"]:
        a, top = choose(s, real, rng)
        start(a, s, real, rng)
        event["started"], event["top"] = a.name, top
        if s["doing"]["travel"] == 0:               # already there
            arrive(s, outcome)
            event["arrived"] = a.name
    return event
