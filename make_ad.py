# Coca-Cola 30s spec ad — kinetic typography motion graphics (1920x1080, 30fps)
import math, random, subprocess, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
W, H, FPS, DUR = 1920, 1080, 30, 30.0
SR = 44100
RED = (244, 0, 9)
BPM_T0, BEAT = 8.5, 0.6

# ---------------------------------------------------------------- AUDIO
def build_audio():
    n = int(SR * DUR); t = np.arange(n) / SR
    mix = np.zeros(n)
    rng = np.random.default_rng(7)

    def band_noise(length, lo, hi):
        x = rng.standard_normal(length); X = np.fft.rfft(x)
        f = np.fft.rfftfreq(length, 1 / SR); X[(f < lo) | (f > hi)] = 0
        y = np.fft.irfft(X, length); return y / (np.abs(y).max() + 1e-9)

    def add(sig, start):
        i = int(start * SR); j = min(n, i + len(sig)); mix[i:j] += sig[: j - i]

    # pad: Am F C G, additive saw-ish, moody
    def note(f): return 440 * 2 ** ((f - 69) / 12)
    chords = [[45, 57, 60, 64], [41, 53, 57, 60], [48, 55, 60, 64], [43, 55, 59, 62]]
    clen = BEAT * 4
    pad = np.zeros(n)
    for ci in range(int(DUR / clen) + 2):
        ch = chords[ci % 4]; s = ci * clen - 0.3
        i0 = max(0, int(s * SR)); i1 = min(n, int((s + clen + 0.6) * SR))
        if i0 >= n: break
        tt = t[i0:i1] - s
        env = np.minimum(1, tt / 0.5) * np.minimum(1, (clen + 0.6 - tt) / 0.6)
        for m in ch:
            f = note(m)
            for det in (-0.12, 0.12):
                for k in range(1, 7):
                    pad[i0:i1] += env * np.sin(2 * np.pi * f * k * (1 + det / 100) * tt) / (k ** 1.6)
    pad /= np.abs(pad).max()
    padenv = np.clip(t / 3.0, 0, 1) * 0.22 + np.where((t > 8.5) & (t < 24.5), 0.05, 0)
    mix += pad * padenv

    # opening fizz + pop
    fz = band_noise(int(3.6 * SR), 3000, 12000)
    fz *= np.exp(-np.linspace(0, 3, len(fz))) * np.minimum(1, np.linspace(0, 40, len(fz)))
    fz *= 1 + 0.6 * (rng.random(len(fz)) > 0.995)
    add(fz * 0.35, 0.35)
    def pop(amp=0.5, f0=900):
        L = int(0.09 * SR); tt = np.arange(L) / SR
        return amp * np.sin(2 * np.pi * (f0 * tt - 2500 * tt ** 2)) * np.exp(-tt * 45)
    for pt in (1.8, 4.0, 4.8, 5.6, 14.2, 15.4, 26.5):
        add(pop(0.45), pt)

    # riser into drop
    rl = int(2.0 * SR); r = band_noise(rl, 1500, 9000) * np.linspace(0, 1, rl) ** 2.5
    add(r * 0.3, 6.5)
    # impact at drop
    L = int(1.2 * SR); tt = np.arange(L) / SR
    boom = np.sin(2 * np.pi * (60 * tt - 12 * tt ** 2)) * np.exp(-tt * 3)
    add(boom * 0.7, 8.5); add(boom * 0.6, 24.5)

    # drums 8.5–24.5
    kl = int(0.35 * SR); kt = np.arange(kl) / SR
    kick = np.sin(2 * np.pi * (45 * kt + 80 / 25 * (1 - np.exp(-kt * 25)))) * np.exp(-kt * 9)
    hat = band_noise(int(0.06 * SR), 7000, 16000) * np.exp(-np.arange(int(0.06 * SR)) / SR * 70)
    clap = band_noise(int(0.2 * SR), 1000, 5000) * np.exp(-np.arange(int(0.2 * SR)) / SR * 22)
    b = 0
    while BPM_T0 + b * BEAT < 24.4:
        bt = BPM_T0 + b * BEAT
        add(kick * 0.8, bt); add(hat * 0.18, bt + BEAT / 2)
        if b % 2 == 1: add(clap * 0.28, bt)
        b += 1
    # sub bass following roots
    roots = [33, 29, 36, 31]
    bass = np.zeros(n)
    for ci in range(12):
        s = BPM_T0 + ci * clen
        if s >= 24.5: break
        i0 = int(s * SR); i1 = min(int(min(s + clen, 24.5) * SR), n)
        tt = t[i0:i1] - s
        bass[i0:i1] = np.sin(2 * np.pi * note(roots[ci % 4] + 12) * tt) * np.minimum(1, tt / 0.02)
    mix += bass * 0.28

    # ending shimmer
    sh = np.zeros(n); i0 = int(24.5 * SR)
    tt = t[i0:] - 24.5
    for m in (69, 72, 76, 81):
        sh[i0:] += np.sin(2 * np.pi * note(m + 12) * tt) * np.exp(-tt * 0.6) * 0.05
    mix += sh

    # voice-over with ducking + small room
    def load(path):
        with wave.open(path) as w:
            sr = w.getframerate(); ch = w.getnchannels()
            d = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
            if ch == 2: d = d[::2]
        x = np.interp(np.arange(0, len(d) * SR / sr) * sr / SR, np.arange(len(d)), d)
        nz = np.nonzero(np.abs(x) > 0.01)[0]
        return x[nz[0]: nz[-1] + 1] / (np.abs(x).max() + 1e-9)
    vo = np.zeros(n)
    for path, st in ((os.path.join(A, "vo1.wav"), 3.95), (os.path.join(A, "vo2.wav"), 25.3)):
        v = load(path); i = int(st * SR); j = min(n, i + len(v)); vo[i:j] += v[: j - i]
    rev = vo.copy()
    for d, g in ((0.031, 0.25), (0.067, 0.18), (0.11, 0.12), (0.17, 0.07)):
        k = int(d * SR); rev[k:] += vo[:-k] * g
    venv = np.convolve((np.abs(vo) > 0.02).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    duck = 1 - 0.55 * np.clip(venv * 4, 0, 1)
    mix = mix * duck + rev * 0.75

    # master: fade-out, soft clip, stereo widen
    mix *= np.clip((DUR - t) / 1.2, 0, 1)
    mix = np.tanh(mix * 1.4) / np.tanh(1.4)
    dl = int(0.012 * SR)
    L_ = mix; R_ = np.concatenate([np.zeros(dl), mix[:-dl]]) * 0.15 + mix * 0.85
    st = np.stack([L_, R_], 1); st /= np.abs(st).max() / 0.92
    out = os.path.join(A, "mix.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    return out

# ---------------------------------------------------------------- VISUAL HELPERS
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def e_out(x): return 1 - (1 - x) ** 4
def e_expo(x): return 1 if x >= 1 else 1 - 2 ** (-10 * x)
def e_back(x, s=1.9): x -= 1; return x * x * ((s + 1) * x + s) + 1
def e_inout(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2

FONT = {"ko": r"C:\Windows\Fonts\malgunbd.ttf", "en": r"C:\Windows\Fonts\impact.ttf",
        "lt": r"C:\Windows\Fonts\malgunsl.ttf"}
_fc, _tc = {}, {}
def font(k, s):
    key = (k, s)
    if key not in _fc: _fc[key] = ImageFont.truetype(FONT[k], s)
    return _fc[key]
def text_img(txt, k, size, fill=(255, 255, 255), stroke=0, sfill=None, track=0):
    key = (txt, k, size, fill, stroke, sfill, track)
    if key in _tc: return _tc[key]
    f = font(k, size)
    if track:
        widths = [f.getbbox(c)[2] for c in txt]
        tw = sum(widths) + track * (len(txt) - 1)
    else:
        tw = f.getbbox(txt)[2]
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(tw + stroke * 2 + 20), asc + desc + stroke * 2 + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if track:
        x = 10 + stroke
        for c, wdt in zip(txt, widths):
            d.text((x, stroke + 5), c, font=f, fill=fill if stroke == 0 or sfill is None else fill,
                   stroke_width=stroke, stroke_fill=sfill)
            x += wdt + track
    else:
        d.text((10 + stroke, stroke + 5), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)
    im = im.crop(im.getbbox()) if im.getbbox() else im
    _tc[key] = im
    return im

def place(frame, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0, anchor="c"):
    if alpha <= 0.003 or scale <= 0.01: return
    if abs(scale - 1) > 0.002:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BILINEAR, expand=True)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    x = int(cx - im.width / 2) if anchor == "c" else int(cx)
    y = int(cy - im.height / 2)
    frame.alpha_composite(im, (x, y)) if (x >= 0 and y >= 0 and x + im.width <= W and y + im.height <= H) \
        else _safe_comp(frame, im, x, y)

def _safe_comp(frame, im, x, y):
    l, t_ = max(0, -x), max(0, -y)
    r, b = min(im.width, W - x), min(im.height, H - y)
    if r <= l or b <= t_: return
    frame.alpha_composite(im.crop((l, t_, r, b)), (x + l, y + t_))

def cover(src, zoom, fx, fy):
    """crop src to 16:9 window with zoom (>=1), focus fx,fy in 0..1"""
    sw, sh = src.size
    base = min(sw / W, sh / H)
    cw, ch = W * base / zoom, H * base / zoom
    x0 = clamp(fx * sw - cw / 2, 0, sw - cw); y0 = clamp(fy * sh - ch / 2, 0, sh - ch)
    return src.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

def solid(c): return Image.new("RGBA", (W, H), c + (255,))
def darken(im, a): return Image.blend(im, solid((0, 0, 0)), a)

# vignette + radial glow precomputed
yy, xx = np.mgrid[0:H, 0:W]
rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIG = Image.fromarray(np.dstack([np.zeros((H, W, 3), np.uint8),
                                 (np.clip((rr - 0.55) / 0.9, 0, 1) ** 1.6 * 235).astype(np.uint8)]), "RGBA")
glow_a = np.clip(1 - rr / 1.1, 0, 1) ** 2.2
GLOW = Image.fromarray(np.dstack([np.full((H, W), 200, np.uint8), np.zeros((H, W), np.uint8),
                                  np.full((H, W), 12, np.uint8), (glow_a * 255).astype(np.uint8)]), "RGBA")
grain_rng = np.random.default_rng(3)
GRAIN = [Image.fromarray(np.dstack([np.full((H // 2, W // 2, 3), 255, np.uint8),
         (grain_rng.random((H // 2, W // 2)) ** 18 * 40).astype(np.uint8)]), "RGBA").resize((W, H))
         for _ in range(4)]

# bubbles
brng = random.Random(11)
BUB = [dict(x=brng.random() * W, y0=brng.random() * H * 1.4, r=brng.choice([2, 3, 4, 5, 7, 10, 14]),
            sp=brng.uniform(60, 260), wob=brng.uniform(0, 6.28), a=brng.uniform(.25, .8)) for _ in range(140)]
def bubbles(frame, t, strength=1.0, speedmul=1.0, color=(255, 255, 255)):
    if strength <= 0: return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for b in BUB:
        y = (b["y0"] - t * b["sp"] * speedmul * (1 + b["r"] / 10)) % (H * 1.4) - H * 0.2
        x = b["x"] + math.sin(t * 2.2 + b["wob"]) * 10 * (b["r"] / 6)
        a = int(255 * b["a"] * strength); r = b["r"]
        d.ellipse((x - r, y - r, x + r, y + r), outline=color + (a,), width=max(1, r // 4))
        if r > 4: d.ellipse((x - r * .45, y - r * .55, x - r * .05, y - r * .15), fill=color + (a,))
    frame.alpha_composite(layer)

def beat_pulse(t):
    if t < BPM_T0: return 0
    ph = ((t - BPM_T0) % BEAT) / BEAT
    return math.exp(-ph * 7)

# ---------------------------------------------------------------- SOURCES
hero = Image.open(os.path.join(A, "hero.png")).convert("RGB")
friends = Image.open(os.path.join(A, "card3.png")).convert("RGB")
endc = Image.open(os.path.join(A, "card1.png")).convert("RGB")
logo = Image.open(os.path.join(A, "logo.png")).convert("RGBA")
end_red = endc.getpixel((20, 20))
END_BG = Image.new("RGB", (W, H), end_red)
_e = endc.resize((int(endc.width * H / endc.height), H), Image.LANCZOS)
END_BG.paste(_e, ((W - _e.width) // 2, 0))
# soften seams of end card
END_BG = END_BG.convert("RGBA")
logo_w = logo.copy(); px = np.array(logo_w); px[..., :3] = 255; LOGO_WHITE = Image.fromarray(px)

# ---------------------------------------------------------------- SCENES
def scene1(t):  # 0-3.5 dark, fizz, "치익—" "톡."
    f = solid((6, 3, 4))
    g = GLOW.copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v * (0.25 + 0.35 * prog(t, 0, 3.5)))))
    f.alpha_composite(g)
    bubbles(f, t, strength=prog(t, 0.3, 1.2), speedmul=0.6)
    # 치익— letter by letter, tracking widens
    word = "치익—"
    p = prog(t, 0.4, 1.5); out = prog(t, 1.6, 1.85)
    for i, ch in enumerate(word):
        lp = e_out(prog(t, 0.4 + i * 0.18, 0.9 + i * 0.18))
        im = text_img(ch, "ko", 150)
        x = W / 2 + (i - 1) * (170 + 60 * p)
        place(f, im, x, H / 2 + (1 - lp) * 40, 1.0, lp * (1 - out))
    # 톡.
    if t >= 1.75:
        lp = prog(t, 1.75, 2.15)
        s = 0.6 + 0.4 * e_back(lp) if lp < 1 else 1.0
        im = text_img("톡.", "ko", 260, fill=RED)
        fade = 1 - prog(t, 3.0, 3.45)
        place(f, im, W / 2, H / 2, s * (1 + 0.04 * (t - 1.75)), min(1, lp * 3) * fade)
        sub = text_img("THE SOUND OF REAL MAGIC", "en", 34, fill=(255, 255, 255), track=10)
        place(f, sub, W / 2, H / 2 + 200, 1, prog(t, 2.2, 2.6) * fade * 0.7)
    return f

def scene2(t):  # 3.5-8.5 hero glass + stacked words
    lt = t - 3.5
    z = 1.75 - 0.25 * e_inout(prog(t, 3.5, 8.5))
    f = darken(cover(hero, z, 0.40, 0.42), 0.38)
    bubbles(f, t, 0.5, 1.2)
    words = [("차갑게", 4.0, (255, 255, 255)), ("터지는", 4.8, (255, 255, 255)), ("그 순간", 5.6, RED)]
    for i, (wd, st, col) in enumerate(words):
        p = e_expo(prog(t, st, st + 0.5))
        ex = e_inout(prog(t, 7.7 + i * 0.08, 8.3 + i * 0.08))
        im = text_img(wd, "ko", 170, fill=col)
        x = 140; y = 300 + i * 220 + (1 - p) * 120 - ex * 900
        place(f, im, x, y, 1.0, min(1, p * 1.4), anchor="l")
        # red underline that wipes under each word
        if p > 0:
            bw = int(im.width * e_out(prog(t, st + 0.15, st + 0.7)) * (1 - ex))
            if bw > 2:
                bar = Image.new("RGBA", (bw, 10), RED + (255,)); place(f, bar, x, y + im.height / 2 + 18, anchor="l")
    cap = text_img("ICE COLD · SINCE 1886", "en", 30, track=8)
    place(f, cap, W - 140 - cap.width, H - 90, 1, prog(t, 4.5, 5.2) * (1 - prog(t, 7.6, 8.1)) * 0.75, anchor="l")
    # flash into drop
    fl = prog(t, 8.25, 8.5)
    if fl > 0: f = Image.blend(f, solid((255, 255, 255)), fl)
    return f

def scene3(t):  # 8.5-13.5 red marquee FIZZ POP AHH
    lt = t - 8.5
    f = solid(RED)
    bp = beat_pulse(t)
    rows = [("FIZZ  ·  POP  ·  AHH  ·  ", (180, 0, 6), 1), ("REFRESH  ·  REFRESH  ·  ", (255, 255, 255), -1),
            ("FIZZ  ·  POP  ·  AHH  ·  ", (180, 0, 6), 1)]
    for i, (txt, col, dr) in enumerate(rows):
        im = text_img(txt * 3, "en", 300, fill=col)
        unit = im.width / 3
        off = (lt * 520 * dr * (1.0 if i != 1 else 0.7)) % unit
        x = -unit + off if dr > 0 else -off
        y = 190 + i * 350 - (1 - e_expo(prog(t, 8.5 + i * 0.1, 9.2 + i * 0.1))) * 600 * (1 if i % 2 else -1)
        sc = 1 + 0.03 * bp
        place(f, im, x, y, sc, 1.0 if i == 1 else 0.95, anchor="l")
    # center can-ish logo burst
    p = e_back(prog(t, 9.0, 9.6))
    disc_r = int(250 * p * (1 + 0.05 * bp))
    if disc_r > 4:
        d = Image.new("RGBA", (disc_r * 2, disc_r * 2), (0, 0, 0, 0))
        ImageDraw.Draw(d).ellipse((0, 0, disc_r * 2 - 1, disc_r * 2 - 1), fill=(255, 255, 255, 255))
        place(f, d, W / 2, H / 2, alpha=1 - prog(t, 13.0, 13.4))
        place(f, logo, W / 2, H / 2, p * 0.85 * (1 + 0.05 * bp), 1 - prog(t, 13.0, 13.4), rot=-6 * (1 - p))
    bubbles(f, t, 0.9, 2.0)
    # white wipe from start
    wp = prog(t, 8.5, 8.75)
    if wp < 1: f = Image.blend(solid((255, 255, 255)), f, wp)
    # circle iris out to friends
    return f

def scene4(t):  # 13.5-19.5 friends
    z = 1.08 + 0.12 * prog(t, 13.5, 19.5)
    f = darken(cover(friends, z, 0.5, 0.42), 0.32)
    warm = Image.new("RGBA", (W, H), (255, 120, 40, 28)); f.alpha_composite(warm)
    bubbles(f, t, 0.35, 0.8)
    # line 1 letter by letter
    for li, (wd, st, col, y) in enumerate((("함께라서", 14.2, (255, 255, 255), 700), ("더 짜릿하게", 15.4, (255, 255, 255), 880))):
        ex = e_inout(prog(t, 18.9, 19.45))
        x = 140
        if li == 1:
            bw_full = text_img(wd, "ko", 150).width + 60
            bw = int(bw_full * e_expo(prog(t, st - 0.1, st + 0.4)))
            if bw > 2:
                bar = Image.new("RGBA", (bw, 190), RED + (255,)); place(f, bar, x - 30, y, alpha=1 - ex, anchor="l")
        cx = x
        for i, ch in enumerate(wd):
            lp = e_back(prog(t, st + i * 0.07, st + i * 0.07 + 0.45), 2.2)
            im = text_img(ch, "ko", 150, fill=col)
            if ch == " ": cx += 50; continue
            place(f, im, cx + im.width / 2, y + (1 - lp) * 80 - ex * 60, max(0.01, lp), min(1, prog(t, st + i * 0.07, st + i * 0.07 + 0.2)) * (1 - ex))
            cx += im.width + 8
    cap = text_img("TOGETHER, REFRESHED.", "en", 36, track=12)
    place(f, cap, 145, 560, 1, prog(t, 16.2, 16.8) * (1 - prog(t, 18.8, 19.3)) * 0.85, anchor="l")
    # iris in from previous scene
    ir = prog(t, 13.5, 14.0)
    if ir < 1:
        mask = Image.new("L", (W, H), 0); r = int(e_out(ir) * 1200)
        ImageDraw.Draw(mask).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=255)
        f = Image.composite(f, scene3(t), mask)
    return f

def scene5(t):  # 19.5-24.5 REAL MAGIC kinetic
    f = solid((8, 4, 5))
    g = GLOW.copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v * 0.5))); f.alpha_composite(g)
    bp = beat_pulse(t)
    bubbles(f, t, 0.6, 1.4)
    shrink = e_inout(prog(t, 23.4, 24.2))
    for wi, (wd, st, col, yy_, dirn) in enumerate((("REAL", 19.8, (255, 255, 255), 400, -1), ("MAGIC", 21.0, RED, 700, 1))):
        f_ = text_img(wd, "en", 330, fill=col)
        letters = [text_img(c, "en", 330, fill=col) for c in wd]
        gap = 14; total = sum(l.width for l in letters) + gap * (len(letters) - 1)
        x = W / 2 - total / 2
        for i, li in enumerate(letters):
            lp = e_back(prog(t, st + i * BEAT / 2, st + i * BEAT / 2 + 0.4), 1.6)
            y = yy_ + dirn * (1 - lp) * 700
            cx = x + li.width / 2
            cx = W / 2 + (cx - W / 2) * (1 - shrink * 0.6)
            y = H / 2 + (y - H / 2) * (1 - shrink * 0.6)
            sc = (1 + 0.04 * bp) * (1 - shrink * 0.6)
            place(f, li, cx, y, sc, (1 if lp > 0 else 0) * (1 - shrink), rot=(1 - lp) * 25 * dirn)
            x += li.width + gap
    # red circle grows to end card
    rp = prog(t, 23.9, 24.5)
    if rp > 0:
        r = int(e_out(rp) * 1200)
        d = ImageDraw.Draw(f); d.ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=end_red + (255,))
    return f

def scene6(t):  # 24.5-30 end card
    p = prog(t, 24.5, 30)
    z = 1.18 - 0.18 * e_out(prog(t, 24.5, 27.0))
    sw = int(W * z); sh = int(H * z)
    big = END_BG.resize((sw, sh), Image.BILINEAR)
    f = solid(end_red); f.alpha_composite(big.crop(((sw - W) // 2, (sh - H) // 2, (sw - W) // 2 + W, (sh - H) // 2 + H)))
    bubbles(f, t, 0.35 * (1 - prog(t, 28.5, 29.5)), 0.6)
    tag = text_img("매일이 짜릿한 마법이 되도록", "ko", 46)
    place(f, tag, W / 2, H - 95 + (1 - e_out(prog(t, 26.5, 27.2))) * 30, 1, prog(t, 26.5, 27.1))
    flash = 1 - prog(t, 24.5, 24.75)
    if flash > 0: f = Image.blend(f, solid(end_red), flash)
    fo = prog(t, 29.3, 30.0)
    if fo > 0: f = Image.blend(f, solid((0, 0, 0)), fo)
    return f

def render(t):
    if t < 3.5: f = scene1(t)
    elif t < 8.5: f = scene2(t)
    elif t < 13.5: f = scene3(t)
    elif t < 19.5: f = scene4(t)
    elif t < 24.5: f = scene5(t)
    else: f = scene6(t)
    if not (24.5 <= t):
        f.alpha_composite(VIG)
    f.alpha_composite(GRAIN[int(t * FPS) % 4])
    # letterbox bars (cinematic) that open at end
    return f.convert("RGB")

if __name__ == "__main__":
    import sys
    audio = os.path.join(A, "mix.wav")
    if not os.path.exists(audio): audio = build_audio()
    print("audio ok", flush=True)
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for ts in [1.0, 2.5, 5.9, 8.4, 10.5, 13.8, 16.5, 20.8, 22.9, 24.3, 27.5]:
            render(ts).resize((960, 540)).save(os.path.join(HERE, "stills", f"s_{ts:05.2f}.jpg"), quality=85)
        sys.exit()
    out = os.path.join(HERE, "CocaCola_RealMagic_30s.mp4")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out],
                            stdin=subprocess.PIPE)
    N = int(DUR * FPS)
    for i in range(N):
        proc.stdin.write(render(i / FPS).tobytes())
        if i % 90 == 0: print(f"frame {i}/{N}", flush=True)
    proc.stdin.close(); proc.wait(); print("done", out)
