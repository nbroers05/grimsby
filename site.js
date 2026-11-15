// Grimsby's site. Reads his public API (data/now, feed, mind, memories, who .json, written by the drive loop in
// drive/) plus the archive (log.json for diary entries, drawings/index.json) and fills the page.
// Everything Grimsby writes is model output, so it only ever goes in via textContent, and drawings via <img>.
(function () {
  "use strict";

  var STALE_AFTER = 25 * 60 * 1000;      // now (Supabase bird_state, else now.json) older than this = the laptop is off = he sleeps
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

  // ---------- live: Supabase (WERELD.md step 2), with data/*.json as fallback ----------
  // Only the publishable key is used here, and RLS lets it read only.
  var SB = null;
  try {
    var C = window.GRIMSBY_CONFIG && window.GRIMSBY_CONFIG.supabase;
    if (C && window.supabase) SB = window.supabase.createClient(C.url, C.key, { auth: { persistSession: false } });
  } catch (e) { SB = null; }

  // Gifts (WERELD.md step 3) go through their own client, which sends a random id of this browser along: the
  // database counts gifts per id for its rate limit (supabase/gifts.sql). Not a login, and never shown.
  var clientId = "";
  try {
    clientId = localStorage.getItem("grimsby-client") || "";
    if (!clientId) { clientId = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)); localStorage.setItem("grimsby-client", clientId); }
  } catch (e) { clientId = String(Math.random()).slice(2); }
  var SBG = null;
  try {
    if (C && window.supabase) SBG = window.supabase.createClient(C.url, C.key, { auth: { persistSession: false },
      global: { headers: { "x-grimsby-client": clientId } } });
  } catch (e) { SBG = null; }
  var GIFT_DAYS = 7, GIFT_MAX = 40;
  function myGifts() { try { return JSON.parse(localStorage.getItem("grimsby-gifts") || "[]"); } catch (e) { return []; } }
  function rememberGift(id) {
    try { localStorage.setItem("grimsby-gifts", JSON.stringify(myGifts().concat([id]).slice(-50))); } catch (e) {}
  }
  function loadGifts() {
    if (!SBG) return;
    var since = new Date(Date.now() - GIFT_DAYS * 864e5).toISOString();
    SBG.from("gifts").select("id,visitor_name,item,note,x,z,created_at,reply,taken")
      .gte("created_at", since).order("created_at", { ascending: false }).limit(GIFT_MAX)
      .then(function (r) {
        if (r.error) return;
        window.GRIMSBY_GIFTS = r.data || [];
        document.dispatchEvent(new CustomEvent("grimsby:gifts", { detail: window.GRIMSBY_GIFTS }));
        showMyReplies(window.GRIMSBY_GIFTS);
      });
  }
  // His answers to what you left, once each (on this browser)
  function showMyReplies(gifts) {
    var mine = myGifts(), shown;
    try { shown = JSON.parse(localStorage.getItem("grimsby-replies-seen") || "[]"); } catch (e) { shown = []; }
    var g = gifts.filter(function (x) { return mine.indexOf(x.id) >= 0 && x.reply && shown.indexOf(x.id) < 0; })[0];
    if (!g) return;
    var st = $("leave-status");
    st.textContent = "";
    st.appendChild(el("b", null, "He answered you"));
    st.appendChild(el("span", "hint", "“" + clean(g.reply) + "”"));
    st.appendChild(el("span", "hint", "next to your note in the sand"));
    st.hidden = false;
    clearTimeout(st._t); st._t = setTimeout(function () { st.hidden = true; }, 15000);
    try { localStorage.setItem("grimsby-replies-seen", JSON.stringify(shown.concat([g.id]).slice(-50))); } catch (e) {}
  }

  function withPos(row) {
    var now = Object.assign({}, row.now || {});
    if (row.x != null) now.pos = { x: row.x, z: row.z, target: { x: row.target_x, z: row.target_z, id: row.target_id } };
    return now;
  }
  function liveNow() {
    return SB.from("bird_state").select("now,x,z,target_x,target_z,target_id,at").eq("id", 1).maybeSingle()
      .then(function (r) { if (r.error || !r.data) throw r.error || new Error("no bird_state"); return withPos(r.data); });
  }
  function liveFeed() {
    return SB.from("feed").select("at,kind,text,why,ok,action,extra").order("at", { ascending: false }).limit(50)
      .then(function (r) {
        if (r.error || !r.data || !r.data.length) throw r.error || new Error("empty feed");
        var entries = r.data.map(function (e) {
          var o = Object.assign({}, e.extra || {}, { at: e.at, kind: e.kind, text: e.text });
          ["why", "ok", "action"].forEach(function (k) { if (e[k] != null) o[k] = e[k]; });
          return o;
        });
        return { v: 1, at: entries[0].at, entries: entries };
      });
  }
  function getNow() { return SB ? liveNow().catch(function () { return getJSON("data/now.json"); }) : getJSON("data/now.json"); }
  function getFeed() { return SB ? liveFeed().catch(function () { return getJSON("data/feed.json"); }) : getJSON("data/feed.json"); }

  var last = { drawings: [], mems: {}, mind: {}, feed: {} };
  function applyNow(now) {
    var asleep = renderStatus(now, last.drawings);
    window.GRIMSBY_DATA = { now: now, asleep: asleep };     // for world.js
    document.dispatchEvent(new CustomEvent("grimsby:data", { detail: window.GRIMSBY_DATA }));
    renderHud(now, asleep, last.mems);
  }
  var feedTimer = null, giftTimer = null;
  function subscribe() {
    if (!SB) return;
    SB.channel("grimsby-live")
      .on("postgres_changes", { event: "*", schema: "public", table: "bird_state" }, function (p) {
        if (p && p.new && p.new.now) applyNow(withPos(p.new));
      })
      .on("postgres_changes", { event: "*", schema: "public", table: "gifts" }, function () {
        clearTimeout(giftTimer); giftTimer = setTimeout(loadGifts, 600);   // new gifts, his replies, taken items
      })
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "feed" }, function () {
        clearTimeout(feedTimer);                    // a tick inserts a few rows at once: refresh once
        feedTimer = setTimeout(function () {
          liveFeed().then(function (feed) { last.feed = feed; renderDay(feed); renderWants(last.mind, feed); }).catch(function () {});
        }, 800);
      })
      .subscribe();
  }

  // ---------- tabs ----------
  var TABS = ["day", "wants", "drawings", "diary", "facts", "about"];
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
    var entries = log.filter(function (e) {
      return (e.action === "diary" || e.action === "dream") && (e.detail || {}).entry;
    }).reverse();
    if (!entries.length) { p.appendChild(el("p", "empty", "The diary is still empty.")); return; }
    var box = el("div", "entries");
    entries.forEach(function (e) {
      var d = e.detail || {};
      var dream = e.action === "dream";
      var a = el("article", dream ? "dream" : null);
      var head = el("span", "label");
      if (dream) head.appendChild(el("span", "pill dream-tag", "dream"));
      head.appendChild(timeEl(e.time, stamp(e.time)));
      a.appendChild(head);
      a.appendChild(el("h2", null, dream ? "A dream" : cap(d.topic || "Untitled")));
      a.appendChild(el("p", null, clean(d.entry || e.line)));
      box.appendChild(a);
    });
    p.appendChild(box);
  }

  function renderFacts(mems) {
    var p = $("panel-facts"); p.textContent = "";
    var facts = (mems.beliefs || []).filter(function (b) { return b && b.text; }).slice().sort(function (a, b) {
      return (b.n || 0) - (a.n || 0);
    });
    if (!facts.length) { p.appendChild(el("p", "empty", "He has not concluded anything yet. He is gathering evidence.")); return; }
    p.appendChild(el("p", "day-head", "what he has come to believe, newest first"));
    var ol = el("ol", "facts");
    facts.forEach(function (f) {
      var li = el("li");
      li.appendChild(el("span", "fact-n", f.n ? "fact " + f.n : "fact"));
      var t = el("div", "txt");
      t.appendChild(el("b", null, clean(f.text)));
      var sub = "based on " + f.evidence + (f.evidence === 1 ? " time" : " times");
      if (f.since) sub += " · since " + stamp(f.since);
      t.appendChild(el("span", null, sub));
      li.appendChild(t);
      ol.appendChild(li);
    });
    p.appendChild(ol);
    p.appendChild(el("p", "hint", "Facts fade when the evidence does. A fact that comes back keeps its number."));
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
    var v = el("div", "about-row version");
    var ver = who.version || 1;
    v.appendChild(el("span", "label", "version " + ver + " of him"));
    var log = Array.isArray(who.changelog) ? who.changelog : [];
    if (!log.length) v.appendChild(el("p", null, "As he was written. Nothing about him has changed yet; that happens in his sleep."));
    else {
      var ul = el("ul", "versions");
      log.forEach(function (c) {
        var li = el("li");
        li.appendChild(el("span", "fact-n", "v" + c.version));
        var when = c.day ? "the night of day " + c.day : c.at ? stamp(c.at) : "before versions were kept";
        li.appendChild(txt(cap(clean(c.added)) + ".", "Added to his " + clean(c.field) + ", " + when + "."));
        ul.appendChild(li);
      });
      v.appendChild(ul);
    }
    box.appendChild(v);
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

  // ---------- expanded world: the HUD ----------
  var worldBox = $("world"), hud = $("hud");
  var places = null, lastNow = {}, lastAsleep = false;
  getJSON("world/places.json").then(function (d) { places = d.places || []; drawMap(); }).catch(function () {});

  function fillNeeds(box, needs) {
    box.textContent = "";
    var top = null;
    NEEDS.forEach(function (n) { var v = needs[n[0]] || 0; if (top === null || v > (needs[top] || 0)) top = n[0]; });
    NEEDS.forEach(function (n) {
      var v = Math.max(0, Math.min(1, needs[n[0]] || 0));
      var row = el("div", "need" + (n[0] === top && v > 0.3 ? " top" : ""));
      row.appendChild(el("span", "need-name", n[1]));
      var bar = el("span", "need-bar"), fill = el("span", "need-fill");
      fill.style.width = Math.round(v * 100) + "%";
      bar.appendChild(fill); row.appendChild(bar);
      row.title = n[1] + ": " + Math.round(v * 100) + "%" + (row.classList.contains("top") ? " (pulls hardest)" : "");
      box.appendChild(row);
    });
  }

  var SVGNS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs, parent) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  var mapFit = null;
  function drawMap() {
    var svg = $("hud-map");
    if (!svg || !places || !places.length) return;
    svg.textContent = "";
    var xs = places.map(function (p) { return p.x; }), zs = places.map(function (p) { return p.z; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), z0 = Math.min.apply(null, zs), z1 = Math.max.apply(null, zs);
    var pad = 18, w = 230, h = 190;
    var s = Math.min((w - 2 * pad) / Math.max(1, x1 - x0), (h - 2 * pad) / Math.max(1, z1 - z0));
    var ox = (w - (x1 - x0) * s) / 2, oz = (h - (z1 - z0) * s) / 2;
    mapFit = function (x, z) { return [ox + (x - x0) * s, oz + (z - z0) * s]; };
    svgEl("rect", { x: 0, y: 0, width: w, height: h, class: "map-ground" }, svg);
    places.forEach(function (p) {
      var c = mapFit(p.x, p.z);
      var dot = svgEl("circle", { cx: c[0].toFixed(1), cy: c[1].toFixed(1), r: 3.2, class: "map-place" + (p.id === "home" ? " home" : "") }, svg);
      svgEl("title", {}, dot).textContent = cap(p.name);
    });
    svgEl("polygon", { id: "map-you", class: "map-you", points: "0,-6 5,4 -5,4" }, svg);
    svgEl("polygon", { id: "map-him", class: "map-him", points: "0,-6 6,0 0,6 -6,0" }, svg);
    placeMarkers();
  }
  function placeMarkers() {
    if (!mapFit) return;
    var pid = lastAsleep ? "home" : ((lastNow.place || {}).id || "home");
    var p = places.filter(function (q) { return q.id === pid; })[0] || places[0];
    var c = mapFit(p.x, p.z);
    var him = document.getElementById("map-him");
    if (him) him.setAttribute("transform", "translate(" + c[0].toFixed(1) + " " + c[1].toFixed(1) + ")");
    var you = document.getElementById("map-you"), w3 = window.__grimsbyWorld;
    var t = w3 && w3.you ? w3.you : null;
    var cy = t ? mapFit(t.x, t.z) : [c[0] + 9, c[1] + 9];
    cy = [Math.max(6, Math.min(224, cy[0])), Math.max(6, Math.min(184, cy[1]))];
    if (you) you.setAttribute("transform", "translate(" + cy[0].toFixed(1) + " " + cy[1].toFixed(1) + ")");
  }

  function renderHud(now, asleep, mems) {
    lastNow = now; lastAsleep = asleep;
    var at = now.at ? new Date(now.at).getTime() : 0;
    var off = !at || Date.now() - at > STALE_AFTER;
    var name = clean(now.name) || "Grimsby";
    $("hud-exe").textContent = name.toLowerCase() + ".exe";
    fillNeeds($("hud-needs"), off ? {} : (now.needs || {}));
    var f = now.feeling || {};
    $("hud-mood").textContent = off ? "away" : moodWord(f.mood || 0);
    $("hud-energy").textContent = off ? "–" : energyWord(f.energy || 0);
    $("hud-now-title").textContent = off ? "Asleep. The computer is off." : asleep ? "Asleep on the roof" : cap(now.doing || "Looking around");
    $("hud-now-thought").textContent = off ? "He is processing what he saw today. He wakes up when the computer does." :
      asleep ? "Head under his wing." : now.thought ? "“" + clean(now.thought) + "”" : clean(f.words);
    var where = $("where");
    $("hud-now-where").textContent = where ? where.textContent : "";
    var w = now.world || {};
    $("hud-day").textContent = w.day ? "day " + w.day + " of his life, " + clean(w.time) + " his time" : "";
    placeMarkers();
  }
  function tickClock() {
    $("hud-time").textContent = fmt(new Date().toISOString(), { hour: "2-digit", minute: "2-digit", hour12: false });
    var where = $("where");                       // world.js writes it after the data arrives
    if (where) $("hud-now-where").textContent = where.textContent;
    placeMarkers();
  }

  var opener = null, clockTimer = null;
  function setOpen(open, from) {
    if (open === worldBox.classList.contains("open")) return;
    worldBox.classList.toggle("open", open);
    document.documentElement.classList.toggle("world-open", open);
    hud.hidden = !open;
    $("world-open").setAttribute("aria-expanded", open ? "true" : "false");
    $("world-walk").setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      opener = from || $("world-open");
      tickClock(); clockTimer = setInterval(tickClock, 1000);
      if (location.hash !== "#world") history.pushState({ world: true }, "", "#world");
      $("world-close").focus();
    } else {
      clearInterval(clockTimer); closeModal();
      if (location.hash === "#world") history.pushState({}, "", location.pathname + location.search);
      if (opener) opener.focus();
    }
  }
  $("world-open").addEventListener("click", function (e) { setOpen(true, e.currentTarget); });
  $("world-walk").addEventListener("click", function (e) { setOpen(true, e.currentTarget); });
  $("world-close").addEventListener("click", function () { setOpen(false); });
  $("hud-diary").addEventListener("click", function (e) { e.preventDefault(); setOpen(false); pick("diary"); $("tab-diary").scrollIntoView({ block: "center" }); });
  window.addEventListener("popstate", function () { setOpen(location.hash === "#world"); });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || !worldBox.classList.contains("open")) return;
    if (!$("leave-modal").hidden) closeModal(); else setOpen(false);
  });
  if (location.hash === "#world") setOpen(true);

  function showNowCard(show) {
    $("hud-now").hidden = !show; $("hud-now-show").hidden = show;
    try { localStorage.setItem("grimsby-nowcard", show ? "1" : "0"); } catch (e) {}
    (show ? $("hud-now-hide") : $("hud-now-show")).focus();
  }
  $("hud-now-hide").addEventListener("click", function () { showNowCard(false); });
  $("hud-now-show").addEventListener("click", function () { showNowCard(true); });
  try { if (localStorage.getItem("grimsby-nowcard") === "0") { $("hud-now").hidden = true; $("hud-now-show").hidden = false; } } catch (e) {}

  // Leave something (WERELD.md step 3): into Supabase, where you stand (or by the water near the station).
  var item = "walnut";
  function closeModal() {
    if ($("leave-modal").hidden) return;
    $("leave-modal").hidden = true; $("leave-open").focus();
  }
  $("leave-open").addEventListener("click", function () {
    $("leave-modal").hidden = false; $("leave-status").hidden = true; $("leave-err").hidden = true;
    try { $("leave-name").value = localStorage.getItem("grimsby-name") || ""; } catch (e) {}
    ($("leave-name").value ? $("leave-note") : $("leave-name")).focus();
  });
  $("leave-cancel").addEventListener("click", closeModal);
  $("leave-modal").addEventListener("click", function (e) { if (e.target === e.currentTarget) closeModal(); });
  $("leave-items").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-item]");
    if (!b) return;
    item = b.dataset.item;
    [].forEach.call(this.querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    $("leave-other").hidden = item !== "other";
    if (item === "other") $("leave-other").focus();
  });
  $("leave-note").addEventListener("input", function () {
    $("leave-count").textContent = this.value.length + " / 280"; $("leave-err").hidden = true;
  });
  $("leave-name").addEventListener("input", function () { $("leave-err").hidden = true; });
  $("leave-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var nm = $("leave-name").value.trim(), note = $("leave-note").value.trim();
    var err = $("leave-err");
    if (!nm) { err.textContent = "Fill in a name first, so he knows who to be suspicious of."; err.hidden = false; $("leave-name").focus(); return; }
    if (item === "note" && !note) { err.textContent = "Just a note needs a note."; err.hidden = false; $("leave-note").focus(); return; }
    var thing = item === "walnut" ? "a walnut" : item === "button" ? "a button" : item === "other" ? $("leave-other").value.trim() : "";
    if (item === "other" && !thing) { err.textContent = "Say what it is."; err.hidden = false; $("leave-other").focus(); return; }
    try { localStorage.setItem("grimsby-name", nm); } catch (x) {}
    var st = $("leave-status");
    function status(head, text) {
      st.textContent = ""; st.appendChild(el("b", null, head)); st.appendChild(el("span", "hint", text)); st.hidden = false;
      clearTimeout(st._t); st._t = setTimeout(function () { st.hidden = true; }, 10000);
    }
    if (!SBG) { err.textContent = "His world cannot be reached right now. Try again later."; err.hidden = false; return; }
    var w3 = window.__grimsbyWorld, at = w3 && w3.dropPoint ? w3.dropPoint() : { x: -72, z: 192 };
    var send = $("leave-form").querySelector("button[type=submit]");
    send.disabled = true;
    SBG.from("gifts").insert({ visitor_name: nm, item: thing || null, note: note || null,
      x: Math.round(at.x * 10) / 10, z: Math.round(at.z * 10) / 10 }).select("id").single().then(function (r) {
      send.disabled = false;
      if (r.error) {
        err.textContent = /too many|rate_limit/i.test((r.error.message || "") + (r.error.hint || "")) ?
          "That is a lot of things for one crow. Try again in an hour." : "It did not land. Try again in a bit.";
        err.hidden = false; return;
      }
      rememberGift(r.data.id);
      $("leave-note").value = ""; $("leave-count").textContent = "0 / 280"; $("leave-other").value = "";
      $("leave-modal").hidden = true;
      status("It is in the sand.", "Anyone walking past can read it. His answer appears next to it once he has read it (and wants to).");
      loadGifts();
      $("leave-open").focus();
    }, function () { send.disabled = false; err.textContent = "It did not land. Try again in a bit."; err.hidden = false; });
  });

  function load() {
    var none = function () { return {}; };
    Promise.all([
      getNow(),
      getFeed().catch(none),
      getJSON("data/mind.json").catch(none),
      getJSON("data/memories.json").catch(none),
      getJSON("data/who.json").catch(none),
      getJSON("log.json").catch(function () { return []; }),
      getJSON("drawings/index.json").catch(function () { return []; })
    ]).then(function (r) {
      var now = r[0] || {}, feed = r[1], mind = r[2], mems = r[3], who = r[4];
      var log = (Array.isArray(r[5]) ? r[5] : []).filter(function (e) { return e && e.ok && !e.withheld; });
      var drawings = Array.isArray(r[6]) ? r[6].filter(function (d) { return d && /^drawings\/[\w.-]+\.svg$/.test(d.file || ""); }) : [];
      last = { drawings: drawings, mems: mems, mind: mind, feed: feed };
      applyNow(now);
      renderDay(feed);
      renderWants(mind, feed);
      renderDrawings(drawings);
      renderDiary(log);
      renderFacts(mems);
      renderAbout(who, mind, mems);
    }).catch(function () {
      $("now").textContent = "Could not reach Grimsby. Try again in a bit.";
    });
  }
  load();
  loadGifts();
  subscribe();
  setInterval(load, SB ? 4 * REFRESH : REFRESH);   // live: Realtime does the work, this only catches up
})();
