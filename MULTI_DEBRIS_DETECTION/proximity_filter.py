import os
import json


# ============================================================
# PROJECT PATHS
# ============================================================

base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

input_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "multi_debris_state.json"
)

output_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "nearby_debris.json"
)


# ============================================================
# PROXIMITY LIMIT
# ============================================================

PROXIMITY_LIMIT_KM = 100.0


# ============================================================
# LOAD MULTI-DEBRIS STATE DATA
# ============================================================

print("=" * 60)
print("100 KM PROXIMITY FILTER")
print("=" * 60)

print("\nReading multi-debris state data:")
print(input_file)


if not os.path.exists(input_file):

    print("\nERROR:")
    print("multi_debris_state.json was not found.")

    raise SystemExit


with open(
    input_file,
    "r",
    encoding="utf-8"
) as file:

    debris_data = json.load(file)


print(
    "\nTotal debris states:",
    len(debris_data)
)


# ============================================================
# APPLY 100 KM FILTER
# ============================================================

nearby_debris = []

outside_range = 0
invalid_distance = 0


for debris in debris_data:

    try:

        relative_distance = float(
            debris["relative_distance"]
        )

        if relative_distance <= PROXIMITY_LIMIT_KM:

            nearby_debris.append(
                debris
            )

        else:

            outside_range += 1

    except (
        KeyError,
        TypeError,
        ValueError
    ):

        invalid_distance += 1


# ============================================================
# SORT NEARBY OBJECTS BY DISTANCE
# ============================================================

nearby_debris.sort(
    key=lambda obj: float(
        obj["relative_distance"]
    )
)


# ============================================================
# SAVE NEARBY DEBRIS
# ============================================================

with open(
    output_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        nearby_debris,
        file,
        indent=4
    )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n")
print("=" * 60)
print("PROXIMITY FILTER COMPLETED")
print("=" * 60)

print(
    "Total debris:",
    len(debris_data)
)

print(
    "100 km limit:",
    PROXIMITY_LIMIT_KM,
    "km"
)

print(
    "Nearby debris (<= 100 km):",
    len(nearby_debris)
)

print(
    "Outside 100 km:",
    outside_range
)

print(
    "Invalid distance records:",
    invalid_distance
)

print("\nOutput file:")
print(output_file)

print("\n")


# ============================================================
# DISPLAY NEARBY OBJECTS
# ============================================================

if len(nearby_debris) > 0:

    print("=" * 60)
    print("NEARBY DEBRIS OBJECTS")
    print("=" * 60)

    for number, debris in enumerate(
        nearby_debris,
        start=1
    ):

        print(
            f"{number}. "
            f"{debris['name']} "
            f"(NORAD {debris['object_id']}) "
            f"- "
            f"{debris['relative_distance']:.3f} km"
        )

else:

    print(
        "No debris objects are currently "
        "within 100 km."
    )

print("=" * 60)