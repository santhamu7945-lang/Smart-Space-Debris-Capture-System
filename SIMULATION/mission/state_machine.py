"""
Autonomous mission state machine for the Smart Space Debris Capture System.

Design intent
-------------
This module provides deterministic, telemetry-driven mission-state
transitions. External commands are deliberately excluded from the
operational transition interface.

The state machine is responsible for:
    - autonomous surveillance and target acquisition
    - target selection and prediction
    - capture planning and spacecraft reorientation
    - controlled approach
    - capture-mode selection
    - gripper/net capture
    - capture verification
    - transfer and storage
    - return-to-orbit
    - fault/collision abort handling
    - post-abort replanning

This is a simulation/engineering model. It is not flight-qualified software.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class MissionState(Enum):
    """Top-level autonomous mission states."""

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
    """Capture strategy selected by the mission planner."""

    GRIPPER = "gripper"
    NET = "net"


class AbortReason(Enum):
    """Categorized autonomous abort conditions."""

    COLLISION_RISK = "external_collision_risk"
    SENSOR_DROPOUT = "internal_sensor_dropout"
    MECHANISM_HEALTH_CRITICAL = "internal_mechanism_health_critical"
    FUEL_BELOW_SAFETY_THRESHOLD = "internal_fuel_below_safety_threshold"
    PREDICTION_UNCERTAINTY_HIGH = "prediction_uncertainty_high"
    TARGET_LOST = "target_lost"
    CAPTURE_FAILURE = "capture_failure"
    STORAGE_FAILURE = "storage_failure"
    GUIDANCE_ERROR = "guidance_error"
    MANUAL_TEST_OVERRIDE = "test_only_manual_override"


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable record of a mission-state transition."""

    from_state: MissionState
    to_state: MissionState
    trigger: str


@dataclass(frozen=True)
class AbortRecord:
    """Immutable record of an autonomous abort event."""

    reason: AbortReason
    detail: dict[str, Any]


# ---------------------------------------------------------------------------
# Allowed state transitions
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS = {
    MissionState.IDLE: {
        MissionState.SURVEILLANCE,
    },

    MissionState.SURVEILLANCE: {
        MissionState.TARGET_TRACKING,
        MissionState.IDLE,
        MissionState.ABORT,
    },

    MissionState.TARGET_TRACKING: {
        MissionState.TARGET_SELECTION,
        MissionState.SURVEILLANCE,
        MissionState.ABORT,
    },

    MissionState.TARGET_SELECTION: {
        MissionState.PREDICTION,
        MissionState.SURVEILLANCE,
        MissionState.ABORT,
    },

    MissionState.PREDICTION: {
        MissionState.CAPTURE_PLANNING,
        MissionState.TARGET_SELECTION,
        MissionState.ABORT,
    },

    MissionState.CAPTURE_PLANNING: {
        MissionState.REORIENTING,
        MissionState.TARGET_SELECTION,
        MissionState.ABORT,
    },

    MissionState.REORIENTING: {
        MissionState.APPROACHING,
        MissionState.ABORT,
    },

    MissionState.APPROACHING: {
        MissionState.CAPTURE_MODE_SELECTION,
        MissionState.TARGET_TRACKING,
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
        MissionState.APPROACHING,
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
        MissionState.SURVEILLANCE,
    },
}


class InvalidTransitionError(RuntimeError):
    """Raised when an illegal mission-state transition is requested."""


class MissionStateMachine:
    """
    Deterministic autonomous mission-state controller.

    The public transition checks accept only internal mission telemetry,
    state estimates, health information, and planner decisions.

    No operational method accepts a ground-command argument.
    """

    def __init__(self) -> None:
        self.state = MissionState.IDLE

        self.history: list[TransitionRecord] = []
        self.abort_log: list[AbortRecord] = []

        self.selected_target_id: Optional[str] = None
        self.capture_mode: Optional[CaptureMode] = None

    # ------------------------------------------------------------------
    # Core transition mechanism
    # ------------------------------------------------------------------

    def transition(
        self,
        new_state: MissionState,
        trigger_reason: str,
    ) -> MissionState:
        """
        Perform one validated state transition.

        This is the only method that changes the mission state.
        """

        allowed = ALLOWED_TRANSITIONS.get(self.state, set())

        if new_state not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition {self.state.name} -> "
                f"{new_state.name}; trigger={trigger_reason}"
            )

        self.history.append(
            TransitionRecord(
                from_state=self.state,
                to_state=new_state,
                trigger=trigger_reason,
            )
        )

        self.state = new_state
        return self.state

    # ------------------------------------------------------------------
    # Mission initialization and surveillance
    # ------------------------------------------------------------------

    def check_idle_to_surveillance(
        self,
        spacecraft_healthy: bool,
        sensors_ready: bool,
    ) -> None:
        """Start autonomous surveillance after health and sensor checks."""

        if (
            self.state == MissionState.IDLE
            and spacecraft_healthy
            and sensors_ready
        ):
            self.transition(
                MissionState.SURVEILLANCE,
                "spacecraft_healthy_and_sensors_ready",
            )

    def check_surveillance_to_tracking(
        self,
        target_detected: bool,
        track_quality_ok: bool,
    ) -> None:
        """Enter target tracking after a valid detection."""

        if (
            self.state == MissionState.SURVEILLANCE
            and target_detected
            and track_quality_ok
        ):
            self.transition(
                MissionState.TARGET_TRACKING,
                "target_detected_and_track_quality_acceptable",
            )

    # ------------------------------------------------------------------
    # Target acquisition and prediction
    # ------------------------------------------------------------------

    def check_tracking_to_selection(
        self,
        target_locked: bool,
        catalog_solution_available: bool,
    ) -> None:
        """Move from tracking to autonomous target-selection logic."""

        if (
            self.state == MissionState.TARGET_TRACKING
            and target_locked
            and catalog_solution_available
        ):
            self.transition(
                MissionState.TARGET_SELECTION,
                "target_locked_and_catalog_solution_available",
            )

    def check_selection_to_prediction(
        self,
        target_id: Optional[str],
        target_score_valid: bool,
    ) -> None:
        """Accept a selected target only when its scoring result is valid."""

        if (
            self.state == MissionState.TARGET_SELECTION
            and target_id
            and target_score_valid
        ):
            self.selected_target_id = target_id

            self.transition(
                MissionState.PREDICTION,
                "target_selected_from_autonomous_scoring",
            )

    def check_prediction_to_planning(
        self,
        trajectory_valid: bool,
        uncertainty_within_limit: bool,
    ) -> None:
        """Proceed only when the predicted encounter is sufficiently bounded."""

        if (
            self.state == MissionState.PREDICTION
            and trajectory_valid
            and uncertainty_within_limit
        ):
            self.transition(
                MissionState.CAPTURE_PLANNING,
                "trajectory_valid_and_uncertainty_within_limit",
            )

    # ------------------------------------------------------------------
    # Capture planning and approach
    # ------------------------------------------------------------------

    def check_planning_to_reorientation(
        self,
        guidance_solution_valid: bool,
        attitude_solution_valid: bool,
    ) -> None:
        """Begin spacecraft reorientation once guidance is valid."""

        if (
            self.state == MissionState.CAPTURE_PLANNING
            and guidance_solution_valid
            and attitude_solution_valid
        ):
            self.transition(
                MissionState.REORIENTING,
                "guidance_and_attitude_solution_valid",
            )

    def check_reorientation_to_approach(
        self,
        attitude_aligned: bool,
        relative_velocity_within_limit: bool,
    ) -> None:
        """Begin final approach after alignment and velocity checks."""

        if (
            self.state == MissionState.REORIENTING
            and attitude_aligned
            and relative_velocity_within_limit
        ):
            self.transition(
                MissionState.APPROACHING,
                "attitude_aligned_and_relative_velocity_safe",
            )

    def check_approach_to_capture_mode_selection(
        self,
        relative_distance_km: float,
        capture_window_km: float,
        relative_velocity_mps: float,
        maximum_capture_velocity_mps: float,
    ) -> None:
        """Enter capture-mode selection only inside the controlled window."""

        if (
            self.state == MissionState.APPROACHING
            and relative_distance_km <= capture_window_km
            and abs(relative_velocity_mps) <= maximum_capture_velocity_mps
        ):
            self.transition(
                MissionState.CAPTURE_MODE_SELECTION,
                "controlled_capture_window_reached",
            )

    # ------------------------------------------------------------------
    # Capture-mode selection
    # ------------------------------------------------------------------

    def select_capture_mode(
        self,
        mode: CaptureMode,
        mechanism_ready: bool,
    ) -> None:
        """
        Select gripper or net capture using the mission planner result.

        The planner decision is treated as an internal autonomy result,
        not an external command.
        """

        if self.state != MissionState.CAPTURE_MODE_SELECTION:
            return

        if not mechanism_ready:
            self._abort(
                AbortReason.MECHANISM_HEALTH_CRITICAL,
                {"detail": "selected_capture_mechanism_not_ready"},
            )
            return

        self.capture_mode = mode

        if mode == CaptureMode.GRIPPER:
            self.transition(
                MissionState.GRIPPER_CAPTURE,
                "autonomous_capture_mode_selected_gripper",
            )

        elif mode == CaptureMode.NET:
            self.transition(
                MissionState.NET_CAPTURE,
                "autonomous_capture_mode_selected_net",
            )

        else:
            raise ValueError(f"Unsupported capture mode: {mode}")

    # ------------------------------------------------------------------
    # Capture execution
    # ------------------------------------------------------------------

    def check_gripper_capture(
        self,
        contact_confirmed: bool,
        grasp_force_valid: bool,
    ) -> None:
        """Verify mechanical contact for gripper capture."""

        if (
            self.state == MissionState.GRIPPER_CAPTURE
            and contact_confirmed
            and grasp_force_valid
        ):
            self.transition(
                MissionState.CAPTURE_VERIFICATION,
                "gripper_contact_and_force_confirmed",
            )

    def check_net_capture(
        self,
        net_deployed: bool,
        net_tension_valid: bool,
        target_contained: bool,
    ) -> None:
        """Verify controlled net deployment and target containment."""

        if (
            self.state == MissionState.NET_CAPTURE
            and net_deployed
            and net_tension_valid
            and target_contained
        ):
            self.transition(
                MissionState.CAPTURE_VERIFICATION,
                "net_deployed_tensioned_and_target_contained",
            )

    # ------------------------------------------------------------------
    # Capture verification and storage
    # ------------------------------------------------------------------

    def check_capture_verification(
        self,
        capture_confirmed: bool,
        target_secured: bool,
    ) -> None:
        """Proceed to transfer only after independent capture confirmation."""

        if (
            self.state == MissionState.CAPTURE_VERIFICATION
            and capture_confirmed
            and target_secured
        ):
            self.transition(
                MissionState.TRANSFER_TO_CANISTER,
                "capture_verified_and_target_secured",
            )

    def check_transfer_to_storage(
        self,
        transfer_complete: bool,
        canister_ready: bool,
    ) -> None:
        """Transfer the captured object into the storage interface."""

        if (
            self.state == MissionState.TRANSFER_TO_CANISTER
            and transfer_complete
            and canister_ready
        ):
            self.transition(
                MissionState.STORAGE_CONFIRMATION,
                "target_transferred_and_canister_ready",
            )

    def check_storage_confirmation(
        self,
        target_stored: bool,
        storage_system_healthy: bool,
    ) -> None:
        """Confirm storage before allowing the spacecraft to depart."""

        if (
            self.state == MissionState.STORAGE_CONFIRMATION
            and target_stored
            and storage_system_healthy
        ):
            self.transition(
                MissionState.RETURN_TO_ORBIT,
                "storage_confirmed_and_storage_system_healthy",
            )

    # ------------------------------------------------------------------
    # Mission completion
    # ------------------------------------------------------------------

    def check_return_to_orbit(
        self,
        safe_orbit_restored: bool,
        spacecraft_healthy: bool,
        mission_complete: bool,
    ) -> None:
        """
        Complete the mission or return to autonomous surveillance.

        If additional targets remain, the mission continues through
        surveillance. Otherwise it can enter COMPLETED.
        """

        if (
            self.state != MissionState.RETURN_TO_ORBIT
            or not safe_orbit_restored
            or not spacecraft_healthy
        ):
            return

        if mission_complete:
            self.transition(
                MissionState.COMPLETED,
                "safe_orbit_restored_and_mission_objective_complete",
            )
        else:
            self.transition(
                MissionState.SURVEILLANCE,
                "safe_orbit_restored_and_additional_targets_available",
            )

    # ------------------------------------------------------------------
    # Abort / FDIR
    # ------------------------------------------------------------------

    def trigger_collision_abort(
        self,
        threat_object_id: str,
        threat_level: str,
    ) -> None:
        """Abort when autonomous collision assessment reaches HIGH risk."""

        operational_states = {
            MissionState.TARGET_TRACKING,
            MissionState.TARGET_SELECTION,
            MissionState.PREDICTION,
            MissionState.CAPTURE_PLANNING,
            MissionState.REORIENTING,
            MissionState.APPROACHING,
            MissionState.CAPTURE_MODE_SELECTION,
            MissionState.GRIPPER_CAPTURE,
            MissionState.NET_CAPTURE,
        }

        if (
            self.state in operational_states
            and threat_level.upper() == "HIGH"
        ):
            self._abort(
                AbortReason.COLLISION_RISK,
                {
                    "threat_object_id": threat_object_id,
                    "threat_level": threat_level,
                },
            )

    def trigger_fault_abort(
        self,
        reason: AbortReason,
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        """Abort because an internal health/safety condition is violated."""

        operational_states = {
            MissionState.SURVEILLANCE,
            MissionState.TARGET_TRACKING,
            MissionState.TARGET_SELECTION,
            MissionState.PREDICTION,
            MissionState.CAPTURE_PLANNING,
            MissionState.REORIENTING,
            MissionState.APPROACHING,
            MissionState.CAPTURE_MODE_SELECTION,
            MissionState.GRIPPER_CAPTURE,
            MissionState.NET_CAPTURE,
            MissionState.CAPTURE_VERIFICATION,
            MissionState.TRANSFER_TO_CANISTER,
            MissionState.STORAGE_CONFIRMATION,
            MissionState.RETURN_TO_ORBIT,
        }

        if self.state in operational_states:
            self._abort(reason, detail or {})

    def _abort(
        self,
        reason: AbortReason,
        detail: dict[str, Any],
    ) -> None:
        """Record and execute an autonomous abort."""

        self.abort_log.append(
            AbortRecord(
                reason=reason,
                detail=detail,
            )
        )

        self.transition(
            MissionState.ABORT,
            trigger_reason=reason.value,
        )

    def replan(self) -> None:
        """
        Return to surveillance after an abort.

        The mission manager is expected to perform fresh target scoring
        rather than blindly resuming the interrupted operation.
        """

        if self.state == MissionState.ABORT:
            self.selected_target_id = None
            self.capture_mode = None

            self.transition(
                MissionState.SURVEILLANCE,
                "post_abort_replan",
            )

    # ------------------------------------------------------------------
    # Safety / resource monitoring
    # ------------------------------------------------------------------

    def force_idle_on_low_fuel(self, fuel_budget: Any) -> None:
        """
        Trigger an autonomous fuel-safety abort.

        The object supplied must expose:
            below_safety_threshold
            remaining_delta_v_km_s
        """

        if (
            getattr(fuel_budget, "below_safety_threshold", False)
            and self.state != MissionState.IDLE
        ):
            self.trigger_fault_abort(
                AbortReason.FUEL_BELOW_SAFETY_THRESHOLD,
                {
                    "remaining_delta_v_km_s": getattr(
                        fuel_budget,
                        "remaining_delta_v_km_s",
                        None,
                    )
                },
            )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Return a dashboard/telemetry-friendly mission-state snapshot."""

        return {
            "state": self.state.name,
            "selected_target_id": self.selected_target_id,
            "capture_mode": (
                self.capture_mode.value
                if self.capture_mode is not None
                else None
            ),
            "transition_count": len(self.history),
            "abort_count": len(self.abort_log),
            "last_transition": (
                {
                    "from": self.history[-1].from_state.name,
                    "to": self.history[-1].to_state.name,
                    "trigger": self.history[-1].trigger,
                }
                if self.history
                else None
            ),
            "last_abort": (
                {
                    "reason": self.abort_log[-1].reason.value,
                    "detail": self.abort_log[-1].detail,
                }
                if self.abort_log
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Standalone engineering smoke test
# ---------------------------------------------------------------------------

def _nominal_smoke_test() -> None:
    """
    Execute one complete nominal mission path.

    This is intentionally deterministic and is suitable as a basic
    regression/smoke test while the larger simulation is being upgraded.
    """

    sm = MissionStateMachine()

    sm.check_idle_to_surveillance(
        spacecraft_healthy=True,
        sensors_ready=True,
    )

    sm.check_surveillance_to_tracking(
        target_detected=True,
        track_quality_ok=True,
    )

    sm.check_tracking_to_selection(
        target_locked=True,
        catalog_solution_available=True,
    )

    sm.check_selection_to_prediction(
        target_id="D001",
        target_score_valid=True,
    )

    sm.check_prediction_to_planning(
        trajectory_valid=True,
        uncertainty_within_limit=True,
    )

    sm.check_planning_to_reorientation(
        guidance_solution_valid=True,
        attitude_solution_valid=True,
    )

    sm.check_reorientation_to_approach(
        attitude_aligned=True,
        relative_velocity_within_limit=True,
    )

    sm.check_approach_to_capture_mode_selection(
        relative_distance_km=0.02,
        capture_window_km=0.05,
        relative_velocity_mps=0.02,
        maximum_capture_velocity_mps=0.10,
    )

    sm.select_capture_mode(
        mode=CaptureMode.NET,
        mechanism_ready=True,
    )

    sm.check_net_capture(
        net_deployed=True,
        net_tension_valid=True,
        target_contained=True,
    )

    sm.check_capture_verification(
        capture_confirmed=True,
        target_secured=True,
    )

    sm.check_transfer_to_storage(
        transfer_complete=True,
        canister_ready=True,
    )

    sm.check_storage_confirmation(
        target_stored=True,
        storage_system_healthy=True,
    )

    sm.check_return_to_orbit(
        safe_orbit_restored=True,
        spacecraft_healthy=True,
        mission_complete=True,
    )

    assert sm.state == MissionState.COMPLETED

    print("NOMINAL MISSION TEST: PASS")
    print("Final state:", sm.state.name)
    print("Transitions:", len(sm.history))
    print("Snapshot:", sm.snapshot())


def _abort_smoke_test() -> None:
    """Verify autonomous collision abort and replan."""

    sm = MissionStateMachine()

    sm.check_idle_to_surveillance(True, True)
    sm.check_surveillance_to_tracking(True, True)
    sm.check_tracking_to_selection(True, True)
    sm.check_selection_to_prediction("D999", True)
    sm.check_prediction_to_planning(True, True)

    sm.trigger_collision_abort(
        threat_object_id="D777",
        threat_level="HIGH",
    )

    assert sm.state == MissionState.ABORT
    assert len(sm.abort_log) == 1
    assert sm.abort_log[0].reason == AbortReason.COLLISION_RISK

    sm.replan()

    assert sm.state == MissionState.SURVEILLANCE

    print("COLLISION ABORT TEST: PASS")
    print("Abort reason:", sm.abort_log[0].reason.value)
    print("Replan state:", sm.state.name)


if __name__ == "__main__":
    _nominal_smoke_test()
    print()
    _abort_smoke_test()
