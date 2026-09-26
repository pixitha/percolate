"""Serialized gameplay state.

This module contains the data-only state boundary used by persistence. Player
actions and gameplay queries live in :class:`percolate.engine.game.GameEngine`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from percolate.config import (
    DEFAULT_LOCATION_ID,
    DEFAULT_PLOT_COUNT,
    DEFAULT_STARTING_GOLD,
    DEFAULT_UNLOCKED_BEANS,
)
from percolate.models.plot import Plot
from percolate.models.roast import RoastBatch


@dataclass
class RoastedProduct:
    name: str
    value: int
    recipe_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RoastedProduct":
        return cls(name=data["name"], value=data["value"], recipe_id=data.get("recipe_id"))


@dataclass
class GameState:
    gold: int = DEFAULT_STARTING_GOLD
    plots: list[Plot] = field(default_factory=list)
    seed_inventory: dict[str, int] = field(default_factory=dict)
    raw_bean_inventory: dict[str, int] = field(default_factory=dict)
    ingredient_inventory: dict[str, int] = field(default_factory=dict)
    roast_batches: list[RoastBatch] = field(default_factory=list)
    roasted_inventory: list[RoastedProduct] = field(default_factory=list)
    owned_upgrades: dict[str, int] = field(default_factory=dict)
    discovered_recipes: set[str] = field(default_factory=set)
    unlocked_beans: set[str] = field(default_factory=lambda: set(DEFAULT_UNLOCKED_BEANS))
    location_id: str = DEFAULT_LOCATION_ID
    location_selected: bool = False
    weather_id: str = "clear"
    weather_started_at: float = 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["discovered_recipes"] = sorted(self.discovered_recipes)
        data["unlocked_beans"] = sorted(self.unlocked_beans)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        return cls(
            gold=data.get("gold", DEFAULT_STARTING_GOLD),
            plots=[Plot.from_dict(plot) for plot in data.get("plots", [])],
            seed_inventory=data.get("seed_inventory", {}),
            raw_bean_inventory=data.get("raw_bean_inventory", {}),
            ingredient_inventory=data.get("ingredient_inventory", {}),
            roast_batches=[RoastBatch.from_dict(batch) for batch in data.get("roast_batches", [])],
            roasted_inventory=[RoastedProduct.from_dict(product) for product in data.get("roasted_inventory", [])],
            owned_upgrades=data.get("owned_upgrades", {}),
            discovered_recipes=set(data.get("discovered_recipes", [])),
            unlocked_beans=set(data.get("unlocked_beans", DEFAULT_UNLOCKED_BEANS)),
            location_id=data.get("location_id", DEFAULT_LOCATION_ID),
            # Saves written before the starting-location choice existed already
            # have an established home; do not interrupt those players.
            location_selected=data.get("location_selected", True),
            weather_id=data.get("weather_id", "clear"),
            weather_started_at=data.get("weather_started_at", 0.0),
        )

    @classmethod
    def new_default(cls) -> "GameState":
        return cls(plots=[Plot() for _ in range(DEFAULT_PLOT_COUNT)])


__all__ = ["GameState", "RoastedProduct"]
