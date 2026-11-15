"""Build Grimsby's world: Berkel en Rodenrijs as one low-poly .glb plus a points-of-interest JSON.

Sources
  - Buildings: 3DBAG (https://3dbag.nl, CC BY 4.0), LoD 1.2 solids from the CityJSON tiles.
  - Roads, paths, rail, water, green, POIs and the village boundary: OpenStreetMap via Overpass (ODbL).

Coordinates
  RD New (EPSG:28992) -> local metres around the village centre (the OSM place node of
  Berkel en Rodenrijs, rounded to whole metres). three.js / glTF axes: +x east, +y up, -z north.
  Every building stands on y = 0 (its own ground level from 3DBAG is subtracted), so the world is flat.

Output (next to this script)
  berkel.glb   one mesh per type, positions + indices only (flat shading is done in the viewer),
               Draco-compressed with gltf-transform (npm, see package.json)
  poi.json     points of interest in the same local metres

Usage
  .venv\\Scripts\\python build_world.py            fetch what is missing in cache/, then build
  .venv\\Scripts\\python build_world.py --refresh  fetch everything again
  .venv\\Scripts\\python build_world.py --radius 1500   only keep things within 1500 m of the centre
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import shutil
import struct
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import mapbox_earcut as earcut
import numpy as np
import requests
import shapely
import shapely.prepared
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, shape
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, unary_union

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
BUILD = HERE / "build"
OUT_GLB = HERE / "berkel.glb"
OUT_POI = HERE / "poi.json"
OUT_SPOTS = HERE / "spots"

# Close-ups for the dashboard panel: one small cut-out around every place the bird can be.
# Must match PLACES and HOME in ../place.js.
SPOT_CATEGORIES = {"library", "bench", "church", "windmill", "artwork", "fountain"}
HOME = "n3149917960"
SPOT_RADIUS = 80.0

UA = {"User-Agent": "grimsby-world-build/0.1 (low-poly village model)"}
OVERPASS = ["https://overpass-api.de/api/interpreter",          # tried in turn when one is busy
            "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
WFS = "https://data.3dbag.nl/api/BAG3D/wfs"

RELATION = 47368                  # OSM: boundary of the woonplaats Berkel en Rodenrijs (from BAG)
PLACE_NODE = 44759560             # OSM: place=town node "Berkel en Rodenrijs" = the village centre
AREA = 3600000000 + RELATION

TO_RD = Transformer.from_crs(4326, 28992, always_xy=True)

# Feature layers, drawn as flat polygons a little above the ground. Earlier layers win where they overlap.
ROAD_WIDTH = {
    "motorway": 14, "trunk": 12, "primary": 10, "secondary": 8, "tertiary": 7,
    "motorway_link": 6, "trunk_link": 6, "primary_link": 6, "secondary_link": 6, "tertiary_link": 6,
    "unclassified": 5, "residential": 5, "living_street": 5, "service": 3.5, "pedestrian": 4,
    "busway": 6, "track": 3,
}
PATH_WIDTH = {"cycleway": 2.5, "footway": 1.8, "path": 1.8, "bridleway": 2, "steps": 1.8}
DITCH_WIDTH = {"river": 12, "canal": 8, "stream": 3, "ditch": 2, "drain": 2}
GREEN_TAGS = {
    "leisure": {"park", "garden", "playground", "pitch", "golf_course", "nature_reserve", "common", "dog_park", "recreation_ground"},
    "landuse": {"grass", "recreation_ground", "meadow", "farmland", "forest", "village_green", "cemetery",
                "allotments", "orchard", "plant_nursery", "flowerbed"},
    "natural": {"wood", "scrub", "grassland", "heath", "wetland"},
}
LAYER_Y = {"green": 0.10, "water": 0.12, "paths": 0.14, "roads": 0.16, "rail": 0.18}

# Points of interest: (category, tag, values). The bird uses the category later.
POI_RULES = [
    ("station", "railway", {"station", "halt"}),
    ("station", "public_transport", {"station"}),
    ("church", "amenity", {"place_of_worship"}),
    ("library", "amenity", {"library"}),
    ("school", "amenity", {"school", "college"}),
    ("supermarket", "shop", {"supermarket"}),
    ("bakery", "shop", {"bakery"}),
    ("cafe", "amenity", {"cafe", "ice_cream"}),
    ("restaurant", "amenity", {"restaurant", "fast_food"}),
    ("townhall", "amenity", {"townhall"}),
    ("community", "amenity", {"community_centre", "theatre", "arts_centre", "cinema"}),
    ("pharmacy", "amenity", {"pharmacy"}),
    ("post", "amenity", {"post_office"}),
    ("market", "amenity", {"marketplace"}),
    ("fountain", "amenity", {"fountain"}),
    ("park", "leisure", {"park"}),
    ("playground", "leisure", {"playground"}),
    ("sports", "leisure", {"sports_centre", "stadium", "swimming_pool"}),
    ("windmill", "man_made", {"windmill"}),
    ("artwork", "tourism", {"artwork"}),
    ("bench", "amenity", {"bench"}),
]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------ fetching

def overpass(query: str, name: str, refresh: bool) -> dict:
    f = CACHE / name
    if f.exists() and not refresh:
        return json.loads(f.read_text(encoding="utf-8"))
    for attempt in range(6):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            r = requests.post(url, data={"data": query}, headers=UA, timeout=360)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                data = r.json()
                if "remark" in data and not data.get("elements"):
                    raise ValueError(data["remark"])
                f.write_text(r.text, encoding="utf-8")
                return data
            log(f"overpass {url.split('/')[2]}: {r.status_code}, trying again")
        except (requests.RequestException, ValueError) as e:
            log(f"overpass {url.split('/')[2]}: {e}, trying again")
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("overpass failed on every server")


def fetch_osm(refresh: bool) -> tuple[dict, dict]:
    base = overpass(f"[out:json][timeout:120];(relation({RELATION});node({PLACE_NODE}););out geom;",
                    "osm_boundary.json", refresh)
    q = f"""[out:json][timeout:300];
area({AREA})->.a;
(
  way["highway"](area.a);
  way["railway"~"^(rail|light_rail|subway|tram)$"](area.a);
  way["natural"="water"](area.a); relation["natural"="water"](area.a);
  way["waterway"](area.a); relation["waterway"="riverbank"](area.a);
  way["landuse"~"^(basin|reservoir)$"](area.a);
  way["leisure"](area.a); relation["leisure"](area.a);
  way["landuse"](area.a); relation["landuse"](area.a);
  way["natural"~"^(wood|scrub|grassland|heath|wetland)$"](area.a);
  relation["natural"~"^(wood|scrub|grassland|heath|wetland)$"](area.a);
  nwr["amenity"](area.a);
  nwr["shop"~"^(supermarket|bakery)$"](area.a);
  nwr["railway"~"^(station|halt)$"](area.a);
  nwr["public_transport"="station"](area.a);
  nwr["man_made"="windmill"](area.a);
  nwr["tourism"="artwork"](area.a);
);
out geom;"""
    feats = overpass(q, "osm_features.json", refresh)
    return base, feats


def fetch_tiles(boundary_rd: Polygon, refresh: bool) -> list[Path]:
    (CACHE / "tiles").mkdir(parents=True, exist_ok=True)
    b = boundary_rd.bounds
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature&typeNames=BAG3D:tiles"
           f"&outputFormat=application/json&bbox={b[0]},{b[1]},{b[2]},{b[3]},urn:ogc:def:crs:EPSG::28992")
    idx = CACHE / "tiles.json"
    if refresh or not idx.exists():
        idx.write_text(requests.get(url, headers=UA, timeout=120).text, encoding="utf-8")
    tiles = [t for t in json.loads(idx.read_text(encoding="utf-8"))["features"]
             if shape(t["geometry"]).intersects(boundary_rd)]
    paths = []
    for i, t in enumerate(tiles, 1):
        u = t["properties"]["cj_download"]
        p = CACHE / "tiles" / u.rsplit("/", 1)[1]
        if refresh or not p.exists():
            log(f"tile {i}/{len(tiles)} {p.name}")
            with requests.get(u, headers=UA, timeout=300, stream=True) as r:
                r.raise_for_status()
                tmp = p.with_suffix(".part")
                with open(tmp, "wb") as fh:
                    shutil.copyfileobj(r.raw, fh)
                tmp.replace(p)
        paths.append(p)
    return paths


# ------------------------------------------------------------------ OSM geometry

def rd_line(geom: list[dict]) -> list[tuple[float, float]]:
    xs, ys = TO_RD.transform([p["lon"] for p in geom], [p["lat"] for p in geom])
    return list(zip(xs, ys))


def osm_polygon(el: dict):
    """Polygon of a closed way or a multipolygon relation, in RD. None if it isn't an area."""
    if el["type"] == "way":
        g = el.get("geometry")
        if not g or len(g) < 4 or (g[0]["lat"], g[0]["lon"]) != (g[-1]["lat"], g[-1]["lon"]):
            return None
        p = Polygon(rd_line(g))
        return p if p.is_valid else p.buffer(0)
    if el["type"] == "relation":
        outer, inner = [], []
        for m in el.get("members", []):
            if m["type"] == "way" and m.get("geometry") and len(m["geometry"]) > 1:
                (inner if m.get("role") == "inner" else outer).append(LineString(rd_line(m["geometry"])))
        if not outer:
            return None
        o = unary_union(list(polygonize(unary_union(outer))))
        if inner:
            o = o.difference(unary_union(list(polygonize(unary_union(inner)))))
        return o if not o.is_empty else None
    return None


def osm_center(el: dict):
    if el["type"] == "node":
        return TO_RD.transform(el["lon"], el["lat"])
    poly = osm_polygon(el)
    if poly is not None and not poly.is_empty:
        p = poly.representative_point()
        return p.x, p.y
    g = el.get("geometry") or [m for mm in el.get("members", []) for m in (mm.get("geometry") or [])]
    if g:
        line = rd_line(g)
        return sum(x for x, _ in line) / len(line), sum(y for _, y in line) / len(line)
    if "bounds" in el:
        b = el["bounds"]
        return TO_RD.transform((b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2)
    return None


def width_of(tags: dict, default: float) -> float:
    try:
        return max(1.0, min(30.0, float(str(tags.get("width", "")).replace(",", ".").split()[0])))
    except (ValueError, IndexError):
        return default


def osm_layers(feats: dict, clip) -> dict[str, object]:
    bucket = defaultdict(list)
    for el in feats["elements"]:
        t = el.get("tags", {})
        if el["type"] == "node":
            continue
        hw, rw, ww = t.get("highway"), t.get("railway"), t.get("waterway")
        if el["type"] == "way" and hw and t.get("area") != "yes" and el.get("geometry"):
            if t.get("tunnel") in ("yes", "building_passage") or t.get("layer", "0").startswith("-"):
                continue
            line = LineString(rd_line(el["geometry"]))
            if hw in ROAD_WIDTH:
                bucket["roads"].append(line.buffer(width_of(t, ROAD_WIDTH[hw]) / 2, cap_style="flat", quad_segs=2))
            elif hw in PATH_WIDTH:
                bucket["paths"].append(line.buffer(width_of(t, PATH_WIDTH[hw]) / 2, cap_style="flat", quad_segs=2))
            continue
        if el["type"] == "way" and rw in ("rail", "light_rail", "subway", "tram") and el.get("geometry"):
            if t.get("tunnel") == "yes":
                continue
            bucket["rail"].append(LineString(rd_line(el["geometry"])).buffer(2.0, cap_style="flat", quad_segs=2))
            continue
        if el["type"] == "way" and ww in DITCH_WIDTH and el.get("geometry"):
            if t.get("tunnel") or t.get("culvert") or t.get("layer", "0").startswith("-"):
                continue
            bucket["water"].append(LineString(rd_line(el["geometry"])).buffer(width_of(t, DITCH_WIDTH[ww]) / 2, quad_segs=2))
            continue
        is_water = t.get("natural") == "water" or ww == "riverbank" or t.get("landuse") in ("basin", "reservoir")
        is_green = any(t.get(k) in v for k, v in GREEN_TAGS.items())
        if is_water or is_green:
            p = osm_polygon(el)
            if p is not None and not p.is_empty:
                bucket["water" if is_water else "green"].append(p)

    layers = {}
    taken = None
    for name in ("rail", "roads", "paths", "water", "green"):
        log(f"osm layer {name}: {len(bucket[name])} shapes")
        if not bucket[name]:
            continue
        g = unary_union(bucket[name]).intersection(clip)
        if taken is not None:
            g = g.difference(taken)
        g = g.simplify(0.25)
        layers[name] = g
        taken = g if taken is None else unary_union([taken, g])
    return layers


def collect_pois(feats: dict, clip, green, to_local) -> list[dict]:
    pois, seen = [], set()
    for el in feats["elements"]:
        t = el.get("tags", {})
        cat = next((c for c, k, vals in POI_RULES if t.get(k) in vals), None)
        if not cat:
            continue
        if cat == "bench" and el["type"] != "node":
            continue
        c = osm_center(el)
        if not c or not clip.contains(Point(c)):
            continue
        if cat == "bench" and (green is None or not green.contains(Point(c))):
            continue          # only park benches; the rest is clutter
        key = (cat, t.get("name"), round(c[0] / 30), round(c[1] / 30))
        if key in seen:           # station mapped as node + area etc.
            continue
        seen.add(key)
        x, z = to_local(*c)
        p = {"id": f"{el['type'][0]}{el['id']}", "category": cat, "x": round(x, 1), "z": round(z, 1)}
        if t.get("name"):
            p["name"] = t["name"]
        sub = t.get("station") or t.get("religion") or t.get("sport")
        if sub:
            p["kind"] = sub
        pois.append(p)
    return pois


# ------------------------------------------------------------------ meshes

class Mesh:
    """Triangles collected in local coordinates; vertices welded at the millimetre on export."""

    def __init__(self):
        self.tris: list[np.ndarray] = []

    def add(self, tri: np.ndarray):
        self.tris.append(tri.astype(np.float64))

    def arrays(self):
        if not self.tris:
            return None, None
        v = np.concatenate(self.tris).reshape(-1, 3)
        key = np.round(v * 1000).astype(np.int64)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        return (uniq / 1000).astype(np.float32), inv.reshape(-1).astype(np.uint32)


def triangulate(rings: list[np.ndarray], normal: np.ndarray) -> np.ndarray:
    """Earcut a planar polygon (outer ring + holes, 3D) -> (n, 3, 3) triangles facing `normal`."""
    ax = int(np.argmax(np.abs(normal)))
    keep = [i for i in range(3) if i != ax]
    pts = np.concatenate(rings)
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    idx = earcut.triangulate_float64(pts[:, keep], ends)
    if len(idx) == 0:
        return np.empty((0, 3, 3))
    tri = pts[idx.reshape(-1, 3)]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    flip = (n @ normal) < 0
    tri[flip] = tri[flip][:, [0, 2, 1]]
    return tri


def newell(ring: np.ndarray) -> np.ndarray:
    nxt = np.roll(ring, -1, axis=0)
    n = np.array([
        np.sum((ring[:, 1] - nxt[:, 1]) * (ring[:, 2] + nxt[:, 2])),
        np.sum((ring[:, 2] - nxt[:, 2]) * (ring[:, 0] + nxt[:, 0])),
        np.sum((ring[:, 0] - nxt[:, 0]) * (ring[:, 1] + nxt[:, 1])),
    ])
    ln = np.linalg.norm(n)
    return n / ln if ln > 0 else n


def flat_polygons(geom, y: float, mesh: Mesh, to_local):
    polys = [geom] if isinstance(geom, Polygon) else [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]
    up = np.array([0.0, 1.0, 0.0])
    for p in polys:
        if p.area < 1.0:
            continue
        rings = []
        for r in [p.exterior, *p.interiors]:
            c = np.asarray(r.coords)[:-1]
            x, z = to_local(c[:, 0], c[:, 1])
            rings.append(np.column_stack([x, np.full(len(c), y), z]))
        mesh.add(triangulate(rings, up))


def plinth(boundary, mesh_top: Mesh, mesh_side: Mesh, to_local, depth: float = 8.0):
    flat_polygons(boundary, 0.0, mesh_top, to_local)
    polys = [boundary] if isinstance(boundary, Polygon) else list(boundary.geoms)
    for p in polys:
        ext = orient(p, 1.0).exterior    # counter-clockwise seen from above
        c = np.asarray(ext.coords)
        x, z = to_local(c[:, 0], c[:, 1])
        for i in range(len(c) - 1):
            a0 = np.array([x[i], 0, z[i]]); b0 = np.array([x[i + 1], 0, z[i + 1]])
            a1 = a0 - [0, depth, 0]; b1 = b0 - [0, depth, 0]
            mid = (a0 + b0) / 2
            out = np.array([b0[2] - a0[2], 0, -(b0[0] - a0[0])])     # outward normal (local z is flipped)
            q = np.array([[a0, a1, b1], [a0, b1, b0]])
            n = np.cross(q[0][1] - q[0][0], q[0][2] - q[0][0])
            if n @ out < 0:
                q = q[:, [0, 2, 1]]
            mesh_side.add(q)


def buildings(tile_paths: list[Path], clip, to_local, meshes: dict[str, Mesh], per_building: list) -> dict:
    stats = defaultdict(int)
    prepared = shapely.prepared.prep(clip)
    for tp in tile_paths:
        cj = json.load(gzip.open(tp))
        sc, tr = np.array(cj["transform"]["scale"]), np.array(cj["transform"]["translate"])
        V = np.array(cj["vertices"], dtype=np.float64) * sc + tr
        objs = cj["CityObjects"]
        for oid, o in objs.items():
            if o["type"] != "Building":
                continue
            a = o.get("attributes", {})
            parts = [objs[c] for c in o.get("children", []) if c in objs]
            geoms = [g for p in parts for g in p.get("geometry", []) if g.get("lod") == "1.2"]
            if not geoms:
                stats["no_lod12"] += 1
                continue
            vids = {v for g in geoms for shell in g["boundaries"] for surf in shell for ring in surf for v in ring}
            pts = V[list(vids)]
            cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
            if not prepared.contains(Point(cx, cy)):
                continue
            ground = a.get("b3_h_maaiveld")
            if ground is None:
                ground = float(pts[:, 2].min())
            kas = bool(a.get("b3_kas_warenhuis"))
            stats["greenhouses" if kas else "buildings"] += 1
            bx, bz = to_local(cx, cy)
            mine = defaultdict(list)
            per_building.append((float(bx), float(bz), mine))
            for g in geoms:
                sem = g.get("semantics", {})
                surfaces, values = sem.get("surfaces", []), sem.get("values", [])
                for si, shell in enumerate(g["boundaries"]):
                    for fi, face in enumerate(shell):
                        st = "WallSurface"
                        if values and values[si] and values[si][fi] is not None:
                            st = surfaces[values[si][fi]]["type"]
                        if st == "GroundSurface":
                            continue
                        rings = []
                        for ring in face:
                            r = V[ring]
                            x, z = to_local(r[:, 0], r[:, 1])
                            rings.append(np.column_stack([x, np.maximum(r[:, 2] - ground, 0.0), z]))
                        n = newell(rings[0])
                        if not n.any():
                            continue
                        tri = triangulate(rings, n)
                        if kas:
                            meshes["greenhouse"].add(tri)
                            mine["greenhouse"].append(tri)
                        else:
                            kind = "roofs" if st == "RoofSurface" else "walls"
                            meshes[kind].add(tri)
                            mine[kind].append(tri)
        log(f"{tp.name}: {stats['buildings']} buildings, {stats['greenhouses']} greenhouses so far")
    return dict(stats)


# ------------------------------------------------------------------ glTF

def write_glb(path: Path, named: list[tuple[str, np.ndarray, np.ndarray]], extras: dict):
    bin_parts, views, accessors, meshes, nodes, materials = [], [], [], [], [], []
    offset = 0

    def push(data: bytes, target: int):
        nonlocal offset
        pad = (-len(data)) % 4
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        bin_parts.append(data + b"\0" * pad)
        offset += len(data) + pad
        return len(views) - 1

    for i, (name, pos, idx) in enumerate(named):
        pv = push(pos.tobytes(), 34962)
        iv = push(idx.tobytes(), 34963)
        accessors.append({"bufferView": pv, "componentType": 5126, "count": len(pos), "type": "VEC3",
                          "min": pos.min(0).tolist(), "max": pos.max(0).tolist()})
        accessors.append({"bufferView": iv, "componentType": 5125, "count": len(idx), "type": "SCALAR"})
        materials.append({"name": name, "pbrMetallicRoughness": {"baseColorFactor": [0.9, 0.9, 0.9, 1], "metallicFactor": 0}})
        meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": len(accessors) - 2},
                                                     "indices": len(accessors) - 1, "material": i}]})
        nodes.append({"name": name, "mesh": i})

    blob = b"".join(bin_parts)
    gltf = {"asset": {"version": "2.0", "generator": "grimsby build_world.py",
                      "copyright": "Buildings: 3DBAG (CC BY 4.0). Map data: OpenStreetMap contributors (ODbL)."},
            "scene": 0, "scenes": [{"name": "berkel", "nodes": list(range(len(nodes))), "extras": extras}],
            "nodes": nodes, "meshes": meshes, "materials": materials, "accessors": accessors,
            "bufferViews": views, "buffers": [{"byteLength": len(blob)}]}
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(blob), 0x004E4942)); f.write(blob)


def draco(raw: Path, out: Path):
    cli = HERE / "node_modules" / ".bin" / ("gltf-transform.cmd" if sys.platform == "win32" else "gltf-transform")
    if not cli.exists():
        subprocess.run("npm install --no-audit --no-fund", cwd=HERE, shell=True, check=True)
    subprocess.run([str(cli), "draco", str(raw), str(out), "--method", "edgebreaker",
                    "--quantize-position", "16"], check=True, shell=sys.platform == "win32")


# ------------------------------------------------------------------ close-ups for the panel

def write_spots(pois: list[dict], per_building: list, layers: dict, clip, cx: float, cy: float):
    """spots/<poi id>.json: everything within SPOT_RADIUS of a place, as flat triangle lists in decimetres,
    relative to the place (x east, y up, z = -north). Small enough to load on the dashboard without the world."""
    OUT_SPOTS.mkdir(exist_ok=True)
    for old in OUT_SPOTS.glob("*.json"):
        old.unlink()
    wanted = [p for p in pois if p["category"] in SPOT_CATEGORIES or p["id"] == HOME]
    total = 0
    for p in wanted:
        px, pz = p["x"], p["z"]
        out = defaultdict(list)

        def put(kind, tri):
            t = tri.reshape(-1, 3) - [px, 0, pz]
            out[kind].extend(np.round(t * 10).astype(int).ravel().tolist())

        for bx, bz, parts in per_building:
            if (bx - px) ** 2 + (bz - pz) ** 2 <= SPOT_RADIUS ** 2:
                for kind, tris in parts.items():
                    for tri in tris:
                        put(kind, tri)
        disc = Point(px + cx, -pz + cy).buffer(SPOT_RADIUS, quad_segs=12).intersection(clip)
        sub = {"ground": Mesh()}
        flat_polygons(disc, 0.0, sub["ground"], lambda x, y: (np.asarray(x) - cx, -(np.asarray(y) - cy)))
        for name, g in layers.items():
            sub[name] = Mesh()
            flat_polygons(g.intersection(disc), LAYER_Y[name], sub[name], lambda x, y: (np.asarray(x) - cx, -(np.asarray(y) - cy)))
        for kind, m in sub.items():
            for tri in m.tris:
                put(kind, tri)
        f = OUT_SPOTS / f"{p['id']}.json"
        f.write_text(json.dumps({"id": p["id"], "category": p["category"], "radius": SPOT_RADIUS, "unit": 0.1,
                                 "layers": out}, separators=(",", ":")), encoding="utf-8")
        total += f.stat().st_size
    log(f"{len(wanted)} close-ups in spots/, {total / 1e6:.1f} MB")


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="download everything again")
    ap.add_argument("--radius", type=float, default=0, help="only keep a circle of this many metres around the centre")
    a = ap.parse_args()
    CACHE.mkdir(exist_ok=True); BUILD.mkdir(exist_ok=True)
    t0 = time.time()

    base, feats = fetch_osm(a.refresh)
    rel = next(e for e in base["elements"] if e["type"] == "relation")
    node = next(e for e in base["elements"] if e["type"] == "node")
    boundary = osm_polygon(rel)
    cx, cy = (round(v) for v in TO_RD.transform(node["lon"], node["lat"]))
    clip = boundary if not a.radius else boundary.intersection(Point(cx, cy).buffer(a.radius, quad_segs=32))
    clip = clip.simplify(0.5)
    log(f"centre RD {cx}, {cy}; area {clip.area / 1e6:.1f} km2")

    def to_local(x, y):
        return np.asarray(x) - cx, -(np.asarray(y) - cy)

    tiles = fetch_tiles(clip, a.refresh)
    meshes = defaultdict(Mesh)
    per_building = []
    stats = buildings(tiles, clip, to_local, meshes, per_building)

    plinth(clip, meshes["ground"], meshes["ground_side"], to_local)
    layers = osm_layers(feats, clip)
    for name, g in layers.items():
        flat_polygons(g, LAYER_Y[name], meshes[name], to_local)

    order = ["ground", "ground_side", "green", "water", "paths", "roads", "rail", "walls", "roofs", "greenhouse"]
    named, tri_count = [], {}
    for name in order:
        pos, idx = meshes[name].arrays() if name in meshes else (None, None)
        if pos is None:
            continue
        named.append((name, pos, idx))
        tri_count[name] = len(idx) // 3

    x0, y0 = clip.bounds[:2]; x1, y1 = clip.bounds[2:]
    extras = {"centre_rd": [cx, cy], "crs": "EPSG:28992 -> local metres, +x east, -z north, y up",
              "bounds_local": {"x": [x0 - cx, x1 - cx], "z": [-(y1 - cy), -(y0 - cy)]},
              "triangles": tri_count, "buildings": stats}
    raw = BUILD / "berkel.raw.glb"
    write_glb(raw, named, extras)
    log(f"raw glb {raw.stat().st_size / 1e6:.1f} MB, {sum(tri_count.values()):,} triangles: {tri_count}")
    draco(raw, OUT_GLB)
    log(f"draco glb {OUT_GLB.stat().st_size / 1e6:.2f} MB")

    green = layers.get("green")
    green = shapely.prepared.prep(green.buffer(5)) if green is not None else None
    pois = collect_pois(feats, clip, green, lambda x, y: (x - cx, -(y - cy)))
    by_cat = defaultdict(int)
    for p in pois:
        by_cat[p["category"]] += 1
    OUT_POI.write_text(json.dumps({
        "centre_rd": [cx, cy],
        "note": "Local metres: x east, z = -north (three.js), from OpenStreetMap (ODbL).",
        "pois": pois,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"{len(pois)} POIs: {dict(by_cat)}")
    write_spots(pois, per_building, layers, clip, cx, cy)
    log(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
