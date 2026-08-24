"""
sensor_fusion.py
Fuses noisy camera + LiDAR readings (from feature_extraction.py) with a
Kalman Filter into a single best-estimate position/velocity, which is what
actually gets written to debris_state.json.

Solves Challenge 1 (sensor limitations).

If you have `filterpy` installed, you can swap SimpleKalmanFilter below for
filterpy.kalman.KalmanFilter with the same call pattern (kf.predict(),
kf.update(z, R=...)). This file is self-contained so it runs with no
extra dependencies.
"""

import numpy as np


class SimpleKalmanFilter:
    """
    Constant-velocity Kalman Filter over a 6D state [x, y, z, vx, vy, vz].

    Parameters
    ----------
    dt_s : float                nominal timestep used to build F, Q
    process_noise_std : float   how much we trust the constant-velocity model
    """

    def __init__(self, initial_position_km, initial_velocity_km_s,
                 dt_s=1.0, process_noise_std=1e-4):
        self.dt = dt_s
        x0 = np.array(initial_position_km, dtype=float)
        v0 = np.array(initial_velocity_km_s, dtype=float)
        self.x = np.concatenate([x0, v0])          # state: [pos(3), vel(3)]
        self.P = np.eye(6) * 1.0                    # state covariance

        self.F = np.eye(6)                           # state transition
        self.F[0:3, 3:6] = np.eye(3) * dt_s

        q = process_noise_std ** 2
        self.Q = np.eye(6) * q                       # process noise covariance

        self.H = np.zeros((3, 6))                     # measurement matrix (we observe position only)
        self.H[0:3, 0:3] = np.eye(3)

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, measured_position_km, measurement_noise_std_km):
        R = np.eye(3) * (measurement_noise_std_km ** 2)
        z = np.array(measured_position_km, dtype=float)

        y = z - self.H @ self.x                       # innovation
        S = self.H @ self.P @ self.H.T + R             # innovation covariance
        K = self.P @ self.H.T @ np.linalg.inv(S)       # Kalman gain

        self.x = self.x + K @ y
        self.P = (np.eye(6) - K @ self.H) @ self.P

    @property
    def position_km(self):
        return self.x[0:3]

    @property
    def velocity_km_s(self):
        return self.x[3:6]

    @property
    def position_uncertainty_km(self):
        """
        Trace of the position block of the covariance matrix — used as the
        detection_confidence proxy written to debris_state.json.
        """
        return float(np.trace(self.P[0:3, 0:3]))


def fuse_debris_state(debris_id, true_position_km, true_velocity_km_s,
                       camera_reading, lidar_reading, kf_store, dt_s=1.0):
    """
    Sequentially update (or create) a per-debris Kalman filter with the
    camera reading, then the LiDAR reading (if available), and return the
    fused state ready to be written into debris_state.json.

    kf_store : dict[debris_id -> SimpleKalmanFilter]   persists filters
               across timesteps, keyed by debris id.
    """
    if debris_id not in kf_store:
        kf_store[debris_id] = SimpleKalmanFilter(true_position_km, true_velocity_km_s, dt_s=dt_s)

    kf = kf_store[debris_id]
    kf.predict()
    kf.update(camera_reading["position_km"], camera_reading["noise_std_km"])
    if lidar_reading is not None:
        kf.update(lidar_reading["position_km"], lidar_reading["noise_std_km"])

    return {
        "position_km": kf.position_km.tolist(),
        "velocity_km_s": kf.velocity_km_s.tolist(),
        "position_uncertainty_km": kf.position_uncertainty_km,
    }


if __name__ == "__main__":
    from feature_extraction import simulate_camera_reading, simulate_lidar_reading

    true_pos = np.array([7002.0, 1.0, 0.2])
    true_vel = np.array([0.0, 7.5, 0.0])
    kf_store = {}

    print("Fixed trajectory, injected noise, tracking convergence:")
    for t in range(10):
        true_pos = true_pos + true_vel * 1.0
        cam = simulate_camera_reading(true_pos, true_vel, range_km=5.0)
        lidar = simulate_lidar_reading(true_pos, true_vel, range_km=5.0)

        fused = fuse_debris_state("D001", true_pos, true_vel, cam, lidar, kf_store)

        fused_err = np.linalg.norm(np.array(fused["position_km"]) - true_pos)
        cam_err = np.linalg.norm(cam["position_km"] - true_pos)
        print(f"t={t}s  fused_err={fused_err:.5f} km  camera_err={cam_err:.5f} km  "
              f"uncertainty={fused['position_uncertainty_km']:.6f}")
