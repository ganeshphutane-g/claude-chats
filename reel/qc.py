"""Encode and QC the reel: probe, contact sheets, safe overlays, flicker, decode-vs-source diff, cover."""
import pathlib, subprocess, sys
import numpy as np
from PIL import Image
from reelkit import encode, probe, contact_sheet, safe_overlay, flicker, W, H
import scenes

out = pathlib.Path("out"); out.mkdir(exist_ok=True)
fr = pathlib.Path("work/frames")
if "--encode" in sys.argv:
    encode(fr, out / "reel_1080.mp4", drawn_fps=30, delivery_fps=30)
info = probe(out / "reel_1080.mp4")
print("probe", info)
assert (info["width"], info["height"], info["fps"], info["codec"], info["pix_fmt"], info["audio"]) == (1080, 1920, "30/1", "h264", "yuv420p", False), info
assert info["frames"] == scenes.TOTAL, (info["frames"], scenes.TOTAL)
contact_sheet(fr, out / "contact_every10.png", every=10, cols=12, width=160)
for name, a, b in scenes.SHOTS:
    mid = (a + b) // 2 if name != "s1" else 0
    safe_overlay(fr / f"fr_{mid:05d}.png", out / f"safe_{name}.png")
# flicker on a region that should be static (background corner) in shots without camera push
print("flicker s4 bg", round(flicker(fr, (0, 1500, 300, 1900), 380, 420), 3))
print("flicker s7 bg", round(flicker(fr, (0, 1500, 300, 1900), 840, 900), 3))
# decode one mid-film frame from the MP4 and compare with its source PNG
g = 700
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / "reel_1080.mp4"), "-vf", f"select=eq(n\\,{g})", "-vframes", "1", str(out / "dec.png")], check=True)
a = np.asarray(Image.open(out / "dec.png").convert("RGB")).astype(int)
b = np.asarray(Image.open(fr / f"fr_{g:05d}.png").convert("RGB").resize((W, H), Image.LANCZOS)).astype(int)
print("decode diff", round(float(abs(a - b).mean()), 2), "per-channel mean shift", (a.mean((0, 1)) - b.mean((0, 1))).round(2))
Image.open(fr / "fr_00000.png").convert("RGB").resize((W, H), Image.LANCZOS).save(out / "cover.png")
print("QC done")
