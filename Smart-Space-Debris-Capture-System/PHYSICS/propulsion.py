"""
propulsion.py
Tracks spacecraft fuel/delta-v budget and estimates delta-v cost for
candidate targets. Consumed by mission_manager.py's scoring function and
state_machine.py's abort/replan trigger.

Solves Challenge 4 (fuel limitations).
"""

import numpy as np


class FuelBudget:
    """
    Tracks remaining delta-v capacity in km/s (consistent single unit,
    chosen here over propellant mass for direct compatibility with the
    CW-equation delta-v outputs from orbit/relative_motion.py).

    Parameters
    ----------
    total_delta_v_km_s : float     total available delta-v at mission start
    safety_margin_km_s : float     reserve that should never be spent
                                    (read by state_machine.py's abort trigger)
    """

    def __init__(self, total_delta_v_km_s=1.5, safety_margin_km_s=0.1):
        self.total_delta_v_km_s = total_delta_v_km_s
        self.remaining_delta_v_km_s = total_delta_v_km_s
        self.safety_margin_km_s = safety_margin_km_s
        self.spent_log = []  # list of dicts: {target_id, delta_v_km_s, timestamp}

    def estimate_delta_v(self, relative_distance_km, relative_velocity_km_s,
                          n_mean_motion=None, placeholder_gain=0.002):
        """
        Estimate delta-v required to reach a candidate target.

        If `n_mean_motion` is provided, delegate to the real CW-equation
        two-impulse solve (orbit.relative_motion.cw_targeting_delta_v).
        Otherwise fall back to a simple proportional placeholder:
            delta_v ~= placeholder_gain * distance_km + relative_speed_km_s
        which is deliberately crude and meant to be replaced once Phase
        3/4 CW output is wired in.
        """
        if n_mean_motion is not None:
            import sys, os
            # relative_motion.py now lives in top-level GNC/ (repo restructure)
            sys.path.append(os.path.join(os.path.dirname(__file__), "..", "GNC"))
            from relative_motion import cw_targeting_delta_v
            rel_speed = np.linalg.norm(relative_velocity_km_s)
            transfer_time_s = max(300.0, relative_distance_km / max(rel_speed, 1e-4))
            _, _, total_dv = cw_targeting_delta_v(
                [relative_distance_km, 0, 0], relative_velocity_km_s,
                n_mean_motion, transfer_time_s
            )
            return float(total_dv)

        rel_speed = float(np.linalg.norm(relative_velocity_km_s))
        return placeholder_gain * relative_distance_km + rel_speed

    def can_afford(self, delta_v_km_s) -> bool:
        return (self.remaining_delta_v_km_s - delta_v_km_s) >= self.safety_margin_km_s

    def spend(self, target_id, delta_v_km_s, timestamp=None):
        """Deduct actual delta-v spent after a completed mission."""
        if delta_v_km_s > self.remaining_delta_v_km_s:
            raise ValueError(
                f"Attempted to spend {delta_v_km_s:.4f} km/s but only "
                f"{self.remaining_delta_v_km_s:.4f} km/s remains."
            )
        self.remaining_delta_v_km_s -= delta_v_km_s
        self.spent_log.append({
            "target_id": target_id,
            "delta_v_km_s": delta_v_km_s,
            "timestamp": timestamp,
        })

    @property
    def below_safety_threshold(self) -> bool:
        """Read by state_machine.py to force Completed/Idle transition."""
        return self.remaining_delta_v_km_s <= self.safety_margin_km_s

    def to_dict(self):
        return {
            "total_delta_v_km_s": self.total_delta_v_km_s,
            "remaining_delta_v_km_s": self.remaining_delta_v_km_s,
            "safety_margin_km_s": self.safety_margin_km_s,
            "missions_completed": len(self.spent_log),
        }


if __name__ == "__main__":
    budget = FuelBudget(total_delta_v_km_s=0.05, safety_margin_km_s=0.01)

    targets = [
        {"id": "D001", "distance_km": 3.0, "rel_vel": [0.001, 0.002, 0.0]},
        {"id": "D002", "distance_km": 8.0, "rel_vel": [0.003, 0.001, 0.0]},
        {"id": "D003", "distance_km": 12.0, "rel_vel": [0.004, 0.002, 0.0]},
    ]

    for t in targets:
        dv = budget.estimate_delta_v(t["distance_km"], t["rel_vel"])
        afford = budget.can_afford(dv)
        print(f"{t['id']}: est_dv={dv:.4f} km/s  affordable={afford}")
        if afford:
            budget.spend(t["id"], dv)
        else:
            print(f"  -> blocked, remaining={budget.remaining_delta_v_km_s:.4f} km/s")
        if budget.below_safety_threshold:
            print("  ** FUEL BELOW SAFETY THRESHOLD - state_machine should force Completed/Idle **")
            break

    print("final budget:", budget.to_dict())
