import json
from pathlib import Path

# Path to processed debris dataset
DATA_FILE = Path('DATA/processed/debris_state.json')


def load_first_debris():
    """Load the first debris object from the dataset."""
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    return data[0]


def load_debris_by_name(target_name: str):
    """Load a debris object by its name."""
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    for obj in data:
        if obj['name'] == target_name:
            return obj

    raise ValueError(f'Debris object {target_name} not found in dataset.')