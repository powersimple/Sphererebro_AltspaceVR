"""Shared helpers for the talk asset scripts (Blender 5.1 or 5.2, run headless).

Each asset script:
    import common as C
    C.begin()                       # parses args, clears the scene
    ... build objects with C.box / C.cyl / C.mesh_from_bm ..., C.mat("TK_...") ...
    C.finish("server_rack_hero")    # UVs, applies transforms, exports GLB + FBX (+LOD1), preview, report

Conventions (see SPHEREREBRO_STATUS.md Decisions):
- metres; origin at the BASE CENTRE (z = 0 is the floor); the FRONT faces Blender +Y.
  Unity import: Blender (x, y, z) -> Unity (-x, z, -y), so the front faces Unity -Z: toward the audience at yaw 0.
- one root EMPTY named after the asset; parts are child meshes with stable names (the Unity builder animates parts
  by name: e.g. "Doors", "LEDs_Green").
- materials come from talk_materials.json by name (TK_*); UVs are box-projected in metres / the material's tile.
Command line:  blender -b --factory-startup --python tools/blender/<asset>.py -- [--out talk/models/<name>.glb]
               [--no-preview] [--no-fbx]
"""
import bpy, bmesh, json, math, os, sys, time
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TEX_DIR = os.path.join(REPO, "tools", "textures")
GEN_DIR = os.path.join(REPO, "talk", "gen")            # generated images (emission maps, screens)
GLB_DIR = os.path.join(REPO, "talk", "models")
PREV_DIR = os.path.join(REPO, "talk", "previews")
FBX_DIR = os.path.join(REPO, "Assets", "_Sphererebro", "Talk", "Models")
MATS = {k: v for k, v in json.load(open(os.path.join(HERE, "talk_materials.json"))).items() if not k.startswith("_")}
# optional modules bring their own materials: talk_materials_<module>.json beside this file (e.g. the Ashburn zoom)
for _f in sorted(os.listdir(HERE)):
    if _f.startswith("talk_materials_") and _f.endswith(".json"):
        MATS.update({k: v for k, v in json.load(open(os.path.join(HERE, _f))).items() if not k.startswith("_")})

ARGS = {"out": None, "preview": True, "fbx": True}
ROOT = None


def _args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    i = 0
    while i < len(a):
        if a[i] == "--out": ARGS["out"] = a[i + 1]; i += 2; continue
        if a[i] == "--no-preview": ARGS["preview"] = False
        if a[i] == "--no-fbx": ARGS["fbx"] = False
        i += 1


def begin():
    _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for d in (GEN_DIR, GLB_DIR, PREV_DIR, FBX_DIR): os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- materials
def _img(path, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color: img.colorspace_settings.name = "Non-Color"
    return img


def _texfile(texid, kind):
    p = os.path.join(TEX_DIR, texid, f"{texid}_1K-JPG_{kind}.jpg")
    return p if os.path.exists(p) else None


def mat(name):
    """The TK_ material `name` (created once, from talk_materials.json)."""
    m = bpy.data.materials.get(name)
    if m: return m
    spec = MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N.get("Principled BSDF")
    tint = spec.get("tint", [1, 1, 1])
    tex = spec.get("tex")
    col_out = None
    if tex and _texfile(tex, "Color"):
        ti = N.new("ShaderNodeTexImage"); ti.image = _img(_texfile(tex, "Color"))
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
        L.new(ti.outputs["Color"], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        col_out = mix.outputs[2]
        L.new(col_out, bsdf.inputs["Base Color"])
        if _texfile(tex, "NormalGL"):
            tn = N.new("ShaderNodeTexImage"); tn.image = _img(_texfile(tex, "NormalGL"), True)
            nm = N.new("ShaderNodeNormalMap"); L.new(tn.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        if spec.get("rough") is None and _texfile(tex, "Roughness"):
            tr = N.new("ShaderNodeTexImage"); tr.image = _img(_texfile(tex, "Roughness"), True)
            L.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
        if spec.get("metal") is None and _texfile(tex, "Metalness"):
            tm = N.new("ShaderNodeTexImage"); tm.image = _img(_texfile(tex, "Metalness"), True)
            L.new(tm.outputs["Color"], bsdf.inputs["Metallic"])
        if spec.get("alpha") == "clip" and _texfile(tex, "Opacity"):
            to = N.new("ShaderNodeTexImage"); to.image = _img(_texfile(tex, "Opacity"), True)
            L.new(to.outputs["Color"], bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = (*tint, 1)
    if spec.get("rough") is not None: bsdf.inputs["Roughness"].default_value = spec["rough"]
    if spec.get("metal") is not None: bsdf.inputs["Metallic"].default_value = spec["metal"]
    emit = spec.get("emit"); etex = spec.get("emitTex")
    if etex:
        p = os.path.join(GEN_DIR, etex)
        if os.path.exists(p):
            te = N.new("ShaderNodeTexImage"); te.image = _img(p)
            L.new(te.outputs["Color"], bsdf.inputs["Base Color"])
            if emit:
                L.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = max(emit)
    elif emit:
        s = max(emit)
        bsdf.inputs["Emission Color"].default_value = (emit[0] / s, emit[1] / s, emit[2] / s, 1)
        bsdf.inputs["Emission Strength"].default_value = s
    if spec.get("alpha") == "blend":
        bsdf.inputs["Alpha"].default_value = spec.get("opacity", 0.5)
    if spec.get("alpha") in ("blend", "clip"):
        try: m.surface_render_method = "BLENDED" if spec["alpha"] == "blend" else "DITHERED"
        except Exception: pass
    return m


def tile_of(m):
    return MATS.get(m.name, {}).get("tile", 1.0) if m else 1.0


# ---------------------------------------------------------------- geometry
def root(name):
    """The asset's root empty (one per asset)."""
    global ROOT
    ROOT = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(ROOT)
    return ROOT


def obj_from_bm(name, bm, materials, parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in materials: me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent if parent is not None else ROOT
    return o


def bm_box(bm, size, loc=(0, 0, 0), mat_index=0, rot_z=0.0):
    """Add an axis box (sx, sy, sz) centred at loc to bm."""
    sx, sy, sz = size
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    M = Matrix.Translation(loc) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mat_index
    return vs


def bm_cyl(bm, r, depth, loc=(0, 0, 0), segs=24, mat_index=0, axis="Z", r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    vs = res["verts"]
    R = Matrix.Identity(4)
    if axis == "X": R = Matrix.Rotation(math.pi / 2, 4, "Y")
    if axis == "Y": R = Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ R, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mat_index
    return vs


def part(name, builder, mats, parent=None, smooth=False):
    """part("Frame", lambda bm: ..., [mat("TK_RackFrame")]) -> object."""
    bm = bmesh.new()
    builder(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    o = obj_from_bm(name, bm, mats, parent)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    return o


def box_uv(o):
    """Box-project UVs in metres / the material's tile. Materials with tile 0 keep existing UVs (or get 0..1 planar)."""
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    mw = o.matrix_world
    for f in bm.faces:
        m = me.materials[f.material_index] if f.material_index < len(me.materials) else None
        t = tile_of(m)
        if not t: continue
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            if ax == 0: u, v = p.y * (1 if n.x > 0 else -1), p.z
            elif ax == 1: u, v = p.x * (-1 if n.y > 0 else 1), p.z
            else: u, v = p.x, p.y * (1 if n.z > 0 else -1)
            l[uv].uv = (u / t, v / t)
    bm.to_mesh(me); bm.free()


def planar_uv(o, axis="Y", bounds=None):
    """0..1 UVs across the object's extent on the plane facing `axis` (for screens, labels, emission sheets)."""
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    xs = [v.co for v in me.vertices]
    if bounds is None:
        mn = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
        mx = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    else: mn, mx = bounds
    a, b = {"Y": (0, 2), "X": (1, 2), "Z": (0, 1)}[axis]
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            u = (p[a] - mn[a]) / max(1e-6, mx[a] - mn[a]); v = (p[b] - mn[b]) / max(1e-6, mx[b] - mn[b])
            if axis == "Y": u = 1 - u  # front faces +Y: looking at it from +Y, +x is on the viewer's left
            me.uv_layers.active.data[li].uv = (u, v)


# ---------------------------------------------------------------- images
def save_png(name, arr):
    """arr: numpy float32 HxWx3 or x4 in 0..1 (top row first). Saved to talk/gen/<name>."""
    import numpy as np
    h, w = arr.shape[:2]
    if arr.shape[2] == 3: arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], axis=2)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
    p = os.path.join(GEN_DIR, name)
    img.filepath_raw = p; img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)
    return p


# ---------------------------------------------------------------- finish / export
def tris(objs):
    n = 0
    for o in objs:
        if o.type == "MESH":
            for p in o.data.polygons: n += len(p.vertices) - 2
    return n


def _select(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def _tree(r):
    out = [r]
    for c in r.children: out += _tree(c)
    return out


def export(name, r):
    objs = _tree(r)
    _select(objs)
    glb = ARGS["out"] if (ARGS["out"] and r is ROOT) else os.path.join(GLB_DIR, name + ".glb")
    glb = os.path.join(REPO, glb) if not os.path.isabs(glb) else glb
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=85)
    # sidecar for Unity: the FBX is imported without materials, so the builder needs each object's material slot names
    slots = {o.name: [m.name if m else "" for m in o.data.materials] for o in objs if o.type == "MESH"}
    with open(os.path.join(GLB_DIR, name + ".mats.json"), "w") as f: json.dump(slots, f)
    if ARGS["fbx"]:
        bpy.ops.export_scene.fbx(filepath=os.path.join(FBX_DIR, name + ".fbx"), use_selection=True,
                                 apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y",
                                 bake_space_transform=True, object_types={"MESH", "EMPTY"}, mesh_smooth_type="FACE",
                                 add_leaf_bones=False, use_mesh_modifiers=True, path_mode="STRIP")
    return glb


def make_lod1(name, r):
    """A copy at ~40% of the triangles (Decimate collapse), as <name>_lod1."""
    objs = [o for o in _tree(r) if o.type == "MESH"]
    nr = bpy.data.objects.new(name + "_lod1", None); bpy.context.scene.collection.objects.link(nr)
    for o in objs:
        c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c)
        c.parent = nr; c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        d = c.modifiers.new("dec", "DECIMATE"); d.ratio = 0.4
        bpy.context.view_layer.objects.active = c
        bpy.ops.object.select_all(action="DESELECT"); c.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
    return nr


def preview(name, objs):
    """2x2 turntable sheet (front, 3/4, side, back 3/4) to talk/previews/<name>.png."""
    import numpy as np
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: sc.render.engine = eng; break
        except Exception: pass
    sc.render.resolution_x = sc.render.resolution_y = 512
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("pv"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.065, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH": continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
    ctr = (mn + mx) / 2; rad = max((mx - mn).length / 2, 0.01)
    cam_d = bpy.data.cameras.new("pc"); cam_d.lens = 50; cam_d.clip_end = rad * 20
    cam = bpy.data.objects.new("pc", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    for nm, e, rot in (("k", 4.0, (50, 0, 30)), ("f", 1.5, (65, 0, -60)), ("r", 3.0, (120, 0, 180))):
        ld = bpy.data.lights.new(nm, "SUN"); ld.energy = e
        lo = bpy.data.objects.new(nm, ld); sc.collection.objects.link(lo)
        lo.rotation_euler = [math.radians(a) for a in rot]
    tiles = []
    for yaw in (0, 40, 90, 200):
        a = math.radians(yaw)
        d = rad * 2.9
        cam.location = ctr + Vector((math.sin(a) * d, math.cos(a) * d, rad * 0.55))
        dirv = (ctr - cam.location).normalized()
        cam.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
        p = os.path.join(PREV_DIR, f"_{name}_{yaw}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p)
        arr = np.array(im.pixels[:], np.float32).reshape(512, 512, 4)[::-1]
        tiles.append(arr); bpy.data.images.remove(im); os.remove(p)
    sheet = np.concatenate([np.concatenate(tiles[:2], 1), np.concatenate(tiles[2:], 1)], 0)
    img = bpy.data.images.new(name + "_prev", 1024, 1024, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(sheet[::-1]).ravel())
    img.filepath_raw = os.path.join(PREV_DIR, name + ".png"); img.file_format = "PNG"; img.save()


def report(name, ntris, path, note=""):
    size = os.path.getsize(path) if os.path.exists(path) else 0
    with open(os.path.join(GLB_DIR, "report.jsonl"), "a") as f:
        f.write(json.dumps({"asset": name, "tris": ntris, "bytes": size, "glb": os.path.relpath(path, REPO).replace("\\", "/"),
                            "note": note, "time": time.strftime("%Y-%m-%d %H:%M")}) + "\n")
    print(f"[talk asset] {name}: {ntris} tris, {size / 1024:.0f} KB -> {path}")


def finish(name, r=None, preview_on=True, note=""):
    r = r or ROOT
    objs = _tree(r)
    for o in objs:
        if o.type == "MESH": box_uv(o) if not o.get("keep_uv") else None
    bpy.context.view_layer.update()
    n = tris(objs)
    glb = export(name, r)
    report(name, n, glb, note)
    if n > 20000:
        l = make_lod1(name, r)
        g2 = export(name + "_lod1", l)
        report(name + "_lod1", tris(_tree(l)), g2, "LOD1 (decimate 0.4)")
        for o in _tree(l): bpy.data.objects.remove(o, do_unlink=True)
    if ARGS["preview"] and preview_on: preview(name, objs)
    return n
