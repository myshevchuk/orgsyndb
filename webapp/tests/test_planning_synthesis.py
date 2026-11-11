"""Tests of the synthesis time (production-planning: Synthesis time)."""

from datetime import date, timedelta

from django.test import SimpleTestCase

from planning import forecast

from . import make_task, substance_for
from .inventory_support import TODAY
from .planning_support import PlanningCase


class SynthesisTimeTests(SimpleTestCase):
    """``synthesis_time`` takes the durations oldest first."""

    def test_longest_of_the_last_three(self) -> None:
        """Scenario: Longest of the last three."""
        self.assertEqual(forecast.synthesis_time([90, 20, 30, 40], 21),
                         (40, 3))

    def test_the_default_until_three_exist(self) -> None:
        """Scenario: The default until three exist."""
        self.assertEqual(forecast.synthesis_time([10], 21), (21, None))
        self.assertEqual(forecast.synthesis_time([], 21), (21, None))
        self.assertEqual(forecast.synthesis_time([10, 12], 21),
                         (21, None))

    def test_a_longer_duration_than_the_default_counts_before_three(
            self) -> None:
        self.assertEqual(forecast.synthesis_time([30], 21), (30, 1))
        self.assertEqual(forecast.synthesis_time([30, 10], 21), (30, 2))
        self.assertEqual(forecast.synthesis_time([5, 40], 21), (40, 2))

    def test_the_default_does_not_count_once_three_exist(self) -> None:
        self.assertEqual(forecast.synthesis_time([5, 6, 7], 21), (7, 3))
        self.assertEqual(forecast.synthesis_time([1, 1, 1], 21), (1, 3))

    def test_only_the_last_three_count(self) -> None:
        self.assertEqual(forecast.synthesis_time([100, 5, 6, 7], 21),
                         (7, 3))
        self.assertEqual(forecast.synthesis_time([5, 100, 6, 7], 21),
                         (100, 3))
        self.assertEqual(forecast.synthesis_time([1, 2, 3, 4, 5, 6], 21),
                         (6, 3))

    def test_the_default_is_a_parameter(self) -> None:
        self.assertEqual(forecast.synthesis_time([10], 35), (35, None))
        self.assertEqual(forecast.synthesis_time([], 1), (1, None))
        self.assertEqual(forecast.synthesis_time([10], 7), (10, 1))

    def test_the_result_is_whole_days(self) -> None:
        found, basis = forecast.synthesis_time([20, 30, 40], 21)
        self.assertIsInstance(found, int)
        self.assertIsInstance(basis, int)


class ArticleSynthesisTests(PlanningCase):
    """The synthesis time of an article from its ended tasks."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def times(self, article: str = "NV-1") -> tuple[int, int | None]:
        found = self.forecast(article)
        return found.synthesis_days, found.basis_count

    def test_the_default_without_a_synthesis(self) -> None:
        self.assertEqual(self.times(), (21, None))

    def test_four_ended_tasks_in_the_order_of_their_end_dates(self) -> None:
        """Scenario: Longest of the last three."""
        for days, ago in ((90, 400), (20, 300), (30, 200), (40, 100)):
            self.synthesis("NV-1", days, TODAY - timedelta(days=ago))
        self.assertEqual(self.times(), (40, 3))

    def test_one_ended_task_leaves_the_default(self) -> None:
        """Scenario: The default until three exist."""
        self.synthesis("NV-1", 10, TODAY - timedelta(days=100))
        self.assertEqual(self.times(), (21, None))

    def test_the_order_is_the_end_date_not_the_start_date(self) -> None:
        """The task that started first but ended last is among the
        three, and the one that ended first is not."""
        self.synthesis("NV-1", 90, date(2026, 5, 1))
        self.synthesis("NV-1", 8, date(2026, 6, 1))
        self.synthesis("NV-1", 9, date(2026, 7, 1))
        self.synthesis("NV-1", 10, date(2026, 8, 1))
        self.assertEqual(self.times(), (10, 3))
        make_task(self.kl, substance="NV-1", started=date(2026, 1, 1),
                  ended=date(2026, 9, 1), report=True, qc_list=True)
        self.assertEqual(self.times(), (243, 3))

    def test_ties_in_the_end_date_go_by_the_start_date(self) -> None:
        end = date(2026, 9, 1)
        for days in (90, 20, 30, 40):
            self.synthesis("NV-1", days, end)
        self.assertEqual(self.times(), (40, 3))

    def test_a_duration_is_at_least_a_day(self) -> None:
        for _ in range(3):
            self.synthesis("NV-1", 0, date(2026, 9, 1))
        self.assertEqual(self.times(), (1, 3))

    def test_cancelled_tasks_are_left_out(self) -> None:
        for days in (10, 11, 12):
            self.synthesis("NV-1", days, date(2026, 9, 1))
        make_task(self.kl, substance="NV-1", started=date(2026, 1, 1),
                  ended=date(2026, 10, 1), cancelled=True)
        self.assertEqual(self.times(), (12, 3))

    def test_planned_and_running_tasks_are_left_out(self) -> None:
        for days in (10, 11, 12):
            self.synthesis("NV-1", days, date(2026, 9, 1))
        make_task(self.kl, substance="NV-1")
        self.running("NV-1", 300)
        self.assertEqual(self.times(), (12, 3))

    def test_other_articles_are_left_out(self) -> None:
        for days in (10, 11, 12):
            self.synthesis("NV-1", days, date(2026, 9, 1))
        self.synthesis("NV-2", 200, date(2026, 10, 1))
        self.assertEqual(self.times(), (12, 3))

    def test_tasks_match_by_substance(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        self.synthesis("cinnamic-acid", 30, date(2026, 8, 1))
        self.synthesis("CH-0012", 31, date(2026, 8, 2))
        self.synthesis(substance_for("CH-0012"), 32, date(2026, 8, 3))
        self.assertEqual(self.times("CH-0012"), (32, 3))

    def test_the_default_is_a_parameter(self) -> None:
        self.parameters(default_synthesis_days=35)
        self.assertEqual(self.times(), (35, None))
        self.synthesis("NV-1", 40, date(2026, 8, 1))
        self.assertEqual(self.times(), (40, 1))


class RemainingTimeTests(PlanningCase):
    """A planned task's remaining time is ``L``; a running task's is
    ``L`` less the days since its start, at least zero. It shows in the
    task's slack."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def slack(self, task) -> float:
        from planning import plan
        return plan.task_priority(task, TODAY)[2]

    def test_a_planned_task_needs_the_whole_time(self) -> None:
        planned = make_task(self.kl, substance="NV-1")
        self.assertAlmostEqual(self.slack(planned), 60.654 - 28 - 21,
                               places=3)

    def test_a_running_task_needs_what_remains(self) -> None:
        for ago, remaining in ((0, 21), (1, 20), (14, 7), (20, 1),
                               (21, 0)):
            with self.subTest(ago=ago):
                task = self.running("NV-1", ago)
                self.assertAlmostEqual(
                    self.slack(task), 60.654 - 28 - remaining, places=3)

    def test_the_remaining_time_is_never_negative(self) -> None:
        task = self.running("NV-1", 60)
        self.assertAlmostEqual(self.slack(task), 60.654 - 28, places=3)

    def test_the_remaining_time_follows_the_synthesis_time(self) -> None:
        for days, ago in ((30, 400), (35, 300), (40, 200)):
            self.synthesis("NV-1", days, TODAY - timedelta(days=ago))
        planned = make_task(self.kl, substance="NV-1")
        running = self.running("NV-1", 10)
        self.assertAlmostEqual(self.slack(planned), 60.654 - 28 - 40,
                               places=3)
        self.assertAlmostEqual(self.slack(running), 60.654 - 28 - 30,
                               places=3)
