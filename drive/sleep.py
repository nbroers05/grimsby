"""Sleep is consolidation.

When he falls asleep (or on the first tick after the laptop was off):
  1. the short-term memory is summarised into one long-term memory
  2. the strongest short-term memories move to long-term (pushing out weaker ones), the rest is forgotten
  3. long-term memories fade a little (`recalled` shrinks)
  4. beliefs are rebuilt from the faded stats
  5. at most one addition to his character sheet, in `who.added`

Steps 1 and 5 are worded by the LLM (`voice`, see run.Voice); without one, code writes a plain version.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from . import beliefs, clock, memory, who

PROMOTE = 5                    # at most this many short memories move to long-term per night
PROMOTE_MIN = 3.0              # keep_score needed to be worth keeping
NIGHT_FADE = 0.9               # recalled *= this every night
ADD_EVIDENCE = 20              # a belief this well established may become part of who he is
ADD_EVERY_NIGHTS = 3           # and at most one addition per this many nights
MAX_NIGHTS_KEPT = 10

PLAIN = {"search": "looked things up", "read_back": "re-read old pages", "diary": "wrote in my diary",
         "draw": "drew", "wander": "flew about town", "pigeons": "watched the pigeons",
         "neighbour": "checked on Pino", "sit": "sat still", "tidy": "tidied the hoard"}


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
            where = "" if place == "*" else " " + beliefs.WHERE[place]
            return "quirks", f"{habit}{where} when a day needs mending"
    return None


def may_add(state: dict) -> bool:
    recent = state.get("nights", [])[-(ADD_EVERY_NIGHTS - 1):]
    return not any(n.get("added") for n in recent)


def consolidate(state: dict, real: datetime, voice=None, why: str = "fell asleep") -> dict:
    mem = state["memories"]
    day = clock.world(real)["day"]
    short = mem["short"]
    report = {"at": real.isoformat(timespec="seconds"), "day": day, "why": why, "short": len(short),
              "promoted": [], "forgotten": 0, "dropped": [], "summary": None}

    if short:
        text = (voice.summarise(short, day) if voice else None) or plain_summary(short, day)
        feel = sum(m.get("feel", 0) for m in short) / len(short)
        res = memory.add(mem["long"], memory.make(text, "moment", 3, real, feel, f"day@{day}"), memory.LONG_MAX)
        report["summary"] = text
        report["dropped"] += [res["dropped"]] if res.get("dropped") else []

        best = sorted(short, key=memory.keep_score, reverse=True)
        keep = [m for m in best if memory.keep_score(m) >= PROMOTE_MIN][:PROMOTE]
        for m in keep:
            res = memory.add(mem["long"], dict(m), memory.LONG_MAX)
            if res.get("added") or res.get("reinforced"):
                report["promoted"].append(m["text"])
            if res.get("dropped"):
                report["dropped"].append(res["dropped"])
        report["forgotten"] = len(short) - len(report["promoted"])
        mem["short"] = []

    for m in mem["long"]:
        m["recalled"] = round(m["recalled"] * NIGHT_FADE, 2)

    report["beliefs"] = beliefs.update(state)

    if may_add(state):
        cand = character_candidate(state)                 # code decides what; the voice only words it
        if cand and voice:
            cand = (cand[0], voice.phrase(cand[0], cand[1]) or cand[1])
        if cand and who.add(state["who"], *cand):
            report["added"] = {cand[0]: cand[1]}

    state["nights"] = (state.get("nights", []) + [report])[-MAX_NIGHTS_KEPT:]
    return report
