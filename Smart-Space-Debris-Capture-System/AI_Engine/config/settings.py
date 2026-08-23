from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_FILE = PROJECT_ROOT / 'DATA' / 'processed' / 'debris_state.json'

TLE_FILE = PROJECT_ROOT / 'DATA' / 'raw' / 'cosmos2251.tle'

OUTPUT_DIR = PROJECT_ROOT / 'AI_Engine' / 'telemetry'

LOG_FILE = OUTPUT_DIR / 'mission.log'

SAFE_DISTANCE_M = 1000.0