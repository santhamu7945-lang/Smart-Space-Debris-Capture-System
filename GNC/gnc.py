"""
gnc.py
Guidance, Navigation & Control.
  - compute_approach_delta_v(): wraps orbit.relative_motion CW targeting,
    called during the Approaching mission phase (Challenge 2).
  - SpacecraftAttitude + apply_disturbance_torque(): Newton's-third-law
    reaction to arm movements, absorbed by a simple reaction wheel model
    (Challenge 6).
  - update_inertia_properties(): receives new mass/CoM/inertia from
    storage_drum.py after each capture and updates control response
    (Challenge 7).
"""

import sys, os
import numpy as np

# relative_motion.py now lives in this same GNC/ folder (repo restructure:
# orbit mechanics + GNC control live together under top-level GNC/)
sys.path.append(os.path.dirname(__file__))
from relative_motion import cw_targeting_delta_v  # noqa: E402


def compute_approach_delta_v(rel_pos_km, rel_vel_km_s, n_mean_motion, transfer_time_s):
    """Called during 'Approaching' phase. Thin wrapper so mission code
    doesn't need to import orbit.relative_motion directly."""
    dv1, dv2, total = cw_targeting_delta_v(rel_pos_km, rel_vel_km_s, n_mean_motion, transfer_time_s)
    return {"burn_now_km_s": dv1, "burn_at_arrival_km_s": dv2, "total_delta_v_km_s": total}


class ReactionWheel:
    """
    Simple single-axis-per-wheel reaction wheel bank that absorbs
    disturbance torque and drives it toward zero over a few timesteps
    (proportional-damping response, not full wheel dynamics).

    Parameters
    ----------
    max_torque_Nm : float          saturation limit per axis
    damping_gain : float           fraction of stored disturbance cancelled per step (0-1)
    """

    def __init__(self, max_torque_Nm=0.5, damping_gain=0.3):
        self.max_torque_Nm = max_torque_Nm
        self.damping_gain = damping_gain
        self.stored_momentum_Nms = np.zeros(3)

    def absorb(self, disturbance_torque_Nm: np.ndarray, dt_s: float):
        """Wheel spins up to counter the disturbance; returns net torque
        actually applied to the spacecraft body after wheel compensation."""
        commanded = np.clip(-disturbance_torque_Nm, -self.max_torque_Nm, self.max_torque_Nm)
        applied = commanded * self.damping_gain
        self.stored_momentum_Nms += applied * dt_s
        net_torque_on_body = disturbance_torque_Nm + applied
        return net_torque_on_body


class SpacecraftAttitude:
    """
    Minimal rigid-body attitude tracker (roll/pitch/yaw rates from torque),
    used to demo disturbance rejection with vs without reaction wheels.
    """

    def __init__(self, inertia_tensor_kg_m2=None):
        self.inertia = inertia_tensor_kg_m2 if inertia_tensor_kg_m2 is not None else np.eye(3) * 50.0
        self.angular_velocity_rad_s = np.zeros(3)   # roll, pitch, yaw rates
        self.attitude_rad = np.zeros(3)
        self.reaction_wheel = ReactionWheel()

    def update_inertia_properties(self, new_inertia_tensor_kg_m2):
        """
        Receives updated inertia tensor from storage_drum.py after a
        capture (Challenge 7). Control response should visibly change
        because torque -> angular acceleration = inertia^-1 @ torque.
        """
        self.inertia = new_inertia_tensor_kg_m2

    def apply_disturbance_torque(self, torque_Nm: np.ndarray, dt_s: float, use_wheel=True):
        """
        Apply an arm-induced disturbance torque (Newton's third law: the
        arm's reaction torque acts on the spacecraft body). If use_wheel,
        route it through the reaction wheel first.
        """
        torque_Nm = np.array(torque_Nm, dtype=float)
        net_torque = self.reaction_wheel.absorb(torque_Nm, dt_s) if use_wheel else torque_Nm

        inv_inertia = np.linalg.inv(self.inertia)
        angular_accel = inv_inertia @ net_torque
        self.angular_velocity_rad_s += angular_accel * dt_s
        self.attitude_rad += self.angular_velocity_rad_s * dt_s
        return self.attitude_rad.copy()


if __name__ == "__main__":
    # Challenge 6 test/demo: attitude drift with vs without reaction wheel
    torque_from_arm = np.array([0.2, -0.05, 0.0])  # Nm, from robotic_arm.py

    sc_with_wheel = SpacecraftAttitude()
    sc_no_wheel = SpacecraftAttitude()

    drift_with, drift_without = [], []
    for _ in range(20):
        a1 = sc_with_wheel.apply_disturbance_torque(torque_from_arm, dt_s=1.0, use_wheel=True)
        a2 = sc_no_wheel.apply_disturbance_torque(torque_from_arm, dt_s=1.0, use_wheel=False)
        drift_with.append(np.linalg.norm(a1))
        drift_without.append(np.linalg.norm(a2))

    print("attitude drift (rad) WITH wheel, last 5 steps:", [f"{v:.4f}" for v in drift_with[-5:]])
    print("attitude drift (rad) WITHOUT wheel, last 5 steps:", [f"{v:.4f}" for v in drift_without[-5:]])
