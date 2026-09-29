"""
ADCS Visualization Pipeline Launcher

This launcher regenerates visualization telemetry.

Run:

python3 SIMULATION/main.py
"""

from pathlib import Path
import subprocess
import sys


SIMULATION_ROOT = Path(__file__).resolve().parent

EXPORTER = (
    SIMULATION_ROOT
    / "engine"
    / "export_for_visualization.py"
)


def main():

    result = subprocess.run(

        [
            sys.executable,
            str(EXPORTER)
        ],

        cwd=str(EXPORTER.parent)
    )

    return result.returncode


if __name__ == "__main__":

    raise SystemExit(main())