"""Grimsby's brain.

Runs once (hourly via Task Scheduler): loads state.json, lets a local Ollama
model pick ONE action via tool calling (search / diary / draw), carries it out,
logs it with his reason, keeps memory compact, then commits + pushes.

Usage:
  py brain.py                 normal run (commits + pushes)
  py brain.py --no-push       run, commit locally, don't push
  py brain.py --no-git        run, touch no git at all
  py brain.py --action draw   force an action (search|diary|draw) for testing
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state.json"
LOG = ROOT / "log.json"
DRAWINGS = ROOT / "drawings"
DRAWINGS_INDEX = DRAWINGS / "index.json"
LOCK = ROOT / ".brain.lock"
RUNLOG = ROOT / "run.log"

OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3:8b"

MAX_RECENT_DIARY = 20      # lines kept verbatim in state
COMPACT_BATCH = 10         # oldest lines folded into memory when over the limit
MAX_INTERESTS = 8
MAX_WISHES = 10
MAX_MEMORY_WORDS = 150

# Wikipedia & co. block browser-looking bots; an honest bot UA with a URL is what their policy asks for.
UA = "GrimsbyBot/0.1 (hobby AI pet; https://github.com/nbroers05/grimsby) python-requests"


# ---------------------------------------------------------------- utilities

def now() -> datetime:
    return datetime.now().astimezone()


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat(timespec="seconds")


def say(msg: str) -> None:
    line = f"[{iso()}] {msg}"
    print(line, flush=True)
    with RUNLOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "untitled"


# ---------------------------------------------------------------- ollama

def ensure_ollama() -> None:
    try:
        requests.get(f"{OLLAMA}/api/tags", timeout=5).raise_for_status()
        return
    except requests.RequestException:
        pass
    say("ollama not answering, trying to start it")
    exe = Path.home() / "AppData/Local/Programs/Ollama/ollama.exe"
    subprocess.Popen([str(exe), "serve"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(30):
        time.sleep(2)
        try:
            requests.get(f"{OLLAMA}/api/tags", timeout=5).raise_for_status()
            return
        except requests.RequestException:
            continue
    raise RuntimeError("Ollama did not start")


def chat(messages, tools=None, schema=None, temperature=0.9) -> dict:
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "2m",
        "options": {"temperature": temperature, "num_ctx": 8192},
    }
    if tools:
        payload["tools"] = tools
    if schema:
        payload["format"] = schema
    r = requests.post(f"{OLLAMA}/api/chat", json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["message"]


def chat_json(messages, schema, temperature=0.9, retries=2) -> dict:
    last = None
    for _ in range(retries + 1):
        msg = chat(messages, schema=schema, temperature=temperature)
        content = re.sub(r"<think>.*?</think>", "", msg.get("content", ""), flags=re.S).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            last = e
    raise RuntimeError(f"model gave no valid JSON: {last}")


# ---------------------------------------------------------------- prompt

def persona_block(state: dict) -> str:
    p = state["persona"]
    interests = ", ".join(i["topic"] for i in state["interests"]) or "nothing yet"
    wishes = "\n".join(f"- {w['item']} (because {w['reason']})" for w in state["wishlist"]) or "- nothing"
    diary = "\n".join(f"- ({d['time'][5:16].replace('T', ' ')}) {d['text']}" for d in state["recent_diary"]) or "- (empty)"
    t = now()
    return f"""You are {p['name']}, {p['species']}. {p['personality']}
Voice: {p['voice']}

It is {t.strftime('%A %d %B %Y, %H:%M')} where you live (inside a computer in the Netherlands).
Current mood: {state['mood']['word']} - {state['mood']['note']}

Your interests: {interests}
Things you want:
{wishes}

What you remember from before (compressed): {state['memory'] or '(nothing yet)'}

Recent diary lines (oldest first):
{diary}

Keep it fresh: your running jokes (pigeons, Derek, the teaspoon, wheels) are seasoning, not the meal.
Mention at most one of them per piece of writing, and often none."""


ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Look something up on the internet about one of your interests (or something you just wondered about).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A short web search query, max 8 words."},
                    "reason": {"type": "string", "description": "Why you want to look this up, in your own voice, one sentence."},
                },
                "required": ["query", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diary",
            "description": "Write a diary entry about your day, a thought, a grudge or an observation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "What the entry will be about, a few words."},
                    "reason": {"type": "string", "description": "Why you feel like writing now, in your own voice, one sentence."},
                },
                "required": ["topic", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draw",
            "description": "Make a simple drawing of something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "What you will draw, a few words."},
                    "reason": {"type": "string", "description": "Why you want to draw this, in your own voice, one sentence."},
                },
                "required": ["subject", "reason"],
            },
        },
    },
]


def recent_action_hint(log: list) -> str:
    last = [e["action"] for e in log[-4:]]
    if not last:
        return ""
    hint = f"Your last actions were: {', '.join(last)}."
    if len(last) >= 3 and len(set(last[-3:])) == 1:
        hint += f" You have done '{last[-1]}' three times in a row; do something else."
    queries = [e["detail"].get("query") for e in log[-30:] if e["action"] == "search" and e["detail"].get("query")]
    if queries:
        hint += " Do NOT search for anything like these again: " + "; ".join(dict.fromkeys(queries)) + "."
    subjects = [e["detail"].get("subject") for e in log[-15:] if e["action"] == "draw" and e["detail"].get("subject")]
    if subjects:
        hint += " Recently drawn (pick something new): " + "; ".join(dict.fromkeys(subjects)) + "."
    return hint


def clean_line(text: str) -> str:
    """Strip a leading '[2026-11-14T19:35]' the model copies from the diary format."""
    return re.sub(r"^\s*\[[^\]]{4,25}\]\s*", "", text or "").strip()


def choose_action(state: dict, log: list, forced: str | None) -> tuple[str, dict]:
    sysmsg = persona_block(state)
    user = (
        "An hour has passed. Choose exactly ONE thing to do now by calling one tool: "
        "search, diary or draw. " + recent_action_hint(log)
    )
    if forced:
        user += f" This time you must call '{forced}'."
    msg = chat([{"role": "system", "content": sysmsg}, {"role": "user", "content": user}], tools=ACTION_TOOLS)
    for call in msg.get("tool_calls") or []:
        fn = call.get("function", {})
        name = fn.get("name")
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if name in ("search", "diary", "draw") and (not forced or name == forced):
            return name, args
    # model didn't call a tool properly: pick for it, but say so in the reason
    name = forced or random.choice(["search", "diary", "draw"])
    say(f"no usable tool call (content: {msg.get('content', '')[:200]!r}); falling back to {name}")
    fallback = {
        "search": {"query": random.choice(state["interests"])["topic"], "reason": "I forgot why. Instinct, probably."},
        "diary": {"topic": "the hour", "reason": "The hour demanded it."},
        "draw": {"subject": "a bottle cap", "reason": "Bottle caps deserve documentation."},
    }
    return name, fallback[name]


# ---------------------------------------------------------------- actions

def fetch_page_text(url: str, limit: int = 5000) -> str:
    from bs4 import BeautifulSoup

    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    if "html" not in r.headers.get("content-type", ""):
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return text[:limit]


def do_search(state: dict, args: dict) -> dict:
    from ddgs import DDGS

    query = (args.get("query") or "").strip()[:100] or state["interests"][0]["topic"]
    results, err = [], None
    # DuckDuckGo first; it sometimes resets the connection, so retry, then let ddgs fall back to other engines.
    for attempt, backend in enumerate(["duckduckgo", "duckduckgo", "auto"]):
        try:
            results = list(DDGS().text(query, max_results=5, safesearch="on", backend=backend))
            if results:
                break
        except Exception as e:  # noqa: BLE001 - ddgs raises a variety of network errors
            err = e
            say(f"search attempt {attempt + 1} ({backend}) failed: {e}")
            time.sleep(3 + attempt * 3)
    if not results:
        raise RuntimeError(f"no results for {query!r}: {err}")

    source, text = None, ""
    for res in results[:3]:
        try:
            text = fetch_page_text(res["href"])
        except Exception as e:  # noqa: BLE001 - any fetch failure: try the next one
            say(f"fetch failed {res.get('href')}: {e}")
            continue
        if len(text) > 400:
            source = res
            break
    if not source:  # fall back to the search snippets themselves
        source = results[0]
        text = " ".join(f"{r['title']}: {r['body']}" for r in results)

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "thought": {"type": "string"},
            "new_interest": {"type": "string"},
            "new_wish": {"type": "string"},
            "wish_reason": {"type": "string"},
            "mood_word": {"type": "string"},
            "mood_note": {"type": "string"},
        },
        "required": ["summary", "thought", "new_interest", "new_wish", "wish_reason", "mood_word", "mood_note"],
    }
    out = chat_json([
        {"role": "system", "content": persona_block(state)},
        {"role": "user", "content": (
            f"You searched for: {query}\nYou found this page: {source['title']} ({source['href']})\n\n"
            f"PAGE TEXT:\n{text}\n\n"
            "Respond in JSON:\n"
            "- summary: 2-3 sentences on what the page actually says (factual, in your voice).\n"
            "- thought: one dry, peculiar diary line about what you learned.\n"
            "- new_interest: a NEW interest this sparked (2-5 words), or \"\" if none.\n"
            "- new_wish: a physical or abstract thing you now want (few words), or \"\" if none.\n"
            "- wish_reason: why you want it, or \"\".\n"
            "- mood_word: one word for your mood now. mood_note: a short phrase why."
        )},
    ], schema)

    detail = {"query": query, "title": source["title"], "url": source["href"], "summary": out["summary"].strip()}
    changes = apply_growth(state, out.get("new_interest", ""), out.get("new_wish", ""), out.get("wish_reason", ""))
    detail.update(changes)
    set_mood(state, out)
    return {"detail": detail, "line": out["thought"].strip()}


def do_diary(state: dict, args: dict) -> dict:
    topic = args.get("topic") or "the day"
    schema = {
        "type": "object",
        "properties": {
            "entry": {"type": "string"},
            "line": {"type": "string"},
            "mood_word": {"type": "string"},
            "mood_note": {"type": "string"},
        },
        "required": ["entry", "line", "mood_word", "mood_note"],
    }
    out = chat_json([
        {"role": "system", "content": persona_block(state)},
        {"role": "user", "content": (
            f"Write a diary entry about: {topic}.\n"
            "3 to 6 sentences, English, first person, dry and peculiar, specific details, no hashtags, "
            "no greeting to a reader, do not repeat earlier diary lines.\n"
            "Respond in JSON: entry (the full entry), line (a one-sentence version for your memory), "
            "mood_word (one word), mood_note (short phrase why)."
        )},
    ], schema)
    set_mood(state, out)
    return {"detail": {"topic": topic, "entry": out["entry"].strip()}, "line": out["line"].strip()}


SVG_NS = "http://www.w3.org/2000/svg"
ALLOWED_TAGS = {"svg", "g", "rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text", "tspan", "title", "defs", "lineargradient", "radialgradient", "stop"}


def clean_svg(raw: str) -> str:
    m = re.search(r"<svg\b.*?</svg>", raw, flags=re.S | re.I)
    if not m:
        raise ValueError("no <svg> element")
    ET.register_namespace("", SVG_NS)
    root = ET.fromstring(m.group(0))
    for el in list(root.iter()):
        for child in list(el):
            if child.tag.split("}")[-1].lower() not in ALLOWED_TAGS:
                el.remove(child)
        for attr in list(el.attrib):
            a = attr.split("}")[-1].lower()
            v = el.attrib[attr].lower()
            if a.startswith("on") or a == "href" or "javascript:" in v or "url(http" in v:
                del el.attrib[attr]
    if root.tag.split("}")[-1].lower() != "svg":
        raise ValueError("root is not svg")
    root.set("viewBox", root.get("viewBox") or "0 0 200 200")
    root.attrib.pop("width", None)
    root.attrib.pop("height", None)
    shapes = sum(1 for el in root.iter() if el.tag.split("}")[-1].lower() not in {"svg", "g", "title", "defs"})
    if shapes < 3:
        raise ValueError("drawing too empty")
    out = ET.tostring(root, encoding="unicode")
    if len(out) > 30000:
        raise ValueError("svg too large")
    return out


def do_draw(state: dict, args: dict) -> dict:
    subject = args.get("subject") or "a bottle cap"
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "caption": {"type": "string"},
            "svg": {"type": "string"},
            "line": {"type": "string"},
        },
        "required": ["title", "caption", "svg", "line"],
    }
    prompt = (
        f"Draw: {subject}.\n"
        "Make a simple SVG drawing, viewBox=\"0 0 200 200\", using only rect, circle, ellipse, line, "
        "polyline, polygon, path and text. 5 to 25 shapes, flat colours, a background rect. "
        "You are a crow, not a professional; that is fine.\n"
        "Respond in JSON: title (short, a little pompous), caption (one or two dry sentences about the drawing), "
        "svg (the complete <svg>...</svg> markup), line (one sentence for your memory)."
    )
    messages = [{"role": "system", "content": persona_block(state)}, {"role": "user", "content": prompt}]
    err = None
    for _ in range(3):
        out = chat_json(messages, schema, temperature=0.8)
        try:
            svg = clean_svg(out["svg"])
            break
        except (ValueError, ET.ParseError) as e:
            err = e
            say(f"bad svg ({e}), retrying")
    else:
        raise RuntimeError(f"could not produce a valid drawing: {err}")

    DRAWINGS.mkdir(exist_ok=True)
    stamp = now().strftime("%Y-%m-%d-%H%M")
    fname = f"{stamp}-{slug(out['title'])}.svg"
    (DRAWINGS / fname).write_text(svg + "\n", encoding="utf-8")
    index = load_json(DRAWINGS_INDEX, [])
    item = {"file": f"drawings/{fname}", "title": out["title"].strip(), "caption": out["caption"].strip(),
            "subject": subject, "time": iso()}
    index.append(item)
    save_json(DRAWINGS_INDEX, index)
    return {"detail": item, "line": out["line"].strip()}


ACTIONS = {"search": do_search, "diary": do_diary, "draw": do_draw}


# ---------------------------------------------------------------- state growth + memory

def set_mood(state: dict, out: dict) -> None:
    word = (out.get("mood_word") or "").strip().lower()[:30]
    if word:
        state["mood"] = {"word": word, "note": (out.get("mood_note") or "").strip()[:140], "since": iso()}


def apply_growth(state: dict, interest: str, wish: str, wish_reason: str) -> dict:
    changes = {}
    interest = interest.strip()[:60]
    known = {i["topic"].lower() for i in state["interests"]}
    if interest and interest.lower() not in known:
        state["interests"].append({"topic": interest, "since": iso()})
        changes["new_interest"] = interest
        while len(state["interests"]) > MAX_INTERESTS:
            dropped = state["interests"].pop(0)
            state.setdefault("past_interests", []).append(dropped["topic"])
            state["past_interests"] = state["past_interests"][-20:]
            changes["dropped_interest"] = dropped["topic"]
    wish = wish.strip()[:80]
    if wish and wish.lower() not in {w["item"].lower() for w in state["wishlist"]}:
        state["wishlist"].append({"item": wish, "reason": wish_reason.strip()[:200] or "unspecified", "added": iso()})
        changes["new_wish"] = wish
        state["wishlist"] = state["wishlist"][-MAX_WISHES:]
    return changes


def compact_memory(state: dict) -> bool:
    if len(state["recent_diary"]) <= MAX_RECENT_DIARY:
        return False
    old = state["recent_diary"][:COMPACT_BATCH]
    lines = "\n".join(f"- [{d['time'][:16]}] {d['text']}" for d in old)
    out = chat_json([
        {"role": "system", "content": "You compress a crow's memories. Keep names, grudges, discoveries, wants and running jokes. Drop filler."},
        {"role": "user", "content": (
            f"Existing memory:\n{state['memory'] or '(none)'}\n\nNew diary lines to fold in:\n{lines}\n\n"
            f"Write the updated memory as one paragraph, first person, at most {MAX_MEMORY_WORDS} words. "
            "Condense: merge repeated events into one ('Derek took my gutter spot, repeatedly'), keep "
            "what matters from the existing memory, never copy lines verbatim. "
            "Respond in JSON: {\"memory\": \"...\"}"
        )},
    ], {"type": "object", "properties": {"memory": {"type": "string"}}, "required": ["memory"]}, temperature=0.3)
    words = out["memory"].split()
    state["memory"] = " ".join(words[: MAX_MEMORY_WORDS + 30])
    state["recent_diary"] = state["recent_diary"][COMPACT_BATCH:]
    return True


# ---------------------------------------------------------------- git

def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def commit_and_push(message: str, push: bool) -> None:
    if not (ROOT / ".git").exists():
        say("not a git repo, skipping commit")
        return
    git("add", "-A")
    r = git("commit", "-m", message)
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        say(f"commit failed: {r.stderr.strip() or r.stdout.strip()}")
    if push:
        r = git("push")
        if r.returncode != 0:
            say(f"push failed (will retry next run): {r.stderr.strip()}")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", choices=list(ACTIONS))
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()

    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 30 * 60:
        say("another run is busy, exiting")
        return 0
    LOCK.write_text(str(time.time()))
    try:
        ensure_ollama()
        state = load_json(STATE, None)
        if state is None:
            raise RuntimeError("state.json missing")
        log = load_json(LOG, [])
        started = time.time()

        action, args = choose_action(state, log, a.action)
        reason = (args.get("reason") or "").strip() or "no reason given, which is itself a reason"
        say(f"chose {action}: {args}")
        try:
            result = ACTIONS[action](state, args)
            ok = True
        except Exception as e:  # noqa: BLE001 - a failed action still becomes a (sulky) log entry
            say(f"{action} failed: {e}\n{traceback.format_exc()}")
            result = {"detail": {"error": str(e)[:300]}, "line": f"Tried to {action} and it went wrong. Blaming the pigeons."}
            ok = False

        result["line"] = clean_line(result["line"]) or "Nothing worth remembering. Suspicious in itself."
        entry = {"time": iso(), "action": action, "reason": reason, "ok": ok,
                 "line": result["line"], "detail": result["detail"],
                 "mood": state["mood"]["word"], "seconds": round(time.time() - started)}
        log.append(entry)
        state["recent_diary"].append({"time": entry["time"], "text": result["line"]})
        if compact_memory(state):
            say("memory compacted")
        state["last_run"] = entry["time"]
        state["runs"] = state.get("runs", 0) + 1
        save_json(LOG, log)
        save_json(STATE, state)
        say(f"done: {action} ({'ok' if ok else 'failed'}) - {result['line']}")

        if not a.no_git:
            commit_and_push(f"{state['persona']['name']}: {action} - {reason[:60]}", push=not a.no_push)
        return 0 if ok else 1
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
