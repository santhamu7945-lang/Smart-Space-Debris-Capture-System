"""
relative_motion.py
Clohessy-Wiltshire (Hill's) equations for close-range relative motion,
used once relative_distance < threshold_km (see orbit_propagator.py).

Frame convention (Hill/RSW frame, chaser relative to target):
  x - radial (away from Earth)
  y - along-track (direction of motion)
  z - cross-track (out of orbital plane)

Solves Challenge 2 (close-range part). Called by physics/gnc.py to compute
the delta-v required to close the gap during the Approaching phase.
"""

import numpy as np


def cw_state_transition_matrices(n: float, t: float):
    """
    Build the CW state transition sub-matrices Phi_rr, Phi_rv, Phi_vr, Phi_vv
    such that:
        [r(t)]   [Phi_rr  Phi_rv] [r0]
        [v(t)] = [Phi_vr  Phi_vv] [v0]

    n : mean motion of the target's orbit (rad/s), from orbit.kepler.mean_motion
    t : elapsed time (s)
    """
    nt = n * t
    s, c = np.sin(nt), np.cos(nt)

    Phi_rr = np.array([
        [4 - 3 * c,      0, 0],
        [6 * (s - nt),   1, 0],
        [0,              0, c],
    ])
    Phi_rv = np.array([
        [s / n,               2 * (1 - c) / n,       0],
        [2 * (c - 1) / n,     (4 * s - 3 * nt) / n,  0],
        [0,                   0,                     s / n],
    ])
    Phi_vr = np.array([
        [3 * n * s,      0, 0],
        [6 * n * (c - 1), 0, 0],
        [0,               0, -n * s],
    ])
    Phi_vv = np.array([
        [c,        2 * s,      0],
        [-2 * s,   4 * c - 3,  0],
        [0,        0,          c],
    ])
    return Phi_rr, Phi_rv, Phi_vr, Phi_vv


def propagate_cw(rel_pos_km, rel_vel_km_s, n: float, dt_s: float):
    """Propagate relative state (r, v) forward dt_s seconds under CW dynamics."""
    Phi_rr, Phi_rv, Phi_vr, Phi_vv = cw_state_transition_matrices(n, dt_s)
    r0 = np.array(rel_pos_km, dtype=float)
    v0 = np.array(rel_vel_km_s, dtype=float)
    r1 = Phi_rr @ r0 + Phi_rv @ v0
    v1 = Phi_vr @ r0 + Phi_vv @ v0
    return r1, v1


def cw_targeting_delta_v(rel_pos_km, rel_vel_km_s, n: float, transfer_time_s: float):
    """
    Two-impulse CW targeting: solve for the initial velocity v0_required that
    drives the chaser from rel_pos_km to the origin (target location) in
    transfer_time_s, then compute the delta-v needed now and the delta-v
    needed at arrival (to null out the resulting velocity).

    Returns
    -------
    dv1_km_s : np.ndarray(3,)  first burn (apply now)
    dv2_km_s : np.ndarray(3,)  second burn (apply at arrival, to stop)
    total_delta_v_km_s : float
    """
    r0 = np.array(rel_pos_km, dtype=float)
    v0 = np.array(rel_vel_km_s, dtype=float)
    Phi_rr, Phi_rv, Phi_vr, Phi_vv = cw_state_transition_matrices(n, transfer_time_s)

    # Solve Phi_rr @ r0 + Phi_rv @ v_required = 0  ->  v_required
    Phi_rv_inv = np.linalg.pinv(Phi_rv)
    v_required = Phi_rv_inv @ (-Phi_rr @ r0)

    dv1 = v_required - v0

    # velocity at arrival under v_required
    v_arrival = Phi_vr @ r0 + Phi_vv @ v_required
    dv2 = -v_arrival  # null relative velocity at rendezvous

    total_dv = np.linalg.norm(dv1) + np.linalg.norm(dv2)
    return dv1, dv2, total_dv


if __name__ == "__main__":
    from kepler import mean_motion
    n = mean_motion(a_km=7000.0)
    r0 = [2.0, -5.0, 0.3]     # km, chaser behind & radially offset from target
    v0 = [0.0, 0.0, 0.0]
    dv1, dv2, total = cw_targeting_delta_v(r0, v0, n, transfer_time_s=1800)
    print("dv1 (km/s):", dv1)
    print("dv2 (km/s):", dv2)
    print("total delta-v (km/s):", total)
