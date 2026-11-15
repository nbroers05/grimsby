"""From the model's plan (where / size / mood, as words) to real places and scales on a 200 x 200 canvas.

There is a ground line, so things stand on something unless they belong in the air: "top" puts a ground thing on
a row further back (a little smaller), "bottom" on a row in front; sky things (sun, cloud, a flying bird) go high.
"""

from __future__ import annotations

import random

CANVAS = 200
MARGIN = 6
ROWS = {"back": 128.0, "middle": 150.0, "front": 178.0}
ROW_SCALE = {"back": 0.8, "middle": 1.0, "front": 1.05}
SKY_Y = {"top": 34.0, "middle": 46.0, "bottom": 70.0}   # middle of a sky thing
SKY_FOOT_MAX = 116.0
SIZES = {"small": 30.0, "medium": 54.0, "big": 86.0}
COLUMNS = {"left": 50.0, "center": 100.0, "right": 150.0}
LOW_SCALE = 1.5      # things lying flat only use the bottom of their frame
MAIN_MIN = "medium"  # the first thing in the plan (the subject) is never small
NUDGE = 7.0          # px of randomness in a position
MIN_GAP = 0.35       # neighbours may overlap at most this share of the smaller width

WHERE = ["left", "center", "right", "top left", "top", "top right", "bottom left", "bottom", "bottom right"]
SIZE_WORDS = list(SIZES)

# mood -> small things in code: paper tint, tilt (degrees), how many background scribbles, how shaky, accents
MOODS = {
    "content":    dict(paper="#efe9dc", tilt=0.0, scribbles=2, shake=1.0, accents=("eva", "red")),
    "proud":      dict(paper="#f1e7d3", tilt=-1.0, scribbles=1, shake=0.9, accents=("eva", "red")),
    "suspicious": dict(paper="#ece8dc", tilt=-4.0, scribbles=4, shake=1.1, accents=("eva", "eva")),
    "gloomy":     dict(paper="#e7e7e1", tilt=3.0, scribbles=6, shake=1.0, accents=("eva", "eva")),
    "excited":    dict(paper="#f2e6d0", tilt=5.0, scribbles=5, shake=1.45, accents=("red", "eva")),
    "calm":       dict(paper="#ebebe3", tilt=0.0, scribbles=0, shake=0.75, accents=("eva", "eva")),
    "grumpy":     dict(paper="#efe4d6", tilt=4.0, scribbles=7, shake=1.3, accents=("red", "red")),
    "dreamy":     dict(paper="#f0e9df", tilt=-2.0, scribbles=3, shake=0.9, accents=("eva", "red")),
}
MOOD_WORDS = list(MOODS)


def place(objects: list[dict], rng: random.Random) -> list[dict]:
    """objects: dicts with what/where/size/kind/aspect. Adds x, y (foot), s (height), row, flip. Keeps order
    for drawing: sky, back, middle, front; big before small within a row."""
    if objects and objects[0].get("size") == "small":
        objects[0]["size"] = MAIN_MIN
    for o in objects:
        where = o.get("where") if o.get("where") in WHERE else "center"
        parts = where.split()
        col = next((p for p in parts if p in COLUMNS), "center")
        vert = "top" if "top" in parts else "bottom" if "bottom" in parts else "middle"
        s = SIZES.get(o.get("size"), SIZES["medium"])
        if o["kind"] == "sky":
            o["row"], y = "sky", min(SKY_FOOT_MAX, SKY_Y[vert] + s * 0.5)
        else:
            o["row"] = {"top": "back", "bottom": "front"}.get(vert, "middle")
            s *= ROW_SCALE[o["row"]]
            y = ROWS[o["row"]]
            if o["kind"] == "low":
                s *= LOW_SCALE
        w = s * o["aspect"]
        if w > CANVAS - 2 * MARGIN:   # too wide for the paper: shrink it to fit
            s *= (CANVAS - 2 * MARGIN) / w
            w = s * o["aspect"]
        o.update(x=COLUMNS[col] + rng.uniform(-NUDGE, NUDGE), y=y + rng.uniform(-2, 2), s=s, w=w)
    for row in ("sky", "back", "middle", "front"):
        _spread([o for o in objects if o["row"] == row])
    for o in objects:
        o["x"] = min(CANVAS - MARGIN - o["w"] / 2, max(MARGIN + o["w"] / 2, o["x"]))
        o["flip"] = o["x"] > 118 if o.get("faces", True) else False
    order = {"sky": 0, "back": 1, "middle": 2, "front": 3}
    return sorted(objects, key=lambda o: (order[o["row"]], -o["s"]))


def _spread(row: list[dict]) -> None:
    row.sort(key=lambda o: o["x"])
    for _ in range(6):
        moved = False
        for a, b in zip(row, row[1:]):
            room = (a["w"] + b["w"]) / 2 - MIN_GAP * min(a["w"], b["w"])
            if b["x"] - a["x"] < room:
                push = (room - (b["x"] - a["x"])) / 2
                a["x"] -= push
                b["x"] += push
                moved = True
        if not moved:
            break
