"""
power_budget.py
Tracks available power (from satellite.solar_panel) vs power draw of
concurrent operations, and blocks simultaneous high-draw operations that
would exceed the available budget.

Solves Challenge 11 (power/energy budget).
"""

# Typical draw values (watts) — tune per your actual hardware assumptions
OPERATION_DRAW_W = {
    "thruster_burn": 150.0,
    "arm_movement": 80.0,
    "lidar_active_scan": 40.0,
    "camera_capture": 5.0,
    "communications": 20.0,
    "idle_bus": 15.0,   # baseline housekeeping load, always on
}


class PowerBudget:
    def __init__(self, solar_panel):
        """
        solar_panel : object with .available_power_w() -> float
                      (see satellite/solar_panel.py)
        """
        self.solar_panel = solar_panel
        self.active_operations = set()

    @property
    def current_draw_w(self) -> float:
        draw = OPERATION_DRAW_W["idle_bus"]
        for op in self.active_operations:
            draw += OPERATION_DRAW_W.get(op, 0.0)
        return draw

    def can_start(self, operation: str) -> bool:
        """Check whether starting `operation` would exceed available power."""
        projected_draw = self.current_draw_w + OPERATION_DRAW_W.get(operation, 0.0)
        return projected_draw <= self.solar_panel.available_power_w()

    def start(self, operation: str) -> bool:
        """Attempt to start an operation. Returns False (and does nothing)
        if it would exceed the power budget -- caller (mission_manager.py
        or gnc.py) should not proceed with that action this cycle."""
        if operation not in OPERATION_DRAW_W:
            raise ValueError(f"Unknown operation '{operation}'")
        if not self.can_start(operation):
            return False
        self.active_operations.add(operation)
        return True

    def stop(self, operation: str):
        self.active_operations.discard(operation)

    def status(self):
        return {
            "available_power_w": self.solar_panel.available_power_w(),
            "current_draw_w": self.current_draw_w,
            "active_operations": sorted(self.active_operations),
        }


if __name__ == "__main__":
    class DummyPanel:
        def available_power_w(self):
            return 200.0

    pb = PowerBudget(DummyPanel())
    print("start thruster_burn:", pb.start("thruster_burn"))     # True, 150+15=165 <= 200
    print("start arm_movement:", pb.start("arm_movement"))         # False, 165+80=245 > 200
    print(pb.status())
    pb.stop("thruster_burn")
    print("start arm_movement after stopping thruster:", pb.start("arm_movement"))  # True
    print(pb.status())
