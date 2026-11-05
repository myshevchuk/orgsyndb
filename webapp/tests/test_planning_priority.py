"""Tests of the slack, the latest start and the priority
(production-planning: Slack and priority, Computed priority on tasks)."""

import math
from datetime import date, timedelta

from django.test import SimpleTestCase

from planning import forecast, plan

from . import make_task
from .inventory_support import TODAY
from .planning_support import WINDOW, PlanningCase


class PriorityBandTests(SimpleTestCase):

    def test_the_bands_of_the_defaults(self) -> None:
        cases = [(-100, "high"), (-0.5, "high"), (0, "high"),
                 (11.65, "high"), (13.99, "high"), (14, "medium"),
                 (14.01, "medium"), (50.8, "medium"), (55.99, "medium"),
                 (56, "low"), (133.8, "low"), (10_000, "low")]
        for slack, expected in cases:
            with self.subTest(slack=slack):
                self.assertEqual(forecast.priority(slack, 14, 56), expected)

    def test_the_bands_are_parameters(self) -> None:
        self.assertEqual(forecast.priority(11.65, 5, 20), "medium")
        self.assertEqual(forecast.priority(4.99, 5, 20), "high")
        self.assertEqual(forecast.priority(5, 5, 20), "medium")
        self.assertEqual(forecast.priority(19.99, 5, 20), "medium")
        self.assertEqual(forecast.priority(20, 5, 20), "low")

    def test_a_high_band_of_zero_is_high_only_when_late(self) -> None:
        self.assertEqual(forecast.priority(-0.01, 0, 10), "high")
        self.assertEqual(forecast.priority(0, 0, 10), "medium")
        self.assertEqual(forecast.priority(10, 0, 10), "low")


class ArticleSlackTests(PlanningCase):

    def hold(self, quantity: int, article: str | None = None):
        self.planned_item(article or f"NV-{quantity}", quantity=quantity)
        return self.forecast(article or f"NV-{quantity}")

    def test_priority_bands(self) -> None:
        """Scenario: Priority bands."""
        expected = [(10, 11, "high", date(2026, 11, 15)),
                    (15, 50, "medium", date(2026, 12, 24)),
                    (25, 133, "low", date(2027, 3, 17))]
        for quantity, slack, priority, start in expected:
            with self.subTest(quantity=quantity):
                found = self.hold(quantity)
                self.assertEqual(math.floor(found.slack), slack)
                self.assertEqual(found.priority, priority)
                self.assertEqual(found.latest_start, start)
                self.assertEqual(found.synthesis_days, 21)

    def test_the_slack_is_unrounded(self) -> None:
        self.assertAlmostEqual(self.hold(10).slack, 60.6544 - 49, places=3)
        self.assertAlmostEqual(self.hold(15).slack, 99.8374 - 49, places=3)
        self.assertAlmostEqual(self.hold(25).slack, 182.8075 - 49, places=3)

    def test_the_latest_start_rounds_down_below_zero_too(self) -> None:
        found = self.hold(7)
        self.assertAlmostEqual(found.slack, 38.5084 - 49, places=3)
        self.assertEqual(found.latest_start, TODAY - timedelta(days=11))
        self.assertEqual(found.priority, "high")

    def test_two_sizes_one_priority(self) -> None:
        """Scenario: Two sizes, one priority."""
        self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.lot("NV-2", "mg", "360")
        found = self.forecast("NV-2")
        self.assertEqual(math.floor(found.slack), 13)
        self.assertEqual(found.priority, "high")
        self.assertEqual(found.latest_start, TODAY + timedelta(days=13))

    def test_the_slack_is_the_runway_less_the_buffer_less_the_time(
            self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.parameters(buffer_days=0)
        self.assertAlmostEqual(self.forecast("NV-1").slack, 60.654 - 21,
                               places=3)

    def test_the_default_synthesis_time_enters_the_slack(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.parameters(default_synthesis_days=40)
        self.assertAlmostEqual(self.forecast("NV-1").slack, 60.654 - 68,
                               places=3)

    def test_past_syntheses_enter_the_slack(self) -> None:
        self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        self.assertAlmostEqual(self.forecast("NV-1").slack, 60.654 - 68,
                               places=3)

    def test_the_certainty_enters_the_runway(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.parameters(certainty=0.5)
        self.assertAlmostEqual(self.forecast("NV-1").slack, 101.458 - 49,
                               places=3)

    def test_the_bands_are_parameters(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.parameters(high_days=5, medium_days=20)
        self.assertEqual(self.forecast("NV-1").priority, "medium")

    def test_a_running_synthesis_does_not_change_the_article(self) -> None:
        self.planned_item("NV-1", quantity=10)
        before = self.forecast("NV-1")
        self.running("NV-1", 14)
        make_task(self.kl, product="NV-1")
        after = self.forecast("NV-1")
        self.assertEqual(after.slack, before.slack)
        self.assertEqual(after.priority, "high")
        self.assertEqual(after.latest_start, before.latest_start)


class TaskPriorityTests(PlanningCase):

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def priority(self, task):
        return plan.task_priority(task, TODAY)

    def test_computed_priority(self) -> None:
        """Scenario: Computed priority."""
        task = make_task(self.kl, product="NV-1", priority="low")
        shown, computed, slack = self.priority(task)
        self.assertEqual(shown, "high")
        self.assertTrue(computed)
        self.assertEqual(math.floor(slack), 11)

    def test_ended_task_keeps_its_entered_priority(self) -> None:
        """Scenario: Ended task keeps its entered priority."""
        task = make_task(self.kl, product="NV-1", priority="low",
                         started=date(2026, 9, 1), ended=date(2026, 9, 20))
        self.assertEqual(self.priority(task), ("low", False, None))

    def test_a_cancelled_task_keeps_its_entered_priority(self) -> None:
        for fields in ({}, {"started": date(2026, 9, 1)},
                       {"started": date(2026, 9, 1),
                        "ended": date(2026, 9, 5)}):
            with self.subTest(**fields):
                task = make_task(self.kl, product="NV-1", priority="medium",
                                 cancelled=True, **fields)
                self.assertEqual(self.priority(task),
                                 ("medium", False, None))

    def test_a_task_of_an_unknown_product_keeps_its_priority(self) -> None:
        task = make_task(self.kl, product="Aspirin", priority="low")
        self.assertEqual(self.priority(task), ("low", False, None))

    def test_a_task_of_an_article_without_demand_keeps_its_priority(
            self) -> None:
        self.item("NV-0", size="1", unit="mg", quantity=10)
        task = make_task(self.kl, product="NV-0", priority="high")
        self.assertEqual(self.priority(task), ("high", False, None))

    def test_a_running_synthesis(self) -> None:
        """Scenario: A running synthesis."""
        task = self.running("NV-1", 14, priority="low")
        shown, computed, slack = self.priority(task)
        self.assertEqual(math.floor(slack), 25)
        self.assertEqual(shown, "medium")
        self.assertTrue(computed)
        self.assertEqual(self.forecast("NV-1").priority, "high")

    def test_a_task_is_late_below_zero(self) -> None:
        self.planned_item("NV-5", quantity=5)
        task = make_task(self.kl, product="NV-5")
        shown, computed, slack = self.priority(task)
        self.assertLess(slack, 0)
        self.assertAlmostEqual(slack, 24.694 - 49, places=3)
        self.assertEqual(shown, "high")

    def test_a_longer_synthesis_time_makes_a_task_late(self) -> None:
        self.planned_item("NV-25", quantity=25)
        task = self.running("NV-25", 0)
        self.assertGreater(self.priority(task)[2], 100)
        self.parameters(default_synthesis_days=200)
        self.assertLess(self.priority(task)[2], 0)

    def test_the_slack_is_the_smallest_over_the_matching_articles(
            self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        self.planned_item("cinnamic-acid", size="10", unit="umol",
                          quantity=20)
        task = make_task(self.kl, product="CH-0012", priority="low")
        shown, computed, slack = self.priority(task)
        self.assertAlmostEqual(slack, 60.654 - 49, places=3)
        self.assertEqual((shown, computed), ("high", True))

    def test_articles_without_a_forecast_do_not_count(self) -> None:
        self.item("ch-0012", size="10", unit="umol", quantity=1000)
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        task = make_task(self.kl, product="CH-0012")
        self.assertAlmostEqual(self.priority(task)[2], 60.654 - 49,
                               places=3)

    def test_the_text_of_a_task_matches_regardless_of_case(self) -> None:
        task = make_task(self.kl, product="nv-1", priority="low")
        self.assertEqual(self.priority(task)[0], "high")

    def test_the_bands_are_parameters(self) -> None:
        self.parameters(high_days=5, medium_days=20)
        task = make_task(self.kl, product="NV-1", priority="low")
        self.assertEqual(self.priority(task)[0], "medium")
