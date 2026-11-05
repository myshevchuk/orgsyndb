"""Tests of the demand models (production-planning: Demand models)."""

from datetime import date

from django.test import SimpleTestCase

from planning import forecast
from planning.forecast import OrderModel, QuarterlyModel

from .inventory_support import TODAY
from .planning_support import (WINDOW, eight_orders, lumpy, middle, params,
                               quarter_days, quarters_back)


def demand(entered=None, orders=None, **over):
    return forecast.demand(entered or {}, orders or [], TODAY,
                           params(**over))


def on(quarter, count, *more):
    """Orders of ``count`` in the middle of ``quarter``."""
    return [(middle(quarter), count)] + [(middle(quarter), c) for c in more]


class OrderModelTests(SimpleTestCase):

    def test_eight_quarters_of_one_order(self) -> None:
        """Scenario: Order model."""
        model = eight_orders()
        self.assertIsInstance(model, OrderModel)
        self.assertFalse(model.rough)
        self.assertAlmostEqual(model.rate, 8 / 730, places=12)
        self.assertEqual(sorted(model.sizes), [10] * 8)

    def test_the_eight_quarters_hold_730_days(self) -> None:
        self.assertEqual(sum(map(quarter_days, quarters_back(8))), 730)

    def test_the_sizes_are_the_counts_of_the_orders(self) -> None:
        model = lumpy([2, 3, 4, 6, 7, 11, 13])
        self.assertIsInstance(model, OrderModel)
        self.assertEqual(sorted(model.sizes), [2, 3, 4, 6, 7, 11, 13])

    def test_equal_sizes_are_kept_as_often_as_they_occur(self) -> None:
        model = lumpy([1, 1, 1, 1, 1, 1, 5])
        self.assertEqual(sorted(model.sizes), [1, 1, 1, 1, 1, 1, 5])

    def test_the_rate_of_a_short_window_counts_all_its_quarters(
            self) -> None:
        """The first quarter with data starts the window: the three
        quarters of 2026 hold 273 days and all seven orders."""
        model = lumpy()
        days = sum(map(quarter_days, [(2026, 1), (2026, 2), (2026, 3)]))
        self.assertEqual(days, 273)
        self.assertAlmostEqual(model.rate, 7 / 273, places=12)

    def test_rising_demand_counts_at_once(self) -> None:
        """The rate is the larger of the whole window's and the latest
        four quarters'."""
        quarters = quarters_back(8)
        early = [(middle(q), 5) for q in quarters[:2]]
        late = [(middle(q), 5) for q in quarters[4:]] * 2
        model = demand(orders=early + late)
        self.assertIsInstance(model, OrderModel)
        self.assertEqual(len(model.sizes), 10)
        self.assertAlmostEqual(model.rate, 8 / 365, places=12)

    def test_falling_demand_keeps_the_longer_rate(self) -> None:
        quarters = quarters_back(8)
        early = [(middle(q), 5) for q in quarters[:4]] * 2
        late = [(middle(q), 5) for q in quarters[4:6]]
        model = demand(orders=early + late)
        self.assertEqual(len(model.sizes), 10)
        self.assertAlmostEqual(model.rate, 10 / 730, places=12)

    def test_the_rate_divides_by_the_days_of_the_order_window(
            self) -> None:
        """Entered values end the order window early, at the six
        quarters after them."""
        entered = {q: 5 for q in WINDOW[:6]}
        orders = [(middle(q), 3) for q in quarters_back(6)] * 2
        model = demand(entered, orders)
        self.assertIsInstance(model, OrderModel)
        self.assertEqual(len(model.sizes), 12)
        days = sum(map(quarter_days, quarters_back(6)))
        latest = sum(map(quarter_days, quarters_back(4)))
        self.assertAlmostEqual(
            model.rate, max(12 / days, 8 / latest), places=12)

    def test_per_year_is_the_rate_times_the_mean_size(self) -> None:
        model = lumpy([2, 3, 4, 6, 7, 11, 13])
        self.assertAlmostEqual(model.per_year, 365.25 * (7 / 273) * 46 / 7,
                               places=9)
        self.assertAlmostEqual(eight_orders().per_year,
                               365.25 * 8 / 730 * 10, places=9)


class OrderWindowTests(SimpleTestCase):

    def test_orders_in_or_before_an_entered_quarter_do_not_count(
            self) -> None:
        """The order window runs back to the latest quarter with an
        entered value, not including it."""
        entered = {(2025, 4): 20}
        before = on((2025, 2), 99, 99, 99, 99) + on((2025, 3), 99)
        inside = on((2025, 4), 98)
        after = [(date(2026, 1, 10), 1), (date(2026, 2, 10), 2),
                 (date(2026, 4, 10), 3), (date(2026, 5, 10), 4),
                 (date(2026, 7, 10), 5), (date(2026, 8, 10), 6)]
        model = demand(entered, before + inside + after)
        self.assertIsInstance(model, OrderModel)
        self.assertEqual(sorted(model.sizes), [1, 2, 3, 4, 5, 6])
        self.assertAlmostEqual(model.rate, 6 / 273, places=12)

    def test_too_few_orders_after_the_entered_quarters(self) -> None:
        entered = {(2025, 4): 20}
        before = on((2025, 2), 9, 9, 9, 9, 9, 9, 9)
        after = [(date(2026, 1, 10), 1), (date(2026, 2, 10), 2),
                 (date(2026, 4, 10), 3), (date(2026, 5, 10), 4),
                 (date(2026, 7, 10), 5)]
        self.assertIsInstance(demand(entered, before + after),
                              QuarterlyModel)

    def test_the_latest_entered_quarter_ends_the_window(self) -> None:
        """An earlier entered quarter does not matter."""
        entered = {(2025, 1): 4, (2025, 3): 4}
        orders = (on((2025, 2), 7, 7, 7)
                  + on((2025, 4), 1, 2, 3, 4, 5, 6))
        model = demand(entered, orders)
        self.assertIsInstance(model, OrderModel)
        self.assertEqual(sorted(model.sizes), [1, 2, 3, 4, 5, 6])

    def test_entered_values_leave_too_few_orders(self) -> None:
        """Scenario: Entered values leave too few orders."""
        entered = {q: 5 for q in WINDOW[:-1]}
        model = demand(entered, on((2026, 3), 3, 4))
        self.assertIsInstance(model, QuarterlyModel)
        self.assertTrue(model.rough)

    def test_the_minimum_is_met_by_exactly_that_many_orders(self) -> None:
        six = [(date(2026, month, 10), 2) for month in range(1, 7)]
        self.assertIsInstance(demand(orders=six), OrderModel)
        self.assertIsInstance(demand(orders=six[:5]), QuarterlyModel)

    def test_min_orders_is_a_parameter(self) -> None:
        five = [(date(2026, month, 10), 2) for month in range(1, 6)]
        self.assertIsInstance(demand(orders=five), QuarterlyModel)
        self.assertIsInstance(demand(orders=five, min_orders=5),
                              OrderModel)
        self.assertIsInstance(demand(orders=five, min_orders=3),
                              OrderModel)
        six = five + [(date(2026, 6, 10), 2)]
        self.assertIsInstance(demand(orders=six, min_orders=7),
                              QuarterlyModel)

    def test_orders_outside_the_history_window_do_not_count(self) -> None:
        recent = [(date(2026, month, 10), 2) for month in range(1, 7)]
        old = [(date(2022, 5, 10), 77), (date(2022, 6, 10), 77),
               (date(2023, 5, 10), 77)]
        model = demand(orders=old + recent)
        self.assertIsInstance(model, OrderModel)
        self.assertEqual(sorted(model.sizes), [2] * 6)

    def test_old_orders_do_not_make_up_the_minimum(self) -> None:
        recent = [(date(2026, month, 10), 2) for month in range(1, 4)]
        old = [(date(2022, month, 10), 2) for month in range(1, 7)]
        self.assertIsInstance(demand(orders=old + recent), QuarterlyModel)

    def test_the_history_window_is_a_parameter(self) -> None:
        recent = [(date(2026, month, 10), 2) for month in range(1, 7)]
        orders = [(date(2024, 5, 10), 77)] * 4 + recent
        for count, expected in ((12, [2] * 6 + [77] * 4), (4, [2] * 6),
                                (40, [2] * 6 + [77] * 4)):
            with self.subTest(history_quarters=count):
                model = demand(orders=orders, history_quarters=count)
                self.assertIsInstance(model, OrderModel)
                self.assertEqual(sorted(model.sizes), sorted(expected))

    def test_orders_of_the_current_quarter_do_not_count(self) -> None:
        five = [(date(2026, month, 10), 2) for month in range(1, 6)]
        now = [(date(2026, 10, 10), 2), (date(2026, 10, 20), 2)]
        self.assertIsInstance(demand(orders=five + now), QuarterlyModel)


class QuarterlyModelTests(SimpleTestCase):

    def test_rising_demand(self) -> None:
        """Scenario: Rising demand in the quarterly model."""
        entered = {q: (4 if index < 8 else 12)
                   for index, q in enumerate(WINDOW)}
        model = demand(entered)
        self.assertIsInstance(model, QuarterlyModel)
        self.assertTrue(model.rough)
        self.assertEqual(model.quarters, 12)
        self.assertAlmostEqual(model.m, 12)
        self.assertAlmostEqual(model.v, 15.52, places=2)

    def test_m_is_the_larger_of_all_and_the_latest_four(self) -> None:
        entered = {q: (12 if index < 4 else 4)
                   for index, q in enumerate(WINDOW)}
        model = demand(entered)
        self.assertAlmostEqual(model.m, 80 / 12, places=9)
        self.assertAlmostEqual(model.v, 15.515151515, places=6)

    def test_v_is_at_least_m(self) -> None:
        """Even demand has no variance; a Poisson process has as much as
        its mean."""
        model = demand({q: 9 for q in WINDOW})
        self.assertAlmostEqual(model.m, 9)
        self.assertAlmostEqual(model.v, 9)

    def test_v_is_the_sample_variance_when_it_is_larger(self) -> None:
        entered = {q: (0 if index % 2 else 20)
                   for index, q in enumerate(WINDOW)}
        model = demand(entered)
        self.assertAlmostEqual(model.m, 10)
        self.assertAlmostEqual(model.v, 12 * 100 / 11, places=9)

    def test_a_single_quarter_has_variance_zero_so_v_is_m(self) -> None:
        model = demand({(2026, 3): 6})
        self.assertEqual(model.quarters, 1)
        self.assertAlmostEqual(model.m, 6)
        self.assertAlmostEqual(model.v, 6)

    def test_quarters_before_the_first_with_data_are_left_out(self) -> None:
        entered = {q: 8 for q in WINDOW[-5:]}
        model = demand(entered)
        self.assertEqual(model.quarters, 5)
        self.assertAlmostEqual(model.m, 8)

    def test_quarters_after_the_first_without_data_count_as_zero(
            self) -> None:
        entered = {(2025, 3): 8, (2026, 1): 8}
        model = demand(entered)
        self.assertEqual(model.quarters, 5)
        self.assertAlmostEqual(model.m, 3.2)
        self.assertAlmostEqual(model.v, 19.2)

    def test_the_latest_four_are_all_when_there_are_fewer(self) -> None:
        model = demand({(2026, 1): 3, (2026, 2): 6, (2026, 3): 9})
        self.assertEqual(model.quarters, 3)
        self.assertAlmostEqual(model.m, 6)

    def test_the_window_holds_the_last_complete_quarters(self) -> None:
        """The quarter of the day is not complete; 2023 Q3 lies outside
        the twelve."""
        entered = {(2023, 3): 1000, (2026, 4): 1000}
        entered.update({q: 3 for q in WINDOW})
        model = demand(entered)
        self.assertEqual(model.quarters, 12)
        self.assertAlmostEqual(model.m, 3)

    def test_history_quarters_is_a_parameter(self) -> None:
        entered = {q: 100 for q in quarters_back(40)}
        entered.update({q: 5 for q in quarters_back(4)})
        for count, expected in ((4, 5), (8, 52.5)):
            with self.subTest(history_quarters=count):
                model = demand(entered, history_quarters=count)
                self.assertEqual(model.quarters, count)
                self.assertAlmostEqual(model.m, expected)

    def test_quarters_count_deliveries_as_well(self) -> None:
        """The totals are the entered values and the containers
        delivered; the orders here are too few for the order model."""
        entered = {(2026, 1): 4}
        orders = [(date(2026, 1, 20), 3), (date(2026, 2, 20), 3),
                  (date(2026, 5, 20), 6)]
        model = demand(entered, orders)
        self.assertIsInstance(model, QuarterlyModel)
        self.assertEqual(model.quarters, 3)
        # 2026 Q1: 4 entered and 6 delivered; Q2: 6; Q3: 0.
        self.assertAlmostEqual(model.m, 16 / 3)
        self.assertAlmostEqual(model.v, 76 / 3, places=9)

    def test_per_year_is_four_times_m(self) -> None:
        self.assertAlmostEqual(demand({q: 9 for q in WINDOW}).per_year, 36)
        entered = {q: (4 if index < 8 else 12)
                   for index, q in enumerate(WINDOW)}
        self.assertAlmostEqual(demand(entered).per_year, 48)

    def test_per_year_keeps_its_fraction(self) -> None:
        window = quarters_back(16)
        entered = {q: (10 if index == 0 else 9)
                   for index, q in enumerate(window)}
        model = demand(entered, history_quarters=16)
        self.assertAlmostEqual(model.m, 145 / 16, places=12)
        self.assertEqual(model.per_year, 36.25)


class NoDemandTests(SimpleTestCase):

    def test_nothing_at_all(self) -> None:
        self.assertIsNone(demand())

    def test_only_zeros(self) -> None:
        self.assertIsNone(demand({q: 0 for q in WINDOW}))

    def test_only_the_current_quarter_has_data(self) -> None:
        """The history window is empty."""
        self.assertIsNone(demand(orders=[(date(2026, 10, 20), 5)]))
        self.assertIsNone(demand({(2026, 4): 5}))

    def test_data_that_lie_before_the_window(self) -> None:
        """The window holds no consumption."""
        self.assertIsNone(demand({(2020, 1): 50}))
        self.assertIsNone(demand(orders=[(date(2021, 3, 3), 4)]))

    def test_consumption_in_the_window_is_demand(self) -> None:
        self.assertIsNotNone(demand({(2026, 3): 1}))
        self.assertIsNotNone(demand(orders=[(date(2026, 8, 1), 1)]))
