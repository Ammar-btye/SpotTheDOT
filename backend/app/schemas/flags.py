from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .common import JSON, Loose, Page


class Flag(Loose):
    flag_id: int
    event_id: Optional[str]
    mission_id: Optional[str]
    action_id: Optional[str]
    location_id: Optional[str]
    asset_id: Optional[str]
    score: float
    severity: str
    title: str
    reasons: List[JSON] = Field(description="Both verdicts first (laya_verdict | laya_unavailable, rules_verdict), "
                                            "then the fired policy rules [{rule, detail, weight}].")
    escalated: bool
    status: str
    created_at: dt.datetime
    priority: Optional[str] = None
    category: Optional[str] = None


class FlagList(BaseModel):
    items: List[Flag]
    page: Page


class FlagDetail(BaseModel):
    flag: Flag
    event: Optional[JSON] = None
    acks: List[JSON] = []
    assessment: Optional[JSON] = None
    system1: List[JSON] = Field([], description="Laya's stored answers for this event (system1_predictions).")


class ContextPacket(Loose):
    """The context packet System 2 reads. From the MCP server (`source: mcp`) or SQL-only (`sql_fallback`)."""
    source: Literal["mcp", "sql_fallback"]
    question: Optional[str] = None
    gaps: Optional[List[str]] = None


class Explanation(Loose):
    """Orbit-style explanation: question / answer / reasoning / recommended action."""
    question: Optional[str]
    answer: Optional[str]
    reasoning: Optional[str]
    recommended_action: Optional[str]
    severity_assessment: Optional[str] = None
    confidence: Optional[float] = None
    model: Optional[str] = None
    source: Literal["system2", "template"]
    cached: bool = False
    fallback_reason: Optional[str] = None
    context_source: Optional[str] = None
    assessment_id: Optional[int] = None


class AckIn(BaseModel):
    action: Literal["ACKNOWLEDGE", "RESOLVE", "ESCALATE", "NOTE"] = "ACKNOWLEDGE"
    note: Optional[str] = Field(None, max_length=4000, description="Free text. Indexed for RAG as an operator_note.")
    operator: str = Field("operator", min_length=1, max_length=100)


class AckOut(BaseModel):
    ack: Dict[str, Any]
    flag_status: str
    rag_indexed: bool = Field(description="True if the note was embedded and upserted as documents.note:<ack_id>.")
    doc_id: Optional[str] = None
    rag_error: Optional[str] = None
