"""Load the NextEra SPOT challenge kit (CSV files in data/kit/) into typed Python dicts."""
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
KIT_DIR = Path(os.environ.get("SPOT_KIT_DIR", ROOT / "data" / "kit"))


def _read(name: str) -> List[Dict[str, str]]:
    with open(KIT_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _int(v: str) -> Optional[int]:
    return None if v in ("", None) else int(float(v))


def _float(v: str) -> Optional[float]:
    return None if v in ("", None) else float(v)


@dataclass
class Kit:
    locations: Dict[str, dict]
    assets: Dict[str, dict]
    missions: Dict[str, dict]
    actions: List[dict]               # sorted by (mission_id, sequence)
    readings: Dict[str, dict]         # action_id -> reading (the kit has at most one per action)
    anomalies: Dict[str, dict]        # action_id -> anomaly (at most one per action)

    def actions_of(self, mission_id: str) -> List[dict]:
        return [a for a in self.actions if a["mission_id"] == mission_id]


def load_kit() -> Kit:
    locations = {r["location_id"]: {
        "location_id": r["location_id"], "location_name": r["location_name"], "zone_type": r["zone_type"],
        "floor": _int(r["floor"]), "environment": r["environment"]} for r in _read("locations.csv")}
    assets = {r["asset_id"]: {
        "asset_id": r["asset_id"], "asset_name": r["asset_name"], "asset_type": r["asset_type"],
        "location_id": r["location_id"], "criticality": r["criticality"]} for r in _read("assets.csv")}
    missions = {r["mission_id"]: {
        "mission_id": r["mission_id"], "mission_name": r["mission_name"], "scenario": r["scenario"],
        "configuration_version": r["configuration_version"], "start_time": r["start_time"],
        "end_time": r["end_time"], "duration_min": _int(r["duration_min"]),
        "start_battery_pct": _int(r["start_battery_pct"]), "end_battery_pct": _int(r["end_battery_pct"]),
        "mission_status": r["mission_status"], "operator_mode": r["operator_mode"]} for r in _read("missions.csv")}
    actions = [{
        "action_id": r["action_id"], "mission_id": r["mission_id"], "sequence": _int(r["sequence"]),
        "timestamp": r["timestamp"], "location_id": r["location_id"], "asset_id": r["asset_id"],
        "action_type": r["action_type"], "battery_pct": _int(r["battery_pct"]), "status": r["status"],
        "failure_type": r["failure_type"] or None, "duration_sec": _int(r["duration_sec"]),
        "configuration_version": r["configuration_version"]} for r in _read("actions.csv")]
    actions.sort(key=lambda a: (a["mission_id"], a["sequence"]))
    readings = {r["action_id"]: {
        "measurement_type": r["measurement_type"], "value": _float(r["value"]), "unit": r["unit"],
        "quality": r["quality"]} for r in _read("readings.csv")}
    anomalies = {r["action_id"]: {
        "anomaly_type": r["anomaly_type"], "severity": r["severity"], "description": r["description"]}
        for r in _read("anomalies.csv")}
    return Kit(locations, assets, missions, actions, readings, anomalies)
