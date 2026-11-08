"""water_tank: a tall transparent storage tank, 8 m diameter x 24 m tall.
Parts: "Glass" (TK_TankGlass shell), "Rings" (TK_SteelRing: plinth ring, hoop bands, top rim, vertical stiffeners,
roof cap ring), "Water" (TK_Water closed cylinder z 0.3..23.5, ORIGIN AT ITS BOTTOM: the engine fills it by scaling Z 0->1;
its top cap is the water surface). Origin at the base centre, front +Y."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

C.begin()
R = 4.0; H = 24.0; SEG = 48

C.root("water_tank")


RS = 32   # segments for the steel bands


def tube(bm, r_in, r_out, z0, z1, segs=RS, mi=0, inner=True):
    """A closed annular ring (washer extruded) from z0 to z1. inner=False skips the inner wall (bands hugging the glass)."""
    vo = []; vi = []
    for zz in (z0, z1):
        ro = [bm.verts.new((r_out * math.cos(2 * math.pi * i / segs), r_out * math.sin(2 * math.pi * i / segs), zz)) for i in range(segs)]
        ri = [bm.verts.new((r_in * math.cos(2 * math.pi * i / segs), r_in * math.sin(2 * math.pi * i / segs), zz)) for i in range(segs)]
        vo.append(ro); vi.append(ri)
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((vo[0][i], vo[0][j], vo[1][j], vo[1][i])); f.material_index = mi        # outer wall
        if inner:
            f = bm.faces.new((vi[0][j], vi[0][i], vi[1][i], vi[1][j])); f.material_index = mi    # inner wall
        f = bm.faces.new((vo[1][i], vo[1][j], vi[1][j], vi[1][i])); f.material_index = mi        # top
        f = bm.faces.new((vo[0][j], vo[0][i], vi[0][i], vi[0][j])); f.material_index = mi        # bottom


# ---- glass shell: open tube, double-sided by an inner wall a few cm in (reads as thick glass)
def glass(bm):
    tube(bm, R - 0.06, R, 0.6, H - 0.35, segs=40)


g = C.part("Glass", glass, [C.mat("TK_TankGlass")], smooth=True)
g["keep_uv"] = True
C.planar_uv(g, "Z")


# ---- steel: concrete-coloured plinth ring is steel here (TK_SteelRing only), hoops, rim, stiffeners
def rings(bm):
    tube(bm, R - 0.35, R + 0.55, 0.0, 0.6)                 # base plinth ring
    tube(bm, R - 0.02, R + 0.14, 0.6, 0.9, inner=False)    # base clamp band over the glass
    for z in (5.0, 9.6, 14.2, 18.8):                       # hoop bands
        tube(bm, R - 0.02, R + 0.16, z - 0.18, z + 0.18, inner=False)
    tube(bm, R - 0.45, R + 0.26, H - 0.5, H)               # top rim
    # vertical stiffeners (8), flat bars standing off the glass
    n = 8
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        rr = R + 0.12
        vs = C.bm_box(bm, (0.12, 0.22, H - 1.1), loc=(0, 0, 0))
        M = C.Matrix.Translation((rr * math.cos(a), rr * math.sin(a), 0.6 + (H - 1.1) / 2 - 0.05)) @ C.Matrix.Rotation(a, 4, "Z")
        bmesh.ops.transform(bm, matrix=M, verts=vs)
    # roof: shallow cone of radial ribs (6) meeting at a hub, so the top reads as a vessel, not an open pipe
    for i in range(6):
        a = 2 * math.pi * i / 6
        L = R - 0.45
        vs = C.bm_box(bm, (L, 0.12, 0.14))
        M = C.Matrix.Translation((L / 2 * math.cos(a), L / 2 * math.sin(a), H - 0.05)) @ C.Matrix.Rotation(a, 4, "Z")
        bmesh.ops.transform(bm, matrix=M, verts=vs)
    C.bm_cyl(bm, 0.45, 0.35, loc=(0, 0, H + 0.05), segs=16)  # hub
    # access ladder up the back (-Y) with a few hoops: rails + rungs
    for sx in (-0.25, 0.25):
        C.bm_box(bm, (0.05, 0.05, H - 1.0), loc=(sx, -(R + 0.55), 0.6 + (H - 1.0) / 2))
    for k in range(0, 38):
        C.bm_box(bm, (0.5, 0.035, 0.035), loc=(0, -(R + 0.55), 1.0 + k * 0.6))
    # inlet / outlet pipe stubs at the base, front
    C.bm_cyl(bm, 0.22, 1.2, loc=(1.6, R + 0.2, 0.35), segs=12, axis="Y")
    C.bm_cyl(bm, 0.3, 0.08, loc=(1.6, R + 0.8, 0.35), segs=12, axis="Y")
    C.bm_cyl(bm, 0.22, 1.2, loc=(-1.6, R + 0.2, 0.35), segs=12, axis="Y")
    C.bm_cyl(bm, 0.3, 0.08, loc=(-1.6, R + 0.8, 0.35), segs=12, axis="Y")


rg = C.part("Rings", rings, [C.mat("TK_SteelRing")])
for p in rg.data.polygons: p.use_smooth = False


# ---- water: closed cylinder; mesh from z 0 .. 23.2, object located at z 0.3 so its origin is its bottom
WZ0, WZ1 = 0.3, 23.5
def water(bm):
    C.bm_cyl(bm, R - 0.1, WZ1 - WZ0, loc=(0, 0, (WZ1 - WZ0) / 2), segs=40)


w = C.part("Water", water, [C.mat("TK_Water")])
for p in w.data.polygons: p.use_smooth = abs(p.normal.z) < 0.5
w.location = (0, 0, WZ0)
w["keep_uv"] = True
C.planar_uv(w, "Z")

C.finish("water_tank", note="Glass/Rings/Water; Water origin at its bottom (z 0.3), fill by scale Z 0..1, top cap = surface")
