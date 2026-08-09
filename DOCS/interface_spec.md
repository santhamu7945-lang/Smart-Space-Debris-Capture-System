# Interface Specification

## Autonomy Constraint (Challenge 5 — Communication Delay)

No external command input is accepted during RENDEZVOUS → CAPTURE states
(`TRACKING`, `APPROACHING`, `CAPTURING`). All transitions in this range are
triggered internally, based on telemetry:

- distance thresholds (`relative_distance_km` vs `capture_threshold_km`)
- velocity thresholds (closing rate from `orbit.orbit_propagator`)
- sensor confirmations (`sensor_confidence_ok` from Kalman filter covariance)
- fuel state (`FuelBudget.below_safety_threshold`)
- mechanism health (`mechanism_health` from `robotic_arm.py` / `capture_net.py`)

`mission.state_machine.MissionStateMachine.transition()` is the only method
that changes mission state, and its signature deliberately has no
"ground_command" or equivalent external-input parameter anywhere in this
codebase. This is proven, not just asserted: running the state machine with
all external inputs disconnected (see `state_machine.py __main__` block)
completes a full mission cycle — TRACKING → APPROACHING → CAPTURING →
ABORT → TRACKING replan — using only internally-derived triggers.

## Limitations and Real-World Considerations (Challenge 9 — Space Environment Effects)

This prototype does not simulate radiation, thermal, or micrometeoroid
physics — that is out of scope for a software/GNC demonstrator and adds no
engineering value at this fidelity level. For flight qualification, the
following would be required:

- **Radiation-hardened components** for the sensor suite, flight computer,
  and reaction wheel electronics, given cumulative dose in the target orbit.
- **Thermal control systems** (radiators, MLI, heaters) to keep the
  Kalman-filtered sensor suite and propulsion valves within operating range
  through eclipse cycles.
- **Micrometeoroid/orbital-debris (MMOD) shielding** (e.g., Whipple
  shielding) on pressurized or thin-walled components, particularly the
  storage drum housing captured debris.
- Standard aerospace practice such as component derating and redundancy
  (dual-string avionics, redundant reaction wheels) would apply throughout,
  at a conceptual level, without further physics modeling in this project.

## Legal and Operational Constraints (Challenge 10)

This project is framed explicitly as a **technology demonstrator**, not an
operational debris-removal system, which sidesteps the need to address real
authorization/licensing processes while still showing awareness of the
governing framework:

- **UN Outer Space Treaty, Article VIII** — ownership and jurisdiction over
  a space object persists with the launching state regardless of its debris
  status; a demonstrator does not "capture" debris in the legal sense of
  taking possession, and any real mission would require coordination with
  the object's registered owner.
- **IADC Space Debris Mitigation Guidelines** — inform general design
  practice (e.g., not creating new debris during capture attempts, safe
  disposal planning) referenced here at a conceptual level only.

## Data Contract — `debris_state.json`

See `data/debris_state.json` for the schema. Key fields:

| Field | Source module | Notes |
|---|---|---|
| `position_km`, `velocity_km_s` | `detection/sensor_fusion.py` | Kalman-fused, NOT raw sensor values |
| `position_uncertainty_km` | `detection/sensor_fusion.py` | trace of KF position covariance |
| `tumbling_rate_rad_s`, `rotation_axis` | `detection/feature_extraction.py` | estimated, not ground truth |
| `collision_confidence`, `threat_level` | `detection/feature_extraction.py`, `mission/mission_manager.py` | bucketed LOW/MED/HIGH |
| `remaining_delta_v_km_s` | `physics/propulsion.py` | read by `state_machine.py` safety trigger |
| `storage_full` | `satellite/storage_drum.py` | read by `mission_manager.py` target gating |
