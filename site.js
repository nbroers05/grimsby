// Grimsby's site. Reads state.json, log.json and drawings/index.json (written by brain.py) and fills the page.
// Everything Grimsby writes is model output, so it only ever goes in via textContent, and drawings via <img>.
(function () {
  "use strict";

  var SLEEP_AFTER = 2 * 60 * 60 * 1000;   // last run longer than 2 h ago = the computer is off
  var REFRESH = 5 * 60 * 1000;
  var TZ = "Europe/Amsterdam";
  var ACT = { search: "search", diary: "diary", draw: "drawing" };

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
  function headline(e) {
    var d = e.detail || {};
    if (e.action === "search") return cap(d.query || d.title || "something");
    if (e.action === "diary") return cap(d.topic || e.line);
    if (e.action === "draw") return cap(d.title || d.subject || "a drawing");
    return cap(e.line);
  }
  function nowText(e) {
    var d = e.detail || {};
    if (e.action === "search") return "Just looked up: " + clean(d.query || d.title).toLowerCase() + ".";
    if (e.action === "diary") return "Just wrote in his diary about " + clean(d.topic || "something").toLowerCase() + ".";
    if (e.action === "draw") return "Just drew " + clean(d.title || "something") + ".";
    return clean(e.line);
  }

  function renderDay(log) {
    var p = $("panel-day"); p.textContent = "";
    if (!log.length) { p.appendChild(el("p", "empty", "He has not done anything yet.")); return; }
    var last = log[log.length - 1].time;
    var key = dayKey(last);
    var today = dayKey(new Date().toISOString()) === key;
    p.appendChild(el("p", "day-head", today ? "today" : dayName(last)));
    var ol = el("ol", "day");
    log.filter(function (e) { return dayKey(e.time) === key; }).forEach(function (e) {
      var li = el("li");
      li.appendChild(timeEl(e.time, hm(e.time)));
      li.appendChild(el("span", "act", ACT[e.action] || e.action));
      li.appendChild(txt(headline(e), e.reason ? "His reason: " + clean(e.reason) : ""));
      ol.appendChild(li);
    });
    p.appendChild(ol);
  }

  function wishRow(w, closed) {
    var li = el("li", closed ? "closed" : "");
    var sub = closed ? clean(w.note || w.reason) : clean(w.reason);
    li.appendChild(txt(cap(w.item), sub));
    if (!closed) li.appendChild(el("span", "pill hot", "wants it"));
    else if (w.outcome === "got") li.appendChild(el("span", "pill eva", "got it"));
    else li.appendChild(el("span", "pill gone", "gave up"));
    return li;
  }
  function renderWants(state) {
    var p = $("panel-wants"); p.textContent = "";
    var open = state.wishlist || [], done = (state.wish_history || []).slice().reverse();
    if (!open.length && !done.length) { p.appendChild(el("p", "empty", "He wants nothing. He says.")); return; }
    if (open.length) {
      var ul = el("ul", "wants");
      open.forEach(function (w) { ul.appendChild(wishRow(w, false)); });
      p.appendChild(ul);
    } else p.appendChild(el("p", "empty", "Nothing on his list right now."));
    if (done.length) {
      p.appendChild(el("p", "sub-head", "earlier"));
      var ul2 = el("ul", "wants");
      done.forEach(function (w) { ul2.appendChild(wishRow(w, true)); });
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
    var entries = log.filter(function (e) { return e.action === "diary"; }).reverse();
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

  function renderAbout(state) {
    var p = $("panel-about"); p.textContent = "";
    var box = el("div", "about");
    box.appendChild(el("p", null, "A crow who lives on a computer in Berkel en Rodenrijs. Awake when the computer is on, gone when it goes off. Reads things on the internet, writes too much about them and draws what he does not understand."));
    var wrap = el("div"); wrap.style.cssText = "display:flex;flex-direction:column;gap:8px";
    wrap.appendChild(el("span", "label", "interests"));
    var chips = el("div", "chips");
    (state.interests || []).slice().sort(function (a, b) { return (b.strength || 0) - (a.strength || 0); })
      .forEach(function (i) { chips.appendChild(el("span", "pill eva", clean(i.topic))); });
    (state.past_interests || []).slice().reverse().forEach(function (t) {
      chips.appendChild(el("span", "pill gone", clean(typeof t === "string" ? t : t.topic)));
    });
    wrap.appendChild(chips);
    wrap.appendChild(el("span", "hint", (state.past_interests || []).length
      ? "Strongest first. Struck through: interests he is done with."
      : "Strongest first. Ones he gets bored of will show up struck through."));
    box.appendChild(wrap);
    p.appendChild(box);
  }

  function renderStatus(state, log, drawings) {
    var lastRun = state.last_run ? new Date(state.last_run).getTime() : 0;
    var asleep = !lastRun || Date.now() - lastRun > SLEEP_AFTER || /[?&]sleep\b/.test(location.search);   // ?sleep = test the sleep look
    var name = clean((state.persona || {}).name) || "Grimsby";
    document.documentElement.classList.toggle("asleep", asleep);
    $("name").textContent = name;
    document.title = name + (asleep ? " (asleep)" : "");
    $("kop").textContent = asleep ? "Asleep. Computer is off." : "Is awake. Unfortunately.";
    var crow = document.querySelector(".world-flat");
    crow.setAttribute("aria-label", asleep ? name + " is asleep" : name + " is standing on the ground, looking around");
    var last = log[log.length - 1];
    $("now").textContent = asleep
      ? (lastRun ? "Asleep since " + hm(state.last_run) + (dayKey(state.last_run) === dayKey(new Date().toISOString()) ? "" : " on " + dayName(state.last_run)) + ". Wakes up when the computer turns on." : "Has not woken up yet.")
      : (last ? nowText(last) : "Just woke up.");
    var mood = state.mood || {};
    $("st-mood").textContent = asleep ? "away" : (clean(mood.word) || "–");
    $("st-last").textContent = state.last_run ? hm(state.last_run) : "–";
    $("st-runs").textContent = state.runs != null ? state.runs : "–";
    $("st-drawings").textContent = drawings.length;
    var note = $("st-note");
    note.hidden = asleep || !mood.note;
    note.textContent = clean(mood.note);
    return asleep;
  }

  function load() {
    Promise.all([
      getJSON("state.json"),
      getJSON("log.json").catch(function () { return []; }),
      getJSON("drawings/index.json").catch(function () { return []; })
    ]).then(function (r) {
      var state = r[0] || {};
      var log = (Array.isArray(r[1]) ? r[1] : []).filter(function (e) { return e && e.ok && !e.withheld; });
      var drawings = Array.isArray(r[2]) ? r[2].filter(function (d) { return d && /^drawings\/[\w.-]+\.svg$/.test(d.file || ""); }) : [];
      var asleep = renderStatus(state, log, drawings);
      window.GRIMSBY_DATA = { state: state, log: log, asleep: asleep };     // for world.js
      document.dispatchEvent(new CustomEvent("grimsby:data", { detail: window.GRIMSBY_DATA }));
      renderDay(log);
      renderWants(state);
      renderDrawings(drawings);
      renderDiary(log);
      renderAbout(state);
    }).catch(function () {
      $("now").textContent = "Could not reach Grimsby. Try again in a bit.";
    });
  }
  load();
  setInterval(load, REFRESH);
})();
