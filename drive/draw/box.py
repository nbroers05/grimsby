"""His drawing box: the things he can draw, each a function in code.

Every symbol draws in its own frame: (x, y) is the middle of its foot on the ground, `schaal` its height in canvas
pixels, `variatie` a dict with at least a seed (and maybe a pose, a flip, accent colours). Inside the frame,
P(u, v) means u heights to the right of the middle and v heights up from the foot.

    teken(name, x, y, schaal, variatie) -> svg fragment

Kinds: "ground" things stand on the ground line, "sky" things hang in the air, "low" things lie flat on the ground
(their drawing only uses the lower part of the frame, so layout gives them a bigger frame).
"""

from __future__ import annotations

import math
import random

from .pen import Pen, arc_pts, ellipse_pts

POSES = ["standing", "proud", "suspicious", "pecking", "sleeping", "flying"]


class Frame:
    def __init__(self, x: float, y: float, s: float, flip: bool = False):
        self.x, self.y, self.s, self.dir = x, y, s, (-1 if flip else 1)

    def P(self, u: float, v: float) -> tuple[float, float]:
        return (self.x + u * self.s * self.dir, self.y - v * self.s)

    def Ps(self, *uv) -> list[tuple[float, float]]:
        return [self.P(u, v) for u, v in uv]

    def L(self, v: float) -> float:   # a length
        return v * self.s

    def ell(self, u, v, ru, rv, rng, rot=0.0, k=18, lumpy=0.03):
        cx, cy = self.P(u, v)
        return ellipse_pts(cx, cy, self.L(ru), self.L(rv), rng, rot * self.dir, k, lumpy)


# ---------------------------------------------------------------- birds

CROW_POSE = {   # head (u, v), head radius, body (u, v, ru, rv, rot), beak tilt (deg up), legs
    "standing":   dict(head=(0.22, 0.70), body=(0.0, 0.42, 0.31, 0.19, -18), tilt=0, legs=True),
    "proud":      dict(head=(0.17, 0.82), body=(0.0, 0.46, 0.27, 0.23, -35), tilt=22, legs=True),
    "suspicious": dict(head=(0.24, 0.66), body=(0.0, 0.40, 0.31, 0.19, -12), tilt=-8, legs=True, squint=True),
    "pecking":    dict(head=(0.40, 0.22), body=(0.02, 0.40, 0.31, 0.18, 22), tilt=-60, legs=True),
    "sleeping":   dict(head=(0.16, 0.50), body=(0.0, 0.36, 0.33, 0.25, -8), tilt=-20, legs=False, asleep=True),
}


def _bird(pen: Pen, F: Frame, var: dict, black: bool) -> None:
    rng = pen.rng
    pose = var.get("pose") if var.get("pose") in POSES else "standing"
    if pose == "flying":
        return _bird_flying(pen, F, black)
    p = CROW_POSE[pose]
    bu, bv, bru, brv, brot = p["body"]
    hu, hv = p["head"]
    hr = 0.13 if black else 0.11
    dense = 0.95 if black else 0.35
    # tail first (behind the body)
    tail = F.Ps((bu - bru * 0.7, bv - 0.02), (bu - bru - 0.22, bv - 0.15), (bu - bru - 0.17, bv - 0.21),
                (bu - bru * 0.5, bv - 0.12))
    pen.shape(tail, hatch=dense, cross=black)
    if p.get("legs"):
        for du in (-0.04, 0.07):
            top, foot = F.P(bu + du, bv - brv * 0.8), F.P(bu + du - 0.02, 0)
            pen.line(*top, *foot, w=pen.width * 0.9)
            pen.stroke([F.P(bu + du - 0.09, 0), foot, F.P(bu + du + 0.07, 0)], w=pen.width * 0.8, double=False)
    body = F.ell(bu, bv, bru, brv, rng, brot)
    pen.shape(body, hatch=dense, cross=black)
    # the wing: a curve over the body, with a blue sheen on a crow
    wing = F.Ps((bu + bru * 0.5, bv + brv * 0.4), (bu - bru * 0.1, bv + brv * 0.25), (bu - bru * 0.85, bv - brv * 0.2))
    pen.stroke(wing, w=pen.width * 0.8, c="paper" if black else "ink", double=False)
    if black:
        pen.hatch(F.ell(bu - 0.05, bv + 0.03, bru * 0.55, brv * 0.4, rng, brot), 0.55, "a", angle=20)
    # head
    pen.shape(F.ell(hu, hv, hr, hr, rng, 0, 14), hatch=dense, cross=black)
    t = math.radians(p["tilt"])
    base_top, base_bot = F.P(hu + hr * 0.75, hv + hr * 0.35), F.P(hu + hr * 0.75, hv - hr * 0.3)
    tip = F.P(hu + hr * 0.75 + 0.2 * math.cos(t), hv + 0.2 * math.sin(t))
    pen.shape([base_top, tip, base_bot], hatch=0.9 if black else 0.6, hatch_c="ink")
    ex, ey = F.P(hu + hr * 0.35, hv + hr * 0.25)
    if p.get("asleep"):
        pen.stroke(arc_pts(ex, ey, F.L(0.04), F.L(0.02), 10, 170, 6), w=pen.width * 0.7, c="paper", double=False)
        zx, zy = F.P(hu + 0.18, hv + 0.25)
        pen.text(zx, zy, "z", size=max(5, F.L(0.12)), rotate=-10)
        pen.text(zx + F.L(0.1), zy - F.L(0.12), "z", size=max(4, F.L(0.09)), rotate=-10)
    else:
        pen.dot(ex, ey, max(0.9, F.L(0.035)), "paper")
        pen.dot(ex + F.L(0.01) * F.dir, ey, max(0.5, F.L(0.018)), "ink" if black else "b")
        if p.get("squint"):
            pen.line(ex - F.L(0.05), ey - F.L(0.03), ex + F.L(0.05), ey - F.L(0.005), w=pen.width * 0.9,
                     c="paper" if black else "ink", double=False)


def _bird_flying(pen: Pen, F: Frame, black: bool) -> None:
    rng = pen.rng
    dense = 0.95 if black else 0.35
    up = rng.uniform(0.25, 0.45)
    for side in (-1, 1):   # far wing, then near wing
        wing = F.Ps((-0.12, 0.5), (0.05 * side - 0.1, 0.5 + up + 0.05 * side), (-0.35, 0.5 + up * 0.8), (0.1, 0.5))
        pen.shape(wing, hatch=dense, cross=black)
    pen.shape(F.Ps((-0.3, 0.5), (-0.55, 0.58), (-0.55, 0.42)), hatch=dense)
    pen.shape(F.ell(-0.05, 0.5, 0.3, 0.1, rng, 0), hatch=dense, cross=black)
    pen.shape(F.ell(0.27, 0.53, 0.1, 0.09, rng, 0, 12), hatch=dense, cross=black)
    pen.shape(F.Ps((0.35, 0.56), (0.5, 0.52), (0.35, 0.49)), hatch=0.8)
    ex, ey = F.P(0.3, 0.55)
    pen.dot(ex, ey, max(0.8, F.L(0.03)), "paper")


def crow(pen, F, var):
    _bird(pen, F, var, black=True)


def pigeon(pen, F, var):
    _bird(pen, F, var, black=False)


# ---------------------------------------------------------------- things he collects

def wheel(pen, F, var, cu=0.0, cv=0.5, r=0.48):
    rng = pen.rng
    pen.shape(F.ell(cu, cv, r, r, rng, 0, 22, 0.015), hatch=0)
    pen.stroke(F.ell(cu, cv, r * 0.86, r * 0.86, rng, 0, 22, 0.015), closed=True, w=pen.width * 0.7, double=False)
    for i in range(var.get("spokes", 8)):
        a = math.pi * 2 * i / var.get("spokes", 8) + rng.uniform(-0.08, 0.08)
        pen.line(*F.P(cu, cv), *F.P(cu + r * 0.84 * math.cos(a), cv + r * 0.84 * math.sin(a)), w=pen.width * 0.5,
                 double=False)
    pen.shape(F.ell(cu, cv, 0.05, 0.05, rng, 0, 8), hatch=1)


def bicycle(pen, F, var):
    rear, front, crank = (-0.5, 0.28), (0.5, 0.28), (-0.02, 0.28)
    seat, head = (-0.14, 0.72), (0.36, 0.72)
    for u, v in (rear, front):
        wheel(pen, F, dict(var, spokes=7), u, v, 0.28)
    frame = [(rear, crank), (rear, seat), (seat, crank), (seat, head), (head, crank), (head, front)]
    for a, b in frame:
        pen.line(*F.P(*a), *F.P(*b), c="b", w=pen.width * 1.1)
    pen.stroke(F.Ps((-0.24, 0.8), (-0.04, 0.82)), w=pen.width * 1.6)            # saddle
    pen.line(*F.P(*seat), *F.P(-0.14, 0.8))
    pen.stroke(F.Ps((0.36, 0.72), (0.38, 0.86), (0.5, 0.88)), w=pen.width)      # handlebar
    pen.stroke(F.Ps((-0.1, 0.18), (crank[0], crank[1]), (0.06, 0.38)), w=pen.width * 0.9)   # pedals


def bottle_cap(pen, F, var):
    rng = pen.rng
    side = []
    for i in range(13):    # crimped edge: a zigzag along the bottom
        u = -0.5 + i / 12
        side.append((u, 0.08 if i % 2 else 0.0))
    body = F.Ps((-0.5, 0.42), *side, (0.5, 0.42))
    pen.shape(body, hatch=0.6, hatch_c="b")
    pen.shape(F.ell(0, 0.42, 0.5, 0.17, rng, 0, 20, 0.01), hatch=0.25, hatch_c="b")
    pen.stroke(F.ell(0, 0.43, 0.32, 0.09, rng, 0, 14, 0.02), closed=True, w=pen.width * 0.6, double=False)


def rubber_band(pen, F, var):
    rng = pen.rng
    for k, r in enumerate((1.0, 0.86)):
        pts = F.ell(0, 0.22, 0.5 * r, 0.2 * r, rng, rng.uniform(-8, 8), 22, 0.09)
        pen.stroke(pts, closed=True, c="b" if k == 0 else "ink", w=pen.width * (1.2 if k == 0 else 0.7))
    # one twist, as a rubber band always has
    pen.stroke(F.Ps((0.28, 0.1), (0.36, 0.22), (0.3, 0.36)), w=pen.width * 0.8, double=False)


def teaspoon(pen, F, var):
    rng = pen.rng
    pen.shape(F.ell(-0.62, 0.17, 0.32, 0.16, rng, -6, 16, 0.02), hatch=0.3, hatch_c="a")
    pen.shape(F.Ps((-0.32, 0.2), (0.95, 0.3), (0.97, 0.22), (-0.32, 0.13)), hatch=0.0)
    pen.stroke(F.Ps((-0.75, 0.24), (-0.6, 0.27)), c="paper", w=pen.width * 1.2, double=False)   # shine


def marble(pen, F, var):
    rng = pen.rng
    pen.shape(F.ell(0, 0.5, 0.48, 0.48, rng, 0, 20, 0.015), hatch=0.45, hatch_c="a")
    pen.stroke(F.Ps((-0.3, 0.45), (-0.05, 0.62), (0.2, 0.5), (0.32, 0.25)), c="a", w=pen.width * 1.4)
    pen.stroke(arc_pts(*F.P(-0.18, 0.7), F.L(0.12), F.L(0.07), 200, 300, 5), c="paper", w=pen.width * 1.6,
               double=False)


def button(pen, F, var):
    rng = pen.rng
    pen.shape(F.ell(0, 0.5, 0.48, 0.48, rng, 0, 20, 0.015), hatch=0.3, hatch_c="b")
    pen.stroke(F.ell(0, 0.5, 0.36, 0.36, rng, 0, 16, 0.02), closed=True, w=pen.width * 0.6, double=False)
    for du, dv in ((-0.1, 0.1), (0.1, 0.1), (-0.1, -0.1), (0.1, -0.1)):
        pen.dot(*F.P(du, 0.5 + dv), max(0.8, F.L(0.05)))


def ring_pull(pen, F, var):
    rng = pen.rng
    pen.shape(F.Ps((-0.45, 0.05), (0.15, 0.05), (0.15, 0.35), (-0.45, 0.35)), hatch=0.2)
    pen.stroke(F.ell(-0.15, 0.2, 0.2, 0.09, rng, 0, 12), closed=True, w=pen.width * 0.8)
    pen.stroke(F.ell(0.32, 0.2, 0.18, 0.13, rng, 0, 14), closed=True, w=pen.width * 1.1)


def paperclip(pen, F, var):
    pts = F.Ps((0.1, 0.05), (-0.4, 0.05), (-0.48, 0.15), (-0.4, 0.25), (0.45, 0.25), (0.52, 0.15),
               (0.45, 0.08), (-0.25, 0.08), (-0.3, 0.15), (-0.25, 0.2), (0.3, 0.2))
    pen.stroke(pts, w=pen.width * 1.1, c="a")


def bottle(pen, F, var):
    pen.shape(F.Ps((-0.18, 0.0), (-0.18, 0.55), (-0.07, 0.7), (-0.06, 0.95), (0.06, 0.95), (0.07, 0.7),
                   (0.18, 0.55), (0.18, 0.0)), hatch=0.3, hatch_c="a")
    pen.shape(F.Ps((-0.07, 0.95), (-0.07, 1.0), (0.07, 1.0), (0.07, 0.95)), hatch=1, hatch_c="b")
    pen.stroke(F.Ps((-0.11, 0.1), (-0.11, 0.5)), c="paper", w=pen.width * 1.3, double=False)


def book(pen, F, var):
    pen.shape(F.Ps((-0.5, 0.0), (0.0, 0.05), (0.5, 0.0), (0.5, 0.5), (0.0, 0.55), (-0.5, 0.5)), hatch=0.0)
    pen.line(*F.P(0, 0.05), *F.P(0, 0.55))
    for i in range(4):
        v = 0.15 + i * 0.09
        pen.line(*F.P(-0.4, v), *F.P(-0.1, v + 0.02), w=pen.width * 0.5, double=False)
        pen.line(*F.P(0.1, v + 0.02), *F.P(0.4, v), w=pen.width * 0.5, double=False)


# ---------------------------------------------------------------- the world around him

def sun(pen, F, var):
    rng = pen.rng
    pen.shape(F.ell(0, 0.5, 0.28, 0.28, rng, 0, 18, 0.03), hatch=0.35, hatch_c="b")
    for i in range(11):
        a = 2 * math.pi * i / 11 + rng.uniform(-0.1, 0.1)
        r0, r1 = 0.36, 0.36 + rng.uniform(0.08, 0.16)
        pen.line(*F.P(r0 * math.cos(a), 0.5 + r0 * math.sin(a)), *F.P(r1 * math.cos(a), 0.5 + r1 * math.sin(a)),
                 w=pen.width * 0.8, double=False)


def cloud(pen, F, var):
    rng = pen.rng
    bumps = rng.randint(3, 4)
    pts = [(-0.85, 0.2)]
    for i in range(bumps):
        u0, u1 = -0.85 + 1.7 * i / bumps, -0.85 + 1.7 * (i + 1) / bumps
        r = (u1 - u0) / 2
        h = r * rng.uniform(0.9, 1.3) * (1.35 if 0 < i < bumps - 1 else 1.0)
        for k in range(1, 8):   # a round bump: half an ellipse
            a = math.pi * (1 - k / 7)
            pts.append(((u0 + u1) / 2 + r * math.cos(a), 0.2 + h * math.sin(a)))
    pts.append((0.85, 0.2))
    pen.shape(F.Ps(*pts), hatch=0.0)
    pen.hatch(F.Ps((-0.75, 0.2), (0.75, 0.2), (0.6, 0.3), (-0.6, 0.3)), 0.4, "a", angle=-20)


def tree(pen, F, var):
    rng = pen.rng
    pen.shape(F.Ps((-0.07, 0), (-0.05, 0.45), (0.05, 0.45), (0.08, 0)), hatch=0.7)
    pen.shape(F.ell(0, 0.68, 0.38, 0.32, rng, 0, 18, 0.1), hatch=0.3, cross=False)
    for _ in range(3):
        u, v = rng.uniform(-0.2, 0.2), rng.uniform(0.55, 0.85)
        pen.stroke(arc_pts(*F.P(u, v), F.L(0.07), F.L(0.05), 180, 360, 5), w=pen.width * 0.6, double=False)


def bench(pen, F, var):
    pen.shape(F.Ps((-0.85, 0.32), (0.85, 0.32), (0.85, 0.4), (-0.85, 0.4)), hatch=0.4)
    pen.shape(F.Ps((-0.85, 0.55), (0.85, 0.55), (0.85, 0.66), (-0.85, 0.66)), hatch=0.4)
    for u in (-0.7, 0.7):
        pen.line(*F.P(u, 0), *F.P(u, 0.55), w=pen.width * 1.2)
        pen.line(*F.P(u + 0.06, 0), *F.P(u + 0.06, 0.32), w=pen.width * 0.9)


def house(pen, F, var):
    pen.shape(F.Ps((-0.42, 0), (-0.42, 0.55), (0.42, 0.55), (0.42, 0)), hatch=0.0)
    pen.shape(F.Ps((-0.5, 0.55), (0, 0.98), (0.5, 0.55)), hatch=0.55, hatch_c="a" if var.get("eva_roof") else "ink")
    pen.shape(F.Ps((-0.3, 0), (-0.3, 0.3), (-0.12, 0.3), (-0.12, 0)), hatch=0.5, hatch_c="b")
    pen.shape(F.Ps((0.06, 0.24), (0.06, 0.42), (0.28, 0.42), (0.28, 0.24)), hatch=0.0)
    pen.line(*F.P(0.17, 0.24), *F.P(0.17, 0.42), w=pen.width * 0.6, double=False)
    pen.line(*F.P(0.06, 0.33), *F.P(0.28, 0.33), w=pen.width * 0.6, double=False)


def church(pen, F, var):
    pen.shape(F.Ps((-0.25, 0), (-0.25, 0.75), (0.0, 0.92), (0.0, 0)), hatch=0.0)          # tower
    pen.shape(F.Ps((-0.27, 0.75), (-0.125, 1.0), (0.02, 0.75)), hatch=0.7)
    pen.line(*F.P(-0.125, 1.0), *F.P(-0.125, 1.12))
    pen.line(*F.P(-0.17, 1.07), *F.P(-0.08, 1.07))
    pen.shape(F.Ps((0.0, 0), (0.0, 0.45), (0.5, 0.45), (0.5, 0)), hatch=0.0)              # nave
    pen.shape(F.Ps((-0.02, 0.45), (0.25, 0.68), (0.52, 0.45)), hatch=0.55)
    pen.shape(F.Ps((-0.17, 0), (-0.17, 0.22), (-0.08, 0.28), (0.0, 0.22), (0.0, 0)), hatch=0.6, hatch_c="b",
              under=False)
    for u in (0.14, 0.33):
        pen.shape(F.Ps((u, 0.15), (u, 0.32), (u + 0.05, 0.36), (u + 0.1, 0.32), (u + 0.1, 0.15)), hatch=0.4,
                  hatch_c="a")


def shop(pen, F, var):
    pen.shape(F.Ps((-0.6, 0), (-0.6, 0.75), (0.6, 0.75), (0.6, 0)), hatch=0.0)
    stripes = 6
    for i in range(stripes):   # the striped awning
        u0, u1 = -0.66 + 1.32 * i / stripes, -0.66 + 1.32 * (i + 1) / stripes
        pen.shape(F.Ps((u0, 0.62), (u0 + 0.03, 0.72), (u1 + 0.03, 0.72), (u1, 0.62)),
                  hatch=0.8 if i % 2 else 0.0, hatch_c="b", double=False)
    pen.shape(F.Ps((-0.5, 0.08), (-0.5, 0.5), (0.05, 0.5), (0.05, 0.08)), hatch=0.15, hatch_c="a")
    pen.shape(F.Ps((0.18, 0), (0.18, 0.5), (0.45, 0.5), (0.45, 0)), hatch=0.0)
    pen.shape(F.Ps((-0.4, 0.78), (-0.4, 0.95), (0.4, 0.95), (0.4, 0.78)), hatch=0.0)
    pen.stroke(F.Ps((-0.3, 0.86), (-0.1, 0.88), (0.05, 0.85), (0.28, 0.87)), w=pen.width * 0.7, double=False)


def windmill(pen, F, var):
    rng = pen.rng
    pen.shape(F.Ps((-0.25, 0), (-0.15, 0.62), (0.15, 0.62), (0.25, 0)), hatch=0.25)
    pen.shape(F.Ps((-0.17, 0.62), (0, 0.76), (0.17, 0.62)), hatch=0.7)
    pen.shape(F.Ps((-0.07, 0), (-0.07, 0.15), (0.07, 0.15), (0.07, 0)), hatch=0.7, hatch_c="b")
    hub = (0, 0.66)
    a0 = rng.uniform(0, 90)
    for k in range(4):
        a = math.radians(a0 + 90 * k)
        ca, sa = math.cos(a), math.sin(a)
        tip = (hub[0] + 0.5 * ca, hub[1] + 0.5 * sa)
        pen.line(*F.P(*hub), *F.P(*tip), w=pen.width * 1.1)
        side = (-sa * 0.11, ca * 0.11)   # the lattice sail beside the arm
        p1, p2 = (hub[0] + 0.12 * ca, hub[1] + 0.12 * sa), tip
        sail = [p1, p2, (p2[0] + side[0], p2[1] + side[1]), (p1[0] + side[0], p1[1] + side[1])]
        pen.shape(F.Ps(*sail), hatch=0.45, cross=True, under=False, double=False)
    pen.dot(*F.P(*hub), max(1.0, F.L(0.025)))


def fountain(pen, F, var):
    rng = pen.rng
    pen.shape(F.Ps((-0.6, 0), (-0.6, 0.18), (0.6, 0.18), (0.6, 0)), hatch=0.3)
    pen.shape(F.ell(0, 0.18, 0.6, 0.07, rng, 0, 18, 0.01), hatch=0.4, hatch_c="a")
    pen.shape(F.Ps((-0.05, 0.18), (-0.05, 0.5), (0.05, 0.5), (0.05, 0.18)), hatch=0.4)
    pen.shape(F.ell(0, 0.5, 0.25, 0.04, rng, 0, 14, 0.01), hatch=0.0)
    for side in (-1, 1):
        for k in (0.7, 1.0):
            pen.stroke([F.P(0, 0.55), F.P(side * 0.15 * k, 0.8 * k), F.P(side * 0.32 * k, 0.6), F.P(side * 0.42 * k, 0.25)],
                       c="a", w=pen.width * 0.8, double=False)


def station(pen, F, var):
    pen.shape(F.Ps((-0.95, 0), (-0.95, 0.12), (0.95, 0.12), (0.95, 0)), hatch=0.4)           # platform
    for u in (-0.7, 0.7):
        pen.line(*F.P(u, 0.12), *F.P(u, 0.62), w=pen.width * 1.2)
    pen.shape(F.Ps((-0.85, 0.62), (0.85, 0.62), (0.95, 0.72), (-0.95, 0.72)), hatch=0.6, hatch_c="a")  # roof
    pen.shape(F.Ps((-0.2, 0.42), (-0.2, 0.55), (0.2, 0.55), (0.2, 0.42)), hatch=0.0)
    pen.text(*F.P(-0.15, 0.455), "M", size=max(4, F.L(0.1)), c="b")


def metro(pen, F, var):
    rng = pen.rng
    pen.line(*F.P(-1.3, 0.0), *F.P(1.3, 0.0), w=pen.width * 0.8)
    pen.shape(F.Ps((-1.25, 0.08), (-1.25, 0.82), (1.05, 0.82), (1.25, 0.6), (1.25, 0.08)), hatch=0.0)
    pen.shape(F.Ps((-1.25, 0.2), (1.25, 0.2), (1.25, 0.3), (-1.25, 0.3)), hatch=0.9, hatch_c="a", under=False)
    for i in range(5):
        u = -1.1 + i * 0.43
        pen.shape(F.Ps((u, 0.45), (u, 0.7), (u + 0.3, 0.7), (u + 0.3, 0.45)), hatch=0.15)
    for u in (-0.9, -0.6, 0.6, 0.9):
        pen.shape(F.ell(u, 0.06, 0.07, 0.07, rng, 0, 10), hatch=1)


def fish(pen, F, var):
    rng = pen.rng
    pen.shape(F.Ps((-0.55, 0.5), (-0.8, 0.72), (-0.78, 0.28)), hatch=0.5, hatch_c="a")
    pen.shape(F.ell(0, 0.5, 0.55, 0.26, rng, 0, 20, 0.02), hatch=0.25, hatch_c="a")
    pen.dot(*F.P(0.35, 0.56), max(0.8, F.L(0.035)))
    for i in range(3):
        pen.stroke(arc_pts(*F.P(-0.15 + i * 0.15, 0.5), F.L(0.07), F.L(0.12), -60, 60, 5), w=pen.width * 0.5,
                   double=False)


def plinth(pen, F, var):
    """A memorial stone."""
    pen.shape(F.Ps((-0.4, 0), (-0.35, 0.55), (0.35, 0.55), (0.4, 0)), hatch=0.3)
    pen.shape(F.Ps((-0.48, 0), (-0.48, 0.08), (0.48, 0.08), (0.48, 0)), hatch=0.6)
    for i in range(3):
        v = 0.4 - i * 0.1
        pen.line(*F.P(-0.22, v), *F.P(0.22, v), w=pen.width * 0.5, double=False)


def trolley(pen, F, var):
    rng = pen.rng
    pen.shape(F.Ps((-0.55, 0.85), (0.5, 0.85), (0.4, 0.35), (-0.45, 0.35)), hatch=0.45, cross=True, under=False)
    pen.stroke(F.Ps((-0.55, 0.85), (-0.75, 0.95)), w=pen.width * 1.1)
    pen.stroke(F.Ps((-0.45, 0.35), (-0.42, 0.12), (0.4, 0.12)), w=pen.width)
    for u in (-0.38, 0.32):
        pen.shape(F.ell(u, 0.06, 0.06, 0.06, rng, 0, 10), hatch=1)


def fries(pen, F, var):
    for i in range(6):
        u = -0.25 + i * 0.1
        pen.shape(F.Ps((u, 0.5), (u + 0.04, 0.95 - (i % 3) * 0.08), (u + 0.09, 0.93 - (i % 2) * 0.1), (u + 0.08, 0.5)),
                  hatch=0.2, under=True, double=False)
    pen.shape(F.Ps((-0.35, 0), (-0.42, 0.62), (0.42, 0.62), (0.35, 0)), hatch=0.7, hatch_c="b")


def bin_(pen, F, var):
    pen.shape(F.Ps((-0.35, 0), (-0.4, 0.8), (0.4, 0.8), (0.35, 0)), hatch=0.0)
    pen.shape(F.Ps((-0.45, 0.8), (-0.45, 0.9), (0.45, 0.9), (0.45, 0.8)), hatch=0.6)
    for u in (-0.18, 0.0, 0.18):
        pen.line(*F.P(u, 0.1), *F.P(u * 1.1, 0.7), w=pen.width * 0.6, double=False)


def worm(pen, F, var):
    pts = [(-0.6 + 1.2 * i / 14, 0.06 + 0.08 * math.sin(i * 1.1)) for i in range(15)]
    pen.stroke(F.Ps(*pts), w=max(2.0, F.L(0.08)), c="b", double=False)


# ---------------------------------------------------------------- registry

SYMBOLS = {   # name: (function, width/height, kind)
    "crow": (crow, 1.05, "ground"), "pigeon": (pigeon, 0.95, "ground"),
    "bicycle": (bicycle, 1.7, "ground"), "wheel": (wheel, 1.0, "ground"),
    "bottle cap": (bottle_cap, 1.0, "ground"), "rubber band": (rubber_band, 1.0, "low"),
    "teaspoon": (teaspoon, 1.9, "low"), "marble": (marble, 1.0, "ground"), "button": (button, 1.0, "ground"),
    "ring pull": (ring_pull, 1.0, "low"), "paperclip": (paperclip, 1.0, "low"), "bottle": (bottle, 0.4, "ground"),
    "book": (book, 1.0, "ground"),
    "sun": (sun, 1.0, "sky"), "cloud": (cloud, 1.7, "sky"), "tree": (tree, 0.8, "ground"),
    "bench": (bench, 1.75, "ground"), "house": (house, 1.0, "ground"), "church": (church, 0.8, "ground"),
    "shop": (shop, 1.3, "ground"), "windmill": (windmill, 1.0, "ground"), "fountain": (fountain, 1.25, "ground"),
    "station": (station, 1.9, "ground"), "metro": (metro, 2.6, "ground"), "fish": (fish, 1.6, "ground"),
    "memorial": (plinth, 1.0, "ground"), "trolley": (trolley, 1.4, "ground"), "fries": (fries, 0.9, "ground"),
    "bin": (bin_, 0.9, "ground"), "worm": (worm, 1.2, "low"),
}

# words the model uses for things in the box (matched as whole words, longest first)
ALIASES = {
    "raven": "crow", "rook": "crow", "jackdaw": "crow", "grimsby": "crow", "myself": "crow", "me": "crow",
    "dove": "pigeon", "derek": "pigeon", "gull": "pigeon", "bird": "pigeon", "pigeons": "pigeon",
    "bike": "bicycle", "cycle": "bicycle", "tyre": "wheel", "tire": "wheel", "pneumatic tire": "wheel",
    "cap": "bottle cap", "bottlecap": "bottle cap", "crown cork": "bottle cap", "cork": "bottle cap", "lid": "bottle cap", "bottle caps": "bottle cap",
    "elastic": "rubber band", "elastic band": "rubber band", "rubber": "rubber band",
    "spoon": "teaspoon", "tea spoon": "teaspoon",
    "ringpull": "ring pull", "pull tab": "ring pull", "tab": "ring pull",
    "paper clip": "paperclip", "clip": "paperclip",
    "diary": "book", "list": "book", "notebook": "book", "library": "book",
    "moon": "sun", "weather": "cloud", "rain": "cloud", "rain cloud": "cloud",
    "oak": "tree", "bush": "tree", "plantsoen": "tree",
    "seat": "bench", "home": "house", "roof": "house",
    "dorpskerk": "church", "bron": "church", "chapel": "church", "tower": "church",
    "albert heijn": "shop", "jumbo": "shop", "supermarket": "shop", "store": "shop", "mcdonald": "shop",
    "turk": "shop", "cafe": "shop", "terrace": "shop", "kebab": "shop",
    "mill": "windmill", "hichte": "windmill", "valk": "windmill", "ondermolen": "memorial",
    "stone": "memorial", "statue": "memorial", "monument": "memorial",
    "platform": "station", "train": "metro", "tram": "metro",
    "vis": "fish", "cart": "trolley", "shopping cart": "trolley", "chips": "fries", "french fries": "fries",
    "rubbish bin": "bin", "trash can": "bin", "dustbin": "bin", "bins": "bin",
}


def width_for(schaal: float) -> float:
    return max(1.0, min(2.2, 0.8 + schaal / 70))


def teken(name: str, x: float, y: float, schaal: float, variatie: dict) -> str:
    rng = random.Random(variatie.get("seed", 0))
    pen = Pen(rng, shake=variatie.get("shake", 1.0), accents=variatie.get("accents", ("#1556cf", "#de2f1f")),
              width=width_for(schaal), paper=variatie.get("paper", "#efe9dc"))
    fn = SYMBOLS[name][0]
    fn(pen, Frame(x, y, schaal, variatie.get("flip", False)), variatie)
    return pen.svg()
