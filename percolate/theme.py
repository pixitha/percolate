"""Percolate's own color themes.

Two warm coffee-roastery palettes — roasted browns, crema gold, terracotta —
registered with Textual's theme system so built-in widgets (buttons, option
lists, selection highlights, scrollbars) match the hand-picked colors
already used throughout the custom ASCII art and CSS, instead of Textual's
default blue-accented dark theme.

Both are dark themes (`dark=True`) — "latte" is only a softer, lighter-roast
variant of "mocha", never a bright/light theme. Both are registered; whichever
is active is chosen in main.py, and either can be picked from the command
palette (ctrl+p) since Textual lists every registered theme there.
"""

from __future__ import annotations

from textual.theme import Theme

PERCOLATE_MOCHA = Theme(
    name="percolate-mocha",
    dark=True,
    background="#1b1410",
    surface="#241a14",
    panel="#2f2119",
    primary="#c9a13b",
    secondary="#a8643c",
    accent="#e0b84c",
    warning="#d98c3d",
    error="#b3503f",
    success="#7a9b5c",
    foreground="#ece0d1",
)

PERCOLATE_LATTE = Theme(
    name="percolate-latte",
    dark=True,
    background="#38322e",
    surface="#423c38",
    panel="#4b4540",
    primary="#caaf72",
    secondary="#b38366",
    accent="#dec58a",
    warning="#d1a26d",
    error="#b57b6d",
    success="#94aa83",
    foreground="#f3e9da",
)

PERCOLATE_THEMES = (PERCOLATE_MOCHA, PERCOLATE_LATTE)


# Geography palettes are deliberately a presentation concern. The location
# data controls gameplay modifiers; this mapping only controls the mood of the
# terminal UI while the farm is there.
LOCATION_THEMES = {
    "highland_estate": Theme(
        name="percolate-highland",
        dark=True,
        background="#18201c",
        surface="#22302a",
        panel="#2b3b32",
        primary="#b7c98a",
        secondary="#729a82",
        accent="#d9c477",
        warning="#d5a45e",
        error="#b96d5f",
        success="#8fb878",
        foreground="#e5ead8",
    ),
    "tropical_lowland": Theme(
        name="percolate-tropical",
        dark=True,
        background="#15221d",
        surface="#1d3328",
        panel="#274536",
        primary="#79c58b",
        secondary="#4ba69b",
        accent="#e7c76c",
        warning="#e0a354",
        error="#bd6654",
        success="#8bd08d",
        foreground="#e2f0d9",
    ),
    "volcanic_island": Theme(
        name="percolate-volcanic",
        dark=True,
        background="#211719",
        surface="#342023",
        panel="#47292a",
        primary="#d58d72",
        secondary="#a86d63",
        accent="#e0b35f",
        warning="#df9c55",
        error="#c95d55",
        success="#91a66c",
        foreground="#f0ded0",
    ),
    "dry_mountain_valley": Theme(
        name="percolate-dry-valley",
        dark=True,
        background="#211c18",
        surface="#342b23",
        panel="#473a2d",
        primary="#d1a56a",
        secondary="#9e765a",
        accent="#e0c27a",
        warning="#df984c",
        error="#b9614e",
        success="#a3a45f",
        foreground="#f0e1c9",
    ),
}


def theme_for_location(location_id: str) -> str:
    """Return a registered Textual theme name for a location.

    Unknown or legacy location identifiers fall back to the stable Highland
    palette rather than preventing the app from starting.
    """
    return LOCATION_THEMES.get(location_id, LOCATION_THEMES["highland_estate"]).name


ALL_THEMES = PERCOLATE_THEMES + tuple(LOCATION_THEMES.values())
