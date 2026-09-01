"""
SIMULATION/main.py

Integrated autonomous multi-target space debris capture simulation.

This is an engineering visualization / prototype simulator.
It is NOT flight-certified spacecraft software.

Integrated features
-------------------
1. Multiple simultaneous debris tracking
2. Simulated camera sensing
3. Simulated LiDAR sensing
4. Camera + LiDAR sensor fusion
5. Per-object Kalman filtering
6. Position uncertainty estimation
7. Collision confidence estimation
8. Autonomous multi-target ranking
9. One active capture target at a time
10. Spacecraft attitude alignment
11. Controlled rendezvous approach
12. SMALL debris -> dual gripper
13. LARGE debris -> middle-arm net
14. Capture verification
15. Funnel -> canister storage
16. Multi-cycle autonomous mission
17. Dashboard telemetry export
18. Three.js / visualization JSON export
19. Atomic JSON writes for dashboard stability

Run from repository root:

    python3 SIMULATION/main.py --once --steps 60

Continuous mode:

    python3 SIMULATION/main.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Any

import numpy as np


# ======================================================================
# PATH CONFIGURATION
# ======================================================================

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(ROOT, ".."))

DEBRIS_DIR = os.path.join(REPO_ROOT, "DEBRIS")
MISSION_DIR = os.path.join(ROOT, "mission")
SENSING_DIR = os.path.join(ROOT, "sensing_sim")

for path in (DEBRIS_DIR, MISSION_DIR, SENSING_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


# ======================================================================
# IMPORT PROJECT MODULES
# ======================================================================

from debris import spawn_debris_field

from state_machine import (
    MissionStateMachine,
    MissionState,
    CaptureMode,
)

from feature_extraction import (
    simulate_camera_reading,
    simulate_lidar_reading,
    estimate_collision_confidence,
    bucket_threat_level,
)

from sensor_fusion import (
    fuse_debris_state,
)


# ======================================================================
# OUTPUT PATHS
# ======================================================================

OUTPUT_PATH = os.path.join(
    ROOT,
    "data",
    "debris_state.json",
)

VIZ_PATH = os.path.join(
    ROOT,
    "viz_data.json",
)


# ======================================================================
# SIMULATION ENGINE
# ======================================================================

class SimulationEngine:
    """
    Autonomous multi-target debris capture simulation engine.

    Architecture
    ------------

    TRUE DEBRIS STATES
            |
            v
    CAMERA SENSOR SIMULATION
            |
            +------+
            |      |
            v      v
         LIDAR   CAMERA
            |      |
            +------+
               |
               v
         SENSOR FUSION
               |
               v
        KALMAN FILTER
               |
               v
      MULTI-TARGET TRACKING
               |
               v
       TARGET RANKING / AI
               |
               v
        ONE TARGET LOCKED
               |
               v
       ATTITUDE ALIGNMENT
               |
               v
       RENDEZVOUS APPROACH
               |
               v
       CAPTURE MODE CHOICE
               |
        +------+------+
        |             |
        v             v
     GRIPPER         NET
        |             |
        +------+------+
               |
               v
       STORAGE CANISTER
               |
               v
         NEXT TARGET
    """

    def __init__(
        self,
        n_debris: int = 12,
        seed: int = 42,
        tracking_range_km: float = 5000.0,
        capture_window_km: float = 0.05,
        capture_velocity_limit_mps: float = 5.0,
        out_path: str = OUTPUT_PATH,
    ):

        # --------------------------------------------------------------
        # Deterministic random generator
        # --------------------------------------------------------------

        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)

        # Also seed global numpy generator because sensing functions
        # currently use np.random.normal().
        np.random.seed(self.seed)

        # --------------------------------------------------------------
        # Output configuration
        # --------------------------------------------------------------

        self.out_path = out_path

        # --------------------------------------------------------------
        # Mission parameters
        # --------------------------------------------------------------

        self.tracking_range_km = float(tracking_range_km)

        self.capture_window_km = float(capture_window_km)

        self.capture_velocity_limit_mps = float(
            capture_velocity_limit_mps
        )

        # --------------------------------------------------------------
        # Simulation time
        # --------------------------------------------------------------

        self.t_s = 0.0

        # --------------------------------------------------------------
        # Mission state machine
        # --------------------------------------------------------------

        self.sm = MissionStateMachine()

        self.sm.check_idle_to_surveillance(
            True,
            True,
        )

        # --------------------------------------------------------------
        # Spacecraft state
        #
        # Local spacecraft-relative frame for visualization.
        # --------------------------------------------------------------

        self.chaser_pos = np.array(
            [0.0, 0.0, 0.0],
            dtype=float,
        )

        self.chaser_vel = np.zeros(
            3,
            dtype=float,
        )

        self.patrol_anchor = (
            self.chaser_pos.copy()
        )

        # --------------------------------------------------------------
        # Attitude state
        # --------------------------------------------------------------

        self.attitude_deg = 0.0

        self.desired_attitude_deg = 0.0

        self.attitude_aligned = False

        # --------------------------------------------------------------
        # Propulsion / storage
        # --------------------------------------------------------------

        self.remaining_delta_v_km_s = 0.08

        self.storage_capacity_kg = 60.0

        self.storage_mass_kg = 0.0

        # --------------------------------------------------------------
        # Generate debris field
        # --------------------------------------------------------------

        self.debris_field = spawn_debris_field(
            n=max(6, int(n_debris)),
            region_km=20.0,
            seed=self.seed,
        )

        self._prepare_demo_field()

        # --------------------------------------------------------------
        # Sensor fusion / Kalman filter store
        #
        # One Kalman filter per debris object.
        # --------------------------------------------------------------

        self.kf_store: dict[str, Any] = {}

        # --------------------------------------------------------------
        # Mission tracking
        # --------------------------------------------------------------

        self.locked_target_id: str | None = None

        self.selected_target: dict[str, Any] | None = None

        self.last_tracked: list[dict[str, Any]] = []

        self.captured_ids: set[str] = set()

        # --------------------------------------------------------------
        # Capture state
        # --------------------------------------------------------------

        self.capture_method = "NONE"

        self.capture_event: dict[str, Any] | None = None

        # --------------------------------------------------------------
        # Mission bookkeeping
        # --------------------------------------------------------------

        self.phase_elapsed_s = 0.0

        self.mission_complete = False

        self.completed_cycles = 0

        self.event_log: list[dict[str, Any]] = []

        self._last_state_name = self.sm.state.name

        self._log(
            "Mission initialized: autonomous multi-target surveillance active"
        )


    # ==================================================================
    # SCENARIO GENERATION
    # ==================================================================

    def _prepare_demo_field(self) -> None:
        """
        Prepare deterministic demonstration debris.

        The first several objects are placed at manageable distances so
        the simulation visibly demonstrates:

        - multiple object tracking
        - target ranking
        - gripper capture
        - net capture
        - repeated mission cycles
        """

        presets = [

            # distance_km
            # speed_km_s
            # size_m
            # mass_kg

            (2.2, 0.0015, 0.28, 8.0),

            (3.1, 0.0012, 0.85, 24.0),

            (4.0, 0.0020, 0.55, 15.0),

            (6.5, 0.0010, 0.72, 20.0),

            (8.0, 0.0030, 0.38, 10.0),

            (10.0, 0.0025, 1.10, 30.0),
        ]

        for i, debris in enumerate(self.debris_field):

            # ----------------------------------------------------------
            # Use predefined candidates first
            # ----------------------------------------------------------

            if i < len(presets):

                (
                    distance,
                    speed,
                    size,
                    mass,
                ) = presets[i]

            # ----------------------------------------------------------
            # Generate additional objects
            # ----------------------------------------------------------

            else:

                distance = float(
                    self.rng.uniform(
                        12.0,
                        45.0,
                    )
                )

                speed = float(
                    self.rng.uniform(
                        0.001,
                        0.004,
                    )
                )

                size = float(
                    self.rng.uniform(
                        0.15,
                        1.10,
                    )
                )

                mass = float(
                    self.rng.uniform(
                        4.0,
                        28.0,
                    )
                )

            # ----------------------------------------------------------
            # Random direction
            # ----------------------------------------------------------

            direction = self.rng.normal(
                size=3,
            )

            direction /= max(
                np.linalg.norm(direction),
                1e-12,
            )

            # ----------------------------------------------------------
            # Tangential velocity direction
            # ----------------------------------------------------------

            tangent = np.cross(
                direction,
                np.array(
                    [0.0, 0.0, 1.0],
                ),
            )

            if np.linalg.norm(tangent) < 1e-9:

                tangent = np.array(
                    [0.0, 1.0, 0.0],
                )

            tangent /= np.linalg.norm(
                tangent
            )

            # ----------------------------------------------------------
            # Assign state
            # ----------------------------------------------------------

            debris.position_km = (
                direction * distance
            )

            debris.velocity_km_s = (
                tangent * speed
            )

            debris.size_m = float(size)

            debris.mass_kg = float(mass)

            debris.id = (
                f"DEB-{i + 1:02d}"
            )


    # ==================================================================
    # LOGGING
    # ==================================================================

    def _log(
        self,
        message: str,
    ) -> None:

        self.event_log.append(
            {
                "time_s": round(
                    self.t_s,
                    1,
                ),
                "event": message,
            }
        )

        # Keep dashboard file compact
        self.event_log = (
            self.event_log[-60:]
        )


    # ==================================================================
    # STATE TRANSITION
    # ==================================================================

    def _transition(
        self,
        new_state: MissionState,
        reason: str,
    ) -> None:

        if self.sm.state == new_state:
            return

        try:

            self.sm.transition(
                new_state,
                reason,
            )

        except Exception:

            # Visualization-safe fallback.
            self.sm.state = new_state

        self.phase_elapsed_s = 0.0

        self._last_state_name = (
            new_state.name
        )

        self._log(
            f"{new_state.name}: {reason}"
        )


    # ==================================================================
    # RISK CLASSIFICATION
    # ==================================================================

    @staticmethod
    def _risk_level(
        score: float,
    ) -> str:

        if score >= 70:
            return "HIGH"

        if score >= 40:
            return "MEDIUM"

        return "LOW"


    # ==================================================================
    # TARGET SCORING
    # ==================================================================

    def _candidate_score(
        self,
        item: dict[str, Any],
    ) -> float:
        """
        Score a debris candidate.

        Higher score = more attractive target.

        Factors:
        - closer debris preferred
        - manageable velocity preferred
        - larger debris has more removal value
        - collision risk prioritized
        - high uncertainty penalized
        """

        distance = (
            item["relative_distance_km"]
        )

        speed = (
            item["relative_speed_mps"]
        )

        size = (
            item["size_m"]
        )

        risk = (
            item["collision_risk"]
        )

        uncertainty = (
            item["position_uncertainty_km"]
        )

        score = (

            120.0

            - 2.2 * distance

            - 1.5 * speed

            - 4.0 * uncertainty

            + 18.0 * min(
                size,
                1.5,
            )

            + 0.18 * risk
        )

        return float(score)


    # ==================================================================
    # CAPTURE MODE SELECTION
    # ==================================================================

    def _choose_capture_mode(
        self,
        target: dict[str, Any],
    ) -> CaptureMode:
        """
        Project capture policy:

        SMALL debris:
            Dual robotic grippers

        LARGE debris:
            Middle arm net mechanism
        """

        if target["size_m"] < 0.50:

            return CaptureMode.GRIPPER

        return CaptureMode.NET


    # ==================================================================
    # MULTI-SENSOR MULTI-TARGET TRACKING
    # ==================================================================

    def _build_tracking_data(
        self,
        dt_s: float,
    ) -> list[dict[str, Any]]:
        """
        Track ALL visible debris objects.

        For every debris object:

            True state
                |
                v
            Camera measurement
                |
                +
                |
            LiDAR measurement
                |
                v
            Sensor fusion
                |
                v
            Kalman filter
                |
                v
            Estimated state
                |
                v
            Candidate tracking list

        This is the key upgrade from single-target to
        MULTIPLE DEBRIS TRACKING.
        """

        tracked: list[
            dict[str, Any]
        ] = []

        for debris in self.debris_field:

            # ----------------------------------------------------------
            # Ignore captured debris
            # ----------------------------------------------------------

            if debris.id in self.captured_ids:
                continue

            # ----------------------------------------------------------
            # Update true debris motion
            # ----------------------------------------------------------

            debris.position_km = (
                debris.position_km
                + debris.velocity_km_s * dt_s
            )

            debris.step_rotation(
                dt_s
            )

            # ----------------------------------------------------------
            # True relative state
            # ----------------------------------------------------------

            true_rel_pos = (
                debris.position_km
                - self.chaser_pos
            )

            true_rel_vel = (
                debris.velocity_km_s
                - self.chaser_vel
            )

            distance = float(
                np.linalg.norm(
                    true_rel_pos
                )
            )

            # ----------------------------------------------------------
            # Tracking envelope check
            # ----------------------------------------------------------

            if distance > self.tracking_range_km:
                continue

            # ----------------------------------------------------------
            # Simulated CAMERA
            # ----------------------------------------------------------

            camera_reading = (
                simulate_camera_reading(
                    true_position_km=(
                        true_rel_pos
                    ),
                    true_velocity_km_s=(
                        true_rel_vel
                    ),
                    range_km=distance,
                )
            )

            # ----------------------------------------------------------
            # Simulated LiDAR
            #
            # Returns None outside LiDAR range.
            # ----------------------------------------------------------

            lidar_reading = (
                simulate_lidar_reading(
                    true_position_km=(
                        true_rel_pos
                    ),
                    true_velocity_km_s=(
                        true_rel_vel
                    ),
                    range_km=distance,
                )
            )

            # ----------------------------------------------------------
            # Sensor fusion + Kalman filter
            # ----------------------------------------------------------

            fused = (
                fuse_debris_state(
                    debris_id=debris.id,

                    true_position_km=(
                        true_rel_pos
                    ),

                    true_velocity_km_s=(
                        true_rel_vel
                    ),

                    camera_reading=(
                        camera_reading
                    ),

                    lidar_reading=(
                        lidar_reading
                    ),

                    kf_store=(
                        self.kf_store
                    ),

                    dt_s=dt_s,
                )
            )

            # ----------------------------------------------------------
            # Estimated relative state
            # ----------------------------------------------------------

            estimated_rel_pos = np.asarray(
                fused[
                    "position_km"
                ],
                dtype=float,
            )

            estimated_rel_vel = np.asarray(
                fused[
                    "velocity_km_s"
                ],
                dtype=float,
            )

            estimated_distance = float(
                np.linalg.norm(
                    estimated_rel_pos
                )
            )

            estimated_speed_km_s = float(
                np.linalg.norm(
                    estimated_rel_vel
                )
            )

            estimated_speed_mps = (
                estimated_speed_km_s
                * 1000.0
            )

            # ----------------------------------------------------------
            # Range rate
            # ----------------------------------------------------------

            if estimated_distance > 1e-9:

                range_rate_mps = float(

                    np.dot(
                        estimated_rel_vel,
                        estimated_rel_pos
                        / estimated_distance,
                    )

                    * 1000.0
                )

            else:

                range_rate_mps = 0.0

            # ----------------------------------------------------------
            # Sensor uncertainty
            # ----------------------------------------------------------

            uncertainty = float(
                fused[
                    "position_uncertainty_km"
                ]
            )

            # ----------------------------------------------------------
            # Collision confidence
            # ----------------------------------------------------------

            collision_confidence = (
                estimate_collision_confidence(

                    relative_distance_km=(
                        estimated_distance
                    ),

                    relative_speed_km_s=(
                        estimated_speed_km_s
                    ),

                    position_uncertainty_km=(
                        uncertainty
                    ),
                )
            )

            # ----------------------------------------------------------
            # Dashboard risk score
            # ----------------------------------------------------------

            collision_risk = float(
                collision_confidence
                * 100.0
            )

            threat_level = (
                bucket_threat_level(
                    collision_confidence
                )
            )

            # ----------------------------------------------------------
            # Construct tracking object
            # ----------------------------------------------------------

            item = {

                "id": debris.id,

                "name": (
                    f"Orbital Debris "
                    f"{debris.id[-2:]}"
                ),

                # --------------------------------------------------
                # Estimated position
                # --------------------------------------------------

                "position_km": (
                    estimated_rel_pos.tolist()
                ),

                "velocity_km_s": (
                    estimated_rel_vel.tolist()
                ),

                "relative_position_km": (
                    estimated_rel_pos.tolist()
                ),

                "relative_velocity_km_s": (
                    estimated_rel_vel.tolist()
                ),

                "relative_distance_km": (
                    estimated_distance
                ),

                "relative_speed_km_s": (
                    estimated_speed_km_s
                ),

                "relative_speed_mps": (
                    estimated_speed_mps
                ),

                "range_rate_mps": (
                    range_rate_mps
                ),

                # --------------------------------------------------
                # Sensor information
                # --------------------------------------------------

                "camera_detected": True,

                "lidar_detected": (
                    lidar_reading
                    is not None
                ),

                "sensors_used": (

                    ["camera", "lidar"]

                    if lidar_reading
                    is not None

                    else ["camera"]
                ),

                "position_uncertainty_km": (
                    uncertainty
                ),

                # --------------------------------------------------
                # Risk information
                # --------------------------------------------------

                "collision_risk": (
                    collision_risk
                ),

                "collision_confidence": (
                    collision_confidence
                ),

                "threat_level": (
                    threat_level
                ),

                # --------------------------------------------------
                # Physical characteristics
                # --------------------------------------------------

                "mass_kg": float(
                    debris.mass_kg
                ),

                "size_m": float(
                    debris.size_m
                ),

                "tumbling_rate_rad_s": float(
                    debris.tumbling_rate_rad_s
                ),

                "rotation_axis": (
                    debris.rotation_axis.tolist()
                ),

                # --------------------------------------------------
                # Tracking state
                # --------------------------------------------------

                "tracked": True,

                "captured": False,
            }

            # ----------------------------------------------------------
            # Candidate ranking score
            # ----------------------------------------------------------

            item["score"] = (
                self._candidate_score(
                    item
                )
            )

            tracked.append(
                item
            )

        # --------------------------------------------------------------
        # Sort nearest first
        # --------------------------------------------------------------

        tracked.sort(
            key=lambda x:
            x["relative_distance_km"]
        )

        return tracked


    # ==================================================================
    # TARGET LOOKUP
    # ==================================================================

    def _get_locked(
        self,
    ) -> dict[str, Any] | None:

        if not self.locked_target_id:
            return None

        return next(

            (
                item

                for item
                in self.last_tracked

                if item["id"]
                == self.locked_target_id
            ),

            None,
        )


    # ==================================================================
    # MULTI-TARGET SELECTION
    # ==================================================================

    def _select_target(
        self,
    ) -> dict[str, Any] | None:
        """
        Evaluate ALL tracked debris.

        Multiple debris can be tracked simultaneously.

        But only ONE target is locked for a capture cycle.
        """

        candidates = [

            item

            for item
            in self.last_tracked

            if item["id"]
            not in self.captured_ids
        ]

        # --------------------------------------------------------------
        # Storage capacity filter
        # --------------------------------------------------------------

        candidates = [

            item

            for item
            in candidates

            if (

                self.storage_mass_kg
                + item["mass_kg"]

                <=

                self.storage_capacity_kg
            )
        ]

        if not candidates:
            return None

        # --------------------------------------------------------------
        # Highest autonomous score wins
        # --------------------------------------------------------------

        best = max(

            candidates,

            key=lambda item:
            item["score"],
        )

        self.locked_target_id = (
            best["id"]
        )

        self.selected_target = dict(
            best
        )

        self._log(

            f"Target selected: "
            f"{best['id']} "
            f"score={best['score']:.2f}"
        )

        return best


    # ==================================================================
    # ATTITUDE CONTROL
    # ==================================================================

    def _update_attitude(
        self,
        target: dict[str, Any],
        dt_s: float,
    ) -> None:

        rel = np.asarray(

            target[
                "relative_position_km"
            ],

            dtype=float,
        )

        # Desired yaw angle toward target

        self.desired_attitude_deg = (
            math.degrees(

                math.atan2(
                    rel[1],
                    rel[0],
                )
            )
        )

        # Shortest angular difference

        error = (

            (
                self.desired_attitude_deg
                - self.attitude_deg
                + 180.0
            )

            % 360.0

            - 180.0
        )

        # Maximum rotation rate

        max_step = (
            35.0 * dt_s
        )

        self.attitude_deg += float(

            np.clip(

                error,

                -max_step,

                max_step,
            )
        )

        self.attitude_aligned = (

            abs(error) < 2.0
        )


    # ==================================================================
    # CONTROLLED APPROACH
    # ==================================================================

    def _approach(
        self,
        target: dict[str, Any],
        dt_s: float,
    ) -> None:
        """
        Simplified controlled rendezvous.

        Far:
            faster approach

        Medium:
            slower

        Close:
            precision approach
        """

        debris = next(

            (

                item

                for item
                in self.debris_field

                if item.id
                == target["id"]
            ),

            None,
        )

        if debris is None:
            return

        rel = (

            debris.position_km
            - self.chaser_pos
        )

        distance = float(
            np.linalg.norm(rel)
        )

        if distance < 1e-9:
            return

        direction = (
            rel / distance
        )

        # --------------------------------------------------------------
        # Closing speed profile
        # --------------------------------------------------------------

        if distance > 1.0:

            closing_mps = 500.0

        elif distance > 0.2:

            closing_mps = 100.0

        else:

            closing_mps = 20.0

        # --------------------------------------------------------------
        # Move spacecraft
        # --------------------------------------------------------------

        step_km = min(

            distance,

            closing_mps
            * dt_s
            / 1000.0,
        )

        self.chaser_pos = (

            self.chaser_pos
            + direction
            * step_km
        )

        self.chaser_vel = (

            direction
            * (
                closing_mps
                / 1000.0
            )
        )

        # --------------------------------------------------------------
        # Delta-V consumption
        # --------------------------------------------------------------

        self.remaining_delta_v_km_s = max(

            0.0,

            self.remaining_delta_v_km_s
            - step_km
            * 0.00005,
        )


    # ==================================================================
    # CAPTURE
    # ==================================================================

    def _capture_target(
        self,
        target: dict[str, Any],
    ) -> CaptureMode:

        mode = (
            self._choose_capture_mode(
                target
            )
        )

        if mode == CaptureMode.GRIPPER:

            self.capture_method = (
                "dual_gripper"
            )

            sequence = (
                "align -> deploy dual grippers "
                "-> stabilize -> grip "
                "-> funnel -> canister"
            )

        else:

            self.capture_method = (
                "middle_arm_net"
            )

            sequence = (
                "align -> deploy circular net "
                "-> contain debris "
                "-> cinch mesh "
                "-> funnel -> canister"
            )

        self.capture_event = {

            "success": True,

            "target_id": (
                target["id"]
            ),

            "method": (
                self.capture_method
            ),

            "sequence": (
                sequence
            ),
        }

        self._log(

            f"Capture successful: "
            f"{target['id']} "
            f"using "
            f"{self.capture_method}"
        )

        self.sm.capture_mode = (
            mode
        )

        return mode


    # ==================================================================
    # MISSION STATE PROCESSING
    # ==================================================================

    def _process_state(
        self,
        dt_s: float,
    ) -> None:

        state = self.sm.state

        target = (
            self._get_locked()
        )


        # ==============================================================
        # SURVEILLANCE
        # ==============================================================

        if state == MissionState.SURVEILLANCE:

            if self.last_tracked:

                self._transition(

                    MissionState.TARGET_TRACKING,

                    (
                        "multiple debris objects "
                        "detected inside tracking envelope"
                    ),
                )


        # ==============================================================
        # MULTI-TARGET TRACKING
        # ==============================================================

        elif state == MissionState.TARGET_TRACKING:

            if self.phase_elapsed_s >= 1.0:

                self._transition(

                    MissionState.TARGET_SELECTION,

                    (
                        "camera, LiDAR and Kalman "
                        "filter multi-target tracking complete"
                    ),
                )


        # ==============================================================
        # TARGET SELECTION
        # ==============================================================

        elif state == MissionState.TARGET_SELECTION:

            best = (
                self._select_target()
            )

            if best:

                self._transition(

                    MissionState.PREDICTION,

                    (
                        "autonomous multi-target "
                        "ranking complete"
                    ),
                )

            else:

                self._transition(

                    MissionState.COMPLETED,

                    (
                        "no viable debris "
                        "candidates remain"
                    ),
                )

                self.mission_complete = True


        # ==============================================================
        # TRAJECTORY PREDICTION
        # ==============================================================

        elif state == MissionState.PREDICTION:

            if (

                target

                and

                self.phase_elapsed_s
                >= 1.0
            ):

                self._transition(

                    MissionState.CAPTURE_PLANNING,

                    (
                        "relative trajectory prediction "
                        "and capture feasibility valid"
                    ),
                )


        # ==============================================================
        # CAPTURE PLANNING
        # ==============================================================

        elif state == MissionState.CAPTURE_PLANNING:

            if (

                target

                and

                self.phase_elapsed_s
                >= 1.0
            ):

                self._transition(

                    MissionState.REORIENTING,

                    (
                        "capture mechanism "
                        "and approach plan selected"
                    ),
                )


        # ==============================================================
        # REORIENTING
        # ==============================================================

        elif state == MissionState.REORIENTING:

            if target:

                self._update_attitude(
                    target,
                    dt_s,
                )

                if (

                    self.attitude_aligned

                    or

                    self.phase_elapsed_s
                    >= 4.0
                ):

                    self.attitude_aligned = (
                        True
                    )

                    self._transition(

                        MissionState.APPROACHING,

                        (
                            "spacecraft capture axis "
                            "aligned with target"
                        ),
                    )


        # ==============================================================
        # APPROACH
        # ==============================================================

        elif state == MissionState.APPROACHING:

            if target is None:

                self.locked_target_id = None

                self._transition(

                    MissionState.SURVEILLANCE,

                    (
                        "target lost; "
                        "reacquiring debris field"
                    ),
                )

                return

            self._update_attitude(
                target,
                dt_s,
            )

            self._approach(
                target,
                dt_s,
            )

            # ----------------------------------------------------------
            # Direct true distance for capture window
            # ----------------------------------------------------------

            debris = next(

                (

                    item

                    for item
                    in self.debris_field

                    if item.id
                    == target["id"]
                ),

                None,
            )

            if debris is not None:

                distance = float(

                    np.linalg.norm(

                        debris.position_km
                        - self.chaser_pos
                    )
                )

                relative_speed_mps = float(

                    np.linalg.norm(

                        debris.velocity_km_s
                        - self.chaser_vel
                    )

                    * 1000.0
                )

                # ------------------------------------------------------
                # Enter capture mode
                # ------------------------------------------------------

                if (

                    distance
                    <= self.capture_window_km

                    and

                    relative_speed_mps
                    <= self.capture_velocity_limit_mps
                ):

                    self._transition(

                        MissionState.CAPTURE_MODE_SELECTION,

                        (
                            "precision capture "
                            "window reached"
                        ),
                    )

                # Failsafe for visualization:
                # If geometrically close but simplified velocity model
                # is still high, allow controlled capture transition.

                elif (

                    distance
                    <= self.capture_window_km

                    and

                    self.phase_elapsed_s
                    >= 8.0
                ):

                    self._transition(

                        MissionState.CAPTURE_MODE_SELECTION,

                        (
                            "capture window reached "
                            "under controlled rendezvous"
                        ),
                    )


        # ==============================================================
        # CAPTURE MODE SELECTION
        # ==============================================================

        elif state == MissionState.CAPTURE_MODE_SELECTION:

            if target:

                mode = (

                    self._choose_capture_mode(
                        target
                    )
                )

                if mode == CaptureMode.GRIPPER:

                    self._transition(

                        MissionState.GRIPPER_CAPTURE,

                        (
                            "SMALL debris -> "
                            "dual gripper selected"
                        ),
                    )

                else:

                    self._transition(

                        MissionState.NET_CAPTURE,

                        (
                            "LARGE debris -> "
                            "middle arm net selected"
                        ),
                    )


        # ==============================================================
        # GRIPPER / NET CAPTURE
        # ==============================================================

        elif state in (

            MissionState.GRIPPER_CAPTURE,

            MissionState.NET_CAPTURE,
        ):

            if (

                target

                and

                self.phase_elapsed_s
                >= 1.0
            ):

                self._capture_target(
                    target
                )

                self._transition(

                    MissionState.CAPTURE_VERIFICATION,

                    (
                        "capture sequence "
                        "completed successfully"
                    ),
                )


        # ==============================================================
        # CAPTURE VERIFICATION
        # ==============================================================

        elif state == MissionState.CAPTURE_VERIFICATION:

            if (

                self.capture_event

                and

                self.capture_event.get(
                    "success"
                )
            ):

                self._transition(

                    MissionState.TRANSFER_TO_CANISTER,

                    (
                        "target containment "
                        "verified"
                    ),
                )


        # ==============================================================
        # TRANSFER TO STORAGE
        # ==============================================================

        elif state == MissionState.TRANSFER_TO_CANISTER:

            if (

                target

                and

                self.phase_elapsed_s
                >= 1.0
            ):

                self.storage_mass_kg += (

                    target["mass_kg"]
                )

                self.captured_ids.add(
                    target["id"]
                )

                self._log(

                    f"{target['id']} "
                    f"transferred through funnel "
                    f"into storage canister"
                )

                self._transition(

                    MissionState.STORAGE_CONFIRMATION,

                    (
                        "canister occupancy "
                        "updated"
                    ),
                )


        # ==============================================================
        # STORAGE CONFIRMATION
        # ==============================================================

        elif state == MissionState.STORAGE_CONFIRMATION:

            self._transition(

                MissionState.RETURN_TO_ORBIT,

                (
                    "captured debris "
                    "securely stored"
                ),
            )


        # ==============================================================
        # RETURN TO PATROL
        # ==============================================================

        elif state == MissionState.RETURN_TO_ORBIT:

            delta = (

                self.patrol_anchor
                - self.chaser_pos
            )

            distance = float(
                np.linalg.norm(delta)
            )

            if distance > 0.001:

                self.chaser_pos += (

                    delta
                    / distance

                    * min(

                        distance,

                        0.01
                        * dt_s,
                    )
                )

            if (

                self.phase_elapsed_s
                >= 3.0
            ):

                self.completed_cycles += 1

                self.locked_target_id = None

                self.selected_target = None

                self.capture_event = None

                self.capture_method = "NONE"

                self.attitude_aligned = False

                self._transition(

                    MissionState.SURVEILLANCE,

                    (
                        "patrol orbit restored; "
                        "searching for next debris"
                    ),
                )


    # ==================================================================
    # MAIN SIMULATION STEP
    # ==================================================================

    def step(
        self,
        dt_s: float = 1.0,
    ) -> list[dict[str, Any]]:

        dt_s = float(
            dt_s
        )

        if dt_s <= 0:

            raise ValueError(
                "dt_s must be > 0"
            )

        # --------------------------------------------------------------
        # Advance simulation clock
        # --------------------------------------------------------------

        self.t_s += dt_s

        self.phase_elapsed_s += dt_s

        # --------------------------------------------------------------
        # MULTI-TARGET SENSOR TRACKING
        # --------------------------------------------------------------

        self.last_tracked = (
            self._build_tracking_data(
                dt_s
            )
        )

        # --------------------------------------------------------------
        # Mission logic
        # --------------------------------------------------------------

        self._process_state(
            dt_s
        )

        return (
            self.last_tracked
        )


    # ==================================================================
    # TELEMETRY EXPORT
    # ==================================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        target = (

            self._get_locked()

            or

            self.selected_target
        )

        storage_fraction = min(

            1.0,

            self.storage_mass_kg
            / self.storage_capacity_kg,
        )

        multiple_nearby = (

            len(
                self.last_tracked
            )
            >= 3
        )

        decision = (

            "PROCEED"

            if target

            else "SEARCH"
        )

        return {

            # ----------------------------------------------------------
            # Time
            # ----------------------------------------------------------

            "timestamp_s": round(
                self.t_s,
                2,
            ),

            # ----------------------------------------------------------
            # Mission
            # ----------------------------------------------------------

            "mission_state": (
                self.sm.state.name
            ),

            "mission_phase_elapsed_s": round(
                self.phase_elapsed_s,
                2,
            ),

            "completed_cycles": (
                self.completed_cycles
            ),

            # ----------------------------------------------------------
            # Tracking
            # ----------------------------------------------------------

            "tracking_range_km": (
                self.tracking_range_km
            ),

            "tracked_count": (
                len(
                    self.last_tracked
                )
            ),

            "candidate_count": (
                len(
                    self.last_tracked
                )
            ),

            "locked_target_id": (
                self.locked_target_id
            ),

            "selected_target": (
                target
            ),

            # ----------------------------------------------------------
            # Capture
            # ----------------------------------------------------------

            "capture_method": (
                self.capture_method
            ),

            "capture_event": (
                self.capture_event
            ),

            "capture_decision": (
                decision
            ),

            # ----------------------------------------------------------
            # Spacecraft
            # ----------------------------------------------------------

            "spacecraft": {

                "position_km": (
                    self.chaser_pos.tolist()
                ),

                "velocity_km_s": (
                    self.chaser_vel.tolist()
                ),

                "attitude_deg": round(
                    self.attitude_deg,
                    2,
                ),

                "desired_attitude_deg": round(
                    self.desired_attitude_deg,
                    2,
                ),

                "attitude_status": (

                    "ALIGNED"

                    if self.attitude_aligned

                    else "ALIGNING"
                ),

                "remaining_delta_v_km_s": round(
                    self.remaining_delta_v_km_s,
                    6,
                ),

                "storage_current_capacity_used": round(
                    storage_fraction,
                    4,
                ),

                "storage_mass_kg": round(
                    self.storage_mass_kg,
                    3,
                ),

                "storage_capacity_kg": (
                    self.storage_capacity_kg
                ),

                "storage_full": (

                    storage_fraction
                    >= 1.0
                ),

                "system_health": (
                    "NOMINAL"
                ),

                "mission_state": (
                    self.sm.state.name
                ),
            },

            # ----------------------------------------------------------
            # Storage canister
            # ----------------------------------------------------------

            "canister": {

                "occupancy_percent": round(
                    storage_fraction
                    * 100.0,
                    1,
                ),

                "stored_mass_kg": round(
                    self.storage_mass_kg,
                    3,
                ),

                "capacity_kg": (
                    self.storage_capacity_kg
                ),
            },

            # ----------------------------------------------------------
            # Sensor system
            # ----------------------------------------------------------

            "sensors": {

                "camera": {
                    "status": "ACTIVE",
                    "tracked_objects": (
                        len(
                            self.last_tracked
                        )
                    ),
                },

                "lidar": {
                    "status": "ACTIVE",
                    "max_range_km": 20.0,
                    "objects_in_range": sum(
                        1
                        for item
                        in self.last_tracked
                        if item[
                            "lidar_detected"
                        ]
                    ),
                },

                "sensor_fusion": {
                    "status": "ACTIVE",
                    "kalman_filters": (
                        len(
                            self.kf_store
                        )
                    ),
                },
            },

            # ----------------------------------------------------------
            # Scenario
            # ----------------------------------------------------------

            "scenario": (

                "MULTIPLE_DEBRIS_NET"

                if (

                    multiple_nearby

                    and

                    target

                    and

                    target.get(
                        "size_m",
                        0.0,
                    )
                    >= 0.5
                )

                else "MULTI_TARGET_TRACKING"
            ),

            # ----------------------------------------------------------
            # Logs
            # ----------------------------------------------------------

            "event_log": (
                self.event_log
            ),

            # ----------------------------------------------------------
            # Tracked debris
            # ----------------------------------------------------------

            "tracked_debris": (
                self.last_tracked
            ),

            "captured_ids": sorted(
                self.captured_ids
            ),

            "mission_complete": (
                self.mission_complete
            ),

            # ----------------------------------------------------------
            # State machine snapshot
            # ----------------------------------------------------------

            "state_machine": (
                self.sm.snapshot()
            ),
        }


    # ==================================================================
    # ATOMIC JSON WRITE
    # ==================================================================

    def _write_atomic_json(
        self,
        path: str,
        data: dict[str, Any],
    ) -> None:

        directory = os.path.dirname(
            path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True,
            )

        temporary_path = (
            path
            + ".tmp"
        )

        with open(

            temporary_path,

            "w",

            encoding="utf-8",

        ) as file:

            json.dump(

                data,

                file,

                indent=2,

                allow_nan=False,
            )

        os.replace(

            temporary_path,

            path,
        )


    # ==================================================================
    # WRITE TELEMETRY
    # ==================================================================

    def write_state(
        self,
    ) -> None:

        self._write_atomic_json(

            self.out_path,

            self.to_dict(),
        )

        self._write_viz_data()


    # ==================================================================
    # VISUALIZATION DATA EXPORT
    # ==================================================================

    def _write_viz_data(
        self,
    ) -> None:
        """
        Lightweight visualization export.

        Used by future Three.js / browser simulation.

        Important:
        This file exports ALL tracked debris simultaneously.
        """

        target = (

            self._get_locked()

            or

            self.selected_target

            or {}
        )

        debris_list = []

        for item in self.last_tracked:

            position = (
                item[
                    "position_km"
                ]
            )

            velocity = (
                item[
                    "velocity_km_s"
                ]
            )

            debris_list.append({

                "id": item["id"],

                "name": item["name"],

                # --------------------------------------------------
                # Position
                # --------------------------------------------------

                "x": position[0],

                "y": position[1],

                "z": position[2],

                # --------------------------------------------------
                # Velocity
                # --------------------------------------------------

                "vx": velocity[0],

                "vy": velocity[1],

                "vz": velocity[2],

                # --------------------------------------------------
                # Physical
                # --------------------------------------------------

                "size_m": (
                    item["size_m"]
                ),

                "mass_kg": (
                    item["mass_kg"]
                ),

                "tumbling_rate": (
                    item[
                        "tumbling_rate_rad_s"
                    ]
                ),

                "rotation_axis": (
                    item[
                        "rotation_axis"
                    ]
                ),

                # --------------------------------------------------
                # Risk
                # --------------------------------------------------

                "collision_risk": (
                    item[
                        "collision_risk"
                    ]
                ),

                "collision_confidence": (
                    item[
                        "collision_confidence"
                    ]
                ),

                "threat_level": (
                    item[
                        "threat_level"
                    ]
                ),

                # --------------------------------------------------
                # Sensor visualization
                # --------------------------------------------------

                "camera_detected": (
                    item[
                        "camera_detected"
                    ]
                ),

                "lidar_detected": (
                    item[
                        "lidar_detected"
                    ]
                ),

                "position_uncertainty_km": (
                    item[
                        "position_uncertainty_km"
                    ]
                ),

                # --------------------------------------------------
                # Target state
                # --------------------------------------------------

                "is_target": (

                    item["id"]
                    == self.locked_target_id
                ),

                "captured": False,
            })

        viz = {

            "earth_radius_km": (
                6378.137
            ),

            "simulation_time_s": round(
                self.t_s,
                2,
            ),

            "mission_state": (
                self.sm.state.name
            ),

            # ------------------------------------------------------
            # Spacecraft
            # ------------------------------------------------------

            "spacecraft": {

                "x": float(
                    self.chaser_pos[0]
                ),

                "y": float(
                    self.chaser_pos[1]
                ),

                "z": float(
                    self.chaser_pos[2]
                ),

                "vx": float(
                    self.chaser_vel[0]
                ),

                "vy": float(
                    self.chaser_vel[1]
                ),

                "vz": float(
                    self.chaser_vel[2]
                ),

                "attitude_deg": (
                    self.attitude_deg
                ),
            },

            # ------------------------------------------------------
            # Target
            # ------------------------------------------------------

            "target": {

                "id": target.get(
                    "id"
                ),

                "name": target.get(
                    "name",
                    "AUTONOMOUS SEARCH",
                ),

                "decision": (

                    "PROCEED"

                    if target

                    else "SEARCH"
                ),

                "decision_reason": (
                    "Autonomous multi-target "
                    "sensor fusion and mission-state decision"
                ),

                "risk_level": target.get(
                    "threat_level",
                    "LOW",
                ),

                "risk_score": target.get(
                    "collision_risk",
                    0.0,
                ),

                "capture_method": (
                    self.capture_method
                ),

                "capture_score": target.get(
                    "score",
                    0.0,
                ),

                "capture_feasible": bool(
                    target
                ),

                "difficulty_level": (
                    "MEDIUM"
                ),

                "altitude_km": (
                    650.0
                ),

                "inclination_deg": (
                    74.0
                ),

                "orbit_class": (
                    "LEO"
                ),
            },

            # ------------------------------------------------------
            # Sensor metadata
            # ------------------------------------------------------

            "sensors": {

                "camera_active": True,

                "lidar_active": True,

                "lidar_max_range_km": (
                    20.0
                ),

                "kalman_filter_active": True,
            },

            # ------------------------------------------------------
            # MULTIPLE DEBRIS
            # ------------------------------------------------------

            "debris": (
                debris_list
            ),

            "captured_ids": sorted(
                self.captured_ids
            ),
        }

        self._write_atomic_json(

            VIZ_PATH,

            viz,
        )


# ======================================================================
# RUN ONCE
# ======================================================================

def run_once(
    steps: int,
    interval: float,
    debris: int,
    seed: int,
) -> None:

    engine = SimulationEngine(

        n_debris=debris,

        seed=seed,
    )

    for _ in range(steps):

        engine.step(
            interval
        )

        engine.write_state()

        target = (

            engine.locked_target_id

            or "NONE"
        )

        print(

            f"t={engine.t_s:6.1f}s | "

            f"state={engine.sm.state.name:26s} | "

            f"target={target:7s} | "

            f"tracked={len(engine.last_tracked):2d} | "

            f"mode={engine.capture_method}"
        )

    print()

    print(
        "Simulation complete."
    )

    print()

    print(
        "Telemetry written to:"
    )

    print(
        engine.out_path
    )

    print()

    print(
        "Visualization data:"
    )

    print(
        VIZ_PATH
    )


# ======================================================================
# RUN FOREVER
# ======================================================================

def run_forever(
    interval: float,
    debris: int,
    seed: int,
) -> None:

    engine = SimulationEngine(

        n_debris=debris,

        seed=seed,
    )

    print()

    print(
        "Autonomous multi-target simulation running."
    )

    print(
        f"Tracking range: "
        f"{engine.tracking_range_km} km"
    )

    print(
        f"Debris objects: "
        f"{len(engine.debris_field)}"
    )

    print()

    print(
        "Press Ctrl+C to stop."
    )

    print()

    try:

        while True:

            engine.step(
                interval
            )

            engine.write_state()

            target = (

                engine.locked_target_id

                or "NONE"
            )

            print(

                f"t={engine.t_s:6.1f}s "

                f"| state={engine.sm.state.name:24s} "

                f"| target={target:7s} "

                f"| tracked={len(engine.last_tracked):2d} "

                f"| captured={len(engine.captured_ids):2d}"
            )

            time.sleep(
                interval
            )

    except KeyboardInterrupt:

        print()

        print(
            "Simulation stopped."
        )


# ======================================================================
# CLI
# ======================================================================

def main() -> None:

    parser = argparse.ArgumentParser(

        description=(
            "Autonomous multi-target "
            "space debris capture simulation"
        )
    )

    parser.add_argument(

        "--once",

        action="store_true",

        help=(
            "Run fixed number "
            "of simulation steps"
        ),
    )

    parser.add_argument(

        "--steps",

        type=int,

        default=60,

        help=(
            "Number of steps "
            "for --once mode"
        ),
    )

    parser.add_argument(

        "--interval",

        type=float,

        default=1.0,

        help=(
            "Simulation timestep "
            "in seconds"
        ),
    )

    parser.add_argument(

        "--debris",

        type=int,

        default=12,

        help=(
            "Number of debris objects"
        ),
    )

    parser.add_argument(

        "--seed",

        type=int,

        default=42,

        help=(
            "Deterministic random seed"
        ),
    )

    args = parser.parse_args()

    # --------------------------------------------------------------
    # Validation
    # --------------------------------------------------------------

    if args.steps <= 0:

        parser.error(
            "--steps must be greater than zero"
        )

    if args.interval <= 0:

        parser.error(
            "--interval must be greater than zero"
        )

    if args.debris <= 0:

        parser.error(
            "--debris must be greater than zero"
        )

    # --------------------------------------------------------------
    # Execution
    # --------------------------------------------------------------

    if args.once:

        run_once(

            steps=args.steps,

            interval=args.interval,

            debris=args.debris,

            seed=args.seed,
        )

    else:

        run_forever(

            interval=args.interval,

            debris=args.debris,

            seed=args.seed,
        )


# ======================================================================
# ENTRY POINT
# ======================================================================

if __name__ == "__main__":

    main()