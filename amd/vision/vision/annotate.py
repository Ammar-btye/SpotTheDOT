"""Set-of-Mark style annotation: each reading's mark drawn and labelled with its V# id (PIL only)."""
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .result import Mark, Reading

MIN_SIDE, MAX_SIDE = 480, 1280
COLOURS = [(0, 255, 255), (255, 0, 255), (0, 255, 0), (255, 255, 0), (255, 128, 0), (64, 160, 255)]
CONTEXT = (160, 160, 160)


def _font(px: int):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:                          # Pillow without FreeType size support
        return ImageFont.load_default()


def _label(d: ImageDraw.ImageDraw, xy, text: str, colour, fnt, size):
    x, y = xy
    x = max(0, min(size[0] - 1, x))
    y = max(0, min(size[1] - 1, y))
    bb = d.textbbox((x, y), text, font=fnt)
    if bb[2] > size[0]:
        x -= bb[2] - size[0] + 2
    if bb[3] > size[1]:
        y -= bb[3] - size[1] + 2
    bb = d.textbbox((x, y), text, font=fnt)
    d.rectangle([bb[0] - 2, bb[1] - 1, bb[2] + 2, bb[3] + 1], fill=(0, 0, 0))
    d.text((x, y), text, fill=colour, font=fnt)


def _draw(d, m: Mark, s: float, colour, width: int):
    c = [v * s for v in m.coords]
    if m.type in ("box", "xbox"):
        d.rectangle(c[:4], outline=colour, width=width)
        if m.type == "xbox":
            d.line([c[0], c[1], c[2], c[3]], fill=colour, width=width)
            d.line([c[0], c[3], c[2], c[1]], fill=colour, width=width)
        if (c[2] - c[0]) > 4 * (c[3] - c[1]):        # a table row: label in the empty middle, not over the text
            return c[0] + 0.45 * (c[2] - c[0]), (c[1] + c[3]) / 2, "mid"
        return c[0], c[1]
    if m.type in ("line", "hline", "vtick"):
        d.line(c[:4], fill=colour, width=width)
        return c[2], c[3]
    if m.type == "dashed":
        x0, y0, x1, y1 = c[:4]
        n = 10
        for i in range(0, n, 2):
            d.line([x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, x0 + (x1 - x0) * (i + 1) / n,
                    y0 + (y1 - y0) * (i + 1) / n], fill=colour, width=width)
        return x1, y1
    if m.type == "point":
        r = 3 * width
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=colour, width=width)
        return c[0] + r, c[1] - r
    if m.type == "circle":
        d.ellipse([c[0] - c[2], c[1] - c[2], c[0] + c[2], c[1] + c[2]], outline=colour, width=max(1, width - 1))
        return c[0] + c[2], c[1]
    return c[0], c[1]


def annotate(orig: np.ndarray, readings: List[Reading], ids: List[str], extra: List[Mark]) -> np.ndarray:
    h, w = orig.shape[:2]
    long_side = max(h, w)
    s = 1.0
    if long_side > MAX_SIDE:
        s = MAX_SIDE / long_side
    elif long_side < MIN_SIDE:
        s = MIN_SIDE / long_side
    im = Image.fromarray(orig).resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS,
                                    reducing_gap=3.0) if s != 1.0 \
        else Image.fromarray(orig.copy())
    d = ImageDraw.Draw(im)
    width = max(2, round(max(im.size) / 400))
    fnt = _font(max(13, round(max(im.size) / 55)))
    for m in extra:
        _draw(d, m, s, CONTEXT if m.type != "xbox" else (255, 64, 64), max(1, width - 1))
    k = 0
    for rd, vid in zip(readings, ids):
        if not rd.marks:
            continue
        colour = COLOURS[k % len(COLOURS)]
        k += 1
        anchor = None
        for m in rd.marks:
            a = _draw(d, m, s, colour, width)
            anchor = anchor or a
        if anchor is not None:
            fh = getattr(fnt, "size", 12)
            y = anchor[1] - fh / 2 - 1 if len(anchor) > 2 else anchor[1] - fh - 4
            unit = (" " + rd.unit) if rd.unit and rd.unit not in ("relative", "ratio", "count") else ""
            _label(d, (anchor[0] + 4, y), "%s %g%s" % (vid, rd.value, unit), colour, fnt, im.size)
    return np.asarray(im.convert("RGB"))
