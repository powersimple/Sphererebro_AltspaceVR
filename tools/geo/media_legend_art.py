"""The legend for the module "media_capture" (tools/talk/modules/media_capture.py): what the dots' colours mean.
Ben, 2026-11-10: "add a legend on the lower right side for 19 of 606". Warm and small, not white (CLAUDE.md rule 12);
no numbers (the atlas package's counts differ from the slide's). The colours are talk_materials_media.json's.
Run (system Python with Pillow):  python tools/geo/media_legend_art.py      Writes talk/gen/media_legend.png (1024 x 512).
"""
import os
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
W, H = 1024, 512
ROWS = [((242, 51, 36), "dot", "Captured or state-controlled"),
        ((77, 173, 168), "dot", "Independent, but state-funded or managed"),
        ((128, 128, 135), "dot", "Not stated"),
        ((255, 204, 77), "spike", "Independent public media"),
        ((240, 62, 158), "diamond", "AI data centers")]
im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
dr.rounded_rectangle((4, 4, W - 4, H - 4), radius=56, fill=(6, 8, 14, 170), outline=(150, 110, 60, 150), width=3)
font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 46)
while max(dr.textlength(t, font=font) for _, _, t in ROWS) > W - 190: font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", font.size - 2)
step = (H - 80) / len(ROWS)
for k, (col, kind, text) in enumerate(ROWS):
    y = 40 + step * (k + 0.5)
    if kind == "dot": dr.ellipse((70 - 22, y - 22, 70 + 22, y + 22), fill=col + (255,))
    elif kind == "diamond": dr.polygon([(70, y - 26), (70 + 26, y), (70, y + 26), (70 - 26, y)], fill=col + (255,))
    else: dr.polygon([(70, y - 40), (70 + 13, y + 26), (70 - 13, y + 26)], fill=col + (255,))
    dr.text((130, y), text, font=font, fill=(226, 176, 116, 235), anchor="lm")
out = os.path.join(REPO, "talk", "gen", "media_legend.png")
im.save(out); print("wrote", out)
