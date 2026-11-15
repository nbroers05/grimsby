"""Does visitors' influence (block G, drive/influence.py) do anything you can see? Simulation without the LLM.

    .venv\\Scripts\\python -m drive.sim_influence [--ticks 600] [--seeds 6]

For every route the same life is run twice per seed, once without and once with one visitor's notes (dropped
every NOTE_EVERY ticks), and the difference is printed. Also: what a single note does, and where the ceiling
(influence.PER_DAY, BONUS_DAY_MAX) stops a visitor who writes far too often.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime

from . import engine, influence, life, notes, who
from .actions import ACTIONS
from .sim import START, sim_describe

START_AT = "2026-11-15T09:00:00+01:00"


def fresh() -> dict:
    s = engine.new_state()
    s["needs"].update(START["needs"])
    s["mood"], s["energy"] = START["mood"], START["energy"]
    s.update({"who": who.fresh(), "memories": {"short": [], "long": []}, "beliefs": [], "belief_stats": {},
              "nights": []})
    return s


def run(ticks: int, seed: int, note: dict | None, every: int, trust: float | None = None) -> dict:
    rng = random.Random(seed)
    real = datetime.fromisoformat(START_AT)
    s = fresh()
    outcome = lambda name, place: rng.random() >= ACTIONS[name].fail  # noqa: E731
    done, effects = [], []
    nrng = random.Random(seed + 99)                  # notes get their own dice, so both runs share the life's
    for t in range(1, ticks + 1):
        ev = life.tick(s, real, rng, outcome, describe=sim_describe)
        if ev["finished"]:
            done.append(ev["finished"])
        if note and t % every == 0:
            notes.drop(s, dict(note))
        if trust is not None and note:              # trust is fixed until brain v3 point 8; here we set it
            influence.profile(s, note["from"], real)["trust"] = trust
        effects += notes.tend(s, real, nrng)
        real = real.__class__.fromtimestamp(real.timestamp() + 90, real.tzinfo)
    return {"s": s, "done": done, "effects": effects}


def share(done: list, action: str, place: str) -> float:
    xs = [d for d in done if d["action"] == action]
    return sum(1 for d in xs if d["place"] == place) / max(1, len(xs))


def visits(done: list, place: str) -> int:
    return sum(1 for d in done if d["place"] == place and d["action"] not in ("sleep", "idle"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=600)
    ap.add_argument("--seeds", type=int, default=6)
    a = ap.parse_args()
    seeds = range(1, a.seeds + 1)

    print("1. What single notes do (fresh state, social need %.2f, trust %.2f):" % (START["needs"]["social"],
                                                                                  influence.TRUST_START))
    real = datetime.fromisoformat(START_AT)
    for stance in ("answer", "disagree", "ignore", "refuse"):
        for text in ("You should try the Jumbo, it is better than the Albert Heijn.",
                     "Do you know why pigeons nod their heads when they walk?"):
            s = fresh()
            e = influence.receive(s, text, "Sanne", stance, real)
            print(f"   {stance:8s} {text[:55]:55s} -> suggest {[(x['action'], x['place'], x['bonus']) for x in e['suggest']]}"
                  f" topic {e['topic']!r} opinion {e['opinion']}")
    s = fresh()
    print("   a negative visitor (trust -0.5), answered: ", end="")
    influence.profile(s, "Tim", real)["trust"] = -0.5
    e = influence.receive(s, "Go to the McDonald's, eat there.", "Tim", "answer", real)
    print([(x["action"], x["place"], x["bonus"]) for x in e["suggest"]])

    print(f"\n2. Suggestions and opinions: one visitor writes the same note every 20 ticks ({len(seeds)} seeds x "
          f"{a.ticks} ticks, the same lives with and without the notes)")
    for text in ("You should eat at the Jumbo, it is better than the Albert Heijn.",
                 "The Jumbo is better than the Albert Heijn. Lovely bread there."):
        print(f"   '{text}'")
        for trust in (0.3, 0.8, -0.5):
            r, stances = [], Counter()
            for sd in seeds:
                base, inf = run(a.ticks, sd, None, 20), run(a.ticks, sd, {"from": "Sanne", "text": text}, 20, trust)
                stances.update(g["stance"] for g in inf["effects"])
                r.append((share(base["done"], "eat", "jumbo"), share(inf["done"], "eat", "jumbo"),
                          share(base["done"], "eat", "albert-heijn"), share(inf["done"], "eat", "albert-heijn")))
            m = lambda i: sum(x[i] for x in r) / len(r)  # noqa: E731
            tot = sum(stances.values()) or 1
            print(f"     trust {trust:+.1f}: meals at the Jumbo {m(0):.0%} -> {m(1):.0%}, at the AH {m(2):.0%} -> "
                  f"{m(3):.0%}   (he took it: " + ", ".join(f"{k} {v / tot:.0%}" for k, v in stances.most_common()) + ")")
    note = {"from": "Sanne", "text": "You should eat at the Jumbo, it is better than the Albert Heijn."}

    print("\n3. The ceiling: the same visitor writes every 2 ticks instead of every 20")
    for every in (20, 2):
        caps, sug, op = Counter(), 0, 0
        for sd in seeds:
            inf = run(a.ticks, sd, note, every, 0.8)
            for g in inf["effects"]:
                eff = g.get("effects") or {}
                sug += len(eff.get("suggest", [])); op += len(eff.get("opinion", []))
                for c in eff.get("capped", []):
                    caps[c[0]] += 1
        print(f"   every {every:2d} ticks: suggestions through {sug / len(seeds):.1f}, opinions through {op / len(seeds):.1f}, "
              f"stopped by the ceiling {dict(caps)} (per run of {a.ticks} ticks = {a.ticks // 120} world days)")

    print("\n4. A planted question: 'Do you know why pigeons nod their heads?' once, at tick 10")
    q = {"from": "Jop", "text": "Do you know why pigeons nod their heads?"}
    planted = searched = 0
    for sd in seeds:
        inf = run(a.ticks, sd, None, 20)
        rng = random.Random(sd)
        s = inf["s"]
        r = influence.receive(s, q["text"], q["from"], "answer", datetime.fromisoformat(START_AT))
        planted += bool(r["topic"])
    print(f"   planted as an open question in {planted}/{len(seeds)} runs: {r['topic']!r}")
    print(f"   too_close('why pigeons nod their heads', topic) = {influence.too_close('why pigeons nod their heads', r['topic'] or '')}"
          f"; too_close('pigeon head bobbing walking reason', topic) = {influence.too_close('pigeon head bobbing walking reason', r['topic'] or '')}")

    print("\n5. Items: 'a shiny marble' left 10 times")
    taken = 0
    for sd in seeds:
        inf = run(a.ticks, sd, {"from": "Eva", "text": "", "item": "a shiny marble"}, 50)
        taken += sum(1 for g in inf["effects"] if (g.get("took") or {}).get("taken"))
    print(f"   taken {taken / len(seeds):.1f} of ~{a.ticks // 50} per run; hoard after: {influence.hoard(inf['s'])}")


if __name__ == "__main__":
    main()
