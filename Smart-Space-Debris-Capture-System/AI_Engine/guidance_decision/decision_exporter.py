"""
Mission Decision Exporter
Writes mission decision to telemetry JSON.
"""

import json
from pathlib import Path


def export_decision(
    file_path: Path,
    mission_data: dict
):

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(mission_data, file, indent=2)