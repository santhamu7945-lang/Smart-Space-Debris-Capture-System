"""
debris.py
Simulated debris objects: orbital state + tumbling (rotational) motion.

Solves Challenge 3 (simulation side): each debris object gets a random
angular velocity at spawn and its orientation is updated every timestep
using the Rodrigues rotation formula so it visibly tumbles.
"""

import numpy as np
import uuid


def rodrigues_rotate(vector: np.ndarray, axis: np.ndarray, angle_rad: float) -> np.ndarray:
    """
    Rotate `vector` about unit `axis` by `angle_rad` using the Rodrigues
    rotation formula:
        v_rot = v*cos(theta) + (k x v)*sin(theta) + k*(k.v)*(1-cos(theta))
    """
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    v = vector
    k = axis
    cos_t = np.cos(angle_rad)
    sin_t = np.sin(angle_rad)
    return (v * cos_t
            + np.cross(k, v) * sin_t
            + k * np.dot(k, v) * (1.0 - cos_t))


class DebrisObject:
    """
    A single tracked piece of debris.

    Parameters
    ----------
    position_km : np.ndarray(3,)      inertial frame position
    velocity_km_s : np.ndarray(3,)    inertial frame velocity
    mass_kg : float
    size_m : float                    characteristic dimension, used for
                                       radar/camera cross-section & arm reach checks
    ang_vel_std_rad_s : float         std-dev used to draw random spin rate at spawn
    """

    def __init__(self, position_km, velocity_km_s, mass_kg=5.0, size_m=0.3,
                 ang_vel_std_rad_s=0.05, debris_id=None):
        self.id = debris_id or str(uuid.uuid4())[:8]
        self.position_km = np.array(position_km, dtype=float)
        self.velocity_km_s = np.array(velocity_km_s, dtype=float)
        self.mass_kg = mass_kg
        self.size_m = size_m

        # --- Challenge 3: random spin axis + rate at spawn ---
        self.angular_velocity_rad_s = np.random.uniform(
            -ang_vel_std_rad_s, ang_vel_std_rad_s, size=3
        )
        # body-fixed reference vector (e.g. the "grab point" direction),
        # rotated every step to track current orientation
        self.orientation_vector = np.array([1.0, 0.0, 0.0])

        # a fixed marker on the body representing the preferred grab point
        self.grab_point_body = np.array([0.0, 0.0, 1.0]) * (size_m / 2.0)
        self.grab_point_world = self.grab_point_body.copy()

    @property
    def tumbling_rate_rad_s(self) -> float:
        """Scalar spin rate, magnitude of angular velocity vector."""
        return float(np.linalg.norm(self.angular_velocity_rad_s))

    @property
    def rotation_axis(self) -> np.ndarray:
        """Unit vector of the current rotation axis."""
        norm = np.linalg.norm(self.angular_velocity_rad_s)
        if norm < 1e-9:
            return np.array([0.0, 0.0, 1.0])
        return self.angular_velocity_rad_s / norm

    def step_orbit(self, dt_s: float):
        """Straight-line propagation placeholder; real propagation should
        call orbit.kepler / orbit.relative_motion instead of this for
        anything beyond a quick local test."""
        self.position_km += self.velocity_km_s * dt_s

    def step_rotation(self, dt_s: float):
        """Advance orientation & grab point by Rodrigues rotation."""
        rate = self.tumbling_rate_rad_s
        if rate < 1e-9:
            return
        angle = rate * dt_s
        axis = self.rotation_axis
        # rotate incrementally from CURRENT world orientation, not the body
        # reference, so successive steps accumulate rotation correctly
        self.orientation_vector = rodrigues_rotate(self.orientation_vector, axis, angle)
        self.grab_point_world = rodrigues_rotate(self.grab_point_world, axis, angle)

    def step(self, dt_s: float):
        self.step_orbit(dt_s)
        self.step_rotation(dt_s)

    def to_dict(self):
        return {
            "id": self.id,
            "position_km": self.position_km.tolist(),
            "velocity_km_s": self.velocity_km_s.tolist(),
            "mass_kg": self.mass_kg,
            "size_m": self.size_m,
            "tumbling_rate_rad_s": self.tumbling_rate_rad_s,
            "rotation_axis": self.rotation_axis.tolist(),
            "grab_point_world": self.grab_point_world.tolist(),
        }


def spawn_debris_field(n=20, region_km=500.0, seed=None):
    """Convenience factory for a randomized debris field."""
    rng = np.random.default_rng(seed)
    field = []
    for _ in range(n):
        pos = rng.uniform(-region_km, region_km, size=3)
        vel = rng.uniform(-0.05, 0.05, size=3)  # km/s
        mass = rng.uniform(1.0, 12.0)
        size = rng.uniform(0.1, 1.0)
        field.append(DebrisObject(pos, vel, mass_kg=mass, size_m=size))
    return field


if __name__ == "__main__":
    # Quick isolated tumbling test (Challenge 3 test step)
    d = DebrisObject([0, 0, 0], [0, 0, 0], ang_vel_std_rad_s=0.2)
    print("initial grab point:", d.grab_point_world)
    for t in range(5):
        d.step_rotation(1.0)
        print(f"t={t+1}s  grab_point={d.grab_point_world}  rate={d.tumbling_rate_rad_s:.4f} rad/s")
