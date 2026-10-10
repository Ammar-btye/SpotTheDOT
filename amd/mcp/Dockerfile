# SPOT context MCP server. Build from the repo root:  docker build -t spot-mcp amd/mcp
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN pip install --no-cache-dir "mcp>=2.3,<3" "psycopg[binary]>=3.2,<4" "psycopg-pool>=3.2,<4"

COPY spot_mcp ./spot_mcp
COPY client_example.py .

RUN useradd --system --uid 10001 --no-create-home mcp
USER mcp

# HTTP by default on a fixed port; all other config comes from the contract env vars
# (DATABASE_URL, LOGS_DATABASE_URL, EMBED_URL, EMBED_MODEL, EMBED_DIM, EMBED_QUERY_PREFIX, MCP_MIN_SIMILARITY...).
ENV MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8090
EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8090/healthz', timeout=2).status == 200 else 1)"

# stdio instead:  docker run -i --rm --env-file amd/mcp/.env -e MCP_TRANSPORT=stdio spot-mcp
CMD ["python", "-m", "spot_mcp"]
