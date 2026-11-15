"""Brain v3, phase 2: working memory and attention. Pure numbers, no LLM.

At most WM_SIZE things are "in his head": for instance the most pressing need, what he is doing, a memory that
came back and something he just saw (a place, a note, how an action turned out). Every tick the candidates compete
on salience (need urgency, |prediction error|, novelty, emotional charge); what loses falls out. Things that are
not renewed fade (WM_DECAY per tick), so a memory or a sight holds his attention for a while and then goes.

Only these items go to the model as context (voice.context), and the winner is `loudest` in mind.json.

Item: {"key", "kind", "subject", "text" (for the model, second person), "sal"}. Kinds: need, goal, memory,
outcome, seen, belief, worry, question, want.
"""

from __future__ import annotations

from datetime import datetime

from . import learn, world
from .actions import ACTIONS

WM_SIZE = 4
WM_DECAY = 0.8                 # salience of an item that is not renewed, x this per tick
WM_MIN = 0.08                  # under this it falls out even with room to spare

NEED_MIN = 0.3                 # a need under this is not on his mind
GOAL_SAL = 0.4                 # what he is busy with
MEM_SAL = 0.25                 # a memory that came back...
MEM_SURPRISE = 1.0             # ...+ |its prediction error| x this
MEM_FEEL = 0.4                 # ...+ |its feel| x this
MEM_RELEVANT = 0.15            # ...+ this when it was recalled for what he is about to say
OUTCOME_SAL = 0.15             # an action that turned out unlike he expected: + |delta| x OUTCOME_SURPRISE
OUTCOME_SURPRISE = 2.5
OUTCOME_MIN = 0.03             # |delta| under this is not worth a thought
SEEN_NOVEL = 0.6               # a place he arrives at, x its novelty
SEEN_NOVEL_MIN = 0.25
NOTE_SAL = 0.6                 # a visitor's note
BELIEF_SAL = 0.15              # a belief about what he is doing: + |V - average| x BELIEF_PULL
BELIEF_PULL = 2.0
OPEN_SAL = {"worry": 0.3, "question": 0.2, "want": 0.15}
WORRY_MOOD = 0.5               # a worry weighs more the worse his mood: + max(0, -mood) x this

NEED_WORDS = {"rest": "you need rest", "curiosity": "you want to find something out",
              "social": "you want company, or at least someone to disapprove of",
              "expression": "you want to make or write something", "quiet": "you want some quiet",
              "hunger": "you are hungry"}


def item(key: str, kind: str, subject: str, text: str, sal: float) -> dict:
    return {"key": key, "kind": kind, "subject": subject, "text": text, "sal": round(sal, 4)}


def standing(s: dict) -> list[dict]:
    """What competes every tick: the top need, what he is doing, a belief about it, his open items."""
    out = []
    need, val = max(s["needs"].items(), key=lambda kv: kv[1])
    if val >= NEED_MIN:
        out.append(item("need:" + need, "need", need, NEED_WORDS.get(need, need), val))
    d = s.get("doing")
    if d and d["action"] != "sleep":
        flying = d.get("travel", 0) > 0
        busy = (f"flying to {world.name(d['place'])} ({ACTIONS[d['action']].doing} there)" if flying
                else f"{ACTIONS[d['action']].doing} {world.words(d['place'])}")
        out.append(item("goal", "goal", busy, "you are busy " + busy, GOAL_SAL))
        b = next((b for b in s.get("beliefs", []) if b["about"] == f"{d['action']}@{d['place']}"), None)
        if b:
            pull = abs(learn.value(s, b["about"]) - learn.average(s))
            out.append(item("belief:" + b["about"], "belief", b["text"], "you believe: " + b["text"],
                            BELIEF_SAL + BELIEF_PULL * pull))
    from .mind import open_items                     # mind imports attend for loudest()
    for i in open_items(s):
        sal = OPEN_SAL.get(i["kind"], 0.15) + (WORRY_MOOD * max(0.0, -s["mood"]) if i["kind"] == "worry" else 0)
        text = {"worry": "a worry: ", "question": "a question you have: ", "want": "you want "}.get(i["kind"], "")
        out.append(item(f"{i['kind']}:{i['subject']}", i["kind"], i["subject"], text + i["subject"], sal))
    return out


def memory_item(m: dict, relevant: bool = False) -> dict:
    sal = MEM_SAL + MEM_SURPRISE * abs(m.get("surprise", 0.0)) + MEM_FEEL * abs(m.get("feel", 0.0))
    return item("memory:" + m["text"][:60], "memory", m["text"], "a memory: " + m["text"],
                sal + (MEM_RELEVANT if relevant else 0.0))


def outcome_item(done: dict) -> dict | None:
    delta = done.get("delta", 0.0)
    if abs(delta) < OUTCOME_MIN:
        return None
    what = f"{ACTIONS[done['action']].doing} {world.words(done['place'])}"
    how = "went better than you expected" if delta > 0 else "went worse than you expected"
    return item(f"outcome:{done['action']}@{done['place']}", "outcome", f"{what} {how}", f"{what} {how}",
                OUTCOME_SAL + OUTCOME_SURPRISE * abs(delta))


def seen_place(place: str, nov: float) -> dict | None:
    if nov < SEEN_NOVEL_MIN:
        return None
    return item("seen:" + place, "seen", world.name(place),
                f"you are somewhere you have not been for a while: {world.name(place)}", SEEN_NOVEL * nov)


def seen_note(author: str) -> dict:
    """Only that there was a note: a visitor's own words never ride along into other prompts."""
    return item("seen:note:" + author, "seen", f"a note from {author}", f"{author} left you a note", NOTE_SAL)


def consider(s: dict, new: list[dict]) -> None:
    """New candidates come in: a renewed item keeps the higher salience; then the strongest WM_SIZE stay."""
    wm = {i["key"]: i for i in s.setdefault("wm", [])}
    for n in new:
        if n is None:
            continue
        old = wm.get(n["key"])
        if not old or n["sal"] >= old["sal"]:
            wm[n["key"]] = n
    keep = sorted((i for i in wm.values() if i["sal"] >= WM_MIN), key=lambda i: -i["sal"])
    s["wm"] = keep[:WM_SIZE]


def tick(s: dict, ev: dict, recalled: list[dict] | None = None, novelty: float | None = None) -> None:
    """Once per tick, after the engine: fade what is held, then let this tick's candidates compete."""
    standing_now = standing(s)
    standing_keys = {i["key"] for i in standing_now}
    held = []
    for i in s.get("wm", []):
        if i["key"] in standing_keys or i["key"] == "goal":
            continue                                  # renewed below at its current salience (or gone)
        held.append({**i, "sal": round(i["sal"] * WM_DECAY, 4)})
    s["wm"] = held
    new = standing_now
    if ev.get("finished") and ev["finished"]["action"] not in ("idle", "sleep"):
        new.append(outcome_item(ev["finished"]))
    if recalled:
        new.append(memory_item(recalled[0]))          # only the best one gets a chance
    if ev.get("arrived") not in (None, "sleep") and novelty is not None and s.get("doing"):
        new.append(seen_place(s["doing"]["place"], novelty))
    consider(s, new)


def for_voice(s: dict, recalled: list[dict] | None = None) -> list[dict]:
    """What goes to the model: the working memory, after the memories recalled for this text had their go."""
    if recalled:
        consider(s, [memory_item(m, relevant=True) for m in recalled])
    return s.get("wm", [])


def loudest(s: dict) -> list[dict]:
    """For mind.json (Pino's shape: kind + subject), the winner first."""
    return [{"kind": i["kind"], "subject": i["subject"]} for i in s.get("wm", [])]


def public(s: dict) -> list[dict]:
    """For the future brain-scan tab."""
    return [{"kind": i["kind"], "subject": i["subject"], "salience": round(i["sal"], 3)} for i in s.get("wm", [])]
