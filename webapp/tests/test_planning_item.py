"""Tests of the item forecast and the delivery rhythm
(production-planning: Item forecast)."""

import math
import re
from datetime import date, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from inventory.bookings import book_note, reverse, reverse_historical
from planning import forecast
from planning.forecast import OrderModel, QuarterlyModel

from . import build_index, make_task
from .inventory_support import (MICRO, TODAY, has_amount, has_number,
                                item_url, newest_movement)
from .planning_support import (WINDOW, PlanningCase, has_date, has_days,
                               section)

D = Decimal
NO_FORECAST_DE = "Kein Verbrauch, keine Prognose."
NO_FORECAST_EN = "No consumption, no forecast."
ORDER_SIZES = [2, 3, 5, 8, 17, 23, 31, 40, 59]


def rough_marks(text: str) -> int:
    return len(re.findall(r"(?<!\w)(?:grob|rough)", text, re.I))


class RhythmTests(SimpleTestCase):

    def test_delivery_rhythm(self) -> None:
        """Scenario: Delivery rhythm."""
        found = forecast.rhythm(
            [date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 31),
             date(2026, 10, 1)], TODAY)
        self.assertEqual(found.last, date(2026, 10, 1))
        self.assertEqual(found.past_year, 4)
        self.assertEqual(found.interval, 31)
        self.assertEqual(found.next, date(2026, 11, 1))

    def test_the_dates_may_come_in_any_order(self) -> None:
        found = forecast.rhythm(
            [date(2026, 10, 1), date(2026, 6, 1), date(2026, 8, 31),
             date(2026, 7, 1)], TODAY)
        self.assertEqual((found.last, found.interval, found.next),
                         (date(2026, 10, 1), 31, date(2026, 11, 1)))

    def test_no_delivery(self) -> None:
        found = forecast.rhythm([], TODAY)
        self.assertEqual((found.last, found.past_year, found.interval,
                          found.next), (None, 0, None, None))

    def test_fewer_than_three_notes_give_no_interval(self) -> None:
        for dates in ([date(2026, 9, 1)],
                      [date(2026, 8, 1), date(2026, 9, 1)]):
            with self.subTest(count=len(dates)):
                found = forecast.rhythm(dates, TODAY)
                self.assertEqual(found.last, date(2026, 9, 1))
                self.assertEqual(found.past_year, len(dates))
                self.assertIsNone(found.interval)
                self.assertIsNone(found.next)

    def test_the_median_is_rounded_half_up(self) -> None:
        """Intervals of 30 and 61 days have the median 45.5."""
        found = forecast.rhythm(
            [date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 31)],
            TODAY)
        self.assertEqual(found.interval, 46)
        self.assertEqual(found.next, date(2026, 10, 16))

    def test_the_median_of_an_even_number_of_intervals(self) -> None:
        start = date(2026, 1, 1)
        for steps, expected in (((10, 20, 30, 40), 25),
                                ((10, 21, 30, 41), 26),
                                ((10, 20, 31, 40), 26)):
            dates = [start]
            for step in steps:
                dates.append(dates[-1] + timedelta(days=step))
            with self.subTest(steps=steps):
                found = forecast.rhythm(dates, TODAY)
                self.assertEqual(found.interval, expected)
                self.assertEqual(found.next,
                                 dates[-1] + timedelta(days=expected))

    def test_the_median_is_not_the_mean(self) -> None:
        found = forecast.rhythm(
            [date(2026, 1, 1), date(2026, 1, 11), date(2026, 1, 21),
             date(2026, 9, 1)], TODAY)
        self.assertEqual(found.interval, 10)

    def test_the_interval_looks_back_730_days(self) -> None:
        """A note from 2023 is not among the three or the intervals."""
        found = forecast.rhythm(
            [date(2023, 1, 1), date(2026, 6, 1), date(2026, 7, 1),
             date(2026, 8, 31)], TODAY)
        self.assertEqual(found.interval, 46)
        self.assertEqual(found.last, date(2026, 8, 31))
        self.assertEqual(found.past_year, 3)

    def test_old_notes_alone_give_no_interval_but_a_last_delivery(
            self) -> None:
        found = forecast.rhythm(
            [date(2022, 1, 1), date(2022, 2, 1), date(2022, 3, 1),
             date(2026, 9, 1)], TODAY)
        self.assertIsNone(found.interval)
        self.assertEqual(found.last, date(2026, 9, 1))
        self.assertEqual(found.past_year, 1)

    def test_the_past_year_counts_365_days(self) -> None:
        found = forecast.rhythm(
            [date(2025, 3, 1), date(2025, 6, 1), date(2025, 9, 1),
             date(2026, 10, 1)], TODAY)
        self.assertEqual(found.past_year, 1)
        self.assertEqual(found.interval, 92)
        found = forecast.rhythm(
            [date(2025, 12, 1), date(2026, 3, 1), date(2026, 10, 1)],
            TODAY)
        self.assertEqual(found.past_year, 3)

    def test_the_next_delivery_may_lie_in_the_past(self) -> None:
        found = forecast.rhythm(
            [date(2025, 10, 1), date(2025, 11, 1), date(2025, 12, 1),
             date(2026, 1, 1)], TODAY)
        self.assertEqual(found.interval, 31)
        self.assertEqual(found.next, date(2026, 2, 1))


class FigureTests(PlanningCase):
    """The figures of an article."""

    def test_forecast_figures(self) -> None:
        """Scenario: Forecast figures."""
        self.planned_item("NV-1", quantity=10)
        found = self.forecast("NV-1")
        self.assertEqual((found.article_number, found.bulk_unit),
                         ("NV-1", "mg"))
        self.assertEqual(math.floor(found.runway), 60)
        self.assertEqual((found.synthesis_days, found.basis_count),
                         (21, None))
        self.assertEqual(math.floor(found.slack), 11)
        self.assertEqual(found.latest_start, date(2026, 11, 15))
        self.assertEqual(found.priority, "high")
        self.assertEqual(found.yield_amount, D(42))
        self.assertEqual(found.lacking, {})
        self.assertIsInstance(found.yield_amount, Decimal)

    def test_the_name_is_that_of_the_first_item(self) -> None:
        """The first in the item list's order, though it has no
        demand."""
        self.item("NV-1", "Erste", "5", "mg", 1)
        self.planned_item("NV-1", size="10", quantity=1, name="Zweite")
        self.assertEqual(self.forecast("NV-1").name, "Erste")

    def test_the_model_of_each_item(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        entry = self.forecast("NV-1").items[0]
        self.assertEqual(entry.item.pk, item.pk)
        self.assertIsInstance(entry.model, QuarterlyModel)
        self.assertTrue(entry.model.rough)
        self.assertAlmostEqual(entry.runway_on_hand, 60.654, places=3)

    def test_orders_make_an_order_model(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        self.orders(item, *[(date(2026, month, 10), size)
                            for month, size in enumerate(ORDER_SIZES, 1)])
        entry = self.forecast("NV-1").items[0]
        self.assertIsInstance(entry.model, OrderModel)
        self.assertEqual(sorted(entry.model.sizes), ORDER_SIZES)

    def test_reversed_lines_are_left_out(self) -> None:
        """Lines of reversed historical notes and of reversed deliveries
        make no order."""
        item = self.item("NV-1", "NV-1", "1", "mg", 100)
        self.orders(item, *[(date(2026, month, 10), 2)
                            for month in range(1, 7)])
        gone = book_note(self.kl, date=date(2026, 7, 10),
                         lines=[(item, 99)], historical=True)
        self.deliver(item, 98, date(2026, 8, 10))
        self.assertEqual(self.sizes(), [2] * 6 + [98, 99])
        reverse(self.kl, newest_movement(item), note="falsch")
        self.assertEqual(self.sizes(), [2] * 6 + [99])
        reverse_historical(self.kl, gone, note="falsch")
        self.assertEqual(self.sizes(), [2] * 6)

    def sizes(self) -> list[int]:
        return sorted(self.forecast("NV-1").items[0].model.sizes)

    def test_a_reversed_delivery_makes_no_order(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 100)
        self.orders(item, *[(date(2026, month, 10), 2)
                            for month in range(1, 6)])
        self.deliver(item, 50, date(2026, 7, 10))
        self.assertIsInstance(self.forecast("NV-1").items[0].model,
                              OrderModel)
        reverse(self.kl, newest_movement(item), note="falsch")
        self.assertIsInstance(self.forecast("NV-1").items[0].model,
                              QuarterlyModel)

    def test_an_item_without_demand_in_an_article_with_demand(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10)
        quiet = self.item("NV-1", "NV-1", "5", "mg", 4)
        entries = self.forecast("NV-1").items
        self.assertEqual(entries[1].item.pk, quiet.pk)
        self.assertIsNone(entries[1].model)
        self.assertIsNone(entries[1].runway_on_hand)

    def test_no_demand_no_forecast(self) -> None:
        self.item("NV-1", "NV-1", "1", "mg", 10)
        self.assertIsNone(self.forecast("NV-1"))


class YieldTests(PlanningCase):
    """The amount a new synthesis must yield, for ``L``, the buffer and
    the target days at the article's certainty."""

    def test_the_usable_bulk_is_taken_off(self) -> None:
        """41.3 containers lacking make 42 mg; a lot of 6 mg counts 5."""
        self.planned_item("NV-1", quantity=10)
        self.assertEqual(self.forecast("NV-1").yield_amount, D(42))
        self.lot("NV-1", "mg", "6")
        self.assertEqual(self.forecast("NV-1").yield_amount, D(37))
        self.lot("NV-1", "mg", "11")
        self.assertEqual(self.forecast("NV-1").yield_amount, D(27))

    def test_nothing_lacking_gives_zero(self) -> None:
        self.planned_item("NV-1", quantity=1000)
        self.assertEqual(self.forecast("NV-1").yield_amount, D(0))

    def test_bulk_beyond_the_need_gives_zero(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.lot("NV-1", "mg", "500")
        self.assertEqual(self.forecast("NV-1").yield_amount, D(0))

    def test_the_time_is_the_synthesis_time_the_buffer_and_the_target(
            self) -> None:
        self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        self.assertEqual(self.forecast("NV-1").yield_amount, D(44))

    def test_a_short_time_needs_little(self) -> None:
        """One day of synthesis, no buffer and 30 days: 31 days need
        5.93 containers, so 6 mg."""
        self.planned_item("NV-1", quantity=0)
        self.parameters(target_days=30, buffer_days=0,
                        default_synthesis_days=1)
        self.assertEqual(self.forecast("NV-1").yield_amount, D(6))

    def test_the_certainty_and_the_parameters_change_it(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.parameters(certainty=0.9, buffer_days=33,
                        default_synthesis_days=17, target_days=222)
        self.assertEqual(self.forecast("NV-1").yield_amount, D(24))

    def test_shared_by_two_sizes(self) -> None:
        self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.lot("NV-2", "mg", "360")
        found = self.forecast("NV-2")
        self.assertEqual(found.yield_amount, D(1280))
        self.assertEqual(found.lacking, {})

    def test_micromoles_and_milligrams(self) -> None:
        """A compound with a molar mass has a bulk of µmol; the yield
        shows also in whole mg."""
        self.planned_item("CH-0012", size="10", unit="umol", quantity=5)
        self.lot("CH-0012", "mg", "20")
        found = self.forecast("CH-0012")
        self.assertEqual(found.bulk_unit, "umol")
        self.assertEqual(found.yield_amount, D(346))
        self.assertEqual(found.yield_mg, 52)
        self.assertIsInstance(found.yield_mg, int)

    def test_an_item_that_does_not_convert_is_counted_in_containers(
            self) -> None:
        mg = self.planned_item("NV-6", size="5", unit="mg", quantity=10)
        micro = self.planned_item("NV-6", size="1", unit="umol",
                                  quantity=10)
        found = self.forecast("NV-6")
        self.assertEqual(found.yield_amount, D(220))
        self.assertEqual(found.lacking, {micro.pk: 44})
        self.assertNotIn(mg.pk, found.lacking)

    def test_an_unplanned_first_item_sets_no_bulk_unit(self) -> None:
        """The first item by unit has never been delivered, so the item
        with demand sets the bulk unit and converts into it."""
        self.item("NV-7", "NV-7", "1", "mg", 10)
        self.planned_item("NV-7", size="5", unit="umol", quantity=10)
        found = self.forecast("NV-7")
        self.assertEqual(found.bulk_unit, "umol")
        self.assertIsNotNone(found.yield_amount)
        self.assertIsNone(found.yield_mg)
        self.assertEqual(found.lacking, {})
        self.assertEqual(found.usable_bulk, D(0))

    def test_an_item_that_lacks_nothing_lacks_no_containers(self) -> None:
        self.planned_item("NV-6", size="5", unit="mg", quantity=10)
        micro = self.planned_item("NV-6", size="1", unit="umol",
                                  quantity=1000)
        self.assertEqual(self.forecast("NV-6").lacking.get(micro.pk, 0), 0)


class PageCase(PlanningCase):

    def prognosis(self, item, signed_in: bool = False):
        return section(self.get(item_url(item), signed_in), "Prognose",
                       "Forecast")


class ForecastPageTests(PageCase):

    def test_forecast_figures(self) -> None:
        """Scenario: Forecast figures."""
        item = self.planned_item("NV-1", quantity=10)
        found = self.prognosis(item)
        text = found.text()
        self.assertTrue(has_days(text, 60), text)
        self.assertTrue(has_days(text, 21), text)
        self.assertIn("Vorgabe", text)
        self.assertTrue(has_days(text, 11), text)
        self.assertTrue(has_date(text, date(2026, 11, 15)), text)
        self.assertIn("hoch", text)
        self.assertTrue(has_amount(text, "42", "mg"), text)
        self.assertGreaterEqual(rough_marks(text), 5, text)

    def test_the_forecast_is_public(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.assertTrue(has_days(self.prognosis(item).text(), 60))
        self.assertTrue(has_days(self.prognosis(item, True).text(), 60))

    def test_the_quarterly_model(self) -> None:
        entered = [4] * 8 + [12] * 4
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        for (year, quarter), count in zip(WINDOW, entered):
            self.enter(item, year, quarter, count)
        text = self.prognosis(item).text()
        self.assertTrue(has_number(text, "12"), text)
        self.assertRegex(text, r"15,5\d?(?!\d)")
        self.assertGreaterEqual(rough_marks(text), 1)

    def test_the_order_model(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        self.orders(item, *[(date(2026, month, 10), size)
                            for month, size in enumerate(ORDER_SIZES, 1)])
        text = self.prognosis(item).text()
        self.assertTrue(has_number(text, "9"), text)
        self.assertTrue(has_number(text, "17"), text)
        self.assertTrue(has_number(text, "59"), text)
        self.assertEqual(rough_marks(text), 0, text)

    def test_the_basis_of_the_synthesis_time(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        text = self.prognosis(item).text()
        self.assertTrue(has_days(text, 40), text)
        self.assertIn("längste der letzten 3 Synthesen", text)
        self.assertNotIn("Vorgabe", text)

    def test_the_english_page(self) -> None:
        self.use_index(build_index("en"))
        item = self.planned_item("NV-1", quantity=10)
        text = self.prognosis(item).text()
        self.assertTrue(has_days(text, 60), text)
        self.assertIn("default", text)
        self.assertGreaterEqual(rough_marks(text), 5, text)
        self.assertTrue(has_date(text, date(2026, 11, 15)), text)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        self.assertIn("longest of the last 3 syntheses",
                      self.prognosis(item).text())

    def test_the_article_of_two_sizes(self) -> None:
        small = self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.lot("NV-2", "mg", "360")
        for item in (small, large):
            with self.subTest(item=item.size):
                text = self.prognosis(item).text()
                self.assertTrue(has_days(text, 62), text)
                self.assertTrue(has_days(text, 13), text)
                self.assertTrue(has_amount(text, "340", "mg"), text)
                self.assertTrue(has_amount(text, "1280", "mg")
                                or has_amount(text, "1.280", "mg"), text)
                self.assertTrue(
                    has_date(text, TODAY + timedelta(days=13)), text)

    def test_the_runway_on_hand_is_that_of_the_item(self) -> None:
        small = self.planned_item("NV-1", size="1", quantity=10)
        large = self.item("NV-1", "NV-1", "5", "mg", 20)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.assertTrue(has_days(self.prognosis(small).text(), 60))
        self.assertTrue(has_days(self.prognosis(large).text(), 140))

    def test_micromoles_and_milligrams(self) -> None:
        item = self.planned_item("CH-0012", size="10", unit="umol",
                                 quantity=5)
        self.lot("CH-0012", "mg", "20")
        text = self.prognosis(item).text()
        self.assertTrue(has_amount(text, "346", MICRO + "mol"), text)
        self.assertTrue(has_amount(text, "52", "mg"), text)

    def test_an_item_that_does_not_convert_shows_containers(self) -> None:
        self.planned_item("NV-6", size="5", unit="mg", quantity=10)
        micro = self.planned_item("NV-6", size="1", unit="umol",
                                  quantity=10)
        text = self.prognosis(micro).text()
        self.assertTrue(has_number(text, "44"), text)
        self.assertTrue(has_amount(text, "220", "mg"), text)

    def test_each_figure_names_its_parameters(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.parameters(certainty=0.9, buffer_days=33, target_days=222)
        text = self.prognosis(item).text()
        self.assertRegex(text, r"(?<![\d,.])(?:0,9|90)(?!\d)")
        self.assertTrue(has_number(text, "33"), text)
        self.assertTrue(has_number(text, "222"), text)

    def test_the_default_parameters_are_named_too(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        text = self.prognosis(item).text()
        self.assertRegex(text, r"(?<![\d,.])(?:0,95|95)(?!\d)")
        self.assertTrue(has_number(text, "28"), text)
        self.assertTrue(has_number(text, "365"), text)

    def test_an_item_without_demand(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        text = self.prognosis(item).text()
        self.assertIn(NO_FORECAST_DE, text)
        self.assertNotIn("Tage", text)
        self.assertEqual(rough_marks(text), 0)

    def test_an_item_without_demand_in_english(self) -> None:
        self.use_index(build_index("en"))
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        self.assertIn(NO_FORECAST_EN, self.prognosis(item).text())

    def test_an_item_without_demand_in_an_article_with_demand(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10)
        quiet = self.item("NV-1", "NV-1", "5", "mg", 4)
        self.assertIn(NO_FORECAST_DE, self.prognosis(quiet).text())

    def test_the_forecast_has_a_heading_of_its_own(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        root = self.get(item_url(item))
        headings = [h.text() for h in root.find_all(("h1", "h2", "h3"))]
        self.assertIn("Prognose", headings)


class RhythmPageTests(PageCase):

    def test_delivery_rhythm(self) -> None:
        """Scenario: Delivery rhythm."""
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        for day in (date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 31),
                    date(2026, 10, 1)):
            self.deliver(item, 1, day)
        text = self.prognosis(item).text()
        self.assertTrue(has_date(text, date(2026, 10, 1)), text)
        self.assertTrue(has_number(text, "4"), text)
        self.assertTrue(has_days(text, 31), text)
        self.assertTrue(has_date(text, date(2026, 11, 1)), text)

    def test_the_count_and_the_interval(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        self.orders(item, *[(date(2026, 5, 17) + timedelta(days=20 * k), 2)
                            for k in range(7)])
        text = self.prognosis(item).text()
        self.assertTrue(has_date(text, date(2026, 9, 14)), text)
        self.assertTrue(has_number(text, "7"), text)
        self.assertTrue(has_days(text, 20), text)
        self.assertTrue(has_date(text, date(2026, 10, 4)), text)

    def test_two_notes_give_no_interval_and_no_next_delivery(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        self.deliver(item, 2, date(2026, 8, 1))
        self.deliver(item, 2, date(2026, 9, 1))
        text = self.prognosis(item).text()
        self.assertTrue(has_date(text, date(2026, 9, 1)), text)
        self.assertFalse(has_days(text, 31), text)
        self.assertFalse(has_date(text, date(2026, 10, 2)), text)

    def test_the_next_delivery_follows_the_last_by_the_interval(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        for day in (date(2026, 8, 1), date(2026, 8, 11),
                    date(2026, 8, 21), date(2026, 9, 10)):
            self.deliver(item, 1, day)
        text = self.prognosis(item).text()
        self.assertTrue(has_days(text, 10), text)
        self.assertTrue(has_date(text, date(2026, 9, 20)), text)

    def test_reversed_lines_do_not_count(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 30)
        for day in (date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1)):
            self.deliver(item, 1, day)
        self.deliver(item, 1, date(2026, 10, 1))
        reverse(self.kl, newest_movement(item), note="falsch")
        gone = book_note(self.kl, date=date(2026, 10, 10),
                         lines=[(item, 1)], historical=True)
        reverse_historical(self.kl, gone, note="falsch")
        text = self.prognosis(item).text()
        self.assertTrue(has_date(text, date(2026, 9, 1)), text)
        self.assertFalse(has_date(text, date(2026, 10, 1)), text)
        self.assertFalse(has_date(text, date(2026, 10, 10)), text)

    def test_deliveries_of_the_article_s_other_items_are_not_mixed_in(
            self) -> None:
        one = self.item("NV-1", "NV-1", "1", "mg", 20)
        other = self.item("NV-1", "NV-1", "5", "mg", 20)
        self.deliver(one, 1, date(2026, 8, 1))
        self.deliver(other, 1, date(2026, 9, 1))
        text = self.prognosis(one).text()
        self.assertTrue(has_date(text, date(2026, 8, 1)), text)
        self.assertFalse(has_date(text, date(2026, 9, 1)), text)

    def test_a_task_does_not_change_the_rhythm(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        self.deliver(item, 1, date(2026, 8, 1))
        make_task(self.kl, product="NV-1")
        self.assertTrue(has_date(self.prognosis(item).text(),
                                 date(2026, 8, 1)))
