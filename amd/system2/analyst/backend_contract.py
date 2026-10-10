"""Authoritative backend HTTP transport; legacy contract.py remains offline-only."""
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BACKEND_CONTRACT_VERSION = "2026-10-10.backend.1"


class BackendAction(str, Enum):
    DISPATCH_TECHNICIAN = "DISPATCH_TECHNICIAN"
    SCHEDULE_MAINTENANCE = "SCHEDULE_MAINTENANCE"
    REINSPECT_NEXT_ROUTE = "REINSPECT_NEXT_ROUTE"
    ESCALATE_TO_SUPERVISOR = "ESCALATE_TO_SUPERVISOR"
    MONITOR = "MONITOR"
    REINSPECT_NOW = "REINSPECT_NOW"
    MANUAL_READING = "MANUAL_READING"
    CHECK_SENSOR_PAYLOAD = "CHECK_SENSOR_PAYLOAD"
    CLEAR_PATH = "CLEAR_PATH"
    ADJUST_WAYPOINT = "ADJUST_WAYPOINT"
    UPDATE_AUTOWALK_MAP = "UPDATE_AUTOWALK_MAP"
    RETURN_TO_DOCK = "RETURN_TO_DOCK"
    CHARGE_BEFORE_NEXT_MISSION = "CHARGE_BEFORE_NEXT_MISSION"
    CHECK_COMMS = "CHECK_COMMS"
    ABORT_MISSION = "ABORT_MISSION"
    REVIEW_MISSION = "REVIEW_MISSION"
    RERUN_FAILED_ACTIONS = "RERUN_FAILED_ACTIONS"
    NO_ACTION = "NO_ACTION"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class BackendAssessRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    flag_id: int = Field(gt=0)
    flag: dict[str, Any]
    context: dict[str, Any]
    request_id: str | None = None
    event: dict[str, Any] | None = None
    reasons: list[str | None] | None = None


class BackendEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claim: str = Field(min_length=1)
    ids: list[str] = Field(min_length=1)


class BackendAssessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    evidence: list[BackendEvidence]
    answer: str = Field(min_length=1)
    question: str
    recommended_action: BackendAction = Field(strict=False)
    confidence: Literal["high", "medium", "low"]
    insufficient_context: bool
    flag_id: int = Field(gt=0)
    model: Literal["stub"] = "stub"
    latency_ms: int = Field(ge=0, default=0)
    tokens_per_sec: float | None = Field(ge=0, default=None)
    path: Literal["stub", "insufficient_context"]

    @model_validator(mode="after")
    def safe_insufficient(self):
        if self.insufficient_context:
            if (self.evidence or self.confidence != "low" or self.recommended_action != BackendAction.MANUAL_REVIEW
                    or self.path != "insufficient_context"):
                raise ValueError("insufficient context requires empty evidence and safe manual review")
        elif self.path != "stub" or not self.evidence:
            raise ValueError("complete assessment requires evidence and stub path")
        return self
