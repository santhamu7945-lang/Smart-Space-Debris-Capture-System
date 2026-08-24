import math
from datetime import datetime, UTC

# ---------------------------------------
# Earth Constants
# ---------------------------------------

EARTH_RADIUS = 6378.137          # km
EARTH_MU = 398600.4418           # km^3/s^2

# ---------------------------------------
# Mission Parameters
# ---------------------------------------

ALTITUDE = 800.0                 # km
INCLINATION = 74.0               # degrees

# ---------------------------------------
# Function to Generate Capture Satellite State
# ---------------------------------------

def get_satellite_state():

    # ---------------------------------------
    # Current UTC Time
    # ---------------------------------------

    now = datetime.now(UTC)

    # Seconds since midnight
    seconds = (
        now.hour * 3600 +
        now.minute * 60 +
        now.second +
        now.microsecond / 1_000_000
    )

    # ---------------------------------------
    # Orbit Radius
    # ---------------------------------------

    orbit_radius = EARTH_RADIUS + ALTITUDE

    # ---------------------------------------
    # Orbital Speed
    # v = sqrt(mu / r)
    # ---------------------------------------

    orbital_speed = math.sqrt(EARTH_MU / orbit_radius)

    # ---------------------------------------
    # Orbital Period
    # ---------------------------------------

    orbital_period = (
        2 * math.pi * orbit_radius
    ) / orbital_speed

    # ---------------------------------------
    # Orbit Angle
    # ---------------------------------------

    theta = (
        2 * math.pi * seconds
    ) / orbital_period

    # Keep angle between 0 and 2π
    theta = theta % (2 * math.pi)

    # ---------------------------------------
    # Inclination
    # ---------------------------------------

    inclination_rad = math.radians(INCLINATION)

    # ---------------------------------------
    # Position (km)
    # ---------------------------------------

    x = orbit_radius * math.cos(theta)

    y = (
        orbit_radius *
        math.sin(theta) *
        math.cos(inclination_rad)
    )

    z = (
        orbit_radius *
        math.sin(theta) *
        math.sin(inclination_rad)
    )

    # ---------------------------------------
    # Velocity (km/s)
    # ---------------------------------------

    vx = -orbital_speed * math.sin(theta)

    vy = (
        orbital_speed *
        math.cos(theta) *
        math.cos(inclination_rad)
    )

    vz = (
        orbital_speed *
        math.cos(theta) *
        math.sin(inclination_rad)
    )

    # ---------------------------------------
    # Return Satellite State
    # ---------------------------------------

    satellite_state = {

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

    return satellite_state


# ---------------------------------------
# Test
# ---------------------------------------

if __name__ == "__main__":

    state = get_satellite_state()

    print("\n---------------------------------------")
    print("Simulated Capture Satellite State")
    print("---------------------------------------\n")

    print("Position (km)")
    print(state["position"])

    print("\nVelocity (km/s)")
    print(state["velocity"])