#!/usr/bin/env bash
# Entrypoint of the db tooling container (also usable on a host with the db/ venv active).
#   all            migrate + seed + ingest (waits for the embedding service)
#   migrate|seed|reset|status ...   -> python db/setup.py <cmd> [args]
#   ingest [args]  -> python amd/embed/ingest.py [args]
#   smoke [args]   -> python db/smoke_test.py [args]
set -euo pipefail
cd "$(dirname "$0")/.."
cmd="${1:-all}"; shift || true
case "$cmd" in
  all)    python db/setup.py migrate && python db/setup.py seed && python amd/embed/ingest.py "$@" \
            && python db/setup.py status ;;
  migrate|seed|reset|status) python db/setup.py "$cmd" "$@" ;;
  ingest) python amd/embed/ingest.py "$@" ;;
  smoke)  python db/smoke_test.py "$@" ;;
  *) echo "usage: job.sh all|migrate|seed|reset|status|ingest|smoke [args]" >&2; exit 2 ;;
esac
