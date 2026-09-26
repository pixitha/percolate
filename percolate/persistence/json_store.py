"""JSON persistence for the gameplay state.

The store owns filesystem access; the game model only owns serialization and
rules. The existing Farm JSON shape is intentionally preserved while the
engine refactor is in progress.
"""

from __future__ import annotations

import json
from pathlib import Path

from percolate.config import STATE_PATH
from percolate.engine.state import GameState


class JsonStateStore:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = Path(path)

    def load(self) -> GameState:
        if not self.path.exists():
            return GameState.new_default()
        with self.path.open("r", encoding="utf-8") as file:
            return GameState.from_dict(json.load(file))

    def save(self, state: GameState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(state.to_dict(), file, indent=2)
