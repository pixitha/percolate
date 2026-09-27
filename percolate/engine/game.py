"""The UI-independent facade for Percolate's gameplay rules.

The engine owns gameplay operations and receives a separate serialized
`GameState`, keeping the UI and persistence layers outside the rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from percolate.content.catalog import ContentCatalog
from percolate.config import DEFAULT_ROAST_SLOTS
from percolate.engine.clock import Clock, SystemClock
from percolate.engine.state import GameState, RoastedProduct
from percolate.models.roast import DEFAULT_ROAST_DURATION, RoastBatch, resolve_roast
from percolate.models.plot import Plot
from percolate.models.timed_process import TimedProcess
from percolate.persistence.json_store import JsonStateStore


@dataclass
class GameEngine:
    state: GameState
    content: ContentCatalog
    clock: Clock
    store: JsonStateStore | None = None

    def __post_init__(self) -> None:
        self.refresh_bean_unlocks()
        self.refresh_weather()

    @classmethod
    def load_default(
        cls,
        store: JsonStateStore | None = None,
        content: ContentCatalog | None = None,
        clock: Clock | None = None,
    ) -> "GameEngine":
        state_store = store or JsonStateStore()
        return cls(
            state=state_store.load(),
            content=content or ContentCatalog.load_default(),
            clock=clock or SystemClock(),
            store=state_store,
        )

    @property
    def now(self) -> float:
        return self.clock.now()

    def save(self) -> None:
        if self.store is not None:
            self.store.save(self.state)

    def is_bean_unlocked(self, bean_id: str) -> bool:
        return bean_id in self.state.unlocked_beans

    @property
    def location(self):
        return self.content.locations[self.state.location_id]

    def set_location(self, location_id: str) -> None:
        """Move the farm to a stable geography profile.

        Location changes are intentionally free for this first slice. Travel
        costs and unlocks can be layered on later without changing the state
        shape or the climate calculation.
        """
        if location_id not in self.content.locations:
            raise ValueError(f"Unknown location: {location_id}")
        self.state.location_id = location_id
        self.state.location_selected = True
        self.state.weather_id = self.location.weather_ids[0]
        self.state.weather_started_at = self.now

    def set_weather(self, weather_id: str) -> None:
        """Set the active weather, provided it belongs to this location."""
        if weather_id not in self.content.weather:
            raise ValueError(f"Unknown weather: {weather_id}")
        if weather_id not in self.location.weather_ids:
            raise ValueError(f"Weather {weather_id!r} is not available in {self.location.name}")
        self.state.weather_id = weather_id
        self.state.weather_started_at = self.now

    def cycle_location(self, direction: int = 1) -> None:
        """Move to the next or previous bundled location."""
        location_ids = list(self.content.locations)
        current = location_ids.index(self.state.location_id)
        self.set_location(location_ids[(current + direction) % len(location_ids)])

    def cycle_weather(self, direction: int = 1) -> None:
        """Move to the next or previous weather in the current location."""
        weather_ids = self.location.weather_ids
        current = weather_ids.index(self.state.weather_id) if self.state.weather_id in weather_ids else -1
        self.set_weather(weather_ids[(current + direction) % len(weather_ids)])

    @property
    def weather(self):
        return self.content.weather[self.state.weather_id]

    def refresh_weather(self) -> None:
        """Advance the stable, clock-driven weather cycle if it has expired."""
        if self.state.weather_started_at <= 0:
            self.state.weather_started_at = self.now
            return
        weather = self.weather
        if self.now < self.state.weather_started_at + weather.duration:
            return
        weather_ids = self.location.weather_ids
        current = weather_ids.index(self.state.weather_id) if self.state.weather_id in weather_ids else -1
        elapsed = self.now - self.state.weather_started_at
        steps = max(1, int(elapsed // weather.duration))
        self.state.weather_id = weather_ids[(current + steps) % len(weather_ids)]
        self.state.weather_started_at = self.now

    def weather_modifier(self, key: str) -> float:
        return getattr(self.weather, key, 0.0)

    def location_modifier(self, bean_id: str, key: str) -> float:
        location = self.location
        bean = self.content.beans[bean_id]
        base = getattr(location, key, 0.0)
        preference = bean.location_modifiers.get(location.id, {})
        return base + preference.get(key, 0.0)

    def growth_speed_bonus_for(self, bean_id: str) -> float:
        return (
            self.growth_speed_bonus()
            + self.location_modifier(bean_id, "growth_speed_bonus")
            + self.weather_modifier("growth_speed_bonus")
        )

    def quality_modifier_for(self, bean_id: str) -> float:
        return self.location_modifier(bean_id, "quality_modifier") + self.weather_modifier(
            "quality_modifier"
        )

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if quantity < 1:
            raise ValueError("Quantity must be positive.")

    def refresh_bean_unlocks(self) -> None:
        for bean in self.content.beans.values():
            unlock = bean.unlock
            if not unlock:
                continue
            if unlock.get("upgrade") and self.upgrade_tier(unlock["upgrade"]) >= unlock.get("tier", 1):
                self.state.unlocked_beans.add(bean.id)

    def upgrade_tier(self, upgrade_id: str) -> int:
        return self.state.owned_upgrades.get(upgrade_id, 0)

    def _current_tier_effect(self, upgrade_id: str, key: str) -> float:
        tier = self.upgrade_tier(upgrade_id)
        tiers = self.content.upgrades.get(upgrade_id, {}).get("tiers", [])
        if tier <= 0 or tier > len(tiers):
            return 0.0
        return tiers[tier - 1].get(key, 0.0)

    def growth_speed_bonus(self) -> float:
        return self._current_tier_effect("soil_quality", "growth_speed_bonus")

    def roast_speed_bonus(self) -> float:
        return self._current_tier_effect("roaster_speed", "roast_speed_bonus")

    def max_ingredients(self) -> int:
        return int(self._current_tier_effect("infuser", "max_ingredients"))

    def max_roast_slots(self) -> int:
        tier = self.upgrade_tier("roaster_slot")
        tiers = self.content.upgrades.get("roaster_slot", {}).get("tiers", [])
        return DEFAULT_ROAST_SLOTS + sum(item.get("slots_added", 0) for item in tiers[:tier])

    def buy_seed(self, bean_id: str, quantity: int = 1) -> None:
        self._validate_quantity(quantity)
        if not self.is_bean_unlocked(bean_id):
            raise ValueError("That bean variety is not unlocked yet.")
        bean = self.content.beans[bean_id]
        cost = bean.seed_cost * quantity
        if self.state.gold < cost:
            raise ValueError("Not enough gold for seed.")
        self.state.gold -= cost
        self.state.seed_inventory[bean_id] = self.state.seed_inventory.get(bean_id, 0) + quantity

    def buy_ingredient(self, ingredient_id: str, quantity: int = 1) -> None:
        self._validate_quantity(quantity)
        ingredient = self.content.ingredients[ingredient_id]
        cost = ingredient.cost * quantity
        if self.state.gold < cost:
            raise ValueError("Not enough gold for ingredient.")
        self.state.gold -= cost
        self.state.ingredient_inventory[ingredient_id] = (
            self.state.ingredient_inventory.get(ingredient_id, 0) + quantity
        )

    def sell_raw(self, bean_id: str, quantity: int = 1) -> None:
        self._validate_quantity(quantity)
        bean = self.content.beans[bean_id]
        have = self.state.raw_bean_inventory.get(bean_id, 0)
        if have < quantity:
            raise ValueError("Not enough raw beans to sell.")
        self.state.raw_bean_inventory[bean_id] = have - quantity
        self.state.gold += bean.raw_sell_value * quantity

    def plant(self, plot_index: int, bean_id: str) -> None:
        if not self.is_bean_unlocked(bean_id):
            raise ValueError("That bean variety is not unlocked yet.")
        bean = self.content.beans[bean_id]
        growth_bonus = self.growth_speed_bonus_for(bean_id)
        growth_time = bean.growth_time * (1 - growth_bonus)
        plot = self.state.plots[plot_index]
        if not plot.is_empty:
            raise ValueError("Plot is already planted.")
        if self.state.seed_inventory.get(bean_id, 0) < 1:
            raise ValueError("No seeds of that strain. Buy some at the Market.")
        self.state.seed_inventory[bean_id] -= 1
        plot.plant(bean_id, growth_time, self.now)

    def harvest(self, plot_index: int) -> str:
        plot = self.state.plots[plot_index]
        if not plot.is_ready(self.now):
            raise ValueError("Plot is not ready to harvest.")
        bean_id = plot.harvest()
        self.state.raw_bean_inventory[bean_id] = (
            self.state.raw_bean_inventory.get(bean_id, 0) + 1
        )
        return bean_id

    def start_roast(self, bean_id: str, ingredient_ids: list[str], roast_level: str) -> None:
        capacity = self.max_roast_slots()
        if len(self.state.roast_batches) >= capacity:
            raise ValueError("No available roaster slot.")

        ingredients = [self.content.ingredients[item_id] for item_id in ingredient_ids]
        if self.state.raw_bean_inventory.get(bean_id, 0) < 1:
            raise ValueError("No raw beans of that strain to roast.")
        for ingredient in ingredients:
            if self.state.ingredient_inventory.get(ingredient.id, 0) < 1:
                raise ValueError(f"Not enough {ingredient.name} to roast.")

        speed_bonus = self.roast_speed_bonus()
        duration = DEFAULT_ROAST_DURATION * (1 - speed_bonus)
        self.state.raw_bean_inventory[bean_id] -= 1
        for ingredient in ingredients:
            self.state.ingredient_inventory[ingredient.id] -= 1
        self.state.roast_batches.append(
            RoastBatch(
                bean_id=bean_id,
                ingredient_ids=ingredient_ids,
                roast_level=roast_level,
                process=TimedProcess(started_at=self.now, duration=duration),
            )
        )

    def collect_roast(self, batch_index: int) -> RoastedProduct:
        batch = self.state.roast_batches[batch_index]
        if not batch.is_ready(self.now):
            raise ValueError("Roast batch is not ready to collect.")

        bean = self.content.beans[batch.bean_id]
        ingredients = [self.content.ingredients[item_id] for item_id in batch.ingredient_ids]
        result = resolve_roast(
            bean,
            ingredients,
            batch.roast_level,
            self.content.recipes,
            extra_quality_modifier=self.quality_modifier_for(batch.bean_id),
        )
        product = RoastedProduct(name=result.name, value=result.value, recipe_id=result.recipe_id)
        self.state.roasted_inventory.append(product)
        if result.recipe_id:
            self.state.discovered_recipes.add(result.recipe_id)
        del self.state.roast_batches[batch_index]
        return product

    def sell_product(self, product_index: int) -> RoastedProduct:
        product = self.state.roasted_inventory.pop(product_index)
        self.state.gold += product.value
        return product

    def purchase_upgrade(self, upgrade_id: str) -> None:
        upgrade = self.content.upgrades[upgrade_id]
        current_tier = self.upgrade_tier(upgrade_id)
        tiers = upgrade["tiers"]
        if current_tier >= len(tiers):
            raise ValueError(f"{upgrade['name']} is already maxed.")

        next_tier = tiers[current_tier]
        if self.state.gold < next_tier["cost"]:
            raise ValueError("Not enough gold for upgrade.")
        self.state.gold -= next_tier["cost"]
        self.state.owned_upgrades[upgrade_id] = current_tier + 1
        if upgrade_id == "plot_expansion":
            self.state.plots.extend(Plot() for _ in range(next_tier["plots_added"]))
        self.refresh_bean_unlocks()

    def advance_debug_time(self, seconds: float) -> None:
        self.state.weather_started_at -= seconds
        for plot in self.state.plots:
            if plot.process is not None:
                plot.process.started_at -= seconds
        for batch in self.state.roast_batches:
            if batch.process is not None:
                batch.process.started_at -= seconds
