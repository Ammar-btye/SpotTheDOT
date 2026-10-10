# Serving HF models on AMD Radeon Cloud (gfx1151): ROCm, llama.cpp, models, HF angles

Researched 2026-10-09 (Fri night). Every fact has a source URL. Anything I couldn't confirm is labeled **unverified** and listed again in section 4.

## 1. Scope

- **Hardware.** Radeon 8060S (Strix Halo, RDNA 3.5, gfx1151) with 64 GB of unified memory, in four AMD environments. The OS image is unknown.
- **Goals.**
  - Serve one vision-language model (VLM) and one text model behind an OpenAI-compatible API tonight.
  - Show measured ROCm gains for AMD, whose prompt says "FSR4 or ROCm" (`research/knighthacks-ix-tracks.md`).
  - Make meaningful use of the Hugging Face ecosystem.
  - Stretch goal: a LoRA fine-tune.

## 2. Findings

### 2.1 ROCm on gfx1151

- **Official support.**
  - ROCm 7.14.0 shipped 2026-07-16 with PyTorch 2.12 and gfx1151 APU support (https://www.linuxcompatible.org/story/amd-rocm-7140-arrives-with-therock-modular-build-pytorch-212-and-new-apu-support/).
  - ROCm 10.0.0 shipped 2026-08-26 and lists gfx1151 Ryzen AI Max parts, including the Max+ 395 (https://rocm.docs.amd.com/en/docs-10.0.0/about/release-notes.html, https://phoronix.com/news/AMD-ROCm-10.0).
  - The 7.14.1 compatibility matrix lists gfx1151 on Ubuntu 24.04.4 (OEM kernel 6.17) and Ubuntu 26.04, with PyTorch 2.10–2.12 and Python 3.11–3.14 (https://rocm.docs.amd.com/en/docs-7.14.1/compatibility/compatibility-matrix.html).
- **PyTorch wheels.** AMD's install page gives this command for ROCm 7.14.1 (https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html):
  `pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1151]==2.12.0+rocm7.14.1" "torchvision[device-gfx1151]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"`
  - I confirmed these wheels and the `amd-torch-device-gfx1151` package are listed on the index tonight.
  - The ROCm 10.1 equivalent uses `https://stable.repo.amd.com/rocm/whl-next/` with `torch==2.14.0+rocm10.1.0`.
  - These wheels pull the ROCm user-space libraries as pip packages (`rocm-sdk-*` on the same index). They should not depend on a system ROCm install, but this is **unverified**: only the kernel driver should matter.
- **Gotchas.**
  - **Kernel versions.** gfx1151 needs Ubuntu 24.04 HWE 6.17.0-19 or later, OEM 6.14.0-1018 or later, or 6.18.4 or later elsewhere (https://rocm.docs.amd.com/en/latest/how-to/system-optimization/strixhalo.html).
  - **GTT memory.** `amdgpu.gttsize` is deprecated. GPU-usable shared memory is now set by the TTM `pages_limit`, either with `amd-ttm --set <GB>` from `pipx install amd-debug-tools` or through `/sys/module/ttm/parameters/pages_limit` (value in pages). Both need a reboot. AMD recommends keeping the BIOS VRAM carve-out around 0.5 GB (same URL).
  - **Half-memory cap.** Users report ROCm seeing only half of unified memory by default (https://forum.level1techs.com/t/rocm-can-only-use-half-of-the-unified-memory-on-my-strix-halo/253152). On a cloud box we probably can't reboot or change this, so plan for about 30 GB of usable GPU memory.
  - **`HSA_OVERRIDE_GFX_VERSION`.** It is only a hack for *unsupported* GPUs (for example 11.0.0 for RDNA3) (https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md). Native gfx1151 builds exist, so don't set it. Using it on gfx1151 is **unverified**.
  - **pytorch.org wheels.** A community guide reports that generic pytorch.org wheels fail on gfx1151 with "invalid device function" (https://smithery.ai/skills/ianbarber/strix-halo-setup). AMD's per-architecture wheels carry gfx1151 fixes, such as a `_grouped_mm` segfault fix (https://sleepingrobots.com/dreams/unsloth-studio-strix-halo/). After every `pip install`, check that torch was not replaced by a CUDA build from PyPI.
  - **Flash Attention.** As of 2025, Flash Attention for gfx1151 was not in the TheRock PyTorch builds (https://community.frame.work/t/pytorch-w-flash-attention-vllm-for-strix-halo/74736). Current status is **unverified**.
  - **Known issues.** ROCm 7.14.1 lists "lower inference performance on RDNA3" and long vLLM warmups on Radeon (https://rocm.docs.amd.com/en/docs-7.14.1/_sources/about/release-notes.md).

### 2.2 Serving options, ranked by "works tonight"

| # | Option | gfx1151 status | Notes |
|---|---|---|---|
| 1 | **llama.cpp, Vulkan prebuilt** | `llama-b11540-bin-ubuntu-vulkan-x64.tar.gz`, released 2026-10-10 (https://github.com/ggml-org/llama.cpp/releases) | Needs no ROCm, only Mesa RADV. Community benchmarks find Vulkan 2–25% faster than ROCm at token generation, while ROCm is faster at prefill (https://github.com/visorcraft/strix-halo-llm-perf). **Not ROCm**, so it is weak for the AMD prize. |
| 2 | **HF transformers on PyTorch ROCm** | Official gfx1151 wheels (2.1) | `transformers serve` gives an OpenAI-compatible server at `localhost:8000` that handles images, with `--continuous-batching` and `--dtype` flags (https://huggingface.co/docs/transformers/main/serving). It's simpler than writing FastAPI and counts for both AMD and HF. It runs bf16 and is slower than GGUF. |
| 3 | **llama.cpp, HIP/ROCm** | Prebuilt `...-ubuntu-rocm-10.0-x64.tar.gz` ships `libggml-hip.so` but **no ROCm libraries** (I listed the tarball contents), so it needs a system ROCm 10.0. Otherwise build from source with `-DGGML_HIP=ON -DGPU_TARGETS=gfx1151` (build.md). | Use `-fa on`. On Strix Halo, avoid mmap: kyuz0's guide says `--no-mmap`, which current master spells `-lm none` (https://github.com/kyuz0/amd-strix-halo-toolboxes, https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md). |
| 4 | **Lemonade** | Its llama.cpp ROCm backend covers Strix Halo. Install with `sudo snap install lemonade-server` or the PPA. It serves on port 13305 (https://lemonade-server.ai/docs/guide/install/ubuntu/, https://lemonade-server.ai/docs/guide/configuration/llamacpp/). | Needs root. |
| 5 | **Ollama** | Its docs map gfx1151 to the Ryzen AI Max+ 395 (https://docs.ollama.com/gpu) | The install script needs root. It's an extra layer on top of llama.cpp. |
| 6 | **vLLM** | vLLM's docs list gfx1151 (https://docs.vllm.ai/en/latest/getting_started/installation/gpu/). AMD's image is `rocm/vllm:rocm7.14.1_rdna_ubuntu24.04_py3.14_pytorch_2.11_vllm_0.23.0` (https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/inference/vllm.html). | The image is **about 25 GB** (Docker Hub API) and needs Docker plus `/dev/kfd`. Warmups are slow. Skip it tonight. |

**Published speeds** (llama.cpp on a Ryzen AI Max+ 395, 128 GB; https://github.com/visorcraft/strix-halo-llm-perf):

| Model | Prompt processing (pp512) | Generation (tg128) |
|---|---|---|
| Llama-2-7B Q4_K_M | 1074 tok/s | **47.3 tok/s** |
| Qwen2.5-Coder-7B Q6_K | 1089 tok/s | 36.7 tok/s |
| Qwen3-30B-A3B (MoE) Q4_K_M, Vulkan | — | 86.1 tok/s |

Speed is bandwidth-bound. I found no published gfx1151 numbers for Qwen3.5 or Qwen3-VL (**unverified**).

### 2.3 Models

- **Key constraint: VLMs read gauges badly.**
  - On MeasureBench, the best model scored only **30.3%** on real-world gauge images and 26.1% on synthetic ones. Models identify units with over 90% accuracy but fail at mapping the needle to a value (https://huggingface.co/datasets/FlagEval/MeasureBench, https://arxiv.org/abs/2510.26865).
  - The same paper found that RL fine-tuning on synthetic gauges helped significantly.
  - So, my recommendation (not sourced): have the VLM return JSON with `unit`, `min`, `max`, `needle_description` and confidence, and cross-check against the mission CSV reading, or use OpenCV to estimate the needle angle. Never trust a VLM's number alone.
- **Qwen3.5-9B** (https://hf.co/Qwen/Qwen3.5-9B; Apache-2.0; Feb 2026).
  - It's a natively multimodal VLM that Qwen says outperforms Qwen3-VL.
  - It **thinks by default**. Disable this with `chat_template_kwargs: {"enable_thinking": false}` or `-rea off` in llama-server. Recommended non-thinking sampling is temp 0.7, top_p 0.8, top_k 20.
  - Its hybrid Gated-DeltaNet architecture is new, so kernel speed on ROCm and Vulkan is **unverified**.
  - GGUF: `unsloth/Qwen3.5-9B-GGUF`, Q4_K_M at 5.68 GB plus `mmproj-F16.gguf` at 0.92 GB.
  - It is **live on 4 HF Inference Providers** (together, featherless-ai, ovhcloud, deepinfra) (hub_repo_details).
- **Qwen3-VL-8B-Instruct** (https://hf.co/Qwen/Qwen3-VL-8B-Instruct).
  - It's a pure instruct model with no thinking toggle, and the safest architecture.
  - There's an official GGUF, `Qwen/Qwen3-VL-8B-Instruct-GGUF`: Q4_K_M at 5.03 GB plus an F16 mmproj at 1.16 GB. Recommended sampling is temp 0.7, top_k 20, top_p 0.8.
  - For transformers it needs version 4.57 or later.
  - **4B and 2B sizes** (with GGUFs) suit the 16 GB environment.
- **Others.**
  - llama.cpp documents multimodal support for Gemma 3, SmolVLM2 and InternVL3 (https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md).
  - Gemma 4 E4B ships an official QAT GGUF (https://hf.co/google/gemma-4-E4B-it-qat-q4_0-gguf).
  - Qwen3.8-27B is dense and much slower. Use it only as an accuracy A/B test.
- **Text model.**
  - Simplest: reuse the VLM for operator explanations, which means one server and one model in memory.
  - For a separate fast text model: `Qwen/Qwen3-4B-Instruct-2507`, a non-thinking model. GGUF `unsloth/Qwen3-4B-Instruct-2507-GGUF` Q4_K_M is 2.50 GB.
- **Fit.** Even both Q4 models together come to about 9 GB plus KV cache, which fits easily. The Qwen3-VL-8B F16 GGUF is 16.4 GB, which fits the 48 GB environment but is tight on the 16 GB one.

### 2.4 LoRA stretch goal

- **TRL.** `SFTTrainer` supports VLMs (dataset with an `image` column, `max_length=None`) and PEFT through `peft_config=LoraConfig()`. It defaults to bf16 and gradient checkpointing (https://huggingface.co/docs/trl/main/en/sft_trainer).
- **bitsandbytes.** The PyPI wheels include **gfx1151** for Linux ROCm 6.4.4 through 10.0.0, and the docs say "All features are supported" on RDNA (https://huggingface.co/docs/bitsandbytes/main/en/installation). QLoRA is therefore possible, but bf16 LoRA on a 2–4B VLM fits 48 GB without it.
- **Unsloth.** It lists gfx1151 as "Full" support, including bitsandbytes QLoRA. Install with `uv pip install unsloth[amd]` after installing ROCm PyTorch (https://unsloth.ai/docs/basics/amd).
- **Timing.** Whether a run fits in 1–2 hours on this GPU is **unverified**. Use 200–500 examples, 1 epoch, and a 2B model.

### 2.5 Benchmarking

- **Throughput.** `llama-bench -m X.gguf -p 512 -n 128 -fa on -r 5 -o md` reports average and standard deviation of tok/s (https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md).
- **Server metrics.** `llama-server --metrics` exposes Prometheus metrics at `/metrics`, and every response carries `timings.predicted_per_second` and `prompt_ms` (server README).
- **GPU monitoring.**
  - Live view: `amd-smi monitor --watch 1` (`--gfx --mem --power-usage --temperature --vram-usage`).
  - Per-process GTT/VRAM: `amd-smi process --gpu 0 --general` (https://rocm.docs.amd.com/projects/amdsmi/en/latest/how-to/amdsmi-cli-tool.html).
  - `rocm-smi` is heading to maintenance mode, so prefer `amd-smi` (https://rocm.docs.amd.com/projects/rocm_smi_lib/en/docs-7.0.0/install/install.html).
- **Story for AMD judges.** Measure the same prompts and images in three configurations, reporting tok/s, time to first token, p50/p95 latency, GPU utilization, and watts:
  1. transformers bf16 on ROCm (baseline)
  2. llama.cpp Q4 on ROCm
  3. llama.cpp Q4 on Vulkan

### 2.6 Hugging Face ecosystem

- **Inference Providers.** OpenAI-compatible router at `https://router.huggingface.co/v1`. Free accounts get no monthly credits, so the $20 hackathon credits pay as you go (https://huggingface.co/docs/inference-providers/pricing).
- **Hub CLI.**
  - `hf auth login`
  - `hf repos create NAME --repo-type dataset`
  - `hf upload REPO ./dir . --repo-type=dataset`
  - `hf repos create NAME --repo-type space --sdk gradio`
  - Source: https://huggingface.co/docs/huggingface_hub/main/en/guides/cli
- **ZeroGPU hosting.** Free accounts must be over 30 days old with a verified email, and can host at most 2 Spaces (https://huggingface.co/docs/hub/spaces-zerogpu).
- **smolagents.** `OpenAIModel(model_id=..., api_base="http://HOST:8080/v1")` points an agent at our local llama-server. `InferenceClientModel` uses Providers instead (https://huggingface.co/docs/smolagents/main/en/reference/models).
- **Cheap, high-signal moves (my ranking):**
  1. Push a **SPOT gauge/thermal eval dataset** with a dataset card: images, ground truth from the CSV, and model outputs.
  2. Write a **model or benchmark card** with the gfx1151 numbers, plus the LoRA adapter if we train one.
  3. Build a **Gradio Space on free CPU** that calls Qwen3.5-9B through Providers, the same model we run locally on AMD.
  4. Add a smolagents "operator explainer" agent with tools that look up readings.

## 3. Recommended stack for tonight

**Design rule:** the app only talks to an OpenAI-compatible `base_url`. That lets us swap backends without touching app code.

### Step 0: Probe (5 min, any environment)

```bash
ls -l /dev/kfd /dev/dri; id                 # need video + render groups
cat /etc/os-release; uname -r               # kernel floor: see 2.1
amd-smi version; ls /opt | grep -i rocm      # system ROCm version, if any
vulkaninfo --summary | grep -iE "deviceName|driverName"
curl -LsSf https://hf.co/cli/install.sh | bash && hf auth login
hf download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_K_M.gguf mmproj-F16.gguf --local-dir ~/models/q35
```

### Primary: llama.cpp `llama-server`, ROCm first, Vulkan as an instant swap

```bash
cd ~ && V=b11540
# (a) ROCm prebuilt: only if Step 0 shows ROCm 10.0 installed
curl -LO https://github.com/ggml-org/llama.cpp/releases/download/$V/llama-$V-bin-ubuntu-rocm-10.0-x64.tar.gz
# (b) otherwise, if hipconfig exists, build HIP for gfx1151 (~10-20 min, time unverified)
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release && cmake --build build --config Release -j 4
# (c) Vulkan fallback, no ROCm needed
curl -LO https://github.com/ggml-org/llama.cpp/releases/download/$V/llama-$V-bin-ubuntu-vulkan-x64.tar.gz
tar xzf llama-$V-bin-ubuntu-vulkan-x64.tar.gz   # (or the rocm tarball) -> llama-$V/llama-server; source build -> build/bin/llama-server

./llama-$V/llama-server -m ~/models/q35/Qwen3.5-9B-Q4_K_M.gguf --mmproj ~/models/q35/mmproj-F16.gguf \
  -ngl all -fa on -lm none -c 16384 -rea off --host 0.0.0.0 --port 8080 --metrics
```

- If `-ngl all`, `-lm` or `-rea` are rejected, the build is older than master. Use `-ngl 999 --no-mmap` and check `--help`.
- If Qwen3.5 is slow or misbehaves, swap in `Qwen/Qwen3-VL-8B-Instruct-GGUF` (`Qwen3VL-8B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen3VL-8B-Instruct-F16.gguf`).

### Fallback: PyTorch ROCm + `transformers serve`

This is also the ROCm baseline for the benchmark and the stack for the LoRA.

```bash
python3 -m venv ~/venv && . ~/venv/bin/activate          # Python 3.11–3.14
pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ \
  "torch[device-gfx1151]==2.12.0+rocm7.14.1" "torchvision[device-gfx1151]==0.27.0+rocm7.14.1" "torchaudio==2.11.0+rocm7.14.1"
pip install -U "transformers[serving]" accelerate pillow
python -c "import torch;print(torch.__version__,torch.cuda.is_available(),torch.cuda.get_device_name(0))"  # must say +rocm, True
transformers serve Qwen/Qwen3-VL-8B-Instruct --dtype bfloat16 --continuous-batching   # http://localhost:8000/v1
```

- If the `torch` line no longer shows `+rocm` after installing transformers, rerun the AMD index install.
- For Qwen3.5 in transformers, its card says to install transformers from `main`.

### Benchmark script (mine, untested)

```python
# bench.py URL MODEL N   e.g. python bench.py http://localhost:8080/v1 q35 30
import sys, time, base64, statistics, requests
url, model, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
img = base64.b64encode(open("gauge.jpg", "rb").read()).decode()
msg = [{"role": "user", "content": [
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}},
    {"type": "text", "text": 'Return JSON {"unit","min","max","value","confidence"}.'}]}]
lat, tps = [], []
for _ in range(n):
    t = time.perf_counter()
    r = requests.post(f"{url}/chat/completions", json={"model": model, "messages": msg,
        "max_tokens": 128, "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False}}).json()
    lat.append(time.perf_counter() - t); tps.append(r["usage"]["completion_tokens"] / lat[-1])
print(f"p50={statistics.median(lat):.2f}s p95={statistics.quantiles(lat, n=20)[18]:.2f}s e2e_tok/s={statistics.median(tps):.1f}")
```

While it runs, keep `amd-smi monitor --watch 1` open in a second terminal.

## 4. Open questions

1. What OS, kernel, ROCm version, Docker access, root access and `/dev/kfd` access do the AMD environments have? Are the "48GB" and "16GB" figures container RAM limits that also cap GPU memory through GTT?
2. Which gfx targets are in the prebuilt `ubuntu-rocm-10.0` llama.cpp build? Is gfx1151 included? Unverified.
3. How fast are Qwen3.5's Gated-DeltaNet kernels on ROCm and Vulkan for gfx1151? There are no published 9B numbers.
4. Do TheRock wheels run with no system ROCm installed (only the kernel driver)? Is Flash Attention on gfx1151 available in 2.12?
5. How long does a LoRA run take on gfx1151? Unmeasured.
6. Do the HF prize judges value Spaces over Hub artifacts? Their criteria only say "meaningful use of the HF ecosystem."
7. Thermal images: does the SPOT kit have radiometric temperatures? If so, pass the numbers to the LLM rather than having the VLM read colors.
