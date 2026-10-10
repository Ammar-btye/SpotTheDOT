# syntax=docker/dockerfile:1.7
# System 1 (Laya) inference service. Build from the REPO ROOT so the image can COPY amd/system1/triage:
#   docker build -f amd/system1/service/Dockerfile --build-arg TORCH_VARIANT=cpu -t spot-system1 .
# TORCH_VARIANT: cpu | rocm-gfx1151 (Strix Halo / Radeon 8060S) | rocm-gfx1201 (Radeon RX 9070 / AI PRO R9700)
# Model weights are NOT baked in: they download to the HF cache volume (/models/hf) on first start, or mount a
# fine-tuned checkpoint at /models/laya and set LAYA_CHECKPOINT=/models/laya.
FROM python:3.12-slim

ARG TORCH_VARIANT=cpu
ARG TORCH_CPU_VERSION=2.12.0
ARG ROCM_TORCH="torch==2.12.0+rocm7.14.1"
ARG ROCM_INDEX=https://repo.amd.com/rocm/whl-multi-arch/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TORCH_COMPILE_DISABLE=1 \
    HF_HUB_OFFLINE=0 \
    HF_HOME=/models/hf \
    LAYA_CHECKPOINT=convaiinnovations/laya \
    LAYA_DEVICE=auto \
    SPOT_AMP=1 \
    HOST=0.0.0.0 \
    PORT=8082 \
    TORCH_VARIANT=${TORCH_VARIANT}

# 1) torch FIRST, from the variant's index, so nothing later pulls the default (CUDA) wheel from PyPI.
RUN set -eux; \
    case "$TORCH_VARIANT" in \
      cpu)          pip install --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_CPU_VERSION}" ;; \
      rocm-gfx1151) pip install --index-url "$ROCM_INDEX" "torch[device-gfx1151]==2.12.0+rocm7.14.1" ;; \
      rocm-gfx1201) pip install --index-url "$ROCM_INDEX" "$ROCM_TORCH" "amd-torch-device-gfx1201==2.12.0+rocm7.14.1" ;; \
      *) echo "unknown TORCH_VARIANT=$TORCH_VARIANT (cpu | rocm-gfx1151 | rocm-gfx1201)" >&2; exit 1 ;; \
    esac; \
    python -c "import torch; print(torch.__version__)" > /opt/torch-version; cat /opt/torch-version

# 2) laya + the service. Then fail the build if anything replaced the variant's torch.
COPY amd/system1/service/requirements.txt /tmp/requirements.txt
RUN set -eux; \
    pip install --retries 10 --timeout 120 -r /tmp/requirements.txt; \
    test "$(python -c 'import torch; print(torch.__version__)')" = "$(cat /opt/torch-version)"; \
    rm /tmp/requirements.txt

# 3) non-root user, writable model dirs (mount volumes over them).
RUN set -eux; \
    useradd --create-home --uid 10001 --shell /usr/sbin/nologin app; \
    mkdir -p /models/hf /models/laya; \
    chown -R app:app /models

WORKDIR /app
COPY --chown=app:app amd/system1/triage/ /app/triage/
COPY --chown=app:app amd/system1/service/ /app/service/

USER app
VOLUME ["/models/hf"]
EXPOSE 8082

# First start downloads ~842 MB of weights: allow a long start period.
HEALTHCHECK --interval=15s --timeout=5s --start-period=600s --retries=3 \
  CMD python -c "import json,os,urllib.request as u; r=json.load(u.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8082'), timeout=4)); raise SystemExit(0 if r.get('model_loaded') else 1)"

CMD ["python", "-m", "service"]
