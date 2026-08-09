"""
mission_states.py
Defines the mission state enum and abort-reason taxonomy.

Solves:
- Challenge 5 (states restricted to internally-triggered transitions)
- Challenge 8 (ABORT state for collision avoidance)
- Challenge 13 (distinguishes internal-fault Aborts from external ones)
"""

from enum import Enum, auto


class MissionState(Enum):
    IDLE = auto()
    TRACKING = auto()
    APPROACHING = auto()
    CAPTURING = auto()
    ABORT = auto()
    COMPLETED = auto()


# Transitions allowed FROM each state, and the internal telemetry
# condition (not an external command) that triggers each one. This table
# is documentation-as-code for interface_spec.md's "no ground command"
# constraint (Challenge 5).
ALLOWED_TRANSITIONS = {
    MissionState.IDLE: {MissionState.TRACKING},
    MissionState.TRACKING: {MissionState.APPROACHING, MissionState.ABORT, MissionState.IDLE},
    MissionState.APPROACHING: {MissionState.CAPTURING, MissionState.ABORT, MissionState.TRACKING},
    MissionState.CAPTURING: {MissionState.COMPLETED, MissionState.ABORT},
    MissionState.ABORT: {MissionState.IDLE, MissionState.TRACKING},
    MissionState.COMPLETED: {MissionState.IDLE},
}


class AbortReason(Enum):
    """Challenge 13: distinguish external threats from internal faults so
    the demo narrative ('responds to both') has real log data behind it."""
    COLLISION_RISK = "external_collision_risk"          # Challenge 8
    SENSOR_DROPOUT = "internal_sensor_dropout"           # Challenge 13
    MECHANISM_HEALTH_CRITICAL = "internal_mechanism_health_critical"  # Challenge 13
    FUEL_BELOW_SAFETY_THRESHOLD = "internal_fuel_below_safety_threshold"  # Challenge 4/13
    MANUAL_TEST_OVERRIDE = "test_only_manual_override"   # never used during RENDEZVOUS->CAPTURE in flight logic
