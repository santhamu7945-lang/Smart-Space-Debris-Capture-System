
"""
GNC/kepler.py

Two-body Keplerian propagation.

Units:
    position : km
    velocity : km/s
    acceleration : km/s^2
    time : s

This module is responsible ONLY for absolute two-body orbital propagation.

It does not perform rendezvous guidance or capture control.
Those functions belong to the relative-motion / approach controller.
"""

from __future__ import annotations

import numpy as np


MU_EARTH_KM3_S2 = 398600.4418


def _as_vector(value, name: str) -> np.ndarray:
    """Convert a 3-element vector to a float numpy array."""
    arr = np.asarray(value, dtype=float)

    if arr.shape != (3,):
        raise ValueError(
            f"{name} must be a 3-element vector, got shape {arr.shape}"
        )

    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")

    return arr


def orbital_elements_from_state(
    position_km,
    velocity_km_s,
    mu: float = MU_EARTH_KM3_S2,
):
    """
    Convert Cartesian state to classical orbital elements.

    Returns:
        {
            "a": semi-major axis [km],
            "e": eccentricity,
            "i": inclination [rad],
            "raan": right ascension of ascending node [rad],
            "argp": argument of periapsis [rad],
            "nu": true anomaly [rad],
        }
    """

    r = _as_vector(position_km, "position_km")
    v = _as_vector(velocity_km_s, "velocity_km_s")

    r_norm = np.linalg.norm(r)
    v_norm = np.linalg.norm(v)

    if r_norm < 1e-9:
        raise ValueError("Position magnitude is too small.")

    h = np.cross(r, v)
    h_norm = np.linalg.norm(h)

    if h_norm < 1e-12:
        raise ValueError("Specific angular momentum is too small.")

    n = np.cross(np.array([0.0, 0.0, 1.0]), h)
    n_norm = np.linalg.norm(n)

    e_vec = np.cross(v, h) / mu - r / r_norm
    e = float(np.linalg.norm(e_vec))

    specific_energy = (
        0.5 * v_norm**2
        - mu / r_norm
    )

    if abs(specific_energy) > 1e-12:
        a = -mu / (2.0 * specific_energy)
    else:
        a = np.inf

    inclination = np.arccos(
        np.clip(h[2] / h_norm, -1.0, 1.0)
    )

    # RAAN
    if n_norm > 1e-12:
        raan = np.arctan2(n[1], n[0]) % (2.0 * np.pi)
    else:
        raan = 0.0

    # Argument of periapsis
    if n_norm > 1e-12 and e > 1e-10:
        argp = np.arccos(
            np.clip(
                np.dot(n, e_vec) / (n_norm * e),
                -1.0,
                1.0,
            )
        )

        if e_vec[2] < 0:
            argp = 2.0 * np.pi - argp
    else:
        argp = 0.0

    # True anomaly
    if e > 1e-10:
        nu = np.arccos(
            np.clip(
                np.dot(e_vec, r) / (e * r_norm),
                -1.0,
                1.0,
            )
        )

        if np.dot(r, v) < 0:
            nu = 2.0 * np.pi - nu
    else:
        nu = 0.0

    return {
        "a": float(a),
        "e": float(e),
        "i": float(inclination),
        "raan": float(raan),
        "argp": float(argp),
        "nu": float(nu),
    }


def mean_motion(
    a_km: float,
    mu: float = MU_EARTH_KM3_S2,
) -> float:
    """
    Mean orbital motion.

    Returns:
        rad/s
    """

    if not np.isfinite(a_km) or a_km <= 0.0:
        raise ValueError("Semi-major axis must be positive and finite.")

    return float(np.sqrt(mu / a_km**3))


def _two_body_acceleration(
    position_km: np.ndarray,
    mu: float,
) -> np.ndarray:
    """Two-body gravitational acceleration."""
    r_norm = np.linalg.norm(position_km)

    if r_norm < 1e-9:
        raise ValueError(
            "Position magnitude became too small during propagation."
        )

    return -mu * position_km / r_norm**3


def propagate_kepler(
    position_km,
    velocity_km_s,
    dt_s: float,
    mu: float = MU_EARTH_KM3_S2,
):
    """
    Propagate an inertial Cartesian state using RK4 integration
    of the two-body equations.

    This is intentionally a small-step propagator suitable for
    the simulation.

    IMPORTANT:
        This function does not perform rendezvous guidance.
        It only propagates the state that it receives.
    """

    r0 = _as_vector(position_km, "position_km")
    v0 = _as_vector(velocity_km_s, "velocity_km_s")

    dt_s = float(dt_s)

    if not np.isfinite(dt_s):
        raise ValueError("dt_s must be finite.")

    if abs(dt_s) < 1e-15:
        return r0.copy(), v0.copy()

    if np.linalg.norm(r0) < 1e-9:
        raise ValueError(
            "Initial position magnitude is too small."
        )

    def derivative(state):
        r = state[:3]
        v = state[3:]

        a = _two_body_acceleration(r, mu)

        return np.concatenate(
            (
                v,
                a,
            )
        )

    state = np.concatenate(
        (
            r0,
            v0,
        )
    )

    # Maximum RK4 substep = 1 second.
    n_substeps = max(
        1,
        int(np.ceil(abs(dt_s))),
    )

    h = dt_s / n_substeps

    for _ in range(n_substeps):

        k1 = derivative(state)

        k2 = derivative(
            state + 0.5 * h * k1
        )

        k3 = derivative(
            state + 0.5 * h * k2
        )

        k4 = derivative(
            state + h * k3
        )

        state = state + (
            h
            / 6.0
            * (
                k1
                + 2.0 * k2
                + 2.0 * k3
                + k4
            )
        )

    r_new = state[:3]
    v_new = state[3:]

    if not np.all(np.isfinite(r_new)):
        raise FloatingPointError(
            "Kepler propagation produced invalid position."
        )

    if not np.all(np.isfinite(v_new)):
        raise FloatingPointError(
            "Kepler propagation produced invalid velocity."
        )

    return r_new, v_new


if __name__ == "__main__":

    r0 = np.array(
        [7000.0, 0.0, 0.0]
    )

    v0 = np.array(
        [0.0, 7.5, 0.5]
    )

    r1, v1 = propagate_kepler(
        r0,
        v0,
        dt_s=600.0,
    )

    print("Initial position:", r0)
    print("Initial velocity:", v0)

    print("Final position:", r1)
    print("Final velocity:", v1)

    elements = orbital_elements_from_state(
        r0,
        v0,
    )

    print("Orbital elements:")
    for key, value in elements.items():
        print(f"  {key}: {value}")

