# syntax=docker/dockerfile:1
# Backend API (FastAPI), port 8000. CPU-only and torch-free: Laya runs in its own service (SYSTEM1_URL).
# Build context is the REPO ROOT, so the image can COPY the shared triage code and the kit data for /replay:
#
#   docker build -f backend/Dockerfile -t spot-backend .
#   docker run --rm -p 8000:8000 -e DATABASE_URL=... -e SYSTEM1_URL=http://host.docker.internal:8082 spot-backend
#
# backend/Dockerfile.dockerignore (a symlink to backend/.dockerignore) limits what is sent to the builder.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# Shared System 1 code (imported, never modified) and the kit CSVs + replay.ndjson.
COPY amd/system1/triage/ amd/system1/triage/
COPY amd/system1/data/kit/ amd/system1/data/kit/
COPY backend/app/ backend/app/

RUN useradd --create-home --uid 10001 app
USER app

# Defaults for docker-compose (services reach each other by name). Override any of them with -e.
ENV PORT=8000 \
    TRIAGE_DIR=/app/amd/system1 \
    KIT_DIR=/app/amd/system1/data/kit \
    TRIAGE_MODE=serial \
    SYSTEM1_URL=http://system1:8082 \
    EMBED_URL=http://embed:8081 \
    EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B \
    EMBED_DIM=1024 \
    MCP_URL=http://mcp:8090/mcp

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health?deep=false' % os.environ.get('PORT','8000'), timeout=2)" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT} --proxy-headers --no-access-log"]
