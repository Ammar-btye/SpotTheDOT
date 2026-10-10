"""Synthetic SPOT missions, calibrated ONLY on the training missions' statistics.

The kit is 27 missions. To give Laya enough updates without memorising them, we sample new missions
from distributions fitted on the training split: battery start/drain per config, (asset, action type)
routes, failure probability by action type x environment x battery band x config, failure type,
reading values (GOOD around the kit mean, occasional out-of-band drift, rare implausible glitches),
anomaly incidence, type and severity. Holdout missions never inform the simulator.

Synthetic events are scored separately from real ones in the benchmark (never pooled into the
real-holdout headline), so a model that only learns the generator is visible as a real-vs-synthetic gap.
"""
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from .kit import Kit
from .policy import PLAUSIBLE, SAFE_BANDS

BANDS = [(0, 25, "<=25"), (26, 40, "26-40"), (41, 60, "41-60"), (61, 80, "61-80"), (81, 100, "81+")]


def battery_band(b: int) -> str:
    for lo, hi, name in BANDS:
        if lo <= b <= hi:
            return name
    return "81+"


def _sample(rng: random.Random, weights: Dict) -> object:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _mean_sd(xs: List[float]):
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1))
    return m, max(sd, 1e-3)


class Simulator:
    def __init__(self, kit: Kit, train_mission_ids: List[str]):
        self.kit = kit
        acts = [a for a in kit.actions if a["mission_id"] in set(train_mission_ids)]
        mis = [kit.missions[m] for m in train_mission_ids]
        if not acts:
            raise ValueError("no training actions to calibrate on")
        loc_env = {k: v["environment"] for k, v in kit.locations.items()}

        # battery: start and per-action drain, per config
        self.start_batt, self.drain = {}, {}
        for cfg in ("V1", "V2"):
            ms = [m for m in mis if m["configuration_version"] == cfg]
            self.start_batt[cfg] = _mean_sd([m["start_battery_pct"] for m in ms])
            drains = []
            for m in ms:
                seq = [a["battery_pct"] for a in acts if a["mission_id"] == m["mission_id"]]
                prev = m["start_battery_pct"]
                for b in seq:
                    drains.append(prev - b)
                    prev = b
            self.drain[cfg] = _mean_sd(drains)
        self.cfg_share = Counter(m["configuration_version"] for m in mis)

        # routes: empirical (asset, action_type) pairs
        self.pairs = [(a["asset_id"], a["action_type"]) for a in acts]
        self.duration = _mean_sd([a["duration_sec"] for a in acts])

        # failure model: smoothed rates combined multiplicatively around the overall rate
        fail = [a["status"] == "FAILED" for a in acts]
        self.p0 = sum(fail) / len(fail)

        def rate(key_fn):
            n, k = Counter(), Counter()
            for a, f in zip(acts, fail):
                key = key_fn(a)
                n[key] += 1
                k[key] += f
            prior = 4.0     # Beta prior strength toward the overall rate
            return {key: (k[key] + prior * self.p0) / (n[key] + prior) for key in n}
        self.r_type = rate(lambda a: a["action_type"])
        self.r_env = rate(lambda a: loc_env[a["location_id"]])
        self.r_band = rate(lambda a: battery_band(a["battery_pct"]))
        self.r_cfg = rate(lambda a: a["configuration_version"])

        # failure type | action type (+ environment), with backoff
        self.ft_type = defaultdict(Counter)
        self.ft_type_env = defaultdict(Counter)
        for a in acts:
            if a["failure_type"]:
                self.ft_type[a["action_type"]][a["failure_type"]] += 1
                self.ft_type_env[(a["action_type"], loc_env[a["location_id"]])][a["failure_type"]] += 1

        # readings
        self.meas = {}                      # action_type -> (measurement_type, unit)
        good, quest = defaultdict(list), defaultdict(list)
        has = defaultdict(lambda: [0, 0])   # (action_type, status) -> [with reading, total]
        for a in acts:
            r = kit.readings.get(a["action_id"])
            has[(a["action_type"], a["status"])][1] += 1
            if r:
                has[(a["action_type"], a["status"])][0] += 1
                self.meas[a["action_type"]] = (r["measurement_type"], r["unit"])
                (good if r["quality"] == "GOOD" else quest)[r["measurement_type"]].append(r["value"])
        self.p_reading = {k: (v[0] + 1) / (v[1] + 2) for k, v in has.items()}
        self.good = {k: _mean_sd(v) for k, v in good.items()}
        self.quest = {k: _mean_sd(v) for k, v in quest.items() if len(v) >= 2}

        # anomalies
        an = defaultdict(lambda: [0, 0])    # (action_type, status) -> [with anomaly, total]
        self.an_type = defaultdict(Counter)
        self.sev_by_type = defaultdict(Counter)
        for a in acts:
            x = kit.anomalies.get(a["action_id"])
            an[(a["action_type"], a["status"])][1] += 1
            if x:
                an[(a["action_type"], a["status"])][0] += 1
                self.an_type[a["action_type"]][x["anomaly_type"]] += 1
                self.sev_by_type[x["anomaly_type"]][x["severity"]] += 1
        self.p_anomaly = {k: (v[0] + 0.5) / (v[1] + 1) for k, v in an.items()}
        all_types = Counter()
        for c in self.an_type.values():
            all_types.update(c)
        self.an_type_all = all_types

    # ── sampling ──
    def _p_fail(self, action_type: str, env: str, batt: int, cfg: str) -> float:
        p = (self.r_type.get(action_type, self.p0)
             * self.r_env.get(env, self.p0) / self.p0
             * self.r_band.get(battery_band(batt), self.p0) / self.p0
             * math.sqrt(self.r_cfg.get(cfg, self.p0) / self.p0))
        return min(0.9, max(0.02, p))

    def _failure_type(self, rng, action_type, env):
        w = Counter()
        for ft, c in self.ft_type[action_type].items():
            w[ft] += c
        for ft, c in self.ft_type_env[(action_type, env)].items():
            w[ft] += 2 * c
        if not w:
            w = Counter({"SENSOR_TIMEOUT": 1, "READING_UNRELIABLE": 1})
        return _sample(rng, w)

    def _reading(self, rng, action_type, status):
        if action_type not in self.meas or rng.random() > self.p_reading.get((action_type, status), 0.8):
            return None
        mtype, unit = self.meas[action_type]
        if status == "FAILED":
            m, sd = self.quest.get(mtype, self.good[mtype])
            return {"measurement_type": mtype, "value": round(rng.gauss(m, sd), 1), "unit": unit,
                    "quality": "QUESTIONABLE"}
        m, sd = self.good[mtype]
        v = rng.gauss(m, sd)
        u = rng.random()
        lo, hi = SAFE_BANDS[mtype]
        if u < 0.10:            # drift beyond the safe band (an equipment concern)
            v = (hi + abs(rng.gauss(0, sd * 0.6)) + 0.5) if hi is not None else (lo - abs(rng.gauss(0, sd * 0.6)) - 0.5)
        elif u < 0.115:         # implausible glitch that still claims GOOD quality
            plo, phi = PLAUSIBLE[mtype]
            v = rng.choice([plo - rng.uniform(5, 100), phi + rng.uniform(5, 200)])
        if u >= 0.115 and unit in ("pct", "score"):
            v = min(v, 100.0)
        return {"measurement_type": mtype, "value": round(v, 1), "unit": unit, "quality": "GOOD"}

    def _anomaly(self, rng, action_type, status):
        if rng.random() > self.p_anomaly.get((action_type, status), 0.05):
            return None
        types = self.an_type.get(action_type) or self.an_type_all
        t = _sample(rng, types)
        sev = Counter({"LOW": 1, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 0.5})
        sev.update(self.sev_by_type.get(t, {}))
        return {"anomaly_type": t, "severity": _sample(rng, sev),
                "description": "Synthetic %s detected." % t.replace("_", " ").lower()}

    def mission(self, rng: random.Random, mission_id: str, start: datetime, stress: bool = False):
        cfg = _sample(rng, self.cfg_share)
        m, sd = self.start_batt[cfg]
        batt = int(round(min(100, max(30, rng.gauss(m, sd)))))
        if stress:
            batt = rng.randint(40, 60)
        dm, dsd = self.drain[cfg]
        actions, readings, anomalies = [], {}, {}
        t = start
        for seq in range(1, 11):
            batt = max(3, int(round(batt - max(0.5, rng.gauss(dm, dsd)))))
            t += timedelta(seconds=186)
            asset_id, atype = rng.choice(self.pairs)
            loc_id = self.kit.assets[asset_id]["location_id"]
            env = self.kit.locations[loc_id]["environment"]
            failed = rng.random() < self._p_fail(atype, env, batt, cfg)
            aid = "%s-A%02d" % (mission_id, seq)
            a = {"action_id": aid, "mission_id": mission_id, "sequence": seq,
                 "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S"), "location_id": loc_id, "asset_id": asset_id,
                 "action_type": atype, "battery_pct": batt, "status": "FAILED" if failed else "SUCCESS",
                 "failure_type": self._failure_type(rng, atype, env) if failed else None,
                 "duration_sec": max(5, int(rng.gauss(*self.duration))), "configuration_version": cfg}
            actions.append(a)
            r = self._reading(rng, atype, a["status"])
            if r:
                readings[aid] = r
            x = self._anomaly(rng, atype, a["status"])
            if x:
                anomalies[aid] = x
        stranded = batt < 12 or any(a["failure_type"] == "COMMUNICATION_LOSS" and a["battery_pct"] <= 20
                                    for a in actions)
        mission = {"mission_id": mission_id, "mission_name": "Synthetic Autowalk " + mission_id,
                   "scenario": "BASELINE" if cfg == "V1" else "IMPROVED", "configuration_version": cfg,
                   "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"), "end_time": t.strftime("%Y-%m-%dT%H:%M:%S"),
                   "duration_min": int((t - start).total_seconds() // 60),
                   "start_battery_pct": actions[0]["battery_pct"] + int(round(dm)), "end_battery_pct": batt,
                   "mission_status": "FAILED" if stranded else "COMPLETED", "operator_mode": "AUTOWALK"}
        return mission, actions, readings, anomalies

    def missions(self, n: int, seed: int, prefix: str, stress_frac: float = 0.15):
        rng = random.Random(seed)
        base = datetime(2026, 10, 1, 6, 0, 0) + timedelta(days=seed % 97)
        out = []
        for i in range(n):
            out.append(self.mission(rng, "%s%04d" % (prefix, i + 1), base + timedelta(hours=8 * i),
                                    stress=rng.random() < stress_frac))
        return out
