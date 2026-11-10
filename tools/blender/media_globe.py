"""media_globe: the Earth with the world's public media on it. Used by the modules "media_tour" (the 14 broadcasters,
one after another) and "media_capture" (every outlet in the State Media Monitor survey, by who controls it).
Data: tools/geo/media_data.json (tools/geo/media_fetch.py). Globe images: talk/gen/ash_globe_*.png (ashburn_fetch.py).

Every part is a unit sphere's worth of geometry about the origin, in UNITY axes with Y = the north pole and longitude
LON0 facing -Z (toward the seats at yaw 0); Blender (x, y, z) = (-X, -Z, Y). The show scales the holder to the globe's
radius in metres, turns it about Y (Spin) to choose a longitude and about X (Tilt) to choose a latitude.
  Globe_W, Globe_E          the Earth, dimmed so the markers carry the picture
  Pin_00 .. Pin_13          a gold pin at each tour stop        Card_00 .. Card_13   its name card (atlas media_cards.png)
  Arc_01 .. Arc_13          the hop from the stop before        Ball                 the light that makes the hops (at the origin)
  Dots_All                  every outlet, one warm dot each
  Dots_Captured, Dots_Mixed, Dots_Unknown, Dots_Independent     the same dots by State Media Monitor's typology
  Beams_Independent         a gold spike on each independent public outlet
Run: blender -b --factory-startup --python tools/blender/media_globe.py
"""
import bpy, bmesh, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()
D = json.load(open(os.path.join(C.REPO, "tools", "geo", "media_data.json"), encoding="utf-8"))
LON0 = 0.0                          # the Greenwich meridian faces the seats at yaw 0
R = C.root("media_globe")


def B(v): return Vector((-v[0], -v[2], v[1]))            # Unity -> Blender


def P(lat, lon, r=1.0):
    """Unity point at latitude, longitude (degrees), radius r."""
    a, d = math.radians(lat), math.radians(lon - LON0)
    return Vector((r * math.cos(a) * math.sin(d), r * math.sin(a), -r * math.cos(a) * math.cos(d)))


def frame(lat, lon):
    """Unit vectors at a place: up (away from the centre), east, north."""
    up = P(lat, lon).normalized()
    north = (P(min(89.9, lat + 0.1), lon) - P(lat, lon)).normalized()
    north = (north - up * north.dot(up)).normalized()
    east = north.cross(up).normalized()
    if (P(lat, lon + 0.1) - P(lat, lon)).dot(east) < 0: east = -east
    return up, east, north


def new_part(name, mats):
    me = bpy.data.meshes.new(name)
    for m in mats: me.materials.append(C.mat(m))
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.parent = R
    o["keep_uv"] = True
    return o, me


def finish_bm(bm, me, centre=None, smooth=False):
    """Faces turned outward (away from the globe's centre, or from `centre` for a closed shape) and written to the mesh."""
    for f in bm.faces:
        f.normal_update()
        ref = f.calc_center_median() - (B(centre) if centre is not None else Vector((0, 0, 0)))
        if f.normal.dot(ref) < 0: f.normal_flip()
        f.smooth = smooth
    bm.to_mesh(me); bm.free()


# ------------------------------------------------------------------ the globe
def globe_half(name, mat, lon0, lon1):
    o, me = new_part(name, [mat])
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    NU, NV = 48, 48; eps = 0.5 / 2048
    vs = [[bm.verts.new(B(P(-90 + 180 * j / NV, lon0 + (lon1 - lon0) * i / NU))) for i in range(NU + 1)] for j in range(NV + 1)]
    for j in range(NV):
        for i in range(NU):
            quad = [vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]]
            if len({tuple(round(c, 9) for c in v.co) for v in quad}) < 3: continue
            try: f = bm.faces.new(quad)
            except ValueError: continue
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (eps + (1 - 2 * eps) * ii / NU, eps + (1 - 2 * eps) * jj / NV)
    finish_bm(bm, me, smooth=True)


globe_half("Globe_W", "TK_MediaGlobeW", -180, 0)
globe_half("Globe_E", "TK_MediaGlobeE", 0, 180)

# ------------------------------------------------------------------ the tour: pins, cards, arcs, the ball
PIN_TIP = 1.13
cols, rows = D["cardGrid"]
for k, s in enumerate(D["stops"]):
    up, east, north = frame(s["lat"], s["lon"])
    base = up * 0.999; tip = up * PIN_TIP
    o, me = new_part(f"Pin_{k:02d}", ["TK_MediaGold"])
    bm = bmesh.new()
    ring = [bm.verts.new(B(base + (east * math.cos(a) + north * math.sin(a)) * 0.011)) for a in (i * math.tau / 6 for i in range(6))]
    neck = [bm.verts.new(B(up * (PIN_TIP - 0.03) + (east * math.cos(a) + north * math.sin(a)) * 0.004)) for a in (i * math.tau / 6 for i in range(6))]
    for i in range(6): bm.faces.new((ring[i], ring[(i + 1) % 6], neck[(i + 1) % 6], neck[i]))
    head = [bm.verts.new(B(tip + d * 0.022)) for d in (up, -up, east, -east, north, -north)]       # an octahedron for the head
    for a, b, c in ((0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)):
        bm.faces.new((head[a], head[b], head[c]))
    for f in bm.faces:                                               # outward from the pin's own axis
        f.normal_update(); c = f.calc_center_median(); axis = B(up)
        if f.normal.dot(c - axis * c.dot(axis) + (axis * 0.001 if c.dot(axis) > (PIN_TIP - 0.0) else Vector((0, 0, 0)))) < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()

    # the name card: above the pin (toward north), facing straight out; 0.42 x 0.105 of the globe's radius (3.8 x 0.95 m)
    o, me = new_part(f"Card_{k:02d}", ["TK_MediaCards"])
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    cen = up * 1.17 + north * 0.14; w, h = 0.42, 0.105
    cx, cy = s["card"]
    u0, u1 = cx / cols, (cx + 1) / cols; v1 = 1 - cy / rows; v0 = 1 - (cy + 1) / rows
    quad = [(cen - east * w / 2 - north * h / 2, (u0, v0)), (cen + east * w / 2 - north * h / 2, (u1, v0)),
            (cen + east * w / 2 + north * h / 2, (u1, v1)), (cen - east * w / 2 + north * h / 2, (u0, v1))]
    f = bm.faces.new([bm.verts.new(B(p)) for p, _ in quad])
    for l, (_, uv) in zip(f.loops, quad): l[uvl].uv = uv
    finish_bm(bm, me)

    if k:                                                            # the hop from the stop before: a thin arc over the surface
        a = P(D["stops"][k - 1]["lat"], D["stops"][k - 1]["lon"]).normalized(); b = up
        ang = a.angle(b); hgt = 0.03 + 0.12 * ang / math.pi
        o, me = new_part(f"Arc_{k:02d}", ["TK_MediaArc"])
        bm = bmesh.new(); N = 40; rings = []
        for i in range(N + 1):
            u = i / N
            d = (a * math.sin((1 - u) * ang) + b * math.sin(u * ang)) / math.sin(ang)
            r = PIN_TIP + hgt * math.sin(math.pi * u)
            t = (b - a * a.dot(b)).normalized() if i == 0 else None
            side = d.cross((b - a)).normalized()
            rings.append([bm.verts.new(B(d * r + (side * math.cos(q) + d * math.sin(q)) * 0.0035)) for q in (j * math.tau / 4 for j in range(4))])
        for i in range(N):
            for j in range(4): bm.faces.new((rings[i][j], rings[i][(j + 1) % 4], rings[i + 1][(j + 1) % 4], rings[i + 1][j]))
        bm.to_mesh(me); bm.free()

o, me = new_part("Ball", ["TK_MediaBall"])
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.024)
for f in bm.faces: f.smooth = True
bm.to_mesh(me); bm.free()

# ------------------------------------------------------------------ every outlet: a dot each, fanned out round its city
DOT_R, STEP, LIFT = 0.011, 0.024, 1.006
by_city = {}
for o_ in D["outlets"]: by_city.setdefault((o_["lat"], o_["lon"]), []).append(o_)
placed = []                                                          # (point up-vector, east, north, group)
for (lat, lon), items in by_city.items():
    up, east, north = frame(lat, lon)
    items.sort(key=lambda x: {"independent": 0, "mixed": 1, "unknown": 2, "captured": 3}[x["group"]])   # the independent ones at the centre
    for j, it in enumerate(items):
        rho = STEP * math.sqrt(j); th = j * math.radians(137.508)
        d = (up + (east * math.cos(th) + north * math.sin(th)) * rho).normalized()
        e2 = (east - d * east.dot(d)).normalized(); n2 = d.cross(e2)
        placed.append((d, e2, n2, it["group"]))


def dots(name, mat, keep, lift=LIFT, radius=DOT_R):
    o, me = new_part(name, [mat])
    bm = bmesh.new()
    for d, e2, n2, grp in placed:
        if not keep(grp): continue
        bm.faces.new([bm.verts.new(B(d * lift + (e2 * math.cos(a) + n2 * math.sin(a)) * radius)) for a in (i * math.tau / 6 for i in range(6))])
    finish_bm(bm, me)
    return len(me.polygons)


n_all = dots("Dots_All", "TK_MediaDotAll", lambda g: True)
n_cap = dots("Dots_Captured", "TK_MediaDotCaptured", lambda g: g == "captured", LIFT + 0.001)
n_mix = dots("Dots_Mixed", "TK_MediaDotMixed", lambda g: g == "mixed", LIFT + 0.001)
n_unk = dots("Dots_Unknown", "TK_MediaDotUnknown", lambda g: g == "unknown", LIFT + 0.001)
n_ind = dots("Dots_Independent", "TK_MediaDotIndependent", lambda g: g == "independent", LIFT + 0.002, DOT_R * 1.5)

# the AI data centers layer (the atlas package's compute "ai"): a magenta diamond each, larger with its power (MW)
o, me = new_part("Dots_AI", ["TK_MediaDotAI"])
bm = bmesh.new()
for a_ in D.get("ai", []):
    up, east, north = frame(a_["lat"], a_["lon"])
    rad = 0.011 + 0.016 * min(1.0, math.sqrt(max(0.0, a_["mw"]) / 1300.0))
    bm.faces.new([bm.verts.new(B(up * (LIFT + 0.004) + (east * math.cos(q) + north * math.sin(q)) * rad)) for q in (i * math.tau / 4 for i in range(4))])
finish_bm(bm, me)
n_ai = len(me.polygons)

o, me = new_part("Beams_Independent", ["TK_MediaGold"])
bm = bmesh.new()
for d, e2, n2, grp in placed:
    if grp != "independent": continue
    ring = [bm.verts.new(B(d * 1.0 + (e2 * math.cos(a) + n2 * math.sin(a)) * 0.009)) for a in (i * math.tau / 5 for i in range(5))]
    tip = bm.verts.new(B(d * 1.2))
    for i in range(5): bm.faces.new((ring[i], ring[(i + 1) % 5], tip))
bm.to_mesh(me); bm.free()

# ------------------------------------------------------------------ the legend for the capture module (1 x 0.5, faces -Z)
o, me = new_part("Legend", ["TK_MediaLegend"])
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
quad = [(Vector((-0.5, -0.25, 0)), (0, 0)), (Vector((0.5, -0.25, 0)), (1, 0)), (Vector((0.5, 0.25, 0)), (1, 1)), (Vector((-0.5, 0.25, 0)), (0, 1))]
f = bm.faces.new([bm.verts.new(B(p)) for p, _ in quad])
for l, (_, uv) in zip(f.loops, quad): l[uvl].uv = uv
finish_bm(bm, me)

# ------------------------------------------------------------------ export
bpy.context.view_layer.update()
objs = C._tree(R)
glb = C.export("media_globe", R)
C.report("media_globe", C.tris(objs), glb, f"globe + {len(D['stops'])} tour stops + {n_all} outlets ({n_cap} captured, {n_mix} mixed, {n_unk} unknown, {n_ind} independent)")
print(f"  dots: all {n_all}, captured {n_cap}, mixed {n_mix}, unknown {n_unk}, independent {n_ind}")
