"""light_beam: a glowing arched tube from (0,0,0) to (0,1,0) (unit length along +Y), peak height 0.35 at the middle.
Radius 0.03 at the ends swelling to 0.05 in the middle; 32 segments along, 8 around. Unity scales it non-uniformly
to span racks -> halls. Origin at the start point (0,0,0).
Parts: Beam (TK_Beam), Halo (TK_BeamHalo: larger, fainter sheath). UVs: u along the length 0..1, v around 0..1.
"""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()
C.MATS["TK_BeamHalo"] = {"tex": None, "tint": [1.0, 0.8, 0.45], "metal": 0, "rough": 0, "tile": 0,
                         "emit": [1.2, 0.85, 0.4], "alpha": "blend", "opacity": 0.14, "unlit": True}

NS, NA, PEAK = 32, 8, 0.35


def path(t):
    return Vector((0.0, t, PEAK * 4 * t * (1 - t)))


def tangent(t):
    return Vector((0.0, 1.0, PEAK * 4 * (1 - 2 * t))).normalized()


def tube(name, mat, rfun):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    X = Vector((1, 0, 0))
    for i in range(NS + 1):
        t = i / NS
        p, tg = path(t), tangent(t)
        b = X.cross(tg).normalized()           # in the arch plane, perpendicular to the tangent
        r = rfun(t)
        rings.append([bm.verts.new(p + (X * math.cos(2 * math.pi * k / NA) + b * math.sin(2 * math.pi * k / NA)) * r) for k in range(NA)])
    uv = bm.loops.layers.uv.new("UVMap")
    for i in range(NS):
        for k in range(NA):
            k2 = (k + 1) % NA
            f = bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][k2], rings[i][k2]))
            for l, (uu, vv) in zip(f.loops, ((i / NS, k / NA), ((i + 1) / NS, k / NA), ((i + 1) / NS, (k + 1) / NA), (i / NS, (k + 1) / NA))):
                l[uv].uv = (uu, vv)
    for ring, u0 in ((rings[0], 0.0), (rings[-1], 1.0)):
        f = bm.faces.new(ring if u0 else list(reversed(ring)))
        for l in f.loops: l[uv].uv = (u0, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.parent = C.ROOT
    for p in me.polygons: p.use_smooth = True
    o["keep_uv"] = True
    return o


R = C.root("light_beam")
tube("Beam", C.mat("TK_Beam"), lambda t: 0.03 + 0.02 * math.sin(math.pi * t))
tube("Halo", C.mat("TK_BeamHalo"), lambda t: 2.2 * (0.03 + 0.02 * math.sin(math.pi * t)))
C.finish("light_beam", R, note="unit arch (0,0,0)->(0,1,0), peak 0.35; Beam + Halo")
