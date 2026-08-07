from pathlib import Path

from AI_Engine.data.data_loader import load_debris_by_name
from AI_Engine.collision_avoidance.closest_approach import closest_approach
from AI_Engine.collision_avoidance.probability import collision_probability
from AI_Engine.guidance_decision.risk_engine import compute_risk_score
from AI_Engine.guidance_decision.capture_feasibility import (
    evaluate_capture_feasibility,
)
from AI_Engine.guidance_decision.mission_manager import (
    generate_mission_decision,
)
from AI_Engine.guidance_decision.decision_exporter import (
    export_decision,
)

# Select the debris object to analyze
TARGET_NAME = 'COSMOS 2251'


def main():

    # Load selected target debris
    debris = load_debris_by_name(TARGET_NAME)

    name = debris['name']

    debris_position_km = (
        debris['position']['x'],
        debris['position']['y'],
        debris['position']['z']
    )

    debris_velocity_kms = (
        debris['velocity']['vx'],
        debris['velocity']['vy'],
        debris['velocity']['vz']
    )

    # Reference satellite state (example)
    satellite_position_km = (7000.0, 0.0, 0.0)
    satellite_velocity_kms = (0.0, 7.5, 0.0)

    # Closest approach analysis
    result = closest_approach(
        satellite_position_km,
        satellite_velocity_kms,
        debris_position_km,
        debris_velocity_kms
    )

    # Collision probability
    probability = collision_probability(
        result['closest_distance_m']
    )

    # Physical parameters from dataset
    size_cm = debris['estimated_size_m'] * 100.0
    tumbling_rate_dps = debris['tumbling_rate']

    # Mission risk assessment
    risk = compute_risk_score(
        closest_distance_m=result['closest_distance_m'],
        relative_velocity_kms=result['relative_velocity_kms'],
        collision_probability=probability,
        tumbling_rate_dps=tumbling_rate_dps,
        prediction_uncertainty_m=100.0
    )

    # Capture feasibility analysis
    capture = evaluate_capture_feasibility(
        size_cm=size_cm,
        relative_velocity_kms=result['relative_velocity_kms'],
        tumbling_rate_dps=tumbling_rate_dps
    )

    # Mission decision generation
    decision = generate_mission_decision(
        risk_level=risk['risk_level'],
        capture_feasible=capture['capture_feasible'],
        capture_score=capture['capture_score']
    )

    # Print mission analysis
    print('\\n===== MISSION RISK ANALYSIS =====')
    print('Target:', name)

    print(f"Tracking ID : {debris['tracking_id']}")
    print(f"Altitude : {debris['altitude']} km")
    print(f"Inclination : {debris['inclination']} deg")
    print(f"Orbit Class : {debris['orbit_class']}")
    print(
        f"Orientation (RPY) : "
        f"{debris['orientation']['roll']}, "
        f"{debris['orientation']['pitch']}, "
        f"{debris['orientation']['yaw']}"
    )
    print(f"Dataset Timestamp : {debris['timestamp']}")
    print(
        f"Closest Distance : {result['closest_distance_m']:.2f} m"
    )
    print(
        f"Time to Closest Approach : "
        f"{result['time_to_closest_approach_s']:.2f} s"
    )
    print(
        f"Relative Velocity : "
        f"{result['relative_velocity_kms']:.3f} km/s"
    )
    print(
        f"Collision Probability : {probability:.6e}"
    )
    print(
        f"Mission Risk Score : {risk['risk_score']:.2f}/100"
    )
    print(
        f"Risk Level : {risk['risk_level']}"
    )
    print(
        f"Capture Method : {capture['capture_method']}"
    )
    print(
        f"Capture Score : {capture['capture_score']}/100"
    )
    print(
        f"Capture Feasible : {capture['capture_feasible']}"
    )
    print(
        f"Difficulty Level : {capture['difficulty_level']}"
    )
    print(
        f"Mission Decision : {decision['decision']}"
    )
    print(
        f"Decision Reason : {decision['reason']}"
    )

    # Export decision to telemetry JSON
    mission_json = {
        'mission_id': 'MIS-2026-001',
        'tracking_id': debris['tracking_id'],
        'target_name': name,
        'orbit_class': debris['orbit_class'],
        'altitude_km': debris['altitude'],
        'inclination_deg': debris['inclination'],
        'risk_level': risk['risk_level'],
        'risk_score': risk['risk_score'],
        'capture_method': capture['capture_method'],
        'capture_score': capture['capture_score'],
        'capture_feasible': capture['capture_feasible'],
        'difficulty_level': capture['difficulty_level'],
        'decision': decision['decision'],
        'reason': decision['reason'],
        'timestamp': debris['timestamp']
    }

    export_decision(
        Path('AI_Engine/telemetry/mission_decision.json'),
        mission_json
    )

    print('\\nMission decision exported successfully.')


if __name__ == '__main__':
    main()