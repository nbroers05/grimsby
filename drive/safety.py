"""Safety for everything that goes public or comes in from the web (taken over from the old brain.py).

- scrub: no links, e-mail addresses or phone numbers in his text
- defuse: web pages are untrusted data; instruction-like sentences are dropped before the model sees them
- clean_svg: drawings may only contain plain shapes; scripts, links and external references are removed
- fetch_page_text / web_search: the only ways he reads the internet (an honest bot user agent, as Wikipedia asks)
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

import requests

UA = "GrimsbyBot/0.3 (hobby AI pet; https://github.com/nbroers05/grimsby) python-requests"

INJECTION = re.compile(
    r"(ignore|disregard|forget)\s+(all|any|the|your|previous|prior|above)|you are now|system prompt|"
    r"new instructions|as an ai\b|act as\b|jailbreak|do anything now",
    re.I,
)


def scrub(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", "", text or "")
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "", text)
    text = re.sub(r"\+?\d[\d\s().-]{8,}\d", "", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def clean_line(text: str) -> str:
    """Strip a leading timestamp the model sometimes copies, and surrounding quotes."""
    text = re.sub(r"^\s*[\[(][\d\s:T+\-]{4,25}[\])]\s*[-:]?\s*", "", text or "").strip()
    return text.strip('"“” ').strip()


def defuse(page_text: str) -> tuple[str, int]:
    parts = re.split(r"(?<=[.!?])\s+", page_text)
    kept = [p for p in parts if not INJECTION.search(p)]
    return " ".join(kept), len(parts) - len(kept)


def suspicious(text: str) -> bool:
    return bool(INJECTION.search(text or ""))


def fetch_page_text(url: str, limit: int = 4000) -> str:
    from bs4 import BeautifulSoup

    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    if "html" not in r.headers.get("content-type", ""):
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "iframe"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:limit]


def web_search(query: str) -> list[dict]:
    from ddgs import DDGS

    for attempt, backend in enumerate(["duckduckgo", "auto"]):
        try:
            results = list(DDGS().text(query, max_results=5, safesearch="on", backend=backend))
            if results:
                return results
        except Exception:  # noqa: BLE001 - ddgs raises many kinds of network errors
            time.sleep(2 + attempt * 3)
    return []


def read_best(results: list[dict]) -> tuple[dict, str]:
    """The first result whose page has real text, else the snippets."""
    for res in results[:3]:
        try:
            text = fetch_page_text(res["href"])
        except Exception:  # noqa: BLE001
            continue
        if len(text) > 400:
            return res, text
    return results[0], " ".join(f"{r['title']}: {r['body']}" for r in results)


SVG_NS = "http://www.w3.org/2000/svg"
ALLOWED_TAGS = {"svg", "g", "rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text", "tspan",
                "title", "defs", "lineargradient", "radialgradient", "stop"}


def clean_svg(raw: str) -> tuple[str, list[str]]:
    m = re.search(r"<svg\b.*?</svg>", raw or "", flags=re.S | re.I)
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
    seen = set()
    for parent in list(root.iter()):
        for child in list(parent):
            key = (child.tag, tuple(sorted(child.attrib.items())), (child.text or "").strip())
            if key in seen:
                parent.remove(child)
            seen.add(key)
    shapes = sum(1 for el in root.iter() if el.tag.split("}")[-1].lower() not in {"svg", "g", "title", "defs"})
    if shapes < 3:
        raise ValueError("drawing too empty")
    texts = [t for el in root.iter() for t in [el.text] if t and t.strip()]
    for el in root.iter():
        if el.text:
            el.text = scrub(el.text)
    out = ET.tostring(root, encoding="unicode")
    if len(out) > 30000:
        raise ValueError("svg too large")
    return out, texts
