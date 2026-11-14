"""Short- and long-term memory, small on purpose.

Every memory: text, kind (fact | person | work | moment), strength (1-5), recalled (how often it came back,
fractional because it fades a little every night), since. Two internal fields stay out of the public JSON:
`feel` (how it felt, -1..1; recalling it nudges mood) and `about` (action@place, for beliefs and dedupe).

Something new only gets in by pushing out something weaker (lowest strength x (1 + recalled)).
"""

from __future__ import annotations

from datetime import datetime

from .text import similarity, words

SHORT_MAX = 30
LONG_MAX = 60
KINDS = ("fact", "person", "work", "moment")
SAME = 0.5                     # similarity above this = the same memory again: reinforce instead of adding
RECALL_FEEL = 0.02             # mood nudge per recalled memory, times its feel
RECALL_BUMP = 0.25             # recall happens often; a memory needs many recalls to really stick
RECALLED_MAX = 10.0
PUBLIC = ("text", "kind", "strength", "recalled", "since")

# the three principles from the character sheet; memories that fit them are kept more firmly
HOLDS_TO = [
    ("A fact is only shiny if it is true.",
     {"true", "truth", "fact", "accurate", "evidence", "proof", "proven", "myth", "false", "wrong", "measured",
      "learned", "discovered", "actually", "checked"}),
    ("Never trust a thing for its wheels, nor dismiss it for them.",
     {"wheel", "bicycle", "bike", "tire", "tyre", "pneumatic", "train", "car", "cart", "roll", "rolling",
      "rubber", "axle", "pram", "skateboard"}),
    ("Every small thing deserves one careful look.",
     {"small", "tiny", "little", "detail", "careful", "closely", "cap", "teaspoon", "button", "crumb", "hoard",
      "shiny", "noticed", "speck", "pebble"}),
]


def holds_to_fit(text: str) -> int:
    """How many of his principles this text touches (0-3)."""
    w = words(text)
    return sum(1 for _, keys in HOLDS_TO if w & keys)


def keep_score(m: dict) -> float:
    return m["strength"] * (1 + m["recalled"])


def make(text: str, kind: str, strength: float, real: datetime, feel: float = 0.0, about: str = "") -> dict:
    assert kind in KINDS, kind
    strength += holds_to_fit(text)                   # principles act as a filter: fitting things stick
    return {"text": text, "kind": kind, "strength": max(1, min(5, round(strength))), "recalled": 0.0,
            "since": real.isoformat(timespec="seconds"), "feel": round(feel, 3), "about": about}


def add(store: list, new: dict, limit: int) -> dict:
    """Put `new` into `store`. Returns {"added"|"reinforced"|"refused": text, "dropped": text?}."""
    for m in store:
        if new["about"].startswith("day@"):      # every day's summary is its own memory
            break
        if (new["about"] and new["about"] == m.get("about") and new["text"] == m["text"]) \
                or similarity(new["text"], m["text"]) >= SAME:
            m["strength"] = min(5, m["strength"] + 1)
            m["recalled"] = round(min(RECALLED_MAX, m["recalled"] + 0.5), 2)
            return {"reinforced": m["text"]}
    if len(store) < limit:
        store.append(new)
        return {"added": new["text"]}
    weakest = min(store, key=keep_score)
    if keep_score(new) < keep_score(weakest):
        return {"refused": new["text"]}
    store.remove(weakest)
    store.append(new)
    return {"added": new["text"], "dropped": weakest["text"]}


def recall(mem: dict, about: str, k: int = 3, bump: bool = True) -> list[dict]:
    """The few most relevant memories for `about` (short and long together). Bumps their `recalled`."""
    q = words(about)
    scored = []
    for m in mem["short"] + mem["long"]:
        overlap = len(q & words(m["text"] + " " + m.get("about", "").replace("@", " ")))
        if overlap >= 2:
            scored.append((overlap + 0.15 * m["strength"] + 0.05 * m["recalled"], m))
    scored.sort(key=lambda x: -x[0])
    out = [m for _, m in scored[:k]]
    if bump:
        for m in out:
            m["recalled"] = round(min(RECALLED_MAX, m["recalled"] + RECALL_BUMP), 2)
    return out


def mood_from(recalled: list[dict]) -> float:
    return sum(RECALL_FEEL * m.get("feel", 0.0) for m in recalled)


def public(m: dict) -> dict:
    return {k: m[k] for k in PUBLIC}
