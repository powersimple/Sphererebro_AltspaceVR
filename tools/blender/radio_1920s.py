"""radio_1920s: a 1920s-30s "cathedral" tabletop radio at real size (0.48 m tall, 0.40 wide, 0.26 deep).
Pointed-arch cabinet in dark walnut on a stepped plinth, a lighter veneer front, a gothic fretwork grille (three lancets and
two roundels) over gold speaker cloth, fluted columns, a brass-bezelled amber dial, three ribbed bakelite knobs with brass caps.
Parts: Cabinet (TK_WoodRadio, TK_WoodVeneer [runtime material], TK_Bakelite), Cloth (TK_SpeakerCloth), Dial (TK_RadioDial, TK_Brass),
Knobs (TK_Bakelite, TK_Brass). Origin at the base centre, front +Y. Generates talk/gen/radio_dial.png."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import prop_shapes as S
import numpy as np
from mathutils import Matrix, Vector

C.begin()

# ------------------------------------------------------------------ radio_dial.png (warm backlit celluloid, no words)
def dial_png():
    H, W = 256, 512; A = 0.080 / 0.036                       # the window's aspect, so circles stay round on the model
    X, Y = S.grid(H, W, A)
    rng = np.random.default_rng(7)
    cx = A / 2
    glow = 0.50 + 0.50 * np.exp(-(((X - cx) / (A * 0.42)) ** 2 + ((Y - 0.55) / 0.55) ** 2))
    mott = S.fbm(H, W, 4, 8, rng, 4) - 0.5
    base = np.array([1.0, 0.70, 0.30], np.float32)
    img = (base * (glow + mott * 0.10)[..., None]).astype(np.float32)
    img = img * (1 - 0.18 * np.clip((Y - 0.2), 0, 1)[..., None])  # a little darker toward the bottom
    ink = (0.16, 0.07, 0.025)
    px = 1.0 / H
    # scale: an arc of ticks centred far below the window
    pcx, pcy, R0 = cx, 1.95, 1.48
    dx = X - pcx; dy = pcy - Y
    r = np.hypot(dx, dy); th = np.degrees(np.arctan2(dx, dy))
    span = 34.0
    step = 1.0
    k = np.round(th / step); dth = np.abs(th - k * step) * math.pi / 180 * r
    major = (np.mod(k, 5) == 0); inside = np.abs(th) <= span
    tlen = np.where(major, 0.16, 0.08)
    tw = np.where(major, 0.75 * px * 2.2, 0.75 * px * 1.3)
    tick = S.cover(dth - tw, px * 1.2) * ((r > R0) & (r < R0 + tlen)) * inside
    S.paint(img, tick, ink, 0.92)
    arcline = S.cover(np.abs(r - R0) - px * 1.1, px * 1.2) * (np.abs(th) <= span + 0.6)
    S.paint(img, arcline, ink, 0.9)
    arc2 = S.cover(np.abs(r - (R0 - 0.035)) - px * 0.7, px * 1.2) * (np.abs(th) <= span + 0.6)
    S.paint(img, arc2, ink, 0.6)
    # abstract numeral marks: little paired pills above each major tick (no digits, no words)
    for kk in range(-int(span), int(span) + 1, 5):
        a = math.radians(kk); rr = R0 + 0.26
        mx, my = pcx + rr * math.sin(a), pcy - rr * math.cos(a)
        n = 1 if kk == 0 else 2
        for j in range(n):
            ox = (j - (n - 1) / 2) * 0.034
            d = S.sd_rrect(X, Y, mx + ox * math.cos(a), my + ox * math.sin(a), 0.010, 0.030, 0.010)
            S.paint(img, S.cover(d, px * 1.5), ink, 0.75)
    # band markers: three small dots below the arc
    for kk in (-24, 0, 24):
        a = math.radians(kk); rr = R0 - 0.08
        S.paint(img, S.cover(S.sd_circle(X, Y, pcx + rr * math.sin(a), pcy - rr * math.cos(a), 0.014), px * 1.5), ink, 0.7)
    # needle (dark red), pivot below the window, slightly right of centre
    na = math.radians(9.0)
    ux, uy = math.sin(na), -math.cos(na)
    t = dx * ux + (-dy) * (-uy) * -1
    # distance from the needle line through the pivot
    t = (X - pcx) * ux + (Y - pcy) * uy
    dist = np.abs((X - pcx) * uy - (Y - pcy) * ux)
    nd = S.cover(dist - px * 1.4, px * 1.3) * ((t > R0 - 0.30) & (t < R0 + 0.42))
    sh = S.cover(np.abs((X - pcx - 0.012) * uy - (Y - pcy - 0.010) * ux) - px * 2.5, px * 6) * ((t > R0 - 0.30) & (t < R0 + 0.42))
    S.paint(img, sh, (0.25, 0.12, 0.04), 0.35)
    S.paint(img, nd, (0.45, 0.04, 0.02), 1.0)
    # vignette into the bezel
    e = np.minimum(np.minimum(X, A - X) / A * 2.2, np.minimum(Y, 1 - Y) * 2.6)
    img *= np.clip(0.55 + e, 0.55, 1.0)[..., None]
    img += (rng.random((H, W, 1)).astype(np.float32) - 0.5) * 0.025
    C.save_png("radio_dial.png", np.clip(img, 0, 1).astype(np.float32))

dial_png()

R = C.root("radio_1920s")
FRONT = 0.115          # the cabinet's front face (y)
VF = 0.121             # the veneer panel's front face

# ------------------------------------------------------------------ cabinet
def cabinet(bm):
    W, L, D = 0, 1, 2   # material slots
    # stepped plinth
    S.prism(bm, S.rrect(0.430, 0.290, 0.012, 3), 0.0, 0.020, "Z", W, bevel=0.005, bseg=2)
    S.prism(bm, S.rrect(0.414, 0.272, 0.010, 3), 0.019, 0.032, "Z", W, bevel=0.004, bseg=2)
    # pointed-arch body
    S.prism(bm, S.gothic(0.195, 0.030, 0.255, 0.226, 16), -0.125, FRONT, "Y", W, bevel=0.010, bseg=3)
    # lighter veneer front panel
    S.prism(bm, S.gothic(0.176, 0.046, 0.255, 0.202, 16), FRONT - 0.004, VF, "Y", L, bevel=0.0025, bseg=2, bevel_back=False)
    # back panel (fibreboard, inset) with vent louvres
    S.prism(bm, S.gothic(0.170, 0.050, 0.255, 0.195, 12), -0.128, -0.122, "Y", L, bevel=0.002, bseg=1)
    for i in range(7):
        x = (i - 3) * 0.034
        S.prism(bm, S.rrect(0.014, 0.12, 0.007, 3, x, 0.30), -0.1288, -0.127, "Y", D)
    # grille frame moulding (dark) around the cloth
    S.ring(bm, S.gothic(0.140, 0.172, 0.270, 0.165, 14), S.gothic(0.126, 0.188, 0.270, 0.146, 14), VF - 0.003, 0.136, "Y", W, d1_in=0.131)
    # fretwork: three lancets + two roundels + a sill
    for cx, zs, h in ((-0.082, 0.292, 0.050), (0.0, 0.322, 0.056), (0.082, 0.292, 0.050)):
        S.ring(bm, S.gothic(0.040, 0.188, zs, h, 8, cx), S.gothic(0.032, 0.196, zs, h - 0.010, 8, cx), VF, 0.130, "Y", W, d1_in=0.128)
    for sx in (-1, 1):
        S.ring(bm, S.circle(0.017, 16, sx * 0.058, 0.374), S.circle(0.0115, 16, sx * 0.058, 0.374), VF, 0.130, "Y", W, d1_in=0.128)
        # a small quatrefoil boss in each roundel
        S.prism(bm, S.circle(0.004, 8, sx * 0.058, 0.374), VF, 0.129, "Y", W)
    # column capitals / bases and fluted shafts flanking the grille
    for sx in (-1, 1):
        x = sx * 0.157
        S.lathe(bm, [(0.0, 0.052), (0.013, 0.052), (0.013, 0.060), (0.0105, 0.064), (0.0095, 0.068), (0.0095, 0.252),
                     (0.0105, 0.256), (0.013, 0.262), (0.013, 0.270), (0.008, 0.272), (0.0075, 0.278), (0.0045, 0.284), (0.0, 0.286)], 16, (x, VF + 0.003, 0.0), "Z", W,
                knurl=lambda ri, k: (0.86 if (k % 2 and 4 <= ri <= 5) else 1.0))
    # brass-free carved apron line under the dial: a thin raised bead
    S.prism(bm, S.rrect(0.250, 0.006, 0.003, 2, 0.0, 0.058), VF - 0.002, VF + 0.004, "Y", W)
    S.autosmooth(bm, 38)

# runtime material: a warmer tint of the light veneer (plain TK_WoodLight reads grey against the walnut)
C.MATS["TK_WoodVeneer"] = {"tex": "Wood049", "tint": [0.92, 0.70, 0.46], "metal": 0, "rough": None, "tile": 0.6}
cab = C.part("Cabinet", cabinet, [C.mat("TK_WoodRadio"), C.mat("TK_WoodVeneer"), C.mat("TK_Bakelite")])

def cloth(bm):
    S.prism(bm, S.gothic(0.128, 0.186, 0.270, 0.149, 14), VF - 0.004, VF + 0.0012, "Y", 0)
    S.autosmooth(bm, 30)
C.part("Cloth", cloth, [C.mat("TK_SpeakerCloth")])

# ------------------------------------------------------------------ dial (face + brass bezel)
DZ = 0.136
def dial(bm):
    win = S.rrect(0.080, 0.036, 0.010, 5, 0.0, DZ)
    S.prism(bm, win, VF - 0.002, VF + 0.0006, "Y", 0)
    S.ring(bm, S.rrect(0.098, 0.054, 0.019, 5, 0.0, DZ), win, VF - 0.002, VF + 0.0075, "Y", 1, d1_in=VF + 0.002)
    # bezel crest: a small brass arch above the window
    S.ring(bm, S.gothic(0.016, DZ + 0.026, DZ + 0.030, 0.016, 6), S.gothic(0.010, DZ + 0.030, DZ + 0.032, 0.010, 6), VF - 0.001, VF + 0.004, "Y", 1)
    S.autosmooth(bm, 40)
dl = C.part("Dial", dial, [C.mat("TK_RadioDial"), C.mat("TK_Brass")])
S.uv_faces(dl, 0, "Y", bounds=((-0.040, DZ - 0.018), (0.040, DZ + 0.018)))

# ------------------------------------------------------------------ knobs
def knobs(bm):
    for (x, z, s) in ((-0.100, DZ, 1.0), (0.100, DZ, 1.0), (0.0, 0.086, 0.86)):
        y = VF
        prof = [(0.0, y - 0.002), (0.0150 * s, y - 0.002), (0.0160 * s, y + 0.003), (0.0160 * s, y + 0.010 * s), (0.0157 * s, y + 0.015 * s),
                (0.0140 * s, y + 0.019 * s), (0.0110 * s, y + 0.0215 * s), (0.0, y + 0.0222 * s)]
        S.lathe(bm, prof, 28, (x, 0, z), "Y", 0, knurl=lambda ri, k: (1.0 if k % 2 else 0.93) if ri in (2, 3, 4) else 1.0)
        # brass cap
        yc = y + 0.0215 * s
        S.lathe(bm, [(0.0, yc - 0.001), (0.0090 * s, yc - 0.001), (0.0092 * s, yc + 0.0012), (0.0065 * s, yc + 0.0024), (0.0, yc + 0.0029)],
                20, (x, 0, z), "Y", 1)
        # pointer line on the skirt
        S.prism(bm, [(x - 0.0012, z + 0.0105 * s), (x + 0.0012, z + 0.0105 * s), (x + 0.0012, z + 0.0158 * s), (x - 0.0012, z + 0.0158 * s)],
                y + 0.012 * s, y + 0.0205 * s, "Y", 1)
    S.autosmooth(bm, 40)
C.part("Knobs", knobs, [C.mat("TK_Bakelite"), C.mat("TK_Brass")])

C.finish("radio_1920s", note="cathedral radio, real size 0.40 x 0.29 x 0.475 m; parts Cabinet, Cloth, Dial, Knobs")
