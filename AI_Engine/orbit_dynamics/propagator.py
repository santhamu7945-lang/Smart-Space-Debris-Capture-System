"""
Orbit Propagation Module
Propagates TLE orbits using the SGP4 model.
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple

from sgp4.api import jday

from AI_Engine.orbit_dynamics.tle_loader import create_satellite


Vector3 = Tuple[float, float, float]


def propagate_tle(
    line1: str,
    line2: str,
    seconds_ahead: int
) -> Dict[str, Vector3]:

    satellite = create_satellite(line1, line2)

    target_time = datetime.utcnow() + timedelta(seconds=seconds_ahead)

    jd, fr = jday(
        target_time.year,
        target_time.month,
        target_time.day,
        target_time.hour,
        target_time.minute,
        target_time.second + target_time.microsecond / 1e6
    )

    error, position, velocity = satellite.sgp4(jd, fr)

    if error != 0:
        raise RuntimeError(f'SGP4 propagation error: {error}')

    return {
        'position_km': position,
        'velocity_kms': velocity
    }