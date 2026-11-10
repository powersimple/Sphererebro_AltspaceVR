"""datahall: one long aisle of a data hall, for the module "datahall" (tools/talk/modules/datahall.py). Ben, 2026-11-10:
"Let's rebuild the data center model", with three pictures of dark aisles: black racks with blue lamps on both sides, a
glossy floor, light strips overhead. Drawn from scratch (textures: tools/geo/datahall_art.py).

UNITY axes, metres: x across the aisle, y up from the floor (0), z along it from the mouth (0) to the end wall (L).
Blender (x, y, z) = (-X, -Z, Y). The show scales and moves the whole thing (it starts as a miniature).
  Racks    64 bays a side (each 4.4 x 15 m, one of four fronts from dh_racks.png) + five across the end wall
  Frame    posts between the racks, cable trays above them with hangers, ceiling beams, the rim round the mouth
  Floor    one quad a bay (dh_floor.png)          Ceil    the ceiling, the wall above the racks, the end wall
  Lights   two light strips along the ceiling     Edge    a thin blue line round the mouth
  Case     the outside (seen while it is small)
Run: blender -b --factory-startup --python tools/blender/datahall.py   (after python tools/geo/datahall_art.py)
"""
import bpy, bmesh, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()
R = C.root("datahall")
N, BW, WX, H, CEIL = 64, 4.4, 11.6, 15.0, 16.5          # bays, bay length, half width to the rack fronts, rack height, ceiling
L = N * BW
rnd = random.Random(5)


def B(v): return Vector((-v[0], -v[2], v[1]))            # Unity -> Blender


class Part:
    def __init__(self, name, mat):
        self.me = bpy.data.meshes.new(name); self.me.materials.append(C.mat(mat))
        self.o = bpy.data.objects.new(name, self.me); bpy.context.scene.collection.objects.link(self.o); self.o.parent = R
        self.o["keep_uv"] = True
        self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new("UVMap")

    def quad(self, pts, normal, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
        """pts: four Unity points in order; normal: the Unity direction the face must be seen from."""
        f = self.bm.faces.new([self.bm.verts.new(B(p)) for p in pts])
        for l, uv in zip(f.loops, uvs): l[self.uv].uv = uv
        f.normal_update()
        if f.normal.dot(B(normal)) < 0: f.normal_flip()

    def box(self, lo, hi, skip=""):
        """An axis box seen from outside. skip: faces to leave out, from "x-x+y-y+z-z+" (e.g. "y+")."""
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        faces = {"x-": ([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], (-1, 0, 0)),
                 "x+": ([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], (1, 0, 0)),
                 "y-": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
                 "y+": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
                 "z-": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
                 "z+": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1))}
        for k, (pts, n) in faces.items():
            if k not in skip: self.quad(pts, n)

    def done(self):
        self.bm.to_mesh(self.me); self.bm.free(); return self.o


racks, frame, floor, ceil = Part("Racks", "TK_DhRack"), Part("Frame", "TK_DhFrame"), Part("Floor", "TK_DhFloor"), Part("Ceil", "TK_DhCeil")
lights, edge, case = Part("Lights", "TK_DhLight"), Part("Edge", "TK_DhEdge"), Part("Case", "TK_DhCase")
fog = Part("Fog", "TK_DhFog")
E = 1.0 / 2048


def rack_uv():
    k = rnd.randrange(4); u0, u1 = k / 4 + E, (k + 1) / 4 - E
    return ((u0, E), (u1, E), (u1, 1 - E), (u0, 1 - E))


for k in range(N):
    z0, z1 = k * BW, (k + 1) * BW
    for sx in (-1, 1):
        x = sx * WX
        racks.quad([(x, 0, z0 + 0.12), (x, 0, z1 - 0.12), (x, H, z1 - 0.12), (x, H, z0 + 0.12)], (-sx, 0, 0), rack_uv())
        xa, xb = sorted((x, x - sx * 0.28))
        frame.box((xa, 0, z0 - 0.12), (xb, H + 0.05, z0 + 0.12), skip="y-")                  # the post between two racks
        xa, xb = sorted((x - sx * 0.75, x - sx * 0.87))
        frame.box((xa, H + 0.62, z0 - 0.06), (xb, CEIL, z0 + 0.06), skip="y-y+")             # the tray's hanger
    floor.quad([(-WX, 0, z0), (WX, 0, z0), (WX, 0, z1), (-WX, 0, z1)], (0, 1, 0))
    frame.box((-WX, CEIL - 0.4, z0 - 0.16), (WX, CEIL, z0 + 0.16), skip="y+x-x+")            # a ceiling beam at every bay
    for cx in (-3.2, 3.2):
        lights.box((cx - 0.28, CEIL - 0.56, z0 + 0.5), (cx + 0.28, CEIL - 0.44, z1 - 0.5), skip="y+")
for sx in (-1, 1):
    x = sx * WX
    xa, xb = sorted((x, x - sx * 1.6))
    frame.box((xa, H + 0.3, 0), (xb, H + 0.62, L), skip="z+")                                # the cable tray, the length of the hall
    ceil.quad([(x, H, 0), (x, H, L), (x, CEIL, L), (x, CEIL, 0)], (-sx, 0, 0))               # the wall above the racks
ceil.quad([(-WX, CEIL, 0), (WX, CEIL, 0), (WX, CEIL, L), (-WX, CEIL, L)], (0, -1, 0))
# Ben, 2026-11-10: "Remove that rectangle in the back of the data center hall" (the end wall and the five racks across it
# read as a video screen at the end of the aisle). No end wall now: the last 44 m of the aisle fade into the dark through
# seven black veils across it, so the aisle has no visible end.
for j in range(7):
    z = L - 44.0 + j * 6.0
    fog.quad([(-WX, 0, z), (WX, 0, z), (WX, CEIL, z), (-WX, CEIL, z)], (0, 0, -1))

# the outside, and the mouth: a rim between the inside and the outside, and a thin blue line round the opening
OX, OY0, OY1 = WX + 0.7, -0.4, CEIL + 0.5
case.box((-OX, OY0, 0), (OX, OY1, L + 0.5), skip="z-")
for part, lo, hi in ((frame, (-OX, 0, 0), (-WX, OY1, 0)), (frame, (WX, 0, 0), (OX, OY1, 0)), (frame, (-WX, CEIL, 0), (WX, OY1, 0)),
                     (case, (-OX, OY0, 0), (OX, 0, 0))):          # under the floor it belongs to the outside (it passes under the seats)
    part.quad([(lo[0], lo[1], 0), (hi[0], lo[1], 0), (hi[0], hi[1], 0), (lo[0], hi[1], 0)], (0, 0, -1))
T = 0.14
for lo, hi in (((-WX, 0, 0), (-WX + T, CEIL, 0)), ((WX - T, 0, 0), (WX, CEIL, 0)), ((-WX, CEIL - T, 0), (WX, CEIL, 0))):
    edge.quad([(lo[0], lo[1], -0.02), (hi[0], lo[1], -0.02), (hi[0], hi[1], -0.02), (lo[0], hi[1], -0.02)], (0, 0, -1))

objs = [p.done() for p in (racks, frame, floor, ceil, lights, edge, case, fog)]
bpy.context.view_layer.update()
glb = C.export("datahall", R)
C.report("datahall", C.tris(objs), glb, f"an aisle {2 * WX:g} m wide, {CEIL:g} m high, {L:g} m long: {N} bays of racks a side")
