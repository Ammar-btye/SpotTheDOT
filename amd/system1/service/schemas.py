"""Request/response models and the canonical-event models.

The event models mirror `triage/events.py` (`pre_action_event`, `action_event`, `mission_event`). Nested
dicts that `render_json` copies verbatim into Laya's state (`mission_so_far`, `reading`, `anomaly`,
`anomalies_by_severity`, `worst_anomaly`) declare their fields in the kit's order and drop unknown keys,
so the rendered state matches what the model was trained on byte for byte. Timestamps stay strings
(parsing them would change their rendering).
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["pre_action", "action", "mission"]
Level = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── canonical events ────────────────────────────────────────────────────────────────────────
class Location(_Model):
    location_id: str
    location_name: str
    zone_type: str
    environment: str
    floor: Optional[int] = None


class Asset(_Model):
    asset_id: str
    asset_name: str
    asset_type: str
    criticality: Level
    location_id: Optional[str] = None


class MissionSoFar(_Model):
    actions_done: int = Field(ge=0)
    failures_so_far: int = Field(ge=0)
    last_status: Optional[Literal["SUCCESS", "FAILED"]] = None
    last_failure_type: Optional[str] = None
    start_battery_pct: int


class Reading(_Model):
    measurement_type: str
    value: float
    unit: str
    quality: str


class Anomaly(_Model):
    anomaly_type: str
    severity: Level
    description: str


class _ActionBase(_Model):
    kind: Optional[Kind] = None
    source: str = "api"
    event_id: Optional[str] = None
    action_id: Optional[str] = None
    mission_id: str
    configuration_version: str
    timestamp: str
    sequence: int = Field(ge=0)
    action_type: str
    battery_pct: int
    location: Location
    asset: Asset


class PreActionEvent(_ActionBase):
    mission_so_far: MissionSoFar


class ActionEvent(_ActionBase):
    status: Literal["SUCCESS", "FAILED"]
    failure_type: Optional[str] = None
    duration_sec: Optional[int] = None
    reading: Optional[Reading] = None
    anomaly: Optional[Anomaly] = None


class SeverityCounts(_Model):
    LOW: int = Field(0, ge=0)
    MEDIUM: int = Field(0, ge=0)
    HIGH: int = Field(0, ge=0)
    CRITICAL: int = Field(0, ge=0)


class WorstAnomaly(_Model):
    anomaly_type: str
    severity: Level
    asset_name: str
    asset_criticality: Level


class MissionEvent(_Model):
    kind: Optional[Kind] = None
    source: str = "api"
    event_id: Optional[str] = None
    mission_id: str
    configuration_version: str
    timestamp: str
    reported_status: str
    duration_min: int
    start_battery_pct: int
    end_battery_pct: int
    actions_total: int = Field(ge=0)
    actions_failed: int = Field(ge=0)
    failure_types: List[str] = []
    anomalies_by_severity: SeverityCounts
    worst_anomaly: Optional[WorstAnomaly] = None


EVENT_MODELS = {"pre_action": PreActionEvent, "action": ActionEvent, "mission": MissionEvent}


# ── /v1/predict ─────────────────────────────────────────────────────────────────────────────
class PredictItem(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    kind: Kind
    event: dict           # validated against EVENT_MODELS[kind] in app.py, so errors name the event field
    questions: Optional[List[str]] = None


class PredictRequest(BaseModel):
    request_id: Optional[str] = Field(None, max_length=200)
    items: List[PredictItem] = Field(min_length=1, max_length=64)


class Answer(BaseModel):
    answer: str
    probs: Dict[str, float]
    confidence: float


class PredictedItem(BaseModel):
    id: str
    kind: Kind
    answers: Dict[str, Answer]


class PredictResponse(BaseModel):
    request_id: Optional[str] = None
    model: str
    fine_tuned: bool
    device: str
    latency_ms: int
    items: List[PredictedItem]
