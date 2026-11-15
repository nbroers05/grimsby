"""Drawing v2: the model thinks up what is in the picture (a plan as JSON, see voice.drawing), code draws it.

    make(plan, rng, learned_dir, ask_symbol) -> {"svg": ..., "objects": [...]}

Every object in the plan is looked up: first in the box (box.py, by name or alias), then among the symbols he
learned (learned.py). If neither has it, `ask_symbol(name)` asks the model for just that symbol (at most
MAX_NEW per drawing); a valid one is kept and he can draw it from then on.
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

from . import box, layout, learned
from .pen import EVA, INK, RED, Pen

MAX_OBJECTS = 5
HOARD = {"bottle cap", "teaspoon", "marble", "button", "ring pull", "paperclip"}
MAX_HOARD = 1        # at most one thing from his collection in a drawing that is not about it
MAX_SAME = 3        # at most this many of one symbol in a drawing
MAX_NEW = 2          # at most this many extra LLM calls (new symbols or a retry) per drawing
ACCENT = {"eva": EVA, "red": RED}
MAX_SVG = 60000


class Empty(ValueError):
    """Nothing in the plan could be drawn."""


def norm(what: str) -> str:
    s = re.sub(r"[^a-z' ]", " ", (what or "").lower()).replace("'s", "").replace("'", "")
    s = re.sub(r"\b(a|an|the|some|my|his|of|small|big|little|tiny|large|old|shiny|one|two|three)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve(what: str) -> tuple[str, str]:
    """-> ("box", symbol) or ("learned"/"new", key)."""
    s = norm(what)
    names = sorted(list(box.SYMBOLS) + list(box.ALIASES), key=len, reverse=True)
    words = s.split()
    singular = " ".join(w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 3 else w for w in words)
    for text in (s, singular):
        for name in names:
            if re.search(rf"\b{re.escape(name)}\b", text):
                return "box", box.ALIASES.get(name, name)
    k = learned.key(singular)
    return ("new", k) if k else ("none", "")


def make(plan: dict, rng: random.Random, learned_dir: Path, ask_symbol=None) -> dict:
    mood = layout.MOODS.get(plan.get("mood"), layout.MOODS["content"])
    accents = tuple(ACCENT[a] for a in mood["accents"])
    budget = MAX_NEW
    objs = []
    subject = resolve(plan.get("_subject", ""))[1]
    for o in (plan.get("objects") or [])[:MAX_OBJECTS]:
        what = str(o.get("what", ""))[:40]
        how, name = resolve(what)
        rec = {"what": what, "where": o.get("where"), "size": o.get("size"), "pose": o.get("pose")}
        if sum(1 for x in objs if x.get("symbol") == name) >= MAX_SAME:
            continue
        if how == "box" and name in HOARD and name != subject:   # his collection creeps into everything
            if sum(1 for x in objs if x.get("symbol") in HOARD and x.get("symbol") != subject) >= MAX_HOARD:
                continue
        if how == "box":
            fn, aspect, kind = box.SYMBOLS[name]
            if name in ("crow", "pigeon") and o.get("pose") == "flying":
                kind = "sky"
            rec.update(symbol=name, drawn="box", kind=kind, aspect=aspect)
        elif how == "new":
            item = learned.load(learned_dir, name)
            due = item and item["drawn"] > 0 and item["drawn"] % learned.RETRY_EVERY == 0
            if (item is None or due) and ask_symbol and budget > 0:
                budget -= 1
                if item is not None:
                    item["tries"] = item.get("tries", 1) + 1
                try:
                    shapes = learned.parse(ask_symbol(name))
                    if learned.valid(shapes):
                        new = {"name": name, "shapes": shapes, "score": learned.score(shapes)}
                        if item is None:
                            item = dict(new, drawn=0, tries=1, learned=plan.get("_when", ""))
                        elif new["score"] > item["score"]:
                            item.update(shapes=shapes, score=new["score"])
                except Exception:  # noqa: BLE001 - a broken symbol is just not learned this time
                    pass
            if item is None:
                rec["drawn"] = "skipped"
                objs.append(rec)
                continue
            rec.update(symbol=name, drawn="learned", kind="ground", aspect=1.0, _item=item)
        else:
            rec["drawn"] = "skipped"
            objs.append(rec)
            continue
        objs.append(rec)
    drawable = [o for o in objs if o["drawn"] != "skipped"]
    if not drawable:
        raise Empty("nothing in the plan could be drawn")
    layout.place(drawable, rng)

    pen = Pen(rng, shake=mood["shake"], accents=accents, paper=mood["paper"])
    _background(pen, mood, rng)
    parts = [pen.svg()]
    for o in drawable:
        var = {"seed": rng.random(), "pose": o.get("pose"), "flip": o["flip"], "accents": accents,
               "shake": mood["shake"], "paper": mood["paper"]}
        if o["drawn"] == "box":
            parts.append(box.teken(o["symbol"], o["x"], o["y"], o["s"], var))
        else:
            p = Pen(random.Random(var["seed"]), shake=mood["shake"], accents=accents, paper=mood["paper"],
                    width=box.width_for(o["s"]))
            learned.render(p, o["_item"]["shapes"], o["x"], o["y"], o["s"], o["flip"])
            parts.append(p.svg())
            item = o.pop("_item")
            item["drawn"] += 1
            learned.save(learned_dir, item)
    sig = Pen(rng, paper=mood["paper"])
    sig.text(184 + rng.uniform(-3, 3), 194, "G.", size=8, rotate=rng.uniform(-12, 4))
    tilt = mood["tilt"] * rng.uniform(0.6, 1.2)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
           f'<rect width="200" height="200" fill="{mood["paper"]}"/>'
           f'<g transform="rotate({tilt:.1f} 100 100)">{"".join(parts)}</g>{sig.svg()}</svg>')
    for o in objs:
        for k in ("kind", "aspect", "x", "y", "s", "w", "row", "flip", "_item"):
            o.pop(k, None)
    return {"svg": svg, "objects": objs, "mood": plan.get("mood")}


def _background(pen: Pen, mood: dict, rng: random.Random) -> None:
    """The ground line with a few tufts and pebbles, and the mood's scribbles in the empty sky."""
    y0 = 150 + rng.uniform(-3, 3)
    pen.stroke([(-4, y0 + rng.uniform(-2, 2)), (60, y0 + rng.uniform(-2, 2)), (140, y0 + rng.uniform(-2, 2)),
                (204, y0 + rng.uniform(-2, 2))], w=1.4)
    pen.hatch([(-4, y0 + 2), (204, y0 + 2), (204, 204), (-4, 204)], 0.12, angle=-30, w=0.5)
    for _ in range(rng.randint(3, 6)):
        x = rng.uniform(8, 192)
        for k in range(rng.randint(2, 3)):
            pen.line(x + k * 2.5, y0, x + k * 2.5 + rng.uniform(-2, 2), y0 - rng.uniform(3, 6), w=0.8, double=False)
    for _ in range(mood["scribbles"]):
        x, y = rng.uniform(12, 188), rng.uniform(12, 70)
        kind = rng.random()
        if kind < 0.4:     # a little loop
            pts = [(x + (4 + i * 0.6) * math.cos(i * 0.9), y + (3 + i * 0.4) * math.sin(i * 0.9))
                   for i in range(14)]
            pen.stroke(pts, w=0.7, double=False, opacity=0.55)
        elif kind < 0.75:  # a patch of hatching
            pen.hatch([(x, y), (x + 14, y + 2), (x + 12, y + 12), (x - 2, y + 10)], 0.5, w=0.6)
        else:              # a few ticks
            for k in range(4):
                pen.line(x + k * 4, y, x + k * 4 + 2, y + 5, w=0.7, double=False, opacity=0.6)


__all__ = ["make", "resolve", "Empty", "MAX_OBJECTS", "INK"]
