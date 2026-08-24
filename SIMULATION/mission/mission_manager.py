"""
mission_manager.py
Target selection/scoring, fuel-aware scoring (Challenge 4), collision
threat-list monitoring (Challenge 8), and storage-full gating (Challenge 7).

This is the orchestration layer: it doesn't do orbital math or Kalman
filtering itself, it calls into detection/, orbit/, physics/, satellite/,
and drives mission/state_machine.py.
"""

import sys, os
import numpy as np

# sensing_sim/ is still a sibling under SIMULATION/ (unchanged)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "sensing_sim"))
# PHYSICS/ is now a top-level repo folder, three levels up from here
# (SIMULATION/mission/mission_manager.py -> repo_root/PHYSICS)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "PHYSICS"))
from feature_extraction import bucket_threat_level  # noqa: E402
from mission_states import AbortReason  # noqa: E402


class MissionManager:
    """
    Parameters
    ----------
    fuel_budget : physics.propulsion.FuelBudget
    storage_drum : satellite.storage_drum.StorageDrum
    state_machine : mission.state_machine.MissionStateMachine
    safety_radius_km : float          used for the collision threat list (Challenge 8)
    fuel_weight : float               how heavily to penalize fuel-expensive targets
    """

    def __init__(self, fuel_budget, storage_drum, state_machine,
                 safety_radius_km=1.0, fuel_weight=0.4):
        self.fuel_budget = fuel_budget
        self.storage_drum = storage_drum
        self.state_machine = state_machine
        self.safety_radius_km = safety_radius_km
        self.fuel_weight = fuel_weight
        self.locked_target_id = None
        self.last_selection_blocked_by_capacity = False

    # --- Challenge 4: fuel-aware target scoring ------------------------

    def score_target(self, candidate, n_mean_motion=None):
        """
        candidate : dict with keys:
            id, relative_distance_km, relative_velocity_km_s,
            collision_confidence, size_m, mass_kg

        Higher score = more attractive target. Distance and fuel cost are
        penalized; larger/heavier debris (more removal value) is rewarded.
        """
        est_dv = self.fuel_budget.estimate_delta_v(
            candidate["relative_distance_km"], candidate["relative_velocity_km_s"],
            n_mean_motion=n_mean_motion
        )
        if not self.fuel_budget.can_afford(est_dv):
            return {"id": candidate["id"], "score": -np.inf, "est_delta_v_km_s": est_dv,
                    "reason": "insufficient_fuel"}

        target_mass = candidate.get("mass_kg", 1.0)
        if self.storage_drum.total_stored_mass_kg + target_mass > self.storage_drum.capacity_kg:
            return {"id": candidate["id"], "score": -np.inf, "est_delta_v_km_s": est_dv,
                    "reason": "would_exceed_storage_capacity"}

        value_term = candidate.get("mass_kg", 1.0) * 0.1 + candidate.get("size_m", 0.1)
        distance_penalty = candidate["relative_distance_km"] * 0.05
        fuel_penalty = est_dv * self.fuel_weight
        risk_bonus = candidate.get("collision_confidence", 0.0) * 0.5  # prioritize removing riskier debris

        score = value_term - distance_penalty - fuel_penalty + risk_bonus
        return {"id": candidate["id"], "score": score, "est_delta_v_km_s": est_dv}

    def select_target(self, candidates, n_mean_motion=None):
        """Score every candidate, return the best-scoring one (or None if
        storage is full or nothing is affordable). Also sets
        self.last_selection_blocked_by_capacity so callers can tell
        'temporarily nothing affordable' apart from 'storage can never
        fit anything remaining, mission is effectively done'."""
        self.last_selection_blocked_by_capacity = False

        if self.storage_drum.storage_full:
            self.last_selection_blocked_by_capacity = True
            return None

        scored_raw = [self.score_target(c, n_mean_motion=n_mean_motion) for c in candidates]
        scored = [s for s in scored_raw if s["score"] > -np.inf]
        if not scored:
            # nothing viable this cycle -- figure out why. If EVERY
            # candidate failed specifically because it wouldn't fit
            # (not because of fuel), nothing remaining will ever be
            # capturable until the drum is emptied, so this isn't a
            # transient "try again next cycle" state.
            if scored_raw and all(s.get("reason") == "would_exceed_storage_capacity" for s in scored_raw):
                self.last_selection_blocked_by_capacity = True
            return None

        best = max(scored, key=lambda s: s["score"])
        self.locked_target_id = best["id"]
        return best

    # --- Challenge 8: collision threat list -----------------------------

    def build_threat_list(self, all_tracked_objects):
        """Excludes the currently locked target. Each object needs
        relative_distance_km and collision_confidence (from
        detection.feature_extraction.estimate_collision_confidence)."""
        return [obj for obj in all_tracked_objects if obj["id"] != self.locked_target_id]

    def check_collision_threats(self, all_tracked_objects):
        """
        Run every cycle. Buckets each threat-list object's collision
        confidence into LOW/MED/HIGH, and triggers an ABORT via the state
        machine if anything is inside safety_radius_km AND HIGH threat.
        """
        threat_list = self.build_threat_list(all_tracked_objects)
        results = []
        for obj in threat_list:
            level = bucket_threat_level(obj["collision_confidence"])
            in_safety_radius = obj["relative_distance_km"] <= self.safety_radius_km
            results.append({"id": obj["id"], "threat_level": level,
                             "in_safety_radius": in_safety_radius})
            if in_safety_radius and level == "HIGH":
                self.state_machine.trigger_collision_abort(obj["id"], level)
        return results

    def on_abort(self, candidates, n_mean_motion=None):
        """Mission Manager should NOT blindly resume the old target after
        an Abort — re-run scoring across the whole field."""
        self.locked_target_id = None
        return self.select_target(candidates, n_mean_motion=n_mean_motion)


if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "PHYSICS"))
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "SATELLITE"))
    from propulsion import FuelBudget
    from storage_drum import StorageDrum
    from state_machine import MissionStateMachine, MissionState

    fuel = FuelBudget(total_delta_v_km_s=0.05, safety_margin_km_s=0.01)
    drum = StorageDrum(capacity_kg=100.0)
    sm = MissionStateMachine()
    sm.transition(MissionState.TRACKING, "startup")

    mgr = MissionManager(fuel, drum, sm, safety_radius_km=1.0)

    candidates = [
        {"id": "D001", "relative_distance_km": 3.0, "relative_velocity_km_s": [0.001, 0.001, 0],
         "collision_confidence": 0.2, "mass_kg": 5, "size_m": 0.3},
        {"id": "D002", "relative_distance_km": 8.0, "relative_velocity_km_s": [0.002, 0.001, 0],
         "collision_confidence": 0.1, "mass_kg": 40, "size_m": 0.9},
    ]

    best = mgr.select_target(candidates)
    print("selected target:", best)

    # Challenge 8: inject fake high-risk object mid-mission
    tracked = candidates + [{"id": "D999", "relative_distance_km": 0.3, "collision_confidence": 0.9}]
    threats = mgr.check_collision_threats(tracked)
    print("threat check:", threats)
    print("state after threat check:", sm.state)

    # Challenge 8: re-score after abort instead of resuming blindly
    sm.replan()
    new_best = mgr.on_abort(candidates)
    print("re-selected target after abort:", new_best)
