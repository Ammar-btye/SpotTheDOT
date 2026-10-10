# SPOT vision/OCR service (docs/vision-contract.md). Build from the repo root:  docker build -t spot-vision amd/vision
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VISION_HOST=0.0.0.0 VISION_PORT=8084 HOME=/tmp

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --uid 10001 --no-create-home vision

COPY vision ./vision
COPY scripts ./scripts
# Bake + verify the OCR models at build time (they live in site-packages/rapidocr/models): no internet at runtime.
RUN python scripts/fetch_models.py

USER 10001:10001
# VISION_API_KEY (>= 16 chars) is required at runtime: the service refuses to start without it (docs/vision-contract.md)
EXPOSE 8084
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
  CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('VISION_PORT', '8084'), timeout=2).status == 200 else 1)"
CMD ["python", "scripts/serve.py"]
