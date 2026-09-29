"""
ADCS Autonomous Mission Decision Logic

Conceptual mission-level decision logic used to synchronize:
- Mission Control
- Mission Visualization
- Live Orbital Simulation

This is a demonstration and visualization decision model.
"""

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):

    HOLD = "HOLD"
    ABORT = "ABORT"

    PROCEED_SMALL = "PROCEED_SMALL"
    PROCEED_LARGE = "PROCEED_LARGE"
    PROCEED_MULTIPLE = "PROCEED_MULTIPLE"


@dataclass
class TargetAssessment:

    size_m: float
    relative_speed_mps: float
    range_km: float
    risk: str

    group_count: int = 1
    tumbling: bool = False
    sensor_confidence: float = 0.95


def evaluate_target(assessment: TargetAssessment):

    """
    Determines one explicit operational decision.

    Priority:
    1. Sensor confidence
    2. Unsafe relative motion
    3. Observation / hold conditions
    4. Multiple-object capture
    5. Small-object gripper capture
    6. Large-object net capture
    """

    if assessment.sensor_confidence < 0.60:

        return (
            Decision.HOLD,
            "Sensor confidence remains below the operational authorization threshold."
        )

    if assessment.range_km < 0.01:

        return (
            Decision.ABORT,
            "Target separation has entered an unsafe proximity condition."
        )

    if assessment.relative_speed_mps > 12:

        return (
            Decision.ABORT,
            "Relative velocity exceeds the defined proximity-operation limit."
        )

    if assessment.relative_speed_mps > 5:

        return (
            Decision.HOLD,
            "Relative motion remains unsuitable for capture authorization."
        )

    if assessment.tumbling and assessment.relative_speed_mps > 3.5:

        return (
            Decision.HOLD,
            "Target attitude motion requires continued observation."
        )

    if assessment.group_count >= 2:

        return (
            Decision.PROCEED_MULTIPLE,
            "Grouped debris objects are compatible with deployable-net containment."
        )

    if assessment.size_m <= 0.75:

        return (
            Decision.PROCEED_SMALL,
            "Target geometry is compatible with precision side-arm gripper capture."
        )

    return (
        Decision.PROCEED_LARGE,
        "Target geometry favors central deployable-net capture."
    )


SCENARIOS = {

    "hold": {

        "label": "HOLD",

        "description":
            "Maintain surveillance while capture conditions remain outside operational limits.",

        "assessment": TargetAssessment(
            size_m=0.55,
            relative_speed_mps=7.2,
            range_km=0.08,
            risk="MEDIUM",
            tumbling=True
        )
    },

    "abort": {

        "label": "ABORT",

        "description":
            "Terminate proximity operations and return the spacecraft to a safe operational state.",

        "assessment": TargetAssessment(
            size_m=1.10,
            relative_speed_mps=14.5,
            range_km=0.008,
            risk="HIGH"
        )
    },

    "small": {

        "label": "PROCEED — SMALL OBJECT",

        "description":
            "Authorize precision capture using the dual side-arm gripper mechanism.",

        "assessment": TargetAssessment(
            size_m=0.42,
            relative_speed_mps=2.1,
            range_km=0.06,
            risk="HIGH"
        )
    },

    "large": {

        "label": "PROCEED — LARGE OBJECT",

        "description":
            "Authorize central deployable-net capture for a large or irregular debris object.",

        "assessment": TargetAssessment(
            size_m=1.65,
            relative_speed_mps=2.4,
            range_km=0.07,
            risk="HIGH",
            tumbling=True
        )
    },

    "multiple": {

        "label": "PROCEED — MULTIPLE OBJECTS",

        "description":
            "Authorize grouped-object containment using the central deployable-net capture mechanism.",

        "assessment": TargetAssessment(
            size_m=0.65,
            relative_speed_mps=2.2,
            range_km=0.08,
            risk="HIGH",
            group_count=3
        )
    }
}


PHASES = [

    "ORBITAL SURVEILLANCE",

    "MULTI-OBJECT TRACKING",

    "TARGET PRIORITIZATION",

    "SPACECRAFT REORIENTATION",

    "RENDEZVOUS",

    "PROXIMITY APPROACH",

    "MISSION DECISION",

    "CAPTURE EXECUTION",

    "ONBOARD TRANSFER",

    "SECURE CONTAINMENT",

    "SYSTEM RESET",

    "CONTINUED SURVEILLANCE"
]