"""Tests of the step a task starts at and the substance it makes
(task-tracker: Task record, Task forms, Task page, Tasks in the
admin)."""

from datetime import date
from typing import Any

from django.db import models

from tasks.models import Task

from . import (NOT_IN_COLLECTION, context_form, field_value, make_lot,
               make_task, make_user, make_withdrawal, page, task_form_data,
               task_steps, task_url)
from .collection_support import (accept, import_collection, longer_collection,
                                 retargeted_collection, shortened_collection,
                                 without_ids)
from .journal_support import step_journal_url
from .task_support import NEW, TaskCase, steps_of

ASA = "acetylsalicylic-acid"
CINNAMIC = "cinnamic-acid"
THREE = [("OSDB-0010", 1), ("OSDB-0007", 1), ("OSDB-0008", 1)]


class StartCase(TaskCase):
    """The task case with the demo collection and, imported after it,
    ``longer_collection``: ``SEQ-0001`` of two steps makes
    ``acetylsalicylic-acid``, and ``SEQ-0003`` of three steps and
    ``SEQ-0004`` of two make ``cinnamic-acid``. ``kl`` is signed in;
    a form that names a sequence without a substance names its
    target."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.longer = import_collection(longer_collection())

    def entries(self, task: Task) -> list[tuple[str, int] | None]:
        return [entry for entry, _import, _done in task_steps(task)]

    def refused(self, response: Any, *fields: str) -> None:
        """The form is shown again with an error at one of FIELDS."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(any(name in errors for name in fields),
                        f"no error at {fields}: {sorted(errors)}")

    def followed(self, sequence: str = "SEQ-0003", start_step: str = "",
                 **fields: str) -> Task:
        """The only task, made through the form."""
        done = self.create(sequence=sequence, start_step=start_step,
                           **fields)
        self.assertEqual(done.status_code, 302)
        return self.only_task()


class RecordTests(StartCase):

    def test_the_field_is_a_positive_integer_that_is_1_by_default(
            self) -> None:
        """Requirement: Task record (`start_step`, from 1, and 1 for a
        task without a sequence)."""
        field = Task._meta.get_field("start_step")
        self.assertIsInstance(field, (models.PositiveIntegerField,
                                      models.PositiveSmallIntegerField))
        self.assertEqual(field.default, 1)
        self.assertEqual(make_task(self.kl).start_step, 1)

    def test_a_task_that_starts_at_the_second_step(self) -> None:
        """Scenario: A task that starts at the second step."""
        done = self.create(substance=ASA, sequence="SEQ-0001",
                           start_step="2")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.start_step, 2)
        self.assertEqual(task_steps(task),
                         [(("OSDB-0002", 1), self.longer, None)])
        self.assertEqual([s.position for s in steps_of(task)], [1])

    def test_the_steps_are_the_sequences_from_the_start(self) -> None:
        """Requirement: Task record (the task's steps become one per
        step of the sequence from `start_step` on, in its order)."""
        wanted = {"": THREE, "1": THREE, "2": THREE[1:], "3": THREE[2:]}
        for start, entries in wanted.items():
            with self.subTest(start_step=start):
                Task.objects.all().delete()
                task = self.followed(start_step=start)
                self.assertEqual(self.entries(task), entries)
                self.assertEqual([s.position for s in steps_of(task)],
                                 list(range(1, len(entries) + 1)))
                self.assertEqual(task.start_step, int(start or 1))

    def test_the_last_step_may_be_the_start(self) -> None:
        """Requirement: Task record (`start_step` at most the number of
        steps)."""
        task = self.followed("SEQ-0001", "2", substance=ASA)
        self.assertEqual(task.steps.count(), 1)

    def test_the_steps_take_the_latest_accepted_import(self) -> None:
        """Requirement: Task record (each with that step's entry and the
        latest accepted import)."""
        later = import_collection(longer_collection())
        task = self.followed(start_step="2")
        self.assertEqual([i for _e, i, _d in task_steps(task)],
                         [later] * 2)

    def test_the_steps_total_is_ignored_with_a_sequence(self) -> None:
        """Requirement: Task forms (with a sequence the field is
        ignored)."""
        task = self.followed(start_step="2", steps_total="7")
        self.assertEqual(task.steps.count(), 2)

    def test_the_start_step_is_ignored_without_a_sequence(self) -> None:
        """Requirement: Task forms (ignored without a sequence); Task
        record (1 for a task without a sequence)."""
        done = self.create(start_step="3", steps_total="2")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.start_step, 1)
        self.assertEqual(task_steps(task), [(None, None, None)] * 2)

    def test_the_steps_done_count_the_steps_from_the_start(self) -> None:
        """Requirement: Task forms (steps done marks the first that many
        steps done)."""
        task = self.followed(start_step="2", started="2025-03-01",
                             steps_done="1")
        self.assertEqual(
            [step.done_on is not None for step in steps_of(task)],
            [True, False])
        self.assertEqual(task.progress, 50)

    def test_steps_done_above_the_steps_from_the_start(self) -> None:
        """Requirement: Task forms (steps done above the number of
        steps)."""
        done = self.create(sequence="SEQ-0001", start_step="2",
                           substance=ASA, steps_done="2",
                           started="2025-03-01")
        self.refused(done, "steps_done")
        self.assertEqual(Task.objects.count(), 0)


class StartStepRuleTests(StartCase):
    """The range of the start step and the sequence's target."""

    def test_a_start_step_beyond_the_sequence(self) -> None:
        """Scenario: A start step beyond the sequence."""
        done = self.create(substance=ASA, sequence="SEQ-0001",
                           start_step="3")
        self.refused(done, "start_step")
        self.assertEqual(Task.objects.count(), 0)

    def test_a_start_step_that_is_no_step(self) -> None:
        """Requirement: Task forms (start step, a whole number, from
        1)."""
        for text in ("0", "-1", "two", "1.5"):
            with self.subTest(start_step=text):
                done = self.create(sequence="SEQ-0003", start_step=text)
                self.refused(done, "start_step")
                self.assertEqual(Task.objects.count(), 0)

    def test_a_sequence_of_another_target(self) -> None:
        """Scenario: A sequence of another target."""
        done = self.create(substance=CINNAMIC, sequence="SEQ-0001")
        self.refused(done, "sequence")
        self.assertEqual(Task.objects.count(), 0)

    def test_the_target_rule_holds_for_every_sequence(self) -> None:
        """Requirement: Task record (its target is the task's
        substance)."""
        for sequence, substance in (("SEQ-0001", "aspirin"),
                                    ("SEQ-0002", ASA),
                                    ("SEQ-0003", ASA),
                                    ("SEQ-0004", "aspirin")):
            with self.subTest(sequence=sequence, substance=substance):
                self.refused(self.create(substance=substance,
                                         sequence=sequence), "sequence")
        self.assertEqual(Task.objects.count(), 0)

    def test_the_target_of_the_sequence_is_accepted(self) -> None:
        """Requirement: Task record (its target is the task's
        substance)."""
        for sequence, substance in (("SEQ-0001", ASA),
                                    ("SEQ-0002", "1-biphenyl-4-yl-ethanol"),
                                    ("SEQ-0003", CINNAMIC),
                                    ("SEQ-0004", CINNAMIC)):
            with self.subTest(sequence=sequence):
                done = self.create(substance=substance, sequence=sequence)
                self.assertEqual(done.status_code, 302)
        self.assertEqual(Task.objects.count(), 4)

    def test_a_sequence_set_on_a_task_of_another_substance(self) -> None:
        """Requirement: Task forms (on a save that plans the steps anew a
        sequence whose target is not the task's substance)."""
        task = make_task(self.kl, "Aspirin", steps=2)
        self.refused(self.change(task, sequence="SEQ-0001",
                                 substance="aspirin"), "sequence")
        task.refresh_from_db()
        self.assertIsNone(task.sequence)
        self.assertEqual(task.steps.count(), 2)
        done = self.change(task, sequence="SEQ-0001", substance=ASA)
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.only_task().sequence.key, "SEQ-0001")

    def test_a_sequence_changed_to_one_of_another_target(self) -> None:
        """Requirement: Task forms (on a save that plans the steps anew
        a sequence whose target is not the task's substance)."""
        task = self.followed()
        done = self.change(task, sequence="SEQ-0001", substance=CINNAMIC)
        self.refused(done, "sequence")
        task = self.only_task()
        self.assertEqual(task.sequence.key, "SEQ-0003")
        self.assertEqual(self.entries(task), THREE)

    def test_a_substance_changed_away_from_the_target(self) -> None:
        """Requirement: Task forms (a substance changed on a task with a
        sequence to another than the sequence's target)."""
        task = self.followed()
        self.refused(self.change(task, substance="aspirin"), "substance",
                     "sequence")
        task = self.only_task()
        self.assertEqual(task.substance.key, CINNAMIC)
        self.assertEqual(self.entries(task), THREE)

    def test_a_substance_may_change_on_a_task_without_a_sequence(
            self) -> None:
        """Requirement: Task record (a task without a sequence makes any
        substance)."""
        task = make_task(self.kl, "Aspirin", steps=1)
        done = self.change(task, substance=CINNAMIC)
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.only_task().substance.key, CINNAMIC)

    def test_the_range_is_not_checked_without_a_sequence(self) -> None:
        """Requirement: Task forms (a start step above the sequence's
        number of steps, on a save that plans the steps anew)."""
        done = self.create(start_step="99", steps_total="1")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.only_task().start_step, 1)


class ChangingTheStartTests(StartCase):
    """A save that changes the start step plans the steps anew, under
    the rules for changing the sequence."""

    def booked(self, task: Task) -> Any:
        """The first step of TASK, with a lot it made."""
        first = steps_of(task)[0]
        make_lot(self.kl, substance=first.products()[0], source="made",
                 task_step=first, unit="g", amount="2")
        return first

    def test_changing_the_start_step_replaces_the_steps(self) -> None:
        """Requirement: Task record (a save that changes `start_step`
        plans the steps anew)."""
        task = self.followed(start_step="3")
        later = import_collection(longer_collection())
        done = self.change(task, start_step="2")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.start_step, 2)
        self.assertEqual(task_steps(task), [
            (("OSDB-0007", 1), later, None),
            (("OSDB-0008", 1), later, None)])
        self.change(task, start_step="1")
        task = self.only_task()
        self.assertEqual((task.start_step, self.entries(task)),
                         (1, THREE))

    def test_changing_the_sequence_keeps_the_posted_start(self) -> None:
        """Requirement: Task record (when it sets or changes either,
        the steps become one per step of the sequence from
        `start_step`)."""
        task = self.followed(start_step="2")
        done = self.change(task, sequence="SEQ-0004")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual((task.sequence.key, task.start_step), (
            "SEQ-0004", 2))
        self.assertEqual(self.entries(task), [("OSDB-0008", 1)])

    def test_setting_a_sequence_with_a_start_step(self) -> None:
        """Requirement: Task record (a sequence set replaces the steps
        from `start_step` on)."""
        task = make_task(self.kl, CINNAMIC, steps=5)
        done = self.change(task, sequence="SEQ-0003", start_step="2")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.start_step, 2)
        self.assertEqual(self.entries(task), THREE[1:])

    def test_clearing_the_sequence_gives_plain_steps_from_1(self) -> None:
        """Requirement: Task record (1 for a task without a sequence;
        when it clears the sequence the steps become plain)."""
        task = self.followed(start_step="2")
        done = self.change(task, sequence="", steps_total="3")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.start_step, 1)
        self.assertEqual(task_steps(task), [(None, None, None)] * 3)

    def test_a_start_step_changed_beyond_a_shorter_sequence(self) -> None:
        """Requirement: Task forms (a start step above the sequence's
        number of steps, on a save that plans the steps anew)."""
        task = self.followed()
        import_collection(shortened_collection())
        self.refused(self.change(task, start_step="3"), "start_step")
        task = self.only_task()
        self.assertEqual((task.start_step, self.entries(task)),
                         (1, THREE))

    def test_no_change_of_the_start_step_with_a_step_done(self) -> None:
        """Requirement: Task forms (a start step changed on a task with
        a step done)."""
        task = self.followed(started="2025-03-01", steps_done="1")
        before = task_steps(task)
        self.refused(self.change(task, start_step="2"), "start_step")
        task = self.only_task()
        self.assertEqual((task.start_step, task_steps(task)), (1, before))

    def test_no_change_with_a_lot_made(self) -> None:
        """Requirement: Task record (a save may change `start_step` only
        while no step has made a lot)."""
        task = self.followed()
        self.booked(task)
        self.refused(self.change(task, start_step="2"), "start_step")
        task = self.only_task()
        self.assertEqual((task.start_step, self.entries(task)),
                         (1, THREE))

    def test_no_change_with_a_withdrawal_taken(self) -> None:
        """Requirement: Task record (a save may change `start_step` only
        while no step has taken a withdrawal)."""
        task = self.followed()
        lot = make_lot(self.kl, substance=steps_of(task)[1].substrates()[0],
                       unit="g", amount="5")
        make_withdrawal(self.kl, lot, steps_of(task)[1], "1")
        self.refused(self.change(task, start_step="2"), "start_step")
        self.assertEqual(self.only_task().start_step, 1)

    def test_no_change_with_a_journal_entry_named(self) -> None:
        """Requirement: Task forms (a start step changed on a task with
        a step naming a journal entry)."""
        task = self.followed()
        done = self.client.post(step_journal_url(steps_of(task)[0]),
                                {"journal_entry": "AE-1/9"})
        self.assertEqual(done.status_code, 302)
        self.refused(self.change(task, start_step="2"), "start_step")
        self.assertEqual(self.only_task().start_step, 1)

    def test_a_start_step_kept_is_no_change(self) -> None:
        """Requirement: Task record (a save that leaves `sequence` and
        `start_step` as they were leaves the steps)."""
        task = self.followed(start_step="2", started="2025-03-01",
                             steps_done="1")
        before = task_steps(task)
        done = self.change(task, note="Nur eine Notiz")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task_steps(task), before)
        self.assertEqual((task.start_step, task.note), (2, "Nur eine Notiz"))

    def test_a_plan_outlives_a_shorter_sequence(self) -> None:
        """Scenario: A plan outlives a shorter sequence."""
        task = self.followed(start_step="3")
        before = task_steps(task)
        self.assertEqual(self.entries(task), THREE[2:])
        import_collection(shortened_collection())
        done = self.change(task, note="Nur eine Notiz")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual((task.start_step, task.note), (3, "Nur eine Notiz"))
        self.assertEqual(task_steps(task), before)

    def test_a_plan_outlives_a_retargeted_sequence(self) -> None:
        """Requirement: Task record (other saves keep a plan whose
        sequence the collection has since changed, whatever its
        target)."""
        task = self.followed(start_step="3")
        before = task_steps(task)
        import_collection(retargeted_collection())
        done = self.change(task, note="Nur eine Notiz")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual((task.start_step, task.substance.key),
                         (3, CINNAMIC))
        self.assertEqual(task_steps(task), before)

    def test_a_plan_outlives_a_withdrawn_sequence(self) -> None:
        """Requirement: Task record (a task keeps its steps after the
        sequence is withdrawn)."""
        task = self.followed("SEQ-0001", "2", substance=ASA)
        import_collection(without_ids("SEQ-0001"))
        done = self.change(task, report="on")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual((task.start_step, task.sequence.key),
                         (2, "SEQ-0001"))
        self.assertEqual(self.entries(task), [("OSDB-0002", 1)])


class FormTests(StartCase):
    """The form's field and what the planning list fills in."""

    def test_the_new_form_fills_in_the_sequence_and_the_start(self) -> None:
        """Scenario: Filled in from the planning list."""
        root = page(self.client.get(
            f"{NEW}?substance={ASA}&sequence=SEQ-0001&start_step=2"))
        self.assertEqual(field_value(root, "substance"), ASA)
        self.assertEqual(field_value(root, "sequence"), "SEQ-0001")
        self.assertEqual(field_value(root, "start_step"), "2")

    def test_a_form_filled_in_from_the_list_saves(self) -> None:
        """Scenario: Filled in from the planning list (the form posts
        as it is)."""
        root = page(self.client.get(
            f"{NEW}?substance={ASA}&sequence=SEQ-0001&start_step=2"))
        done = self.client.post(NEW, task_form_data(**{
            name: field_value(root, name) or ""
            for name in ("substance", "sequence", "start_step")}))
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual((task.sequence.key, task.start_step), (
            "SEQ-0001", 2))

    def test_the_form_has_the_start_step_field_with_its_label(self) -> None:
        """Requirement: Task forms (start step, `Beginn ab Stufe`)."""
        root = page(self.client.get(NEW))
        self.assertIsNotNone(root.find(("input", "select"),
                                       name="start_step"))
        self.assertIn("Beginn ab Stufe", root.text())
        accept(language="en")
        self.assertIn("Start at step", page(self.client.get(NEW)).text())

    def test_the_edit_form_shows_the_start_step(self) -> None:
        """Requirement: Task forms (start step)."""
        task = self.followed(start_step="2")
        root = page(self.client.get(task_url(task, "edit")))
        self.assertEqual(field_value(root, "start_step"), "2")
        self.assertEqual(field_value(root, "sequence"), "SEQ-0003")
        self.assertEqual(field_value(root, "steps_total"), "2")


class PageTests(StartCase):
    """The task page (task-tracker: Task page)."""

    def show(self, task: Task) -> Any:
        self.client.logout()
        response = self.client.get(task_url(task))
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_the_page_shows_where_the_task_starts(self) -> None:
        """Requirement: Task page (the sequence's ID followed by `ab
        Stufe <k>` when its `start_step` is above 1)."""
        task = self.followed("SEQ-0001", "2", substance=ASA)
        root = self.show(task)
        self.assertIn("SEQ-0001 ab Stufe 2", root.text())
        links = root.find_all("a", href="/sequences/seq-0001/")
        self.assertEqual([a.text() for a in links], ["SEQ-0001"])

    def test_the_page_shows_where_the_task_starts_in_english(self) -> None:
        """Requirement: Task page (`from step <k>`)."""
        task = self.followed("SEQ-0001", "2", substance=ASA)
        accept(language="en")
        self.assertIn("SEQ-0001 from step 2", self.show(task).text())

    def test_a_task_from_the_first_step_shows_no_start(self) -> None:
        """Requirement: Task page (when its `start_step` is above 1)."""
        task = self.followed("SEQ-0001", "1", substance=ASA)
        text = self.show(task).text()
        self.assertIn("SEQ-0001", text)
        self.assertNotIn("ab Stufe", text)

    def test_a_task_without_a_sequence_shows_no_start(self) -> None:
        """Requirement: Task page (a task with a sequence shows the
        sequence's ID)."""
        task = make_task(self.kl, CINNAMIC, steps=2)
        self.assertNotIn("ab Stufe", self.show(task).text())

    def test_the_steps_listed_are_those_from_the_start(self) -> None:
        """Requirement: Task page (a task with steps lists them in
        order)."""
        task = self.followed(start_step="2")
        items = self.show(task).find("ol").find_all("li")
        self.assertEqual([[a.get("href") for a in item.find_all("a")]
                          for item in items],
                         [["/procedures/osdb-0007/"],
                          ["/procedures/osdb-0008/"]])
        self.assertIn("SEQ-0003 ab Stufe 2", self.show(task).text())

    def test_a_withdrawn_sequence_keeps_the_start_on_the_page(
            self) -> None:
        """Requirement: Task page (a withdrawn sequence shows with the
        mark and no link)."""
        task = self.followed("SEQ-0001", "2", substance=ASA)
        import_collection(without_ids("SEQ-0001"))
        text = self.show(task).text()
        self.assertIn(NOT_IN_COLLECTION["de"], text)
        self.assertIn("ab Stufe 2", text)


class AdminTests(StartCase):
    """Requirement: Tasks in the admin (the plan read-only; the same
    refusal of a substance change)."""

    def setUp(self) -> None:
        super().setUp()
        self.staff = make_user("boss", "BO", is_staff=True,
                               is_superuser=True)

    def change_page(self, task: Task) -> Any:
        self.client.force_login(self.staff)
        return self.client.get(f"/lab/admin/tasks/task/{task.pk}/change/")

    def posted(self, response: Any, **over: Any) -> dict[str, Any]:
        """The change page's form as it stands, with OVER applied: every
        field of the form, and the empty management form of the
        steps."""
        form = response.context["adminform"].form
        data: dict[str, Any] = {}
        for name in form.fields:
            value = form[name].value()
            if value is True:
                data[name] = "on"
            elif value not in (None, False):
                data[name] = (value.isoformat()
                              if isinstance(value, date) else value)
            elif value is None:
                data[name] = ""
        data.update({"steps-TOTAL_FORMS": "0", "steps-INITIAL_FORMS": "0",
                     "steps-MIN_NUM_FORMS": "0",
                     "steps-MAX_NUM_FORMS": "1000"})
        data.update(over)
        return data

    def test_the_plan_shows_read_only(self) -> None:
        """Scenario: The plan read-only in the admin (the sequence and
        the start step show read-only)."""
        task = self.followed(start_step="2")
        html = self.change_page(task).content.decode()
        self.assertNotIn('name="sequence"', html)
        self.assertNotIn('name="start_step"', html)
        self.assertIn("field-sequence", html)
        self.assertIn("field-start_step", html)

    def test_a_save_in_the_admin_as_it_stands(self) -> None:
        """Scenario: The plan read-only in the admin (a post that
        changes nothing is saved)."""
        task = self.followed(start_step="2")
        response = self.change_page(task)
        done = self.client.post(
            f"/lab/admin/tasks/task/{task.pk}/change/",
            self.posted(response, note="Aus dem Admin"))
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual((task.note, task.start_step, task.sequence.key),
                         ("Aus dem Admin", 2, "SEQ-0003"))

    def test_no_revert_from_the_history(self) -> None:
        """Requirement: Tasks in the admin (`start_step` read-only:
        reverting to a past version, which would restore it without
        planning the steps, is refused)."""
        task = self.followed(start_step="2")
        first = task.history.order_by("history_id").first()
        task.start_step = 1
        task.save()
        self.client.force_login(self.staff)
        path = (f"/lab/admin/tasks/task/{task.pk}/history/"
                f"{first.history_id}/")
        shown = self.client.get(path)
        self.assertEqual(shown.status_code, 200)
        done = self.client.post(path, self.posted(shown))
        self.assertEqual(done.status_code, 403)
        self.assertEqual(Task.objects.get(pk=task.pk).start_step, 1)

    def test_the_admin_refuses_another_substance(self) -> None:
        """Scenario: The plan read-only in the admin."""
        from registry.models import Substance
        task = self.followed(start_step="2")
        response = self.change_page(task)
        done = self.client.post(
            f"/lab/admin/tasks/task/{task.pk}/change/",
            self.posted(response, substance=Substance.objects.get(
                key="aspirin").pk))
        self.assertEqual(done.status_code, 200)
        self.assertTrue(
            done.context["adminform"].form.errors
            or "errornote" in done.content.decode())
        task = self.only_task()
        self.assertEqual(task.substance.key, CINNAMIC)
        self.assertEqual(task.start_step, 2)

    def test_the_admin_changes_the_substance_of_a_task_without_a_sequence(
            self) -> None:
        """Requirement: Tasks in the admin (a substance changed on a
        task with a sequence is refused, not on one without)."""
        from registry.models import Substance
        task = make_task(self.kl, "Aspirin", steps=1)
        response = self.change_page(task)
        done = self.client.post(
            f"/lab/admin/tasks/task/{task.pk}/change/",
            self.posted(response, substance=Substance.objects.get(
                key=CINNAMIC).pk))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Task.objects.get().substance.key, CINNAMIC)
