"""The overview's chart of the containers delivered per month: an SVG bar
chart drawn on the server, each month beside the same month a year
before."""

from dataclasses import dataclass
from datetime import date

from django.utils import dateformat

from overview.figures import Month

WIDTH = 600
HEIGHT = 180
TOP = 10
BOTTOM = 24
BAR = 16
SPAN = WIDTH // 12


@dataclass(frozen=True)
class Bar:
    """A bar: its value, its title, and its place in the drawing."""

    value: int
    title: str
    x: int
    y: float
    height: float


@dataclass(frozen=True)
class MonthBars:
    """A month: the bar of the year before, PREVIOUS, the month's own,
    CURRENT, and the month's LABEL centred at LABEL_X."""

    previous: Bar
    current: Bar
    label: str
    label_x: int


@dataclass(frozen=True)
class Chart:
    """The drawing: its size, its months and the baseline's height."""

    width: int
    height: int
    baseline: int
    months: list[MonthBars]


def chart(months: list[Month], current: list[int], previous: list[int]
          ) -> Chart:
    """Return the chart of MONTHS, oldest first, with the containers
    delivered in each, CURRENT, and in the same months a year before,
    PREVIOUS, scaled to the highest bar. Titles and labels name the
    months as the active language does."""
    baseline = HEIGHT - BOTTOM
    scale = (baseline - TOP) / max([*current, *previous, 1])
    drawn = []
    for position, ((year, month), now, before) in enumerate(
            zip(months, current, previous)):
        left = position * SPAN + (SPAN - 2 * BAR - 2) // 2

        def bar(value: int, day: date, x: int) -> Bar:
            height = value * scale
            return Bar(value=value,
                       title=f"{dateformat.format(day, 'F Y')}: {value}",
                       x=x, y=baseline - height, height=height)

        drawn.append(MonthBars(
            previous=bar(before, date(year - 1, month, 1), left),
            current=bar(now, date(year, month, 1), left + BAR + 2),
            label=dateformat.format(date(year, month, 1), "M"),
            label_x=position * SPAN + SPAN // 2))
    return Chart(width=WIDTH, height=HEIGHT, baseline=baseline,
                 months=drawn)
