"""tv_midcentury: a 1950s wooden console television at real size (1.05 m tall, 0.78 wide, 0.50 deep) on four splayed tapered
legs with brass ferrules. Walnut cabinet with an overhanging lid, a gold mask around a bulging rounded-corner CRT, a pill-shaped
brass control escutcheon with four bakelite knobs, and a full-width cloth speaker grille behind vertical brass rods.
Parts: Cabinet (TK_WoodTV, TK_Brass, TK_DarkPlastic back vents), Screen (TK_TVScreen, UVs 0..1, u = 0 at the viewer's left), Grille (TK_SpeakerCloth,
TK_Brass), Knobs (TK_Bakelite, TK_Brass), Legs (TK_WoodTV, TK_Brass). Origin at the base centre, front +Y.
Generates talk/gen/tv_glow.png."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import prop_shapes as S
import numpy as np
from mathutils import Matrix, Vector

C.begin()

# ------------------------------------------------------------------ tv_glow.png: soft blue-grey glow, faint scanlines, vignette
def glow_png():
    H, W = 768, 1024
    X, Y = S.grid(H, W, W / H)
    cx, cy = W / H / 2, 0.5
    rng = np.random.default_rng(11)
    r2 = ((X - cx) / (W / H * 0.5)) ** 2 + ((Y - cy) / 0.5) ** 2
    core = np.exp(-r2 * 1.15)
    lo = np.array([0.10, 0.12, 0.15], np.float32); mid = np.array([0.42, 0.49, 0.56], np.float32); hi = np.array([0.80, 0.86, 0.92], np.float32)
    t = core[..., None]
    img = lo * (1 - t) + mid * t
    img = img + (hi - mid) * (np.clip(core - 0.55, 0, 1) / 0.45)[..., None] ** 1.5
    # slow luminous mottling (phosphor), a faint brighter roll band
    img *= (0.94 + 0.12 * S.fbm(H, W, 3, 4, rng, 4))[..., None]
    img *= (1.0 + 0.05 * np.exp(-((Y - 0.36) / 0.06) ** 2))[..., None]
    # scanlines: every 3 px a slightly darker line
    rows = (np.arange(H) % 3 == 2).astype(np.float32)[:, None, None]
    img *= 1 - rows * 0.10
    # rounded-tube vignette
    d = S.sd_rrect(X, Y, cx, cy, W / H / 2, 0.5, 0.12)
    img *= np.clip(-d / 0.10, 0, 1)[..., None] ** 0.6 * 0.85 + 0.15
    img += (rng.random((H, W, 1)).astype(np.float32) - 0.5) * 0.03
    C.save_png("tv_glow.png", np.clip(img, 0, 1).astype(np.float32))

glow_png()

C.root("tv_midcentury")
FY = 0.240                    # cabinet front face
SCX, SCZ, SW, SH, SR = 0.070, 0.800, 0.480, 0.360, 0.052   # screen opening
GZ = 0.470                    # grille centre
KX = -0.278                   # control column

def cabinet(bm):
    Wd, B = 0, 1
    S.prism(bm, S.rrect(0.750, 0.480, 0.040, 5), 0.300, 1.020, "Z", Wd, bevel=0.010, bseg=2)
    S.prism(bm, S.rrect(0.780, 0.505, 0.050, 5, 0.0, 0.004), 1.012, 1.050, "Z", Wd, bevel=0.012, bseg=3)   # lid
    S.prism(bm, S.rrect(0.722, 0.455, 0.030, 4), 0.268, 0.306, "Z", Wd, bevel=0.006, bseg=2)               # apron
    # gold mask around the tube: sloped inner lip
    S.ring(bm, S.rrect(0.565, 0.445, 0.080, 6, SCX, SCZ), S.rrect(SW, SH, SR, 6, SCX, SCZ), FY - 0.004, FY + 0.016, "Y", B, d1_in=FY + 0.004)
    # a thin wooden bead framing the mask
    S.ring(bm, S.rrect(0.595, 0.475, 0.092, 6, SCX, SCZ), S.rrect(0.565, 0.445, 0.080, 6, SCX, SCZ), FY - 0.004, FY + 0.012, "Y", Wd)
    # control escutcheon (a brass pill)
    S.prism(bm, S.rrect(0.094, 0.330, 0.046, 6, KX, 0.800), FY - 0.003, FY + 0.006, "Y", B, bevel=0.0025, bseg=2, bevel_back=False)
    # brass trim bead along the bottom of the front and down the corners of the lid
    S.tube(bm, (-0.352, FY + 0.002, 0.330), (0.352, FY + 0.002, 0.330), 0.0045, 8, B)
    S.prism(bm, S.rrect(0.784, 0.509, 0.052, 5, 0.0, 0.004), 1.008, 1.013, "Z", B)
    # back: an inset hardboard panel with rows of vent slots
    S.prism(bm, S.rrect(0.640, 0.600, 0.020, 3, 0.0, 0.680), -FY - 0.006, -FY + 0.004, "Y", Wd, bevel=0.003, bseg=1)
    for row in range(4):
        for col in range(5):
            S.prism(bm, S.rrect(0.090, 0.014, 0.007, 3, (col - 2) * 0.115, 0.86 + row * 0.04), -FY - 0.0072, -FY - 0.004, "Y", 2)
    S.autosmooth(bm, 38)
C.part("Cabinet", cabinet, [C.mat("TK_WoodTV"), C.mat("TK_Brass"), C.mat("TK_DarkPlastic")])

# ------------------------------------------------------------------ screen: a bulging rounded-corner CRT face
def screen(bm):
    nx, nz = 20, 15
    hw, hh, r = SW / 2, SH / 2, SR
    V = {}
    for i in range(nx + 1):
        for j in range(nz + 1):
            x = -hw + 2 * hw * i / nx; z = -hh + 2 * hh * j / nz
            ax, az = abs(x) - (hw - r), abs(z) - (hh - r)
            if ax > 0 and az > 0:
                L = math.hypot(ax, az)
                k = r / L if L > r else 1.0
                x = math.copysign(hw - r + ax * k, x); z = math.copysign(hh - r + az * k, z)
            xn, zn = x / hw, z / hh
            y = FY + 0.002 + 0.024 * (1 - xn * xn) * (1 - zn * zn)
            V[i, j] = bm.verts.new((SCX + x, y, SCZ + z))
    for i in range(nx):
        for j in range(nz):
            f = bm.faces.new((V[i, j], V[i + 1, j], V[i + 1, j + 1], V[i, j + 1]))
            f.normal_update()
            if f.normal.y < 0: f.normal_flip()
    for f in bm.faces: f.smooth = True
sc = C.part("Screen", screen, [C.mat("TK_TVScreen")])
C.planar_uv(sc, "Y"); sc["keep_uv"] = True

# ------------------------------------------------------------------ grille: cloth behind a brass frame and vertical rods
def grille(bm):
    Cl, B = 0, 1
    S.prism(bm, S.rrect(0.640, 0.215, 0.022, 4, 0.0, GZ), FY - 0.004, FY + 0.001, "Y", Cl)
    S.ring(bm, S.rrect(0.672, 0.247, 0.036, 5, 0.0, GZ), S.rrect(0.640, 0.215, 0.022, 5, 0.0, GZ), FY - 0.003, FY + 0.012, "Y", B, d1_in=FY + 0.006)
    n = 17
    for i in range(n):
        x = -0.300 + 0.600 * i / (n - 1)
        S.tube(bm, (x, FY + 0.0075, GZ - 0.108), (x, FY + 0.0075, GZ + 0.108), 0.0032, 6, B)
    # a horizontal tie bar through the rods
    S.tube(bm, (-0.318, FY + 0.0105, GZ), (0.318, FY + 0.0105, GZ), 0.0042, 8, B)
    S.autosmooth(bm, 50)
C.part("Grille", grille, [C.mat("TK_SpeakerCloth"), C.mat("TK_Brass")])

# ------------------------------------------------------------------ knobs
def knobs(bm):
    for (x, z, s) in ((KX, 0.890, 1.0), (KX, 0.780, 0.80), (KX - 0.021, 0.690, 0.46), (KX + 0.021, 0.690, 0.46)):
        y = FY + 0.005
        R0 = 0.030 * s
        prof = [(0.0, y - 0.002), (R0 * 0.92, y - 0.002), (R0, y + 0.004 * s), (R0, y + 0.016 * s), (R0 * 0.97, y + 0.020 * s),
                (R0 * 0.62, y + 0.024 * s), (R0 * 0.55, y + 0.034 * s), (R0 * 0.48, y + 0.037 * s), (0.0, y + 0.038 * s)]
        S.lathe(bm, prof, 28 if s > 0.6 else 16, (x, 0, z), "Y", 0,
                knurl=lambda ri, k: (1.0 if k % 2 else 0.92) if ri in (2, 3) else 1.0)
        yc = y + 0.0365 * s
        S.lathe(bm, [(0.0, yc - 0.001), (R0 * 0.42, yc - 0.001), (R0 * 0.44, yc + 0.0015), (R0 * 0.28, yc + 0.003), (0.0, yc + 0.0035)],
                16, (x, 0, z), "Y", 1)
        # brass skirt ring behind the big knobs
        if s > 0.6:
            S.lathe(bm, [(R0 * 1.05, y - 0.001), (R0 * 1.18, y - 0.001), (R0 * 1.18, y + 0.0015), (R0 * 1.05, y + 0.0015)], 28, (x, 0, z), "Y", 1)
    S.autosmooth(bm, 40)
C.part("Knobs", knobs, [C.mat("TK_Bakelite"), C.mat("TK_Brass")])

# ------------------------------------------------------------------ legs: tapered, splayed, brass ferrules
def legs(bm):
    top_z = 0.282; a = math.radians(8.0)
    L = top_z / math.cos(a)
    for sx in (-1, 1):
        for sy in (-1, 1):
            top = Vector((sx * 0.300, sy * 0.170, top_z))
            d = Vector((sx * 0.6, sy * 0.8, 0)).normalized()
            v = Vector((d.x * math.sin(a), d.y * math.sin(a), -math.cos(a)))
            Rm = Vector((0, 0, -1)).rotation_difference(v).to_matrix().to_4x4()
            M = Matrix.Translation(top) @ Rm
            wood = S.lathe(bm, [(0.0, 0.0), (0.024, 0.0), (0.024, -0.012), (0.021, -0.020), (0.0175, -L * 0.55), (0.0135, -(L - 0.045)),
                                (0.0, -(L - 0.045))], 12, (0, 0, 0), "Z", 0)
            S.xform(bm, wood["verts"], M)
            fer = S.lathe(bm, [(0.0, -(L - 0.048)), (0.0142, -(L - 0.048)), (0.0142, -(L - 0.044)), (0.0130, -(L - 0.040)),
                               (0.0118, -(L - 0.004)), (0.0105, -L), (0.0, -L)], 12, (0, 0, 0), "Z", 1)
            S.xform(bm, fer["verts"], M)
            # mounting plate under the apron
            S.prism(bm, S.rrect(0.07, 0.07, 0.012, 2, sx * 0.300, sy * 0.170), 0.262, 0.270, "Z", 1)
    S.autosmooth(bm, 40)
C.part("Legs", legs, [C.mat("TK_WoodTV"), C.mat("TK_Brass")])

C.finish("tv_midcentury", note="1950s console TV, real size 0.78 x 0.51 x 1.05 m; parts Cabinet, Screen, Grille, Knobs, Legs")
