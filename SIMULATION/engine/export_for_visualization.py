"""
ADCS Mission Visualization Data Generator

Run from project root:

python3 SIMULATION/engine/export_for_visualization.py
"""

from pathlib import Path
import json
import random
import math

from scenario_logic import (
    SCENARIOS,
    PHASES,
    evaluate_target
)


random.seed(42)

OUTPUT = Path(__file__).with_name("viz_data.json")


DEBRIS_SHAPES = [
    "fragment",
    "panel",
    "cylinder",
    "irregular",
    "bracket"
]


def generate_background_debris():

    debris = []

    for i in range(180):

        angle = random.random() * math.tau

        vertical = random.uniform(-1, 1)

        radius = random.uniform(1.2, 2.6)

        debris.append({

            "id": f"ORB-BG-{i + 1:03d}",

            "class": "BACKGROUND",

            "shape": DEBRIS_SHAPES[i % len(DEBRIS_SHAPES)],

            "position": [

                round(math.cos(angle) * radius, 4),

                round(vertical * radius * 0.65, 4),

                round(math.sin(angle) * radius, 4)
            ],

            "size_m": round(
                random.uniform(0.05, 1.4),
                2
            ),

            "velocity_kms": round(
                random.uniform(6.9, 8.1),
                2
            ),

            "risk": "LOW"
        })

    return debris


def generate_tracked_debris():

    debris = []

    for i in range(15):

        angle = (
            math.tau * i / 15
            + random.uniform(-0.12, 0.12)
        )

        radius = random.uniform(0.30, 0.88)

        risk = "LOW"

        if i == 4:
            risk = "HIGH"

        elif i in (2, 8, 11):
            risk = "MEDIUM"

        debris.append({

            "id": f"ORB-DEB-{i + 1:02d}",

            # EXACTLY ONE TARGET
            "class":
                "TARGET"
                if i == 4
                else "TRACKED",

            "shape":
                DEBRIS_SHAPES[
                    (i + 2) % len(DEBRIS_SHAPES)
                ],

            "position": [

                round(math.cos(angle) * radius, 4),

                round(
                    random.uniform(-0.35, 0.35),
                    4
                ),

                round(math.sin(angle) * radius, 4)
            ],

            "size_m":
                round(random.uniform(0.12, 1.8), 2),

            "velocity_kms":
                round(random.uniform(7.1, 7.9), 2),

            "risk": risk,

            "distance_km":
                round(random.uniform(12, 98), 1)
        })

    return debris


def generate_scenarios():

    scenarios = {}

    for key, scenario in SCENARIOS.items():

        assessment = scenario["assessment"]

        decision, rationale = evaluate_target(
            assessment
        )

        scenarios[key] = {

            "label":
                scenario["label"],

            "decision":
                decision.value,

            "description":
                scenario["description"],

            "rationale":
                rationale,

            "assessment": {

                "size_m":
                    assessment.size_m,

                "relative_speed_mps":
                    assessment.relative_speed_mps,

                "range_km":
                    assessment.range_km,

                "risk":
                    assessment.risk,

                "group_count":
                    assessment.group_count,

                "tumbling":
                    assessment.tumbling,

                "sensor_confidence":
                    assessment.sensor_confidence
            }
        }

    return scenarios


def main():

    print("=" * 72)
    print("ADCS MISSION VISUALIZATION ENGINE")
    print("=" * 72)

    background = generate_background_debris()

    tracked = generate_tracked_debris()

    debris = background + tracked

    data = {

        "project": {

            "name":
                "Autonomous Space Debris Monitoring & Capturing System",

            "short":
                "ADCS"
        },

        "environment": {

            "monitored_objects":
                195,

            "tracked_objects":
                15,

            "surveillance_radius_km":
                100,

            "orbit_altitude_km":
                550,

            "orbital_velocity_kms":
                7.58
        },

        "spacecraft": {

            "id":
                "ADCS-SERVICER-01",

            "color":
                "#9b6cff",

            "storage_capacity":
                "6–10 objects",

            "storage_note":
                "Subject to cumulative captured mass and available containment volume."
        },

        "active_target_id":
            "ORB-DEB-05",

        "debris":
            debris,

        "phases":
            PHASES,

        "scenarios":
            generate_scenarios(),

        "default_scenario":
            "large"
    }

    OUTPUT.write_text(

        json.dumps(
            data,
            indent=2
        ),

        encoding="utf-8"
    )

    print(
        f"Total monitored objects: "
        f"{data['environment']['monitored_objects']}"
    )

    print(
        f"Tracked objects within "
        f"{data['environment']['surveillance_radius_km']} km: "
        f"{data['environment']['tracked_objects']}"
    )

    print(
        f"Active operational target: "
        f"{data['active_target_id']}"
    )

    print()
    print("Available demonstration scenarios:")

    for scenario in data["scenarios"].values():

        print(
            f"  • {scenario['label']}"
        )

    print()
    print(f"Output file: {OUTPUT}")
    print("=" * 72)


if __name__ == "__main__":
    main()