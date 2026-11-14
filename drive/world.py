"""Grimsby's world as his brain knows it: world/places.json. Places, where they are, what can happen there.

He is always at one place (state["at"]). Going somewhere else takes travel ticks and costs energy, so the
choice of action and place weighs how far away it is. The brain knows nothing about the 3D world; the `poi` and
`category` fields in places.json are only passed on to the site.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

PLACES_FILE = Path(__file__).resolve().parent.parent / "world" / "places.json"
HOME = "home"
KM_PER_TICK = 1.2              # a crow in no hurry: 1.2 km per tick (12 world minutes)
ENERGY_PER_KM = 0.04
TRAVEL_COST = 0.035            # utility lost per km...
TIRED_TRAVEL = 2.0             # ...times (1 + this x how tired he is)

# brain v2 before step 12 used place categories; this is where each one went
OLD_CATEGORY = {"library": "library", "bench": "plantsoen-bench", "church": "dorpskerk", "windmill": "hichte-mill",
                "artwork": "vis", "fountain": "centre-fountain", "home": "home"}


@lru_cache(maxsize=1)
def places() -> dict[str, dict]:
    data = json.loads(PLACES_FILE.read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["places"]}


def place(pid: str) -> dict:
    return places().get(pid) or places()[HOME]


def places_for(action: str, here: str = HOME) -> list[str]:
    if action == "wander":                   # anywhere but home and where he already is
        return [pid for pid in places() if pid not in (HOME, here)]
    if action == "idle":                     # right where he is
        return [here]
    return [pid for pid, p in places().items() if action in p["actions"]]


def km(a: str, b: str) -> float:
    pa, pb = place(a), place(b)
    return math.hypot(pa["x"] - pb["x"], pa["z"] - pb["z"]) / 1000


def travel_ticks(a: str, b: str) -> int:
    return 0 if a == b else max(1, math.ceil(km(a, b) / KM_PER_TICK))


def travel_cost(a: str, b: str, energy: float) -> float:
    return TRAVEL_COST * km(a, b) * (1 + TIRED_TRAVEL * max(0.0, -energy))


def words(pid: str) -> str:
    return place(pid)["words"]


def name(pid: str) -> str:
    return place(pid)["name"]


def feel(action: str, pid: str) -> float:
    p = place(pid)
    return p.get("feel", 0.0) + p.get("feel_for", {}).get(action, 0.0)


def migrate_state(s: dict) -> bool:
    """Old place categories -> place ids (beliefs, their stats, memories, the running action). Returns changed."""
    if s.get("world_version") == 1:
        return False
    conv = lambda key: (lambda a, p: f"{a}@{OLD_CATEGORY.get(p, p)}")(*key.split("@", 1)) if "@" in key else key  # noqa: E731
    s["belief_stats"] = {conv(k): v for k, v in s.get("belief_stats", {}).items()}
    for b in s.get("beliefs", []):
        b["about"] = conv(b["about"])
    for m in s["memories"]["short"] + s["memories"]["long"]:
        if m.get("about") and not m["about"].startswith("day@"):
            m["about"] = conv(m["about"])
    for key in ("doing", "pending", "pending_done"):
        if s.get(key) and s[key].get("place"):
            s[key]["place"] = OLD_CATEGORY.get(s[key]["place"], s[key]["place"])
    s.setdefault("at", s["doing"]["place"] if s.get("doing") else HOME)
    s["world_version"] = 1
    return True
