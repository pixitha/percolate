"""Compatibility exports for the pre-engine state module.

`Farm` remains a data-state alias only; gameplay actions belong to
`percolate.engine.GameEngine`.
"""

from percolate.engine.state import GameState, RoastedProduct

Farm = GameState

__all__ = ["Farm", "GameState", "RoastedProduct"]
