"""stills: one flat picture per still in tools/geo/stills_data.json (tools/geo/stills_art.py), for the module "stills".
UNITY axes: each part Pic_<name> is 1 high and (width / height) wide, centred on the origin, facing -Z (the seats).
Material TK_Still_<name> (talk_materials_stills.json).   Run: blender -b --factory-startup --python tools/blender/stills.py
"""
import bpy, bmesh, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector

C.begin()
D = json.load(open(os.path.join(C.REPO, "tools", "geo", "stills_data.json"), encoding="utf-8"))
R = C.root("stills")


def B(v): return Vector((-v[0], -v[2], v[1]))            # Unity -> Blender


for name, s in D["stills"].items():
    me = bpy.data.meshes.new("Pic_" + name); me.materials.append(C.mat("TK_Still_" + name))
    o = bpy.data.objects.new("Pic_" + name, me); bpy.context.scene.collection.objects.link(o); o.parent = R
    o["keep_uv"] = True
    w = s["w"] / s["h"] / 2
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    if s.get("depth"):
        # a relief: a grid pushed toward the seats (-Z) by the depth image (white = near), up to RELIEF of the height
        img = bpy.data.images.load(os.path.join(C.GEN_DIR, s["depth"])); iw, ih = img.size; px = list(img.pixels)
        def depth(u, v): return px[4 * (min(ih - 1, int(v * ih)) * iw + min(iw - 1, int(u * iw)))]
        NX = 110; NY = round(NX * s["h"] / s["w"]); RELIEF = 0.16
        grid = [[bm.verts.new(B((-w + 2 * w * i / NX, -0.5 + j / NY, -RELIEF * depth(i / NX, j / NY)))) for i in range(NX + 1)] for j in range(NY + 1)]
        for j in range(NY):
            for i in range(NX):
                f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
                for l, uv in zip(f.loops, ((i / NX, j / NY), ((i + 1) / NX, j / NY), ((i + 1) / NX, (j + 1) / NY), (i / NX, (j + 1) / NY))): l[uvl].uv = uv
        bm.to_mesh(me); bm.free(); continue
    quad = [((-w, -0.5, 0), (0, 0)), ((w, -0.5, 0), (1, 0)), ((w, 0.5, 0), (1, 1)), ((-w, 0.5, 0), (0, 1))]
    f = bm.faces.new([bm.verts.new(B(p)) for p, _ in quad])
    for l, (_, uv) in zip(f.loops, quad): l[uvl].uv = uv
    bm.to_mesh(me); bm.free()

bpy.context.view_layer.update()
objs = C._tree(R)
glb = C.export("stills", R)
C.report("stills", C.tris(objs), glb, "flat pictures: " + ", ".join(D["stills"]))
