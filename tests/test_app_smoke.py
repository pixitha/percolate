import asyncio

from textual.widgets import ListView, OptionList

from percolate.main import PercolateApp
from percolate.engine.state import GameState as Farm
from percolate.persistence.json_store import JsonStateStore
from percolate.screens.farm_screen import FarmScreen
from percolate.screens.help_modal import HelpModal
from percolate.screens.market_screen import MarketScreen
from percolate.screens.roast_screen import RoastScreen
from percolate.screens.upgrade_modal import UpgradeModal


def _run_app(monkeypatch, scenario) -> None:
    """Run a scenario against an isolated, non-persisting application."""

    def fresh_state():
        state = Farm.new_default()
        state.location_selected = True
        return state

    monkeypatch.setattr(JsonStateStore, "load", lambda self: fresh_state())
    monkeypatch.setattr(JsonStateStore, "save", lambda self, state: None)

    async def run() -> None:
        async with PercolateApp().run_test(size=(120, 40)) as pilot:
            await scenario(pilot)

    asyncio.run(run())


def test_app_starts_on_farm_and_builds_plot_field(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app

        assert isinstance(app.screen, FarmScreen)
        assert len(app.screen._cells) == len(app.engine.state.plots)
        assert app.screen.query_one("#field")
        assert app.screen.query_one("#backdrop")

    _run_app(monkeypatch, scenario)


def test_global_screen_navigation_mounts_each_screen(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app

        await pilot.press("r")
        assert isinstance(app.screen, RoastScreen)
        assert app.screen.query_one("#builder_panel")

        await pilot.press("m")
        assert isinstance(app.screen, MarketScreen)
        assert app.screen.query_one("#buy_seeds", ListView)
        assert app.screen.query_one("#sell_products", ListView)

        await pilot.press("f")
        assert isinstance(app.screen, FarmScreen)

    _run_app(monkeypatch, scenario)


def test_help_modal_opens_and_closes(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app

        await pilot.press("h")
        assert isinstance(app.screen, HelpModal)
        assert app.screen.query_one("#help_picker")

        await pilot.press("escape")
        assert isinstance(app.screen, FarmScreen)

    _run_app(monkeypatch, scenario)


def test_market_enter_buys_one_seed(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app
        await pilot.press("m")
        market = app.screen
        buy_seeds = market.query_one("#buy_seeds", ListView)
        buy_seeds.focus()

        await pilot.press("enter")

        assert app.engine.state.gold == 24
        assert app.engine.state.seed_inventory["typica"] == 1

    _run_app(monkeypatch, scenario)


def test_market_seed_listing_shows_base_and_current_grow_times(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app
        await pilot.press("m")
        market = app.screen
        buy_seeds = market.query_one("#buy_seeds", ListView)
        first_listing = buy_seeds.children[0].query_one("Label")

        listing = str(first_listing.render())
        assert "grow 45m base /" in listing
        assert "here" in listing

    _run_app(monkeypatch, scenario)


def test_farm_upgrade_modal_can_purchase_plot_expansion(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app
        app.engine.state.gold = 1000

        await pilot.press("u")
        assert isinstance(app.screen, UpgradeModal)
        upgrade_list = app.screen.query_one("#upgrade_list", ListView)
        upgrade_list.focus()

        await pilot.press("enter")

        assert app.engine.upgrade_tier("plot_expansion") == 1
        assert len(app.engine.state.plots) == 4
        await pilot.press("escape")
        assert isinstance(app.screen, FarmScreen)

    _run_app(monkeypatch, scenario)


def test_roast_screen_builder_has_expected_controls(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app
        await pilot.press("r")
        roast = app.screen

        assert roast.query_one("#bean_list", OptionList)
        assert roast.query_one("#flavor_list")
        assert roast.query_one("#level_list", OptionList)
        assert roast.query_one("#start_button")
        assert roast.query_one("#recipe_list")

    _run_app(monkeypatch, scenario)


def test_roast_builder_supports_arrow_field_navigation_and_requires_level(monkeypatch) -> None:
    async def scenario(pilot) -> None:
        app = pilot.app
        app.engine.state.raw_bean_inventory["bourbon"] = 1
        await pilot.press("r")
        roast = app.screen
        bean_list = roast.query_one("#bean_list", OptionList)
        flavor_list = roast.query_one("#flavor_list")
        level_list = roast.query_one("#level_list", OptionList)

        assert bean_list.has_focus
        await pilot.press("right")
        assert flavor_list.has_focus
        await pilot.press("right")
        assert level_list.has_focus

        await pilot.press("s")
        assert app.engine.state.roast_batches == []

        await pilot.press("enter")
        await pilot.press("s")
        assert app.engine.state.roast_batches[0].roast_level == "light"

    _run_app(monkeypatch, scenario)
