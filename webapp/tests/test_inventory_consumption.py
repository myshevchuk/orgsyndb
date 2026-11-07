"""Tests of the consumption per quarter (end-product-inventory:
Consumption)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import Refused, book_note, enter_consumption, reverse
from inventory.models import EnteredConsumption

from .inventory_support import InventoryCase, fresh, snapshot


class QuarterTests(InventoryCase):

    def test_an_entered_value_is_the_consumption_of_its_quarter(
            self) -> None:
        item = self.item()
        self.enter(item, 2025, 2, 7)
        quarters = self.consumption(item).quarters
        self.assertEqual(quarters[(2025, 2)], 7)
        self.assertEqual(quarters.get((2025, 1), 0), 0)
        self.assertEqual(quarters.get((2025, 3), 0), 0)

    def test_a_quarter_adds_the_entered_value_and_the_lines(self) -> None:
        item = self.item(quantity=20)
        self.enter(item, 2025, 2, 5)
        self.deliver(item, 2, date(2025, 4, 1))
        self.deliver(item, 3, date(2025, 6, 30))
        self.deliver(item, 4, date(2025, 7, 1))
        quarters = self.consumption(item).quarters
        self.assertEqual(quarters[(2025, 2)], 10)
        self.assertEqual(quarters[(2025, 3)], 4)

    def test_lines_of_historical_notes_count(self) -> None:
        item = self.item(quantity=5)
        book_note(self.kl, date=date(2025, 8, 3), historical=True,
                  lines=[(item, 4)])
        book_note(self.kl, date=date(2025, 9, 30), historical=True,
                  lines=[(item, 3)])
        self.assertEqual(self.consumption(item).quarters[(2025, 3)], 7)

    def test_each_item_has_its_own_consumption(self) -> None:
        first = self.item("CH-0001")
        second = self.item("CH-0002")
        self.enter(first, 2025, 1, 3)
        self.assertEqual(
            self.consumption(second).quarters.get((2025, 1), 0), 0)

    def test_a_reversed_delivery_does_not_count(self) -> None:
        item = self.item(quantity=9)
        first = self.deliver_movement(item, 2, date(2025, 5, 1))
        self.deliver(item, 3, date(2025, 5, 2))
        reverse(self.kl, first, note="falsch")
        self.assertEqual(self.consumption(item).quarters[(2025, 2)], 3)


class MeanTests(InventoryCase):

    def test_means_and_coverage(self) -> None:
        """Scenario: Means and coverage."""
        item = self.means_item()
        self.assertEqual(fresh(item).quantity, 3)
        figures = self.consumption(item)
        self.assertAlmostEqual(float(figures.mean_year), 18)
        self.assertAlmostEqual(float(figures.mean_quarter), 4.5)
        self.assertEqual(figures.this_year, 13)
        self.assertAlmostEqual(float(figures.coverage), 3 / 4.5)
        self.assertEqual(figures.level, "low")

    def test_years_counted(self) -> None:
        """Scenario: Years counted."""
        first = self.item("CH-0001", quantity=5)
        self.enter(first, 2024, 3, 0)
        self.enter_year(first, 2025, 8)
        second = self.item("CH-0002", quantity=5)
        self.enter_year(second, 2026, 8)
        figures = self.consumption(first)
        self.assertAlmostEqual(float(figures.mean_year), 16)
        figures = self.consumption(second)
        self.assertTrue(figures.projected)
        self.assertIsNotNone(figures.mean_year)
        self.assertIsNotNone(figures.coverage)
        self.assertEqual(figures.this_year, 32)

    def test_without_a_mean_an_empty_item_is_out(self) -> None:
        item = self.item("CH-0002", quantity=0)
        self.enter_year(item, 2026, 8)
        self.assertEqual(self.consumption(item).level, "out")

    def test_a_reversed_note_does_not_start_the_history(self) -> None:
        """Scenario: A reversed note does not start the history."""
        from inventory.bookings import reverse_historical
        item = self.item(quantity=5)
        self.enter_year(item, 2025, 8)
        note = book_note(self.kl, date=date(2024, 5, 2), historical=True,
                         lines=[(item, 1)])
        self.assertAlmostEqual(
            float(self.consumption(item).mean_year), 16.5)
        reverse_historical(self.kl, note, note="falsch")
        self.assertAlmostEqual(
            float(self.consumption(item).mean_year), 32)

    def test_a_reversed_delivery_does_not_start_the_history(self) -> None:
        item = self.item(quantity=5)
        self.enter_year(item, 2025, 8)
        delivery = self.deliver_movement(item, 1, date(2023, 6, 1))
        self.assertAlmostEqual(
            float(self.consumption(item).mean_year), 33 / 3)
        reverse(self.kl, delivery, note="falsch")
        self.assertAlmostEqual(
            float(self.consumption(item).mean_year), 32)

    def test_a_delivery_before_the_entered_values_starts_the_history(
            self) -> None:
        item = self.item(quantity=5)
        self.enter(item, 2025, 1, 8)
        self.deliver(item, 2, date(2023, 6, 1))
        figures = self.consumption(item)
        self.assertAlmostEqual(float(figures.mean_year), 10 / 3)
        self.assertAlmostEqual(float(figures.mean_quarter), 10 / 12)

    def test_a_zero_starts_the_history(self) -> None:
        item = self.item()
        self.enter(item, 2023, 4, 0)
        self.enter(item, 2025, 1, 6)
        self.assertAlmostEqual(
            float(self.consumption(item).mean_year), 2)

    def test_the_current_year_stays_out_of_the_mean(self) -> None:
        item = self.item(quantity=20)
        self.enter(item, 2025, 1, 8)
        self.enter(item, 2026, 1, 100)
        self.deliver(item, 5, date(2026, 10, 1))
        figures = self.consumption(item)
        self.assertAlmostEqual(float(figures.mean_year), 8)
        self.assertEqual(figures.this_year, 105)

    def test_a_year_is_complete_when_today_is_in_the_next(self) -> None:
        item = self.item()
        self.enter(item, 2025, 1, 8)
        self.assertTrue(
            self.consumption(item, date(2025, 12, 31)).projected)
        figures = self.consumption(item, date(2026, 1, 1))
        self.assertFalse(figures.projected)
        self.assertAlmostEqual(float(figures.mean_year), 8)
        self.assertEqual(figures.this_year, 0)

    def test_the_current_year_so_far(self) -> None:
        item = self.item(quantity=20)
        self.enter(item, 2025, 1, 8)
        self.deliver(item, 5, date(2026, 2, 1))
        self.assertEqual(self.consumption(item).this_year, 5)
        self.assertEqual(self.consumption(item, date(2025, 6, 1)).this_year,
                         8)

    def test_a_mean_of_zero_is_never_delivered(self) -> None:
        item = self.item(quantity=2)
        self.enter(item, 2025, 1, 0)
        figures = self.consumption(item)
        self.assertEqual(float(figures.mean_year), 0)
        self.assertEqual(float(figures.mean_quarter), 0)
        self.assertIsNone(figures.coverage)
        self.assertEqual(figures.level, "undelivered")

    def test_never_delivered_wins_over_out(self) -> None:
        item = self.item(quantity=0)
        self.enter(item, 2025, 1, 0)
        self.assertEqual(self.consumption(item).level, "undelivered")

    def test_an_empty_item_has_a_coverage_of_zero(self) -> None:
        item = self.item(quantity=0)
        self.with_mean_quarter(item, 4)
        figures = self.consumption(item)
        self.assertEqual(float(figures.coverage), 0)
        self.assertEqual(figures.level, "out")

    def test_the_mean_per_quarter_is_a_quarter_of_the_year(self) -> None:
        item = self.item()
        self.enter(item, 2022, 1, 9)
        figures = self.consumption(item)
        self.assertAlmostEqual(float(figures.mean_year), 9 / 4)
        self.assertAlmostEqual(float(figures.mean_quarter), 9 / 16)

    def test_no_consumption(self) -> None:
        """Scenario: No consumption."""
        item = self.item(quantity=2)
        figures = self.consumption(item)
        self.assertIsNone(figures.mean_year)
        self.assertIsNone(figures.mean_quarter)
        self.assertIsNone(figures.coverage)
        self.assertEqual(figures.level, "undelivered")
        self.assertEqual(figures.this_year, 0)


class EnteredValueTests(InventoryCase):

    def test_entered_consumption_replaced(self) -> None:
        """Scenario: Entered consumption replaced."""
        item = self.item()
        enter_consumption(self.kl, item, year=2026, quarter=2, count=4)
        enter_consumption(self.kl, item, year=2026, quarter=2, count=5)
        entered = EnteredConsumption.objects.get(item=item, year=2026,
                                                 quarter=2)
        self.assertEqual(entered.count, 5)
        self.assertEqual(item.entered_consumption.count(), 1)

    def test_other_quarters_stay(self) -> None:
        item = self.item()
        self.enter(item, 2026, 1, 3)
        self.enter(item, 2026, 2, 4)
        self.enter(item, 2025, 2, 5)
        self.assertEqual(item.entered_consumption.count(), 3)

    def test_none_removes_the_value(self) -> None:
        item = self.item()
        self.enter(item, 2026, 1, 3)
        self.enter(item, 2026, 2, 4)
        self.enter(item, 2026, 1, None)
        self.assertEqual(
            list(item.entered_consumption.values_list("quarter", "count")),
            [(2, 4)])

    def test_zero_is_a_value(self) -> None:
        item = self.item()
        self.enter(item, 2026, 1, 0)
        self.assertEqual(item.entered_consumption.get().count, 0)

    def test_a_negative_count_is_refused(self) -> None:
        item = self.item()
        before = snapshot()
        with self.assertRaises(Refused):
            enter_consumption(self.kl, item, year=2026, quarter=1, count=-1)
        self.assertEqual(snapshot(), before)

    def test_a_quarter_is_one_to_four(self) -> None:
        item = self.item()
        before = snapshot()
        for quarter in (0, 5):
            with self.subTest(quarter=quarter), self.assertRaises(Refused):
                enter_consumption(self.kl, item, year=2026, quarter=quarter,
                                  count=1)
        self.assertEqual(snapshot(), before)

    def test_it_changes_no_quantity(self) -> None:
        item = self.item(quantity=5)
        self.enter(item, 2025, 1, 3)
        self.assertEqual(item.movements.count(), 1)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 3)


class ExactCoverageTests(InventoryCase):

    def test_coverage_is_exact_where_the_mean_recurs(self) -> None:
        item = self.item(quantity=6)
        self.enter(item, 2023, 1, 32)
        self.enter(item, 2026, 1, 1)
        figures = self.consumption(item)
        self.assertEqual(figures.coverage, Decimal("2.25"))
