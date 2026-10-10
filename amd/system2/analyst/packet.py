"""Normalize supplied packet evidence; no retrieval, fixture substitution, or tools."""
from dataclasses import dataclass
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
    for name in ("facts", "manual", "policy", "similar_incidents", "asset_history"):
        items = p.get(name, [])
        if not isinstance(items, list):
            raise ValueError("%s must be a list" % name)
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("evidence items must be objects")
            identifier = item.get("id")
            if identifier is not None and not isinstance(identifier, str):
                raise ValueError("id must be a string")
            for key in ("fact", "text", "content"):
                if key in item and not isinstance(item[key], str):
                    raise ValueError("evidence text must be a string")
            text = next((item[k].strip() for k in ("fact", "text", "content") if item.get(k, "").strip()), "")
            if identifier and text:
                content[identifier] = text
    return PreparedPacket(body.flag_id, question, content, tuple(dict.fromkeys(actions + ["MANUAL_REVIEW"])),
                          suggested, not bool(content) or not bool(actions))


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
