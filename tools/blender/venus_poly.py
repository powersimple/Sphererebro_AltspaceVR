"""venus_poly: Ben's Venus figure (D:/WebXR/AWETalks/AWE2025/VenusPoly.glb, 393,000 triangles, six gold materials, no
textures) made fit for Quest: joined, cut to about 40,000 triangles, 1 unit tall, standing on the origin, front toward
-Z in Unity. Two materials: TK_VenusGold (the red gold) and TK_VenusBrass (the yellow), talk_materials_stills.json.
Run: blender -b --factory-startup --python tools/blender/venus_poly.py [-- path to the GLB]
"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from mathutils import Vector, Matrix

SRC = r"D:\WebXR\AWETalks\AWE2025\VenusPoly.glb"
TARGET = 40000

C.begin()
R = C.root("venus_poly")
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in bpy.context.scene.objects: o.select_set(o in meshes)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
o = bpy.context.view_layer.objects.active
o.parent = None
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# the two golds, by the source material's colour (green channel: 0.305 red gold, 0.55 yellow)
gold, brass = C.mat("TK_VenusGold"), C.mat("TK_VenusBrass")
for i, slot in enumerate(o.material_slots):
    src = slot.material; g = 0.3
    if src and src.node_tree:
        b = next((n for n in src.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b: g = b.inputs["Base Color"].default_value[1]
    slot.material = brass if g > 0.42 else gold

# weld the seams and make the normals agree before cutting (the source is a dense sculpt)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0002); bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
before = sum(len(p.vertices) - 2 for p in o.data.polygons)
m = o.modifiers.new("Decimate", "DECIMATE"); m.ratio = min(1.0, TARGET / before)
bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.shade_smooth()

# 1 unit tall, standing on the origin, centred; turned half round (glTF's front is +Z, the show's is -Z)
vs = [v.co for v in o.data.vertices]
lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
k = 1.0 / (hi.z - lo.z)
o.data.transform(Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Scale(k, 4) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
o.data.update()
o.name = "Venus"; o.data.name = "Venus"; o.parent = R
for x in list(bpy.context.scene.objects):
    if x is not o and x is not R: bpy.data.objects.remove(x)

bpy.context.view_layer.update()
objs = C._tree(R)
glb = C.export("venus_poly", R)
if C.ARGS["preview"]: C.preview("venus_poly", objs)
C.report("venus_poly", C.tris(objs), glb, f"Ben's VenusPoly.glb cut from {before:,} triangles; 1 unit tall, {(hi.x - lo.x) * k:.2f} wide")
