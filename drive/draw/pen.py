"""His pen. Every drawing goes through here, so everything he makes looks like his: ink on paper, at most two
accent colours, every line a little shaky (like rough.js: each stretch of line gets a few pixels of noise),
contours often drawn twice, and shading as slanted hatching instead of flat fills.

All coordinates are canvas pixels (200 x 200). A Pen collects path strings; `svg()` gives the joined fragment.
Hatch lines of one shape go into one <path> (several M..L runs), which keeps a drawing well under the size limit.
"""

from __future__ import annotations

import math
import random

INK = "#16130f"
PAPER = "#efe9dc"
EVA = "#1556cf"
RED = "#de2f1f"

SEG = 7.0            # px of line per wobble point
JITTER = 0.9         # px of noise per wobble point (times the pen's shake)
DOUBLE = 0.7         # chance a contour gets a second, thinner stroke
DOUBLE_OFFSET = 0.9  # px the second stroke wanders from the first
OVERSHOOT = 0.06     # closed shapes overshoot their start a little, like a quick hand
HATCH_ANGLE = -55    # degrees
HATCH_SHAKE = 0.5    # hatch lines are calmer than contours


def n(v: float) -> str:
    s = f"{v:.1f}"
    return "0" if s in ("-0.0", "0.0") else s.rstrip("0").rstrip(".")


class Pen:
    def __init__(self, rng: random.Random, shake: float = 1.0, accents: tuple[str, str] = (EVA, RED),
                 width: float = 1.5, paper: str = PAPER):
        self.rng = rng
        self.paper = paper
        self.shake = shake
        self.accents = accents
        self.width = width
        self.parts: list[str] = []

    # ------------------------------------------------------------ helpers
    def colour(self, c: str) -> str:
        return {"ink": INK, "paper": self.paper, "a": self.accents[0], "b": self.accents[1]}.get(c, c)

    def wobble(self, pts: list[tuple[float, float]], closed: bool, shake: float = 1.0) -> list[tuple[float, float]]:
        if closed:
            pts = pts + [pts[0]]
        out = []
        amp = JITTER * self.shake * shake
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / SEG))
            for i in range(steps):
                t = i / steps
                out.append((x1 + (x2 - x1) * t + self.rng.gauss(0, amp), y1 + (y2 - y1) * t + self.rng.gauss(0, amp)))
        out.append((pts[-1][0] + self.rng.gauss(0, amp), pts[-1][1] + self.rng.gauss(0, amp)))
        if closed and len(out) > 3:   # overshoot: carry on past the start for a bit
            k = max(1, int(len(out) * OVERSHOOT))
            out += [(x + self.rng.gauss(0, amp), y + self.rng.gauss(0, amp)) for x, y in out[1:k + 1]]
        return out

    @staticmethod
    def d(pts: list[tuple[float, float]]) -> str:
        return "M" + "L".join(f"{n(x)} {n(y)}" for x, y in pts)

    # ------------------------------------------------------------ marks
    def stroke(self, pts, closed=False, w: float | None = None, c="ink", double: bool | None = None,
               shake: float = 1.0, opacity: float = 1.0) -> None:
        if len(pts) < 2:
            return
        w = self.width if w is None else w
        op = f' stroke-opacity="{n(opacity)}"' if opacity < 1 else ""
        style = f'fill="none" stroke="{self.colour(c)}" stroke-linecap="round" stroke-linejoin="round"'
        self.parts.append(f'<path d="{self.d(self.wobble(list(pts), closed, shake))}" {style} '
                          f'stroke-width="{n(w)}"{op}/>')
        if double if double is not None else self.rng.random() < DOUBLE:
            moved = [(x + self.rng.gauss(0, DOUBLE_OFFSET), y + self.rng.gauss(0, DOUBLE_OFFSET)) for x, y in pts]
            self.parts.append(f'<path d="{self.d(self.wobble(moved, closed, shake))}" {style} '
                              f'stroke-width="{n(w * 0.55)}" stroke-opacity="0.75"/>')

    def line(self, x1, y1, x2, y2, **kw) -> None:
        self.stroke([(x1, y1), (x2, y2)], **kw)

    def under(self, pts) -> None:
        """Paper behind a shape, so what is behind it does not show through. Not a visible fill."""
        self.parts.append(f'<path d="{self.d(pts)}Z" fill="{self.paper}"/>')

    def shape(self, pts, closed=True, w=None, c="ink", hatch: float = 0.0, hatch_c="ink", cross=False,
              under=True, double=None) -> None:
        """A contour, optionally shaded. hatch: 0 = none, 1 = as dense as he can."""
        pts = list(pts)
        if closed and under:
            self.under(pts)
        if closed and hatch > 0:
            self.hatch(pts, hatch, hatch_c, cross=cross)
        self.stroke(pts, closed, w, c, double)

    def hatch(self, pts, density: float, c="ink", angle: float = HATCH_ANGLE, cross=False, w=None) -> None:
        gap = max(1.6, 7.5 - 6.0 * min(1.0, density))
        self._hatch(pts, gap, c, angle, w)
        if cross:
            self._hatch(pts, gap * 1.15, c, angle + 80, w)

    def _hatch(self, pts, gap, c, angle, w) -> None:
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        rot = [(x * ca + y * sa, -x * sa + y * ca) for x, y in pts]
        ys = [p[1] for p in rot]
        y = min(ys) + self.rng.uniform(0.2, 0.9) * gap
        runs = []
        edges = list(zip(rot, rot[1:] + rot[:1]))
        while y < max(ys):
            xs = sorted(x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                        for (x1, y1), (x2, y2) in edges if (y1 <= y < y2) or (y2 <= y < y1))
            for x1, x2 in zip(xs[::2], xs[1::2]):
                x1, x2 = x1 + self.rng.uniform(0.2, 1.2), x2 - self.rng.uniform(0.2, 1.2)
                if x2 - x1 > 1.2:
                    yy = y + self.rng.gauss(0, 0.25)
                    seg = [(x1, yy), (x2, yy + self.rng.gauss(0, 0.4))]
                    seg = [(x * ca - v * sa, x * sa + v * ca) for x, v in seg]
                    runs.append(self.d(self.wobble(seg, False, HATCH_SHAKE)))
            y += gap * self.rng.uniform(0.85, 1.15)
        if runs:
            w = (self.width * 0.55) if w is None else w
            self.parts.append(f'<path d="{"".join(runs)}" fill="none" stroke="{self.colour(c)}" '
                              f'stroke-width="{n(w)}" stroke-linecap="round"/>')

    def dot(self, x, y, r, c="ink") -> None:
        self.parts.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{self.colour(c)}"/>')

    def text(self, x, y, s: str, size=7.0, c="ink", rotate=0.0) -> None:
        t = f' transform="rotate({n(rotate)} {n(x)} {n(y)})"' if rotate else ""
        safe = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.parts.append(f'<text x="{n(x)}" y="{n(y)}" font-family="Comic Sans MS, Segoe Print, cursive" '
                          f'font-size="{n(size)}" fill="{self.colour(c)}"{t}>{safe}</text>')

    def svg(self) -> str:
        return "".join(self.parts)


# ---------------------------------------------------------------- point helpers

def ellipse_pts(cx, cy, rx, ry, rng: random.Random, rot: float = 0.0, k: int = 18, lumpy: float = 0.03):
    r = math.radians(rot)
    out = []
    for i in range(k):
        t = 2 * math.pi * i / k
        f = 1 + rng.gauss(0, lumpy)
        x, y = rx * f * math.cos(t), ry * f * math.sin(t)
        out.append((cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)))
    return out


def arc_pts(cx, cy, rx, ry, a0, a1, k=10):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / k)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / k))) for i in range(k + 1)]
