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
def propagate_gp_record(gp_record, seconds_ahead):
    """
    Propagate an orbit directly from a GP orbital-data record.

    Parameters:
        gp_record: Dictionary containing GP orbital elements.
        seconds_ahead: Prediction time in seconds.

    Returns:
        Dictionary containing predicted position and velocity.
    """

    import math
    from datetime import datetime, timedelta, timezone
    from sgp4.api import Satrec, WGS72, jday

    # Read orbital elements
    satnum = int(gp_record["NORAD_CAT_ID"])

    bstar = float(gp_record["BSTAR"])
    eccentricity = float(gp_record["ECCENTRICITY"])

    inclination = math.radians(
        float(gp_record["INCLINATION"])
    )

    raan = math.radians(
        float(gp_record["RA_OF_ASC_NODE"])
    )

    arg_pericenter = math.radians(
        float(gp_record["ARG_OF_PERICENTER"])
    )

    mean_anomaly = math.radians(
        float(gp_record["MEAN_ANOMALY"])
    )

    # Mean motion: revolutions/day → radians/minute
    mean_motion = (
        float(gp_record["MEAN_MOTION"])
        * 2.0
        * math.pi
        / 1440.0
    )

    # GP epoch
    epoch_time = datetime.fromisoformat(
        gp_record["EPOCH"]
    ).replace(tzinfo=timezone.utc)

    jd, fr = jday(
        epoch_time.year,
        epoch_time.month,
        epoch_time.day,
        epoch_time.hour,
        epoch_time.minute,
        epoch_time.second
        + epoch_time.microsecond / 1e6
    )

    # SGP4 epoch is measured from 1949-12-31
    epoch = (jd + fr) - 2433281.5

    # Create SGP4 satellite
    satellite = Satrec()

    satellite.sgp4init(
        WGS72,
        "i",
        satnum,
        epoch,
        bstar,
        0.0,
        0.0,
        eccentricity,
        arg_pericenter,
        inclination,
        mean_anomaly,
        mean_motion,
        raan
    )

    # Prediction time
    target_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=seconds_ahead)
    )

    jd_target, fr_target = jday(
        target_time.year,
        target_time.month,
        target_time.day,
        target_time.hour,
        target_time.minute,
        target_time.second
        + target_time.microsecond / 1e6
    )

    # Propagate
    error, position, velocity = satellite.sgp4(
        jd_target,
        fr_target
    )

    if error != 0:
        raise RuntimeError(
            f"SGP4 propagation error: {error}"
        )

    return {
        "position_km": position,
        "velocity_kms": velocity,
        "prediction_horizon_s": seconds_ahead
    }