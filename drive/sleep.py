"""Sleep is consolidation.

When he falls asleep (or on the first tick after the laptop was off):
  1. the short-term memory is summarised into one long-term memory
  2. the strongest short-term memories move to long-term (pushing out weaker ones), the rest is forgotten
  3. long-term memories he has not thought of for too long are forgotten (memory.py: the forgetting curve)
  4. beliefs are rebuilt from the faded stats (new ones get a fact number; see beliefs.py)
  5. at most one addition to his character sheet, in `who.added`; each one makes a new version of him
  6. one dream: 3-5 memories from short and long term, the surprising ones most likely (replay), shuffled
     together. Replaying them teaches V once more, softly, and colours them with his mood (brain v3, phase 2)

Steps 1, 5, 6 and the closers of new failure beliefs are worded by the LLM (`voice`, see run.Voice); without
one, code writes a plain version. The dream is the night's only extra LLM call.
"""

from __future__ import annotations

import random
import re
from collections import Counter
from datetime import datetime

from . import beliefs, clock, influence, learn, memory, who

PROMOTE = 5                    # at most this many short memories move to long-term per night
PROMOTE_MIN = 3.0              # keep_score needed to be worth keeping
REPLAY_BASE = 0.03             # dream weight = this + |surprise| (brain v3: surprising memories are replayed most)
ADD_EVIDENCE = 20              # a belief this well established may become part of who he is
ADD_EVERY_NIGHTS = 3           # and at most one addition per this many nights
MAX_NIGHTS_KEPT = 10
DREAM_MIN, DREAM_MAX = 3, 5

PLAIN = {"search": "looked things up", "read_back": "re-read old pages", "diary": "wrote in my diary",
         "draw": "drew", "wander": "flew about town", "pigeons": "watched the pigeons",
         "neighbour": "checked on Pino", "sit": "sat still", "tidy": "tidied the hoard", "eat": "ate"}


def plain_summary(short: list[dict], day: int) -> str:
    acts = Counter(m["about"].split("@")[0] for m in short if m.get("about"))
    parts = [f"{PLAIN[a]}{'' if n == 1 else f' {n} times'}" for a, n in acts.most_common(4) if a in PLAIN]
    feel = sum(m.get("feel", 0) for m in short) / max(1, len(short))
    verdict = "A decent day." if feel > 0.15 else "A poor day." if feel < -0.05 else "An adequate day."
    if not parts:
        return f"Day {day}: little happened. {verdict}"
    return f"Day {day}: " + ", ".join(parts) + f". {verdict}"


def character_candidate(state: dict) -> tuple[str, str] | None:
    sheet = state["who"]
    taken = " ".join(t.lower() for f in sheet["added"].values() for t in f)
    for b in sorted(state.get("beliefs", []), key=lambda b: -b["evidence"]):
        if b["evidence"] >= ADD_EVIDENCE and b["sign"] > 0:
            action, place = b["about"].split("@")
            habit = beliefs.HABIT[action]
            if habit in taken:               # one habit per action, however many places
                continue
            where = "" if place == "*" else " " + beliefs.where(place)
            return "quirks", f"{habit}{where} when a day needs mending"
    return influence.sheet_candidate(state)               # repeated influence by one visitor (block G)


def replay_weight(m: dict) -> float:
    return REPLAY_BASE + abs(m.get("surprise", 0.0))


def dream_pieces(mem: dict, rng: random.Random) -> list[dict]:
    """Brain v3: not at random but weighted, the most surprising memories come back most (hippocampal replay)."""
    pool = [m for m in mem["short"] + mem["long"] if not m.get("about", "").startswith("day@")]
    if len(pool) < DREAM_MIN:
        pool = mem["short"] + mem["long"]
    pool, out = list(pool), []
    for _ in range(min(len(pool), rng.randint(DREAM_MIN, DREAM_MAX))):
        m = rng.choices(pool, weights=[replay_weight(x) for x in pool])[0]
        pool.remove(m)
        out.append(m)
    return out


def replay(state: dict, pieces: list[dict], real: datetime) -> list[dict]:
    """The dreamt memories are lived once more: V of their action@place learns softly, and they count as thought
    of (stability up, feel a little towards his mood now)."""
    out = []
    for m in pieces:
        about = m.get("about", "")
        d = learn.replay(state, about, m["outcome"]) if "@" in about and "outcome" in m else None
        memory.touch(m, real, state["mood"])
        out.append({"text": m["text"], "about": about, "surprise": m.get("surprise"),
                    "delta": None if d is None else round(d, 4)})
    return out


def forget(mem: dict, real: datetime) -> list[dict]:
    """The forgetting curve: long-term memories he has not thought of for too long are gone."""
    gone = [m for m in mem["long"] if memory.retention(m, real) < memory.FORGET_AT]
    for m in gone:
        mem["long"].remove(m)
    return [{"text": m["text"], "S": m.get("S"), "days": round(memory.age(m, real), 1)} for m in gone]


def plain_dream(pieces: list[dict], rng: random.Random) -> str:
    """Without a voice: cut the memories into bits and deal them out in the wrong order."""
    bits = []
    for m in pieces:
        t = re.sub(r"^Day \d+(, [0-9:]+)?: ", "", m["text"]).rstrip(".")
        bits += [b.strip() for b in re.split(r"[,:;]| and ", t) if len(b.strip()) > 3]
    rng.shuffle(bits)
    bits = [b if b.split()[0] not in ("A", "An", "The", "Looking", "Drawing", "Writing", "Sitting", "Having",
                                      "Keeping", "Checking", "Tidying", "Re-reading")
            else b[0].lower() + b[1:] for b in bits[:6]]          # names keep their capital
    if not bits:
        return "A dream with nothing in it, which was restful."
    return "Dreamt " + bits[0] + "".join((", but then " if i % 2 else ", and ") + b
                                         for i, b in enumerate(bits[1:])) + "."


def may_add(state: dict) -> bool:
    recent = state.get("nights", [])[-(ADD_EVERY_NIGHTS - 1):]
    return not any(n.get("added") for n in recent)


def consolidate(state: dict, real: datetime, voice=None, why: str = "fell asleep") -> dict:
    mem = state["memories"]
    day = clock.world(real)["day"]
    short = mem["short"]
    report = {"at": real.isoformat(timespec="seconds"), "day": day, "why": why, "short": len(short),
              "promoted": [], "forgotten": 0, "dropped": [], "summary": None}

    memory.setup(mem, real)                               # old memories get a forgetting curve that starts now
    rng = random.Random(real.timestamp())
    pieces = dream_pieces(mem, rng)                       # before the short-term memory is cleared
    if pieces:
        report["dream"] = {"text": (voice.dream(pieces) if voice else None) or plain_dream(pieces, rng),
                           "from": [m["text"] for m in pieces]}
        report["replay"] = replay(state, pieces, real)

    if short:
        text = (voice.summarise(short, day) if voice else None) or plain_summary(short, day)
        feel = sum(m.get("feel", 0) for m in short) / len(short)
        res = memory.add(mem["long"], memory.make(text, "moment", 3, real, feel, f"day@{day}"), memory.LONG_MAX)
        report["summary"] = text
        report["dropped"] += [res["dropped"]] if res.get("dropped") else []

        best = sorted(short, key=lambda m: memory.keep_score(m, real), reverse=True)
        keep = [m for m in best if memory.keep_score(m, real) >= PROMOTE_MIN][:PROMOTE]
        for m in keep:
            res = memory.add(mem["long"], dict(m), memory.LONG_MAX)
            if res.get("added") or res.get("reinforced"):
                report["promoted"].append(m["text"])
            if res.get("dropped"):
                report["dropped"].append(res["dropped"])
        report["forgotten"] = len(short) - len(report["promoted"])
        mem["short"] = []

    report["faded"] = forget(mem, real)                   # v3: the forgetting curve instead of a fixed NIGHT_FADE

    report["beliefs"] = beliefs.update(state)
    for b in report["beliefs"]["new"]:
        if b.get("closer") and voice:                     # a failure belief: the closer in his own words
            b["closer"] = voice.closer(b["text"]) or b["closer"]
            state["facts"][b["text"]]["closer"] = b["closer"]

    if may_add(state):
        cand = character_candidate(state)                 # code decides what; the voice only words it
        if cand and voice:
            cand = (cand[0], voice.phrase(cand[0], cand[1]) or cand[1])
        if cand and who.add(state["who"], *cand, real=real, day=day):
            report["added"] = {cand[0]: cand[1]}
            report["version"] = state["who"]["version"]

    state["nights"] = (state.get("nights", []) + [report])[-MAX_NIGHTS_KEPT:]
    return report
