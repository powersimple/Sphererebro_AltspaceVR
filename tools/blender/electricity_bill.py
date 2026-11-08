"""electricity_bill: a 7 m wide x 60 m long paper strip hanging DOWN from a roll.
ORIGIN AT THE TOP CENTRE (exception to the base-centre rule: the engine unrolls it by scaling Z from the top).
Parts: Roll (paper roll + TK_StampMetal end caps), Strip (double-sided paper, curled edges, gentle ripple),
       Perforations (tractor-feed holes along both edges), Numbers (TK_BillInk panel down the middle-right,
       ruled lines / columns / header bar only: no words, no numbers), NumbersAnchor (empty, bottom of the numbers
       column on its front surface).
Generates talk/gen/bill_numbers.png.
"""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import numpy as np
from mathutils import Vector

C.begin()
C.MATS["TK_PerfHole"] = {"tex": None, "tint": [0.10, 0.10, 0.11], "metal": 0, "rough": 0.9, "tile": 0}
# Paper006 (TK_Paper) is kraft-brown; a bill is white: generated off-white fibre paper, UVs set here (tile 0, repeats)
C.MATS["TK_BillPaper"] = {"tex": None, "emitTex": "bill_paper.png", "tint": [1, 1, 1], "metal": 0, "rough": 0.85, "tile": 0}
PAPER_TILE = 3.5   # metres per repeat of bill_paper.png

WID, LEN = 7.0, 60.0
RR = 0.95                     # paper roll radius
RC = Vector((0, 0, -1.08))    # roll centre (caps' top at z = 0)
TOP = RC.z                    # strip leaves the roll at the front tangent, at this height
NX, NZ = 10, 40               # strip grid

# numbers column (viewer's middle-right = -X side)
NUM_X0, NUM_X1 = -3.0, 0.6
NUM_Z0, NUM_Z1 = TOP - 2.2, TOP - LEN + 0.8


def surf(x, z):
    """Strip surface y at (x, z): front tangent of the roll, a gentle ripple, edges curling back."""
    t = (TOP - z) / LEN
    e = abs(x) / (WID / 2)
    curl = -0.32 * max(0.0, (e - 0.72) / 0.28) ** 2
    ripple = 0.10 * math.sin(t * 9.5 + 0.6) * min(1.0, t * 6)
    sway = 0.18 * t * t       # hangs slightly forward toward the bottom
    return RR + ripple + sway + curl


# ------------------------------------------------------------------ bill_numbers.png (lines / columns / header only)
IW, IH = 256, 2048
img = np.ones((IH, IW, 3), np.float32) * np.array([0.95, 0.94, 0.9], np.float32)
ky = IH / (NUM_Z0 - NUM_Z1)                   # px per metre down the column
hdr = int(1.6 * ky)
img[: hdr] = (0.16, 0.22, 0.3)                # header bar
img[hdr: hdr + 3] = (0.6, 0.45, 0.2)          # thin accent rule
img[hdr + 8: hdr + int(0.55 * ky)] = (0.86, 0.87, 0.88)   # column-heading band (blank)
row = 0.62
y = hdr + int(0.55 * ky)
k = 0
while y < IH - 40:
    nxt = int(y + row * ky)
    if k % 2 == 1: img[y:nxt] = (0.92, 0.925, 0.92)   # banded rows
    img[nxt - 1: nxt] = (0.72, 0.76, 0.8)             # ruled line
    y = nxt; k += 1
for cx in (0.42, 0.62, 0.8):                           # column rules
    c = int(cx * IW); img[hdr:, c: c + 1] = (0.6, 0.64, 0.68)
img[IH - 40: IH - 36] = (0.16, 0.22, 0.3)              # double total rule
img[IH - 30: IH - 26] = (0.16, 0.22, 0.3)
img[IH - 26:] = (0.95, 0.94, 0.9)
img[:, :2] = (0.55, 0.58, 0.62); img[:, -2:] = (0.55, 0.58, 0.62)
C.save_png("bill_numbers.png", img)

# bill_paper.png: tileable off-white paper with soft fibre mottling (wrap-safe: built from periodic noise)
rs = np.random.RandomState(4)
PN = 256
acc = np.zeros((PN, PN), np.float32)
for octave, amp in ((4, 0.5), (8, 0.3), (32, 0.15), (128, 0.08)):
    f = rs.randn(octave, octave).astype(np.float32)
    rep = np.kron(f, np.ones((PN // octave, PN // octave), np.float32))
    for _ in range(2):
        rep = (rep + np.roll(rep, 1, 0) + np.roll(rep, -1, 0) + np.roll(rep, 1, 1) + np.roll(rep, -1, 1)) / 5
    acc += rep * amp
fib = (rs.rand(PN, PN) < 0.004).astype(np.float32)
fib = np.maximum(fib, np.roll(fib, 1, 1) * 0.7)
acc = acc / (np.abs(acc).max() + 1e-6)
paper = np.array([0.93, 0.925, 0.9], np.float32) + acc[..., None] * 0.025 - fib[..., None] * 0.06
C.save_png("bill_paper.png", np.clip(paper, 0, 1).astype(np.float32))

R = C.root("electricity_bill")


# ------------------------------------------------------------------ Roll
def roll(bm):
    C.bm_cyl(bm, RR, WID + 0.1, tuple(RC), 28, mat_index=0, axis="X")
    for sx in (-1, 1):
        C.bm_cyl(bm, RR + 0.13, 0.14, (sx * (WID / 2 + 0.12), RC.y, RC.z), 28, mat_index=1, axis="X")
        C.bm_cyl(bm, 0.38, 0.3, (sx * (WID / 2 + 0.33), RC.y, RC.z), 14, mat_index=1, axis="X")
        C.bm_cyl(bm, 0.2, 0.25, (sx * (WID / 2 + 0.6), RC.y, RC.z), 10, mat_index=1, axis="X")
o = C.part("Roll", roll, [C.mat("TK_BillPaper"), C.mat("TK_StampMetal")])
for p in o.data.polygons:
    if p.material_index == 0 and abs(p.normal.x) < 0.5: p.use_smooth = True
me = o.data; me.uv_layers.new(name="UVMap")
for p in me.polygons:
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        ang = math.atan2(co.z - RC.z, co.y - RC.y)
        me.uv_layers.active.data[li].uv = ((WID / 2 - co.x) / PAPER_TILE, ang * RR / PAPER_TILE)
o["keep_uv"] = True


# ------------------------------------------------------------------ Strip (double-sided)
def xs():
    # denser columns near the edges for the curl
    u = [i / NX for i in range(NX + 1)]
    return [WID / 2 * math.copysign(abs(2 * a - 1) ** 0.8, 2 * a - 1) for a in u]


def zs():
    return [TOP - LEN * (j / NZ) for j in range(NZ + 1)]


def strip(bm):
    X, Z = xs(), zs()
    for side in (0, 1):
        g = [[bm.verts.new((x, surf(x, z) - side * 0.012, z)) for x in X] for z in Z]
        for j in range(NZ):
            for i in range(NX):
                q = (g[j][i], g[j + 1][i], g[j + 1][i + 1], g[j][i + 1])
                bm.faces.new(q if side == 0 else tuple(reversed(q)))
o = C.part("Strip", strip, [C.mat("TK_BillPaper")], smooth=True)
# make sure the front faces point +Y
bmx = bmesh.new(); bmx.from_mesh(o.data)
for f in bmx.faces:
    f.normal_update()
bmx.to_mesh(o.data); bmx.free()
fr = [p for p in o.data.polygons]
front_ok = sum(1 for p in fr if p.normal.y > 0) >= len(fr) // 2 - 2
print("[bill] strip normals ok:", front_ok)
me = o.data; me.uv_layers.new(name="UVMap")
for p in me.polygons:
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        me.uv_layers.active.data[li].uv = ((WID / 2 - co.x) / PAPER_TILE, (co.z - TOP) / PAPER_TILE)
o["keep_uv"] = True


# ------------------------------------------------------------------ Perforations (tractor-feed holes, both edges)
def perfs(bm):
    pitch = 0.75; r = 0.1
    n = int((LEN - 0.6) / pitch)
    for sx in (-1, 1):
        x = sx * (WID / 2 - 0.28)
        for k in range(n):
            z = TOP - 0.4 - k * pitch
            y = surf(x, z) + 0.008
            vs = [bm.verts.new((x + r * math.cos(a * math.pi / 3), surf(x + r * math.cos(a * math.pi / 3), z) + 0.008,
                                z + r * math.sin(a * math.pi / 3))) for a in range(6)]
            bm.faces.new(vs if True else vs)
o = C.part("Perforations", perfs, [C.mat("TK_PerfHole")])
bmx = bmesh.new(); bmx.from_mesh(o.data)
for f in bmx.faces:
    f.normal_update()
    if f.normal.y < 0: f.normal_flip()
bmx.to_mesh(o.data); bmx.free()


# ------------------------------------------------------------------ Numbers panel (follows the strip surface)
def numbers(bm):
    cols = 3; rows = NZ
    X = [NUM_X0 + (NUM_X1 - NUM_X0) * i / cols for i in range(cols + 1)]
    Z = [NUM_Z0 + (NUM_Z1 - NUM_Z0) * j / rows for j in range(rows + 1)]
    g = [[bm.verts.new((x, surf(x, z) + 0.006, z)) for x in X] for z in Z]
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((g[j][i], g[j + 1][i], g[j + 1][i + 1], g[j][i + 1]))
o = C.part("Numbers", numbers, [C.mat("TK_BillInk")])
bmx = bmesh.new(); bmx.from_mesh(o.data)
for f in bmx.faces:
    f.normal_update()
    if f.normal.y < 0: f.normal_flip()
bmx.to_mesh(o.data); bmx.free()
C.planar_uv(o, "Y"); o["keep_uv"] = True

a = bpy.data.objects.new("NumbersAnchor", None)
bpy.context.scene.collection.objects.link(a)
a.parent = R
xa = (NUM_X0 + NUM_X1) / 2
a.location = (xa, surf(xa, NUM_Z1) + 0.008, NUM_Z1)
a.empty_display_size = 0.5

C.finish("electricity_bill", R, note="origin at top centre; strip hangs to z -61; Numbers panel x -3.0..0.6")
