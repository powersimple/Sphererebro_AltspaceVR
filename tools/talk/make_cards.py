"""Timeline cards for cue 2T (the media timeline, tools/talk/layers.py): one 1024x256 card per item, layer name and
axis year (ffmpeg drawtext; warm and dim, never white: rule 12), packed 2 x 8 into 2048x2048 atlases talk/gen/tl_cards_<n>.png, with talk/gen/tl_cards.json
(uv rect and world size of each card) for SphererebroTalkTimeline.cs and the harness.
Run: <blender python> tools/talk/make_cards.py
"""
import json, os, subprocess, glob, textwrap, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
GEN = os.path.join(REPO, "talk", "gen")
import sys; sys.path.insert(0, HERE)
import layers as LY
FF = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))[0]
def ffp(p): return p.replace("\\", "/").replace(":", "\\:")
_ald = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Aldrich-Regular.ttf")
F_YEAR = ffp(_ald if os.path.exists(_ald) else r"C:\Windows\Fonts\Inter-SemiBold.ttf")
F_TEXT = ffp(r"C:\Windows\Fonts\Inter-SemiBold.ttf")
W, H = 1024, 256
tmp = tempfile.mkdtemp(prefix="tlcards_")
INK = "0xd8c9a8"            # warm, dim: no white on the dark sphere


def run(args):
    r = subprocess.run([FF, "-y", "-loglevel", "error"] + args, capture_output=True, text=True)
    if r.returncode: raise SystemExit("ffmpeg failed: " + r.stderr[-800:])


def txt(name, s):
    f = os.path.join(tmp, name); open(f, "w", encoding="utf-8", newline="\n").write(s); return ffp(f)


IMG = os.path.join(REPO, "talk", "timeline_img")
cards, pics = [], []
for c in LY.layout()["cards"]:
    i = c["i"]; col = "0x" + c["color"]
    if c["kind"] == "pic":
        src = os.path.join(IMG, c["img"])
        if not os.path.exists(src): raise SystemExit("timeline picture missing: " + src)
        out = os.path.join(tmp, f"pic_{i:03d}.png")      # centre square, 512 px, a thin frame in the layer's colour
        run(["-i", src, "-vf", f"scale=512:512:force_original_aspect_ratio=increase,crop=512:512,drawbox=x=0:y=0:w=512:h=512:color={col}@0.9:t=6,format=rgba", "-frames:v", "1", out])
        pics.append({"i": i, "year": None, "kind": "pic", "img": c["img"], "w": c["w"], "h": c["h"], "file": out})
        continue
    if c["kind"] == "item":
        year = ("c. " if c.get("approx") else "") + str(c["year"])
        tx = 300 if c.get("img") else 44                 # a pictured card keeps its left end clear for the picture
        room = (W - tx - 20) / 0.56
        fs = int(min(84, room / max(1, len(c["t"]))))
        vf = (f"drawbox=x=0:y=0:w=10:h={H}:color={col}@1:t=fill,"
              f"drawtext=fontfile='{F_YEAR}':textfile='{txt(f'y{i}.txt', year)}':fontcolor={col}:fontsize=92:x={tx}:y=24,"
              f"drawtext=fontfile='{F_TEXT}':textfile='{txt(f't{i}.txt', c['t'])}':fontcolor={INK}:fontsize={fs}:x={tx}:y={142 + (84 - fs) // 2}")
        bg = "0x0b0d12@0.6"
    elif c["kind"] == "layer":
        vf = f"drawtext=fontfile='{F_YEAR}':textfile='{txt(f't{i}.txt', c['t'].upper())}':fontcolor={col}:fontsize=88:x=w-tw-30:y=(h-th)/2"
        bg = "0x000000@0"
    else:
        vf = f"drawtext=fontfile='{F_YEAR}':textfile='{txt(f'y{i}.txt', str(c['year']))}':fontcolor={col}:fontsize=150:x=(w-tw)/2:y=(h-th)/2"
        bg = "0x000000@0"
    out = os.path.join(tmp, f"card_{i:03d}.png")
    run(["-f", "lavfi", "-i", f"color=c={bg}:s={W}x{H},format=rgba", "-vf", vf, "-frames:v", "1", out])
    cards.append({"i": i, "year": c.get("year"), "kind": c["kind"], "img": c.get("img"), "w": c["w"], "h": c["h"], "file": out})

# Atlases, 2048 x 2048 each (ASTC 6x6 on Quest, about 1.9 MB): text cards drawn at 1024 x 256 and packed at half size
# (4 x 16 = 64 a sheet: plenty for a 1.5 m card 46 m away); pictures 512 x 512, 4 x 4 = 16 a sheet. Was six sheets.
os.makedirs(GEN, exist_ok=True)
for f in glob.glob(os.path.join(GEN, "tl_cards_*.png")): os.remove(f)
atlas = 0
def pack(group, cols, rows, cw, ch):
    global atlas
    per = cols * rows
    for a in range(0, len(group), per):
        chunk = group[a:a + per]
        d = os.path.join(tmp, f"atlas{atlas}"); os.makedirs(d)
        for j, c in enumerate(chunk): shutil.copy(c["file"], os.path.join(d, f"c_{j:03d}.png"))
        # transparent fillers, made FROM a real card (same size and pixel format, alpha zeroed). A lavfi colour frame came
        # out in another format: the sheet then read its real cards as transparent and its fillers as solid black, so every
        # card on a part-filled sheet was blank in the world (2026-11-10: the last two layers and the year labels)
        for j in range(len(chunk), per):
            run(["-i", chunk[0]["file"], "-vf", "format=rgba,colorchannelmixer=rr=0:gg=0:bb=0:aa=0", "-frames:v", "1", os.path.join(d, f"c_{j:03d}.png")])
        run(["-framerate", "1", "-i", os.path.join(d, "c_%03d.png"), "-vf", f"scale={cw}:{ch}:flags=lanczos,tile={cols}x{rows},format=rgba", "-frames:v", "1", os.path.join(GEN, f"tl_cards_{atlas}.png")])
        for j, c in enumerate(chunk):
            x, y = j % cols, j // cols
            c.update({"atlas": atlas, "u0": x / cols, "u1": (x + 1) / cols, "v0": 1 - (y + 1) / rows, "v1": 1 - y / rows})
        atlas += 1
pack(cards, 4, 16, 512, 128)
pack(pics, 4, 4, 512, 512)
allc = sorted(cards + pics, key=lambda c: c["i"])
for c in allc: del c["file"]
json.dump({"cards": allc}, open(os.path.join(GEN, "tl_cards.json"), "w"), indent=1)
print(f"cards: {len(cards)} text + {len(pics)} pictures in {atlas} atlases -> {GEN}")
