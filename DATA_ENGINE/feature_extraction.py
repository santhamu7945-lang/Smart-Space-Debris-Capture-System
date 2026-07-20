import os
import json
import math
from datetime import datetime
from skyfield.api import EarthSatellite, load

# ----------------------------------
# Project Paths
# ----------------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

input_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "clean_debris.json"
)

output_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "debris_state.json"
)

# ----------------------------------
# Load cleaned debris data
# ----------------------------------
with open(input_file, "r", encoding="utf-8") as file:
    debris_data = json.load(file)

print(f"Total debris objects: {len(debris_data)}")

# ----------------------------------
# Load Skyfield
# ----------------------------------
ts = load.timescale()
t = ts.now()

print("Skyfield loaded successfully!")

# ----------------------------------
# Feature Extraction
# ----------------------------------
feature_data = []

EARTH_RADIUS = 6378.137  # km

for obj in debris_data:

    try:

        # Create satellite object
        satellite = EarthSatellite(
            obj["line1"],
            obj["line2"],
            obj["name"],
            ts
        )

        # Position and velocity
        geocentric = satellite.at(t)

        x, y, z = geocentric.position.km
        vx, vy, vz = geocentric.velocity.km_per_s

        # Speed
        speed = math.sqrt(vx**2 + vy**2 + vz**2)

        # Distance from Earth's center
        distance = math.sqrt(x**2 + y**2 + z**2)

        # Altitude
        altitude = distance - EARTH_RADIUS

        # Inclination
        inclination = float(obj["line2"].split()[2])

        # Orbit Classification
        if altitude < 2000:
            orbit_class = "LEO"
        elif altitude < 35786:
            orbit_class = "MEO"
        else:
            orbit_class = "GEO"

        # Timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Store extracted features
        feature_data.append({

            "object_id": obj["norad_id"],
            "name": obj["name"],

            "position": {
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(z, 3)
            },

            "velocity": {
                "vx": round(vx, 6),
                "vy": round(vy, 6),
                "vz": round(vz, 6)
            },

            "speed": round(speed, 6),

            "altitude": round(altitude, 3),

            "inclination": inclination,

            "orbit_class": orbit_class,

            "timestamp": timestamp

        })

    except Exception as e:
        print(f"Error processing {obj['name']}: {e}")

# ----------------------------------
# Save JSON
# ----------------------------------
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(feature_data, file, indent=4)

print("\nFeature Extraction Completed!")
print(f"Processed Objects : {len(feature_data)}")
print(f"Output Saved To : {output_file}")

# ----------------------------------
# Display first object
# ----------------------------------
if feature_data:
    print("\nFirst Object:\n")
    print(json.dumps(feature_data[0], indent=4))