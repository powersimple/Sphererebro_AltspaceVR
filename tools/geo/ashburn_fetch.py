"""Ashburn zoom module, step 1: fetch open data and bake the map layers.

Run (system Python 3.12 with numpy + Pillow):  python tools/geo/ashburn_fetch.py [--refetch]
Reads   nothing from the project (downloads are cached in tools/geo/cache/, which can be deleted).
Writes  talk/gen/ash_globe_w.png, ash_globe_e.png     the whole Earth, two 2048 x 2048 halves (opaque)
        talk/gen/ash_L1.png .. ash_L6.png             nested map layers centred on the focus, 2048 x 2048 RGBA, feathered edge
        tools/geo/ashburn_data.json                   focus point, layer sizes, building footprints (metres east/north)

Sources (see CREDITS.md):
  NASA Blue Marble Next Generation (public domain)            the globe
  USGS The National Map, USGSImageryOnly tiles (public domain) every layer (Blue Marble / Landsat / NAIP by zoom)
  OpenStreetMap contributors (ODbL)                            building footprints

Each layer is an azimuthal-equidistant square about the focus: pixel (u, v) is (east, north) kilometres along great
circles, so the Blender script can lay the same grid exactly on the sphere.
"""
import io, json, math, os, sys, time, urllib.request, urllib.parse
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(HERE, "cache")
GEN = os.path.join(REPO, "talk", "gen")
UA = {"User-Agent": "geo-bake-script/1.0"}
REFETCH = "--refetch" in sys.argv
R_EARTH = 6371.0088

# Search box for buildings: Ashburn / Sterling, Loudoun County, Virginia ("Data Center Alley")
BOX = (38.955, -77.545, 39.075, -77.405)          # south, west, north, east
MIN_AREA = 1500.0                                  # m2: only large buildings become 3D blocks (houses stay in the imagery)
# layer: (name, full width km, tile zoom)
LAYERS = [("L1", 5000.0, 6), ("L2", 1000.0, 8), ("L3", 200.0, 11), ("L4", 40.0, 13), ("L5", 8.0, 15), ("L6", 2.4, 16)]
SIZE = 2048
TILES = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
BLUE = "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-topography-bathymetry/january/world.topo.bathy.200401.3x5400x2700.jpg"
DC_WORDS = ("data cent", "datacent", "equinix", "digital realty", "amazon", "aws", "google", "microsoft", "meta ", "facebook",
            "cyrusone", "coresite", "ntt", "raging wire", "ragingwire", "qts", "vantage", "aligned", "stack infra", "cloudhq",
            "iron mountain", "sabey", "dupont fabros", "cologix", "evoque", "centersquare", "compass datacent", "h5 ", "switch ",
            "yondr", "edgecore", "stream data", "prime data", "american tower", "databank", "flexential", "verizon", "oracle")


def get(url, name, data=None, tries=4):
    p = os.path.join(CACHE, name)
    if os.path.exists(p) and not REFETCH and os.path.getsize(p) > 0: return open(p, "rb").read()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            b = urllib.request.urlopen(req, timeout=90).read()
            open(p, "wb").write(b); return b
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(2 + 3 * k)


# ---------------------------------------------------------------- buildings
def buildings():
    s, w, n, e = BOX
    q = f'[out:json][timeout:120];(way["building"]({s},{w},{n},{e});relation["building"]({s},{w},{n},{e}););out tags geom;'
    raw = json.loads(get("https://overpass-api.de/api/interpreter", "osm_buildings.json", urllib.parse.urlencode({"data": q}).encode()))
    out = []
    for el in raw["elements"]:
        rings = []
        if el["type"] == "way" and "geometry" in el: rings = [el["geometry"]]
        elif el["type"] == "relation":
            rings = [m["geometry"] for m in el.get("members", []) if m.get("role") == "outer" and "geometry" in m]
        tags = el.get("tags", {})
        for g in rings:
            if len(g) < 4: continue
            out.append({"ll": [(p["lat"], p["lon"]) for p in g], "tags": tags})
    return out, raw.get("osm3s", {}).get("timestamp_osm_base", "")


def is_dc(tags):
    if tags.get("telecom") == "data_center" or tags.get("building") in ("data_center", "data_centre") or tags.get("man_made") == "data_center":
        return True
    txt = " ".join(tags.get(k, "") for k in ("name", "operator", "brand", "description", "owner")).lower() + " "
    return any(wd in txt for wd in DC_WORDS)


def height_of(tags, dc):
    for k in ("height", "building:height"):
        try: return float(str(tags[k]).split()[0])
        except Exception: pass
    try: return float(tags["building:levels"]) * (6.0 if dc else 4.0)
    except Exception: pass
    return 14.0 if dc else 8.0


def local_m(lat, lon, lat0, lon0):
    """Metres east / north of the focus (equirectangular: fine over a few km)."""
    return ((lon - lon0) * math.cos(math.radians(lat0)) * 111194.9, (lat - lat0) * 111194.9)


def area(pts):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]): a += x0 * y1 - x1 * y0
    return a / 2


# ---------------------------------------------------------------- tiles
def tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n
    return x, y


def mosaic(z, x0, y0, x1, y1):
    """Tiles x0..x1, y0..y1 (inclusive) as one RGB array."""
    W = (x1 - x0 + 1) * 256; H = (y1 - y0 + 1) * 256
    arr = np.zeros((H, W, 3), np.uint8)
    n = 2 ** z; todo = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    for k, (x, y) in enumerate(todo):
        im = None
        for up in range(0, 4):                                  # a missing tile is filled from its parent, enlarged
            try:
                zz, xx, yy = z - up, (x % n) >> up, y >> up
                b = get(TILES.format(z=zz, y=yy, x=xx), f"tiles/{zz}/{yy}_{xx}.jpg", tries=2 if up == 0 else 3)
                im = Image.open(io.BytesIO(b)).convert("RGB")
                if np.asarray(im).reshape(-1, 3).max(1).mean() < 6: raise ValueError("served black")   # an empty tile, not night
                if up:
                    s = 256 >> up; ox = ((x % n) - (xx << up)) * s; oy = (y - (yy << up)) * s
                    im = im.crop((ox, oy, ox + s, oy + s)).resize((256, 256), Image.BICUBIC)
                    print(f"   tile {z}/{y}/{x} missing: filled from z{zz}")
                break
            except Exception as e:
                im = None
        if im is not None: arr[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = np.asarray(im)
        else: print(f"   tile {z}/{y}/{x} missing, no parent either")
        if k % 40 == 39: print(f"   z{z}: {k + 1}/{len(todo)} tiles")
    return arr


def bilinear(arr, fx, fy):
    H, W = arr.shape[:2]
    fx = np.clip(fx, 0, W - 1.001); fy = np.clip(fy, 0, H - 1.001)
    x0 = fx.astype(np.int32); y0 = fy.astype(np.int32); ax = (fx - x0)[..., None]; ay = (fy - y0)[..., None]
    a = arr[y0, x0].astype(np.float32); b = arr[y0, x0 + 1].astype(np.float32)
    c = arr[y0 + 1, x0].astype(np.float32); d = arr[y0 + 1, x0 + 1].astype(np.float32)
    return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay


def aeqd(x_km, y_km, lat0, lon0):
    """Azimuthal equidistant about the focus: (east, north) km -> lat, lon (degrees)."""
    d = np.hypot(x_km, y_km) / R_EARTH
    brg = np.arctan2(x_km, y_km)
    p0 = math.radians(lat0)
    lat = np.arcsin(np.sin(p0) * np.cos(d) + np.cos(p0) * np.sin(d) * np.cos(brg))
    lon = math.radians(lon0) + np.arctan2(np.sin(brg) * np.sin(d) * np.cos(p0), np.cos(d) - np.sin(p0) * np.sin(lat))
    return np.degrees(lat), np.degrees(lon)


def feather(n, frac=0.07):
    t = np.linspace(-1, 1, n, dtype=np.float32)
    e = np.clip((1 - np.abs(t)) / frac, 0, 1)
    e = e * e * (3 - 2 * e)
    return np.minimum(e[None, :], e[:, None])


def bake_layer(name, width_km, z, lat0, lon0):
    half = width_km / 2
    g = (np.arange(SIZE, dtype=np.float64) + 0.5) / SIZE * 2 - 1
    xk, yk = np.meshgrid(g * half, -g * half)                 # row 0 = north
    lat, lon = aeqd(xk, yk, lat0, lon0)
    tx, ty = tile_xy(lat, lon, z)
    x0, x1 = int(math.floor(tx.min())), int(math.floor(tx.max())); y0, y1 = int(math.floor(ty.min())), int(math.floor(ty.max()))
    print(f"{name}: {width_km:g} km, z{z}, tiles x {x0}..{x1} y {y0}..{y1} ({(x1 - x0 + 1) * (y1 - y0 + 1)}), "
          f"{width_km * 1000 / SIZE:.1f} m/px wanted, {156543.03 * math.cos(math.radians(lat0)) / 2 ** z:.1f} m/px source")
    src = mosaic(z, x0, y0, x1, y1)
    rgb = bilinear(src, (tx - x0) * 256 - 0.5, (ty - y0) * 256 - 0.5)
    # no-data holes (served black, mostly open water): filled from the imagery three zoom levels up
    hole = rgb.max(2) < 10
    if hole.mean() > 0.0005 and z >= 5:
        hi = Image.fromarray((hole * 255).astype(np.uint8)).filter(__import__("PIL.ImageFilter", fromlist=["x"]).MaxFilter(9))
        soft = np.asarray(hi.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(4)), np.float32)[..., None] / 255.0
        zc = z - 3; cx, cy = tile_xy(lat, lon, zc)
        a0, a1 = int(math.floor(cx.min())), int(math.floor(cx.max())); b0, b1 = int(math.floor(cy.min())), int(math.floor(cy.max()))
        coarse = bilinear(mosaic(zc, a0, b0, a1, b1), (cx - a0) * 256 - 0.5, (cy - b0) * 256 - 0.5)
        rgb = rgb * (1 - soft) + coarse * soft
        print(f"   {name}: {hole.mean() * 100:.1f}% no-data filled from z{zc}")
    a = feather(SIZE)[..., None] * 255.0
    out = np.concatenate([rgb, a], axis=2).round().clip(0, 255).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(GEN, f"ash_{name}.png"), optimize=False, compress_level=4)
    return {"name": name, "km": width_km, "zoom": z, "mean": [float(v) for v in rgb.reshape(-1, 3).mean(0).round(1)]}


def globe():
    im = Image.open(io.BytesIO(get(BLUE, "bluemarble_5400.jpg"))).convert("RGB").resize((4096, 2048), Image.LANCZOS)
    im.crop((0, 0, 2048, 2048)).save(os.path.join(GEN, "ash_globe_w.png"), compress_level=4)      # lon -180..0
    im.crop((2048, 0, 4096, 2048)).save(os.path.join(GEN, "ash_globe_e.png"), compress_level=4)   # lon 0..180
    print("globe: Blue Marble 5400 x 2700 -> two 2048 x 2048 halves")


def main():
    os.makedirs(CACHE, exist_ok=True); os.makedirs(GEN, exist_ok=True)
    bs, stamp = buildings()
    lat_c = (BOX[0] + BOX[2]) / 2; lon_c = (BOX[1] + BOX[3]) / 2
    big = []
    for b in bs:
        pts = [local_m(la, lo, lat_c, lon_c) for la, lo in b["ll"]]
        a = abs(area(pts))
        if a < MIN_AREA: continue
        dc = is_dc(b["tags"])
        cx = sum(p[0] for p in pts[:-1]) / (len(pts) - 1); cy = sum(p[1] for p in pts[:-1]) / (len(pts) - 1)
        big.append({"pts": pts, "area": a, "dc": dc, "h": height_of(b["tags"], dc), "c": (cx, cy),
                    "name": b["tags"].get("name") or b["tags"].get("operator") or ""})
    dcs = [b for b in big if b["dc"]]
    print(f"OSM {stamp}: {len(bs)} buildings in the box, {len(big)} over {MIN_AREA:g} m2, {len(dcs)} tagged or named as data centres")
    # focus: the point with the most data-centre floor area within 1.2 km (searched on a 100 m grid)
    cand = dcs if len(dcs) >= 8 else sorted(big, key=lambda b: -b["area"])[:120]
    best = None
    for gx in np.arange(-6000, 6001, 100.0):
        for gy in np.arange(-6500, 6501, 100.0):
            s = sum(b["area"] for b in cand if (b["c"][0] - gx) ** 2 + (b["c"][1] - gy) ** 2 < 1200.0 ** 2)
            if best is None or s > best[0]: best = (s, gx, gy)
    _, fx, fy = best
    lat0 = lat_c + fy / 111194.9; lon0 = lon_c + fx / (math.cos(math.radians(lat_c)) * 111194.9)
    print(f"focus: {lat0:.5f}, {lon0:.5f} ({best[0] / 1e6:.2f} km2 of data-centre roof within 1.2 km)")
    keep = []
    for b in big:
        pts = [(round(x - fx, 2), round(y - fy, 2)) for x, y in b["pts"]]
        if max(abs(p[0]) for p in pts) > 4100 or max(abs(p[1]) for p in pts) > 4100: continue
        if area(pts) < 0: pts = pts[::-1]                      # counter-clockwise
        keep.append({"pts": pts[:-1], "h": round(b["h"], 1), "dc": b["dc"], "area": round(b["area"]), "name": b["name"]})
    print(f"buildings kept within 4.1 km of the focus: {len(keep)} ({sum(1 for b in keep if b['dc'])} data centres)")
    globe()
    layers = [bake_layer(n, w, z, lat0, lon0) for n, w, z in LAYERS]
    data = {"_readme": "GENERATED by tools/geo/ashburn_fetch.py: do not edit.", "focus": {"lat": round(lat0, 6), "lon": round(lon0, 6)},
            "earthRadiusKm": R_EARTH, "layers": layers, "osmTimestamp": stamp, "buildings": keep}
    json.dump(data, open(os.path.join(HERE, "ashburn_data.json"), "w"), separators=(",", ":"))
    print("wrote tools/geo/ashburn_data.json")


if __name__ == "__main__":
    main()
