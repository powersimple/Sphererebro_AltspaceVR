"""stamp: a giant classic office rubber stamp, ~8 m tall. Origin at the face centre (z = 0 is the rubber face).
Parts: Face (TK_StampRubber die, bottom), Cushion (foam layer), Block (wooden mount, chamfered), IndexLabel (paper
impression label on top of the block, blank), Ferrule (TK_StampMetal collar + shank), Handle (turned wood knob,
TK_StampHandle), FaceAnchor (empty at the face centre, z = 0; the engine puts the impression text there).
"""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()

FW, FD = 5.4, 3.0                # face
BW, BD, BH = 5.8, 3.4, 1.45      # wooden mount block
Z_RUB = 0.28                     # rubber die thickness
Z_CUSH = 0.18                    # cushion
Z_B0 = Z_RUB + Z_CUSH            # block bottom
Z_B1 = Z_B0 + BH                 # block top


def cbox(bm, size, loc, c=0.06, mi=0, segs=1):
    vs = C.bm_box(bm, size, loc, mi)
    if c > 0:
        es = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=vs + es, offset=c, segments=segs, affect="EDGES", profile=0.5, material=mi)
    return vs


def lathe(bm, prof, segs=24, mi=0, z_off=0.0):
    """prof: [(r, z)] bottom to top; r=0 at an end closes it to a pole."""
    rings = []
    for r, z in prof:
        if r < 1e-4:
            rings.append([bm.verts.new((0, 0, z + z_off))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z + z_off)) for k in range(segs)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        if len(a) == 1:
            for k in range(segs): f = bm.faces.new((a[0], b[k], b[(k + 1) % segs])); f.material_index = mi
        elif len(b) == 1:
            for k in range(segs):
                f = bm.faces.new((a[k], a[(k + 1) % segs], b[0])); f.material_index = mi
        else:
            for k in range(segs):
                f = bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k])); f.material_index = mi
    if len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0]))); f.material_index = mi
    if len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1]); f.material_index = mi


def fix(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()


R = C.root("stamp")

# rubber die: slab with a raised rim (stamp border) on the printing face
def face(bm):
    cbox(bm, (FW, FD, Z_RUB * 0.6), (0, 0, Z_RUB * 0.4 + Z_RUB * 0.3), 0.05)
    t = 0.16; h = Z_RUB * 0.4
    for (sx, sy, lx, ly) in ((FW - 0.3, t, 0, FD / 2 - 0.15 - t / 2), (FW - 0.3, t, 0, -(FD / 2 - 0.15 - t / 2)),
                             (t, FD - 0.3, FW / 2 - 0.15 - t / 2, 0), (t, FD - 0.3, -(FW / 2 - 0.15 - t / 2), 0)):
        cbox(bm, (sx, sy, h), (lx, ly, h / 2), 0.02)
o = C.part("Face", face, [C.mat("TK_StampRubber")]); fix(o)

def cushion(bm):
    cbox(bm, (FW + 0.1, FD + 0.1, Z_CUSH), (0, 0, Z_RUB + Z_CUSH / 2), 0.06)
o = C.part("Cushion", cushion, [C.mat("TK_DarkPlastic")]); fix(o)

def block(bm):
    cbox(bm, (BW, BD, BH), (0, 0, Z_B0 + BH / 2), 0.16, segs=2)
    # finger grooves along the long sides
    for sy in (-1, 1):
        cbox(bm, (BW - 1.0, 0.1, 0.18), (0, sy * (BD / 2 + 0.01), Z_B0 + BH * 0.62), 0.03)
o = C.part("Block", block, [C.mat("TK_StampHandle")]); fix(o)

def index_label(bm):
    w, d = BW - 1.2, BD - 0.9
    v = [bm.verts.new((x, y, Z_B1 + 0.006)) for x, y in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
    bm.faces.new(v)
o = C.part("IndexLabel", index_label, [C.mat("TK_Paper")])

# metal ferrule: a flared base plate screwed to the block, a collar and the shank the handle sits on
def ferrule(bm):
    lathe(bm, [(1.15, 0.0), (1.15, 0.08), (0.95, 0.2), (0.7, 0.3), (0.62, 0.42), (0.62, 1.05), (0.7, 1.12), (0.7, 1.3), (0.6, 1.36)],
          28, z_off=Z_B1)
    for k in range(4):   # screws
        a = math.pi / 4 + k * math.pi / 2
        C.bm_cyl(bm, 0.09, 0.06, (math.cos(a) * 0.95, math.sin(a) * 0.95, Z_B1 + 0.13), 8)
o = C.part("Ferrule", ferrule, [C.mat("TK_StampMetal")]); fix(o)
for p in o.data.polygons: p.use_smooth = True

# turned wooden handle: neck, a swelling body, a waist, a ball knob
Z_H = Z_B1 + 1.3
prof = [(0.6, 0.0), (0.66, 0.15), (0.64, 0.4), (0.74, 0.75), (0.92, 1.3), (0.98, 1.75), (0.9, 2.2), (0.68, 2.65),
        (0.52, 3.0), (0.5, 3.2), (0.62, 3.45), (0.9, 3.75), (1.08, 4.1), (1.12, 4.45), (1.04, 4.8), (0.82, 5.12),
        (0.48, 5.36), (0.0, 5.45)]
def handle(bm):
    lathe(bm, prof, 28, z_off=Z_H)
o = C.part("Handle", handle, [C.mat("TK_StampHandle")]); fix(o)
for p in o.data.polygons: p.use_smooth = True

a = bpy.data.objects.new("FaceAnchor", None)
bpy.context.scene.collection.objects.link(a)
a.parent = R; a.location = (0, 0, 0); a.empty_display_size = 1.0

C.finish("stamp", R, note=f"height {Z_H + 5.45:.2f} m; face {FW}x{FD} m at z=0 (rim raised 0.11)")
