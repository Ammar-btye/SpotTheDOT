"""Reader inputs and outputs. Every coordinate here is in ORIGINAL image pixels."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .textaxes import Word


@dataclass
class Frame:
    orig: np.ndarray          # H x W x 3 uint8 RGB, original resolution
    work: np.ndarray          # downscaled copy (long side <= work_max_side)
    scale: float              # work px per original px (<= 1)

    def to_orig(self, v: float) -> float:
        return float(v) / self.scale

    def box_to_orig(self, b: Sequence[float]) -> List[int]:
        return [int(round(float(c) / self.scale)) for c in b]

    def pt_to_orig(self, p: Sequence[float]) -> List[int]:
        return [int(round(float(c) / self.scale)) for c in p]


@dataclass
class Mark:
    """What to draw for a reading: 'box' (x0,y0,x1,y1), 'line' (x0,y0,x1,y1), 'point' (x,y) or 'circle' (x,y,r)."""
    type: str
    coords: List[float]


@dataclass
class Reading:
    quantity: str
    value: float
    unit: str
    confidence: float
    method: str
    flags: List[str] = field(default_factory=list)
    bbox: Optional[List[int]] = None
    point: Optional[List[int]] = None
    note: Optional[str] = None
    primary: bool = False            # the reading compared against a logged value
    full_scale: Optional[float] = None
    clipped: bool = False
    marks: List[Mark] = field(default_factory=list)


@dataclass
class ReaderResult:
    readings: List[Reading] = field(default_factory=list)
    key_results: List[Dict[str, Any]] = field(default_factory=list)
    alert: Optional[Dict[str, Any]] = None
    flags: List[str] = field(default_factory=list)
    words: List[Word] = field(default_factory=list)
    extra_marks: List[Mark] = field(default_factory=list)   # unlabelled context marks (e.g. dial circle, colorbar)


def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def r1(x: float, nd: int = 1) -> float:
    return float(round(float(x), nd))
