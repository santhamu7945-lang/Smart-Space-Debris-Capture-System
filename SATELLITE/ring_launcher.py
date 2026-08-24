"""
ring_launcher.py
Launches a capture ring/tether at debris within range. Same wear-tracking
pattern as robotic_arm.py and capture_net.py (Challenge 12).
"""

import numpy as np


class RingLauncher:
    def __init__(self, max_range_m=3.0, launch_speed_m_s=2.0, wear_per_use=0.5):
        self.max_range_m = max_range_m
        self.launch_speed_m_s = launch_speed_m_s
        self.wear_per_use = wear_per_use
        self.mechanism_health = 100.0
        self.servicing_needed = False

    def time_to_target(self, offset_m) -> float:
        dist = float(np.linalg.norm(offset_m))
        if dist > self.max_range_m:
            return float("inf")
        return dist / self.launch_speed_m_s

    def launch(self, debris_offset_m, storage_drum, debris_mass_kg, gnc=None):
        """Fire the ring at a stationary intercept point. Assumes upstream
        capture-window logic (robotic_arm.compute_capture_window /
        equivalent) already confirmed a good moment to fire."""
        dist = float(np.linalg.norm(debris_offset_m))
        self._register_use()

        if dist > self.max_range_m:
            return {"success": False, "reason": "out_of_range"}
        if storage_drum.storage_full:
            return {"success": False, "reason": "storage_full"}

        storage_drum.capture(debris_mass_kg, debris_offset_m, gnc=gnc)
        return {"success": True, "flight_time_s": self.time_to_target(debris_offset_m)}

    def _register_use(self):
        self.mechanism_health = max(0.0, self.mechanism_health - self.wear_per_use)
        if self.mechanism_health < 20.0:
            self.servicing_needed = True


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.dirname(__file__))
    from storage_drum import StorageDrum

    drum = StorageDrum(capacity_kg=100.0)
    launcher = RingLauncher()
    print(launcher.launch([1.0, 0.5, 0.0], drum, debris_mass_kg=6.0))
    print(launcher.launch([5.0, 0.0, 0.0], drum, debris_mass_kg=6.0))  # out of range
    print("health:", launcher.mechanism_health)
