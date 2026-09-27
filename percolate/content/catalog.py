"""Load the data-driven content used by Percolate.

This is deliberately separate from the Textual app. The engine needs gameplay
definitions, while screens can load art and help text independently.
"""

from __future__ import annotations

from dataclasses import dataclass

from percolate.models.bean import Bean, load_bean_registry
from percolate.config import LOCATIONS_PATH, UPGRADES_PATH, WEATHER_PATH
from percolate.models.roast import (
    Ingredient,
    Recipe,
    load_ingredient_registry,
    load_recipe_registry,
)


@dataclass(frozen=True)
class ContentCatalog:
    beans: dict[str, Bean]
    ingredients: dict[str, Ingredient]
    recipes: dict[str, Recipe]
    upgrades: dict
    locations: dict[str, "Location"]
    weather: dict[str, "Weather"]

    @classmethod
    def load_default(cls) -> "ContentCatalog":
        return cls(
            beans=load_bean_registry(),
            ingredients=load_ingredient_registry(),
            recipes=load_recipe_registry(),
            upgrades=_load_json(UPGRADES_PATH),
            locations=_load_location_registry(),
            weather=_load_weather_registry(),
        )


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: str
    growth_speed_bonus: float = 0.0
    quality_modifier: float = 0.0
    weather_ids: tuple[str, ...] = ("clear",)

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            growth_speed_bonus=data.get("growth_speed_bonus", 0.0),
            quality_modifier=data.get("quality_modifier", 0.0),
            weather_ids=tuple(data.get("weather", ["clear"])),
        )


@dataclass(frozen=True)
class Weather:
    id: str
    name: str
    description: str
    duration: float
    growth_speed_bonus: float = 0.0
    quality_modifier: float = 0.0
    color: str = "grey70"
    overlays: tuple[dict, ...] = ()
    animation_frames: tuple[tuple[dict, ...], ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "Weather":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            duration=data.get("duration", 900),
            growth_speed_bonus=data.get("growth_speed_bonus", 0.0),
            quality_modifier=data.get("quality_modifier", 0.0),
            color=data.get("color", "grey70"),
            overlays=tuple(data.get("overlays", [])),
            animation_frames=tuple(tuple(frame) for frame in data.get("animation", [])),
        )


def _load_location_registry(path=LOCATIONS_PATH) -> dict[str, Location]:
    raw = _load_json(path)
    return {location_id: Location.from_dict(entry) for location_id, entry in raw.items()}


def _load_weather_registry(path=WEATHER_PATH) -> dict[str, Weather]:
    raw = _load_json(path)
    return {weather_id: Weather.from_dict(entry) for weather_id, entry in raw.items()}


def _load_json(path) -> dict:
    import json

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
