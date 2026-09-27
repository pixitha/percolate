"""App entry point, screen router, global tick loop."""

from __future__ import annotations

from textual.app import App

from percolate.backdrop_compositor import load_farmhouse_data
from percolate.config import DEV_MODE, PACKAGE_DIR, UI_TICK_SECONDS
from percolate.content.art import load_plant_stage_art, load_roast_stage_art
from percolate.content.catalog import ContentCatalog
from percolate.engine.game import GameEngine
from percolate.screens.farm_screen import FarmScreen
from percolate.screens.help_modal import HelpModal
from percolate.screens.location_modal import LocationChoiceModal
from percolate.screens.market_screen import MarketScreen
from percolate.screens.roast_screen import RoastScreen
from percolate.theme import ALL_THEMES, theme_for_location


class PercolateApp(App):
    TITLE = "Percolate"
    CSS_PATH = "percolate.tcss"
    # Textual resolves a relative CSS_PATH via inspect.getfile(type(self)).
    # _BASE_PATH is Textual's documented override for that — point it at
    # config.PACKAGE_DIR, which already knows how to find the real, on-disk
    # package directory whether running from source or a Nuitka build.
    _BASE_PATH = str(PACKAGE_DIR / "main.py")

    SCREENS = {
        "farm": FarmScreen,
        "roast": RoastScreen,
        "market": MarketScreen,
    }

    BINDINGS = [
        ("f", "show_screen('farm')", "Farm"),
        ("r", "show_screen('roast')", "Roast"),
        ("m", "show_screen('market')", "Market"),
        ("h", "show_help", "Help"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        for theme in ALL_THEMES:
            self.register_theme(theme)
        self.content = ContentCatalog.load_default()
        self.engine = GameEngine.load_default(content=self.content)
        self.theme = theme_for_location(self.engine.state.location_id)
        self.plant_stages = load_plant_stage_art()
        self.farmhouse_data = load_farmhouse_data()
        self.roast_stages = load_roast_stage_art()

        if DEV_MODE:
            self.bind("right_square_bracket", "dev_skip_small", description="Dev: +15m")
            self.bind("left_square_bracket", "dev_skip_large", description="Dev: +6h")
            self.bind("g", "dev_add_gold", description="Dev: +1000g")
            self.bind("l", "dev_next_location", description="Dev: next location")
            self.bind("shift+l", "dev_previous_location", description="Dev: previous location")
            self.bind("w", "dev_next_weather", description="Dev: next weather")
            self.bind("shift+w", "dev_previous_weather", description="Dev: previous weather")

    def on_mount(self) -> None:
        self.push_screen("farm")
        self.update_subtitle()
        if not self.engine.state.location_selected:
            self.push_screen(LocationChoiceModal(), self._finish_location_choice)
        self.set_interval(UI_TICK_SECONDS, self.update_subtitle)

    def _finish_location_choice(self, location_id: str | None) -> None:
        if location_id is None:
            return
        self.engine.set_location(location_id)
        self.engine.save()
        self.update_subtitle()
        self.notify(f"Home region: {self.engine.location.name}")

    def update_subtitle(self) -> None:
        self.theme = theme_for_location(self.engine.state.location_id)
        self.sub_title = f"{self.engine.state.gold}g"

    def action_show_screen(self, name: str) -> None:
        self.switch_screen(name)

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    def action_quit(self) -> None:
        self.engine.save()
        self.exit()

    # --- Dev tools (PERCOLATE_DEV=1 only) --------------------------------

    def _dev_refresh_screen(self) -> None:
        # Give immediate feedback rather than waiting for the next 5s tick.
        screen = self.screen
        if hasattr(screen, "_update_location_label"):
            screen._update_location_label()
        if hasattr(screen, "_render_backdrop"):
            screen._render_backdrop()
        if hasattr(screen, "refresh_plots"):
            screen.refresh_plots()
        if hasattr(screen, "refresh_batches"):
            screen.refresh_batches()
        if hasattr(screen, "refresh_market"):
            self.run_worker(screen.refresh_market(), exclusive=False)

    def action_dev_skip_small(self) -> None:
        self.engine.advance_debug_time(15 * 60)
        self.engine.save()
        self._dev_refresh_screen()
        self.notify("Dev: skipped 15 minutes")

    def action_dev_skip_large(self) -> None:
        self.engine.advance_debug_time(6 * 3600)
        self.engine.save()
        self._dev_refresh_screen()
        self.notify("Dev: skipped 6 hours")

    def action_dev_add_gold(self) -> None:
        self.engine.state.gold += 1000
        self.engine.save()
        self.update_subtitle()
        self.notify("Dev: +1000g")

    def action_dev_next_location(self) -> None:
        self.engine.cycle_location()
        self.engine.save()
        self._dev_refresh_screen()
        self.update_subtitle()
        self.notify(f"Dev: location → {self.engine.location.name}")

    def action_dev_previous_location(self) -> None:
        self.engine.cycle_location(-1)
        self.engine.save()
        self._dev_refresh_screen()
        self.update_subtitle()
        self.notify(f"Dev: location → {self.engine.location.name}")

    def action_dev_next_weather(self) -> None:
        self.engine.cycle_weather()
        self.engine.save()
        self._dev_refresh_screen()
        self.notify(f"Dev: weather → {self.engine.weather.name}")

    def action_dev_previous_weather(self) -> None:
        self.engine.cycle_weather(-1)
        self.engine.save()
        self._dev_refresh_screen()
        self.notify(f"Dev: weather → {self.engine.weather.name}")


def main() -> None:
    PercolateApp().run()


if __name__ == "__main__":
    main()
