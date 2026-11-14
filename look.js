// Grimsby's look, shared by the site (world.js) and the dashboard panel (nbroers05/Dashboard widgets/grimsby.js).
// Takes THREE as an argument instead of importing it, so it works with or without an import map.

export const INK = "#16130f", RED = "#d7261e";

// House style colours, a touch lighter for 3D
export const COLORS = {
  ground: "#f3eee3", ground_side: "#cbbfa6", green: "#d3dcb4", water: "#9ccbec",
  paths: "#e3dacb", roads: "#c4bcae", rail: "#8f877a", walls: "#f8f4ea", roofs: "#8c95cc", greenhouse: "#bfe1f5",
};

// Digital Future in the morning, Poster in the afternoon, Title card at night (same names as the dashboard's html[data-mood])
export const MOODS = {
  digital:   { bg: "#bfe6fa", fog: "#cfeaf8", sky: "#eaf6ff", ground: "#1b2a8c", hemi: 1.25, sun: "#ffffff", sunI: 1.45, sunPos: [-700, 600, 350], walls: "#f8f4ea", day: 1, night: 0 },
  poster:    { bg: "#efe9dc", fog: "#efe9dc", sky: "#fff1d8", ground: "#3a3f8f", hemi: 1.1, sun: "#ffe7c4", sunI: 1.65, sunPos: [500, 800, 500], walls: "#f8f4ea", day: 1, night: 0 },
  titlecard: { bg: "#0b0b0d", fog: "#0b0b0d", sky: "#27325f", ground: "#05060c", hemi: 0.5, sun: "#9fb0ff", sunI: 0.3, sunPos: [300, 800, -600], walls: "#aaa59b", day: 0, night: 1 },
};

// Soft three-step toon materials, one per world layer, with windows drawn on the walls by the shader
export function makeLook(THREE) {
  const steps = [150, 150, 205, 205, 255, 255];
  const gradientMap = new THREE.DataTexture(new Uint8Array(steps.flatMap(v => [v, v, v, 255])), steps.length, 1, THREE.RGBAFormat);
  gradientMap.minFilter = gradientMap.magFilter = THREE.LinearFilter; gradientMap.needsUpdate = true;
  const toon = (color, extra = {}) => new THREE.MeshToonMaterial({ color, gradientMap, ...extra });

  const mats = Object.fromEntries(Object.entries(COLORS).map(([k, c]) => [k, toon(c)]));
  mats.greenhouse.transparent = true; mats.greenhouse.opacity = 0.5; mats.greenhouse.depthWrite = false;
  for (const k of ["green", "water", "paths", "roads", "rail"]) { mats[k].polygonOffset = true; mats[k].polygonOffsetFactor = -1; }

  // Soft eva panes by day, some lit warm at night
  const win = { uDay: { value: 1 }, uNight: { value: 0 }, uPane: { value: new THREE.Color("#c3cbe8") }, uWarm: { value: new THREE.Color("#ffc977") } };
  mats.walls.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, win);
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;")
      .replace("#include <project_vertex>", "#include <project_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWNrm = normalize(mat3(modelMatrix) * objectNormal);");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", `#include <common>
varying vec3 vWPos; varying vec3 vWNrm;
uniform float uDay; uniform float uNight; uniform vec3 uPane; uniform vec3 uWarm;
float gWin; float gLit;`)
      .replace("#include <color_fragment>", `#include <color_fragment>
{
  float wall = 1.0 - step(0.25, abs(vWNrm.y));
  vec2 t = normalize(vec2(-vWNrm.z, vWNrm.x) + 1e-5);
  vec2 g = vec2(dot(vWPos.xz, t) / 3.4, (vWPos.y - 0.7) / 2.9);
  vec2 c = floor(g), f = fract(g);
  gWin = wall * step(0.0, g.y) * step(0.3, f.x) * step(f.x, 0.7) * step(0.28, f.y) * step(f.y, 0.78);
  float h = fract(sin(dot(c + floor(vWPos.xz / 23.0) * 1.7, vec2(12.9898, 78.233))) * 43758.5453);
  gLit = step(0.62, h);
  diffuseColor.rgb = mix(diffuseColor.rgb, uPane, gWin * uDay * 0.75);
}`)
      .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += uWarm * gWin * gLit * uNight * 1.4;");
  };

  const hemi = new THREE.HemisphereLight("#fff6e6", "#1b2a8c", 1.2);
  const sun = new THREE.DirectionalLight("#ffffff", 1.6);

  // Sets background, fog, lights, wall colour and windows for a mood. fog = [near, far].
  function applyMood(scene, name, fog) {
    const s = MOODS[name] || MOODS.poster;
    scene.background = new THREE.Color(s.bg);
    scene.fog = new THREE.Fog(s.fog, fog[0], fog[1]);
    hemi.color.set(s.sky); hemi.groundColor.set(s.ground); hemi.intensity = s.hemi;
    sun.color.set(s.sun); sun.intensity = s.sunI; sun.position.set(...s.sunPos);
    mats.walls.color.set(s.walls);
    win.uDay.value = s.day; win.uNight.value = s.night;
    return s;
  }

  // The crow: a handful of low-poly shapes in ink, beak along +x
  function makeCrow() {
    const ink = toon("#24201b"), paper = toon("#f8f4ea");
    const g = new THREE.Group();
    const add = (geo, mat, pos, rot = [0, 0, 0], scale = [1, 1, 1], parent = g) => {
      const m = new THREE.Mesh(geo, mat); m.position.set(...pos); m.rotation.set(...rot); m.scale.set(...scale); parent.add(m); return m;
    };
    const body = new THREE.Group(); g.add(body);
    add(new THREE.IcosahedronGeometry(1, 0), ink, [0, 1.25, 0], [0, 0, 0.25], [1.45, 0.9, 0.85], body);
    const head = new THREE.Group(); head.position.set(1.15, 2.05, 0); body.add(head);
    add(new THREE.IcosahedronGeometry(0.58, 0), ink, [0, 0, 0], [0, 0, 0], [1, 1, 1], head);
    add(new THREE.ConeGeometry(0.2, 0.75, 4), ink, [0.7, -0.08, 0], [0, 0, -Math.PI / 2], [1, 1, 0.8], head);
    const eyes = [0.36, -0.36].map(z => add(new THREE.IcosahedronGeometry(0.11, 0), paper, [0.3, 0.14, z], [0, 0, 0], [1, 1, 1], head));
    const shut = [0.36, -0.36].map(z => add(new THREE.BoxGeometry(0.22, 0.04, 0.04), paper, [0.3, 0.1, z], [0, 0, 0], [1, 1, 1], head));
    add(new THREE.ConeGeometry(0.5, 1.4, 3), ink, [-1.55, 1.05, 0], [0, 0, Math.PI / 2 + 0.25], [1, 1, 0.45], body);
    const wings = [1, -1].map(s => {
      const pivot = new THREE.Group(); pivot.position.set(0.25, 1.65, 0.62 * s); body.add(pivot);
      add(new THREE.BoxGeometry(1.7, 0.1, 0.9), ink, [-0.4, 0, 0.42 * s], [0, 0, 0.15], [1, 1, 1], pivot);
      return pivot;
    });
    const legs = [0.28, -0.28].map(z => add(new THREE.CylinderGeometry(0.05, 0.05, 0.75, 4), ink, [0.1, 0.38, z]));
    g.scale.setScalar(1.7);
    return { group: g, body, head, eyes, shut, wings, legs };
  }

  // Resting pose for a still picture (the panel) or the first frame
  function restPose(crow, asleep, action) {
    crow.eyes.forEach(e => e.visible = !asleep);
    crow.shut.forEach(e => e.visible = asleep);
    crow.head.rotation.set(0, 0, asleep ? -0.5 : action === "diary" ? -0.55 : action === "draw" ? -0.2 : 0.1);
    crow.head.position.y = 2.05 + (asleep ? -0.35 : 0);
    crow.wings[0].rotation.x = -0.1; crow.wings[1].rotation.x = 0.1;
  }

  // The one red thing in the scene: the ring where he is now
  const ring = () => {
    const m = new THREE.Mesh(new THREE.RingGeometry(3.4, 4.4, 28), new THREE.MeshBasicMaterial({ color: RED, side: THREE.DoubleSide, fog: false }));
    m.rotation.x = -Math.PI / 2; return m;
  };

  return { gradientMap, toon, mats, win, hemi, sun, applyMood, makeCrow, restPose, ring };
}

// Sunrise and sunset in UTC hours for Berkel en Rodenrijs (good to a few minutes)
export function sunTimes(date) {
  const lat = 51.99 * Math.PI / 180, lon = 4.47;
  const n = (date - Date.UTC(date.getUTCFullYear(), 0, 0)) / 864e5;
  const dec = -23.44 * Math.PI / 180 * Math.cos(2 * Math.PI * (n + 10) / 365);
  const b = 2 * Math.PI * (n - 81) / 364, eot = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
  const ha = Math.acos(Math.min(1, Math.max(-1, (Math.sin(-0.833 * Math.PI / 180) - Math.sin(lat) * Math.sin(dec)) / (Math.cos(lat) * Math.cos(dec))))) * 180 / Math.PI;
  const noon = 12 - lon / 15 - eot / 60;
  return [noon - ha / 15, noon + ha / 15];
}

// Mood by the clock in the Netherlands: sunrise-12:00 digital, 12:00-sunset poster, otherwise titlecard
export function moodNow(d = new Date()) {
  const utc = d.getUTCHours() + d.getUTCMinutes() / 60;
  const local = +new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Amsterdam", hour: "numeric", hourCycle: "h23" }).format(d) + d.getUTCMinutes() / 60;
  const [rise, set] = sunTimes(d);
  const noonUtc = utc + (12 - local);
  if (utc >= rise && utc < noonUtc) return "digital";
  if (utc >= noonUtc && utc < set) return "poster";
  return "titlecard";
}
