"""Grimsby's world as his brain knows it: world/places.json. Places, where they are, what can happen there.

He is always at one place (state["at"]). Going somewhere else takes travel ticks and costs energy, so the
choice of action and place weighs how far away it is. The brain knows nothing about the 3D world; the `obj` and
`category` fields in places.json are only passed on to the site.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

PLACES_FILE = Path(__file__).resolve().parent.parent / "world" / "places.json"
HOME = "home"
# The island (EILAND.md) is Berkel at toy scale: places are ~14x closer than on the old map. For his body the
# village should feel as far as Berkel did, or every flight is free and he flits about all day. So distances
# count x FEEL_SCALE ("crow km"); the 3D world still flies the real metres. Checked in drive.sim (15-11-2026):
# with this, place changes and flying ticks per day stay close to the old map.
FEEL_SCALE = 14.0
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
    return math.hypot(pa["x"] - pb["x"], pa["z"] - pb["z"]) / 1000 * FEEL_SCALE


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


ISLAND_NEWS = ("Woke up and everything was different. Water everywhere. The station is called Rodenrijs now. "
               "The Jumbo is still there, unfortunately.")


def migrate_state(s: dict) -> bool:
    """Bring his state up to the current world. Returns changed.
    v1: old place categories -> place ids (beliefs, their stats, memories, the running action).
    v2: the island (EILAND.md). Ids stay the same, so nothing moves in his head; only `island_news` is set, so the
    loop tells him once (run.load). Old memories that say Westpolder stay: that is his history."""
    if s.get("world_version", 0) == 1:
        s["world_version"] = 2
        s["island_news"] = True
        who = s.get("who", {})                       # his address on the character sheet is a fact, not a choice
        if isinstance(who.get("core"), str):
            who["core"] = who["core"].replace("station Berkel Westpolder", "station Rodenrijs")
        return True
    if s.get("world_version", 0) >= 2:
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
    migrate_state(s)
    return True
