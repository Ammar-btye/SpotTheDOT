"""Shared helpers for db/setup.py and amd/embed/ingest.py: paths, connections, job logging.

Pure Python + psycopg 3. No torch, so the db tooling container stays CPU-only and small.
"""
import contextlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import parse_qs, urlparse

import psycopg

REPO = Path(__file__).resolve().parents[1]
DB_DIR = REPO / "db"
SYSTEM1_DIR = REPO / "amd" / "system1"
KIT_DIR = Path(os.environ.get("SPOT_KIT_DIR", SYSTEM1_DIR / "data" / "kit"))
MANUAL_DIR = Path(os.environ.get("SPOT_MANUAL_DIR", REPO / "SPOTDATA" / "SPOT_KnightHacks_Challenge_Kit Part Two"))
MEDIA_DIR = Path(os.environ.get(
    "SPOT_MEDIA_DIR", REPO / "SPOTDATA" / "SPOT_KnightHacks_Challenge_Kit Part One" / "04_ASSETS" / "sample_inspection_images"))

# The System 1 triage package (kit loader, event builders, renderers, policy) lives in amd/system1/triage.
if str(SYSTEM1_DIR) not in sys.path:
    sys.path.insert(0, str(SYSTEM1_DIR))


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set (Neon: copy the connection string from the console; local: db/local_pgvector.sh)")
    return url


def logs_database_url() -> str:
    return os.environ.get("LOGS_DATABASE_URL") or database_url()


def _with_ssl(url: str) -> str:
    """Neon requires TLS. Add sslmode=require if a Neon URL lacks it (local URLs are left alone)."""
    u = urlparse(url)
    if (u.hostname or "").endswith((".neon.tech", ".neon.build")) and "sslmode" not in parse_qs(u.query):
        return url + ("&" if u.query else "?") + "sslmode=require"
    return url


def connect(url: Optional[str] = None, autocommit: bool = False) -> psycopg.Connection:
    # prepare_threshold=None: no server-side prepared statements, so Neon's pooled (-pooler, PgBouncer) URLs work.
    return psycopg.connect(_with_ssl(url or database_url()), autocommit=autocommit, prepare_threshold=None)


def redact(url: str) -> str:
    u = urlparse(url)
    if u.password:
        url = url.replace(":" + u.password + "@", ":***@")
    return url


def has_table(conn: psycopg.Connection, qualified: str) -> bool:
    return conn.execute("SELECT to_regclass(%s) IS NOT NULL", (qualified,)).fetchone()[0]


class JobRun:
    """Mutable counts for an app.job_runs row."""

    def __init__(self, run_id: Optional[int]):
        self.run_id = run_id
        self.counts: dict = {}
        self.metadata: dict = {}


@contextlib.contextmanager
def job_run(job: str, metadata: Optional[dict] = None) -> Iterator[JobRun]:
    """Log a job to app.job_runs (on LOGS_DATABASE_URL). No-op with a warning if app.* doesn't exist yet."""
    run = JobRun(None)
    run.metadata = dict(metadata or {})
    conn = None
    try:
        conn = connect(logs_database_url(), autocommit=True)
        if has_table(conn, "app.job_runs"):
            run.run_id = conn.execute(
                "INSERT INTO app.job_runs (job, metadata) VALUES (%s, %s) RETURNING run_id",
                (job, json.dumps(run.metadata))).fetchone()[0]
        else:
            print("warning: app.job_runs missing (run `python db/setup.py migrate`); job not logged", file=sys.stderr)
    except psycopg.Error as e:
        print("warning: could not log job start: %s" % e, file=sys.stderr)
    t0 = time.perf_counter()
    try:
        yield run
    except BaseException as e:
        _finish(conn, run, "error", repr(e), t0)
        raise
    else:
        _finish(conn, run, "ok", None, t0)
    finally:
        if conn is not None:
            conn.close()


def _finish(conn, run: JobRun, status: str, error: Optional[str], t0: float) -> None:
    if conn is None or run.run_id is None:
        return
    run.metadata["seconds"] = round(time.perf_counter() - t0, 2)
    try:
        conn.execute(
            "UPDATE app.job_runs SET finished_at = now(), status = %s, counts = %s, error = %s, metadata = %s "
            "WHERE run_id = %s",
            (status, json.dumps(run.counts), error, json.dumps(run.metadata, default=str), run.run_id))
    except psycopg.Error as e:
        print("warning: could not log job end: %s" % e, file=sys.stderr)


def log_model_call(conn: psycopg.Connection, **f) -> None:
    """Append one row to app.model_calls. `conn` should be an autocommit connection to the logs DB."""
    cols = ["request_id", "system", "model", "endpoint", "flag_id", "action_id", "input_tokens", "output_tokens",
            "latency_ms", "tokens_per_sec", "device", "ok", "error", "metadata"]
    vals = [json.dumps(f.get(c) or {}) if c == "metadata" else f.get(c) for c in cols]
    conn.execute("INSERT INTO app.model_calls (%s) VALUES (%s)" % (", ".join(cols), ", ".join(["%s"] * len(cols))),
                 vals)
