import os
import json
from datetime import datetime, UTC


# ============================================================
# PATHS
# ============================================================

base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

input_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "nearby_debris.json"
)

output_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "multi_tracking_state.json"
)


# ============================================================
# SETTINGS
# ============================================================

PROXIMITY_LIMIT_KM = 100.0


# ============================================================
# START
# ============================================================

print("=" * 60)
print("MULTI-OBJECT TRACKER")
print("=" * 60)

print("\nReading nearby debris:")
print(input_file)


# ============================================================
# CHECK INPUT FILE
# ============================================================

if not os.path.exists(input_file):
    print("\nERROR:")
    print("nearby_debris.json was not found.")
    raise SystemExit


# ============================================================
# LOAD CURRENT NEARBY DEBRIS
# ============================================================

try:
    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as file:
        nearby_debris = json.load(file)

except json.JSONDecodeError:
    print("\nERROR:")
    print("nearby_debris.json contains invalid JSON.")
    raise SystemExit


if not isinstance(nearby_debris, list):
    print("\nERROR:")
    print("nearby_debris.json must contain a JSON list.")
    raise SystemExit


print(
    "\nObjects inside 100 km:",
    len(nearby_debris)
)


# ============================================================
# LOAD PREVIOUS TRACKING STATE
# ============================================================

previous_tracking = {}

if os.path.exists(output_file):

    try:
        with open(
            output_file,
            "r",
            encoding="utf-8"
        ) as file:
            previous_data = json.load(file)

        if isinstance(previous_data, list):

            for obj in previous_data:

                object_id = str(
                    obj.get("object_id", "")
                ).strip()

                if object_id:
                    previous_tracking[object_id] = obj

    except (json.JSONDecodeError, TypeError):
        print(
            "\nWarning:"
        )
        print(
            "Previous tracking state could not be read."
        )
        print(
            "Starting a new tracking state."
        )


# ============================================================
# TRACK CURRENT OBJECTS
# ============================================================

current_tracking = []

new_objects = 0
continued_objects = 0

current_object_ids = set()


for debris in nearby_debris:

    object_id = str(
        debris.get("object_id", "")
    ).strip()

    if not object_id:
        continue

    current_object_ids.add(object_id)

    # --------------------------------------------------------
    # EXISTING OBJECT
    # --------------------------------------------------------

    if object_id in previous_tracking:

        old_tracking = previous_tracking[object_id]

        tracking_id = old_tracking.get(
            "tracking_id"
        )

        first_seen = old_tracking.get(
            "first_seen"
        )

        continued_objects += 1

        tracking_status = "CONTINUED"

    # --------------------------------------------------------
    # NEW OBJECT
    # --------------------------------------------------------

    else:

        tracking_id = (
            f"TRK_{object_id}"
        )

        first_seen = datetime.now(
            UTC
        ).isoformat()

        new_objects += 1

        tracking_status = "NEW"

    # --------------------------------------------------------
    # CREATE TRACKING RECORD
    # --------------------------------------------------------

    tracking_record = {
        "tracking_id": tracking_id,

        "object_id": object_id,

        "name": debris.get(
            "name",
            "UNKNOWN"
        ),

        "tracking_status": tracking_status,

        "first_seen": first_seen,

        "last_seen": datetime.now(
            UTC
        ).isoformat(),

        "relative_distance": debris.get(
            "relative_distance"
        ),

        "relative_velocity": debris.get(
            "relative_velocity"
        ),

        "position": debris.get(
            "position"
        ),

        "velocity": debris.get(
            "velocity"
        ),

        "speed": debris.get(
            "speed"
        ),

        "altitude": debris.get(
            "altitude"
        ),

        "inclination": debris.get(
            "inclination"
        ),

        "orbit_class": debris.get(
            "orbit_class"
        ),

        "orientation": debris.get(
            "orientation"
        ),

        "estimated_size_m": debris.get(
            "estimated_size_m"
        ),

        "estimated_rcs_m2": debris.get(
            "estimated_rcs_m2"
        ),

        "object_type": debris.get(
            "object_type"
        ),

        "estimated_mass_kg": debris.get(
            "estimated_mass_kg"
        ),

        "motion_rate": debris.get(
            "motion_rate"
        ),

        "tumbling_rate": debris.get(
            "tumbling_rate"
        ),

        "collision_confidence": debris.get(
            "collision_confidence"
        )
    }

    current_tracking.append(
        tracking_record
    )


# ============================================================
# IDENTIFY OBJECTS THAT LEFT 100 KM
# ============================================================

left_objects = []

for object_id in previous_tracking:

    if object_id not in current_object_ids:

        old_tracking = previous_tracking[
            object_id
        ]

        left_objects.append({
            "tracking_id": old_tracking.get(
                "tracking_id"
            ),

            "object_id": object_id,

            "name": old_tracking.get(
                "name",
                "UNKNOWN"
            ),

            "status": "OUTSIDE_100_KM",

            "last_seen": old_tracking.get(
                "last_seen"
            )
        })


# ============================================================
# SAVE CURRENT TRACKING STATE
# ============================================================

os.makedirs(
    os.path.dirname(output_file),
    exist_ok=True
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        current_tracking,
        file,
        indent=4
    )


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n")
print("=" * 60)
print("MULTI-OBJECT TRACKING COMPLETED")
print("=" * 60)

print(
    "100 km proximity limit:",
    PROXIMITY_LIMIT_KM,
    "km"
)

print(
    "Current nearby objects:",
    len(current_tracking)
)

print(
    "New objects:",
    new_objects
)

print(
    "Continued objects:",
    continued_objects
)

print(
    "Objects that left 100 km:",
    len(left_objects)
)

print("\nOutput file:")
print(output_file)


# ============================================================
# DISPLAY CURRENT TRACKING OBJECTS
# ============================================================

if current_tracking:

    print("\n")
    print("=" * 60)
    print("CURRENTLY TRACKED OBJECTS")
    print("=" * 60)

    for number, obj in enumerate(
        current_tracking,
        start=1
    ):

        print(
            f"{number}. "
            f"{obj['name']} "
            f"(NORAD {obj['object_id']}) "
            f"| Tracking ID: "
            f"{obj['tracking_id']} "
            f"| Distance: "
            f"{obj['relative_distance']} km "
            f"| Status: "
            f"{obj['tracking_status']}"
        )

else:

    print("\n")
    print(
        "No debris objects are currently "
        "within 100 km."
    )

    print(
        "Tracker is ready for future "
        "nearby objects."
    )


# ============================================================
# DISPLAY OBJECTS THAT LEFT THE RANGE
# ============================================================

if left_objects:

    print("\n")
    print("=" * 60)
    print("OBJECTS THAT LEFT 100 KM")
    print("=" * 60)

    for obj in left_objects:

        print(
            f"NORAD {obj['object_id']} "
            f"| {obj['name']} "
            f"| {obj['tracking_id']} "
            f"| {obj['status']}"
        )


print("=" * 60)