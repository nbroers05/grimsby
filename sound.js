// Sounds on the island, made in code with WebAudio (no files, nothing to credit): footsteps, the sea, now and then
// a bird, a whistle, his caw. Browsers only allow sound after a click, so nothing plays until start() is called
// from one. Off/on is remembered per visitor.

let ctx = null, master = null, sea = null, on = true, birdTimer = null;
try { on = localStorage.getItem("grimsby-sound") !== "0"; } catch (e) {}

function noiseBuffer(sec) {
  const b = ctx.createBuffer(1, Math.floor(ctx.sampleRate * sec), ctx.sampleRate), d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  return b;
}

export function start() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    master = ctx.createGain(); master.gain.value = on ? 0.7 : 0; master.connect(ctx.destination);
    // the sea: brown-ish noise through a low filter, slowly swelling
    const src = ctx.createBufferSource(); src.buffer = noiseBuffer(4); src.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 420;
    const g = ctx.createGain(); g.gain.value = 0.0;
    const lfo = ctx.createOscillator(), lfoG = ctx.createGain(); lfo.frequency.value = 0.12; lfoG.gain.value = 0.05;
    lfo.connect(lfoG); lfoG.connect(g.gain); lfo.start();
    src.connect(lp); lp.connect(g); g.connect(master); src.start();
    sea = g;
  }
  if (ctx.state === "suspended") ctx.resume();
  if (!birdTimer) birdTimer = setInterval(() => { if (Math.random() < 0.25) bird(); }, 7000);
}

export function stop() { clearInterval(birdTimer); birdTimer = null; if (ctx) ctx.suspend(); }
export function isOn() { return on; }
export function setOn(v) {
  on = v;
  try { localStorage.setItem("grimsby-sound", v ? "1" : "0"); } catch (e) {}
  if (master) master.gain.setTargetAtTime(v ? 0.7 : 0, ctx.currentTime, 0.05);
}

// how close the sea is: 0 inland, 1 on the beach (world.js passes the shore distance)
export function seaNear(k) { if (sea) sea.gain.setTargetAtTime(0.05 + 0.12 * k, ctx.currentTime, 0.5); }

export function step(onSand) {
  if (!ctx || !on) return;
  const t = ctx.currentTime, src = ctx.createBufferSource(); src.buffer = noiseBuffer(0.12);
  const f = ctx.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = onSand ? 700 : 1500; f.Q.value = 0.8;
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(onSand ? 0.12 : 0.18, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + (onSand ? 0.11 : 0.07));
  src.connect(f); f.connect(g); g.connect(master); src.start(t); src.stop(t + 0.13);
}

// a whistle: two rising notes. volume 0..1 (distance)
export function whistle(volume = 1) {
  if (!ctx || !on || volume <= 0.02) return;
  const t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain();
  o.type = "sine";
  o.frequency.setValueAtTime(1500, t); o.frequency.exponentialRampToValueAtTime(2300, t + 0.18);
  o.frequency.setValueAtTime(1700, t + 0.26); o.frequency.exponentialRampToValueAtTime(2600, t + 0.5);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(0.16 * volume, t + 0.03); g.gain.setValueAtTime(0.16 * volume, t + 0.17);
  g.gain.exponentialRampToValueAtTime(0.02 * volume, t + 0.23); g.gain.exponentialRampToValueAtTime(0.16 * volume, t + 0.29);
  g.gain.exponentialRampToValueAtTime(0.0001, t + 0.55);
  o.connect(g); g.connect(master); o.start(t); o.stop(t + 0.6);
}

// his caw: a rough, falling sawtooth through a nasal filter, twice
export function caw(volume = 1) {
  if (!ctx || !on || volume <= 0.02) return;
  for (const [d, len] of [[0, 0.32], [0.42, 0.26]]) {
    const t = ctx.currentTime + d, o = ctx.createOscillator(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    o.type = "sawtooth"; o.frequency.setValueAtTime(520, t); o.frequency.exponentialRampToValueAtTime(330, t + len);
    f.type = "bandpass"; f.frequency.value = 1100; f.Q.value = 2.5;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.22 * volume, t + 0.03);
    g.gain.exponentialRampToValueAtTime(0.0001, t + len);
    o.connect(f); f.connect(g); g.connect(master); o.start(t); o.stop(t + len + 0.02);
  }
}

// some small bird far off: three quick chirps
function bird() {
  if (!ctx || !on) return;
  const base = 2600 + Math.random() * 1400;
  for (let i = 0; i < 3; i++) {
    const t = ctx.currentTime + i * 0.13, o = ctx.createOscillator(), g = ctx.createGain();
    o.type = "sine"; o.frequency.setValueAtTime(base, t); o.frequency.exponentialRampToValueAtTime(base * 1.35, t + 0.07);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.04, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
    o.connect(g); g.connect(master); o.start(t); o.stop(t + 0.1);
  }
}
