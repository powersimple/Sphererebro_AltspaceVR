"""curved_screen: a curved video screen 40 m wide (arc length) x 22 m tall on a 30 m radius, concave toward +Y (the
viewer). Origin at the base centre (bottom edge of the screen at z = 0, centre of the arc at x = 0, y = 0).
Arc centre is at (0, +30, z). Edges come forward to y = +6.4.
Parts: Screen (TK_ScreenVideo, 48 x 2 quads, UVs exactly 0..1: u = 0 on the viewer's left (+X), v = 0 at the bottom),
       Back (TK_ScreenBack shell 1.2 m deep with ribs), Frame (TK_RackFrame thin bezel lip over the edges).
"""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()

RAD, WID, HGT = 30.0, 40.0, 22.0
TH = WID / 2 / RAD                 # half angle (rad)
NC = 48
CEN = Vector((0, RAD, 0))


def P(theta, r, z):
    """Point on the arc of radius r about CEN; theta > 0 -> +X (viewer's left)."""
    return Vector((r * math.sin(theta), RAD - r * math.cos(theta), z))


def fix(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()


R = C.root("curved_screen")

# ------------------------------------------------------------------ Screen
me = bpy.data.meshes.new("Screen")
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
grid = []
for j in range(3):
    z = HGT * j / 2
    grid.append([bm.verts.new(P(TH - 2 * TH * i / NC, RAD, z)) for i in range(NC + 1)])   # i = 0 at +X (u = 0)
for j in range(2):
    for i in range(NC):
        # i -> i+1 runs from +X to -X; with z up this winding gives a normal toward the arc centre (+Y)
        vs = (grid[j][i + 1], grid[j][i], grid[j + 1][i], grid[j + 1][i + 1])
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.dot(CEN - f.calc_center_median()) < 0:
            f.normal_flip()
        for l in f.loops:
            ii = grid[j].index(l.vert) if l.vert in grid[j] else grid[j + 1].index(l.vert)
            jj = j if l.vert in grid[j] else j + 1
            l[uvl].uv = (ii / NC, jj / 2)
bm.to_mesh(me); bm.free()
me.materials.append(C.mat("TK_ScreenVideo"))
scr = bpy.data.objects.new("Screen", me); bpy.context.scene.collection.objects.link(scr); scr.parent = R
scr["keep_uv"] = True
nrm_ok = all(p.normal.y > 0 or abs(p.normal.y) < 0.5 for p in me.polygons)
print("[screen] normals toward viewer:", nrm_ok, " sample:", tuple(round(c, 2) for c in me.polygons[NC // 2].normal))

# ------------------------------------------------------------------ Back shell (behind the screen) + ribs
D = 1.2; NB = 24; ZT = HGT + 0.35
def back(bm):
    r0, r1 = RAD + 0.04, RAD + D
    cols = [TH * 1.012 - 2 * TH * 1.012 * i / NB for i in range(NB + 1)]
    def ring(r, z): return [bm.verts.new(P(t, r, z)) for t in cols]
    a0, a1, b0, b1 = ring(r0, -0.0), ring(r0, ZT), ring(r1, 0.0), ring(r1, ZT - 0.25)
    for i in range(NB):
        bm.faces.new((b0[i], b0[i + 1], b1[i + 1], b1[i]))       # back skin
        bm.faces.new((a1[i], a1[i + 1], b1[i + 1], b1[i]))       # top (slight slope)
        bm.faces.new((a0[i], a0[i + 1], b0[i + 1], b0[i]))       # bottom
        bm.faces.new((a0[i], a0[i + 1], a1[i + 1], a1[i]))       # front (behind the screen)
    for k in (0, NB):
        bm.faces.new((a0[k], b0[k], b1[k], a1[k]))               # ends
    # vertical ribs + a horizontal stiffener on the back
    for k in range(1, 8):
        t = TH - 2 * TH * k / 8
        p = P(t, r1 + 0.3, 0); n = (P(t, r1 + 0.3, 0) - P(t, r1, 0)).normalized()
        vs = C.bm_box(bm, (0.5, 0.6, ZT - 0.6), (p.x, p.y, (ZT - 0.6) / 2))
        bmesh.ops.rotate(bm, verts=vs, cent=(p.x, p.y, 0), matrix=__import__("mathutils").Matrix.Rotation(-t, 3, "Z"))
o = C.part("Back", back, [C.mat("TK_ScreenBack")]); fix(o)

# ------------------------------------------------------------------ Frame (bezel lip over the screen edges)
def frame(bm):
    lip = 0.28; dep = 0.18
    rf, rb = RAD - dep, RAD + 0.05
    cols = [TH + 0.012 - 2 * (TH + 0.012) * i / NC for i in range(NC + 1)]
    def band(z0, z1):
        A = [[bm.verts.new(P(t, r, z)) for t in cols] for (r, z) in ((rb, z0), (rf, z0), (rf, z1), (rb, z1))]
        for i in range(NC):
            for s in range(3):
                bm.faces.new((A[s][i], A[s][i + 1], A[s + 1][i + 1], A[s + 1][i]))
    band(0.0, lip)                  # bottom lip
    band(HGT - lip, HGT + 0.35)     # top lip
    for sgn in (1, -1):             # side stiles: thin boxes rotated to the arc tangent
        t = sgn * (TH + 0.004)
        p = P(t, (rf + rb) / 2, 0)
        vs = C.bm_box(bm, (lip * 1.3, dep + 0.05, HGT + 0.35), (p.x, p.y, (HGT + 0.35) / 2))
        bmesh.ops.rotate(bm, verts=vs, cent=(p.x, p.y, 0), matrix=__import__("mathutils").Matrix.Rotation(-t, 3, "Z"))
o = C.part("Frame", frame, [C.mat("TK_RackFrame")]); fix(o)

C.finish("curved_screen", R, note="40 x 22 m arc, r 30, concave to +Y; Screen UV 0..1 (u=0 at +X)")
