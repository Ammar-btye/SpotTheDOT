"""Shared model-independent baseline and safe fallback (generation fields only)."""
from .packet import PreparedPacket


def template_assessment(prepared: PreparedPacket) -> dict:
    insufficient = prepared.insufficient_context or not prepared.content
    evidence = [] if insufficient else [
        {'claim': prepared.content[identifier], 'ids': [identifier]}
        for identifier in sorted(prepared.content)[:2]
    ]
    action = 'MANUAL_REVIEW' if insufficient else (prepared.suggested_action or 'MANUAL_REVIEW')
    return {
        'evidence': evidence,
        'answer': 'Insufficient supplied context; request manual review.' if insufficient else ' '.join(e['claim'] for e in evidence),
        'question': prepared.question,
        'recommended_action': action,
        'confidence': 'low' if insufficient else 'medium',
        'insufficient_context': insufficient,
    }
