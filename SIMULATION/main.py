"""
main.py
Continuously-running simulation engine.

Spawns a debris field, then loops forever: detection (simulated sensors) ->
sensor fusion -> orbit propagation -> mission scoring -> state machine ->
capture -> mass property update -> writes debris_state.json. The file is
rewritten every cycle, so anything reading it (your dashboard, Member 3's
prediction module) always sees fresh data without you re-running anything.

Usage:
    python3 main.py                    # runs forever, updates every 1s (Ctrl+C to stop)
    python3 main.py --interval 2       # update every 2 seconds instead
    python3 main.py --once             # single cycle then exit (old behavior, for testing)
    python3 main.py --steps 15 --once  # run 15 internal physics steps, write once, exit
"""

import sys, os, json, time, argparse
import numpy as np

ROOT = os.path.dirname(__file__)
REPO_ROOT = os.path.join(ROOT, "..")   # SIMULATION/ -> repo root

# top-level subsystem folders (repo restructure: each lives at repo root,
# not nested inside SIMULATION/)
for sub in ["DEBRIS", "GNC", "PHYSICS", "SATELLITE"]:
    sys.path.append(os.path.join(REPO_ROOT, sub))
# these two stay nested under SIMULATION/ itself
for sub in ["sensing_sim", "mission"]:
    sys.path.append(os.path.join(ROOT, sub))

from debris import spawn_debris_field                       # noqa: E402
from feature_extraction import (                             # noqa: E402
    simulate_camera_reading, simulate_lidar_reading,
    estimate_collision_confidence, bucket_threat_level,
)
from sensor_fusion import fuse_debris_state                  # noqa: E402
from propulsion import FuelBudget                            # noqa: E402
from power_budget import PowerBudget                         # noqa: E402
from gnc import SpacecraftAttitude                            # noqa: E402
from solar_panel import SolarPanel                            # noqa: E402
from storage_drum import StorageDrum                          # noqa: E402
from capture_net import CaptureNet                            # noqa: E402
from state_machine import MissionStateMachine                 # noqa: E402
from mission_states import MissionState                       # noqa: E402
from mission_manager import MissionManager                    # noqa: E402

OUTPUT_PATH = os.path.join(ROOT, "data", "debris_state.json")


class SimulationEngine:
    """
    Holds all persistent simulation state across cycles. Call .step(dt_s)
    once per cycle, then .write_state() to publish the latest
    debris_state.json. Designed to be driven either by run_forever() below
    or embedded in a dashboard/notebook that calls .step() on its own timer.
    """

    def __init__(self, n_debris=6, seed=42, capture_threshold_km=0.05,
                 out_path=OUTPUT_PATH):
        self.rng = np.random.default_rng(seed)
        self.out_path = out_path
        self.capture_threshold_km = capture_threshold_km
        self.t_s = 0.0

        self.chaser_pos = np.array([7000.0, 0.0, 0.0])
        self.chaser_vel = np.array([0.0, 7.5, 0.0])

        self.debris_field = spawn_debris_field(n=n_debris, region_km=8.0, seed=seed)
        # give each object a realistic km-scale range and a small relative
        # perturbation on top of the chaser's orbital velocity, instead of
        # an independent near-zero velocity (which would imply an absurd
        # multi-km/s relative closing speed)
        for d in self.debris_field:
            d.position_km += self.chaser_pos
            d.velocity_km_s = self.chaser_vel + d.velocity_km_s * 0.02

        self.fuel = FuelBudget(total_delta_v_km_s=0.08, safety_margin_km_s=0.01)
        self.solar = SolarPanel()
        self.power = PowerBudget(self.solar)
        self.attitude = SpacecraftAttitude()
        self.drum = StorageDrum(capacity_kg=60.0, spacecraft_dry_mass_kg=500.0)
        self.net = CaptureNet()
        self.sm = MissionStateMachine()
        self.mgr = MissionManager(self.fuel, self.drum, self.sm, safety_radius_km=0.5)
        self.kf_store = {}

        self.sm.transition(MissionState.TRACKING, "startup_scan_complete")
        self.last_tracked = []
        self.mission_complete = False

    def step(self, dt_s=1.0):
        """Advance the whole system by one cycle."""
        self.t_s += dt_s
        tracked = []

        # chaser's own bulk orbital motion, so only the small relative
        # offset to each debris object matters for closing distance
        self.chaser_pos = self.chaser_pos + self.chaser_vel * dt_s

        for d in self.debris_field:
            d.step(dt_s)
            rel = d.position_km - self.chaser_pos
            range_km = float(np.linalg.norm(rel))
            rel_speed = float(np.linalg.norm(d.velocity_km_s - self.chaser_vel))

            cam = simulate_camera_reading(d.position_km, d.velocity_km_s, range_km)
            lidar = simulate_lidar_reading(d.position_km, d.velocity_km_s, range_km)
            fused = fuse_debris_state(d.id, d.position_km, d.velocity_km_s,
                                       cam, lidar, self.kf_store, dt_s=dt_s)

            conf = estimate_collision_confidence(range_km, rel_speed, fused["position_uncertainty_km"])
            tracked.append({
                "id": d.id,
                "position_km": fused["position_km"],
                "velocity_km_s": fused["velocity_km_s"],
                "position_uncertainty_km": fused["position_uncertainty_km"],
                "relative_distance_km": range_km,
                "relative_velocity_km_s": (d.velocity_km_s - self.chaser_vel).tolist(),
                "collision_confidence": conf,
                "threat_level": bucket_threat_level(conf),
                "mass_kg": d.mass_kg,
                "size_m": d.size_m,
                "tumbling_rate_rad_s": d.tumbling_rate_rad_s,
                "rotation_axis": d.rotation_axis.tolist(),
            })

        self.mgr.check_collision_threats(tracked)

        if self.sm.state == MissionState.ABORT:
            self.sm.replan()

        if self.sm.state == MissionState.TRACKING and not self.mission_complete:
            best = self.mgr.select_target(tracked)
            if best and best["score"] > -np.inf:
                self.sm.check_tracking_to_approaching(target_locked=True, sensor_confidence_ok=True)
            elif self.mgr.last_selection_blocked_by_capacity:
                # nothing left will EVER fit in the remaining storage
                # capacity -- this isn't "try again next cycle", the
                # mission is effectively done. Park it instead of
                # silently re-checking the same failing candidates forever.
                self.mission_complete = True
                self.sm.transition(MissionState.IDLE, "storage_capacity_exhausted_mission_complete")

        elif self.sm.state == MissionState.APPROACHING and self.mgr.locked_target_id:
            target = next(x for x in tracked if x["id"] == self.mgr.locked_target_id)
            # proportional guidance toward the target (stand-in for firing
            # the CW-computed burn from gnc.compute_approach_delta_v)
            direction = np.array(target["position_km"]) - self.chaser_pos
            self.chaser_pos = self.chaser_pos + direction * 0.4
            self.sm.check_approaching_to_capturing(target["relative_distance_km"],
                                                    capture_threshold_km=self.capture_threshold_km)

        elif self.sm.state == MissionState.CAPTURING and self.mgr.locked_target_id:
            target = next(x for x in tracked if x["id"] == self.mgr.locked_target_id)
            result = self.net.attempt_capture(
                np.array(target["position_km"]) - self.chaser_pos, target["tumbling_rate_rad_s"],
                self.drum, target["mass_kg"], gnc=self.attitude, rng=self.rng,
            )
            self.sm.check_capturing_to_completed(result["success"])
            if self.sm.state == MissionState.COMPLETED:
                est_dv = self.mgr.score_target(target)["est_delta_v_km_s"]
                self.fuel.spend(self.mgr.locked_target_id, est_dv, timestamp=self.t_s)
                self.sm.transition(MissionState.IDLE, "post_capture_idle")
                self.mgr.locked_target_id = None
            else:
                # capture attempt failed (net miss, or target no longer
                # fits storage) -- don't retry forever, abort and let
                # mission_manager re-score onto a different target
                self._capture_attempts = getattr(self, "_capture_attempts", 0) + 1
                if self._capture_attempts >= 3:
                    self.sm.trigger_fault_abort(
                        __import__("mission_states").AbortReason.MECHANISM_HEALTH_CRITICAL,
                        detail={"reason": "repeated_capture_failure", "target_id": self.mgr.locked_target_id},
                    )
                    self._capture_attempts = 0

        self.sm.force_idle_on_low_fuel(self.fuel)
        if self.sm.state == MissionState.IDLE and not self.mission_complete:
            self.sm.transition(MissionState.TRACKING, "resume_scanning")

        self.last_tracked = tracked
        return tracked

    def to_dict(self):
        return {
            "timestamp_s": self.t_s,
            "spacecraft": {
                "total_mass_kg": self.drum.total_mass_kg,
                "center_of_mass_m": self.drum.center_of_mass_m.tolist(),
                "remaining_delta_v_km_s": self.fuel.remaining_delta_v_km_s,
                "storage_current_capacity_used": self.drum.current_capacity_used,
                "storage_full": self.drum.storage_full,
            },
            "tracked_debris": self.last_tracked,
            "mission_state": self.sm.state.name,
            "locked_target_id": self.mgr.locked_target_id,
            "abort_log": self.sm.abort_log,
        }

    def write_state(self):
        """Atomic-ish write: write to a temp file then rename, so a reader
        (dashboard, prediction module) polling this path never sees a
        half-written file."""
        tmp_path = self.out_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(tmp_path, self.out_path)


def run_forever(interval_s=1.0, n_debris=6, seed=42):
    """
    Runs the simulation indefinitely, writing debris_state.json every
    `interval_s` seconds until interrupted with Ctrl+C. This is what you
    leave running in a terminal (or as a background/launchd service) so
    the dashboard and prediction module always have fresh data without
    you manually re-running anything.
    """
    engine = SimulationEngine(n_debris=n_debris, seed=seed)
    print(f"Simulation running. Writing {engine.out_path} every {interval_s}s. Ctrl+C to stop.")
    announced_complete = False
    try:
        while True:
            engine.step(dt_s=interval_s)
            engine.write_state()
            if engine.mission_complete and not announced_complete:
                announced_complete = True
                print(f"\n*** MISSION COMPLETE at t={engine.t_s:.0f}s — storage full "
                      f"({engine.drum.current_capacity_used:.2f}), no remaining debris "
                      f"can fit. Fuel remaining: {engine.fuel.remaining_delta_v_km_s:.4f} km/s. ***\n"
                      f"(still writing debris_state.json every {interval_s}s so the "
                      f"dashboard keeps showing the final state)\n")
            print(f"t={engine.t_s:.0f}s  state={engine.sm.state.name}  "
                  f"locked={engine.mgr.locked_target_id}  "
                  f"fuel_left={engine.fuel.remaining_delta_v_km_s:.4f}  "
                  f"storage={engine.drum.current_capacity_used:.2f}"
                  + ("  [MISSION COMPLETE]" if engine.mission_complete else ""))
            time.sleep(interval_s)
    except KeyboardInterrupt:
        print("\nStopped.")


def run_once(n_steps=15, dt_s=1.0, n_debris=6, seed=42):
    """Single-shot mode for quick local testing (old behavior)."""
    engine = SimulationEngine(n_debris=n_debris, seed=seed)
    for _ in range(n_steps):
        engine.step(dt_s=dt_s)
        print(f"t={engine.t_s:.0f}s  state={engine.sm.state.name}  "
              f"locked={engine.mgr.locked_target_id}  "
              f"fuel_left={engine.fuel.remaining_delta_v_km_s:.4f}  "
              f"storage={engine.drum.current_capacity_used:.2f}")
    engine.write_state()
    print(f"\nWrote final state to {engine.out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run a fixed number of steps then exit")
    parser.add_argument("--steps", type=int, default=15, help="steps to run in --once mode")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between updates in continuous mode")
    parser.add_argument("--debris", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.once:
        run_once(n_steps=args.steps, n_debris=args.debris, seed=args.seed)
    else:
        run_forever(interval_s=args.interval, n_debris=args.debris, seed=args.seed)
