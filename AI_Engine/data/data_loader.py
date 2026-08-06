"""
Debris State Data Loader
Loads processed debris catalog from Member 2 dataset.
"""

import json
from pathlib import Path
from typing import Dict, List


DATA_FILE = Path('DATA/processed/debris_state.json')


def load_debris_catalog() -> List[Dict]:

    with open(DATA_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)


def load_first_debris() -> Dict:

    catalog = load_debris_catalog()

    if not catalog:
        raise ValueError('Debris catalog is empty')

    return catalog[0]