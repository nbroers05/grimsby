"""Grimsby's life per tick: the engine (needs, choice) plus memory, beliefs and sleep.

`describe(done, real, rng)` turns a finished action into the text of a memory. From step 4 the LLM writes
that text; until then (and in the simulation) code does.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Callable

from . import attend, clock, engine, learn, memory, needs, sleep, world
from .actions import ACTIONS, RISE_ASLEEP_SHARE

OFF_GAP = timedelta(minutes=15)          # longer than this between ticks = the laptop was off = he slept
KIND = {"search": "fact", "read_back": "moment", "diary": "work", "draw": "work", "wander": "moment",
        "pigeons": "person", "neighbour": "person", "sit": "moment", "tidy": "work",
        "eat": "moment"}
QUIET_ACTIONS = ("sit",)                 # mostly not worth a memory


def plain_describe(done: dict, real: datetime, rng: random.Random) -> str:
    w = clock.world(real)
    what = ACTIONS[done["action"]].doing
    what += " " + world.words(done["place"])
    return f"Day {w['day']}, {w['time']}: {what}" + ("" if done["ok"] else ", and it went wrong") + "."


def remember(state: dict, done: dict, real: datetime, rng: random.Random, describe) -> dict | None:
    if done["action"] in ("idle", "sleep") or (done["action"] in QUIET_ACTIONS and rng.random() > 0.2):
        return None
    strength = 2 + (0 if done["ok"] else 1) + (1 if abs(done["dmood"]) > 0.06 else 0)
    feel = max(-1.0, min(1.0, done["dmood"] * 6))
    m = memory.make(describe(done, real, rng), KIND[done["action"]], strength, real, feel,
                    f"{done['action']}@{done['place']}")
    m["surprise"] = done.get("delta", 0.0)          # internal: how much it differed from what he expected
    if "outcome" in done:
        m["outcome"] = done["outcome"]                # internal: what it really gave (sleep replays it)
    return memory.add(state["memories"]["short"], m, memory.SHORT_MAX)


def catch_up(state: dict, real: datetime, voice=None) -> dict | None:
    """First tick after a gap: he slept through it. Consolidate and wake rested."""
    last = state.get("last_tick")
    if not last or real - datetime.fromisoformat(last) <= OFF_GAP:
        return None
    gap_ticks = (real - datetime.fromisoformat(last)).total_seconds() / clock.TICK_SECONDS
    report = sleep.consolidate(state, real, voice, why="the laptop was off")
    state["needs"]["rest"] = 0.0
    state["energy"] = needs.clamp(state["energy"] + gap_ticks * ACTIONS["sleep"].energy, -1, 1)
    for n in needs.NEEDS:
        if n != "rest":
            state["needs"][n] = needs.clamp(state["needs"][n] + gap_ticks * needs.RISE[n] * RISE_ASLEEP_SHARE, 0, 0.8)
    state["doing"] = None
    state["at"] = world.HOME                       # he slept on his roof
    return report


def tick(state: dict, real: datetime, rng: random.Random, outcome: Callable[[str, str], bool],
         describe=plain_describe, voice=None) -> dict:
    ev = {"slept_through": catch_up(state, real, voice)}
    state["pending_done"] = state.get("pending")   # the running action's result; a new start overwrites "pending"
    learn.setup(state)
    memory.setup(state["memories"], real)
    ev.update(engine.tick(state, real, rng, outcome))
    if ev["finished"]:
        if ev["finished"]["action"] not in ("idle", "sleep"):
            learn.surprise(state, learn.learn(state, ev["finished"], real))
        ev["memory"] = remember(state, ev["finished"], real, rng, describe)
    recalled = None
    if ev["arrived"] == "sleep":                   # home on the roof: sleep is consolidation
        ev["night"] = sleep.consolidate(state, real, voice)
    elif ev["arrived"]:
        d = state["doing"]
        recalled = memory.recall(state["memories"], f"{d['action']} {d['place']} {ACTIONS[d['action']].doing}",
                                 real=real, mood=state["mood"])
        state["mood"] = needs.clamp(state["mood"] + memory.mood_from(recalled), -1, 1)
        ev["recalled"] = [m["text"] for m in recalled]
    attend.tick(state, ev, recalled, (state.get("doing") or {}).get("novelty") if ev["arrived"] else None)
    state["last_tick"] = real.isoformat(timespec="seconds")
    return ev
