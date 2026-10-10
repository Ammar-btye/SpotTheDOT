# AMD GPU instance: specs, access and what they mean for us

_Measured 2026-10-10 over SSH on an AMD one-click / lablab runtime instance. The values
come from `amd-smi`, sysfs/KFD, cgroups and a PyTorch run; nothing is copied from a datasheet._

## Access
```bash
ssh spot-amd        # ~/.ssh/config entry: HostName/Port from the AMD console's SSH line, User root, your key
```
- **Each teammate adds their own public key** in the AMD console's SSH-key settings, then relaunches the instance.
  Never share private keys. The console shows the SSH line (`ssh root@<ip> -p <port>`).
- **The host and port change on every relaunch** (and the host key changes with them). Keep them in your local
  `~/.ssh/config`, not in this public repo:
  ```
  Host spot-amd
      HostName <ip from console>
      Port <port from console>
      User root
      IdentityFile ~/.ssh/<your key>
      IdentitiesOnly yes
  ```
- **SSH sessions don't inherit the notebook's proxy.** Before any `pip`/`git`/`curl`:
  ```bash
  export HTTPS_PROXY=http://notebook-egress-proxy.amd-oneclick-lablab.svc.cluster.local:3128
  export HTTP_PROXY=$HTTPS_PROXY https_proxy=$HTTPS_PROXY http_proxy=$HTTPS_PROXY
  ```
- The address in the instance's `no_proxy` is the notebook's web gateway; SSH is not on its port 22, so use the console's SSH line.

## Hardware (this container)
| | Value |
|---|---|
| **GPU** | **AMD Radeon Pro W7900D**, PCI `1002:744b`, 1 GPU assigned to this container (`/dev/dri/card1`, `renderD128`). The host has 8 of them. |
| Architecture | **gfx1100** (RDNA 3, Navi 31) |
| Compute units | 96 CUs (`amd-smi`). PyTorch's `multi_processor_count` reports 48, which counts work-group processors (2 CUs each). |
| VRAM | **48 GiB GDDR6** (49,136 MB), Samsung, 384-bit |
| GTT (host-visible) | 252 GiB |
| Link | PCIe 4.0 x16 (16 GT/s) |
| Power limit | 241 W (min 144 W); slowdown at 100 °C edge / 110 °C hotspot |
| Measured matmul (8192³) | **fp16 65.4 TFLOPS, bf16 65.5 TFLOPS**; fp32 only 1.3 TFLOPS (see "What it means") |
| CPU | Host: 2 × AMD EPYC 9334 (32 cores each, 128 threads). **Container: 16 CPUs** (`cpu.max` 1600000/100000) |
| RAM | Host 503 GiB. **Container limit 55 GiB** (cgroup `memory.max` 59,055,800,320 B). No swap. |
| Disk | `/` overlay 3.5 TB (2.0 TB free, shared). **`/tmp` is only a 4 GB tmpfs**; `/dev/shm` is 32 GB. |

## Software
| | Value |
|---|---|
| OS / kernel | Ubuntu 26.04 LTS, Linux 6.8.0-79-generic |
| Driver | amdgpu 6.16.13 |
| ROCm | 10.0.0, installed as pip packages in **`/opt/venv`** (amd-smi 27.0.0, `hipcc`, `amdclang`). There is no `/opt/rocm`, and `rocminfo` isn't installed. |
| Python | 3.14.4 (system and `/opt/venv`) |
| PyTorch | **`/opt/venv`: torch 2.13.0+rocm10.0.0 (HIP 7.15), triton 3.8.0. It works on the GPU.** System Python has no torch. |
| User | `root`, but **no Docker or Podman** (a Kubernetes pod) |

## Network (outbound only through the proxy above)
| Destination | Result |
|---|---|
| repo.amd.com (ROCm wheels), pypi.org, github.com, download.pytorch.org | ✅ 200 |
| hf-mirror.com (public HF mirror) | ✅ 200 |
| **huggingface.co, cdn-lfs.huggingface.co** | ❌ **times out (blocked or hanging at the proxy)** |
| Docker Hub (registry-1.docker.io) | ❌ blocked |
| Inbound | SSH only, via the platform's port mapping |

## What it means for SPOTlight
1. **The GPU is not the 8060S/R9700 we planned around.** It's `gfx1100`, which our Docker `TORCH_VARIANT`s
   (`cpu|rocm-gfx1151|rocm-gfx1201`) don't cover. There's no Docker here anyway, so services run **natively**.
   Use the already-working `/opt/venv` torch and install our requirements into it (`laya` and the rest don't replace
   torch; re-check `torch.__version__` shows `+rocm10.0.0` after installing). AMD's index also carries
   `amd-torch-device-gfx1100` if a separate venv is needed.
2. **Use fp16/bf16, not fp32.** The fp32 GEMM path measured ~50× slower (1.3 vs 65 TFLOPS). Keep AMP on: don't
   pass `--no-amp` to `finetune.py`, and keep `SPOT_AMP=1` for the Laya service.
3. **Everything fits on one card.** 48 GB VRAM holds Laya (421M), Qwen3-Embedding-0.6B and Qwen3.5-9B (Q4 GGUF ≈ 6 GB
   plus KV cache) at the same time. The container's 55 GiB RAM limit and 16 CPUs are the tighter constraints. Laya
   fine-tuning should run much faster here than on the 8060S (65 fp16 TFLOPS on a dedicated card).
4. **Models can't come from huggingface.co.** In order of preference:
   - copy them from a laptop that has them cached:
     `rsync -a ~/.cache/huggingface/hub/models--convaiinnovations--laya ~/.cache/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B spot-amd:/root/.cache/huggingface/hub/`
   - fine-tuned checkpoints: `rsync -a amd/system1/checkpoints/<run>/best spot-amd:/root/models/`
   - otherwise `export HF_ENDPOINT=https://hf-mirror.com` (a third-party mirror; Laya ships safetensors, but verify the
     revision hash matches).
   Point `HF_HOME` at disk (e.g. `/root/.cache/huggingface`), never `/tmp` (4 GB).
5. **Hybrid mode works through an SSH tunnel.** Run `system1` (8082), `embed` (8081) and `llama-server` (8080)
   natively here, then from the laptop:
   `ssh -N -L 18082:localhost:8082 -L 18081:localhost:8081 -L 18080:localhost:8080 spot-amd &`, then run the compose
   `hybrid` profile exactly as in `docs/RUNNING.md` "Mode 2" (it expects those host ports: 18082 Laya, 18081 embed,
   18080 llama-server).
6. **Treat the instance as ephemeral.** A relaunch changes the address and port. Copy results off (or push to the HF
   Hub through the mirror/rsync route) as soon as a run finishes.

## Other AMD instances seen this weekend
| Instance | GPU | Arch | Memory | Notes |
|---|---|---|---|---|
| `jupyter-amducf07` (`/ryzers/notebooks`) | Radeon 8060S (Strix Halo iGPU) | gfx1151 | 64 GB unified | Jupyter only, user `jovyan`, no root. run2 fine-tune ran here. |
| `jupyter-amducf07` (`/opt/workspace`) | Radeon AI PRO R9700 | gfx1201 | 32 GB | needed `amd-torch-device-gfx1201` |
| **SSH instance (this one)** | **Radeon Pro W7900D** | **gfx1100** | **48 GB** | root, SSH, proxy egress, HF blocked |
