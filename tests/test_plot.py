import pytest

from percolate.models.plot import Plot


def test_plot_starts_empty() -> None:
    plot = Plot()

    assert plot.is_empty
    assert plot.progress(100.0) == 0.0
    assert not plot.is_ready(100.0)


def test_plot_plant_grow_and_harvest() -> None:
    plot = Plot()

    plot.plant("bourbon", growth_time=60.0, now=100.0)

    assert not plot.is_empty
    assert plot.progress(130.0) == 0.5
    assert not plot.is_ready(159.9)
    assert plot.is_ready(160.0)
    assert plot.harvest() == "bourbon"
    assert plot.is_empty
    assert plot.process is None


def test_empty_plot_cannot_be_harvested() -> None:
    with pytest.raises(ValueError, match="empty plot"):
        Plot().harvest()


def test_plot_round_trips_with_active_process() -> None:
    plot = Plot()
    plot.plant("geisha", growth_time=90.0, now=500.0)

    restored = Plot.from_dict(plot.to_dict())

    assert restored == plot
