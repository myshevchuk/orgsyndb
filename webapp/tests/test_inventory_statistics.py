"""Tests of the rows of the item list's statistics popup, computed from
an item's consumption (end-product-inventory: Item list)."""

from datetime import date
from unittest import TestCase

from inventory.figures import figures_of
from inventory.statistics import statistics

TODAY = date(2026, 11, 4)


class StatisticsTests(TestCase):

    def test_the_scenarios_years(self) -> None:
        """Scenario: Statistics popup (the figures)."""
        entered = {(2024, q): 4 for q in range(1, 5)}
        entered.update({(2026, 1): 6, (2026, 2): 5, (2026, 3): 7})
        figures = figures_of(6, entered, {(2026, 4): 2}, TODAY)
        found = statistics(figures, TODAY)
        self.assertEqual([(row.year, row.quarters, row.total)
                          for row in found.years],
                         [(2024, [4, 4, 4, 4], 16),
                          (2025, [0, 0, 0, 0], 0),
                          (2026, [6, 5, 7, 2], 20)])
        self.assertEqual([(bar.quarter, bar.value, bar.share, bar.current)
                          for bar in found.bars],
                         [(1, 6, 86, False), (2, 5, 71, False),
                          (3, 7, 100, False), (4, 2, 29, True)])
        self.assertEqual(found.entered_years, [2024, 2026])
        self.assertEqual(found.year, 2026)

    def test_quarters_to_come(self) -> None:
        today = date(2026, 5, 4)
        figures = figures_of(3, {(2026, 1): 3}, {}, today)
        found = statistics(figures, today)
        self.assertEqual(found.years[2].quarters, [3, 0, None, None])
        self.assertEqual(found.years[2].total, 3)
        self.assertEqual([(bar.value, bar.share, bar.current)
                          for bar in found.bars],
                         [(3, 100, False), (0, 0, True), (None, 0, False),
                          (None, 0, False)])

    def test_a_year_without_consumption(self) -> None:
        found = statistics(figures_of(2, {}, {}, TODAY), TODAY)
        self.assertEqual([row.total for row in found.years], [0, 0, 0])
        self.assertEqual([bar.share for bar in found.bars], [0, 0, 0, 0])
        self.assertEqual(found.entered_years, [])

    def test_deliveries_and_entered_zeros_are_not_entered(self) -> None:
        figures = figures_of(2, {(2025, 2): 0}, {(2024, 3): 5}, TODAY)
        found = statistics(figures, TODAY)
        self.assertEqual(found.entered_years, [])
        self.assertEqual(found.years[0].quarters, [0, 0, 5, 0])

    def test_shares_round_half_up(self) -> None:
        entered = {(2026, 1): 8, (2026, 2): 1, (2026, 3): 3}
        found = statistics(figures_of(1, entered, {}, TODAY), TODAY)
        self.assertEqual([bar.share for bar in found.bars],
                         [100, 13, 38, 0])
