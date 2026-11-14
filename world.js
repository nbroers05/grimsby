// Grimsby's 3D world: Berkel en Rodenrijs (world/berkel.glb) with the crow at the place that fits what he did last.
// site.js loads data/now.json and sends it here with a "grimsby:data" event ({now, asleep}); this file only draws.
// If WebGL or the files fail, the flat placeholder scene in index.html simply stays.
// The look (materials, moods, crow) is in look.js and the choice of place in place.js: the dashboard panel uses them too.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { INK, MOODS, makeLook, moodNow } from "./look.js";
import { placeFor, placeForNow, pose as poseFor, whereText, perch as perchOf } from "./place.js";

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
const camera = new THREE.PerspectiveCamera(38, 2, 1, 16000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.enableZoom = false;                       // wheel scrolls the page; ctrl/cmd + wheel zooms (below)
controls.minPolarAngle = 0.35; controls.maxPolarAngle = 1.32;
renderer.domElement.style.touchAction = "pan-y";   // a finger on the world still scrolls the page on a phone
controls.touches.ONE = null; controls.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
let camDist = 70;
renderer.domElement.addEventListener("wheel", e => {
  if (!e.ctrlKey && !e.metaKey) return;
  e.preventDefault();
  camDist = THREE.MathUtils.clamp(camDist * (e.deltaY > 0 ? 1.12 : 0.89), 18, 900);
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
  look.applyMood(scene, m, [700, 4200]);
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
    for (const k of ["walls", "roofs", "greenhouse"]) {
      if (meshes[k]) edges.add(new THREE.LineSegments(new THREE.EdgesGeometry(meshes[k].geometry, 25), edgeMat));
    }
    scene.add(edges);
  }
  if (edges) edges.visible = on;
}

// ---------- the crow, the red ring, zzz ----------
const crow = look.makeCrow();
scene.add(crow.group);
const ring = look.ring();
scene.add(ring);

function zzzSprite() {
  const c = document.createElement("canvas"); c.width = 256; c.height = 128;
  const x = c.getContext("2d");
  x.font = "800 96px 'Shippori Mincho B1', Georgia, serif"; x.fillStyle = "#fff"; x.textBaseline = "middle";
  x.fillText("zzz", 16, 66);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), color: INK, transparent: true, fog: false }));
  s.scale.set(7, 3.5, 1); return s;
}
let zzz = null;

// ---------- night lamps along the roads ----------
let lamps = null;
function makeLamps(roads) {
  const pos = roads.geometry.attributes.position, n = pos.count / 3;
  const pts = [], seen = new Set();
  for (let i = 0; i < n && pts.length < 9000; i += 3) {
    const x = (pos.getX(i * 3) + pos.getX(i * 3 + 1) + pos.getX(i * 3 + 2)) / 3;
    const z = (pos.getZ(i * 3) + pos.getZ(i * 3 + 1) + pos.getZ(i * 3 + 2)) / 3;
    const k = Math.round(x / 28) + "," + Math.round(z / 28);           // about one lamp per 28 m
    if (seen.has(k)) continue; seen.add(k); pts.push(x, 4.5, z);
  }
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d"), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, "rgba(255,226,160,1)"); gr.addColorStop(0.25, "rgba(255,200,110,.55)"); gr.addColorStop(1, "rgba(255,190,90,0)");
  x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
  const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  const p = new THREE.Points(geo, new THREE.PointsMaterial({ size: 9, map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: true }));
  p.visible = false; return p;
}

// ---------- places ----------
let meshes = {}, pois = [], solid = [];
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
  state.dur = THREE.MathUtils.clamp(d / 260, 2.5, 8) * 1000;
  state.t0 = performance.now(); state.flying = true;
  faceTowards(state.to.x - state.from.x, state.to.z - state.from.z);
}
function stepFlight(now) {
  if (!state.flying) return;
  const k = Math.min(1, (now - state.t0) / state.dur);
  const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
  const d = state.from.distanceTo(state.to);
  state.pos.lerpVectors(state.from, state.to, e);
  state.pos.y += Math.sin(Math.PI * k) * Math.min(160, 25 + d * 0.12);
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
  c.group.position.y += bob * 1.7;
  ring.visible = !state.flying;
  ring.position.set(state.pos.x, (state.to || state.pos).y + 0.25, state.pos.z);
  if (zzz) { zzz.visible = state.asleep; zzz.position.set(state.pos.x + 2, state.pos.y + 7 + Math.sin(t) * 0.6, state.pos.z); }
}

// ---------- data from site.js ----------
let ready = false, pending = null;
function onData(d) {
  if (!ready) { pending = d; return; }
  const now = d.now || {};
  const place = placeForNow(now, d.asleep, pois);
  const key = (place.poi ? place.poi.id : "") + "|" + d.asleep + "|" + now.action;
  if (key === state.key) return;
  const first = !state.key;
  state.key = key; state.asleep = !!d.asleep; state.action = d.asleep ? null : poseFor(now.action);
  if (!place.poi) return;
  const target = perch(place.poi);
  if (whereEl) whereEl.textContent = whereText(place, d.asleep);
  if (first) {
    const home = perch(placeFor(null, true, pois).poi);
    state.pos.copy(home);                      // every visit starts at home; he flies out if he's busy elsewhere
    controls.target.copy(home);
    camera.position.copy(home).addScaledVector(camOffset, camDist);
    if (!place.home) setTimeout(() => goTo(target), 900); else goTo(target, true);
  } else goTo(target);
}
document.addEventListener("grimsby:data", e => onData(e.detail));

// ---------- load ----------
const draco = new DRACOLoader().setDecoderPath("https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/");
const loader = new GLTFLoader().setDRACOLoader(draco);
Promise.all([
  loader.loadAsync("world/berkel.glb"),
  fetch("world/poi.json").then(r => r.json()),
]).then(([gltf, poi]) => {
  pois = poi.pois;
  gltf.scene.traverse(o => {
    if (!o.isMesh) return;
    o.geometry = o.geometry.toNonIndexed();          // positions only in the file: give every face its own normal
    o.geometry.computeVertexNormals();
    o.material = mats[o.name] || mats.walls;
    if (o.name === "greenhouse") o.renderOrder = 2;
    meshes[o.name] = o;
  });
  solid = ["roofs", "walls", "greenhouse"].map(k => meshes[k]).filter(Boolean);
  scene.add(gltf.scene);
  if (meshes.roads) { lamps = makeLamps(meshes.roads); scene.add(lamps); }
  zzz = zzzSprite(); scene.add(zzz);
  setMood(currentMood());
  setOutline(outlineOn);
  ready = true;
  resize();
  worldEl.classList.add("has-3d");
  const d = pending || window.GRIMSBY_DATA;
  if (d) onData(d);
  setInterval(() => setMood(currentMood()), 60000);
  renderer.setAnimationLoop(frame);
}).catch(err => {
  console.warn("Grimsby's 3D world did not load, keeping the flat scene:", err);
  renderer.domElement.remove();
});

const btn = document.getElementById("outline-btn");
if (btn) btn.addEventListener("click", () => setOutline(!outlineOn));

function frame(now) {
  if (document.hidden) return;
  stepFlight(now);
  pose(now);
  // follow him: move the orbit centre with the bird, keep the user's chosen angle, distance eases to camDist
  const aim = state.pos.clone(); aim.y += 3;
  const delta = aim.sub(controls.target);
  controls.target.add(delta); camera.position.add(delta);
  const off = camera.position.clone().sub(controls.target);
  off.setLength(THREE.MathUtils.lerp(off.length(), state.flying ? Math.max(camDist, 140) : camDist, 0.04));
  camera.position.copy(controls.target).add(off);
  controls.update();
  renderer.render(scene, camera);
}

window.__grimsbyWorld = { scene, camera, controls, state, setMood, setOutline, meshes, renderer };
