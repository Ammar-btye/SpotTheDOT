"""Start the System 2 stub API (fixtures behind the real contract) so web can build against it. Run from amd/system2:

    AMD_API_KEY=... python scripts/serve.py
    AMD_API_KEY=... python scripts/serve.py --port 8100
    AMD_API_KEY=... uv run --no-project --with-requirements requirements.txt python scripts/serve.py

Binds 127.0.0.1 by default (T-01-11): remote callers reach it through an SSH tunnel
(`ssh -L 8000:127.0.0.1:8000 <box>`), never a public interface. Refuses to start (exit 2, before binding any port)
unless AMD_API_KEY holds a shared secret of at least MIN_KEY_LEN characters (T-01-12). The key is never logged.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from analyst.api import FIXTURES, MIN_KEY_LEN, create_app  # noqa: E402
from analyst.contract import CONTRACT_VERSION  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LOOPBACK = ("127.0.0.1", "localhost", "::1")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Serve the System 2 stub /v1/assess on localhost.")
    ap.add_argument("--host", default="127.0.0.1", help="bind address; keep loopback and tunnel in over SSH")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--fixtures", default=str(FIXTURES), help="directory of fixture *.json pairs")
    ap.add_argument("--log-level", default="info", choices=["critical", "error", "warning", "info", "debug"])
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    key = os.environ.get("AMD_API_KEY", "")
    if len(key) < MIN_KEY_LEN:
        print("ERROR: set AMD_API_KEY to a shared secret of at least %d characters (it is never logged)"
              % MIN_KEY_LEN, file=sys.stderr)
        sys.exit(2)
    if args.host not in LOOPBACK:
        print("WARNING: binding %s exposes the API beyond localhost; prefer an SSH tunnel" % args.host,
              file=sys.stderr)
    app = create_app(key, Path(args.fixtures))
    print("System 2 stub on http://%s:%d | contract %s | %d fixtures"
          % (args.host, args.port, CONTRACT_VERSION, len(app.state.fixtures)), flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
