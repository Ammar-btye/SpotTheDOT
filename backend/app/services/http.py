"""Shared plumbing for the HTTP clients: a circuit breaker and a typed "service unavailable" error.

The breaker matters for the live demo: if System 1 is black-holed, every replay event would otherwise wait
for the full timeout. After a failure the breaker stays open for BREAKER_COOLDOWN_S, so callers fall back
instantly; the next call after the cooldown probes the service again.
"""
from __future__ import annotations

import time
from typing import Optional


class ServiceUnavailable(RuntimeError):
    def __init__(self, service: str, reason: str):
        super().__init__("%s unavailable: %s" % (service, reason))
        self.service = service
        self.reason = reason


class Breaker:
    def __init__(self, cooldown_s: float = 10.0):
        self.cooldown_s = cooldown_s
        self.open_until = 0.0
        self.last_error: Optional[str] = None
        self.failures = 0

    def allow(self) -> bool:
        return time.monotonic() >= self.open_until

    def success(self) -> None:
        self.open_until, self.failures, self.last_error = 0.0, 0, None

    def failure(self, error: str) -> None:
        self.failures += 1
        self.last_error = error
        self.open_until = time.monotonic() + self.cooldown_s

    def reset(self) -> None:
        self.success()

    @property
    def state(self) -> str:
        return "closed" if self.allow() else "open"


def short_error(exc: BaseException) -> str:
    name = type(exc).__name__
    msg = str(exc).strip()
    return ("%s: %s" % (name, msg))[:300] if msg else name
