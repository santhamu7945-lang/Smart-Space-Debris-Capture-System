"""
Capture Feasibility Engine
Evaluates whether the debris can be captured by the robotic system.
"""

from typing import Dict


def evaluate_capture_feasibility(
    size_cm: float,
    relative_velocity_kms: float,
    tumbling_rate_dps: float
) -> Dict[str, object]:

    score = 100.0

    # Size factor
    if size_cm > 50:
        score -= 40
        method = 'robotic_net_large'
        difficulty = 'HIGH'

    elif size_cm > 15:
        score -= 20
        method = 'robotic_net'
        difficulty = 'MEDIUM'

    else:
        method = 'dual_arm'
        difficulty = 'LOW'

    # Relative velocity factor
    if relative_velocity_kms > 1.0:
        score -= 30

    # Tumbling factor
    if tumbling_rate_dps > 10:
        score -= 20

    score = max(0.0, min(score, 100.0))

    feasible = score >= 40.0

    return {
        'capture_method': method,
        'capture_score': round(score, 2),
        'capture_feasible': feasible,
        'difficulty_level': difficulty
    }