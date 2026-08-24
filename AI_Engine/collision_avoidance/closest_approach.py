"""
Closest Approach Analysis Module
Computes relative motion and closest approach distance.
"""

from typing import Dict
import numpy as np


def closest_approach(
    sat_position_km,
    sat_velocity_kms,
    debris_position_km,
    debris_velocity_kms
) -> Dict[str, float]:

    # Relative position vector
    r_rel = np.array(debris_position_km) - np.array(sat_position_km)

    # Relative velocity vector
    v_rel = np.array(debris_velocity_kms) - np.array(sat_velocity_kms)

    # Relative speed squared
    v_rel_sq = np.dot(v_rel, v_rel)

    # Time to closest approach
    if v_rel_sq < 1e-12:
        t_ca = 0.0
    else:
        t_ca = -np.dot(r_rel, v_rel) / v_rel_sq

    # Only future times are considered
    t_ca = max(t_ca, 0.0)

    # Position at closest approach
    r_ca = r_rel + v_rel * t_ca

    # Distance at closest approach
    distance_km = np.linalg.norm(r_ca)

    # Relative speed
    relative_velocity_kms = np.linalg.norm(v_rel)

    return {
        'time_to_closest_approach_s': float(t_ca),
        'closest_distance_m': float(distance_km * 1000.0),
        'relative_velocity_kms': float(relative_velocity_kms)
    }