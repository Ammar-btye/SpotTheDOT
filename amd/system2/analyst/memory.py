"""Peak amdgpu device memory during a report run, sampled from sysfs (EVAL-05).

Reads /sys/class/drm/card*/device/mem_info_vram_used and mem_info_gtt_used. These are world-readable, so this
works without root on the Radeon Cloud Jupyter VM. On the gfx1151 APU the model weights largely live in GTT (unified
memory), so both VRAM and GTT are reported and summed. The numbers are system-wide device memory in use: they
include the already-loaded model and any other process, not just this run's extra allocations. If the files are
missing (container, non-AMD host, no driver), nothing is measured and the result says so instead of guessing.
Connector entries such as card0-DP-1 are ignored. Stdlib only; never raises on unreadable files.
"""
from __future__ import annotations

from pathlib import Path
import re
import threading
from typing import Optional

DRM_ROOT = Path('/sys/class/drm')
CARD = re.compile(r'^card\d+$')
MIB = 1024 * 1024
SCOPE = ('system-wide amdgpu VRAM+GTT in use while the report ran, including the loaded model and any other process')
DISABLED = 'memory sampling disabled (--mem-source none)'


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding='ascii').strip()
    except (OSError, ValueError):
        return None


def _int(path: Path) -> Optional[int]:
    text = _read(path)
    try:
        return int(text) if text else None
    except ValueError:
        return None


def _sizes(values: Optional[dict]) -> Optional[dict]:
    if values is None:
        return None
    out = {}
    for k in ('vram', 'gtt', 'total'):
        out[k + '_bytes'] = values[k]
        out[k + '_mib'] = round(values[k] / MIB, 1)
    return out


class MemorySampler:
    """sample() once, or start()/stop() a daemon thread sampling every interval_s; stop() returns the result dict."""

    def __init__(self, drm_root: Path = DRM_ROOT, interval_s: float = 0.5, enabled: bool = True):
        self.drm_root, self.interval_s, self.enabled = Path(drm_root), float(interval_s), enabled
        self.baseline = self.peak = None
        self.samples, self.cards = 0, []
        self._stop, self._thread, self._result = threading.Event(), None, None
        self._lock = threading.Lock()

    def _cards(self):
        try:
            entries = sorted(p for p in self.drm_root.iterdir() if CARD.match(p.name))
        except OSError:
            return []
        return [p for p in entries
                if (p / 'device/mem_info_vram_used').is_file() and (p / 'device/mem_info_gtt_used').is_file()]

    def sample(self) -> Optional[dict]:
        """Read every card once; update baseline/peak; the summed {vram, gtt, total} in bytes, or None."""
        if not self.enabled:
            return None
        cards, vram, gtt, found = [], 0, 0, False
        for card in self._cards():
            v, g = _int(card / 'device/mem_info_vram_used'), _int(card / 'device/mem_info_gtt_used')
            if v is None or g is None:
                continue
            found = True
            vram, gtt = vram + v, gtt + g
            cards.append({'card': card.name, 'vendor': _read(card / 'device/vendor'),
                          'device': _read(card / 'device/device')})
        if not found:
            return None
        total = {'vram': vram, 'gtt': gtt, 'total': vram + gtt}
        with self._lock:
            self.samples += 1
            self.cards = cards
            if self.baseline is None:
                self.baseline = total
            if self.peak is None or total['total'] > self.peak['total']:
                self.peak = total
        return total

    def _loop(self):
        while not self._stop.wait(self.interval_s):
            self.sample()

    def start(self) -> 'MemorySampler':
        if self.enabled and self._thread is None and self._result is None:
            self.sample()
            self._thread = threading.Thread(target=self._loop, name='memory-sampler', daemon=True)
            self._thread.start()
        return self

    def stop(self) -> dict:
        """Final sample, join the thread, return the result; idempotent."""
        if self._result is not None:
            return self._result
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self.sample()
        if not self.enabled:
            available, reason = False, DISABLED
        elif self.peak is None:
            available, reason = False, 'no readable amdgpu mem_info_vram_used/mem_info_gtt_used under %s' % (
                self.drm_root)
        else:
            available, reason = True, None
        self._result = {'source': 'sysfs', 'drm_root': str(self.drm_root), 'available': available, 'reason': reason,
                        'interval_s': self.interval_s, 'samples': self.samples, 'cards': list(self.cards),
                        'baseline': _sizes(self.baseline), 'peak': _sizes(self.peak), 'scope': SCOPE}
        return self._result

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False
