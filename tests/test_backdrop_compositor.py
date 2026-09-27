from percolate.backdrop_compositor import composite_backdrop, composite_weather, load_farmhouse_data
from percolate.content.catalog import ContentCatalog


def test_weather_overlay_paints_ascii_art_over_the_farm_backdrop() -> None:
    content = ContentCatalog.load_default()
    backdrop = composite_backdrop(load_farmhouse_data())
    rendered = composite_weather(backdrop, content.weather["drizzle"])

    assert "·" in str(rendered)
    assert "|" in str(rendered)


def test_every_weather_profile_has_layered_sky_art_within_canvas() -> None:
    content = ContentCatalog.load_default()
    backdrop_data = load_farmhouse_data()
    backdrop = composite_backdrop(backdrop_data)
    width = backdrop_data["canvas"]["width"]

    for weather in content.weather.values():
        # Clear weather intentionally leaves the authored sun unobstructed;
        # every active weather condition adds layered atmosphere of its own.
        if weather.id != "clear":
            assert len(weather.overlays) >= 2
        assert all(
            0 <= overlay["row"] < backdrop_data["canvas"]["height"]
            and 0 <= overlay.get("col", 0)
            and overlay.get("col", 0) + len(overlay["text"]) <= width
            for overlay in weather.overlays
        )
        assert all(
            0 <= overlay["row"] < backdrop_data["canvas"]["height"]
            and 0 <= overlay.get("col", 0)
            and overlay.get("col", 0) + len(overlay["text"]) <= width
            for frame in weather.animation_frames
            for overlay in frame
        )
        assert len(str(composite_weather(backdrop, weather)).splitlines()) == backdrop_data["canvas"]["height"]


def test_weather_animation_frames_change_the_rendered_scene() -> None:
    content = ContentCatalog.load_default()
    backdrop = composite_backdrop(load_farmhouse_data())
    weather = content.weather["rain"]

    assert len(weather.animation_frames) >= 2
    assert str(composite_weather(backdrop, weather, phase=0)) != str(
        composite_weather(backdrop, weather, phase=1)
    )


def test_drizzle_has_a_dense_field_of_falling_drops() -> None:
    weather = ContentCatalog.load_default().weather["drizzle"]

    assert all(len(frame) >= 10 for frame in weather.animation_frames)


def test_cool_snap_masks_the_clear_sky_sun() -> None:
    content = ContentCatalog.load_default()
    backdrop = composite_backdrop(load_farmhouse_data())
    rendered = str(composite_weather(backdrop, content.weather["cool_snap"]))

    assert rendered.splitlines()[4][40] != "'"


def test_tropical_rain_reaches_across_the_full_farm_scene() -> None:
    weather = ContentCatalog.load_default().weather["rain"]

    assert all(len(frame) >= 15 for frame in weather.animation_frames)
    assert all(
        any(overlay["row"] >= 5 for overlay in frame)
        for frame in weather.animation_frames
    )


def test_humid_heat_has_ground_level_heat_shimmer() -> None:
    weather = ContentCatalog.load_default().weather["humid_heat"]

    assert len(weather.animation_frames) >= 2
    assert all(
        len(frame) >= 7
        and all(overlay["text"] == "S" and overlay["row"] >= 15 for overlay in frame)
        for frame in weather.animation_frames
    )


def test_humid_heat_does_not_add_a_second_sun() -> None:
    content = ContentCatalog.load_default()
    backdrop = composite_backdrop(load_farmhouse_data())
    rendered = str(composite_weather(backdrop, content.weather["humid_heat"]))

    assert "- O -" not in rendered


def test_weather_does_not_add_sun_glyphs_to_the_authored_sky() -> None:
    content = ContentCatalog.load_default()
    backdrop = composite_backdrop(load_farmhouse_data())

    for weather in content.weather.values():
        sky = str(composite_weather(backdrop, weather)).splitlines()[:5]
        assert all("O" not in row for row in sky), weather.id


def test_island_storm_has_the_same_full_scene_rain_treatment() -> None:
    weather = ContentCatalog.load_default().weather["storm"]

    assert len(weather.animation_frames) == 3
    assert all(len(frame) >= 14 for frame in weather.animation_frames)
    assert all(any(overlay["row"] >= 15 for overlay in frame) for frame in weather.animation_frames)
