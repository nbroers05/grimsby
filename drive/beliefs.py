"""Beliefs: the wording of what he has learned (learn.py: an expected value V per "action@place").

Since brain v3 there are no separate belief stats any more: every finished action updates V by its prediction
error (learn.learn). At night the evidence counts fade a little, and beliefs are (re)made from V:

  - an action/place whose V lies clearly above or below his average V: "Drawing on the windmill cheers me up."
  - two places for the same action whose V differs clearly: "The Albert Heijn is better than the Jumbo."
    (place-bound, about = "eat@albert-heijn", vs = "jumbo")

evidence = how many times it was tried, faded. The choice itself uses V directly (bonus -> learn.value_bonus);
beliefs only put it into words, for him, his facts and the site.

Facts: every belief gets a number the night it first forms ("fact 14"), from state["facts_made"]. A belief that
comes mostly from things going wrong (ok: false) ends with a dry closer in his own words ("I shall not be doing
that again."); the closer is kept as long as the belief is.
"""

from __future__ import annotations

from . import learn

NIGHT_FADE = 0.92
MIN_COUNT = 4.0                # tried at least this often (faded) before he believes anything about it
MARGIN = 0.05                  # V must differ this much from his average to form a belief
KEEP_MARGIN = 0.025            # ...and an existing belief stays until it drops under this (no flip-flopping)
COMPARE_MARGIN = 0.05          # two places for one action must differ this much in V to compare them
MAX_BELIEFS = 12
FAIL_SHARE = 0.15              # a bad belief with at least this share of failures behind it gets a closer

HABIT = {                      # third person, for his character sheet
    "search": "looks things up", "read_back": "re-reads his old pages", "diary": "writes in his diary",
    "draw": "draws", "wander": "flies about town", "pigeons": "goes to glare at the pigeons",
    "neighbour": "checks on Pino", "sit": "sits very still", "tidy": "tidies his hoard", "eat": "eats",
}
DOING = {
    "search": "Looking things up", "read_back": "Re-reading my old pages", "diary": "Writing my diary",
    "draw": "Drawing", "wander": "Flying about town", "pigeons": "Keeping an eye on the pigeons",
    "neighbour": "Checking on Pino", "sit": "Sitting still", "tidy": "Tidying the hoard", "eat": "Eating",
}
# when code has no voice for the closer (simulation, Ollama down); in his voice, picked by fact number
CLOSERS = ["I shall not be doing that again.", "Noted, and not repeated.", "Once was several times too many.",
           "Filed under: no.", "Lesson learned, at some cost.", "I have crossed it off the list."]


def where(place: str) -> str:
    from . import world
    return world.words(place)


def name(place: str) -> str:
    from . import world
    n = world.name(place)
    return n[0].upper() + n[1:]


def text_for(action: str, place: str, sign: int) -> str:
    where_ = "" if place == "*" else " " + where(place)
    verb = "cheers me up" if sign > 0 else "never goes well"
    return f"{DOING[action]}{where_} {verb}."


def compare_text(action: str, better: str, worse: str) -> str:
    if action == "eat":
        w = name(worse)
        return f"{name(better)} is better than {'the' + w[3:] if w.startswith('The ') else w}."
    return f"{DOING[action]} {where(better)} beats {DOING[action].lower()} {where(worse)}."


def comparisons(values: dict, held_texts: set) -> list[dict]:
    """Per action: the best and the worst place he knows well enough, if their V differs clearly."""
    by_action: dict[str, list] = {}
    for key, v in values.items():
        action, place = key.split("@")
        if place != "*" and action in DOING and v.get("n", 0) >= MIN_COUNT:
            by_action.setdefault(action, []).append((v["V"], place, v["n"]))
    out = []
    for action, rows in by_action.items():
        if len(rows) < 2:
            continue
        rows.sort()
        (lo, worse, n_lo), (hi, better, n_hi) = rows[0], rows[-1]
        text = compare_text(action, better, worse)
        if hi - lo < (KEEP_MARGIN * 2 if text in held_texts else COMPARE_MARGIN):
            continue
        out.append({"text": text, "evidence": int(round(n_lo + n_hi)), "about": f"{action}@{better}",
                    "vs": worse, "sign": 1, "diff": round((hi - lo) / 2, 4)})
    return out


def update(state: dict) -> dict:
    """Run at night: fade the evidence, reword V as beliefs, number new ones.
    Returns {"new": [...], "back": [...], "lost": [...]} ("new" and "back" hold the beliefs themselves)."""
    learn.setup(state)
    learn.night_fade(state, NIGHT_FADE)
    values = state["values"]
    avg = learn.average(state)

    old = {b["text"]: b for b in state.get("beliefs", [])}
    cands = []
    for key, v in values.items():
        action, place = key.split("@")
        if action not in DOING or v.get("n", 0) < MIN_COUNT:
            continue
        diff = v["V"] - avg
        sign = 1 if diff > 0 else -1
        held = text_for(action, place, sign) in old
        if abs(diff) < (KEEP_MARGIN if held else MARGIN):
            continue
        if place != "*" and len({k for k in values if k.startswith(action + "@") and k != f"{action}@*"}) <= 1:
            continue                     # only one place for this action: the place says nothing, use action@*
        cands.append({"text": text_for(action, place, sign), "evidence": int(round(v["n"])),
                      "about": key, "sign": sign, "diff": round(diff, 4),
                      "failed": sign < 0 and v.get("fail", 0.0) / v["n"] >= FAIL_SHARE})
    # a place belief beats the general one for the same action and direction
    specific = {(c["about"].split("@")[0], c["sign"]) for c in cands if not c["about"].endswith("@*")}
    cands = [c for c in cands if not (c["about"].endswith("@*") and (c["about"][:-2], c["sign"]) in specific)]
    cands += comparisons(values, set(old))
    cands.sort(key=lambda c: -(c["evidence"] * abs(c["diff"])))
    kept = cands[:MAX_BELIEFS]

    # every belief he ever held keeps its number: one that fades and comes back is the same fact again
    known = state.setdefault("facts", {})
    new, back = [], []
    for b in kept:
        failed = b.pop("failed", False)
        was = old.get(b["text"]) or known.get(b["text"])
        if was and was.get("n"):         # the same belief keeps its number, its date and its closer
            b.update(n=was["n"], since=was.get("since"), closer=was.get("closer"))
            if b["text"] not in old:
                back.append(b)
        else:
            state["facts_made"] = state.get("facts_made", 0) + 1
            b["n"] = state["facts_made"]
            b["since"] = state.get("last_tick")
            b["closer"] = CLOSERS[b["n"] % len(CLOSERS)] if failed else None
            new.append(b)
        known[b["text"]] = {"n": b["n"], "since": b["since"], "closer": b["closer"]}
    state["beliefs"] = kept
    lost = sorted(t for t in old if t not in {b["text"] for b in kept})
    return {"new": new, "back": back, "lost": lost}


def number_old(state: dict) -> bool:
    """Beliefs from before numbering get their numbers now, strongest first. Returns changed."""
    todo = [b for b in state.get("beliefs", []) if not b.get("n")]
    for b in sorted(todo, key=lambda b: -b["evidence"]):
        state["facts_made"] = state.get("facts_made", 0) + 1
        b.update(n=state["facts_made"], since=b.get("since"), closer=b.get("closer"))
        state.setdefault("facts", {})[b["text"]] = {"n": b["n"], "since": b["since"], "closer": b["closer"]}
    state.setdefault("facts_made", 0)
    return bool(todo)


def bonus(state: dict, action: str, place: str | None = None) -> float:
    """Utility from what he has learned about an action (at a place, or at its best place). Uses V (learn.py)."""
    if place:
        return learn.value_bonus(state, action, place)
    from . import world
    opts = [learn.value_bonus(state, action, p) for p in world.places_for(action, state.get("at", world.HOME))]
    return max(opts) if opts else learn.value_bonus(state, action, None)


def full_text(b: dict) -> str:
    return b["text"] + (" " + b["closer"] if b.get("closer") else "")


def public(b: dict) -> dict:
    return {"n": b.get("n"), "text": full_text(b), "evidence": b["evidence"], "since": b.get("since")}
