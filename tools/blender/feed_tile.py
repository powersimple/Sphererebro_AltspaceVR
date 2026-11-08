"""feed_tile: portrait 9:16 "feed" tiles (1.08 x 1.92 x 0.06 m) with a bevelled dark body and an inset glowing screen, as
separate variants side by side along X (1.5 m spacing), each with its ORIGIN at its own base centre (Unity instances them).
Screens sample talk/gen/feed_screens.png: a 4 x 2 atlas (2048 x 1024) of eight abstract, photographic-feeling images made with
numpy (sunset sea, bokeh city lights, underwater rays, neon ring, soft clouds, aurora, desert dunes, misty ridges): no faces,
no text, no logos. Cells are square in the atlas but painted in 9:16 screen space, so they look right on the tiles.
Objects: Tile_Screen_0..5 (cells 0..5), Tile_Play_0/1 (cells 6/7 + a raised white play triangle in a translucent dark disc),
Tile_Heart_0/1 (cells 4/5 + a raised pink-red heart). Materials: TK_TileBody, TK_TileScreen, and runtime TK_IconDisc,
TK_IconWhite, TK_HeartIcon."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import prop_shapes as S
import numpy as np
from mathutils import Matrix, Vector

C.begin()

# ------------------------------------------------------------------ the atlas
N = 512; AS = 9 / 16
X, Y = S.grid(N, N, AS)              # X 0..0.5625 (left..right), Y 0..1 (top..bottom): 9:16 screen space

def lerp_stops(t, stops):
    """t HxW in 0..1, stops [(pos, (r,g,b)), ...] -> HxWx3."""
    t = np.clip(t, 0, 1); out = np.zeros(t.shape + (3,), np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = ((t >= p0) & (t <= p1))[..., None]
        k = ((t - p0) / max(1e-6, p1 - p0))[..., None]
        out = np.where(m, np.asarray(c0, np.float32) * (1 - k) + np.asarray(c1, np.float32) * k, out)
    return out

def grain(img, rng, a=0.035):
    return img + (rng.random(img.shape[:2] + (1,)).astype(np.float32) - 0.5) * a

def vignette(img, k=0.35):
    d = ((X - AS / 2) / (AS * 0.75)) ** 2 + ((Y - 0.5) / 0.75) ** 2
    return img * (1 - k * np.clip(d, 0, 1))[..., None]

def cell_sunset(rng):
    hz = 0.60
    sky = lerp_stops(Y / hz, [(0, (0.07, 0.06, 0.22)), (0.35, (0.38, 0.16, 0.42)), (0.70, (0.92, 0.38, 0.30)), (0.92, (1.0, 0.62, 0.25)), (1.0, (1.0, 0.80, 0.45))])
    sx, sy = AS * 0.42, hz - 0.035
    r = np.hypot(X - sx, Y - sy)
    sky += (np.exp(-r / 0.05) * 0.9)[..., None] * np.array([1.0, 0.7, 0.35], np.float32)
    sky += (np.exp(-r / 0.20) * 0.35)[..., None] * np.array([1.0, 0.5, 0.25], np.float32)
    sky = np.where((r < 0.034)[..., None], np.array([1.0, 0.93, 0.75], np.float32), sky)
    cl = S.fbm(N, N, 26, 3, rng, 5)                         # stretched streak clouds
    cmask = np.clip((cl - 0.52) * 4, 0, 1) * np.clip((hz - Y) / 0.25, 0, 1) * np.clip(Y / 0.15, 0, 1)
    ccol = lerp_stops(Y / hz, [(0, (0.25, 0.12, 0.30)), (0.6, (0.85, 0.35, 0.45)), (1, (1.0, 0.65, 0.45))])
    sky = sky * (1 - cmask[..., None] * 0.75) + ccol * cmask[..., None] * 0.75
    # sea: mirrored sky, darker, with a glitter column under the sun
    my = np.clip(2 * hz - Y, 0, 1)
    refl = lerp_stops(my / hz, [(0, (0.05, 0.05, 0.16)), (0.5, (0.30, 0.13, 0.30)), (0.85, (0.75, 0.32, 0.25)), (1, (0.95, 0.55, 0.30))]) * 0.55
    waves = S.fbm(N, N, 90, 6, rng, 4)
    glit = np.exp(-((X - sx) / (0.03 + (Y - hz) * 0.35)) ** 2) * np.clip((waves - 0.45) * 3, 0, 1)
    sea = refl * (0.75 + 0.5 * waves[..., None]) + glit[..., None] * np.array([1.0, 0.75, 0.45], np.float32) * 1.1
    sea *= (1 - 0.45 * np.clip((Y - hz) / (1 - hz), 0, 1))[..., None]
    img = np.where((Y < hz)[..., None], sky, sea)
    img += (np.exp(-np.abs(Y - hz) / 0.008) * 0.25)[..., None] * np.array([1, 0.7, 0.4], np.float32)
    return vignette(grain(img, rng), 0.3)

def cell_bokeh(rng):
    img = lerp_stops(Y, [(0, (0.02, 0.02, 0.06)), (0.5, (0.07, 0.04, 0.14)), (1, (0.12, 0.05, 0.12))])
    pal = [(1.0, 0.62, 0.22), (1.0, 0.80, 0.45), (1.0, 0.35, 0.30), (0.95, 0.40, 0.65), (0.35, 0.75, 1.0), (1.0, 0.95, 0.85)]
    acc = np.zeros_like(img)
    for i in range(70):
        cx, cy = rng.uniform(-0.05, AS + 0.05), rng.uniform(0.05, 0.98)
        r = rng.uniform(0.012, 0.075) * (1.3 if cy > 0.5 else 0.8)
        col = np.asarray(pal[rng.integers(len(pal))], np.float32) * rng.uniform(0.35, 0.95)
        d = np.hypot(X - cx, Y - cy) / r
        disc = np.clip((1.0 - d) / 0.08, 0, 1) * (0.75 + 0.35 * np.clip((d - 0.75) / 0.25, 0, 1))
        acc += disc[..., None] * col * rng.uniform(0.35, 0.8)
    img = img + acc
    img += (np.exp(-((Y - 0.78) / 0.12) ** 2) * 0.12)[..., None] * np.array([1.0, 0.5, 0.3], np.float32)
    return vignette(grain(img, rng, 0.04), 0.35)

def cell_underwater(rng):
    img = lerp_stops(Y, [(0, (0.35, 0.80, 0.90)), (0.25, (0.05, 0.45, 0.65)), (0.65, (0.01, 0.18, 0.36)), (1, (0.00, 0.05, 0.14))])
    ang = np.arctan2(X - AS * 0.55, Y + 0.25)
    n1 = S.vnoise(1, 4096, 1, 120, rng)[0]
    idx = np.clip(((ang + 1.2) / 2.4 * 4095).astype(int), 0, 4095)
    rays = np.clip((n1[idx] - 0.45) * 2.5, 0, 1) * np.clip(1 - Y * 1.1, 0, 1) ** 1.5
    img += rays[..., None] * np.array([0.35, 0.65, 0.70], np.float32) * 0.7
    c = S.fbm(N, N, 10, 6, rng, 3)
    caus = np.clip(1 - np.abs(c - 0.5) * 14, 0, 1) * np.clip(0.22 - Y, 0, 1) / 0.22
    img += caus[..., None] * np.array([0.7, 0.95, 1.0], np.float32) * 0.6
    for i in range(26):
        bx, by = rng.uniform(0.05, AS - 0.05), rng.uniform(0.25, 0.95); br = rng.uniform(0.004, 0.014)
        d = np.hypot(X - bx, Y - by)
        ring_ = np.exp(-((d - br) / (br * 0.25)) ** 2) * 0.5 + np.exp(-((X - bx + br * 0.4) ** 2 + (Y - by + br * 0.4) ** 2) / (br * 0.3) ** 2) * 0.6
        img += ring_[..., None] * np.array([0.7, 0.9, 1.0], np.float32)
    return vignette(grain(img, rng, 0.03), 0.4)

def cell_neon(rng):
    img = lerp_stops(Y, [(0, (0.05, 0.01, 0.10)), (0.6, (0.10, 0.02, 0.18)), (1, (0.02, 0.01, 0.05))])
    for (bx, by, br, col) in ((AS * 0.15, 0.30, 0.35, (0.85, 0.10, 0.65)), (AS * 0.9, 0.62, 0.40, (0.05, 0.65, 0.95)), (AS * 0.5, 0.95, 0.30, (0.40, 0.10, 0.85))):
        img += (np.exp(-((X - bx) ** 2 + (Y - by) ** 2) / br ** 2) * 0.55)[..., None] * np.asarray(col, np.float32)
    cx, cy, R0 = AS / 2, 0.46, 0.17
    d = np.abs(np.hypot(X - cx, Y - cy) - R0)
    tube_ = np.exp(-(d / 0.006) ** 2)
    glow = np.exp(-d / 0.03) * 0.6 + np.exp(-d / 0.09) * 0.25
    t = np.clip((np.arctan2(Y - cy, X - cx) + math.pi) / (2 * math.pi), 0, 1)
    col = lerp_stops(t, [(0, (1.0, 0.2, 0.75)), (0.5, (0.2, 0.8, 1.0)), (1, (1.0, 0.2, 0.75))])
    img += col * glow[..., None] + tube_[..., None] * np.array([1.0, 0.95, 1.0], np.float32)
    # wet floor reflection below
    fl = Y > 0.78
    ry = 2 * 0.78 - Y
    dr = np.abs(np.hypot(X - cx, ry - cy) - R0)
    refl = (np.exp(-dr / 0.03) * 0.3)[..., None] * col * S.fbm(N, N, 60, 4, rng, 3)[..., None]
    img = np.where(fl[..., None], img * 0.6 + refl, img)
    return vignette(grain(img, rng, 0.04), 0.3)

def cell_clouds(rng):
    img = lerp_stops(Y, [(0, (0.14, 0.36, 0.75)), (0.6, (0.38, 0.62, 0.90)), (1, (0.70, 0.82, 0.95))])
    f = S.fbm(N, N, 5, 3, rng, 6, 0.55)
    dens = np.clip((f - 0.47) * 3.2, 0, 1)
    shade = np.clip(1 - (S.fbm(N, N, 5, 3, np.random.default_rng(99), 4) - 0.4) * 1.5, 0.55, 1.0)
    cloud = np.array([1.0, 0.98, 0.96], np.float32) * shade[..., None]
    cloud = cloud * (0.82 + 0.18 * (1 - Y))[..., None]
    img = img * (1 - dens[..., None]) + cloud * dens[..., None]
    sun = np.exp(-np.hypot(X - AS * 0.8, Y - 0.12) / 0.12)
    img += sun[..., None] * np.array([0.45, 0.40, 0.30], np.float32)
    return vignette(grain(img, rng, 0.025), 0.2)

def cell_aurora(rng):
    img = lerp_stops(Y, [(0, (0.01, 0.01, 0.05)), (0.6, (0.02, 0.05, 0.12)), (1, (0.02, 0.06, 0.10))])
    st = rng.random((N, N)) > 0.9965
    stars = st.astype(np.float32) * rng.random((N, N)).astype(np.float32)
    stars = S.blur(stars, 1) * 6
    img += stars[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
    xs = X[0]
    base = 0.50 + 0.10 * np.sin(xs * 9.0 + 0.5) + 0.05 * np.sin(xs * 23.0)
    rays = S.vnoise(1, N, 1, 70, rng)[0] * 0.7 + 0.3
    for k, (off, col, amp) in enumerate(((0.0, (0.15, 1.0, 0.45), 1.0), (-0.12, (0.35, 0.9, 0.7), 0.5))):
        yc = (base + off)[None, :]
        below = np.exp(-((Y - yc) / 0.018) ** 2)
        above = np.exp(-np.clip(yc - Y, 0, None) / 0.17) * (Y < yc)
        inten = (below * 0.8 + above * 0.9) * rays[None, :] * amp
        top = np.clip((yc - Y) / 0.30, 0, 1)
        c = np.asarray(col, np.float32) * (1 - top[..., None]) + np.array([0.55, 0.15, 0.75], np.float32) * top[..., None]
        img += inten[..., None] * c * 0.8
    ridge = 0.80 + 0.06 * (S.vnoise(1, N, 1, 6, rng)[0] - 0.5) * 2 + 0.03 * (S.vnoise(1, N, 1, 30, rng)[0] - 0.5)
    m = Y > ridge[None, :]
    img = np.where(m[..., None], np.array([0.01, 0.015, 0.025], np.float32) + img * 0.08, img)
    return vignette(grain(img, rng, 0.03), 0.3)

def cell_dunes(rng):
    img = lerp_stops(Y, [(0, (0.30, 0.25, 0.52)), (0.30, (0.80, 0.50, 0.55)), (0.48, (1.0, 0.72, 0.48)), (1, (1.0, 0.80, 0.55))])
    img += (np.exp(-np.hypot(X - AS * 0.3, Y - 0.46) / 0.1) * 0.5)[..., None] * np.array([1, 0.85, 0.6], np.float32)
    xs = X[0]
    layers = [(0.50, (0.78, 0.48, 0.38), (0.55, 0.32, 0.30)), (0.58, (0.85, 0.50, 0.32), (0.55, 0.28, 0.24)),
              (0.68, (0.90, 0.55, 0.30), (0.50, 0.24, 0.18)), (0.82, (0.95, 0.58, 0.30), (0.42, 0.18, 0.12))]
    for i, (h0, lit, sh) in enumerate(layers):
        ph = rng.uniform(0, 6); fr = rng.uniform(5, 10) / (1 + i * 0.3)
        crest = h0 + 0.035 * np.sin(xs * fr + ph) + 0.02 * np.sin(xs * fr * 2.3 + ph * 2)
        crest_x = (np.sin(xs * fr + ph) > 0)
        m = Y > crest[None, :]
        # lit / shadow split along a curved line under the crest
        split = np.sin((X * fr + ph) + (Y - crest[None, :]) * 9) > 0
        col = np.where(split[..., None], np.asarray(lit, np.float32), np.asarray(sh, np.float32))
        col = col * (1 - 0.25 * np.clip((Y - crest[None, :]) / 0.25, 0, 1))[..., None]
        img = np.where(m[..., None], col, img)
    tex = S.fbm(N, N, 120, 20, rng, 3)
    img *= (0.94 + 0.12 * tex)[..., None]
    return vignette(grain(img, rng, 0.03), 0.3)

def cell_ridges(rng):
    img = lerp_stops(Y, [(0, (0.55, 0.62, 0.75)), (0.45, (0.92, 0.82, 0.70)), (1, (0.75, 0.75, 0.78))])
    img += (np.exp(-np.hypot(X - AS * 0.65, Y - 0.36) / 0.14) * 0.45)[..., None] * np.array([1, 0.9, 0.7], np.float32)
    xs = X[0]
    for i in range(6):
        h0 = 0.40 + i * 0.10
        rid = h0 + 0.09 * (S.vnoise(1, N, 1, 3 + i, rng)[0] - 0.5) * 2 + 0.02 * (S.vnoise(1, N, 1, 25, rng)[0] - 0.5)
        depth = i / 5
        col = np.array([0.55, 0.62, 0.72], np.float32) * (1 - depth) + np.array([0.08, 0.12, 0.14], np.float32) * depth
        m = Y > rid[None, :]
        fog = np.clip((Y - rid[None, :]) / 0.12, 0, 1)
        layer = col * (1 - 0.25 * fog[..., None]) + np.array([0.85, 0.85, 0.88], np.float32) * (0.25 * fog[..., None] * (1 - depth))
        img = np.where(m[..., None], layer, img)
    return vignette(grain(img, rng, 0.03), 0.3)

cells = [cell_sunset, cell_bokeh, cell_underwater, cell_neon, cell_clouds, cell_aurora, cell_dunes, cell_ridges]
atlas = np.zeros((1024, 2048, 3), np.float32)
for i, fn in enumerate(cells):
    im = np.clip(fn(np.random.default_rng(100 + i)), 0, 1)
    r, c = divmod(i, 4)
    atlas[r * 512:(r + 1) * 512, c * 512:(c + 1) * 512] = im
C.save_png("feed_screens.png", atlas)

def cell_uv(i):
    r, c = divmod(i, 4)
    return (c / 4, 1 - (r + 1) / 2, (c + 1) / 4, 1 - r / 2)

# ------------------------------------------------------------------ runtime materials (icons)
C.MATS["TK_IconDisc"] = {"tex": None, "tint": [0.02, 0.02, 0.03], "metal": 0, "rough": 0.3, "tile": 0, "alpha": "blend", "opacity": 0.6}
C.MATS["TK_IconWhite"] = {"tex": None, "tint": [1, 1, 1], "metal": 0, "rough": 0.3, "tile": 0, "emit": [1.5, 1.5, 1.5], "unlit": True}
C.MATS["TK_HeartIcon"] = {"tex": None, "tint": [1.0, 0.18, 0.35], "metal": 0, "rough": 0.3, "tile": 0, "emit": [2.6, 0.35, 0.7], "unlit": True}

# ------------------------------------------------------------------ tiles
TW, TH, TD, TR = 1.08, 1.92, 0.06, 0.095
BEZ = 0.032
SCR = (TW - 2 * BEZ, TH - 2 * BEZ)
YF = TD / 2 - 0.004          # screen plane after the inset

def rounded_poly(pts, r, seg=3):
    """Convex polygon (a, b) grown by radius r with round corners (output CCW)."""
    area = sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))
    if area < 0: pts = pts[::-1]
    out = []; n = len(pts)
    for k in range(n):
        p0, p1, p2 = pts[k - 1], pts[k], pts[(k + 1) % n]
        a0 = math.atan2(-(p1[0] - p0[0]), (p1[1] - p0[1]))     # outward normal (dy, -dx) of edge p0->p1
        a1 = math.atan2(-(p2[0] - p1[0]), (p2[1] - p1[1]))
        while a1 < a0: a1 += 2 * math.pi
        for s in range(seg + 1):
            a = a0 + (a1 - a0) * s / seg
            out.append((p1[0] + r * math.cos(a), p1[1] + r * math.sin(a)))
    return out

def heart(size, n=32, ca=0.0, cb=0.0):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((ca + x / 34 * size, cb + (y + 2) / 34 * size))
    return pts

def tile(name, cell, icon=None, x=0.0):
    def build(bm):
        pr = S.prism(bm, S.rrect(TW, TH, TR, 6, 0.0, TH / 2), -TD / 2, TD / 2, "Y", 0, bevel=0.010, bseg=2)
        ff = pr["front"]
        bmesh.ops.inset_individual(bm, faces=[ff], thickness=BEZ - 0.010, depth=-0.004, use_even_offset=True)
        ff.material_index = 1
        if icon == "play":
            S.prism(bm, S.circle(0.22, 28, 0.0, TH / 2), YF, YF + 0.008, "Y", 2)
            tri = [(0.058, TH / 2 - 0.094), (-0.104, TH / 2), (0.058, TH / 2 + 0.094)]
            S.prism(bm, rounded_poly(tri, 0.020, 3), YF + 0.004, YF + 0.022, "Y", 3)
        if icon == "heart":
            S.prism(bm, heart(0.34, 32, -0.26, 0.38), YF, YF + 0.028, "Y", 2)
        S.autosmooth(bm, 40)
    extra = {"play": ["TK_IconDisc", "TK_IconWhite"], "heart": ["TK_HeartIcon"]}.get(icon, [])
    o = C.part(name, build, [C.mat(m) for m in ["TK_TileBody", "TK_TileScreen"] + extra])
    S.uv_faces(o, 1, "Y", bounds=((-SCR[0] / 2, BEZ), (SCR[0] / 2, TH - BEZ)), cell=cell_uv(cell))
    o.location.x = x
    return o

names = [("Tile_Screen_%d" % i, i, None) for i in range(6)] + [("Tile_Play_0", 6, "play"), ("Tile_Play_1", 7, "play"),
         ("Tile_Heart_0", 4, "heart"), ("Tile_Heart_1", 5, "heart")]
C.root("feed_tile")
for k, (nm, cell, icon) in enumerate(names):
    tile(nm, cell, icon, -(k - (len(names) - 1) / 2) * 1.5)      # index 0 on the viewer's left


C.finish("feed_tile", note="10 portrait 9:16 tiles 1.08 x 1.92 x 0.06 m, 1.5 m apart along X, each origin at its own base centre")
