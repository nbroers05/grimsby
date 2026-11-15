"""Grimsby's live loop: a tick every 90 seconds while the laptop is on.

  .venv\\Scripts\\python -m drive.run                  run until stopped
  .venv\\Scripts\\python -m drive.run --ticks 40 --fast   40 ticks back to back, world time jumps 90 s per tick

  .venv\\Scripts\\python -m drive.run --test --ticks 40 --fast
        a separate test life in drive/test/ (own state, archive and data, no git)
  loop.pyw (repo root)   what Task Scheduler starts at log-on with pythonw: this loop, without a console

Live: his private state is drive/live/state.json; the archive (log.json, drawings/) and the public data/*.json are
in the repo root, and only those are committed and pushed, at most every 10 minutes.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from . import beliefs, clock, learn, life, mind, output, voice, who, world
from .act import Executor
from .voice import VoiceDown, Withheld

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LIVE = HERE / "live"           # private state, lock and run log
ARCHIVE = ROOT                 # log.json + drawings/
DATA = ROOT / "data"           # the public API files
PUBLIC = True                  # commit + push
STATE = LIVE / "state.json"
LOCK = LIVE / ".lock"
RUNLOG = LIVE / "run.log"


def use_test_dirs() -> None:
    global LIVE, ARCHIVE, DATA, PUBLIC, STATE, LOCK, RUNLOG
    LIVE = ARCHIVE = HERE / "test"
    DATA = LIVE / "data"
    PUBLIC = False
    STATE, LOCK, RUNLOG = LIVE / "state.json", LIVE / ".lock", LIVE / "run.log"
FEELING_EVERY = 8            # ticks at least between two feeling-words updates
FEELING_SHIFT = 0.2          # ...and only when mood or energy moved this much
TOPIC_NIGHT_FADE = 0.3


def say(msg: str) -> None:
    line = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {msg}"
    if sys.stdout:
        print(line, flush=True)
    LIVE.mkdir(exist_ok=True)
    with RUNLOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load() -> dict:
    LIVE.mkdir(exist_ok=True)
    if not STATE.exists():
        shutil.copy(HERE / "state_v2.json", STATE)
        say("started from the migrated state (drive/state_v2.json)")
    s = json.loads(STATE.read_text(encoding="utf-8"))
    mind.migrate_wants(s)
    if world.migrate_state(s):
        say("moved his beliefs and memories from place categories to world/places.json")
    s.setdefault("feeling", {"words": s.pop("feeling_words", None), "mood": s["mood"], "energy": s["energy"],
                             "tick": 0})
    s.setdefault("ticks", 0)
    learn.setup(s)
    if beliefs.number_old(s):
        say(f"numbered his beliefs as facts (up to fact {s['facts_made']})")
    if who.migrate(s["who"]):
        say(f"his character sheet is now version {s['who']['version']}")
    return s


def save(s: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(STATE)


class Voice:
    """What sleep needs from the LLM, with plain fallbacks when it is down."""

    def __init__(self, state: dict, real: datetime):
        self.state, self.real = state, real

    def summarise(self, short: list[dict], day: int) -> str | None:
        try:
            text = voice.summarise(self.state, self.real, short, day)
            voice.vet([text], "a crow's summary of his day")
            return f"Day {day}: {text}"
        except (VoiceDown, Withheld) as e:
            say(f"no day summary: {e}")
            return None

    def dream(self, pieces: list[dict]) -> str | None:
        try:
            text = voice.dream(self.state, self.real, pieces)
            voice.vet([text], "a crow's dream, a muddle of his memories")
            return text
        except (VoiceDown, Withheld) as e:
            say(f"no dream words: {e}")
            return None

    def closer(self, belief: str) -> str | None:
        try:
            text = voice.closer(self.state, belief)
            voice.vet([text], "a crow's dry remark about something he will not do again")
            return text
        except (VoiceDown, Withheld):
            return None

    def phrase(self, field: str, plain: str) -> str | None:
        try:
            text = voice.phrase_addition(self.state, field, plain)
            voice.vet([text], "a line a crow adds to his own character sheet")
            return text
        except (VoiceDown, Withheld):
            return None


def describe_from_pending(state: dict):
    def describe(done, real, rng):
        p = state.get("pending_done") or {}
        if p.get("action") == done["action"] and p.get("memory"):
            return p["memory"]
        return life.plain_describe(done, real, rng)
    return describe


def after_tick(s: dict, ev: dict, real: datetime) -> None:
    for night in (ev.get("slept_through"), ev.get("night")):
        if night:
            for t in s.get("topics", []):
                t["strength"] = round(max(0.0, t["strength"] - TOPIC_NIGHT_FADE), 2)
            if night.get("summary"):
                mind.feed(s, "noticed", night["summary"], real)
            for b in night["beliefs"]["new"]:
                mind.feed(s, "noticed", f"Fact {b['n']}: {beliefs.full_text(b)}", real, fact=b["n"])
            for b in night["beliefs"].get("back", []):
                mind.feed(s, "noticed", f"Fact {b['n']} holds after all: {beliefs.full_text(b)}", real, fact=b["n"])
            if night.get("added"):
                (field, text), = night["added"].items()
                mind.feed(s, "mind", f"Something about me: {text}. (Version {night.get('version')} of me.)", real,
                          change="opened", about="self")
            if night.get("dream"):                 # in the diary, as its own kind
                Executor(s, real, random.Random(), ARCHIVE, say).archive(
                    "dream", True, night["dream"]["text"], {"kind": "dream", "entry": night["dream"]["text"],
                                                            "from": night["dream"]["from"]}, "asleep")
            say(f"night (day {night['day']}, {night['why']}): {night['short']} short -> {len(night['promoted'])} kept")
    p = s.get("pending") or {}
    if ev["started"] and s["doing"] and s["doing"].get("travel", 0) > 0:
        d = s["doing"]
        mind.feed(s, "did", f"flying from {world.name(d['from'])} to {world.name(d['place'])}", real, why=None,
                  ok=True, action="fly")
        say(f"flying {d['from']} -> {d['place']} for {ev['started']} ({d['travel']} ticks)")
    if ev["arrived"] and p.get("action") == ev["arrived"]:
        if ev["arrived"] != "idle":
            mind.feed(s, "did", p["doing"], real, why=p.get("why"), ok=p["ok"], action=p["action"])
        for n in p.get("noticed", []):
            mind.feed(s, "noticed", n, real)
        if p.get("thought"):
            s["thought"] = p["thought"]
        if p.get("archive"):
            a = p["archive"]
            ex = Executor(s, real, random.Random(), ARCHIVE, say)
            ex.archive(p["action"], p["ok"], a.get("line") or p.get("memory") or p["doing"], a.get("detail", {}),
                       p.get("why") or "", withheld=a.get("withheld", False))
        if ev["arrived"] != "idle":
            say(f"{ev["arrived"]}@{s['doing']['place'] if s['doing'] else '-'} ok={p['ok']} | why: {p.get('why')} | "
                f"thought: {p.get('thought')}")
    mind.tend(s, real)
    f = s["feeling"]
    asleep = bool(s["doing"] and s["doing"]["action"] == "sleep")
    shifted = abs(s["mood"] - f["mood"]) > FEELING_SHIFT or abs(s["energy"] - f["energy"]) > FEELING_SHIFT * 1.5
    if not asleep and (shifted or not f.get("words")) and s["ticks"] - f["tick"] >= FEELING_EVERY:
        try:
            words = voice.feeling(s, real)
            voice.vet([words], "how a crow feels")
            s["feeling"] = {"words": words, "mood": s["mood"], "energy": s["energy"], "tick": s["ticks"]}
            mind.feed(s, "felt", words, real)
        except (VoiceDown, Withheld) as e:
            say(f"no feeling words: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=0, help="stop after this many ticks (0 = never)")
    ap.add_argument("--fast", action="store_true", help="no waiting; world time jumps 90 s per tick")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--test", action="store_true", help="a separate test life in drive/test/, never pushed")
    a = ap.parse_args()
    if a.test:
        use_test_dirs()

    LIVE.mkdir(exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 10 * 60:
        say("another loop is running, exiting")
        return 0
    rng = random.Random(a.seed)
    if not voice.ensure_ollama():
        say("Ollama is not running; ticks go on, words fall back to plain text")
    s = load()
    real = datetime.now().astimezone()
    n = 0
    try:
        while not a.ticks or n < a.ticks:
            LOCK.write_text(str(time.time()))
            started = time.time()
            try:
                ex = Executor(s, real, rng, ARCHIVE, say)
                ev = life.tick(s, real, rng, ex, describe=describe_from_pending(s), voice=Voice(s, real))
                s["ticks"] += 1
                after_tick(s, ev, real)
                save(s)
                output.write(s, real, DATA)
                if PUBLIC:
                    output.publish(s, real, ROOT, say)
            except Exception:  # noqa: BLE001 - one bad tick must not kill the loop
                say("tick failed:\n" + traceback.format_exc())
            n += 1
            if a.fast:
                real = real + timedelta(seconds=clock.TICK_SECONDS)
            else:
                time.sleep(max(1.0, clock.TICK_SECONDS - (time.time() - started)))
                real = datetime.now().astimezone()
    except KeyboardInterrupt:
        say("stopped")
    finally:
        if PUBLIC and n:
            try:
                output.publish(s, real, ROOT, say, force=True)     # what happened since the last push
            except Exception:  # noqa: BLE001
                say("final push failed: " + traceback.format_exc())
        LOCK.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
