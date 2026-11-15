"""The feed and the things on his mind, all decided in code.

Feed kinds (as in Pino's API): did (with why, ok), noticed, felt, mind (with change opened/closed and about).
Open items: want, worry, question (promise is reserved; he makes none yet).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import clock
from .text import words

FEED_MAX = 200                 # kept in state; the public feed shows the newest 50
WANT_DAYS = 8                  # world days before he lets a want go
QUESTION_DAYS = 5
WORRY_OPEN, WORRY_CLOSE = -0.3, 0.05


def feed(state: dict, kind: str, text: str, real: datetime, **extra) -> dict:
    e = {"at": real.isoformat(timespec="seconds"), "kind": kind, "text": text, **extra}
    state["feed"] = ([e] + state.get("feed", []))[:FEED_MAX]
    return e


def open_items(state: dict, kind: str | None = None) -> list[dict]:
    return [i for i in state.setdefault("open", []) if kind is None or i["kind"] == kind]


def open_item(state: dict, kind: str, subject: str, real: datetime, text: str, **extra) -> bool:
    if any(i["kind"] == kind and i["subject"].lower() == subject.lower() for i in open_items(state)):
        return False
    state["open"].append({"kind": kind, "subject": subject, "since": real.isoformat(timespec="seconds"), **extra})
    feed(state, "mind", text, real, change="opened", about=kind)
    return True


def close_item(state: dict, item: dict, real: datetime, text: str) -> None:
    state["open"].remove(item)
    feed(state, "mind", text, real, change="closed", about=item["kind"])


def world_days_since(iso: str, real: datetime) -> float:
    return (clock.world_minutes(real) - clock.world_minutes(datetime.fromisoformat(iso))) / 1440


def migrate_wants(state: dict) -> None:
    """state_v2 kept the old wishlist under `wants`; it becomes open items."""
    for w in state.pop("wants", []):
        state.setdefault("open", []).append({"kind": "want", "subject": w["subject"], "since": w["since"],
                                             "why": w.get("why", "")})


def tend(state: dict, real: datetime) -> None:
    """Per tick: worries come and go with mood; old wants and questions are let go."""
    worries = open_items(state, "worry")
    if state["mood"] < WORRY_OPEN and not worries:
        need = max(state["needs"].items(), key=lambda kv: kv[1])[0]
        open_item(state, "worry", "how things are going", real,
                  f"Started to worry: things are not going my way. ({need} is pulling hardest)")
    elif state["mood"] > WORRY_CLOSE:
        for w in worries:
            close_item(state, w, real, "Stopped worrying. Things are tolerable.")
    for i in list(open_items(state, "want")):
        if world_days_since(i["since"], real) > WANT_DAYS:
            close_item(state, i, real, f"Let go of wanting {i['subject']}.")
    for i in list(open_items(state, "question")):
        if world_days_since(i["since"], real) > QUESTION_DAYS:
            close_item(state, i, real, f"Gave up on a question: {i['subject']}.")


def answers(state: dict, query: str, real: datetime) -> None:
    """A successful search closes an open question that it shares words with."""
    q = words(query)
    for i in list(open_items(state, "question")):
        if len(q & words(i["subject"])) >= 2:
            close_item(state, i, real, f"Found an answer to: {i['subject']}.")


def loudest(state: dict, n: int = 3) -> list[dict]:
    """What pulls hardest, for mind.json: his working memory, winner first (brain v3, attend.py). Before the first
    tick of v3 it falls back to the strongest needs and open items."""
    if state.get("wm"):
        from . import attend
        return attend.loudest(state)
    out =[{"kind": "need", "subject": k} for k, v in sorted(state["needs"].items(), key=lambda kv: -kv[1]) if v > 0.3]
    out += [{"kind": i["kind"], "subject": i["subject"]} for i in reversed(open_items(state))]
    return out[:n]
