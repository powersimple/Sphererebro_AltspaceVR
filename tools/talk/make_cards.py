"""Timeline cards for cue 2T: one 1024x256 card per event (ffmpeg drawtext + the public-domain photos from Ben's
2020Vision assets), packed 2 x 8 into 2048x2048 atlases talk/gen/tl_cards_<n>.png, with talk/gen/tl_cards.json
(uv rect and world size of each card) for SphererebroTalkTimeline.cs and the harness.
Run: <blender python> tools/talk/make_cards.py
"""
import json, os, subprocess, glob, textwrap, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
GEN = os.path.join(REPO, "talk", "gen")
TL = json.load(open(os.path.join(REPO, "Assets", "_Sphererebro", "Config", "talk_timeline_events.json"), encoding="utf-8-sig"))
ASSETS = r"B:\_powersimple\OmniScience\2020Vision\assets"
FF = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))[0]
F_YEAR = r"C\:/Users/power/AppData/Local/Microsoft/Windows/Fonts/Aldrich-Regular.ttf"
F_TEXT = r"C\:/Windows/Fonts/Inter-SemiBold.ttf"
F_TEXT2 = r"C\:/Windows/Fonts/Inter-Regular.ttf"
W, H = 1024, 256
tmp = tempfile.mkdtemp(prefix="tlcards_")


def ffp(p): return p.replace("\\", "/").replace(":", "\\:")


def run(args):
    r = subprocess.run([FF, "-y", "-loglevel", "error"] + args, capture_output=True, text=True)
    if r.returncode: raise SystemExit("ffmpeg failed: " + r.stderr[-800:])


cards = []
for i, ev in enumerate(TL["events"]):
    media = ev["kind"] == "media"
    img = ev.get("img")
    if img and not os.path.exists(os.path.join(ASSETS, img)): img = None
    tx = 300 if img else 40
    width_chars = 40 if img else 54
    lines = textwrap.wrap(ev["t"], width_chars)[:3]
    year = ("c. " if ev.get("approx") else "") + str(ev["y"])
    yf = os.path.join(tmp, f"y{i}.txt"); open(yf, "w", encoding="utf-8", newline="\n").write(year)
    tf = os.path.join(tmp, f"t{i}.txt"); open(tf, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    bg = "0x0b0d12@0.86" if media else "0x0b0d12@0.62"
    gold = "0xf2c46b" if media else "0x9a8a6a"
    ink = "0xf4f1ea" if media else "0xb8b4ac"
    fs = 34 if len(lines) <= 2 else 29
    vf = (f"drawbox=x=0:y=0:w=6:h={H}:color={gold}@1:t=fill,"
          f"drawbox=x=0:y=0:w={W}:h=2:color={gold}@0.6:t=fill,"
          f"drawtext=fontfile='{F_YEAR}':textfile='{ffp(yf)}':fontcolor={gold}:fontsize={62 if media else 50}:x={tx}:y=22,"
          f"drawtext=fontfile='{F_TEXT if media else F_TEXT2}':textfile='{ffp(tf)}':fontcolor={ink}:fontsize={fs}:line_spacing=6:x={tx}:y={100 if media else 92}")
    out = os.path.join(tmp, f"card_{i:03d}.png")
    if img:
        run(["-f", "lavfi", "-i", f"color=c={bg}:s={W}x{H},format=rgba", "-i", os.path.join(ASSETS, img),
             "-filter_complex", f"[1:v]scale=232:232:force_original_aspect_ratio=increase,crop=232:232,format=rgba[p];"
                                f"[0:v][p]overlay=24:12,{vf}", "-frames:v", "1", out])
    else:
        run(["-f", "lavfi", "-i", f"color=c={bg}:s={W}x{H},format=rgba", "-vf", vf, "-frames:v", "1", out])
    cards.append({"i": i, "year": ev["y"], "kind": ev["kind"], "img": img, "w": 8.0 if media else 5.6, "h": 2.0 if media else 1.4})

PER = 16
os.makedirs(GEN, exist_ok=True)
for a in range(0, (len(cards) + PER - 1) // PER):
    chunk = cards[a * PER:(a + 1) * PER]
    d = os.path.join(tmp, f"atlas{a}"); os.makedirs(d)
    for j, c in enumerate(chunk): shutil.copy(os.path.join(tmp, f"card_{c['i']:03d}.png"), os.path.join(d, f"c_{j:03d}.png"))
    for j in range(len(chunk), PER):     # transparent fillers
        run(["-f", "lavfi", "-i", f"color=c=0x000000@0:s={W}x{H},format=rgba", "-frames:v", "1", os.path.join(d, f"c_{j:03d}.png")])
    run(["-framerate", "1", "-i", os.path.join(d, "c_%03d.png"), "-vf", "tile=2x8,format=rgba", "-frames:v", "1", os.path.join(GEN, f"tl_cards_{a}.png")])
    for j, c in enumerate(chunk):
        col, row = j % 2, j // 2
        c.update({"atlas": a, "u0": col * 0.5, "u1": col * 0.5 + 0.5, "v0": 1 - (row + 1) / 8, "v1": 1 - row / 8})
json.dump({"cards": cards}, open(os.path.join(GEN, "tl_cards.json"), "w"), indent=1)
shutil.copy(os.path.join(tmp, "card_016.png"), os.path.join(GEN, "_sample_card.png"))
print(f"cards: {len(cards)} in {(len(cards) + PER - 1) // PER} atlases -> {GEN}")
