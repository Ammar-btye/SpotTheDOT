"""Download and verify the RapidOCR ONNX models once (Docker build step; first native setup).

RapidOCR stores them inside its package directory (rapidocr/models/), so after this runs the service needs no
internet. Exits 1 if a smoke OCR of a rendered '123' fails.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from vision import textaxes  # noqa: E402


def main():
    from rapidocr import RapidOCR
    RapidOCR(params={"Global.log_level": "error"})          # default config pulls det + cls + rec
    im = Image.new("RGB", (240, 80), (255, 255, 255))
    ImageDraw.Draw(im).text((20, 15), "123", fill=(0, 0, 0), font=ImageFont.load_default(size=40))
    words = textaxes.ocr(np.asarray(im))
    texts = [w.text for w in words]
    if not any("123" in t for t in texts):
        print("OCR smoke test failed: %r" % texts, file=sys.stderr)
        sys.exit(1)
    import rapidocr
    print("RapidOCR models ready in %s" % (Path(rapidocr.__file__).parent / "models"))


if __name__ == "__main__":
    main()
