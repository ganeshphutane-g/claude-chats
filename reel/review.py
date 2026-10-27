"""Render one still per listed global frame at scale 1 and tile them into a review sheet."""
import sys, pathlib
sys.path.insert(0, ".")
import scenes
from reelkit import Renderer
from PIL import Image, ImageDraw
frames = [int(a) for a in sys.argv[2:]]
out = sys.argv[1]
scenes.Ctx.r = Renderer("work", scale=1)
scenes.Ctx.r.page.set_default_timeout(300000)
ims = []
for g in frames:
    p = f"work/rv_{g:05d}.png"
    scenes.Ctx.r.still(scenes.frame(g), p)
    ims.append((g, Image.open(p).convert("RGB")))
scenes.Ctx.r.close()
cols = min(4, len(ims)); tw = 400; th = int(tw * 1920 / 1080)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), "#000")
for i, (g, im) in enumerate(ims):
    t = im.resize((tw, th), Image.LANCZOS); ImageDraw.Draw(t).text((8, 6), str(g), fill="#ffff00")
    sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
sheet.save(out); print("sheet", out)
