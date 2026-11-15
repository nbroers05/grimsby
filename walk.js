// Walking around the island in first person, like pinos.world: click to look (pointer lock), W/S walk, A/D turn,
// shift to hurry. Arrow keys work too. Collisions come from island.js (walkable, groundAt): 2D outlines, not meshes.
// Used by world/viewer.html and the site's expanded world (world.js). Touch: not yet (low priority in WERELD.md).

const SPEED = 4.2, RUN = 8.5, TURN = 1.9, EYE = 1.62, LOOK = 0.0022;

export function makeWalker(THREE, camera, dom, island, opts = {}) {
  const pos = new THREE.Vector3(island.spawn.x, 0, island.spawn.z);
  let yaw = island.spawn.yaw, pitch = -0.05, on = false, eyeY = null;
  const keys = new Set();

  const down = e => {
    if (!on || e.ctrlKey || e.metaKey || e.altKey) return;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || "")) return;
    const k = e.code;
    if (["KeyW", "KeyS", "KeyA", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "ShiftLeft", "ShiftRight"].includes(k)) {
      keys.add(k); e.preventDefault();
    }
    if (k === "KeyE" && opts.onWhistle) opts.onWhistle(pos.clone());
  };
  const up = e => keys.delete(e.code);
  const move = e => {
    if (!on || document.pointerLockElement !== dom) return;
    yaw += e.movementX * LOOK;
    pitch = Math.max(-1.2, Math.min(1.1, pitch - e.movementY * LOOK));
  };
  const click = () => { if (on && document.pointerLockElement !== dom && dom.requestPointerLock) dom.requestPointerLock(); };
  addEventListener("keydown", down); addEventListener("keyup", up); addEventListener("blur", () => keys.clear());
  document.addEventListener("mousemove", move); dom.addEventListener("click", click);

  function tryMove(nx, nz) {                        // slide along walls: whole step, else one axis, else stay
    if (island.walkable(nx, nz)) { pos.x = nx; pos.z = nz; return; }
    if (island.walkable(nx, pos.z)) { pos.x = nx; return; }
    if (island.walkable(pos.x, nz)) pos.z = nz;
  }

  function update(dt) {
    if (!on) return;
    dt = Math.min(dt, 0.1);
    const has = k => keys.has(k);
    if (has("KeyA") || has("ArrowLeft")) yaw -= TURN * dt;
    if (has("KeyD") || has("ArrowRight")) yaw += TURN * dt;
    const f = (has("KeyW") || has("ArrowUp") ? 1 : 0) - (has("KeyS") || has("ArrowDown") ? 1 : 0);
    if (f) {
      const v = (has("ShiftLeft") || has("ShiftRight") ? RUN : SPEED) * f * dt;
      tryMove(pos.x + Math.cos(yaw) * v, pos.z + Math.sin(yaw) * v);
    }
    const g = island.groundAt(pos.x, pos.z) + EYE;
    eyeY = eyeY == null ? g : eyeY + (g - eyeY) * Math.min(1, dt * 10);   // step onto the platform softly
    pos.y = eyeY;
    camera.position.copy(pos);
    camera.lookAt(pos.x + Math.cos(yaw) * Math.cos(pitch), pos.y + Math.sin(pitch), pos.z + Math.sin(yaw) * Math.cos(pitch));
  }

  return {
    pos, update, get on() { return on; }, get yaw() { return yaw; },
    start() { on = true; eyeY = null; update(0); },
    stop() { on = false; keys.clear(); if (document.pointerLockElement === dom) document.exitPointerLock(); },
    reset() { pos.set(island.spawn.x, 0, island.spawn.z); yaw = island.spawn.yaw; pitch = -0.05; eyeY = null; },
    dispose() { removeEventListener("keydown", down); removeEventListener("keyup", up); document.removeEventListener("mousemove", move); dom.removeEventListener("click", click); },
  };
}
