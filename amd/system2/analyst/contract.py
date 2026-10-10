"""System 2 typed contract: the flag System 2 receives, the context packet it builds, the explanation it returns.

This file supersedes the `POST /v1/assess` sketch in docs/ARCHITECTURE.md section 4. System 2 owns the flag contract;
System 1 (Laya + validator) conforms to `Flag`, and until then flags are faked from amd/system1/triage/policy.py.
Packet sections and their order follow research R2, the explanation schema follows R3
(research/tech-system2-context-distill-2026-10-10.md). Model field order IS the JSON Schema property order, and the
Phase 2 grammar depends on it, so never reorder fields. Any wire change bumps CONTRACT_VERSION.

Decisions (plan 01-01, open to veto before web integrates):
  A1  The request carries only the System 1 flag; System 2 builds the context packet itself (DATA-01).
  A2  Mission-level flags are kind="mission" with category="mission_health" (policy.label_mission has no category).
  A3  Event rows get the ID prefix E#, so every packet row is citable (alongside F/S/W/I from PKT-02).
  A4  The Action enum and ACTIONS_BY_CATEGORY are System 2's proposal; the validator-to-action map is Phase 2 work.
  A5  confidence is low|med|high (R3), not a float; severity_assessment/reasoning are replaced by cited evidence.
  A6  The stub returns the matched fixture response with meta.model="stub" and keeps the fixture's path.
  A7  Every model forbids extra fields (unknown field -> 422); contract changes bump CONTRACT_VERSION.
  A8  Strict types: the runtime accepts exactly what the exported JSON Schema allows (no "yes" -> bool, no "5" -> int,
      no int -> datetime). Timestamps are naive ISO 8601 strings in kit site time, the only form the kit CSVs use
      ("2026-09-01T18:27:54"); an offset or "Z" is rejected so naive and aware values never mix.
"""
import re
from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional, Tuple, Union, get_args

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema, model_validator

CONTRACT_VERSION = "2026-10-10.1"

# ── enums ────────────────────────────────────────────────────────────────────

Category = Literal["equipment", "robot_health", "navigation", "data_quality", "mission_health"]
Kind = Literal["action", "mission"]
Priority = Literal["P1", "P2", "P3", "P4"]
Trust = Literal["trusted", "untrusted", "none"]
Source = Literal["policy", "system1"]
Split = Literal["train", "holdout"]
Action = Literal[
    "dispatch_technician",       # send a person to the asset now
    "schedule_maintenance",      # book a planned work order, not urgent
    "reinspect_next_mission",    # add the waypoint to the next SPOT route
    "verify_reading_manually",   # take the reading by hand; the robot's value is not trusted
    "recharge_robot",            # dock and charge SPOT before further work
    "check_robot_comms",         # inspect SPOT's radio/network link
    "clear_route_obstruction",   # remove whatever blocks the path
    "relocalize_robot",          # re-run localization / fiducial check
    "monitor",                   # no action now; watch the trend
    "manual_review",             # a human must look; System 2 cannot tell
]
Confidence = Literal["low", "med", "high"]
PathTaken = Literal["first_pass", "retry", "fallback", "insufficient_context"]
Section = Literal["event", "facts", "asset", "waypoint", "incidents"]

FlagId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,64}$")]
SafeId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,64}$")]
MissionId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")]
RowId = Annotated[str, Field(pattern=r"^[EFSWI][1-9][0-9]?$")]
Prob = Annotated[float, Field(ge=0, le=1)]
Scalar = Union[str, int, float, bool, None]

# Decision A8. Same regex at runtime and in the exported schema, so both accept exactly the same strings. The schema
# drops `format: date-time` on purpose: RFC 3339 date-time requires an offset, which kit timestamps never carry.
NAIVE_ISO = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?$"


def _naive_iso(v):
    """Pass a naive ISO 8601 string (or naive datetime) on to datetime parsing; ValueError on anything else."""
    if isinstance(v, str) and re.fullmatch(NAIVE_ISO, v):
        return v
    if isinstance(v, datetime) and v.tzinfo is None:
        return v
    raise ValueError("timestamp must be a naive ISO 8601 string like '2026-09-01T18:27:54' (kit site time, "
                     "no offset or 'Z'), got %s" % type(v).__name__)


Timestamp = Annotated[datetime, Field(strict=False), BeforeValidator(_naive_iso),
                      WithJsonSchema({"type": "string", "pattern": NAIVE_ISO,
                                      "description": "Naive ISO 8601 kit site time, no offset or Z"})]

CATEGORIES: Tuple[str, ...] = get_args(Category)
ACTIONS: Tuple[str, ...] = get_args(Action)
SECTIONS: Tuple[str, ...] = get_args(Section)

SECTION_PREFIX: Dict[str, str] = {"event": "E", "facts": "F", "asset": "S", "waypoint": "W", "incidents": "I"}
EXPLANATION_ORDER = ("evidence", "answer", "question", "recommended_action", "confidence", "insufficient_context")

# Every packet must offer "manual_review": the insufficient-context and fallback paths always answer with it, so a
# packet without it would make those answers unconstructible (a 500 instead of the safe answer). "monitor" is listed
# for every category but a packet may leave it out (an insufficient-context packet carries only "manual_review").
ALWAYS_ALLOWED = "manual_review"

# Ordered most-specific first.
ACTIONS_BY_CATEGORY: Dict[str, Tuple[str, ...]] = {
    "equipment": ("dispatch_technician", "schedule_maintenance", "reinspect_next_mission", "monitor",
                  "manual_review"),
    "robot_health": ("recharge_robot", "check_robot_comms", "reinspect_next_mission", "monitor", "manual_review"),
    "navigation": ("clear_route_obstruction", "relocalize_robot", "reinspect_next_mission", "monitor",
                   "manual_review"),
    "data_quality": ("verify_reading_manually", "reinspect_next_mission", "schedule_maintenance", "monitor",
                     "manual_review"),
    "mission_health": ACTIONS,
}


# ── models ───────────────────────────────────────────────────────────────────

class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)        # decisions A7, A8


class Reason(_Model):
    rule: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,40}$")]
    text: Annotated[str, Field(min_length=1, max_length=200)]


class Flag(_Model):
    flag_id: FlagId
    kind: Kind
    event_id: SafeId
    mission_id: MissionId
    action_id: Optional[SafeId] = None
    timestamp: Timestamp
    category: Category
    priority: Priority
    escalate: bool
    reading_trust: Trust
    reasons: Annotated[List[Reason], Field(min_length=1, max_length=10)]
    scores: Annotated[Dict[str, Prob], Field(max_length=16)] = {}
    source: Source = "system1"
    split: Optional[Split] = None

    @model_validator(mode="after")
    def _kind_rules(self) -> "Flag":
        if self.kind == "action" and (self.action_id is None or self.category == "mission_health"):
            raise ValueError("action flag needs action_id and a non-mission category, got %r / %r"
                             % (self.action_id, self.category))
        if self.kind == "mission" and (self.action_id is not None or self.category != "mission_health"):
            raise ValueError("mission flag needs action_id None and category 'mission_health', got %r / %r"
                             % (self.action_id, self.category))       # decision A2
        return self


class Row(_Model):
    id: RowId
    text: Annotated[str, Field(min_length=1, max_length=300)]
    ref: Annotated[Optional[str], Field(max_length=80)] = None     # kit row reference, e.g. "actions.csv:A0009"
    data: Annotated[Dict[str, Scalar], Field(max_length=12)] = {}


Rows = Annotated[List[Row], Field(max_length=12)]


class ContextPacket(_Model):
    flag: Flag
    event: Rows = []
    facts: Rows = []
    asset: Rows = []
    waypoint: Rows = []
    incidents: Annotated[List[Row], Field(max_length=5)] = []
    allowed_actions: Annotated[List[Action], Field(min_length=1, max_length=10)]
    validator_action: Optional[Action] = None
    missing: List[Section] = []
    question: Annotated[str, Field(min_length=1, max_length=300)]     # last, per R2

    def ids(self) -> List[str]:
        """Every row ID, in SECTIONS order then row order."""
        return [r.id for sec in SECTIONS for r in getattr(self, sec)]

    @model_validator(mode="after")
    def _rows_and_actions(self) -> "ContextPacket":
        for sec in SECTIONS:
            bad = [r.id for r in getattr(self, sec) if r.id[0] != SECTION_PREFIX[sec]]
            if bad:
                raise ValueError("section %r only takes %s# rows, got %r" % (sec, SECTION_PREFIX[sec], bad))
        ids = self.ids()
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError("duplicate row IDs %r" % dup)
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ValueError("duplicate allowed_actions %r" % self.allowed_actions)
        extra = [a for a in self.allowed_actions if a not in ACTIONS_BY_CATEGORY[self.flag.category]]
        if extra:
            raise ValueError("allowed_actions %r not allowed for category %r" % (extra, self.flag.category))
        if ALWAYS_ALLOWED not in self.allowed_actions:
            raise ValueError("allowed_actions %r must include %r" % (self.allowed_actions, ALWAYS_ALLOWED))
        if self.validator_action is not None and self.validator_action not in self.allowed_actions:
            raise ValueError("validator_action %r not in allowed_actions" % self.validator_action)
        if len(set(self.missing)) != len(self.missing):
            raise ValueError("duplicate missing sections %r" % self.missing)
        full = [sec for sec in self.missing if getattr(self, sec)]
        if full:
            raise ValueError("sections %r are listed as missing but have rows" % full)
        return self


class Evidence(_Model):
    claim: Annotated[str, Field(min_length=1, max_length=300)]
    ids: Annotated[List[RowId], Field(min_length=1, max_length=5)]


class Explanation(_Model):
    evidence: Annotated[List[Evidence], Field(max_length=6)]
    answer: Annotated[str, Field(min_length=1, max_length=600)]
    question: Annotated[str, Field(min_length=1, max_length=300)]
    recommended_action: Action
    confidence: Confidence
    insufficient_context: bool

    @model_validator(mode="after")
    def _evidence_rules(self) -> "Explanation":
        if not self.insufficient_context and not self.evidence:
            raise ValueError("a sufficient-context explanation needs at least one evidence item")
        if self.insufficient_context and self.recommended_action != "manual_review":
            raise ValueError("insufficient context must recommend 'manual_review', got %r"
                             % self.recommended_action)  # no LLM runs on insufficient context (PKT-04)
        if self.insufficient_context and (self.evidence or self.confidence != "low"):
            raise ValueError("insufficient context carries no evidence and confidence 'low', got %d evidence / %r"
                             % (len(self.evidence), self.confidence))  # a half-run model must not pass (PKT-04)
        return self


class Meta(_Model):
    model: Annotated[str, Field(min_length=1, max_length=80)]
    prompt_ver: Annotated[Optional[str], Field(max_length=40)] = None
    path: PathTaken
    latency_ms: Annotated[int, Field(ge=0)]
    tokens_per_sec: Annotated[Optional[float], Field(ge=0)] = None
    packet_hash: Annotated[Optional[str], Field(pattern=r"^[0-9a-f]{8,64}$")] = None


class AssessRequest(_Model):
    flag: Flag


class AssessResponse(_Model):
    contract_version: str = CONTRACT_VERSION
    flag_id: FlagId
    explanation: Explanation
    packet: ContextPacket
    meta: Meta

    @model_validator(mode="after")
    def _grounded(self) -> "AssessResponse":
        if self.flag_id != self.packet.flag.flag_id:
            raise ValueError("flag_id %r != packet.flag.flag_id %r" % (self.flag_id, self.packet.flag.flag_id))
        known = set(self.packet.ids())
        cited = [i for ev in self.explanation.evidence for i in ev.ids if i not in known]
        if cited:
            raise ValueError("evidence cites row IDs %r that are not in the packet" % cited)
        if self.explanation.recommended_action not in self.packet.allowed_actions:
            raise ValueError("recommended_action %r not in packet.allowed_actions %r"
                             % (self.explanation.recommended_action, self.packet.allowed_actions))
        if self.explanation.insufficient_context != bool(self.packet.missing):
            raise ValueError("insufficient_context %r disagrees with packet.missing %r"
                             % (self.explanation.insufficient_context, self.packet.missing))
        return self
