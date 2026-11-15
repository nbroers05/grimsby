// Grimsby's 3D world: his island (island.js, built in code at load) with the crow at the place in data/now.json.
// Folded into the page you look around him; expanded (site.js adds .open) you walk around on foot (walk.js).
// site.js loads data/now.json and sends it here with a "grimsby:data" event ({now, asleep}); this file only draws.
// If WebGL or the files fail, the flat placeholder scene in index.html simply stays.
// The look (materials, moods, crow) is in look.js and the choice of place in place.js: the dashboard panel uses them too.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { buildIsland, islandMeshes } from "./island.js";
import { makeWalker } from "./walk.js";
import { INK, MOODS, makeLook, moodNow } from "./look.js";
import { placeFor, placeForNow, pose as poseFor, whereNow, perch as perchOf } from "./place.js";

const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const params = new URLSearchParams(location.search);

const box = document.getElementById("world3d");
const worldEl = box.closest(".world");
const whereEl = document.getElementById("where");

// ---------- renderer ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
box.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 2, 0.2, 9000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.enableZoom = false;                       // wheel scrolls the page; ctrl/cmd + wheel zooms (below)
controls.minPolarAngle = 0.35; controls.maxPolarAngle = 1.32;
renderer.domElement.style.touchAction = "pan-y";   // a finger on the world still scrolls the page on a phone
controls.touches.ONE = null; controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
let camDist = 34;
renderer.domElement.addEventListener("wheel", e => {
  if (!e.ctrlKey && !e.metaKey) return;
  e.preventDefault();
  camDist = THREE.MathUtils.clamp(camDist * (e.deltaY > 0 ? 1.12 : 0.89), 8, 600);
}, { passive: false });

function resize() {
  const w = box.clientWidth, h = box.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(box);

const look = makeLook(THREE);
const { mats } = look;
scene.add(look.hemi, look.sun);

// ---------- moods ----------
let mood = null;
const currentMood = () => (MOODS[params.get("mood")] ? params.get("mood") : moodNow());
function setMood(m) {
  if (m === mood) return;
  mood = m;
  look.applyMood(scene, m, walking ? [60, 420] : [300, 1500]);
  if (lamps) lamps.visible = m === "titlecard";
  edgeMat.color.set(m === "titlecard" ? "#5c5852" : INK);
  if (zzz) zzz.material.color.set(m === "titlecard" ? "#f2efe8" : INK);
  worldEl.dataset.mood = m;
}

// ---------- outline (on/off, remembered per visitor) ----------
const edgeMat = new THREE.LineBasicMaterial({ color: INK, transparent: true, opacity: 0.5, fog: true });
let edges = null, outlineOn = false;
try { outlineOn = localStorage.getItem("grimsby-outline") === "1"; } catch (e) {}
function setOutline(on) {
  outlineOn = on;
  try { localStorage.setItem("grimsby-outline", on ? "1" : "0"); } catch (e) {}
  const btn = document.getElementById("outline-btn");
  if (btn) btn.setAttribute("aria-pressed", on);
  if (on && !edges && meshes.walls) {
    edges = new THREE.Group();
    for (const k of ["walls", "roofs", "stone", "awning"]) {
      if (meshes[k]) edges.add(new THREE.LineSegments(new THREE.EdgesGeometry(meshes[k].geometry, 25), edgeMat));
    }
    scene.add(edges);
  }
  if (edges) edges.visible = on;
}

// ---------- the crow, the red ring, zzz ----------
const CROW = 0.6;                                  // look.js makes him 1.7: on the island that is taller than a house
const crow = look.makeCrow();
crow.group.scale.setScalar(CROW);
scene.add(crow.group);
const ring = look.ring();
ring.scale.setScalar(0.45);
scene.add(ring);

function zzzSprite() {
  const c = document.createElement("canvas"); c.width = 256; c.height = 128;
  const x = c.getContext("2d");
  x.font = "800 96px 'Shippori Mincho B1', Georgia, serif"; x.fillStyle = "#fff"; x.textBaseline = "middle";
  x.fillText("zzz", 16, 66);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), color: INK, transparent: true, fog: false }));
  s.scale.set(2.8, 1.4, 1); return s;
}
let zzz = null;

// ---------- night lamps along the roads ----------
let lamps = null;
function makeLamps(points) {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d"), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, "rgba(255,226,160,1)"); gr.addColorStop(0.25, "rgba(255,200,110,.55)"); gr.addColorStop(1, "rgba(255,190,90,0)");
  x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
  const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.BufferAttribute(points, 3));
  const p = new THREE.Points(geo, new THREE.PointsMaterial({ size: 5, map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: true }));
  p.visible = false; return p;
}

// ---------- places ----------
let meshes = {}, pois = [], solid = [], spinners = [], island = null, walker = null, walking = false;
const ray = new THREE.Raycaster();
function heightAt(x, z) {          // top of whatever is there: a roof, or the ground
  ray.set(new THREE.Vector3(x, 400, z), new THREE.Vector3(0, -1, 0));
  const hit = ray.intersectObjects(solid, false)[0];
  return hit ? hit.point.y : 0;
}
const perch = p => new THREE.Vector3(...perchOf(p, heightAt));

// ---------- movement ----------
const state = { pos: new THREE.Vector3(), from: null, to: null, t0: 0, dur: 0, asleep: false, action: null, flying: false, key: "" };
const camOffset = new THREE.Vector3(-0.62, 0.48, 0.62).normalize();
function faceTowards(dx, dz) { if (Math.abs(dx) + Math.abs(dz) > 0.01) crow.group.rotation.y = Math.atan2(-dz, dx); }
function goTo(target, instant) {
  if (instant || reduceMotion || state.pos.distanceTo(target) < 1) {
    state.pos.copy(target); state.flying = false; return;
  }
  state.from = state.pos.clone(); state.to = target.clone();
  const d = state.from.distanceTo(state.to);
  state.dur = THREE.MathUtils.clamp(d / 40, 2.5, 8) * 1000;
  state.t0 = performance.now(); state.flying = true;
  faceTowards(state.to.x - state.from.x, state.to.z - state.from.z);
}
function stepFlight(now) {
  if (!state.flying) return;
  const k = Math.min(1, (now - state.t0) / state.dur);
  const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
  const d = state.from.distanceTo(state.to);
  state.pos.lerpVectors(state.from, state.to, e);
  state.pos.y += Math.sin(Math.PI * k) * Math.min(45, 8 + d * 0.18);
  if (k >= 1) { state.flying = false; state.pos.copy(state.to); }
}

function pose(now) {
  const t = now / 1000;
  const c = crow;
  c.group.position.copy(state.pos);
  c.eyes.forEach(e => e.visible = !state.asleep);
  c.shut.forEach(e => e.visible = state.asleep);
  c.legs.forEach(l => l.visible = !state.flying);
  let flap = 0.1, headY = 0, headZ = 0, bob = 0, bodyTilt = 0;
  if (state.flying) {
    flap = Math.sin(t * 14) * 0.9; bodyTilt = -0.12;
  } else if (state.asleep) {
    headY = -0.35; headZ = -0.5; bob = Math.sin(t * 1.4) * 0.04;
  } else if (state.action === "diary") {          // writing: head down, a peck now and then
    headZ = -0.55 + Math.max(0, Math.sin(t * 2.2)) * 0.35;
  } else if (state.action === "search") {          // looking around
    c.head.rotation.y = Math.sin(t * 0.8) * 0.7; headZ = 0.1 * Math.sin(t * 1.7);
  } else if (state.action === "draw") {            // little hops
    bob = Math.max(0, Math.sin(t * 3.1)) * 0.35; headZ = -0.2;
  }
  if (!state.flying && state.action !== "search") c.head.rotation.y = 0;
  c.wings[0].rotation.x = -flap; c.wings[1].rotation.x = flap;
  c.head.rotation.z = headZ; c.head.position.y = 2.05 + headY;
  c.body.rotation.z = bodyTilt;
  c.group.position.y += bob * CROW;
  ring.visible = !state.flying;
  ring.position.set(state.pos.x, (state.to || state.pos).y + 0.25, state.pos.z);
  if (zzz) { zzz.visible = state.asleep; zzz.position.set(state.pos.x + 0.8, state.pos.y + 2.8 + Math.sin(t) * 0.25, state.pos.z); }
}

// ---------- data from site.js ----------
let ready = false, pending = null;
function onData(d) {
  if (!ready) { pending = d; return; }
  const now = d.now || {};
  const place = placeForNow(now, d.asleep, pois);
  const key = (place.poi ? place.poi.id : "") + "|" + d.asleep + "|" + now.action + "|" + !!now.flying;
  if (key === state.key) return;
  const first = !state.key;
  state.key = key; state.asleep = !!d.asleep; state.action = d.asleep ? null : poseFor(now.action);
  if (!place.poi) return;
  const target = perch(place.poi);
  if (whereEl) whereEl.textContent = whereNow(now, place, d.asleep);
  if (first) {
    const home = perch(placeFor(null, true, pois).poi);
    state.pos.copy(home);                      // every visit starts at home; he flies out if he's busy elsewhere
    controls.target.copy(home);
    camera.position.copy(home).addScaledVector(camOffset, camDist);
    if (!place.home) setTimeout(() => goTo(target), 900); else goTo(target, true);
  } else goTo(target);
}
document.addEventListener("grimsby:data", e => onData(e.detail));

// ---------- what visitors left (WERELD.md step 3): notes as writing in the sand, his reply beside it, items ----------
// Visitor text is only ever drawn as pixels on a canvas, never as HTML.
const BEACH_DROP = { x: -71, z: 193 };             // by the water in front of the station, for gifts left from afar
const gifts = new THREE.Group();
scene.add(gifts);
let giftData = [];
function wrap(ctx, text, width) {
  const lines = [];
  for (const para of String(text).split(/\n+/)) {
    let line = "";
    for (const w of para.split(/\s+/)) {
      const t = line ? line + " " + w : w;
      if (ctx.measureText(t).width > width && line) { lines.push(line); line = w; } else line = t;
    }
    if (line) lines.push(line);
  }
  return lines;
}
function sandText(text, sign, color) {             // text pressed into the sand, read from the south
  const c = document.createElement("canvas"); c.width = 768; c.height = 384;
  const x = c.getContext("2d");
  x.font = "700 34px 'Shippori Mincho B1', Georgia, serif";
  let lines = wrap(x, text, 720);
  if (lines.length > 7) { lines = lines.slice(0, 7); lines[6] += " …"; }
  x.fillStyle = color; x.textBaseline = "top";
  lines.forEach((l, i) => x.fillText(l, 24, 16 + i * 44));
  if (sign) { x.font = "400 28px 'Shippori Mincho B1', Georgia, serif"; x.fillText("— " + sign, 24, 16 + lines.length * 44 + 6); }
  const tex = new THREE.CanvasTexture(c); tex.anisotropy = 4;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.6),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  m.rotation.x = -Math.PI / 2; m.renderOrder = 3;
  return m;
}
function thingMesh(item) {                         // a small low-poly stand-in for what was left
  const it = String(item || "").toLowerCase();
  let geo, mat;
  if (/walnut|nut/.test(it)) { geo = new THREE.IcosahedronGeometry(0.16, 0); mat = mats.trunk; }
  else if (/button|coin|cap|marble/.test(it)) { geo = new THREE.CylinderGeometry(0.14, 0.14, 0.05, 10); mat = mats.awning; }
  else { geo = new THREE.BoxGeometry(0.3, 0.14, 0.22); mat = mats.sail; }
  return new THREE.Mesh(geo, mat || mats.walls);
}
function drawGifts() {
  if (!island) return;
  for (const o of [...gifts.children]) { gifts.remove(o); o.traverse(n => { if (n.geometry) n.geometry.dispose(); if (n.material && n.material.map) { n.material.map.dispose(); n.material.dispose(); } }); }
  let onRoof = 0;
  const home = pois.find(p => p.place === "home");
  for (const g of giftData) {
    const y = island.groundAt(g.x, g.z) + 0.04;
    if (g.note) {
      const t = sandText(g.note, g.visitor_name, "#3a3226"); t.position.set(g.x, y, g.z); gifts.add(t);
      if (g.reply) { const r = sandText(g.reply, "Grimsby", "#1b2a8c"); r.position.set(g.x + 3.4, y, g.z + 0.2); gifts.add(r); }
    }
    if (g.item) {
      const m = thingMesh(g.item);
      if (g.taken && home && onRoof < 12) {        // on his roof, in a row along the ridge
        m.position.set(home.x + 0.9, perch(home).y + 0.12, home.z - 4 + onRoof * 0.7); onRoof++; gifts.add(m);
      } else if (!g.taken) { m.position.set(g.x - 1.9, y + 0.1, g.z + 0.3); gifts.add(m); }
    }
  }
}
document.addEventListener("grimsby:gifts", e => { giftData = e.detail || []; drawGifts(); });
function dropPoint() {                             // where a gift lands: where you stand, else by the water
  if (walking && walker && island.walkable(walker.pos.x, walker.pos.z)) {
    return { x: walker.pos.x + Math.cos(walker.yaw) * 1.5, z: walker.pos.z + Math.sin(walker.yaw) * 1.5 };
  }
  return { ...BEACH_DROP };
}

// ---------- load: the island is built here, nothing to download but three.js ----------
Promise.resolve().then(() => {
  island = buildIsland(THREE);
  const built = islandMeshes(THREE, island, mats);
  meshes = built.meshes; spinners = built.spinners;
  pois = island.pois;
  solid = ["roofs", "walls"].map(k => meshes[k]).filter(Boolean);
  scene.add(built.group);
  lamps = makeLamps(island.lamps); scene.add(lamps);
  zzz = zzzSprite(); scene.add(zzz);
  walker = makeWalker(THREE, camera, renderer.domElement, island);
  setMood(currentMood());
  setOutline(outlineOn);
  ready = true;
  resize();
  worldEl.classList.add("has-3d");
  const d = pending || window.GRIMSBY_DATA;
  if (d) onData(d);
  setInterval(() => setMood(currentMood()), 60000);
  watchOpen();
  if (window.GRIMSBY_GIFTS) { giftData = window.GRIMSBY_GIFTS; drawGifts(); }
  renderer.setAnimationLoop(frame);
}).catch(err => {
  console.warn("Grimsby's island did not build, keeping the flat scene:", err);
  renderer.domElement.remove();
});

// ---------- walking: only in the expanded world, and not on touch screens (no joystick yet) ----------
const canWalk = !matchMedia("(pointer: coarse)").matches;
function setWalking(on) {
  on = on && canWalk && !!walker;
  if (on === walking) return;
  walking = on;
  controls.enabled = !on;
  if (on) { walker.reset(); walker.start(); }
  else {
    walker.stop();
    const aim = state.pos.clone(); aim.y += 1.5;      // back to looking at him
    controls.target.copy(aim);
    camera.position.copy(aim).addScaledVector(camOffset, camDist);
  }
  const m = mood; mood = null; setMood(m);           // the fog distance differs per mode
}
function watchOpen() {
  const check = () => setWalking(worldEl.classList.contains("open"));
  new MutationObserver(check).observe(worldEl, { attributes: true, attributeFilter: ["class"] });
  check();
}

const btn = document.getElementById("outline-btn");
if (btn) btn.addEventListener("click", () => setOutline(!outlineOn));

let lastFrame = 0;
function frame(now) {
  if (document.hidden) return;
  const dt = lastFrame ? (now - lastFrame) / 1000 : 0; lastFrame = now;
  stepFlight(now);
  pose(now);
  for (const s of spinners) s.rotation.z -= dt * 0.6;
  if (walking) { walker.update(dt); renderer.render(scene, camera); return; }
  // follow him: move the orbit centre with the bird, keep the user's chosen angle, distance eases to camDist
  const aim = state.pos.clone(); aim.y += 1.5;
  const delta = aim.sub(controls.target);
  controls.target.add(delta); camera.position.add(delta);
  const off = camera.position.clone().sub(controls.target);
  off.setLength(THREE.MathUtils.lerp(off.length(), state.flying ? Math.max(camDist, 70) : camDist, 0.04));
  camera.position.copy(controls.target).add(off);
  controls.update();
  renderer.render(scene, camera);
}

window.__grimsbyWorld = { scene, camera, controls, state, setMood, setOutline, renderer, get meshes() { return meshes; },
  get island() { return island; }, get walking() { return walking; },
  get you() { return walking && walker ? walker.pos : controls.target; }, dropPoint };
