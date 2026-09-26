"""Presentation assets loaded outside the gameplay engine."""

from __future__ import annotations

import json

from percolate.config import PLANT_STAGES_PATH, ROAST_STAGES_PATH


def load_plant_stage_art(path=PLANT_STAGES_PATH) -> dict[str, list[str]]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_roast_stage_art(path=ROAST_STAGES_PATH) -> dict[str, list[list[str]]]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
