import os
import json
import math
import random
from datetime import datetime, UTC

import pandas as pd
from skyfield.api import load, EarthSatellite

from multi_satellite_orbit import get_multi_satellite_state


# ============================================================
# PROJECT PATHS
# ============================================================

base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

gp_file = os.path.join(
    base_dir,
    "DATA",
    "raw",
    "multi_debris",
    "gp_data.csv"
)

output_folder = os.path.join(
    base_dir,
    "DATA",
    "processed"
)

output_file = os.path.join(
    output_folder,
    "multi_debris_state.json"
)

os.makedirs(output_folder, exist_ok=True)


# ============================================================
# CONSTANTS
# ============================================================

EARTH_RADIUS = 6378.137

EFFECTIVE_DENSITY_KG_M3 = {
    "R/B": 250,
    "PAYLOAD": 700,
    "DEB": 1800,
    "DEFAULT": 900
}


# ============================================================
# FEATURE ESTIMATION FUNCTIONS
# Same methodology as single-object system
# ============================================================

def estimate_size(name, norad_id):
    """
    Estimate object size based on object name/type.

    Same logic as the single-object system.
    """

    name = str(name).upper()

    if "R/B" in name or "ROCKET" in name:
        return 8.0

    if "PAYLOAD" in name:
        return 2.5

    if "DEB" in name:
        random.seed(int(norad_id))
        return round(
            random.uniform(0.10, 0.50),
            3
        )

    return 1.0


def estimate_rcs(size):
    """
    Estimate radar cross section from estimated size.
    """

    rcs = math.pi * (size / 2) ** 2 * 0.8

    return round(rcs, 3)


def classify_object_type(name):
    """
    Classify object based on object name.
    """

    name = str(name).upper()

    if "R/B" in name or "ROCKET" in name:
        return "R/B"

    if "PAYLOAD" in name:
        return "PAYLOAD"

    if "DEB" in name:
        return "DEB"

    return "DEFAULT"


def estimate_mass(size, object_type):
    """
    Estimate mass using sphere-equivalent volume
    and effective density.
    """

    radius = size / 2

    volume = (
        (4 / 3)
        * math.pi
        * radius ** 3
    )

    density = EFFECTIVE_DENSITY_KG_M3.get(
        object_type,
        EFFECTIVE_DENSITY_KG_M3["DEFAULT"]
    )

    mass = volume * density

    return round(mass, 4)


def estimate_tumbling_rate(
    size,
    relative_velocity
):
    """
    Estimate tumbling rate using the same
    methodology as the single-object system.
    """

    if size < 0.5:
        base_rate = random.uniform(1.0, 4.0)

    elif size < 2.0:
        base_rate = random.uniform(0.5, 3.0)

    else:
        base_rate = random.uniform(0.2, 2.0)

    velocity_factor = min(
        relative_velocity / 10.0,
        1.5
    )

    tumbling_rate = (
        base_rate
        * velocity_factor
    )

    return round(tumbling_rate, 2)


def estimate_roll(
    yaw,
    pitch,
    tumbling_rate
):
    """
    Estimate roll angle using the same
    engineering approximation as the
    single-object system.
    """

    roll = (
        0.45 * yaw
        + 0.25 * pitch
        + 3.5 * tumbling_rate
    )

    roll = (
        (roll + 180) % 360
    ) - 180

    return round(roll, 2)


def estimate_rotation_axis(
    vx,
    vy,
    vz
):
    """
    Use normalized velocity vector as
    engineering proxy for rotation axis.
    """

    magnitude = math.sqrt(
        vx ** 2
        + vy ** 2
        + vz ** 2
    )

    if magnitude == 0:
        return {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0
        }

    return {
        "x": round(vx / magnitude, 6),
        "y": round(vy / magnitude, 6),
        "z": round(vz / magnitude, 6)
    }


def calculate_collision_confidence(
    distance,
    relative_velocity,
    size
):
    """
    Same collision-confidence calculation
    used in the single-object system.
    """

    distance_score = (
        100
        * math.exp(
            -distance / 8000
        )
    )

    velocity_score = (
        100
        * math.exp(
            -relative_velocity / 8
        )
    )

    size_score = min(
        size * 12,
        100
    )

    confidence = (
        0.50 * distance_score
        + 0.30 * velocity_score
        + 0.20 * size_score
    )

    return round(
        confidence,
        2
    )


# ============================================================
# LOAD GP DATA
# ============================================================

print("=" * 60)
print("MULTI-DEBRIS FEATURE EXTRACTION")
print("=" * 60)

print("\nReading GP data:")

print(gp_file)

if not os.path.exists(gp_file):

    print("\nERROR:")
    print("gp_data.csv was not found.")

    raise SystemExit


gp_df = pd.read_csv(gp_file)

print(
    "\nTotal GP records:",
    len(gp_df)
)


# ============================================================
# CLEAN NORAD IDs
# ============================================================

gp_df["NORAD_CAT_ID"] = pd.to_numeric(
    gp_df["NORAD_CAT_ID"],
    errors="coerce"
)

gp_df = gp_df[
    gp_df["NORAD_CAT_ID"].notna()
].copy()

gp_df["NORAD_CAT_ID"] = (
    gp_df["NORAD_CAT_ID"]
    .astype(int)
)

print(
    "Valid GP records:",
    len(gp_df)
)


# ============================================================
# INITIALIZE SKYFIELD
# ============================================================

ts = load.timescale()

t = ts.now()


# ============================================================
# CAPTURE SATELLITE STATE
# ============================================================

capture_satellite = (
    get_multi_satellite_state()
)

capture_position = (
    capture_satellite["position"]
)

capture_velocity = (
    capture_satellite["velocity"]
)

print("\nCapture satellite state:")

print(
    "Position:",
    capture_position
)

print(
    "Velocity:",
    capture_velocity
)


# ============================================================
# PROCESS EVERY DEBRIS OBJECT
# ============================================================

all_objects = []

total = len(gp_df)

successful = 0
failed = 0


for index, row in gp_df.iterrows():

    try:

        # ----------------------------------------------------
        # BASIC INFORMATION
        # ----------------------------------------------------

        name = str(
            row["OBJECT_NAME"]
        ).strip()

        norad_id = int(
            row["NORAD_CAT_ID"]
        )

        object_id = str(
            norad_id
        )


        # ----------------------------------------------------
        # CREATE SKYFIELD SATELLITE
        #
        # GP CSV is modern OMM data.
        # Skyfield supports this through from_omm().
        # ----------------------------------------------------

        element_dict = {
            key: (
                "" if pd.isna(value)
                else str(value)
            )
            for key, value
            in row.to_dict().items()
        }

        satellite = EarthSatellite.from_omm(
            ts,
            element_dict
        )


        # ----------------------------------------------------
        # CALCULATE POSITION AND VELOCITY
        # ----------------------------------------------------

        geocentric = satellite.at(t)

        position = (
            geocentric.position.km
        )

        velocity = (
            geocentric.velocity.km_per_s
        )


        x = float(position[0])
        y = float(position[1])
        z = float(position[2])

        vx = float(velocity[0])
        vy = float(velocity[1])
        vz = float(velocity[2])


        # ----------------------------------------------------
        # CHECK FOR INVALID SGP4 RESULT
        # ----------------------------------------------------

        values = [
            x, y, z,
            vx, vy, vz
        ]

        if not all(
            math.isfinite(value)
            for value in values
        ):
            raise ValueError(
                "Invalid position/velocity returned by SGP4"
            )


        # ----------------------------------------------------
        # SPEED
        # ----------------------------------------------------

        speed = math.sqrt(
            vx ** 2
            + vy ** 2
            + vz ** 2
        )


        # ----------------------------------------------------
        # DISTANCE FROM EARTH CENTER
        # ----------------------------------------------------

        distance_from_earth = math.sqrt(
            x ** 2
            + y ** 2
            + z ** 2
        )


        # ----------------------------------------------------
        # ALTITUDE
        # Same method as single-object system
        # ----------------------------------------------------

        altitude = (
            distance_from_earth
            - EARTH_RADIUS
        )


        # ----------------------------------------------------
        # INCLINATION
        # ----------------------------------------------------

        inclination = float(
            row["INCLINATION"]
        )


        # ----------------------------------------------------
        # ORBIT CLASS
        # ----------------------------------------------------

        if altitude < 2000:

            orbit_class = "LEO"

        elif altitude < 35786:

            orbit_class = "MEO"

        else:

            orbit_class = "GEO"


        # ----------------------------------------------------
        # RELATIVE POSITION
        # ----------------------------------------------------

        relative_x = (
            x
            - capture_position["x"]
        )

        relative_y = (
            y
            - capture_position["y"]
        )

        relative_z = (
            z
            - capture_position["z"]
        )


        # ----------------------------------------------------
        # RELATIVE DISTANCE
        # ----------------------------------------------------

        relative_distance = math.sqrt(
            relative_x ** 2
            + relative_y ** 2
            + relative_z ** 2
        )


        # ----------------------------------------------------
        # RELATIVE VELOCITY
        # ----------------------------------------------------

        relative_vx = (
            vx
            - capture_velocity["vx"]
        )

        relative_vy = (
            vy
            - capture_velocity["vy"]
        )

        relative_vz = (
            vz
            - capture_velocity["vz"]
        )


        relative_velocity = math.sqrt(
            relative_vx ** 2
            + relative_vy ** 2
            + relative_vz ** 2
        )


        # ----------------------------------------------------
        # YAW
        # ----------------------------------------------------

        yaw = math.degrees(
            math.atan2(
                vy,
                vx
            )
        )


        # ----------------------------------------------------
        # PITCH
        # ----------------------------------------------------

        horizontal_velocity = math.sqrt(
            vx ** 2
            + vy ** 2
        )

        pitch = math.degrees(
            math.atan2(
                vz,
                horizontal_velocity
            )
        )


        # ----------------------------------------------------
        # OBJECT TYPE
        # ----------------------------------------------------

        object_type = (
            classify_object_type(name)
        )


        # ----------------------------------------------------
        # ESTIMATED SIZE
        # ----------------------------------------------------

        estimated_size = (
            estimate_size(
                name,
                norad_id
            )
        )


        # ----------------------------------------------------
        # ESTIMATED RCS
        # ----------------------------------------------------

        estimated_rcs = (
            estimate_rcs(
                estimated_size
            )
        )


        # ----------------------------------------------------
        # ESTIMATED MASS
        # ----------------------------------------------------

        estimated_mass = (
            estimate_mass(
                estimated_size,
                object_type
            )
        )


        # ----------------------------------------------------
        # TUMBLING RATE
        # ----------------------------------------------------

        tumbling_rate = (
            estimate_tumbling_rate(
                estimated_size,
                relative_velocity
            )
        )


        # ----------------------------------------------------
        # ROLL
        # ----------------------------------------------------

        roll = estimate_roll(
            yaw,
            pitch,
            tumbling_rate
        )


        # ----------------------------------------------------
        # ROTATION AXIS
        # ----------------------------------------------------

        rotation_axis = (
            estimate_rotation_axis(
                vx,
                vy,
                vz
            )
        )


        # ----------------------------------------------------
        # MOTION RATE
        # Same methodology as single-object system
        # ----------------------------------------------------

        if distance_from_earth > 0:

            motion_rate = math.degrees(
                speed
                / distance_from_earth
            )

        else:

            motion_rate = 0.0


        # ----------------------------------------------------
        # COLLISION CONFIDENCE
        # ----------------------------------------------------

        collision_confidence = (
            calculate_collision_confidence(
                relative_distance,
                relative_velocity,
                estimated_size
            )
        )


        # ----------------------------------------------------
        # TRACKING ID
        # ----------------------------------------------------

        tracking_id = (
            f"TRK_{norad_id}_"
            f"{index + 1:06d}"
        )


        # ----------------------------------------------------
        # TIMESTAMP
        # ----------------------------------------------------

        timestamp = (
            datetime.now(UTC)
            .isoformat()
        )


        # ----------------------------------------------------
        # FINAL OBJECT
        # ----------------------------------------------------

        debris_object = {

            "tracking_id":
                tracking_id,

            "object_id":
                object_id,

            "name":
                name,

            "position": {

                "x":
                    round(x, 3),

                "y":
                    round(y, 3),

                "z":
                    round(z, 3)
            },

            "velocity": {

                "vx":
                    round(vx, 6),

                "vy":
                    round(vy, 6),

                "vz":
                    round(vz, 6)
            },

            "speed":
                round(speed, 4),

            "altitude":
                round(altitude, 3),

            "inclination":
                round(inclination, 4),

            "orbit_class":
                orbit_class,

            "relative_distance":
                round(
                    relative_distance,
                    3
                ),

            "relative_velocity":
                round(
                    relative_velocity,
                    5
                ),

            "orientation": {

                "roll":
                    roll,

                "pitch":
                    round(
                        pitch,
                        2
                    ),

                "yaw":
                    round(
                        yaw,
                        2
                    )
            },

            "rotation_axis":
                rotation_axis,

            "estimated_size_m":
                estimated_size,

            "estimated_rcs_m2":
                estimated_rcs,

            "object_type":
                object_type,

            "estimated_mass_kg":
                estimated_mass,

            "motion_rate":
                round(
                    motion_rate,
                    6
                ),

            "tumbling_rate":
                tumbling_rate,

            "collision_confidence":
                collision_confidence,

            "timestamp":
                timestamp
        }


        all_objects.append(
            debris_object
        )

        successful += 1


    except Exception as error:

        failed += 1

        print(
            f"\nFailed object "
            f"{index + 1}/{total}"
        )

        print(
            "NORAD:",
            row.get(
                "NORAD_CAT_ID",
                "Unknown"
            )
        )

        print(
            "Name:",
            row.get(
                "OBJECT_NAME",
                "Unknown"
            )
        )

        print(
            "Error:",
            error
        )


    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    if (
        (index + 1) % 500 == 0
        or index + 1 == total
    ):

        print(
            f"\nProgress: "
            f"{index + 1}/{total}"
        )

        print(
            "Successful:",
            successful
        )

        print(
            "Failed:",
            failed
        )


# ============================================================
# SAVE JSON
# ============================================================

with open(
    output_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        all_objects,
        file,
        indent=4
    )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n")
print("=" * 60)
print("MULTI-DEBRIS FEATURE EXTRACTION COMPLETED")
print("=" * 60)

print(
    "Total GP objects:",
    total
)

print(
    "Successfully processed:",
    successful
)

print(
    "Failed:",
    failed
)

print(
    "Total objects saved:",
    len(all_objects)
)

print("\nOutput file:")

print(output_file)

print("\n")
print("All available features were generated.")
print("=" * 60)