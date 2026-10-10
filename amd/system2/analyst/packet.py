"""Normalize supplied packet evidence; no retrieval, fixture substitution, or tools."""
from dataclasses import dataclass
import json
import math
from typing import Callable

from .backend_contract import BackendAction, BackendAssessRequest, BackendAssessResponse


@dataclass(frozen=True)
class PreparedPacket:
    flag_id: int
    question: str
    content: dict[str, str]
    allowed_actions: tuple[str, ...]
    suggested_action: str | None
    insufficient_context: bool


# Only emitted evidence fields are consumed. Additive unknown data and identifiers
# cannot masquerade as grounding content. Nested IDs get their own resolution entry.
TEXT_FIELDS = frozenset({"fact", "text", "content", "status", "reported_status", "mission_status",
    "description", "action_type", "failure_type", "battery_status", "configuration_version", "name",
    "mission_name", "type", "criticality", "zone", "environment", "measurement_type", "unit", "quality",
    "trust", "assessment", "anomaly_type", "severity", "when", "q", "answer", "meaning", "priority",
    "category", "escalate", "reading_trust", "suggested_action", "mission_misleading", "why", "rule",
    "detail", "action", "note", "operator"})
NUMBER_FIELDS = frozenset({"sequence", "battery_pct", "duration_sec", "duration_min", "value", "p",
    "start_battery_pct", "end_battery_pct", "actions_total", "actions_failed", "true_health_pct", "score",
    "n", "n_success", "success_rate_pct"})
BOOL_FIELDS = frozenset({"operator_review_required", "correct", "status_misleading", "escalated", "in_safe_band"})
OBJECT_FIELDS = frozenset({"mission", "asset", "location", "validator", "true_health", "worst_anomaly"})
LIST_FIELDS = frozenset({"readings", "anomalies", "actions", "operator_acks", "reasons"})


def _evidence_object(obj: dict, resolved: dict[str, str]) -> dict:
    identifier = obj.get("id")
    if identifier is not None and (not isinstance(identifier, str) or not identifier.strip()):
        raise ValueError("id must be a nonblank string")
    values = {}
    for key, value in obj.items():
        if key in TEXT_FIELDS:
            if value is not None and not isinstance(value, str):
                raise ValueError("%s must be a string or null" % key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
        elif key in NUMBER_FIELDS:
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError("%s must be a finite number or null" % key)
            if value is not None:
                values[key] = value
        elif key in BOOL_FIELDS:
            if value is not None and type(value) is not bool:
                raise ValueError("%s must be a boolean or null" % key)
            if value is not None:
                values[key] = value
        elif key in OBJECT_FIELDS:
            if value is not None and not isinstance(value, dict):
                raise ValueError("%s must be an object or null" % key)
            nested = _evidence_object(value, resolved) if value is not None else {}
            if nested:
                values[key] = nested
        elif key in LIST_FIELDS:
            if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
                raise ValueError("%s must be a list of objects" % key)
            nested = [_evidence_object(item, resolved) for item in value]
            if any(nested):
                values[key] = [n for n in nested if n]
        elif key in ("safe_band", "ci95_pct"):
            if (not isinstance(value, list) or len(value) != 2 or
                    any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in value)):
                raise ValueError("%s must be a numeric pair" % key)
            if any(v is not None for v in value):
                values[key] = value
        elif key == "anomalies_by_severity":
            if not isinstance(value, dict) or any(type(v) is not int or v < 0 for v in value.values()):
                raise ValueError("anomalies_by_severity must map severities to nonnegative integers")
            counts = {k: v for k, v in value.items() if k in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
            if counts:
                values[key] = counts
        elif key == "failure_types":
            if not isinstance(value, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0
                                                  for k, v in value.items()):
                raise ValueError("failure_types must map failure types to nonnegative counts")
            if value:
                values[key] = value
    # A document's title/metadata alone must not rescue blank content.
    text = next((values[k] for k in ("fact", "text", "content") if k in values), None)
    if any(k in obj for k in ("fact", "text", "content")):
        content = text or ""
    else:
        content = json.dumps(values, sort_keys=True, ensure_ascii=False) if values else ""
    if identifier:
        if identifier in resolved and resolved[identifier] != content:
            raise ValueError("conflicting content for duplicate id %s" % identifier)
        resolved[identifier] = content
    return values


def normalize_packet(body: BackendAssessRequest) -> PreparedPacket:
    p = body.context
    question = p.get("question", "What needs operator attention?")
    if not isinstance(question, str):
        raise ValueError("question must be a string")
    raw_actions = p.get("allowed_actions", {})
    if not isinstance(raw_actions, (dict, list)):
        raise ValueError("allowed_actions must be a mapping or list")
    actions = list(raw_actions)
    for code in actions:
        if not isinstance(code, str) or code not in BackendAction._value2member_map_:
            raise ValueError("unknown action code")
    if isinstance(raw_actions, dict) and any(not isinstance(v, str) for v in raw_actions.values()):
        raise ValueError("action meanings must be strings")
    suggested = p.get("suggested_action")
    if suggested is not None and (not isinstance(suggested, str) or suggested not in actions):
        raise ValueError("suggested_action must belong to supplied allowed_actions")
    content = {}
    for name in ("facts", "manual", "policy", "similar_incidents", "asset_history", "system1"):
        items = p.get(name, [])
        if not isinstance(items, list):
            raise ValueError("%s must be a list" % name)
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("evidence items must be objects")
            _evidence_object(item, content)
    for name in ("event", "mission", "flag"):
        if name in p:
            if not isinstance(p[name], dict):
                raise ValueError("%s must be an object" % name)
            _evidence_object(p[name], content)
    guard = False
    for name in ("missing", "gaps", "citation_ids"):
        items = p.get(name, [])
        if not isinstance(items, list) or any(not isinstance(v, str) for v in items):
            raise ValueError("%s must be a string list" % name)
        if name == "citation_ids":
            guard = guard or any(not content.get(i) for i in items)
        else:
            guard = guard or bool(items)
    if "insufficient_context" in p and type(p["insufficient_context"]) is not bool:
        raise ValueError("insufficient_context must be boolean")
    content = {i: text for i, text in content.items() if text}
    return PreparedPacket(body.flag_id, question, content, tuple(dict.fromkeys(actions + ["MANUAL_REVIEW"])),
                          suggested, guard or p.get("insufficient_context", False) or not content or not actions)


def stub_assessment(p: PreparedPacket) -> BackendAssessResponse:
    identifier, claim = next(iter(p.content.items()))
    return BackendAssessResponse(flag_id=p.flag_id, question=p.question, answer=claim,
                                 evidence=[{"claim": claim, "ids": [identifier]}],
                                 recommended_action=p.suggested_action or p.allowed_actions[0],
                                 confidence="medium", insufficient_context=False, path="stub")


def assess_prepared_packet(p: PreparedPacket,
                           generate: Callable[[PreparedPacket], BackendAssessResponse] = stub_assessment
                           ) -> BackendAssessResponse:
    if p.insufficient_context:
        return BackendAssessResponse(flag_id=p.flag_id, question=p.question,
                                     answer="Insufficient supplied context; request manual review.", evidence=[],
                                     recommended_action="MANUAL_REVIEW", confidence="low",
                                     insufficient_context=True, path="insufficient_context")
    result = BackendAssessResponse.model_validate(generate(p))
    if result.flag_id != p.flag_id or result.insufficient_context:
        raise ValueError("assessment does not match prepared packet")
    if result.recommended_action.value not in p.allowed_actions:
        raise ValueError("assessment action not allowed by packet")
    for evidence in result.evidence:
        if any(not p.content.get(i) for i in evidence.ids):
            raise ValueError("assessment cites unresolved evidence")
    return result
