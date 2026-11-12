"""Tests of the task record: state, progress, steps, numbers and
history (task-tracker: Task record, Task numbers)."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import SimpleTestCase, TestCase

from tasks.models import Task

from . import (berlin, done_days, frozen, make_task, make_user, past,
               substance_for, task_steps, task_url)
from .collection_support import (accepts, changed_collection,
                                 import_collection, latest_import,
                                 make_import, refuses, without_ids)
from .task_support import TaskCase


class StateTests(SimpleTestCase):

    def test_state_follows_the_dates(self) -> None:
        self.assertEqual(Task().state, "planned")
        self.assertEqual(Task(started=past(1)).state,
                         "running")
        self.assertEqual(
            Task(started=past(1), ended=past(2)).state,
            "ended")

    def test_cancelled_outranks_the_dates(self) -> None:
        """Scenario: Cancelled outranks ended."""
        task = Task(started=past(1), ended=past(2),
                    cancelled=True)
        self.assertEqual(task.state, "cancelled")
        self.assertFalse(task.needs_follow_up)
        self.assertEqual(Task(cancelled=True).state,
                         "cancelled")
        self.assertEqual(
            Task(started=past(1), cancelled=True).state,
            "cancelled")

    def test_follow_up(self) -> None:
        """Scenario: Follow-up."""
        ended = {"started": past(1), "ended": past(2)}
        task = Task(report=True, qc_list=False, **ended)
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
                task = Task(report=report, qc_list=qc_list,
                            **ended)
                self.assertIs(task.needs_follow_up, expected)

    def test_only_ended_tasks_need_follow_up(self) -> None:
        self.assertIs(Task().needs_follow_up, False)
        self.assertIs(
            Task(started=past(1)).needs_follow_up, False)


class DefaultTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")
        cls.substance = substance_for("Aspirin")

    def test_a_new_task_starts_planned(self) -> None:
        task = make_task(self.kl, self.substance)
        task.refresh_from_db()
        self.assertEqual(task.number, "T-001")
        self.assertEqual(task.substance, self.substance)
        self.assertEqual(task.priority, "medium")
        self.assertIsNone(task.assignee)
        self.assertIsNone(task.started)
        self.assertIsNone(task.ended)
        self.assertIsNone(task.sequence)
        self.assertEqual(list(task.steps.all()), [])
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
        task = Task(created_by=self.kl,
                    **{"substance": self.substance, **fields})
        try:
            task.full_clean(exclude=["number"])
        except ValidationError as exc:
            return exc.message_dict
        return {}

    def test_a_valid_task_has_no_errors(self) -> None:
        self.assertEqual(self.errors(), {})

    def test_the_substance_is_required(self) -> None:
        self.assertNotIn("substance", self.errors())
        self.assertIn("substance", self.errors(substance=None))

    def test_batch_is_at_most_30_characters(self) -> None:
        self.assertNotIn("batch", self.errors(batch="b" * 30))
        self.assertIn("batch", self.errors(batch="b" * 31))
        self.assertNotIn("batch", self.errors(batch=""))


class NumberTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_numbers_count_up(self) -> None:
        numbers = [make_task(self.kl).number for _ in range(3)]
        self.assertEqual(numbers, ["T-001", "T-002", "T-003"])

    def test_saving_again_keeps_the_number(self) -> None:
        task = make_task(self.kl)
        task.note = "Changed"
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


class ProgressTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_running_task_and_its_progress(self) -> None:
        """Scenario: State and progress."""
        task = make_task(self.kl, started=date(2026, 11, 2), steps=5,
                         done=2)
        self.assertEqual(task.state, "running")
        self.assertEqual(task.progress, 40)

    def test_progress_is_rounded_down(self) -> None:
        """Requirement: Task record (a whole percentage rounded
        down)."""
        for done, total, expected in ((0, 5, 0), (1, 3, 33), (2, 3, 66),
                                      (3, 3, 100), (1, 1, 100),
                                      (199, 200, 99)):
            with self.subTest(done=done, total=total):
                task = make_task(self.kl, steps=total, done=done)
                self.assertEqual(task.progress, expected)

    def test_progress_needs_steps(self) -> None:
        """Requirement: Task record (no value without steps)."""
        self.assertIsNone(make_task(self.kl).progress)

    def test_progress_counts_the_steps_done_wherever_they_are(self) -> None:
        """Requirement: Task record (the steps done over the steps)."""
        task = make_task(self.kl, steps=4)
        task.steps.filter(position=4).update(done_on=past(2))
        self.assertEqual(task.progress, 25)
        task.steps.filter(position=1).update(done_on=past(2))
        self.assertEqual(task.progress, 50)

    def test_progress_follows_the_steps(self) -> None:
        task = make_task(self.kl, steps=2, done=1)
        self.assertEqual(task.progress, 50)
        task.steps.filter(done_on=None).delete()
        self.assertEqual(task.progress, 100)

    def test_the_task_has_no_step_counters(self) -> None:
        """Requirement: Task record (the counters are gone)."""
        names = {field.name for field in Task._meta.get_fields()}
        for gone in ("sequence_steps", "steps_total", "steps_done"):
            with self.subTest(field=gone):
                self.assertNotIn(gone, names)


class StepRecordTests(TaskCase):
    """The step rows (task-tracker: Task record)."""

    def entry(self, procedure: str, position: int = 1):
        from collection.models import ScopeEntry
        return ScopeEntry.objects.get(procedure__key=procedure,
                                      position=position)

    def test_a_step_holds_its_fields(self) -> None:
        """Requirement: Task record (a step's position, entry, planned
        import and day done)."""
        from tasks.models import TaskStep
        task = make_task(self.kl)
        made = TaskStep.objects.create(
            task=task, position=1, entry=self.entry("OSDB-0009", 2),
            planned_import=self.first, done_on=past(3))
        found = TaskStep.objects.get(pk=made.pk)
        self.assertEqual((found.task, found.position, found.entry,
                          found.planned_import, found.done_on),
                         (task, 1, self.entry("OSDB-0009", 2), self.first,
                          past(3)))

    def test_entry_import_and_day_may_be_none(self) -> None:
        """Requirement: Task record (a step not written down as an
        entry; no import; not done)."""
        from tasks.models import TaskStep
        task = make_task(self.kl)
        made = TaskStep(task=task, position=1)
        made.full_clean()
        made.save()
        found = TaskStep.objects.get(pk=made.pk)
        self.assertEqual((found.entry, found.planned_import,
                          found.done_on), (None, None, None))

    def test_the_steps_come_in_order_of_their_position(self) -> None:
        """Requirement: Task record (its steps, in order)."""
        from tasks.models import TaskStep
        task = make_task(self.kl)
        for position in (3, 1, 2):
            TaskStep.objects.create(task=task, position=position)
        self.assertEqual([s.position for s in task.steps.all()],
                         [1, 2, 3])

    def test_a_position_is_taken_once_per_task(self) -> None:
        """Requirement: Task record (`position`, from 1, unique per
        task)."""
        from tasks.models import TaskStep
        task = make_task(self.kl)
        other = make_task(self.kl)
        TaskStep.objects.create(task=task, position=1)
        TaskStep.objects.create(task=other, position=1)
        refuses(self, lambda: TaskStep(task=task, position=1))

    def test_a_position_starts_at_one(self) -> None:
        """Requirement: Task record (`position`, from 1)."""
        from tasks.models import TaskStep
        task = make_task(self.kl)
        refuses(self, lambda: TaskStep(task=task, position=0))
        accepts(self, lambda: TaskStep(task=task, position=1))

    def test_deleting_a_task_deletes_its_steps(self) -> None:
        from tasks.models import TaskStep
        task = make_task(self.kl, steps=3)
        make_task(self.kl, steps=1)
        task.delete()
        self.assertEqual(TaskStep.objects.count(), 1)

    def test_an_entry_a_step_names_cannot_be_deleted(self) -> None:
        """Requirement: Imported rows (a scope entry that a row names
        cannot be deleted)."""
        from tasks.models import TaskStep
        entry = self.entry("OSDB-0006")
        task = make_task(self.kl)
        TaskStep.objects.create(task=task, position=1, entry=entry)
        with self.assertRaises(ProtectedError):
            entry.delete()

    def test_an_import_a_step_names_cannot_be_deleted(self) -> None:
        """Design: Steps are rows (the import is protected)."""
        from collection.models import Import
        from tasks.models import TaskStep
        planned = make_import()
        task = make_task(self.kl)
        TaskStep.objects.create(task=task, position=1,
                                planned_import=planned)
        with self.assertRaises(ProtectedError):
            planned.delete()
        self.assertTrue(Import.objects.filter(pk=planned.pk).exists())

    def test_a_task_names_a_sequence_row(self) -> None:
        """Requirement: Task record (`sequence`, a synthesis sequence of
        the collection)."""
        from collection.models import Sequence
        sequence = Sequence.objects.get(key="SEQ-0001")
        task = make_task(self.kl, sequence=sequence)
        task.refresh_from_db()
        self.assertEqual(task.sequence, sequence)
        self.assertIsNone(make_task(self.kl).sequence)

    def test_steps_keep_a_history(self) -> None:
        """Requirement: Task record (tasks and their steps keep a change
        history)."""
        from tasks.models import TaskStep
        task = make_task(self.kl, steps=1)
        (step,) = task.steps.all()
        self.assertEqual([r.history_type for r in step.history.all()],
                         ["+"])
        step._history_user = self.kl
        step.done_on = past(4)
        step.save()
        newest = step.history.first()
        self.assertEqual((newest.history_type, newest.done_on,
                          newest.history_user),
                         ("~", past(4), self.kl))
        self.assertEqual(step.history.count(), 2)
        pk = step.pk
        step.delete()
        self.assertEqual(
            TaskStep.history.filter(id=pk).first().history_type, "-")


class StepsFromASequenceTests(TaskCase):
    """The steps a save gives the task (task-tracker: Task record)."""

    def entries(self, task) -> list[tuple[str, int]]:
        return [entry for entry, _import, _done in task_steps(task)]

    def test_steps_from_a_sequence(self) -> None:
        """Scenario: Steps from a sequence."""
        done = self.create(sequence="SEQ-0002", steps_total="7")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.sequence.key, "SEQ-0002")
        self.assertEqual(task.steps.count(), 2)
        self.assertEqual(task_steps(task), [
            (("OSDB-0004", 1), self.first, None),
            (("OSDB-0009", 1), self.first, None)])

    def test_the_steps_take_the_latest_accepted_import(self) -> None:
        """Requirement: Task record (the latest accepted import)."""
        later = import_collection()
        make_import(outcome="refused")
        self.assertNotEqual(later, self.first)
        self.create(sequence="SEQ-0001")
        task = self.only_task()
        self.assertEqual({i for _e, i, _d in task_steps(task)}, {later})
        self.assertEqual(latest_import(), later)

    def test_the_steps_follow_the_sequence_in_its_order(self) -> None:
        """Requirement: Task record (one per step of the sequence, in
        its order)."""
        self.create(sequence="SEQ-0001")
        self.assertEqual(self.entries(self.only_task()),
                         [("OSDB-0001", 1), ("OSDB-0002", 1)])

    def test_a_save_that_keeps_the_sequence_keeps_the_steps(self) -> None:
        """Requirement: Task record (a task keeps its steps after the
        sequence changes in the collection)."""
        self.create(sequence="SEQ-0002")
        task = self.only_task()
        before = [step.pk for step in task.steps.order_by("position")]
        import_collection(changed_collection("OSDB-0009"))
        self.change(task, note="Only a note")
        task = self.only_task()
        self.assertEqual(
            [step.pk for step in task.steps.order_by("position")], before)
        self.assertEqual(task_steps(task), [
            (("OSDB-0004", 1), self.first, None),
            (("OSDB-0009", 1), self.first, None)])

    def test_sequence_gone_from_the_collection(self) -> None:
        """Scenario: Sequence gone from the collection."""
        self.create(sequence="SEQ-0001")
        task = self.only_task()
        import_collection(without_ids("SEQ-0001"))
        from collection.models import Sequence
        self.assertTrue(Sequence.objects.get(key="SEQ-0001").withdrawn)
        done = self.change(task, report="on")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertTrue(task.report)
        self.assertEqual(task.sequence.key, "SEQ-0001")
        self.assertEqual(task_steps(task), [
            (("OSDB-0001", 1), self.first, None),
            (("OSDB-0002", 1), self.first, None)])

    def test_a_withdrawn_sequence_cannot_be_set(self) -> None:
        """Requirement: Task record (a sequence that is not withdrawn
        when a save sets or changes it)."""
        import_collection(without_ids("SEQ-0001"))
        self.create(sequence="SEQ-0001")
        from tasks.models import Task
        self.assertEqual(Task.objects.count(), 0)

    def test_without_a_sequence_the_steps_carry_no_entry(self) -> None:
        """Requirement: Task record (without a sequence the steps carry
        no entry and no import)."""
        self.create(steps_total="3")
        task = self.only_task()
        self.assertIsNone(task.sequence)
        self.assertEqual(task_steps(task), [(None, None, None)] * 3)
        self.assertEqual([s.position for s in task.steps.all()],
                         [1, 2, 3])

    def test_clearing_the_sequence_gives_plain_steps(self) -> None:
        """Requirement: Task record (when it clears the sequence the
        steps become plain steps, as many as the form's steps
        total)."""
        self.create(sequence="SEQ-0001")
        task = self.only_task()
        self.change(task, sequence="", steps_total="3")
        task = self.only_task()
        self.assertIsNone(task.sequence)
        self.assertEqual(task_steps(task), [(None, None, None)] * 3)

    def test_changing_the_sequence_replaces_the_steps(self) -> None:
        """Requirement: Task record (when it sets or changes the
        sequence, the steps become one per step of the sequence)."""
        self.create(sequence="SEQ-0001")
        task = self.only_task()
        later = import_collection()
        self.change(task, sequence="SEQ-0002")
        task = self.only_task()
        self.assertEqual(task.sequence.key, "SEQ-0002")
        self.assertEqual(task_steps(task), [
            (("OSDB-0004", 1), later, None),
            (("OSDB-0009", 1), later, None)])
        self.assertEqual([s.position for s in task.steps.all()], [1, 2])

    def test_setting_a_sequence_on_a_task_with_plain_steps(self) -> None:
        """Requirement: Task record (a sequence set replaces the
        steps)."""
        self.create(steps_total="5")
        task = self.only_task()
        self.change(task, sequence="SEQ-0001")
        self.assertEqual(self.entries(self.only_task()),
                         [("OSDB-0001", 1), ("OSDB-0002", 1)])

    def test_no_change_of_sequence_with_a_step_done(self) -> None:
        """Requirement: Task record (a save may set, change or clear the
        sequence only while none of the steps is done)."""
        self.create(sequence="SEQ-0002", started="2025-03-01")
        task = self.only_task()
        self.change(task, steps_done="1")
        task = self.only_task()
        before = task_steps(task)
        self.assertIsNotNone(before[0][2])
        for sequence in ("SEQ-0001", ""):
            with self.subTest(sequence=sequence):
                self.change(task, sequence=sequence)
                task = self.only_task()
                self.assertEqual(task.sequence.key, "SEQ-0002")
                self.assertEqual(task_steps(task), before)

    def test_a_task_with_steps_done_may_keep_its_sequence(self) -> None:
        """Requirement: Task record (only a set, change or clear is
        refused)."""
        self.create(sequence="SEQ-0002", started="2025-03-01")
        task = self.only_task()
        self.change(task, steps_done="1")
        done = self.change(self.only_task(), note="Still the same")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.only_task().note, "Still the same")

    def test_the_steps_are_recorded_with_the_save_day(self) -> None:
        """Requirement: Task record (`done_on`)."""
        with frozen(berlin(2026, 11, 5)):
            self.create(steps_total="2", started="2026-11-04",
                        steps_done="1")
        self.assertEqual(done_days(self.only_task()),
                         [date(2026, 11, 5), None])

    def test_creating_the_steps_records_their_history(self) -> None:
        """Requirement: Task record (tasks and their steps keep a
        change history)."""
        from tasks.models import TaskStep
        self.create(steps_total="2")
        task = self.only_task()
        self.assertEqual(
            TaskStep.history.filter(task_id=task.pk).count(), 2)
        self.assertEqual(self.client.get(task_url(task)).status_code, 200)
