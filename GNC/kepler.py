"""
kepler.py
Two-body Keplerian propagation, used for LONG-RANGE prediction
(relative_distance > threshold_km). Handed off to relative_motion.py's
CW equations once inside close range — see orbit_propagator.py.

Solves Challenge 2 (long-range part).
"""

import numpy as np

MU_EARTH_KM3_S2 = 398600.4418  # standard gravitational parameter, km^3/s^2


def orbital_elements_from_state(position_km, velocity_km_s, mu=MU_EARTH_KM3_S2):
    """
    Convert a Cartesian state vector to classical orbital elements.
    Returns dict: a (semi-major axis, km), e (eccentricity),
    i (inclination, rad), raan (rad), argp (rad), nu (true anomaly, rad).
    """
    r = np.array(position_km, dtype=float)
    v = np.array(velocity_km_s, dtype=float)
    r_norm = np.linalg.norm(r)
    v_norm = np.linalg.norm(v)

    h = np.cross(r, v)              # specific angular momentum
    h_norm = np.linalg.norm(h)
    n = np.cross([0, 0, 1], h)      # node vector
    n_norm = np.linalg.norm(n)

    e_vec = (np.cross(v, h) / mu) - (r / r_norm)
    e = np.linalg.norm(e_vec)

    energy = v_norm ** 2 / 2 - mu / r_norm
    a = -mu / (2 * energy) if abs(energy) > 1e-12 else np.inf

    i = np.arccos(np.clip(h[2] / h_norm, -1, 1))

    if n_norm > 1e-9:
        raan = np.arccos(np.clip(n[0] / n_norm, -1, 1))
        if n[1] < 0:
            raan = 2 * np.pi - raan
    else:
        raan = 0.0

    if n_norm > 1e-9 and e > 1e-9:
        argp = np.arccos(np.clip(np.dot(n, e_vec) / (n_norm * e), -1, 1))
        if e_vec[2] < 0:
            argp = 2 * np.pi - argp
    else:
        argp = 0.0

    if e > 1e-9:
        nu = np.arccos(np.clip(np.dot(e_vec, r) / (e * r_norm), -1, 1))
        if np.dot(r, v) < 0:
            nu = 2 * np.pi - nu
    else:
        nu = 0.0

    return {"a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu}


def mean_motion(a_km, mu=MU_EARTH_KM3_S2) -> float:
    """n = sqrt(mu / a^3), rad/s. Needed by relative_motion.py's CW equations."""
    return np.sqrt(mu / a_km ** 3)


def _solve_kepler_eq(M, e, tol=1e-10, max_iter=50):
    """Newton-Raphson solve of Kepler's equation M = E - e*sin(E)."""
    E = M if e < 0.8 else np.pi
    for _ in range(max_iter):
        dE = (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
        E -= dE
        if abs(dE) < tol:
            break
    return E


def propagate_kepler(position_km, velocity_km_s, dt_s, mu=MU_EARTH_KM3_S2):
    """
    Propagate a Cartesian state forward by dt_s seconds using classical
    Keplerian (two-body) mechanics. Returns (new_position_km, new_velocity_km_s).
    """
    elems = orbital_elements_from_state(position_km, velocity_km_s, mu)
    a, e, i, raan, argp, nu0 = (elems["a"], elems["e"], elems["i"],
                                 elems["raan"], elems["argp"], elems["nu"])

    n = mean_motion(a, mu)
    E0 = 2 * np.arctan2(np.sqrt(1 - e) * np.sin(nu0 / 2), np.sqrt(1 + e) * np.cos(nu0 / 2))
    M0 = E0 - e * np.sin(E0)
    M1 = M0 + n * dt_s
    E1 = _solve_kepler_eq(M1 % (2 * np.pi), e)
    nu1 = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E1 / 2), np.sqrt(1 - e) * np.cos(E1 / 2))

    p = a * (1 - e ** 2)
    r_mag = p / (1 + e * np.cos(nu1))

    # position/velocity in perifocal frame
    r_pf = r_mag * np.array([np.cos(nu1), np.sin(nu1), 0])
    v_pf = (np.sqrt(mu / p) * np.array([-np.sin(nu1), e + np.cos(nu1), 0]))

    # rotation perifocal -> ECI
    cO, sO = np.cos(raan), np.sin(raan)
    ci, si = np.cos(i), np.sin(i)
    cw, sw = np.cos(argp), np.sin(argp)
    R = np.array([
        [cO * cw - sO * sw * ci, -cO * sw - sO * cw * ci, sO * si],
        [sO * cw + cO * sw * ci, -sO * sw + cO * cw * ci, -cO * si],
        [sw * si,                 cw * si,                 ci],
    ])

    r_new = R @ r_pf
    v_new = R @ v_pf
    return r_new, v_new


if __name__ == "__main__":
    r0 = [7000.0, 0.0, 0.0]
    v0 = [0.0, 7.5, 0.5]
    r1, v1 = propagate_kepler(r0, v0, dt_s=600)
    print("r1:", r1)
    print("v1:", v1)
