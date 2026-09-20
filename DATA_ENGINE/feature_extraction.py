import os
import json
import math
import random
from datetime import datetime, UTC

from skyfield.api import EarthSatellite, load
from satellite_orbit import get_satellite_state


# =====================================================
# PROJECT PATHS
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "DATA",
    "processed",
    "clean_debris.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "DATA",
    "processed",
    "debris_state.json"
)

EARTH_RADIUS = 6378.137  # km


# =====================================================
# LOAD DATASET
# =====================================================

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    debris_data = json.load(f)

print(f"Loaded {len(debris_data)} debris objects")


# =====================================================
# LOAD SKYFIELD
# =====================================================

ts = load.timescale()
t = ts.now()

print("Skyfield Loaded Successfully")


# =====================================================
# LOAD CAPTURE SATELLITE
# =====================================================

capture_sat = get_satellite_state()

sat_pos = capture_sat["position"]
sat_vel = capture_sat["velocity"]

print("\nCapture Satellite Loaded")
print("Position :", sat_pos)
print("Velocity :", sat_vel)


# =====================================================
# OUTPUT CONTAINER
# =====================================================

feature_data = []
tracking_counter = 1


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def estimate_size(name, norad_id):
    """
    Estimate debris size in meters.
    """

    name = name.upper()

    if "R/B" in name or "ROCKET" in name:
        return 8.0

    elif "PAYLOAD" in name:
        return 2.5

    elif "DEB" in name:
        random.seed(int(norad_id))
        return round(random.uniform(0.10, 0.50), 2)

    else:
        return 1.0


def estimate_rcs(size):
    """
    Estimate Radar Cross Section (m²).
    """

    radius = size / 2

    return round(
        math.pi * radius * radius * 0.8,
        3
    )


# =====================================================
# MASS ESTIMATION
# =====================================================

# ENGINEERING ASSUMPTION:
# True mass cannot be derived from tracking data (TLE) alone.
# Mass is estimated using a sphere-equivalent volume proxy
# and type-dependent effective density.
#
# These values are engineering assumptions for the
# student-project level and are not measured constants.

EFFECTIVE_DENSITY_KG_M3 = {

    "R/B": 250.0,

    "PAYLOAD": 700.0,

    "DEB": 1800.0,

    "DEFAULT": 900.0

}


def classify_object_type(name):

    name = name.upper()

    if "R/B" in name or "ROCKET" in name:

        return "R/B"

    elif "PAYLOAD" in name:

        return "PAYLOAD"

    elif "DEB" in name:

        return "DEB"

    else:

        return "DEFAULT"


def estimate_mass(size, object_type):
    """
    Estimate mass in kg using a sphere-equivalent
    volume proxy with type-dependent density.
    """

    if size is None or size <= 0:

        return 0.0

    density = EFFECTIVE_DENSITY_KG_M3.get(
        object_type,
        EFFECTIVE_DENSITY_KG_M3["DEFAULT"]
    )

    radius = size / 2

    volume = (
        (4.0 / 3.0)
        * math.pi
        * (radius ** 3)
    )

    return round(
        density * volume,
        4
    )


# =====================================================
# TUMBLING RATE
# =====================================================

def estimate_tumbling_rate(
    size,
    relative_velocity
):
    """
    Estimated tumbling rate (deg/sec).

    This is an engineering estimate.
    """

    if size <= 0.20:

        base = random.uniform(
            8.0,
            15.0
        )

    elif size <= 0.50:

        base = random.uniform(
            4.0,
            8.0
        )

    elif size <= 2.0:

        base = random.uniform(
            1.0,
            3.0
        )

    else:

        base = random.uniform(
            0.2,
            1.0
        )

    velocity_factor = min(
        relative_velocity / 10.0,
        1.5
    )

    return round(
        base * velocity_factor,
        2
    )


# =====================================================
# ESTIMATED ROLL
# =====================================================

def estimate_roll(
    yaw,
    pitch,
    tumbling_rate
):
    """
    Estimated roll angle.

    Since TLE does not contain roll,
    we estimate it for robotic-arm alignment.
    """

    roll = (

        0.45 * yaw +

        0.25 * pitch +

        3.5 * tumbling_rate

    )

    while roll > 180:

        roll -= 360

    while roll < -180:

        roll += 360

    return round(
        roll,
        2
    )


# =====================================================
# ROTATION AXIS ESTIMATION
# =====================================================

def estimate_rotation_axis(
    vx,
    vy,
    vz
):
    """
    Estimate rotation-axis direction.

    TLE data does not contain the actual attitude
    or physical spin-axis measurement.

    Therefore, the normalized velocity direction
    is used as an engineering proxy for the rotation
    axis.

    The returned vector is normalized.
    """

    magnitude = math.sqrt(

        vx**2 +

        vy**2 +

        vz**2

    )

    if magnitude == 0:

        return {

            "x": 0.0,

            "y": 0.0,

            "z": 0.0

        }

    return {

        "x": round(
            vx / magnitude,
            6
        ),

        "y": round(
            vy / magnitude,
            6
        ),

        "z": round(
            vz / magnitude,
            6
        )

    }


# =====================================================
# COLLISION CONFIDENCE
# =====================================================

def calculate_collision_confidence(
    distance,
    relative_velocity,
    size
):
    """
    Collision confidence (0-100).

    Represents collision risk.

    Higher score means closer distance,
    higher relative velocity and/or larger object.
    """

    distance_score = max(

        0,

        100 * math.exp(
            -distance / 8000
        )

    )

    velocity_score = max(

        0,

        100 * math.exp(
            -relative_velocity / 8
        )

    )

    size_score = min(
        size * 12,
        100
    )

    confidence = (

        0.50 * distance_score +

        0.30 * velocity_score +

        0.20 * size_score

    )

    return round(
        confidence,
        2
    )


# =====================================================
# START FEATURE EXTRACTION LOOP
# =====================================================

for obj in debris_data:

    try:

        # =================================================
        # CREATE SKYFIELD SATELLITE
        # =================================================

        satellite = EarthSatellite(

            obj["line1"],

            obj["line2"],

            obj["name"],

            ts

        )

        # =================================================
        # CALCULATE POSITION AND VELOCITY
        # =================================================

        geocentric = satellite.at(t)

        x, y, z = geocentric.position.km

        vx, vy, vz = (
            geocentric.velocity.km_per_s
        )


        # =================================================
        # BASIC ORBIT PARAMETERS
        # =================================================

        speed = math.sqrt(

            vx**2 +

            vy**2 +

            vz**2

        )

        distance_from_earth = math.sqrt(

            x**2 +

            y**2 +

            z**2

        )

        altitude = (

            distance_from_earth -

            EARTH_RADIUS

        )

        inclination = float(

            obj["line2"].split()[2]

        )


        # =================================================
        # ORBIT CLASS
        # =================================================

        if altitude < 2000:

            orbit_class = "LEO"

        elif altitude < 35786:

            orbit_class = "MEO"

        else:

            orbit_class = "GEO"


        # =================================================
        # RELATIVE DISTANCE
        # =================================================

        relative_distance = math.sqrt(

            (x - sat_pos["x"])**2 +

            (y - sat_pos["y"])**2 +

            (z - sat_pos["z"])**2

        )


        # =================================================
        # RELATIVE VELOCITY
        # =================================================

        relative_velocity = math.sqrt(

            (vx - sat_vel["vx"])**2 +

            (vy - sat_vel["vy"])**2 +

            (vz - sat_vel["vz"])**2

        )


        # =================================================
        # ORIENTATION
        # =================================================

        yaw = math.degrees(

            math.atan2(
                vy,
                vx
            )

        )

        horizontal_velocity = math.sqrt(

            vx**2 +

            vy**2

        )

        pitch = math.degrees(

            math.atan2(

                vz,

                horizontal_velocity

            )

        )


        # =================================================
        # ESTIMATED PARAMETERS
        # =================================================

        estimated_size = estimate_size(

            obj["name"],

            obj["norad_id"]

        )

        estimated_rcs = estimate_rcs(

            estimated_size

        )

        object_type = classify_object_type(

            obj["name"]

        )

        estimated_mass = estimate_mass(

            estimated_size,

            object_type

        )

        tumbling_rate = estimate_tumbling_rate(

            estimated_size,

            relative_velocity

        )

        roll = estimate_roll(

            yaw,

            pitch,

            tumbling_rate

        )


        # =================================================
        # ROTATION AXIS
        # =================================================

        rotation_axis = estimate_rotation_axis(

            vx,

            vy,

            vz

        )


        # =================================================
        # MOTION RATE
        # =================================================

        motion_rate = round(

            math.degrees(

                speed /

                distance_from_earth

            ),

            6

        )


        # =================================================
        # COLLISION CONFIDENCE
        # =================================================

        confidence = calculate_collision_confidence(

            relative_distance,

            relative_velocity,

            estimated_size

        )


        # =================================================
        # TRACKING ID
        # =================================================

        tracking_id = (

            f"TRK_{obj['norad_id']}_"
            f"{tracking_counter:06d}"

        )

        tracking_counter += 1


        # =================================================
        # TIMESTAMP
        # =================================================

        timestamp = datetime.now(
            UTC
        ).isoformat()


        # =================================================
        # STORE FEATURES
        # =================================================

        feature_data.append({

            "tracking_id": tracking_id,

            "object_id": obj["norad_id"],

            "name": obj["name"],


            # -------------------------------
            # POSITION
            # -------------------------------

            "position": {

                "x": round(x, 3),

                "y": round(y, 3),

                "z": round(z, 3)

            },


            # -------------------------------
            # VELOCITY
            # -------------------------------

            "velocity": {

                "vx": round(vx, 6),

                "vy": round(vy, 6),

                "vz": round(vz, 6)

            },


            # -------------------------------
            # BASIC PARAMETERS
            # -------------------------------

            "speed": round(
                speed,
                6
            ),

            "altitude": round(
                altitude,
                3
            ),

            "inclination": round(
                inclination,
                4
            ),

            "orbit_class": orbit_class,


            # -------------------------------
            # RELATIVE MOTION
            # -------------------------------

            "relative_distance": round(

                relative_distance,

                3

            ),

            "relative_velocity": round(

                relative_velocity,

                6

            ),


            # -------------------------------
            # ORIENTATION
            # -------------------------------

            "orientation": {

                "roll": roll,

                "pitch": round(
                    pitch,
                    2
                ),

                "yaw": round(
                    yaw,
                    2
                )

            },


            # -------------------------------
            # ROTATION AXIS
            # -------------------------------

            "rotation_axis": {

                "x": rotation_axis["x"],

                "y": rotation_axis["y"],

                "z": rotation_axis["z"]

            },


            # -------------------------------
            # ESTIMATED PARAMETERS
            # -------------------------------

            "estimated_size_m":
                estimated_size,

            "estimated_rcs_m2":
                estimated_rcs,

            "object_type":
                object_type,

            "estimated_mass_kg":
                estimated_mass,

            "motion_rate":
                motion_rate,

            "tumbling_rate":
                tumbling_rate,


            # -------------------------------
            # COLLISION
            # -------------------------------

            "collision_confidence":
                confidence,


            # -------------------------------
            # TIMESTAMP
            # -------------------------------

            "timestamp":
                timestamp

        })


    except Exception as e:

        print(
            f"Error processing "
            f"{obj['name']} : {e}"
        )


# =====================================================
# SAVE JSON
# =====================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(

        feature_data,

        file,

        indent=4

    )


# =====================================================
# SUMMARY
# =====================================================

print(
    "\n========================================"
)

print(
    " Feature Extraction Completed Successfully "
)

print(
    "========================================"
)

print(
    f"Processed Objects : "
    f"{len(feature_data)}"
)

print(
    "\nOutput File :"
)

print(
    OUTPUT_FILE
)


# =====================================================
# SHOW FIRST OBJECT
# =====================================================

if feature_data:

    print(
        "\n================ FIRST OBJECT ================\n"
    )

    print(

        json.dumps(

            feature_data[0],

            indent=4

        )

    )


print(
    "\n========================================"
)

print(
    " debris_state.json generated successfully "
)

print(
    "========================================"
)