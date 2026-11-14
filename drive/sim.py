"""Simulate Grimsby's life without the LLM.

  .venv\\Scripts\\python -m drive.sim                         100 ticks from now, fresh start, seed 1
  .venv\\Scripts\\python -m drive.sim --state drive/state_v2.json --ticks 1200 --quiet
  .venv\\Scripts\\python -m drive.sim --ticks 300 --seed 7 --start 2026-11-15T09:00:00+01:00

With --state it starts from a copy of that state (never written back). The first tick after a gap counts as
sleep, as it will live. Prints a table (or with --quiet only the nights) and writes drive/sim_out.json.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import beliefs, clock, engine, life, memory, who, world
from .actions import ACTIONS

OUT = Path(__file__).with_name("sim_out.json")

START = {"needs": {"rest": 0.30, "curiosity": 0.40, "social": 0.60, "expression": 0.50, "quiet": 0.20},
         "mood": 0.0, "energy": 0.30}

# stand-ins for what the LLM will write from step 4: enough variety that memories are not all the same line
DETAIL = {
    "search": ["the history of the teaspoon", "why rubber bands snap", "how pigeons navigate", "the first tram",
               "bottle cap sizes", "the Dutch word for drizzle", "vulcanised rubber", "why windmills turn left"],
    "read_back": ["the page about Derek", "my list of wheels", "an entry from day one", "the vulcanisation notes"],
    "diary": ["the drizzle", "a train that was early", "Derek's posture", "the smell of the library",
              "a dropped glove", "the teaspoon"],
    "draw": ["a bottle cap", "the station clock", "Derek, unflatteringly", "a rubber band at rest", "a cloud"],
    "wander": ["the canal", "the school yard", "the church spire", "the Albert Heijn car park"],
    "pigeons": ["Derek was there, and smug", "Derek was elsewhere", "three pigeons, no Derek", "Derek's cousin"],
    "neighbour": ["Pino was patching his synth", "Pino was asleep", "Pino was paddling in his pond"],
    "sit": ["the rails", "the drizzle"],
    "tidy": ["the bottle caps", "the teaspoon", "a shiny button"],
}


def sim_describe(done: dict, real: datetime, rng: random.Random) -> str:
    w = clock.world(real)
    what = f"{ACTIONS[done['action']].doing} {world.words(done['place'])}"
    return f"Day {w['day']}: {what}: {rng.choice(DETAIL[done['action']])}" + ("" if done["ok"] else ", it went wrong") + "."


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--start", help="real start time (ISO), default now")
    ap.add_argument("--state", help="start from a copy of this state file (e.g. drive/state_v2.json)")
    ap.add_argument("--quiet", action="store_true", help="only print the nights and the end result")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    real = datetime.fromisoformat(a.start) if a.start else datetime.now().astimezone()
    if a.state:
        s = json.loads(Path(a.state).read_text(encoding="utf-8"))
        world.migrate_state(s)
    else:
        s = engine.new_state()
        s["needs"].update(START["needs"])
        s["mood"], s["energy"] = START["mood"], START["energy"]
        s.update({"who": who.fresh(), "memories": {"short": [], "long": []}, "beliefs": [], "belief_stats": {},
                  "nights": []})
    outcome = lambda name, place: rng.random() >= ACTIONS[name].fail  # noqa: E731

    rows, done = [], []
    if not a.quiet:
        print(f"{'tick':>4} {'world':>11}  {'rest':>4} {'cur':>4} {'soc':>4} {'exp':>4} {'qui':>4} "
              f"{'mood':>5} {'enrg':>5}  event")
    for t in range(1, a.ticks + 1):
        ev = life.tick(s, real, rng, outcome, describe=sim_describe)
        w = clock.world(real)
        n = s["needs"]
        for night in (ev.get("slept_through"), ev.get("night")):
            if night:
                print_night(night, s)
        note = []
        if ev["finished"]:
            done.append(ev["finished"])
            note.append(f"done {ev['finished']['action']}{'' if ev['finished']['ok'] else ' (FAILED)'}")
        if ev["started"]:
            d = s["doing"]
            fly = f" (fly {d['travel']})" if d and d.get("travel") else ""
            note.append(f"-> {ev['started']}@{d['place'] if d else s.get('at')}{fly}  ["
                        + ", ".join(f"{x} {y:.2f}" for x, y in ev["top"][:3]) + "]")
        if not a.quiet:
            print(f"{t:>4} d{w['day']} {w['time']}  {n['rest']:.2f} {n['curiosity']:.2f} {n['social']:.2f} "
                  f"{n['expression']:.2f} {n['quiet']:.2f} {s['mood']:+.2f} {s['energy']:+.2f}  {'; '.join(note)}")
        rows.append({"tick": t, "day": w["day"], "time": w["time"], "night": clock.is_night(real),
                     "needs": {k: round(v, 3) for k, v in n.items()}, "mood": round(s["mood"], 3),
                     "energy": round(s["energy"], 3), "doing": s["doing"]["action"] if s["doing"] else None,
                     "place": s["doing"]["place"] if s["doing"] else None,
                     "started": ev["started"], "finished": ev["finished"],
                     "short": len(s["memories"]["short"]), "long": len(s["memories"]["long"])})
        real = clock.next_tick(real)

    c = Counter(f["action"] for f in done)
    fails = Counter(f["action"] for f in done if not f["ok"])
    print("\nfinished actions:", ", ".join(f"{k} {v}" + (f" ({fails[k]} failed)" if fails[k] else "")
                                         for k, v in c.most_common()))
    places = Counter(f"{f['action']}@{f['place']}" for f in done if f["action"] not in ("idle", "sleep"))
    print("places:", ", ".join(f"{k} {v}" for k, v in places.most_common()))
    print(f"memories: short {len(s['memories']['short'])}/{memory.SHORT_MAX}, long {len(s['memories']['long'])}/{memory.LONG_MAX}")
    print("beliefs:", *[f"  {b['text']} (evidence {b['evidence']})" for b in s["beliefs"]] or ["  none"], sep="\n")
    print("added to his character:", s["who"]["added"])
    print("strongest long memories:")
    for m in sorted(s["memories"]["long"], key=memory.keep_score, reverse=True)[:8]:
        print(f"  [{m['kind']}, strength {m['strength']}, recalled {m['recalled']}] {m['text'][:100]}")
    OUT.write_text(json.dumps({"seed": a.seed, "rows": rows, "end": {
        "beliefs": [beliefs.public(b) for b in s["beliefs"]], "nights": s["nights"], "added": s["who"]["added"],
        "long": [memory.public(m) for m in s["memories"]["long"]]}}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"written {OUT}")


def print_night(r: dict, s: dict) -> None:
    print(f"  == night, day {r['day']} ({r['why']}): {r['short']} short memories -> {len(r['promoted'])} kept, "
          f"{r['forgotten']} forgotten" + (f", pushed out of long-term: {len(r['dropped'])}" if r["dropped"] else ""))
    if r["summary"]:
        print(f"     summary: {r['summary']}")
    for t in r["beliefs"]["new"]:
        print(f"     new belief: {t}")
    for t in r["beliefs"]["lost"]:
        print(f"     no longer believes: {t}")
    if r.get("added"):
        print(f"     added to who he is: {r['added']}")


if __name__ == "__main__":
    main()
