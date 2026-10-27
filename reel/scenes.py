"""Reel #1 for @handmadewith.ai - "Your AI ad may not be yours".
Every pixel is SVG written here; rendered with reelkit (headless Chromium + ffmpeg). Silent.
Run:  python3 scenes.py still <frame> [scale] [out.png]
      python3 scenes.py render <start> <stop> [scale]"""
import math, random, sys, pathlib
from reelkit import *

FPS = 30
SKETCHES = 14          # placeholder data approved by the person: make it true before posting

# ------------------------------------------------------------------ style bible ---
WALL_T, WALL_B = "#1a1d23", "#101216"      # graphite sweep, wall
FLOOR_T, FLOOR_B = "#16181d", "#08090c"    # floor near horizon -> bottom
HZ = 1300                                  # wall/floor junction
WHITE, GRAY, GRAY2 = "#f5f5f7", "#a1a1a6", "#6e6e73"
AMB_A, AMB_B = "#ffc46b", "#ff6f3c"        # accent: the human / authorship thread
BLUE = "#7d95ff"                           # cool rim light
TEAL = "#3fd28b"                           # fact-checked
KEY = "#ffe8cc"                            # key light colour (warm soft box, top-left)
SHD = "#07080b"                            # tinted near-black for shadows (never #000)
PAPER = "#f1ece3"
GRAPHITE = "#3b3f46"                       # pencil
FD, FT, MONO = "Inter Display", "Inter", "JetBrains Mono"

SHOTS = [  # (name, first, last) global frames @30fps
    ("s1", 0, 149), ("s2", 150, 257), ("s3", 258, 371), ("s4", 372, 545), ("s5", 546, 683),
    ("s6", 684, 827), ("s7", 828, 935), ("s8", 936, 1019), ("s9", 1020, 1115)]
TOTAL = 1116
XF = 8                                     # dissolve length in frames


# ------------------------------------------------------------------ helpers ---
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def T(x, y, s, size, weight=600, fill=WHITE, fam=FT, anchor="middle", ls=0, op=1.0, raw=False, extra=""):
    body = s if raw else esc(s)
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-weight="{weight}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op:.3f}" {extra}>{body}</text>')


def eo(t, p=3):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** p


def eio(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def appear(f, f0, dur=16, dist=28):
    """Apple-style text entrance: fade + rise with a long ease-out. Returns (opacity, dy)."""
    t = eo((f - f0) / dur)
    return t, (1 - t) * dist


def rrect(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    return (f"M{x + r:.1f},{y:.1f}H{x + w - r:.1f}A{r},{r} 0 0 1 {x + w:.1f},{y + r:.1f}V{y + h - r:.1f}"
            f"A{r},{r} 0 0 1 {x + w - r:.1f},{y + h:.1f}H{x + r:.1f}A{r},{r} 0 0 1 {x:.1f},{y + h - r:.1f}"
            f"V{y + r:.1f}A{r},{r} 0 0 1 {x + r:.1f},{y:.1f}Z")


def poly(pts):
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


def ell(cx, cy, rx, ry, fill, op=1.0, extra=""):
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" opacity="{op:.3f}" {extra}/>'


def glow(cx, cy, r, col, op, gid, blend="screen"):
    return (radial(gid, [(0, col, op), (.35, col, op * .45), (1, col, 0)]) +
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="url(#{gid})" style="mix-blend-mode:{blend}"/>')


SHARED_DEFS = (
    linear("gAmb", [(0, AMB_A, 1), (1, AMB_B, 1)], 0, 0, 1, 0) +
    linear("gAmbV", [(0, AMB_A, 1), (1, AMB_B, 1)], 0, 0, 0, 1) +
    linear("gTeal", [(0, "#6ff0b0", 1), (1, "#22b46b", 1)], 0, 0, 1, 1) +
    '<filter id="dof1" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.2"/></filter>'
    '<filter id="dof4" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter>')


# ------------------------------------------------------------------ studio ---
def studio(seed=1, key=(300, 520), floor_pool=(520, 1480), warmth=1.0):
    """Graphite infinity sweep: wall, soft curved junction, polished floor, key pool, cool rim. Static layer."""
    s = [linear("wall", [(0, WALL_T, 1), (.8, "#121418", 1), (1, "#16181d", 1)]),
         f'<rect width="{W}" height="{HZ}" fill="url(#wall)"/>',
         linear("flr", [(0, "#16181d", 1), (.25, "#0f1114", 1), (1, FLOOR_B, 1)]),
         f'<rect y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#flr)"/>']
    # the sweep: wall curves into the floor; one very wide, very soft band so there is no visible seam
    s.append(f'<ellipse cx="540" cy="{HZ}" rx="1100" ry="170" fill="#262a32" opacity=".7" filter="url(#soft3)"/>')
    s.append(f'<ellipse cx="{key[0]}" cy="{HZ - 10}" rx="620" ry="70" fill="{KEY}" opacity="{.05 * warmth:.3f}" filter="url(#soft3)" style="mix-blend-mode:screen"/>')
    # key light pool on the wall and spill on the floor
    s.append(glow(key[0], key[1], 980, KEY, .16 * warmth, "kp"))
    s.append(f'<ellipse cx="{floor_pool[0]}" cy="{floor_pool[1]}" rx="560" ry="150" fill="{KEY}" opacity="{.08 * warmth:.3f}" '
             f'filter="url(#soft3)" style="mix-blend-mode:screen"/>')
    # cool rim from the right
    s.append(glow(1180, 820, 760, BLUE, .12, "rim"))
    return "".join(s)


def dust(f, seed=7, n=70, box=(60, 300, 760, 1300), drift=.32):
    """Motes floating in the key light (T1). Screen blend at top level."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    out = []
    for i in range(n):
        bx, by = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        ph, sp, rad = rnd.uniform(0, 6.28), rnd.uniform(.6, 1.4), rnd.choice([.9, 1.2, 1.5, 2.0, 2.6, 4.0, 6.0])
        y = y0 + ((by - y0 - f * drift * sp) % (y1 - y0))
        x = bx + 14 * math.sin(f / 50 * sp + ph)
        dist_key = math.hypot(x - 320, y - 640) / 700
        op = max(0, .55 - dist_key * .45) * (.5 + .5 * math.sin(f / 23 + ph))
        if op < .03:
            continue
        flt = ' filter="url(#soft0)"' if rad >= 4 else ""
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}" fill="{KEY}" opacity="{op * (.45 if rad >= 4 else 1):.3f}"{flt}/>')
    return '<g style="mix-blend-mode:screen">' + "".join(out) + '</g>'


# ------------------------------------------------------------------ the AI ad (fictional brand LUMEN) ---
SKIES = [  # top -> horizon
    ["#17224a", "#3b4583", "#b9688d", "#f2a46c", "#ffdca2"],
    ["#0f2a44", "#2c5b80", "#7fa0b8", "#f0c08e", "#fff0c8"],
    ["#26163f", "#5b2f6e", "#c2577a", "#f58f62", "#ffd08a"],
    ["#10233a", "#24506b", "#5f8d97", "#d9b38a", "#fbe3b6"],
    ["#1f1838", "#4a3a78", "#9a6aa0", "#eaa48a", "#ffe0b4"],
    ["#2a1a2e", "#6b3346", "#c45a4a", "#f39a52", "#ffd38c"],
    ["#0d1d33", "#284c76", "#8a7ea6", "#f2b48a", "#ffe6bf"],
    ["#1a2038", "#3d3f6f", "#a2607c", "#ef9b6a", "#ffd9a6"]]


def ad_scene(v=0, ui=True):
    """The polished 'AI ad': amber perfume bottle on a travertine plinth, backlit dunes at golden hour.
    Drawn on the full 1080x1920 canvas; placed scaled into devices and thumbnails. v = variant (S4 outputs)."""
    rnd = random.Random(300 + v)
    sky = SKIES[v % len(SKIES)]
    sunx = [700, 310, 820, 560, 640, 380, 760, 470][v % 8]
    suny = [1090, 1060, 1120, 1000, 1110, 1080, 1040, 1100][v % 8]
    bw, bh, bshape = [(150, 250, 0), (120, 300, 1), (190, 210, 2), (140, 270, 0), (170, 230, 2), (115, 310, 1), (160, 240, 0), (150, 260, 2)][v % 8]
    cap_col = [("#e9cf8f", "#8a6a2c"), ("#2a2b2f", "#0d0e10"), ("#d8dbe0", "#6d717a")][[0, 1, 0, 2, 0, 1, 2, 0][v % 8]]
    cx = [400, 560, 420, 520, 400, 600, 450, 520][v % 8]
    s = []
    stops = [(0, sky[0]), (.28, sky[1]), (.48, sky[2]), (.6, sky[3]), (.66, sky[4])]
    s.append(linear("sky", [(o, c, 1) for o, c in stops]) + f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    # high thin clouds lit from below (wisps)
    for i in range(9):
        y = rnd.uniform(520, 960)
        x = rnd.uniform(-100, W)
        w = rnd.uniform(220, 520)
        col = mix(sky[3], "#ffffff", .25) if y > 760 else mix(sky[2], sky[3], .5)
        s.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{w:.0f}" ry="{rnd.uniform(8, 22):.0f}" fill="{col}" '
                 f'opacity="{rnd.uniform(.25, .55):.2f}" filter="url(#wisp)"/>')
    # sun + atmosphere
    s.append(glow(sunx, suny, 760, "#ffc27a", .55, "sg1") + glow(sunx, suny, 260, "#fff3d6", .9, "sg2"))
    s.append(f'<circle cx="{sunx}" cy="{suny}" r="70" fill="#fff8e6"/>')

    def ridge(base, amp, n, phase, seed2):
        r2 = random.Random(seed2)
        pts = [(-60, base + 40)]
        for k in range(n + 1):
            x = -60 + k * (W + 120) / n
            pts.append((x, base - amp * (0.55 + 0.45 * math.sin(k * 1.3 + phase)) - r2.uniform(0, amp * .3)))
        return pts
    # three dune ridges, backlit: crest rim light, shadowed faces, aerial perspective
    ridges = [(1185, 55, 7, .4, 0.85), (1300, 80, 6, 1.9, 0.55), (1500, 120, 5, 3.1, 0.2)]
    sand = "#b8714a"
    for i, (base, amp, n, ph, depth) in enumerate(ridges):
        pts = ridge(base, amp, n, ph, 40 + i + v * 3)
        top = catmull(pts[1:])
        d = top + f"L{W + 60},{H}L-60,{H}Z"
        c_top = aerial(tint(sand, .25, "#ffcf9a"), depth, sky[3])
        c_bot = aerial(shade(sand, .55, "#2a1630"), depth, sky[2])
        s.append(linear(f"dn{i}", [(0, c_top, 1), (.35, mix(c_top, c_bot, .6), 1), (1, c_bot, 1)]) +
                 f'<path d="{d}" fill="url(#dn{i})"/>')
        # rim light along the crest (backlit by the sun), stronger near the sun
        s.append(f'<path d="{top}" fill="none" stroke="{tint(sky[4], .3, "#ffffff")}" stroke-width="{3 + 3 * (1 - depth):.1f}" '
                 f'opacity="{.5 + .3 * (1 - depth):.2f}" filter="url(#soft0)" style="mix-blend-mode:screen"/>')
        s.append(f'<path d="{top}" fill="none" stroke="#fff4dc" stroke-width="1.6" opacity="{.35 + .4 * (1 - depth):.2f}"/>')
        if i < 2:
            s.append(veil(f"dv{i}", base - 60, base + 260, sky[3], 0, .25))
    # wind ripples on the near dune (fine texture, follows the slope)
    rip = []
    for k in range(80):
        y = rnd.uniform(1480, 1900)
        x = rnd.uniform(-40, W)
        L = rnd.uniform(60, 180)
        bend = rnd.uniform(-8, 8)
        rip.append(f'<path d="M{x:.0f},{y:.0f}q{L / 2:.0f},{bend - 6:.0f} {L:.0f},{bend:.0f}" stroke="{tint(sand, .3, "#ffd3a6")}" '
                   f'stroke-width="{rnd.uniform(1.2, 2.6):.1f}" fill="none" opacity="{rnd.uniform(.12, .3):.2f}" stroke-linecap="round"/>')
    s.append('<g filter="url(#rough)">' + "".join(rip) + '</g>')

    # travertine plinth
    px, ptop, prx, pry, ph_ = cx, 1395, 175, 38, 245
    stone = "#d9c7ae"
    body = f"M{px - prx},{ptop}V{ptop + ph_}A{prx},{pry} 0 0 0 {px + prx},{ptop + ph_}V{ptop}Z"
    s.append(f'<ellipse cx="{px}" cy="{ptop + ph_ + 6}" rx="{prx + 50}" ry="{pry + 14}" fill="#2a1424" opacity=".55" filter="url(#soft)"/>')
    s.append(linear("pl", [(0, shade(stone, .55, "#3a2a48"), 1), (.55, shade(stone, .3, "#5a3f55"), 1), (.86, tint(stone, .05, "#ffd2a0"), 1),
                           (1, tint(stone, .5, "#ffe2b8"), 1)], 0, 0, 1, 0) + f'<path d="{body}" fill="url(#pl)"/>')
    # travertine veins: horizontal, broken (small texture scale)
    vein = []
    for k in range(110):
        y = rnd.uniform(ptop + 12, ptop + ph_ + 20)
        x = rnd.uniform(px - prx + 6, px + prx - 10)
        L = rnd.uniform(6, 34)
        vein.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{L:.0f}" height="{rnd.uniform(1.4, 3.2):.1f}" rx="1.5" fill="#5b4652" opacity="{rnd.uniform(.12, .3):.2f}"/>')
    s.append(f'<clipPath id="plc"><path d="{body}"/></clipPath><g clip-path="url(#plc)" filter="url(#rough)">' + "".join(vein) + '</g>')
    s.append(f'<ellipse cx="{px}" cy="{ptop}" rx="{prx}" ry="{pry}" fill="{tint(stone, .2, "#ffe0bb")}"/>')
    s.append(f'<ellipse cx="{px}" cy="{ptop}" rx="{prx}" ry="{pry}" fill="none" stroke="#fff1da" stroke-width="2" opacity=".6"/>')
    s.append(f'<path d="M{px + prx - 4},{ptop + 4}V{ptop + ph_}" stroke="#ffe9c8" stroke-width="5" opacity=".55" filter="url(#soft0)"/>')

    # amber glass bottle
    by1 = ptop + 2
    by0 = by1 - bh
    bx0 = px - bw / 2
    rad = [28, 18, 70][bshape]
    neck_w, neck_h = bw * .34, 34
    cap_w, cap_h = bw * .5, [86, 110, 64][bshape]
    # shadow + caustic on the plinth top (sun behind-right -> shadow toward viewer-left)
    s.append(f'<clipPath id="ptc"><ellipse cx="{px}" cy="{ptop}" rx="{prx}" ry="{pry}"/></clipPath><g clip-path="url(#ptc)">'
             f'<ellipse cx="{px - bw * .55}" cy="{ptop + 14}" rx="{bw * .95}" ry="22" fill="#4a2410" opacity=".45" filter="url(#soft0)"/>'
             f'<ellipse cx="{px - bw * .45}" cy="{ptop + 16}" rx="{bw * .42}" ry="10" fill="#ffb347" opacity=".75" filter="url(#soft0)" style="mix-blend-mode:screen"/></g>')
    bd = rrect(bx0, by0, bw, bh, rad)
    s.append(linear("gl", [(0, "#4d1f06", 1), (.18, "#9a4a12", 1), (.5, "#e08a2c", 1), (.78, "#b85d16", 1), (1, "#ffcf7a", 1)], 0, 0, 1, 0) +
             f'<path d="{bd}" fill="url(#gl)"/>')
    # liquid line and inner glow (backlight passing through)
    s.append(f'<clipPath id="blc"><path d="{bd}"/></clipPath><g clip-path="url(#blc)">'
             f'<rect x="{bx0}" y="{by0 + bh * .16}" width="{bw}" height="4" fill="#ffd89a" opacity=".55"/>'
             f'<ellipse cx="{px + bw * .18}" cy="{by1 - bh * .25}" rx="{bw * .35}" ry="{bh * .3}" fill="#ffd27a" opacity=".55" filter="url(#soft)"/>'
             f'<rect x="{bx0 + bw * .14}" y="{by0 + 10}" width="{bw * .07}" height="{bh - 26}" rx="6" fill="#fff6e6" opacity=".55" filter="url(#soft0)"/>'
             f'<rect x="{bx0 + bw * .16}" y="{by0 + 18}" width="{bw * .025}" height="{bh * .55}" rx="3" fill="#ffffff" opacity=".75"/>'
             f'<rect x="{bx0 + bw - 9}" y="{by0 + 6}" width="7" height="{bh - 12}" fill="#fff0c8" opacity=".85" filter="url(#soft0)"/>'
             '</g>')
    # label
    lw, lh = bw * .62, bh * .26
    s.append(f'<rect x="{px - lw / 2:.1f}" y="{by0 + bh * .44:.1f}" width="{lw:.1f}" height="{lh:.1f}" rx="3" fill="#f3e6cf" opacity=".93"/>')
    s.append(T(px, by0 + bh * .44 + lh * .58, "LUMEN", lh * .32, 300, "#5a3a1c", FT, ls=lh * .06))
    # neck + brushed cap
    s.append(f'<rect x="{px - neck_w / 2:.1f}" y="{by0 - neck_h:.1f}" width="{neck_w:.1f}" height="{neck_h + 4}" fill="#8a4512"/>')
    s.append(linear("cap", [(0, cap_col[1], 1), (.3, cap_col[0], 1), (.55, tint(cap_col[0], .5), 1), (.8, cap_col[0], 1), (1, cap_col[1], 1)], 0, 0, 1, 0) +
             f'<rect x="{px - cap_w / 2:.1f}" y="{by0 - neck_h - cap_h:.1f}" width="{cap_w:.1f}" height="{cap_h:.1f}" rx="4" fill="url(#cap)"/>')
    brush = "".join(f'<rect x="{px - cap_w / 2 + k * cap_w / 26:.1f}" y="{by0 - neck_h - cap_h + 2:.1f}" width="1.2" height="{cap_h - 4:.1f}" '
                    f'fill="{"#ffffff" if k % 3 else "#000000"}" opacity=".08"/>' for k in range(26))
    s.append(brush)
    s.append(f'<rect x="{px - cap_w / 2:.1f}" y="{by0 - neck_h - cap_h:.1f}" width="{cap_w:.1f}" height="5" fill="#fff7e0" opacity=".55"/>')
    # bottle rim light (sun behind right)
    s.append(f'<path d="{bd}" fill="none" stroke="#ffe7b0" stroke-width="2" opacity=".5"/>')
    # lens flare streak across the sun
    s.append(f'<rect x="{sunx - 420}" y="{suny - 2}" width="840" height="4" fill="#fff2d2" opacity=".35" filter="url(#soft0)" style="mix-blend-mode:screen"/>')
    s.append(grade("#1b1640", "#ffe1bd", .1))
    if ui:   # ad typography + platform chrome
        s.append(T(540, 380, "LUMEN", 158, 200, "#fffaf2", FD, ls=34, op=.96))
        s.append(T(540, 450, "EAU DE PARFUM  ·  N°7", 30, 500, "#fff3e2", FT, ls=9, op=.8))
        s.append(f'<circle cx="104" cy="148" r="30" fill="#f3e6cf" opacity=".9"/>' + T(104, 158, "L", 30, 600, "#5a3a1c", FT))
        s.append(T(152, 140, "lumen.parfum", 30, 600, "#ffffff", FT, anchor="start", op=.92) +
                 T(152, 176, "Sponsored", 25, 400, "#ffffff", FT, anchor="start", op=.7))
        s.append(f'<rect x="370" y="1712" width="340" height="96" rx="48" fill="#fffaf2" opacity=".94"/>' +
                 T(540, 1772, "Shop now", 34, 600, "#2a1a10", FT))
    return "".join(s)


# ------------------------------------------------------------------ objects ---
def device(cx, cy, w, h, img, uid, rot=0.0, scale=1.0):
    """Floating glass-and-aluminium device. img = <image> tag of a full-canvas layer, scaled into the screen."""
    x0, y0 = cx - w / 2, cy - h / 2
    R = w * .14
    s = [f'<g transform="rotate({rot:.2f} {cx:.1f} {cy:.1f})">']
    # ambient occlusion halo on the wall behind (offset down-right, away from the key)
    s.append(f'<path d="{rrect(x0 + 16, y0 + 34, w + 6, h + 6, R)}" fill="{SHD}" opacity=".7" filter="url(#soft2)"/>')
    # aluminium frame
    s.append(linear(f"{uid}al", [(0, "#c9ccd3", 1), (.22, "#5b5f68", 1), (.5, "#2b2e34", 1), (.78, "#4a4e56", 1), (1, "#8f939c", 1)], 0, 0, 1, 1) +
             f'<path d="{rrect(x0 - 9, y0 - 9, w + 18, h + 18, R + 9)}" fill="url(#{uid}al)"/>')
    s.append(f'<path d="{rrect(x0 - 3, y0 - 3, w + 6, h + 6, R + 3)}" fill="#0a0b0e"/>')
    # screen
    k = w / W
    s.append(f'<clipPath id="{uid}sc"><path d="{rrect(x0, y0, w, h, R * .86)}"/></clipPath>'
             f'<g clip-path="url(#{uid}sc)"><g transform="translate({x0:.1f},{y0:.1f}) scale({k:.5f})">{img}</g>'
             # glass: diagonal gloss + top-edge sheen
             + linear(f"{uid}gl", [(0, "#ffffff", .16), (.42, "#ffffff", .03), (.43, "#ffffff", 0), (1, "#ffffff", 0)], 0, 0, 1, 1) +
             f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#{uid}gl)"/></g>')
    # frame highlights: key from top-left, cool rim right
    s.append(f'<path d="{rrect(x0 - 9, y0 - 9, w + 18, h + 18, R + 9)}" fill="none" stroke="#fff3e3" stroke-width="1.6" opacity=".55"/>')
    s.append(linear(f"{uid}rm", [(0, BLUE, 0), (.7, BLUE, 0), (1, BLUE, .9)], 0, 0, 1, 0) +
             f'<path d="{rrect(x0 - 8, y0 - 8, w + 16, h + 16, R + 8)}" fill="none" stroke="url(#{uid}rm)" stroke-width="3"/>')
    s.append('</g>')
    return "".join(s)


def reflection(body, axis_y, gap=40, k=.5, op=.11, uid="rf"):
    """Polished-floor reflection: the body mirrored about axis_y, squashed, faded, softened."""
    return (linear(f"{uid}m", [(0, "#ffffff", 1), (1, "#ffffff", 0)]) +
            f'<mask id="{uid}k" maskUnits="userSpaceOnUse" x="0" y="{axis_y}" width="{W}" height="{H - axis_y}">'
            f'<rect x="0" y="{axis_y + gap}" width="{W}" height="{(H - axis_y) * .38:.0f}" fill="url(#{uid}m)"/></mask>'
            f'<g mask="url(#{uid}k)" opacity="{op}"><g filter="url(#defocus)" transform="translate(0,{axis_y * 2 + gap:.1f}) scale(1,-1)">'
            f'<g transform="translate(0,{axis_y * (1 - k):.1f}) scale(1,{k})">{body}</g></g></g>')


def _sector(r0, r1, a0, a1, jag0=None, jag1=None, n=10):
    """Annulus sector polygon (angles in degrees). jag = mid-cut offsets so breaks look like real fractures."""
    pts = [(r1 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), r1 * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    if jag1:
        rm = (r0 + r1) / 2
        pts.append((rm * math.cos(math.radians(a1 + jag1)), rm * math.sin(math.radians(a1 + jag1))))
    pts += [(r0 * math.cos(math.radians(a1 - (a1 - a0) * i / n)), r0 * math.sin(math.radians(a1 - (a1 - a0) * i / n))) for i in range(n + 1)]
    if jag0:
        rm = (r0 + r1) / 2
        pts.append((rm * math.cos(math.radians(a0 + jag0)), rm * math.sin(math.radians(a0 + jag0))))
    return pts


def _medal_shards(R):
    cuts = [-95, -38, 8, 61, 104, 151, 203, 248]
    jag = [7, -6, 9, -8, 6, -9, 8, -7]
    shards = []
    for i in range(len(cuts)):
        a0, a1 = cuts[i], cuts[(i + 1) % len(cuts)] + (360 if i == len(cuts) - 1 else 0)
        shards.append(_sector(R * .72, R, a0, a1, jag[i], jag[(i + 1) % len(jag)]))
    ccuts = [40, 120, 205, 320]
    for i in range(len(ccuts) - 1):
        shards.append(_sector(R * .25, R * .5, ccuts[i], ccuts[i + 1], 6 if i else None, -6 if i < 2 else None))
    return shards


def medal(cx, cy, R, uid, crack=0.0, burst=0.0, tilt=0.0):
    """Chrome copyright medallion. crack 0..1 draws fracture lines, burst 0..1 throws the shards apart."""
    shards = _medal_shards(R)
    rnd = random.Random(11)
    s = [linear(f"{uid}ch", [(0, "#fbfbfd", 1), (.16, "#c6c9d0", 1), (.32, "#666a73", 1), (.47, "#eef0f3", 1), (.6, "#8b9099", 1),
                             (.78, "#2c2f35", 1), (1, "#b7bbc4", 1)], 0, 0, .8, 1),
         linear(f"{uid}ed", [(0, "#4b4f57", 1), (1, "#17191d", 1)], 0, 0, 0, 1)]
    # warm alarm glow behind as it breaks
    if burst > 0:
        s.append(glow(cx + R * .4, cy + R * .3, R * 2.2, AMB_B, .22 * eo(burst * 3) * (1 - burst * .6), f"{uid}gw"))
    groups = []
    for i, pts in enumerate(shards):
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        d = math.hypot(mx, my) or 1
        sp = rnd.uniform(.7, 1.3)
        dx = (mx / d * R * 1.3 * sp + R * .7) * eo(burst, 2)
        dy = max(my / d * R * 1.1 * sp, -R * .12) * eo(burst, 2) + R * .9 * burst ** 2
        rot = rnd.uniform(-40, 40) * eo(burst, 2)
        p_local = [(px, py) for px, py in pts]
        dd = poly([(cx + px, cy + py) for px, py in p_local])
        tr = f'translate({dx:.1f},{dy:.1f}) rotate({rot:.1f} {cx + mx:.1f} {cy + my:.1f})'
        # shadow, extruded edge, chrome face, bevel
        groups.append(f'<g transform="{tr}">'
                      f'<path d="{dd}" fill="{SHD}" opacity=".55" transform="translate(10,16)" filter="url(#soft0)"/>'
                      f'<path d="{dd}" fill="url(#{uid}ed)" transform="translate(3,4)"/>'
                      f'<path d="{dd}" fill="url(#{uid}ch)"/>'
                      f'<path d="{dd}" fill="none" stroke="#ffffff" stroke-width="1.4" opacity=".55"/></g>')
    s.append(f'<g>{"".join(groups)}</g>')
    # specular glint on the intact medal
    if burst == 0:
        s.append(f'<ellipse cx="{cx - R * .45:.1f}" cy="{cy - R * .62:.1f}" rx="{R * .22:.1f}" ry="{R * .06:.1f}" fill="#ffffff" opacity=".8" '
                 f'transform="rotate(-35 {cx - R * .45:.1f} {cy - R * .62:.1f})" filter="url(#soft0)"/>')
    if crack > 0 and burst == 0:   # bright fracture lines along the cuts
        lines = []
        for a, j in zip([-95, -38, 8, 61, 104, 151, 203, 248], [7, -6, 9, -8, 6, -9, 8, -7]):
            p1 = (cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a)))
            pm = (cx + R * .86 * math.cos(math.radians(a + j)), cy + R * .86 * math.sin(math.radians(a + j)))
            p0 = (cx + R * .72 * math.cos(math.radians(a)), cy + R * .72 * math.sin(math.radians(a)))
            lines.append(f'<path d="M{p1[0]:.1f},{p1[1]:.1f}L{pm[0]:.1f},{pm[1]:.1f}L{p0[0]:.1f},{p0[1]:.1f}" />')
        s.append(f'<g fill="none" stroke="#fff2e0" stroke-width="2.2" stroke-linejoin="round" opacity="{crack:.2f}">{"".join(lines)}</g>'
                 f'<g fill="none" stroke="{AMB_B}" stroke-width="7" opacity="{crack * .6:.2f}" filter="url(#soft0)" style="mix-blend-mode:screen">{"".join(lines)}</g>')
    return "".join(s)


# ------------------------------------------------------------------ shots ---
class Ctx:
    r = None
    L = {}


def lay(name, body):
    if name not in Ctx.L:
        Ctx.L[name] = Ctx.r.layer(name, body)
    return Ctx.L[name]


def push(body, f, n, focus=(540, 930), amount=.03):
    k = 1 + amount * eio(f / max(1, n))
    return (f'<g transform="translate({focus[0]:.1f},{focus[1]:.1f}) scale({k:.5f}) translate({-focus[0]:.1f},{-focus[1]:.1f})">'
            f'{body}</g>')


def shot1(f, n):
    bg = lay("studio1", studio(1))
    ad = lay("ad0", ad_scene(0))
    dcx, dcy, dw, dh = 520, 958, 336, 597
    dev = device(dcx, dcy, dw, dh, ad, "d1", rot=-3)
    crack = eo((f - 34) / 12) if f >= 34 else 0
    burst = eo((f - 52) / 80, 2) if f >= 52 else 0
    md = medal(716, 700, 90, "m1", crack=crack if burst == 0 else 0, burst=burst)
    scene = bg + reflection(dev, HZ - 20, uid="r1") + dev + md
    scene = push(scene, f, n, focus=(560, 900))
    txt = (T(540, 338, "NOBODY TELLS YOU THIS", 28, 600, "url(#gAmb)", FT, ls=5) +
           T(540, 446, "Your AI ad", 100, 700, WHITE, FD, ls=-2) +
           T(540, 552, "may not be yours.", 100, 700, WHITE, FD, ls=-2))
    return scene + dust(f, 7), txt


def backout(t, c1=1.70158):
    t = max(0.0, min(1.0, t))
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def sparkle(cx, cy, r, fill):
    d = (f"M{cx},{cy - r}Q{cx + r * .12},{cy - r * .12} {cx + r},{cy}Q{cx + r * .12},{cy + r * .12} {cx},{cy + r}"
         f"Q{cx - r * .12},{cy + r * .12} {cx - r},{cy}Q{cx - r * .12},{cy - r * .12} {cx},{cy - r}Z")
    return f'<path d="{d}" fill="{fill}"/>'


def thumb(img, x, y, s, uid, crop=(0, 820, 1080), h=None, rx=None):
    """Crop a square (or s x h) window (x0, y0, width) of a full-canvas layer into a rounded tile."""
    h = h or s
    cx0, cy0, size = crop
    k = s / size
    rx = s * .08 if rx is None else rx
    return (f'<clipPath id="{uid}"><rect x="{x:.1f}" y="{y:.1f}" width="{s:.1f}" height="{h:.1f}" rx="{rx:.1f}"/></clipPath>'
            f'<g clip-path="url(#{uid})"><g transform="translate({x - cx0 * k:.2f},{y - cy0 * k:.2f}) scale({k:.5f})">{img}</g></g>')


def glass_card(x, y, w, h, uid, rx=34, fill="#1d2027", op=.78):
    """Frosted dark glass panel: contact + cast shadow, body, top sheen, hairline edge lit from top-left."""
    return (f'<rect x="{x + 10}" y="{y + 26}" width="{w}" height="{h}" rx="{rx}" fill="{SHD}" opacity=".6" filter="url(#soft2)"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" opacity="{op}"/>'
            + linear(f"{uid}sh", [(0, "#ffffff", .10), (.35, "#ffffff", .02), (1, "#ffffff", 0)], 0, 0, .6, 1) +
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#{uid}sh)"/>'
            + linear(f"{uid}ed", [(0, "#ffffff", .38), (.5, "#ffffff", .08), (1, "#ffffff", .16)], 0, 0, 1, 1) +
            f'<rect x="{x + .7}" y="{y + .7}" width="{w - 1.4}" height="{h - 1.4}" rx="{rx}" fill="none" stroke="url(#{uid}ed)" stroke-width="1.4"/>')


# ------------------------------------------------------------------ shot 2: the copies ---
def tag_icon(kind, x, y, s=1.0):
    st = f'fill="none" stroke="{WHITE}" stroke-width="{2.6 * s:.1f}" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "Saved":
        d = f"M{x + 1},{y - 11 * s}h{14 * s}v{22 * s}l{-7 * s},{-6 * s}l{-7 * s},{6 * s}z"
    elif kind == "Reposted":
        d = (f"M{x},{y + 3 * s}v{-4 * s}a{4 * s},{4 * s} 0 0 1 {4 * s},{-4 * s}h{11 * s}m{-4 * s},{-4 * s}l{4 * s},{4 * s}l{-4 * s},{4 * s}"
             f"M{x + 19 * s},{y - 3 * s}v{4 * s}a{4 * s},{4 * s} 0 0 1 {-4 * s},{4 * s}h{-11 * s}m{4 * s},{4 * s}l{-4 * s},{-4 * s}l{4 * s},{-4 * s}")
    elif kind == "Downloaded":
        d = f"M{x + 9 * s},{y - 12 * s}v{15 * s}m{-6 * s},{-6 * s}l{6 * s},{6 * s}l{6 * s},{-6 * s}M{x},{y + 5 * s}v{6 * s}h{18 * s}v{-6 * s}"
    else:
        d = (rrect(x + 5 * s, y - 6 * s, 14 * s, 17 * s, 3 * s) +
             f"M{x + 1 * s},{y + 7 * s}V{y - 9 * s}a{2 * s},{2 * s} 0 0 1 {2 * s},{-2 * s}H{x + 14 * s}")
    return f'<path d="{d}" {st}/>'


def pill(x, y, label, kind, t, uid, icon=None):
    if t <= 0:
        return ""
    w, h = 70 + len(label) * 13.6, 54
    sc = .55 + .45 * backout(t)
    cx, cy = x + w / 2, y + h / 2
    return (f'<g opacity="{min(1, t * 1.8):.3f}" transform="translate({cx:.1f},{cy:.1f}) scale({sc:.4f}) translate({-cx:.1f},{-cy:.1f})">'
            f'<rect x="{x + 4}" y="{y + 12}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="{SHD}" opacity=".55" filter="url(#soft0)"/>'
            f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="#1f222a" opacity=".86"/>'
            f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="none" stroke="#ffffff" stroke-opacity=".24" stroke-width="1.4"/>'
            + (icon(x + 30, y + h / 2) if icon else tag_icon(kind, x + 20, y + h / 2, .95)) + T(x + 52, y + h / 2 + 8.5, label, 24, 600, WHITE, FT, anchor="start") + '</g>')


def shot2(f, n):
    bg = lay("studio2", studio(2, key=(520, 560)))
    ad = lay("ad0", ad_scene(0))
    cen = (540, 960)
    P = eo(f / n, 2)
    copies = [(150, 690, 150, -8, 1.0, "Saved", 30), (930, 700, 150, 7, 1.0, "Copied", 40),
              (300, 1250, 136, -4, 1.0, None, 0), (790, 1246, 140, 5, 1.0, None, 0),
              (186, 990, 214, -6, .5, "Reposted", 12), (894, 985, 214, 6, .5, "Downloaded", 22)]
    s, tags = [bg], []
    for i, (cx, cy, w, rot, depth, tag, tf) in enumerate(copies):
        x = cx + (cx - cen[0]) * .07 * P
        y = cy + (cy - cen[1]) * .05 * P + 6 * math.sin((f + i * 17) / 26)
        h = w * 16 / 9
        dev = device(x, y, w, h, ad, f"s2c{i}", rot=rot + 1.5 * math.sin((f + i * 9) / 40))
        s.append(f'<g filter="url(#{"dof4" if depth >= 1 else "dof1"})" opacity="{.6 if depth >= 1 else .88}">{dev}</g>')
        if tag:
            pw = 70 + len(tag) * 13.6
            tx = x - w / 2 - 26 if cx < 540 else x + w / 2 + 26 - pw
            tags.append(pill(max(72, min(1008 - pw, tx)), y + h * .12, tag, tag, (f - tf) / 12, f"s2p{i}"))
    s.append(device(540, 962 - 6 * P, 330, 330 * 16 / 9, ad, "s2o", rot=-2 + 2 * P))
    scene = push("".join(s), f, n, focus=(540, 950), amount=.02) + "".join(tags)
    o1, d1 = appear(f, 2)
    o2, d2 = appear(f, 10)
    txt = (T(540, 446 + d1, "Anyone can reuse it.", 94, 700, WHITE, FD, ls=-2, op=o1) +
           T(540, 516 + d2, "Copyright won't stop them.", 40, 500, GRAY, FT, op=o2))
    return scene + dust(f, 8, 50), txt


# ------------------------------------------------------------------ shot 3: the report, flat lay ---
def desk_layer(seed=3):
    rnd = random.Random(seed)
    s = [linear("dk", [(0, "#26292e", 1), (1, "#121417", 1)], 0, 0, .3, 1), f'<rect width="{W}" height="{H}" fill="url(#dk)"/>']
    s.append(brush_layer(paint((-150, -150, W + 150, H + 150), 160, ValueMap(.5, grad=(0, .7, H, .25)),
                               ["#121417", "#1c1e22", "#272a30", "#30333a"], (100, 220), rnd, angle=(25, 35), length=(1.4, 2.6),
                               opacity=(.18, .4), noise=.25), "wash"))
    sp = []
    for i in range(2800):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        sp.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice([.6, .8, 1.0, 1.3, 1.8])}" '
                  f'fill="{rnd.choice(["#43464e", "#0b0c0e", "#555962", "#2b2d33"])}" opacity="{rnd.uniform(.2, .65):.2f}"/>')
    s.append("".join(sp))
    s.append(glow(420, 820, 1050, KEY, .16, "dkp"))
    for k in range(6):   # window-blind light across the desk
        x0 = -420 + k * 200
        s.append(f'<path d="{poly([(x0, -100), (x0 + 80, -100), (x0 + 80 + 980, H + 100), (x0 + 980, H + 100)])}" fill="{KEY}" '
                 f'opacity=".055" filter="url(#soft2)" style="mix-blend-mode:screen"/>')
    return "".join(s)


def paper(x, y, w, h, uid, seed=1, col=PAPER, stack=0):
    rnd = random.Random(seed)
    s = [f'<rect x="{x + 16}" y="{y + 26}" width="{w}" height="{h}" fill="{SHD}" opacity=".62" filter="url(#soft2)"/>',
         f'<rect x="{x + 3}" y="{y + 5}" width="{w}" height="{h}" fill="{SHD}" opacity=".5" filter="url(#soft0)"/>']
    for k in range(stack, 0, -1):
        s.append(f'<rect x="{x + k * 2.4:.1f}" y="{y + k * 3:.1f}" width="{w}" height="{h}" fill="{shade(col, .1 + k * .04, "#4a4038")}"/>')
    s.append(linear(f"{uid}pg", [(0, tint(col, .3, "#fff9ef"), 1), (.6, col, 1), (1, shade(col, .12, "#6a5a4a"), 1)], 0, 0, 1, 1) +
             f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{uid}pg)"/>')
    fib = []
    for i in range(int(w * h / 700)):
        fx, fy = rnd.uniform(x + 2, x + w - 2), rnd.uniform(y + 2, y + h - 2)
        a, L = rnd.uniform(0, 6.28), rnd.uniform(2, 8)
        fib.append(f'<path d="M{fx:.1f},{fy:.1f}l{L * math.cos(a):.1f},{L * math.sin(a):.1f}" stroke="#8a7a66" stroke-width=".7" '
                   f'opacity="{rnd.uniform(.06, .18):.2f}"/>')
    s.append("".join(fib))
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#ffffff" stroke-opacity=".55" stroke-width="1"/>')
    return "".join(s)


def report(cx, cy, rot=-4):
    w, h = 480, 640
    x, y = cx - w / 2, cy - h / 2
    ink = "#23262c"
    rnd = random.Random(21)
    s = [f'<g transform="rotate({rot} {cx} {cy})">', paper(x, y, w, h, "rp", 5, "#efebe4", stack=4),
         T(x + 46, y + 74, "U.S. COPYRIGHT OFFICE", 15, 700, ink, FT, anchor="start", ls=3),
         f'<rect x="{x + 46}" y="{y + 94}" width="{w - 92}" height="1.6" fill="{ink}" opacity=".55"/>',
         T(x + 46, y + 166, "Copyright and", 34, 600, ink, FD, anchor="start", ls=-.4),
         T(x + 46, y + 208, "Artificial Intelligence", 34, 600, ink, FD, anchor="start", ls=-.4),
         T(x + 46, y + 256, "Part 2: Copyrightability", 24, 500, "#5b6068", FT, anchor="start")]
    yy = y + 320
    for para in (5, 6, 4):    # faux body copy, set as fine grey rules
        for k in range(para):
            ln = (w - 92) * (rnd.uniform(.55, .8) if k == para - 1 else rnd.uniform(.9, 1))
            s.append(f'<rect x="{x + 46}" y="{yy:.0f}" width="{ln:.0f}" height="5" rx="2.5" fill="#9a9ea6" opacity=".55"/>')
            yy += 15
        yy += 14
    s.append(T(x + 46, y + h - 46, "January 2025", 18, 600, ink, FT, anchor="start", ls=.4))
    s.append(f'<rect x="{x + w - 110}" y="{y + h - 62}" width="64" height="20" rx="3" fill="none" stroke="{ink}" stroke-opacity=".35"/>')
    s.append('</g>')
    return "".join(s)


def pen(cx, cy, L=470, ang=74):
    w = 26
    x0 = cx - L / 2
    body = (f'<rect x="{x0:.1f}" y="{cy - w / 2:.1f}" width="{L - 70}" height="{w}" rx="{w / 2}"/>'
            f'<path d="M{x0 + L - 74:.1f},{cy - w / 2:.1f}L{x0 + L - 8:.1f},{cy - 3:.1f}L{x0 + L - 8:.1f},{cy + 3:.1f}L{x0 + L - 74:.1f},{cy + w / 2:.1f}Z"/>')
    return (f'<g transform="translate(16,24) rotate({ang} {cx} {cy})" fill="{SHD}" opacity=".6" filter="url(#soft)">{body}</g>'
            f'<g transform="rotate({ang} {cx} {cy})">'
            + linear("penb", [(0, "#14151a", 1), (.22, "#5c6069", 1), (.34, "#d0d3d9", 1), (.46, "#454950", 1), (.8, "#1f2126", 1), (1, "#0f1013", 1)]) +
            f'<rect x="{x0:.1f}" y="{cy - w / 2:.1f}" width="{L - 70}" height="{w}" rx="{w / 2}" fill="url(#penb)"/>'
            + linear("pent", [(0, "#3b3e44", 1), (.3, "#b9bdc4", 1), (.5, "#6f737b", 1), (1, "#2a2c31", 1)]) +
            f'<path d="M{x0 + L - 74:.1f},{cy - w / 2:.1f}L{x0 + L - 8:.1f},{cy - 3:.1f}L{x0 + L - 8:.1f},{cy + 3:.1f}L{x0 + L - 74:.1f},{cy + w / 2:.1f}Z" fill="url(#pent)"/>'
            f'<circle cx="{x0 + L - 6:.1f}" cy="{cy}" r="2.6" fill="#0d0e10"/>'
            f'<rect x="{x0 + L * .34:.1f}" y="{cy - w / 2:.1f}" width="3" height="{w}" fill="#0c0d10" opacity=".7"/>'
            f'<rect x="{x0 + 30:.1f}" y="{cy - w / 2 - 5:.1f}" width="{L * .26:.1f}" height="9" rx="4.5" fill="url(#pent)"/>'
            f'<rect x="{x0 + 8}" y="{cy - w / 2 + 6:.1f}" width="{L - 90}" height="2" rx="1" fill="#ffffff" opacity=".35"/></g>')


def cup(cx, cy, uid="cp"):
    rnd = random.Random(9)
    s = [ell(cx + 24, cy + 34, 178, 178, SHD, .62, 'filter="url(#soft2)"'),
         radial(f"{uid}sa", [(0, "#f6f3ee", 1), (.7, "#e4dfd7", 1), (.9, "#cdc6bb", 1), (1, "#b3ab9f", 1)], cx=.42, cy=.4, r=.62) +
         f'<circle cx="{cx}" cy="{cy}" r="165" fill="url(#{uid}sa)"/>',
         f'<circle cx="{cx}" cy="{cy}" r="122" fill="none" stroke="#b9b1a4" stroke-width="3" opacity=".55"/>',
         f'<circle cx="{cx}" cy="{cy}" r="163" fill="none" stroke="#ffffff" stroke-width="2" opacity=".6"/>']
    # spoon resting on the saucer
    s.append(f'<g transform="rotate(-128 {cx} {cy})">'
             + linear(f"{uid}sp", [(0, "#8d9198", 1), (.4, "#f1f2f4", 1), (1, "#6e727a", 1)]) +
             f'<rect x="{cx + 40}" y="{cy - 5}" width="110" height="10" rx="5" fill="url(#{uid}sp)"/>'
             f'<ellipse cx="{cx + 160}" cy="{cy}" rx="24" ry="15" fill="url(#{uid}sp)"/></g>')
    s.append(f'<g transform="rotate(38 {cx} {cy})"><rect x="{cx + 96}" y="{cy - 18}" width="74" height="36" rx="18" fill="#ebe6de"/>'
             f'<rect x="{cx + 112}" y="{cy - 7}" width="42" height="14" rx="7" fill="#c3bcb0"/></g>')
    s.append(ell(cx + 8, cy + 12, 110, 110, SHD, .45, 'filter="url(#soft0)"'))
    s.append(radial(f"{uid}cu", [(0, "#ffffff", 1), (.78, "#ede8e0", 1), (1, "#c9c1b5", 1)], cx=.4, cy=.38, r=.66) +
             f'<circle cx="{cx}" cy="{cy}" r="105" fill="url(#{uid}cu)"/>')
    s.append(radial(f"{uid}cf", [(0, "#2b160b", 1), (.6, "#3b1f10", 1), (.86, "#7c4b25", 1), (1, "#a9723f", 1)], r=.5) +
             f'<circle cx="{cx}" cy="{cy}" r="87" fill="url(#{uid}cf)"/>')
    cr = "".join(f'<circle cx="{cx + rnd.gauss(0, 34):.1f}" cy="{cy + rnd.gauss(0, 34):.1f}" r="{rnd.uniform(1.5, 5):.1f}" fill="#b07a45" '
                 f'opacity="{rnd.uniform(.08, .22):.2f}"/>' for _ in range(70))
    s.append(f'<clipPath id="{uid}cc"><circle cx="{cx}" cy="{cy}" r="86"/></clipPath><g clip-path="url(#{uid}cc)">{cr}'
             f'<rect x="{cx - 56}" y="{cy - 56}" width="46" height="26" rx="7" fill="#ffffff" opacity=".42" filter="url(#soft0)" transform="rotate(-18 {cx} {cy})"/></g>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="#ffffff" stroke-width="3" opacity=".75"/>')
    return "".join(s)


def badge(cx, cy, t, label="FACT CHECKED"):
    if t <= 0:
        return ""
    w, h = 338, 74
    x, y = cx - w / 2, cy - h / 2
    sc = .5 + .5 * backout(t)
    ck = f"M{x + 28},{y + h / 2 + 1}l9,9l18,-19"
    return (f'<g opacity="{min(1, t * 2):.3f}" transform="translate({cx},{cy}) scale({sc:.4f}) translate({-cx},{-cy})">'
            f'<rect x="{x + 6}" y="{y + 16}" width="{w}" height="{h}" rx="{h / 2}" fill="{SHD}" opacity=".6" filter="url(#soft)"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="#17191e" opacity=".9"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="none" stroke="#ffffff" stroke-opacity=".22" stroke-width="1.4"/>'
            f'<circle cx="{x + 45}" cy="{y + h / 2}" r="25" fill="url(#gTeal)"/>'
            f'<path d="{ck}" fill="none" stroke="#06140c" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" transform="translate(4,0)"/>'
            + T(x + 86, y + h / 2 + 9, label, 26, 700, WHITE, FT, anchor="start", ls=2.5) + '</g>')


def shot3(f, n):
    bg = lay("desk", desk_layer(3))
    props = lay("s3props", report(560, 905, -4) + pen(938, 975, 470, 74) + cup(150, 1340))
    scene = push(bg + props, f, n, focus=(560, 900), amount=.035)
    top = (linear("s3t", [(0, SHD, .78), (.75, SHD, .35), (1, SHD, 0)]) + f'<rect width="{W}" height="620" fill="url(#s3t)"/>')
    o1, d1 = appear(f, 2)
    o2, d2 = appear(f, 10)
    txt = (top + T(540, 440 + d1, "Fact check.", 100, 700, WHITE, FD, ls=-2, op=o1) +
           T(540, 510 + d2, "U.S. Copyright Office  ·  January 2025", 36, 500, GRAY, FT, op=o2) +
           badge(770, 1162, (f - 26) / 14))
    return scene, txt


# ------------------------------------------------------------------ shot 4: prompts ---
PROMPT = "amber perfume bottle, dunes, golden hour"


def shot4(f, n):
    bg = lay("studio4", studio(4, key=(540, 420), floor_pool=(540, 1460), warmth=.8))
    s = [bg]
    bx, by, bw, bh = 72, 540, 936, 92
    s.append(f'<rect x="{bx + 6}" y="{by + 20}" width="{bw}" height="{bh}" rx="{bh / 2}" fill="{SHD}" opacity=".6" filter="url(#soft)"/>'
             f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="{bh / 2}" fill="#20232a" opacity=".9"/>'
             + linear("pbs", [(0, "#ffffff", .34), (1, "#ffffff", .06)]) +
             f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="{bh / 2}" fill="none" stroke="url(#pbs)" stroke-width="1.6"/>')
    s.append(sparkle(bx + 50, by + bh / 2, 17, "url(#gAmb)"))
    nch = max(0, min(len(PROMPT), int((f - 4) * 1.3)))
    s.append(T(bx + 84, by + bh / 2 + 10, PROMPT[:nch], 28, 500, WHITE, MONO, anchor="start", op=.92))
    if nch < len(PROMPT) or (f // 9) % 2 == 0:
        s.append(f'<rect x="{bx + 86 + nch * 16.8:.1f}" y="{by + 28}" width="3" height="36" rx="1.5" fill="{AMB_A}"/>')
    pulse = .5 + .5 * math.sin(f / 4) if 34 <= f < 100 else 0
    s.append(glow(bx + bw - 46, by + bh / 2, 70, AMB_B, .35 * pulse, "gbtn") +
             f'<circle cx="{bx + bw - 46}" cy="{by + bh / 2}" r="31" fill="url(#gAmb)"/>'
             f'<path d="M{bx + bw - 46},{by + bh / 2 + 12}V{by + bh / 2 - 11}M{bx + bw - 56},{by + bh / 2 - 1}L{bx + bw - 46},{by + bh / 2 - 11}L{bx + bw - 36},{by + bh / 2 - 1}" '
             f'fill="none" stroke="#2a1408" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    cnt = 0 if f < 40 else 100 if f >= 100 else 1 + int(99 * ((f - 40) / 60) ** 2.2)
    cs, gap = 236, 16
    gx, gy = 540 - cs - gap / 2, 666
    for i in range(4):
        x, y = gx + (i % 2) * (cs + gap), gy + (i // 2) * (cs + gap)
        s.append(f'<rect x="{x + 6}" y="{y + 18}" width="{cs}" height="{cs}" rx="{cs * .08:.0f}" fill="{SHD}" opacity=".6" filter="url(#soft)"/>')
        if cnt == 0:
            sw = ((f * 14 + i * 60) % 520) - 140
            s.append(f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="{cs * .08:.0f}" fill="#1c1f25"/>'
                     f'<clipPath id="s4k{i}"><rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="{cs * .08:.0f}"/></clipPath>'
                     f'<g clip-path="url(#s4k{i})"><rect x="{x + sw}" y="{y - 40}" width="70" height="{cs + 80}" fill="#ffffff" opacity=".06" '
                     f'transform="rotate(20 {x + sw} {y})" filter="url(#soft0)"/></g>')
        else:
            v = (cnt * 3 + i * 5) % 8
            img = lay(f"adv{v}", ad_scene(v, ui=False))
            s.append(thumb(img, x, y, cs, f"s4t{i}", crop=(0, 760, 1080)))
            s.append(f'<rect x="{x + .7}" y="{y + .7}" width="{cs - 1.4}" height="{cs - 1.4}" rx="{cs * .08:.0f}" fill="none" stroke="#ffffff" stroke-opacity=".22"/>')
    if cnt:
        cx, cy = 540, gy + cs + gap / 2
        s.append(f'<circle cx="{cx + 4}" cy="{cy + 14}" r="78" fill="{SHD}" opacity=".6" filter="url(#soft)"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="78" fill="#17191e" opacity=".92"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="78" fill="none" stroke="#ffffff" stroke-opacity=".25" stroke-width="1.4"/>'
                 + T(cx, cy + 14, f"×{cnt}", 50 if cnt < 100 else 46, 700, "url(#gAmb)" if cnt == 100 else WHITE, FD, ls=-1) +
                 T(cx, cy + 44, "REWRITES", 15, 600, GRAY, FT, ls=2.5))
    scene = "".join(s)
    o1, d1 = appear(f, 2)
    o2, d2 = appear(f, 9)
    o3, d3 = appear(f, 96)
    txt = (T(540, 392 + d1, "Prompts alone don't", 84, 700, WHITE, FD, ls=-2, op=o1) +
           T(540, 482 + d2, "make you the author.", 84, 700, WHITE, FD, ls=-2, op=o2) +
           T(540, 1222 + d3, 'Rewrite it 100 times. <tspan fill="url(#gAmb)">Still not enough.</tspan>', 38, 600, WHITE, FT, op=o3, raw=True))
    return scene + dust(f, 9, 40), txt


# ------------------------------------------------------------------ shot 5: the human part ---
def pencil(x0, y0, x1, y1, w=16, uid="pc"):
    """Matte graphite pencil with a sharpened cedar tip, from (x0,y0) to the point (x1,y1)."""
    L = math.hypot(x1 - x0, y1 - y0)
    a = math.degrees(math.atan2(y1 - y0, x1 - x0))
    tip = w * 2.3
    return (f'<g transform="translate({x0:.1f},{y0:.1f}) rotate({a:.1f})">'
            f'<rect x="6" y="{-w / 2 + 12}" width="{L}" height="{w}" rx="3" fill="{SHD}" opacity=".5" filter="url(#soft0)"/>'
            + linear(f"{uid}b", [(0, "#0e0f12", 1), (.3, "#3a3d44", 1), (.42, "#6a6e77", 1), (.55, "#24262b", 1), (1, "#0c0d0f", 1)], 0, 0, 0, 1) +
            f'<rect x="0" y="{-w / 2}" width="{L - tip}" height="{w}" rx="2" fill="url(#{uid}b)"/>'
            f'<rect x="0" y="{-w / 2}" width="{w * .9:.1f}" height="{w}" rx="2" fill="#c9ccd2"/>'
            f'<rect x="{w * .3:.1f}" y="{-w / 2}" width="2" height="{w}" fill="#6e727a"/>'
            + linear(f"{uid}w", [(0, "#a8774a", 1), (.45, "#e0b383", 1), (1, "#8a5e36", 1)], 0, 0, 0, 1) +
            f'<path d="M{L - tip},{-w / 2}L{L - 6},{-2.2}L{L - 6},{2.2}L{L - tip},{w / 2}Z" fill="url(#{uid}w)"/>'
            f'<path d="M{L - 9},{-3.2}L{L},{0}L{L - 9},{3.2}Z" fill="#2c2e33"/>'
            f'<rect x="{w}" y="{-w / 2 + 3}" width="{L - tip - w - 4}" height="1.6" fill="#ffffff" opacity=".25"/></g>')


def pencil_lines(pts, rnd, passes=2, width=(1.3, 2.2), op=(.45, .85), jitter=1.6, closed=False, col=GRAPHITE):
    out = []
    for _ in range(passes):
        q = [(x + rnd.gauss(0, jitter), y + rnd.gauss(0, jitter)) for x, y in pts]
        out.append(f'<path d="{catmull(q, closed)}" fill="none" stroke="{col}" stroke-width="{rnd.uniform(*width):.2f}" '
                   f'opacity="{rnd.uniform(*op):.2f}" stroke-linecap="round" stroke-linejoin="round"/>')
    return "".join(out)


def bottle_sketch(cx, base, k, seed, notes=True):
    """Pencil study of the bottle on its plinth: construction lines, 2-3 passes of contour, hatching, notes."""
    rnd = random.Random(seed)
    bw, bh = (k * rnd.uniform(.26, .4), k * rnd.uniform(.42, .6))
    r = bw * rnd.uniform(.1, .45)
    s = []
    # construction: axis, horizon, ellipse guide
    s.append(f'<path d="M{cx:.1f},{base - bh * 1.7:.1f}V{base + k * .5:.1f}" stroke="{GRAPHITE}" stroke-width="1" opacity=".22" stroke-dasharray="6 7"/>')
    s.append(f'<path d="M{cx - k * .9:.1f},{base - bh * .2:.1f}H{cx + k * .9:.1f}" stroke="{GRAPHITE}" stroke-width="1" opacity=".2"/>')
    # sun sketched
    sx, sy = cx + k * rnd.uniform(.35, .6), base - bh * rnd.uniform(.35, .7)
    s.append(pencil_lines([(sx + k * .09 * math.cos(t / 8 * 6.283), sy + k * .09 * math.sin(t / 8 * 6.283)) for t in range(8)], rnd, 2, (1, 1.6), (.3, .55), 1.4, True))
    # plinth
    prx, pry, ph = k * .42, k * .08, k * .44
    top = [(cx + prx * math.cos(t / 16 * 6.283), base + pry * math.sin(t / 16 * 6.283)) for t in range(16)]
    s.append(pencil_lines(top, rnd, 2, closed=True))
    s.append(pencil_lines([(cx - prx, base), (cx - prx, base + ph * .5), (cx - prx, base + ph)], rnd, 2))
    s.append(pencil_lines([(cx + prx, base), (cx + prx, base + ph * .5), (cx + prx, base + ph)], rnd, 2))
    s.append(pencil_lines([(cx + prx * math.cos(t / 10 * 3.1416), base + ph + pry * math.sin(t / 10 * 3.1416)) for t in range(11)], rnd, 2))
    # bottle body (rounded rect as points), neck, cap
    x0, x1, y0, y1 = cx - bw / 2, cx + bw / 2, base - bh, base
    body = [(x0 + r, y0), (cx, y0 - 1), (x1 - r, y0), (x1, y0 + r), (x1, (y0 + y1) / 2), (x1, y1 - r * .4), (cx, y1), (x0, y1 - r * .4), (x0, (y0 + y1) / 2), (x0, y0 + r)]
    s.append(pencil_lines(body, rnd, 3, closed=True))
    nw, nh = bw * .32, k * .05
    cw, ch = bw * .5, k * rnd.uniform(.1, .17)
    s.append(pencil_lines([(cx - nw / 2, y0), (cx - nw / 2, y0 - nh), (cx + nw / 2, y0 - nh), (cx + nw / 2, y0)], rnd, 2))
    s.append(pencil_lines([(cx - cw / 2, y0 - nh), (cx - cw / 2, y0 - nh - ch), (cx + cw / 2, y0 - nh - ch), (cx + cw / 2, y0 - nh), (cx - cw / 2, y0 - nh)], rnd, 2))
    # hatching on the shadow side (left) of bottle and plinth
    hatch = []
    for i in range(int(bh / 7)):
        yy = y0 + 6 + i * 7
        hatch.append(f'<path d="M{x0 + 3:.1f},{yy + 9:.1f}L{x0 + bw * .32:.1f},{yy:.1f}"/>')
    for i in range(int(ph / 8)):
        yy = base + 10 + i * 8
        hatch.append(f'<path d="M{cx - prx + 3:.1f},{yy + 10:.1f}L{cx - prx * .45:.1f},{yy:.1f}"/>')
    s.append(f'<path d="M{x0:.1f},{y0 + 8:.1f}L{x0 + bw * .36:.1f},{y0 + 8:.1f}L{x0 + bw * .3:.1f},{y1 - 4:.1f}L{x0:.1f},{y1 - 6:.1f}Z" fill="{GRAPHITE}" opacity=".10" filter="url(#soft0)"/>'
             f'<path d="M{cx - prx:.1f},{base + 6:.1f}L{cx - prx * .4:.1f},{base + 6:.1f}L{cx - prx * .45:.1f},{base + ph:.1f}L{cx - prx:.1f},{base + ph:.1f}Z" fill="{GRAPHITE}" opacity=".09" filter="url(#soft0)"/>')
    s.append(f'<g stroke="{GRAPHITE}" stroke-width="1.1" opacity=".42" stroke-linecap="round">{"".join(hatch)}</g>')
    s.append(f'<path d="M{x1 - bw * .18:.1f},{y0 + bh * .15:.1f}L{x1 - bw * .14:.1f},{y0 + bh * .38:.1f}" stroke="#fbf7f0" stroke-width="5" stroke-linecap="round" opacity=".85"/>')
    # cast shadow scribble on plinth top toward viewer-left
    s.append(pencil_lines([(cx - bw * .2, base + pry * .2), (cx - bw * .9, base + pry * .5), (cx - bw * 1.2, base + pry * .2)], rnd, 3, (1, 1.8), (.3, .5), 2))
    # label + dune line
    s.append(pencil_lines([(x0 + bw * .2, y0 + bh * .45), (x1 - bw * .2, y0 + bh * .45), (x1 - bw * .2, y0 + bh * .7), (x0 + bw * .2, y0 + bh * .7)], rnd, 1, (1, 1.4), (.35, .5), 1, True))
    s.append(pencil_lines([(cx - k * .95, base - bh * .05), (cx - k * .5, base - bh * .2), (cx - k * .1, base - bh * .1), (cx + k * .4, base - bh * .25), (cx + k * .95, base - bh * .12)], rnd, 2, (1, 1.6), (.3, .5)))
    return "".join(s)


def sketch_page(i, cx=540, cy=940, w=440, h=560):
    rnd = random.Random(500 + i)
    x, y = cx - w / 2, cy - h / 2
    s = [paper(x, y, w, h, f"sp{i}", 40 + i, "#f3eee5")]
    if i in (4, 11):   # a coffee ring on two of the pages
        s.append(f'<circle cx="{x + w * .78:.0f}" cy="{y + h * .2:.0f}" r="46" fill="none" stroke="#a5703c" stroke-width="5" opacity=".18" filter="url(#rough2)"/>')
    s.append(bottle_sketch(cx, cy + 40, 300, 900 + i))
    notes = [["V" + str(i + 1)], ["AMBER GLASS"], ["SUN: BACK RIGHT"], ["CAP TALLER?"], ["SOFTER SHADOW"], ["LABEL LOWER"],
             ["DUNES: 3 LAYERS"], ["MORE GLOW"], ["PLINTH: STONE"], ["TRY 3/4 VIEW"]]
    t1, _ = lettering(notes[0], x + 30, y + 52, cap=22, colour=GRAPHITE, seed=40 + i, align="left")
    t2, _ = lettering(notes[1 + i % 9], x + w - 30, y + h - 34, cap=16, colour=GRAPHITE, seed=60 + i, align="right")
    s.append(f'<g opacity=".8">{t1}{t2}</g>')
    # eraser crumbs
    s.append("".join(f'<ellipse cx="{x + rnd.uniform(20, w - 20):.0f}" cy="{y + rnd.uniform(h * .6, h - 20):.0f}" rx="{rnd.uniform(2, 4):.1f}" '
                     f'ry="{rnd.uniform(1, 2):.1f}" fill="#cbb9a6" opacity=".55"/>' for _ in range(rnd.randint(0, 5))))
    return "".join(s)


def ill_sketchbook(x, y, w, h):
    rnd = random.Random(31)
    px, py, pw, ph = x + 22, y + 26, w - 44, h - 40
    s = [paper(px, py, pw, ph, "sb", 77, "#f3eee5", stack=2)]
    for k in range(9):   # spiral binding
        cx = px + 24 + k * (pw - 48) / 8
        s.append(f'<ellipse cx="{cx:.1f}" cy="{py + 2}" rx="5" ry="12" fill="none" stroke="#9ea2aa" stroke-width="3"/>'
                 f'<ellipse cx="{cx:.1f}" cy="{py + 10}" rx="3" ry="3" fill="#1a1c20"/>')
    s.append(bottle_sketch(px + pw / 2, py + ph * .58, pw * .62, 77))
    s.append(pencil(px + pw * .1, py + ph * .98, px + pw * .9, py + ph * .64, 13, "sbp"))
    return "".join(s)


def ill_lens(cx, cy, r):
    s = [ell(cx + 10, cy + 22, r, r, SHD, .6, 'filter="url(#soft)"')]
    s.append(radial("ln0", [(0, "#2a2c31", 1), (.8, "#16171a", 1), (1, "#0b0c0e", 1)]) + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#ln0)"/>')
    ticks = "".join(f'<path d="M{cx + r * .9 * math.cos(t / 72 * 6.283):.1f},{cy + r * .9 * math.sin(t / 72 * 6.283):.1f}L'
                    f'{cx + r * .99 * math.cos(t / 72 * 6.283):.1f},{cy + r * .99 * math.sin(t / 72 * 6.283):.1f}"/>' for t in range(72))
    s.append(f'<g stroke="#3d4047" stroke-width="2.4">{ticks}</g>')
    s.append(linear("ln1", [(0, "#d7dade", 1), (.5, "#6b6f78", 1), (1, "#b6bac2", 1)], 0, 0, 1, 1) +
             f'<circle cx="{cx}" cy="{cy}" r="{r * .86}" fill="url(#ln1)"/><circle cx="{cx}" cy="{cy}" r="{r * .78}" fill="#111215"/>')
    s.append(f'<path id="lnarc" d="M{cx - r * .795},{cy}A{r * .795},{r * .795} 0 0 1 {cx + r * .795},{cy}" fill="none"/>'
             f'<text font-family="{FT}" font-size="{r * .062:.1f}" font-weight="700" fill="#24262b" letter-spacing="1.2">'
             f'<textPath href="#lnarc" startOffset="50%" text-anchor="middle">35mm  1:1.4  ·  0.3m / 1ft</textPath></text>')
    s.append(radial("ln2", [(0, "#1d2a44", 1), (.55, "#0c1222", 1), (.85, "#070a12", 1), (1, "#2b2f3a", 1)], cx=.45, cy=.42) +
             f'<circle cx="{cx}" cy="{cy}" r="{r * .62}" fill="url(#ln2)"/>')
    # multi-coating reflections
    s.append(f'<path d="M{cx - r * .5:.1f},{cy - r * .1:.1f}A{r * .5:.1f},{r * .5:.1f} 0 0 1 {cx + r * .1:.1f},{cy - r * .5:.1f}" stroke="#a46bff" stroke-width="{r * .08:.1f}" fill="none" opacity=".55" filter="url(#soft0)" style="mix-blend-mode:screen"/>'
             f'<path d="M{cx + r * .2:.1f},{cy + r * .42:.1f}A{r * .45:.1f},{r * .45:.1f} 0 0 0 {cx + r * .45:.1f},{cy + r * .1:.1f}" stroke="#4fe0a0" stroke-width="{r * .06:.1f}" fill="none" opacity=".5" filter="url(#soft0)" style="mix-blend-mode:screen"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r * .3}" fill="none" stroke="#3a4a6a" stroke-width="2" opacity=".6"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r * .14}" fill="#050608"/>'
             f'<ellipse cx="{cx - r * .24:.1f}" cy="{cy - r * .26:.1f}" rx="{r * .14:.1f}" ry="{r * .07:.1f}" fill="#ffffff" opacity=".85" transform="rotate(-35 {cx - r * .24:.1f} {cy - r * .26:.1f})"/>'
             f'<circle cx="{cx + r * .2:.1f}" cy="{cy + r * .22:.1f}" r="{r * .03:.1f}" fill="#ffffff" opacity=".6"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r - 1}" fill="none" stroke="#ffffff" stroke-opacity=".2" stroke-width="1.5"/>')
    return "".join(s)


def ill_timeline(x, y, w, h):
    rnd = random.Random(52)
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="#101216"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="none" stroke="#ffffff" stroke-opacity=".1"/>']
    # preview monitor
    s.append(thumb(lay("ad0", ad_scene(0)), x + 16, y + 16, w - 32, "tlpv", crop=(0, 700, 1080), h=h * .36, rx=8))
    ry = y + 22 + h * .36
    ticks = "".join(f'<rect x="{x + 16 + k * (w - 32) / 24:.1f}" y="{ry + (0 if k % 4 else -4)}" width="1.2" height="{6 if k % 4 else 10}" fill="#6e727a"/>' for k in range(25))
    s.append(ticks)
    cols = ["#ff9a4a", "#7d95ff", "#b48cff", "#3fd28b"]
    ty = ry + 20
    th = (y + h - 16 - ty) / 4 - 6
    for tr in range(4):
        xx = x + 16
        while xx < x + w - 30:
            cw = rnd.uniform(26, 70)
            cw = min(cw, x + w - 16 - xx)
            if cw < 10:
                break
            c = cols[tr]
            s.append(f'<rect x="{xx:.1f}" y="{ty + tr * (th + 6):.1f}" width="{cw - 3:.1f}" height="{th:.1f}" rx="4" fill="{c}" opacity=".85"/>'
                     f'<rect x="{xx:.1f}" y="{ty + tr * (th + 6):.1f}" width="{cw - 3:.1f}" height="{th * .38:.1f}" rx="4" fill="#ffffff" opacity=".18"/>')
            xx += cw + rnd.choice([0, 0, 8])
    ph = x + w * .58
    s.append(f'<rect x="{ph - 1.2:.1f}" y="{ry - 6}" width="2.4" height="{y + h - 12 - ry:.1f}" fill="{WHITE}"/>'
             f'<path d="M{ph - 8:.1f},{ry - 14}h16v8l-8,7l-8,-7z" fill="{WHITE}"/>')
    return "".join(s)


def s5_cards():
    out = []
    w, h, gap, y = 296, 470, 20, 612
    x0 = 540 - (3 * w + 2 * gap) / 2
    for i in range(3):
        x = x0 + i * (w + gap)
        c = glass_card(x, y, w, h, f"s5c{i}", 34)
        if i == 0:
            c += ill_sketchbook(x + 8, y + 10, w - 16, 330)
        elif i == 1:
            c += ill_lens(x + w / 2, y + 180, 118)
        else:
            c += ill_timeline(x + 18, y + 28, w - 36, 300)
        title, sub = [("Your sketches", "expressive input"), ("Your footage", "you shot it"), ("Your edit", "selection & arrangement")][i]
        c += T(x + w / 2, y + 396, title, 32, 600, WHITE, FT, ls=-.3) + T(x + w / 2, y + 432, sub, 20, 500, GRAY, FT)
        out.append(lay(f"s5card{i}", c))
    return out


def shot5(f, n):
    bg = lay("studio5", studio(5, key=(380, 600), warmth=1.1))
    cards = s5_cards()
    s = [bg]
    for i, c in enumerate(cards):
        o, d = appear(f, 14 + i * 8, 18, 60)
        if o > 0:
            s.append(f'<g opacity="{o:.3f}" transform="translate(0,{d:.1f})">{c}</g>')
    scene = push("".join(s), f, n, focus=(540, 860), amount=.02)
    o1, d1 = appear(f, 2)
    o2, d2 = appear(f, 8)
    txt = (T(540, 410 + d1, "What counts", 96, 700, WHITE, FD, ls=-2, op=o1) +
           T(540, 512 + d2, 'is the <tspan fill="url(#gAmb)">human part.</tspan>', 96, 700, WHITE, FD, ls=-2, op=o2, raw=True))
    return scene + dust(f, 10, 50), txt


# ------------------------------------------------------------------ shot 6: the sketches ---
PAGE_T = [6 + i * 4 for i in range(SKETCHES)]


def shot6(f, n):
    bg = lay("desk", desk_layer(3))
    s = [bg]
    rnd = random.Random(66)
    landed = 0
    for i in range(SKETCHES):
        rot, jx, jy = rnd.uniform(-9, 9), rnd.uniform(-34, 34), rnd.uniform(-24, 24)
        t0 = PAGE_T[i]
        if f < t0:
            continue
        t = eo((f - t0) / 7, 3)
        if f - t0 >= 3:
            landed = i + 1
        sc = 1.12 - .12 * t
        page = lay(f"page{i}", sketch_page(i))
        s.append(f'<g opacity="{min(1, t * 1.5):.3f}" transform="translate({540 + jx:.1f},{940 + jy:.1f}) rotate({rot:.2f}) scale({sc:.4f}) translate(-540,-940)">{page}</g>')
    # the one AI frame, born from the last sketch
    a = eo((f - 76) / 20, 2) if f >= 76 else 0
    if a > 0:
        s.append(glow(540, 940, 520, AMB_A, .25 * a, "s6g"))
        img = lay("adv0n", ad_scene(0, ui=False))
        s.append(f'<g opacity="{a:.3f}"><rect x="{540 - 220 + 14}" y="{940 - 280 + 26}" width="440" height="560" fill="{SHD}" opacity=".6" filter="url(#soft2)"/>'
                 + thumb(img, 540 - 220, 940 - 280, 440, "s6ai", crop=(0, 600, 1080), h=560, rx=6) +
                 f'<rect x="{540 - 220}" y="{940 - 280}" width="440" height="560" rx="6" fill="none" stroke="#ffffff" stroke-opacity=".5"/></g>')
        s.append(pill(540 + 220 - 196, 940 - 280 + 24, "AI frame", "", (f - 88) / 12, "s6pl", icon=lambda x, y: sparkle(x, y, 12, "url(#gAmb)")))
    scene = push("".join(s), f, n, focus=(540, 940), amount=.03)
    k = max(1, landed)
    o1, d1 = appear(f, 0)
    o3, d3 = appear(f, 80)
    word = "sketch" if k == 1 else "sketches"
    top = (linear("s6t", [(0, SHD, .75), (.8, SHD, .3), (1, SHD, 0)]) + f'<rect width="{W}" height="640" fill="url(#s6t)"/>')
    txt = (top + T(540, 350 + d1, "Our last film:", 44, 600, GRAY, FT, op=o1) +
           T(540, 466 + d1, f'<tspan fill="url(#gAmb)">{k}</tspan> {word}', 112, 700, WHITE, FD, ls=-3, op=o1, raw=True) +
           T(540, 540 + d3, "before one AI frame.", 52, 600, WHITE, FD, ls=-1, op=o3))
    return scene, txt


# ------------------------------------------------------------------ shot 7: pipeline ---
def node_icon(kind, cx, cy, col):
    st = f'fill="none" stroke="{col}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"'
    if kind == 0:
        return f'<path d="M{cx - 11},{cy + 11}l3,-10l14,-14l7,7l-14,14z M{cx + 3},{cy - 10}l7,7" {st}/>'
    if kind == 1:
        return sparkle(cx, cy, 15, col)
    return (f'<path d="M{cx},{cy - 13}l15,7l-15,7l-15,-7z" {st}/><path d="M{cx - 15},{cy + 1}l15,7l15,-7" {st}/>'
            f'<path d="M{cx - 15},{cy + 8}l15,7l15,-7" {st}/>')


def shot7(f, n):
    bg = lay("studio7", studio(7, key=(540, 520)))
    s = [bg]
    xs = [220, 540, 860]
    cs = 270
    imgs = [(lay("page13", sketch_page(13)), (320, 660, 440)), (lay("adv3n", ad_scene(3, ui=False)), (0, 700, 1080)),
            (lay("ad0", ad_scene(0)), (0, 760, 1080))]
    for i, x in enumerate(xs):
        o, d = appear(f, 4 + i * 7, 16, 40)
        if o <= 0:
            continue
        tx, ty = x - cs / 2, 626 + d
        tile = (f'<rect x="{tx + 8}" y="{ty + 22}" width="{cs}" height="{cs}" rx="26" fill="{SHD}" opacity=".6" filter="url(#soft2)"/>'
                + thumb(imgs[i][0], tx, ty, cs, f"s7t{i}", crop=imgs[i][1], rx=26) +
                f'<rect x="{tx + .7}" y="{ty + .7}" width="{cs - 1.4}" height="{cs - 1.4}" rx="26" fill="none" stroke="#ffffff" stroke-opacity=".25"/>')
        if i == 1:   # raw output looks flat until it is finished
            tile += f'<rect x="{tx}" y="{ty}" width="{cs}" height="{cs}" rx="26" fill="#6b6f78" opacity=".28" style="mix-blend-mode:saturation"/>'
        s.append(f'<g opacity="{o:.3f}">{tile}</g>')
    ly = 1000
    p = eo((f - 14) / 58, 2) if f >= 14 else 0
    s.append(f'<rect x="{xs[0]}" y="{ly - 3}" width="{xs[2] - xs[0]}" height="6" rx="3" fill="#2a2d35"/>'
             f'<rect x="{xs[0]}" y="{ly - 3}" width="{(xs[2] - xs[0]) * p:.1f}" height="6" rx="3" fill="url(#gAmb)"/>')
    for i, x in enumerate(xs):
        on = p >= i / 2 - .001 and f >= 14
        tt = eo(((p - i / 2) * 6)) if on else 0
        s.append(glow(x, ly, 90, AMB_B, .4 * tt, f"s7g{i}") if tt > 0 else "")
        s.append(f'<circle cx="{x}" cy="{ly}" r="38" fill="{"url(#gAmb)" if on else "#20232a"}"/>'
                 f'<circle cx="{x}" cy="{ly}" r="38" fill="none" stroke="#ffffff" stroke-opacity="{.15 if on else .3}" stroke-width="1.4"/>'
                 + node_icon(i, x, ly, "#2a1408" if on else GRAY))
        lab, sub = [("Sketch", "by hand"), ("Generate", "AI, second"), ("Finish", "After Effects")][i]
        s.append(T(x, ly + 84, lab, 34, 600, WHITE, FT) + T(x, ly + 120, sub, 24, 500, GRAY, FT))
    scene = "".join(s)
    o1, d1 = appear(f, 2)
    o2, d2 = appear(f, 8)
    txt = (T(540, 412 + d1, "Sketch. Generate.", 92, 700, WHITE, FD, ls=-2, op=o1) +
           T(540, 508 + d2, 'Finish <tspan fill="url(#gAmb)">by hand.</tspan>', 92, 700, WHITE, FD, ls=-2, op=o2, raw=True))
    return scene + dust(f, 12, 40), txt


# ------------------------------------------------------------------ shot 8: brand ---
def shot8(f, n):
    bg = lay("studio8", studio(8, key=(540, 760), floor_pool=(540, 1420), warmth=1.3))
    rev = eo(f / 26, 2)
    lt, bb = lettering(["HANDMADE,"], 540, 846, cap=116, colour="#f6efe4", weight=13, seed=808, reveal=rev)
    assert in_safe(bb), bb
    L = 760
    swoosh = catmull([(196, 900), (360, 918), (560, 912), (760, 902), (884, 890)])
    dash = L * (1 - eo((f - 16) / 16)) if f >= 16 else L
    o2, d2 = appear(f, 20, 16, 30)
    o3, d3 = appear(f, 28, 16, 20)
    txt = (glow(540, 900, 520, AMB_A, .14, "s8g") + lt +
           f'<path d="{swoosh}" fill="none" stroke="url(#gAmb)" stroke-width="7" stroke-linecap="round" stroke-dasharray="{L}" '
           f'stroke-dashoffset="{dash:.1f}" filter="url(#rough)"/>' +
           T(540, 1036 + d2, "with AI.", 124, 700, WHITE, FD, ls=-3, op=o2) +
           T(540, 1120 + d3, "@handmadewith.ai", 40, 500, GRAY, FT, op=o3))
    return bg + dust(f, 13, 50), txt


# ------------------------------------------------------------------ shot 9: CTA ---
def plane(cx, cy, s, rot):
    top = poly([(cx + 60 * s, cy), (cx - 42 * s, cy - 34 * s), (cx - 18 * s, cy + 4 * s)])
    bot = poly([(cx + 60 * s, cy), (cx - 18 * s, cy + 4 * s), (cx - 6 * s, cy + 36 * s)])
    return (f'<g transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})">'
            f'<path d="{top}" fill="#ffffff" fill-opacity=".14" stroke="{WHITE}" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="{bot}" fill="#ffffff" fill-opacity=".06" stroke="{WHITE}" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="M{cx - 18 * s:.1f},{cy + 4 * s:.1f}L{cx + 2 * s:.1f},{cy + 22 * s:.1f}" stroke="{WHITE}" stroke-width="5" stroke-linecap="round"/></g>')


def share_sheet(f, sel_t):
    """Frosted 'Send to' sheet with four recipients; the first one gets picked and confirmed."""
    x, y, w, h = 110, 760, 860, 300
    s = [glass_card(x, y, w, h, "s9c", 40), T(x + 44, y + 58, "Send to", 26, 600, GRAY, FT, anchor="start"),
         f'<rect x="{x + 44}" y="{y + 80}" width="{w - 88}" height="1" fill="#ffffff" opacity=".1"/>']
    who = [("LG", "Legal", ("#ffb35c", "#ff6f3c")), ("BL", "Brand lead", ("#9fb3ff", "#5b6cff")),
           ("AG", "Agency", ("#c3a3ff", "#7f56e8")), ("ED", "Editor", ("#7fe3b6", "#22a868"))]
    for k, (ini, lab, (c1, c2)) in enumerate(who):
        cx, cy = x + 130 + k * 200, y + 168
        o, d = appear(f, 10 + k * 4, 14, 20)
        if o <= 0:
            continue
        g = linear(f"s9a{k}", [(0, c1, 1), (1, c2, 1)], 0, 0, 1, 1)
        ring = ""
        if k == 0 and sel_t > 0:
            ring = (f'<circle cx="{cx}" cy="{cy + d}" r="{52 + 4 * (1 - eo(sel_t)):.1f}" fill="none" stroke="{WHITE}" stroke-width="3.5" opacity="{eo(sel_t):.2f}"/>'
                    f'<circle cx="{cx + 34}" cy="{cy + d - 34}" r="{15 * eo(sel_t):.1f}" fill="url(#gTeal)"/>'
                    f'<path d="M{cx + 27},{cy + d - 34}l5,5l9,-10" fill="none" stroke="#06140c" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" opacity="{eo(sel_t):.2f}"/>')
        s.append(f'<g opacity="{o:.3f}">{g}<circle cx="{cx}" cy="{cy + d}" r="44" fill="url(#s9a{k})"/>'
                 f'<circle cx="{cx}" cy="{cy + d}" r="44" fill="none" stroke="#ffffff" stroke-opacity=".3"/>'
                 + T(cx, cy + d + 11, ini, 30, 700, "#14161a", FT, ls=.5) + T(cx, cy + d + 84, lab, 24, 500, WHITE, FT) + ring + '</g>')
    return "".join(s)


def shot9(f, n):
    bg = lay("studio9", studio(9, key=(600, 640)))
    t = eo(f / 46, 3)
    pts = [(120, 700), (330, 640), (560, 618), (760, 648), (930, 712)]

    def at(u):
        u = max(0, min(.9999, u)) * (len(pts) - 1)
        i = int(u)
        a, b = pts[i], pts[i + 1]
        return a[0] + (b[0] - a[0]) * (u - i), a[1] + (b[1] - a[1]) * (u - i)
    trail = [at(t * k / 24) for k in range(25)]
    px, py = at(t)
    qx, qy = at(min(1, t + .02))
    ang = math.degrees(math.atan2(qy - py, qx - px))
    s = [bg, share_sheet(f, (f - 44) / 10),
         f'<path d="{catmull(trail)}" fill="none" stroke="url(#gAmb)" stroke-width="4" stroke-linecap="round" stroke-dasharray="2 16" opacity=".9"/>',
         glow(px, py, 150, AMB_A, .2, "s9g"), plane(px, py, 1.1, ang)]
    o1, d1 = appear(f, 2)
    o2, d2 = appear(f, 8)
    o3, d3 = appear(f, 22)
    txt = (T(540, 410 + d1, "Send this to whoever", 84, 700, WHITE, FD, ls=-2, op=o1) +
           T(540, 502 + d2, 'handles your <tspan fill="url(#gAmb)">copyright.</tspan>', 84, 700, WHITE, FD, ls=-2, op=o2, raw=True) +
           T(540, 1150 + d3, "Not legal advice. US rules; other countries differ.", 26, 500, GRAY2, FT, op=o3))
    return "".join(s) + dust(f, 14, 40), txt


SHOT_FN = {"s1": shot1, "s2": shot2, "s3": shot3, "s4": shot4, "s5": shot5, "s6": shot6, "s7": shot7, "s8": shot8, "s9": shot9}
LOOP = 12          # last frames dissolve into frame 0 so the replay is seamless


def frame(g):
    """Global frame g -> SVG body. Dissolves of XF frames between neighbouring shots."""
    parts = []
    for i, (name, a, b) in enumerate(SHOTS):
        if name not in SHOT_FN:
            continue
        lo, hi = a - (XF if i else 0), b
        if lo <= g <= hi:
            op = 1.0
            if i and g < a:
                op = eio((g - (a - XF)) / XF)
            sc, tx = SHOT_FN[name](g - a if g >= a else 0, b - a + 1)
            parts.append((op, sc + tx))
    if g >= TOTAL - LOOP:
        sc, tx = shot1(0, SHOTS[0][2] + 1)
        parts.append((eio((g - (TOTAL - LOOP) + 1) / LOOP), sc + tx))
    if not parts:
        parts = [(1, f'<rect width="{W}" height="{H}" fill="{WALL_B}"/>')]
    body = f'<defs>{SHARED_DEFS}</defs><rect width="{W}" height="{H}" fill="{WALL_B}"/>'
    for op, p in parts:
        body += p if op >= 1 else f'<g opacity="{op:.3f}">{p}</g>'
    return body + grade("#14203c", "#ffe8cc", .08) + finish_cached(Ctx.r, vignette=.42, mottle=.025, grain=.05)


def warm():
    """Build every cached layer once, so parallel render processes never race to write the same file."""
    lay("studio1", studio(1)); lay("studio2", studio(2, key=(520, 560)))
    lay("studio4", studio(4, key=(540, 420), floor_pool=(540, 1460), warmth=.8)); lay("studio5", studio(5, key=(380, 600), warmth=1.1))
    lay("studio7", studio(7, key=(540, 520))); lay("studio8", studio(8, key=(540, 760), floor_pool=(540, 1420), warmth=1.3))
    lay("studio9", studio(9, key=(600, 640))); lay("ad0", ad_scene(0)); lay("adv0n", ad_scene(0, ui=False)); lay("adv3n", ad_scene(3, ui=False))
    for v in range(8):
        lay(f"adv{v}", ad_scene(v, ui=False))
    lay("desk", desk_layer(3)); lay("s3props", report(560, 905, -4) + pen(938, 975, 470, 74) + cup(150, 1340))
    s5_cards()
    for i in range(SKETCHES):
        lay(f"page{i}", sketch_page(i))
    finish_cached(Ctx.r, vignette=.42, mottle=.025, grain=.05)


def main():
    cmd = sys.argv[1]
    if cmd == "still":
        g = int(sys.argv[2])
        scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1
        out = sys.argv[4] if len(sys.argv) > 4 else f"work/still_{g:05d}.png"
        Ctx.r = Renderer("work", scale=scale)
        Ctx.r.page.set_default_timeout(300000)
        Ctx.r.still(frame(g), out)
        Ctx.r.close()
        print("wrote", out)
    elif cmd == "warm":
        Ctx.r = Renderer("work", scale=float(sys.argv[2]) if len(sys.argv) > 2 else 2)
        Ctx.r.page.set_default_timeout(300000)
        warm()
        Ctx.r.close()
        print("warm ok", len(Ctx.L))
    elif cmd == "render":
        a, b = int(sys.argv[2]), int(sys.argv[3])
        scale = float(sys.argv[4]) if len(sys.argv) > 4 else 2
        Ctx.r = Renderer("work", scale=scale)
        Ctx.r.page.set_default_timeout(300000)
        u = Ctx.r.frames(frame, b, a)
        Ctx.r.close()
        print("unique", u)


if __name__ == "__main__":
    main()
