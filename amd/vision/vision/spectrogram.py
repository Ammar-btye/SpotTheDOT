"""Spectrogram reader (the kit's acoustic_valve_01.jpg: 0-20 kHz x 0-10 s, jet colours, no colorbar).

OCR the axes -> RANSAC calibrate (row -> kHz, column -> s) -> jet-LUT inversion with off-table pixels masked
(grid lines, text) -> relative band levels, peak frequency, high-frequency ratio, and burst times from peaks of the
>5 kHz energy over time. With no colorbar there is no absolute dB: every level is relative (0-1 of the colour scale).
"""
from typing import List, Optional, Tuple

import numpy as np

from . import textaxes
from .result import Frame, Mark, ReaderResult, Reading, clamp01, r1
from .thermal import invert

# matplotlib 'jet' segment data (x, value)
_JET = {"r": [(0, 0), (0.35, 0), (0.66, 1), (0.89, 1), (1, 0.5)],
        "g": [(0, 0), (0.125, 0), (0.375, 1), (0.64, 1), (0.91, 0), (1, 0)],
        "b": [(0, 0.5), (0.11, 1), (0.34, 1), (0.65, 0), (1, 0)]}
BANDS_KHZ = [(0, 2), (2, 5), (5, 10), (10, 20)]
HF_SPLIT_KHZ = 5.0


def jet_lut(n: int = 256) -> np.ndarray:
    x = np.linspace(0, 1, n)
    return np.stack([np.interp(x, *zip(*_JET[c])) for c in "rgb"], 1).astype(np.float32) * 255


def plot_area(img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """(x0, y0, x1, y1) of the saturated plot rectangle."""
    f = img.astype(np.int16)
    sat = (f.max(2) - f.min(2)) > 90
    rows = np.where(sat.mean(1) > 0.5)[0]
    cols = np.where(sat.mean(0) > 0.5)[0]
    if rows.size < 10 or cols.size < 10:
        return None

    def longest(idx):
        runs = np.split(idx, np.where(np.diff(idx) > 3)[0] + 1)
        r = max(runs, key=len)
        return int(r[0]), int(r[-1])
    y0, y1 = longest(rows)
    x0, x1 = longest(cols)
    return x0, y0, x1, y1


def _peaks(z: np.ndarray, thr: float, min_sep: int) -> List[int]:
    idx = [i for i in range(len(z)) if z[i] > thr and z[i] >= z[max(0, i - 1)] and z[i] >= z[min(len(z) - 1, i + 1)]]
    out: List[int] = []
    for i in sorted(idx, key=lambda i: -z[i]):
        if all(abs(i - j) >= min_sep for j in out):
            out.append(i)
    return sorted(out)


def read(frame: Frame, hints: Optional[dict] = None) -> ReaderResult:
    img = frame.work
    h, w = img.shape[:2]
    res = ReaderResult()
    words = textaxes.ocr(img)
    res.words = [wd.shifted(0, 0, frame.scale) for wd in words]
    area = plot_area(img)
    if area is None:
        res.flags.append("NO_PLOT")
        return res
    x0, y0, x1, y1 = area
    yt = textaxes.find_ticks([wd for wd in words if wd.cx < x0], axis="y", region=(0, y0 - 0.1 * h, x0, y1 + 0.1 * h))
    xt = textaxes.find_ticks([wd for wd in words if wd.cy > y1], axis="x", region=(x0 - 0.1 * w, y1, w, h))
    fy = textaxes.calibrate_axis(yt, "linear", expect_sign=-1) if len(yt) >= 3 else None
    fx = textaxes.calibrate_axis(xt, "linear", expect_sign=1) if len(xt) >= 3 else None
    flags = ["RELATIVE_ONLY"]
    conf = 0.8
    if fy is None:
        res.flags.append("AXIS_FIT_FAILED")
        return res
    # tick values above 200 can only be Hz (OCR drops the 'k' of 'kHz' in the kit's axis title)
    hz_scale = 0.001 if max(t.value for t in yt) > 200 else 1.0
    if fx is None:
        flags.append("TIME_AXIS_UNREAD")
        conf -= 0.1
    plot = img[y0:y1 + 1, x0:x1 + 1]
    lvl, _ = invert(plot, jet_lut(), np.linspace(0, 1, 256).astype(np.float32), max_dist=60.0)
    valid = np.isfinite(lvl)
    if valid.mean() < 0.6:
        flags.append("LOW_PALETTE_MATCH")
        conf -= 0.2
    fk = fy.value(np.arange(y0, y1 + 1)) * hz_scale            # kHz per plot row
    fmax = float(np.nanmax(fk))
    prof = np.nanmean(np.where(valid, lvl, np.nan), axis=1)
    k = max(1, len(prof) // 60)
    sm = np.convolve(np.nan_to_num(prof, nan=0.0), np.ones(2 * k + 1) / (2 * k + 1), mode="same")
    ip = int(np.argmax(sm))
    peak_khz = float(fk[ip])
    total = float(np.nansum(prof))
    hf = float(np.nansum(prof[fk > HF_SPLIT_KHZ])) / total if total > 0 else 0.0
    readings = [Reading("peak_frequency", r1(peak_khz, 2), "kHz", round(clamp01(conf), 2), "jet_lut_row_mean",
                        list(flags), point=[int(round(frame.to_orig((x0 + x1) / 2))), int(round(frame.to_orig(y0 + ip)))],
                        note="strongest band centred near %.1f kHz (relative level, no absolute dB)" % peak_khz,
                        primary=True,
                        marks=[Mark("hline", [frame.to_orig(x0), frame.to_orig(y0 + ip), frame.to_orig(x1),
                                              frame.to_orig(y0 + ip)])])]
    band_kr = []
    for lo, hi in BANDS_KHZ:
        if lo >= fmax:
            break
        m = (fk >= lo) & (fk < hi)
        if not m.any():
            continue
        lv = float(np.nanmean(prof[m]))
        readings.append(Reading("band_energy_%g_%gkhz" % (lo, hi), round(lv, 3), "relative", round(clamp01(conf), 2),
                                "jet_lut_band_mean", list(flags)))
        band_kr.append({"name": "Band %g-%g kHz" % (lo, hi), "units": "relative", "value": round(lv, 3)})
    readings.append(Reading("high_frequency_ratio", round(hf, 3), "ratio", round(clamp01(conf), 2), "jet_lut",
                            list(flags), note="share of level above %g kHz" % HF_SPLIT_KHZ))
    # bursts: broadband energy above the split over time
    burst_times: List[float] = []
    hfm = fk > HF_SPLIT_KHZ
    if hfm.sum() >= 3:
        series = np.nanmean(np.where(valid[hfm], lvl[hfm], np.nan), axis=0)
        series = np.nan_to_num(series, nan=float(np.nanmean(series)))
        sd = float(series.std())
        if sd > 1e-6:
            z = (series - series.mean()) / sd
            cols = np.arange(x0, x1 + 1)
            secs_per_px = abs(float(fx.slope)) if fx is not None else None
            min_sep = max(2, int(0.3 / secs_per_px)) if secs_per_px else max(2, len(z) // 30)
            pk = _peaks(z, 1.5, min_sep)
            if fx is not None:
                burst_times = [r1(float(fx.value(cols[i])), 2) for i in pk]
            for i in pk:
                res.extra_marks.append(Mark("vtick", [frame.to_orig(cols[i]), frame.to_orig(y0),
                                                      frame.to_orig(cols[i]), frame.to_orig(y0 + 0.12 * (y1 - y0))]))
    readings.append(Reading("burst_count", float(len(burst_times) if fx is not None else 0), "count",
                            round(clamp01(conf - (0.2 if fx is None else 0)), 2), "hf_energy_peaks", list(flags),
                            note=("broadband bursts at %s s" % ", ".join("%g" % t for t in burst_times))
                            if burst_times else "no broadband bursts found"))
    res.readings = readings
    res.key_results = [{"name": "Peak Frequency", "units": "kHz", "value": r1(peak_khz, 2)},
                       *band_kr,
                       {"name": "High Frequency Ratio", "units": "", "value": round(hf, 3)},
                       {"name": "Burst Times", "units": "s", "value": ", ".join("%g" % t for t in burst_times)},
                       {"name": "Frequency Range", "units": "kHz", "value": "%g–%g" % (round(float(np.nanmin(fk)), 1),
                                                                                       round(fmax, 1))},
                       {"name": "absolute_db_available", "units": "", "value": "false"}]
    if len(burst_times) >= 3:
        iv = float(np.median(np.diff(burst_times)))
        res.key_results.append({"name": "Burst Interval", "units": "s", "value": r1(iv, 2)})
    res.flags += [f for f in flags if f != "RELATIVE_ONLY"]
    res.extra_marks.append(Mark("box", frame.box_to_orig([x0, y0, x1, y1])))
    return res
