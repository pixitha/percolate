from percolate.backdrop_compositor import composite_backdrop, composite_weather, load_farmhouse_data
from percolate.content.catalog import ContentCatalog


def test_weather_overlay_paints_ascii_art_over_the_farm_backdrop() -> None:
    content = ContentCatalog.load_default()
    backdrop = composite_backdrop(load_farmhouse_data())
    rendered = composite_weather(backdrop, content.weather["drizzle"])

    assert "·" in str(rendered)
    assert "|" in str(rendered)
