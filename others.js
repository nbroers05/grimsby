// Other visitors on the island (WERELD.md step 4), through Supabase Realtime on one channel "island":
//   Presence  who is here (a name), so visitors.exe can list them
//   Broadcast where everyone is (at most MOVE_HZ a second, only when moving, plus a slow heartbeat) and whistles
// Others are small eva figures with their name above them. Names are only drawn on a canvas, never as HTML.
// Nothing is stored: when you leave, you are gone. A random id per page load, not the browser id gifts use.

const MOVE_HZ = 4, HEARTBEAT = 3000, GONE_AFTER = 15000, EVA = "#1556cf", INK = "#16130f";

function nameSprite(THREE, text) {
  const c = document.createElement("canvas"), x = c.getContext("2d"), f = "700 30px 'Zen Kaku Gothic New', system-ui, sans-serif";
  x.font = f; const w = Math.min(512, Math.ceil(x.measureText(text).width) + 20); c.width = w; c.height = 44;
  x.font = f; x.fillStyle = "rgba(248,244,234,.92)"; x.fillRect(0, 0, w, 44);
  x.strokeStyle = INK; x.lineWidth = 2; x.strokeRect(1, 1, w - 2, 42);
  x.fillStyle = INK; x.textBaseline = "middle"; x.fillText(text, 10, 23);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  s.scale.set(w / 44 * 0.42, 0.42, 1); s.position.y = 2.15; return s;
}

function figure(THREE, toon, name) {
  const g = new THREE.Group(), eva = toon(EVA), paper = toon("#f8f4ea");
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.32, 1.05, 6), eva); body.position.y = 0.55;
  const head = new THREE.Mesh(new THREE.IcosahedronGeometry(0.22, 0), paper); head.position.y = 1.32;
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.14, 4), eva); nose.rotation.z = -Math.PI / 2; nose.position.set(0.24, 1.32, 0);
  g.add(body, head, nose, nameSprite(THREE, name));
  const note = nameSprite(THREE, "♪"); note.position.y = 2.65; note.visible = false; g.add(note);
  return { group: g, note };
}

export function makeOthers(THREE, scene, toon, opts) {
  const { client, groundAt, onWhistle, onList } = opts;
  const me = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)).slice(0, 12);
  const people = new Map();          // id -> {name, fig, target{x,z,yaw}, seen}
  let ch = null, name = opts.name || "visitor", last = { x: 0, z: 0, yaw: 0, t: 0 }, beat = null, getPos = null;

  function list() {
    onList && onList([...people.values()].filter(p => p.name).map(p => p.name));
  }
  function person(id, nm) {
    let p = people.get(id);
    if (!p) { p = { name: nm || "visitor", fig: null, target: null, seen: Date.now() }; people.set(id, p); }
    if (nm && nm !== p.name) {               // renamed: a new label
      p.name = nm;
      if (p.fig) { scene.remove(p.fig.group); p.fig = null; }
      list();
    }
    return p;
  }
  function place(id, msg) {
    const p = person(id, msg.name);
    p.seen = Date.now();
    p.target = { x: +msg.x, z: +msg.z, yaw: +msg.yaw || 0 };
    if (!Number.isFinite(p.target.x) || !Number.isFinite(p.target.z)) { p.target = null; return; }
    if (!p.fig) {
      p.fig = figure(THREE, toon, p.name.slice(0, 24));
      p.fig.group.position.set(p.target.x, groundAt(p.target.x, p.target.z), p.target.z);
      scene.add(p.fig.group);
    }
  }
  function send(force) {
    if (!ch || !getPos) return;
    const now = Date.now(), pos = getPos();
    if (!pos) return;
    const moved = Math.hypot(pos.x - last.x, pos.z - last.z) > 0.2 || Math.abs(pos.yaw - last.yaw) > 0.1;
    if (!force && (!moved || now - last.t < 1000 / MOVE_HZ)) return;
    last = { x: pos.x, z: pos.z, yaw: pos.yaw, t: now };
    ch.send({ type: "broadcast", event: "move", payload: { id: me, name, x: +pos.x.toFixed(2), z: +pos.z.toFixed(2), yaw: +pos.yaw.toFixed(2) } });
  }

  return {
    get count() { return people.size + 1; },
    join(positionFn) {
      if (!client || ch) return;
      getPos = positionFn;
      ch = client.channel("island", { config: { presence: { key: me }, broadcast: { self: false } } });
      ch.on("presence", { event: "sync" }, () => {
        const state = ch.presenceState(), here = new Set();
        for (const [id, metas] of Object.entries(state)) {
          if (id === me) continue;
          here.add(id); person(id, String((metas[0] || {}).name || "visitor").slice(0, 24));
        }
        for (const [id, p] of people) if (!here.has(id)) { if (p.fig) scene.remove(p.fig.group); people.delete(id); }
        list();
      });
      ch.on("broadcast", { event: "move" }, ({ payload }) => { if (payload && payload.id !== me) place(payload.id, payload); });
      ch.on("broadcast", { event: "whistle" }, ({ payload }) => {
        if (!payload || payload.id === me) return;
        const p = people.get(payload.id);
        if (p && p.fig) { p.fig.note.visible = true; setTimeout(() => { if (p.fig) p.fig.note.visible = false; }, 1500); }
        onWhistle && onWhistle({ x: +payload.x, z: +payload.z });
      });
      ch.subscribe(status => {
        if (status === "SUBSCRIBED") { ch.track({ name }); send(true); }
      });
      beat = setInterval(() => send(true), HEARTBEAT);
    },
    leave() {
      clearInterval(beat); beat = null;
      if (ch) { client.removeChannel(ch); ch = null; }
      for (const p of people.values()) if (p.fig) scene.remove(p.fig.group);
      people.clear(); list();
    },
    rename(nm) {
      name = String(nm || "visitor").trim().slice(0, 24) || "visitor";
      if (ch) { ch.track({ name }); send(true); }
    },
    whistle(x, z) {
      if (ch) ch.send({ type: "broadcast", event: "whistle", payload: { id: me, x: +x.toFixed(1), z: +z.toFixed(1) } });
    },
    update(dt) {
      send(false);
      const now = Date.now();
      for (const [id, p] of people) {
        if (!p.fig || !p.target) continue;
        if (now - p.seen > GONE_AFTER) { scene.remove(p.fig.group); p.fig = null; p.target = null; continue; }
        const g = p.fig.group, k = Math.min(1, dt * 6);
        g.position.x += (p.target.x - g.position.x) * k;
        g.position.z += (p.target.z - g.position.z) * k;
        g.position.y = groundAt(g.position.x, g.position.z);
        g.rotation.y = -p.target.yaw;
      }
    },
    people,
  };
}
