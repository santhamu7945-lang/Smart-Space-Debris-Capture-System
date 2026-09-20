"""
Target Selection Module
Selects one debris target from multiple tracked candidates.
"""

from typing import Dict, List, Optional


def select_target(candidates: List[Dict]) -> Optional[Dict]:
    """
    Select the most suitable debris target from the candidate list.

    Selection is based on:
    1. Capture feasibility
    2. Capture score
    3. Risk score
    4. Closest approach distance
    """

    # Keep only targets that can be captured
    feasible_targets = [
        candidate
        for candidate in candidates
        if candidate['capture_feasible']
    ]

    # No feasible target
    if not feasible_targets:
        return None

    # Sort candidates using project criteria
    feasible_targets.sort(
        key=lambda candidate: (
            -candidate['capture_score'],
            candidate['risk_score'],
            candidate['closest_distance_m']
        )
    )

    return feasible_targets[0]