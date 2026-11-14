"""Beliefs: patterns he has noticed, grown in code from what actions at places did to his mood.

Every finished action adds to running stats per "action@place" (count and summed mood change). At night those
stats fade a little (old experience counts less), and beliefs are (re)made from them: an action/place that
lifts his mood clearly more than his average becomes "Drawing on the windmill cheers me up." (evidence = how
many times it was tried, faded). Beliefs feed back into the action choice and the choice of place.
"""

from __future__ import annotations

NIGHT_FADE = 0.92
MIN_COUNT = 4.0                # tried at least this often (faded) before he believes anything about it
MARGIN = 0.012                 # mood change per go must differ this much from his average to form a belief
KEEP_MARGIN = 0.006            # ...and an existing belief stays until it drops under this (no flip-flopping)
MAX_BELIEFS = 12
BONUS = 0.06                   # utility bonus of a fully established belief
FULL_EVIDENCE = 12.0

HABIT = {                      # third person, for his character sheet
    "search": "looks things up", "read_back": "re-reads his old pages", "diary": "writes in his diary",
    "draw": "draws", "wander": "flies about town", "pigeons": "goes to glare at the pigeons",
    "neighbour": "checks on Pino", "sit": "sits very still", "tidy": "tidies his hoard",
}
DOING = {
    "search": "Looking things up", "read_back": "Re-reading my old pages", "diary": "Writing my diary",
    "draw": "Drawing", "wander": "Flying about town", "pigeons": "Keeping an eye on the pigeons",
    "neighbour": "Checking on Pino", "sit": "Sitting still", "tidy": "Tidying the hoard",
}
def where(place: str) -> str:
    from . import world
    return world.words(place)


def observe(stats: dict, done: dict) -> None:
    for key in (f"{done['action']}@{done['place']}", f"{done['action']}@*"):
        st = stats.setdefault(key, {"n": 0.0, "sum": 0.0})
        st["n"] = round(st["n"] + 1, 3)
        st["sum"] = round(st["sum"] + done["dmood"], 4)


def text_for(action: str, place: str, sign: int) -> str:
    where_ = "" if place == "*" else " " + where(place)
    verb = "cheers me up" if sign > 0 else "never goes well"
    return f"{DOING[action]}{where_} {verb}."


def update(state: dict) -> dict:
    """Run at night: fade the stats, rebuild beliefs. Returns {"new": [...], "lost": [...]}."""
    stats = state.setdefault("belief_stats", {})
    for st in stats.values():
        st["n"] = round(st["n"] * NIGHT_FADE, 3)
        st["sum"] = round(st["sum"] * NIGHT_FADE, 4)
    tot_n = sum(st["n"] for k, st in stats.items() if k.endswith("@*"))
    avg = (sum(st["sum"] for k, st in stats.items() if k.endswith("@*")) / tot_n) if tot_n else 0.0

    held_texts = {b["text"] for b in state.get("beliefs", [])}
    cands = []
    for key, st in stats.items():
        action, place = key.split("@")
        if action not in DOING or st["n"] < MIN_COUNT:
            continue
        diff = st["sum"] / st["n"] - avg
        sign = 1 if diff > 0 else -1
        held = text_for(action, place, sign) in held_texts
        if abs(diff) < (KEEP_MARGIN if held else MARGIN):
            continue
        if place != "*" and len({k for k in stats if k.startswith(action + "@") and k != f"{action}@*"}) <= 1:
            continue                     # only one place for this action: the place says nothing, use action@*
        cands.append({"text": text_for(action, place, sign), "evidence": int(round(st["n"])),
                      "about": key, "sign": sign, "diff": round(diff, 4)})
    # a place belief beats the general one for the same action and direction
    specific = {(c["about"].split("@")[0], c["sign"]) for c in cands if not c["about"].endswith("@*")}
    cands = [c for c in cands if not (c["about"].endswith("@*") and (c["about"][:-2], c["sign"]) in specific)]
    cands.sort(key=lambda c: -(c["evidence"] * abs(c["diff"])))
    old = {b["text"] for b in state.get("beliefs", [])}
    state["beliefs"] = cands[:MAX_BELIEFS]
    new = {b["text"] for b in state["beliefs"]}
    return {"new": sorted(new - old), "lost": sorted(old - new)}


def bonus(state: dict, action: str, place: str | None = None) -> float:
    """Utility bonus for an action (best place if none given) from his beliefs."""
    best = None
    for b in state.get("beliefs", []):
        a, p = b["about"].split("@")
        if a != action or (place and p not in (place, "*")):
            continue
        v = b["sign"] * BONUS * min(1.0, b["evidence"] / FULL_EVIDENCE)
        best = v if best is None else (max(best, v) if place is None else best + v)
    return best or 0.0


def public(b: dict) -> dict:
    return {"text": b["text"], "evidence": b["evidence"]}
