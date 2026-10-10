"""Env-var configuration (docs/vision-contract.md "Environment"). Read once per create_app()."""
import os
from dataclasses import dataclass
from typing import Optional

MIN_KEY_LEN = 16
HARD_MAX_PIXELS = 50_000_000   # VISION_MAX_PIXELS may not exceed this; also PIL's own decompression-bomb backstop


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError("%s must be an integer, got %r" % (name, raw))


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise RuntimeError("%s must be a number, got %r" % (name, raw))


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def key_problem(key: str) -> Optional[str]:
    """Why `key` cannot be the shared secret, or None. Never includes the key (same rules as System 2)."""
    if len(key) < MIN_KEY_LEN:
        return "it has fewer than %d characters" % MIN_KEY_LEN
    if key != key.strip():
        return "it has leading or trailing whitespace"
    if not key.isascii():
        return "it has non-ASCII characters"
    if not key.isprintable():
        return "it has non-printable characters"
    return None


@dataclass(frozen=True)
class Settings:
    api_key: Optional[str] = None
    allow_no_auth: bool = False
    max_image_bytes: int = 12_000_000
    max_pixels: int = 12_000_000
    work_max_side: int = 1280
    cache_size: int = 64
    ocr_threads: int = -1
    max_concurrency: int = 2
    queue_timeout_s: float = 3.0

    @property
    def max_body_bytes(self) -> int:
        """Largest accepted request body: base64 of max_image_bytes plus 64 KiB for the JSON around it."""
        return (self.max_image_bytes * 4) // 3 + 8 + 65536

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.environ.get("VISION_API_KEY") or None
        s = cls(api_key=key, allow_no_auth=_flag("VISION_ALLOW_NO_AUTH"),
                max_image_bytes=_int("VISION_MAX_IMAGE_BYTES", cls.max_image_bytes),
                max_pixels=_int("VISION_MAX_PIXELS", cls.max_pixels),
                work_max_side=_int("VISION_WORK_MAX_SIDE", cls.work_max_side),
                cache_size=_int("VISION_CACHE_SIZE", cls.cache_size),
                ocr_threads=_int("VISION_OCR_THREADS", cls.ocr_threads),
                max_concurrency=_int("VISION_MAX_CONCURRENCY", cls.max_concurrency),
                queue_timeout_s=_float("VISION_QUEUE_TIMEOUT_S", cls.queue_timeout_s))
        s.check()
        return s

    def check(self) -> None:
        """RuntimeError for an unusable setting or a missing key (unless allow_no_auth); never prints the key."""
        if self.max_image_bytes <= 0 or self.max_pixels <= 0 or self.work_max_side < 256:
            raise RuntimeError("VISION_MAX_IMAGE_BYTES/VISION_MAX_PIXELS must be > 0 and VISION_WORK_MAX_SIDE >= 256")
        if self.max_pixels > HARD_MAX_PIXELS:
            raise RuntimeError("VISION_MAX_PIXELS must be at most %d" % HARD_MAX_PIXELS)
        if self.max_concurrency < 1 or not 0 <= self.queue_timeout_s <= 60:
            raise RuntimeError("VISION_MAX_CONCURRENCY must be >= 1 and VISION_QUEUE_TIMEOUT_S within 0..60")
        if self.api_key is None:
            if not self.allow_no_auth:
                raise RuntimeError("VISION_API_KEY is not set (>= %d printable ASCII characters); set "
                                   "VISION_ALLOW_NO_AUTH=1 only for tests" % MIN_KEY_LEN)
            return
        why = key_problem(self.api_key)
        if why:
            raise RuntimeError("VISION_API_KEY is unusable: %s (the key is never logged)" % why)
