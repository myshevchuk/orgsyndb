"""Tests of the task record: state, progress, numbers and history
(task-tracker: Task record, Task numbers)."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from tasks.models import Task

from . import make_task, make_user, past


class StateTests(SimpleTestCase):

    def test_running_task_and_its_progress(self) -> None:
        """Scenario: State and progress."""
        task = Task(product="X", started=date(2026, 11, 2),
                    steps_total=5, steps_done=2)
        self.assertEqual(task.state, "running")
        self.assertEqual(task.progress, 40)

    def test_state_follows_the_dates(self) -> None:
        self.assertEqual(Task(product="X").state, "planned")
        self.assertEqual(Task(product="X", started=past(1)).state,
                         "running")
        self.assertEqual(
            Task(product="X", started=past(1), ended=past(2)).state,
            "ended")

    def test_cancelled_outranks_the_dates(self) -> None:
        """Scenario: Cancelled outranks ended."""
        task = Task(product="X", started=past(1), ended=past(2),
                    cancelled=True)
        self.assertEqual(task.state, "cancelled")
        self.assertFalse(task.needs_follow_up)
        self.assertEqual(Task(product="X", cancelled=True).state,
                         "cancelled")
        self.assertEqual(
            Task(product="X", started=past(1), cancelled=True).state,
            "cancelled")

    def test_follow_up(self) -> None:
        """Scenario: Follow-up."""
        ended = {"started": past(1), "ended": past(2)}
        task = Task(product="X", report=True, qc_list=False, **ended)
        self.assertEqual(task.state, "ended")
        self.assertTrue(task.needs_follow_up)
        task.qc_list = True
        self.assertFalse(task.needs_follow_up)

    def test_follow_up_for_either_flag_or_both_off(self) -> None:
        ended = {"started": past(1), "ended": past(2)}
        for report, qc_list, expected in ((False, False, True),
                                          (True, False, True),
                                          (False, True, True),
                                          (True, True, False)):
            with self.subTest(report=report, qc_list=qc_list):
                task = Task(product="X", report=report, qc_list=qc_list,
                            **ended)
                self.assertIs(task.needs_follow_up, expected)

    def test_only_ended_tasks_need_follow_up(self) -> None:
        self.assertIs(Task(product="X").needs_follow_up, False)
        self.assertIs(
            Task(product="X", started=past(1)).needs_follow_up, False)

    def test_progress_is_rounded_down(self) -> None:
        for done, total, expected in ((0, 5, 0), (1, 3, 33), (2, 3, 66),
                                      (3, 3, 100), (1, 1, 100),
                                      (199, 200, 99)):
            with self.subTest(done=done, total=total):
                task = Task(product="X", steps_total=total,
                            steps_done=done)
                self.assertEqual(task.progress, expected)

    def test_progress_needs_a_total(self) -> None:
        self.assertIsNone(Task(product="X").progress)
        self.assertIsNone(Task(product="X", steps_done=0).progress)


class DefaultTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_a_new_task_starts_planned(self) -> None:
        task = Task.objects.create(product="X", created_by=self.kl)
        task.refresh_from_db()
        self.assertEqual(task.number, "T-001")
        self.assertEqual(task.priority, "medium")
        self.assertIsNone(task.assignee)
        self.assertIsNone(task.started)
        self.assertIsNone(task.ended)
        self.assertFalse(task.sequence)
        self.assertEqual(list(task.sequence_steps), [])
        self.assertIsNone(task.steps_total)
        self.assertEqual(task.steps_done, 0)
        self.assertFalse(task.batch)
        self.assertFalse(task.report)
        self.assertFalse(task.qc_list)
        self.assertFalse(task.cancelled)
        self.assertFalse(task.note)
        self.assertEqual(task.created_by, self.kl)
        self.assertIsNotNone(task.created_at)
        self.assertEqual(task.state, "planned")
        self.assertFalse(task.needs_follow_up)
        self.assertIsNone(task.progress)

    def test_priority_values(self) -> None:
        for priority in ("high", "medium", "low"):
            with self.subTest(priority=priority):
                self.assertNotIn("priority", self.errors(priority=priority))
        self.assertIn("priority", self.errors(priority="urgent"))

    def errors(self, **fields) -> dict:
        task = Task(created_by=self.kl, **{"product": "X", **fields})
        try:
            task.full_clean(exclude=["number"])
        except ValidationError as exc:
            return exc.message_dict
        return {}

    def test_a_valid_task_has_no_errors(self) -> None:
        self.assertEqual(self.errors(), {})

    def test_product_is_required_and_at_most_100_characters(self) -> None:
        self.assertNotIn("product", self.errors(product="x" * 100))
        self.assertIn("product", self.errors(product="x" * 101))
        self.assertIn("product", self.errors(product=""))

    def test_batch_is_at_most_30_characters(self) -> None:
        self.assertNotIn("batch", self.errors(batch="b" * 30))
        self.assertIn("batch", self.errors(batch="b" * 31))
        self.assertNotIn("batch", self.errors(batch=""))

    def test_steps_total_is_at_least_one(self) -> None:
        self.assertNotIn("steps_total", self.errors(steps_total=1))
        self.assertNotIn("steps_total", self.errors(steps_total=None))
        self.assertIn("steps_total", self.errors(steps_total=0))
        self.assertIn("steps_total", self.errors(steps_total=-3))

    def test_steps_done_is_not_negative(self) -> None:
        self.assertIn("steps_done", self.errors(steps_total=3,
                                                steps_done=-1))


class NumberTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_numbers_count_up(self) -> None:
        numbers = [make_task(self.kl).number for _ in range(3)]
        self.assertEqual(numbers, ["T-001", "T-002", "T-003"])

    def test_saving_again_keeps_the_number(self) -> None:
        task = make_task(self.kl)
        task.product = "Changed"
        task.save()
        task.refresh_from_db()
        self.assertEqual(task.number, "T-001")
        self.assertEqual(make_task(self.kl).number, "T-002")

    def test_numbers_after_a_deletion(self) -> None:
        """Scenario: Numbers after a deletion."""
        tasks = [make_task(self.kl) for _ in range(3)]
        tasks[2].delete()
        self.assertEqual(make_task(self.kl).number, "T-004")

    def test_a_deleted_first_task_does_not_free_its_number(self) -> None:
        first = make_task(self.kl)
        first.delete()
        self.assertEqual(make_task(self.kl).number, "T-002")
        self.assertFalse(Task.objects.filter(number="T-001").exists())

    def test_numbers_have_at_least_three_digits(self) -> None:
        numbers = [make_task(self.kl).number for _ in range(1000)]
        self.assertEqual(numbers[98:101], ["T-099", "T-100", "T-101"])
        self.assertEqual(numbers[998:], ["T-999", "T-1000"])
        self.assertEqual(len(set(numbers)), 1000)


class HistoryTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_creation_and_changes_are_kept(self) -> None:
        task = make_task(self.kl, priority="medium")
        self.assertEqual(task.history.count(), 1)
        self.assertEqual(task.history.get().history_type, "+")
        task._history_user = self.kl
        task.priority = "high"
        task.save()
        self.assertEqual(task.history.count(), 2)
        newest = task.history.first()
        self.assertEqual(newest.history_type, "~")
        self.assertEqual(newest.history_user, self.kl)
        self.assertEqual(newest.priority, "high")
        self.assertEqual(task.history.last().priority, "medium")

    def test_history_names_the_task(self) -> None:
        task = make_task(self.kl)
        self.assertEqual(task.history.get().number, task.number)


class SequenceTotalTests(SimpleTestCase):

    def test_a_sequence_needs_its_total(self) -> None:
        """A task with copied steps may not lose its steps total."""
        task = Task(product="Aspirin", sequence="SEQ-0001",
                    sequence_steps=["OSDB-0001", "OSDB-0002"])
        with self.assertRaises(ValidationError) as caught:
            task.clean()
        self.assertIn("steps_total", caught.exception.message_dict)
