"""Tests of the runway (production-planning: Runway)."""

import math
from decimal import Decimal
from statistics import NormalDist

from django.test import SimpleTestCase

from planning import forecast

from inventory.models import Unit

from .inventory_support import TODAY
from .planning_support import (WINDOW, PlanningCase, closed_form,
                               eight_orders, lumpy, params, quarterly,
                               quarters_back)

D = Decimal


class QuarterlyRunwayTests(SimpleTestCase):

    def test_even_demand(self) -> None:
        """Scenario: Even demand (the item's runway on hand)."""
        model = quarterly(9)
        self.assertAlmostEqual(model.runway(10, 0.95), 60.654, places=3)
        self.assertEqual(math.floor(model.runway(10, 0.95)), 60)
        self.assertAlmostEqual(model.runway(10, 0.5), 101.458, places=3)
        self.assertEqual(math.floor(model.runway(10, 0.5)), 101)

    def test_the_closed_form(self) -> None:
        rising = forecast.demand(
            {q: (4 if index < 8 else 12) for index, q in enumerate(WINDOW)},
            [], TODAY, params())
        for model, m, v in ((quarterly(9), 9, 9), (quarterly(1), 1, 1),
                            (rising, 12, 15.515151515151516)):
            for stock in (1, 5, 10, 250):
                for certainty in (0.5, 0.8, 0.95, 0.975, 0.999):
                    with self.subTest(m=m, stock=stock, q=certainty):
                        self.assertAlmostEqual(
                            model.runway(stock, certainty),
                            closed_form(m, v, stock, certainty), places=6)

    def test_zero_stock_has_a_runway_of_zero(self) -> None:
        for certainty in (0.5, 0.95, 0.999):
            with self.subTest(q=certainty):
                self.assertEqual(quarterly(9).runway(0, certainty), 0)

    def test_the_need_is_the_mean_plus_z_standard_deviations(self) -> None:
        model = quarterly(9)
        for days in (1, 30, 414):
            for certainty in (0.5, 0.95, 0.975):
                with self.subTest(days=days, q=certainty):
                    z = NormalDist().inv_cdf(certainty)
                    mu = 9 / 91.3125
                    sigma = (9 / 91.3125) ** 0.5
                    self.assertAlmostEqual(
                        model.need(days, certainty),
                        mu * days + z * sigma * days ** 0.5, places=9)

    def test_the_need_of_the_runway_is_the_stock(self) -> None:
        model = quarterly(9)
        for stock in (1, 10, 100):
            with self.subTest(stock=stock):
                found = model.runway(stock, 0.95)
                self.assertAlmostEqual(model.need(found, 0.95), stock,
                                       places=6)

    def test_the_need_of_no_days_is_nothing(self) -> None:
        self.assertEqual(quarterly(9).need(0, 0.95), 0)

    def test_a_longer_stock_and_a_lower_certainty_last_longer(self) -> None:
        model = quarterly(9)
        stocks = [model.runway(s, 0.95) for s in (0, 1, 2, 5, 10, 50)]
        self.assertEqual(stocks, sorted(set(stocks)))
        certainties = [model.runway(10, q)
                       for q in (0.999, 0.99, 0.95, 0.9, 0.5)]
        self.assertEqual(certainties, sorted(set(certainties)))
        needs = [model.need(h, 0.95) for h in (1, 10, 100, 1000)]
        self.assertEqual(needs, sorted(set(needs)))

    def test_a_higher_mean_shortens_the_runway(self) -> None:
        self.assertGreater(quarterly(9).runway(10, 0.95),
                           quarterly(18).runway(10, 0.95))

    def test_lumpier_demand_shortens_the_runway(self) -> None:
        """The same mean with a larger variance lasts less long."""
        even = quarterly(10)
        entered = {q: (0 if index % 2 else 20)
                   for index, q in enumerate(WINDOW)}
        lumpy_model = forecast.demand(entered, [], TODAY, params())
        self.assertAlmostEqual(lumpy_model.m, even.m)
        self.assertLess(lumpy_model.runway(10, 0.95),
                        even.runway(10, 0.95))


class OrderRunwayTests(SimpleTestCase):

    def assertRunway(self, model, stock: int, certainty: float) -> float:
        """The runway holds to 0.01 days: the need at it fits the stock,
        and a little later it does not."""
        found = model.runway(stock, certainty)
        self.assertLessEqual(model.need(max(found - 0.02, 0), certainty),
                             stock)
        self.assertGreater(model.need(found + 0.02, certainty), stock)
        return found

    def test_lumpy_orders(self) -> None:
        """Scenario: Lumpy orders."""
        model = eight_orders()
        for stock, days in ((9, 4), (10, 32), (20, 74)):
            with self.subTest(stock=stock):
                found = model.runway(stock, 0.95)
                self.assertEqual(math.floor(found), days)
        self.assertAlmostEqual(model.runway(9, 0.95), 4.6805, delta=0.011)
        self.assertAlmostEqual(model.runway(10, 0.95), 32.4267, delta=0.011)
        self.assertAlmostEqual(model.runway(20, 0.95), 74.6143, delta=0.011)

    def test_the_quarterly_model_of_the_same_history_gives_more(
            self) -> None:
        """The same eight quarters of 10 as totals: 47 days for 9."""
        entered = {q: 10 for q in quarters_back(8)}
        model = forecast.demand(entered, [], TODAY, params())
        self.assertTrue(model.rough)
        self.assertEqual(math.floor(model.runway(9, 0.95)), 47)

    def test_zero_stock_lasts_until_the_first_order(self) -> None:
        """The time within which no order arrives with probability q."""
        rate = 8 / 730
        for certainty in (0.5, 0.95, 0.99):
            with self.subTest(q=certainty):
                self.assertAlmostEqual(
                    eight_orders().runway(0, certainty),
                    -math.log(certainty) / rate, delta=0.011)
        self.assertEqual(math.floor(eight_orders().runway(0, 0.95)), 4)

    def test_a_stock_below_every_order_lasts_to_the_first(self) -> None:
        model = eight_orders()
        self.assertAlmostEqual(model.runway(9, 0.95),
                               model.runway(0, 0.95), delta=0.011)
        self.assertAlmostEqual(model.runway(1, 0.95),
                               model.runway(9, 0.95), delta=0.011)

    def test_the_need_counts_whole_orders(self) -> None:
        model = eight_orders()
        self.assertEqual(model.need(0, 0.95), 0)
        self.assertEqual(model.need(4, 0.95), 0)
        self.assertEqual(model.need(5, 0.95), 10)
        self.assertEqual(model.need(50, 0.95), 20)
        self.assertEqual(model.need(100, 0.95), 30)
        self.assertEqual(model.need(200, 0.95), 50)
        self.assertIsInstance(model.need(100, 0.95), int)

    def test_the_need_of_mixed_sizes(self) -> None:
        """The smallest n with P(demand <= n) >= q, the demand a Poisson
        number of orders of the sizes 2, 3, 4, 6, 7, 11 and 13 (273
        days, 7 orders)."""
        model = lumpy()
        expected = {
            0: (0, 0, 0), 10: (0, 11, 26), 30: (2, 18, 38),
            90: (13, 37, 64), 365: (60, 103, 147),
        }
        for days, needs in expected.items():
            for certainty, need in zip((0.5, 0.95, 0.999), needs):
                with self.subTest(days=days, q=certainty):
                    self.assertEqual(model.need(days, certainty), need)

    def test_the_runway_of_mixed_sizes(self) -> None:
        model = lumpy()
        expected = {
            (0, 0.95): 2.0, (5, 0.95): 3.468, (20, 0.95): 36.635,
            (40, 0.95): 103.586, (0, 0.5): 27.033, (5, 0.5): 43.146,
            (20, 0.5): 132.801, (40, 0.5): 250.682,
        }
        for (stock, certainty), days in expected.items():
            with self.subTest(stock=stock, q=certainty):
                self.assertAlmostEqual(
                    model.runway(stock, certainty), days, delta=0.011)
                self.assertRunway(model, stock, certainty)

    def test_a_larger_order_than_the_stock_always_breaks_it(self) -> None:
        """Every order is 13: a stock of 12 lasts until the first."""
        model = lumpy([13, 13, 13, 13, 13, 13])
        self.assertAlmostEqual(model.runway(12, 0.95),
                               model.runway(0, 0.95), delta=0.011)

    def test_the_runway_grows_with_the_stock(self) -> None:
        model = lumpy()
        found = [model.runway(s, 0.95) for s in (0, 1, 2, 5, 10, 20, 40)]
        self.assertEqual(found, sorted(found))
        self.assertGreater(found[-1], found[0])

    def test_a_lower_certainty_lasts_longer(self) -> None:
        model = lumpy()
        found = [model.runway(20, q) for q in (0.999, 0.95, 0.9, 0.5)]
        self.assertEqual(found, sorted(found))
        self.assertLess(found[0], found[-1])

    def test_the_need_grows_with_the_days_and_the_certainty(self) -> None:
        model = lumpy()
        by_days = [model.need(h, 0.95) for h in (0, 5, 30, 90, 365)]
        self.assertEqual(by_days, sorted(by_days))
        by_certainty = [model.need(90, q) for q in (0.5, 0.9, 0.95, 0.999)]
        self.assertEqual(by_certainty, sorted(by_certainty))


class UsableBulkTests(SimpleTestCase):

    def test_two_lots_of_the_shared_scenario(self) -> None:
        self.assertEqual(forecast.usable_bulk([D(360)], D(20)), D(340))

    def test_lots_too_small_to_fill(self) -> None:
        """Scenario: Lots too small to fill."""
        self.assertEqual(forecast.usable_bulk([D(6), D(6)], D(10)), D(0))

    def test_each_lot_counts_its_amount_less_the_largest_size(self) -> None:
        self.assertEqual(
            forecast.usable_bulk([D(25), D(10), D(9), D(40)], D(10)),
            D(15 + 0 + 0 + 30))

    def test_no_largest_size_counts_every_amount(self) -> None:
        self.assertEqual(forecast.usable_bulk([D(5), D(7)], D(0)), D(12))

    def test_no_lot_gives_nothing(self) -> None:
        self.assertEqual(forecast.usable_bulk([], D(10)), D(0))

    def test_the_result_is_a_decimal_and_keeps_its_places(self) -> None:
        found = forecast.usable_bulk([D("12.5"), D("3.25")], D("2.5"))
        self.assertIsInstance(found, Decimal)
        self.assertEqual(found, D("10") + D("0.75"))


class ArticleRunwayTests(SimpleTestCase):

    def runway(self, items, bulk, certainty: float = 0.95):
        return forecast.article_runway(items, D(bulk), certainty)

    def test_bulk_shared_by_two_sizes(self) -> None:
        """Scenario: Bulk shared by two sizes."""
        model = quarterly(9)
        found = self.runway([(model, 0, D(10)), (model, 0, D(20))], 340)
        self.assertAlmostEqual(found, 62.320, places=3)
        self.assertEqual(math.floor(found), 62)

    def test_each_size_given_the_whole_lot_would_claim_more(self) -> None:
        model = quarterly(9)
        self.assertEqual(
            math.floor(self.runway([(model, 0, D(10))], 360)), 277)
        self.assertEqual(
            math.floor(self.runway([(model, 0, D(20))], 360)), 124)

    def test_each_of_k_items_is_planned_at_the_union_bound(self) -> None:
        """k items at a certainty c each last as one item at
        1 - (1 - c) / k."""
        model = quarterly(9)
        for count in (1, 2, 3, 5):
            with self.subTest(count=count):
                together = self.runway([(model, 10, None)] * count, 0)
                alone = self.runway([(model, 10, None)], 0,
                                    1 - 0.05 / count)
                self.assertAlmostEqual(together, alone, places=6)

    def test_two_unconverting_items_are_planned_at_0975(self) -> None:
        model = quarterly(9)
        found = self.runway([(model, 10, None), (model, 10, None)], 0)
        self.assertAlmostEqual(found, closed_form(9, 9, 10, 0.975),
                               places=6)
        self.assertAlmostEqual(found, 55.112, places=3)

    def test_an_item_that_does_not_convert_is_its_runway_on_hand(
            self) -> None:
        model = quarterly(9)
        self.assertAlmostEqual(self.runway([(model, 10, None)], 0), 60.654,
                               places=3)
        self.assertAlmostEqual(
            self.runway([(model, 10, None)], 1000), 60.654, places=3)

    def test_the_certainty_is_the_one_given(self) -> None:
        model = quarterly(9)
        self.assertAlmostEqual(
            self.runway([(model, 10, None)], 0, certainty=0.5), 101.458,
            places=3)
        self.assertAlmostEqual(
            self.runway([(model, 10, D(1))], 0, certainty=0.5), 101.458,
            places=3)

    def test_containers_on_hand_count_first(self) -> None:
        model = quarterly(9)
        found = self.runway([(model, 5, D(10)), (model, 0, D(20))], 340)
        self.assertAlmostEqual(found, 77.084, places=3)

    def test_zero_stock_without_bulk_is_zero(self) -> None:
        model = quarterly(9)
        self.assertAlmostEqual(self.runway([(model, 0, D(10))], 0), 0,
                               places=6)

    def test_more_bulk_lasts_longer(self) -> None:
        model = quarterly(9)
        found = [self.runway([(model, 0, D(10))], bulk)
                 for bulk in (0, 10, 50, 100, 1000)]
        self.assertEqual(found, sorted(found))
        self.assertLess(found[0], found[-1])

    def test_bulk_that_converts_and_an_item_that_does_not(self) -> None:
        """The runway is the shorter of what the bulk gives and what the
        item that does not convert has on hand, both at 0.975."""
        model = quarterly(9)
        items = [(model, 0, D(10)), (model, 10, None)]
        self.assertAlmostEqual(self.runway(items, 340), 55.112, places=3)
        self.assertAlmostEqual(self.runway(items, 30), 10.3515, places=3)

    def test_items_without_demand_do_not_count(self) -> None:
        model = quarterly(9)
        self.assertIsNone(self.runway([], 100))
        self.assertIsNone(self.runway([(None, 5, D(10))], 100))
        self.assertIsNone(self.runway([(None, 5, None)], 0))
        found = self.runway([(None, 5, D(10)), (model, 10, None)], 0)
        self.assertAlmostEqual(found, 60.654, places=3)

    def test_orders_in_an_article(self) -> None:
        model = eight_orders()
        self.assertAlmostEqual(self.runway([(model, 9, None)], 0), 4.6805,
                               delta=0.011)
        self.assertAlmostEqual(
            self.runway([(model, 9, None), (model, 9, None)], 0),
            -math.log(0.975) / (8 / 730), delta=0.011)

    def test_orders_and_bulk(self) -> None:
        """Whole orders of 10 containers need whole containers of
        bulk."""
        model = eight_orders()
        small = self.runway([(model, 0, D(1))], 9)
        large = self.runway([(model, 0, D(1))], 10)
        self.assertLess(small, large)
        self.assertAlmostEqual(small, model.runway(0, 0.95), delta=0.011)
        self.assertAlmostEqual(large, model.runway(10, 0.95), delta=0.011)

    def test_the_bulk_unit_does_not_matter_only_the_sizes(self) -> None:
        model = quarterly(9)
        mg = self.runway([(model, 0, D(10)), (model, 0, D(20))], 340)
        scaled = self.runway([(model, 0, D("0.01")), (model, 0, D("0.02"))],
                             D("0.34"))
        self.assertAlmostEqual(mg, scaled, places=6)


class SharedBulkTests(PlanningCase):
    """The same figures from the inventory."""

    def two_sizes(self):
        small = self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.lot("NV-2", "mg", "360")
        return small, large

    def test_bulk_shared_by_two_sizes(self) -> None:
        """Scenario: Bulk shared by two sizes."""
        small, large = self.two_sizes()
        found = self.forecast("NV-2")
        self.assertEqual(found.usable_bulk, D(340))
        self.assertEqual(found.bulk_unit, Unit.MG)
        self.assertAlmostEqual(found.runway, 62.320, places=3)
        self.assertEqual(math.floor(found.runway), 62)
        self.assertEqual([e.item.pk for e in found.items],
                         [small.pk, large.pk])
        for entry in found.items:
            self.assertEqual(entry.runway_on_hand, 0)

    def test_even_demand_of_the_only_item(self) -> None:
        """Scenario: Even demand."""
        self.planned_item("NV-1", size="1", quantity=10)
        found = self.forecast("NV-1")
        self.assertEqual(math.floor(found.runway), 60)
        self.assertEqual(math.floor(found.items[0].runway_on_hand), 60)
        self.assertEqual(found.usable_bulk, D(0))
        self.parameters(certainty=0.5)
        found = self.forecast("NV-1")
        self.assertEqual(math.floor(found.runway), 101)
        self.assertEqual(math.floor(found.items[0].runway_on_hand), 101)

    def test_lots_too_small_to_fill(self) -> None:
        """Scenario: Lots too small to fill."""
        self.planned_item("NV-3", size="10", quantity=10)
        self.lot("NV-3", "mg", "6")
        self.lot("NV-3", "mg", "6")
        found = self.forecast("NV-3")
        self.assertEqual(found.usable_bulk, D(0))
        self.assertAlmostEqual(found.runway, found.items[0].runway_on_hand,
                               places=6)

    def test_a_lot_of_the_largest_size_counts_nothing(self) -> None:
        self.planned_item("NV-3", size="10", quantity=10)
        self.lot("NV-3", "mg", "10")
        self.assertEqual(self.forecast("NV-3").usable_bulk, D(0))

    def test_lots_in_other_units_and_other_articles(self) -> None:
        self.planned_item("NV-3", size="10", quantity=10)
        self.lot("NV-3", "g", "1")
        self.lot("NV-3", "mg", "600")
        self.lot("NV-3", "mg", "0")
        self.lot("NV-9", "mg", "5000")
        self.assertEqual(self.forecast("NV-3").usable_bulk, D(1580))

    def test_the_largest_size_is_that_of_the_items_with_demand(self) -> None:
        self.planned_item("NV-3", size="10", quantity=10)
        self.item("NV-3", "NV-3", "100", "mg", 0)
        self.lot("NV-3", "mg", "100")
        found = self.forecast("NV-3")
        self.assertEqual(found.usable_bulk, D(90))
        self.assertAlmostEqual(found.runway, 132.469, places=3)
        self.assertEqual([e.model is None for e in found.items],
                         [False, True])
        self.assertIsNone(found.items[1].runway_on_hand)

    def test_sizes_are_taken_in_the_bulk_unit(self) -> None:
        self.planned_item("NV-4", size="500", unit="mg", quantity=2)
        gram = self.item("NV-4", "NV-4", "1", "g", 2)
        for year, quarter in WINDOW:
            self.enter(gram, year, quarter, 3)
        self.lot("NV-4", "g", "2.5")
        found = self.forecast("NV-4")
        self.assertEqual(found.bulk_unit, Unit.MG)
        self.assertEqual(found.usable_bulk, D(1500))

    def test_the_bulk_unit_is_micromole_for_a_compound_with_a_mass(
            self) -> None:
        self.planned_item("CH-0012", size="10", unit="mg", quantity=10)
        self.lot("CH-0012", "mg", "100")
        found = self.forecast("CH-0012")
        self.assertEqual(found.bulk_unit, Unit.UMOL)
        self.assertAlmostEqual(float(found.usable_bulk),
                               90 * 1000 / 148.16, places=6)

    def test_the_bulk_unit_follows_the_first_item_without_a_mass(
            self) -> None:
        self.planned_item("NV-5", size="1", unit="umol", quantity=10)
        self.assertEqual(self.forecast("NV-5").bulk_unit, Unit.UMOL)
        self.planned_item("NV-6", size="1", unit="umol", quantity=10)
        self.planned_item("NV-6", size="5", unit="mg", quantity=10)
        self.assertEqual(self.forecast("NV-6").bulk_unit, Unit.MG)

    def test_a_dormant_size_does_not_choose_the_bulk_unit(self) -> None:
        """Scenario: A dormant size does not choose the bulk unit."""
        self.item("NV-9", size="1", unit="mg", quantity=0,
                  status="not_needed")
        self.planned_item("NV-9", size="1", unit="umol", quantity=10)
        self.lot("NV-9", "umol", "100")
        found = self.forecast("NV-9")
        self.assertEqual(found.bulk_unit, Unit.UMOL)
        self.assertEqual(found.usable_bulk, D(99))

    def test_the_molar_mass_is_the_substances(self) -> None:
        """A substance with a molar mass has a bulk of µmol, whatever
        the index says."""
        self.planned_item("NV-5", size="10", unit="mg", quantity=10)
        self.lot("NV-5", "mg", "100")
        self.assertEqual(self.forecast("NV-5").bulk_unit, Unit.MG)
        self.item("NV-5", mw="100", size="5", unit="mg")
        found = self.forecast("NV-5")
        self.assertEqual(found.bulk_unit, Unit.UMOL)

    def test_an_item_that_does_not_convert_limits_the_runway(self) -> None:
        mg = self.planned_item("NV-6", size="10", unit="mg", quantity=0)
        micro = self.planned_item("NV-6", size="1", unit="umol",
                                  quantity=10)
        self.lot("NV-6", "mg", "350")
        found = self.forecast("NV-6")
        self.assertEqual(found.usable_bulk, D(340))
        self.assertAlmostEqual(found.runway, 55.112, places=3)
        by_item = {e.item.pk: e for e in found.items}
        self.assertAlmostEqual(by_item[micro.pk].runway_on_hand, 60.654,
                               places=3)
        self.assertEqual(by_item[mg.pk].runway_on_hand, 0)

    def test_a_small_lot_binds_before_the_item_that_does_not_convert(
            self) -> None:
        self.planned_item("NV-6", size="10", unit="mg", quantity=0)
        self.planned_item("NV-6", size="1", unit="umol", quantity=10)
        self.lot("NV-6", "mg", "40")
        self.assertAlmostEqual(self.forecast("NV-6").runway, 10.3515,
                               places=3)

    def test_a_lot_that_does_not_convert_counts_nothing(self) -> None:
        self.planned_item("NV-7", size="10", unit="mg", quantity=10)
        self.lot("NV-7", "umol", "1000")
        found = self.forecast("NV-7")
        self.assertEqual(found.usable_bulk, D(0))
        self.assertAlmostEqual(found.runway, found.items[0].runway_on_hand,
                               places=6)

    def test_an_article_without_demand_has_no_forecast(self) -> None:
        self.item("NV-8", size="10", unit="mg", quantity=10)
        self.assertIsNone(self.forecast("NV-8"))
        self.assertIsNone(self.forecast("NV-404"))
