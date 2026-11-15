"""The public side: data/*.json in the shape of Pino's API (every answer starts with "v" and "at"), and a git
commit + push at most every 10 minutes. The site and the Dashboard panel read only these files (plus the
archive: log.json and drawings/index.json).
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from . import attend, beliefs, clock, learn, memory, mind, world
from .actions import ACTIONS

V = 1
FEED_PUBLIC = 50
PUSH_EVERY = 10 * 60          # seconds
DATA_EVERY = 60 * 60          # with Supabase live, data/*.json is only a fallback: pushed at most hourly
CLOUD_FRESH = 30 * 60         # Supabase counts as live if a write worked this recently
PUBLISH = ["data", "log.json", "drawings"]     # only these are ever committed by the loop (never git add -A)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def files(s: dict, real: datetime) -> dict[str, dict]:
    at = real.isoformat(timespec="seconds")
    head = {"v": V, "at": at}
    d = s.get("doing")
    p = s.get("pending") or {}
    flying = bool(d and d.get("travel", 0) > 0)
    asleep = bool(d and d["action"] == "sleep" and not flying)
    doing = None
    if flying:
        doing = f"flying to {world.name(d['place'])}" + (" to sleep" if d["action"] == "sleep" else "")
    elif d:
        same = p.get("action") == d["action"] and p.get("place") == d["place"]
        doing = p.get("doing") if same else f"{ACTIONS[d['action']].doing} {world.words(d['place'])}"
    pl = world.place(d["place"] if d else s.get("at", world.HOME))
    w = clock.world(real)
    f = s.get("feeling", {})
    now = {**head, "name": s["who"]["name"], "asleep": asleep, "doing": doing, "thought": s.get("thought"),
           "feeling": {"mood": round(s["mood"], 2), "energy": round(s["energy"], 2), "words": f.get("words"),
                       "emotion": learn.emotion(s), "arousal": round(s.get("arousal", 0), 2)},
           "needs": {k: round(v, 2) for k, v in s["needs"].items()},
           "world": {"name": "Berkel en Rodenrijs", "day": w["day"], "time": w["time"]},
           # additions to Pino's shape, for the 3D world and the dashboard panel
           "action": d["action"] if d else None,
           # where he is, or where he is flying to; poi/category only for the 3D world (world/places.json)
           "place": {"id": pl["id"], "name": pl["name"], "words": pl["words"], "poi": pl["poi"],
                     "category": pl["category"]},
           "flying": {"from": world.name(d["from"]), "to": world.name(d["place"])} if flying else None}

    feed = {**head, "entries": [{k: v for k, v in e.items()} for e in s.get("feed", [])[:FEED_PUBLIC]]}

    open_ = mind.open_items(s)
    counts = {k: 0 for k in ("piece", "person", "question", "want", "worry", "promise")}
    for i in open_:
        counts[i["kind"]] = counts.get(i["kind"], 0) + 1
    mind_json = {**head, "thought": s.get("thought"), "loudest": mind.loudest(s), "open": counts,
                 "busy": doing if not asleep else None, "promises": [], "holdsTo": s["who"]["holdsTo"],
                 # additions: the open items themselves, his interests and pretend budget
                 "items": [{"kind": i["kind"], "subject": i["subject"], "since": i["since"],
                            **({"why": i["why"]} if i.get("why") else {})} for i in open_],
                 "interests": [{"topic": t["topic"], "strength": round(t["strength"], 1)}
                               for t in sorted(s.get("topics", []), key=lambda t: -t["strength"])],
                 "budget": s.get("budget"),
                 # brain v3: data for the future 'brain scan' tab (not shown yet)
                 "brain": {**learn.public(s), "workingMemory": attend.public(s)}}

    mems = {**head, "beliefs": [beliefs.public(b) for b in sorted(s.get("beliefs", []), key=lambda b: -(b.get("n") or 0))],
            "long": [memory.public(m) for m in sorted(s["memories"]["long"], key=lambda m: m["since"], reverse=True)],
            "short": [memory.public(m) for m in sorted(s["memories"]["short"], key=lambda m: m["since"], reverse=True)]}

    who = {**head, **{k: s["who"][k] for k in ("name", "core", "backstory", "traits", "values", "fears", "quirks",
                                               "voice", "holdsTo", "added")},
           # additions: which version of him this is, and what changed in each version (newest first)
           "version": s["who"].get("version", 1), "changelog": list(reversed(s["who"].get("changelog", [])))}
    return {"now": now, "feed": feed, "mind": mind_json, "memories": mems, "who": who}


def write(s: dict, real: datetime, data_dir: Path) -> dict[str, dict]:
    out = files(s, real)
    for name, content in out.items():
        write_json(data_dir / f"{name}.json", content)
    return out


def paths(s: dict, real: datetime, root: Path, force: bool) -> list[str]:
    """What to commit this time. While Supabase is live, data/ goes along only hourly (or on the final push)."""
    ok = s.get("cloud_ok_at")
    live = bool(ok and (real - datetime.fromisoformat(ok)).total_seconds() < CLOUD_FRESH)
    last = s.get("last_data_push")
    data_due = force or not live or not last or (real - datetime.fromisoformat(last)).total_seconds() >= DATA_EVERY
    if data_due:
        s["last_data_push"] = real.isoformat(timespec="seconds")
    return [p for p in PUBLISH if (root / p).exists() and (p != "data" or data_due)]


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def publish(s: dict, real: datetime, root: Path, say, force: bool = False) -> None:
    """Commit + push the public files, at most every PUSH_EVERY seconds."""
    last = s.get("last_push")
    if not force and last and (real - datetime.fromisoformat(last)).total_seconds() < PUSH_EVERY:
        return
    s["last_push"] = real.isoformat(timespec="seconds")
    if not (root / ".git").exists():
        return
    todo = paths(s, real, root, force)
    git(root, "add", "--", *todo)
    did = next((e for e in s.get("feed", []) if e["kind"] == "did"), None)
    msg = f"Grimsby, day {clock.world(real)['day']}: {did['text'] if did else 'awake'}"[:100]
    r = git(root, "commit", "-m", msg, "--", *todo)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        say(f"commit failed: {(r.stderr or r.stdout).strip()[:300]}")
        return
    r = git(root, "push")
    if r.returncode != 0:
        pull = git(root, "pull", "--rebase", "--autostash")
        r = git(root, "push") if pull.returncode == 0 else pull
        if r.returncode != 0:
            say(f"push failed (tries again in 10 minutes): {(r.stderr or r.stdout).strip()[:300]}")
