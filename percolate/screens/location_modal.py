"""One-time home-region selection shown when starting a new farm."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from percolate.focus_widgets import FocusHighlightOptionList


class LocationChoiceModal(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Use Highland Estate")]

    def compose(self) -> ComposeResult:
        with Vertical(id="location_picker"):
            yield Label("Choose your home region")
            yield Label("This choice shapes your farm's climate and coffee tradeoffs.")
            options = []
            for location in self.app.engine.content.locations.values():
                growth = int(location.growth_speed_bonus * 100)
                quality = int(location.quality_modifier * 100)
                options.append(
                    Option(
                        f"{location.name} — {growth:+d}% growth, {quality:+d}% quality\n  {location.description}",
                        id=location.id,
                    )
                )
            yield FocusHighlightOptionList(*options, id="location_list")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss("highland_estate")
