"""Synthetic inspection images with known ground truth (PIL only, deterministic)."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def font(size: int):
    return ImageFont.load_default(size=size)


def render_gauge(value: float, vmin: float = 0.0, vmax: float = 300.0, size: int = 360, sweep: float = 270.0,
                 major: float = 50.0, minor: float = 10.0, tail: float = 0.15, two_ended: bool = False,
                 unit: str = "psi", bg=(150, 140, 120)) -> np.ndarray:
    """A dial gauge: white face, ticks, labels every `major`, black needle pointing at `value`."""
    im = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(im)
    cx = cy = size / 2
    R = size * 0.44
    d.ellipse([cx - R - 8, cy - R - 8, cx + R + 8, cy + R + 8], fill=(90, 90, 95))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(245, 245, 240))

    def ang(v):  # cw from up
        return -sweep / 2 + (v - vmin) / (vmax - vmin) * sweep

    def pt(a, rr):
        return cx + rr * math.sin(math.radians(a)), cy - rr * math.cos(math.radians(a))
    v = vmin
    while v <= vmax + 1e-9:
        a = ang(v)
        is_major = abs((v - vmin) / major - round((v - vmin) / major)) < 1e-6
        d.line([pt(a, R * (0.82 if is_major else 0.88)), pt(a, R * 0.96)], fill=(20, 20, 20),
               width=3 if is_major else 1)
        if is_major:
            x, y = pt(a, R * 0.66)
            d.text((x, y), "%g" % v, fill=(15, 15, 15), font=font(int(size * 0.06)), anchor="mm")
        v += minor
    d.text((cx, cy + R * 0.45), unit, fill=(30, 30, 30), font=font(int(size * 0.06)), anchor="mm")
    a = ang(value)
    tip = pt(a, R * 0.78)
    back = pt(a + 180, R * (0.6 if two_ended else tail))
    d.line([back, tip], fill=(10, 10, 10), width=max(3, size // 90))
    rr = size * 0.025
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(10, 10, 10))
    return np.asarray(im)


def ironbow(t: np.ndarray) -> np.ndarray:
    """t in [0,1] -> RGB uint8, an ironbow-like palette (black-purple -> red -> orange -> yellow -> white)."""
    stops = np.array([[0.0, 5, 0, 30], [0.2, 70, 0, 140], [0.4, 170, 0, 140], [0.55, 220, 40, 60],
                      [0.7, 245, 120, 0], [0.85, 250, 200, 10], [1.0, 255, 255, 230]], dtype=float)
    out = np.empty(t.shape + (3,), float)
    for c in range(3):
        out[..., c] = np.interp(t, stops[:, 0], stops[:, c + 1])
    return out.clip(0, 255).astype(np.uint8)


def render_thermal(max_c: float, tmin: float = 20.0, tmax: float = 120.0, body_c: float = 40.0,
                   w: int = 320, h: int = 220, hot_xy=(150, 90), labels=None) -> np.ndarray:
    """A thermal frame: background tmin+5, a body at body_c, a Gaussian hotspot peaking at max_c, and a
    vertical colorbar tmin..tmax on the right with labelled ticks."""
    scene_w = int(w * 0.78)
    yy, xx = np.mgrid[0:h, 0:scene_w].astype(float)
    T = np.full((h, scene_w), tmin + 5.0)
    body = (np.abs(xx - scene_w * 0.45) < scene_w * 0.33) & (np.abs(yy - h * 0.5) < h * 0.3)
    T[body] = body_c
    hx, hy = hot_xy
    g = np.exp(-(((xx - hx) ** 2) + ((yy - hy) ** 2)) / (2 * 9.0 ** 2))
    T = np.where(g > 0.01, np.maximum(T, body_c + (max_c - body_c) * g), T)
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (12, 12, 16)
    img[:, :scene_w] = ironbow(np.clip((T - tmin) / (tmax - tmin), 0, 1))
    top, bot = int(h * 0.15), int(h * 0.85)
    bx0, bx1 = scene_w + 12, scene_w + 22
    for y in range(top, bot + 1):
        img[y, bx0:bx1 + 1] = ironbow(np.array([(bot - y) / (bot - top)]))[0]
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    labels = labels or [tmin + k * (tmax - tmin) / 4 for k in range(5)]
    for v in labels:
        y = bot - (v - tmin) / (tmax - tmin) * (bot - top)
        d.text((bx1 + 6, y), "%g" % v, fill=(250, 250, 250), font=font(14), anchor="lm")
    d.text((bx0, top - 14), "°C", fill=(250, 250, 250), font=font(13), anchor="lm")
    return np.asarray(im)


def jet(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0, 1)
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    return (np.stack([r, g, b], -1) * 255).astype(np.uint8)


def render_spectrogram(peak_khz: float = 3.0, fmax_khz: float = 20.0, dur_s: float = 10.0,
                       bursts=(2.0, 5.0, 8.0), w: int = 420, h: int = 280) -> np.ndarray:
    """A 0-fmax kHz x 0-dur s jet spectrogram with a tonal band at peak_khz and broadband bursts, with axes."""
    x0, y0, x1, y1 = 60, 15, w - 15, h - 50
    pw, ph = x1 - x0, y1 - y0
    f = (1 - np.arange(ph) / (ph - 1))[:, None] * fmax_khz
    t = (np.arange(pw) / (pw - 1))[None, :] * dur_s
    v = 0.12 + 0.05 * np.exp(-f / 4.0)
    v = v + 0.7 * np.exp(-((f - peak_khz) ** 2) / (2 * 0.5 ** 2))
    for b in bursts:
        v = v + 0.45 * np.exp(-((t - b) ** 2) / (2 * 0.08 ** 2)) * (0.6 + 0.4 * np.exp(-f / 15))
    v = np.clip(v * np.ones((ph, pw)), 0, 1)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    img.paste(Image.fromarray(jet(v)), (x0, y0))
    d = ImageDraw.Draw(img)
    fnt = font(14)
    for k in range(0, int(fmax_khz) + 1, 5):
        y = y1 - 1 - k / fmax_khz * (ph - 1)
        d.line([(x0 - 5, y), (x0, y)], fill=(0, 0, 0))
        d.text((x0 - 8, y), str(k), fill=(0, 0, 0), font=fnt, anchor="rm")
    for k in range(0, int(dur_s) + 1, 2):
        x = x0 + k / dur_s * (pw - 1)
        d.line([(x, y1), (x, y1 + 5)], fill=(0, 0, 0))
        d.text((x, y1 + 8), str(k), fill=(0, 0, 0), font=fnt, anchor="mt")
    d.text(((x0 + x1) / 2, h - 12), "Time (s)", fill=(0, 0, 0), font=fnt, anchor="mm")
    return np.asarray(img)


def jpeg(rgb: np.ndarray, quality: int = 85, blur: float = 0.0) -> np.ndarray:
    import io
    im = Image.fromarray(rgb)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    return np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
