"""The typed questions Laya answers, one set per event kind.

Every question is a `choice`. Laya's model card reports that `noul` can lock onto its label pair on
the English checkpoint (issue #156), so yes/no questions use neutral keys A/B with the wording in the
descriptions. Options stay short: all options of a question share the 192-token head budget.
"""
QUESTIONS = {
    # ── Track A: before the action runs ──
    "will_fail": {
        "type": "choice",
        "instructions": "Before SPOT runs this inspection action, will the action fail?",
        "criteria": {"A": "yes, the action is likely to fail", "B": "no, the action is likely to succeed"},
    },
    "failure_mode": {
        "type": "choice",
        "instructions": "If this action fails, what kind of failure is it most likely to be?",
        "criteria": {
            "navigation": "the robot cannot reach or localize at the waypoint",
            "data_quality": "the sensor reading times out, is noisy or unreliable, or the target is not detected",
            "robot_health": "the robot loses communication",
            "none": "the action will succeed",
        },
    },
    "anomaly_expected": {
        "type": "choice",
        "instructions": "Will this action raise an anomaly that an operator should know about?",
        "criteria": {"A": "yes, an anomaly is likely", "B": "no anomaly is likely"},
    },
    # ── Track B: after the action / mission ──
    "escalate": {
        "type": "choice",
        "instructions": "Should this SPOT event be escalated to the analyst for operator attention now?",
        "criteria": {"A": "yes, escalate: it needs operator attention", "B": "no, log only: it is routine"},
    },
    "priority": {
        "type": "choice",
        "instructions": "What operator priority does this SPOT event deserve?",
        "criteria": {
            "P1": "immediate: critical equipment or the robot is at serious risk",
            "P2": "this shift: degraded equipment, an important missed inspection, or low battery",
            "P3": "next route: a minor issue to recheck",
            "P4": "informational: normal operation",
        },
    },
    "category": {
        "type": "choice",
        "instructions": "What is the main issue in this SPOT event?",
        "criteria": {
            "equipment": "the inspected equipment shows a problem",
            "data_quality": "the reading or sensor data cannot be trusted",
            "navigation": "the robot could not reach or localize at the waypoint",
            "robot_health": "the robot itself is at risk: low battery or lost communication",
            "none": "nothing is wrong",
        },
    },
    "reading_trust": {
        "type": "choice",
        "instructions": "Can the reading SPOT reported for this action be trusted?",
        "criteria": {"A": "yes, the reading can be trusted", "B": "no, the reading should not be trusted",
                     "C": "no reading was reported"},
    },
    "mission_misleading": {
        "type": "choice",
        "instructions": "Does this mission's reported status hide failed actions or serious anomalies?",
        "criteria": {"A": "yes, the status looks fine but hides problems",
                     "B": "no, the status reflects what happened"},
    },
}

QUESTION_SETS = {
    "pre_action": ["will_fail", "failure_mode", "anomaly_expected"],
    "action": ["escalate", "priority", "category", "reading_trust"],
    "mission": ["escalate", "priority", "mission_misleading"],
}

TRACK = {"pre_action": "predict", "action": "triage", "mission": "triage"}

# The class counted as "positive" for precision/recall on binary questions.
POSITIVE = {"will_fail": "A", "anomaly_expected": "A", "escalate": "A", "mission_misleading": "A"}


def questions_for(kind: str) -> dict:
    return {q: QUESTIONS[q] for q in QUESTION_SETS[kind]}
