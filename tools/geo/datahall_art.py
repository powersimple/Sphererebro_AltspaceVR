"""Textures for the module "datahall" (tools/talk/modules/datahall.py, tools/blender/datahall.py). Drawn, not photographed:
nothing here is copied from the reference pictures Ben sent (dark aisles of black racks with blue LEDs and a glossy floor).
Run (system Python 3.12 with Pillow):  python tools/geo/datahall_art.py
Writes  talk/gen/dh_racks.png   2048 x 2048: four rack fronts side by side (each 512 x 2048 = 4.4 x 15 m in the show)
        talk/gen/dh_floor.png   1024 x 256: one bay of the glossy floor, across the aisle (23.2 m) x along it (4.4 m);
                                constant along the aisle apart from the tile joints, so the bays join without a seam
"""
import os, random
from PIL import Image, ImageChops, ImageDraw, ImageFilter

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(REPO, "talk", "gen")
BLUE, CYAN, AMBER, PALE = (60, 130, 255), (60, 215, 255), (255, 170, 44), (215, 228, 255)


def rack(seed):
    rnd = random.Random(seed); W, H = 512, 2048
    base = Image.new("RGB", (W, H), (6, 8, 12)); d = ImageDraw.Draw(base)
    glow = Image.new("RGB", (W, H), (0, 0, 0)); g = ImageDraw.Draw(glow)
    d.rectangle([0, 0, W - 1, H - 1], outline=(30, 35, 47), width=10)                 # the cabinet's frame
    d.rectangle([16, 16, W - 17, H - 17], outline=(15, 18, 25), width=4)
    d.rectangle([10, 10, W - 11, 62], fill=(15, 18, 25)); d.rectangle([10, H - 72, W - 11, H - 11], fill=(15, 18, 25))
    top, bot, U = 82, H - 92, 42; uh = (bot - top) / U
    for u in range(U):                                                                # 42 units, most of them with lamps
        y0 = top + u * uh; k = rnd.randint(0, 5)
        d.rectangle([34, y0 + 3, W - 35, y0 + uh - 3], fill=(10 + k, 13 + k, 19 + k))
        if rnd.random() < 0.1: continue                                               # a blanking plate
        for x in range(48, W - 170, 22): d.rectangle([x, y0 + 9, x + 14, y0 + uh - 10], fill=(15 + k, 19 + k, 27 + k))
        n = rnd.randint(5, 12)
        for i in range(n):
            if rnd.random() < 0.18: continue
            r = rnd.random(); col = BLUE if r < 0.76 else CYAN if r < 0.87 else AMBER if r < 0.96 else PALE
            cx = W - 150 + i * 9.5; cy = y0 + uh / 2 + rnd.choice((-7, 0, 7))
            g.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=col)
    for x in (24, W - 30):                                                            # a blue light strip down each door edge
        g.rectangle([x, 76, x + 5, H - 86], fill=(34, 80, 235))
    d.line([W // 2, 64, W // 2, H - 74], fill=(19, 23, 31), width=4)                  # the door split
    out = ImageChops.add(base, glow.filter(ImageFilter.GaussianBlur(14)))
    out = ImageChops.add(out, glow.filter(ImageFilter.GaussianBlur(4)))
    return ImageChops.add(out, glow)


atlas = Image.new("RGB", (2048, 2048))
for k in range(4): atlas.paste(rack(101 + k), (512 * k, 0))
atlas.save(os.path.join(OUT, "dh_racks.png"))

# the floor: dark, with the racks' blue along both sides and the two ceiling strips as soft streaks (a fake reflection)
W, H = 1024, 256
px = []
for x in range(W):
    u = x / (W - 1); side = min(u, 1 - u) / 0.5                    # 0 at a rack, 1 on the centre line
    blue = max(0.0, 1 - side / 0.42) ** 2.2
    xm = (u - 0.5) * 23.2                                           # metres from the centre line
    strip = sum(2.718281828 ** (-((xm - c) / 0.9) ** 2) for c in (-3.2, 3.2))
    px.append((int(8 + 26 * blue + 62 * strip), int(11 + 52 * blue + 74 * strip), int(17 + 150 * blue + 92 * strip)))
row = Image.new("RGB", (W, 1)); row.putdata(px)
floor = row.resize((W, H), Image.NEAREST); d = ImageDraw.Draw(floor)
dark = Image.new("RGB", (W, H), (0, 0, 0)); dd = ImageDraw.Draw(dark)
for j in range(8): dd.line([0, j * 32, W, j * 32], fill=(7, 8, 10), width=2)          # tile joints: 8 across a bay (0.55 m)
for i in range(1, 40): dd.line([i * W / 40.7, 0, i * W / 40.7, H], fill=(7, 8, 10), width=2)
floor = ImageChops.subtract(floor, dark)
floor.save(os.path.join(OUT, "dh_floor.png"))
print("datahall_art: dh_racks.png 2048x2048, dh_floor.png 1024x256 ->", OUT)
