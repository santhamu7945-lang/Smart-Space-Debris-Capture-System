import os
import json

base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

input_file = os.path.join(
    base_dir,
    "DATA",
    "processed",
    "multi_debris_state.json"
)

with open(input_file, "r", encoding="utf-8") as file:
    debris_data = json.load(file)

distances = []

for debris in debris_data:
    try:
        distance = float(debris["relative_distance"])
        distances.append((distance, debris))
    except (KeyError, TypeError, ValueError):
        pass

distances.sort(key=lambda x: x[0])

print("=" * 60)
print("RELATIVE DISTANCE CHECK")
print("=" * 60)

print("\nTotal valid distance records:", len(distances))

if distances:
    print("\nClosest 20 debris objects:")
    print("-" * 60)

    for i, (distance, debris) in enumerate(
        distances[:20],
        start=1
    ):
        print(
            f"{i}. "
            f"NORAD {debris['object_id']} | "
            f"{debris['name']} | "
            f"{distance:.3f} km"
        )

    print("\n")
    print("Minimum distance:", distances[0][0], "km")
    print("Maximum distance:", distances[-1][0], "km")

    within_100 = [
        item for item in distances
        if item[0] <= 100
    ]

    print(
        "\nObjects within 100 km:",
        len(within_100)
    )

print("=" * 60)