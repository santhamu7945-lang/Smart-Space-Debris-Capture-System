"""
solar_panel.py
Simple solar power generation model, feeding physics/power_budget.py.
"""

import numpy as np


class SolarPanel:
    """
    Parameters
    ----------
    area_m2 : float             total panel area
    efficiency : float          cell efficiency, 0-1
    solar_flux_w_m2 : float     incident flux (1361 W/m^2 at 1 AU nominal)
    """

    def __init__(self, area_m2=4.0, efficiency=0.29, solar_flux_w_m2=1361.0):
        self.area_m2 = area_m2
        self.efficiency = efficiency
        self.solar_flux_w_m2 = solar_flux_w_m2
        self.in_eclipse = False
        self.sun_incidence_angle_rad = 0.0  # 0 = panel normal to sun

    def available_power_w(self) -> float:
        """
        P = flux * area * efficiency * cos(incidence_angle), zero if in eclipse.
        """
        if self.in_eclipse:
            return 0.0
        cos_theta = max(0.0, np.cos(self.sun_incidence_angle_rad))
        return self.solar_flux_w_m2 * self.area_m2 * self.efficiency * cos_theta

    def set_eclipse(self, in_eclipse: bool):
        self.in_eclipse = in_eclipse

    def set_sun_incidence_angle(self, angle_rad: float):
        self.sun_incidence_angle_rad = angle_rad


if __name__ == "__main__":
    panel = SolarPanel()
    print("full sun, normal incidence:", panel.available_power_w(), "W")
    panel.set_sun_incidence_angle(np.pi / 4)
    print("45 deg incidence:", panel.available_power_w(), "W")
    panel.set_eclipse(True)
    print("in eclipse:", panel.available_power_w(), "W")
