// Grimsby's island (EILAND.md): a made-up island that is secretly Berkel. Built in code, the same every time.
// Shared by the site (world.js), world/viewer.html and world/build_spots.mjs (cut-outs for the dashboard panel).
// Takes THREE as an argument (like look.js), so it runs in the browser and in Node.
//
// Frame: metres, (0, 0) the middle of the island, x = east, z = south, y = up. Sea level is y = -0.8, the village
// is flat at y = 0 (so a raycast that misses every roof still lands on the village floor).
// Sizes follow Noah's sketch (world/eiland-schets.png, 1 px = 1 m): island ~756 x 410 m; the village is a bit
// bigger than drawn (~250 x 96 m) so every place fits, on the south coast around (0, +160).

export const SEA = -0.8;
const ISLAND = { rx: 378, rz: 205 };                 // outer shore (before noise)
const FOREST = { cx: 0, cz: 10, rx: 350, rz: 185 };  // green in the sketch
const VILLAGE = { cx: 0, cz: 160, rx: 125, rz: 48 }; // grey in the sketch (a bit bigger, so the places fit)

// The forest is cut into sections that can be opened one by one later (EILAND.md "Later"). Closed = a wall of trees.
export const FOREST_SECTIONS = ["w", "nw", "n", "ne", "e", "se", "s", "sw"];

// Every place from world/places.json: the 3D object it belongs to, its category (for place.js), and the point
// where he lands. world/places.json takes x/z from here (world/build_spots.mjs --places).
export const SPOTS = {
  "home":             { obj: "station-rodenrijs", category: "station",     name: "Rodenrijs",            x: -76,  z: 169 },
  "station-fountain": { obj: "fontein-station",   category: "fountain",    name: "fountain by the station", x: -56.6, z: 170 },
  "station-bench":    { obj: "bank-station",      category: "bench",       name: "bench by the station", x: -64,  z: 182.2 },
  "jumbo":            { obj: "jumbo",             category: "supermarket", name: "Jumbo",                x: -98,  z: 136 },
  "de-turk":          { obj: "de-turk",           category: "restaurant",  name: "De Turk",              x: -64,  z: 135 },
  "ondermolen":       { obj: "ondermolen-steen",  category: "artwork",     name: "Ondermolen",           x: -36.4, z: 168 },
  "albert-heijn":     { obj: "albert-heijn",      category: "supermarket", name: "Albert Heijn",         x: -9,   z: 135 },
  "library":          { obj: "bibliotheek",       category: "library",     name: "library",              x: -21,  z: 173 },
  "vis":              { obj: "vis",               category: "artwork",     name: "Vis",                  x: 4.2,  z: 166 },
  "centre-fountain":  { obj: "fontein-centrum",   category: "fountain",    name: "fountain in the centre", x: 19.4, z: 172 },
  "dorpskerk":        { obj: "dorpskerk",         category: "church",      name: "Dorpskerk",            x: 38,   z: 130 },
  "de-bron":          { obj: "de-bron",           category: "church",      name: "de Bron",              x: 71,   z: 134 },
  "plantsoen-bench":  { obj: "bank-plantsoen",    category: "bench",       name: "Gouden Griffelplantsoen", x: 77, z: 173.2 },
  "mcdonalds":        { obj: "mcdonalds",         category: "fast_food",   name: "McDonald's",           x: 103,  z: 139 },
  "hichte-mill":      { obj: "molen-de-hichte",   category: "windmill",    name: "De Hichte",            x: -128, z: 182 },
  "de-valk":          { obj: "molen-de-valk",     category: "windmill",    name: "De Valk",              x: 128,  z: 182 },
};
export const SPAWN = { x: -76.6, z: 175, yaw: 0 };   // on the platform of station Rodenrijs, looking east (yaw 0 = +x)

// ---------- shape of the land ----------
function rand(seed) {                                // mulberry32
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const angDiff = (a, b) => { let d = a - b; while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; return d; };

function makeLand(seed) {
  const r = rand(seed);
  const ph = Array.from({ length: 12 }, () => r() * Math.PI * 2);
  const NE = Math.atan2(-0.62, 0.78);                // north-east in the parametric angle (z < 0 is north)
  // shore as a factor on the ellipse, per parametric angle t
  const shoreK = t => {
    const calm = 1 - 0.85 * Math.exp(-(angDiff(t, Math.PI / 2) ** 2) / 0.35);   // the village coast stays smooth
    const base = 0.016 * Math.sin(3 * t + ph[0]) + 0.011 * Math.sin(7 * t + ph[1]) + 0.006 * Math.sin(13 * t + ph[2]);
    const ne = Math.exp(-(angDiff(t, NE) ** 2) / (2 * 0.33 ** 2));
    const rag = ne * (0.03 + 0.03 * Math.sin(19 * t + ph[3]) + 0.02 * Math.sin(31 * t + ph[4]));
    return 1 + base * calm + rag;
  };
  // metres from the shore, > 0 inland
  const shoreDist = (x, z) => {
    const ex = x / ISLAND.rx, ez = z / ISLAND.rz, e = Math.hypot(ex, ez), t = Math.atan2(ez, ex);
    return (shoreK(t) - e) * Math.hypot(ISLAND.rx * Math.cos(t), ISLAND.rz * Math.sin(t));
  };
  const fNorm = (x, z) => Math.hypot((x - FOREST.cx) / FOREST.rx, (z - FOREST.cz) / FOREST.rz);
  const vNorm = (x, z) => Math.hypot((x - VILLAGE.cx) / VILLAGE.rx, (z - VILLAGE.cz) / VILLAGE.rz);
  const noise = (x, z) => 0.5 + 0.25 * Math.sin(x * 0.019 + ph[5]) * Math.sin(z * 0.023 + ph[6])
    + 0.15 * Math.sin(x * 0.047 + z * 0.021 + ph[7]) + 0.1 * Math.sin(z * 0.061 - x * 0.033 + ph[8]);
  const inVillage = (x, z) => vNorm(x, z) < 1;
  const MILLS = [SPOTS["hichte-mill"], SPOTS["de-valk"]];          // a clearing on the beach around each mill
  const inForest = (x, z) => fNorm(x, z) < 1 && vNorm(x, z) >= 1.04 && !MILLS.some(m => Math.hypot(x - m.x, z - m.z) < 13);
  const height = (x, z) => {
    const d = shoreDist(x, z);
    let h = SEA + Math.min(9, Math.max(-30, d)) * (-SEA / 9);           // 0 from 9 m inland, sloping into the sea
    const vm = smooth(1.12, 0.96, vNorm(x, z));
    h += (1 - vm) * 0.35 * noise(x, z) * smooth(8, 30, d);               // a little dune
    const fm = smooth(1.0, 0.8, fNorm(x, z)) * (1 - smooth(1.2, 1.0, vNorm(x, z)));
    h += fm * (1.4 + 2.6 * noise(x * 1.3, z * 1.3));                      // the forest a bit higher, never hills
    return h;
  };
  const section = (x, z) => {
    const a = Math.atan2(z - FOREST.cz, x - FOREST.cx);                 // -pi = west, -pi/2 = north
    return FOREST_SECTIONS[Math.round((a + Math.PI) / (Math.PI / 4)) % 8];
  };
  return { shoreDist, fNorm, vNorm, inVillage, inForest, height, section, noise };
}

// ---------- the build ----------
// Returns plain data: per layer (a look.js material name) a flat array of triangle positions, plus what moves,
// the lamps, the places, and functions for walking (groundAt, walkable).
export function buildIsland(THREE, opt = {}) {
  const open = new Set(opt.open || []);              // forest sections that are open
  const land = makeLand(opt.seed ?? 20261115);
  const rnd = rand((opt.seed ?? 20261115) + 1);
  const L = {};
  const blockers = [];                                // {x, z, hw, hd, ry} boxes and {x, z, r} circles you can't walk into
  const floors = [];                                  // {x, z, hw, hd, ry, top}: things you can stand on (the platform)
  const sails = [];
  const lamps = [];
  const objs = {};

  const V = new THREE.Vector3(), Q = new THREE.Quaternion(), E = new THREE.Euler(), S = new THREE.Vector3();
  const M = (x = 0, y = 0, z = 0, ry = 0, rx = 0, rz = 0) => new THREE.Matrix4().compose(V.set(x, y, z), Q.setFromEuler(E.set(rx, ry, rz)), S.set(1, 1, 1));
  function put(layer, geo, m) {
    const g = geo.index ? geo.toNonIndexed() : geo;
    if (m) g.applyMatrix4(m);
    const a = g.attributes.position.array, out = (L[layer] ||= []);
    for (let i = 0; i < a.length; i++) out.push(a[i]);
    geo.dispose(); if (g !== geo) g.dispose();
  }
  const box = (layer, B, x, y, z, w, h, d, ry = 0, rx = 0, rz = 0) => put(layer, new THREE.BoxGeometry(w, h, d), B.clone().multiply(M(x, y, z, ry, rx, rz)));
  const cyl = (layer, B, x, y, z, rt, rb, h, seg = 8, rx = 0, rz = 0) => put(layer, new THREE.CylinderGeometry(rt, rb, h, seg), B.clone().multiply(M(x, y, z, 0, rx, rz)));
  function gable(layer, B, x, y, z, w, d, h, ry = 0) {   // a roof: ridge along local x, w wide, d deep, h high
    const a = [-w / 2, 0, d / 2, w / 2, 0, d / 2, w / 2, h, 0, -w / 2, 0, d / 2, w / 2, h, 0, -w / 2, h, 0,
      w / 2, 0, -d / 2, -w / 2, 0, -d / 2, -w / 2, h, 0, w / 2, 0, -d / 2, -w / 2, h, 0, w / 2, h, 0,
      -w / 2, 0, -d / 2, -w / 2, 0, d / 2, -w / 2, h, 0, w / 2, 0, d / 2, w / 2, 0, -d / 2, w / 2, h, 0];
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(a, 3));
    put(layer, g, B.clone().multiply(M(x, y, z, ry)));
  }
  const at = (x, z, ry = 0) => M(x, 0, z, ry);
  const block = (x, z, w, d, ry = 0) => blockers.push({ x, z, hw: w / 2, hd: d / 2, ry });
  const round = (x, z, r) => blockers.push({ x, z, r });
  const obj = (id, x, z, extra = {}) => { objs[id] = { id, x, z, ...extra }; };

  // ---- the building kit (front of everything = local +z) ----
  function house(B, w, d, floors_, style) {
    const h = floors_ * 2.9 + 0.5;
    box("walls", B, 0, h / 2, 0, w, h, d);
    if (style === "front") gable("roofs", B, 0, h, 0, d + 0.8, w + 0.5, w * 0.62, Math.PI / 2);   // Dutch: gable to the street
    else gable("roofs", B, 0, h, 0, w + 0.4, d + 0.9, d * 0.42);
    box("trunk", B, w * 0.22, 1.05, d / 2 + 0.03, 1.0, 2.1, 0.08);                               // door
  }
  function shop(B, w, d, h, awn = true) {
    box("walls", B, 0, h / 2, 0, w, h, d);
    box("roofs", B, 0, h + 0.2, 0, w + 0.6, 0.4, d + 0.6);
    if (awn) box("awning", B, 0, 3.0, d / 2 + 0.95, w - 1.2, 0.12, 2.0, 0, 0.32);
    box("trunk", B, 0, 1.1, d / 2 + 0.03, 2.2, 2.2, 0.08);
  }
  function bench(B) {
    box("trunk", B, 0, 0.45, 0, 2.0, 0.1, 0.6);
    box("trunk", B, 0, 0.8, -0.27, 2.0, 0.55, 0.08);
    box("rail", B, -0.8, 0.22, 0, 0.1, 0.45, 0.5); box("rail", B, 0.8, 0.22, 0, 0.1, 0.45, 0.5);
  }
  function fountain(B) {
    cyl("stone", B, 0, 0.3, 0, 3, 3.1, 0.6, 14);
    cyl("water", B, 0, 0.52, 0, 2.65, 2.65, 0.06, 14);
    cyl("stone", B, 0, 1.2, 0, 0.35, 0.45, 1.9, 8);
    cyl("stone", B, 0, 2.15, 0, 1.1, 0.5, 0.35, 10);
    cyl("water", B, 0, 2.33, 0, 0.9, 0.9, 0.04, 10);
  }
  function lamp(x, z) {
    const B = at(x, z);
    cyl("rail", B, 0, 2.1, 0, 0.07, 0.1, 4.2, 5);
    box("rail", B, 0, 4.3, 0, 0.5, 0.3, 0.5);
    lamps.push(x, 4.3, z);
  }
  function tree(x, z, y, s, kind, trunk = true) {
    const B = M(x, y, z, rnd() * 6);
    if (trunk) put("trunk", new THREE.CylinderGeometry(0.18 * s, 0.26 * s, 2.0 * s, 4, 1, true), B.clone().multiply(M(0, 1.0 * s, 0)));
    const layer = rnd() < 0.5 ? "trees" : "trees2";
    if (kind === "round") put(layer, new THREE.IcosahedronGeometry(1.9 * s, 0), B.clone().multiply(M(0, 3.4 * s, 0)));
    else {
      put(layer, new THREE.ConeGeometry(2.0 * s, 3.6 * s, 7, 1, true), B.clone().multiply(M(0, 3.4 * s, 0)));
      put(layer, new THREE.ConeGeometry(1.5 * s, 3.0 * s, 7, 1, true), B.clone().multiply(M(0, 5.2 * s, 0)));
    }
  }
  function windmill(id, x, z, face) {
    const B = at(x, z, face);
    cyl("roofs", B, 0, 5.5, 0, 2.5, 3.9, 11, 8);                  // the body, dark like a real mill
    cyl("stone", B, 0, 0.6, 0, 4.4, 4.6, 1.2, 8);                 // brick foot
    cyl("trunk", B, 0, 4.6, 0, 5.2, 5.2, 0.25, 8);                // the stage around it
    put("roofs", new THREE.ConeGeometry(2.9, 3.2, 8), B.clone().multiply(M(0, 12.5, 0)));
    // sails turn: kept apart, pivot at the front of the cap (local +z)
    const p = new THREE.Vector3(0, 11.6, 3.1).applyMatrix4(B);
    const g = [];
    for (let i = 0; i < 4; i++) {
      const R = M(0, 0, 0, 0, 0, i * Math.PI / 2);
      for (const [geo, m] of [[new THREE.BoxGeometry(0.35, 11, 0.25), M(0, 5.6, 0)], [new THREE.BoxGeometry(1.9, 8.5, 0.08), M(1.15, 6.6, 0.1)]]) {
        const gg = geo.toNonIndexed(); gg.applyMatrix4(R.clone().multiply(m));
        g.push(...gg.attributes.position.array); geo.dispose(); gg.dispose();
      }
    }
    sails.push({ id, x: p.x, y: p.y, z: p.z, ry: face, positions: g });
    round(x, z, 4.8);
    obj(id, x, z, { kind: "windmill" });
  }

  // ---- terrain: one grid, each triangle goes to the layer of the land under its middle ----
  const X0 = -420, X1 = 420, Z0 = -252, Z1 = 264, CELL = 4;
  const nx = (X1 - X0) / CELL, nz = (Z1 - Z0) / CELL;
  const H = new Float32Array((nx + 1) * (nz + 1));
  for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) H[j * (nx + 1) + i] = land.height(X0 + i * CELL, Z0 + j * CELL);
  const groundLayer = (x, z) => {
    if (land.inVillage(x, z) && land.shoreDist(x, z) > 11) return "ground";
    if (land.inForest(x, z)) return "forest";
    return "sand";
  };
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const x = X0 + i * CELL, z = Z0 + j * CELL;
    const h00 = H[j * (nx + 1) + i], h10 = H[j * (nx + 1) + i + 1], h01 = H[(j + 1) * (nx + 1) + i], h11 = H[(j + 1) * (nx + 1) + i + 1];
    for (const t of [[x, h00, z, x, h01, z + CELL, x + CELL, h10, z], [x + CELL, h10, z, x, h01, z + CELL, x + CELL, h11, z + CELL]]) {
      if (Math.max(t[1], t[4], t[7]) < SEA - 0.4) continue;       // deep under water: nobody sees it
      const out = (L[groundLayer((t[0] + t[3] + t[6]) / 3, (t[2] + t[5] + t[8]) / 3)] ||= []);
      for (const v of t) out.push(v);
    }
  }
  put("water", new THREE.PlaneGeometry(6000, 6000).rotateX(-Math.PI / 2), M(0, SEA, 0));

  // ---- streets ----
  const strip = (layer, x0, x1, z0, z1) => box(layer, at((x0 + x1) / 2, (z0 + z1) / 2), 0, 0.02, 0, x1 - x0, 0.04, z1 - z0);
  strip("roads", -120, 120, 147, 153);              // Dorpsstraat, west to east
  strip("paths", -104, 104, 184, 189);              // the promenade along the beach
  strip("paths", -72, -44, 158, 186);               // station square
  strip("paths", -32, 34, 157, 186);                // the square in the centre
  for (const x of [-38, 46]) strip("paths", x - 1.5, x + 1.5, 153, 184);
  for (let x = -112; x <= 112; x += 16) { lamp(x, 145.5); if (Math.abs(x) < 100) lamp(x + 8, 190.5); }

  // ---- station Rodenrijs: a track from the forest straight into the sea, a platform, a roof he sleeps on ----
  {
    const TX = -82;
    for (let z = 40; z <= 262; z += 1.2) {
      const y = Math.max(land.height(TX, z), SEA - 3) + 0.12;
      box("trunk", at(TX, z), 0, y, 0, 2.6, 0.14, 0.32);
    }
    for (const dx of [-0.72, 0.72]) for (let z = 40; z < 262; z += 6) {
      const y0 = Math.max(land.height(TX, z), SEA - 3), y1 = Math.max(land.height(TX, z + 6), SEA - 3);
      box("rail", at(TX + dx, z + 3), 0, (y0 + y1) / 2 + 0.25, 0, 0.12, 0.14, 6.05, 0, Math.atan2(y0 - y1, 6));
    }
    const B = at(-76, 169);
    box("stone", B, 0, 0.45, 0, 4.4, 0.9, 30);                    // the platform, z 154-184
    floors.push({ x: -76, z: 169, hw: 2.2, hd: 15, ry: 0, top: 0.9 });
    for (const dz of [-9, -3, 3, 9]) { cyl("rail", B, 0.9, 2.35, dz, 0.09, 0.09, 2.9, 6); round(-75.1, 169 + dz, 0.15); }
    box("roofs", B, 0.3, 3.9, 0, 5.4, 0.3, 22);                   // the roof: his home
    box("walls", B, 1.1, 0.9 + 1.5, -12.5, 2.2, 3.0, 4);          // ticket hut at the north end
    box("roofs", B, 1.1, 0.9 + 3.15, -12.5, 2.8, 0.3, 4.6);
    for (const dz of [-6, 6]) bench(B.clone().multiply(M(1.4, 0.9, dz, -Math.PI / 2)));
    block(-74.9, 156.5, 2.2, 4);                                  // ticket hut
    obj("station-rodenrijs", -76, 169, { kind: "station" });
  }

  // ---- west: Jumbo, De Turk, fountain and bench by the station ----
  shop(at(-98, 137), 18, 12, 5.2); block(-98, 137, 18, 12); obj("jumbo", -98, 137);
  {
    const B = at(-64, 136);
    shop(B, 11, 10, 6.4);
    gable("roofs", B, 0, 6.4, 0, 11.6, 10.6, 2.4);
    for (const dx of [-3.2, 0, 3.2]) {                           // terrace
      cyl("trunk", B, dx, 0.75, 7.6, 0.55, 0.55, 0.08, 8); cyl("rail", B, dx, 0.37, 7.6, 0.05, 0.05, 0.74, 4);
      box("trunk", B, dx - 0.8, 0.25, 7.6, 0.45, 0.5, 0.45); box("trunk", B, dx + 0.8, 0.25, 7.6, 0.45, 0.5, 0.45);
    }
    block(-64, 136, 11, 10); obj("de-turk", -64, 136);
  }
  fountain(at(-60, 170)); round(-60, 170, 3.2); obj("fontein-station", -60, 170);
  bench(at(-64, 181)); block(-64, 181, 2.1, 0.8); obj("bank-station", -64, 181);
  {                                                              // the Ondermolen memorial: a stone and a millstone
    const B = at(-38, 168, 0.3);
    box("stone", B, 0, 0.7, 0, 1.4, 1.4, 0.6);
    cyl("stone", B, 1.3, 0.85, 0, 0.85, 0.85, 0.28, 14, Math.PI / 2);
    block(-37.6, 168, 3.2, 1.4); obj("ondermolen-steen", -38, 168);
  }

  // ---- the centre: Albert Heijn, library, Vis, fountain, Dorpskerk ----
  {
    const B = at(-9, 136);
    shop(B, 24, 14, 5.6);
    for (let i = 0; i < 5; i++) box("rail", B, -10 + i * 0.7, 0.5, 8.6, 0.55, 0.9, 1.0);   // trolleys
    bench(B.clone().multiply(M(5, 0, 8.6, Math.PI)));
    block(-9, 136, 24, 14); obj("albert-heijn", -9, 136);
  }
  {
    const B = at(-22, 171, Math.PI);
    box("walls", B, 0, 4.4, 0, 13, 8.8, 11);
    box("roofs", B, 0, 9.0, 0, 13.8, 0.45, 11.8);
    box("awning", B, 0, 3.2, 6.2, 9, 0.12, 1.6, 0, 0.25);
    box("trunk", B, 0, 1.2, 5.53, 2.4, 2.4, 0.08);
    block(-22, 171, 13, 11); obj("bibliotheek", -22, 171);
  }
  {
    const B = at(2, 166, 0.5);
    box("stone", B, 0, 0.6, 0, 1.6, 1.2, 1.2);
    put("roofs", new THREE.IcosahedronGeometry(1, 0), B.clone().multiply(new THREE.Matrix4().compose(V.set(0, 2.1, 0), Q.setFromEuler(E.set(0, 0, 0.35)), S.set(1.5, 0.75, 0.38))));
    put("roofs", new THREE.ConeGeometry(0.7, 1.3, 4), B.clone().multiply(M(-1.7, 1.6, 0, 0, 0, Math.PI / 2 + 0.6)));
    block(2, 166, 1.8, 1.4, 0.5); obj("vis", 2, 166);
  }
  fountain(at(16, 172)); round(16, 172, 3.2); obj("fontein-centrum", 16, 172);
  {
    const B = at(38, 133);
    box("walls", B, 0, 4.2, -2, 10, 8.4, 20);
    gable("roofs", B, 0, 8.4, -2, 10.8, 20.6, 5.2, Math.PI / 2);
    box("walls", B, 0, 8, 9.2, 5, 16, 5);
    put("roofs", new THREE.ConeGeometry(3.4, 10, 4), B.clone().multiply(M(0, 21, 9.2, Math.PI / 4)));
    box("trunk", B, 0, 1.3, 11.73, 1.6, 2.6, 0.08);
    block(38, 131, 10, 20); block(38, 142.2, 5, 5); obj("dorpskerk", 38, 133);
  }

  // ---- east: de Bron, the Gouden Griffelplantsoen, McDonald's ----
  {
    const B = at(71, 135);
    box("walls", B, 0, 3.2, 0, 18, 6.4, 14);
    box("roofs", B, 0, 6.6, 0, 18.8, 0.4, 14.8);
    gable("roofs", B, -3, 6.8, 0, 10, 14.8, 2.2, Math.PI / 2);
    box("stone", B, 8.2, 7, 6.2, 1.6, 14, 1.6);                  // a thin bell tower
    box("trunk", B, 0, 1.3, 7.03, 3.0, 2.6, 0.08);
    block(71, 135, 18, 14); block(79.2, 141.2, 1.8, 1.8); obj("de-bron", 71, 135);
  }
  {
    const B = at(77, 170);
    box("green", B, 0, 0.03, 0, 26, 0.06, 18);
    for (const [dx, dz] of [[-10, -6], [10, -6], [-10, 6], [10, 6], [-3, -7]]) { tree(77 + dx, 170 + dz, 0, 0.7, "round"); round(77 + dx, 170 + dz, 0.5); }
    bench(at(77, 172)); block(77, 172, 2.1, 0.8); obj("bank-plantsoen", 77, 172);
  }
  {
    const B = at(103, 139);
    shop(B, 12, 10, 4.6);
    cyl("rail", B, 4.2, 0.45, 6.3, 0.35, 0.3, 0.9, 8);           // the bin with chips, of course
    cyl("awning", B, 4.2, 0.93, 6.3, 0.3, 0.3, 0.06, 8);
    block(103, 139, 12, 10); round(107.2, 145.3, 0.4); obj("mcdonalds", 103, 139);
  }

  // ---- the two mills on the beach, far out so they're seen from everywhere ----
  windmill("molen-de-hichte", -128, 182, -0.5);
  windmill("molen-de-valk", 128, 182, 0.5);

  // ---- fill the village with terraced houses where nothing else stands ----
  const reserved = [[-110, -86, 128, 146], [-90, -70, 120, 200], [-76, -52, 128, 150], [-72, -44, 156, 188],
    [-46, -30, 160, 176], [-24, 6, 126, 146], [-32, 34, 155, 188], [22, 52, 118, 147], [58, 86, 124, 146],
    [62, 92, 158, 182], [94, 114, 131, 148], [-40, -36, 150, 186], [44, 48, 150, 186]];
  const free = (x0, x1, z0, z1) => !reserved.some(([a, b, c, d]) => x0 < b && x1 > a && z0 < d && z1 > c)
    && [[x0, z0], [x1, z0], [x0, z1], [x1, z1]].every(([x, z]) => land.vNorm(x, z) < 1.0 && land.shoreDist(x, z) > 9);
  for (const [zc, ry] of [[124.5, Math.PI], [137.5, 0], [162.5, Math.PI], [176.5, 0]]) {
    let x = -118;
    while (x < 118) {
      const n = 3 + Math.floor(rnd() * 5), style = rnd() < 0.5 ? "front" : "eaves", fl = rnd() < 0.7 ? 2 : 3;
      let built = 0;
      for (let k = 0; k < n; k++) {
        const w = 5.4 + rnd() * 1.4, d = 9;
        if (free(x, x + w, zc - d / 2, zc + d / 2)) {
          house(at(x + w / 2, zc, ry), w - 0.05, d, fl + (rnd() < 0.15 ? 1 : 0), style);
          block(x + w / 2, zc, w, d); built++;
        }
        x += w;
      }
      x += built ? 3.5 : 2;                          // an alley between blocks
    }
  }

  // ---- the forest: dense at the edge (you can't get in), thinner inside, a gap where the track goes in ----
  let nTrees = 0;
  for (let gz = -200; gz < 200; gz += 5) for (let gx = -360; gx < 360; gx += 5) {
    const x = gx + (rnd() - 0.5) * 4, z = gz + (rnd() - 0.5) * 4;
    if (!land.inForest(x, z)) continue;
    if (Math.abs(x + 82) < 4.5 && z > 30) continue;
    const f = land.fNorm(x, z), edge = f > 0.9 || land.vNorm(x, z) < 1.25;
    const sec = land.section(x, z);
    if (open.has(sec) && edge) continue;
    if (!edge && rnd() > 0.45) continue;
    tree(x, z, land.height(x, z) - 0.2, 0.9 + rnd() * 0.8, rnd() < 0.7 ? "pine" : "round");
    nTrees++;
  }
  // a few on the beach and in the village
  for (const [x, z] of [[-112, 160], [-30, 150], [58, 156], [112, 162], [-47, 186], [92, 186]]) { tree(x, z, 0, 0.75, "round"); round(x, z, 0.5); }

  // ---- walking ----
  const groundAt = (x, z) => {
    let y = land.height(x, z);
    for (const f of floors) if (inBox(f, x, z, 0)) y = Math.max(y, f.top);
    return y;
  };
  const walkable = (x, z, pad = 0.35) => {
    if (land.shoreDist(x, z) < 1.5) return false;               // the sea
    if (land.inForest(x, z) && !open.has(land.section(x, z))) return false;
    if (Math.abs(x + 82) < 3 && z < 125) return false;          // along the track into the forest: no
    for (const b of blockers) if (b.r ? Math.hypot(x - b.x, z - b.z) < b.r + pad : inBox(b, x, z, pad)) return false;
    return true;
  };

  const pois = Object.entries(SPOTS).map(([place, s]) => ({ id: s.obj, place, category: s.category, name: s.name, x: s.x, z: s.z }));
  const layers = Object.fromEntries(Object.entries(L).map(([k, v]) => [k, new Float32Array(v)]));
  const tris = Object.values(layers).reduce((n, a) => n + a.length / 9, 0) + sails.reduce((n, s) => n + s.positions.length / 9, 0);
  return { layers, sails, lamps: new Float32Array(lamps), pois, objs, spawn: SPAWN, groundAt, walkable, land, blockers, floors,
    stats: { tris: Math.round(tris), trees: nTrees, houses: blockers.length } };
}

function inBox(b, x, z, pad) {
  const c = Math.cos(-b.ry || 0), s = Math.sin(-b.ry || 0), dx = x - b.x, dz = z - b.z;
  const lx = dx * c + dz * s, lz = -dx * s + dz * c;
  return Math.abs(lx) < b.hw + pad && Math.abs(lz) < b.hd + pad;
}

// Meshes for a scene: one per layer with flat normals, the sails as spinning groups (mesh.userData.spin).
export function islandMeshes(THREE, island, mats) {
  const group = new THREE.Group(), meshes = {};
  for (const [name, arr] of Object.entries(island.layers)) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    geo.computeVertexNormals();
    const m = new THREE.Mesh(geo, mats[name] || mats.walls);
    m.name = name; meshes[name] = m; group.add(m);
  }
  const spinners = island.sails.map(s => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(s.positions, 3));
    geo.computeVertexNormals();
    const pivot = new THREE.Group(); pivot.position.set(s.x, s.y, s.z); pivot.rotation.y = s.ry;
    const blades = new THREE.Mesh(geo, mats.sail || mats.walls); pivot.add(blades);
    group.add(pivot);
    return blades;
  });
  return { group, meshes, spinners };
}
