"""
mission_states.py

Mission-state definitions for the autonomous debris-capture simulation.

This state model is shared by the mission state machine, simulation engine,
mission manager, and dashboard telemetry.
"""

from enum import Enum, auto


class MissionState(Enum):
    """Autonomous mission lifecycle."""

    IDLE = auto()
    SURVEILLANCE = auto()
    TARGET_TRACKING = auto()
    TARGET_SELECTION = auto()
    PREDICTION = auto()
    CAPTURE_PLANNING = auto()
    REORIENTING = auto()
    APPROACHING = auto()
    CAPTURE_MODE_SELECTION = auto()
    GRIPPER_CAPTURE = auto()
    NET_CAPTURE = auto()
    CAPTURE_VERIFICATION = auto()
    TRANSFER_TO_CANISTER = auto()
    STORAGE_CONFIRMATION = auto()
    RETURN_TO_ORBIT = auto()
    ABORT = auto()
    COMPLETED = auto()


class CaptureMode(Enum):
    """Available autonomous capture mechanisms."""

    GRIPPER = "gripper"
    NET = "net"


class AbortReason(Enum):
    """Autonomous abort categories."""

    COLLISION_RISK = "external_collision_risk"

    SENSOR_DROPOUT = "internal_sensor_dropout"

    MECHANISM_HEALTH_CRITICAL = (
        "internal_mechanism_health_critical"
    )

    FUEL_BELOW_SAFETY_THRESHOLD = (
        "internal_fuel_below_safety_threshold"
    )

    PREDICTION_UNCERTAINTY_HIGH = (
        "prediction_uncertainty_high"
    )

    TARGET_LOST = "target_lost"

    CAPTURE_FAILURE = "capture_failure"

    STORAGE_FAILURE = "storage_failure"

    GUIDANCE_ERROR = "guidance_error"

    MANUAL_TEST_OVERRIDE = "test_only_manual_override"


# Only these transitions are permitted.
#
# The state machine decides when a transition occurs using internal
# telemetry, sensor estimates, guidance results, mechanism health,
# resource state, and mission-planner decisions.
ALLOWED_TRANSITIONS = {

    MissionState.IDLE: {
        MissionState.SURVEILLANCE,
    },

    MissionState.SURVEILLANCE: {
        MissionState.TARGET_TRACKING,
        MissionState.ABORT,
    },

    MissionState.TARGET_TRACKING: {
        MissionState.TARGET_SELECTION,
        MissionState.ABORT,
    },

    MissionState.TARGET_SELECTION: {
        MissionState.PREDICTION,
        MissionState.ABORT,
    },

    MissionState.PREDICTION: {
        MissionState.CAPTURE_PLANNING,
        MissionState.ABORT,
    },

    MissionState.CAPTURE_PLANNING: {
        MissionState.REORIENTING,
        MissionState.ABORT,
    },

    MissionState.REORIENTING: {
        MissionState.APPROACHING,
        MissionState.ABORT,
    },

    MissionState.APPROACHING: {
        MissionState.CAPTURE_MODE_SELECTION,
        MissionState.ABORT,
    },

    MissionState.CAPTURE_MODE_SELECTION: {
        MissionState.GRIPPER_CAPTURE,
        MissionState.NET_CAPTURE,
        MissionState.ABORT,
    },

    MissionState.GRIPPER_CAPTURE: {
        MissionState.CAPTURE_VERIFICATION,
        MissionState.ABORT,
    },

    MissionState.NET_CAPTURE: {
        MissionState.CAPTURE_VERIFICATION,
        MissionState.ABORT,
    },

    MissionState.CAPTURE_VERIFICATION: {
        MissionState.TRANSFER_TO_CANISTER,
        MissionState.ABORT,
    },

    MissionState.TRANSFER_TO_CANISTER: {
        MissionState.STORAGE_CONFIRMATION,
        MissionState.ABORT,
    },

    MissionState.STORAGE_CONFIRMATION: {
        MissionState.RETURN_TO_ORBIT,
        MissionState.ABORT,
    },

    MissionState.RETURN_TO_ORBIT: {
        MissionState.SURVEILLANCE,
        MissionState.COMPLETED,
        MissionState.ABORT,
    },

    MissionState.ABORT: {
        MissionState.SURVEILLANCE,
        MissionState.IDLE,
    },

    MissionState.COMPLETED: {
        MissionState.IDLE,
    },
}