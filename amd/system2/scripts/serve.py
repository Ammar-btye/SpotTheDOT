"""Serve System 2 /v1/assess on localhost:8083: the packet-grounded stub by default, live when SYSTEM2_LLAMA_URL is set.

    python scripts/serve.py                                   # stub
    SYSTEM2_LLAMA_URL=http://127.0.0.1:8080 SYSTEM2_MODEL=qwen3.5-9b-q4km python scripts/serve.py   # live

Live mode runs the checked pipeline (analyst.live) against llama-server and needs SYSTEM2_MODEL; an incomplete or
unusable live config exits 2 before binding. SYSTEM2_CACHE_DIR sets the explanation cache (docs/RUNNING.md).

SYSTEM2_API_KEY is canonical; AMD_API_KEY is a backward-compatible alias.
Both must agree when set. SYSTEM2_HOST/SYSTEM2_PORT provide defaults; CLI
options override them. Containers bind 0.0.0.0 inside their network; native
remote callers use ssh -L 8083:127.0.0.1:8083 <box>. Secrets are never logged.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from analyst.api import FIXTURES, resolve_api_key, create_app  # noqa: E402
from analyst.evaluation import endpoint  # noqa: E402
from analyst.live import URL_ENV, assessor_from_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LOOPBACK = ("127.0.0.1", "localhost", "::1")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Serve System 2 /v1/assess on localhost: stub by default, live checked pipeline when "
                                             "SYSTEM2_LLAMA_URL (and SYSTEM2_MODEL) are set.")
    ap.add_argument("--host", default=os.environ.get("SYSTEM2_HOST", "127.0.0.1"), help="bind address; keep loopback and tunnel in over SSH")
    ap.add_argument("--port", type=int, default=os.environ.get("SYSTEM2_PORT", "8083"))
    ap.add_argument("--fixtures", default=str(FIXTURES), help="directory of fixture *.json pairs")
    ap.add_argument("--log-level", default="info", choices=["critical", "error", "warning", "info", "debug"])
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        key = resolve_api_key()
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        sys.exit(2)
    if args.host not in LOOPBACK:
        print("WARNING: binding %s exposes the API beyond localhost; prefer an SSH tunnel" % args.host,
              file=sys.stderr)
    try:
        assessor = assessor_from_env()
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        sys.exit(2)
    app = create_app(key, Path(args.fixtures), assessor=assessor)
    if assessor is None:
        print("System 2 stub on http://%s:%d" % (args.host, args.port), flush=True)
    else:
        print("System 2 live (model %s via %s) on http://%s:%d"
              % (assessor.model, endpoint(os.environ[URL_ENV].strip()), args.host, args.port), flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
