"""Thermal reader for colour-mapped frames with a vertical colorbar (the kit's thermal JPEGs).

colorbar -> LUT from the bar's centre columns (ends trimmed) -> OCR'd tick labels -> RANSAC linear fit (row -> °C)
-> nearest-LUT-colour inversion with a distance cut-off -> 5x5 nan-aware smoothing -> max / p95 / median, hotspot
(largest blob >= max - 3 °C), reference + ΔT, CLIPPED when the max sits at the top of the scale.

Orbit thermal panes have no colorbar; their Region Max/Min come from the Orbit reader instead.
"""
from typing import Optional, Tuple

import cv2
import numpy as np

from . import textaxes
from .result import Frame, Mark, ReaderResult, Reading, clamp01, r1

MAX_COLOR_DIST = 45.0       # RGB distance beyond which a pixel is "not on the palette" (text, overlays)
HOTSPOT_BAND_C = 3.0        # hotspot = largest blob within this many °C of the max
SMOOTH = 5                  # smoothing kernel (work pixels)


def _run(col: np.ndarray) -> Optional[Tuple[int, int]]:
    """Longest vertical run of coloured/bright rows in a (H x 3) column."""
    sat = col.max(1) - col.min(1)
    rows = np.where((sat > 30) | (col.sum(1) > 600))[0]
    if rows.size == 0:
        return None
    runs = np.split(rows, np.where(np.diff(rows) > 2)[0] + 1)
    run = max(runs, key=len)
    return int(run[0]), int(run[-1])


def find_colorbar(img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """(x0, x1, top, bottom) of a vertical colour bar in the right 45 % of the frame, or None.

    A bar is a narrow strip (3 px .. 8 % of the width) between two strong vertical edges, flat across its width,
    covering >= 35 % of the height, with a large and monotonic luminance change from bottom to top."""
    h, w = img.shape[:2]
    f = img.astype(np.float32)
    e = np.abs(np.diff(f, axis=1)).sum(2).mean(0)          # e[x] = edge strength between x and x+1
    thr = max(25.0, 4.0 * float(np.median(e)))
    xs = [x for x in range(int(w * 0.55), w - 3)
          if e[x] >= thr and e[x] >= e[x - 1] and e[x] >= e[x + 1]]
    lum_w = np.array([0.299, 0.587, 0.114], np.float32)
    best = None
    for i, a in enumerate(xs):
        for b in xs[i + 1:]:
            width = b - a
            if width < 3:
                continue
            if width > max(24, int(0.08 * w)):
                break
            inner = e[a + 1:b]
            if inner.size and float(inner.mean()) > 0.35 * min(e[a], e[b]):
                continue
            x0, x1 = a + 1, b
            xc = (x0 + x1) // 2
            col = np.median(f[:, max(x0, xc - 1):min(x1, xc + 1) + 1], axis=1)
            run = _run(col)
            if run is None or run[1] - run[0] < 0.35 * h:
                continue
            top, bot = run
            seg = f[top:bot + 1, x0 + 1:x1] if x1 - x0 >= 3 else f[top:bot + 1, x0:x1 + 1]
            if float(seg.std(axis=1).mean()) > 12:            # not flat across its width
                continue
            lum = col[top:bot + 1] @ lum_w
            if float(np.ptp(lum)) < 80:
                continue
            rho = abs(float(np.corrcoef(np.argsort(np.argsort(lum)), np.arange(lum.size))[0, 1]))
            if rho < 0.7:
                continue
            score = (min(e[a], e[b]), x0)
            if best is None or score > best[0]:
                best = (score, (x0, x1, top, bot))
    return None if best is None else best[1]


def _lut(img: np.ndarray, bar) -> Tuple[np.ndarray, np.ndarray]:
    """(colours L x 3 float, row y of each entry). Centre columns, ends trimmed by 2 px."""
    x0, x1, top, bot = bar
    c0, c1 = x0 + (1 if x1 - x0 >= 3 else 0), x1 - (1 if x1 - x0 >= 3 else 0)
    trim = 2 if bot - top > 20 else 0
    ys = np.arange(top + trim, bot - trim + 1)
    cols = np.median(img[ys][:, c0:c1 + 1].astype(np.float32), axis=1)
    return cols, ys.astype(np.float32)


def invert(scene: np.ndarray, lut: np.ndarray, lut_vals: np.ndarray, max_dist: float = MAX_COLOR_DIST):
    """Per-pixel value of the nearest LUT colour; NaN where the nearest colour is farther than max_dist.

    Colours are quantised to 5 bits/channel and each unique colour is solved once."""
    q = (scene >> 3).astype(np.int32)
    code = (q[..., 0] << 10) | (q[..., 1] << 5) | q[..., 2]
    uniq, inv = np.unique(code.ravel(), return_inverse=True)
    centres = np.stack([(uniq >> 10) & 31, (uniq >> 5) & 31, uniq & 31], axis=1).astype(np.float32) * 8 + 4
    vals = np.empty(len(uniq), np.float32)
    dist = np.empty(len(uniq), np.float32)
    for s in range(0, len(uniq), 4096):
        d = ((centres[s:s + 4096, None, :] - lut[None, :, :]) ** 2).sum(-1)
        i = d.argmin(1)
        vals[s:s + 4096] = lut_vals[i]
        dist[s:s + 4096] = np.sqrt(d[np.arange(len(i)), i])
    v = vals[inv].reshape(code.shape)
    dd = dist[inv].reshape(code.shape)
    v[dd > max_dist] = np.nan
    return v, dd


def nan_smooth(v: np.ndarray, k: int = SMOOTH) -> np.ndarray:
    m = np.isfinite(v).astype(np.float32)
    z = np.where(np.isfinite(v), v, 0).astype(np.float32)
    num = cv2.blur(z, (k, k), borderType=cv2.BORDER_REFLECT)
    den = cv2.blur(m, (k, k), borderType=cv2.BORDER_REFLECT)
    out = np.full(v.shape, np.nan, np.float32)
    ok = (den >= 0.5) & (m > 0)
    out[ok] = num[ok] / den[ok]
    return out


def _merge_ticks(acc, new):
    for t in new:
        if not any(abs(t.pos - o.pos) < max(3.0, 0.5 * (t.word.h if t.word else 6)) for o in acc):
            acc.append(t)
    return sorted(acc, key=lambda t: t.pos)


def _scale_fit(img: np.ndarray, bar):
    """OCR the colorbar labels and fit row -> °C. OCR of short numbers is crop-sensitive (the kit's '50' reads as
    'SO' in some crops and vanishes in others), so up to four crops are tried and their ticks merged."""
    h, w = img.shape[:2]
    x0, x1, top, bot = bar
    regions = [(max(0, x0 - int(0.1 * w)), 0, w, h), (x1 + 1, 0, w, h), (x0, 0, w, h),
               (max(0, x0 - int(0.25 * w)), 0, w, h)]
    words, ticks, fit = [], [], None
    for reg in regions:
        ws = textaxes.ocr(img, region=reg)
        right = [wd for wd in ws if wd.cx > x1]
        for wd in right:
            if not any(abs(wd.cx - o.cx) < 2 and abs(wd.cy - o.cy) < 2 for o in words):
                words.append(wd)
        ticks = _merge_ticks(ticks, textaxes.find_ticks(right, axis="y", region=(x1 + 1, top - 0.1 * h, w,
                                                                                  bot + 0.1 * h)))
        if len(ticks) >= 3:
            fit = textaxes.calibrate_axis(ticks, "linear", expect_sign=-1)
            if fit is not None and fit.inliers >= 4:
                break
    if fit is None:          # labels on the left of the bar
        ws = textaxes.ocr(img, region=(max(0, x0 - int(0.2 * w)), 0, x0, h))
        lt = textaxes.find_ticks(ws, axis="y", region=(0, top - 0.1 * h, x0, bot + 0.1 * h))
        if len(lt) >= 3:
            fit = textaxes.calibrate_axis(lt, "linear", expect_sign=-1)
            if fit is not None:
                words += ws
    return words, fit


def ticks_of(words, bar, h, w):
    x0, x1, top, bot = bar
    return textaxes.find_ticks([wd for wd in words if wd.cx > x1], axis="y",
                               region=(x1 + 1, top - 0.1 * h, w, bot + 0.1 * h))


def ticks_inliers(fit, ticks):
    span = abs(float(fit.value(max(t.pos for t in ticks)) - fit.value(min(t.pos for t in ticks)))) if ticks else 0
    return [t for t in ticks if abs(float(fit.value(t.pos)) - t.value) <= max(1.0, 0.05 * span)]


def read(frame: Frame, hints: Optional[dict] = None) -> ReaderResult:
    img = frame.work
    h, w = img.shape[:2]
    res = ReaderResult()
    bar = find_colorbar(img)
    if bar is None:
        res.flags.append("NO_COLORBAR")
        res.words = textaxes.ocr(frame.orig)
        return res
    x0, x1, top, bot = bar
    words, fit = _scale_fit(img, bar)
    flags, conf = [], 0.9
    lut, ys = _lut(img, bar)
    if fit is not None:
        lut_vals = fit.value(ys).astype(np.float32)
        span = float(abs(fit.value(top) - fit.value(bot)))
        if fit.max_resid > 0.03 * span:
            conf -= 0.15
        if fit.rejected:
            flags.append("LABEL_OUTLIER")
    elif hints and hints.get("range_max") is not None:
        lo = float(hints.get("range_min") or 0.0)
        hi = float(hints["range_max"])
        lut_vals = np.linspace(hi, lo, len(ys)).astype(np.float32)
        flags.append("USED_HINT")
        conf = 0.6
    else:
        res.flags.append("AXIS_FIT_FAILED")
        res.words = [wd.shifted(0, 0, frame.scale) for wd in words]
        return res
    t_top, t_bot = float(lut_vals[0]), float(lut_vals[-1])
    span = abs(t_top - t_bot)
    scale_top = t_top        # the top label, when one sits at the top of the bar (the fit may overshoot it)
    if fit is not None:
        top_ticks = [tk for tk in ticks_inliers(fit, ticks_of(words, bar, h, w)) if tk.pos <= top + 0.06 * (bot - top)]
        if top_ticks:
            scale_top = max(tk.value for tk in top_ticks)

    scene_x1 = max(1, x0 - 2)
    scene = img[:, :scene_x1]
    raw, dist = invert(scene, lut, lut_vals)
    valid = np.isfinite(raw)
    valid_share = float(valid.mean())
    if valid_share < 0.6:
        conf -= 0.2
        flags.append("LOW_PALETTE_MATCH")
    t = nan_smooth(raw)
    if not np.isfinite(t).any():
        res.flags.append("READER_FAILED")
        return res
    tmax = float(np.nanmax(t))
    p95 = float(np.nanpercentile(t, 95))
    med = float(np.nanmedian(t))
    # hotspot: largest connected blob within HOTSPOT_BAND_C of the max
    hot = (np.nan_to_num(t, nan=-1e9) >= tmax - HOTSPOT_BAND_C).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(hot, connectivity=8)
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])) if n > 1 else 0
    bx, by, bw, bh = (int(v) for v in stats[big, :4])
    blob = lab == big
    tb = np.where(blob, np.nan_to_num(t, nan=-1e9), -1e9)
    py, px = np.unravel_index(int(np.argmax(tb)), tb.shape)
    blob_max = float(t[py, px])
    # reference: the scene median outside the (dilated) hotspot
    far = cv2.dilate(blob.astype(np.uint8), np.ones((15, 15), np.uint8)) == 0
    vals = t[far & np.isfinite(t)]
    ref = float(np.median(vals)) if vals.size >= 20 else med
    dT = blob_max - ref

    clipped = blob_max >= min(t_top, scale_top) - max(1.0, 0.015 * span)
    mflags = list(flags)
    note = "hottest spot %.1f °C" % blob_max
    if clipped:
        blob_max = scale_top             # the value is a lower bound: report the top of the scale
        dT = blob_max - ref
        mflags.append("CLIPPED")
        note = "hottest spot reaches the %g °C top of the scale; true value may be higher" % round(scale_top, 1)
    bbox = frame.box_to_orig([bx, by, bx + bw - 1, by + bh - 1])
    point = frame.pt_to_orig([px, py])
    c = clamp01(conf)
    res.readings = [
        Reading("max_temperature", r1(blob_max), "°C", round(c if not clipped else min(c, 0.8), 2), "colorbar_lut",
                mflags, bbox=bbox, point=point, note=note, primary=True, full_scale=scale_top, clipped=clipped,
                marks=[Mark("box", bbox), Mark("point", point)]),
        Reading("p95_temperature", r1(p95), "°C", round(c, 2), "colorbar_lut", list(flags)),
        Reading("median_temperature", r1(med), "°C", round(c, 2), "colorbar_lut", list(flags)),
        Reading("reference_temperature", r1(ref), "°C", round(clamp01(c - 0.15), 2), "scene_median_outside_hotspot",
                list(flags), note="median of the scene outside the hotspot"),
        Reading("delta_t", r1(dT), "°C", round(clamp01(c - 0.15), 2), "hotspot_minus_reference",
                list(flags) + (["CLIPPED"] if clipped else []),
                note="hotspot %.1f °C over the reference %.1f °C" % (dT, ref)),
    ]
    res.key_results = [
        {"name": "Max Temperature", "units": "°C", "value": r1(blob_max)},
        {"name": "Reference Temperature", "units": "°C", "value": r1(ref)},
        {"name": "Delta T", "units": "°C", "value": r1(dT)},
        {"name": "Scale", "units": "°C", "value": "%g–%g" % (round(t_bot, 1), round(t_top, 1))},
        {"name": "Clipped", "units": "", "value": "yes" if clipped else "no"},
    ]
    sev = 0
    if dT > 15:
        sev = 3
    elif dT >= 4:
        sev = 2
    elif dT >= 1:
        sev = 1
    if blob_max >= 95.0:
        sev = 4
    if sev:
        res.alert = {"title": "Thermal hotspot %s%.1f °C (ΔT %.0f °C over reference)"
                              % ("≥" if clipped else "", blob_max, dT),
                     "severity": sev, "source": "vision.thermal"}
    res.words = [wd.shifted(0, 0, frame.scale) for wd in words]
    res.extra_marks = [Mark("box", frame.box_to_orig([x0, top, x1, bot]))]
    return res
