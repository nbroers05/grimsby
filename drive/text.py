"""Small text helpers shared by memory and beliefs (same rules as the old brain.py)."""

from __future__ import annotations

import re

STOP = set("""
the a an and or but of to in on at for with from by is are was were be been being it its this that these those
i me my mine you your he his she her they them their we our us not no nor so as if then than too very just about
into over under again more most some any all can could would should will shall do does did done have has had what
which who whom why how when where there here also only even still like one two three each every much many such
own same other another once ever never always now today tonight hour hours time made make makes thing things
upon while whilst perhaps rather quite really get got let may say see too use way yes yet new old off out day
him per via etc
""".split())


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z]{3,}", (text or "").lower()):
        if w in STOP:
            continue
        if w.endswith("s") and len(w) > 4:
            w = w[:-1]
        out.add(w)
    return out


def similarity(a: str, b: str) -> float:
    """Word overlap (Jaccard) of content words; 0 when fewer than 3 words are shared."""
    wa, wb = words(a), words(b)
    shared = len(wa & wb)
    if shared < 3:
        return 0.0
    return shared / len(wa | wb)
