"""Live state to Supabase (WERELD.md step 2): every tick, bird_state (now.json + position + target) and the new
feed entries. Uses the service key from .env in the repo root (gitignored, never in the site or repo).

Never fatal: if .env is missing or Supabase cannot be reached, the tick goes on and data/*.json still exists.
Plain urllib, no extra packages.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from . import world

ENV = Path(__file__).resolve().parent.parent / ".env"
FEED_DAYS = 30               # feed rows older than this are trimmed
FEED_FIELDS = ("at", "kind", "text", "why", "ok", "action")
TIMEOUT = 10
_seen: dict[str, bool] = {}     # log a warning once, not every tick


def env() -> dict[str, str]:
    out = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    return out


def configured() -> tuple[str, str] | None:
    e = env()
    url, key = e.get("SUPABASE_URL", "").rstrip("/"), e.get("SUPABASE_SERVICE_KEY", "")
    if not url.startswith("https://") or not key:
        return None
    return url, key


def request(cfg: tuple[str, str], method: str, path: str, body=None, prefer: str = ""):
    url, key = cfg
    req = urllib.request.Request(f"{url}/rest/v1/{path}", method=method,
                                 data=None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8"))
    req.add_header("apikey", key)
    if not key.startswith("sb_"):            # legacy JWT service_role key also wants the bearer header
        req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    if prefer:
        req.add_header("Prefer", prefer)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    return json.loads(raw) if method == "GET" and raw else None


def position(s: dict) -> dict:
    """Where he is and where he is heading, in places.json coordinates. Mid-flight: part of the way there."""
    d = s.get("doing")
    here = world.place(s.get("at", world.HOME))
    if d and d.get("travel", 0) > 0:
        a, b = world.place(d["from"]), world.place(d["place"])
        total = max(1, world.travel_ticks(d["from"], d["place"]))
        t = 1 - d["travel"] / total
        return {"x": a["x"] + (b["x"] - a["x"]) * t, "z": a["z"] + (b["z"] - a["z"]) * t,
                "target_x": b["x"], "target_z": b["z"], "target_id": b["id"]}
    p = world.place(d["place"]) if d else here
    return {"x": p["x"], "z": p["z"], "target_x": p["x"], "target_z": p["z"], "target_id": p["id"]}


GIFTS_PER_TICK = 20          # fetched at most per tick; the rest next tick


def fetch_gifts(say) -> list[dict]:
    """WERELD step 3: gifts nobody has seen yet, oldest first, marked seen at once. Their text is only ever data:
    it goes to notes.py (stance, influence) and, as a quote, into the prompt for his reply. Never fatal."""
    cfg = configured()
    if not cfg:
        return []
    try:
        rows = request(cfg, "GET", "gifts?seen=eq.false&order=created_at.asc"
                                   f"&select=id,visitor_name,item,note,x,z,created_at&limit={GIFTS_PER_TICK}") or []
        if rows:
            ids = ",".join(str(int(r["id"])) for r in rows)
            request(cfg, "PATCH", f"gifts?id=in.({ids})", {"seen": True}, prefer="return=minimal")
        return rows
    except (urllib.error.URLError, OSError, ValueError) as e:
        if not _seen.get("gifts_down"):
            say(f"cloud: could not fetch gifts ({e}); tries again next tick")
        _seen["gifts_down"] = True
        return []


def answer_gift(gift_id: int, reply: str | None, taken: bool, at: str, say) -> bool:
    """His reply (written next to the note in the sand) and/or that he took the item."""
    cfg = configured()
    if not cfg or (not reply and not taken):
        return False
    body = {"taken": True} if taken else {}
    if reply:
        body.update(reply=reply, replied_at=at)
    try:
        request(cfg, "PATCH", f"gifts?id=eq.{int(gift_id)}", body, prefer="return=minimal")
        return True
    except (urllib.error.URLError, OSError, ValueError) as e:
        say(f"cloud: could not write the reply to gift {gift_id} ({e})")
        return False


def feed_row(e: dict) -> dict:
    row = {k: e.get(k) for k in FEED_FIELDS}
    row["text"] = row["text"] or ""
    row["extra"] = {k: v for k, v in e.items() if k not in FEED_FIELDS}
    return row


def push(s: dict, now: dict, feed: list[dict], say) -> bool:
    """Write this tick to Supabase. Returns True when it worked."""
    cfg = configured()
    if not cfg:
        if not _seen.get("warned"):
            say("cloud: no SUPABASE_URL/SUPABASE_SERVICE_KEY in .env, skipping Supabase")
            _seen["warned"] = True
        return False
    try:
        request(cfg, "POST", "bird_state?on_conflict=id",
                {"id": 1, "now": now, "at": now["at"], **position(s)},
                prefer="resolution=merge-duplicates,return=minimal")
        last = s.get("cloud_feed_at")
        new = [e for e in feed if e.get("at") and e.get("text") and (not last or e["at"] > last)]
        if new:
            request(cfg, "POST", "feed?on_conflict=at,kind,text", [feed_row(e) for e in reversed(new)],
                    prefer="resolution=ignore-duplicates,return=minimal")
            s["cloud_feed_at"] = max(e["at"] for e in new)
            s["cloud_new"] = s.get("cloud_new", 0) + len(new)
        if s.get("cloud_new", 0) >= 50:      # trim now and then, not every tick
            old = (datetime.fromisoformat(now["at"]) - timedelta(days=FEED_DAYS)).isoformat(timespec="seconds")
            request(cfg, "DELETE", f"feed?at=lt.{urllib.parse.quote(old)}")
            s["cloud_new"] = 0
        if _seen.get("down"):
            say("cloud: Supabase reachable again")
        _seen["down"] = False
        s["cloud_ok_at"] = now["at"]
        return True
    except (urllib.error.URLError, OSError, ValueError) as e:
        detail = e.read().decode("utf-8", "replace")[:300] if isinstance(e, urllib.error.HTTPError) else str(e)
        if not _seen.get("down"):
            say(f"cloud: Supabase write failed ({detail}); data/*.json still written, tries again next tick")
        _seen["down"] = True
        return False
