"""web_monitor_1990s: a beige 1990s CRT computer monitor (0.38 m tall, deep tapering back, swivel base) with a 101-key
keyboard in front of it. The screen shows a plain, wordless 90s encyclopedia-style web page (talk/gen/web_page.png).
Parts: Monitor (TK_BeigePlastic, TK_KeyCaps, TK_LED_Green, TK_DarkPlastic), Screen (TK_WebPage, curved glass, UVs 0..1 with
u = 0 at the viewer's left), Keyboard (TK_BeigePlastic body + modifier keys, TK_KeyCaps keys, TK_LED_Green, TK_DarkPlastic).
Origin at the base centre of the monitor's swivel foot; front +Y; the keyboard sits in front (y 0.33..0.50)."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import prop_shapes as S
import numpy as np
from mathutils import Matrix, Vector

C.begin()

# ------------------------------------------------------------------ web_page.png (1024 x 768, no words, no branding)
def page_png():
    H, W = 768, 1024
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    img = np.ones((H, W, 3), np.float32)
    grey = (0.75, 0.75, 0.75); dark = (0.50, 0.50, 0.50); hi = (1.0, 1.0, 1.0); ink = (0.0, 0.0, 0.0)

    def rect(x0, y0, x1, y1, col, a=1.0):
        m = ((xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)).astype(np.float32)
        S.paint(img, m, col, a)

    def bevel_box(x0, y0, x1, y1, raised=True, face=grey):
        rect(x0, y0, x1, y1, hi if raised else dark)
        rect(x0 + 1, y0 + 1, x1, y1, dark if raised else hi)
        rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, face)

    def pill(x0, yc, length, hgt, col, a=1.0):
        d = S.sd_rrect(xx, yy, x0 + length / 2, yc, length / 2, hgt / 2, hgt / 2)
        S.paint(img, S.cover(d, 1.0), col, a)

    # window frame + title bar (grey, three small window buttons on the right)
    bevel_box(0, 0, W, H)
    rect(4, 4, W - 4, 26, (0.56, 0.57, 0.60))
    tg = np.clip((xx - 4) / (W - 8), 0, 1)[..., None]
    band = ((yy >= 4) & (yy < 26))[..., None]
    img[:] = np.where(band, img * (1.08 - 0.25 * tg), img)
    pill(30, 15, 220, 8, (0.88, 0.88, 0.90), 0.9)                 # a wordless title
    for i in range(3):
        x = W - 4 - 22 * (3 - i)
        bevel_box(x + 2, 7, x + 20, 23)
    # menu strip + toolbar with raised buttons + an address field
    rect(4, 26, W - 4, 46, grey)
    for i, L in enumerate((26, 30, 26, 34, 40, 26)):
        pill(14 + i * 64, 36, L, 6, (0.30, 0.30, 0.30), 0.8)
    rect(4, 46, W - 4, 47, dark); rect(4, 47, W - 4, 48, hi)
    for i in range(8):
        x = 10 + i * 54
        bevel_box(x, 52, x + 48, 92)
        S.paint(img, S.cover(S.sd_circle(xx, yy, x + 24, 68, 9), 1.0), ((0.25, 0.45, 0.70), (0.25, 0.55, 0.30), (0.70, 0.45, 0.15), (0.45, 0.45, 0.50))[i % 4], 0.9)
        pill(x + 10, 84, 28, 4, (0.25, 0.25, 0.25), 0.7)
    bevel_box(W - 92, 52, W - 10, 92)
    S.paint(img, S.cover(S.sd_circle(xx, yy, W - 51, 72, 14), 1.0), (0.20, 0.30, 0.65), 1.0)
    rect(4, 96, W - 4, 97, dark); rect(4, 97, W - 4, 98, hi)
    pill(12, 111, 50, 6, (0.30, 0.30, 0.30), 0.8)
    bevel_box(74, 101, W - 14, 122, raised=False, face=(1, 1, 1))
    pill(84, 111.5, 300, 6, (0.15, 0.15, 0.15), 0.8)
    rect(4, 126, W - 4, 127, dark); rect(4, 127, W - 4, 128, hi)
    # page area (white), scrollbar, status bar
    PX0, PY0, PX1, PY1 = 6, 130, W - 26, H - 30
    rect(PX0, PY0, PX1, PY1, (1, 1, 1))
    rect(PX1, PY0, W - 6, PY1, (0.85, 0.85, 0.85))
    bevel_box(PX1, PY0, W - 6, PY0 + 20); bevel_box(PX1, PY1 - 20, W - 6, PY1); bevel_box(PX1, PY0 + 22, W - 6, PY0 + 150)
    rect(4, H - 28, W - 4, H - 4, grey)
    bevel_box(8, H - 26, 700, H - 6, raised=False)
    pill(16, H - 16, 160, 5, (0.25, 0.25, 0.25), 0.7)
    bevel_box(704, H - 26, W - 8, H - 6, raised=False)
    # page content: heading bar, rule, image placeholder, text lines, link bars
    L0 = 40
    d = S.sd_rrect(xx, yy, L0 + 230, 168, 230, 17, 3)
    S.paint(img, S.cover(d, 1.0), (0.10, 0.10, 0.12))
    rect(L0, 196, PX1 - 30, 198, (0.62, 0.62, 0.62))
    pill(L0, 214, 520, 6, (0.55, 0.55, 0.55), 0.9)
    IX0, IY0, IX1, IY1 = PX1 - 260, 214, PX1 - 34, 384
    rect(IX0, IY0, IX1, IY1, (0.55, 0.55, 0.55)); rect(IX0 + 2, IY0 + 2, IX1 - 2, IY1 - 2, (0.88, 0.89, 0.90))
    rect(IX0 + 10, IY0 + 10, IX1 - 10, IY1 - 34, (0.74, 0.80, 0.86))
    mtn = (yy > IY1 - 34 - 50 + 40 * np.abs(((xx - IX0) / 60.0) % 2 - 1)) & (xx > IX0 + 10) & (xx < IX1 - 10) & (yy < IY1 - 34)
    S.paint(img, mtn.astype(np.float32), (0.50, 0.58, 0.52))
    S.paint(img, S.cover(S.sd_circle(xx, yy, IX1 - 46, IY0 + 36, 12), 1.0), (0.96, 0.86, 0.50))
    pill(IX0 + 20, IY1 - 16, 150, 5, (0.50, 0.50, 0.50), 0.8)
    rng = np.random.default_rng(5)
    y = 244; para = 0; links = {(1, 2), (3, 1), (4, 4)}
    while y < PY1 - 20:
        right = (IX0 - 24) if y < IY1 + 8 else (PX1 - 40)
        nlines = int(rng.integers(3, 7))
        if para in (2, 5):                                  # a sub-heading bar
            S.paint(img, S.cover(S.sd_rrect(xx, yy, L0 + 110, y + 4, 110, 8, 2), 1.0), (0.18, 0.18, 0.2))
            y += 30; para += 1; continue
        for li in range(nlines):
            if y > PY1 - 20: break
            right = (IX0 - 24) if y < IY1 + 8 else (PX1 - 40)
            last = li == nlines - 1
            length = (right - L0) * (rng.uniform(0.35, 0.7) if last else rng.uniform(0.92, 1.0))
            x = L0; segs = []
            while x < L0 + length - 20:                     # words: short pills with gaps
                wl = float(rng.uniform(18, 70)); wl = min(wl, L0 + length - x)
                segs.append((x, wl)); x += wl + 7
            for si, (sx, wl) in enumerate(segs):
                if (para, li) in links and 2 <= si <= 4:
                    pill(sx, y, wl, 6, (0.0, 0.0, 0.80))
                    rect(sx, y + 5, sx + wl, y + 6.5, (0.0, 0.0, 0.80))
                else:
                    pill(sx, y, wl, 6, (0.50, 0.50, 0.52), 0.95)
            y += 15
        y += 13; para += 1
    C.save_png("web_page.png", np.clip(img, 0, 1).astype(np.float32))

page_png()

C.root("web_monitor_1990s")

# ------------------------------------------------------------------ monitor body (loft from the bezel lip to the tapering back)
SEG = 4
OPN = (0.300, 0.228, 0.016, 0.0, 0.234)          # screen opening (w, h, r, cx, cz)
ZB = 0.050                                       # bottom of the case

def rr(w, h, r, cz): return S.rrect(w, h, r, SEG, 0.0, cz)

def monitor(bm):
    Bg, Kc, Led, Dk = 0, 1, 2, 3
    W0, H0 = 0.372, 0.330; zc = ZB + H0 / 2
    rear_w, rear_h = 0.250, 0.220; rzc = ZB + 0.008 + rear_h / 2
    secs = [(0.176, S.rrect(*OPN[:3], SEG, OPN[3], OPN[4])),
            (0.186, S.rrect(0.312, 0.240, 0.022, SEG, 0.0, OPN[4])),
            (0.1905, S.rrect(0.326, 0.254, 0.028, SEG, 0.0, OPN[4])),
            (0.1910, rr(W0 - 0.012, H0 - 0.012, 0.018, zc)),
            (0.1860, rr(W0, H0, 0.024, zc)),
            (0.1180, rr(W0, H0, 0.024, zc)),
            (0.1100, rr(W0 - 0.018, H0 - 0.012, 0.028, zc - 0.002)),
            (0.0950, rr(W0 - 0.030, H0 - 0.024, 0.034, zc - 0.006)),
            (-0.195, rr(rear_w, rear_h, 0.040, rzc)),
            (-0.212, rr(rear_w - 0.020, rear_h - 0.020, 0.032, rzc))]
    lf = S.loft(bm, secs, "Y", Bg, cap0=False, cap1=False)
    loops = lf["loops"]
    # orient: a face on the +X flank must face +X
    test = [f for f in bm.faces if f.calc_center_median().x > 0.18 and abs(f.calc_center_median().z - zc) < 0.05]
    test[0].normal_update()
    if test[0].normal.x < 0:
        for f in bm.faces: f.normal_flip()
    cap = bm.faces.new(loops[-1]); cap.material_index = Bg; cap.normal_update()
    if cap.normal.y > 0: cap.normal_flip()
    # rear: a raised service panel with vent slots and a small cable recess
    S.prism(bm, rr(0.180, 0.150, 0.020, rzc), -0.218, -0.211, "Y", Bg, bevel=0.002, bseg=1)
    for i in range(6):
        S.prism(bm, S.rrect(0.120, 0.006, 0.003, 2, 0.0, rzc + 0.045 - i * 0.014), -0.2195, -0.217, "Y", Dk)
    # top vents on the sloping back
    y0, z0 = 0.095, zc + (H0 - 0.024) / 2; y1, z1 = -0.195, rzc + rear_h / 2
    ang = math.atan2(z0 - z1, y0 - y1)
    for i in range(7):
        y = 0.02 - i * 0.030
        z = z1 + (y - y1) * (z0 - z1) / (y0 - y1)
        v = S.box(bm, (0.170, 0.009, 0.004), (0.0, y, z), Dk)
        S.xform(bm, v["verts"], Matrix.Translation((0, y, z)) @ Matrix.Rotation(ang, 4, "X") @ Matrix.Translation((0, -y, -z)))
    # chin controls: a pill power key, a green LED, four small round keys, a recessed grip line (viewer's right is -X)
    FYc = 0.1905
    S.prism(bm, S.rrect(0.030, 0.012, 0.0059, 4, -0.128, 0.083), FYc - 0.003, FYc + 0.0045, "Y", Kc, bevel=0.0012, bseg=2, bevel_back=False)
    S.lathe(bm, [(0.0, FYc - 0.002), (0.0028, FYc - 0.002), (0.0028, FYc + 0.0012), (0.0, FYc + 0.0018)], 10, (-0.100, 0, 0.083), "Y", Led)
    for i in range(4):
        x = 0.140 - i * 0.022
        S.lathe(bm, [(0.0, FYc - 0.002), (0.0055, FYc - 0.002), (0.0055, FYc + 0.0018), (0.0042, FYc + 0.0030), (0.0, FYc + 0.0034)], 12, (x, 0, 0.083), "Y", Kc)
    S.prism(bm, S.rrect(0.200, 0.003, 0.0015, 2, 0.0, 0.064), FYc - 0.002, FYc + 0.0008, "Y", Dk)
    # swivel foot: an oval dished pedestal and a neck into the case
    foot = S.lathe(bm, [(0.0, 0.0), (0.118, 0.0), (0.121, 0.004), (0.116, 0.011), (0.090, 0.021), (0.062, 0.026), (0.052, 0.029),
                        (0.050, ZB + 0.01), (0.0, ZB + 0.01)], 32, (0, 0, 0), "Z", Bg)
    S.xform(bm, foot["verts"], Matrix.Translation((0, 0.0, 0)) @ Matrix.Diagonal((1.0, 1.2, 1.0, 1.0)))
    S.autosmooth(bm, 36)

mon = C.part("Monitor", monitor, [C.mat("TK_BeigePlastic"), C.mat("TK_KeyCaps"), C.mat("TK_LED_Green"), C.mat("TK_DarkPlastic")])

# ------------------------------------------------------------------ screen glass (bulging both ways, edge tucked behind the lip)
def screen(bm):
    w, h, r, cx, cz = OPN
    nx, nz = 16, 12; hw, hh = w / 2 + 0.002, h / 2 + 0.002
    V = {}
    for i in range(nx + 1):
        for j in range(nz + 1):
            x = -hw + 2 * hw * i / nx; z = -hh + 2 * hh * j / nz
            ax, az = abs(x) - (hw - r), abs(z) - (hh - r)
            if ax > 0 and az > 0:
                Lr = math.hypot(ax, az)
                if Lr > r: x = math.copysign(hw - r + ax * r / Lr, x); z = math.copysign(hh - r + az * r / Lr, z)
            xn, zn = x / hw, z / hh
            y = 0.1752 + 0.012 * (1 - xn * xn) * (1 - zn * zn)
            V[i, j] = bm.verts.new((cx + x, y, cz + z))
    for i in range(nx):
        for j in range(nz):
            f = bm.faces.new((V[i, j], V[i + 1, j], V[i + 1, j + 1], V[i, j + 1])); f.normal_update()
            if f.normal.y < 0: f.normal_flip()
    for f in bm.faces: f.smooth = True
scr = C.part("Screen", screen, [C.mat("TK_WebPage")])
C.planar_uv(scr, "Y"); scr["keep_uv"] = True

# ------------------------------------------------------------------ keyboard: wedge body + 101 individual keys
KY0, KY1 = 0.330, 0.500
def surf_z(y): return 0.0205 + (y - 0.338) * 0.118

def keyboard(bm):
    Bg, Kc, Led, Dk = 0, 1, 2, 3
    prof = [(KY0, 0.0), (KY1, 0.0), (KY1, 0.034), (KY1 - 0.008, 0.0395), (0.338, 0.0215), (KY0, 0.017)]
    S.prism(bm, prof, -0.235, 0.235, "X", Bg, bevel=0.0035, bseg=2)
    slope = math.atan(0.118)
    U = 0.019
    XL = 0.2185                                         # user's left edge (viewer's left is +X)
    def key(u, w, y, dep=1.0, mod=False):
        cxu = u + w / 2
        x = XL - cxu * U
        yc = y - (dep - 1) * U / 2
        zc = surf_z(yc) + 0.0048
        v = S.box(bm, (w * U - 0.0019, dep * U - 0.0019, 0.0085), (x, yc, zc), Bg if mod else Kc, taper=0.0021)
        S.xform(bm, v["verts"], Matrix.Translation((x, yc, zc)) @ Matrix.Rotation(slope, 4, "X") @ Matrix.Translation((-x, -yc, -zc)))
    rows = [0.4475, 0.4285, 0.4095, 0.3905, 0.3715]    # number row .. space row
    yf = 0.4725                                          # function row
    # function row
    key(0, 1, yf, mod=True)
    for g, u0 in enumerate((2, 6.5, 11)):
        for i in range(4): key(u0 + i, 1, yf, mod=(g == 1))
    for i in range(3): key(15.5 + i, 1, yf, mod=True)
    # main block
    for i in range(13): key(i, 1, rows[0])
    key(13, 2, rows[0], mod=True)
    key(0, 1.5, rows[1], mod=True)
    for i in range(12): key(1.5 + i, 1, rows[1])
    key(13.5, 1.5, rows[1])
    key(0, 1.75, rows[2], mod=True)
    for i in range(11): key(1.75 + i, 1, rows[2])
    key(12.75, 2.25, rows[2], mod=True)
    key(0, 2.25, rows[3], mod=True)
    for i in range(10): key(2.25 + i, 1, rows[3])
    key(12.25, 2.75, rows[3], mod=True)
    key(0, 1.5, rows[4], mod=True); key(2.5, 1.5, rows[4], mod=True); key(4, 7, rows[4]); key(11, 1.5, rows[4], mod=True); key(13.5, 1.5, rows[4], mod=True)
    # navigation cluster
    for r in (0, 1):
        for i in range(3): key(15.5 + i, 1, rows[r], mod=True)
    key(16.5, 1, rows[3], mod=True)
    for i in range(3): key(15.5 + i, 1, rows[4], mod=True)
    # numeric pad
    NX = 19
    for i in range(4): key(NX + i, 1, rows[0], mod=(i > 0))
    for r in (1, 2, 3):
        for i in range(3): key(NX + i, 1, rows[r])
    key(NX + 3, 1, rows[1] , dep=2, mod=True)           # tall +
    key(NX + 3, 1, rows[3], dep=2, mod=True)            # tall enter
    key(NX, 2, rows[4]); key(NX + 2, 1, rows[4])
    # lock lights above the pad (one lit)
    for i in range(3):
        x = XL - (NX + 0.6 + i * 1.2) * U
        S.lathe(bm, [(0.0, surf_z(yf) - 0.001), (0.0022, surf_z(yf) - 0.001), (0.0022, surf_z(yf) + 0.0012), (0.0, surf_z(yf) + 0.0016)], 8,
                (x, yf, 0), "Z", Led if i == 0 else Dk)
    # a raised wordless maker's strip above the lock lights is omitted on purpose (no branding)
    S.autosmooth(bm, 36)

C.part("Keyboard", keyboard, [C.mat("TK_BeigePlastic"), C.mat("TK_KeyCaps"), C.mat("TK_LED_Green"), C.mat("TK_DarkPlastic")])

C.finish("web_monitor_1990s", note="beige CRT 0.37 x 0.42 x 0.38 m on a swivel foot + 101-key keyboard; parts Monitor, Screen, Keyboard")
