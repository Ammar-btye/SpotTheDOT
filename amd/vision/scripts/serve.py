"""Serve the vision/OCR service (docs/vision-contract.md) on VISION_HOST:VISION_PORT (default 127.0.0.1:8084).

    python scripts/serve.py                       # native (AMD Jupyter VM): keep loopback, tunnel in over SSH
    VISION_HOST=0.0.0.0 python scripts/serve.py   # container (the Dockerfile sets this)

A bad VISION_* setting exits 2 before binding. VISION_API_KEY is never logged.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from vision.api import create_app  # noqa: E402
from vision.config import Settings  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default=os.environ.get("VISION_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("VISION_PORT", "8084")))
    ap.add_argument("--log-level", default=os.environ.get("VISION_LOG_LEVEL", "info"),
                    choices=["critical", "error", "warning", "info", "debug"])
    args = ap.parse_args(argv)
    try:
        settings = Settings.from_env()
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        sys.exit(2)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(levelname)s:     %(name)s %(message)s")
    print("vision/OCR on http://%s:%d (auth %s)" % (args.host, args.port, "on" if settings.api_key else "off"),
          flush=True)
    uvicorn.run(create_app(settings), host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
