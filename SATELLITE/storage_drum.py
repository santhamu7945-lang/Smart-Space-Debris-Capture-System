"""
storage_drum.py
Tracks captured-debris storage and recomputes spacecraft mass/CoM/inertia
after each successful capture, pushing the update into physics/gnc.py so
control response visibly changes.

Solves Challenge 7 (storage management / mass-CoM changes).
"""

import numpy as np


class StorageDrum:
    """
    Parameters
    ----------
    capacity_kg : float               max total stored mass
    spacecraft_dry_mass_kg : float    spacecraft mass excluding captured debris
    spacecraft_dry_com_m : array(3,)  spacecraft CoM excluding captured debris (body frame)
    spacecraft_dry_inertia_kg_m2 : array(3,3)  base inertia tensor
    """

    def __init__(self, capacity_kg=200.0,
                 spacecraft_dry_mass_kg=500.0,
                 spacecraft_dry_com_m=None,
                 spacecraft_dry_inertia_kg_m2=None):
        self.capacity_kg = capacity_kg
        self.total_stored_mass_kg = 0.0
        self.current_capacity_used = 0.0   # fraction 0-1
        self.storage_full = False

        self.dry_mass_kg = spacecraft_dry_mass_kg
        self.dry_com_m = (np.array(spacecraft_dry_com_m, dtype=float)
                           if spacecraft_dry_com_m is not None else np.zeros(3))
        self.dry_inertia = (np.array(spacecraft_dry_inertia_kg_m2, dtype=float)
                             if spacecraft_dry_inertia_kg_m2 is not None else np.eye(3) * 50.0)

        self.captured_items = []  # list of {mass_kg, position_m}
        # current live properties (start equal to dry properties)
        self.total_mass_kg = self.dry_mass_kg
        self.center_of_mass_m = self.dry_com_m.copy()
        self.inertia_kg_m2 = self.dry_inertia.copy()

    def capture(self, debris_mass_kg, debris_position_body_m, gnc=None):
        """
        Register a successful capture (called from capture_net.py or
        robotic_arm.py on success), recompute mass properties, push the
        new inertia into gnc (SpacecraftAttitude) if provided.
        """
        if self.total_stored_mass_kg + debris_mass_kg > self.capacity_kg:
            raise ValueError("Capture would exceed storage capacity — check storage_full first.")

        self.captured_items.append({
            "mass_kg": debris_mass_kg,
            "position_m": np.array(debris_position_body_m, dtype=float),
        })
        self.total_stored_mass_kg += debris_mass_kg
        self.current_capacity_used = self.total_stored_mass_kg / self.capacity_kg
        self.storage_full = self.current_capacity_used >= 1.0

        self.update_mass_properties()

        if gnc is not None:
            gnc.update_inertia_properties(self.inertia_kg_m2)

    def update_mass_properties(self):
        """Recompute total_mass, CoM (weighted average), and inertia tensor
        (parallel axis theorem) from dry spacecraft + all captured items."""
        total_mass = self.dry_mass_kg + self.total_stored_mass_kg

        # weighted-average CoM
        weighted_com = self.dry_mass_kg * self.dry_com_m
        for item in self.captured_items:
            weighted_com += item["mass_kg"] * item["position_m"]
        new_com = weighted_com / total_mass

        # parallel axis theorem: I_new = I_dry_shifted + sum(I_item_shifted)
        new_inertia = self._shift_inertia(self.dry_inertia, self.dry_mass_kg,
                                           self.dry_com_m, new_com)
        for item in self.captured_items:
            # treat each captured item as a point mass: I_point = 0 about its own CoM
            item_inertia = np.zeros((3, 3))
            new_inertia += self._shift_inertia(item_inertia, item["mass_kg"],
                                                item["position_m"], new_com)

        self.total_mass_kg = total_mass
        self.center_of_mass_m = new_com
        self.inertia_kg_m2 = new_inertia

    @staticmethod
    def _shift_inertia(I_about_own_com, mass_kg, own_com_m, new_com_m):
        """Parallel axis theorem: I_new = I_own + m * (d^2 * Identity - outer(d,d))
        where d = own_com - new_com."""
        d = np.array(own_com_m, dtype=float) - np.array(new_com_m, dtype=float)
        d_outer = np.outer(d, d)
        shift = mass_kg * (np.dot(d, d) * np.eye(3) - d_outer)
        return I_about_own_com + shift

    def to_dict(self):
        return {
            "total_stored_mass_kg": self.total_stored_mass_kg,
            "current_capacity_used": self.current_capacity_used,
            "storage_full": self.storage_full,
            "total_mass_kg": self.total_mass_kg,
            "center_of_mass_m": self.center_of_mass_m.tolist(),
        }


if __name__ == "__main__":
    drum = StorageDrum(capacity_kg=50.0, spacecraft_dry_mass_kg=400.0)

    print("initial:", drum.to_dict())
    for i, (m, pos) in enumerate([(10, [0.5, 0.2, 0.0]), (15, [-0.3, 0.4, 0.1]), (20, [0.1, -0.5, 0.2])]):
        try:
            drum.capture(m, pos)
            print(f"after capture {i+1}:", drum.to_dict())
        except ValueError as e:
            print(f"capture {i+1} rejected:", e)
