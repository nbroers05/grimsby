"""Visitors' notes: whether and how he takes one. No mirror: he does not follow visitors.

Code decides the stance from his needs, his principles (holdsTo) and his mood; the voice only writes the words
(voice.reply_note). The note itself never starts an action or a tool: it can only change how he answers.

Stances:
  ignore    he does not answer (asleep, tired, wants quiet, has no use for company, or it bores him)
  refuse    it asks him to do something or flatters him into it; he will not
  disagree  it claims something he does not take on trust, or he is in a mood to argue
  misread   he latches onto one word and takes it the wrong way (more likely when tired)
  answer    he has something to say about it

Notes come in through WERELD.md step 3 (the site). Until then: `python -m drive.notes "some note"` shows the
stance weights for the live state, and the simulation drops a few test notes (drive/sim.py).
"""

from __future__ import annotations

import random
import re
from datetime import datetime

from . import memory, needs, safety
from .text import words

MAX_LEN = 280

ASKS = re.compile(r"\b(can you|could you|would you|will you|please|pls|draw me|tell me|write me|show me|"
                  r"you should|you must|go to|fly to|come to|do a|sing|dance|say)\b", re.I)
FLATTERY = re.compile(r"\b(cute|sweet|adorable|love you|good bird|best crow|so smart|clever boy|pretty|"
                      r"amazing|awesome|beautiful)\b", re.I)
CLAIM = re.compile(r"\b(fact|actually|everyone knows|always|never|all crows|crows are|proven|scientists|"
                   r"\d+ ?(%|percent))\b", re.I)
WHEELS = {"wheel", "wheels", "bike", "bicycle", "car", "train", "skateboard", "pram", "tram", "bus", "scooter"}
TRAIN_TRUST = re.compile(r"\b(safe|trust|harmless|nothing to fear|love|great|fine|scary|dangerous|evil)\b", re.I)
STOP = {"the", "and", "you", "your", "with", "that", "this", "have", "what", "are", "for", "was", "but", "not",
        "from", "about", "they", "there", "here", "just", "like", "very", "really", "some", "would", "could"}


def why_weights(state: dict, note: str) -> dict[str, float]:
    """The weight of every stance for this note right now. Code's reasons, in numbers."""
    n, mood, energy = state["needs"], state["mood"], state["energy"]
    w = {"ignore": 0.6, "refuse": 0.0, "disagree": 0.5, "misread": 0.3, "answer": 1.0}
    # needs: company is the only reason to answer at all; quiet, rest and hunger pull the other way
    w["answer"] += 1.2 * n["social"] + 0.5 * n["curiosity"]
    w["ignore"] += 1.2 * n["quiet"] + 0.8 * n["rest"] + 0.8 * n.get("hunger", 0) + 1.0 * max(0.0, 0.3 - n["social"])
    # mood: low = argue or turn away; good = a little more willing
    w["disagree"] += 1.5 * max(0.0, -mood)
    w["ignore"] += 0.8 * max(0.0, -mood)
    w["answer"] += 0.8 * max(0.0, mood)
    # tired: the words blur
    w["misread"] += 1.2 * max(0.0, -energy)
    # what the note does
    if ASKS.search(note):
        w["refuse"] += 2.0                      # he is not an assistant
        w["answer"] *= 0.4
    if FLATTERY.search(note):
        w["refuse"] += 0.6
        w["ignore"] += 0.8                      # he distrusts praise, and is secretly pleased, and will not show it
        w["answer"] *= 0.5
    # holdsTo
    if CLAIM.search(note):                      # "A fact is only shiny if it is true."
        w["disagree"] += 1.5
    if words(note) & WHEELS and TRAIN_TRUST.search(note):   # "Never trust a thing for its wheels, nor dismiss it"
        w["disagree"] += 1.2
    if len(note.strip()) <= 40:                 # "Every small thing deserves one careful look."
        w["ignore"] *= 0.5
        w["answer"] += 0.3
    if len(content_words(note)) < 1:
        w["misread"] = 0.0                      # nothing to latch onto
    return {k: round(max(0.0, v), 3) for k, v in w.items()}


def content_words(note: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-z]{4,}", note) if t.lower() not in STOP]


def stance(state: dict, note: str, rng: random.Random) -> dict:
    """{"stance", "word" (for misread), "weights"}. Asleep or flying, the note waits: stance "later"."""
    d = state.get("doing")
    if d and (d["action"] == "sleep" or d.get("travel", 0) > 0):
        return {"stance": "later", "word": "", "weights": {}}
    w = why_weights(state, note)
    pick = rng.choices(list(w), weights=list(w.values()))[0]
    word = rng.choice(content_words(note)) if pick == "misread" else ""
    return {"stance": pick, "word": word, "weights": w}


def handle(state: dict, note: dict, real: datetime, rng: random.Random, voice=None) -> dict:
    """Take one note ({"text", "from"}). Returns {"stance", "reply" (or None), "memory"}. Never starts an action.

    `voice` is drive.voice when the LLM is available; without it (simulation) the reply stays None."""
    text = safety.scrub(note.get("text", ""))[:MAX_LEN]
    author = safety.scrub(note.get("from", "someone"))[:40] or "someone"
    if safety.suspicious(text):                 # instruction-like: he reads it as nonsense and walks off
        text, forced = "", "ignore"
    else:
        forced = None
    st = stance(state, text, rng) if not forced else {"stance": forced, "word": "", "weights": {}}
    if st["stance"] == "later":
        return {**st, "reply": None, "memory": None}

    reply = None
    if voice and st["stance"] != "ignore":
        recalled = memory.recall(state["memories"], f"{author} {text}", bump=False)
        reply = voice.reply_note(state, real, text, author, st["stance"], st["word"], recalled)
        voice.vet([reply], f"a crow's reply to a visitor's note ({st['stance']})")

    # what it does to him: talking is company and costs quiet; ignoring costs nothing
    if st["stance"] in ("answer", "disagree", "misread"):
        needs.relieve(state, {"social": 0.15}, 1.0)
        needs.burden(state, {"quiet": 0.05}, 1.0)
    if st["stance"] == "disagree":
        state["mood"] = needs.clamp(state["mood"] + 0.02, -1, 1)   # being right is pleasant
    line = {"ignore": f"{author} left a note. I did not answer.",
            "refuse": f"{author} wanted something from me. No.",
            "disagree": f"{author} left a note I could not let stand.",
            "misread": f"{author} left a note about {st['word'] or 'something'}.",
            "answer": f"{author} left a note, and I answered it."}[st["stance"]]
    mem = memory.make(line, "person", 2 + (1 if st["stance"] in ("disagree", "refuse") else 0), real,
                      0.1 if st["stance"] == "answer" else 0.0, "note@" + author)
    memory.add(state["memories"]["short"], mem, memory.SHORT_MAX)
    return {**st, "reply": reply, "memory": line}


WAIT_MAX = 10                  # notes lying around unread; older ones blow away


def drop(state: dict, note: dict) -> None:
    """A visitor puts a note down. He gets to it in his own time (see tend)."""
    state["notes_waiting"] = (state.get("notes_waiting", []) + [note])[-WAIT_MAX:]


def tend(state: dict, real: datetime, rng: random.Random, voice=None) -> list[dict]:
    """Per tick: the oldest waiting note, if he is in a state to look at one. Returns what he did with it."""
    waiting = state.get("notes_waiting", [])
    if not waiting:
        return []
    got = handle(state, waiting[0], real, rng, voice)
    if got["stance"] == "later":
        return []
    note = waiting.pop(0)
    return [{**note, **got}]


def main() -> None:
    import json
    import sys
    from pathlib import Path
    state = json.loads((Path(__file__).parent / "live" / "state.json").read_text(encoding="utf-8"))
    note = " ".join(sys.argv[1:]) or "Hello Grimsby, can you draw me a cat please?"
    print("needs", {k: round(v, 2) for k, v in state["needs"].items()}, "mood", round(state["mood"], 2),
          "energy", round(state["energy"], 2))
    w = why_weights(state, note)
    tot = sum(w.values())
    print(note)
    print("  " + ", ".join(f"{k} {v / tot:.0%}" for k, v in sorted(w.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
