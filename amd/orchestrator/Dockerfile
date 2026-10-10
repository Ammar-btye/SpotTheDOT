# syntax=docker/dockerfile:1
# SPOT orchestrator (LangGraph), port 8085. CPU-only; build context is this folder:
#
#   docker build -t spot-orchestrator amd/orchestrator
#   docker run --rm -p 8085:8085 -e ORCHESTRATOR_API_KEY=... -e MCP_URL=http://host.docker.internal:8090/mcp \
#     -e GATEWAY_URL=http://host.docker.internal:4000 -e SYSTEM2_URL=http://host.docker.internal:8083 spot-orchestrator
#
# Configured only by env vars (docs/orchestrator-contract.md). Demo images (DEMO_IMAGES=1) are mounted read-only at
# /app/demo-images (compose: ./web/public/kit/inspection).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && useradd --system --uid 10001 --no-create-home orch
COPY orchestrator ./orchestrator

USER 10001:10001
ENV ORCHESTRATOR_HOST=0.0.0.0 ORCHESTRATOR_PORT=8085 \
    MCP_URL=http://mcp:8090/mcp GATEWAY_URL=http://gateway:4000 VISION_URL=http://vision:8084 \
    SYSTEM2_URL=http://system2:8083 DEMO_IMAGES_DIR=/app/demo-images
EXPOSE 8085

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('ORCHESTRATOR_PORT','8085'), timeout=2)" || exit 1

CMD ["python", "-m", "orchestrator"]
