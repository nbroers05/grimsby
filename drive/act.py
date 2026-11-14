"""Doing the action code chose, for real. Code picks the subject (which topic, what to draw, what to write
about); the voice writes the words. The result decides `ok`.

The executor is the `outcome(action, place)` callback of the engine: it runs when an action starts and leaves
what happened in state["pending"], so the memory can be written from it when the action ends (a later tick).
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from pathlib import Path

import requests

from . import beliefs, clock, memory, mind, safety, voice, world
from .actions import ACTIONS
from .voice import VoiceDown, Withheld

ROOT = Path(__file__).resolve().parent.parent
PINO = "https://pinos.world/api/v1"
MAX_TOPICS = 8
MAX_WANTS = 3
WANT_CHANCE = 0.25           # the model may suggest a want; code decides whether he takes it up
INTEREST_CHANCE = 0.35
HOARD = ["the bottle caps", "the teaspoon", "a shiny button", "a ring pull", "a blue marble", "a bent paperclip"]
PIGEONS_OK = ["Derek was there, and smug about it", "three pigeons and Derek, in a row", "Derek's cousin, who is worse",
              "Derek, alone, pretending not to see me"]
PIGEONS_FAIL = ["no Derek anywhere, which is suspicious", "the pigeons ignored me entirely", "a gull took the spot"]
NEED_REASON = {"rest": "you are tired", "curiosity": "you are curious", "social": "you are lonely",
               "expression": "you want to make or write something", "quiet": "you want quiet",
               "hunger": "you are hungry"}


class Executor:
    def __init__(self, state: dict, real: datetime, rng: random.Random, archive_dir: Path, say=print):
        """archive_dir holds log.json and drawings/ (the repo root when live, a test folder otherwise)."""
        self.state, self.real, self.rng, self.dir, self.say = state, real, rng, archive_dir, say

    # ------------------------------------------------------------ helpers
    def reason(self, action: str, place: str) -> str:
        a = ACTIONS[action]
        n = self.state["needs"]
        if action == "sleep":
            return "you are tired and it is " + ("night" if clock.is_night(self.real) else "late")
        need = max(a.relief, key=lambda k: n[k] * a.relief[k]) if a.relief else "rest"
        bits = [f"{NEED_REASON[need]} ({need} at {n[need]:.1f} of 1)"]
        b = next((b for b in self.state.get("beliefs", []) if b["about"] in (f"{action}@{place}", f"{action}@*")), None)
        if b:
            bits.append(f"you believe: {b['text']}")
        return "; ".join(bits)


    def recall(self, about: str) -> list[dict]:
        return memory.recall(self.state["memories"], about, bump=False)

    def pick_topic(self) -> str:
        qs = mind.open_items(self.state, "question")
        topics = self.state.setdefault("topics", [])
        options = [(i["subject"], 5.0) for i in qs] + [(t["topic"], max(0.5, t["strength"])) for t in topics]
        if not options:
            return "bottle caps"
        return self.rng.choices([o for o, _ in options], weights=[w for _, w in options])[0]

    def grow_topics(self, topic: str, new: str) -> None:
        topics = self.state.setdefault("topics", [])
        for t in topics:
            if t["topic"] == topic:
                t["strength"] = min(10.0, t["strength"] + 1)
        new = safety.scrub(new)[:60]
        if new and new.lower() not in {t["topic"].lower() for t in topics}:
            topics.append({"topic": new, "strength": 3.0, "since": self.real.isoformat(timespec="seconds")})
            mind.feed(self.state, "mind", f"A new interest: {new}.", self.real, change="opened", about="question")
            if len(topics) > MAX_TOPICS:
                topics.remove(min(topics[:-1], key=lambda t: t["strength"]))

    def archive(self, action: str, ok: bool, line: str, detail: dict, why: str, withheld=False) -> None:
        path = self.dir / "log.json"
        log = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        log.append({"time": self.real.isoformat(timespec="seconds"), "action": action, "reason": why, "ok": ok,
                    "withheld": withheld, "line": line, "detail": detail, "mood": round(self.state["mood"], 2)})
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)

    # ------------------------------------------------------------ the callback
    def __call__(self, action: str, place: str) -> bool:
        st = self.state
        doing = ACTIONS[action].doing if action == "neighbour" else f"{ACTIONS[action].doing} {world.words(place)}"
        p = {"action": action, "place": place, "doing": doing, "memory": None, "noticed": [],
             "content": "", "archive": None, "thought": None, "why": None, "ok": True, "public": []}
        try:
            getattr(self, "do_" + action, self.do_plain)(p)
        except VoiceDown as e:
            self.say(f"voice down during {action}: {e}")
            p["ok"] = False
            p["memory"] = f"Tried {p['doing']}, but my thoughts would not come."
        except Withheld as e:
            self.say(f"{action} withheld: {e}")
            p.update(ok=True, memory="Wrote something, read it back, and quietly ate the page.", noticed=[],
                     archive={"withheld": True, "detail": {"withheld": True}}, public=[])
        except Exception as e:  # noqa: BLE001 - anything else: the action simply didn't work this time
            self.say(f"{action} went wrong: {e!r}")
            p["ok"] = False
            p["memory"] = f"Tried {p['doing']}. Something got in the way."
        if action != "idle":
            self.words_for(p)
        st["pending"] = p
        return p["ok"]

    def words_for(self, p: dict) -> None:
        """Thought and why, after the action's content is known. Checked together with the content."""
        try:
            tw = voice.thought_why(self.state, self.real, p["action"], p["place"], p["doing"],
                                   self.reason(p["action"], p["place"]) + ("" if p["ok"] else "; it is not going well"),
                                   p["content"], self.recall(p["doing"] + " " + p["content"]))
            texts = [tw["why"], tw["thought"]] + p["public"]
            voice.vet(texts, f"{p['doing']}")
            p["why"], p["thought"] = safety.clean_line(tw["why"]), safety.clean_line(tw["thought"])
        except (VoiceDown, Withheld) as e:
            self.say(f"no thought for {p['action']}: {e}")
            if p["public"]:                       # the content itself might be the problem: hold it back
                p.update(memory="Wrote something, read it back, and quietly ate the page.", noticed=[],
                         archive={"withheld": True, "detail": {"withheld": True}}, public=[])
            p["why"], p["thought"] = None, None

    # ------------------------------------------------------------ actions
    def do_plain(self, p: dict) -> None:
        if p["action"] == "sit":
            p["memory"] = f"Sat still {world.words(p['place'])}. Nothing rolled my way."
        elif p["action"] == "sleep":
            p["doing"] = f"falling asleep {world.words(p['place'])}"

    do_idle = do_plain
    do_sleep = do_plain
    do_sit = do_plain

    def do_search(self, p: dict) -> None:
        topic = self.pick_topic()
        query = voice.search_query(self.state, self.real, topic)
        p["doing"] = f"looking up {query.lower()} {world.words(p['place'])}"
        results = safety.web_search(query)
        if not results:
            p.update(ok=False, memory=f"Searched for {query} and found nothing at all.",
                     content=f"you searched for {query} and found nothing at all")
            mind.open_item(self.state, "question", query, self.real, f"An open question: {query}?")
            p["archive"] = {"detail": {"query": query, "found": False}, "line": p["memory"]}
            return
        source, page = safety.read_best(results)
        page, dropped = safety.defuse(page)
        if dropped:
            self.say(f"removed {dropped} instruction-like sentence(s) from the page")
        out = voice.read_page(self.state, self.real, query, source["title"], page, self.recall(query))
        p["public"] = [out["summary"], out["thought"], out["new_interest"], out["want"], out["want_why"]]
        voice.vet(p["public"], f"search about {query!r}")
        p["content"] = out["summary"]
        p["memory"] = out["summary"].split(". ")[0].rstrip(".") + "."
        p["noticed"].append(f"Read that {out['summary'][0].lower()}{out['summary'][1:]}")
        p["archive"] = {"line": safety.clean_line(out["thought"]), "detail": {
            "query": query, "title": safety.scrub(source["title"]), "url": source["href"],
            "summary": out["summary"], "new_interest": out["new_interest"]}}
        mind.answers(self.state, query, self.real)
        self.grow_topics(topic, out["new_interest"] if self.rng.random() < INTEREST_CHANCE else "")
        if out["want"] and len(mind.open_items(self.state, "want")) < MAX_WANTS and self.rng.random() < WANT_CHANCE:
            want = safety.scrub(out["want"])[:80]
            want = want[0].lower() + want[1:] if want[:2] != want[:2].upper() else want
            mind.open_item(self.state, "want", want, self.real, f"Started wanting {want}.", why=out["want_why"])

    def do_diary(self, p: dict) -> None:
        worries = mind.open_items(self.state, "worry")
        short = self.state["memories"]["short"]
        if worries:
            about = "the worry that " + worries[0]["subject"]
        elif short:
            about = max(short, key=lambda m: abs(m.get("feel", 0)) + self.rng.random() * 0.3)["text"]
        else:
            about = self.pick_topic()
        out = voice.diary(self.state, self.real, about, self.recall(about))
        p["public"] = [out["entry"], out["line"]]
        voice.vet(p["public"], "diary entry")
        p["content"] = out["line"]
        p["memory"] = safety.clean_line(out["line"])
        p["archive"] = {"line": p["memory"], "detail": {"topic": about[:120], "entry": out["entry"]}}

    def do_draw(self, p: dict) -> None:
        wants = mind.open_items(self.state, "want")
        options = [world.name(p["place"]), self.pick_topic(), self.rng.choice(HOARD)] + \
            ([wants[0]["subject"]] if wants else [])
        subject = self.rng.choice(options)
        p["doing"] = f"drawing {subject} {world.words(p['place'])}"
        for _ in range(2):
            out = voice.drawing(self.state, self.real, subject)
            try:
                svg, svg_texts = safety.clean_svg(out["svg"])
                break
            except Exception as e:  # noqa: BLE001 - any parse problem: try once more
                self.say(f"bad svg: {e}")
        else:
            p.update(ok=False, memory=f"Tried to draw {subject}. The result is not fit to be seen.",
                     content=f"your drawing of {subject} came out as nothing")
            return
        title, caption = safety.scrub(out["title"]), safety.scrub(out["caption"])
        p["public"] = [title, caption, out["line"], *svg_texts]
        voice.vet(p["public"], f"drawing of {subject!r}")
        d = self.dir / "drawings"
        d.mkdir(parents=True, exist_ok=True)
        fname = f"{self.real.strftime('%Y-%m-%d-%H%M')}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40] or 'untitled'}.svg"
        (d / fname).write_text(svg + "\n", encoding="utf-8")
        index_path = d / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
        item = {"file": f"drawings/{fname}", "title": title, "caption": caption, "subject": subject,
                "time": self.real.isoformat(timespec="seconds")}
        index.append(item)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        p["content"] = f"{title}: {caption}"
        p["memory"] = safety.clean_line(out["line"])
        p["archive"] = {"line": p["memory"], "detail": item}

    def do_neighbour(self, p: dict) -> None:
        try:
            now = requests.get(f"{PINO}/now", headers={"User-Agent": safety.UA}, timeout=15)
            if now.status_code != 200:
                raise requests.RequestException(f"HTTP {now.status_code}")
            now = now.json()
        except (requests.RequestException, ValueError) as e:
            self.say(f"Pino not answering: {e}")
            p.update(ok=False, memory="Looked over at Pino's. Nobody answered.")
            return
        bits = []
        if now.get("asleep"):
            bits.append("Pino was asleep")
        elif now.get("doing"):
            bits.append(f"Pino was {safety.scrub(now['doing'])}")
        if now.get("thought") and not now.get("asleep"):
            bits.append(f"thinking \"{safety.scrub(now['thought'])[:160]}\"")
        noticed = (", ".join(bits) or "Pino was there, doing nothing in particular") + " (from pinos.world)."
        if safety.suspicious(noticed):
            noticed = "Pino was there, saying something odd (from pinos.world)."
        opinion = voice.about_pino(self.state, self.real, noticed, self.recall("Pino"))
        p["public"] = [noticed, opinion]
        voice.vet(p["public"], "a crow's opinion about his neighbour Pino, a bird from pinos.world")
        p["noticed"].append(noticed)
        p["content"] = noticed
        p["memory"] = f"Pino: {opinion}"

    def do_pigeons(self, p: dict) -> None:
        p["ok"] = self.rng.random() >= ACTIONS["pigeons"].fail       # whether Derek and co. show up is luck
        what = self.rng.choice(PIGEONS_OK if p["ok"] else PIGEONS_FAIL)
        p["content"] = what
        p["noticed"].append(what[0].upper() + what[1:] + ".")
        p["memory"] = voice.memory_line(self.state, self.real, f"At the {p['place']}: {what}.", self.recall("Derek pigeon"))
        p["public"] = [p["memory"], what]

    def do_eat(self, p: dict) -> None:
        p["ok"] = self.rng.random() >= ACTIONS["eat"].fail           # whether there is anything is luck
        food = world.place(p["place"]).get("food") or ["a crumb"]
        what = self.rng.choice(food) if p["ok"] else "nothing; someone had been there first"
        p["doing"] = f"looking for something to eat {world.words(p['place'])}"
        p["content"] = f"you found {what}"
        p["noticed"].append(f"Found {what} {world.words(p['place'])}.")
        p["memory"] = voice.memory_line(self.state, self.real, f"You went to eat {world.words(p['place'])} and found "
                                        f"{what}.", self.recall(world.name(p["place"]) + " eat"))
        p["public"] = [p["memory"]]

    def do_wander(self, p: dict) -> None:
        name = world.name(p["place"])
        p["doing"] = f"flying about town, as far as {name}"
        p["content"] = name
        p["memory"] = voice.memory_line(self.state, self.real, f"You flew about town and ended up at {name}.",
                                        self.recall(name))
        p["public"] = [p["memory"]]

    def do_tidy(self, p: dict) -> None:
        item = self.rng.choice(HOARD)
        p["doing"] = f"tidying his hoard: {item}"
        p["content"] = item
        p["memory"] = voice.memory_line(self.state, self.real, f"You tidied your hoard and handled {item}.",
                                        self.recall(item))
        p["public"] = [p["memory"]]

    def do_read_back(self, p: dict) -> None:
        old = self.state["memories"]["long"]
        if not old:
            p.update(ok=False, memory="Went to re-read my old pages. There are none yet.")
            return
        m = self.rng.choice(old)
        m["recalled"] = round(min(memory.RECALLED_MAX, m["recalled"] + 1), 2)
        p["content"] = m["text"]
        p["memory"] = voice.memory_line(self.state, self.real, f"You re-read an old memory: \"{m['text']}\"", [m])
        p["public"] = [p["memory"]]
