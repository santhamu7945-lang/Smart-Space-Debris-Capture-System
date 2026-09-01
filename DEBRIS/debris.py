
"""
DEBRIS/debris.py

Simulated orbital debris objects.

Each object contains:

    - inertial position
    - inertial velocity
    - mass
    - characteristic size
    - angular velocity
    - orientation
    - grab-point orientation

Translational motion uses the repository GNC two-body propagator
when the object represents a real orbital state.

Rotational motion uses Rodrigues rotation.

This is simulation software, not flight-qualified software.
"""

from __future__ import annotations

import os
import sys
import uuid

import numpy as np


# ----------------------------------------------------------------------
# Repository import
# ----------------------------------------------------------------------

THIS_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

REPO_ROOT = os.path.dirname(
    THIS_DIR
)

GNC_DIR = os.path.join(
    REPO_ROOT,
    "GNC",
)

if GNC_DIR not in sys.path:
    sys.path.insert(
        0,
        GNC_DIR,
    )

from kepler import propagate_kepler


# ----------------------------------------------------------------------
# Rotation utilities
# ----------------------------------------------------------------------

def rodrigues_rotate(
    vector: np.ndarray,
    axis: np.ndarray,
    angle_rad: float,
) -> np.ndarray:
    """
    Rotate vector about axis using Rodrigues' rotation formula.
    """

    vector = np.asarray(
        vector,
        dtype=float,
    )

    axis = np.asarray(
        axis,
        dtype=float,
    )

    axis_norm = np.linalg.norm(axis)

    if axis_norm < 1e-12:
        return vector.copy()

    k = axis / axis_norm

    cos_t = np.cos(angle_rad)
    sin_t = np.sin(angle_rad)

    return (
        vector * cos_t
        + np.cross(k, vector) * sin_t
        + k * np.dot(k, vector) * (1.0 - cos_t)
    )


# ----------------------------------------------------------------------
# Debris object
# ----------------------------------------------------------------------

class DebrisObject:
    """
    Single simulated debris object.

    Parameters
    ----------
    position_km:
        Inertial position [km].

    velocity_km_s:
        Inertial velocity [km/s].

    mass_kg:
        Object mass [kg].

    size_m:
        Characteristic size [m].

    ang_vel_std_rad_s:
        Standard deviation used when generating random spin.

    debris_id:
        Optional deterministic identifier.
    """

    def __init__(
        self,
        position_km,
        velocity_km_s,
        mass_kg=5.0,
        size_m=0.3,
        ang_vel_std_rad_s=0.05,
        debris_id=None,
        rng=None,
    ):

        self.id = (
            debris_id
            or str(uuid.uuid4())[:8]
        )

        self.position_km = np.asarray(
            position_km,
            dtype=float,
        )

        self.velocity_km_s = np.asarray(
            velocity_km_s,
            dtype=float,
        )

        if self.position_km.shape != (3,):
            raise ValueError(
                "position_km must have shape (3,)"
            )

        if self.velocity_km_s.shape != (3,):
            raise ValueError(
                "velocity_km_s must have shape (3,)"
            )

        self.mass_kg = float(mass_kg)
        self.size_m = float(size_m)

        if self.mass_kg <= 0.0:
            raise ValueError(
                "mass_kg must be positive."
            )

        if self.size_m <= 0.0:
            raise ValueError(
                "size_m must be positive."
            )

        # --------------------------------------------------------------
        # Deterministic RNG when provided.
        # --------------------------------------------------------------

        if rng is None:
            rng = np.random.default_rng()

        self.angular_velocity_rad_s = rng.uniform(
            -ang_vel_std_rad_s,
            ang_vel_std_s
            if False
            else ang_vel_std_rad_s,
            size=3,
        )

        # --------------------------------------------------------------
        # Orientation state.
        # --------------------------------------------------------------

        self.orientation_vector = np.array(
            [1.0, 0.0, 0.0],
            dtype=float,
        )

        self.grab_point_body = (
            np.array(
                [0.0, 0.0, 1.0],
                dtype=float,
            )
            * (self.size_m / 2.0)
        )

        self.grab_point_world = (
            self.grab_point_body.copy()
        )

    # ------------------------------------------------------------------
    # Rotational properties
    # ------------------------------------------------------------------

    @property
    def tumbling_rate_rad_s(self) -> float:
        return float(
            np.linalg.norm(
                self.angular_velocity_rad_s
            )
        )

    @property
    def rotation_axis(self) -> np.ndarray:

        norm = np.linalg.norm(
            self.angular_velocity_rad_s
        )

        if norm < 1e-12:
            return np.array(
                [0.0, 0.0, 1.0],
                dtype=float,
            )

        return (
            self.angular_velocity_rad_s
            / norm
        )

    # ------------------------------------------------------------------
    # Orbital motion
    # ------------------------------------------------------------------

    def step_orbit(
        self,
        dt_s: float,
    ):
        """
        Propagate inertial orbital state.

        Objects sufficiently far from the origin are treated as
        real orbital objects.

        Degenerate near-origin states are retained for isolated
        unit tests using simple linear motion.
        """

        dt_s = float(dt_s)

        r_norm = float(
            np.linalg.norm(
                self.position_km
            )
        )

        v_norm = float(
            np.linalg.norm(
                self.velocity_km_s
            )
        )

        # --------------------------------------------------------------
        # Real orbital state
        # --------------------------------------------------------------

        if r_norm > 100.0 and v_norm > 0.1:

            self.position_km, self.velocity_km_s = (
                propagate_kepler(
                    self.position_km,
                    self.velocity_km_s,
                    dt_s,
                )
            )

            return

        # --------------------------------------------------------------
        # Degenerate/unit-test state
        # --------------------------------------------------------------

        self.position_km = (
            self.position_km
            + self.velocity_km_s * dt_s
        )

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    def step_rotation(
        self,
        dt_s: float,
    ):
        """
        Integrate orientation using Rodrigues rotation.
        """

        rate = self.tumbling_rate_rad_s

        if rate < 1e-12:
            return

        angle = rate * dt_s

        axis = self.rotation_axis

        self.orientation_vector = (
            rodrigues_rotate(
                self.orientation_vector,
                axis,
                angle,
            )
        )

        self.grab_point_world = (
            rodrigues_rotate(
                self.grab_point_world,
                axis,
                angle,
            )
        )

    # ------------------------------------------------------------------
    # Combined step
    # ------------------------------------------------------------------

    def step(
        self,
        dt_s: float,
    ):
        self.step_orbit(dt_s)
        self.step_rotation(dt_s)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self):

        return {
            "id": self.id,
            "position_km": (
                self.position_km.tolist()
            ),
            "velocity_km_s": (
                self.velocity_km_s.tolist()
            ),
            "mass_kg": self.mass_kg,
            "size_m": self.size_m,
            "tumbling_rate_rad_s": (
                self.tumbling_rate_rad_s
            ),
            "rotation_axis": (
                self.rotation_axis.tolist()
            ),
            "grab_point_world": (
                self.grab_point_world.tolist()
            ),
        }


# ----------------------------------------------------------------------
# Field generation
# ----------------------------------------------------------------------

def spawn_debris_field(
    n=20,
    region_km=500.0,
    seed=None,
):
    """
    Generate deterministic debris objects.

    IMPORTANT:

    The generated positions are local offsets.

    main.py is responsible for transforming these offsets into
    inertial spacecraft-relative positions.
    """

    rng = np.random.default_rng(seed)

    field = []

    for _ in range(n):

        position = rng.uniform(
            -region_km,
            region_km,
            size=3,
        )

        velocity = rng.uniform(
            -0.05,
            0.05,
            size=3,
        )

        mass = rng.uniform(
            1.0,
            12.0,
        )

        size = rng.uniform(
            0.1,
            1.0,
        )

        debris = DebrisObject(
            position_km=position,
            velocity_km_s=velocity,
            mass_kg=mass,
            size_m=size,
            rng=rng,
        )

        field.append(
            debris
        )

    return field


# ----------------------------------------------------------------------
# Isolated test
# ----------------------------------------------------------------------

if __name__ == "__main__":

    debris = DebrisObject(
        position_km=[7000.0, 0.0, 0.0],
        velocity_km_s=[0.0, 7.5, 0.0],
        ang_vel_std_rad_s=0.2,
        rng=np.random.default_rng(42),
    )

    print(
        "Initial grab point:",
        debris.grab_point_world,
    )

    for t in range(5):

        debris.step(
            1.0
        )

        print(
            f"t={t + 1}s "
            f"position={debris.position_km} "
            f"rate={debris.tumbling_rate_rad_s:.4f}"
        )
