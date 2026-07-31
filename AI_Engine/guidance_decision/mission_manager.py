"""
Mission Manager
Generates final autonomous mission decision.
"""

from typing import Dict


def generate_mission_decision(
    risk_level: str,
    capture_feasible: bool,
    capture_score: float
) -> Dict[str, str]:

    if risk_level == 'CRITICAL':
        decision = 'ABORT'
        reason = 'Critical collision risk'

    elif not capture_feasible:
        decision = 'ABORT'
        reason = 'Capture not feasible'

    elif capture_score < 60:
        decision = 'HOLD'
        reason = 'Capture score below operational threshold'

    else:
        decision = 'CAPTURE'
        reason = 'Target approved for capture'

    return {
        'decision': decision,
        'reason': reason
    }