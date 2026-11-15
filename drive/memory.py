"""Short- and long-term memory, small on purpose.

Every memory: text, kind (fact | person | work | moment), strength (1-5), recalled (how often it came back),
since. Internal fields stay out of the public JSON: `feel` (how it felt, -1..1; recalling it nudges mood),
`about` (action@place, for beliefs and dedupe), and from brain v3: `surprise` (the prediction error of that
action), `outcome` (what it really gave, for replay), `S` (stability, world days), `last` (when he last thought
of it) and `touched` (how often).

Brain v3, phase 2, forgetting along a curve: retention = exp(-t / S), t = world days since `last`. Each time a
memory comes back (`touch`), S grows, more when it had nearly slipped away (spacing effect), and its feel moves a
little towards his mood now (reconsolidation). Emotional and strong memories start with a higher S. Below
FORGET_AT a memory is gone at night, even with room to spare (sleep.consolidate).

Something new only gets in by pushing out something weaker (lowest strength x (1 + recalled) x retention).
"""

from __future__ import annotations

import math
from datetime import datetime

from . import clock
from .text import similarity, words

SHORT_MAX = 30
LONG_MAX = 60
KINDS = ("fact", "person", "work", "moment")
SAME = 0.5                     # similarity above this = the same memory again: reinforce instead of adding
RECALL_FEEL = 0.02             # mood nudge per recalled memory, times its feel
RECALL_BUMP = 0.25             # recall happens often; a memory needs many recalls to really stick
RECALLED_MAX = 10.0
PUBLIC = ("text", "kind", "strength", "recalled", "since")

# ---- brain v3: the forgetting curve
S_BASE = 1.0                   # world days of stability for an ordinary memory (strength 2, no feeling); at 1.5
                               # nothing faded within 5 sim nights
S_STRENGTH = 2.0               # x this per strength step above 2 (strength 5 = 8 world days)
S_FEEL = 1.5                   # x (1 + S_FEEL * |feel|): emotional memories last longer
S_GAIN = 2.0                   # on recall: S *= 1 + S_GAIN_MIN + S_GAIN * (1 - retention)  (spacing effect)
S_GAIN_MIN = 0.02              # ...so thinking of it again straight away hardly helps
S_MAX = 120.0
FORGET_AT = 0.1                # retention under this = gone (checked at night)
RECON = 0.1                    # on recall, feel moves this share of the way towards his mood now

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


# ---------------------------------------------------------------- the forgetting curve

def start_stability(strength: float, feel: float) -> float:
    return round(S_BASE * S_STRENGTH ** (strength - 2) * (1 + S_FEEL * abs(feel)), 3)


def stability(m: dict) -> float:
    return m.get("S") or start_stability(m["strength"], m.get("feel", 0.0))


def age(m: dict, real: datetime) -> float:
    """World days since he last thought of it."""
    last = datetime.fromisoformat(m.get("last") or m["since"])
    return max(0.0, (clock.world_minutes(real) - clock.world_minutes(last)) / 1440)


def retention(m: dict, real: datetime | None) -> float:
    return 1.0 if real is None else math.exp(-age(m, real) / stability(m))


def setup(mem: dict, real: datetime) -> int:
    """Old memories get S, and their clock starts now (otherwise half the archive would go in one night)."""
    n = 0
    for m in mem["short"] + mem["long"]:
        if "S" not in m:
            m["S"] = start_stability(m["strength"], m.get("feel", 0.0))
            m["last"] = real.isoformat(timespec="seconds")
            n += 1
    return n


def touch(m: dict, real: datetime, mood: float | None = None) -> None:
    """He thought of it: it becomes more stable (more so after a gap), and is coloured by his mood now."""
    r = retention(m, real)
    m["S"] = round(min(S_MAX, stability(m) * (1 + S_GAIN_MIN + S_GAIN * (1 - r))), 3)
    m["last"] = real.isoformat(timespec="seconds")
    m["touched"] = m.get("touched", 0) + 1
    if mood is not None:
        m["feel"] = round(m.get("feel", 0.0) + RECON * (mood - m.get("feel", 0.0)), 3)


def keep_score(m: dict, real: datetime | None = None) -> float:
    return m["strength"] * (1 + m["recalled"]) * retention(m, real)


# ---------------------------------------------------------------- storing and recalling

def make(text: str, kind: str, strength: float, real: datetime, feel: float = 0.0, about: str = "") -> dict:
    assert kind in KINDS, kind
    strength += holds_to_fit(text)                   # principles act as a filter: fitting things stick
    strength = max(1, min(5, round(strength)))
    now = real.isoformat(timespec="seconds")
    return {"text": text, "kind": kind, "strength": strength, "recalled": 0.0, "since": now,
            "feel": round(feel, 3), "about": about, "S": start_stability(strength, feel), "last": now}


def add(store: list, new: dict, limit: int) -> dict:
    """Put `new` into `store`. Returns {"added"|"reinforced"|"refused": text, "dropped": text?}."""
    real = datetime.fromisoformat(new["since"])
    for m in store:
        if new["about"].startswith("day@"):      # every day's summary is its own memory
            break
        if (new["about"] and new["about"] == m.get("about") and new["text"] == m["text"]) \
                or similarity(new["text"], m["text"]) >= SAME:
            m["strength"] = min(5, m["strength"] + 1)
            m["recalled"] = round(min(RECALLED_MAX, m["recalled"] + 0.5), 2)
            if m is not new and new.get("last", "") >= m.get("last", ""):
                touch(m, datetime.fromisoformat(new["last"]))   # living it again = thinking of it
            return {"reinforced": m["text"]}
    if len(store) < limit:
        store.append(new)
        return {"added": new["text"]}
    weakest = min(store, key=lambda m: keep_score(m, real))
    if keep_score(new, real) < keep_score(weakest, real):
        return {"refused": new["text"]}
    store.remove(weakest)
    store.append(new)
    return {"added": new["text"], "dropped": weakest["text"]}


def recall(mem: dict, about: str, k: int = 3, bump: bool = True, real: datetime | None = None,
           mood: float | None = None) -> list[dict]:
    """The few most relevant memories for `about` (short and long together). `bump` raises their `recalled`;
    with `real` they also count as thought of (touch: stability up, feel towards `mood`). Fading memories come up
    less easily."""
    q = words(about)
    scored = []
    for m in mem["short"] + mem["long"]:
        overlap = len(q & words(m["text"] + " " + m.get("about", "").replace("@", " ")))
        if overlap >= 2:
            scored.append((overlap + 0.15 * m["strength"] + 0.05 * m["recalled"] + 0.5 * retention(m, real), m))
    scored.sort(key=lambda x: -x[0])
    out = [m for _, m in scored[:k]]
    for m in out:
        if bump:
            m["recalled"] = round(min(RECALLED_MAX, m["recalled"] + RECALL_BUMP), 2)
        if real is not None:
            touch(m, real, mood)
    return out


def mood_from(recalled: list[dict]) -> float:
    return sum(RECALL_FEEL * m.get("feel", 0.0) for m in recalled)


def public(m: dict) -> dict:
    return {k: m[k] for k in PUBLIC}
