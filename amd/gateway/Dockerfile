# SPOT model gateway: LiteLLM proxy on :4000 (aliases system2, system2-vision, system1, embed). See README.md.
# requirements.txt is a hashed lock of litellm[proxy]==1.104.1 (README "Supply chain"); --require-hashes refuses any
# file whose hash differs from the lock, so a re-published or tampered wheel fails the build instead of installing.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp \
    GATEWAY_HOST=0.0.0.0 GATEWAY_PORT=4000 \
    LITELLM_TELEMETRY=False LITELLM_LOCAL_MODEL_COST_MAP=True DISABLE_ADMIN_UI=True LITELLM_MODE=PRODUCTION
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && ! find / -xdev -name 'litellm_init.pth' 2>/dev/null | grep -q . \
    && useradd --uid 10001 --no-create-home gateway
COPY config.yaml laya_provider.py serve.py ./
USER 10001:10001
EXPOSE 4000
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health/liveliness' % os.environ.get('GATEWAY_PORT', '4000'), timeout=2).read()"
CMD ["python", "serve.py"]
