from pathlib import Path
import pandas as pd

from AI_Engine.data.data_loader import load_all_tracked_debris

from AI_Engine.orbit_dynamics.propagator import (
    propagate_gp_record,
)

from AI_Engine.collision_avoidance.probability import (
    collision_probability,
)

from AI_Engine.guidance_decision.risk_engine import (
    compute_risk_score,
)

from AI_Engine.guidance_decision.capture_feasibility import (
    evaluate_capture_feasibility,
)

from AI_Engine.guidance_decision.mission_manager import (
    generate_mission_decision,
)

from AI_Engine.guidance_decision.decision_exporter import (
    export_decision,
)

from AI_Engine.target_selection.target_selector import (
    select_target,
)


# ==============================
# CONFIGURATION
# ==============================

GP_DATA_FILE = Path(
    "DATA/raw/multi_debris/gp_data.csv"
)

PREDICTION_HORIZON_S = 60


def main():

    # ==========================================
    # LOAD DETECTION OUTPUT
    # ==========================================

    debris_list = load_all_tracked_debris()

    print("\n===== MULTI-DEBRIS AI ANALYSIS =====")
    print(
        f"Total tracked debris: {len(debris_list)}"
    )

    # ==========================================
    # LOAD GP ORBITAL DATA
    # ==========================================

    gp_df = pd.read_csv(GP_DATA_FILE)

    candidates = []

    # ==========================================
    # PROCESS EACH TRACKED DEBRIS
    # ==========================================

    for debris in debris_list:

        name = debris["name"]
        tracking_id = debris["tracking_id"]
        object_id = int(debris["object_id"])

        print("\n--------------------------------")
        print(f"Target: {name}")
        print(f"Tracking ID: {tracking_id}")
        print(f"NORAD ID: {object_id}")

        # ======================================
        # FIND CORRESPONDING GP RECORD
        # ======================================

        matching_rows = gp_df[
            gp_df["NORAD_CAT_ID"] == object_id
        ]

        if matching_rows.empty:

            print(
                "GP orbital record not found."
            )

            continue

        gp_record = (
            matching_rows.iloc[0].to_dict()
        )

        # ======================================
        # SGP4 FUTURE PREDICTION
        # ======================================

        try:

            prediction = propagate_gp_record(
                gp_record,
                PREDICTION_HORIZON_S
            )

        except Exception as error:

            print(
                f"Prediction failed: {error}"
            )

            continue

        predicted_position = (
            prediction["position_km"]
        )

        predicted_velocity = (
            prediction["velocity_kms"]
        )

        print(
            "\n===== SGP4 PREDICTION ====="
        )

        print(
            f"Prediction Horizon: "
            f"{PREDICTION_HORIZON_S} s"
        )

        print(
            "Predicted Position (km):"
        )

        print(
            f"X: {predicted_position[0]:.3f}"
        )

        print(
            f"Y: {predicted_position[1]:.3f}"
        )

        print(
            f"Z: {predicted_position[2]:.3f}"
        )

        print(
            "Predicted Velocity (km/s):"
        )

        print(
            f"Vx: {predicted_velocity[0]:.3f}"
        )

        print(
            f"Vy: {predicted_velocity[1]:.3f}"
        )

        print(
            f"Vz: {predicted_velocity[2]:.3f}"
        )

        # ======================================
        # CURRENT DETECTION PARAMETERS
        # ======================================

        closest_distance_m = (
            debris["relative_distance"]
            * 1000.0
        )

        relative_velocity_kms = (
            debris["relative_velocity"]
        )

        tumbling_rate_dps = (
            debris["tumbling_rate"]
        )

        size_cm = (
            debris["estimated_size_m"]
            * 100.0
        )

        # ======================================
        # COLLISION PROBABILITY
        # ======================================

        probability = collision_probability(
            closest_distance_m
        )

        # ======================================
        # RISK ANALYSIS
        # ======================================

        risk = compute_risk_score(

            closest_distance_m=(
                closest_distance_m
            ),

            relative_velocity_kms=(
                relative_velocity_kms
            ),

            collision_probability=(
                probability
            ),

            tumbling_rate_dps=(
                tumbling_rate_dps
            ),

            prediction_uncertainty_m=100.0
        )

        # ======================================
        # CAPTURE FEASIBILITY
        # ======================================

        capture = evaluate_capture_feasibility(

            size_cm=size_cm,

            relative_velocity_kms=(
                relative_velocity_kms
            ),

            tumbling_rate_dps=(
                tumbling_rate_dps
            )
        )

        # ======================================
        # CREATE CANDIDATE
        # ======================================

        candidate = {

            "tracking_id":
                tracking_id,

            "object_id":
                str(object_id),

            "name":
                name,

            "altitude_km":
                debris["altitude"],

            "inclination_deg":
                debris["inclination"],

            "orbit_class":
                debris["orbit_class"],

            "closest_distance_m":
                closest_distance_m,

            "time_to_closest_approach_s":
                0.0,

            "relative_velocity_kms":
                relative_velocity_kms,

            "collision_probability":
                probability,

            "risk_score":
                risk["risk_score"],

            "risk_level":
                risk["risk_level"],

            "capture_method":
                capture["capture_method"],

            "capture_score":
                capture["capture_score"],

            "capture_feasible":
                capture["capture_feasible"],

            "difficulty_level":
                capture["difficulty_level"],

            # ------------------------------
            # FUTURE PREDICTION
            # ------------------------------

            "prediction_horizon_s":
                PREDICTION_HORIZON_S,

            "predicted_position_km": {

                "x":
                    predicted_position[0],

                "y":
                    predicted_position[1],

                "z":
                    predicted_position[2]
            },

            "predicted_velocity_kms": {

                "vx":
                    predicted_velocity[0],

                "vy":
                    predicted_velocity[1],

                "vz":
                    predicted_velocity[2]
            },

            "timestamp":
                debris["last_seen"]
        }

        candidates.append(candidate)

        # ======================================
        # DISPLAY AI RESULTS
        # ======================================

        print("\n===== AI ANALYSIS =====")

        print(
            f"Relative Distance: "
            f"{closest_distance_m:.2f} m"
        )

        print(
            f"Relative Velocity: "
            f"{relative_velocity_kms:.3f} km/s"
        )

        print(
            f"Collision Probability: "
            f"{probability:.6e}"
        )

        print(
            f"Risk Score: "
            f"{risk['risk_score']:.2f}/100"
        )

        print(
            f"Risk Level: "
            f"{risk['risk_level']}"
        )

        print(
            f"Capture Method: "
            f"{capture['capture_method']}"
        )

        print(
            f"Capture Score: "
            f"{capture['capture_score']}/100"
        )

        print(
            f"Capture Feasible: "
            f"{capture['capture_feasible']}"
        )

        print(
            f"Difficulty: "
            f"{capture['difficulty_level']}"
        )

    # ==========================================
    # TARGET SELECTION
    # ==========================================

    if not candidates:

        print(
            "\nNo valid prediction candidates found."
        )

        return

    selected_target = select_target(
        candidates
    )

    if selected_target is None:

        print(
            "\n===== TARGET SELECTION ====="
        )

        print(
            "No feasible debris target found."
        )

        return

    print(
        "\n===== SELECTED TARGET ====="
    )

    print(
        f"Tracking ID: "
        f"{selected_target['tracking_id']}"
    )

    print(
        f"Target: "
        f"{selected_target['name']}"
    )

    print(
        f"Risk Score: "
        f"{selected_target['risk_score']:.2f}/100"
    )

    print(
        f"Risk Level: "
        f"{selected_target['risk_level']}"
    )

    print(
        f"Capture Score: "
        f"{selected_target['capture_score']:.2f}/100"
    )

    print(
        f"Capture Method: "
        f"{selected_target['capture_method']}"
    )

    # ==========================================
    # MISSION DECISION
    # ==========================================

    decision = generate_mission_decision(

        risk_level=
            selected_target["risk_level"],

        capture_feasible=
            selected_target[
                "capture_feasible"
            ],

        capture_score=
            selected_target[
                "capture_score"
            ]
    )

    print(
        "\n===== MISSION DECISION ====="
    )

    print(
        f"Decision: "
        f"{decision['decision']}"
    )

    print(
        f"Reason: "
        f"{decision['reason']}"
    )

    # ==========================================
    # FINAL OUTPUT JSON
    # ==========================================

    mission_json = {

        "mission_id":
            "MIS-2026-001",

        "tracking_id":
            selected_target["tracking_id"],

        "object_id":
            selected_target["object_id"],

        "target_name":
            selected_target["name"],

        "orbit_class":
            selected_target["orbit_class"],

        "altitude_km":
            selected_target["altitude_km"],

        "inclination_deg":
            selected_target["inclination_deg"],

        "closest_distance_m":
            selected_target[
                "closest_distance_m"
            ],

        "time_to_closest_approach_s":
            selected_target[
                "time_to_closest_approach_s"
            ],

        "relative_velocity_kms":
            selected_target[
                "relative_velocity_kms"
            ],

        "collision_probability":
            selected_target[
                "collision_probability"
            ],

        "risk_level":
            selected_target[
                "risk_level"
            ],

        "risk_score":
            selected_target[
                "risk_score"
            ],

        "capture_method":
            selected_target[
                "capture_method"
            ],

        "capture_score":
            selected_target[
                "capture_score"
            ],

        "capture_feasible":
            selected_target[
                "capture_feasible"
            ],

        "difficulty_level":
            selected_target[
                "difficulty_level"
            ],

        # ------------------------------
        # PREDICTION OUTPUT
        # ------------------------------

        "prediction_horizon_s":
            selected_target[
                "prediction_horizon_s"
            ],

        "predicted_position_km":
            selected_target[
                "predicted_position_km"
            ],

        "predicted_velocity_kms":
            selected_target[
                "predicted_velocity_kms"
            ],

        "decision":
            decision["decision"],

        "reason":
            decision["reason"],

        "timestamp":
            selected_target["timestamp"]
    }

    # ==========================================
    # EXPORT
    # ==========================================

    export_decision(

        Path(
            "AI_Engine/telemetry/"
            "mission_decision.json"
        ),

        mission_json
    )

    print(
        "\nMission decision exported successfully."
    )


if __name__ == "__main__":
    main()