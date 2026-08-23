"""
TLE Loader Module
Reads and validates Two-Line Element orbital data.
"""

from pathlib import Path
from typing import Tuple

from sgp4.api import Satrec


class TLEFormatError(Exception):
    """Raised when TLE format is invalid."""


def load_tle(tle_path: Path) -> Tuple[str, str, str]:

    if not tle_path.exists():
        raise FileNotFoundError(f'TLE file not found: {tle_path}')

    with open(tle_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]

    if len(lines) < 3:
        raise TLEFormatError('TLE file must contain at least 3 lines.')

    name, line1, line2 = lines[0], lines[1], lines[2]

    if not line1.startswith('1 '):
        raise TLEFormatError('Invalid TLE line 1.')

    if not line2.startswith('2 '):
        raise TLEFormatError('Invalid TLE line 2.')

    return name, line1, line2


def create_satellite(line1: str, line2: str) -> Satrec:
    return Satrec.twoline2rv(line1, line2)