from percolate.models.bean import Bean, load_bean_registry
from percolate.models.roast import (
    Ingredient,
    Recipe,
    resolve_roast,
    load_ingredient_registry,
    load_recipe_registry,
)
from percolate.content.catalog import ContentCatalog


def test_unmatched_roast_gets_generated_name_and_base_value() -> None:
    bean = Bean("test", "Test Bean", 60.0, 1, 20)
    ingredients = [Ingredient("vanilla", "Vanilla", 5, 7)]

    result = resolve_roast(bean, ingredients, "light", recipes={})

    assert result.name == "Test Bean Light Vanilla"
    assert result.value == 37  # 20 * 1.5 + 7
    assert result.recipe_id is None


def test_curated_recipe_overrides_name_and_adds_bonus() -> None:
    bean = Bean("test", "Test Bean", 60.0, 1, 20)
    ingredient = Ingredient("vanilla", "Vanilla", 5, 7)
    recipe = Recipe("reserve", "Test Reserve", "test", ["vanilla"], "medium", 2.0)

    result = resolve_roast(bean, [ingredient], "medium", {recipe.id: recipe})

    assert result.name == "Test Reserve"
    assert result.value == 74
    assert result.recipe_id == "reserve"


def test_bundled_registries_load_and_reference_known_content() -> None:
    beans = load_bean_registry()
    ingredients = load_ingredient_registry()
    recipes = load_recipe_registry()

    assert {
        "typica",
        "caturra",
        "bourbon",
        "yirgacheffe",
        "robusta",
        "catimor",
        "sl28",
        "geisha",
        "liberica",
    } <= beans.keys()
    assert "vanilla" in ingredients
    assert recipes["bourbon_reserve"].bean == "bourbon"
    assert recipes["sl28_cardamom"].bean == "sl28"
    assert recipes["robusta_chocolate"].bean == "robusta"


def test_locations_reference_only_bundled_weather() -> None:
    content = ContentCatalog.load_default()

    for location in content.locations.values():
        assert location.weather_ids
        assert set(location.weather_ids) <= content.weather.keys()


def test_quality_traits_change_roast_value() -> None:
    plain = Bean("plain", "Plain", 60.0, 1, 20)
    premium = Bean(
        "premium",
        "Premium",
        60.0,
        1,
        20,
        traits={"quality_modifier": 0.25},
    )

    plain_result = resolve_roast(plain, [], "medium", {})
    premium_result = resolve_roast(premium, [], "medium", {})

    assert premium_result.value > plain_result.value
