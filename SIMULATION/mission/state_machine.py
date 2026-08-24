"""
state_machine.py
Core mission state machine. All transitions between TRACKING, APPROACHING,
and CAPTURING are triggered ONLY by internal telemetry conditions —
distance thresholds, velocity thresholds, sensor confirmations, fuel
state, mechanism health. No function in this range accepts a "ground
command" parameter — this is a hard design constraint (Challenge 5).

Also implements the Abort/Replan trigger for fuel (Challenge 4), collision
avoidance (Challenge 8), and internal-fault FDIR (Challenge 13).
"""

from mission_states import MissionState, ALLOWED_TRANSITIONS, AbortReason


class InvalidTransitionError(Exception):
    pass


class MissionStateMachine:
    def __init__(self):
        self.state = MissionState.IDLE
        self.history = []          # list of (from_state, to_state, reason)
        self.abort_log = []        # list of dicts: {reason, detail, timestamp}

    def transition(self, new_state: MissionState, trigger_reason: str):
        """
        The ONLY way to change state. Deliberately takes no external
        "ground_command" argument anywhere in this signature or class —
        every call site in this codebase must derive `new_state` from
        internal telemetry (see interface_spec.md).
        """
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidTransitionError(
                f"Cannot transition {self.state} -> {new_state}"
            )
        self.history.append((self.state, new_state, trigger_reason))
        self.state = new_state
        return self.state

    # --- Internal telemetry-driven transition checks -----------------

    def check_tracking_to_approaching(self, target_locked: bool, sensor_confidence_ok: bool):
        if target_locked and sensor_confidence_ok and self.state == MissionState.TRACKING:
            self.transition(MissionState.APPROACHING, "target_locked_and_sensor_confirmed")

    def check_approaching_to_capturing(self, relative_distance_km: float, capture_threshold_km: float):
        if (self.state == MissionState.APPROACHING
                and relative_distance_km <= capture_threshold_km):
            self.transition(MissionState.CAPTURING, "within_capture_threshold")

    def check_capturing_to_completed(self, capture_success: bool):
        if self.state == MissionState.CAPTURING and capture_success:
            self.transition(MissionState.COMPLETED, "capture_confirmed")

    # --- Abort triggers (Challenge 8: external, Challenge 13: internal) ---

    def trigger_collision_abort(self, threat_object_id: str, threat_level: str):
        """Challenge 8: external collision-avoidance abort."""
        if threat_level == "HIGH" and self.state in (MissionState.APPROACHING, MissionState.CAPTURING, MissionState.TRACKING):
            self._abort(AbortReason.COLLISION_RISK, detail={"threat_object_id": threat_object_id})

    def trigger_fault_abort(self, reason: AbortReason, detail=None):
        """Challenge 13: internal-fault abort (sensor dropout, mechanism
        health critical, fuel below safety threshold), logged separately
        from external collision aborts."""
        if self.state in (MissionState.TRACKING, MissionState.APPROACHING, MissionState.CAPTURING):
            self._abort(reason, detail=detail or {})

    def _abort(self, reason: AbortReason, detail: dict):
        self.abort_log.append({"reason": reason.value, "detail": detail})
        self.transition(MissionState.ABORT, trigger_reason=reason.value)

    def replan(self):
        """After Abort, Mission Manager should re-run target scoring, not
        blindly resume — this just clears back to TRACKING/IDLE for a
        fresh scoring pass."""
        if self.state == MissionState.ABORT:
            self.transition(MissionState.TRACKING, "post_abort_replan")

    def force_idle_on_low_fuel(self, fuel_budget):
        """Fuel safety trigger (Challenge 4): if remaining fuel drops below
        safety threshold, force Completed/Idle instead of accepting new
        targets."""
        if fuel_budget.below_safety_threshold and self.state != MissionState.IDLE:
            self.trigger_fault_abort(AbortReason.FUEL_BELOW_SAFETY_THRESHOLD,
                                      detail={"remaining_delta_v_km_s": fuel_budget.remaining_delta_v_km_s})
            self.transition(MissionState.IDLE, "fuel_safety_forced_idle")


if __name__ == "__main__":
    sm = MissionStateMachine()
    sm.transition(MissionState.TRACKING, "startup_scan_complete")
    sm.check_tracking_to_approaching(target_locked=True, sensor_confidence_ok=True)
    sm.check_approaching_to_capturing(relative_distance_km=0.02, capture_threshold_km=0.05)
    print("state after nominal progression:", sm.state)

    # Challenge 8 test: inject high-risk object mid-mission
    sm.trigger_collision_abort("D999", "HIGH")
    print("state after collision abort:", sm.state, "| abort_log:", sm.abort_log)

    sm.replan()
    print("state after replan:", sm.state)

    print("\nfull-autonomy test (no external inputs, Challenge 5):")
    for f, t, r in sm.history:
        print(f"  {f.name} -> {t.name}  (trigger: {r})")
