#!/usr/bin/env bash
# Smoke-test the gateway. Uses amd/gateway/.venv when present, else python3 (needs httpx; --stubs needs the lock).
#   amd/gateway/scripts/smoke.sh --stubs                                   # offline: stubs + local gateway
#   LITELLM_MASTER_KEY=sk-... amd/gateway/scripts/smoke.sh                 # a running gateway on :4000
#   GATEWAY_URL=http://127.0.0.1:4000 amd/gateway/scripts/smoke.sh --only system2,embed --image gauge.png
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
py="$here/.venv/bin/python"
[ -x "$py" ] || py="python3"
exec "$py" "$here/scripts/smoke.py" "$@"
