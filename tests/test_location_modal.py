import asyncio

from percolate.engine.state import GameState
from percolate.main import PercolateApp
from percolate.persistence.json_store import JsonStateStore
from percolate.screens.location_modal import LocationChoiceModal


def test_new_farm_prompts_for_home_location(monkeypatch) -> None:
    monkeypatch.setattr(JsonStateStore, "load", lambda self: GameState.new_default())
    monkeypatch.setattr(JsonStateStore, "save", lambda self, state: None)

    async def run() -> None:
        async with PercolateApp().run_test(size=(120, 40)) as pilot:
            assert isinstance(pilot.app.screen, LocationChoiceModal)
            await pilot.press("down")
            await pilot.press("enter")
            assert pilot.app.engine.state.location_selected is True
            assert pilot.app.engine.state.location_id == "tropical_lowland"

    asyncio.run(run())
