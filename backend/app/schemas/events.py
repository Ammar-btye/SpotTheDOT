from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import JSON, Loose, TriageMode

EventType = Literal["MISSION_STARTED", "ACTION_STARTED", "ACTION_COMPLETED", "ACTION_FAILED", "MISSION_COMPLETED"]


class SpotEvent(BaseModel):
    """One SPOT event, in the kit's replay.ndjson format. Extra fields are kept verbatim in raw.spot_event_log."""
    model_config = ConfigDict(extra="allow", json_schema_extra={"example": {
        "event_id": "E00003", "mission_id": "M001", "timestamp": "2026-09-01T18:03:06",
        "event_type": "ACTION_FAILED",
        "details": {"action_id": "A0001", "status": "FAILED", "failure_type": "OBSTACLE_DETECTION"}}})

    event_id: str = Field(min_length=1, max_length=200)
    mission_id: Optional[str] = Field(None, max_length=100)
    timestamp: str = Field(description="Robot time, ISO 8601 (e.g. 2026-09-01T18:03:06).")
    event_type: EventType
    details: Dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    events: List[SpotEvent] = Field(min_length=1, max_length=500)
    source: str = Field("api", max_length=60, description="Recorded in raw.spot_event_log.source.")
    triage_mode: Optional[TriageMode] = Field(None, description="Override TRIAGE_MODE for this batch.")


class Decision(Loose):
    escalated: bool
    priority: str
    category: str
    severity: str
    score: float
    decided_by: str
    agreement: str = Field(description="confirmed | rules_rejected | rules_only_escalate | both_routine | "
                                       "laya_unavailable")
    summary: str = Field(description="e.g. 'Laya: escalate (0.83) · rules: confirmed'")
    title: str


class IngestResult(Loose):
    """What the pipeline did with one event (every step, so the UI and tests can see it)."""
    event_id: Optional[str]
    request_id: str
    event_type: Optional[str]
    mission_id: Optional[str]
    action_id: Optional[str] = None
    triage_mode: str
    source: str
    raw_log_id: Optional[int] = None
    raw_duplicate: bool = False
    persisted: bool = Field(description="False when the database was unavailable (the verdict is still returned).")
    kind: Optional[str] = Field(None, description="Canonical event kind: pre_action | action | mission.")
    triage_event_id: Optional[str] = None
    skipped: Optional[str] = Field(None, description="Why the event was not triaged (e.g. MISSION_STARTED).")
    system1: Optional[JSON] = Field(None, description="Laya's answers, or status `laya_unavailable`.")
    forecast: Optional[JSON] = None
    rules: Optional[JSON] = None
    laya: Optional[JSON] = None
    decision: Optional[Decision] = None
    reasons: Optional[List[JSON]] = None
    flag: Optional[JSON] = None
    latency_ms: int
    warnings: List[str] = []


class BatchResult(BaseModel):
    request_id: str
    count: int
    escalated: int
    flags_created: int
    results: List[IngestResult]


class FeedItem(Loose):
    event_id: str
    mission_id: Optional[str]
    ts: dt.datetime
    event_type: str
    action_id: Optional[str]
    location_id: Optional[str]
    asset_id: Optional[str]
    battery_pct: Optional[int]
    payload: JSON
    ingested_at: dt.datetime
    flag_id: Optional[int] = None
    escalated: Optional[bool] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    cursor: str


class Feed(BaseModel):
    items: List[FeedItem] = Field(description="Oldest first, so a live client can append.")
    next_cursor: Optional[str] = Field(None, description="Poll with `after=<next_cursor>` for newer events.")
    prev_cursor: Optional[str] = Field(None, description="Page back with `before=<prev_cursor>`.")
