"""commons_halls: four open public halls for the "commons" sequence, one run, four assets:
hall_library, hall_museum, hall_classroom, hall_studio.

Each hall: 28 m wide (X) x 18 m deep (Y) x 14 m to the ceiling, plaster walls with stone/wood/concrete trim, a roof slab
with cornice and parapet, a floor, and the FRONT (+Y) wall opened by a 12 m x 10 m doorway (arch, portico, framed opening or
industrial portal) so the audience looks into a warmly lit interior.
Common parts in every hall:
  Shell    plaster walls + roof slab (TK_Plaster)
  Floor    the floor (per hall)
  Trim     exterior/interior trim (stone, wood or concrete)
  Glow     every warm emissive element of the interior (TK_HallGlow), one object: the engine brightens it
  Doorway  EMPTY at the centre of the threshold, floor level
plus per-hall furnishing parts (listed in each builder).
Origin: base centre (floor z = 0); front faces +Y. Generated images: talk/gen/book_spines.png, talk/gen/gallery_art.png."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import numpy as np
from mathutils import Vector, Matrix

C.begin()

# runtime materials (not in talk_materials.json; listed in the report)
C.MATS["TK_Rug"] = {"tex": "Carpet016", "tint": [0.62, 0.22, 0.14], "metal": 0, "rough": None, "tile": 1.5}
C.MATS["TK_Cyc"] = {"tex": None, "tint": [0.9, 0.9, 0.88], "metal": 0, "rough": 0.85, "tile": 0}

W2, D2, H = 14.0, 9.0, 14.0        # half width, half depth, ceiling height
T = 0.6                            # wall thickness
FY = D2 - T                        # interior face of the front wall (8.4)
OW2, OH = 6.0, 10.0                # doorway half width, height


# =================================================================== geometry helpers
def abox(bm, p, q, mi=0):
    """Axis box between two opposite corners."""
    lo = [min(a, b) for a, b in zip(p, q)]; hi = [max(a, b) for a, b in zip(p, q)]
    return C.bm_box(bm, (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]), loc=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2), mat_index=mi)


def face(bm, pts, normal, mi=0, uvs=None):
    """A polygon facing `normal` (flipped if needed), with optional per-vertex UVs."""
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs); f.material_index = mi
    f.normal_update()
    if f.normal.dot(Vector(normal)) < 0: f.normal_flip()
    if uvs:
        lay = bm.loops.layers.uv.verify()
        for l in f.loops: l[lay].uv = uvs[vs.index(l.vert)]
    return f


def pipe(bm, p0, p1, r, segs=8, mi=0):
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    vs = C.bm_cyl(bm, r, d.length, segs=segs, mat_index=mi)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), verts=vs)
    return vs


def sphere(bm, r, loc, u=16, v=8, mi=0, scale=(1, 1, 1)):
    res = bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((*scale, 1)), verts=res["verts"])
    for f in {f for vv in res["verts"] for f in vv.link_faces}: f.material_index = mi
    return res["verts"]


def torus(bm, R, r, loc, segs=24, rsegs=10, mi=0, rot=Matrix.Identity(4)):
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ring = []
        for j in range(rsegs):
            b = 2 * math.pi * j / rsegs
            p = Vector(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
            ring.append(bm.verts.new(Vector(loc) + (rot @ p.to_4d()).to_3d()))
        rings.append(ring)
    for i in range(segs):
        for j in range(rsegs):
            a, b = rings[i], rings[(i + 1) % segs]
            f = bm.faces.new((a[j], b[j], b[(j + 1) % rsegs], a[(j + 1) % rsegs])); f.material_index = mi


def wall(bm, along, a0, a1, t0, t1, z0, z1, openings=(), mi=0):
    """A wall slab: long along 'x' or 'y' from a0..a1, thickness t0..t1, height z0..z1, with rectangular openings
    [(a_lo, a_hi, z_lo, z_hi)]. Built as a grid of boxes, skipping opening cells, merging runs along the wall."""
    As = sorted({a0, a1, *[o[0] for o in openings], *[o[1] for o in openings]})
    Zs = sorted({z0, z1, *[o[2] for o in openings], *[o[3] for o in openings]})
    for zi in range(len(Zs) - 1):
        za, zb = Zs[zi], Zs[zi + 1]
        run = None
        for ai in range(len(As) - 1):
            aa, ab = As[ai], As[ai + 1]
            am, zm = (aa + ab) / 2, (za + zb) / 2
            hole = any(o[0] < am < o[1] and o[2] < zm < o[3] for o in openings)
            if not hole:
                run = (run[0], ab) if run else (aa, ab)
            if (hole or ai == len(As) - 2) and run:
                if along == "x": abox(bm, (run[0], t0, za), (run[1], t1, zb), mi)
                else: abox(bm, (t0, run[0], za), (t1, run[1], zb), mi)
                run = None


# =================================================================== the shell shared by all four halls
def shell(front_openings_override=None, side_openings=(), back_openings=(), arch=None):
    """Plaster walls + roof slab + parapet. arch = (spring, rise) gives a segmental arch over the doorway instead of a
    flat lintel. Returns the Shell object."""
    def b(bm):
        # back + side walls
        wall(bm, "x", -W2, W2, -D2, -D2 + T, 0, H, back_openings)
        wall(bm, "y", -D2 + T, D2 - T, -W2, -W2 + T, 0, H, side_openings)
        wall(bm, "y", -D2 + T, D2 - T, W2 - T, W2, 0, H, [(o[0], o[1], o[2], o[3]) for o in side_openings])
        # front wall either side of the doorway
        abox(bm, (-W2, FY, 0), (-OW2, D2, H))
        abox(bm, (OW2, FY, 0), (W2, D2, H))
        if arch is None:
            abox(bm, (-OW2, FY, OH), (OW2, D2, H))
        else:
            spring, rise = arch
            R = (OW2 ** 2 + rise ** 2) / (2 * rise); cz = spring + rise - R
            n = 16
            xs = [-OW2 + 2 * OW2 * i / n for i in range(n + 1)]
            zf = lambda x: cz + math.sqrt(max(0.0, R * R - x * x))
            for i in range(n):
                xa, xb = xs[i], xs[i + 1]; za, zb = zf(xa), zf(xb)
                face(bm, [(xa, D2, za), (xb, D2, zb), (xb, D2, H), (xa, D2, H)], (0, 1, 0))
                face(bm, [(xa, FY, za), (xb, FY, zb), (xb, FY, H), (xa, FY, H)], (0, -1, 0))
                xm = (xa + xb) / 2
                face(bm, [(xa, FY, za), (xb, FY, zb), (xb, D2, zb), (xa, D2, za)], (-xm, 0, -(zf(xm) - cz)))
            face(bm, [(-OW2, FY, H), (OW2, FY, H), (OW2, D2, H), (-OW2, D2, H)], (0, 0, 1))
        # roof slab (ceiling at H) and parapet
        abox(bm, (-W2, -D2, H), (W2, D2, H + 0.6))
        P = 0.4; z0, z1 = H + 0.6, H + 1.5
        abox(bm, (-W2, D2 - P, z0), (W2, D2, z1)); abox(bm, (-W2, -D2, z0), (W2, -D2 + P, z1))
        abox(bm, (-W2, -D2 + P, z0), (-W2 + P, D2 - P, z1)); abox(bm, (W2 - P, -D2 + P, z0), (W2, D2 - P, z1))
    return C.part("Shell", b, [C.mat("TK_Plaster")])


def outer_trim(bm, mi=0, cornice=True, quoins=True):
    """Exterior trim: base course, cornice, parapet coping, corner quoins/pilasters (in material mi)."""
    e = 0.12
    for (p, q) in (((-W2 - e, D2 - 0.01, 0), (-OW2 - 0.9, D2 + e, 0.8)), ((OW2 + 0.9, D2 - 0.01, 0), (W2 + e, D2 + e, 0.8)),
                   ((-W2 - e, -D2 - e, 0), (W2 + e, -D2 + 0.01, 0.8)),
                   ((-W2 - e, -D2, 0), (-W2 + 0.01, D2, 0.8)), ((W2 - 0.01, -D2, 0), (W2 + e, D2, 0.8))):
        abox(bm, p, q, mi)
    if cornice:   # two-step cornice under the roof line + coping on the parapet
        for (o, z0, z1) in ((0.18, H - 0.6, H - 0.2), (0.4, H - 0.2, H + 0.25)):
            abox(bm, (-W2 - o, D2 - 0.01, z0), (W2 + o, D2 + o, z1), mi)
            abox(bm, (-W2 - o, -D2 - o, z0), (W2 + o, -D2 + 0.01, z1), mi)
            abox(bm, (-W2 - o, -D2, z0), (-W2 + 0.01, D2, z1), mi)
            abox(bm, (W2 - 0.01, -D2, z0), (W2 + o, D2, z1), mi)
        c = 0.08; z0, z1 = H + 1.5, H + 1.68
        abox(bm, (-W2 - c, D2 - 0.4 - c, z0), (W2 + c, D2 + c, z1), mi)
        abox(bm, (-W2 - c, -D2 - c, z0), (W2 + c, -D2 + 0.4 + c, z1), mi)
        abox(bm, (-W2 - c, -D2, z0), (-W2 + 0.4 + c, D2, z1), mi)
        abox(bm, (W2 - 0.4 - c, -D2, z0), (W2 + c, D2, z1), mi)
    if quoins:    # alternating quoin blocks on the four vertical corners
        for (sx, sy) in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
            for k in range(9):
                z0 = 0.8 + k * 1.4; z1 = z0 + 1.25
                if z1 > H - 0.6: break
                la = 1.1 if k % 2 == 0 else 0.7
                x0 = sx * W2; y0 = sy * D2
                abox(bm, (x0 + sx * 0.06, y0 - sy * 0.0, z0), (x0 - sx * la, y0 + sy * 0.06, z1), mi)   # on the Y face
                abox(bm, (x0 + sx * 0.06, y0 + sy * 0.06, z0), (x0 - sx * 0.0, y0 - sy * (1.8 - la), z1), mi)  # on the X face


def inner_trim(bm, mi=0, skirt=0.25, crown=True, dado=None):
    """Interior skirting, optional dado rail and crown moulding on back and side walls (and the front wall's inside)."""
    i = 0.04
    segs = (((-W2 + T, -D2 + T, 0), (W2 - T, -D2 + T + i, 1)), ((-W2 + T, -D2 + T, 0), (-W2 + T + i, FY, 1)),
            ((W2 - T - i, -D2 + T, 0), (W2 - T, FY, 1)), ((-W2 + T, FY - i, 0), (-OW2, FY, 1)), ((OW2, FY - i, 0), (W2 - T, FY, 1)))
    levels = [(0, skirt, 1.0)]
    if dado: levels.append((dado, dado + 0.08, 1.4))
    if crown: levels += [(H - 0.5, H - 0.25, 2.0), (H - 0.25, H, 4.0)]
    for (z0, z1, k) in levels:
        for (p, q) in segs:
            d = i * k
            pp = list(p); qq = list(q)
            # grow the thickness inward by d
            if abs(q[1] - p[1]) < 0.1:   # runs along x
                if p[1] < 0: qq[1] = p[1] + d
                else: pp[1] = q[1] - d
            else:
                if p[0] < 0: qq[0] = p[0] + d
                else: pp[0] = q[0] - d
            pp[2] = z0; qq[2] = z1
            abox(bm, pp, qq, mi)


def floor(mat_name, extra=None):
    def b(bm):
        abox(bm, (-W2, -D2, -0.3), (W2, D2, 0.0))
        abox(bm, (-OW2 - 0.6, D2, -0.3), (OW2 + 0.6, D2 + 1.6, -0.0), 0)     # apron in front of the doorway
        if extra: extra(bm)
    return C.part("Floor", b, [C.mat(mat_name)])


def doorway_empty(r):
    e = bpy.data.objects.new("Doorway", None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = r; e.location = (0, D2 - T / 2, 0)
    e.empty_display_type = "ARROWS"
    return e


def preview_lights(points, energy=2500):
    """Warm point lights for the preview render only (not parented to the asset, so not exported)."""
    out = []
    for i, p in enumerate(points):
        ld = bpy.data.lights.new(f"pvl{i}", "POINT"); ld.energy = energy; ld.color = (1.0, 0.78, 0.52); ld.shadow_soft_size = 1.5
        o = bpy.data.objects.new(f"pvl{i}", ld); bpy.context.scene.collection.objects.link(o); o.location = p
        out.append(o)
    return out


def inside_view(name):
    """An extra preview: the view an audience member gets, standing back from the doorway (talk/previews/<name>_inside.png)."""
    sc = bpy.context.scene
    cam_d = bpy.data.cameras.new("pv_in"); cam_d.lens = 28
    cam = bpy.data.objects.new("pv_in", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (0, 26, 4.5)
    d = (Vector((0, -4, 4.2)) - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 1024, 640
    sc.render.filepath = os.path.join(C.PREV_DIR, name + "_inside.png")
    bpy.ops.render.render(write_still=True)
    sc.render.resolution_x = sc.render.resolution_y = 512


def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if m.users == 0: bpy.data.meshes.remove(m)
    for l in list(bpy.data.lights): bpy.data.lights.remove(l)
    for c in list(bpy.data.cameras): bpy.data.cameras.remove(c)


def run(name, build, lights):
    r = C.root(name)
    build(r)
    doorway_empty(r)
    preview_lights(lights)
    bpy.context.view_layer.update()
    n = C.finish(name, r)
    inside_view(name)
    clear_scene()
    return n


# =================================================================== generated images
def blur(a, k, axis):
    """Box blur of width 2k+1 along axis (wraps)."""
    c = np.cumsum(np.concatenate([np.take(a, range(-k - 1, 0), axis=axis), a, np.take(a, range(0, k), axis=axis)], axis=axis), axis=axis)
    n = a.shape[axis]
    return (np.take(c, range(2 * k + 1, 2 * k + 1 + n), axis=axis) - np.take(c, range(0, n), axis=axis)) / (2 * k + 1)


def smooth_noise(rng, h, w, k, passes=2):
    a = rng.random((h, w)).astype(np.float32)
    for _ in range(passes): a = blur(blur(a, k, 0), k, 1)
    a -= a.min(); a /= max(1e-6, a.max())
    return a


BOOK_ROWS = 5


def gen_book_spines():
    """2048 x 1024: five shelf rows of leather/cloth spines, gold bands and raised bands, no titles."""
    rng = np.random.default_rng(11)
    Wd, Ht = 2048, 1024
    rh = Ht // BOOK_ROWS
    img = np.zeros((Ht, Wd, 3), np.float32)
    # back-of-shelf darkness, a little warm
    yy = np.linspace(0, 1, rh)[:, None]
    pal = np.array([
        (0.42, 0.08, 0.06), (0.30, 0.05, 0.05), (0.50, 0.14, 0.08), (0.12, 0.22, 0.13), (0.07, 0.15, 0.10), (0.08, 0.11, 0.24),
        (0.11, 0.16, 0.32), (0.32, 0.19, 0.09), (0.45, 0.28, 0.13), (0.58, 0.44, 0.26), (0.09, 0.07, 0.06), (0.66, 0.56, 0.40),
        (0.26, 0.06, 0.14), (0.55, 0.33, 0.10), (0.16, 0.26, 0.30), (0.36, 0.30, 0.22), (0.20, 0.12, 0.08)], np.float32)
    gold = np.array((0.86, 0.66, 0.30), np.float32)
    grain = smooth_noise(rng, Ht, Wd, 1, 1) * 0.5 + smooth_noise(rng, Ht, Wd, 6, 2) * 0.5
    for r in range(BOOK_ROWS):
        top = r * rh; bot = top + rh
        img[top:bot] = np.array((0.05, 0.035, 0.025)) * (0.6 + 0.5 * yy)[..., None]
        x = int(rng.integers(0, 8))
        series = 0
        while x < Wd:
            if rng.random() < 0.04:            # a gap on the shelf
                x += int(rng.integers(10, 40)); continue
            if series <= 0:                    # runs of matching volumes
                series = int(rng.integers(1, 9)); col = pal[rng.integers(len(pal))] * rng.uniform(0.8, 1.15)
                bw0 = int(rng.integers(16, 40)); bh0 = rng.uniform(0.62, 0.95); style = int(rng.integers(0, 4))
            series -= 1
            bw = max(10, bw0 + int(rng.integers(-2, 3))); bh = int(rh * min(0.97, bh0 + rng.uniform(-0.02, 0.02)))
            x1 = min(Wd, x + bw)
            y0 = bot - 3 - bh; y1 = bot - 3
            u = np.linspace(0, 1, x1 - x)[None, :]
            shade = 0.45 + 0.55 * np.sin(np.pi * np.clip(u * 0.94 + 0.03, 0, 1)) ** 0.7
            c = col * rng.uniform(0.92, 1.08)
            blk = np.ones((y1 - y0, x1 - x, 3), np.float32) * c
            g = grain[y0:y1, x:x1, None]
            blk *= (0.82 + 0.36 * g)
            hh = y1 - y0
            def band(z0, z1, colr, mix=1.0):
                z0 = int(np.clip(z0, 0, hh)); z1 = int(np.clip(z1, 0, hh))
                if z1 > z0: blk[z0:z1] = blk[z0:z1] * (1 - mix) + colr * mix
            if style == 0:      # gold double rules near head and tail
                for zc in (0.08, 0.12, 0.88, 0.92): band(hh * zc, hh * zc + 2, gold)
            elif style == 1:    # raised bands (leather), gilt edges on each
                for k in range(5):
                    zc = hh * (0.12 + k * 0.18)
                    band(zc - 4, zc + 4, c * 0.55)
                    band(zc - 5, zc - 4, gold); band(zc + 4, zc + 5, gold)
            elif style == 2:    # a dark label panel with a gilt border, blank
                band(hh * 0.16, hh * 0.32, gold)
                band(hh * 0.16 + 2, hh * 0.32 - 2, np.array((0.06, 0.05, 0.04)) + c * 0.3)
                band(hh * 0.86, hh * 0.86 + 3, gold)
            else:               # cloth: one broad gilt band near the head
                band(hh * 0.07, hh * 0.13, gold * 0.95)
            blk *= shade[..., None]
            blk[:2] *= 0.7                                 # head edge
            img[y0:y1, x:x1] = blk
            img[y0:y1, x1 - 1:x1] *= 0.35                  # gap line between books
            x = x1
        img[bot - 3:bot] = (0.03, 0.02, 0.015)
    img += (rng.random(img.shape).astype(np.float32) - 0.5) * 0.025
    C.save_png("book_spines.png", np.clip(img, 0, 1))


def gen_gallery_art():
    """2048 x 1024 atlas, 3 x 2 cells of 4:3 abstract painterly canvases (no figures, no faces, no text)."""
    rng = np.random.default_rng(5)
    Wd, Ht = 2048, 1024
    cw, ch = Wd // 3, Ht // 2
    atlas = np.zeros((Ht, Wd, 3), np.float32)
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    U = xx / cw; V = yy / ch

    def canvas_tex(img, amt=0.06):
        weave = (np.sin(xx * 1.7) * np.sin(yy * 1.7))[..., None] * 0.015
        n = smooth_noise(rng, ch, cw, 2, 1)[..., None]
        return np.clip(img * (1 - amt + amt * 2 * n) + weave, 0, 1)

    def strokes(img, n, cols, rmin, rmax, length, angle=None, alpha=0.8):
        for _ in range(n):
            c = np.array(cols[rng.integers(len(cols))], np.float32) * rng.uniform(0.85, 1.12)
            x0, y0 = rng.uniform(0, cw), rng.uniform(0, ch)
            a = rng.uniform(0, math.pi * 2) if angle is None else angle + rng.normal(0, 0.25)
            L = rng.uniform(*length); bend = rng.normal(0, 0.6)
            r = rng.uniform(rmin, rmax)
            steps = max(4, int(L / (r * 0.6)))
            for s in range(steps):
                t = s / steps
                aa = a + bend * t
                x = x0 + math.cos(aa) * L * t; y = y0 + math.sin(aa) * L * t
                xa, xb = int(max(0, x - r)), int(min(cw, x + r + 1)); ya, yb = int(max(0, y - r)), int(min(ch, y + r + 1))
                if xa >= xb or ya >= yb: continue
                d = ((xx[ya:yb, xa:xb] - x) ** 2 + (yy[ya:yb, xa:xb] - y) ** 2) / (r * r)
                m = np.clip(1 - d, 0, 1) ** 0.5 * alpha * (0.6 + 0.4 * rng.random((yb - ya, xb - xa)))
                img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - m[..., None]) + c * m[..., None]
        return img

    def soft_rect(x0, x1, y0, y1, feather):
        fx = np.clip(np.minimum(U - x0, x1 - U) / feather, 0, 1); fy = np.clip(np.minimum(V - y0, y1 - V) / feather, 0, 1)
        return (fx * fy)[..., None]

    cells = []
    # 1. colour field: two soft stacked blocks on a warm ground
    img = np.ones((ch, cw, 3), np.float32) * (0.62, 0.22, 0.12)
    img = img * (1 - soft_rect(0.08, 0.92, 0.07, 0.52, 0.04)) + np.array((0.86, 0.48, 0.16)) * soft_rect(0.08, 0.92, 0.07, 0.52, 0.04)
    img = img * (1 - soft_rect(0.08, 0.92, 0.6, 0.93, 0.04)) + np.array((0.32, 0.08, 0.1)) * soft_rect(0.08, 0.92, 0.6, 0.93, 0.04)
    img *= (0.88 + 0.24 * smooth_noise(rng, ch, cw, 12, 2))[..., None]
    cells.append(canvas_tex(img, 0.1))
    # 2. gestural: blue/ochre/white brushwork on cream
    img = np.ones((ch, cw, 3), np.float32) * (0.9, 0.86, 0.76)
    img = strokes(img, 60, [(0.12, 0.2, 0.42), (0.18, 0.32, 0.55), (0.82, 0.6, 0.2), (0.95, 0.93, 0.88), (0.08, 0.08, 0.1)], 6, 22, (80, 320))
    cells.append(canvas_tex(img))
    # 3. abstract horizon: banded earth and sky, scraped texture
    img = np.zeros((ch, cw, 3), np.float32)
    sky = np.array((0.55, 0.68, 0.78)) * (1 - V[..., None]) + np.array((0.92, 0.78, 0.6)) * V[..., None]
    img[:] = sky
    hz = 0.55 + 0.03 * np.sin(U * 7 + 1.3)
    bands = [(0.0, (0.45, 0.36, 0.22)), (0.08, (0.3, 0.34, 0.2)), (0.2, (0.52, 0.3, 0.16)), (0.32, (0.22, 0.2, 0.16))]
    for off, colr in bands:
        m = (V > hz + off + 0.02 * np.sin(U * 13 + off * 20)).astype(np.float32)[..., None]
        img = img * (1 - m) + np.array(colr) * m
    scrape = blur(rng.random((ch, cw)).astype(np.float32), 30, 1)
    img *= (0.85 + 0.3 * (scrape - scrape.mean()) / max(1e-6, scrape.std()) * 0.25)[..., None]
    img = strokes(img, 25, [(0.95, 0.9, 0.8), (0.4, 0.3, 0.2)], 3, 8, (100, 400), angle=0.0, alpha=0.35)
    cells.append(canvas_tex(img))
    # 4. geometric: overlapping circles and arcs, soft colours, painterly fill
    img = np.ones((ch, cw, 3), np.float32) * (0.93, 0.9, 0.84)
    for (cx, cy, rr, colr) in ((0.35, 0.45, 0.3, (0.85, 0.35, 0.2)), (0.62, 0.55, 0.26, (0.16, 0.38, 0.5)), (0.5, 0.3, 0.15, (0.95, 0.75, 0.25)),
                               (0.75, 0.25, 0.1, (0.15, 0.15, 0.18)), (0.22, 0.75, 0.12, (0.55, 0.62, 0.45))):
        d = np.sqrt(((U - cx) * 4 / 3) ** 2 + (V - cy) ** 2)
        m = np.clip((rr - d) / 0.006, 0, 1)[..., None] * 0.88
        img = img * (1 - m) + np.array(colr) * m
    ring = np.abs(np.sqrt(((U - 0.5) * 4 / 3) ** 2 + (V - 0.5) ** 2) - 0.42)
    img = img * (1 - (np.clip((0.006 - ring) / 0.003, 0, 1))[..., None]) + 0.1 * (np.clip((0.006 - ring) / 0.003, 0, 1))[..., None]
    img *= (0.9 + 0.2 * smooth_noise(rng, ch, cw, 4, 1))[..., None]
    cells.append(canvas_tex(img))
    # 5. organic: soft blobs in terracotta, teal and gold
    img = np.ones((ch, cw, 3), np.float32) * (0.16, 0.2, 0.22)
    f = np.zeros((ch, cw), np.float32)
    for _ in range(9):
        cx, cy, s = rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0.02, 0.06)
        f += s / (((U - cx) * 4 / 3) ** 2 + (V - cy) ** 2 + 1e-3)
    m1 = np.clip((f - 1.2) * 2, 0, 1)[..., None]; m2 = np.clip((f - 3.0) * 1.5, 0, 1)[..., None]
    img = img * (1 - m1) + np.array((0.72, 0.36, 0.22)) * m1
    img = img * (1 - m2) + np.array((0.93, 0.74, 0.38)) * m2
    img = strokes(img, 30, [(0.2, 0.45, 0.45), (0.1, 0.3, 0.32)], 4, 12, (60, 200), alpha=0.5)
    img *= (0.88 + 0.24 * smooth_noise(rng, ch, cw, 8, 2))[..., None]
    cells.append(canvas_tex(img))
    # 6. vertical zips and drips
    img = np.ones((ch, cw, 3), np.float32) * (0.12, 0.16, 0.3)
    for (x0, x1, colr) in ((0.18, 0.21, (0.95, 0.85, 0.6)), (0.47, 0.56, (0.78, 0.18, 0.12)), (0.8, 0.82, (0.9, 0.9, 0.86))):
        m = soft_rect(x0, x1, -0.1, 1.1, 0.004)
        img = img * (1 - m) + np.array(colr) * m
    drips = blur((rng.random((1, cw)) > 0.985).astype(np.float32).repeat(ch, 0), 1, 1) * (V < rng.uniform(0.2, 0.7, (1, cw)))
    img = img * (1 - drips[..., None] * 0.6) + np.array((0.85, 0.75, 0.55)) * drips[..., None] * 0.6
    img *= (0.85 + 0.3 * blur(smooth_noise(rng, ch, cw, 3, 1), 20, 0))[..., None]
    cells.append(canvas_tex(img))
    for i, c in enumerate(cells):
        cx, cy = i % 3, i // 3
        atlas[cy * ch:(cy + 1) * ch, cx * cw:(cx + 1) * cw] = c
    C.save_png("gallery_art.png", np.clip(atlas, 0, 1))


def art_uv(cell, mirror=False):
    """UVs (BL, BR, TR, TL) of atlas cell 0..5 (row-major from the top-left)."""
    cx, cy = cell % 3, cell // 3
    u0, u1 = cx / 3 + 0.002, (cx + 1) / 3 - 0.002
    v1, v0 = 1 - cy / 2 - 0.002, 1 - (cy + 1) / 2 + 0.002
    if mirror: u0, u1 = u1, u0
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


gen_book_spines()
gen_gallery_art()


# =================================================================== hall_library
def library(r):
    rng = np.random.default_rng(3)
    shell(arch=(7.0, 3.0))

    def trim(bm):  # stone (TK_Plinth): base course, cornice, quoins, archivolt, keystone, imposts, jamb pilasters
        outer_trim(bm, 0)
        spring, rise = 7.0, 3.0
        R = (OW2 ** 2 + rise ** 2) / (2 * rise); cz = spring + rise - R
        t0 = math.acos(OW2 / R); n = 16
        for i in range(n):
            a = t0 + (math.pi - 2 * t0) * i / n; b = t0 + (math.pi - 2 * t0) * (i + 1) / n
            pa = lambda rr, ang, y: (rr * math.cos(ang), y, cz + rr * math.sin(ang))
            ro = R + 1.0; yf = D2 + 0.2
            face(bm, [pa(R, a, yf), pa(ro, a, yf), pa(ro, b, yf), pa(R, b, yf)], (0, 1, 0))
            face(bm, [pa(ro, a, D2), pa(ro, b, D2), pa(ro, b, yf), pa(ro, a, yf)], (math.cos((a + b) / 2), 0, math.sin((a + b) / 2)))
            face(bm, [pa(R, a, D2), pa(R, b, D2), pa(R, b, yf), pa(R, a, yf)], (-math.cos((a + b) / 2), 0, -math.sin((a + b) / 2)))
        abox(bm, (-0.55, D2, cz + R - 0.2), (0.55, D2 + 0.4, cz + R + 1.3))                 # keystone
        for s in (-1, 1):
            abox(bm, (s * (OW2 - 0.15), D2 - 0.05, spring - 0.45), (s * (OW2 + 1.3), D2 + 0.35, spring))   # impost
            abox(bm, (s * OW2, D2, 0.8), (s * (OW2 + 1.0), D2 + 0.22, spring - 0.45))                # jamb pilaster
            abox(bm, (s * (OW2 - 0.25), FY - 0.05, 0), (s * OW2, D2, spring))                        # reveal lining
        abox(bm, (-W2 - 0.12, D2, 10.8), (W2 + 0.12, D2 + 0.15, 11.1))                                 # string course
        # interior: oak? no: dark wood crown and skirting
    C.part("Trim", trim, [C.mat("TK_Plinth")])

    def wood_trim(bm):
        inner_trim(bm, 0)
        for x in range(-12, 13, 4):  # ceiling beams across the depth, with a wall plate
            abox(bm, (x - 0.3, -D2 + T, H - 1.0), (x + 0.3, FY, H))
        abox(bm, (-W2 + T, -1.2, H - 0.8), (W2 - T, -0.8, H))
    C.part("Beams", wood_trim, [C.mat("TK_WoodTV")])

    floor("TK_WoodFloor")

    # ---- bookcases: lower level 0..6, upper (gallery) 6.6..12.4, on back and side walls
    BAY, SH, DEP = 2.4, 0.43, 0.5
    runs = []   # (origin, along unit, inward unit, length)
    runs.append((Vector((-W2 + T, -D2 + T, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), 2 * (W2 - T)))
    runs.append((Vector((-W2 + T, -D2 + T + DEP, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), FY - (-D2 + T + DEP)))
    runs.append((Vector((W2 - T, -D2 + T + DEP, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), FY - (-D2 + T + DEP)))
    levels = [(0.0, 6.0), (6.6, 12.4)]

    def cases(bm):
        lay = bm.loops.layers.uv.verify()
        for (o, a, n, L) in runs:
            nb = max(1, round(L / BAY)); bw = L / nb
            for (z0, z1) in levels:
                P = lambda s, d, z: o + a * s + n * d + Vector((0, 0, z))
                abox(bm, P(0, 0, z0), P(L, DEP + 0.05, z0 + 0.25), 0)               # plinth
                abox(bm, P(0, 0, z1 - 0.25), P(L, DEP + 0.12, z1), 0)               # cornice
                for k in range(nb + 1):
                    s = k * bw
                    abox(bm, P(max(0, s - 0.05), 0, z0), P(min(L, s + 0.05), DEP + 0.03, z1), 0)   # uprights
                rows = int((z1 - z0 - 0.5) / SH)
                for j in range(1, rows + 1):
                    z = z0 + 0.25 + j * SH
                    if z > z1 - 0.3: break
                    abox(bm, P(0, 0, z - 0.035), P(L, DEP, z), 0)                  # shelf boards
                # books: one quad per bay per shelf row, mapped to a random stretch of the spines atlas
                for k in range(nb):
                    for j in range(rows):
                        zb = z0 + 0.25 + j * SH; zt = min(zb + SH - 0.035, z1 - 0.25)
                        if zt - zb < 0.2: continue
                        s0, s1 = k * bw + 0.05, (k + 1) * bw - 0.05
                        row = int(rng.integers(BOOK_ROWS)); w_img = (s1 - s0) / 4.0
                        u0 = float(rng.uniform(0, 1 - w_img))
                        v0 = 1 - (row + 1) / BOOK_ROWS; v1 = 1 - row / BOOK_ROWS
                        d = DEP - 0.07
                        # viewer faces -n: their right is a x n... order corners BL, BR, TR, TL as seen from the room
                        pts = [P(s0, d, zb), P(s1, d, zb), P(s1, d, zt), P(s0, d, zt)]
                        uvs = [(u0, v0), (u0 + w_img, v0), (u0 + w_img, v1), (u0, v1)]
                        # if 'a' runs to the viewer's left, swap u so the spines read upright either way
                        if a.cross(n).z > 0: uvs = [(u0 + w_img, v0), (u0, v0), (u0, v1), (u0 + w_img, v1)]
                        face(bm, pts, tuple(n), 1, uvs)
    bc = C.part("Bookcases", cases, [C.mat("TK_WoodTV"), C.mat("TK_BookSpines")])

    # ---- gallery: walkway slab at 6.0..6.6 on back and sides, balustrade, corbels; stair along the front-left
    GD = 1.9

    def gallery(bm):
        zt = 6.6
        abox(bm, (-W2 + T, -D2 + T, 6.3), (W2 - T, -D2 + T + GD, zt))
        abox(bm, (-W2 + T, -D2 + T + GD, 6.3), (-W2 + T + GD, FY, zt))
        abox(bm, (W2 - T - GD, -D2 + T + GD, 6.3), (W2 - T, FY, zt))
        abox(bm, (-W2 + T + GD, -D2 + T + GD - 0.04, 6.15), (W2 - T - GD, -D2 + T + GD + 0.04, 6.45))     # fascia
        # balustrade: rails + balusters
        edge = [((-W2 + T + GD, -D2 + T + GD), (W2 - T - GD, -D2 + T + GD)),
                ((-W2 + T + GD, -D2 + T + GD), (-W2 + T + GD, FY - 0.05)),
                ((W2 - T - GD, -D2 + T + GD), (W2 - T - GD, FY - 0.05))]
        for (p, q) in edge:
            p = Vector((*p, 0)); q = Vector((*q, 0)); L = (q - p).length; dvec = (q - p).normalized()
            w = Vector((0.05, 0.05, 0))
            abox(bm, p + Vector((0, 0, zt + 0.95)) - w * 1.4, q + Vector((0, 0, zt + 1.05)) + w * 1.4, 1)   # top rail
            abox(bm, p + Vector((0, 0, zt + 0.08)) - w, q + Vector((0, 0, zt + 0.14)) + w, 1)                # bottom rail
            nb = int(L / 0.55)
            for k in range(nb + 1):
                c = p + dvec * (k * L / nb)
                abox(bm, c + Vector((-0.025, -0.025, zt + 0.14)), c + Vector((0.025, 0.025, zt + 0.95)), 1)
            nc = int(L / 2.4)
            for k in range(nc + 1):   # corbels under the slab
                c = p + dvec * (k * L / nc)
                inward = Vector((0, -1, 0)) if abs(dvec.y) < 0.5 else Vector((-1 if p.x < 0 else 1, 0, 0))
                abox(bm, c + Vector((0, 0, 5.4)) - Vector((0.12, 0.12, 0)), c + inward * GD + Vector((0, 0, 6.3)) + Vector((0.12, 0.12, 0)), 0)
        # straight stair along the inside of the front wall, rising from x -7 (floor) to the left gallery (6.6)
        nst = 22
        for k in range(nst):
            x1 = -7.0 - k * 0.27; z = (k + 1) * 6.6 / nst
            abox(bm, (x1 - 0.29, FY - 1.3, z - 0.06), (x1, FY - 0.05, z), 0)
        stl = Vector((-7.0, FY - 1.32, 0)); st2 = Vector((-7.0 - nst * 0.27, FY - 1.32, 6.6))
        pipe(bm, stl + Vector((0, 0, 1.0)), st2 + Vector((0, 0, 1.0)), 0.035, 6, 1)
        pipe(bm, stl, stl + Vector((0, 0, 1.0)), 0.04, 6, 1)
        pipe(bm, stl + Vector((0, 0.05, -0.15)), st2 + Vector((0, 0.05, -0.15)), 0.16, 4, 0)    # stringer
    C.part("Gallery", gallery, [C.mat("TK_WoodTV"), C.mat("TK_Brass")])

    # ---- reading tables, chairs, lamps
    tables = [(-5.2, -2.6), (5.2, -2.6), (-5.2, 2.4), (5.2, 2.4)]

    def furniture(bm):
        for (tx, ty) in tables:
            abox(bm, (tx - 2.0, ty - 0.65, 0.72), (tx + 2.0, ty + 0.65, 0.78), 0)              # top
            abox(bm, (tx - 1.85, ty - 0.55, 0.6), (tx + 1.85, ty + 0.55, 0.72), 0)              # apron
            for sx in (-1, 1):
                for sy in (-1, 1): abox(bm, (tx + sx * 1.8 - 0.06, ty + sy * 0.5 - 0.06, 0), (tx + sx * 1.8 + 0.06, ty + sy * 0.5 + 0.06, 0.6), 0)
            for k in (-1.2, 0, 1.2):          # chairs both sides
                for sy in (-1, 1):
                    cx, cy = tx + k, ty + sy * 1.05
                    abox(bm, (cx - 0.24, cy - 0.24, 0.44), (cx + 0.24, cy + 0.24, 0.5), 1)
                    abox(bm, (cx - 0.24, cy + sy * 0.2, 0.5), (cx + 0.24, cy + sy * 0.25, 1.0), 1)
                    for lx in (-0.2, 0.2):
                        for ly in (-0.2, 0.2): abox(bm, (cx + lx - 0.025, cy + ly - 0.025, 0), (cx + lx + 0.025, cy + ly + 0.025, 0.44), 1)
            for k in (-1.0, 1.0):             # lamps (base + stem + shade)
                C.bm_cyl(bm, 0.11, 0.03, loc=(tx + k, ty, 0.795), segs=8, mat_index=2)
                pipe(bm, (tx + k, ty, 0.8), (tx + k, ty, 1.15), 0.012, 4, 2)
                C.bm_cyl(bm, 0.22, 0.14, loc=(tx + k, ty, 1.2), segs=8, mat_index=2, r2=0.08)
        # a rug down the centre aisle and under the tables
        abox(bm, (-8.5, -4.5, 0.0), (8.5, 4.3, 0.012), 3)
    C.part("Furniture", furniture, [C.mat("TK_WoodTV"), C.mat("TK_WoodLight"), C.mat("TK_Brass"), C.mat("TK_Rug")])

    # ---- lanterns (frames) + glow
    lanterns = [(x, y) for x in (-6.0, 0.0, 6.0) for y in (-3.5, 2.5)]

    def lantern_frames(bm):
        for (x, y) in lanterns:
            z = 9.2
            pipe(bm, (x, y, z + 1.0), (x, y, H), 0.03, 4, 0)
            C.bm_cyl(bm, 0.55, 0.12, loc=(x, y, z + 0.95), segs=8, mat_index=0, r2=0.25)
            C.bm_cyl(bm, 0.5, 0.1, loc=(x, y, z - 0.05), segs=8, mat_index=0)
            C.bm_cyl(bm, 0.15, 0.25, loc=(x, y, z - 0.2), segs=8, mat_index=0, r2=0.02)
    C.part("Lanterns", lantern_frames, [C.mat("TK_Brass")])

    def glow(bm):
        for (x, y) in lanterns:
            C.bm_cyl(bm, 0.42, 0.9, loc=(x, y, 9.6), segs=8)
        # concealed strip along the top of the lower and upper bookcases (washes the ceiling and the shelves)
        for z in (5.98, 12.42):
            abox(bm, (-W2 + T + 0.2, -D2 + T + 0.1, z), (W2 - T - 0.2, -D2 + T + 0.3, z + 0.06))
            abox(bm, (-W2 + T + 0.1, -D2 + T + 0.6, z), (-W2 + T + 0.3, FY - 0.2, z + 0.06))
            abox(bm, (W2 - T - 0.3, -D2 + T + 0.6, z), (W2 - T - 0.1, FY - 0.2, z + 0.06))
        for (tx, ty) in tables:   # lamp shade undersides
            for k in (-1.0, 1.0):
                C.bm_cyl(bm, 0.2, 0.02, loc=(tx + k, ty, 1.12), segs=8)
    C.part("Glow", glow, [C.mat("TK_HallGlow")])


# =================================================================== hall_museum
def museum(r):
    shell()

    def trim(bm):  # marble trim + classical portico (columns, entablature, pediment)
        outer_trim(bm, 0, quoins=False)
        inner_trim(bm, 0, skirt=0.4, dado=1.1)
        for s in (-1, 1):  # corner pilasters
            abox(bm, (s * (W2 - 1.4), D2, 0.8), (s * (W2 + 0.05), D2 + 0.25, H - 0.6))
        # portico: stylobate, 4 columns, entablature, pediment, portico ceiling
        PY0, PY1 = D2, D2 + 3.4
        abox(bm, (-8.6, PY0, -0.3), (8.6, PY1 + 0.4, 0.03))
        for k in range(3):
            abox(bm, (-8.6 + 0.0, PY1 + 0.4 + k * 0.45, -0.3 - (k + 1) * 0.0), (8.6, PY1 + 0.85 + k * 0.45, -0.0 - (k + 1) * 0.15))
        cols = [-7.5, -2.5, 2.5, 7.5]
        for x in cols:
            y = PY1 - 0.7
            abox(bm, (x - 0.75, y - 0.75, 0), (x + 0.75, y + 0.75, 0.3))                    # plinth
            C.bm_cyl(bm, 0.7, 0.25, loc=(x, y, 0.42), segs=16, mat_index=0)                 # torus-ish base
            C.bm_cyl(bm, 0.58, 10.0 - 1.15, loc=(x, y, 0.55 + (10.0 - 1.15) / 2), segs=16, mat_index=0, r2=0.5)   # shaft (entasis-ish taper)
            C.bm_cyl(bm, 0.5, 0.25, loc=(x, y, 9.5), segs=16, mat_index=0, r2=0.66)          # echinus
            abox(bm, (x - 0.8, y - 0.8, 9.62), (x + 0.8, y + 0.8, 9.9))                      # abacus
        abox(bm, (-8.4, PY0, 9.9), (8.4, PY1 + 0.15, 10.9))                                  # architrave
        abox(bm, (-8.5, PY0, 10.9), (8.5, PY1 + 0.25, 11.9))                                 # frieze
        abox(bm, (-8.8, PY0, 11.9), (8.8, PY1 + 0.55, 12.3))                                 # cornice
        for k in range(15):                                                                   # dentils
            x = -8.1 + k * 1.157
            abox(bm, (x - 0.15, PY1 + 0.25, 11.65), (x + 0.15, PY1 + 0.4, 11.9))
        # pediment: triangular gable on top of the cornice, back to the roof
        yA, yB = PY0, PY1 + 0.3; z0, zt = 12.3, 15.6
        for (y, nrm) in ((yB, (0, 1, 0)),):
            face(bm, [(-8.6, y, z0), (8.6, y, z0), (0, y, zt)], nrm)
        face(bm, [(-8.6, yA, z0), (-8.6, yB, z0), (0, yB, zt), (0, yA, zt)], (-0.35, 0, 1))
        face(bm, [(8.6, yA, z0), (8.6, yB, z0), (0, yB, zt), (0, yA, zt)], (0.35, 0, 1))
        # raking cornices
        for s in (-1, 1):
            vs = C.bm_box(bm, (math.hypot(8.9, 3.4), 0.6, 0.3))
            ang = math.atan2(3.4, 8.9)
            bmesh.ops.transform(bm, matrix=Matrix.Translation((s * 4.4, yB, (z0 + zt) / 2 + 0.15)) @ Matrix.Rotation(s * ang, 4, "Y"), verts=vs)
        # tympanum recess and a central disc ornament (no lettering)
        face(bm, [(-6.8, yB - 0.12, 12.55), (6.8, yB - 0.12, 12.55), (0, yB - 0.12, 15.0)], (0, 1, 0), 1)
        C.bm_cyl(bm, 0.75, 0.15, loc=(0, yB - 0.05, 13.4), segs=16, mat_index=0, axis="Y")
        # portico soffit (coffered ceiling under the entablature)
        abox(bm, (-8.4, PY0, 9.7), (8.4, PY1 - 1.5, 9.9))
        # door surround inside the portico
        for s in (-1, 1):
            abox(bm, (s * OW2, D2, 0), (s * (OW2 + 0.6), D2 + 0.2, OH + 0.6))
        abox(bm, (-OW2 - 0.6, D2, OH), (OW2 + 0.6, D2 + 0.2, OH + 0.6))
    C.part("Trim", trim, [C.mat("TK_Plinth"), C.mat("TK_Plaster")])

    floor("TK_Marble")

    # ---- laylight ceiling: coffer beams + glowing panels; plus picture lights
    def coffers(bm):
        for x in (-9.0, -3.0, 3.0, 9.0):
            abox(bm, (x - 0.35, -D2 + T, H - 1.2), (x + 0.35, FY, H))
        for y in (-4.4, 0.0, 4.4):
            abox(bm, (-W2 + T, y - 0.35, H - 1.2), (W2 - T, y + 0.35, H))
        abox(bm, (-W2 + T, -D2 + T, H - 1.2), (W2 - T, -D2 + T + 0.6, H))
        abox(bm, (-W2 + T, FY - 0.6, H - 1.2), (W2 - T, FY, H))
    C.part("Coffers", coffers, [C.mat("TK_Plaster")])

    paintings = []   # (centre, normal, w, h, cell, mirror)
    paintings.append((Vector((0, -D2 + T, 5.2)), Vector((0, 1, 0)), 6.4, 4.8, 0, False))
    paintings.append((Vector((-8.6, -D2 + T, 4.6)), Vector((0, 1, 0)), 3.6, 2.7, 1, False))
    paintings.append((Vector((8.6, -D2 + T, 4.6)), Vector((0, 1, 0)), 3.6, 2.7, 2, False))
    paintings.append((Vector((-W2 + T, -3.6, 4.6)), Vector((1, 0, 0)), 4.0, 3.0, 3, False))
    paintings.append((Vector((-W2 + T, 3.4, 4.6)), Vector((1, 0, 0)), 4.0, 3.0, 4, False))
    paintings.append((Vector((W2 - T, -3.6, 4.6)), Vector((-1, 0, 0)), 4.0, 3.0, 5, False))
    paintings.append((Vector((W2 - T, 3.4, 4.6)), Vector((-1, 0, 0)), 4.0, 3.0, 1, True))

    def frames(bm):
        for (c, n, w, h, cell, mir) in paintings:
            right = Vector((0, 0, 1)).cross(n)
            up = Vector((0, 0, 1)); fw = 0.22; dep = 0.12
            cc = c + n * 0.06
            for (a0, a1, b0, b1) in ((-w / 2 - fw, w / 2 + fw, h / 2, h / 2 + fw), (-w / 2 - fw, w / 2 + fw, -h / 2 - fw, -h / 2),
                                     (-w / 2 - fw, -w / 2, -h / 2, h / 2), (w / 2, w / 2 + fw, -h / 2, h / 2)):
                p = c + right * a0 + up * b0; q = c + right * a1 + up * b1 + n * dep
                abox(bm, p, q, 0)
            # inner gilt slip
            # canvas
            pts = [cc - right * w / 2 - up * h / 2, cc + right * w / 2 - up * h / 2, cc + right * w / 2 + up * h / 2, cc - right * w / 2 + up * h / 2]
            face(bm, [tuple(p) for p in pts], tuple(n), 1, art_uv(cell, mir))
            # picture light: brass bar on an arm above the frame
            pl = c + up * (h / 2 + fw + 0.35) + n * 0.45
            abox(bm, pl - right * (w * 0.3) - Vector((0.06, 0.06, 0.06)), pl + right * (w * 0.3) + Vector((0.06, 0.06, 0.06)), 0)
            pipe(bm, c + up * (h / 2 + fw + 0.05) + n * 0.02, pl, 0.025, 4, 0)
    C.part("Paintings", frames, [C.mat("TK_Frame"), C.mat("TK_Gallery")])

    # ---- plinths and sculptures (abstract, smooth)
    plinths = [((0.0, -1.2), 1.4, 1.1), ((-7.0, -4.5), 1.0, 1.0), ((7.0, -4.5), 1.0, 1.0), ((-7.5, 3.6), 0.9, 1.2), ((7.5, 3.6), 0.9, 1.2)]

    def plinth(bm):
        for ((x, y), s, h) in plinths:
            abox(bm, (x - s / 2 - 0.06, y - s / 2 - 0.06, 0), (x + s / 2 + 0.06, y + s / 2 + 0.06, 0.1))
            abox(bm, (x - s / 2, y - s / 2, 0.1), (x + s / 2, y + s / 2, h))
            abox(bm, (x - s / 2 - 0.04, y - s / 2 - 0.04, h - 0.06), (x + s / 2 + 0.04, y + s / 2 + 0.04, h))
        # benches (wood seat on marble blocks)
        for y in (2.5,):
            for x in (-3.2, 3.2):
                abox(bm, (x - 1.4, y - 0.3, 0), (x - 1.0, y + 0.3, 0.42)); abox(bm, (x + 1.0, y - 0.3, 0), (x + 1.4, y + 0.3, 0.42))
    C.part("Plinths", plinth, [C.mat("TK_Plinth")])

    def benches(bm):
        for x in (-3.2, 3.2):
            abox(bm, (x - 1.6, 2.5 - 0.35, 0.42), (x + 1.6, 2.5 + 0.35, 0.5))
    C.part("Benches", benches, [C.mat("TK_WoodLight")])

    def sculpt_brass(bm):
        # centre: a large tilted ring (torus) balanced on a sphere
        sphere(bm, 0.45, (0, -1.2, 1.1 + 0.45), 16, 8)
        torus(bm, 1.5, 0.22, (0, -1.2, 1.1 + 0.9 + 1.3), 32, 10, rot=Matrix.Rotation(math.radians(70), 4, "X") @ Matrix.Rotation(0.3, 4, "Z"))
        # left back: stacked twisted slabs
        for k in range(7):
            vs = C.bm_box(bm, (0.7 - k * 0.05, 0.25, 0.22))
            bmesh.ops.transform(bm, matrix=Matrix.Translation((-7.0, -4.5, 1.0 + 0.11 + k * 0.23)) @ Matrix.Rotation(k * 0.32, 4, "Z"), verts=vs)
        # front right: ellipsoid ribbon (two interlocked rings)
        torus(bm, 0.55, 0.07, (7.5, 3.6, 1.2 + 0.7), 24, 8, rot=Matrix.Rotation(math.pi / 2, 4, "X"))
        torus(bm, 0.55, 0.07, (7.5, 3.6, 1.2 + 0.7), 24, 8, rot=Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "X"))
    C.part("Sculpture_Brass", sculpt_brass, [C.mat("TK_Brass")], smooth=True)

    def sculpt_marble(bm):
        # right back: an egg on a cone
        sphere(bm, 0.5, (7.0, -4.5, 1.0 + 1.15), 16, 10, scale=(0.75, 0.75, 1.1))
        C.bm_cyl(bm, 0.42, 0.6, loc=(7.0, -4.5, 1.0 + 0.3), segs=16, r2=0.08)
        # front left: a smooth lens pebble standing on edge + small sphere
        sphere(bm, 0.75, (-7.5, 3.6, 1.2 + 0.75), 20, 10, scale=(1.0, 0.35, 1.0))
        sphere(bm, 0.22, (-7.0, 3.3, 1.2 + 0.22), 12, 6)
    C.part("Sculpture_Marble", sculpt_marble, [C.mat("TK_Marble")], smooth=True)

    def glow(bm):
        xs = (-W2 + T + 0.6, -9.35, -2.65, 3.35, 9.35); xe = (-9.35, -3.35, 2.65, 8.65, W2 - T - 0.6)
        for x0, x1 in zip((-W2 + T + 0.6, -8.65, -2.65, 3.35, 9.35), (-9.35, -3.35, 2.65, 8.65, W2 - T)):
            pass
        bx = [-W2 + T + 0.6, -9.0, -3.0, 3.0, 9.0, W2 - T - 0.6]
        by = [-D2 + T + 0.6, -4.4, 0.0, 4.4, FY - 0.6]
        for i in range(len(bx) - 1):
            for j in range(len(by) - 1):
                x0 = bx[i] + (0.35 if i > 0 else 0); x1 = bx[i + 1] - (0.35 if i < len(bx) - 2 else 0)
                y0 = by[j] + (0.35 if j > 0 else 0); y1 = by[j + 1] - (0.35 if j < len(by) - 2 else 0)
                face(bm, [(x0, y0, H - 0.25), (x1, y0, H - 0.25), (x1, y1, H - 0.25), (x0, y1, H - 0.25)], (0, 0, -1))
        for (c, n, w, h, cell, mir) in paintings:    # picture-light lenses
            right = Vector((0, 0, 1)).cross(n); up = Vector((0, 0, 1))
            pl = c + up * (h / 2 + 0.22 + 0.35) + n * 0.45 - up * 0.07
            pts = [pl - right * w * 0.3 - n * 0.05, pl + right * w * 0.3 - n * 0.05, pl + right * w * 0.3 + n * 0.05, pl - right * w * 0.3 + n * 0.05]
            face(bm, [tuple(p) for p in pts], (0, 0, -1))
    C.part("Glow", glow, [C.mat("TK_HallGlow")])


# =================================================================== hall_classroom
def classroom(r):
    win_y = [-5.5, -1.5, 2.5, 6.5]
    side_open = [(y - 1.1, y + 1.1, 1.6, 9.2) for y in win_y]
    shell(side_openings=side_open)

    def trim(bm):   # wood: base, cornice, quoins outside; wainscot, dado, crown inside; door frame + transom
        outer_trim(bm, 0, quoins=False)
        inner_trim(bm, 0, skirt=0.2, dado=1.2)
        for s in (-1, 1):
            for x in (W2 - T - 0.03, W2 - T):  # wainscot panelling on the side walls (thin slab to dado height)
                pass
        for (p, q) in (((-W2 + T, -D2 + T, 0), (W2 - T, -D2 + T + 0.03, 1.2)), ((-W2 + T, -D2 + T, 0), (-W2 + T + 0.03, FY, 1.2)),
                       ((W2 - T - 0.03, -D2 + T, 0), (W2 - T, FY, 1.2))):
            abox(bm, p, q, 0)
        # window frames + mullions + transoms (both sides), sills
        for sx in (-1, 1):
            xo, xi = sx * W2, sx * (W2 - T)
            for y in win_y:
                y0, y1 = y - 1.1, y + 1.1
                for (a, b) in ((y0, y0 + 0.12), (y1 - 0.12, y1), (y - 0.05, y + 0.05)):
                    abox(bm, (xo, a, 1.6), (xi, b, 9.2))
                for z in (1.6, 4.2, 6.8, 9.08):
                    abox(bm, (xo, y0, z), (xi, y1, z + 0.12))
                abox(bm, (xi - sx * 0.25, y0 - 0.15, 1.45), (xo + sx * 0.12, y1 + 0.15, 1.6))   # sill
        # door frame (architrave) + transom with glazing bars
        for s in (-1, 1):
            abox(bm, (s * OW2, FY - 0.08, 0), (s * (OW2 + 0.55), D2 + 0.12, OH + 0.55))
        abox(bm, (-OW2 - 0.55, FY - 0.08, OH), (OW2 + 0.55, D2 + 0.12, OH + 0.55))
        abox(bm, (-OW2, D2 - 0.4, 8.3), (OW2, D2 - 0.2, 8.5))
        for k in range(1, 8):
            x = -OW2 + k * 2 * OW2 / 8
            abox(bm, (x - 0.06, D2 - 0.4, 8.5), (x + 0.06, D2 - 0.2, OH))
        abox(bm, (-W2 - 0.12, D2, 10.8), (W2 + 0.12, D2 + 0.15, 11.1))
        # chalkboard frame + chalk tray
        bx0, bx1, bz0, bz1 = -8.0, 8.0, 1.0, 4.2
        yb = -D2 + T
        abox(bm, (bx0 - 0.15, yb, bz1), (bx1 + 0.15, yb + 0.1, bz1 + 0.15))
        abox(bm, (bx0 - 0.15, yb, bz0 - 0.15), (bx1 + 0.15, yb + 0.1, bz0))
        abox(bm, (bx0 - 0.15, yb, bz0), (bx0, yb + 0.1, bz1)); abox(bm, (bx1, yb, bz0), (bx1 + 0.15, yb + 0.1, bz1))
        abox(bm, (bx0, yb, bz0 - 0.05), (bx1, yb + 0.2, bz0))
        # ceiling beams
        for x in (-7.0, 0.0, 7.0):
            abox(bm, (x - 0.25, -D2 + T, H - 0.7), (x + 0.25, FY, H))
    C.part("Trim", trim, [C.mat("TK_WoodLight")])

    def board(bm):
        face(bm, [(-8.0, -D2 + T + 0.03, 1.0), (8.0, -D2 + T + 0.03, 1.0), (8.0, -D2 + T + 0.03, 4.2), (-8.0, -D2 + T + 0.03, 4.2)], (0, 1, 0))
    C.part("Chalkboard", board, [C.mat("TK_Chalkboard")])

    def glass(bm):
        for sx in (-1, 1):
            x = sx * (W2 - T / 2)
            for y in win_y:
                face(bm, [(x, y - 1.0, 1.6), (x, y + 1.0, 1.6), (x, y + 1.0, 9.2), (x, y - 1.0, 9.2)], (-sx, 0, 0))
        face(bm, [(-OW2, D2 - 0.3, 8.5), (OW2, D2 - 0.3, 8.5), (OW2, D2 - 0.3, OH), (-OW2, D2 - 0.3, OH)], (0, 1, 0))
    g = C.part("Windows", glass, [C.mat("TK_Glass")])

    floor("TK_WoodFloor")

    xs = [-9.6, -6.6, -3.6, 3.6, 6.6, 9.6]
    ys = [-2.0, 0.6, 3.2, 5.8]

    def desks(bm):
        for x in xs:
            for y in ys:
                # desk (faces -Y: pupils look at the board)
                abox(bm, (x - 0.65, y - 0.35, 0.72), (x + 0.65, y + 0.35, 0.76), 0)
                abox(bm, (x - 0.6, y - 0.3, 0.55), (x + 0.6, y - 0.28, 0.72), 0)      # modesty panel
                abox(bm, (x - 0.58, y - 0.3, 0.55), (x + 0.58, y + 0.2, 0.57), 1)     # book rack
                for lx in (-0.6, 0.6):
                    for ly in (-0.3, 0.3): abox(bm, (x + lx - 0.02, y + ly - 0.02, 0), (x + lx + 0.02, y + ly + 0.02, 0.72), 1)
                # chair behind it
                cy = y + 0.65
                abox(bm, (x - 0.22, cy - 0.2, 0.44), (x + 0.22, cy + 0.2, 0.47), 0)
                abox(bm, (x - 0.22, cy + 0.2, 0.62), (x + 0.22, cy + 0.23, 0.9), 0)
                for lx in (-0.19, 0.19):
                    abox(bm, (x + lx - 0.015, cy - 0.17, 0), (x + lx + 0.015, cy - 0.14, 0.44), 1)
                    abox(bm, (x + lx - 0.015, cy + 0.17, 0), (x + lx + 0.015, cy + 0.22, 0.9), 1)
        # teacher's desk with drawer pedestals + chair
        tx, ty = 0.0, -5.6
        abox(bm, (tx - 1.1, ty - 0.45, 0.74), (tx + 1.1, ty + 0.45, 0.79), 0)
        for s in (-1, 1):
            abox(bm, (tx + s * 1.05 - s * 0.5, ty - 0.42, 0), (tx + s * 1.05, ty + 0.42, 0.74), 0)
            for k in range(3): abox(bm, (tx + s * 1.05 - s * 0.47, ty - 0.44, 0.06 + k * 0.23), (tx + s * 1.05 - s * 0.03, ty - 0.42, 0.26 + k * 0.23), 2)
        abox(bm, (tx - 0.55, ty + 0.4, 0.3), (tx + 0.55, ty + 0.42, 0.74), 0)
        abox(bm, (tx - 0.25, ty - 0.95, 0.44), (tx + 0.25, ty - 0.55, 0.48), 0)
        abox(bm, (tx - 0.25, ty - 1.0, 0.48), (tx + 0.25, ty - 0.96, 0.95), 0)
        pipe(bm, (tx, ty - 0.75, 0), (tx, ty - 0.75, 0.44), 0.03, 6, 1)
        # low bookshelves under the side windows (between window bays) + a few book rows
        for sx in (-1, 1):
            x0 = sx * (W2 - T); x1 = sx * (W2 - T - 0.45)
            abox(bm, (x0, -7.6, 0), (x1, 7.6, 0.1), 0); abox(bm, (x0, -7.6, 0.95), (x1, 7.6, 1.0), 0); abox(bm, (x0, -7.6, 0.5), (x1, 7.6, 0.53), 0)
            for y in (-7.6, -3.5, 0.5, 4.5, 7.55):
                abox(bm, (x0, y, 0), (x1, y + 0.05, 0.95), 0)
    C.part("Desks", desks, [C.mat("TK_WoodLight"), C.mat("TK_SteelRing"), C.mat("TK_Brass")])

    rng = np.random.default_rng(9)

    def books(bm):
        for sx in (-1, 1):
            x = sx * (W2 - T - 0.38)
            for (y0, y1) in ((-7.55, -3.5), (-3.45, 0.5), (0.55, 4.5), (4.55, 7.55)):
                for (zb, zt) in ((0.1, 0.5), (0.53, 0.95)):
                    row = int(rng.integers(BOOK_ROWS)); w_img = min(0.95, (y1 - y0) / 4.0); u0 = float(rng.uniform(0, 1 - w_img))
                    v0 = 1 - (row + 1) / BOOK_ROWS; v1 = 1 - row / BOOK_ROWS
                    uv = [(u0, v0), (u0 + w_img, v0), (u0 + w_img, v1), (u0, v1)]
                    if sx > 0: uv = [(u0 + w_img, v0), (u0, v0), (u0, v1), (u0 + w_img, v1)]
                    face(bm, [(x, y0, zb), (x, y1, zb), (x, y1, zt), (x, y0, zt)], (-sx, 0, 0), 0, uv)
    C.part("Books", books, [C.mat("TK_BookSpines")])

    lights = [(x, y) for x in (-6.6, 0.0, 6.6) for y in (-3.6, 1.4, 6.0)]

    def fittings(bm):
        for (x, y) in lights:
            abox(bm, (x - 1.6, y - 0.18, 7.9), (x + 1.6, y + 0.18, 8.05))
            for s in (-1.3, 1.3): pipe(bm, (x + s, y, 8.05), (x + s, y, H), 0.012, 4)
    C.part("LightFittings", fittings, [C.mat("TK_DarkPlastic")])

    def glow(bm):
        for (x, y) in lights:
            face(bm, [(x - 1.55, y - 0.14, 7.89), (x + 1.55, y - 0.14, 7.89), (x + 1.55, y + 0.14, 7.89), (x - 1.55, y + 0.14, 7.89)], (0, 0, -1))
            face(bm, [(x - 1.55, y - 0.14, 8.06), (x + 1.55, y - 0.14, 8.06), (x + 1.55, y + 0.14, 8.06), (x - 1.55, y + 0.14, 8.06)], (0, 0, 1))
        # warm lamp over the chalkboard
        abox(bm, (-7.6, -D2 + T + 0.25, 4.55), (7.6, -D2 + T + 0.35, 4.62))
    C.part("Glow", glow, [C.mat("TK_HallGlow")])


# =================================================================== hall_studio
def studio(r):
    shell()

    def trim(bm):   # concrete: base, cornice, portal frame; steel header + parked sliding door track
        outer_trim(bm, 0, quoins=False)
        inner_trim(bm, 0, skirt=0.15, crown=False)
        # heavy portal frame around the opening
        for s in (-1, 1):
            abox(bm, (s * OW2, FY - 0.1, 0), (s * (OW2 + 0.9), D2 + 0.45, OH + 0.9))
        abox(bm, (-OW2 - 0.9, FY - 0.1, OH), (OW2 + 0.9, D2 + 0.45, OH + 0.9))
        # vertical concrete fins on the facade
        for x in (-11.5, -9.0, 9.0, 11.5):
            abox(bm, (x - 0.2, D2, 0.8), (x + 0.2, D2 + 0.5, H - 0.6))
    C.part("Trim", trim, [C.mat("TK_Concrete")])

    def steel(bm):
        abox(bm, (-W2 + 0.6, D2 + 0.45, OH + 1.0), (OW2 + 1.0, D2 + 0.7, OH + 1.3))                 # door track
        # lighting grid: pipes along X and Y at 10.8 m, hangers to the ceiling
        zg = 10.8
        for y in (-6.0, -3.0, 0.0, 3.0, 6.0):
            pipe(bm, (-12.5, y, zg), (12.5, y, zg), 0.025, 6)
        for x in (-12.0, -6.0, 0.0, 6.0, 12.0):
            pipe(bm, (x, -6.6, zg + 0.07), (x, 6.6, zg + 0.07), 0.025, 6)
            for y in (-6.0, 0.0, 6.0): pipe(bm, (x, y, zg + 0.1), (x, y, H), 0.012, 4)
        # cable trays along the side walls
        for sx in (-1, 1):
            x = sx * (W2 - T - 0.3)
            abox(bm, (x - 0.25, -D2 + T, 9.0), (x + 0.25, FY, 9.05))
            abox(bm, (x - 0.25, -D2 + T, 9.05), (x - 0.22, FY, 9.2)); abox(bm, (x + 0.22, -D2 + T, 9.05), (x + 0.25, FY, 9.2))
    C.part("Rig", steel, [C.mat("TK_SteelRing")])

    def door(bm):   # big acoustic sliding door, parked open on the left of the portal (outside)
        abox(bm, (-W2 + 0.8, D2 + 0.5, 0.05), (-OW2 - 0.95, D2 + 0.75, OH + 1.0))
        for z in (2.0, 4.5, 7.0, 9.5):
            abox(bm, (-W2 + 0.8, D2 + 0.75, z), (-OW2 - 0.95, D2 + 0.8, z + 0.15))
    C.part("StudioDoor", door, [C.mat("TK_Corrugated")])

    floor("TK_Concrete")

    # ---- cyclorama: a coved white wall sweeping round the back and into the sides
    def cyc(bm):
        path = []
        Rc = 3.0; xb = W2 - T - 0.6 - Rc; yb = -D2 + T + 0.4
        for i in range(9):  # left side straight (front to back), corner, back, corner, right side
            path.append((Vector((-(W2 - T - 0.6), 2.0 - i * (2.0 - (yb + Rc)) / 8, 0)), Vector((1, 0, 0))))
        for i in range(1, 8):
            a = math.pi + (math.pi / 2) * i / 8
            c = Vector((-xb, yb + Rc, 0))
            p = c + Vector((math.cos(a), math.sin(a), 0)) * Rc
            path.append((p, (c - p).normalized()))
        for i in range(0, 9):
            path.append((Vector((-xb + 2 * xb * i / 8, yb, 0)), Vector((0, 1, 0))))
        for i in range(1, 8):
            a = 1.5 * math.pi + (math.pi / 2) * i / 8
            c = Vector((xb, yb + Rc, 0))
            p = c + Vector((math.cos(a), math.sin(a), 0)) * Rc
            path.append((p, (c - p).normalized()))
        for i in range(9):
            path.append((Vector(((W2 - T - 0.6), (yb + Rc) + i * (2.0 - (yb + Rc)) / 8, 0)), Vector((-1, 0, 0))))
        rc = 1.5; Hc = 9.0
        prof = [(2.6, 0.01)] + [(rc + rc * math.cos(math.radians(270 - 90 * k / 6)), 0.01 + rc + rc * math.sin(math.radians(270 - 90 * k / 6))) for k in range(7)] + [(0.0, Hc)]
        grid = [[bm.verts.new(p + n * d + Vector((0, 0, z))) for (d, z) in prof] for (p, n) in path]
        lay = bm.loops.layers.uv.verify()
        for i in range(len(path) - 1):
            for j in range(len(prof) - 1):
                f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
                f.normal_update()
                n_exp = path[i][1] + Vector((0, 0, 1))
                if f.normal.dot(n_exp) < 0: f.normal_flip()
        # back of the cyc (a plain flat shell behind it is the hall wall; close the top with a lip)
    cy = C.part("Cyclorama", cyc, [C.mat("TK_Cyc")], smooth=True)

    # ---- presenter desk: an arc facing the cameras (+Y)
    def desk(bm):
        cx, cyy, Rd = 0.0, -6.2, 3.6
        n = 12; a0, a1 = math.radians(55), math.radians(125)
        for i in range(n):
            a = a0 + (a1 - a0) * i / n; b = a0 + (a1 - a0) * (i + 1) / n
            P = lambda rr, ang, z: (cx + rr * math.cos(ang), cyy + rr * math.sin(ang), z)
            for (r0, r1, z0, z1, mi) in ((Rd - 0.45, Rd + 0.05, 0.98, 1.04, 0),):
                face(bm, [P(r0, a, z1), P(r1, a, z1), P(r1, b, z1), P(r0, b, z1)], (0, 0, 1), mi)
                face(bm, [P(r1, a, z0), P(r1, b, z0), P(r1, b, z1), P(r1, a, z1)], (math.cos((a + b) / 2), math.sin((a + b) / 2), 0), mi)
                face(bm, [P(r0, a, z0), P(r1, a, z0), P(r1, b, z0), P(r0, b, z0)], (0, 0, -1), mi)
            face(bm, [P(Rd - 0.05, a, 0.08), P(Rd - 0.05, b, 0.08), P(Rd - 0.05, b, 0.95), P(Rd - 0.05, a, 0.95)], (math.cos((a + b) / 2), math.sin((a + b) / 2), 0), 1)
            face(bm, [P(Rd - 0.05, a, 0.0), P(Rd - 0.05, b, 0.0), P(Rd - 0.05, b, 0.08), P(Rd - 0.05, a, 0.08)], (math.cos((a + b) / 2), math.sin((a + b) / 2), 0), 1)
        # end caps
        for ang in (a0, a1):
            P0 = Vector((cx + (Rd - 0.45) * math.cos(ang), cyy + (Rd - 0.45) * math.sin(ang), 0)); P1 = Vector((cx + (Rd + 0.05) * math.cos(ang), cyy + (Rd + 0.05) * math.sin(ang), 0))
            nrm = Vector((math.sin(ang), -math.cos(ang), 0)) * (1 if ang == a0 else -1)
            face(bm, [tuple(P0), tuple(P1), tuple(P1 + Vector((0, 0, 1.04))), tuple(P0 + Vector((0, 0, 1.04)))], tuple(nrm), 1)
        # 3 stools behind the desk + a pair of floor monitors
        for x in (-1.6, 0.0, 1.6):
            y = cyy + math.sqrt(max(0, (Rd - 1.0) ** 2 - x * x)) - 0.0
            C.bm_cyl(bm, 0.22, 0.06, loc=(x, y, 0.78), segs=10, mat_index=1)
            pipe(bm, (x, y, 0), (x, y, 0.75), 0.03, 6, 2)
            C.bm_cyl(bm, 0.25, 0.03, loc=(x, y, 0.015), segs=10, mat_index=2)
        for x in (-5.5, 5.5):
            vs = C.bm_box(bm, (1.2, 0.35, 0.75), mat_index=1)
            bmesh.ops.transform(bm, matrix=Matrix.Translation((x, -0.5, 0.4)) @ Matrix.Rotation(math.radians(-25 if x > 0 else 25), 4, "Z") @ Matrix.Rotation(math.radians(-15), 4, "X"), verts=vs)
    C.part("PresenterDesk", desk, [C.mat("TK_WoodLight"), C.mat("TK_DarkPlastic"), C.mat("TK_SteelRing")])

    # ---- studio lights on the grid: fresnels aimed at the desk + cyc floods
    target = Vector((0, -4.5, 1.2))
    fixtures = []
    for x in (-9.0, -4.5, 0.0, 4.5, 9.0):
        for y in (-3.0, 3.0):
            fixtures.append(Vector((x, y, 10.8 - 0.6)))
    for x in (-8.0, -2.7, 2.7, 8.0):
        fixtures.append(Vector((x, -6.0, 10.8 - 0.6)))

    def aim(p):
        t = target if p.y > -5 else Vector((p.x, -9.0, 4.0))
        d = (t - p).normalized()
        return d

    def housings(bm):
        for p in fixtures:
            d = aim(p)
            q = Vector((0, 0, 1)).rotation_difference(d)
            M = Matrix.Translation(p) @ q.to_matrix().to_4x4()
            vs = C.bm_cyl(bm, 0.24, 0.55, segs=10, mat_index=0); bmesh.ops.transform(bm, matrix=M, verts=vs)
            vs = C.bm_cyl(bm, 0.2, 0.12, loc=(0, 0, -0.32), segs=10, mat_index=0); bmesh.ops.transform(bm, matrix=M, verts=vs)
            for k in range(4):   # barn doors
                a = k * math.pi / 2
                vs = C.bm_box(bm, (0.42, 0.01, 0.22), mat_index=0)
                bmesh.ops.transform(bm, matrix=M @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0, 0.25, 0.36)) @ Matrix.Rotation(math.radians(-20), 4, "X"), verts=vs)
            # yoke up to the grid
            abox(bm, p + Vector((-0.3, -0.02, 0.0)), p + Vector((-0.27, 0.02, 0.55)), 1)
            abox(bm, p + Vector((0.27, -0.02, 0.0)), p + Vector((0.3, 0.02, 0.55)), 1)
            abox(bm, p + Vector((-0.3, -0.03, 0.52)), p + Vector((0.3, 0.03, 0.56)), 1)
            pipe(bm, p + Vector((0, 0, 0.56)), p + Vector((0, 0, 0.6)), 0.05, 6, 1)
        # ---- two camera pedestals facing the desk (generic: no brand, no text)
        for (x, y, yaw) in ((-3.8, 4.0, 0.3), (3.8, 4.0, -0.3)):
            M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z")
            def add(vs): bmesh.ops.transform(bm, matrix=M, verts=vs)
            add(C.bm_cyl(bm, 0.5, 0.18, loc=(0, 0, 0.18), segs=12, mat_index=0))                 # skirt / base
            for k in range(3):
                a = k * 2 * math.pi / 3
                add(C.bm_box(bm, (0.12, 0.16, 0.12), loc=(0.48 * math.cos(a), 0.48 * math.sin(a), 0.06), mat_index=0))
            add(C.bm_cyl(bm, 0.16, 0.8, loc=(0, 0, 0.67), segs=10, mat_index=1))                 # column lower
            add(C.bm_cyl(bm, 0.12, 0.45, loc=(0, 0, 1.28), segs=10, mat_index=0))                # column upper
            add(C.bm_cyl(bm, 0.36, 0.035, loc=(0, 0, 1.0), segs=14, mat_index=1))                # steering ring
            add(C.bm_box(bm, (0.3, 0.3, 0.14), loc=(0, 0, 1.55), mat_index=0))                   # pan/tilt head
            add(C.bm_box(bm, (0.26, 0.6, 0.3), loc=(0, -0.05, 1.78), mat_index=0))               # camera body
            add(C.bm_cyl(bm, 0.11, 0.42, loc=(0, -0.55, 1.8), segs=12, mat_index=0, axis="Y"))   # lens
            add(C.bm_box(bm, (0.5, 0.06, 0.42), loc=(0, -0.95, 1.8), mat_index=0))              # prompter hood frame
            add(C.bm_box(bm, (0.5, 0.32, 0.04), loc=(0, -0.8, 2.02), mat_index=0))              # prompter hood top
            add(C.bm_box(bm, (0.24, 0.2, 0.17), loc=(0, 0.05, 2.03), mat_index=0))              # viewfinder
            for s in (-1, 1):
                pv = C.bm_cyl(bm, 0.018, 0.75, segs=6, mat_index=1, axis="Y")
                bmesh.ops.transform(bm, matrix=M @ Matrix.Translation((s * 0.22, 0.55, 1.5)) @ Matrix.Rotation(math.radians(-20), 4, "X"), verts=pv)
    C.part("Fixtures", housings, [C.mat("TK_DarkPlastic"), C.mat("TK_SteelRing")])

    def lenses(bm):
        for p in fixtures:
            d = aim(p)
            q = Vector((0, 0, 1)).rotation_difference(d)
            M = Matrix.Translation(p) @ q.to_matrix().to_4x4()
            vs = C.bm_cyl(bm, 0.19, 0.02, loc=(0, 0, 0.285), segs=10); bmesh.ops.transform(bm, matrix=M, verts=vs)
    C.part("Lenses", lenses, [C.mat("TK_StudioLight")])

    def prompters(bm):   # prompter glass on the two cameras (angled pane)
        for (x, y, yaw) in ((-3.8, 4.0, 0.3), (3.8, 4.0, -0.3)):
            M = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z")
            vs = C.bm_box(bm, (0.46, 0.005, 0.5)); bmesh.ops.transform(bm, matrix=M @ Matrix.Translation((0, -0.8, 1.8)) @ Matrix.Rotation(math.radians(45), 4, "X"), verts=vs)
    C.part("PrompterGlass", prompters, [C.mat("TK_Glass")])

    def cables(bm):
        paths = [[(-3.8, 4.0, 0.02), (-3.0, 5.0, 0.02), (-3.0, 7.0, 0.02), (-10.0, 7.6, 0.02), (-12.8, 7.6, 0.02), (-12.8, 7.6, 9.0)],
                 [(3.8, 4.0, 0.02), (4.5, 5.2, 0.02), (6.0, 6.8, 0.02), (11.0, 7.4, 0.02), (12.8, 7.4, 0.02), (12.8, 7.4, 9.0)],
                 [(0.0, -5.0, 0.02), (1.5, -3.0, 0.02), (5.5, -1.0, 0.02), (12.8, -1.0, 0.02), (12.8, -1.0, 9.0)],
                 [(-5.5, -0.5, 0.02), (-8.0, 0.5, 0.02), (-12.8, 0.6, 0.02), (-12.8, 0.6, 9.0)]]
        for pts in paths:
            for a, b in zip(pts, pts[1:]):
                pipe(bm, a, b, 0.025, 4)
            for a in pts[1:-1]:
                sphere(bm, 0.025, a, 4, 2)
        # cable ramps over the main run
        abox(bm, (-3.5, 6.5, 0), (-2.5, 7.5, 0.06), 0)
    C.part("Cables", cables, [C.mat("TK_DarkPlastic")])

    def glow(bm):
        # ground-row cyc lights: a warm strip at the foot of the cove, and a top cove strip over the cyc
        abox(bm, (-9.0, -D2 + T + 2.6, 0.0), (9.0, -D2 + T + 2.75, 0.12))
        abox(bm, (-10.5, -D2 + T + 0.35, 9.3), (10.5, -D2 + T + 0.5, 9.4))
        # practical warm strips round the room at the top of the walls
        for (p, q) in (((-W2 + T, FY - 0.15, 11.8), (W2 - T, FY, 11.9)), ((-W2 + T, -D2 + T, 11.8), (-W2 + T + 0.15, FY, 11.9)),
                       ((W2 - T - 0.15, -D2 + T, 11.8), (W2 - T, FY, 11.9))):
            abox(bm, p, q)
        # desk under-glow (kick strip under the top)
        cx, cyy, Rd = 0.0, -6.2, 3.6
        n = 12; a0, a1 = math.radians(55), math.radians(125)
        for i in range(n):
            a = a0 + (a1 - a0) * i / n; b = a0 + (a1 - a0) * (i + 1) / n
            P = lambda rr, ang, z: (cx + rr * math.cos(ang), cyy + rr * math.sin(ang), z)
            face(bm, [P(Rd - 0.02, a, 0.9), P(Rd - 0.02, b, 0.9), P(Rd - 0.02, b, 0.95), P(Rd - 0.02, a, 0.95)], (math.cos((a + b) / 2), math.sin((a + b) / 2), 0))
            face(bm, [P(Rd - 0.02, a, 0.0), P(Rd - 0.02, b, 0.0), P(Rd - 0.02, b, 0.05), P(Rd - 0.02, a, 0.05)], (math.cos((a + b) / 2), math.sin((a + b) / 2), 0))
    C.part("Glow", glow, [C.mat("TK_HallGlow")])


# =================================================================== run all four
IN = [(0, -3, 11), (-8, -4, 9), (8, -4, 9), (0, 4, 10), (-8, 3, 6), (8, 3, 6)]
which = [a for a in sys.argv[sys.argv.index("--") + 1:] if a.startswith("hall_")] if "--" in sys.argv else []
results = {}
for name, fn in (("hall_library", library), ("hall_museum", museum), ("hall_classroom", classroom), ("hall_studio", studio)):
    if which and name not in which: continue
    results[name] = run(name, fn, IN)
print("[commons_halls]", results)
