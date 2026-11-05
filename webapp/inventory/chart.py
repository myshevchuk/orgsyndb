"""The consumption chart of an item's page: an SVG bar chart drawn on the
server."""

from dataclasses import dataclass
from decimal import Decimal

from inventory.figures import Consumption, Quarter

WIDTH = 480
HEIGHT = 180
TOP = 10
BOTTOM = 36
BAR = 24
GAP = 16
SPAN = 40


@dataclass(frozen=True)
class Bar:
    """A bar: its quarter, its value, its title, and its place in the
    drawing."""

    quarter: Quarter
    value: int
    title: str
    x: int
    y: float
    height: float
    label_x: int


@dataclass(frozen=True)
class Chart:
    """The drawing: its size, its bars, the baseline's height, the label
    of each year with its place, and the height of the line at the mean
    per quarter, None without a mean."""

    width: int
    height: int
    baseline: int
    bars: list[Bar]
    years: list[tuple[int, int]]
    mean_y: float | None


def quarters_shown(year: int) -> list[Quarter]:
    """Return the quarters the chart of YEAR draws: those of the two
    years before it and of YEAR itself."""
    return [(each, quarter) for each in (year - 2, year - 1, year)
            for quarter in range(1, 5)]


def chart(figures: Consumption, year: int) -> Chart:
    """Return the chart of FIGURES for the current YEAR, one bar per
    quarter of ``quarters_shown``, scaled to the larger of the highest
    bar and the mean per quarter."""
    shown = quarters_shown(year)
    values = [figures.total(quarter) for quarter in shown]
    mean = figures.mean_quarter
    top = max([*values, mean or 0, 1])
    baseline = HEIGHT - BOTTOM
    scale = Decimal(baseline - TOP) / Decimal(top)
    bars = []
    for position, (quarter, value) in enumerate(zip(shown, values)):
        x = GAP // 2 + position * SPAN
        height = float(value * scale)
        bars.append(Bar(quarter=quarter, value=value,
                        title=f"Q{quarter[1]} {quarter[0]}: {value}",
                        x=x, y=baseline - height, height=height,
                        label_x=x + BAR // 2))
    return Chart(
        width=WIDTH, height=HEIGHT, baseline=baseline, bars=bars,
        years=[(each, GAP // 2 + offset * 4 * SPAN + 2 * SPAN - GAP // 2)
               for offset, each in enumerate((year - 2, year - 1, year))],
        mean_y=None if mean is None else float(baseline - mean * scale))
