"""Symbols he learned himself: his vocabulary grows with practice.

When a thing is not in the box, the model draws only that thing in a 50 x 50 box with at most 8 shapes. That SVG
goes through safety.clean_svg, and then it is taken apart into plain outlines (points in the 50 x 50 box, plus
whether it was filled and in which colour family). It is never used as SVG again: it is redrawn with his pen,
in his colours, so it looks like the rest of his work.

Saved in <dir>/<name>.json with a counter. Every RETRY_EVERY drawings he tries it once more and keeps the version
that is least broken (score: more shapes inside the box, fewer points on or over the edge).
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import safety
from .pen import Pen

BOX = 50.0
MAX_SHAPES = 8
EDGE = 1.5           # points closer than this to the edge count as touching it
MIN_INSIDE = 0.8     # at least this share of points must lie inside the box
RETRY_EVERY = 5


def key(name: str) -> str:
    return re.sub(r"[^a-z ]", "", name.lower()).strip()[:30]


def path_for(d: Path, name: str) -> Path:
    return d / (key(name).replace(" ", "-") + ".json")


def load(d: Path, name: str) -> dict | None:
    p = path_for(d, name)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(d: Path, item: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    path_for(d, item["name"]).write_text(json.dumps(item, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def count(d: Path) -> int:
    return len(list(d.glob("*.json"))) if d.exists() else 0


# ---------------------------------------------------------------- taking an SVG apart

NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _nums(s: str | None) -> list[float]:
    return [float(x) for x in NUM.findall(s or "")]


def _path_pts(d: str) -> list[tuple[list, bool]]:
    """A small path parser: M L H V C S Q T A Z, absolute and relative. Curves become a few points."""
    toks = re.findall(r"[MLHVCSQTAZmlhvcsqtaz]|" + NUM.pattern, d or "")
    out, cur, closed = [], [], False
    x = y = sx = sy = 0.0
    cmd, i = None, 0
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    out.append((cur, True))
                cur, x, y = [], sx, sy
            continue
        if cmd is None:
            break
        need = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}[cmd.upper()]
        args = toks[i:i + need]
        if len(args) < need:
            break
        a = [float(v) for v in args]
        i += need
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            if cur:
                out.append((cur, False))
            x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            sx, sy, cur = x, y, [(x, y)]
            cmd = "l" if rel else "L"
            continue
        if c == "H":
            x = x + a[0] if rel else a[0]
        elif c == "V":
            y = y + a[0] if rel else a[0]
        elif c in "CSQ":
            ox, oy = (x, y) if rel else (0, 0)
            ctrl = [(ox + a[k], oy + a[k + 1]) for k in range(0, len(a) - 2, 2)]
            end = (ox + a[-2], oy + a[-1])
            p0 = (x, y)
            pts = [p0, *ctrl, end]
            for s in range(1, 5):   # sample the curve (de Casteljau)
                q = list(pts)
                tt = s / 4
                while len(q) > 1:
                    q = [(q[k][0] + (q[k + 1][0] - q[k][0]) * tt, q[k][1] + (q[k + 1][1] - q[k][1]) * tt)
                         for k in range(len(q) - 1)]
                cur.append(q[0])
            x, y = end
            continue
        else:   # L, T, A: straight to the end point
            x, y = (x + a[-2], y + a[-1]) if rel else (a[-2], a[-1])
        cur.append((x, y))
    if cur:
        out.append((cur, closed))
    return out


def _family(colour: str | None) -> str | None:
    """none / which of his colours a fill becomes: dark -> ink, blue-ish -> a, red/warm -> b, light -> none."""
    c = (colour or "").strip().lower()
    if not c or c in ("none", "transparent"):
        return None
    named = {"black": "ink", "blue": "a", "navy": "a", "red": "b", "orange": "b", "brown": "ink", "grey": "ink",
             "gray": "ink", "white": None, "yellow": "b", "green": "a", "silver": "ink", "gold": "b"}
    if c in named:
        return named[c]
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", c)
    if not m:
        return "ink"
    h = m.group(1)
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[k:k + 2], 16) for k in (0, 2, 4))
    if r + g + b > 600:
        return None
    if b > r + 30 and b > g - 10:
        return "a"
    if r > b + 40:
        return "b"
    return "ink"


def parse(raw_svg: str) -> list[dict]:
    """Model SVG -> outlines in the 50 x 50 box. Raises ValueError when there is nothing usable."""
    clean, _ = safety.clean_svg(raw_svg, min_shapes=1)
    root = ET.fromstring(clean)
    vb = _nums(root.get("viewBox")) or [0, 0, BOX, BOX]
    vx, vy, vw, vh = (vb + [0, 0, BOX, BOX])[:4] if len(vb) >= 4 else (0, 0, BOX, BOX)
    fx, fy = BOX / (vw or BOX), BOX / (vh or BOX)
    shapes = []
    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        g = lambda k, dflt=0.0: (_nums(el.get(k)) or [dflt])[0]   # noqa: E731
        fill = _family(el.get("fill", "#000" if tag in ("rect", "circle", "ellipse", "polygon", "path") else "none"))
        stroke = _family(el.get("stroke"))
        runs: list[tuple[list, bool]] = []
        if tag == "rect":
            x, y, w, h = g("x"), g("y"), g("width"), g("height")
            runs = [([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)]
        elif tag in ("circle", "ellipse"):
            cx, cy = g("cx"), g("cy")
            rx = g("r") if tag == "circle" else g("rx")
            ry = g("r") if tag == "circle" else g("ry")
            runs = [([(cx + rx * math.cos(2 * math.pi * k / 16), cy + ry * math.sin(2 * math.pi * k / 16))
                      for k in range(16)], True)]
        elif tag == "line":
            runs = [([(g("x1"), g("y1")), (g("x2"), g("y2"))], False)]
        elif tag in ("polyline", "polygon"):
            v = _nums(el.get("points"))
            runs = [(list(zip(v[::2], v[1::2])), tag == "polygon")]
        elif tag == "path":
            runs = _path_pts(el.get("d", ""))
        for pts, closed in runs:
            pts = [((px - vx) * fx, (py - vy) * fy) for px, py in pts]
            if len(pts) < 2:
                continue
            closed = closed or (fill is not None and len(pts) > 2)
            shapes.append({"pts": [[round(px, 1), round(py, 1)] for px, py in pts], "closed": closed,
                           "fill": fill if closed else None, "stroke": stroke or "ink"})
            if len(shapes) >= MAX_SHAPES:
                return shapes
    if not shapes:
        raise ValueError("nothing drawable in the symbol")
    return shapes


def score(shapes: list[dict]) -> float:
    pts = [p for s in shapes for p in s["pts"]]
    if not pts:
        return 0.0
    inside = sum(1 for x, y in pts if EDGE <= x <= BOX - EDGE and EDGE <= y <= BOX - EDGE) / len(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    fills = min(1.0, (max(xs) - min(xs)) * (max(ys) - min(ys)) / (BOX * BOX * 0.35))   # uses the box, not a speck
    return round(len(shapes) * inside * (0.5 + 0.5 * fills), 2)


def valid(shapes: list[dict]) -> bool:
    pts = [p for s in shapes for p in s["pts"]]
    inside = sum(1 for x, y in pts if 0 <= x <= BOX and 0 <= y <= BOX) / max(1, len(pts))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    big_enough = (max(xs) - min(xs)) > 8 or (max(ys) - min(ys)) > 8
    return inside >= MIN_INSIDE and big_enough


# ---------------------------------------------------------------- drawing it again, with his pen

def render(pen: Pen, shapes: list[dict], x: float, y: float, schaal: float, flip: bool = False) -> None:
    """(x, y) is the middle of the foot, schaal the height in pixels: the 50 x 50 box is scaled to it."""
    k = schaal / BOX
    def tr(p):   # noqa: E306
        px = (p[0] - BOX / 2) * k
        return (x + (-px if flip else px), y - (BOX - min(BOX, max(0.0, p[1]))) * k)
    for s in shapes:
        pts = [tr((min(BOX, max(0.0, px)), py)) for px, py in s["pts"]]
        if s["closed"]:
            pen.shape(pts, hatch=0.55 if s["fill"] else 0.0, hatch_c=s["fill"] or "ink", c=s["stroke"])
        else:
            pen.stroke(pts, c=s["stroke"])
