"""reelkit.py - hand-drawn SVG reel toolkit. Canvas 1080x1920, rendered with headless Chromium, encoded with ffmpeg.
Every picture element is an SVG path, gradient or filter written by the author. No image or video generation models."""
import base64, hashlib, json, math, pathlib, random, shutil, subprocess

W, H = 1080, 1920
SAFE = dict(top=270, bottom=670, side=65)          # px to keep clear of platform UI on a 1080x1920 reel


# ------------------------------------------------------------------ colour ---
def _rgb(c): return [int(c[i:i + 2], 16) for i in (1, 3, 5)]
def _hex(v): return "#" + "".join(f"{max(0, min(255, round(x))):02x}" for x in v)
def mix(c1, c2, t): return _hex([a + (b - a) * t for a, b in zip(_rgb(c1), _rgb(c2))])


def ramp(cols, t):
    """Sample a dark-to-light colour ramp at t in 0..1."""
    t = max(0.0, min(.9999, t)) * (len(cols) - 1)
    i = int(t)
    return mix(cols[i], cols[i + 1], t - i)


def jit(c, rnd, amt=6):
    d = rnd.uniform(-amt, amt)
    return _hex([x + d + rnd.uniform(-amt / 3, amt / 3) for x in _rgb(c)])


# ----------------------------------------------------------------- brushes ---
def _disp(fid, freq, octv, scale, seed, blur=0, streak=None, pad=8):
    s = (f'<filter id="{fid}" x="-{pad}%" y="-{pad}%" width="{100 + 2 * pad}%" height="{100 + 2 * pad}%" color-interpolation-filters="sRGB">'
         f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octv}" seed="{seed}" result="n"/>'
         f'<feDisplacementMap in="SourceGraphic" in2="n" scale="{scale}" xChannelSelector="R" yChannelSelector="G" result="d"/>')
    if streak:                                   # bristle gaps running along the local x axis of the filtered group
        f2, gain, bias = streak
        s += (f'<feTurbulence type="fractalNoise" baseFrequency="{f2}" numOctaves="2" seed="{seed + 7}" result="s"/>'
              f'<feColorMatrix in="s" type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 {gain} {bias}" result="m"/>'
              '<feComposite in="d" in2="m" operator="in" result="d"/>')
    if blur:
        s += f'<feGaussianBlur in="d" stdDeviation="{blur}"/>'
    return s + '</filter>'


def _noise(fid, freq, octv, seed, gain, bias):
    return (f'<filter id="{fid}" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octv}" seed="{seed}"/>'
            f'<feColorMatrix type="matrix" values="{gain} 0 0 0 {bias} {gain} 0 0 0 {bias} {gain} 0 0 0 {bias} 0 0 0 0 1"/></filter>')


BRUSHES = "".join([
    _disp("bristle", 0.023, 2, 16, 4, streak=("0.0047 0.2", 7.5, -2.75)),      # opaque gouache mark, ragged edge
    _disp("dry", 0.03, 2, 14, 15, streak=("0.004 0.26", 9, -3.9)),             # dry brush, more gaps
    _disp("wash", 0.008, 3, 70, 9, blur=3.3, streak=("0.0027 0.08", 4, -1.1)),  # wet, soft-edged sky stroke
    _disp("cloud", 0.0087, 4, 69, 2, blur=4.8, pad=25),
    _disp("cloudfine", 0.02, 3, 45, 6, blur=2.4, pad=25),
    _disp("cloudsoft", 0.0133, 3, 57, 8, blur=12, pad=25),
    _disp("wisp", 0.012, 4, 105, 12, blur=9, pad=25),
    _disp("haze", 0.006, 3, 120, 14, blur=20, pad=40),
    _disp("rough", 0.019, 2, 5, 3),                                            # hand wobble for inked shapes
    _disp("rough2", 0.033, 2, 12, 17),                                         # torn / organic silhouettes
    '<filter id="defocus" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="3"/></filter>',
    '<filter id="soft0" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>',
    '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14"/></filter>',
    '<filter id="soft2" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="34"/></filter>',
    '<filter id="soft3" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="70"/></filter>',
    _noise("grain", 0.9, 2, 5, 1.6, -0.3),                                     # paper tooth
    _noise("mottle", "0.004 0.006", 4, 31, 2.2, -0.6),                         # large uneven pigment
])


def boil(seed, amount=4.5):
    """Line boil for hand-drawn characters: change `seed` every 2 drawn frames. Returns (filter_def, filter_id)."""
    fid = f"boil{seed}"
    return _disp(fid, 0.04, 2, amount, 100 + seed, pad=20), fid


def radial(gid, stops, cx=.5, cy=.5, r=.5):
    """stops: (offset, colour, opacity)."""
    return (f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">' +
            "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops) + '</radialGradient>')


def linear(gid, stops, x1=0, y1=0, x2=0, y2=1):
    return (f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">' +
            "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops) + '</linearGradient>')


def stroke_shape(length, width, bend, n=9):
    """One brush mark along +x from the origin: quick attack, long tapering release."""
    p1 = (length * .5, bend)
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        x = 2 * (1 - t) * t * p1[0] + t * t * length
        y = 2 * (1 - t) * t * p1[1]
        dx = 2 * (1 - t) * p1[0] + 2 * t * (length - p1[0])
        dy = 2 * (1 - t) * p1[1] + 2 * t * (-p1[1])
        d = math.hypot(dx, dy) or 1
        hw = width / 2 * ((t / .14) ** .6 if t < .14 else 1) * (1 - (max(0, (t - .55) / .45) ** 1.5) * .8)
        left.append((x - dy / d * hw, y + dx / d * hw))
        right.append((x + dy / d * hw, y - dx / d * hw))
    return left + right[::-1]


def brush_layer(strokes, brush="bristle", step=15):
    """strokes: (x, y, angle_deg, length, width, bend, colour, opacity). Marks are bucketed by direction and drawn in a
    rotated group, so the brush filter's bristle streaks run along every mark. One call = one paint pass."""
    buckets = {}
    for s in strokes:
        buckets.setdefault(round(s[2] / step) * step, []).append(s)
    out = []
    for a, ss in buckets.items():
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        out.append(f'<g transform="rotate({a})" filter="url(#{brush})">')
        for (x, y, ang, ln, wd, bend, col, op) in ss:
            lx, ly = x * ca + y * sa, -x * sa + y * ca
            r = math.radians(ang - a)
            cr, sr = math.cos(r), math.sin(r)
            pts = [(lx + px * cr - py * sr, ly + px * sr + py * cr) for px, py in stroke_shape(ln, wd, bend)]
            out.append(f'<path d="M{"L".join(f"{px:.1f},{py:.1f}" for px, py in pts)}Z" fill="{col}" fill-opacity="{op:.2f}"/>')
        out.append('</g>')
    return "".join(out)


class ValueMap:
    """Composition control: how light the picture is at (x, y), 0 = darkest, 1 = lightest.
    grad=(y0, v0, y1, v1) is a vertical ramp; blobs are (cx, cy, rx, ry, delta) soft light or shadow masses."""

    def __init__(self, base=.35, blobs=(), grad=None):
        self.base, self.blobs, self.grad = base, list(blobs), grad

    def __call__(self, x, y):
        v = self.base
        if self.grad:
            y0, v0, y1, v1 = self.grad
            v = v0 + (v1 - v0) * max(0, min(1, (y - y0) / (y1 - y0)))
        for cx, cy, rx, ry, d in self.blobs:
            v += d * math.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))
        return max(0.0, min(1.0, v))


def paint(region, n, vmap, pal, size, rnd, angle=(0, 20), length=(3, 7), opacity=(.5, .9), bend=.2, noise=.1, accept=None, favour=0):
    """Scatter n marks inside region=(x0, y0, x1, y1). Colour = ramp `pal` (dark -> light) read at the value map, so marks
    gather into light and dark masses. angle is (mean, sd) or a function (x, y) -> degrees (a flow field).
    favour > 0 puts more marks where it is light, favour < 0 where it is dark."""
    x0, y0, x1, y1 = region
    out, tries = [], 0
    while len(out) < n and tries < n * 8:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if accept and not accept(x, y):
            continue
        v = vmap(x, y)
        if favour and rnd.random() > (1 - abs(favour)) + abs(favour) * (v if favour > 0 else 1 - v):
            continue
        w = rnd.uniform(*size)
        ln = w * rnd.uniform(*length)
        a = angle(x, y) if callable(angle) else rnd.gauss(*angle)
        out.append((x, y, a, ln, w, rnd.uniform(-bend, bend) * ln, jit(ramp(pal, v + rnd.gauss(0, noise)), rnd, 5), rnd.uniform(*opacity)))
    return out


def blade(bx, by, height, lean, width, sway=0.0, n=8):
    """Tapered grass blade / reed / hair strand as a path d-string. Animate by changing sway."""
    tipx, tipy = bx + lean + sway * 2.2, by - height
    cx, cy = bx + lean * .15 + sway * .5, by - height * .62
    left, right = [], []
    for k in range(n + 1):
        u = k / n
        x = (1 - u) ** 2 * bx + 2 * (1 - u) * u * cx + u * u * tipx
        y = (1 - u) ** 2 * by + 2 * (1 - u) * u * cy + u * u * tipy
        dx = 2 * (1 - u) * (cx - bx) + 2 * u * (tipx - cx)
        dy = 2 * (1 - u) * (cy - by) + 2 * u * (tipy - cy)
        d = math.hypot(dx, dy) or 1
        hw = width / 2 * (1 - u) ** .8
        left.append((x - dy / d * hw, y + dx / d * hw))
        right.append((x + dy / d * hw, y - dx / d * hw))
    return "M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in left + right[::-1]) + "Z"


def catmull(pts, closed=False):
    """Smooth path through hand-placed points."""
    n = len(pts)
    g = (lambda i: pts[i % n]) if closed else (lambda i: pts[max(0, min(n - 1, i))])
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = g(i - 1), g(i), g(i + 1), g(i + 2)
        d += (f"C{p1[0] + (p2[0] - p0[0]) / 6:.1f},{p1[1] + (p2[1] - p0[1]) / 6:.1f} "
              f"{p2[0] - (p3[0] - p1[0]) / 6:.1f},{p2[1] - (p3[1] - p1[1]) / 6:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return d + ("Z" if closed else "")


# ------------------------------------------------------------- perspective ---
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _norm(a): l = math.sqrt(_dot(a, a)) or 1; return (a[0] / l, a[1] / l, a[2] / l)


class Cam:
    """Pinhole camera so interiors, furniture and vehicles are constructed, not guessed.
    World axes: x right, y up, z away from the viewer. roll (degrees) gives a dutch angle."""

    def __init__(self, pos, target, fov=50, roll=0, cx=W / 2, cy=H / 2):
        self.pos, self.cx, self.cy = pos, cx, cy
        self.f = _norm(_sub(target, pos))
        self.r = _norm(_cross((0, 1, 0), self.f))
        self.u = _cross(self.f, self.r)
        self.focal = (H / 2) / math.tan(math.radians(fov) / 2)
        self.cr, self.sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))

    def p(self, pt):
        """World point -> (sx, sy, depth), or None if behind the camera."""
        d = _sub(pt, self.pos)
        z = _dot(d, self.f)
        if z < .05:
            return None
        x, y = self.focal * _dot(d, self.r) / z, -self.focal * _dot(d, self.u) / z
        return (self.cx + x * self.cr - y * self.sr, self.cy + x * self.sr + y * self.cr, z)

    def poly(self, pts3, pad=300):
        """d-string for a 3D polygon. It is clipped where it passes behind the camera and to the frame plus `pad` px,
        so long shadows and ground planes that run past the viewer still draw. None if nothing is visible."""
        near, vis = .06, []
        zs = [_dot(_sub(q, self.pos), self.f) for q in pts3]
        for i, q in enumerate(pts3):
            j = (i + 1) % len(pts3)
            if zs[i] >= near:
                vis.append(q)
            if (zs[i] >= near) != (zs[j] >= near):
                vis.append(_add(q, _mul(_sub(pts3[j], q), (near - zs[i]) / (zs[j] - zs[i]))))
        s = [self.p(q)[:2] for q in vis]
        for axis, lim, keep_below in ((0, -pad, False), (0, W + pad, True), (1, -pad, False), (1, H + pad, True)):
            out = []
            for i, a in enumerate(s):
                b = s[(i + 1) % len(s)]
                ina, inb = (a[axis] <= lim) == keep_below, (b[axis] <= lim) == keep_below
                if ina:
                    out.append(a)
                if ina != inb:
                    t = (lim - a[axis]) / (b[axis] - a[axis])
                    out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            s = out
        if len(s) < 3:
            return None
        return "M" + "L".join(f"{q[0]:.1f},{q[1]:.1f}" for q in s) + "Z"


def quad(origin, u, v):
    """Corners of the 3D parallelogram origin + a*u + b*v."""
    return [origin, _add(origin, u), _add(_add(origin, u), v), _add(origin, v)]


def box_faces(cam, lo, hi, inside=False):
    """Visible faces of an axis-aligned box as {name: (origin, u, v)}, far faces first.
    inside=True returns the inner faces (a room seen from within)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    dx, dy, dz = (x1 - x0, 0, 0), (0, y1 - y0, 0), (0, 0, z1 - z0)
    faces = {"bottom": ((x0, y0, z0), dx, dz, (0, -1, 0)), "top": ((x0, y1, z0), dx, dz, (0, 1, 0)),
             "front": ((x0, y0, z0), dx, dy, (0, 0, -1)), "back": ((x0, y0, z1), dx, dy, (0, 0, 1)),
             "left": ((x0, y0, z0), dz, dy, (-1, 0, 0)), "right": ((x1, y0, z0), dz, dy, (1, 0, 0))}
    vis = []
    for name, (o, u, v, nrm) in faces.items():
        centre = _add(o, _add(_mul(u, .5), _mul(v, .5)))
        facing = _dot(nrm, _sub(cam.pos, centre)) > 0
        if facing != inside:
            vis.append((-_dot(_sub(centre, cam.pos), cam.f), name, (o, u, v)))
    return {name: f for _, name, f in sorted(vis)}


def plane_marks(cam, face, n, vmap, pal, rnd, size=(.02, .05), length=(3, 8), along="u", opacity=(.5, .9), jitter=5, noise=.1, bend=.12):
    """Brush marks lying on a 3D face (origin, u, v), drawn in perspective: they follow the surface direction and
    shrink with distance (wood grain, floorboards, wall texture, cloth). size is in world units; vmap is in screen space."""
    o, u, v = face
    d, perp = (_norm(u), _norm(v)) if along == "u" else (_norm(v), _norm(u))
    out = []
    for _ in range(n):
        P = _add(o, _add(_mul(u, rnd.random()), _mul(v, rnd.random())))
        w = rnd.uniform(*size)
        ln = w * rnd.uniform(*length)
        s0, s1, s2 = cam.p(P), cam.p(_add(P, _mul(d, ln))), cam.p(_add(P, _mul(perp, w)))
        if not (s0 and s1 and s2):
            continue
        L = math.hypot(s1[0] - s0[0], s1[1] - s0[1]) or 1
        wd = abs((s1[0] - s0[0]) * (s2[1] - s0[1]) - (s1[1] - s0[1]) * (s2[0] - s0[0])) / L
        ang = math.degrees(math.atan2(s1[1] - s0[1], s1[0] - s0[0])) + rnd.gauss(0, jitter)
        col = jit(ramp(pal, vmap(s0[0], s0[1]) + rnd.gauss(0, noise)), rnd, 5)
        out.append((s0[0], s0[1], ang, L, max(1.5, wd), rnd.uniform(-bend, bend) * L, col, rnd.uniform(*opacity)))
    return out


# ---------------------------------------- depth: tones, tints, shade, shadow ---
def tint(c, t, light="#fff1dc"):
    """Lighter and toward the colour of the light (hue + light)."""
    return mix(c, light, t)


def shade(c, t, dark="#151a3a"):
    """Darker and toward the colour of the shadow (hue + dark). The dark is a tinted near-black, never #000."""
    return mix(c, dark, t)


def tone(c, t):
    """Greyer at the same lightness (hue + grey): for distance, overcast light and things that should recede."""
    r, g, b = _rgb(c)
    y = .299 * r + .587 * g + .114 * b
    return mix(c, _hex([y, y, y]), t)


def form_ramp(base, light="#ffe2b8", shadow="#1a2150"):
    """Seven-step modelling ramp for one local colour, dark -> light: core shadow, shadow, halftone, local, light,
    lighter, highlight. Light steps lean to the light's colour and dark steps to the shadow's, so hue shifts with value
    as it does in paint. Use it as `pal` for paint() and plane_marks()."""
    return [shade(base, .8, shadow), shade(base, .55, shadow), shade(tone(base, .2), .28, shadow), base,
            tint(base, .3, light), tint(base, .58, light), tint(base, .86, light)]


def aerial(c, depth, air="#b9c3dc", strength=1.0):
    """Atmospheric perspective. depth 0 = near, 1 = far: distant colours lose contrast and saturation and take the
    colour of the air in front of them."""
    k = max(0.0, min(1.0, depth)) * strength
    return mix(tone(c, .5 * k), air, .78 * k)


def lambert(cam, face, light, ambient=.2):
    """Brightness 0..1 of a constructed face (origin, u, v) under a directional light (the direction it travels).
    Faces turned away from the light keep only `ambient`."""
    o, u, v = face
    n = _norm(_cross(u, v))
    if _dot(n, _sub(cam.pos, _add(o, _add(_mul(u, .5), _mul(v, .5))))) < 0:
        n = _mul(n, -1)
    return ambient + (1 - ambient) * max(0.0, _dot(n, _mul(_norm(light), -1)))


def face_value(brightness, vmap=None, swing=.3):
    """Value function for paint passes on one face: its lambert brightness, modulated a little by the shot's value map."""
    return lambda x, y: max(0.0, min(1.0, brightness + ((vmap(x, y) - .5) * swing if vmap else 0)))


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]


def cast(pts3, light, y=0.0):
    """Where world points land on the horizontal plane at height y when carried along the light: (x, z) pairs."""
    L = _norm(light)
    return [(p[0] + L[0] * (p[1] - y) / -L[1], p[2] + L[2] * (p[1] - y) / -L[1]) for p in pts3]


def shadow(cam, pts3, light, colour="#2f4fa0", opacity=.75, y=0.0, soft="soft", core=.62):
    """Cast shadow on the ground of a convex solid given its corner points (include the corners that touch the ground).
    A multiply layer: a firm core plus a blurred penumbra. The colour is the sky's, never grey or black."""
    d = cam.poly([(x, y + .003, z) for x, z in _hull(cast(pts3, light, y))])
    if not d:
        return ""
    return (f'<g style="mix-blend-mode:multiply"><path d="{d}" fill="{colour}" fill-opacity="{opacity * core:.2f}" filter="url(#rough2)"/>'
            f'<path d="{d}" fill="{colour}" fill-opacity="{opacity * (1 - core):.2f}" filter="url(#{soft})"/></g>')


def contact(cam, p, rx, rz, colour="#151a3a", opacity=.6, soft="soft0"):
    """Contact shadow: the small dark pool where something meets the ground. p = ground point, rx / rz in metres."""
    d = cam.poly([(p[0] + rx * math.cos(a * math.pi / 8), p[1] + .004, p[2] + rz * math.sin(a * math.pi / 8)) for a in range(16)])
    return f'<path d="{d}" fill="{colour}" fill-opacity="{opacity}" filter="url(#{soft})" style="mix-blend-mode:multiply"/>' if d else ""


def occlusion(cam, a, b, width=.25, colour="#151a3a", opacity=.5, soft="soft0"):
    """Ambient occlusion along the 3D edge a-b where two surfaces meet (under eaves, wall to ground, inside corners).
    width in metres. Drawn as a blurred strip, not a line, so it always has an area to filter."""
    p, q = cam.p(a), cam.p(b)
    if not (p and q):
        return ""
    w = max(3.0, cam.focal / ((p[2] + q[2]) / 2) * width)
    L = math.hypot(q[0] - p[0], q[1] - p[1]) or 1
    nx, ny = -(q[1] - p[1]) / L * w / 2, (q[0] - p[0]) / L * w / 2
    d = f"M{p[0] + nx:.1f},{p[1] + ny:.1f}L{q[0] + nx:.1f},{q[1] + ny:.1f}L{q[0] - nx:.1f},{q[1] - ny:.1f}L{p[0] - nx:.1f},{p[1] - ny:.1f}Z"
    return f'<path d="{d}" fill="{colour}" fill-opacity="{opacity}" filter="url(#{soft})" style="mix-blend-mode:multiply"/>'


def model(d, uid, bbox, toward=(-1, -1), shadow_col="#1a2150", light_col="#ffe2b8", shadow=.6, light=.4, reflect=.3, rim=0.0, rim_w=7):
    """Form modelling for any closed path d that should look round: shade grows away from the light, peaks at a core
    shadow and eases off toward the far edge (reflected light); tint grows toward the light; optional rim light on the
    lit edge. `toward` is the screen direction from the form to the light. `uid` must be unique in the frame.
    Draw the form's own fill and texture first, then this on top."""
    x0, y0, x1, y1 = bbox
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 or 1
    k = math.hypot(*toward) or 1
    a, b = (cx + toward[0] / k * r, cy + toward[1] / k * r), (cx - toward[0] / k * r, cy - toward[1] / k * r)

    def grad(gid, stops):
        return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}">' +
                "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{op}"/>' for o, c, op in stops) + '</linearGradient>')
    box = f'x="{x0 - 20:.0f}" y="{y0 - 20:.0f}" width="{x1 - x0 + 40:.0f}" height="{y1 - y0 + 40:.0f}"'
    s = (f'<clipPath id="{uid}c"><path d="{d}"/></clipPath>' +
         grad(uid + "s", [(0, shadow_col, 0), (.36, shadow_col, 0), (.72, shadow_col, shadow), (1, shadow_col, shadow * (1 - reflect))]) +
         grad(uid + "l", [(0, light_col, light), (.5, light_col, 0), (1, light_col, 0)]) +
         grad(uid + "m", [(0, "#fff", 1), (.5, "#000", 1), (1, "#000", 1)]) +
         f'<mask id="{uid}k" maskUnits="userSpaceOnUse" {box}><rect {box} fill="url(#{uid}m)"/></mask>'
         f'<g clip-path="url(#{uid}c)"><rect {box} fill="url(#{uid}s)"/><rect {box} fill="url(#{uid}l)"/>')
    if rim:
        s += f'<path d="{d}" fill="none" stroke="{light_col}" stroke-opacity="{rim}" stroke-width="{rim_w * 2}" stroke-linejoin="round" mask="url(#{uid}k)"/>'
    return s + '</g>'


def veil(uid, y0, y1, colour="#c9cfe6", top=0.0, bottom=.55):
    """A band of air between two depth planes: clear at y0, densest at y1. Put one behind each nearer plane."""
    return linear(uid, [(0, colour, top), (1, colour, bottom)]) + f'<rect y="{y0}" width="{W}" height="{y1 - y0}" fill="url(#{uid})"/>'


def grade(shadows="#14244c", lights="#ffe6c4", amount=.2):
    """Split-tone grade over the whole frame: darks lean to one tint, lights to its opposite. Ties the layers together."""
    return (f'<rect width="{W}" height="{H}" fill="{shadows}" style="mix-blend-mode:screen" opacity="{amount}"/>'
            f'<rect width="{W}" height="{H}" fill="{lights}" style="mix-blend-mode:multiply" opacity="{amount}"/>')


# ------------------------------------------------------- character rigging ---
class Rig:
    """Forward-kinematics puppet. bones = {name: (parent or None, length)} listed parent-first.
    A pose is {name: angle_deg}; angle 0 points straight down, measured relative to the parent bone."""

    def __init__(self, bones):
        self.bones = bones

    def solve(self, root, pose, flip=1):
        """-> {name: (start_xy, end_xy, absolute_angle)}. flip=-1 mirrors the character."""
        pts = {}
        for name, (parent, length) in self.bones.items():
            start, base = (root, 0) if parent is None else (pts[parent][1], pts[parent][2])
            a = base + pose.get(name, 0)
            pts[name] = (start, (start[0] + flip * length * math.sin(math.radians(a)), start[1] + length * math.cos(math.radians(a))), a)
        return pts


def ease(t, kind="inout"):
    t = max(0.0, min(1.0, t))
    return {"linear": t, "in": t * t, "out": 1 - (1 - t) ** 2, "inout": t * t * (3 - 2 * t), "hold": 0.0}[kind]


def tween(keys, f):
    """Pose-to-pose animation. keys = [(frame, pose_dict, ease_kind_into_next), ...] sorted by frame.
    Returns the pose at drawn frame f; missing joints default to 0. Author every key pose by hand."""
    if f <= keys[0][0]:
        return dict(keys[0][1])
    for (f0, p0, e), (f1, p1, _) in zip(keys, keys[1:]):
        if f <= f1:
            t = ease((f - f0) / (f1 - f0), e)
            return {k: p0.get(k, 0) + (p1.get(k, 0) - p0.get(k, 0)) * t for k in set(p0) | set(p1)}
    return dict(keys[-1][1])


def limb(points, width, colour, outline=None, ow=3):
    """Round-capped limb through joint positions (use the end points from Rig.solve)."""
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    s = ""
    if outline:
        s += f'<path d="{d}" fill="none" stroke="{outline}" stroke-width="{width + 2 * ow}" stroke-linecap="round" stroke-linejoin="round"/>'
    return s + f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'


# ---------------------------------------------------------- hand lettering ---
class S(list):
    """A stroke that should be drawn as a smooth curve through its points."""


def _arc(cx, cy, rx, ry, a0, a1, n=12):
    return S((cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1))


_BOWL = S([(0, 0), (.3, 0), (.45, .14), (.45, .38), (.3, .52), (0, .52)])
GLYPH = {   # (advance width, strokes) on a unit square: y = 0 cap height, y = 1 baseline
    "A": (.6, [[(0, 1), (.3, 0), (.6, 1)], [(.12, .62), (.48, .62)]]),
    "B": (.5, [[(0, 0), (0, 1)], S([(0, 0), (.28, 0), (.42, .12), (.42, .34), (.28, .47), (0, .48)]), S([(0, .48), (.32, .5), (.48, .64), (.48, .86), (.32, 1), (0, 1)])]),
    "C": (.55, [_arc(.3, .5, .3, .5, -50, -310)]),
    "D": (.55, [[(0, 0), (0, 1)], S([(0, 0), (.25, .02), (.45, .2), (.5, .5), (.45, .8), (.25, .98), (0, 1)])]),
    "E": (.48, [[(.45, 0), (0, 0), (0, 1), (.47, 1)], [(0, .5), (.36, .5)]]),
    "F": (.46, [[(.45, 0), (0, 0), (0, 1)], [(0, .5), (.34, .5)]]),
    "G": (.62, [_arc(.3, .5, .3, .5, -50, -330), [(.34, .55), (.6, .55), (.6, .82)]]),
    "H": (.52, [[(0, 0), (0, 1)], [(.5, 0), (.5, 1)], [(0, .5), (.5, .5)]]),
    "I": (.1, [[(.05, 0), (.05, 1)]]),
    "J": (.44, [S([(.4, 0), (.4, .74), (.33, .93), (.19, 1), (.04, .88)])]),
    "K": (.5, [[(0, 0), (0, 1)], [(.45, 0), (0, .58)], [(.16, .42), (.48, 1)]]),
    "L": (.44, [[(0, 0), (0, 1), (.42, 1)]]),
    "M": (.68, [[(0, 1), (.04, 0), (.33, .7), (.62, 0), (.66, 1)]]),
    "N": (.52, [[(0, 1), (0, 0), (.5, 1), (.5, 0)]]),
    "O": (.6, [_arc(.3, .5, .3, .5, -90, 270, 16)]),
    "P": (.48, [[(0, 0), (0, 1)], _BOWL]),
    "Q": (.62, [_arc(.3, .5, .3, .5, -90, 270, 16), [(.36, .72), (.6, 1.05)]]),
    "R": (.5, [[(0, 0), (0, 1)], _BOWL, [(.2, .52), (.48, 1)]]),
    "S": (.45, [S([(.42, .1), (.28, 0), (.1, .04), (.02, .2), (.1, .42), (.32, .56), (.42, .76), (.34, .95), (.16, 1), (0, .9)])]),
    "T": (.56, [[(0, 0), (.56, 0)], [(.28, 0), (.28, 1)]]),
    "U": (.52, [S([(0, 0), (0, .7), (.08, .92), (.25, 1), (.42, .92), (.5, .7), (.5, 0)])]),
    "V": (.56, [[(0, 0), (.28, 1), (.56, 0)]]),
    "W": (.78, [[(0, 0), (.18, 1), (.38, .3), (.58, 1), (.76, 0)]]),
    "X": (.5, [[(0, 0), (.5, 1)], [(.5, 0), (0, 1)]]),
    "Y": (.54, [[(0, 0), (.27, .5), (.54, 0)], [(.27, .5), (.27, 1)]]),
    "Z": (.52, [[(0, 0), (.5, 0), (0, 1), (.52, 1)]]),
    "0": (.5, [_arc(.25, .5, .25, .5, -90, 270, 16)]),
    "1": (.26, [[(.03, .22), (.2, 0), (.2, 1)]]),
    "2": (.5, [S([(.02, .2), (.14, .03), (.3, 0), (.44, .1), (.46, .3), (.3, .56), (0, 1)]), [(0, 1), (.5, 1)]]),
    "3": (.46, [S([(.03, .12), (.2, 0), (.4, .1), (.42, .32), (.2, .48)]), S([(.2, .48), (.44, .62), (.44, .86), (.22, 1), (0, .88)])]),
    "4": (.5, [[(.36, 1), (.36, 0), (0, .68), (.5, .68)]]),
    "5": (.46, [[(.42, 0), (.06, 0), (.03, .44)], S([(.03, .44), (.24, .38), (.44, .52), (.45, .8), (.26, 1), (0, .9)])]),
    "6": (.46, [S([(.4, .04), (.2, .1), (.06, .4), (.03, .72), (.14, .95), (.3, 1), (.44, .86), (.44, .64), (.3, .5), (.12, .56), (.04, .72)])]),
    "7": (.46, [[(0, 0), (.46, 0), (.16, 1)]]),
    "8": (.46, [_arc(.23, .25, .19, .25, -90, 270), _arc(.23, .75, .23, .25, -90, 270)]),
    "9": (.46, [S([(.42, .3), (.3, .48), (.14, .5), (.02, .34), (.04, .12), (.2, 0), (.36, .06), (.43, .3), (.42, .6), (.3, .9), (.1, 1)])]),
    ".": (.1, [[(.04, .97), (.05, 1)]]), ",": (.12, [[(.08, .94), (.02, 1.16)]]), "'": (.1, [[(.06, 0), (.03, .2)]]),
    "!": (.1, [[(.05, 0), (.05, .7)], [(.05, .97), (.05, 1)]]), ":": (.1, [[(.05, .34), (.05, .37)], [(.05, .97), (.05, 1)]]),
    "?": (.42, [S([(.02, .16), (.14, .02), (.32, .04), (.4, .22), (.28, .42), (.2, .55), (.2, .7)]), [(.2, .97), (.2, 1)]]),
    "-": (.38, [[(.04, .55), (.34, .55)]]),
}


def lettering(lines, cx, y0, cap=46, colour="#f7f0e6", weight=None, gap=1.5, seed=71, reveal=1.0, align="center"):
    """Hand-lettered caption from the stroke font above (upper case, digits, basic punctuation).
    y0 = baseline of the first line. reveal 0..1 writes the text on letter by letter.
    Returns (svg, (x0, y0, x1, y1)) so the caption can be checked against SAFE."""
    rnd = random.Random(seed)
    weight = weight or cap * .14
    lines = [ln.upper() for ln in lines]
    total_letters = sum(1 for ln in lines for ch in ln if ch in GLYPH)
    show, count = round(total_letters * reveal), 0
    o = [f'<g fill="none" stroke="{colour}" stroke-width="{weight:.1f}" stroke-linecap="round" stroke-linejoin="round" filter="url(#rough)">']
    bx0, bx1 = W, 0
    for li, line in enumerate(lines):
        widths = [(GLYPH[ch][0] if ch in GLYPH else .36) + .24 for ch in line]
        total = sum(widths) * cap
        x = {"center": cx - total / 2, "left": cx, "right": cx - total}[align]
        bx0, bx1 = min(bx0, x), max(bx1, x + total)
        base = y0 + li * cap * gap
        for ch, wd in zip(line, widths):
            if ch in GLYPH:
                s, dy, rot = cap * rnd.uniform(.93, 1.07), rnd.uniform(-.07, .07) * cap, rnd.uniform(-3.5, 3.5)
                jig = [[(px * s + rnd.uniform(-.026, .026) * cap, py * s + rnd.uniform(-.026, .026) * cap) for px, py in st] for st in GLYPH[ch][1]]
                if count < show:
                    o.append(f'<g transform="translate({x:.1f},{base - s + dy:.1f}) rotate({rot:.1f})">')
                    for st, pts in zip(GLYPH[ch][1], jig):
                        d = catmull(pts) if isinstance(st, S) else "M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
                        o.append(f'<path d="{d}"/>')
                    o.append('</g>')
                count += 1
            x += wd * cap
    o.append('</g>')
    return "".join(o), (bx0, y0 - cap * 1.1, bx1, y0 + (len(lines) - 1) * cap * gap + cap * .2)


def in_safe(bbox):
    x0, y0, x1, y1 = bbox
    return x0 >= SAFE["side"] and x1 <= W - SAFE["side"] and y0 >= SAFE["top"] and y1 <= H - SAFE["bottom"]


# ------------------------------------------------ supplied illustration art ---
def embed_image(path, x=0, y=0, w=W, h=H, opacity=1, extra=""):
    """Place a supplied raster illustration (PNG / JPG / WebP) as a layer, untouched."""
    p = pathlib.Path(path)
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}[p.suffix.lower().lstrip(".")]
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<image href="data:{mime};base64,{b64}" x="{x}" y="{y}" width="{w}" height="{h}" opacity="{opacity}" preserveAspectRatio="xMidYMid slice" {extra}/>'


# ------------------------------------------------------------------ finish ---
def finish(vignette=.5, mottle=.2, grain=.1):
    """Final unifying pass over the whole frame: vignette, uneven pigment, paper tooth (also prevents banding)."""
    return (radial("_vig", [(.55, "#0a0f12", 0), (1, "#0a0f12", vignette)], cy=.46, r=.75) +
            f'<rect width="{W}" height="{H}" fill="url(#_vig)"/>'
            f'<rect width="{W}" height="{H}" filter="url(#mottle)" style="mix-blend-mode:soft-light" opacity="{mottle}"/>'
            f'<rect width="{W}" height="{H}" filter="url(#grain)" style="mix-blend-mode:overlay" opacity="{grain}"/>')


def finish_cached(r, vignette=.5, mottle=.2, grain=.1):
    """finish() with the noise fields rasterised once by Renderer r. Use this inside frame functions: it is much faster."""
    v = r.layer("fin_vig", radial("_vig", [(.55, "#0a0f12", 0), (1, "#0a0f12", vignette)], cy=.46, r=.75) + f'<rect width="{W}" height="{H}" fill="url(#_vig)"/>')
    m = r.layer("fin_mottle", f'<rect width="{W}" height="{H}" filter="url(#mottle)"/>')
    g = r.layer("fin_grain", f'<rect width="{W}" height="{H}" filter="url(#grain)"/>')
    return v + f'<g style="mix-blend-mode:soft-light" opacity="{mottle}">{m}</g><g style="mix-blend-mode:overlay" opacity="{grain}">{g}</g>'


# ------------------------------------------------------- render and encode ---
class Renderer:
    """Rasterises SVG with headless Chromium. scale=2 supersamples to 2160x3840, which is then downscaled for a clean
    1080x1920 file or kept as a 4K master. Static layers are rendered once and reused."""

    def __init__(self, workdir, scale=2):
        from playwright.sync_api import sync_playwright
        self.dir = pathlib.Path(workdir).resolve()
        (self.dir / "cache").mkdir(parents=True, exist_ok=True)
        (self.dir / "frames").mkdir(exist_ok=True)
        self.scale = scale
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self.page = self._browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)

    def _shot(self, body, path, alpha):
        html = self.dir / "_page.html"
        bg = "transparent" if alpha else "#000"
        html.write_text(f'<html><body style="margin:0;background:{bg}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                        f'width="{W}" height="{H}"><defs>{BRUSHES}</defs>{body}</svg></body></html>')
        self.page.goto(html.as_uri(), wait_until="load")
        self.page.wait_for_timeout(60)
        self.page.screenshot(path=str(path), omit_background=alpha, clip={"x": 0, "y": 0, "width": W, "height": H})

    def layer(self, name, body):
        """Render a static layer once (transparent PNG). Returns an <image> tag to place in every frame."""
        key = hashlib.sha1((body + str(self.scale)).encode()).hexdigest()[:12]
        p = self.dir / "cache" / f"{name}_{key}.png"
        if not p.exists():
            self._shot(body, p, True)
        return f'<image href="cache/{p.name}" x="0" y="0" width="{W}" height="{H}"/>'

    def still(self, body, path):
        self._shot(body, path, False)

    def raster(self, svg_path, out, w, h):
        """Rasterise a supplied SVG file on its own (so its ids cannot collide with the brush filters) to a transparent
        PNG of w x h px times the render scale. Place the result with embed_image."""
        html = self.dir / "_art.html"
        html.write_text(f'<html><body style="margin:0;background:transparent"><img src="{pathlib.Path(svg_path).resolve().as_uri()}" '
                        f'style="width:{w}px;height:{h}px;object-fit:contain"></body></html>')
        self.page.goto(html.as_uri(), wait_until="load")
        self.page.wait_for_timeout(60)
        self.page.screenshot(path=str(out), omit_background=True, clip={"x": 0, "y": 0, "width": w, "height": h})

    def frames(self, frame_fn, stop, start=0):
        """frame_fn(f) -> SVG body for drawn frame f, for f in start..stop-1. Identical frames (holds) are rendered once
        and copied. Returns the number of unique frames rendered. Split start/stop across two processes to use two cores."""
        seen = {}
        for f in range(start, stop):
            body = frame_fn(f)
            key = hashlib.sha1(body.encode()).hexdigest()
            out = self.dir / "frames" / f"fr_{f:05d}.png"
            if key in seen:
                shutil.copy(seen[key], out)
            else:
                self._shot(body, out, False)
                seen[key] = out
        return len(seen)

    def close(self):
        self._browser.close()
        self._pw.stop()


def encode(frames_dir, out, drawn_fps=15, delivery_fps=30, size=(W, H), crf=14):
    """Silent H.264 MP4. Each drawn frame is held delivery_fps / drawn_fps output frames (15 -> 30 = on twos)."""
    assert delivery_fps % drawn_fps == 0, "delivery fps must be a whole multiple of the drawn fps"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(drawn_fps), "-i", f"{frames_dir}/fr_%05d.png",
                    "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos:out_color_matrix=bt709:out_range=tv,fps={delivery_fps},format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-profile:v", "high",
                    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    "-movflags", "+faststart", "-an", str(out)], check=True)


def probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return dict(width=v["width"], height=v["height"], fps=v["r_frame_rate"], frames=int(v.get("nb_frames", 0)), codec=v["codec_name"],
                pix_fmt=v["pix_fmt"], duration=float(j["format"]["duration"]), size_mb=round(int(j["format"]["size"]) / 1e6, 2),
                audio=any(s["codec_type"] == "audio" for s in j["streams"]))


# ---------------------------------------------------------------------- QC ---
def contact_sheet(frames_dir, out, every=5, cols=8, width=270):
    from PIL import Image, ImageDraw
    files = sorted(pathlib.Path(frames_dir).glob("fr_*.png"))[::every]
    th = round(width * H / W)
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * width, rows * th), "#000")
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB").resize((width, th), Image.LANCZOS)
        ImageDraw.Draw(im).text((6, 4), f.stem[3:], fill="#ffff00")
        sheet.paste(im, ((i % cols) * width, (i // cols) * th))
    sheet.save(out)


def safe_overlay(frame_png, out):
    """Draw the platform-UI zones over a frame to check captions and focal points by eye."""
    from PIL import Image, ImageDraw
    im = Image.open(frame_png).convert("RGBA").resize((W, H), Image.LANCZOS)
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for box in ((0, 0, W, SAFE["top"]), (0, H - SAFE["bottom"], W, H), (0, 0, SAFE["side"], H), (W - SAFE["side"], 0, W, H)):
        d.rectangle(box, fill=(255, 0, 80, 90))
    Image.alpha_composite(im, ov).convert("RGB").save(out)


def flicker(frames_dir, box, f0, f1):
    """Mean frame-to-frame change inside box=(x0, y0, x1, y1) in 1080x1920 coordinates. A held background should be ~0."""
    import numpy as np
    from PIL import Image
    files = sorted(pathlib.Path(frames_dir).glob("fr_*.png"))[f0:f1 + 1]
    prev, tot = None, []
    for f in files:
        a = np.asarray(Image.open(f).convert("L").resize((W // 2, H // 2)).crop(tuple(v // 2 for v in box))).astype(int)
        if prev is not None:
            tot.append(float(abs(a - prev).mean()))
        prev = a
    return sum(tot) / max(1, len(tot))


# ------------------------------------------------------ reference analysis ---
def analyze_reference(video, outdir, width=360):
    """Break a reference video into shots and measure it: cuts, duration, how much of the frame moves, palette.
    Writes numbered contact sheets to outdir for reading by eye. Returns {"info": ..., "shots": [...]}."""
    import numpy as np
    from PIL import Image
    out = pathlib.Path(outdir)
    (out / "f").mkdir(parents=True, exist_ok=True)
    info = probe(video)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"scale={width}:-2", str(out / "f" / "fr_%05d.png")], check=True)
    files = sorted((out / "f").glob("fr_*.png"))
    A = [np.asarray(Image.open(f).convert("RGB")).astype(np.int16) for f in files]
    d = [0.0] + [float(np.abs(A[i] - A[i - 1]).mean()) for i in range(1, len(A))]
    med = sorted(d)[len(d) // 2]
    cuts = [0] + [i for i in range(1, len(d)) if d[i] > max(12.0, 8 * med + 6)] + [len(A)]
    num, den = (int(x) for x in info["fps"].split("/"))
    fps = num / den
    shots = []
    for s, e in zip(cuts, cuts[1:]):
        moved = np.zeros(A[0].shape[:2], bool)
        for i in range(s + 1, e):
            moved |= np.abs(A[i] - A[i - 1]).max(axis=2) > 24
        q = Image.open(files[(s + e) // 2]).convert("RGB").quantize(8)
        pal, cnt = q.getpalette()[:24], sorted(q.getcolors(), reverse=True)
        shots.append(dict(first=s, last=e - 1, start_s=round(s / fps, 2), seconds=round((e - s) / fps, 2), moving_pct=round(float(moved.mean()) * 100, 1),
                          still=bool(moved.mean() < .002), palette=[f"#{pal[i * 3]:02x}{pal[i * 3 + 1]:02x}{pal[i * 3 + 2]:02x}" for _, i in cnt]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    "scale=240:-2,drawtext=text='%{n}':x=6:y=6:fontsize=26:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=9x3", str(out / "sheet_%02d.png")], check=True)
    return dict(info=info, shots=shots)


# ---------------------------------------------------- self-test / example ---
def _selftest(work="reel_selftest"):
    """A complete miniature production: also the reference example of how a scene file is organised."""
    rnd = random.Random(1)
    r = Renderer(work, scale=1)
    cam = Cam(pos=(0, 1.6, -4), target=(0, .6, 2), fov=60)
    vm = ValueMap(base=.2, grad=(900, .55, H, .15), blobs=[(540, 1150, 360, 220, .35)])
    sky = (linear("sk", [(0, "#39486a", 1), (1, "#d9a48f", 1)]) + f'<rect width="{W}" height="1000" fill="url(#sk)"/>' +
           brush_layer(paint((-200, 0, W, 980), 90, ValueMap(grad=(0, .2, 980, .9)), ["#34425f", "#6f6f8a", "#c9988c", "#e9bda8"], (60, 130), rnd, angle=(0, 6), length=(4, 8), opacity=(.2, .45)), "wash"))
    floor = ((-3, 0, -1), (6, 0, 0), (0, 0, 9))                                    # origin, u, v of the ground plane
    ground = (f'<rect y="960" width="{W}" height="960" fill="#1c2a2c"/>' +
              brush_layer(plane_marks(cam, floor, 500, vm, ["#101a1c", "#22363a", "#3f5f58", "#7da087", "#d9e2b0"], rnd, size=(.05, .16), length=(3, 7), along="u"), "bristle"))
    light = (.62, -.36, -.7)                                                       # direction the light travels
    wood = form_ramp("#8b5e3c")
    faces = box_faces(cam, (-.6, 0, 1.4), (.6, .9, 2.4))
    lit = {n: lambert(cam, f, light) for n, f in faces.items()}
    assert max(lit.values()) - min(lit.values()) > .2, lit                         # faces must separate into light and shade
    corners = [(x, y, z) for x in (-.6, .6) for y in (0, .9) for z in (1.4, 2.4)]
    crate = (shadow(cam, corners, light) + contact(cam, (0, 0, 1.9), .8, .6) +
             "".join(f'<path d="{cam.poly(quad(*f))}" fill="{ramp(wood, lit[n] * .8)}" stroke="#191d20" stroke-width="5" stroke-linejoin="round" filter="url(#rough)"/>'
                     for n, f in faces.items()) + occlusion(cam, (-.6, .03, 1.4), (.6, .03, 1.4)))
    ball_d = catmull([(820 + 70 * math.cos(a * math.pi / 6), 1210 + 70 * math.sin(a * math.pi / 6)) for a in range(12)], closed=True)
    ball = f'<path d="{ball_d}" fill="{aerial("#b4482e", .15)}"/>' + model(ball_d, "ball", (750, 1140, 890, 1280), toward=(-1, -.6), rim=.6)
    static = r.layer("static", sky + veil("air", 700, 1000) + ground + crate + ball)
    fin = grade() + finish_cached(r)
    arm = Rig({"upper": (None, 90), "fore": ("upper", 80)})
    keys = [(0, dict(upper=150, fore=20), "inout"), (3, dict(upper=205, fore=-40), "hold"), (5, dict(upper=205, fore=-40), "inout")]
    top = cam.p((0, .9, 1.9))

    def frame(f):
        b = arm.solve((top[0], top[1]), tween(keys, f))
        fd, fid = boil(f // 2)
        txt, bbox = lettering(["SELF TEST 0123", "QUICK, BROWN FOX?"], W / 2, 420, cap=48, reveal=min(1, (f + 1) / 3))
        assert in_safe(bbox), bbox
        return (static + f'<defs>{fd}</defs><g filter="url(#{fid})">' + limb([b["upper"][0], b["upper"][1], b["fore"][1]], 22, "#f2ead8", "#191d20") + '</g>' + txt + fin)

    unique = r.frames(frame, 6)
    r.close()
    out = pathlib.Path(work) / "selftest.mp4"
    encode(pathlib.Path(work) / "frames", out)
    info = probe(out)
    contact_sheet(pathlib.Path(work) / "frames", pathlib.Path(work) / "sheet.png", every=1, cols=6)
    safe_overlay(pathlib.Path(work) / "frames" / "fr_00005.png", pathlib.Path(work) / "safe.png")
    assert (info["width"], info["height"], info["fps"], info["frames"], info["audio"]) == (W, H, "30/1", 12, False), info
    assert unique == 5, unique                     # frames 3-4 share a held pose, 4 and 5 are identical
    assert flicker(pathlib.Path(work) / "frames", (0, 0, 300, 250), 0, 5) < .1
    print("SELFTEST OK", info)


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
