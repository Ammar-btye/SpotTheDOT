"""Decode, bound, downscale and encode images. Raises ImageError(status, message) for the API to map.

Only JPEG, PNG and WebP are opened (docs/vision-contract.md, decided 2026-10-10: WebP was already supported; BMP, GIF,
TIFF and every other Pillow plugin are refused). The pixel limit is checked from the image header, before the raster
is decoded; Pillow's own decompression-bomb check stays on as a backstop at HARD_MAX_PIXELS.
"""
import base64
import binascii
import hashlib
import io
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

from .config import HARD_MAX_PIXELS

Image.MAX_IMAGE_PIXELS = HARD_MAX_PIXELS   # backstop; our own (lower) limit is checked from the header first
FORMATS = ("JPEG", "PNG", "WEBP")


class ImageError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Decoded:
    rgb: np.ndarray        # H x W x 3 uint8, original resolution
    sha256: str
    nbytes: int

    @property
    def size(self):
        return self.rgb.shape[1], self.rgb.shape[0]


def decode_b64(image_b64: str, max_bytes: int, max_pixels: int) -> Decoded:
    """base64 (or data: URL) -> RGB array. 413 when too big, 422 when not an image."""
    if not isinstance(image_b64, str) or not image_b64.strip():
        raise ImageError(422, "image_b64 is empty")
    s = image_b64.strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    if len(s) > (max_bytes * 4) // 3 + 8:     # before decoding: never allocate for an oversized string
        raise ImageError(413, "image_b64 exceeds the %d-byte image limit" % max_bytes)
    try:
        raw = base64.b64decode(s, validate=False)
    except (binascii.Error, ValueError):
        raise ImageError(422, "image_b64 is not valid base64")
    if len(raw) > max_bytes:
        raise ImageError(413, "decoded image is %d bytes; limit is %d" % (len(raw), max_bytes))
    return decode_bytes(raw, max_pixels)


def decode_bytes(raw: bytes, max_pixels: int) -> Decoded:
    try:
        im = Image.open(io.BytesIO(raw), formats=FORMATS)   # lazy: reads the header only
        w, h = im.size
    except Image.DecompressionBombError:
        raise ImageError(422, "image is larger than %d pixels" % HARD_MAX_PIXELS)
    except Exception:
        raise ImageError(422, "image_b64 is not a decodable JPEG, PNG or WebP image")
    if w * h > max_pixels:
        raise ImageError(422, "image is %dx%d = %d pixels; limit is %d" % (w, h, w * h, max_pixels))
    try:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            im = Image.alpha_composite(bg, im)
        rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
    except Exception:
        raise ImageError(422, "image_b64 is not a decodable image")
    return Decoded(rgb=np.ascontiguousarray(rgb), sha256=hashlib.sha256(raw).hexdigest(), nbytes=len(raw))


def downscale(rgb: np.ndarray, max_side: int):
    """(image, scale) with the long side <= max_side; scale = work px per original px (<= 1)."""
    h, w = rgb.shape[:2]
    s = min(1.0, float(max_side) / max(h, w))
    if s >= 1.0:
        return rgb, 1.0
    size = (max(1, round(w * s)), max(1, round(h * s)))
    # reducing_gap: Pillow first shrinks by an integer factor (Image.reduce, a cheap box filter), then LANCZOS for the
    # rest, so a large frame is never LANCZOS-filtered at full resolution
    im = Image.fromarray(rgb).resize(size, Image.LANCZOS, reducing_gap=3.0)
    return np.asarray(im), s


def encode_jpeg_b64(rgb: np.ndarray, quality: int = 85) -> str:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def to_b64_png(rgb: np.ndarray) -> str:
    """Test/helper: RGB array -> base64 PNG."""
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
