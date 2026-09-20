import math
from datetime import datetime, UTC


# =========================================================
# EARTH CONSTANTS
# =========================================================

EARTH_RADIUS = 6378.137       # km
EARTH_MU = 398600.4418        # km^3/s^2


# =========================================================
# MISSION PARAMETERS
# =========================================================

ALTITUDE = 800.0              # km
INCLINATION = 74.0             # degrees


# =========================================================
# CAPTURE SATELLITE STATE
# =========================================================

def get_multi_satellite_state():

    # -----------------------------------------------------
    # Current UTC time
    # -----------------------------------------------------

    now = datetime.now(UTC)

    seconds = (
        now.hour * 3600
        + now.minute * 60
        + now.second
        + now.microsecond / 1_000_000
    )


    # -----------------------------------------------------
    # Orbit radius
    # -----------------------------------------------------

    orbit_radius = EARTH_RADIUS + ALTITUDE


    # -----------------------------------------------------
    # Orbital speed
    # -----------------------------------------------------

    orbital_speed = math.sqrt(
        EARTH_MU / orbit_radius
    )


    # -----------------------------------------------------
    # Orbital period
    # -----------------------------------------------------

    orbital_period = (
        2 * math.pi * orbit_radius
    ) / orbital_speed


    # -----------------------------------------------------
    # Orbit angle
    # -----------------------------------------------------

    theta = (
        2 * math.pi * seconds
    ) / orbital_period

    theta = theta % (2 * math.pi)


    # -----------------------------------------------------
    # Inclination
    # -----------------------------------------------------

    inclination_rad = math.radians(
        INCLINATION
    )


    # -----------------------------------------------------
    # Position
    # -----------------------------------------------------

    x = (
        orbit_radius
        * math.cos(theta)
    )

    y = (
        orbit_radius
        * math.sin(theta)
        * math.cos(inclination_rad)
    )

    z = (
        orbit_radius
        * math.sin(theta)
        * math.sin(inclination_rad)
    )


    # -----------------------------------------------------
    # Velocity
    # -----------------------------------------------------

    vx = (
        -orbital_speed
        * math.sin(theta)
    )

    vy = (
        orbital_speed
        * math.cos(theta)
        * math.cos(inclination_rad)
    )

    vz = (
        orbital_speed
        * math.cos(theta)
        * math.sin(inclination_rad)
    )


    # -----------------------------------------------------
    # Return state
    # -----------------------------------------------------

    return {

        "position": {

            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3)

        },

        "velocity": {

            "vx": round(vx, 6),
            "vy": round(vy, 6),
            "vz": round(vz, 6)

        }

    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    state = get_multi_satellite_state()

    print("\n========================================")
    print("Multi-Debris Capture Satellite State")
    print("========================================\n")

    print("Position (km)")
    print(state["position"])

    print("\nVelocity (km/s)")
    print(state["velocity"])

    print("\n========================================")