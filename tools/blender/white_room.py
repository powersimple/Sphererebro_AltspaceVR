"""white_room: the white void for cue 4 ("The Construct"). An inverted sphere, unlit, with a faint floor gradient baked into
its emission image (talk/gen/white_room.png). Radius 450 m: far larger than the 50 m theatre shell, so the rows of 50 m racks
can run out to a white horizon (Decision in SPHEREREBRO_STATUS.md). Origin at the centre of the sphere (not the base: it is
placed with its centre at the audience). Normals face inward."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import numpy as np

C.begin()
R = 450.0
# emission image: u = around, v = bottom (0) .. top (1). Pure white sky, a soft cool-grey band near the horizon, a faint
# warm-grey floor that fades into the horizon: enough to read "ground" without a hard horizon line.
H, W = 512, 16
v = np.linspace(1, 0, H)[:, None]                 # row 0 = top
lat = (v - 0.5) * math.pi                          # -pi/2 .. pi/2
sky = np.ones((H, W, 3), np.float32) * 0.97
floor_mix = np.clip((-lat) / (math.pi / 2), 0, 1) ** 0.6    # 0 at horizon, 1 straight down
floor_col = np.array([0.80, 0.79, 0.77], np.float32)
img = sky * (1 - floor_mix[..., None] * 0.22) + floor_col * (floor_mix[..., None] * 0.22)
band = np.exp(-((lat) / 0.05) ** 2)                # very soft horizon haze (brighter, not darker: no line)
img = np.clip(img + band[..., None] * 0.03, 0, 1)
C.save_png("white_room.png", img.astype(np.float32))

C.root("white_room")
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=R)
bmesh.ops.reverse_faces(bm, faces=bm.faces)
o = C.obj_from_bm("WhiteRoom", bm, [C.mat("TK_WhiteRoom")])
me = o.data; me.uv_layers.new(name="UVMap")
for p in me.polygons:
    p.use_smooth = True
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        u = (math.atan2(co.x, co.y) / (2 * math.pi)) % 1.0
        vv = 0.5 + math.asin(max(-1, min(1, co.z / R))) / math.pi
        me.uv_layers.active.data[li].uv = (u, vv)
o["keep_uv"] = True
C.finish("white_room", note="inverted sphere r 450, unlit, floor gradient in its emission map")
