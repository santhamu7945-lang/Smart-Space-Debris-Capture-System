import json
from pathlib import Path


class MissionStateMachine:

    def __init__(self, file_path: Path):

        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        self.current_state = data['current_state']
        self.transitions = data['allowed_transitions']
        self.file_path = file_path

    def transition(self, next_state: str):

        allowed = self.transitions.get(self.current_state, [])

        if next_state not in allowed:
            raise ValueError(
                f'Invalid transition: {self.current_state} -> {next_state}'
            )

        self.current_state = next_state

        self._save()

    def _save(self):

        data = {
            'current_state': self.current_state,
            'allowed_transitions': self.transitions
        }

        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)

    def __str__(self):

        return f'Current State: {self.current_state}'