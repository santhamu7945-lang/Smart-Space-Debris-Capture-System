"""
export_for_visualization.py

Exports a lightweight JSON for the Three.js dashboard/simulation, combining
debris_state.json (Detection) and mission_decision.json (Mission Manager).

UPDATED: now includes each object's velocity vector (vx, vy, vz), not just
position. This is required for real two-body Kepler orbital propagation in
the simulation — position alone isn't enough to determine an orbit; you
need velocity too, since state vectors (r, v) uniquely define the six
classical orbital elements.

IMPORTANT: tracking_id resets and regenerates every time
feature_extraction.py runs, so a tracking_id saved in an older
mission_decision.json will NOT reliably match the tracking_id in a
freshly-regenerated debris_state.json. This script matches the target by
NAME instead, which is stable across separate runs.

Run from repo root:
    python3 SIMULATION/engine/export_for_visualization.py

Output:
    SIMULATION/viz_data.json
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEBRIS_STATE_PATH = os.path.join(BASE_DIR, "DATA", "processed", "debris_state.json")
MISSION_DECISION_PATH = os.path.join(BASE_DIR, "AI_Engine", "telemetry", "mission_decision.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "SIMULATION", "viz_data.json")

EARTH_RADIUS_KM = 6378.137


def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    debris_raw = load_json(DEBRIS_STATE_PATH)
    if isinstance(debris_raw, dict) and "debris_objects" in debris_raw:
        debris_raw = debris_raw["debris_objects"]

    mission_raw = load_json(MISSION_DECISION_PATH)
    if isinstance(mission_raw, list) and len(mission_raw) > 0:
        mission_raw = mission_raw[0]

    target_name = mission_raw.get("target_name")

    debris_list = []
    matched_target = False

    for obj in debris_raw:
        pos = obj.get("position", {})
        vel = obj.get("velocity", {})
        if pos.get("x") is None:
            continue

        is_target = (obj.get("name") == target_name) and not matched_target
        if is_target:
            matched_target = True

        debris_list.append({
            "id": obj.get("tracking_id"),
            "name": obj.get("name"),
            "x": pos.get("x"),
            "y": pos.get("y"),
            "z": pos.get("z"),
            # NEW: velocity components, needed to compute real orbital
            # elements (a, e, i, RAAN, argument of perigee, true anomaly)
            # for Kepler propagation in the simulation.
            "vx": vel.get("vx"),
            "vy": vel.get("vy"),
            "vz": vel.get("vz"),
            "size_m": obj.get("estimated_size_m"),
            "mass_kg": obj.get("estimated_mass_kg"),
            "tumbling_rate": obj.get("tumbling_rate"),
            "collision_risk": obj.get("collision_confidence"),
            "is_target": is_target
        })

    if not matched_target:
        print(f"WARNING: No debris object found matching target_name "
              f"'{target_name}'. Target will not be highlighted.")

    output = {
        "earth_radius_km": EARTH_RADIUS_KM,
        "target": {
            "id": mission_raw.get("tracking_id"),
            "name": target_name,
            "decision": mission_raw.get("decision"),
            "decision_reason": mission_raw.get("reason"),
            "risk_level": mission_raw.get("risk_level"),
            "risk_score": mission_raw.get("risk_score"),
            "capture_method": mission_raw.get("capture_method"),
            "capture_score": mission_raw.get("capture_score"),
            "capture_feasible": mission_raw.get("capture_feasible"),
            "difficulty_level": mission_raw.get("difficulty_level"),
            "altitude_km": mission_raw.get("altitude_km"),
            "inclination_deg": mission_raw.get("inclination_deg"),
            "orbit_class": mission_raw.get("orbit_class"),
        },
        "debris": debris_list
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Exported {len(debris_list)} debris objects (with velocity vectors) for visualization")
    print(f"Target: {output['target']['name']} ({'matched' if matched_target else 'NOT MATCHED'})")
    print(f"Decision: {output['target']['decision']}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
