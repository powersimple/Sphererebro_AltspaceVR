"""talk_text: every on-screen word of the talk as its own mesh (so the engine can fade words in one at a time), plus the
odometer glyphs. Text comes ONLY from talk_show.json "text" (Ben's cue sheet). Objects: <key>_L<line>_W<nn>, origin at the
word's centre, laid out along the line (line centred on x = 0, 1 em = 1 m; the Unity builder scales). glyph_0..9,
glyph_dollar, glyph_point. Front faces +Y like every asset. Also writes the generated images the builder needs that are
not tied to one asset: env_dark.png, warm_room.png, particle_soft.png, contact_shadow.png, feed_icons.png."""
import bpy, bmesh, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import numpy as np
from mathutils import Matrix, Vector

C.begin()
SHOW = json.load(open(os.path.join(C.REPO, "Assets", "_Sphererebro", "Config", "talk_show.json"), encoding="utf-8-sig"))
FONTS = {
    "inter": r"C:\Windows\Fonts\Inter-SemiBold.ttf",
    "aldrich": os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts\Aldrich-Regular.ttf"),
    "stamp": r"C:\Windows\Fonts\bahnschrift.ttf",
}
def font_for(key):
    if key.startswith("label") or key.startswith("glyph") or key.startswith("bill"): return "aldrich"
    if key.startswith("stamp"): return "stamp"
    return "inter"

loaded = {}
def font(name):
    if name not in loaded: loaded[name] = bpy.data.fonts.load(FONTS[name], check_existing=True)
    return loaded[name]

root = C.root("talk_text")
M = C.mat("TK_TextLight")
ROT = Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")   # reads toward -X, faces +Y

def word_mesh(name, body, fnt):
    cu = bpy.data.curves.new(name + "_c", "FONT"); cu.body = body; cu.size = 1.0; cu.font = fnt
    cu.extrude = 0.025; cu.resolution_u = 3; cu.align_x = "LEFT"; cu.align_y = "BOTTOM_BASELINE"
    tmp = bpy.data.objects.new(name + "_t", cu); bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    xs = [v.co.x for v in me.vertices] or [0]
    x0, x1 = min(xs), max(xs)
    adv = x1 - x0
    # centre the word on its own origin (x middle, y at 0.36 em: the middle of lower-case/cap height)
    me.transform(Matrix.Translation((-(x0 + x1) / 2, -0.36, 0)))
    me.transform(ROT)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.parent = root; o.data.materials.append(M); o["keep_uv"] = True
    return o, x0, x1

def space_w(fnt):
    a, _, _ = word_mesh("_sp_a", "a a", fnt); b, _, _ = word_mesh("_sp_b", "aa", fnt)
    wa = max(v.co.x for v in a.data.vertices) - min(v.co.x for v in a.data.vertices)
    wb = max(v.co.x for v in b.data.vertices) - min(v.co.x for v in b.data.vertices)
    bpy.data.objects.remove(a); bpy.data.objects.remove(b)
    return abs(wa - wb)

texts = dict(SHOW["text"])
texts["billsub"] = ["per megawatt-day"]
texts.pop("bill", None)                        # "$333.44" is the odometer (glyphs); its words are the sub line
count = 0
for key, lines in texts.items():
    fnt = font(font_for(key)); sp = space_w(fnt)
    for li, line in enumerate(lines):
        words = line.split(" ")
        made = []
        for wi, w in enumerate(words):
            o, x0, x1 = word_mesh(f"{key}_L{li}_W{wi:02d}", w, fnt)
            made.append((o, x1 - x0))
            count += 1
        total = sum(wd for _, wd in made) + sp * (len(made) - 1)
        x = -total / 2
        for o, wd in made:
            cx = x + wd / 2
            o.location = (-cx, 0, 0)            # Blender -x = Unity +x (the viewer's right)
            x += wd + sp
for g, label in [(str(d), str(d)) for d in range(10)] + [("$", "dollar"), (".", "point")]:
    o, x0, x1 = word_mesh(f"glyph_{label}", g, font("aldrich"))
    o.location = (0, 0, 0)
print(f"[talk_text] {count} words + 12 glyphs")
C.finish("talk_text", preview_on=False, note="all on-screen words, one mesh per word")

# ------------------------------------------------------------------ shared generated images
def grad_sphere(name, stops, H=512):
    """vertical gradient for an inverted env sphere: stops = [(v, (r,g,b)), ...], v 0 = bottom, 1 = top."""
    v = np.linspace(1, 0, H)
    img = np.zeros((H, 8, 3), np.float32)
    for c in range(3):
        img[:, :, c] = np.interp(v, [s[0] for s in stops], [s[1][c] for s in stops])[:, None]
    C.save_png(name, img)

grad_sphere("env_dark.png", [(0, (0.004, 0.004, 0.008)), (0.45, (0.010, 0.012, 0.022)), (0.5, (0.016, 0.018, 0.032)), (0.6, (0.008, 0.009, 0.018)), (1, (0.002, 0.002, 0.006))])
grad_sphere("warm_room.png", [(0, (0.10, 0.06, 0.04)), (0.42, (0.42, 0.22, 0.10)), (0.5, (0.95, 0.62, 0.30)), (0.56, (0.70, 0.42, 0.28)), (0.7, (0.22, 0.18, 0.30)), (1, (0.04, 0.05, 0.12))])
N = 128
yy, xx = np.mgrid[0:N, 0:N] / (N - 1) * 2 - 1
r = np.sqrt(xx ** 2 + yy ** 2)
soft = np.clip(1 - r, 0, 1) ** 2.2
C.save_png("particle_soft.png", np.dstack([soft, soft, soft, soft]).astype(np.float32))
# contact shadow: dark in the middle of the footprint, soft to the edge (multiply: white = no change)
sh = np.clip((np.maximum(np.abs(xx) * 1.0, np.abs(yy) * 1.0) - 0.55) / 0.45, 0, 1) ** 0.8
sh = 0.45 + 0.55 * sh
C.save_png("contact_shadow.png", np.dstack([sh, sh, sh]).astype(np.float32))
# feed icons: [play in a dark disc | heart], 512 x 256, alpha
W2 = 256
yy, xx = np.mgrid[0:W2, 0:W2] / (W2 - 1) * 2 - 1
disc = (np.sqrt(xx ** 2 + yy ** 2) < 0.92).astype(np.float32)
tri = ((xx > -0.28) & (np.abs(yy) < (0.55 - (xx + 0.28) * 0.62))).astype(np.float32)
play = np.zeros((W2, W2, 4), np.float32)
play[..., :3] = 0.03; play[..., 3] = disc * 0.62
play[tri > 0] = [1, 1, 1, 1]
hx, hy = xx * 1.25, -yy * 1.25 + 0.25
heart = ((hx ** 2 + hy ** 2 - 0.6) ** 3 - hx ** 2 * hy ** 3 < 0).astype(np.float32)
hrt = np.zeros((W2, W2, 4), np.float32); hrt[..., 0] = 1.0; hrt[..., 1] = 0.2; hrt[..., 2] = 0.36; hrt[..., 3] = heart
C.save_png("feed_icons.png", np.concatenate([play, hrt], 1))
print("[talk_text] images written")
