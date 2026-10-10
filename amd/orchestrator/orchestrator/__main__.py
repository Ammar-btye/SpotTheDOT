"""Run the orchestrator:  python -m orchestrator   (host/port from ORCHESTRATOR_HOST / ORCHESTRATOR_PORT)."""
import logging
import sys

import uvicorn

from .app import create_app
from .config import Settings


def main() -> None:
    s = Settings.from_env()
    logging.basicConfig(level=s.log_level, stream=sys.stderr, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        app = create_app(s)
    except RuntimeError as exc:
        raise SystemExit("orchestrator: %s" % exc) from None
    uvicorn.run(app, host=s.host, port=s.port, log_level=s.log_level.lower(), proxy_headers=True)


if __name__ == "__main__":
    main()
