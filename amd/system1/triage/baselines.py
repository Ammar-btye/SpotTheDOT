"""Classic (non-Laya) baselines for Track A, trained on the same training rows' structured features.

Track B labels come from the deterministic policy, so a rules engine scores 100% there by
construction. Classic models are only meaningful on Track A, where labels are real outcomes.
"""
from typing import Dict, List

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

TRACK_A = ("will_fail", "failure_mode", "anomaly_expected")


def _events(rows: List[dict]):
    """One sample per event (training rows repeat events across renderings)."""
    seen, out = set(), []
    for r in rows:
        m = r["meta"]
        if m["track"] == "predict" and m["event_id"] not in seen:
            seen.add(m["event_id"])
            out.append(r)
    return out


def _x(r):
    f = dict(r["meta"]["features"])
    f["battery_low"] = int(f["battery_pct"] <= 25)
    return f


MODELS = {
    "logreg": lambda: LogisticRegression(max_iter=2000, C=1.0),
    "hgb": lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                                  random_state=0),
}


def run(train_rows: List[dict], bench_rows: List[dict]) -> Dict[str, List[dict]]:
    """Returns {model_name: predictions} in the same shape as LayaRunner.predict()['predictions']."""
    train = _events(train_rows)
    bench = [r for r in bench_rows if r["meta"]["track"] == "predict"]
    vec = DictVectorizer(sparse=False)
    xtr = vec.fit_transform([_x(r) for r in train])
    xbe = vec.transform([_x(r) for r in bench])
    out = {}
    for name, make in MODELS.items():
        preds = []
        for qid in TRACK_A:
            y = np.array([r["expected"][qid] for r in train])
            clf = make().fit(xtr, y)
            proba = clf.predict_proba(xbe)
            classes = list(clf.classes_)
            options = list(bench[0]["questions"][qid]["criteria"].keys())
            for r, p in zip(bench, proba):
                probs = {o: float(p[classes.index(o)]) if o in classes else 0.0 for o in options}
                pred = max(probs, key=probs.get)
                preds.append({"id": r["id"], "qid": qid, "gold": r["expected"][qid], "pred": pred,
                              "confidence": probs[pred], "probs": probs,
                              "meta": {k: v for k, v in r["meta"].items() if k != "features"}})
        out[name] = preds
    return out
