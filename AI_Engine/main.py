from AI_Engine.config.settings import TLE_FILE
from AI_Engine.orbit_dynamics.tle_loader import load_tle
from AI_Engine.orbit_dynamics.propagator import propagate_tle
from AI_Engine.collision_avoidance.closest_approach import closest_approach
from AI_Engine.collision_avoidance.probability import collision_probability
from AI_Engine.guidance_decision.risk_engine import compute_risk_score
from AI_Engine.guidance_decision.capture_feasibility import (
    evaluate_capture_feasibility,
)


def main():

    # Load target debris
    name, line1, line2 = load_tle(TLE_FILE)

    debris_state = propagate_tle(line1, line2, 0)

    # Reference satellite state (example)
    satellite_position_km = (7000.0, 0.0, 0.0)
    satellite_velocity_kms = (0.0, 7.5, 0.0)

    # Closest approach analysis
    result = closest_approach(
        satellite_position_km,
        satellite_velocity_kms,
        debris_state['position_km'],
        debris_state['velocity_kms']
    )

    # Collision probability
    probability = collision_probability(
        result['closest_distance_m']
    )

    # Mission risk assessment
    risk = compute_risk_score(
        closest_distance_m=result['closest_distance_m'],
        relative_velocity_kms=result['relative_velocity_kms'],
        collision_probability=probability,
        tumbling_rate_dps=2.0,
        prediction_uncertainty_m=100.0
    )

    # Example physical properties from Member 2 dataset
    size_cm = 25.0
    tumbling_rate_dps = 2.0

    capture = evaluate_capture_feasibility(
        size_cm=size_cm,
        relative_velocity_kms=result['relative_velocity_kms'],
        tumbling_rate_dps=tumbling_rate_dps
    )

    print('\n===== MISSION RISK ANALYSIS =====')
    print('Target:', name)

    print(
        f"Closest Distance : {result['closest_distance_m']:.2f} m"
    )

    print(
        f"Time to Closest Approach : {result['time_to_closest_approach_s']:.2f} s"
    )

    print(
        f"Relative Velocity : {result['relative_velocity_kms']:.3f} km/s"
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


if __name__ == '__main__':
    main()