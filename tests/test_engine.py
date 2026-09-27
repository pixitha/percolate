from dataclasses import dataclass

import pytest

from percolate.content.catalog import ContentCatalog
from percolate.engine.game import GameEngine
from percolate.engine.state import GameState as Farm
from percolate.persistence.json_store import JsonStateStore


@dataclass
class FixedClock:
    value: float = 1000.0

    def now(self) -> float:
        return self.value


@pytest.fixture
def engine(tmp_path):
    return GameEngine(
        state=Farm.new_default(),
        content=ContentCatalog.load_default(),
        clock=FixedClock(),
        store=JsonStateStore(tmp_path / "state.json"),
    )


def test_engine_uses_ids_and_clock_for_planting(engine) -> None:
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")

    assert engine.state.seed_inventory["bourbon"] == 0
    assert engine.state.plots[0].process.started_at == 1000.0
    assert engine.state.plots[0].process.duration == pytest.approx(3600 * 0.95)


def test_engine_applies_growth_upgrade_to_new_plants(engine) -> None:
    engine.state.gold = 1000
    engine.purchase_upgrade("soil_quality")
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")

    assert engine.state.plots[0].process.duration == pytest.approx(3600 * 0.85)


def test_engine_location_changes_growth_and_quality_modifiers(engine) -> None:
    assert engine.location.id == "highland_estate"
    assert engine.growth_speed_bonus_for("bourbon") == pytest.approx(0.05)
    assert engine.quality_modifier_for("bourbon") == pytest.approx(0.04)

    engine.set_location("tropical_lowland")
    assert engine.growth_speed_bonus_for("bourbon") == pytest.approx(0.15)
    assert engine.quality_modifier_for("bourbon") == pytest.approx(-0.03)

    with pytest.raises(ValueError, match="Unknown location"):
        engine.set_location("moon_base")


def test_engine_location_affects_new_plant_duration(engine) -> None:
    engine.set_location("tropical_lowland")
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")

    assert engine.state.plots[0].process.duration == pytest.approx(3600 * 0.85)


def test_engine_weather_cycles_from_the_injected_clock(engine) -> None:
    assert engine.weather.id == "clear"
    assert engine.weather_modifier("growth_speed_bonus") == 0.0

    engine.clock.value += 900
    engine.refresh_weather()

    assert engine.weather.id == "drizzle"
    assert engine.weather_modifier("growth_speed_bonus") == pytest.approx(0.04)
    assert engine.growth_speed_bonus_for("bourbon") == pytest.approx(0.09)


def test_engine_location_resets_weather_to_that_region_cycle(engine) -> None:
    engine.set_location("dry_mountain_valley")

    assert engine.weather.id == "clear"
    assert engine.state.weather_started_at == engine.now


def test_engine_can_set_and_cycle_weather_for_current_location(engine) -> None:
    engine.set_weather("drizzle")
    assert engine.weather.id == "drizzle"
    assert engine.state.weather_started_at == engine.now

    engine.cycle_weather()
    assert engine.weather.id == "cool_snap"
    engine.cycle_weather(-1)
    assert engine.weather.id == "drizzle"

    with pytest.raises(ValueError, match="not available"):
        engine.set_weather("storm")


def test_engine_can_cycle_locations(engine) -> None:
    starting_location = engine.location.id

    engine.cycle_location()
    assert engine.location.id != starting_location
    assert engine.weather.id == "clear"

    engine.cycle_location(-1)
    assert engine.location.id == starting_location


def test_engine_starts_with_one_basic_roaster_slot(engine) -> None:
    engine.state.raw_bean_inventory["bourbon"] = 1

    engine.start_roast("bourbon", [], "medium")

    assert len(engine.state.roast_batches) == 1
    assert engine.state.raw_bean_inventory["bourbon"] == 0


def test_engine_blocks_a_roast_when_the_basic_slot_is_busy(engine) -> None:
    engine.state.raw_bean_inventory["bourbon"] = 2
    engine.start_roast("bourbon", [], "medium")

    with pytest.raises(ValueError, match="roaster slot"):
        engine.start_roast("bourbon", [], "medium")

    assert engine.state.raw_bean_inventory["bourbon"] == 1


def test_engine_rejects_non_positive_quantities_without_mutation(engine) -> None:
    engine.state.raw_bean_inventory["bourbon"] = 2
    starting_gold = engine.state.gold

    for action in (
        lambda: engine.buy_seed("bourbon", 0),
        lambda: engine.buy_ingredient("caramel", -1),
        lambda: engine.sell_raw("bourbon", 0),
    ):
        with pytest.raises(ValueError, match="positive"):
            action()

    assert engine.state.gold == starting_gold
    assert engine.state.raw_bean_inventory["bourbon"] == 2


def test_engine_rejects_invalid_actions_without_partial_mutation(engine) -> None:
    engine.state.gold = 30
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")

    with pytest.raises(ValueError, match="already planted"):
        engine.plant(0, "bourbon")
    with pytest.raises(ValueError, match="not unlocked"):
        engine.plant(0, "sl28")
    with pytest.raises(ValueError, match="Not enough raw beans"):
        engine.sell_raw("bourbon")

    engine.state.owned_upgrades["roaster_slot"] = 1
    engine.state.raw_bean_inventory["bourbon"] = 1
    with pytest.raises(ValueError, match="Not enough Caramel"):
        engine.start_roast("bourbon", ["caramel"], "medium")
    assert engine.state.raw_bean_inventory["bourbon"] == 1

    engine.state.gold = 0
    with pytest.raises(ValueError, match="Not enough gold"):
        engine.buy_ingredient("caramel")
    with pytest.raises(ValueError, match="Not enough gold"):
        engine.purchase_upgrade("soil_quality")

    engine.state.gold = 10_000
    engine.purchase_upgrade("roaster_speed")
    engine.purchase_upgrade("roaster_speed")
    with pytest.raises(ValueError, match="already maxed"):
        engine.purchase_upgrade("roaster_speed")


def test_engine_purchase_upgrade_applies_plot_effect(engine) -> None:
    engine.state.gold = 1000

    engine.purchase_upgrade("plot_expansion")

    assert engine.state.gold == 700
    assert engine.upgrade_tier("plot_expansion") == 1
    assert len(engine.state.plots) == 4


def test_engine_unlocks_beans_from_progression_upgrades(engine) -> None:
    assert not engine.is_bean_unlocked("sl28")
    assert not engine.is_bean_unlocked("geisha")
    assert not engine.is_bean_unlocked("catimor")
    assert not engine.is_bean_unlocked("robusta")

    engine.state.gold = 10_000
    engine.purchase_upgrade("plot_expansion")
    assert engine.is_bean_unlocked("sl28")
    assert engine.is_bean_unlocked("catimor")

    engine.purchase_upgrade("soil_quality")
    assert engine.is_bean_unlocked("robusta")

    engine.purchase_upgrade("roaster_slot")
    assert engine.is_bean_unlocked("geisha")

    with pytest.raises(ValueError, match="not unlocked"):
        engine.buy_seed("liberica")


def test_engine_save_uses_injected_store(engine, tmp_path) -> None:
    engine.save()

    restored = JsonStateStore(tmp_path / "state.json").load()

    assert restored.to_dict() == engine.state.to_dict()


def test_engine_runs_complete_grow_roast_sell_loop(engine) -> None:
    engine.state.gold = 10_000
    engine.buy_seed("bourbon")
    engine.plant(0, "bourbon")

    engine.clock.value += 10_800
    assert engine.harvest(0) == "bourbon"
    engine.buy_ingredient("caramel")
    engine.start_roast("bourbon", ["caramel"], "dark")

    engine.clock.value += 3_600
    product = engine.collect_roast(0)
    engine.sell_product(0)

    assert product.recipe_id == "bourbon_reserve"
    assert engine.state.roast_batches == []
    assert engine.state.roasted_inventory == []
    assert engine.state.gold == 10098


def test_engine_persists_active_weather_state(engine, tmp_path) -> None:
    engine.set_location("volcanic_island")
    engine.clock.value += 100
    engine.refresh_weather()
    engine.save()

    restored = JsonStateStore(tmp_path / "state.json").load()

    assert restored.location_id == "volcanic_island"
    assert restored.weather_id == "clear"
    assert restored.weather_started_at == 1000.0
