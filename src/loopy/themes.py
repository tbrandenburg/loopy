import curses
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple


ColorPairDefinition = Tuple[str, Tuple[int, int]]


@dataclass(frozen=True)
class Theme:
    """Representation of a curses colour theme."""

    key: str
    display_name: str
    description: str
    palette: Sequence[ColorPairDefinition]
    emphasis: Dict[str, int]

    def apply(self, screen) -> Dict[str, int]:
        """Initialise the curses colour pairs for the theme and set defaults."""
        color_ids: Dict[str, int] = {}

        try:
            curses.start_color()
            try:
                curses.use_default_colors()
            except curses.error:
                pass
        except curses.error:
            return color_ids

        try:
            if not curses.has_colors():
                return color_ids
        except curses.error:
            return color_ids

        for index, (token, (fg, bg)) in enumerate(self.palette, start=1):
            try:
                curses.init_pair(index, fg, bg)
                color_ids[token] = index
            except curses.error:
                # Skip colours the terminal cannot represent.
                continue

        background_token = "background"
        if background_token in color_ids:
            try:
                screen.bkgd(" ", curses.color_pair(color_ids[background_token]))
            except curses.error:
                pass

        return color_ids

    def style(self, token: str, color_ids: Dict[str, int]) -> int:
        """Return the curses attribute for a styling token."""
        attribute = curses.A_NORMAL
        pair_id = color_ids.get(token)
        if pair_id is not None:
            attribute |= curses.color_pair(pair_id)
        emphasis_value = self.emphasis.get(token)
        if emphasis_value is not None:
            attribute |= emphasis_value
        return attribute


THEMES: Dict[str, Theme] = {
    "classic": Theme(
        key="classic",
        display_name="Classic Console",
        description="Monochrome inspired classic theme for broad compatibility.",
        palette=[
            ("background", (curses.COLOR_BLACK, -1)),
            ("title", (curses.COLOR_WHITE, -1)),
            ("channel_label", (curses.COLOR_WHITE, -1)),
            ("step_on", (curses.COLOR_GREEN, -1)),
            ("step_off", (curses.COLOR_WHITE, -1)),
            ("grid", (curses.COLOR_WHITE, -1)),
            ("meta", (curses.COLOR_WHITE, -1)),
        ],
        emphasis={
            "title": curses.A_BOLD,
            "channel_label": curses.A_BOLD,
            "step_on": curses.A_BOLD,
        },
    ),
    "tokyo-night": Theme(
        key="tokyo-night",
        display_name="Tokyo Nightfall",
        description="Blue-forward nocturnal tones inspired by Tokyo's neon skyline.",
        palette=[
            ("background", (curses.COLOR_BLACK, -1)),
            ("title", (curses.COLOR_BLUE, -1)),
            ("channel_label", (curses.COLOR_CYAN, -1)),
            ("step_on", (curses.COLOR_BLACK, curses.COLOR_BLUE)),
            ("step_off", (curses.COLOR_CYAN, -1)),
            ("grid", (curses.COLOR_MAGENTA, -1)),
            ("meta", (curses.COLOR_WHITE, -1)),
        ],
        emphasis={
            "title": curses.A_BOLD,
            "channel_label": curses.A_BOLD,
            "step_on": curses.A_BOLD,
            "meta": curses.A_DIM,
        },
    ),
    "lofi-chill": Theme(
        key="lofi-chill",
        display_name="LoFi Chilly",
        description="Harmonic teal, magenta and midnight hues for a gem-like chill vibe.",
        palette=[
            ("background", (curses.COLOR_BLACK, -1)),
            ("title", (curses.COLOR_CYAN, -1)),
            ("channel_label", (curses.COLOR_MAGENTA, -1)),
            ("step_on", (curses.COLOR_BLACK, curses.COLOR_CYAN)),
            ("step_off", (curses.COLOR_CYAN, -1)),
            ("grid", (curses.COLOR_BLUE, -1)),
            ("meta", (curses.COLOR_WHITE, -1)),
        ],
        emphasis={
            "title": curses.A_BOLD,
            "channel_label": curses.A_BOLD,
            "step_on": curses.A_BOLD,
            "meta": curses.A_DIM,
        },
    ),
}


def get_theme(name: str) -> Theme:
    """Return a theme by its key, raising a KeyError if it doesn't exist."""
    key = name.lower()
    if key not in THEMES:
        raise KeyError(f"Unknown theme '{name}'. Available themes: {', '.join(sorted(THEMES))}")
    return THEMES[key]


def list_theme_keys() -> List[str]:
    """Return the available theme keys."""
    return sorted(THEMES.keys())


def iter_themes() -> Iterable[Theme]:
    """Iterate over the available themes."""
    return THEMES.values()
