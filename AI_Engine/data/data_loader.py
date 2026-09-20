import json
from pathlib import Path

# Existing single-debris dataset
DATA_FILE = Path('DATA/processed/debris_state.json')

# New multi-debris tracking dataset
MULTI_DATA_FILE = Path('DATA/processed/multi_tracking_state.json')


def load_first_debris():
    """Load the first debris object from the single-debris dataset."""
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    return data[0]


def load_debris_by_name(target_name: str):
    """Load a debris object by its name from the single-debris dataset."""
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    for obj in data:
        if obj['name'] == target_name:
            return obj

    raise ValueError(f'Debris object {target_name} not found in dataset.')


def load_all_tracked_debris():
    """Load all tracked debris objects from the multi-debris dataset."""
    with open(MULTI_DATA_FILE, 'r') as f:
        data = json.load(f)

    return data


def load_tracked_debris_by_id(tracking_id: str):
    """Load one tracked debris object using its tracking ID."""
    data = load_all_tracked_debris()

    for obj in data:
        if obj['tracking_id'] == tracking_id:
            return obj

    raise ValueError(
        f'Tracked debris {tracking_id} not found in multi-tracking dataset.'
    )