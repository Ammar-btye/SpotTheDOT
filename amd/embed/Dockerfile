# syntax=docker/dockerfile:1
# Embedding service (server.py): OpenAI-compatible POST /v1/embeddings + GET /health on port 8081.
#
#   CPU:           docker build --build-arg TORCH_VARIANT=cpu -t spot-embed amd/embed
#                  docker run -p 8081:8081 -v hf-cache:/models spot-embed
#   ROCm (Linux host with an AMD GPU; NOT the AMD Jupyter VMs, which have no root/Docker):
#                  docker build --build-arg TORCH_VARIANT=rocm-gfx1151 -t spot-embed:rocm amd/embed
#                  docker run --device=/dev/kfd --device=/dev/dri --group-add video \
#                    -p 8081:8081 -v hf-cache:/models spot-embed:rocm
#
# The model is downloaded on first start into /models (HF_HOME), a mounted volume, so the image stays small.
# Optional bake-in: --build-arg BAKE_MODEL=1 downloads EMBED_MODEL at build time (bigger image, no first-start
# download, works offline). Don't mount an empty bind directory over /models then (a named volume is fine: Docker
# copies the baked files into it on first use).
FROM python:3.12-slim

ARG TORCH_VARIANT=cpu
ARG BAKE_MODEL=0
ARG EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models \
    EMBED_MODEL=${EMBED_MODEL} \
    EMBED_DIM=1024 \
    EMBED_HOST=0.0.0.0 \
    EMBED_PORT=8081

WORKDIR /app

# 1) torch FIRST, from the index that matches the hardware (amd/system1/README.md; AMD gfx1151/gfx1201 wheels).
RUN set -eux; \
    case "$TORCH_VARIANT" in \
      cpu)          pip install --index-url https://download.pytorch.org/whl/cpu torch ;; \
      rocm-gfx1151) pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ \
                      "torch[device-gfx1151]==2.12.0+rocm7.14.1" ;; \
      rocm-gfx1201) pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ \
                      "torch==2.12.0+rocm7.14.1" "amd-torch-device-gfx1201==2.12.0+rocm7.14.1" ;; \
      *) echo "TORCH_VARIANT must be cpu | rocm-gfx1151 | rocm-gfx1201" >&2; exit 1 ;; \
    esac; \
    python -c "import torch; print(torch.__version__)" > /tmp/torch_version

# 2) the rest. requirements.txt has no torch; fail the build if pip swapped the wheel anyway.
COPY requirements.txt .
RUN pip install -r requirements.txt \
 && python -c "import torch; print(torch.__version__)" | diff - /tmp/torch_version \
 && echo "torch $(cat /tmp/torch_version) kept"

RUN useradd --create-home --uid 10001 app && mkdir -p /models && chown app:app /models
COPY --chown=app:app server.py client.py ./
USER app

RUN if [ "$BAKE_MODEL" = "1" ]; then \
      python -c "import os; from sentence_transformers import SentenceTransformer as S; S(os.environ['EMBED_MODEL'], device='cpu')"; \
    fi

EXPOSE 8081
# Generous start period: the first start downloads the model (~1.2 GB for Qwen3-Embedding-0.6B).
HEALTHCHECK --interval=15s --timeout=5s --start-period=600s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('EMBED_PORT','8081'), timeout=4)" || exit 1

CMD ["python", "server.py"]
