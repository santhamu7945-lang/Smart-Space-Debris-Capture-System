"""
robotic_arm.py
Computes the reaction torque generated whenever the arm moves (feeds
physics/gnc.py, Challenge 6), and tracks mechanism wear/health
(Challenge 12).
"""

import numpy as np


class RoboticArm:
    """
    Parameters
    ----------
    segment_mass_kg : float          mass of the moving segment
    segment_length_m : float         length from pivot to effective CoM
    reach_envelope_m : float         max reach, used for capture-window checks
    wear_per_use : float             mechanism_health points lost per movement
    """

    def __init__(self, segment_mass_kg=8.0, segment_length_m=1.2,
                 reach_envelope_m=1.5, wear_per_use=0.4):
        self.segment_mass_kg = segment_mass_kg
        self.segment_length_m = segment_length_m
        self.reach_envelope_m = reach_envelope_m
        self.wear_per_use = wear_per_use

        # moment of inertia of a rod pivoting at one end: I = (1/3) m L^2
        self.moment_of_inertia_kg_m2 = (1.0 / 3.0) * segment_mass_kg * segment_length_m ** 2

        self.mechanism_health = 100.0   # Challenge 12
        self.servicing_needed = False

    def compute_reaction_torque(self, angular_acceleration_rad_s2: np.ndarray) -> np.ndarray:
        """
        torque = I * angular_acceleration (per axis), the reaction torque
        felt by the spacecraft body (Newton's third law) when the arm
        executes this movement. Passed to gnc.py as a disturbance input.
        """
        angular_acceleration_rad_s2 = np.array(angular_acceleration_rad_s2, dtype=float)
        torque = self.moment_of_inertia_kg_m2 * angular_acceleration_rad_s2
        self._register_use()
        return torque

    def _register_use(self):
        """Challenge 12: decrement mechanism_health on each use, flag for
        servicing if it drops below threshold."""
        self.mechanism_health = max(0.0, self.mechanism_health - self.wear_per_use)
        if self.mechanism_health < 20.0:
            self.servicing_needed = True

    def in_reach(self, target_offset_m: np.ndarray) -> bool:
        """Used with Challenge 3's capture-window computation: is the
        debris grab point currently within the arm's reach envelope?"""
        return float(np.linalg.norm(target_offset_m)) <= self.reach_envelope_m

    def compute_capture_window(self, grab_point_world_m, arm_base_position_m,
                                rotation_axis, tumbling_rate_rad_s, horizon_s=10.0, dt_s=0.5):
        """
        Scan forward over `horizon_s` seconds, checking when the (tumbling)
        grab point falls within the arm's reach envelope. Returns list of
        candidate times (s) — the "capture window" from Challenge 3.
        """
        import sys, os
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "DEBRIS"))
        from debris import rodrigues_rotate  # DEBRIS/debris.py (top-level folder, repo restructure)

        grab_point = np.array(grab_point_world_m, dtype=float)
        base = np.array(arm_base_position_m, dtype=float)
        axis = np.array(rotation_axis, dtype=float)

        window = []
        t = 0.0
        while t <= horizon_s:
            angle = tumbling_rate_rad_s * t
            gp_t = rodrigues_rotate(grab_point, axis, angle)
            offset = gp_t - base
            if self.in_reach(offset):
                window.append(round(t, 2))
            t += dt_s
        return window


if __name__ == "__main__":
    arm = RoboticArm()
    torque = arm.compute_reaction_torque([0.3, -0.1, 0.0])
    print("reaction torque (Nm):", torque)
    print("mechanism_health after 1 use:", arm.mechanism_health)

    for _ in range(250):
        arm.compute_reaction_torque([0.1, 0, 0])
    print("mechanism_health after many uses:", arm.mechanism_health,
          "servicing_needed:", arm.servicing_needed)
