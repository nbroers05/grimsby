"""One-off: turn the old state.json + log.json into drive/state_v2.json. Reads only; changes nothing old.

  ..\\.venv\\Scripts\\python -m drive.migrate_v2        (from the grimsby folder: .venv\\Scripts\\python -m drive.migrate_v2)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import engine, memory, who

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).with_name("state_v2.json")

PLACE = {"search": "library", "diary": "bench", "draw": "artwork"}
KIND = {"search": "fact", "diary": "moment", "draw": "work"}   # old diary lines were passing thoughts


def did_text(e: dict) -> str:
    d = e.get("detail", {})
    if e["action"] == "search":
        return f"looking up {d.get('query', 'something')}"
    if e["action"] == "diary":
        return f"writing in his diary about {d.get('topic', 'the day').lower()}"
    if e["action"] == "draw":
        return f"drawing {d.get('subject', 'something')}"
    return e["action"]


def main() -> None:
    old = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))
    log = json.loads((ROOT / "log.json").read_text(encoding="utf-8"))
    s = engine.new_state()
    s["needs"].update({"rest": 0.30, "curiosity": 0.40, "social": 0.60, "expression": 0.50, "quiet": 0.20})
    s["mood"], s["energy"] = 0.0, 0.30
    s["who"] = who.fresh()
    s["memories"] = {"short": [], "long": []}
    s["beliefs"], s["belief_stats"], s["nights"] = [], {}, []

    # what happened under the old brain becomes short-term memory: his own lines, and for searches the facts
    report = {"short": [], "long": []}
    for e in log:
        if not e.get("ok") or e.get("withheld"):
            continue
        t = datetime.fromisoformat(e["time"])
        d = e.get("detail", {})
        text = d.get("summary", "").split(". ")[0].rstrip(".") + "." if e["action"] == "search" and d.get("summary") \
            else e["line"]
        m = memory.make(text, KIND[e["action"]], 2, t, 0.1, f"{e['action']}@{PLACE[e['action']]}")
        report["short"].append(memory.add(s["memories"]["short"], m, memory.SHORT_MAX))
        if e["action"] == "search" and e["line"] and d.get("summary"):
            m = memory.make(e["line"], "moment", 2, t, 0.1, f"search@library")
            report["short"].append(memory.add(s["memories"]["short"], m, memory.SHORT_MAX))

    # the old compressed knowledge, as long-term memory
    hatch = datetime.fromisoformat(log[0]["time"])
    seeds = [
        ("Derek, a pigeon. Wrong about bicycles, wrong about bottle caps, wrong in general.", "person", 4, -0.2),
        ("The computer I live in hums. I have been counting the hum for a while.", "moment", 3, -0.1),
    ]
    for w in old.get("wish_history", []):
        if w.get("outcome") == "got":
            seeds.append((f"I got {w['item']}. {w.get('note', '')}".strip(), "moment", 3, 0.4))
    for text, kind, strength, feel in seeds:
        report["long"].append(memory.add(s["memories"]["long"], memory.make(text, kind, strength, hatch, feel),
                                         memory.LONG_MAX))

    s["topics"] = [{"topic": i["topic"], "strength": i["strength"], "since": i["since"]} for i in old["interests"]]
    s["wants"] = [{"kind": "want", "subject": w["item"], "why": w["reason"], "since": w["added"]}
                  for w in old["wishlist"]]
    s["budget"] = {"amount": 12, "unit": "bottle caps", "note": "imaginary; he spends it on his wishlist in his head"}
    s["feeling_words"] = f"{old['mood']['word'].capitalize()}. {old['mood']['note']}"
    s["feed"] = [{"at": e["time"], "kind": "did", "text": did_text(e), "why": e.get("reason"), "ok": e["ok"],
                  "action": e["action"]}
                 for e in reversed(log)]
    s["last_tick"] = old["last_run"]
    s["migrated"] = {"from": "state.json + log.json", "runs": old.get("runs"), "at": datetime.now().astimezone()
                     .isoformat(timespec="seconds")}

    OUT.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"short memories: {len(s['memories']['short'])}, long: {len(s['memories']['long'])}")
    for r in report["short"] + report["long"]:
        print(" ", r)
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
