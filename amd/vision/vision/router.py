"""Pick the reader: explicit kind > action_type map > colour/size heuristic > visual (OCR only)."""
from typing import Dict, Optional

import cv2
import numpy as np

KINDS = ("thermal", "gauge", "acoustic_imager", "spectrogram", "orbit_screenshot", "visual")
ACTION_TYPE_MAP = {"THERMAL_INSPECTION": "thermal", "GAUGE_READING": "gauge",
                   "ACOUSTIC_INSPECTION": "spectrogram|acoustic_imager", "VISUAL_INSPECTION": "visual"}
COLOURFUL_MIN = 0.6          # saturated share + half the near-black share (thermal backgrounds are black)


def colour_stats(img: np.ndarray) -> Dict[str, float]:
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    hue = hsv[..., 0] * (360.0 / 256.0)
    s = hsv[..., 1] / 255.0
    v = hsv[..., 2] / 255.0
    sat = (s >= 0.5) & (v >= 0.15)
    dark = v < 0.15
    f = img.astype(np.int16)
    grey = ((f.max(2) - f.min(2)) < 20) & (f.mean(2) > 20) & (f.mean(2) < 80)
    jet = sat & (hue >= 90) & (hue < 250)                 # cyan/green/blue: jet, not ironbow
    iron = sat & ((hue >= 250) | (hue < 70))              # violet/magenta/red/orange/yellow: ironbow-like
    return {"colourful": float(sat.mean() + 0.5 * dark.mean()), "jet": float(jet.mean()),
            "iron": float(iron.mean()), "ui_grey": float(grey.mean())}


def _acoustic(img: np.ndarray):
    st = colour_stats(img)
    if st["colourful"] >= COLOURFUL_MIN and st["jet"] > st["iron"]:
        return "spectrogram"
    return "acoustic_imager"


def route(img: np.ndarray, orig_size, kind: Optional[str] = None, action_type: Optional[str] = None) -> Dict:
    """img = the work image; orig_size = (W, H) of the original."""
    if kind and kind != "auto":
        return {"label": kind, "method": "kind", "confidence": 1.0}
    at = (action_type or "").strip().upper()
    if at in ACTION_TYPE_MAP:
        label = ACTION_TYPE_MAP[at]
        if label == "spectrogram|acoustic_imager":
            label = _acoustic(img)
        return {"label": label, "method": "action_type", "confidence": 1.0}
    W, H = orig_size
    st = colour_stats(img)
    if W >= 1600 and W / max(1, H) >= 1.4 and st["ui_grey"] >= 0.3:
        return {"label": "orbit_screenshot", "method": "heuristic", "confidence": round(min(1.0, 0.5 + st["ui_grey"]), 2)}
    if st["colourful"] >= COLOURFUL_MIN:
        tot = st["jet"] + st["iron"]
        margin = abs(st["jet"] - st["iron"]) / tot if tot > 0 else 0.0
        label = "spectrogram" if st["jet"] > st["iron"] else "thermal"
        return {"label": label, "method": "heuristic", "confidence": round(0.5 + 0.5 * margin, 2)}
    return {"label": "visual", "method": "default", "confidence": round(1.0 - st["colourful"], 2)}
