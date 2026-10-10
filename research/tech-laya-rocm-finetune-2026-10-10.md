# Laya fine-tuning on AMD ROCm gfx1151: risks, internals, and settings (2026-10-10)

## 1. Scope

This note covers the risks of fine-tuning and running Laya (`convaiinnovations/laya`, laya 0.4.1, repo HEAD `1adc59f`, Oct 8 2026) on a Radeon 8060S (gfx1151) with torch 2.12.0+rocm7.14.1. It also covers the fine-tuning internals, known issues, a rough time estimate, and Hub publishing. It does not cover the basic quickstart API. Every claim was checked against source code or a page linked below. **[UNCONFIRMED]** marks anything I could not verify.

## 2. Findings

### 2.1 Will it run on ROCm?

- **Nobody has verified Laya on ROCm.** The PR that made training device-agnostic says: "ROCm is supported by construction, not verified: no ROCm host was available" ([PR #53](https://github.com/NandhaKishorM/laya/pull/53)). The Docker docs say "AMD/ROCm … containers are outside this quickstart" ([docs/docker.md](https://github.com/NandhaKishorM/laya/blob/main/docs/docker.md)).
- **`cuda` works through HIP.** `resolve_device("auto")` picks `cuda` whenever `torch.cuda.is_available()` ([laya/train.py L528-537](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). On CUDA, the training loop turns on fp16 autocast, `GradScaler("cuda")`, and gradient checkpointing by default (`amp=(device.type=="cuda")`) ([train.py L635-682](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). A ROCm build reports `device.type == "cuda"`, so it takes this same path.
- **Attention has no flash-attn dependency.** Laya hardcodes `attn_implementation="sdpa"` when it builds the encoder ([laya/common.py L709-712](https://github.com/NandhaKishorM/laya/blob/main/laya/common.py)). ModernBERT's unpadding path runs only when `_attn_implementation == "flash_attention_2"` ([transformers v4.57.1 modeling_modernbert.py](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/modernbert/modeling_modernbert.py)), so Laya always takes the padded SDPA path. On gfx1151, PyTorch exposes no flash or memory-efficient SDPA backend by default and falls back to `math`. Setting `TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1` enables AOTriton ([axjns/strix-halo-kernels](https://huggingface.co/axjns/strix-halo-kernels)). Our sequences are about 350 tokens, so even the math fallback costs only tens of MB per layer. This is not a blocker.
- **ModernBERT's hidden `torch.compile` on transformers 4.x.** In 4.x, `reference_compile=None` resolves to `is_triton_available()`, and the MLP and embeddings are decorated with `@torch.compile(dynamic=True)` ([v4.57.1 source, `_maybe_set_compile`](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/modernbert/modeling_modernbert.py)). `laya.Agent` sets `reference_compile` to False, but the training loader `load_checkpoint` never touches it ([agent.py L686-690](https://github.com/NandhaKishorM/laya/blob/main/laya/agent.py), [train.py L573-587](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). So with transformers 4.x plus ROCm Triton, training would trigger Inductor compiles on gfx1151. transformers 5.x removes the option: the config pops `reference_compile` ([v5 configuration_modernbert.py](https://github.com/huggingface/transformers/blob/main/src/transformers/models/modernbert/configuration_modernbert.py)). The shipped encoder config was saved with `transformers_version: 5.0.0` ([encoder/config.json](https://huggingface.co/convaiinnovations/laya/blob/main/encoder/config.json)). `TORCH_COMPILE_DISABLE=1` disables Dynamo globally ([torch 2.12 _dynamo/config.py L275](https://github.com/pytorch/pytorch/blob/v2.12.0/torch/_dynamo/config.py)).
- **`laya[fast]` and TileLang only work on CUDA.** The doc says "TileLang portability: the kernels are CUDA-only", and the HIP constructs are untested ([docs/compile-and-fast-path.md](https://github.com/NandhaKishorM/laya/blob/main/docs/compile-and-fast-path.md)). The fast path also records `torch.cuda.CUDAGraph` ([laya/fast.py L190-197](https://github.com/NandhaKishorM/laya/blob/main/laya/fast.py)).
- **Trap: `backend="auto"` assumes ROCm is CUDA.** `auto_policy` returns `tilelang` when it is installed, and otherwise `compile` (Inductor with reduce-overhead/CUDA graphs). It does this for any `device.type == "cuda"` and has no HIP check ([laya/backends/__init__.py L47-56](https://github.com/NandhaKishorM/laya/blob/main/laya/backends/__init__.py)). With no `backend`, `compile`, or `fast` argument, the default is eager ([compile-and-fast-path.md](https://github.com/NandhaKishorM/laya/blob/main/docs/compile-and-fast-path.md)).
- **Inference dtype.** On CUDA, a device with capability major ≥ 8 uses the checkpoint's `amp_dtype` (bf16). `LAYA_CUDA_AMP=fp16` overrides it. The docs report that bf16 flips 3 of 864 argmaxes and fp16 flips none ([agent.py L299-308, L760-772](https://github.com/NandhaKishorM/laya/blob/main/laya/agent.py), [docs/docker.md](https://github.com/NandhaKishorM/laya/blob/main/docs/docker.md)). **[UNCONFIRMED]** what `get_device_capability()` returns on gfx1151.
- **AMD's known issue.** In AMD's words: "PyTorch training and fine-tuning workloads … might experience GPU resets". The workaround is `TORCH_BLAS_PREFER_HIPBLASLT=0`, which may reduce performance ([AMD PyTorch install for ROCm 7.14](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html)). The same page confirms that Radeon 8060S is supported and gives the install command: `pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1151]==2.12.0+rocm7.14.1" …`.
- **GEMM speed on gfx1151 varies a lot by kernel library.** Theoretical peak is 59 FP16 TFLOPS, but "effective is much lower". gfx1151 rocBLAS kernels lag gfx1100 rocBLAS by 2.5–6× ([Framework thread](https://community.frame.work/t/amd-strix-halo-ryzen-ai-max-395-gpu-llm-performance-tests/72521)). **[UNCONFIRMED, search snippet only]** mamf-finder measured 5.1 bf16 TFLOPS without hipBLASLt and 36.9 with it ([r/LocalLLaMA post](https://www.reddit.com/r/LocalLLaMA/comments/1kmi3ra/)). Measured GPU bandwidth is about 215 GB/s ([Framework thread](https://community.frame.work/t/amd-strix-halo-ryzen-ai-max-395-gpu-llm-performance-tests/72521)).

### 2.2 Fine-tuning internals

- **Loss.** `--loss rlcd` is the default. It combines a GRPO-style policy-gradient term with a full-weight soft cross-entropy term: 4 noisy samples, σ annealed 0.4→0.1, reward 0.75·spherical + 1.0·RPS. `--loss soft-ce` drops the policy-gradient term ([docs/finetune.md](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md), [train.py `rlcd_loss`](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). The "RL" part works only on detached logits against a known target, so this is effectively supervised learning ([#238](https://github.com/NandhaKishorM/laya/issues/238)). A controlled A/B found soft-CE at least as good: 80.50% vs 79.08% ([#741](https://github.com/NandhaKishorM/laya/issues/741)). The maintainers' table shows soft-ce at 0.790 vs rlcd at 0.7715 ([docs/finetune.md](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md)). Hard labels (`expected`) work as well as teacher `gold` probabilities.
- **Hyperparameters** (`TrainConfig` defaults are the notebook's settings). 4 epochs, `micro_batch` 8 × `grad_accum` 8 (effective batch 64), encoder lr 2.5e-5, head lr 1e-4, AdamW with weight decay 0.01, cosine schedule down to 1e-6, gradient clip 1.0, fp16 autocast and checkpointing on CUDA. The notebook used `max_len` 1024 and `head_max_len` 256. The base checkpoint's own values are 512 and 192 ([train.py L78-125](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py), [rl_agent_config.json](https://huggingface.co/convaiinnovations/laya/blob/main/rl_agent_config.json)).
- **One item is one (state, question) sequence.** Each question re-encodes the full state ([common.py `build_sequence`](https://github.com/NandhaKishorM/laya/blob/main/laya/common.py), [train.py `encode_item`](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). So 1,500–3,000 cases × 4–5 questions gives about 6,000–15,000 items.
- **Memory.** The model loads in fp32 ([train.py `load_checkpoint`](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). For 421M parameters, weights + grads + 2 AdamW states ≈ 6.7 GB, plus checkpointed activations (my arithmetic). One community fine-tune reports that "plain fp32 AdamW does not fit a 421M encoder in 6GB" ([Aditharavind/swarm-laya](https://huggingface.co/Aditharavind/swarm-laya)). That is comfortable on 64 GB, but **[UNCONFIRMED]** how much the cloud VM exposes to the GPU.
- **Calibration.** A slice of `min(400, 10%)` items is held out before training (seed 20260922). After the last epoch, the loop fits one temperature per question type, which needs ≥10 items per type (`MIN_TYPE_N`). Per-(type, option-count) buckets (`choice:2`, `choice:3-5`, `6-10`, `11+`) need ≥**2,000** items each (`MIN_BUCKET_N`), so at our scale only the per-type scalars get fitted. Temperatures are clamped to [0.5, 5.0]. Any inherited `temperature_by_options` is dropped ([laya/calibrate.py L37-41, `fit_temperature_map`](https://github.com/NandhaKishorM/laya/blob/main/laya/calibrate.py), [common.py L815-825](https://github.com/NandhaKishorM/laya/blob/main/laya/common.py), [train.py L1215-1223](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)). The docs' "[0.1, 10]" range describes the old notebook.
- **Head-only training and LoRA.** `--freeze-encoder` trains only the decision head; it "gains much less than a full fine-tune" ([docs/finetune.md](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md)). `laya.train` has no LoRA or PEFT support (grep of the repo). Residual adapters are still an open PR ([#921](https://github.com/NandhaKishorM/laya/pull/921)). A community desktop app claims LoRA training, **[UNCONFIRMED]** ([PR #1064](https://github.com/NandhaKishorM/laya/pull/1064)).
- **Outputs.** A run writes `model.safetensors` (fp16), `encoder/`, `tokenizer/`, `rl_agent_config.json`, `questions.json`, and a `checkpoint_latest/` folder that is rewritten after every epoch ([docs/finetune.md](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md)). Passing `--eval` gives a before/after report ([#967 via #887](https://github.com/NandhaKishorM/laya/issues/887)).

### 2.3 Known issues and small-data experience

- **#156 (noul).** On the base English checkpoint, a `true`/`false` noul returns the negative label regardless of the state. Supplying criteria does not help. An opt-in `labels` override exists (#163), but on `laya-typed-decisions` neutral labels did worse than the default ([#156](https://github.com/NandhaKishorM/laya/issues/156)).
- **#185 (`act_probability`).** It is always 1.0; it is "a leftover the current checkpoints never learned" ([#185](https://github.com/NandhaKishorM/laya/issues/185)). The training loop discards the act output (`logits, _act = model(...)`) ([train.py `_forward`](https://github.com/NandhaKishorM/laya/blob/main/laya/train.py)), so fine-tuning will not fix it either.
- **#963 (small data collapses to the class prior).** With about 1,100 items, the 4-epoch default gives only 72 optimizer updates, and the model ended at chance. The run needed up to 32 epochs, and only 9 of 15 seeds learned at all. Since 0.3.29 there is a collapse warning, and since 0.4.1 the update budget is printed. Early stopping is still open ([#963](https://github.com/NandhaKishorM/laya/issues/963), [docs/finetune.md](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md)).
- **Other limits.** Option counts above about 10 degrade confidence ([#394](https://github.com/NandhaKishorM/laya/issues/394)). Forced-choice negation can follow the question rather than the state ([#377](https://github.com/NandhaKishorM/laya/issues/377)).
- **Community fine-tunes.**
  - `Snugasabug/laya-finetuned-rlcd`: 4,000 rows, trained on CPU. Accuracy went from 0.403 to 0.959, but that is agreement with the teacher, not human ground truth. Fitted temperatures moved from 5.6–10 down to about 1.07–1.20 ([card](https://huggingface.co/Snugasabug/laya-finetuned-rlcd)). Its GGUF companion repo only re-exports the weights ([card](https://huggingface.co/Snugasabug/laya-finetuned-rlcd-GGUF)).
  - `swarm-laya`: a robotics decision task with 5,368 states. It scored 83.1% on test, and its rarest class (`hold_position`) reached only about 4–5% ([card](https://huggingface.co/Aditharavind/swarm-laya)).
  - `caldec-v1-laya`: soft-CE, 6 epochs, micro-batch 4 × accumulation 8. Its card is a good template, with `model-index` and ECE reported ([card](https://huggingface.co/kgrozdanovski/caldec-v1-laya)).
  - PR #705: 128 cases, 8 epochs, about 14 minutes on a 12-core CPU, with real held-out gains ([#705](https://github.com/NandhaKishorM/laya/pull/705)).

### 2.4 Time estimate (rough)

- **Assumptions.** About 360 tokens per item after padding. About 3e9 training FLOPs per token, i.e. 8 × ~0.37B non-embedding parameters, counting the checkpoint recompute. The RLCD term adds negligible compute.
- **Per-epoch work.** The 6,000-item case leaves 5,600 training items, about 6e15 FLOPs. The 15,000-item case leaves 14,600 training items, about 1.6e16 FLOPs.
- **T4.** Peak is 65 FP16 TFLOPS ([NVIDIA T4](https://www.nvidia.com/en-us/data-center/tesla-t4/)); I assume 13–20 TFLOPS effective. That gives about **5–8 min per epoch** for 5,600 items and **13–20 min** for 14,600. Laya's own figures disagree with each other by about 10×. "4–6 min" for 6,000 decisions × 4 epochs on 2×T4 implies about 1.5 min per T4-epoch. "4–5 h for 4 epochs over ~30k" implies about 25 min per T4-epoch for 5,600 items ([docs/finetune.md](https://github.com/NandhaKishorM/laya/blob/main/docs/finetune.md)).
- **gfx1151.** I assume 5–20 TFLOPS effective, depending on hipBLASLt (see 2.1). That gives about **5–20 min per epoch** for 5,600 items and **13–55 min** for 14,600. A 4-epoch run would take about 20–80 min for the small set and 1–3.5 h for the large one. Measure this; don't trust the estimate.

## 3. Recommendations

**Environment** (set before `import torch`):
```bash
pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ "torch[device-gfx1151]==2.12.0+rocm7.14.1"
pip install "laya==0.4.1" "transformers>=5"        # NOT laya[fast]; transformers 5 removes ModernBERT reference_compile
export TORCH_COMPILE_DISABLE=1                      # no Dynamo/Inductor anywhere
export TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1    # optional; unset if numerics look off
export LAYA_CUDA_AMP=fp16                           # inference autocast dtype
# only if the GPU resets mid-training (slower):
# export TORCH_BLAS_PREFER_HIPBLASLT=0
python -c "import torch;print(torch.__version__,torch.version.hip,torch.cuda.is_available(),torch.cuda.get_device_name(0),torch.cuda.mem_get_info())"
```
Afterwards, check that `pip install laya` did not replace the ROCm torch: `torch.version.hip` must not be None.

**Inference.** Call `laya.load(path)` with no `backend`, `compile`, or `fast` argument. Never pass `backend="auto"` on ROCm.

**Training:**
1. `laya-train --data spot_train.jsonl --base english --out ./laya-spot --dry-run`. Read the printed item count, the skip reasons, and the optimizer budget.
2. Run a smoke test with about 200 cases and `--epochs 1`, and time the throughput before committing to the full run.
3. Full run: `laya-train --data spot_train.jsonl --eval spot_test.jsonl --base english --out ./laya-spot --loss soft-ce --epochs 4 --micro-batch 8 --grad-accum 8 --device cuda --seed 0`. Add `--shuffle-options` only if a choice question has more than about 10 options. Keep the base `max_len` of 512 and `head_max_len` of 192; our states fit.
4. **Size the run by updates, not epochs.** Aim for at least 350 optimizer updates. If there are fewer than about 5,600 training items, raise `--epochs` using the formula in the finetune docs. If the run prints the collapse warning, rerun with 2–3 more seeds.
5. Keep one evaluation set of whole cases that never enters training, so no case contributes questions to both sides. Report accuracy, ECE, and per-class recall, especially for rare classes.
6. Dashboard: don't show `act_probability`. For noul questions, check P(true) on held-out positives. If it stays biased, rephrase yes/no questions as 2-option `choice` questions with descriptive keys.
7. Fallback if gfx1151 misbehaves: run the same command with `--device cpu` (slow), or use the Kaggle 2×T4 notebook.

**Hub publishing.**
- Write `README.md` into `./laya-spot` with this YAML front matter: `license: apache-2.0`, `library_name: laya`, `base_model: convaiinnovations/laya`, `base_model_relation: finetune`, `pipeline_tag: text-classification`, `datasets: [<our HF dataset>]`, and `model-index` entries for accuracy and expected_calibration_error ([HF model-card docs](https://huggingface.co/docs/hub/model-cards)).
- The body should cover:
  - the hardware (Radeon 8060S, ROCm 7.14.1, torch 2.12);
  - the loss, epochs, update count, and fitted temperatures;
  - base vs fine-tuned metrics on held-out data;
  - intended use (operator triage assist, not autonomous robot control);
  - limitations (#156, #185, synthetic or small data);
  - an "unofficial fine-tune" disclaimer, as in [swarm-laya](https://huggingface.co/Aditharavind/swarm-laya);
  - a `laya.load` snippet.
- Upload with `HfApi(token=...).create_repo(repo, exist_ok=True)` followed by `upload_folder(folder_path=..., repo_id=..., repo_type="model")`. These are the notebook's own calls ([notebook cell 16](https://github.com/NandhaKishorM/laya/blob/main/notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb)). Leave `checkpoint_latest/` out of the upload. Also publishing the dataset and linking it in `datasets:` strengthens the open-source story.

## 4. Open questions

- Does fp16 autocast + GradScaler training on gfx1151 hit NaNs or GPU resets in practice? This has never been tested on ROCm.
- What does `torch.cuda.get_device_capability()` return on gfx1151, and therefore which inference dtype does Laya pick? Setting `LAYA_CUDA_AMP` sidesteps this.
- How much memory does the Radeon Cloud VM actually give the GPU (`mem_get_info`)?
- What is the real throughput with hipBLASLt on vs off?
- Which base is better for our task, `english` or `typed-decisions`? Unknown; try both only if there is time.
- Does training data accept the noul `labels` override? Not verified in `to_internal`.
