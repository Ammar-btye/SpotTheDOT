"""Serve the packet-grounded stub on localhost:8083.

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

ROOT = Path(__file__).resolve().parents[1]
LOOPBACK = ("127.0.0.1", "localhost", "::1")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Serve the System 2 stub /v1/assess on localhost.")
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
    app = create_app(key, Path(args.fixtures))
    print("System 2 stub on http://%s:%d" % (args.host, args.port), flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
