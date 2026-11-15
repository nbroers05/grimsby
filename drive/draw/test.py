"""Test sheet for drawing v2: 10 drawings with the real model, from a read-only copy of his live state.

    .venv\\Scripts\\python -m drive.draw.test [--n 10] [--seed 1]

Writes to drive/test/tekenen/ (not in git): tekeningen.html with every drawing next to the plan the model made,
plus tekendoos.html (every symbol in the box, no model). Learned symbols go to drive/test/tekenen/learned, never
to his real vocabulary.
"""

from __future__ import annotations

import argparse
import html
import json
import random
import time
from datetime import datetime
from pathlib import Path

from .. import safety, voice
from . import MAX_SVG, box, make

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "drive" / "test" / "tekenen"
HOARD = ["the bottle caps", "the teaspoon", "a shiny button", "a ring pull", "a blue marble", "a bent paperclip"]
PAGE = ("<!doctype html><meta charset=utf-8><title>{title}</title><style>body{{font-family:system-ui,sans-serif;"
        "background:#ddd;margin:16px}}.c{{display:inline-block;vertical-align:top;width:300px;margin:8px;"
        "background:#fff;padding:8px;font-size:12px}}svg{{width:300px;height:300px;display:block}}"
        "pre{{white-space:pre-wrap;font-size:10.5px;background:#f4f4f4;padding:4px}}</style><h2>{title}</h2>{body}")


def sheet() -> None:
    cells = []
    for name in box.SYMBOLS:
        poses = box.POSES if name in ("crow", "pigeon") else [None]
        for pz in poses:
            plan = {"mood": "content", "objects": [{"what": name, "where": "center", "size": "big", "pose": pz}]}
            pic = make(plan, random.Random(len(cells)), OUT / "learned")
            svg, _ = safety.clean_svg(pic["svg"], max_len=MAX_SVG)
            cells.append(f'<div class=c style="width:180px">{svg.replace("<svg", "<svg style=width:180px;height:180px", 1)}'
                         f'{name}{f" ({pz})" if pz else ""}</div>')
    (OUT / "tekendoos.html").write_text(PAGE.format(title="Tekendoos (zonder LLM)", body="".join(cells)),
                                        encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    sheet()
    state = json.loads((ROOT / "drive" / "live" / "state.json").read_text(encoding="utf-8"))
    rng = random.Random(a.seed)
    topics = [t["topic"] for t in sorted(state.get("topics", []), key=lambda t: -t["strength"])] or ["bottle caps"]
    # his interests first (that is what the plan asks), then two from his collection and some places
    subjects = topics[:5] + rng.sample(HOARD, 2) + ["the windmill at De Hichte", "the fountain by the station",
                                                    "the Jumbo"]
    cells = []
    for i, subject in enumerate(subjects[:a.n]):
        t0 = time.time()
        try:
            plan = voice.drawing(state, datetime.now().astimezone(), subject)
            plan["_when"], plan["_subject"] = datetime.now().isoformat(timespec="seconds"), subject
            pic = make(plan, rng, OUT / "learned", voice.symbol)
            svg, _ = safety.clean_svg(pic["svg"], max_len=MAX_SVG)
            shown = {k: plan[k] for k in ("title", "caption", "mood")}
            shown["objects"] = pic["objects"]
            cells.append(f"<div class=c>{svg}<b>{html.escape(subject)}</b> ({time.time() - t0:.0f}s, "
                         f"{len(svg) // 1000} kB)<pre>{html.escape(json.dumps(shown, indent=1, ensure_ascii=False))}"
                         "</pre></div>")
            print(f"{i + 1}. {subject}: {[o['what'] + '/' + o['drawn'] for o in pic['objects']]}")
        except Exception as e:  # noqa: BLE001 - show the failure on the sheet too
            cells.append(f"<div class=c><b>{html.escape(subject)}</b><pre>failed: {html.escape(repr(e))}</pre></div>")
            print(f"{i + 1}. {subject}: FAILED {e!r}")
        (OUT / "tekeningen.html").write_text(PAGE.format(title="Tekenen v2: 10 testtekeningen", body="".join(cells)),
                                             encoding="utf-8")


if __name__ == "__main__":
    main()
