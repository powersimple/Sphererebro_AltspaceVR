"""server_rack: four giant 50 m server racks for the talk (one run builds all four).

  server_rack_hero    closed perforated doors, servers + LEDs behind them
  server_rack_open    the same, doors swung open 110 deg outward (toward +Y)
  server_rack_locked  glass doors, shelves of archive tape (reels + cartridges), a giant padlock on a hasp
  server_rack_label   the hero rack with a dark label panel (bezel) at ~22 m and an empty "LabelAnchor" for engine text

Rack: 12 m wide (X), 18 m deep (Y), 50 m tall. Origin at the base centre, front faces +Y.
Parts (exact names, the Unity builder animates by name):
  Frame, SidePanels, BackPanel, Rails, ServerFace, LEDs_Green, LEDs_Blue, LEDs_Amber, Door_XP, Door_XN
  Door_XP origin on the +X hinge axis, Door_XN origin on the -X hinge axis (rotate about local Z; +110 deg opens XN, -110 opens XP)
  locked: Shelves, TapeReels, TapeCarts, TapeLabels, Padlock (origin = hang point at the top of the shackle)
  label:  LabelPanel, LabelBezel, LabelMounts, LabelAnchor (empty)
Generates talk/gen/server_faces.png (procedural 1U/2U/4U server fronts; no text, no brands) and talk/gen/tape_label.png.
"""
import bpy, bmesh, math, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import numpy as np
from mathutils import Vector, Matrix

C.begin()

# ------------------------------------------------------------------ runtime materials (report these for merging)
C.MATS["TK_TapeLabel"] = {"tex": None, "emitTex": "tape_label.png", "tint": [1, 1, 1], "metal": 0, "rough": 0.6, "tile": 0}

# ------------------------------------------------------------------ dimensions
W, D, H = 12.0, 18.0, 50.0
HX, HY = W / 2, D / 2               # 6, 9
POST = 1.0                          # corner post section
BAY_X = HX - POST                   # 5: inner edge of the posts
FACE_Y = 7.0                        # server face plane
FACE_Z0, FACE_Z1 = 2.0, 48.0        # 46 m of servers
DOOR_Z0, DOOR_Z1 = 1.5, 48.7
DOOR_T = 0.32                       # door leaf thickness (front face at y = HY)
HANDLE_Z = (27.0, 33.0)
NU = 42                             # rack units in the face
UH = (FACE_Z1 - FACE_Z0) / NU       # 1.095 m per U


# ------------------------------------------------------------------ geometry helpers
def cbox(bm, size, loc, c=0.06, mi=0):
    """Box with chamfered edges (one bevel segment)."""
    vs = C.bm_box(bm, size, loc, mi)
    if c > 0:
        es = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=vs + es, offset=c, segments=1, affect="EDGES", profile=0.5, material=mi)
    return vs


def quad_y(bm, x0, x1, z0, z1, y, mi=0, back=False):
    """Axis quad in the XZ plane at y, normal +Y (or -Y with back=True)."""
    a = bm.verts.new((x0, y, z0)); b = bm.verts.new((x1, y, z0)); c = bm.verts.new((x1, y, z1)); d = bm.verts.new((x0, y, z1))
    f = bm.faces.new((a, b, c, d) if not back else (d, c, b, a))
    f.material_index = mi
    f.normal_update()
    return f


def sweep(bm, pts, radius, segs=8, mi=0, cap=True, up=Vector((0, 1, 0))):
    """Tube along a polyline pts (list of Vector)."""
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.cross(up)
        if a.length < 1e-4: a = t.cross(Vector((1, 0, 0)))
        a.normalize(); b = a.cross(t).normalized()
        r = radius(i / (n - 1)) if callable(radius) else radius
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r) for k in range(segs)])
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.material_index = mi
    if cap:
        f = bm.faces.new(list(reversed(rings[0]))); f.material_index = mi
        f = bm.faces.new(rings[-1]); f.material_index = mi
    return rings


def fix_normals(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()


def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for l in list(bpy.data.lights): bpy.data.lights.remove(l)
    for c in list(bpy.data.cameras): bpy.data.cameras.remove(c)


# ------------------------------------------------------------------ server face image + LED layout
SS = 2                                   # supersample
IW, IH = 512 * SS, 2048 * SS
KX, KY = IW / (2 * BAY_X), IH / (FACE_Z1 - FACE_Z0)   # px per metre (s across 0..10, t down 0..46)
rng = random.Random(7)
img = np.zeros((IH, IW, 3), np.float32)
LEDS = []                                # (s, t, colour)  s from the viewer's left, t from the top (metres)


def R(s0, t0, s1, t1, col):
    img[max(0, int(round(t0 * KY))):int(round(t1 * KY)), max(0, int(round(s0 * KX))):int(round(s1 * KX))] = col


def bevel_rect(s0, t0, s1, t1, col, hi=0.06, lo=-0.05, e=0.03):
    """Rect with a light top/left edge and a dark bottom/right edge (reads as a raised part)."""
    col = np.array(col, np.float32)
    R(s0, t0, s1, t1, col)
    R(s0, t0, s1, t0 + e, np.clip(col + hi, 0, 1)); R(s0, t0, s0 + e, t1, np.clip(col + hi * 0.7, 0, 1))
    R(s0, t1 - e, s1, t1, np.clip(col + lo, 0, 1)); R(s1 - e, t0, s1, t1, np.clip(col + lo, 0, 1))


def dots(s0, t0, s1, t1, base, hole, pitch=0.12, rad=0.04, hexa=True):
    """Vent grille: round holes on a (hex) grid."""
    R(s0, t0, s1, t1, base)
    y0, y1 = int(t0 * KY), int(t1 * KY); x0, x1 = int(s0 * KX), int(s1 * KX)
    if y1 <= y0 or x1 <= x0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    ty = yy / KY; sx = xx / KX
    row = np.floor((ty - t0) / (pitch * 0.866))
    cy = t0 + (row + 0.5) * pitch * 0.866
    off = (row % 2) * pitch * 0.5 if hexa else 0
    cx = s0 + np.floor((sx - s0 - off) / pitch) * pitch + pitch * 0.5 + off
    m = (sx - cx) ** 2 + (ty - cy) ** 2 < rad ** 2
    sub = img[y0:y1, x0:x1]; sub[m] = hole


def circle(s, t, r, col):
    y0, y1 = int((t - r) * KY), int((t + r) * KY) + 1; x0, x1 = int((s - r) * KX), int((s + r) * KX) + 1
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = (xx / KX - s) ** 2 + (yy / KY - t) ** 2 < r * r
    img[y0:y1, x0:x1][m] = col


def slots(s0, t0, s1, t1, base, slot, n, horiz=True, frac=0.45):
    R(s0, t0, s1, t1, base)
    for i in range(n):
        if horiz:
            a = t0 + (t1 - t0) * (i + 0.5 - frac / 2) / n; b = a + (t1 - t0) * frac / n
            R(s0 + 0.05, a, s1 - 0.05, b, slot)
        else:
            a = s0 + (s1 - s0) * (i + 0.5 - frac / 2) / n; b = a + (s1 - s0) * frac / n
            R(a, t0 + 0.05, b, t1 - 0.05, slot)


def led(s, t, col):
    LEDS.append((s, t, col))


def ear(t0, t1):
    for s0, s1 in ((0.0, 0.42), (9.58, 10.0)):
        bevel_rect(s0, t0 + 0.02, s1, t1 - 0.02, (0.24, 0.245, 0.26), 0.08, -0.08)
        nu = max(1, int(round((t1 - t0) / UH)))
        for k in range(nu):
            tc = t0 + (k + 0.5) * (t1 - t0) / nu
            circle((s0 + s1) / 2, tc, 0.085, (0.42, 0.43, 0.45)); circle((s0 + s1) / 2, tc, 0.04, (0.12, 0.12, 0.13))


def control(s0, t0, s1, t1):
    """Server control strip: grille, power button, ID button, pull-tab (label blank)."""
    dots(s0, t0 + 0.06, s1, t1 - 0.06, (0.2, 0.205, 0.215), (0.03, 0.03, 0.035), 0.1, 0.032)
    tc = (t0 + t1) / 2
    circle(s0 + 0.22, tc, 0.12, (0.5, 0.51, 0.53)); circle(s0 + 0.22, tc, 0.08, (0.08, 0.08, 0.09))
    led(s0 + 0.22, tc - 0.2 if t1 - t0 > 0.6 else tc, "G")
    circle(s0 + 0.55, tc, 0.08, (0.3, 0.31, 0.33)); led(s0 + 0.55, tc, "B")
    if rng.random() < 0.12: led(s0 + 0.8, tc, "A")


def server1u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.17, 0.175, 0.19), 0.07, -0.08)
    control(0.55, t0 + 0.08, 1.75, t1 - 0.08)
    nb = 10; s0, s1 = 1.9, 8.1; w = (s1 - s0) / nb
    for i in range(nb):
        a = s0 + i * w + 0.03; b = a + w - 0.06
        bevel_rect(a, t0 + 0.1, b, t1 - 0.1, (0.07, 0.07, 0.08), 0.05, -0.04, 0.025)
        slots(a + 0.06, t0 + 0.18, b - 0.06, t1 - 0.32, (0.07, 0.07, 0.08), (0.025, 0.025, 0.03), 6, horiz=False, frac=0.5)
        R(a + 0.04, t1 - 0.28, b - 0.04, t1 - 0.14, (0.36, 0.37, 0.4))     # release latch
        if rng.random() < 0.85: led(b - 0.1, t0 + 0.2, "G" if rng.random() < 0.8 else "B")
    dots(8.25, t0 + 0.1, 9.45, t1 - 0.1, (0.22, 0.225, 0.24), (0.03, 0.03, 0.035), 0.11, 0.038)
    R(8.3, t1 - 0.3, 8.9, t1 - 0.16, (0.72, 0.72, 0.68))                     # pull-tab label blank


def server2u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.15, 0.155, 0.17), 0.07, -0.08)
    control(0.55, t0 + 0.1, 1.75, t1 - 0.1)
    if rng.random() < 0.5:   # 12 x 3.5" carriers, 4 cols x 3 rows
        cols, rows = 4, 3; s0, s1 = 1.9, 8.2
        w = (s1 - s0) / cols; h = (t1 - t0 - 0.2) / rows
        for r in range(rows):
            for c in range(cols):
                a = s0 + c * w + 0.04; b = a + w - 0.08; u = t0 + 0.1 + r * h + 0.03; v = u + h - 0.06
                bevel_rect(a, u, b, v, (0.09, 0.09, 0.1), 0.06, -0.05, 0.025)
                dots(a + 0.08, u + 0.07, b - 0.45, v - 0.07, (0.11, 0.11, 0.12), (0.02, 0.02, 0.025), 0.07, 0.024)
                R(b - 0.4, u + 0.08, b - 0.1, v - 0.08, (0.4, 0.41, 0.44))     # handle
                if rng.random() < 0.9: led(b - 0.25, u + 0.12, "G" if rng.random() < 0.85 else "B")
    else:                    # 24 x 2.5" vertical carriers
        nb = 24; s0, s1 = 1.9, 8.2; w = (s1 - s0) / nb
        for i in range(nb):
            a = s0 + i * w + 0.02; b = a + w - 0.04
            bevel_rect(a, t0 + 0.12, b, t1 - 0.12, (0.08, 0.08, 0.09), 0.05, -0.04, 0.02)
            slots(a + 0.03, t0 + 0.2, b - 0.03, t1 - 0.7, (0.08, 0.08, 0.09), (0.02, 0.02, 0.025), 8, frac=0.5)
            R(a + 0.03, t1 - 0.6, b - 0.03, t1 - 0.2, (0.34, 0.35, 0.38))
            if rng.random() < 0.6: led((a + b) / 2, t0 + 0.2, "G" if rng.random() < 0.75 else "B")
    dots(8.35, t0 + 0.1, 9.45, t1 - 0.1, (0.21, 0.215, 0.23), (0.03, 0.03, 0.035), 0.11, 0.038)
    R(8.4, t0 + 0.25, 9.0, t0 + 0.4, (0.72, 0.72, 0.68))


def storage4u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.2, 0.205, 0.22), 0.08, -0.08)
    R(0.6, t0 + 0.12, 9.4, t0 + 0.35, (0.11, 0.11, 0.12))       # top bezel band
    dots(0.7, t0 + 0.15, 9.3, t0 + 0.32, (0.11, 0.11, 0.12), (0.03, 0.03, 0.03), 0.08, 0.025, True)
    led(9.1, t0 + 0.23, "B"); led(8.8, t0 + 0.23, "G")
    cols, rows = 6, 4; s0, s1 = 0.6, 9.4
    w = (s1 - s0) / cols; h = (t1 - t0 - 0.55) / rows
    for r in range(rows):
        for c in range(cols):
            a = s0 + c * w + 0.04; b = a + w - 0.08; u = t0 + 0.42 + r * h + 0.03; v = u + h - 0.06
            bevel_rect(a, u, b, v, (0.075, 0.075, 0.085), 0.06, -0.05, 0.025)
            slots(a + 0.1, u + 0.08, b - 0.5, v - 0.08, (0.075, 0.075, 0.085), (0.02, 0.02, 0.025), 5, frac=0.4)
            R(b - 0.42, u + 0.1, b - 0.12, v - 0.1, (0.45, 0.46, 0.49))
            if rng.random() < 0.92: led(b - 0.27, v - 0.16, "G" if rng.random() < 0.8 else ("A" if rng.random() < 0.3 else "B"))


def switch1u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.1, 0.105, 0.115), 0.06, -0.06)
    dots(0.55, t0 + 0.12, 1.2, t1 - 0.12, (0.13, 0.13, 0.14), (0.03, 0.03, 0.03), 0.09, 0.03)
    R(1.3, t0 + 0.35, 1.55, t1 - 0.35, (0.02, 0.02, 0.02)); led(1.42, t0 + 0.22, "G")
    s = 1.75; pw = 0.25
    for g in range(4):
        for i in range(6):
            for r in range(2):
                a = s + i * pw; u = t0 + 0.14 + r * 0.42
                R(a + 0.02, u, a + pw - 0.02, u + 0.36, (0.18, 0.18, 0.19))
                R(a + 0.05, u + 0.04, a + pw - 0.05, u + 0.32, (0.015, 0.015, 0.018))
                R(a + 0.09, u + (0.26 if r == 0 else 0.04), a + pw - 0.09, u + (0.32 if r == 0 else 0.1), (0.3, 0.3, 0.3))
                if rng.random() < 0.55: led(a + pw / 2, u + (-0.03 if r == 0 else 0.39), "G" if rng.random() < 0.85 else "A")
        s += 6 * pw + 0.12
    for k in range(4):   # SFP cages
        a = 8.1 + k * 0.34
        bevel_rect(a, t0 + 0.28, a + 0.3, t1 - 0.28, (0.5, 0.51, 0.53), 0.1, -0.15, 0.02)
        R(a + 0.04, t0 + 0.36, a + 0.26, t1 - 0.36, (0.03, 0.03, 0.03))
        if k < 2: led(a + 0.15, t0 + 0.2, "B")


def patch1u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.12, 0.12, 0.13), 0.06, -0.06)
    s = 1.0; pw = 0.32
    for g in range(4):
        for i in range(6):
            a = s + i * pw
            R(a + 0.04, t0 + 0.2, a + pw - 0.04, t0 + 0.34, (0.75, 0.75, 0.72))   # write-on label blank
            R(a + 0.03, t0 + 0.42, a + pw - 0.03, t1 - 0.2, (0.02, 0.02, 0.022))
            R(a + 0.12, t1 - 0.36, a + pw - 0.12, t1 - 0.28, (0.25, 0.25, 0.25))
        s += 6 * pw + 0.24


def blank1u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.13, 0.135, 0.145), 0.06, -0.07)
    dots(0.8, t0 + 0.2, 9.2, t1 - 0.2, (0.13, 0.135, 0.145), (0.06, 0.06, 0.065), 0.1, 0.03)


def cable1u(t0, t1):
    bevel_rect(0.42, t0 + 0.02, 9.58, t1 - 0.02, (0.09, 0.09, 0.1), 0.05, -0.05)
    R(0.7, t0 + 0.42, 9.3, t1 - 0.42, (0.02, 0.02, 0.02))
    slots(0.7, t0 + 0.38, 9.3, t1 - 0.38, (0.03, 0.03, 0.035), (0.07, 0.07, 0.075), 120, horiz=False, frac=0.35)
    for k in range(5):   # D-ring loops
        a = 0.9 + k * 1.95
        bevel_rect(a, t0 + 0.12, a + 0.3, t1 - 0.12, (0.25, 0.25, 0.27), 0.1, -0.1, 0.03)


LAYOUT = [("patch", 1), ("switch", 1), ("cable", 1), ("switch", 1), ("blank", 1),
          ("s1", 1), ("s1", 1), ("s1", 1), ("s1", 1), ("s1", 1), ("s1", 1),
          ("s2", 2), ("s2", 2), ("s2", 2), ("blank", 1),
          ("st4", 4), ("st4", 4),
          ("s2", 2), ("s2", 2), ("s1", 1), ("s1", 1), ("s1", 1), ("s1", 1), ("blank", 1), ("s2", 2),
          ("s1", 1), ("s1", 1), ("cable", 1), ("s2", 2)]
used = sum(n for _, n in LAYOUT)
assert used == NU, used
FN = {"patch": patch1u, "switch": switch1u, "cable": cable1u, "blank": blank1u, "s1": server1u, "s2": server2u, "st4": storage4u}

img[:] = (0.02, 0.02, 0.022)
u = 0
for kind, n in LAYOUT:
    t0, t1 = u * UH, (u + n) * UH
    FN[kind](t0, t1)
    ear(t0, t1)
    u += n
# subtle vertical light falloff / grime so it isn't flat
tt = np.linspace(0, 1, IH)[:, None, None]
img *= (0.92 + 0.08 * np.cos(tt * math.pi * 3) ** 2)
img = img.reshape(IH // SS, SS, IW // SS, SS, 3).mean(axis=(1, 3))
C.save_png("server_faces.png", np.clip(img, 0, 1).astype(np.float32))

# tape label: white label, barcode bars (no text), a coloured generation band at the top
TW, TH = 64, 256
lab = np.ones((TH, TW, 3), np.float32) * 0.92
lab[:30] = (0.15, 0.35, 0.7)
r2 = random.Random(3)
y = 50
while y < TH - 20:
    w = r2.choice((2, 2, 3, 4, 6))
    lab[y:y + w, 8:TW - 8] = 0.05
    y += w + r2.choice((2, 3, 4))
lab[TH - 12:] = 0.85
C.save_png("tape_label.png", lab)

rng = random.Random(11)
LEDS_SEL = LEDS
print("[server_rack] LEDs in layout:", len(LEDS))


def led_world(s, t):
    return BAY_X - s, FACE_Z1 - t


# ------------------------------------------------------------------ body (shared)
def build_body(variant):
    mF, mP = C.mat("TK_RackFrame"), C.mat("TK_RackPanel")

    def frame(bm):
        # feet + recessed plinth + base frame
        for sx in (-1, 1):
            for sy in (-1, 1):
                C.bm_cyl(bm, 0.38, 0.22, (sx * (HX - 1.0), sy * (HY - 1.0), 0.11), 8)
        cbox(bm, (W - 0.8, D - 0.8, 0.75), (0, 0, 0.22 + 0.375), 0.05)
        cbox(bm, (W, D, 0.5), (0, 0, 0.97 + 0.25), 0.08)
        # corner posts
        for sx in (-1, 1):
            for sy in (-1, 1):
                cbox(bm, (POST, POST, 47.6), (sx * (HX - POST / 2), sy * (HY - POST / 2), 1.47 + 23.8), 0.09)
        # top: recessed band + cap with a lip + low cable-entry boxes
        cbox(bm, (W - 0.3, D - 0.3, 0.5), (0, 0, 49.07 + 0.25 - 0.0), 0.04)
        cbox(bm, (W + 0.2, D + 0.2, 0.75), (0, 0, 49.6), 0.12)
        cbox(bm, (3.2, 2.0, 0.35), (-2.5, -4.0, 50.15), 0.06)
        cbox(bm, (3.2, 2.0, 0.35), (2.5, -4.0, 50.15), 0.06)
        # front bay: sill + header
        cbox(bm, (2 * BAY_X, 0.7, 0.55), (0, HY - 0.65, 1.47 + 0.27), 0.05)
        cbox(bm, (2 * BAY_X, 0.7, 0.75), (0, HY - 0.65, 48.4), 0.05)
        # side-panel backing (dark, shows through the seams)
        for sx in (-1, 1):
            C.bm_box(bm, (0.1, D - 2 * POST + 0.1, 47.4), (sx * (HX - 0.42), 0, 1.47 + 23.7))
        C.bm_box(bm, (2 * BAY_X + 0.1, 0.1, 47.4), (0, -(HY - 0.42), 1.47 + 23.7))
    o = C.part("Frame", frame, [mF])
    fix_normals(o)

    def sides(bm):
        n = 4; z0, z1 = 1.5, 48.75; h = (z1 - z0) / n
        for sx in (-1, 1):
            for i in range(n):
                cbox(bm, (0.26, D - 2 * POST - 0.12, h - 0.12), (sx * (HX - 0.2), 0, z0 + (i + 0.5) * h), 0.07)
                # recessed grip / key lock
                C.bm_cyl(bm, 0.16, 0.12, (sx * (HX - 0.05), 5.8, z0 + (i + 0.5) * h + 1.5), 10, axis="X")
                C.bm_box(bm, (0.1, 1.6, 0.35), (sx * (HX - 0.05), 5.8, z0 + (i + 0.5) * h))
            # louvre vents on the top panel
            for k in range(7):
                C.bm_box(bm, (0.12, 9.0, 0.16), (sx * (HX - 0.04), -0.5, 45.4 - k * 0.42))
    o = C.part("SidePanels", sides, [mP]); fix_normals(o)

    def back(bm):
        n = 3; z0, z1 = 1.5, 48.75; h = (z1 - z0) / n
        for i in range(n):
            for sx in (-1, 1):
                cbox(bm, (BAY_X - 0.08, 0.26, h - 0.12), (sx * BAY_X / 2, -(HY - 0.2), z0 + (i + 0.5) * h), 0.06)
    o = C.part("BackPanel", back, [mP]); fix_normals(o)


def build_rails():
    def rails(bm):
        for sx in (-1, 1):
            cbox(bm, (0.32, 0.45, FACE_Z1 - FACE_Z0 + 0.4), (sx * (BAY_X - 0.16), FACE_Y + 0.25, (FACE_Z0 + FACE_Z1) / 2), 0.04)
            # square-hole strip as small dark blocks would cost tris; rails stay plain
    o = C.part("Rails", rails, [C.mat("TK_RackFrame")]); fix_normals(o)


def build_server_face():
    def face(bm):
        quad_y(bm, -BAY_X, BAY_X, FACE_Z0, FACE_Z1, FACE_Y)
    o = C.part("ServerFace", face, [C.mat("TK_ServerFace")])
    C.planar_uv(o, "Y"); o["keep_uv"] = True

    groups = {"G": [], "B": [], "A": []}
    for s, t, c in LEDS_SEL:
        groups[c].append((s, t))
    for c, nm, mn in (("G", "LEDs_Green", "TK_LED_Green"), ("B", "LEDs_Blue", "TK_LED_Blue"), ("A", "LEDs_Amber", "TK_LED_Amber")):
        pts = groups[c]
        def leds(bm, pts=pts):
            for s, t in pts:
                x, z = led_world(s, t)
                quad_y(bm, x - 0.08, x + 0.08, z - 0.05, z + 0.05, FACE_Y + 0.03)
        if pts: C.part(nm, leds, [C.mat(mn)])
    return {k: len(v) for k, v in groups.items()}


def build_doors(glass=False, open_deg=0.0, hasp=False):
    """Two leaves. Door_XP hinge at x=+BAY_X (leaf spans local x -5..0), Door_XN hinge at x=-BAY_X."""
    inset = C.mat("TK_Glass") if glass else C.mat("TK_RackDoor")
    mats = [C.mat("TK_RackFrame"), inset, C.mat("TK_SteelRing")]
    out = {}
    for name, sgn in (("Door_XP", 1), ("Door_XN", -1)):
        # local coordinates: hinge at origin, leaf extends toward -sgn*X, front face at y=0
        def leaf(bm, sgn=sgn, name=name):
            g = 0.03; L = BAY_X - 2 * g          # leaf width
            def X(a, b):                          # local span from hinge distance a..b -> centre/size
                return (-sgn * (g + (a + b) / 2), b - a)
            st, rl = 0.55, 0.65
            z0, z1 = DOOR_Z0, DOOR_Z1
            yc = -DOOR_T / 2
            # stiles
            cx, sx = X(0, st); cbox(bm, (sx, DOOR_T, z1 - z0), (cx, yc, (z0 + z1) / 2), 0.06)
            cx, sx = X(L - st, L); cbox(bm, (sx, DOOR_T, z1 - z0), (cx, yc, (z0 + z1) / 2), 0.06)
            # rails: top, bottom, two intermediate
            cx, sx = X(st, L - st)
            for za, zb in ((z0, z0 + rl), (z1 - rl, z1), (16.0, 16.5), (31.5, 32.0)):
                cbox(bm, (sx, DOOR_T * 0.9, zb - za), (cx, yc, (za + zb) / 2), 0.05)
            # inset sheet (thin box so both faces render)
            cbox(bm, (sx + 0.1, 0.05, z1 - z0 - 2 * rl + 0.1), (cx, yc - 0.02, (z0 + z1) / 2), 0.0, mi=1)
            # hinge knuckles
            for zk in (6.0, 25.0, 44.0):
                C.bm_cyl(bm, 0.2, 1.6, (0, 0.05, zk), 10, mat_index=2)
            # vertical handle with two standoffs on the meeting edge
            hx = -sgn * (L - 0.32)
            sweep(bm, [Vector((hx, 0.0, HANDLE_Z[0])), Vector((hx, 0.45, HANDLE_Z[0] + 0.4)),
                       Vector((hx, 0.45, HANDLE_Z[1] - 0.4)), Vector((hx, 0.0, HANDLE_Z[1]))], 0.13, 8, mi=2,
                  up=Vector((1, 0, 0)))
            cbox(bm, (0.42, 0.08, 1.0), (hx, 0.02, HANDLE_Z[0] - 0.1), 0.02, mi=2)
            cbox(bm, (0.42, 0.08, 1.0), (hx, 0.02, HANDLE_Z[1] + 0.1), 0.02, mi=2)
            # keyed latch below the handle
            C.bm_cyl(bm, 0.2, 0.1, (hx, 0.04, HANDLE_Z[0] - 1.4), 10, axis="Y", mat_index=2)
            if hasp and name == "Door_XN":
                # hasp plate (hinged on XN, crosses the gap), with a slot for the staple at world x=+0.6
                hzc = 17.6
                # plate in world: x from -1.7 to +1.25 ; local = world - hinge(-5) -> +3.3 .. 6.25
                def W2L(xw): return xw - (-BAY_X)
                for (xa, xb, za, zb) in ((-1.7, 0.35, hzc - 0.9, hzc + 0.9), (0.35, 1.25, hzc + 0.42, hzc + 0.9),
                                         (0.35, 1.25, hzc - 0.9, hzc - 0.42), (0.85, 1.25, hzc - 0.42, hzc + 0.42)):
                    cbox(bm, (xb - xa, 0.14, zb - za), (W2L((xa + xb) / 2), 0.07, (za + zb) / 2), 0.02, mi=2)
                C.bm_cyl(bm, 0.18, 1.8, (W2L(-1.7), 0.12, hzc), 10, mat_index=2)          # hasp hinge pin
                for zz in (hzc - 0.65, hzc + 0.65):
                    C.bm_cyl(bm, 0.1, 0.06, (W2L(-1.3), 0.17, zz), 8, axis="Y", mat_index=2)  # rivets
            if hasp and name == "Door_XP":
                hzc = 17.6
                def W2L(xw): return xw - BAY_X
                cbox(bm, (0.9, 0.08, 1.6), (W2L(0.6), 0.04, hzc), 0.02, mi=2)      # staple base plate
                # staple loop: two horizontal legs out along +Y and a vertical front bar (eye axis = X)
                sweep(bm, [Vector((W2L(0.6), 0.0, hzc + 0.42)), Vector((W2L(0.6), 1.2, hzc + 0.42)),
                           Vector((W2L(0.6), 1.25, hzc + 0.3)), Vector((W2L(0.6), 1.25, hzc - 0.3)),
                           Vector((W2L(0.6), 1.2, hzc - 0.42)), Vector((W2L(0.6), 0.0, hzc - 0.42))], 0.11, 8, mi=2,
                      up=Vector((1, 0, 0)))
        o = C.part(name, leaf, mats)
        fix_normals(o)
        o.location = (sgn * BAY_X, HY, 0.0)
        if open_deg:
            o.rotation_euler = (0, 0, math.radians(-sgn * open_deg))
        out[name] = o
    return out


# ------------------------------------------------------------------ locked interior
def build_tape_interior():
    mats_sh = [C.mat("TK_RackFrame"), C.mat("TK_RackPanel")]
    shelf_z = [FACE_Z0 + i * 5.75 for i in range(8)]
    BACK_Y = 3.4

    def shelves(bm):
        C.bm_box(bm, (2 * BAY_X, 0.2, FACE_Z1 - FACE_Z0 + 0.8), (0, BACK_Y - 0.1, (FACE_Z0 + FACE_Z1) / 2), mat_index=1)  # back wall
        for z in shelf_z:
            cbox(bm, (2 * BAY_X - 0.1, FACE_Y + 0.6 - BACK_Y, 0.22), (0, (BACK_Y + FACE_Y + 0.6) / 2, z - 0.11), 0.04)
            cbox(bm, (2 * BAY_X - 0.1, 0.12, 0.4), (0, FACE_Y + 0.55, z - 0.05), 0.03)      # lip
        cbox(bm, (2 * BAY_X, FACE_Y + 0.6 - BACK_Y, 0.3), (0, (BACK_Y + FACE_Y + 0.6) / 2, FACE_Z1 + 0.3), 0.03)
        for sx in (-1, 1):
            cbox(bm, (0.3, FACE_Y + 0.6 - BACK_Y, FACE_Z1 - FACE_Z0 + 0.6), (sx * (BAY_X - 0.15), (BACK_Y + FACE_Y + 0.6) / 2, (FACE_Z0 + FACE_Z1) / 2), 0.04)
    o = C.part("Shelves", shelves, mats_sh); fix_normals(o)

    reel_rows = [shelf_z[i] for i in (1, 3, 5, 7)]
    cart_rows = [shelf_z[i] for i in (0, 2, 4, 6)]
    rr = random.Random(5)

    def reels(bm):
        for z in reel_rows:
            n = 3
            for k in range(n):
                x = -BAY_X + 0.3 + (k + 0.5) * (2 * BAY_X - 0.6) / n + rr.uniform(-0.2, 0.2)
                rad = 2.15; yc = 5.6
                zc = z + rad
                for dy in (-0.33, 0.33):
                    C.bm_cyl(bm, rad, 0.08, (x, yc + dy, zc), 24, mat_index=1, axis="Y")       # metal flanges
                pack = rr.uniform(1.2, 1.9)
                C.bm_cyl(bm, pack, 0.58, (x, yc, zc), 24, mat_index=2, axis="Y")                # wound tape
                C.bm_cyl(bm, 0.6, 0.9, (x, yc, zc), 12, mat_index=0, axis="Y")                  # hub
                # flange spoke windows suggested by three dark slots on the front flange
                for a in range(3):
                    ang = a * 2 * math.pi / 3 + 0.5
                    cx, cz = x + math.cos(ang) * 1.65, zc + math.sin(ang) * 1.65
                    cbox(bm, (0.5, 0.04, 0.5), (cx, yc + 0.39, cz), 0.0, mi=0)
    o = C.part("TapeReels", reels, [C.mat("TK_TapeReel"), C.mat("TK_TapeMetal"), C.mat("TK_TapeBand")], smooth=False)
    fix_normals(o)

    labels = []

    def carts(bm):
        for z in cart_rows:
            x = -BAY_X + 0.45
            while x < BAY_X - 0.8:
                w = 0.56
                h = 2.6; d = 2.5
                if rr.random() < 0.07:      # gap
                    x += w + 0.1; continue
                pull = rr.uniform(0.0, 0.12)   # cartridges not perfectly aligned
                cbox(bm, (w - 0.04, d, h), (x + w / 2, FACE_Y - d / 2 + 0.2 + pull, z + h / 2), 0.03, mi=0)
                labels.append((x + w / 2, z, w, h, pull))
                x += w + 0.035
    o = C.part("TapeCarts", carts, [C.mat("TK_TapeReel")]); fix_normals(o)

    def labs(bm):
        for (xc, z, w, h, pull) in labels:
            quad_y(bm, xc - w * 0.36, xc + w * 0.36, z + 0.3, z + h - 0.25, FACE_Y + 0.215 + pull)
    ol = C.part("TapeLabels", labs, [C.mat("TK_TapeLabel")])
    me = ol.data; me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        vs = [me.vertices[i].co for i in p.vertices]
        xs = [v.x for v in vs]; zs = [v.z for v in vs]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            me.uv_layers.active.data[li].uv = (1 - (co.x - min(xs)) / (max(xs) - min(xs)), (co.z - min(zs)) / (max(zs) - min(zs)))
    ol["keep_uv"] = True

    def amber(bm):
        for z in shelf_z[1:]:
            for xx in (-4.2, 4.2):
                if rr.random() < 0.7:
                    quad_y(bm, xx - 0.1, xx + 0.1, z - 0.15, z - 0.03, FACE_Y + 0.62)
        for k in range(4):
            quad_y(bm, -0.6 + k * 0.4 - 0.1, -0.6 + k * 0.4 + 0.1, 48.25, 48.4, HY + 0.005)   # header status strip
    C.part("LEDs_Amber", amber, [C.mat("TK_LED_Amber")])


def build_padlock():
    """Padlock hanging from the staple at world (0.6, HY+0.9, 17.6). Origin = hang point."""
    hang = Vector((0.6, HY + 0.93, 17.6))
    def lock(bm):
        # shackle: steel U in the XZ plane, top of the arc at the origin
        ra = 1.05; tube = 0.27
        cz = -ra                                 # arc centre (local)
        pts = []
        legb = cz - 1.25
        pts.append(Vector((-ra, 0, legb)))
        pts.append(Vector((-ra, 0, cz - 0.4)))
        for i in range(13):
            a = math.pi - i * math.pi / 12
            pts.append(Vector((math.cos(a) * ra, 0, cz + math.sin(a) * ra)))
        pts.append(Vector((ra, 0, cz - 0.4)))
        pts.append(Vector((ra, 0, legb)))
        sweep(bm, pts, tube, 10, mi=1, up=Vector((0, 1, 0)))
        # body: laminated brass block, chamfered, slightly wider than the shackle
        bw, bd, bh = 3.4, 1.25, 3.0
        top = legb + 0.2
        cbox(bm, (bw, bd, bh), (0, 0, top - bh / 2), 0.16, mi=0)
        # laminations (shallow bands proud of the sides)
        for k in range(5):
            zz = top - 0.35 - k * 0.58
            cbox(bm, (bw + 0.06, bd + 0.06, 0.12), (0, 0, zz), 0.03, mi=0)
        # top collar where the shackle enters
        for sx in (-1, 1):
            C.bm_cyl(bm, 0.38, 0.12, (sx * ra, 0, top + 0.05), 12, mat_index=1)
        # keyway: steel boss + dark slot on the front
        C.bm_cyl(bm, 0.42, 0.1, (0, bd / 2 + 0.03, top - bh * 0.68), 16, mat_index=1, axis="Y")
        cbox(bm, (0.13, 0.04, 0.5), (0, bd / 2 + 0.09, top - bh * 0.7), 0.0, mi=2)
        C.bm_cyl(bm, 0.11, 0.04, (0, bd / 2 + 0.09, top - bh * 0.62), 10, mat_index=2, axis="Y")
    o = C.part("Padlock", lock, [C.mat("TK_Padlock"), C.mat("TK_SteelRing"), C.mat("TK_RackFrame")])
    fix_normals(o)
    o.location = hang
    return o


# ------------------------------------------------------------------ label panel
def build_label():
    zc, pw, ph = 22.0, 10.5, 5.0
    yb = HY + 0.75                        # panel back
    yf = yb + 0.3                         # panel front
    def panel(bm):
        quad_y(bm, -pw / 2, pw / 2, zc - ph / 2, zc + ph / 2, yf)
        C.bm_box(bm, (pw, 0.3, ph), (0, (yb + yf) / 2 - 0.005, zc))
    o = C.part("LabelPanel", panel, [C.mat("TK_LabelPanel")]); fix_normals(o)
    C.planar_uv(o, "Y"); o["keep_uv"] = True

    def bezel(bm):
        b = 0.22; dpt = 0.45; yc = yf - dpt / 2 + 0.08
        cbox(bm, (pw + 2 * b, dpt, b), (0, yc, zc + ph / 2 + b / 2), 0.05)
        cbox(bm, (pw + 2 * b, dpt, b), (0, yc, zc - ph / 2 - b / 2), 0.05)
        cbox(bm, (b, dpt, ph), (-pw / 2 - b / 2, yc, zc), 0.05)
        cbox(bm, (b, dpt, ph), (pw / 2 + b / 2, yc, zc), 0.05)
    o = C.part("LabelBezel", bezel, [C.mat("TK_Frame")]); fix_normals(o)

    def mounts(bm):
        for sx in (-1, 1):
            for zz in (zc - 1.6, zc + 1.6):
                C.bm_box(bm, (0.4, yb - HY + 0.05, 0.5), (sx * (BAY_X + 0.5), (HY + yb) / 2, zz))
    o = C.part("LabelMounts", mounts, [C.mat("TK_StampMetal")]); fix_normals(o)

    a = bpy.data.objects.new("LabelAnchor", None)
    bpy.context.scene.collection.objects.link(a)
    a.parent = C.ROOT
    a.location = (0, yf + 0.002, zc)
    a.empty_display_size = 1.0
    return a


# ------------------------------------------------------------------ optional close-up check renders (env RACK_CLOSEUP=dir)
def closeup(name):
    sc = bpy.context.scene
    cam = sc.camera
    for i, (loc, tgt) in enumerate((((14, 40, 26), (0, 8, 22)), ((4, 22, 18), (0, 8, 16)), ((-10, 30, 40), (0, 7, 40)))):
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(os.environ["RACK_CLOSEUP"], f"{name}_c{i}.png")
        bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------ build all four
results = {}
for name in ("server_rack_hero", "server_rack_open", "server_rack_locked", "server_rack_label"):
    clear_scene()
    r = C.root(name)
    build_body(name)
    if name == "server_rack_locked":
        build_tape_interior()
        build_doors(glass=True, hasp=True)
        build_padlock()
        note = "glass doors, tape shelves, padlock on hasp"
    else:
        build_rails()
        counts = build_server_face()
        build_doors(glass=False, open_deg=110.0 if name == "server_rack_open" else 0.0)
        note = f"LEDs G{counts['G']} B{counts['B']} A{counts['A']}"
        if name == "server_rack_open": note += "; doors open 110 deg"
        if name == "server_rack_label":
            build_label(); note += "; LabelPanel + LabelAnchor"
    results[name] = C.finish(name, r, note=note)
    if os.environ.get("RACK_CLOSEUP"): closeup(name)
print("[server_rack] done", results)
