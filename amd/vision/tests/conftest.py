"""Shared fixtures. Kit-image tests skip cleanly when the SPOT kit is absent (VISION_KIT_DIR overrides the path)."""
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

KIT = Path(os.environ.get("VISION_KIT_DIR") or
           ROOT.parents[1] / "SPOTDATA" / "SPOT_KnightHacks_Challenge_Kit Part One")
SAMPLES = KIT / "04_ASSETS" / "sample_inspection_images"
ORBIT = KIT / "01_REFERENCE" / "Approved_Orbit_Screenshots"

requires_kit = pytest.mark.skipif(not SAMPLES.is_dir(), reason="SPOT kit images not present (set VISION_KIT_DIR)")
requires_orbit = pytest.mark.skipif(not ORBIT.is_dir(), reason="Orbit screenshots not present (set VISION_KIT_DIR)")


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def orbit_shot(stamp: str) -> Path:
    """Screenshot by its time stamp, e.g. '11.29.51'. File names contain a narrow no-break space, so glob."""
    hits = sorted(ORBIT.glob("*%s*.png" % stamp))
    assert hits, "no Orbit screenshot matching %s" % stamp
    return hits[0]


@pytest.fixture
def frame_of():
    from vision.imageio import downscale
    from vision.result import Frame

    def make(rgb, max_side=1280):
        work, s = downscale(rgb, max_side)
        return Frame(orig=rgb, work=work, scale=s)
    return make


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: runs every Orbit screenshot (~45 s); deselect with -m 'not slow'")
