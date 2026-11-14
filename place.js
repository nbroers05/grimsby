// Where Grimsby is, shared by the site (world.js) and the dashboard panel.
// The categories and HOME must match SPOT_CATEGORIES / HOME in world/build_world.py (that script cuts out a small
// close-up of every possible place for the panel).

export const HOME = "n3149917960";                 // OSM: station Berkel Westpolder. He lives on its roof.
export const PLACES = {                             // old brain (log.json entries): what he did last -> where he goes
  search: ["library"],
  diary: ["bench"],
  draw: ["church", "windmill", "artwork", "fountain"],
};
// Brain v2 actions -> one of the three poses look.js/world.js know (head down, looking around, hopping)
const POSES = { diary: "diary", read_back: "diary", tidy: "diary", search: "search", wander: "search",
  pigeons: "search", neighbour: "search", draw: "draw" };
export const pose = (action) => POSES[action] || null;
const WORDS = {
  library: "at the library", bench: "on a bench in the park", church: "on the church roof",
  windmill: "on the windmill", artwork: "next to a statue", fountain: "by the fountain",
};

function hash(s) { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }

// Same answer on every page load for the same last action
export function placeFor(entry, asleep, pois) {
  const home = pois.find(p => p.id === HOME) || pois.find(p => p.category === "station");
  if (asleep || !entry) return { poi: home, home: true };
  const cats = PLACES[entry.action] || [];
  const options = pois.filter(p => cats.includes(p.category));
  if (!options.length) return { poi: home, home: true };
  return { poi: options[hash(entry.time) % options.length], home: false };
}

// Brain v2: data/now.json says where he is (place.poi = an id from world/poi.json, place.category as fallback)
export function placeForNow(now, asleep, pois) {
  const home = pois.find(p => p.id === HOME) || pois.find(p => p.category === "station");
  const pl = now && now.place;
  if (asleep || !pl || pl.category === "home" || pl.poi === HOME) return { poi: home, home: true };
  const exact = pois.find(p => p.id === pl.poi);
  if (exact) return { poi: exact, home: false };
  const options = pois.filter(p => p.category === pl.category);
  if (!options.length) return { poi: home, home: true };
  return { poi: options[hash(now.at || "") % options.length], home: false };
}

export function whereText(place, asleep) {
  const p = place.poi;
  if (!p) return "";
  if (place.home) return (asleep ? "Asleep on the roof of station " : "At home, on the roof of station ") + (p.name || "") + ".";
  const w = WORDS[p.category] || "somewhere";
  return w.charAt(0).toUpperCase() + w.slice(1) + (p.name && p.category !== "bench" ? ": " + p.name : "") + ".";
}

// Where on (or next to) a place he lands. heightAt(x, z) gives the top of whatever is there (roof or ground).
// x/z are relative to the place when `local` is true (the panel's close-up), else world coordinates.
export function perch(p, heightAt, local = false) {
  const ox = local ? 0 : p.x, oz = local ? 0 : p.z;
  if (["bench", "fountain", "artwork"].includes(p.category)) return [ox, heightAt(ox, oz), oz];
  for (let r = 0; r <= 60; r += 6) {               // the point may sit next to its building: look around for a roof
    for (let a = 0; a < (r ? 8 : 1); a++) {
      const x = ox + r * Math.cos(a * Math.PI / 4), z = oz + r * Math.sin(a * Math.PI / 4);
      const y = heightAt(x, z);
      if (y > 2) return [x, y, z];
    }
  }
  return [ox, heightAt(ox, oz), oz];
}
