"""devices: three generic, unbranded devices side by side along X, each with its ORIGIN at its own base centre.
Phone (+X, the viewer's left): an upright 0.15 m slab, rounded corners, thin bezel, glowing screen, side keys, a rear camera island.
Laptop (centre): 0.33 m wide, lid open 110 deg, glowing screen, a recessed keyboard deck with individual keys and a trackpad.
  Child "Laptop_Lid" carries the lid with its origin on the hinge axis and identity rotation (the 20 deg tilt is in the mesh).
Headset (-X): a soft-cornered VR visor shell (glossy black front), a thin emissive accent strip, fabric face cushion, a rear head
  strap loop and an over-the-top strap. No logos, no copied product shapes.
Materials: TK_DeviceBody, TK_DeviceScreen, TK_DarkPlastic, TK_Visor, TK_Fabric."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import prop_shapes as S
from mathutils import Matrix, Vector

C.begin()
C.root("devices")
MATS = [C.mat("TK_DeviceBody"), C.mat("TK_DeviceScreen"), C.mat("TK_DarkPlastic"), C.mat("TK_Visor"), C.mat("TK_Fabric")]
BODY, SCREEN, DARK, VISOR, FABRIC = range(5)

# ------------------------------------------------------------------ Phone
def phone(bm):
    W, H, T = 0.072, 0.150, 0.0082
    pr = S.prism(bm, S.rrect(W, H, 0.0105, 5, 0.0, H / 2), -T / 2, T / 2, "Y", BODY, bevel=0.0024, bseg=2)
    bmesh.ops.inset_individual(bm, faces=[pr["front"]], thickness=0.0016, depth=-0.0003, use_even_offset=True)
    pr["front"].material_index = DARK                       # black glass border
    r2 = bmesh.ops.inset_individual(bm, faces=[pr["front"]], thickness=0.0022, depth=0.0, use_even_offset=True)
    pr["front"].material_index = SCREEN
    # front camera dot in the top border, side keys (+X edge: two volume pills; -X edge: one power pill)
    S.lathe(bm, [(0.0, T / 2 - 0.0005), (0.0016, T / 2 - 0.0005), (0.0016, T / 2 + 0.0002), (0.0, T / 2 + 0.0003)], 10, (0, 0, H - 0.0058), "Y", VISOR)
    for z, L in ((0.112, 0.016), (0.090, 0.016)):
        S.prism(bm, S.rrect(0.0035, L, 0.0017, 3, 0.0, z), W / 2 - 0.0008, W / 2 + 0.0008, "X", BODY)
    S.prism(bm, S.rrect(0.0035, 0.022, 0.0017, 3, 0.0, 0.104), -W / 2 - 0.0008, -W / 2 + 0.0008, "X", BODY)
    # rear camera island with two lenses (on the back, -Y)
    S.prism(bm, S.rrect(0.024, 0.034, 0.007, 4, 0.016, H - 0.026), -T / 2 - 0.0012, -T / 2 + 0.0005, "Y", BODY, bevel=0.0006, bseg=1)
    for z in (H - 0.017, H - 0.035):
        S.lathe(bm, [(0.0, -T / 2 - 0.0026), (0.0040, -T / 2 - 0.0024), (0.0052, -T / 2 - 0.0016), (0.0052, -T / 2 - 0.0008), (0.0, -T / 2 - 0.0008)],
                16, (0.016, 0, z), "Y", VISOR)
    S.autosmooth(bm, 38)

ph = C.part("Phone", phone, MATS)
ph.location.x = 0.42

# ------------------------------------------------------------------ Laptop (base) + Laptop_Lid (hinge origin)
LW, LD, LT = 0.330, 0.230, 0.016
HY, HZ = -LD / 2 + 0.006, LT          # hinge axis (in the laptop's space)

def laptop_base(bm):
    pr = S.prism(bm, S.rrect(LW, LD, 0.014, 4), 0.0, LT, "Z", BODY, bevel=0.003, bseg=2)
    # keyboard well: a shallow recess in the top deck
    ky0, ky1 = -0.006, 0.098          # well spans y (front edge at -LD/2 + 0.010 is the palm rest... keys toward the hinge)
    S.prism(bm, S.rrect(0.288, 0.122, 0.006, 3, 0.0, 0.005), LT - 0.0012, LT + 0.0001, "Z", DARK)
    U = 0.0192
    rows = 6
    for r in range(rows):
        y = 0.055 - r * U
        keys = [1.0] * 14 if r < 5 else [1.25, 1.0, 1.25, 5.5, 1.25, 1.0, 1.0, 1.0]
        if r == 1: keys = [1.0] * 13 + [1.5]
        if r == 2: keys = [1.5] + [1.0] * 12 + [1.0]
        if r == 3: keys = [1.75] + [1.0] * 11 + [1.75]
        if r == 4: keys = [2.25] + [1.0] * 10 + [2.25]
        if r == 0: keys = [1.0] * 14
        tot = sum(keys); u = 0.0
        h = 0.55 if r == 0 else 1.0
        for k in keys:
            x = (tot / 2 - u - k / 2) * U                 # first key on the user's left (+X)
            S.box(bm, (k * U - 0.0026, h * U - 0.0026, 0.0018), (x, y + (0.0043 if r == 0 else 0.0), LT + 0.0002), BODY, taper=0.0004)
            u += k
    # trackpad and a thin front lip notch
    S.prism(bm, S.rrect(0.110, 0.050, 0.006, 3, 0.0, -0.084), LT - 0.0003, LT + 0.0002, "Z", DARK)
    S.autosmooth(bm, 38)

lap = C.part("Laptop", laptop_base, MATS)

def laptop_lid(bm):
    LH, LL = 0.220, 0.0055
    pr = S.prism(bm, S.rrect(LW, LH, 0.012, 4, 0.0, LH / 2 + 0.002), -LL, 0.0, "Y", BODY, bevel=0.002, bseg=2)
    bmesh.ops.inset_individual(bm, faces=[pr["front"]], thickness=0.004, depth=-0.0002, use_even_offset=True)
    pr["front"].material_index = DARK
    bmesh.ops.inset_individual(bm, faces=[pr["front"]], thickness=0.0055, depth=0.0, use_even_offset=True)
    pr["front"].material_index = SCREEN
    S.lathe(bm, [(0.0, 0.0002), (0.0013, 0.0002), (0.0, 0.0006)], 8, (0, 0, LH - 0.006), "Y", VISOR)   # camera
    # hinge barrel
    S.tube(bm, (-LW / 2 + 0.03, -0.003, 0.0), (LW / 2 - 0.03, -0.003, 0.0), 0.0055, 12, BODY)
    S.xform(bm, list(bm.verts), Matrix.Rotation(math.radians(20.0), 4, "X"))   # open to 110 deg
    S.autosmooth(bm, 38)

lid = C.part("Laptop_Lid", laptop_lid, MATS, parent=lap)
lid.location = (0.0, HY, HZ)

# ------------------------------------------------------------------ Headset
A, B, Cz = 0.094, 0.046, 0.050        # shell half extents (x, y, z)
ZC = Cz + 0.0                         # shell centre height (bottom at z 0)

def headset(bm):
    e1, e2 = 0.35, 0.35               # superellipsoid exponents (soft box)
    nlat, nlon = 12, 28
    def sp(c, e): return math.copysign(abs(c) ** e, c)
    rows = []
    for i in range(nlat + 1):
        u = -math.pi / 2 + math.pi * i / nlat
        if i in (0, nlat):
            rows.append([bm.verts.new((0, 0, ZC + sp(math.sin(u), e1) * Cz))]); continue
        row = []
        for j in range(nlon):
            v = 2 * math.pi * j / nlon
            x = A * sp(math.cos(u), e1) * sp(math.cos(v), e2)
            y = B * sp(math.cos(u), e1) * sp(math.sin(v), e2)
            z = ZC + Cz * sp(math.sin(u), e1)
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    faces = []
    for a, b in zip(rows, rows[1:]):
        for j in range(nlon):
            j2 = (j + 1) % nlon
            if len(a) == 1: faces.append(bm.faces.new((a[0], b[j2], b[j])))
            elif len(b) == 1: faces.append(bm.faces.new((a[j], a[j2], b[0])))
            else: faces.append(bm.faces.new((a[j], a[j2], b[j2], b[j])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.normal_update(); c = f.calc_center_median()
        f.material_index = BODY
        if f.normal.y > 0.45:
            f.material_index = VISOR
    # accent strip: one latitude band of front faces, emissive
    band_z = ZC - Cz * 0.62
    for f in faces:
        c = f.calc_center_median()
        if f.normal.y > 0.25 and abs(c.z - band_z) < 0.0045 and abs(c.x) < A * 0.85:
            f.material_index = SCREEN
    # face cushion (fabric) at the back
    S.ring(bm, S.rrect(0.172, 0.088, 0.034, 5, 0.0, ZC - 0.002), S.rrect(0.120, 0.050, 0.022, 5, 0.0, ZC - 0.002),
           -B - 0.024, -B + 0.012, "Y", FABRIC)
    # nose relief: a soft dark wedge under the cushion opening
    S.prism(bm, S.gothic(0.018, ZC - 0.046, ZC - 0.030, 0.018, 4), -B - 0.020, -B + 0.006, "Y", DARK)
    # rear head-strap loop (an elliptical band) and an over-the-top strap
    def ell(ax, ay, cy, n=36):
        return [(ax * math.cos(2 * math.pi * k / n), cy + ay * math.sin(2 * math.pi * k / n)) for k in range(n)]
    S.ring(bm, ell(A + 0.006, 0.130, -0.120), ell(A, 0.124, -0.120), ZC - 0.016, ZC + 0.016, "Z", FABRIC)
    n = 14
    t0 = math.radians(30.0); ang = [t0 + (math.pi - t0) * k / n for k in range(n + 1)]
    outer = [(-0.130 + 0.120 * math.cos(t), ZC + 0.098 * math.sin(t)) for t in ang]
    inner = [(-0.130 + 0.114 * math.cos(t), ZC + 0.092 * math.sin(t)) for t in ang]
    S.prism(bm, outer + inner[::-1], -0.013, 0.013, "X", FABRIC)
    # side strap anchors (body)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (A - 0.004), sx * (A + 0.009)))
        S.prism(bm, S.rrect(0.040, 0.030, 0.010, 3, -0.010, ZC), x0, x1, "X", BODY)
    S.autosmooth(bm, 40)

hs = C.part("Headset", headset, MATS)
hs.location.x = -0.45

# keep only the material slots each device uses (rebuild the lists; indices are remapped)
for o in (ph, lap, lid, hs):
    me = o.data
    used = sorted({p.material_index for p in me.polygons})
    remap = {old: new for new, old in enumerate(used)}
    keep = [me.materials[i] for i in used]
    idx = [remap[p.material_index] for p in me.polygons]
    me.materials.clear()
    for m in keep: me.materials.append(m)
    for p, i in zip(me.polygons, idx): p.material_index = i

C.finish("devices", note="Phone 0.072 x 0.15 m upright, Laptop 0.33 m open 110 deg (child Laptop_Lid, hinge origin), Headset 0.19 m visor")
