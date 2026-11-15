// Writes what other code needs from the island (island.js), so there is one source for where things are:
//   node world/build_spots.mjs            -> world/poi.json + world/spots/<obj>.json (the dashboard panel's cut-outs,
//                                            same format as before: layers of triangles in 0.1 m ints around a place)
//   node world/build_spots.mjs --places   -> also world/places.json: x/z and obj from island.js SPOTS; ids, actions,
//                                            feel, feel_for and food stay exactly as they are
// Needs three from world/node_modules (npm install in world/).
import { readFileSync, writeFileSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const THREE = await import(pathToFileURL(join(HERE, "node_modules/three/build/three.module.js")).href);
const { buildIsland, SPOTS, SEA } = await import(pathToFileURL(join(HERE, "..", "island.js")).href);

const RADIUS = 45, UNIT = 0.1;                 // the panel looks from 34 m away, fog from 70 m
const island = buildIsland(THREE);

if (process.argv.includes("--places")) {
  const file = join(HERE, "places.json");
  const data = JSON.parse(readFileSync(file, "utf8"));
  data.note = "Grimsby's world as his brain knows it: places, where they are (metres on the island, x = east, z = south; " +
    "taken from SPOTS in island.js by world/build_spots.mjs --places) and what can happen there. The brain never sees the 3D; " +
    "`obj` and `category` are only for the site. `feel` is how a place affects his mood (hidden from him; his beliefs have " +
    "to find it out). `food` is what he can find at an eating place (words only).";
  for (const p of data.places) {
    const s = SPOTS[p.id];
    if (!s) throw new Error(`no SPOT for place ${p.id} in island.js`);
    p.x = s.x; p.z = s.z; p.obj = s.obj; p.category = s.category;
    delete p.poi;
    if (p.id === "home") p.words = "on the roof of station Rodenrijs";
  }
  // keep a tidy key order: id, name, words, x, z, actions, feel, feel_for, obj, category, food
  const order = ["id", "name", "words", "x", "z", "actions", "feel", "feel_for", "obj", "category", "food"];
  data.places = data.places.map(p => Object.fromEntries([...order.filter(k => k in p).map(k => [k, p[k]]),
    ...Object.entries(p).filter(([k]) => !order.includes(k))]));
  writeFileSync(file, JSON.stringify(data, null, 1) + "\n");
  console.log(`places.json: ${data.places.length} places moved to the island`);
}

// poi.json: the places as the site and the panel look them up (place.js placeForNow)
const pois = island.pois.map(p => ({ id: p.id, category: p.category, x: p.x, z: p.z, name: p.name, place: p.place }));
writeFileSync(join(HERE, "poi.json"), JSON.stringify({ note: "The island's places (island.js), written by world/build_spots.mjs. " +
  "id = the 3D object; place = the id in places.json.", pois }) + "\n");

// spots: every triangle whose middle lies within RADIUS of the place, relative to it, plus a bit of sea
const dir = join(HERE, "spots");
mkdirSync(dir, { recursive: true });
for (const f of readdirSync(dir)) rmSync(join(dir, f));
const sails = new Float32Array(island.sails.flatMap(s => {
  const m = new THREE.Matrix4().compose(new THREE.Vector3(s.x, s.y, s.z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, s.ry, 0)), new THREE.Vector3(1, 1, 1));
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(s.positions, 3)); g.applyMatrix4(m);
  return Array.from(g.attributes.position.array);
}));
const layers = { ...island.layers, sail: sails };
delete layers.water;                                  // the sea plane is far too big: a local square instead, below
let total = 0;
for (const p of pois) {
  const out = {};
  for (const [name, a] of Object.entries(layers)) {
    const ints = [];
    for (let i = 0; i < a.length; i += 9) {
      const cx = (a[i] + a[i + 3] + a[i + 6]) / 3 - p.x, cz = (a[i + 2] + a[i + 5] + a[i + 8]) / 3 - p.z;
      if (cx * cx + cz * cz > RADIUS * RADIUS) continue;
      for (let k = 0; k < 9; k += 3) ints.push(Math.round((a[i + k] - p.x) / UNIT), Math.round(a[i + k + 1] / UNIT), Math.round((a[i + k + 2] - p.z) / UNIT));
    }
    if (ints.length) out[name] = ints;
  }
  // the fountains' water is part of island.layers.water too: keep the small pieces near the place
  const w = [], r = RADIUS * 2, y = Math.round(SEA / UNIT), s = Math.round(r / UNIT);
  w.push(-s, y, -s, -s, y, s, s, y, s, -s, y, -s, s, y, s, s, y, -s);
  const wa = island.layers.water;
  for (let i = 0; i < wa.length; i += 9) {
    const cx = (wa[i] + wa[i + 3] + wa[i + 6]) / 3 - p.x, cz = (wa[i + 2] + wa[i + 5] + wa[i + 8]) / 3 - p.z;
    if (Math.abs(cx) > 1000 || cx * cx + cz * cz > RADIUS * RADIUS) continue;
    for (let k = 0; k < 9; k += 3) w.push(Math.round((wa[i + k] - p.x) / UNIT), Math.round(wa[i + k + 1] / UNIT), Math.round((wa[i + k + 2] - p.z) / UNIT));
  }
  out.water = w;
  const json = JSON.stringify({ id: p.id, category: p.category, radius: RADIUS, unit: UNIT, layers: out });
  writeFileSync(join(dir, `${p.id}.json`), json);
  total += json.length;
  console.log(`${p.id.padEnd(20)} ${(json.length / 1000).toFixed(0)} kB`);
}
console.log(`poi.json: ${pois.length} places; spots: ${(total / 1e6).toFixed(2)} MB in all`);
