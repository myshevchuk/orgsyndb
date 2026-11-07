"""The rows of the item list's statistics popup: an item's consumption by
quarter in the current year and the two years before it."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from inventory.figures import Consumption, quarter_of


@dataclass(frozen=True)
class YearRow:
    """A year of the popup's table: the consumption of each of its
    QUARTERS, None for a quarter still to come, and their TOTAL."""

    year: int
    quarters: list[int | None]
    total: int


@dataclass(frozen=True)
class QuarterBar:
    """A bar of the current year: its QUARTER, 1 to 4, its VALUE, None
    for a quarter still to come, its SHARE of the year's largest quarter
    in whole percent, and whether it is the CURRENT quarter."""

    quarter: int
    value: int | None
    share: int
    current: bool


@dataclass(frozen=True)
class Statistics:
    """The popup's figures: the current YEAR, a row for each of the
    YEARS shown, oldest first, the current year's BARS, and the
    ENTERED_YEARS among those shown that hold an entered value above
    zero."""

    year: int
    years: list[YearRow]
    bars: list[QuarterBar]
    entered_years: list[int]


def statistics(figures: Consumption, today: date) -> Statistics:
    """Return the popup's figures for the consumption FIGURES as of
    TODAY: the two years before TODAY's and TODAY's own, the quarters
    after TODAY's empty, and bars whose shares round half up."""
    year, current = quarter_of(today)
    years = []
    for shown in (year - 2, year - 1, year):
        quarters = [figures.total((shown, quarter))
                    if (shown, quarter) <= (year, current) else None
                    for quarter in range(1, 5)]
        years.append(YearRow(year=shown, quarters=quarters,
                             total=sum(value or 0 for value in quarters)))
    largest = max(value or 0 for value in years[-1].quarters)
    bars = [QuarterBar(
        quarter=quarter, value=value, current=quarter == current,
        share=int((Decimal(100 * value) / largest).quantize(
            Decimal(1), ROUND_HALF_UP)) if value and largest else 0)
        for quarter, value in enumerate(years[-1].quarters, start=1)]
    entered = sorted({shown for (shown, _), count in figures.entered.items()
                      if count > 0 and year - 2 <= shown <= year})
    return Statistics(year=year, years=years, bars=bars,
                      entered_years=entered)
