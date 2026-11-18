# Fully synthesized soundtrack: score + SFX, mixed to stereo 48 kHz. No samples.
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
SR = 48000; DUR = 25.0; N = int(SR * DUR)
rng = np.random.default_rng(7)
T = np.arange(N) / SR

def env(n, a=0.01, r=0.2, curve=1.0):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    na = min(na, n); nr = min(nr, n)
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr) ** curve
    return e
def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, btype='low', fs=SR, output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, btype='high', fs=SR, output='sos'), x)
def swept_noise(n, f0, f1, q=0.6, steps=48):
    """noise through a band-pass whose centre glides f0->f1 (block-wise, crossfaded)"""
    out = np.zeros(n); x = rng.standard_normal(n); hop = n // steps + 1; win = np.hanning(2 * hop)
    for i in range(steps + 1):
        f = f0 * (f1 / f0) ** (i / steps); s = max(0, i * hop - hop); e = min(n, i * hop + hop)
        if e <= s: continue
        y = bp(x[s:e], max(30, f * (1 - q / 2)), min(SR / 2 - 100, f * (1 + q / 2)))
        w = win[(s - (i * hop - hop)):(s - (i * hop - hop)) + (e - s)]
        out[s:e] += y * w
    return out
L = np.zeros(N); R = np.zeros(N)
def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR); n = min(len(sig), N - i)
    if n <= 0: return
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i:i + n] += sig[:n] * gain * l; R[i:i + n] += sig[:n] * gain * r
def note(f, dur, kind='pad', vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    if kind == 'pad':      # detuned saw-ish stack, low-passed: strings
        y = sum(np.sin(2 * np.pi * f * k * t * (1 + d) + ph) / k for k in range(1, 9) for d, ph in ((-.003, 0), (.004, 1.3)))
        y = lp(y, 2200) * env(n, min(.9, dur * .3), min(1.2, dur * .4))
    elif kind == 'piano':  # struck string: decaying inharmonic partials
        y = sum(np.sin(2 * np.pi * f * k * np.sqrt(1 + .0004 * k * k) * t) * np.exp(-t * (1.6 + .9 * k)) / k ** 1.1 for k in range(1, 10))
        y *= env(n, .004, .08)
    elif kind == 'low':    # cello-ish drone
        y = sum(np.sin(2 * np.pi * f * k * t + .3 * np.sin(2 * np.pi * 5.1 * t)) / k ** 1.4 for k in range(1, 12))
        y = lp(y, 700) * env(n, min(1.5, dur * .3), min(1.5, dur * .4))
    elif kind == 'bell':
        y = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in ((1, 1, 2.2), (2.76, .5, 3.5), (5.4, .25, 5), (8.9, .12, 7)))
        y *= env(n, .002, .05)
    return y * vel
def hz(m): return 440 * 2 ** ((m - 69) / 12)

# ---------------- SCORE ----------------
# Act 1 (0-12): D minor, tense. Act 2 (14.5-25): D major, warm, 100 bpm.
put(note(hz(38), 12.6, 'low'), 0.0, .16); put(note(hz(45), 12.6, 'low'), 0.0, .07, .3)
put(note(hz(50), 6.5, 'low'), 6.0, .06, -.3)
for t, m in ((0.5, 62), (1.9, 65), (3.3, 69), (4.6, 68), (6.3, 62), (7.2, 65), (8.1, 70), (9.3, 69), (10.2, 73), (11.0, 74), (11.5, 76)):
    put(note(hz(m), 2.5, 'piano'), t, .22, rng.uniform(-.4, .4))
# heartbeat-like pulse that accelerates with the stamp words
for k in range(60):
    u = k / 59; t = 0.4 + 11.4 * (1 - (1 - u) ** 1.9)
    n = int(.09 * SR); tt = np.arange(n) / SR
    put(np.sin(2 * np.pi * (70 - 25 * tt / .09) * tt) * np.exp(-tt * 40), t, .22 + .2 * u)
# act 2 chords: D  A/C#  Bm  G | D  A  G  D   (2 beats each at 100 bpm = 1.2 s)
beat = 0.6; t0 = 14.55
chords = [(50, [62, 66, 69, 74]), (49, [61, 64, 69, 76]), (47, [59, 62, 66, 74]), (43, [59, 62, 67, 71]),
          (50, [62, 66, 69, 78]), (45, [61, 64, 69, 76]), (43, [59, 62, 67, 74]), (50, [62, 66, 69, 74])]
for i, (b, ns) in enumerate(chords):
    t = t0 + i * 2 * beat; d = 2 * beat + .5 if i < 7 else 3.2
    if t >= DUR: break
    put(note(hz(b - 12), d, 'low'), t, .24)
    for j, m in enumerate(ns): put(note(hz(m), d, 'pad'), t, .055, (j - 1.5) * .35)
    arp = ns + [ns[2] + 12, ns[1] + 12, ns[3], ns[2]]
    for j in range(8 if i < 7 else 4):
        tt = t + j * beat / 4
        if tt < DUR - .2: put(note(hz(arp[j % 8] + 12), 1.4, 'piano'), tt, .16 + .04 * (j % 4 == 0), np.sin(j) * .5)
# melody on top (bell)
for t, m in ((14.55, 86), (15.75, 85), (16.95, 83), (17.55, 86), (18.15, 90), (19.35, 88), (20.55, 86), (21.15, 83), (21.75, 86), (22.95, 90), (23.55, 93)):
    put(note(hz(m), 2.2, 'bell'), t, .085, .2)

# ---------------- SFX ----------------
def whoosh(dur, f0=200, f1=3500, down=False):
    n = int(dur * SR); y = swept_noise(n, f1 if down else f0, f0 if down else f1)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2.2
    return y * e + lp(rng.standard_normal(n), 120) * e * .8
def boom(dur=1.8, f=58):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (f * t - 18 * (1 - np.exp(-t * 9)) / 9 * -1)) * np.exp(-t * 2.6)
    y += lp(rng.standard_normal(n), 300) * np.exp(-t * 14) * .7
    return y
def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = swept_noise(n, 300, 9000, q=.9) * (t / dur) ** 2.5
    y += np.sin(2 * np.pi * (110 * t + 260 * t * t / dur)) * (t / dur) ** 2 * .25
    return y
def tick(f=2600):
    n = int(.03 * SR); t = np.arange(n) / SR
    return bp(rng.standard_normal(n), f * .7, f * 1.4) * np.exp(-t * 220)
def key():
    n = int(.045 * SR); t = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 1500, 5200) * np.exp(-t * 160) + np.sin(2 * np.pi * 180 * t) * np.exp(-t * 90) * .5)
def paper(dur):
    n = int(dur * SR); y = hp(rng.standard_normal(n), 2500); m = np.zeros(n)
    for _ in range(int(dur * 28)):
        i = rng.integers(0, n - 2000); k = rng.integers(400, 2000); m[i:i + k] += np.hanning(k) * rng.uniform(.3, 1)
    return y * m
def shimmer(dur):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for k in range(26):
        f = hz(rng.choice([86, 90, 93, 98, 102, 105])) * rng.choice([1, 2]); s = rng.uniform(0, dur * .7)
        tt = np.clip(t - s, 0, None); y += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 5) * (t > s) * rng.uniform(.3, 1)
    return y * env(n, .01, .6)
def scratch(dur):   # quill on paper
    n = int(dur * SR); t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 2500, 7000) * (.5 + .5 * np.sin(2 * np.pi * 7 * t) ** 2) * (np.sin(2 * np.pi * 1.6 * t) > -.3) * env(n, .05, .2)
def chop():
    n = int(.35 * SR); t = np.arange(n) / SR
    return lp(rng.standard_normal(n), 1800) * np.exp(-t * 28) + np.sin(2 * np.pi * 95 * t) * np.exp(-t * 16)
def birdsong(dur):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for _ in range(int(dur * 3.2)):
        s = rng.uniform(0, dur - .4); d = rng.uniform(.06, .16); f0 = rng.uniform(2600, 5200)
        for r in range(rng.integers(1, 5)):
            i = int((s + r * d * 1.25) * SR); k = int(d * SR)
            if i + k >= n: break
            tt = np.arange(k) / SR
            y[i:i + k] += np.sin(2 * np.pi * (f0 * tt + rng.uniform(-1, 1) * 9000 * tt * tt)) * np.hanning(k) * rng.uniform(.3, 1)
    return y * env(n, .8, .8)
def wind(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 250, 1100) * (.6 + .4 * np.sin(2 * np.pi * .23 * t)) * env(n, .8, .9)

# hook: arrival whoosh + low hit so frame 1 has sound
put(whoosh(.55, 300, 2500, down=True), 0.0, .5, .5); put(boom(1.6, 52), 0.38, .55)
put(tick(900), 1.35, .9); put(boom(1.2, 70), 1.35, .35)                # "You still work like this" punch
# fly into the painting
put(riser(.6), 2.65, .35); put(whoosh(.75), 2.75, .7); put(boom(1.8), 3.2, .6)
put(scratch(2.3), 3.5, .22, .25)                                         # quill
for t in np.arange(3.6, 5.8, .5): put(tick(1700), t, .28, -.5)           # clock
# whip to woodchopper
put(whoosh(.5), 5.85, .7, -.2); put(boom(1.0, 75), 6.28, .35)
for t in (6.75, 7.45, 8.15): put(chop(), t, .6, .1)
# burst of paper
put(riser(.5), 8.5, .35); put(whoosh(.6), 8.75, .7, .3); put(boom(1.6), 9.25, .5)
put(paper(3.0) * np.linspace(.5, 1, int(3.0 * SR)), 9.0, .22)
for k in range(40):                                                        # stamp hits accelerate
    u = k / 39; b = u * u * 14 + u * 5
for idx in range(19):
    # invert beats(u)=14u^2+5u
    u = (-5 + np.sqrt(25 + 56 * idx)) / 28; t = 9.4 + u * 2.55
    put(key(), t, .55, (-1) ** idx * .4); put(tick(3200), t, .3)
put(riser(1.6), 10.35, .55)
# freeze: sudden silence, then typing
put(boom(1.4, 45), 11.97, .6)
TYPED = 'Do the boring part for me.'
for i in range(len(TYPED)):
    if TYPED[i] != ' ': put(key(), 12.3 + 1.15 * i / len(TYPED), .42, rng.uniform(-.2, .2))
put(key(), 13.72, .8); put(note(hz(86), .9, 'bell'), 13.74, .16)           # enter
# release
put(riser(.8), 13.75, .45); put(shimmer(2.6), 13.9, .11); put(whoosh(.8, 300, 5000), 14.05, .7); put(boom(2.2, 50), 14.55, .7)
put(paper(.9), 14.0, .2)
put(birdsong(10.4), 14.6, .035, -.3); put(wind(7), 18.2, .10, .2)
put(whoosh(.5), 17.98, .5, .2); put(shimmer(1.4), 18.35, .05)
put(whoosh(.5), 21.58, .5, -.2); put(shimmer(1.4), 21.95, .05)
put(whoosh(1.1, 2500, 250), 23.4, .35)
put(whoosh(.45), 24.58, .5, -.5)

# ---------------- MIX ----------------
mix = np.stack([L, R], 1)
# simple plate-ish reverb
ir_n = int(1.6 * SR); ir = rng.standard_normal((ir_n, 2)) * np.exp(-np.arange(ir_n) / SR * 4.2)[:, None]
ir = np.stack([hp(lp(ir[:, c], 6000), 250) for c in range(2)], 1); ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([fftconvolve(mix[:, c], ir[:, c])[:N] for c in range(2)], 1)
mix = mix + .16 * wet
# duck everything for the freeze (12.0-13.9)
g = np.ones(N); a, b = int(12.05 * SR), int(13.85 * SR); g[a:b] = .55; k = int(.1 * SR)
g = np.convolve(g, np.ones(k) / k, mode='same'); mix *= g[:, None]
mix[:int(.01 * SR)] *= np.linspace(0, 1, int(.01 * SR))[:, None]; mix[-int(.12 * SR):] *= np.linspace(1, 0, int(.12 * SR))[:, None]
mix = hp(mix.T, 28).T
mix = np.tanh(mix * 1.6) / 1.6            # soft clip
mix /= np.abs(mix).max() / .92
wavfile.write('mix_raw.wav', SR, (mix * 32767).astype(np.int16))
print('ok', mix.shape, 'peak', np.abs(mix).max())
