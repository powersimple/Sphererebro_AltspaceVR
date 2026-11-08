"""Shape + image helpers for the period props (radio_1920s, tv_midcentury, web_monitor_1990s, feed_tile, devices).
Pure helpers on top of common.py: bmesh solids built from 2D outlines (prism, ring, loft, lathe), smoothing by angle,
per-face planar UVs, and numpy drawing (noise, signed-distance shapes) for the generated screen images."""
import bmesh, math
from mathutils import Vector, Matrix
import numpy as np


# ----------------------------------------------------------------- 2D outlines (a, b) -> placed by axis
def to3(p, d, axis):
    a, b = p
    if axis == "Y": return Vector((a, d, b))      # (x, z) outline, depth along Y
    if axis == "Z": return Vector((a, b, d))      # (x, y) outline, height along Z
    return Vector((d, a, b))                      # (y, z) outline, along X


def rrect(w, h, r, seg=6, ca=0.0, cb=0.0):
    """Rounded rectangle, 4*(seg+1) points, CCW from the bottom-right corner."""
    r = max(1e-4, min(r, w / 2 * 0.999, h / 2 * 0.999))
    pts = []
    for x0, z0, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90.0 * i / seg)
            pts.append((ca + x0 + r * math.cos(a), cb + z0 + r * math.sin(a)))
    return pts


def circle(r, n=24, ca=0.0, cb=0.0, start=0.0):
    return [(ca + r * math.cos(start + 2 * math.pi * i / n), cb + r * math.sin(start + 2 * math.pi * i / n)) for i in range(n)]


def gothic(hw, z0, zs, h, n=10, cx=0.0):
    """Pointed (h > hw) or round (h == hw) arch: bottom z0, straight sides to the springline zs, apex at zs + h. CCW."""
    h = max(h, hw)
    x0 = (hw * hw - h * h) / (2 * hw); R = hw - x0
    t1 = math.atan2(h, -x0)
    right = [(cx + x0 + R * math.cos(t1 * i / n), zs + R * math.sin(t1 * i / n)) for i in range(n + 1)]
    left = [(2 * cx - x, z) for (x, z) in reversed(right[:-1])]
    pts = []
    if z0 < zs - 1e-6: pts.append((cx + hw, z0))
    pts += right + left
    if z0 < zs - 1e-6: pts.append((cx - hw, z0))
    return pts


# ----------------------------------------------------------------- solids
def _finish(bm, faces, mat):
    for f in faces: f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=faces)


def prism(bm, pts, d0, d1, axis="Y", mat=0, bevel=0.0, bseg=2, bevel_back=True):
    """Outline extruded from d0 (back) to d1 (front) along axis, capped; optional rounded bevel on the cap edges."""
    back = [bm.verts.new(to3(p, d0, axis)) for p in pts]
    front = [bm.verts.new(to3(p, d1, axis)) for p in pts]
    n = len(pts)
    fb = bm.faces.new(back); ff = bm.faces.new(front)
    faces = [fb, ff] + [bm.faces.new((back[i], back[(i + 1) % n], front[(i + 1) % n], front[i])) for i in range(n)]
    _finish(bm, faces, mat)
    if bevel > 0:
        edges = list(ff.edges) + (list(fb.edges) if bevel_back else [])
        res = bmesh.ops.bevel(bm, geom=edges, offset=bevel, offset_type="OFFSET", segments=bseg, profile=0.5,
                              affect="EDGES", clamp_overlap=True)
        # the bevel can replace the cap faces: find the new ones (largest faces facing along the axis)
        ax = {"X": 0, "Y": 1, "Z": 2}[axis]
        allv = {v for v in back + front if v.is_valid} | set(res.get("verts", []))
        cand = {f for v in allv for f in v.link_faces}
        for f in cand: f.normal_update()
        ff = max((f for f in cand if f.normal[ax] > 0.99), key=lambda f: f.calc_area())
        fb = max((f for f in cand if f.normal[ax] < -0.99), key=lambda f: f.calc_area())
    return {"front": ff, "back": fb, "verts": back + front}


def ring(bm, outer, inner, d0, d1, axis="Y", mat=0, d1_in=None, d0_in=None):
    """Frame between two outlines with the same point count. d1_in pushes the inner front edge (a sloped bezel)."""
    d1_in = d1 if d1_in is None else d1_in; d0_in = d0 if d0_in is None else d0_in
    ob = [bm.verts.new(to3(p, d0, axis)) for p in outer]; of = [bm.verts.new(to3(p, d1, axis)) for p in outer]
    ib = [bm.verts.new(to3(p, d0_in, axis)) for p in inner]; inf = [bm.verts.new(to3(p, d1_in, axis)) for p in inner]
    n = len(outer); faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [bm.faces.new((of[i], of[j], inf[j], inf[i])), bm.faces.new((ob[i], ib[i], ib[j], ob[j])),
                  bm.faces.new((ob[i], ob[j], of[j], of[i])), bm.faces.new((ib[i], inf[i], inf[j], ib[j]))]
    _finish(bm, faces, mat)
    return {"verts": ob + of + ib + inf, "front_outer": of, "front_inner": inf}


def loft(bm, sections, axis="Y", mat=0, cap0=True, cap1=True):
    """sections = [(d, outline), ...] with equal point counts; quads between consecutive loops; optional end caps."""
    loops = [[bm.verts.new(to3(p, d, axis)) for p in pts] for d, pts in sections]
    n = len(loops[0]); faces = []
    for a, b in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    caps = []
    if cap0: caps.append(bm.faces.new(loops[0]))
    if cap1: caps.append(bm.faces.new(loops[-1]))
    faces += caps
    if cap0 and cap1: _finish(bm, faces, mat)
    else:
        for f in faces: f.material_index = mat
    return {"loops": loops, "caps": caps, "verts": [v for l in loops for v in l]}


def lathe(bm, prof, segs, center=(0, 0, 0), axis="Z", mat=0, knurl=None, phase=0.0):
    """Revolve [(r, d), ...] around axis through center (d along the axis). r = 0 rows become a single pole vertex.
    knurl(row, k) -> radius factor (flutes, ribbed knob edges)."""
    c = Vector(center); rings = []
    for ri, (r, d) in enumerate(prof):
        if r < 1e-7:
            rings.append([bm.verts.new(c + to3((0, 0), d, axis) if axis != "Z" else c + Vector((0, 0, d)))]); continue
        rr = []
        for k in range(segs):
            a = phase + 2 * math.pi * k / segs
            q = r * (knurl(ri, k) if knurl else 1.0)
            u, v = q * math.cos(a), q * math.sin(a)
            if axis == "Z": p = Vector((u, v, d))
            elif axis == "Y": p = Vector((u, d, v))
            else: p = Vector((d, u, v))
            rr.append(bm.verts.new(c + p))
        rings.append(rr)
    faces = []
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        for k in range(segs):
            k2 = (k + 1) % segs
            if len(a) == 1: faces.append(bm.faces.new((a[0], b[k], b[k2])))
            elif len(b) == 1: faces.append(bm.faces.new((a[k], a[k2], b[0])))
            else: faces.append(bm.faces.new((a[k], a[k2], b[k2], b[k])))
    if len(rings[0]) > 1: faces.append(bm.faces.new(rings[0]))
    if len(rings[-1]) > 1: faces.append(bm.faces.new(rings[-1]))
    _finish(bm, faces, mat)
    return {"verts": [v for r in rings for v in r]}


def tube(bm, a, b, r, segs=8, mat=0, r2=None):
    """Capped cylinder from point a to point b."""
    a = Vector(a); b = Vector(b); d = b - a; L = d.length
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=L)
    q = d.normalized().to_track_quat("Z", "Y")
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=res["verts"])
    for f in {f for v in res["verts"] for f in v.link_faces}: f.material_index = mat
    return {"verts": res["verts"]}


def box(bm, size, loc=(0, 0, 0), mat=0, taper=0.0, bevel=0.0, bseg=1):
    """Box (sx, sy, sz) centred at loc. taper shrinks the top face (keycaps). Bottom face kept."""
    sx, sy, sz = size
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((sx, sy, sz, 1)), verts=vs)
    if taper:
        top = [v for v in vs if v.co.z > loc[2]]
        for v in top:
            v.co.x = loc[0] + (v.co.x - loc[0]) * (1 - taper / sx * 2)
            v.co.y = loc[1] + (v.co.y - loc[1]) * (1 - taper / sy * 2)
    faces = list({f for v in vs for f in v.link_faces})
    for f in faces: f.material_index = mat
    if bevel:
        edges = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, offset_type="OFFSET", segments=bseg, profile=0.5, affect="EDGES", clamp_overlap=True)
        vs = list({v for f in faces for v in f.verts} | set(vs))
    return {"verts": vs}


def xform(bm, verts, M):
    bmesh.ops.transform(bm, matrix=M, verts=[v for v in verts if v.is_valid])


def autosmooth(bm, deg=35.0):
    """Smooth shading with sharp edges above deg (rounded bevels read soft, real corners stay crisp)."""
    lim = math.radians(deg)
    for f in bm.faces: f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) != 2: e.smooth = False; continue
        e.smooth = e.calc_face_angle(0.0) <= lim


def uv_faces(o, mat_index, axis="Y", bounds=None, cell=None, flip_u=None):
    """0..1 planar UVs on the faces of material slot mat_index (others untouched).
    bounds = ((amin, bmin), (amax, bmax)) on the projection plane; cell = (u0, v0, u1, v1) remaps into an atlas cell.
    axis Y: viewer looks from +Y, so u = 0 at +x (viewer's left)."""
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    ia, ib = {"Y": (0, 2), "X": (1, 2), "Z": (0, 1)}[axis]
    polys = [p for p in me.polygons if p.material_index == mat_index]
    cos = [me.vertices[i].co for p in polys for i in p.vertices]
    if bounds is None:
        bounds = ((min(c[ia] for c in cos), min(c[ib] for c in cos)), (max(c[ia] for c in cos), max(c[ib] for c in cos)))
    (a0, b0), (a1, b1) = bounds
    fu = (axis == "Y") if flip_u is None else flip_u
    uvl = me.uv_layers.active.data
    for p in polys:
        for li in p.loop_indices:
            c = me.vertices[me.loops[li].vertex_index].co
            u = (c[ia] - a0) / max(1e-9, a1 - a0); v = (c[ib] - b0) / max(1e-9, b1 - b0)
            if fu: u = 1 - u
            if cell: u = cell[0] + u * (cell[2] - cell[0]); v = cell[1] + v * (cell[3] - cell[1])
            uvl[li].uv = (u, v)


# ----------------------------------------------------------------- numpy image helpers (row 0 = top)
def grid(h, w, aspect=None):
    """Pixel-centre coordinates: X in [0, aspect], Y in [0, 1] (Y down). aspect defaults to w / h."""
    aspect = w / h if aspect is None else aspect
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return (x + 0.5) / w * aspect, (y + 0.5) / h


def smooth(t): return t * t * (3 - 2 * t)


def vnoise(h, w, cy, cx, rng):
    """Smooth value noise with cy x cx cells."""
    g = rng.random((cy + 2, cx + 2)).astype(np.float32)
    ys = np.linspace(0, cy, h, endpoint=False, dtype=np.float32); xs = np.linspace(0, cx, w, endpoint=False, dtype=np.float32)
    y0 = ys.astype(int); x0 = xs.astype(int); fy = smooth(ys - y0)[:, None]; fx = smooth(xs - x0)[None, :]
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, cy, cx, rng, octaves=5, gain=0.5):
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        out += vnoise(h, w, cy * 2 ** o, cx * 2 ** o, rng) * amp; tot += amp; amp *= gain
    return out / tot


def sd_rrect(X, Y, cx, cy, hw, hh, r):
    qx = np.abs(X - cx) - (hw - r); qy = np.abs(Y - cy) - (hh - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def sd_circle(X, Y, cx, cy, r): return np.hypot(X - cx, Y - cy) - r


def cover(d, aa): return np.clip(0.5 - d / aa, 0, 1)


def paint(img, m, col, a=1.0):
    m = (m * a)[..., None]
    img[:] = img * (1 - m) + np.asarray(col, np.float32) * m


def blur(a, r):
    """Cheap separable box blur x3 (≈ gaussian), radius r pixels, on HxW or HxWxC."""
    r = int(max(1, r))
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == ax else (0, 0) for i in range(a.ndim)], mode="edge"), axis=ax)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax); lo = np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)
            a = (hi - lo) / (2 * r + 1)
    return a
