"""
feature_extraction.py
Turns raw simulated "true" debris state into noisy per-sensor readings
(camera + LiDAR), plus estimated features (tumbling rate/axis, collision
confidence) that downstream modules consume.

Solves:
- Challenge 1 (produces the two noisy sensor streams sensor_fusion.py fuses)
- Challenge 3 (estimation side: tumbling_rate + rotation_axis output)
- feeds collision_confidence used by mission_manager.py (Challenge 8)
"""

import numpy as np


def simulate_camera_reading(true_position_km, true_velocity_km_s,
                             range_km, base_noise_std_km=0.01,
                             range_scale_factor=0.002):
    """
    Camera noise DEGRADES with distance (angular resolution is fixed,
    so linear position error grows with range).

    noise_std = base_noise_std_km + range_scale_factor * range_km
    """
    noise_std = base_noise_std_km + range_scale_factor * range_km
    pos_noise = np.random.normal(0, noise_std, size=3)
    vel_noise = np.random.normal(0, noise_std * 0.1, size=3)  # velocity derived, noisier fraction
    return {
        "position_km": np.array(true_position_km) + pos_noise,
        "velocity_km_s": np.array(true_velocity_km_s) + vel_noise,
        "noise_std_km": noise_std,
        "sensor": "camera",
    }


def simulate_lidar_reading(true_position_km, true_velocity_km_s,
                            range_km, base_noise_std_km=0.002,
                            range_scale_factor=0.0002,
                            max_range_km=20.0):
    """
    LiDAR is more precise at short range but has a hard max range and
    noise grows more slowly with distance than camera noise.
    Returns None if out of LiDAR range (camera-only fallback upstream).
    """
    if range_km > max_range_km:
        return None
    noise_std = base_noise_std_km + range_scale_factor * range_km
    pos_noise = np.random.normal(0, noise_std, size=3)
    vel_noise = np.random.normal(0, noise_std * 0.1, size=3)
    return {
        "position_km": np.array(true_position_km) + pos_noise,
        "velocity_km_s": np.array(true_velocity_km_s) + vel_noise,
        "noise_std_km": noise_std,
        "sensor": "lidar",
    }


def estimate_tumbling(prev_orientation, curr_orientation, dt_s):
    """
    Estimate rotation_axis (unit vector) and tumbling_rate (rad/s) from two
    successive observed orientation vectors, via the small-angle rotation
    between them (cross product for axis, arccos for angle).

    Solves Challenge 3 (estimation side) -- extends beyond a scalar rate to
    also output the rotation_axis used for capture-window planning.
    """
    p = np.array(prev_orientation, dtype=float)
    c = np.array(curr_orientation, dtype=float)
    p_n = p / (np.linalg.norm(p) + 1e-12)
    c_n = c / (np.linalg.norm(c) + 1e-12)

    axis = np.cross(p_n, c_n)
    axis_norm = np.linalg.norm(axis)
    cos_angle = np.clip(np.dot(p_n, c_n), -1.0, 1.0)
    angle = np.arccos(cos_angle)

    if axis_norm < 1e-9 or dt_s <= 0:
        return {"rotation_axis": np.array([0.0, 0.0, 1.0]), "tumbling_rate_rad_s": 0.0}

    return {
        "rotation_axis": axis / axis_norm,
        "tumbling_rate_rad_s": float(angle / dt_s),
    }


def estimate_collision_confidence(relative_distance_km, relative_speed_km_s,
                                   position_uncertainty_km):
    """
    Simple heuristic collision-confidence score in [0, 1], combining
    closing speed, current range, and sensor uncertainty. Consumed by
    mission_manager.py (Challenge 8) which buckets it into LOW/MED/HIGH.
    """
    # closer + faster-closing + more uncertain => higher confidence of risk
    range_term = np.exp(-relative_distance_km / 5.0)         # decays over 5 km scale
    speed_term = np.clip(relative_speed_km_s / 0.05, 0, 1)     # saturates at 50 m/s closing
    uncertainty_term = np.clip(position_uncertainty_km / 1.0, 0, 1)

    confidence = 0.5 * range_term + 0.35 * speed_term + 0.15 * uncertainty_term
    return float(np.clip(confidence, 0.0, 1.0))


def bucket_threat_level(collision_confidence: float) -> str:
    if collision_confidence >= 0.7:
        return "HIGH"
    elif collision_confidence >= 0.35:
        return "MED"
    return "LOW"


if __name__ == "__main__":
    true_pos = [7002.0, 1.0, 0.2]
    true_vel = [0.0, 7.5, 0.0]
    rng = 5.0

    cam = simulate_camera_reading(true_pos, true_vel, rng)
    lidar = simulate_lidar_reading(true_pos, true_vel, rng)
    print("camera:", cam)
    print("lidar:", lidar)

    tumble = estimate_tumbling([1, 0, 0], [0.98, 0.15, 0.02], dt_s=1.0)
    print("tumble estimate:", tumble)

    conf = estimate_collision_confidence(2.0, 0.03, 0.05)
    print("collision_confidence:", conf, bucket_threat_level(conf))
