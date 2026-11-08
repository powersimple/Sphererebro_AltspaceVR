"""server_rack_far / server_rack_far_open: the distant racks of the data-hall field (Quest budget). The hero rack (and its
open variant) decimated to about a third of the triangles; LEDs kept whole (they are what reads at distance).
Built from talk/models/server_rack_hero.glb and server_rack_open.glb (run server_rack.py first)."""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

C.begin()
for src, name in (("server_rack_hero", "server_rack_far"), ("server_rack_open", "server_rack_far_open")):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(C.GLB_DIR, src + ".glb"))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    r = C.root(name)
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = r; o.matrix_world = mw
        # the GLB importer names materials by their TK_ names; make sure we use the shared ones
        for i, m in enumerate(o.data.materials):
            if m and m.name.split(".")[0] in C.MATS: o.data.materials[i] = C.mat(m.name.split(".")[0])
        if o.name.startswith("LEDs"): continue
        d = o.modifiers.new("dec", "DECIMATE"); d.ratio = 0.3
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
        o["keep_uv"] = True
    for o in list(bpy.data.objects):
        if o.type == "EMPTY" and o is not r: bpy.data.objects.remove(o, do_unlink=True)
    C.finish(name, r, preview_on=(name == "server_rack_far"), note=f"{src} decimated to ~30% (LEDs whole), for distant racks")
