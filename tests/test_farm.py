import json
from dataclasses import dataclass

import pytest

from percolate.content.catalog import ContentCatalog
from percolate.engine.game import GameEngine
from percolate.engine.state import GameState
from percolate.persistence.json_store import JsonStateStore


@dataclass
class FixedClock:
    value: float = 100.0

    def now(self) -> float:
        return self.value


@pytest.fixture
def engine(tmp_path):
    return GameEngine(
        state=GameState.new_default(),
        content=ContentCatalog.load_default(),
        clock=FixedClock(),
        store=JsonStateStore(tmp_path / "state.json"),
    )


def test_default_farm_has_starting_plots_and_gold() -> None:
    state = GameState.new_default()

    assert state.gold == 30
    assert len(state.plots) == 3
    assert all(plot.is_empty for plot in state.plots)


def test_seed_plant_harvest_and_sell_loop(engine) -> None:
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")

    assert engine.state.gold == 22
    assert engine.state.seed_inventory["bourbon"] == 0
    with pytest.raises(ValueError, match="not ready"):
        engine.harvest(0)

    engine.clock.value += engine.state.plots[0].process.duration
    assert engine.harvest(0) == "bourbon"
    engine.sell_raw("bourbon")

    assert engine.state.gold == 36
    assert engine.state.raw_bean_inventory["bourbon"] == 0


def test_roast_collects_recipe_and_sells_product(engine) -> None:
    engine.state.gold = 2000
    engine.purchase_upgrade("roaster_slot")
    engine.state.raw_bean_inventory["bourbon"] = 1
    engine.state.ingredient_inventory["caramel"] = 1

    engine.start_roast("bourbon", ["caramel"], "dark")

    with pytest.raises(ValueError, match="not ready"):
        engine.collect_roast(0)

    engine.clock.value += 3600
    product = engine.collect_roast(0)

    assert product.recipe_id == "bourbon_reserve"
    assert product.name == "Bourbon Caramel Reserve"
    assert engine.state.discovered_recipes == {"bourbon_reserve"}
    assert engine.state.roast_batches == []
    engine.sell_product(0)
    assert engine.state.gold == 2000 - 1000 + product.value


def test_insufficient_resources_do_not_mutate_state(engine) -> None:
    engine.state.gold = 0

    with pytest.raises(ValueError, match="Not enough gold"):
        engine.buy_seed("typica")
    assert engine.state.gold == 0

    with pytest.raises(ValueError, match="No seeds"):
        engine.plant(0, "bourbon")
    assert engine.state.plots[0].is_empty

    with pytest.raises(ValueError, match="No raw beans"):
        engine.state.owned_upgrades["roaster_slot"] = 1
        engine.start_roast("bourbon", ["vanilla"], "medium")
    assert engine.state.roast_batches == []


def test_upgrade_effects_and_persistence(tmp_path) -> None:
    state = GameState.new_default()
    state.gold = 10_000
    store = JsonStateStore(tmp_path / "state.json")
    engine = GameEngine(state=state, content=ContentCatalog.load_default(), clock=FixedClock(), store=store)

    engine.purchase_upgrade("soil_quality")
    engine.purchase_upgrade("infuser")
    engine.purchase_upgrade("roaster_slot")
    engine.purchase_upgrade("plot_expansion")
    engine.purchase_upgrade("plot_expansion")
    engine.save()

    restored = store.load()
    restored_engine = GameEngine(
        state=restored,
        content=ContentCatalog.load_default(),
        clock=FixedClock(),
    )

    assert restored.to_dict() == json.loads((tmp_path / "state.json").read_text())
    assert restored_engine.max_ingredients() == 1
    assert restored_engine.max_roast_slots() == 1
    assert len(restored.plots) == 6


def test_persistence_preserves_active_processes_and_discovered_recipes(tmp_path) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    clock = FixedClock()
    engine = GameEngine(
        state=GameState.new_default(),
        content=ContentCatalog.load_default(),
        clock=clock,
        store=store,
    )
    engine.state.gold = 2000
    engine.purchase_upgrade("roaster_slot")
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")
    engine.state.raw_bean_inventory["bourbon"] = 1
    engine.state.ingredient_inventory["caramel"] = 1
    clock.value = 200.0
    engine.start_roast("bourbon", ["caramel"], "dark")
    engine.state.discovered_recipes.add("bourbon_reserve")
    engine.save()

    restored = store.load()

    assert restored.plots[0].bean_id == "bourbon"
    assert restored.plots[0].process.started_at == 100.0
    assert restored.plots[0].process.duration == pytest.approx(3600 * 0.95)
    assert restored.roast_batches[0].bean_id == "bourbon"
    assert restored.roast_batches[0].process.started_at == 200.0
    assert restored.roast_batches[0].process.duration == 3600.0
    assert restored.discovered_recipes == {"bourbon_reserve"}


def test_saved_state_has_stable_top_level_schema(tmp_path) -> None:
    state = GameState.new_default()
    path = tmp_path / "state.json"
    JsonStateStore(path).save(state)

    assert set(json.loads(path.read_text())) == {
        "gold",
        "plots",
        "seed_inventory",
        "raw_bean_inventory",
        "ingredient_inventory",
        "roast_batches",
        "roasted_inventory",
        "owned_upgrades",
        "discovered_recipes",
        "unlocked_beans",
        "location_id",
        "location_selected",
        "weather_id",
        "weather_started_at",
    }


def test_debug_time_advancement_rewinds_all_active_processes(engine) -> None:
    engine.state.gold = 2000
    engine.purchase_upgrade("roaster_slot")
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")
    engine.state.raw_bean_inventory["bourbon"] = 1
    engine.start_roast("bourbon", [], "medium")

    engine.advance_debug_time(30.0)

    assert engine.state.plots[0].process.started_at == 70.0
    assert engine.state.roast_batches[0].process.started_at == 70.0


def test_missing_state_file_loads_new_default_farm(tmp_path) -> None:
    restored = JsonStateStore(tmp_path / "missing.json").load()

    assert restored == GameState.new_default()


def test_legacy_state_without_optional_fields_still_loads() -> None:
    restored = GameState.from_dict({"gold": 17, "plots": []})

    assert restored.gold == 17
    assert restored.seed_inventory == {}
    assert restored.discovered_recipes == set()
    assert restored.unlocked_beans == {"typica", "caturra", "bourbon", "yirgacheffe"}
    assert restored.location_id == "highland_estate"
    assert restored.location_selected is True
    assert restored.weather_id == "clear"
    assert restored.weather_started_at == 0.0
