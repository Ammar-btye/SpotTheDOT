"""Benchmark metrics: per question, per segment, per rendering, with mission-level bootstrap CIs.

Headline metrics (research/tech-smalldata-finetune-eval-2026-10-10.md):
- macro-F1 and accuracy per question (macro-F1 because most labels are imbalanced),
- recall / precision on the positive class of binary questions (escalate, will_fail, ...),
- calibration: top-1 ECE (15 bins) and multi-class Brier,
- majority-class baseline per question (from the TRAINING label distribution) for context.
CIs resample whole missions (rows of one mission are correlated), 1,000 resamples.
"""
import random
from collections import Counter, defaultdict
from typing import Dict, List, Optional

import numpy as np

from .questions import POSITIVE


def _macro_f1(golds, preds, labels):
    f1s = []
    for c in labels:
        tp = sum(1 for g, p in zip(golds, preds) if g == c and p == c)
        fp = sum(1 for g, p in zip(golds, preds) if g != c and p == c)
        fn = sum(1 for g, p in zip(golds, preds) if g == c and p != c)
        if tp + fp + fn == 0:
            continue
        f1s.append(2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f1s)) if f1s else float("nan")


def _prf(golds, preds, pos):
    tp = sum(1 for g, p in zip(golds, preds) if g == pos and p == pos)
    fp = sum(1 for g, p in zip(golds, preds) if g != pos and p == pos)
    fn = sum(1 for g, p in zip(golds, preds) if g == pos and p != pos)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return prec, rec


def ece(conf: List[float], correct: List[bool], bins: int = 15) -> float:
    conf, correct = np.asarray(conf), np.asarray(correct, dtype=float)
    if not len(conf):
        return float("nan")
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            total += m.sum() / len(conf) * abs(conf[m].mean() - correct[m].mean())
    return float(total)


def brier(preds: List[dict]) -> float:
    vals = [sum((p["probs"][o] - (1.0 if o == p["gold"] else 0.0)) ** 2 for o in p["probs"]) for p in preds
            if "probs" in p]
    return float(np.mean(vals)) if vals else float("nan")


def score(preds: List[dict], majority: Optional[Dict[str, str]] = None) -> dict:
    """Metrics for one group of predictions, split by question."""
    by_q = defaultdict(list)
    for p in preds:
        by_q[p["qid"]].append(p)
    out = {}
    for qid, ps in sorted(by_q.items()):
        golds, prs = [p["gold"] for p in ps], [p["pred"] for p in ps]
        labels = sorted(set(golds) | set(prs) | set(ps[0].get("probs", {}).keys()))
        m = {"n": len(ps), "accuracy": float(np.mean([g == q for g, q in zip(golds, prs)])),
             "macro_f1": _macro_f1(golds, prs, labels),
             "pred_distribution": dict(Counter(prs)), "gold_distribution": dict(Counter(golds))}
        if qid in POSITIVE:
            m["precision"], m["recall"] = _prf(golds, prs, POSITIVE[qid])
        if all("confidence" in p for p in ps):
            m["ece"] = ece([p["confidence"] for p in ps], [p["gold"] == p["pred"] for p in ps])
            m["brier"] = brier(ps)
            m["mean_confidence"] = float(np.mean([p["confidence"] for p in ps]))
        if majority and qid in majority:
            m["majority_accuracy"] = float(np.mean([g == majority[qid] for g in golds]))
            m["majority_macro_f1"] = _macro_f1(golds, [majority[qid]] * len(golds), labels)
        out[qid] = m
    accs = [v["accuracy"] for v in out.values()]
    f1s = [v["macro_f1"] for v in out.values()]
    out["_all"] = {"n": len(preds), "decision_accuracy": float(np.mean([p["gold"] == p["pred"] for p in preds]))
                   if preds else float("nan"),
                   "mean_question_accuracy": float(np.mean(accs)) if accs else float("nan"),
                   "mean_question_macro_f1": float(np.nanmean(f1s)) if f1s else float("nan")}
    return out


def bootstrap(preds: List[dict], stat, n: int = 1000, seed: int = 0):
    """95% CI of `stat(preds)` resampling whole missions."""
    groups = defaultdict(list)
    for p in preds:
        groups[p["meta"]["mission_id"]].append(p)
    keys = list(groups)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = [p for k in rng.choices(keys, k=len(keys)) for p in groups[k]]
        v = stat(sample)
        if v == v:  # not NaN
            vals.append(v)
    if not vals:
        return None
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def macro_f1_of(qid):
    def f(ps):
        ps = [p for p in ps if p["qid"] == qid]
        if not ps:
            return float("nan")
        labels = sorted({p["gold"] for p in ps} | {p["pred"] for p in ps})
        return _macro_f1([p["gold"] for p in ps], [p["pred"] for p in ps], labels)
    return f


def recall_of(qid):
    def f(ps):
        ps = [p for p in ps if p["qid"] == qid]
        return _prf([p["gold"] for p in ps], [p["pred"] for p in ps], POSITIVE[qid])[1] if ps else float("nan")
    return f


def full_report(preds: List[dict], majority: Dict[str, str], with_ci: bool = True) -> dict:
    """Scores per segment, per track and per rendering, plus CIs for the headline numbers on REAL data."""
    rep = {"overall": score(preds, majority)}
    for key in ("segment", "rendering"):
        groups = defaultdict(list)
        for p in preds:
            groups[p["meta"][key]].append(p)
        rep["by_" + key] = {g: score(ps, majority) for g, ps in sorted(groups.items())}
    real = [p for p in preds if p["meta"]["segment"] == "real"]
    if with_ci and real:
        rep["ci_real"] = {}
        for qid in sorted({p["qid"] for p in real}):
            rep["ci_real"][qid] = {"macro_f1": bootstrap(real, macro_f1_of(qid))}
            if qid in POSITIVE:
                rep["ci_real"][qid]["recall"] = bootstrap(real, recall_of(qid))
    return rep


def majority_from_rows(rows: List[dict]) -> Dict[str, str]:
    c = defaultdict(Counter)
    for r in rows:
        for q, v in r["expected"].items():
            c[q][v] += 1
    return {q: cnt.most_common(1)[0][0] for q, cnt in c.items()}
