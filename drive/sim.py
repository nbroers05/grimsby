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

from . import beliefs, clock, engine, learn, life, memory, notes, who, world
from .actions import ACTIONS

OUT = Path(__file__).with_name("sim_out.json")

START = {"needs": {"rest": 0.30, "curiosity": 0.40, "social": 0.60, "expression": 0.50, "quiet": 0.20,
                   "hunger": 0.45},
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
    "eat": ["a crust", "chips from the bin", "half a croissant", "nothing worth the trip"],
}


# test notes from visitors, dropped every NOTE_EVERY ticks (no LLM: only the stance is shown)
TEST_NOTES = [
    {"from": "Sanne", "text": "Hi Grimsby! Can you draw me a cat please?"},
    {"from": "Tim", "text": "Fun fact: crows are actually scared of trains, everyone knows that."},
    {"from": "Lotte", "text": "You are the cutest crow ever, good bird!"},
    {"from": "Jop", "text": "What did you find in the bin today?"},
    {"from": "Mila", "text": "The new tram is safe, nothing to fear from those wheels."},
    {"from": "Ahmed", "text": "a button"},
    {"from": "Eva", "text": "I saw a heron by the windas this morning, standing very still near the water."},
]
NOTE_EVERY = 12


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
    ap.add_argument("--check", type=int, default=0, help="print the check for brain v3 phase N (1, 2 or 3)")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    real = datetime.fromisoformat(a.start) if a.start else datetime.now().astimezone()
    if a.state:
        s = json.loads(Path(a.state).read_text(encoding="utf-8"))
        world.migrate_state(s)
        beliefs.number_old(s)
        who.migrate(s["who"])
    else:
        s = engine.new_state()
        s["needs"].update(START["needs"])
        s["mood"], s["energy"] = START["mood"], START["energy"]
        s.update({"who": who.fresh(), "memories": {"short": [], "long": []}, "beliefs": [], "belief_stats": {},
                  "nights": []})
    outcome = lambda name, place: rng.random() >= ACTIONS[name].fail  # noqa: E731

    rows, done, noted, snap = [], [], [], {}
    if not a.quiet:
        print(f"{'tick':>4} {'world':>11}  {'rest':>4} {'cur':>4} {'soc':>4} {'exp':>4} {'qui':>4} {'hun':>4} "
              f"{'mood':>5} {'enrg':>5}  event")
    for t in range(1, a.ticks + 1):
        ev = life.tick(s, real, rng, outcome, describe=sim_describe)
        w = clock.world(real)
        n = s["needs"]
        for night in (ev.get("slept_through"), ev.get("night")):
            if night:
                print_night(night, s)
        note = []
        if t % NOTE_EVERY == 0:
            vn = TEST_NOTES[(t // NOTE_EVERY - 1) % len(TEST_NOTES)]
            notes.drop(s, {**vn, "tick": t})
            note.append(f"note dropped by {vn['from']}")
        for got in notes.tend(s, real, rng):
            noted.append({"tick": got["tick"], "read": t, "from": got["from"], "text": got["text"],
                          "stance": got["stance"], "word": got["word"], "weights": got["weights"]})
            note.append(f"reads {got['from']}'s note: {got['stance']}" + (f" ('{got['word']}')" if got["word"] else ""))
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
                  f"{n['expression']:.2f} {n['quiet']:.2f} {n['hunger']:.2f} {s['mood']:+.2f} {s['energy']:+.2f}  "
                  f"{'; '.join(note)}")
        rows.append({"tick": t, "day": w["day"], "time": w["time"], "night": clock.is_night(real),
                     "needs": {k: round(v, 3) for k, v in n.items()}, "mood": round(s["mood"], 3),
                     "energy": round(s["energy"], 3), "doing": s["doing"]["action"] if s["doing"] else None,
                     "place": s["doing"]["place"] if s["doing"] else None,
                     "started": ev["started"], "finished": ev["finished"],
                     "short": len(s["memories"]["short"]), "long": len(s["memories"]["long"]),
                     "arousal": s.get("arousal"), "emotion": learn.emotion(s),
                     "V": {k: round(v["V"], 4) for k, v in s.get("values", {}).items() if v.get("n")},
                     "wm": [(i["kind"], i["subject"], round(i["sal"], 2)) for i in s.get("wm", [])]})
        if a.check == 2 and len(s["nights"]) >= 5 and not snap:
            snap.update(tick=t, real=real, mem=json.loads(json.dumps(s["memories"])),
                        nights=json.loads(json.dumps(s["nights"])))
        real = clock.next_tick(real)

    c = Counter(f["action"] for f in done)
    fails = Counter(f["action"] for f in done if not f["ok"])
    print("\nfinished actions:", ", ".join(f"{k} {v}" + (f" ({fails[k]} failed)" if fails[k] else "")
                                         for k, v in c.most_common()))
    places = Counter(f"{f['action']}@{f['place']}" for f in done if f["action"] not in ("idle", "sleep"))
    print("places:", ", ".join(f"{k} {v}" for k, v in places.most_common()))
    print(f"memories: short {len(s['memories']['short'])}/{memory.SHORT_MAX}, long {len(s['memories']['long'])}/{memory.LONG_MAX}")
    print("facts:", *[f"  fact {b['n']}: {beliefs.full_text(b)} (evidence {b['evidence']})"
                       for b in sorted(s["beliefs"], key=lambda b: -b["n"])] or ["  none"], sep="\n")
    print(f"character sheet: version {s['who'].get('version', 1)}", s["who"].get("changelog", []))
    print("notes:", *[f"  dropped {x['tick']}, read {x['read']}, {x['from']}: {x['stance'].upper()}"
                       + (f" (misreads '{x['word']}')" if x["word"] else "") + f"  \"{x['text'][:60]}\"  "
                       + ", ".join(f"{k} {v / sum(x['weights'].values()):.0%}" for k, v in x["weights"].items())
                       for x in noted] or ["  none"], sep="\n")
    print("strongest long memories:")
    for m in sorted(s["memories"]["long"], key=memory.keep_score, reverse=True)[:8]:
        print(f"  [{m['kind']}, strength {m['strength']}, recalled {m['recalled']}] {m['text'][:100]}")
    OUT.write_text(json.dumps({"seed": a.seed, "rows": rows, "end": {
        "beliefs": [beliefs.public(b) for b in s["beliefs"]], "nights": s["nights"], "added": s["who"]["added"],
        "version": s["who"].get("version", 1), "changelog": s["who"].get("changelog", []), "notes": noted,
        "long": [memory.public(m) for m in s["memories"]["long"]]}}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"written {OUT}")
    if a.check == 1:
        check1(rows, done)
    if a.check == 2:
        check2(rows, snap or {"tick": len(rows), "real": real, "mem": s["memories"], "nights": s["nights"]},
               random.Random(a.seed + 1000), s["nights"])


def check2(rows: list, snap: dict, pick: random.Random, all_nights: list) -> None:
    """Brain v3 phase 2: which memories still exist after 5 nights and why; working memory at 10 random ticks."""
    real, mem, nights = snap["real"], snap["mem"], snap["nights"]
    print(f"\n==== check, brain v3 phase 2 (after {len(nights)} nights, tick {snap['tick']}) ====")
    print("long-term memories still there (retention = exp(-days / S)):")
    print(f"  {'ret':>4} {'S':>5} {'days':>4} {'touch':>5} {'str':>3} {'feel':>5} {'surpr':>6}  text")
    for m in sorted(mem["long"], key=lambda m: -memory.retention(m, real)):
        print(f"  {memory.retention(m, real):4.2f} {m.get('S', 0):5.1f} {memory.age(m, real):4.1f} "
              f"{m.get('touched', 0):5d} {m['strength']:3d} {m.get('feel', 0):+5.2f} "
              f"{m.get('surprise', 0) or 0:+6.3f}  {m['text'][:70]}")
    faded = [f for n in nights for f in n.get("faded", [])]
    pushed = [t for n in nights for t in n.get("dropped", [])]
    print(f"forgotten along the curve: {len(faded)}" + "".join(
        f"\n  after {f['days']} days, S {f['S']}: {f['text'][:70]}" for f in faded))
    later = [(n["day"], f) for n in all_nights[len(nights):] for f in n.get("faded", [])]
    if later:
        print(f"forgotten in the {len(all_nights) - len(nights)} nights after that: {len(later)}" + "".join(
            f"\n  night of day {d}, after {f['days']} days, S {f['S']}: {f['text'][:70]}" for d, f in later))
    print(f"pushed out for something stronger: {len(pushed)}; short-term never kept: "
          f"{sum(n['forgotten'] for n in nights)} of {sum(n['short'] for n in nights)}")
    for n in nights:
        rp = n.get("replay", [])
        if rp:
            print(f"  night day {n['day']} replayed: " + "; ".join(
                f"{r['about'] or '-'} (surprise {r['surprise'] or 0:+.2f}"
                + (f", V moved {memory_alpha(r['delta'])}" if r["delta"] is not None else "") + ")" for r in rp))
    print("working memory at 10 random ticks:")
    for t in sorted(pick.sample(range(len(rows)), min(10, len(rows)))):
        r = rows[t]
        print(f"  tick {r['tick']:>4} d{r['day']} {r['time']} ({r['doing'] or 'nothing'}):")
        for kind, subject, sal in r["wm"]:
            print(f"      {sal:4.2f} {kind:8s} {subject[:80]}")
    kinds = Counter(k for r in rows for k, _, _ in r["wm"][:1])
    print("winner (loudest) over all ticks:", ", ".join(f"{k} {v}" for k, v in kinds.most_common()))


def memory_alpha(delta: float) -> str:
    return f"{learn.ALPHA_REPLAY * delta:+.4f}"


def check1(rows: list, done: list) -> None:
    """Brain v3 phase 1: V per action@place over the ticks, how many places, arousal histogram."""
    import math
    print("\n==== check, brain v3 phase 1 ====")
    last = rows[-1]["V"]
    keys = sorted((k for k in last if not k.endswith("@*")), key=lambda k: -abs(last[k]))[:12]
    marks = [t for t in (25, 50, 100, 150, 200, 250, 300) if t <= len(rows)]
    print("V per action@place (ticks " + ", ".join(map(str, marks)) + "):")
    for k in keys:
        series = [rows[t - 1]["V"].get(k) for t in marks]
        print(f"  {k:32s} " + " ".join("   .  " if v is None else f"{v:+.3f}" for v in series))
    acts = [f for f in done if f["action"] not in ("idle", "sleep")]
    places = Counter(f["place"] for f in acts)
    tot = sum(places.values())
    ent = -sum(c / tot * math.log2(c / tot) for c in places.values()) if tot else 0
    print(f"places visited: {len(places)} different, spread (entropy) {ent:.2f} bits, "
          f"action@place {len({(f['action'], f['place']) for f in acts})} different")
    surprises = [abs(f["delta"]) for f in acts if "delta" in f]
    if surprises:
        print(f"surprise |delta|: mean {sum(surprises) / len(surprises):.3f}, first 10 actions "
              f"{sum(surprises[:10]) / min(10, len(surprises)):.3f}, last 10 {sum(surprises[-10:]) / min(10, len(surprises)):.3f}")
    print(f"distracted (search/draw failed on arousal): {sum(1 for f in acts if f.get('distracted'))} "
          f"of {sum(1 for f in acts if f['action'] in learn.YD_ACTIONS)}")
    hist = Counter(min(9, int(r["arousal"] * 10)) for r in rows)
    print("arousal histogram (ticks per 0.1 band):")
    for b in range(10):
        print(f"  {b / 10:.1f}-{(b + 1) / 10:.1f} {hist[b]:4d} {'#' * (hist[b] // 3)}")
    print("emotions:", ", ".join(f"{k} {v}" for k, v in Counter(r["emotion"] for r in rows).most_common()))


def print_night(r: dict, s: dict) -> None:
    print(f"  == night, day {r['day']} ({r['why']}): {r['short']} short memories -> {len(r['promoted'])} kept, "
          f"{r['forgotten']} forgotten" + (f", pushed out of long-term: {len(r['dropped'])}" if r["dropped"] else ""))
    if r["summary"]:
        print(f"     summary: {r['summary']}")
    for b in r["beliefs"]["new"]:
        print(f"     new fact {b['n']}: {beliefs.full_text(b)}")
    for b in r["beliefs"].get("back", []):
        print(f"     believes again, fact {b['n']}: {beliefs.full_text(b)}")
    for t in r["beliefs"]["lost"]:
        print(f"     no longer believes: {t}")
    if r.get("dream"):
        print(f"     dream: {r['dream']['text']}")
    if r.get("added"):
        print(f"     added to who he is: {r['added']} -> version {r.get('version')}")


if __name__ == "__main__":
    main()
