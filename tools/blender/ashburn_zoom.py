"""ashburn_zoom: the Earth, six nested map layers centred on Ashburn, Virginia, and its large buildings as blocks.
Module "ashburn" (tools/talk/modules/ashburn.py animates it; tools/geo/ashburn_fetch.py makes the images and data).

Every part is authored in the frame of the node that holds it in the show, in UNITY axes X = east, Y = up (away from
the Earth's centre at the focus), Z = north; Blender (x, y, z) = (-X, -Z, Y), the project's measured FBX mapping.
  Globe_W, Globe_E   unit sphere about the origin, in the Earth-axis frame (Y = north pole), turned so that the holder's
                     tilt (90 - latitude about X) puts the focus on top. Two halves, one 2048 texture each.
  L1, L2             spherical caps, radius 1 (unit = the Earth's radius), origin at the focus (the sphere's top).
  L3 .. L6           the same, in METRES (the holder is scaled 1 / Earth radius).
  Blocks_DC, Blocks_Other   buildings over 1,500 m2 from OpenStreetMap, in metres, heights x 2 so they read from the
                     seats. Unlit: roof, sunlit wall and shaded wall are three flat tones (no lights needed).
Run: blender -b --factory-startup --python tools/blender/ashburn_zoom.py
"""
import bpy, bmesh, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()
D = json.load(open(os.path.join(C.REPO, "tools", "geo", "ashburn_data.json")))
LAT, LON = math.radians(D["focus"]["lat"]), math.radians(D["focus"]["lon"])
R_M = D["earthRadiusKm"] * 1000.0
H_SCALE = 2.0                      # building heights exaggerated
# above the globe, which is still drawn under these two (its facets dip 0.002 below the true sphere). Kept small: the lift
# grows with the zoom (x the globe's radius), 1.2 m for each by the time it is switched off (radius 800 and 4,000 m)
LIFT = {"L1": 0.0015, "L2": 0.0003}
GRID = {"L1": 48, "L2": 24, "L3": 12, "L4": 6, "L5": 4, "L6": 2}
SUN = Vector((-0.55, 0.0, -0.35)).normalized()   # light from the south-west (Unity X east, Z north): shades the N and E walls

R = C.root("ashburn_zoom")


def B(X, Y, Z): return Vector((-X, -Z, Y))      # Unity -> Blender


def new_part(name, mats):
    me = bpy.data.meshes.new(name)
    for m in mats: me.materials.append(C.mat(m))
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.parent = R
    o["keep_uv"] = True
    return o, me


def outward(bm, centre_fn):
    """Flip any face whose normal points toward centre_fn(face centre) instead of away."""
    for f in bm.faces:
        f.normal_update()
        if f.normal.dot(centre_fn(f.calc_center_median())) < 0: f.normal_flip()


# ------------------------------------------------------------------ the globe (Earth-axis frame, focus-aligned)
def ecef(lat, lon): return Vector((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)))
E = Vector((-math.sin(LON), math.cos(LON), 0)); U = ecef(LAT, LON); N = U.cross(E)          # east, up, north at the focus
TILT = math.pi / 2 - LAT                                                                    # the holder's X rotation
ct, st = math.cos(TILT), math.sin(TILT)


def globe_point(lat, lon):
    v = ecef(lat, lon)
    X, Y, Z = v.dot(E), v.dot(U), v.dot(N)                  # focus frame: the focus is (0, 1, 0)
    return B(X, Y * ct + Z * st, -Y * st + Z * ct)          # undo the holder's tilt: Unity Rx(TILT) takes +Y to (0, cos, sin)


def globe_half(name, mat, lon0, lon1):
    o, me = new_part(name, [mat])
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    NU, NV = 48, 48; eps = 0.5 / 2048
    vs = [[bm.verts.new(globe_point(math.radians(-90 + 180 * j / NV), math.radians(lon0 + (lon1 - lon0) * i / NU))) for i in range(NU + 1)] for j in range(NV + 1)]
    uv = {}
    for j in range(NV + 1):
        for i in range(NU + 1): uv[vs[j][i]] = (eps + (1 - 2 * eps) * i / NU, eps + (1 - 2 * eps) * j / NV)
    for j in range(NV):
        for i in range(NU):
            quad = [vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]]
            if len({tuple(round(c, 9) for c in v.co) for v in quad}) < 3: continue
            try: f = bm.faces.new(quad)
            except ValueError: continue
            for l in f.loops: l[uvl].uv = uv[l.vert]
    outward(bm, lambda c: c)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    return o


globe_half("Globe_W", "TK_AshGlobeW", -180, 0)
globe_half("Globe_E", "TK_AshGlobeE", 0, 180)


# ------------------------------------------------------------------ map layers (azimuthal equidistant about the focus)
def ground(x, y, radius, lift=0.0):
    """(east, north) along great circles from the focus -> Unity point, in units of `radius`' unit; origin = the focus."""
    d = math.hypot(x, y) / radius
    if d < 1e-12: return (0.0, lift, 0.0)
    b = math.atan2(x, y); r = radius + lift
    return (r * math.sin(d) * math.sin(b), r * math.cos(d) - radius, r * math.sin(d) * math.cos(b))


def layer(spec):
    name = spec["name"]; n = GRID[name]
    metres = name not in LIFT
    radius = R_M if metres else 1.0
    half = spec["km"] * 1000.0 / 2 / (1.0 if metres else R_M)
    lift = LIFT.get(name, 0.0)
    o, me = new_part(name, ["TK_Ash" + name])
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    vs = [[bm.verts.new(B(*ground(-half + 2 * half * i / n, -half + 2 * half * j / n, radius, lift))) for i in range(n + 1)] for j in range(n + 1)]
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): l[uvl].uv = (ii / n, jj / n)   # v = 1 at north
    up = B(0, 1, 0)
    for f in bm.faces:
        f.normal_update()
        if f.normal.dot(up) < 0: f.normal_flip()
        f.smooth = True
    bm.to_mesh(me); bm.free()
    return o


for sp in D["layers"]: layer(sp)


# ------------------------------------------------------------------ buildings
def blocks(name, items, mats):
    o, me = new_part(name, mats)
    bm = bmesh.new()
    for b in items:
        pts = b["pts"]; h = b["h"] * H_SCALE
        if len(pts) < 3: continue
        base = [ground(x, y, R_M) for x, y in pts]
        lo = [bm.verts.new(B(*p)) for p in base]
        hi = [bm.verts.new(B(p[0], p[1] + h, p[2])) for p in base]
        try:
            roof = bm.faces.new(hi); roof.material_index = 0
        except ValueError: continue
        roof.normal_update()
        if roof.normal.dot(B(0, 1, 0)) < 0: roof.normal_flip()
        k = len(pts)
        for i in range(k):
            j = (i + 1) % k
            (x0, y0), (x1, y1) = pts[i], pts[j]
            nrm = Vector((y1 - y0, 0.0, -(x1 - x0)))                    # outward for a counter-clockwise ring (Unity X, ., Z)
            if nrm.length < 1e-6: continue
            nrm.normalize()
            try: f = bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
            except ValueError: continue
            f.material_index = 1 if nrm.dot(-SUN) > 0.05 else 2
            f.normal_update()
            if f.normal.dot(B(nrm.x, 0, nrm.z)) < 0: f.normal_flip()
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(me); bm.free()
    return o


dc = [b for b in D["buildings"] if b["dc"]]; other = [b for b in D["buildings"] if not b["dc"]]
blocks("Blocks_DC", dc, ["TK_AshDCRoof", "TK_AshDCWallLit", "TK_AshDCWallShade"])
blocks("Blocks_Other", other, ["TK_AshRoof", "TK_AshWallLit", "TK_AshWallShade"])

# ------------------------------------------------------------------ export (no box UVs, no LOD, no turntable: the parts differ in scale by 10^6)
bpy.context.view_layer.update()
objs = C._tree(R)
n = C.tris(objs)
glb = C.export("ashburn_zoom", R)
C.report("ashburn_zoom", n, glb, f"globe + 6 map layers + {len(dc)} data-centre and {len(other)} other blocks; focus {D['focus']['lat']}, {D['focus']['lon']}")
for o in objs:
    if o.type == "MESH": print(f"  {o.name:14s} {C.tris([o]):6d} tris")
