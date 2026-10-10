"""Our Laya training loop: the same batches and losses as `laya.train.train_model`, with a better schedule.

Laya's built-in loop (laya==0.4.1) has a fixed cosine schedule, no warmup, one learning rate for the whole
encoder and no stopping rule. This loop reuses Laya's own pieces (encode_item, draw_option_order,
collate_items, _forward, soft_ce_loss, rlcd_loss) so every batch and loss is computed exactly as Laya does,
and adds:

- **Warmup + decay**: linear warmup (`warmup_ratio`), then cosine/linear decay to `min_lr_ratio` x peak.
  Without warmup the first updates hit a freshly-unfrozen encoder at full learning rate.
- **Layer-wise LR decay** (`llrd`): the top encoder layer trains at `encoder_lr`, each layer below at
  `llrd` times the one above, embeddings lowest. Standard for BERT-style fine-tuning on small data.
- **No weight decay on norms and biases.**
- **LoRA via Hugging Face PEFT** (`apply_lora`): low-rank adapters on the encoder's Wqkv/Wo/Wi (attention
  and MLP); the base encoder is frozen except its LayerNorms, and Laya's decision head trains fully.
  Adapters train at their own flat `lora_lr` (no layer-wise decay: LoRA wants ~10x the full fine-tune LR in
  every layer), optionally with LoRA+ (`loraplus_ratio`: B trains faster than A). `export_state_dict`
  merges the adapters into plain weights, so checkpoints still load with `laya.load`.
  See research/tech-lora-gap-2026-10-10.md.
- **Class rebalancing** (`oversample_positives`): duplicates positive items of rare yes/no questions
  (e.g. will_fail, ~20% positive) so the model can't win by always answering "no".
- **Counterfactual pairs stay together**: items sharing a `pair` key (an event and its one-field edit) are
  shuffled as a group, so both land in the same optimizer update and the contrast is learned directly.
- **Time budget**: after the first optimizer updates the loop measures its speed and shortens the
  schedule (fewer epochs and a matching LR horizon) so training plus evaluation ends by the deadline,
  with the LR fully decayed rather than cut off mid-schedule.
- **NaN guard**: stops with a clear message (use --no-amp) instead of training on NaNs.
"""
import json
import math
import os
import random
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import torch
from laya.common import collate_items
from laya.train import (_forward, draw_option_order, encode_item, encode_state, make_item, rlcd_loss,
                        sigma_at, soft_ce_loss, target_from_expected, to_internal)

LORA_TARGETS = ("Wqkv", "Wo", "Wi")


@dataclass
class LoopConfig:
    epochs: int = 6
    micro_batch: int = 8
    grad_accum: int = 4
    encoder_lr: float = 2e-5            # full fine-tune; under LoRA it only drives the unfrozen LayerNorms
    head_lr: float = 1e-4
    lora_lr: float = 2e-4               # LoRA adapters, same in every layer (llrd does not apply)
    loraplus_ratio: float = 1.0         # LoRA+: lora_B trains at lora_lr x ratio (1.0 = plain LoRA)
    warmup_ratio: float = 0.06
    schedule: str = "cosine"            # cosine | linear | constant
    min_lr_ratio: float = 0.05          # LR floor as a fraction of each group's peak
    llrd: float = 1.0                   # layer-wise LR decay; 1.0 = off
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    loss: str = "soft-ce"               # soft-ce | rlcd (Laya's objectives)
    rl_samples: int = 4
    sigma_start: float = 0.4
    sigma_end: float = 0.1
    w_sph: float = 0.75
    w_rps: float = 1.0
    shuffle_options: Tuple[str, ...] = ("choice",)
    freeze_encoder: bool = False
    amp: bool = True
    grad_checkpointing: bool = False
    seed: int = 0
    log_every: int = 50

    def validate(self):
        if self.schedule not in ("cosine", "linear", "constant"):
            raise ValueError("schedule must be cosine, linear or constant")
        if self.loss not in ("soft-ce", "rlcd"):
            raise ValueError("loss must be soft-ce or rlcd")
        if not 0 < self.llrd <= 1:
            raise ValueError("llrd must be in (0, 1]")
        if not 0 <= self.warmup_ratio < 1:
            raise ValueError("warmup_ratio must be in [0, 1)")
        if self.loraplus_ratio <= 0:
            raise ValueError("loraplus_ratio must be > 0")


# ── data ──────────────────────────────────────────────────────────────────────────────────────
def items_with_qids(tok, rows: List[dict], max_len: int, head_max_len: int,
                    label_smoothing: float = 0.0) -> Tuple[List[dict], Dict[str, int]]:
    """Like laya.train.items_from_rows for {state, questions, expected} rows, but each item keeps its
    question id and gold answer (needed for per-question rebalancing)."""
    items, skipped = [], {}
    for r in rows:
        state_ids = encode_state(tok, r["state"], max_len)
        for qid, question in r["questions"].items():
            if qid not in r.get("expected", {}):
                continue
            q = to_internal(qid, question)
            target = target_from_expected(q, r["expected"][qid], label_smoothing=label_smoothing)
            item, reason = make_item(tok, q, target, state_ids, head_max_len, max_len)
            if item is None:
                skipped[reason] = skipped.get(reason, 0) + 1
                continue
            item["qid"], item["gold"] = qid, r["expected"][qid]
            item["pair"] = r.get("meta", {}).get("pair")     # counterfactual pair key, if any
            items.append(item)
    return items, skipped


def oversample_positives(items: List[dict], factors: Dict[str, float], positive: Dict[str, str],
                         seed: int = 0) -> Tuple[List[dict], Dict[str, int]]:
    """Repeat items whose gold answer is the positive class of question `qid` ~factors[qid] times."""
    rng = random.Random(seed)
    out, added = list(items), {}
    for it in items:
        f = factors.get(it.get("qid"))
        if not f or it.get("gold") != positive.get(it["qid"]):
            continue
        extra = int(f) - 1 + (1 if rng.random() < f - int(f) else 0)
        out.extend([it] * extra)
        added[it["qid"]] = added.get(it["qid"], 0) + extra
    return out, added


# ── LoRA (Hugging Face PEFT) ──────────────────────────────────────────────────────────────────
def apply_lora(model, r: int = 16, alpha: int = 32, dropout: float = 0.0,
               targets: Sequence[str] = LORA_TARGETS, init="default", train_norms: bool = True):
    """Wrap Laya's encoder with LoRA adapters. The base encoder is frozen; the decision head stays trainable.

    dropout 0: ModernBERT's own dropouts are all 0, so adapter dropout is noise a full fine-tune doesn't have.
    init: "default" (B = 0), or a PEFT init such as "pissa_niter_16" or "olora". Run this before .to(device)
    so the SVD/QR runs on the CPU.
    train_norms: unfreeze the encoder's LayerNorms (58K params, incl. final_norm, which feeds the head). A full
    fine-tune trains them; they land in the merged checkpoint but not in lora_adapter/."""
    from peft import LoraConfig, get_peft_model
    cfg = LoraConfig(r=r, lora_alpha=alpha, lora_dropout=dropout, target_modules=list(targets), bias="none",
                     init_lora_weights=True if init == "default" else init)
    model.encoder = get_peft_model(model.encoder, cfg)
    if train_norms:
        for m in model.encoder.modules():
            if isinstance(m, torch.nn.LayerNorm):
                for p in m.parameters():
                    p.requires_grad_(True)
    return model


def is_lora(model) -> bool:
    return hasattr(model.encoder, "peft_config")


def encoder_config(model):
    enc = model.encoder
    return enc.get_base_model().config if is_lora(model) else enc.config


@torch.no_grad()
def export_state_dict(model) -> Dict[str, torch.Tensor]:
    """A plain Laya state dict. With LoRA, adapters are merged into the base weights for the copy, then unmerged."""
    if not is_lora(model):
        return {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.encoder.merge_adapter()
    try:
        sd = {}
        for k, v in model.state_dict().items():
            if "lora_" in k:
                continue
            sd[k.replace("encoder.base_model.model.", "encoder.").replace(".base_layer.", ".")] = v.detach().clone()
    finally:
        model.encoder.unmerge_adapter()
    return sd


def save_laya(model, tok, cfg: dict, path: str) -> None:
    """Write the layout `laya.load` reads (same as laya.train.save_checkpoint), LoRA merged; plus the adapter."""
    from safetensors.torch import save_file
    os.makedirs(path, exist_ok=True)
    sd = export_state_dict(model)
    save_file({k: v.half().cpu().contiguous() for k, v in sd.items()}, os.path.join(path, "model.safetensors"))
    encoder_config(model).save_pretrained(os.path.join(path, "encoder"))
    tok.save_pretrained(os.path.join(path, "tokenizer"))
    tmp = os.path.join(path, "rl_agent_config.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, os.path.join(path, "rl_agent_config.json"))
    if is_lora(model):
        init = model.encoder.peft_config["default"].init_lora_weights
        if isinstance(init, str) and init.startswith(("pissa", "olora", "corda", "loftq")):
            # these inits rewrite the base weights, so the adapter only applies to that residual base;
            # the merged model.safetensors is the checkpoint
            return
        model.encoder.save_pretrained(os.path.join(path, "lora_adapter"))


# ── optimisation ──────────────────────────────────────────────────────────────────────────────
def param_groups(model, cfg: LoopConfig) -> List[dict]:
    names = [n for n, p in model.named_parameters() if p.requires_grad]
    layer_ids = [int(m.group(1)) for n in names if n.startswith("encoder.")
                 for m in [re.search(r"\.layers\.(\d+)\.", n)] if m]
    n_layers = max(layer_ids) + 1 if layer_ids else 0
    groups: Dict[Tuple[float, bool], List[torch.nn.Parameter]] = {}
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if name.startswith("encoder.") and "lora_" in name:
            lr = cfg.lora_lr * (cfg.loraplus_ratio if "lora_B" in name else 1.0)
        elif name.startswith("encoder."):
            m = re.search(r"\.layers\.(\d+)\.", name)
            depth = (n_layers - 1 - int(m.group(1))) if m else (n_layers if "embeddings" in name else 0)
            lr = cfg.encoder_lr * (cfg.llrd ** depth)
        else:
            lr = cfg.head_lr
        no_decay = p.ndim < 2 or "norm" in name or name.endswith(".bias")
        groups.setdefault((lr, no_decay), []).append(p)
    return [{"params": ps, "lr": lr, "weight_decay": 0.0 if nd else cfg.weight_decay}
            for (lr, nd), ps in sorted(groups.items(), key=lambda kv: -kv[0][0])]


def lr_factor(step: int, horizon: int, warmup: int, cfg: LoopConfig) -> float:
    if warmup and step < warmup:
        return (step + 1) / warmup
    if cfg.schedule == "constant":
        return 1.0
    progress = min(1.0, (step - warmup) / max(1, horizon - warmup))
    shape = 0.5 * (1 + math.cos(math.pi * progress)) if cfg.schedule == "cosine" else 1 - progress
    return cfg.min_lr_ratio + (1 - cfg.min_lr_ratio) * shape


def trainable_summary(model) -> str:
    total = sum(p.numel() for p in model.parameters())
    train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return "%.1fM of %.1fM parameters trainable (%.1f%%)" % (train / 1e6, total / 1e6, 100 * train / total)


def train_loop(model, tok, items: List[dict], cfg: LoopConfig, device: torch.device, max_len: int,
               head_max_len: int, parallel: bool,
               on_epoch_end: Callable[[int, float, bool], Optional[bool]],
               deadline: Optional[float] = None, eval_seconds: float = 0.0, budget_probe: int = 20) -> List[float]:
    """Train in place. `on_epoch_end(epoch_idx, mean_loss, partial)` runs the benchmark; returning False stops
    early. `deadline` (unix time) caps training plus the per-epoch evaluations (`eval_seconds` each)."""
    cfg.validate()
    if not items:
        raise ValueError("no training items")
    if cfg.freeze_encoder:
        for p in model.encoder.parameters():
            p.requires_grad_(False)
    if cfg.grad_checkpointing and hasattr(model.encoder, "gradient_checkpointing_enable"):
        if is_lora(model) and hasattr(model.encoder, "enable_input_require_grads"):
            model.encoder.enable_input_require_grads()
        model.encoder.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

    def set_train_mode():
        model.to(device).train()
        if cfg.freeze_encoder:
            model.encoder.eval()
    set_train_mode()

    groups = param_groups(model, cfg)
    peak_lrs = [g["lr"] for g in groups]
    optimizer = torch.optim.AdamW(groups)
    steps_per_epoch = math.ceil(len(items) / cfg.micro_batch)
    updates_per_epoch = math.ceil(steps_per_epoch / cfg.grad_accum)
    plan = {"horizon": updates_per_epoch * cfg.epochs, "epochs": cfg.epochs, "max_updates": None,
            "warmup_ratio": cfg.warmup_ratio}
    plan["warmup"] = int(cfg.warmup_ratio * plan["horizon"])     # recomputed if the time budget shrinks the run
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda s: lr_factor(s, plan["horizon"], plan["warmup"], cfg))
    use_amp = cfg.amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda") if use_amp else None
    params = [p for g in groups for p in g["params"]]
    print("trainer: %s | %d param groups, peak LR %.2g..%.2g (llrd %.2f), warmup %d, %s schedule, %d updates/epoch"
          % (trainable_summary(model), len(groups), min(peak_lrs), max(peak_lrs),
             cfg.llrd, plan["warmup"], cfg.schedule, updates_per_epoch), flush=True)

    probe_at = max(1, min(budget_probe, updates_per_epoch // 2))   # measure speed early in epoch 1
    torch.manual_seed(cfg.seed)
    order_rng = random.Random(cfg.seed)
    history, updates, t_train0 = [], 0, time.time()
    for epoch in range(cfg.epochs):
        if epoch >= plan["epochs"]:
            break
        epoch_items = shuffled_groups(items, cfg.seed + epoch)
        sigma = sigma_at(epoch, cfg.epochs, cfg.sigma_start, cfg.sigma_end)
        total, n_steps, partial, pending = 0.0, 0, False, False
        t_epoch0 = time.time()
        optimizer.zero_grad(set_to_none=True)
        for start in range(0, len(epoch_items), cfg.micro_batch):
            chunk = [encode_item(tok, it, max_len, head_max_len,
                                 draw_option_order(it, order_rng, cfg.shuffle_options), parallel)
                     for it in epoch_items[start:start + cfg.micro_batch]]
            batch = collate_items([chunk], tok.pad_token_id)
            logits = _forward(model, batch, device, use_amp, cfg.freeze_encoder)
            mask, target = batch["marker_mask"].to(device), batch["target"].to(device)
            if cfg.loss == "rlcd":
                loss = rlcd_loss(logits, target, mask, batch["qtype"].to(device), sigma,
                                 cfg.rl_samples, cfg.w_sph, cfg.w_rps)
            else:
                loss = soft_ce_loss(logits, target, mask)
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite loss at epoch %d step %d: rerun with --no-amp (fp32)"
                                         % (epoch + 1, n_steps + 1))
            window_start = (n_steps // cfg.grad_accum) * cfg.grad_accum
            window = min(cfg.grad_accum, steps_per_epoch - window_start)
            (scaler.scale(loss / window) if scaler else loss / window).backward()
            pending = True
            n_steps += 1
            total += loss.item()
            if n_steps % cfg.grad_accum == 0 or start + cfg.micro_batch >= len(epoch_items):
                _step(optimizer, scheduler, scaler, params, cfg.grad_clip)
                pending, updates = False, updates + 1
                if epoch == 0 and updates == probe_at and deadline is not None:
                    _fit_budget(plan, updates, time.time() - t_train0, deadline, eval_seconds,
                                updates_per_epoch, cfg.epochs)
                if plan["max_updates"] is not None and updates >= plan["max_updates"]:
                    partial = True
            if cfg.log_every and n_steps % cfg.log_every == 0:
                print("epoch %d/%d step %d loss %.4f lr %.2e" % (epoch + 1, plan["epochs"], n_steps, loss.item(),
                                                               scheduler.get_last_lr()[0]), flush=True)
            if deadline is not None and time.time() > deadline - eval_seconds:
                partial = True
            if partial:
                break
        if pending:
            _step(optimizer, scheduler, scaler, params, cfg.grad_clip)
            updates += 1
        mean = total / max(1, n_steps)
        history.append(mean)
        print("epoch %d/%d mean loss %.4f%s" % (epoch + 1, plan["epochs"], mean,
                                                " (stopped early: time budget)" if partial else ""), flush=True)
        keep_going = on_epoch_end(epoch, mean, partial)
        set_train_mode()
        if partial or keep_going is False:
            break
        if deadline is not None:
            _replan(plan, epoch, time.time() - t_epoch0, deadline, updates, updates_per_epoch)
    model.eval()
    return history


def shuffled_groups(items: List[dict], seed: int) -> List[dict]:
    """Shuffle, keeping items that share a `pair` key adjacent. With no pairs this is a plain shuffle
    (same permutation as random.shuffle on the items)."""
    groups, index = [], {}
    for i, it in enumerate(items):
        key = it.get("pair") or ("item", i)
        if key not in index:
            index[key] = len(groups)
            groups.append([])
        groups[index[key]].append(it)
    random.Random(seed).shuffle(groups)
    return [it for g in groups for it in g]


def _step(optimizer, scheduler, scaler, params, clip):
    if scaler is not None:
        scaler.unscale_(optimizer)
    torch.nn.utils.clip_grad_norm_(params, clip)
    if scaler is not None:
        scaler.step(optimizer)
        scaler.update()
    else:
        optimizer.step()
    scheduler.step()
    optimizer.zero_grad(set_to_none=True)


def _fit_budget(plan, updates_done, elapsed, deadline, eval_seconds, updates_per_epoch, epochs):
    """Shrink epochs and the LR horizon so training + per-epoch evals finish by the deadline."""
    sec = elapsed / updates_done
    remaining = deadline - time.time()
    rest_of_epoch0 = (updates_per_epoch - updates_done) * sec + eval_seconds
    per_epoch = updates_per_epoch * sec + eval_seconds
    if rest_of_epoch0 > remaining:
        fit = updates_done + max(1, int((remaining - eval_seconds) / sec))
        plan.update(epochs=1, horizon=fit, max_updates=fit, warmup=min(plan["warmup"], int(plan["warmup_ratio"] * fit)))
        print("time budget: %.2fs/update; epoch 1 alone won't fit, so training stops at update %d of %d "
              "with the LR schedule compressed to match" % (sec, fit, updates_per_epoch), flush=True)
        return
    fit_epochs = max(1, min(epochs, 1 + int((remaining - rest_of_epoch0) / per_epoch)))
    print("time budget: %.2fs/update, %.1f min/epoch incl. eval -> %d of %d epoch(s) fit; LR schedule set to %d epoch(s)"
          % (sec, per_epoch / 60, fit_epochs, epochs, fit_epochs), flush=True)
    if fit_epochs < epochs:
        horizon = updates_per_epoch * fit_epochs
        # warmup is a fraction of the run actually done (it was sized for the full horizon before)
        plan.update(epochs=fit_epochs, horizon=horizon, warmup=int(plan["warmup_ratio"] * horizon))


def _replan(plan, epoch_idx, last_epoch_seconds, deadline, updates_done, updates_per_epoch):
    """After each epoch, re-check the budget with the epoch's MEASURED wall time (training + eval)."""
    remaining_planned = plan["epochs"] - (epoch_idx + 1)
    if remaining_planned <= 0:
        return
    fit_more = int((deadline - time.time()) / max(1.0, last_epoch_seconds))
    if fit_more < remaining_planned:
        plan.update(epochs=epoch_idx + 1 + fit_more, horizon=updates_done + fit_more * updates_per_epoch)
        print("time budget: last epoch took %.1f min; %d more epoch(s) fit, schedule shortened to %d epoch(s)"
              % (last_epoch_seconds / 60, fit_more, plan["epochs"]), flush=True)
