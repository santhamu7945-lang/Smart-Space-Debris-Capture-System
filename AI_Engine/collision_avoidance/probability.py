"""
Collision Probability Estimation Module
Simple Gaussian-based probability approximation.
"""

import math


def collision_probability(
    closest_distance_m: float,
    sigma_m: float = 100.0
) -> float:

    probability = math.exp(
        -(closest_distance_m ** 2) / (2 * sigma_m ** 2)
    )

    return float(probability)