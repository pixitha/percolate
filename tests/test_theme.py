from percolate.theme import ALL_THEMES, theme_for_location


def test_each_location_has_a_distinct_registered_theme() -> None:
    names = [theme_for_location(location_id) for location_id in (
        "highland_estate",
        "tropical_lowland",
        "volcanic_island",
        "dry_mountain_valley",
    )]

    assert len(set(names)) == 4
    assert all(name in {theme.name for theme in ALL_THEMES} for name in names)


def test_unknown_location_uses_the_safe_default_theme() -> None:
    assert theme_for_location("old_save_location") == "percolate-highland"
