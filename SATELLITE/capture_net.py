"""
capture_net.py
Net-based capture mechanism (alternative/complementary to robotic_arm.py
for grabbing debris). On a successful capture, registers the event with
storage_drum.py and applies its own mechanism wear (Challenge 12).
"""

import numpy as np


class CaptureNet:
    def __init__(self, deploy_radius_m=1.0, success_probability_base=0.85, wear_per_use=0.6):
        self.deploy_radius_m = deploy_radius_m
        self.success_probability_base = success_probability_base
        self.wear_per_use = wear_per_use
        self.mechanism_health = 100.0
        self.servicing_needed = False

    def attempt_capture(self, debris_offset_m, debris_tumbling_rate_rad_s, storage_drum,
                         debris_mass_kg, gnc=None, rng=None):
        """
        Attempt to net-capture a debris object at `debris_offset_m` relative
        to the net. Success probability drops with distance from center and
        with higher tumbling rate. On success, registers with storage_drum.
        """
        rng = rng or np.random.default_rng()
        offset_norm = float(np.linalg.norm(debris_offset_m))

        if offset_norm > self.deploy_radius_m:
            self._register_use()
            return {"success": False, "reason": "out_of_deploy_radius"}

        # tumbling debris is harder to net cleanly
        tumble_penalty = min(0.5, debris_tumbling_rate_rad_s * 0.5)
        distance_penalty = (offset_norm / self.deploy_radius_m) * 0.3
        p_success = max(0.0, self.success_probability_base - tumble_penalty - distance_penalty)

        self._register_use()
        success = rng.random() < p_success

        if success:
            if storage_drum.storage_full:
                return {"success": False, "reason": "storage_full", "p_success": p_success}
            if storage_drum.total_stored_mass_kg + debris_mass_kg > storage_drum.capacity_kg:
                return {"success": False, "reason": "would_exceed_capacity", "p_success": p_success}
            storage_drum.capture(debris_mass_kg, debris_offset_m, gnc=gnc)

        return {"success": success, "p_success": p_success}

    def _register_use(self):
        self.mechanism_health = max(0.0, self.mechanism_health - self.wear_per_use)
        if self.mechanism_health < 20.0:
            self.servicing_needed = True


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__)))
    from storage_drum import StorageDrum

    drum = StorageDrum(capacity_kg=100.0)
    net = CaptureNet()
    rng = np.random.default_rng(1)

    for i in range(5):
        result = net.attempt_capture([0.2, 0.1, 0.0], debris_tumbling_rate_rad_s=0.1,
                                      storage_drum=drum, debris_mass_kg=8.0, rng=rng)
        print(f"attempt {i+1}:", result, "| health:", net.mechanism_health)
    print("drum state:", drum.to_dict())
