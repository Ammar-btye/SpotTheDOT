"""Run a Laya model over benchmark rows and return per-question probabilities.

Uses Laya's own training-time encoding (`laya.train.encode_item` / `_forward`), the same path
`laya.train.finetune` uses to score its eval set, so an untuned checkpoint, an in-memory model
mid-training and a saved fine-tuned checkpoint are all measured identically. Temperatures are applied
the way `laya.Agent` applies them (per (question type, option count) bucket, else per type).
`parity_check` confirms agreement with `laya.load(...).predict` on a sample.

Decision thresholds: a checkpoint may carry `decision_thresholds` ({qid: t}) fitted on the calibration
missions by scripts/finetune.py. For those yes/no questions the positive answer wins when its calibrated
probability is >= t (instead of > 0.5). Temperature scaling never changes the argmax, so this is what moves
recall on rare positives (will_fail, anomaly_expected). `pred_argmax` keeps the plain-argmax answer;
`laya.load(...).predict` does not apply thresholds.

Pinned to laya==0.4.1: `_forward` is a private helper.
"""
import math
import os
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
from laya.common import QTYPES, clamp_temperature, collate_items, temp_bucket, uses_parallel_layout
from laya.train import (_forward, encode_item, encode_state, load_checkpoint, make_item, resolve_device,
                        target_from_expected, to_internal)

from .metrics import _macro_f1
from .questions import POSITIVE


class LayaRunner:
    def __init__(self, model, tok, cfg: dict, device: torch.device, name: str = "laya",
                 amp: Optional[bool] = None):
        self.model, self.tok, self.cfg, self.device, self.name = model, tok, cfg, device, name
        self.max_len = cfg.get("max_len", 512)
        self.head_max_len = cfg.get("head_max_len", 192)
        self.parallel = uses_parallel_layout(cfg)
        # fp16 autocast on GPU by default; amp=False (--no-amp) or SPOT_AMP=0 forces fp32,
        # for GPUs whose fp16 GEMM path fails (e.g. "invalid argument" in F.linear on new ROCm targets).
        self.amp = (device.type == "cuda" and os.environ.get("SPOT_AMP", "1") != "0") if amp is None else amp

    @classmethod
    def load(cls, model_id_or_path: str = "convaiinnovations/laya", device: str = "auto",
             amp: Optional[bool] = None) -> "LayaRunner":
        model, tok, cfg = load_checkpoint(model_id_or_path)
        dev = resolve_device(device)
        model.to(dev).eval()
        return cls(model, tok, cfg, dev, name=model_id_or_path, amp=amp)

    def set_temperatures(self, temperature: Optional[Sequence[float]], by_options: Optional[Dict[str, float]]):
        self.cfg = dict(self.cfg, temperature=list(temperature) if temperature is not None else None,
                        temperature_by_options=by_options or {})

    def set_thresholds(self, thresholds: Optional[Dict[str, float]]):
        self.cfg = dict(self.cfg, decision_thresholds=dict(thresholds or {}))

    def _temp(self, qtype: int, k: int) -> float:
        by_opt = self.cfg.get("temperature_by_options") or {}
        base = self.cfg.get("temperature")
        t = by_opt.get(temp_bucket(qtype, k), base[qtype] if base else 1.0)
        return clamp_temperature(float(t))

    def build_items(self, rows: List[dict]):
        """One item per (row, question). Returns (items, metas, skipped)."""
        items, metas, skipped = [], [], Counter()
        for r in rows:
            state_ids = encode_state(self.tok, r["state"], self.max_len)
            for qid, question in r["questions"].items():
                q = to_internal(qid, question)
                target = target_from_expected(q, r["expected"][qid])
                item, reason = make_item(self.tok, q, target, state_ids, self.head_max_len, self.max_len)
                if item is None:
                    skipped[reason] += 1
                    continue
                items.append(item)
                metas.append({"row": r, "qid": qid, "options": list(q["crit"].keys()),
                              "gold": r["expected"][qid]})
        return items, metas, dict(skipped)

    @torch.no_grad()
    def logits(self, items: List[dict], batch_size: int = 16) -> List[np.ndarray]:
        was_training = self.model.training
        self.model.eval()
        out = []
        try:
            for start in range(0, len(items), batch_size):
                chunk = items[start:start + batch_size]
                batch = collate_items([[encode_item(self.tok, it, self.max_len, self.head_max_len,
                                                    parallel=self.parallel) for it in chunk]],
                                      self.tok.pad_token_id)
                lg = _forward(self.model, batch, self.device, self.amp, detach_encoder=False).cpu().numpy()
                out.extend(row[:it["k"]] for row, it in zip(lg, chunk))
        finally:
            if was_training:
                self.model.train()
        return out

    def decide(self, items: List[dict], metas: List[dict], lgs: List[np.ndarray], calibrated: bool = True,
               thresholds: bool = True) -> List[dict]:
        """Turn logits into per-question predictions (temperatures, then decision thresholds)."""
        thr = (self.cfg.get("decision_thresholds") or {}) if thresholds else {}
        preds = []
        for it, m, lg in zip(items, metas, lgs):
            t = self._temp(it["qtype"], it["k"]) if calibrated else 1.0
            z = lg / t
            p = np.exp(z - z.max())
            p /= p.sum()
            probs = {o: float(v) for o, v in zip(m["options"], p)}
            argmax = m["options"][int(p.argmax())]
            pred = apply_threshold(m["qid"], probs, thr.get(m["qid"])) if m["qid"] in thr else argmax
            preds.append({"id": m["row"]["id"], "qid": m["qid"], "gold": m["gold"], "pred": pred,
                          "pred_argmax": argmax, "confidence": probs[pred], "probs": probs,
                          "logits": [float(v) for v in lg], "qtype": it["qtype"], "k": it["k"],
                          "meta": {k: v for k, v in m["row"]["meta"].items() if k != "features"}})
        return preds

    def predict(self, rows: List[dict], batch_size: int = 16, calibrated: bool = True) -> dict:
        """Per-question predictions plus raw logits (kept so temperatures can be refitted later)."""
        items, metas, skipped = self.build_items(rows)
        t0 = time.perf_counter()
        lgs = self.logits(items, batch_size)
        secs = time.perf_counter() - t0
        preds = self.decide(items, metas, lgs, calibrated)
        return {"predictions": preds, "skipped": skipped, "items": len(items), "seconds": secs,
                "items_per_sec": len(items) / secs if secs else math.nan,
                "rows_per_sec": len(rows) / secs if secs else math.nan}


def apply_threshold(qid: str, probs: Dict[str, float], t: Optional[float]) -> str:
    """The positive answer if its probability >= t, else the most likely other answer."""
    pos = POSITIVE.get(qid)
    if t is None or pos not in probs:
        return max(probs, key=probs.get)
    if probs[pos] >= t:
        return pos
    return max((o for o in probs if o != pos), key=probs.get)


def fit_thresholds(preds: List[dict], min_each: int = 10) -> Dict[str, float]:
    """Per yes/no question, the threshold on P(positive) that maximises macro-F1 on these (calibration)
    predictions. Ties go to the threshold nearest 0.5. Questions with fewer than `min_each` positives or
    negatives are left on argmax."""
    by_q = defaultdict(list)
    for p in preds:
        if p["qid"] in POSITIVE and POSITIVE[p["qid"]] in p["probs"]:
            by_q[p["qid"]].append(p)
    out = {}
    for qid, ps in sorted(by_q.items()):
        pos, golds = POSITIVE[qid], [p["gold"] for p in ps]
        n_pos = sum(g == pos for g in golds)
        if min(n_pos, len(golds) - n_pos) < min_each:
            continue
        labels = sorted(ps[0]["probs"])
        best = max((round(t, 2) for t in np.arange(0.05, 0.951, 0.01)),
                   key=lambda t: (round(_macro_f1(golds, [apply_threshold(qid, p["probs"], t) for p in ps], labels), 4),
                                  -abs(t - 0.5)))
        out[qid] = float(best)
    return out


def parity_check(model_path: str, rows: List[dict], runner_preds: List[dict], device: str = "auto") -> dict:
    """Argmax agreement between this harness and `laya.load(...).predict` on the given rows."""
    import laya
    agent = laya.load(model_path, device=None if device == "auto" else device)
    ours = {(p["id"], p["qid"]): p.get("pred_argmax", p["pred"]) for p in runner_preds}   # laya applies no thresholds
    agree = total = 0
    for r in rows:
        res = agent.predict(r["state"], r["questions"])
        for qid, ans in res["answers"].items():
            key = (r["id"], qid)
            if key in ours:
                total += 1
                agree += int(ans.get("choice") == ours[key])
    return {"rows": len(rows), "decisions": total, "agreement": agree / total if total else math.nan}


def qtype_id(name: str) -> int:
    return QTYPES[name]
