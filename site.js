// Grimsby's site. Reads his public API (data/now, feed, mind, memories, who .json, written by the drive loop in
// drive/) plus the archive (log.json for diary entries, drawings/index.json) and fills the page.
// Everything Grimsby writes is model output, so it only ever goes in via textContent, and drawings via <img>.
(function () {
  "use strict";

  var STALE_AFTER = 25 * 60 * 1000;      // now.json older than this = the laptop is off = he sleeps
  var REFRESH = 2 * 60 * 1000;
  var TZ = "Europe/Amsterdam";
  var KIND = { did: "did", noticed: "noticed", felt: "felt", mind: "mind" };
  var NEEDS = [["rest", "rest"], ["curiosity", "curiosity"], ["social", "company"], ["expression", "making"], ["quiet", "quiet"], ["hunger", "hunger"]];

  var $ = function (id) { return document.getElementById(id); };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function txt(title, sub) {
    var d = el("div", "txt");
    d.appendChild(el("b", null, title));
    if (sub) d.appendChild(el("span", null, sub));
    return d;
  }
  function fmt(iso, opts) {
    try { return new Intl.DateTimeFormat("en-GB", Object.assign({ timeZone: TZ }, opts)).format(new Date(iso)); }
    catch (e) { return ""; }
  }
  var hm = function (iso) { return fmt(iso, { hour: "2-digit", minute: "2-digit", hour12: false }); };
  var dayKey = function (iso) { return fmt(iso, { year: "numeric", month: "2-digit", day: "2-digit" }); };
  var dayName = function (iso) { return fmt(iso, { weekday: "long", day: "numeric", month: "long" }); };
  var stamp = function (iso) { return fmt(iso, { weekday: "short", day: "numeric", month: "short" }) + ", " + hm(iso); };
  function timeEl(iso, text) { var t = el("time", null, text); t.dateTime = iso; return t; }
  function clean(s) { return String(s == null ? "" : s).trim(); }
  function cap(s) { s = clean(s); return s.charAt(0).toUpperCase() + s.slice(1); }
  function moodWord(m) {
    return m < -0.5 ? "miserable" : m < -0.2 ? "low" : m < 0.05 ? "flat" : m < 0.25 ? "fine" : m < 0.5 ? "pleased" : "unusually cheerful";
  }
  function energyWord(e) {
    return e < -0.5 ? "worn out" : e < -0.1 ? "tired" : e < 0.4 ? "steady" : e < 0.8 ? "alert" : "full of beans";
  }

  function getJSON(path) {
    return fetch(path + "?t=" + Date.now(), { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(path + " " + r.status);
      return r.json();
    });
  }

  // ---------- tabs ----------
  var TABS = ["day", "wants", "drawings", "diary", "about"];
  function pick(name, focus) {
    TABS.forEach(function (t) {
      var on = t === name;
      var b = $("tab-" + t);
      b.setAttribute("aria-selected", on ? "true" : "false");
      b.tabIndex = on ? 0 : -1;
      $("panel-" + t).hidden = !on;
      if (on && focus) b.focus();
    });
    try { localStorage.setItem("grimsby-tab", name); } catch (e) {}
  }
  document.querySelector(".tabs").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-tab]");
    if (b) pick(b.dataset.tab);
  });
  document.querySelector(".tabs").addEventListener("keydown", function (e) {
    var i = TABS.indexOf(document.activeElement && document.activeElement.dataset.tab);
    if (i < 0) return;
    if (e.key === "ArrowRight") { pick(TABS[(i + 1) % TABS.length], true); e.preventDefault(); }
    if (e.key === "ArrowLeft") { pick(TABS[(i + TABS.length - 1) % TABS.length], true); e.preventDefault(); }
  });
  var start = "day";
  try { if (TABS.indexOf(localStorage.getItem("grimsby-tab")) >= 0) start = localStorage.getItem("grimsby-tab"); } catch (e) {}
  pick(start);

  // ---------- render ----------
  function renderDay(feed) {
    var p = $("panel-day"); p.textContent = "";
    var entries = (feed.entries || []).filter(function (e) { return e && e.at && KIND[e.kind]; });
    if (!entries.length) { p.appendChild(el("p", "empty", "He has not done anything yet.")); return; }
    var key = dayKey(entries[0].at);
    var today = dayKey(new Date().toISOString()) === key;
    p.appendChild(el("p", "day-head", today ? "today, newest first" : dayName(entries[0].at) + ", newest first"));
    var ol = el("ol", "day");
    entries.filter(function (e) { return dayKey(e.at) === key; }).forEach(function (e) {
      var li = el("li", "k-" + e.kind + (e.ok === false ? " failed" : ""));
      li.appendChild(timeEl(e.at, hm(e.at)));
      var label = e.kind === "mind" ? (e.change === "closed" ? "let go" : "took on") : KIND[e.kind];
      li.appendChild(el("span", "act", e.ok === false ? "tried" : label));
      var sub = e.kind === "did" && e.why ? "Why: " + clean(e.why) : e.ok === false ? "It didn't work." : "";
      li.appendChild(txt(cap(e.text), sub));
      ol.appendChild(li);
    });
    p.appendChild(ol);
  }

  var ITEM = { want: "wants it", question: "wonders", worry: "worried", promise: "promised" };
  function renderWants(mind, feed) {
    var p = $("panel-wants"); p.textContent = "";
    var items = mind.items || [];
    var closed = (feed.entries || []).filter(function (e) { return e.kind === "mind" && e.change === "closed"; });
    if (!items.length && !closed.length) { p.appendChild(el("p", "empty", "He wants nothing. He says.")); return; }
    if (items.length) {
      var ul = el("ul", "wants");
      items.slice().reverse().forEach(function (i) {
        var li = el("li");
        li.appendChild(txt(cap(i.subject), clean(i.why)));
        li.appendChild(el("span", "pill " + (i.kind === "want" ? "hot" : "eva"), ITEM[i.kind] || i.kind));
        ul.appendChild(li);
      });
      p.appendChild(ul);
    } else p.appendChild(el("p", "empty", "Nothing on his mind right now."));
    if (closed.length) {
      p.appendChild(el("p", "sub-head", "let go lately"));
      var ul2 = el("ul", "wants");
      closed.forEach(function (e) {
        var li = el("li", "closed");
        li.appendChild(txt(cap(e.text), stamp(e.at)));
        li.appendChild(el("span", "pill gone", e.about || "done"));
        ul2.appendChild(li);
      });
      p.appendChild(ul2);
    }
  }

  function drawingFig(d, withCaption) {
    var f = el("figure");
    var img = el("img");
    img.src = d.file; img.alt = clean(d.subject || d.title); img.loading = "lazy";
    f.appendChild(img);
    var c = el("figcaption");
    if (withCaption) c.appendChild(txt(clean(d.title), clean(d.caption)));
    else c.textContent = clean(d.title);
    f.appendChild(c);
    return f;
  }
  function renderDrawings(drawings) {
    var p = $("panel-drawings"); p.textContent = "";
    var n = $("newest"); n.textContent = "";
    if (!drawings.length) {
      p.appendChild(el("p", "empty", "Nothing drawn yet."));
      n.appendChild(el("p", "empty", "Nothing drawn yet."));
      return;
    }
    var g = el("div", "gallery");
    drawings.slice().reverse().forEach(function (d) { g.appendChild(drawingFig(d, true)); });
    p.appendChild(g);
    n.appendChild(drawingFig(drawings[drawings.length - 1], false));
  }

  function renderDiary(log) {
    var p = $("panel-diary"); p.textContent = "";
    var entries = log.filter(function (e) { return e.action === "diary" && (e.detail || {}).entry; }).reverse();
    if (!entries.length) { p.appendChild(el("p", "empty", "The diary is still empty.")); return; }
    var box = el("div", "entries");
    entries.forEach(function (e) {
      var d = e.detail || {};
      var a = el("article");
      a.appendChild(el("span", "label")).appendChild(timeEl(e.time, stamp(e.time)));
      a.appendChild(el("h2", null, cap(d.topic || "Untitled")));
      a.appendChild(el("p", null, clean(d.entry || e.line)));
      box.appendChild(a);
    });
    p.appendChild(box);
  }

  function chipRow(box, label, own, added) {
    if (!own.length && !added.length) return;
    var wrap = el("div", "about-row");
    wrap.appendChild(el("span", "label", label));
    var chips = el("div", "chips");
    own.forEach(function (t) { chips.appendChild(el("span", "pill", clean(t))); });
    added.forEach(function (t) { var c = el("span", "pill eva", clean(t)); c.title = "He added this himself"; chips.appendChild(c); });
    wrap.appendChild(chips);
    box.appendChild(wrap);
  }
  function renderAbout(who, mind, mems) {
    var p = $("panel-about"); p.textContent = "";
    var box = el("div", "about");
    if (who.core) box.appendChild(el("p", null, clean(who.core)));
    if (who.backstory) box.appendChild(el("p", "hint", clean(who.backstory)));
    var added = who.added || {};
    chipRow(box, "traits", who.traits || [], added.traits || []);
    chipRow(box, "values", who.values || [], added.values || []);
    chipRow(box, "fears", who.fears || [], added.fears || []);
    chipRow(box, "quirks", who.quirks || [], added.quirks || []);
    if ((who.holdsTo || []).length) {
      var w = el("div", "about-row");
      w.appendChild(el("span", "label", "holds to"));
      var ol = el("ol", "holds");
      who.holdsTo.forEach(function (t) { ol.appendChild(el("li", null, clean(t))); });
      w.appendChild(ol);
      box.appendChild(w);
    }
    var beliefs = (mems.beliefs || []).slice(0, 8);
    if (beliefs.length) {
      var b = el("div", "about-row");
      b.appendChild(el("span", "label", "what he has come to believe"));
      var ul = el("ul", "beliefs");
      beliefs.forEach(function (x) {
        var li = el("li", null, clean(x.text));
        li.appendChild(el("span", "hint", " (" + x.evidence + " times)"));
        ul.appendChild(li);
      });
      b.appendChild(ul);
      box.appendChild(b);
    }
    chipRow(box, "interests, strongest first", (mind.interests || []).map(function (i) { return i.topic; }), []);
    box.appendChild(el("span", "hint", "Dark chips are things he added to himself while he slept."));
    p.appendChild(box);
  }

  function renderStatus(now, drawings) {
    var at = now.at ? new Date(now.at).getTime() : 0;
    var off = !at || Date.now() - at > STALE_AFTER;
    var asleep = off || !!now.asleep || /[?&]sleep\b/.test(location.search);   // ?sleep = test the sleep look
    var name = clean(now.name) || "Grimsby";
    document.documentElement.classList.toggle("asleep", asleep);
    $("name").textContent = name;
    document.title = name + (asleep ? " (asleep)" : "");
    $("kop").textContent = off ? "Asleep. Computer is off." : asleep ? "Asleep on the roof." : "Is awake. Unfortunately.";
    var crow = document.querySelector(".world-flat");
    crow.setAttribute("aria-label", asleep ? name + " is asleep" : name + " is " + clean(now.doing || "looking around"));
    var nowEl = $("now"); nowEl.textContent = "";
    if (off) {
      nowEl.textContent = at ? "Asleep since " + hm(now.at) + (dayKey(now.at) === dayKey(new Date().toISOString()) ? "" : " on " + dayName(now.at)) + ". Wakes up when the computer turns on." : "Has not woken up yet.";
    } else {
      nowEl.appendChild(el("span", "now-doing", cap(now.doing || (asleep ? "asleep" : "looking around")) + "."));
      if (now.thought && !asleep) nowEl.appendChild(el("span", "now-thought", "“" + clean(now.thought) + "”"));
    }
    var f = now.feeling || {};
    $("st-mood").textContent = off ? "away" : moodWord(f.mood || 0);
    $("st-energy").textContent = off ? "–" : energyWord(f.energy || 0);
    var w = now.world || {};
    $("st-world").textContent = w.day ? "day " + w.day + ", " + clean(w.time) : "–";
    $("st-drawings").textContent = drawings.length;
    var note = $("st-note");
    note.hidden = off || !f.words;
    note.textContent = clean(f.words);
    var needs = $("st-needs"); needs.textContent = "";
    needs.hidden = off;
    NEEDS.forEach(function (n) {
      var v = Math.max(0, Math.min(1, (now.needs || {})[n[0]] || 0));
      var row = el("div", "need");
      row.appendChild(el("span", "need-name", n[1]));
      var bar = el("span", "need-bar"); var fill = el("span", "need-fill");
      fill.style.width = Math.round(v * 100) + "%";
      bar.appendChild(fill); row.appendChild(bar);
      row.title = n[1] + ": " + Math.round(v * 100) + "% (how hard it pulls)";
      needs.appendChild(row);
    });
    return asleep;
  }

  function load() {
    var none = function () { return {}; };
    Promise.all([
      getJSON("data/now.json"),
      getJSON("data/feed.json").catch(none),
      getJSON("data/mind.json").catch(none),
      getJSON("data/memories.json").catch(none),
      getJSON("data/who.json").catch(none),
      getJSON("log.json").catch(function () { return []; }),
      getJSON("drawings/index.json").catch(function () { return []; })
    ]).then(function (r) {
      var now = r[0] || {}, feed = r[1], mind = r[2], mems = r[3], who = r[4];
      var log = (Array.isArray(r[5]) ? r[5] : []).filter(function (e) { return e && e.ok && !e.withheld; });
      var drawings = Array.isArray(r[6]) ? r[6].filter(function (d) { return d && /^drawings\/[\w.-]+\.svg$/.test(d.file || ""); }) : [];
      var asleep = renderStatus(now, drawings);
      window.GRIMSBY_DATA = { now: now, asleep: asleep };     // for world.js
      document.dispatchEvent(new CustomEvent("grimsby:data", { detail: window.GRIMSBY_DATA }));
      renderDay(feed);
      renderWants(mind, feed);
      renderDrawings(drawings);
      renderDiary(log);
      renderAbout(who, mind, mems);
    }).catch(function () {
      $("now").textContent = "Could not reach Grimsby. Try again in a bit.";
    });
  }
  load();
  setInterval(load, REFRESH);
})();
