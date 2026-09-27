"""Capture one Farm-screen screenshot for every location palette.

Usage:
    python tools/capture_location_screenshots.py /tmp/percolate-location-shots

The capture set deliberately includes two clear scenes and two storm scenes so
the artifacts demonstrate both the location palettes and the weather art.
The app runs headlessly with an in-memory fresh save, so this never touches
the player's real ~/.config/percolate state.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from percolate.engine.state import GameState
from percolate.main import PercolateApp
from percolate.persistence.json_store import JsonStateStore
from percolate.theme import LOCATION_THEMES


SCREENSHOT_WEATHER = {
    "highland_estate": "clear",
    "dry_mountain_valley": "clear",
    "tropical_lowland": "rain",
    "volcanic_island": "storm",
}


def colorize_export(svg: str, location_id: str) -> str:
    """Restore the location palette lost by Textual's headless compositor.

    The compositor currently reduces widget colors to a grayscale terminal
    palette before Rich serializes the SVG. Background and foreground values
    are still structurally correct, so map those known grayscale buckets back
    to the active Textual theme for useful visual review artifacts.
    """
    theme = LOCATION_THEMES[location_id]
    palette = {
        "#1e1e1e": theme.background,
        "#191919": theme.background,
        "#2d2d2d": theme.surface,
        "#242424": theme.surface,
        "#2f2f2f": theme.panel,
        "#2b2b2b": theme.panel,
        "#b3b3b3": theme.primary,
        "#808080": theme.secondary,
        "#868686": theme.secondary,
        "#717171": theme.secondary,
        "#c5c8c6": theme.foreground,
        "#d0d0d0": theme.foreground,
        "#e8e8e8": theme.foreground,
        "#e1e1e1": theme.foreground,
    }
    for source, target in palette.items():
        svg = svg.replace(source, target)
    return svg


async def capture(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    original_load = JsonStateStore.load
    original_save = JsonStateStore.save

    def fresh_captured_state() -> GameState:
        state = GameState.new_default()
        state.location_selected = True
        return state

    JsonStateStore.load = lambda self: fresh_captured_state()  # type: ignore[method-assign]
    JsonStateStore.save = lambda self, state: None  # type: ignore[method-assign]
    try:
        async with PercolateApp().run_test(size=(120, 40)) as pilot:
            app = pilot.app
            for location_id in app.engine.content.locations:
                app.engine.set_location(location_id)
                app.engine.set_weather(SCREENSHOT_WEATHER[location_id])
                app.screen._update_location_label()
                app.screen._render_backdrop()
                app.update_subtitle()
                await pilot.pause()
                filename = f"farm-{location_id}.svg"
                svg_path = Path(app.save_screenshot(filename=filename, path=str(output_dir)))
                svg_path.write_text(
                    colorize_export(svg_path.read_text(encoding="utf-8"), location_id),
                    encoding="utf-8",
                )
                print(output_dir / filename)
    finally:
        JsonStateStore.load = original_load  # type: ignore[method-assign]
        JsonStateStore.save = original_save  # type: ignore[method-assign]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    asyncio.run(capture(args.output_dir))


if __name__ == "__main__":
    main()
