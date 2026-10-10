"""Optional, fire-and-forget logging of /v1/predict calls to `app.model_calls` (docs/system2-rag-contract.md §6).

Rows go through a bounded queue to one background thread, so a slow or unreachable database never adds
latency to, or fails, a request. When the queue is full, or an insert fails, the row is dropped with a
warning. Disabled (a no-op) unless LOGS_DATABASE_URL is set.
"""
import json
import logging
import queue
import threading
import time
from typing import Optional

log = logging.getLogger("system1.calllog")

INSERT = ("INSERT INTO app.model_calls (request_id, system, model, endpoint, action_id, latency_ms, device, ok, "
          "error, metadata) VALUES (%s, 'system1', %s, %s, %s, %s, %s, %s, %s, %s::jsonb)")


class CallLogger:
    def __init__(self, dsn: Optional[str], maxsize: int = 1000):
        self.dsn = dsn
        self.q: "queue.Queue" = queue.Queue(maxsize=maxsize)
        self.dropped = 0
        self._thread: Optional[threading.Thread] = None
        self._conn = None
        if dsn:
            self._thread = threading.Thread(target=self._run, name="model-calls-log", daemon=True)
            self._thread.start()

    @property
    def enabled(self) -> bool:
        return self._thread is not None

    def log(self, *, request_id: Optional[str], model: str, endpoint: str, latency_ms: int, device: str, ok: bool,
            error: Optional[str] = None, action_id: Optional[str] = None, metadata: Optional[dict] = None) -> None:
        if not self.enabled:
            return
        row = (request_id, model, endpoint, action_id, latency_ms, device, ok, (error or None) and error[:2000],
               json.dumps(metadata or {}, default=str))
        try:
            self.q.put_nowait(row)
        except queue.Full:
            self.dropped += 1
            if self.dropped % 100 == 1:
                log.warning("model_calls log queue full; dropped %d row(s)", self.dropped)

    def close(self, timeout: float = 2.0) -> None:
        if not self.enabled:
            return
        try:
            self.q.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout)

    # ── worker ──
    def _connect(self):
        import psycopg
        return psycopg.connect(self.dsn, autocommit=True, connect_timeout=5)

    def _run(self) -> None:
        backoff = 0.0
        while True:
            row = self.q.get()
            if row is None:
                break
            if backoff and time.monotonic() < backoff:
                self.dropped += 1          # DB recently unreachable: drop instead of piling up
                continue
            try:
                if self._conn is None or self._conn.closed:
                    self._conn = self._connect()
                with self._conn.cursor() as cur:
                    cur.execute(INSERT, row)
                backoff = 0.0
            except Exception as err:       # never let logging take the service down
                log.warning("could not log to app.model_calls (%s: %s)", type(err).__name__, err)
                try:
                    if self._conn is not None:
                        self._conn.close()
                except Exception:
                    pass
                self._conn = None
                backoff = time.monotonic() + 30.0
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
