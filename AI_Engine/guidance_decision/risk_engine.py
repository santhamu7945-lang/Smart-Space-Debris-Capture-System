"""
Mission Risk Engine
Computes a normalized mission risk score.
"""

from typing import Dict


def compute_risk_score(
    closest_distance_m: float,
    relative_velocity_kms: float,
    collision_probability: float,
    tumbling_rate_dps: float = 0.0,
    prediction_uncertainty_m: float = 100.0
) -> Dict[str, float]:

    # Normalize distance risk
    distance_risk = max(0.0, 1.0 - closest_distance_m / 10000.0)

    # Normalize velocity risk
    velocity_risk = min(relative_velocity_kms / 10.0, 1.0)

    # Normalize tumbling risk
    tumbling_risk = min(tumbling_rate_dps / 30.0, 1.0)

    # Normalize uncertainty risk
    uncertainty_risk = min(prediction_uncertainty_m / 1000.0, 1.0)

    probability_risk = min(collision_probability, 1.0)

    # Weighted mission risk score
    risk_score = (
        0.35 * distance_risk +
        0.25 * velocity_risk +
        0.20 * probability_risk +
        0.10 * tumbling_risk +
        0.10 * uncertainty_risk
    ) * 100.0

    # Risk level classification
    if risk_score < 25:
        risk_level = 'LOW'
    elif risk_score < 50:
        risk_level = 'MEDIUM'
    elif risk_score < 75:
        risk_level = 'HIGH'
    else:
        risk_level = 'CRITICAL'

    return {
        'risk_score': round(risk_score, 2),
        'risk_level': risk_level
    }