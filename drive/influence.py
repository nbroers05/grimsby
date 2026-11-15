"""Visitors can influence him (VOLGENDE.md block G), the way people influence each other: he hears it, weighs it
and does something with it, or not. All in code; the model only talks. A visitor's text never starts a tool or an
action: it can only move numbers through the routes below.

Routes:
  suggestion  a place and/or action from a fixed list (places.json, actions) -> a bonus (or, with negative trust,
              a penalty) for that action@place in his choice, salience = trust x social need, fading over about a
              world day; also an item in his working memory (in code's words, never the visitor's)
  topic       a question or "about X" -> an open question, marked with who planted it. He may search it later:
              the model writes the query in his own words, and a query too close to the visitor's text is refused
              (too_close, used by act.do_search)
  opinion     "the Jumbo is better (than ...)" -> weak evidence on his V for that place: OPINION_WEIGHT of one own
              experience x trust. His own experience keeps coming, so in the end it wins
  item        a left item: code decides whether he takes it to his roof; then a memory, his hoard, a little mood,
              and a matching interest grows
  sheet       visitors cannot write on his character sheet, but repeated influence by one visitor over several
              days can make sleep propose a line ("mostly listens to Sanne", or the opposite)
How he took the note (notes.py stance, no mirror) decides how much of it counts (SHARE).
Ceiling: per visitor per world day at most PER_DAY of each route and BONUS_DAY_MAX of suggestion bonus.

Trust lives in a small profile per visitor (by name). It starts at TRUST_START and stays there until brain v3
point 8 (BREIN-v3.md, phase 3) lets it learn.
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta

from . import attend, clock, learn, memory, mind, safety, world
from .actions import ACTIONS
from .text import words

CHARACTER_ID = "grimsby"
TRUST_START = 0.3              # a stranger: some benefit of the doubt (-1..1)
SUGGEST_BONUS = 0.3            # utility of a suggestion at salience 1 (trust 1 x social need 1)
SUGGEST_PLACE_ONLY = 0.5       # a place without an action: this share, for any action there
SUGGEST_HOURS = 3.0            # real hours a suggestion lasts (= one world day), fading linearly
SUGGEST_TOTAL_MAX = 0.2        # all suggestions together never add more than this to one action@place
OPINION_WEIGHT = 0.3           # one opinion = this share of one own experience (x trust)
OPINION_SIZE = 0.06            # "better" = his average V + this, "worse" = - this
TOPIC_WORDS = 8                # a planted question is at most this many of the visitor's words
PER_DAY = {"suggest": 3, "topic": 1, "opinion": 2, "item": 3}
BONUS_DAY_MAX = 0.2            # sum of |suggestion bonus| one visitor may add per world day
TAKE_BASE = 0.35               # chance he takes an item: base + curiosity + trust - quiet (below)
TAKE_MOOD = 0.03
HOARD_MAX = 12
SHEET_TIMES = 6                # influence events by one visitor...
SHEET_DAYS = 3                 # ...over this many world days...
SHEET_TRUST = 0.35             # ...with |trust| above this -> a candidate line for his character sheet
# how much of each route counts, per stance (notes.py). Negative = it works the other way (he is being contrary).
SHARE = {
    "answer":   {"suggest": 1.0, "topic": 1.0, "opinion": 1.0},
    "disagree": {"suggest": 0.5, "topic": 1.0, "opinion": 0.0},
    "ignore":   {"suggest": 0.0, "topic": 1.0, "opinion": 0.5},
    "misread":  {"suggest": 0.0, "topic": 0.0, "opinion": 0.0},
    "refuse":   {"suggest": -0.5, "topic": 0.0, "opinion": 0.0},
}

# ---------------------------------------------------------------- recognising places, actions, opinions
PLACE_WORDS = {
    "albert-heijn": ["albert heijn", "the ah", "ah", "appie"],
    "jumbo": ["jumbo"],
    "mcdonalds": ["mcdonald's", "mcdonalds", "mcdonald", "macdonalds", "mac", "mcd"],
    "de-turk": ["de turk", "the turk", "turk", "döner", "doner", "kebab"],
    "library": ["library", "bibliotheek", "bieb"],
    "vis": ["fish statue", "vis"],
    "dorpskerk": ["dorpskerk", "village church", "old church"],
    "de-bron": ["de bron", "bron"],
    "hichte-mill": ["de hichte", "hichte"],
    "de-valk": ["de valk", "valk"],
    "home": ["your roof", "station roof", "the roof", "your nest", "home"],
    "station-fountain": ["fountain by the station", "station fountain"],
    "centre-fountain": ["fountain in the centre", "centre fountain", "center fountain", "fountain"],
    "station-bench": ["bench by the station"],
    "plantsoen-bench": ["plantsoen", "griffel", "the park"],
    "ondermolen": ["ondermolen", "memorial", "millstone"],
}
ACTION_WORDS = {
    "draw": ["draw", "drawing", "sketch", "doodle", "teken", "tekenen"],
    "diary": ["diary", "write", "writing", "dagboek", "schrijf", "schrijven"],
    "search": ["look up", "look it up", "search", "google", "find out", "opzoeken", "zoek"],
    "eat": ["eat", "food", "hungry", "snack", "lunch", "chips", "fries", "eten", "honger", "patat"],
    "pigeons": ["pigeon", "pigeons", "duif", "duiven"],
    "sit": ["sit", "rest", "sit still", "zitten", "zit"],
    "wander": ["fly around", "explore", "look around", "wander", "rondvliegen", "rondkijken"],
    "tidy": ["tidy", "your hoard", "opruimen"],
    "read_back": ["re-read", "reread", "read back", "teruglezen"],
    "neighbour": ["pino"],
}
CUE = re.compile(r"\b(go|try|you should|should|why don't you|why not|let's|come|visit|check out|ga|probeer|"
                 r"moet je|kom|bezoek|naar)\b", re.I)
GOOD = re.compile(r"\b(better|best|great|good|nice|tasty|lovely|delicious|cosy|cozy|beter|beste|lekker|leuk|"
                  r"goed|mooi|fijn)\b", re.I)
BAD = re.compile(r"\b(worse|worst|bad|terrible|awful|gross|vile|boring|disgusting|slechter|slecht|vies|smerig|"
                 r"saai|stom)\b", re.I)
THAN = re.compile(r"\b(than|dan)\b", re.I)
QUESTION_LEAD = re.compile(r"^(hi|hey|hello|hallo|hoi|dear|beste)?[\s,!]*(grimsby)?[\s,!]*"
                           r"(do you know|did you know|have you ever wondered|weet jij|weet je|wist je)?[\s,]*", re.I)
ABOUT = re.compile(r"\b(?:about|over)\s+([a-zà-ÿ' -]{3,60})", re.I)


def _find(text: str, table: dict[str, list[str]]) -> list[tuple[int, str]]:
    """(position, key) of every key whose words occur in the text, longest words first, no overlaps."""
    low, taken, out = text.lower(), [], []
    pairs = sorted(((w, k) for k, ws in table.items() for w in ws), key=lambda p: -len(p[0]))
    for w, k in pairs:
        for m in re.finditer(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", low):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            out.append((m.start(), k))
    return sorted(out)


def places_in(text: str) -> list[str]:
    seen = []
    for _, k in _find(text, PLACE_WORDS):
        if k not in seen and k in world.places():
            seen.append(k)
    return seen


def actions_in(text: str) -> list[str]:
    seen = []
    for _, k in _find(text, ACTION_WORDS):
        if k not in seen and k in ACTIONS:
            seen.append(k)
    return seen


def suggestions_in(text: str) -> list[tuple[str | None, str | None]]:
    """(action, place) pairs a note suggests. A place counts on its own; an action only with a nudge word
    ("go", "try", "you should") or a place, so "why do pigeons nod?" is a topic, not an errand."""
    pl, ac = places_in(text), actions_in(text)
    if not pl and not (ac and CUE.search(text)):
        return []
    if len(pl) >= 2 and THAN.search(text):
        pl = pl[:1]                                   # "X is better than Y": only X is a suggestion
    out = []
    for p in pl[:2]:
        fit = [a for a in ac if a in world.place(p)["actions"]]
        out += [(a, p) for a in fit[:1]] or [(None, p)]
    if not pl:
        out = [(a, None) for a in ac[:1]]
    return out


def opinions_in(text: str) -> list[tuple[str, int]]:
    """(place, +1/-1). "X is better than Y" -> X +1, Y -1. One place with a good or bad word -> that sign."""
    pl = places_in(text)
    good, bad = bool(GOOD.search(text)), bool(BAD.search(text))
    if not pl or good == bad:
        return []
    sign = 1 if good else -1
    if len(pl) >= 2 and THAN.search(text):
        return [(pl[0], sign), (pl[1], -sign)]
    return [(pl[0], sign)]


def topic_in(text: str) -> str | None:
    """A question or "about X" from the note, as a few of the visitor's words (lowercase, cleaned)."""
    m = ABOUT.search(text)
    subject = m.group(1) if m else None
    if not subject:
        q = next((s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip().endswith("?")), None)
        if not q:
            return None
        subject = QUESTION_LEAD.sub("", q.strip()).rstrip("?").strip()
    subject = re.sub(r"[^a-zà-ÿ0-9' -]", " ", subject.lower())
    ws = subject.split()[:TOPIC_WORDS]
    if len([w for w in ws if len(w) > 2]) < 2:
        return None
    return " ".join(ws)


def too_close(query: str, subject: str) -> bool:
    """Is a search query (nearly) the visitor's own words? Then it may not be used (block G)."""
    q, s = words(query), words(subject)
    if not q or not s:
        return False
    if " ".join(sorted(q)) == " ".join(sorted(s)) or subject.lower().strip() in query.lower():
        return True
    return len(q & s) / len(q | s) >= 0.7


# ---------------------------------------------------------------- visitors' profiles and the ceiling
def key_of(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())[:24]


def profile(s: dict, name: str, real: datetime) -> dict:
    vs = s.setdefault("visitors", {})
    k = key_of(name)
    p = vs.setdefault(k, {"name": name.strip()[:24], "trust": TRUST_START, "notes": 0, "feel": 0.0, "items": [],
                          "since": real.isoformat(timespec="seconds"), "day": None, "used": {}, "days": [],
                          "times": 0, "character_id": s.get("character_id", CHARACTER_ID)})
    day = clock.world(real)["day"]
    if p["day"] != day:
        p["day"], p["used"] = day, {}
    return p


def room(p: dict, route: str, amount: float = 1.0) -> bool:
    """Is there room under the ceiling for this visitor today? Counts it if so."""
    used = p["used"]
    if used.get(route, 0) + 1 > PER_DAY[route]:
        return False
    if route == "suggest" and used.get("bonus", 0.0) + abs(amount) > BONUS_DAY_MAX + 1e-9:
        return False
    used[route] = used.get(route, 0) + 1
    if route == "suggest":
        used["bonus"] = round(used.get("bonus", 0.0) + abs(amount), 4)
    return True


def mark(p: dict, real: datetime) -> None:
    p["times"] += 1
    day = clock.world(real)["day"]
    if day not in p["days"]:
        p["days"] = (p["days"] + [day])[-30:]


# ---------------------------------------------------------------- receiving a note
def receive(s: dict, text: str, author: str, stance: str, real: datetime) -> dict:
    """After notes.py chose how he takes it: what of it gets through. Returns what happened, per route."""
    p = profile(s, author, real)
    p["notes"] += 1
    out = {"suggest": [], "topic": None, "opinion": [], "capped": []}
    share = SHARE.get(stance, {})
    if not text or safety.suspicious(text):
        return out
    social = s["needs"].get("social", 0.0)

    for action, place in suggestions_in(text):
        sh = share.get("suggest", 0.0)
        if not sh:
            continue
        size = SUGGEST_BONUS * abs(p["trust"]) * social * abs(sh) * (1.0 if action else SUGGEST_PLACE_ONLY)
        sign = -1 if (p["trust"] < 0 or sh < 0) else 1
        if size < 1e-4:
            continue
        if not room(p, "suggest", size):
            out["capped"].append(("suggest", action, place))
            continue
        until = (real + timedelta(hours=SUGGEST_HOURS)).isoformat(timespec="seconds")
        sug = {"from": key_of(author), "action": action, "place": place, "bonus": round(sign * size, 4),
               "since": real.isoformat(timespec="seconds"), "until": until}
        s["suggestions"] = [x for x in s.get("suggestions", []) if x["until"] > sug["since"]] + [sug]
        out["suggest"].append(sug)
        mark(p, real)
        what = (ACTIONS[action].doing if action else "going") + (f" {world.words(place)}" if place else "")
        verb = "suggested" if sign > 0 else "wants me to try"
        attend.consider(s, [attend.item(f"suggest:{key_of(author)}", "suggestion", what,
                                        f"{p['name']} {verb} {what}" + ("" if sign > 0 else " (you'd rather not)"),
                                        abs(p["trust"]) * social + 0.1)])

    subject = topic_in(text)
    if subject and share.get("topic") and not safety.suspicious(subject):
        if room(p, "topic"):
            if mind.open_item(s, "question", subject, real, f"An open question, from {p['name']}: {subject}?",
                              via=key_of(author)):
                out["topic"] = subject
                mark(p, real)
        else:
            out["capped"].append(("topic", subject))

    for place, sign in opinions_in(text):
        w = OPINION_WEIGHT * share.get("opinion", 0.0) * p["trust"]
        if abs(w) < 1e-4:
            continue
        if not room(p, "opinion"):
            out["capped"].append(("opinion", place))
            continue
        target = learn.average(s) + sign * OPINION_SIZE
        for action in world.place(place)["actions"]:
            if action in ("sit", "idle", "sleep"):
                continue
            v = s.setdefault("values", {}).setdefault(f"{action}@{place}", {"V": 0.0, "n": 0, "fail": 0.0, "var": 0.0})
            v["V"] = round(v["V"] + learn.ALPHA * w * (target - v["V"]), 5)
            v["n"] = round(v["n"] + abs(w), 3)            # weak evidence: counts a little towards a belief
            v["heard"] = round(v.get("heard", 0.0) + abs(w), 3)
        out["opinion"].append((place, sign, round(w, 3)))
        mark(p, real)
    return out


def bonus(s: dict, action: str, place: str, real: datetime) -> float:
    """What visitors' suggestions add to (or take from) action@place right now, fading as they age."""
    total, now = 0.0, real.isoformat(timespec="seconds")
    for x in s.get("suggestions", []):
        if x["until"] <= now:
            continue
        if x["action"] and x["action"] != action:
            continue
        if x["place"] and x["place"] != place:
            continue
        a, b = datetime.fromisoformat(x["since"]), datetime.fromisoformat(x["until"])
        left = max(0.0, (b - real).total_seconds() / max(1.0, (b - a).total_seconds()))
        total += x["bonus"] * left
    return max(-SUGGEST_TOTAL_MAX, min(SUGGEST_TOTAL_MAX, total))


# ---------------------------------------------------------------- items
ITEM_RE = re.compile(r"[^a-zà-ÿ0-9' -]")


def item_words(item: str) -> str:
    ws = ITEM_RE.sub(" ", (item or "").lower()).split()
    while ws and ws[0] in ("a", "an", "the", "een", "de", "het", "some", "my"):
        ws = ws[1:]
    return " ".join(ws[:4])


def consider_item(s: dict, item: str, author: str, real: datetime, rng: random.Random) -> dict:
    """A left item: does he take it to his roof? Code decides. Returns {"taken", "item", "chance"}."""
    thing = item_words(item)
    if not thing or thing == "note" or safety.suspicious(thing):
        return {"taken": False, "item": thing, "chance": 0.0}
    p = profile(s, author, real)
    n = s["needs"]
    chance = max(0.05, min(0.95, TAKE_BASE + 0.3 * n.get("curiosity", 0) + 0.3 * p["trust"] - 0.3 * n.get("quiet", 0)))
    if not room(p, "item") or rng.random() >= chance:
        return {"taken": False, "item": thing, "chance": round(chance, 2)}
    label = f"{p['name']}'s {thing}"
    s["hoard_extra"] = (s.get("hoard_extra", []) + [{"item": thing, "from": p["name"],
                                                     "since": real.isoformat(timespec="seconds")}])[-HOARD_MAX:]
    p["items"] = (p["items"] + [thing])[-10:]
    s["mood"] = max(-1.0, min(1.0, s["mood"] + TAKE_MOOD))
    memory.add(s["memories"]["short"], memory.make(f"Took {label} back to the roof.", "moment", 3, real, 0.2,
                                                   "hoard@home"), memory.SHORT_MAX)
    tw = words(thing)
    for t in s.get("topics", []):                     # it colours his interests a little
        if words(t["topic"]) & tw:
            t["strength"] = round(t["strength"] + 1.0, 2)
    mark(p, real)
    return {"taken": True, "item": thing, "chance": round(chance, 2)}


def hoard(s: dict) -> list[str]:
    """What he can tidy: visitors' things he took, in his words."""
    return [f"{x['from']}'s {x['item']}" for x in s.get("hoard_extra", [])]


# ---------------------------------------------------------------- the character sheet (asked by sleep.py)
NAME_OK = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' -]{0,23}$")


def sheet_candidate(s: dict) -> tuple[str, str] | None:
    """Repeated influence by one visitor over several days -> a plain line for his sheet (sleep words it)."""
    for p in sorted(s.get("visitors", {}).values(), key=lambda p: -p["times"]):
        if p.get("on_sheet") or p["times"] < SHEET_TIMES or len(p["days"]) < SHEET_DAYS:
            continue
        if not NAME_OK.match(p["name"]) or safety.suspicious(p["name"]):
            continue
        if p["trust"] >= SHEET_TRUST:
            p["on_sheet"] = True
            return "quirks", f"mostly listens to {p['name']}, though he would deny it"
        if p["trust"] <= -SHEET_TRUST:
            p["on_sheet"] = True
            return "quirks", f"does the opposite of whatever {p['name']} suggests"
    return None
