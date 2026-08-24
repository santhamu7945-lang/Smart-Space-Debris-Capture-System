"""
orbit_propagator.py
Unified propagation interface: uses Keplerian two-body propagation for
long range, switches to Clohessy-Wiltshire relative motion once inside
`threshold_km`. This is the single entry point GNC / Mission Manager
should call instead of hitting kepler.py or relative_motion.py directly.

Solves Challenge 2 (switch-over rule).
"""

import numpy as np

from kepler import propagate_kepler, mean_motion, orbital_elements_from_state
from relative_motion import propagate_cw

DEFAULT_THRESHOLD_KM = 50.0


class OrbitPropagator:
    def __init__(self, threshold_km: float = DEFAULT_THRESHOLD_KM):
        self.threshold_km = threshold_km

    def relative_distance_km(self, chaser_pos_km, target_pos_km) -> float:
        return float(np.linalg.norm(np.array(chaser_pos_km) - np.array(target_pos_km)))

    def propagate(self, chaser_pos_km, chaser_vel_km_s,
                   target_pos_km, target_vel_km_s, dt_s):
        """
        Propagate the chaser forward dt_s seconds, automatically choosing
        Keplerian (far) or CW relative-motion (near) dynamics.

        Returns dict with new chaser state, mode used, and current range.
        """
        dist = self.relative_distance_km(chaser_pos_km, target_pos_km)

        if dist > self.threshold_km:
            # --- far range: independent two-body propagation ---
            new_pos, new_vel = propagate_kepler(chaser_pos_km, chaser_vel_km_s, dt_s)
            mode = "keplerian"
        else:
            # --- close range: CW relative motion about the target ---
            rel_pos = np.array(chaser_pos_km) - np.array(target_pos_km)
            rel_vel = np.array(chaser_vel_km_s) - np.array(target_vel_km_s)

            elems = orbital_elements_from_state(target_pos_km, target_vel_km_s)
            n = mean_motion(elems["a"])

            rel_pos_new, rel_vel_new = propagate_cw(rel_pos, rel_vel, n, dt_s)

            # target itself still moves under two-body dynamics
            target_pos_new, target_vel_new = propagate_kepler(target_pos_km, target_vel_km_s, dt_s)

            new_pos = target_pos_new + rel_pos_new
            new_vel = target_vel_new + rel_vel_new
            mode = "clohessy-wiltshire"

        return {
            "position_km": new_pos,
            "velocity_km_s": new_vel,
            "mode": mode,
            "relative_distance_km": dist,
        }


if __name__ == "__main__":
    prop = OrbitPropagator(threshold_km=50.0)

    # far-range case
    out_far = prop.propagate([7100, 100, 0], [0, 7.4, 0.1],
                              [7000, 0, 0], [0, 7.5, 0], dt_s=60)
    print("FAR:", out_far["mode"], "range=%.1f km" % out_far["relative_distance_km"])

    # near-range case
    out_near = prop.propagate([7002, 1.0, 0.2], [0, 7.5, 0],
                               [7000, 0, 0], [0, 7.5, 0], dt_s=60)
    print("NEAR:", out_near["mode"], "range=%.3f km" % out_near["relative_distance_km"])
