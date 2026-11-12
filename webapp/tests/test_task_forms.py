"""Tests of the task forms (task-tracker: Task forms, Task record)."""

from datetime import date

from tasks.models import Task

from . import (berlin, context_form, done_days, edit_data, field_value,
               frozen, make_lot, make_task, page, past, sent_messages,
               substance_for, task_form_data, task_steps, task_url)
from .collection_support import (accept, changed_collection,
                                 import_collection, without_ids)
from .task_support import NEW, TaskCase, history_text, make_product_lot

FIELDS = {"substance", "priority", "assignee", "started", "ended", "sequence",
          "steps_total", "steps_done", "batch", "report", "qc_list",
          "note"}


class FormCase(TaskCase):

    def setUp(self) -> None:
        super().setUp()
        for text in ("Aspirin", "Probe", "CH-0012"):
            substance_for(text)

    def only_task(self) -> Task:
        return Task.objects.get()

    def refused(self, response, field: str | None = None) -> None:
        """The form is shown again with errors, and nothing changed."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(errors, "the form shows no error")
        if field is not None:
            self.assertIn(field, errors)


class CreateTests(FormCase):

    def test_creating_a_task(self) -> None:
        """Scenario: Creating a task."""
        done = self.client.post(NEW, task_form_data(
            substance="cinnamic-acid", priority="high",
            assignee=str(self.ae.pk)))
        task = self.only_task()
        self.assertRegex(task.number, r"^T-\d{3,}$")
        self.assertEqual(task.state, "planned")
        self.assertEqual(task.created_by, self.kl)
        self.assertEqual(task.substance.key, "cinnamic-acid")
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.assignee, self.ae)
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        text = page(self.client.get(task_url(task))).text()
        self.assertIn(f"Aufgabe {task.number} gespeichert.", text)
        self.assertIn("(E)-Zimtsäure", text)

    def test_the_message_is_shown_on_the_page_after_the_redirect(
            self) -> None:
        done = self.client.post(NEW, task_form_data(), follow=True)
        number = self.only_task().number
        self.assertIn(f"Aufgabe {number} gespeichert.",
                      page(done).text())

    def test_the_message_is_english_on_an_english_site(self) -> None:
        accept(language="en")
        done = self.client.post(NEW, task_form_data(), follow=True)
        number = self.only_task().number
        self.assertIn(f"Task {number} saved.", page(done).text())

    def test_all_fields_are_saved(self) -> None:
        make_lot(self.kl, substance=substance_for("Probe"), batch="B-9")
        self.client.post(NEW, task_form_data(
            substance="probe", priority="low", assignee=str(self.ae.pk),
            started="2025-03-02", ended="2025-03-05", steps_total="5",
            steps_done="3", batch="B-9", report="on", qc_list="on",
            note="Zeile eins\nZeile zwei"))
        task = self.only_task()
        self.assertEqual(
            (task.substance.key, task.priority, task.assignee),
            ("probe", "low", self.ae))
        self.assertEqual((task.started, task.ended),
                         (past(2), past(5)))
        self.assertEqual(task.steps.count(), 5)
        self.assertEqual(
            [d is not None for d in done_days(task)],
            [True, True, True, False, False])
        self.assertEqual(task.batch, "B-9")
        self.assertTrue(task.report)
        self.assertTrue(task.qc_list)
        self.assertFalse(task.cancelled)
        self.assertIn("Zeile zwei", task.note)
        self.assertEqual(task.state, "ended")

    def test_steps_done_defaults_to_zero(self) -> None:
        self.client.post(NEW, task_form_data(steps_total="4"))
        task = self.only_task()
        self.assertEqual(done_days(task), [None] * 4)

    def test_without_a_total_steps_done_is_zero(self) -> None:
        self.client.post(NEW, task_form_data())
        task = self.only_task()
        self.assertEqual(task.steps.count(), 0)
        self.assertIsNone(task.progress)

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(NEW))
        form = root.find("input", name="substance").closest("form")
        names = {e.get("name") for e in
                 form.find_all(("input", "select", "textarea"))}
        names.discard("csrfmiddlewaretoken")
        self.assertEqual(names, FIELDS)

    def test_cancelled_and_failed_are_on_the_edit_form_only(self) -> None:
        """Requirement: Task forms (cancelled and failed, on the edit
        form only)."""
        task = make_task(self.kl)
        root = page(self.client.get(task_url(task, "edit")))
        form = root.find("input", name="substance").closest("form")
        names = {e.get("name") for e in
                 form.find_all(("input", "select", "textarea"))}
        names.discard("csrfmiddlewaretoken")
        self.assertEqual(names, FIELDS | {"cancelled", "failed"})

    def test_priority_choices_and_default(self) -> None:
        root = page(self.client.get(NEW))
        options = root.find("select", name="priority").find_all("option")
        self.assertEqual({o.get("value"): o.text() for o in options},
                         {"high": "hoch", "medium": "mittel",
                          "low": "niedrig"})
        self.assertEqual(field_value(root, "priority"), "medium")

    def test_assignee_choices(self) -> None:
        root = page(self.client.get(NEW))
        options = root.find("select", name="assignee").find_all("option")
        values = [o.get("value") for o in options]
        self.assertIn("", values)
        self.assertLessEqual({str(self.kl.pk), str(self.ae.pk)},
                             set(values))
        texts = [o.text() for o in options]
        self.assertTrue(any("AE" in t and "Anna Eisele" in t
                            for t in texts), texts)
        self.assertEqual(field_value(root, "assignee"), "")

    def test_the_creator_is_the_signed_in_user(self) -> None:
        self.client.force_login(self.ae)
        self.client.post(NEW, task_form_data())
        self.assertEqual(self.only_task().created_by, self.ae)


class ValidationTests(FormCase):

    def test_end_before_start(self) -> None:
        """Scenario: End before start."""
        done = self.client.post(NEW, task_form_data(
            started="2025-03-05", ended="2025-03-04"))
        self.refused(done, "ended")
        self.assertEqual(Task.objects.count(), 0)

    def test_end_without_a_start(self) -> None:
        done = self.client.post(NEW, task_form_data(ended="2025-03-04"))
        self.refused(done)
        self.assertEqual(Task.objects.count(), 0)

    def test_same_day_is_allowed(self) -> None:
        make_lot(self.kl, substance=substance_for("Aspirin"), batch="B-1")
        self.client.post(NEW, task_form_data(
            started="2025-03-04", ended="2025-03-04", batch="B-1"))
        self.assertEqual(self.only_task().state, "ended")

    def test_dates_may_not_lie_in_the_future(self) -> None:
        done = self.client.post(NEW, task_form_data(started="2999-01-01"))
        self.refused(done, "started")
        done = self.client.post(NEW, task_form_data(
            started="2025-03-04", ended="2999-01-01"))
        self.refused(done, "ended")
        self.assertEqual(Task.objects.count(), 0)

    def test_steps_done_above_the_total(self) -> None:
        done = self.client.post(NEW, task_form_data(
            steps_total="3", steps_done="4"))
        self.refused(done, "steps_done")
        self.assertEqual(Task.objects.count(), 0)

    def test_steps_done_equal_to_the_total_is_allowed(self) -> None:
        self.client.post(NEW, task_form_data(steps_total="3",
                                             steps_done="3"))
        self.assertEqual(self.only_task().progress, 100)

    def test_steps_total_is_at_least_one(self) -> None:
        for value in ("-1", "two"):
            with self.subTest(value=value):
                done = self.client.post(NEW, task_form_data(
                    steps_total=value))
                self.refused(done, "steps_total")
        self.assertEqual(Task.objects.count(), 0)

    def test_steps_done_is_not_negative(self) -> None:
        done = self.client.post(NEW, task_form_data(
            steps_total="3", steps_done="-1"))
        self.refused(done, "steps_done")

    def test_the_substance_is_required(self) -> None:
        self.refused(self.client.post(NEW, task_form_data(substance="")),
                     "substance")
        self.assertEqual(Task.objects.count(), 0)

    def test_unknown_substance(self) -> None:
        self.refused(self.client.post(NEW, task_form_data(
            substance="no-such-substance")), "substance")
        self.assertEqual(Task.objects.count(), 0)

    def test_a_substance_is_named_by_its_key_alone(self) -> None:
        for text in ("Aspirin", "CH-0012", "(E)-Zimtsäure"):
            with self.subTest(text=text):
                self.refused(self.client.post(NEW, task_form_data(
                    substance=text)), "substance")
        self.assertEqual(Task.objects.count(), 0)

    def test_batch_is_bounded(self) -> None:
        self.refused(self.client.post(NEW, task_form_data(
            batch="b" * 31)), "batch")
        self.assertEqual(Task.objects.count(), 0)

    def test_priority_must_be_one_of_the_three(self) -> None:
        self.refused(self.client.post(NEW, task_form_data(
            priority="urgent")), "priority")

    def test_assignee_must_be_an_account(self) -> None:
        self.refused(self.client.post(NEW, task_form_data(
            assignee="99999")), "assignee")

    def test_the_form_keeps_what_was_typed(self) -> None:
        done = self.client.post(NEW, task_form_data(
            substance="probe", batch="B-9", steps_total="3",
            steps_done="4"))
        root = page(done)
        self.assertEqual(field_value(root, "substance"), "probe")
        self.assertEqual(field_value(root, "batch"), "B-9")
        self.assertEqual(field_value(root, "steps_done"), "4")

    def test_a_refused_form_sends_no_success_message(self) -> None:
        done = self.client.post(NEW, task_form_data(substance=""))
        self.assertEqual(sent_messages(done), [])


class EditTests(FormCase):

    def test_the_form_shows_the_task(self) -> None:
        task = make_task(self.kl, substance="Probe", priority="low",
                         assignee=self.ae, started=past(2),
                         steps=5, done=2, batch="B-9",
                         report=True, note="Notiz")
        root = page(self.client.get(task_url(task, "edit")))
        self.assertEqual(field_value(root, "substance"), "probe")
        self.assertEqual(field_value(root, "priority"), "low")
        self.assertEqual(field_value(root, "assignee"), str(self.ae.pk))
        self.assertEqual(field_value(root, "steps_total"), "5")
        self.assertEqual(field_value(root, "steps_done"), "2")
        self.assertEqual(field_value(root, "batch"), "B-9")
        self.assertEqual(field_value(root, "report"), "on")
        self.assertEqual(field_value(root, "qc_list"), "")
        self.assertEqual(field_value(root, "note"), "Notiz")

    def test_changing_a_task(self) -> None:
        task = make_task(self.kl, substance="Probe")
        self.client.force_login(self.ae)
        done = self.client.post(task_url(task, "edit"), edit_data(
            task, priority="high", batch="B-1", cancelled="on"))
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.batch, "B-1")
        self.assertTrue(task.cancelled)
        self.assertEqual(task.state, "cancelled")
        self.assertEqual(task.created_by, self.kl)
        self.assertEqual(task.number, "T-001")
        text = page(self.client.get(task_url(task))).text()
        self.assertIn(f"Aufgabe {task.number} gespeichert.", text)

    def test_a_change_is_recorded_with_its_user(self) -> None:
        task = make_task(self.kl, substance="Probe")
        self.client.post(task_url(task, "edit"),
                         edit_data(task, priority="high"))
        newest = task.history.first()
        self.assertEqual(newest.history_user, self.kl)
        self.assertEqual(task.history.count(), 2)

    def test_a_refused_edit_changes_nothing(self) -> None:
        task = make_task(self.kl, substance="Probe", started=past(5))
        done = self.client.post(task_url(task, "edit"), edit_data(
            task, ended="2025-03-04", substance="aspirin"))
        self.refused(done, "ended")
        task.refresh_from_db()
        self.assertEqual(task.substance.key, "probe")
        self.assertIsNone(task.ended)
        self.assertEqual(task.history.count(), 1)

    def test_flags_can_be_turned_off(self) -> None:
        task = make_task(self.kl, started=past(1), ended=past(2),
                         report=True, qc_list=True, batch="B-7")
        make_product_lot(task)
        data = edit_data(task)
        del data["report"]
        self.client.post(task_url(task, "edit"), data)
        task.refresh_from_db()
        self.assertFalse(task.report)
        self.assertTrue(task.qc_list)

    def test_a_cancelled_task_can_be_taken_back(self) -> None:
        task = make_task(self.kl, cancelled=True)
        data = edit_data(task)
        del data["cancelled"]
        self.client.post(task_url(task, "edit"), data)
        task.refresh_from_db()
        self.assertEqual(task.state, "planned")


class StepsDoneTests(FormCase):
    """Steps by hand and the steps done (task-tracker: Task forms)."""

    def test_steps_by_hand(self) -> None:
        """Scenario: Steps by hand."""
        with frozen(berlin(2026, 11, 5)):
            self.create(steps_total="3", steps_done="1")
        task = self.only_task()
        self.assertEqual(task.steps.count(), 3)
        self.assertEqual([e for e, _i, _d in task_steps(task)],
                         [None] * 3)
        with frozen(berlin(2026, 11, 6)):
            self.change(task, steps_done="2")
        self.assertEqual(done_days(self.only_task()),
                         [date(2026, 11, 5), date(2026, 11, 6), None])

    def test_steps_done_left_alone_keep_their_dates(self) -> None:
        """Requirement: Task forms (those done before keep their
        dates)."""
        with frozen(berlin(2026, 11, 5)):
            self.create(steps_total="3", steps_done="2")
        task = self.only_task()
        with frozen(berlin(2026, 11, 9)):
            self.change(task, note="Another day")
        self.assertEqual(done_days(self.only_task()),
                         [date(2026, 11, 5), date(2026, 11, 5), None])

    def test_fewer_steps_done_clear_the_last_ones(self) -> None:
        """Requirement: Task forms (the rest not done)."""
        with frozen(berlin(2026, 11, 5)):
            self.create(steps_total="3", steps_done="3")
        task = self.only_task()
        self.change(task, steps_done="1")
        self.assertEqual(done_days(self.only_task()),
                         [date(2026, 11, 5), None, None])
        self.change(self.only_task(), steps_done="")
        self.assertEqual(done_days(self.only_task()), [None] * 3)

    def test_steps_done_mark_the_first_steps(self) -> None:
        """Requirement: Task forms (marks the first that many steps
        done)."""
        self.create(steps_total="4", steps_done="2")
        self.assertEqual(
            [d is not None for d in done_days(self.only_task())],
            [True, True, False, False])

    def test_the_steps_total_adds_steps_at_the_end(self) -> None:
        """Requirement: Task forms (steps are added, not done)."""
        with frozen(berlin(2026, 11, 5)):
            self.create(steps_total="2", steps_done="1")
        task = self.only_task()
        first = [s.pk for s in task.steps.order_by("position")]
        self.change(task, steps_total="4")
        task = self.only_task()
        steps = list(task.steps.order_by("position"))
        self.assertEqual([s.position for s in steps], [1, 2, 3, 4])
        self.assertEqual([s.pk for s in steps[:2]], first)
        self.assertEqual(done_days(task),
                         [date(2026, 11, 5), None, None, None])

    def test_the_steps_total_removes_the_last_steps(self) -> None:
        """Requirement: Task forms (the last ones removed)."""
        self.create(steps_total="4", steps_done="1")
        task = self.only_task()
        first = [s.pk for s in task.steps.order_by("position")]
        self.change(task, steps_total="2")
        steps = list(self.only_task().steps.order_by("position"))
        self.assertEqual([s.pk for s in steps], first[:2])

    def test_an_empty_total_removes_every_step(self) -> None:
        """Requirement: Task forms (an empty total removes them all)."""
        self.create(steps_total="3")
        task = self.only_task()
        self.change(task, steps_total="")
        self.assertEqual(self.only_task().steps.count(), 0)

    def test_a_removed_step_is_recorded_in_its_history(self) -> None:
        """Requirement: Task record (steps keep a change history)."""
        from tasks.models import TaskStep
        self.create(steps_total="3")
        task = self.only_task()
        removed = task.steps.get(position=3)
        self.change(task, steps_total="2")
        self.assertEqual(
            TaskStep.history.filter(id=removed.pk).first().history_type,
            "-")

    def test_steps_done_above_the_steps(self) -> None:
        """Requirement: Task forms (steps done above the number of
        steps)."""
        self.refused(self.create(steps_total="2", steps_done="3"),
                     "steps_done")
        self.refused(self.create(steps_done="1"), "steps_done")
        self.assertEqual(Task.objects.count(), 0)

    def test_a_total_below_the_steps_done(self) -> None:
        """Requirement: Task forms (a steps total below the number of
        steps done)."""
        self.create(steps_total="3", steps_done="2")
        task = self.only_task()
        before = task_steps(task)
        self.refused(self.change(task, steps_total="1"))
        self.assertEqual(task_steps(self.only_task()), before)

    def test_the_total_cannot_remove_a_step_done(self) -> None:
        """Requirement: Task forms (the last ones removed, not done
        ones)."""
        self.create(steps_total="3", steps_done="1")
        task = self.only_task()
        self.refused(self.change(task, steps_total="", steps_done="1"))
        self.assertEqual(self.only_task().steps.count(), 3)

    def test_the_edit_form_shows_the_steps_and_those_done(self) -> None:
        task = make_task(self.kl, steps=5, done=2)
        root = page(self.client.get(task_url(task, "edit")))
        self.assertEqual(field_value(root, "steps_total"), "5")
        self.assertEqual(field_value(root, "steps_done"), "2")

    def test_steps_done_of_a_task_with_a_sequence(self) -> None:
        """Requirement: Task forms (steps done with a sequence)."""
        with frozen(berlin(2026, 11, 5)):
            self.create(sequence="SEQ-0001", steps_done="1")
        task = self.only_task()
        self.assertEqual(done_days(task), [date(2026, 11, 5), None])
        self.refused(self.change(task, steps_done="3"), "steps_done")


class SequenceFieldTests(FormCase):
    """The sequence choice (task-tracker: Task forms)."""

    def options(self, path: str) -> dict[str, str]:
        select = page(self.client.get(path)).find("select",
                                                  name="sequence")
        self.assertIsNotNone(select, "the form has no sequence choice")
        return {o.get("value"): o.text() for o in select.find_all("option")}

    def test_the_choice_offers_the_sequences_by_id_and_title(self) -> None:
        """Requirement: Task forms (a choice of the collection's
        sequences, by ID and title, or none)."""
        options = self.options(NEW)
        self.assertEqual(set(options), {"", "SEQ-0001", "SEQ-0002"})
        for key in ("SEQ-0001", "SEQ-0002"):
            with self.subTest(key=key):
                self.assertIn(key, options[key])
        self.assertIn("Aspirin aus Wintergrünöl", options["SEQ-0001"])
        self.assertEqual(field_value(page(self.client.get(NEW)),
                                     "sequence"), "")

    def test_the_choice_offers_no_withdrawn_sequence(self) -> None:
        """Requirement: Task forms (the sequences that are not
        withdrawn)."""
        import_collection(without_ids("SEQ-0001"))
        self.assertEqual(set(self.options(NEW)), {"", "SEQ-0002"})

    def test_the_choice_keeps_a_withdrawn_sequence_of_the_task(
            self) -> None:
        """Requirement: Task forms (keeping a withdrawn sequence the
        task already has)."""
        self.create(sequence="SEQ-0001")
        task = self.only_task()
        import_collection(without_ids("SEQ-0001"))
        path = task_url(task, "edit")
        self.assertEqual(set(self.options(path)),
                         {"", "SEQ-0001", "SEQ-0002"})
        self.assertEqual(field_value(page(self.client.get(path)),
                                     "sequence"), "SEQ-0001")
        other = make_task(self.kl)
        self.assertEqual(set(self.options(task_url(other, "edit"))),
                         {"", "SEQ-0002"})

    def test_the_edit_form_shows_the_sequence(self) -> None:
        self.create(sequence="SEQ-0002")
        task = self.only_task()
        root = page(self.client.get(task_url(task, "edit")))
        self.assertEqual(field_value(root, "sequence"), "SEQ-0002")
        self.assertEqual(field_value(root, "steps_total"), "2")

    def test_the_total_is_ignored_with_a_sequence(self) -> None:
        """Requirement: Task forms (with a sequence the field is
        ignored)."""
        self.create(sequence="SEQ-0001", steps_total="7")
        self.assertEqual(self.only_task().steps.count(), 2)
        task = self.only_task()
        self.change(task, steps_total="1")
        self.assertEqual(self.only_task().steps.count(), 2)

    def test_the_steps_come_from_the_sequence(self) -> None:
        """Scenario: Steps from a sequence."""
        done = self.create(sequence="SEQ-0002", steps_total="7")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(task_steps(self.only_task()), [
            (("OSDB-0004", 1), self.first, None),
            (("OSDB-0009", 1), self.first, None)])

    def test_an_unknown_sequence(self) -> None:
        """Requirement: Task forms (invalid input shows the form
        again)."""
        self.refused(self.create(sequence="SEQ-9999"), "sequence")
        self.assertEqual(Task.objects.count(), 0)

    def test_a_withdrawn_sequence_is_refused_when_new(self) -> None:
        """Requirement: Task forms (a withdrawn sequence the task did
        not have)."""
        import_collection(without_ids("SEQ-0001"))
        self.refused(self.create(sequence="SEQ-0001"), "sequence")
        self.assertEqual(Task.objects.count(), 0)
        task = make_task(self.kl, steps=2)
        self.refused(self.change(task, sequence="SEQ-0001"), "sequence")
        task.refresh_from_db()
        self.assertIsNone(task.sequence)

    def test_a_withdrawn_sequence_is_kept_by_a_save(self) -> None:
        """Scenario: Sequence gone from the collection (through the
        form)."""
        make_lot(self.kl, substance=substance_for("Aspirin"), batch="B-1")
        self.create(sequence="SEQ-0001", started="2025-03-01",
                    ended="2025-03-02", batch="B-1")
        task = self.only_task()
        import_collection(without_ids("SEQ-0001"))
        done = self.change(task, report="on")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertTrue(task.report)
        self.assertEqual(task.sequence.key, "SEQ-0001")
        self.assertEqual(task.steps.count(), 2)

    def test_a_sequence_with_work_done(self) -> None:
        """Scenario: A sequence with work done."""
        self.create(sequence="SEQ-0002", started="2025-03-01")
        task = self.only_task()
        self.change(task, steps_done="1")
        task = self.only_task()
        before = task_steps(task)
        done = self.change(task, sequence="SEQ-0001")
        self.refused(done, "sequence")
        task = self.only_task()
        self.assertEqual(task.sequence.key, "SEQ-0002")
        self.assertEqual(task_steps(task), before)

    def test_clearing_a_sequence_with_work_done(self) -> None:
        """Requirement: Task forms (a sequence cleared on a task with a
        step done)."""
        self.create(sequence="SEQ-0002", started="2025-03-01")
        task = self.only_task()
        self.change(task, steps_done="1")
        task = self.only_task()
        before = task_steps(task)
        self.refused(self.change(task, sequence="", steps_total="2"),
                     "sequence")
        self.assertEqual(task_steps(self.only_task()), before)

    def test_a_sequence_set_on_a_new_task_with_steps_done(self) -> None:
        """Requirement: Task forms (steps done with a new sequence)."""
        done = self.create(sequence="SEQ-0001", steps_done="1",
                           started="2025-03-01")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(
            [d is not None for d in done_days(self.only_task())],
            [True, False])

    def test_a_save_that_leaves_the_sequence_changes_no_step(self) -> None:
        """Requirement: Task record (a save that leaves the sequence as
        it was leaves the steps' entries and imports)."""
        self.create(sequence="SEQ-0002")
        task = self.only_task()
        before = task_steps(task)
        import_collection(changed_collection("OSDB-0009"))
        done = self.change(task, note="Nur eine Notiz")
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task_steps(task), before)
        self.assertEqual(task.note, "Nur eine Notiz")


class ConsistencyTests(FormCase):
    """The review's cases: the posted form under the locks, the admin
    and the history of a step's position."""

    def test_a_posted_form_holds_the_import_lock(self) -> None:
        """Requirement: Task record (the steps of a sequence carry the
        latest accepted import, read under the import lock with them)."""
        from unittest import mock
        task = make_task(self.kl, substance="Probe")
        with mock.patch("orgsyndb_web.lock.hold") as hold:
            done = self.client.post(task_url(task, "edit"),
                                    edit_data(task, note="locked"))
        self.assertEqual(done.status_code, 302)
        self.assertTrue(hold.called)

    def test_the_admin_shows_the_sequence_and_steps_read_only(
            self) -> None:
        """Requirement: Task forms (only the task form changes a task's
        sequence and steps, so its rules hold)."""
        from . import make_user
        staff = make_user("boss", "BO", is_staff=True, is_superuser=True)
        task = make_task(self.kl, substance="Probe", steps=2)
        self.client.force_login(staff)
        html = self.client.get(
            f"/lab/admin/tasks/task/{task.pk}/change/").content.decode()
        self.assertNotIn('name="sequence"', html)
        self.assertNotIn('name="steps-0-done_on"', html)
        self.assertNotIn('name="steps-0-position"', html)

    def test_a_position_change_shows_in_the_history(self) -> None:
        """Requirement: Task page (the history lists the steps'
        changes)."""
        task = make_task(self.kl, substance="Probe", steps=2)
        last = task.steps.get(position=2)
        last.position = 3
        last.save()
        text = history_text(page(self.client.get(task_url(task))))
        self.assertIn("Stufe 3", text)


class ProductLotTests(FormCase):
    """Requirement: Task record (a task that is ended and has not failed
    has a batch and a product lot, and a save that would end one without
    them is refused) and Task forms."""

    def running(self, **fields) -> Task:
        return make_task(self.kl, "Aspirin", started=past(1), steps=2,
                         **fields)

    def refused_at(self, response, *fields: str) -> None:
        """The form is shown again with an error at one of ``fields``."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(any(name in errors for name in fields),
                        f"no error at {fields}: {sorted(errors)}")

    def test_ending_needs_a_product_lot(self) -> None:
        """Scenario: Ending needs a product lot (through the form)."""
        task = self.running(batch="B-7")
        done = self.change(task, ended="2025-03-04")
        self.refused_at(done, "ended", "batch")
        task.refresh_from_db()
        self.assertIsNone(task.ended)
        self.assertEqual(task.history.count(), 1)
        make_product_lot(task)
        done = self.change(task, ended="2025-03-04")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual((task.ended, task.state), (past(4), "ended"))

    def test_ending_needs_a_batch(self) -> None:
        task = self.running()
        make_product_lot(task, batch="")
        self.refused_at(self.change(task, ended="2025-03-04"), "ended",
                        "batch")
        task.refresh_from_db()
        self.assertIsNone(task.ended)

    def test_only_a_made_lot_of_the_substance_and_the_batch_counts(
            self) -> None:
        """Requirement: Task record (a made lot of its substance whose
        batch is the task's batch)."""
        task = self.running(batch="B-7")
        make_product_lot(task, source="bought", supplier="Sigma")
        make_product_lot(task, substance=substance_for("Probe"))
        make_product_lot(task, batch="B-8")
        self.refused_at(self.change(task, ended="2025-03-04"), "ended",
                        "batch")
        task.refresh_from_db()
        self.assertIsNone(task.ended)

    def test_a_new_task_that_ended_needs_its_lot_too(self) -> None:
        data = task_form_data(started="2025-03-01", ended="2025-03-04",
                              batch="B-7")
        self.refused_at(self.client.post(NEW, data), "ended", "batch")
        self.assertEqual(Task.objects.count(), 0)
        make_lot(self.kl, substance=substance_for("Aspirin"), batch="B-7")
        self.assertEqual(self.client.post(NEW, data).status_code, 302)
        self.assertEqual(self.only_task().state, "ended")

    def test_a_task_not_ended_needs_no_lot(self) -> None:
        task = self.running(batch="B-7")
        done = self.change(task, note="Notiz")
        self.assertEqual(done.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.note, "Notiz")


class FailedTaskTests(FormCase):
    """Requirement: Task forms (failed, on the edit form only; a batch on
    a failed task is invalid) and Task record."""

    def running(self, **fields) -> Task:
        return make_task(self.kl, "Aspirin", started=past(1), steps=2,
                         **fields)

    def test_a_task_is_failed_through_the_form(self) -> None:
        task = self.running()
        done = self.change(task, ended="2025-03-04", failed="on")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual((task.state, task.batch, task.ended),
                         ("failed", "", past(4)))
        self.assertFalse(task.needs_follow_up)
        text = page(self.client.get(task_url(task))).text()
        self.assertIn("Fehlgeschlagen", text)

    def test_a_failed_task_needs_no_product_lot(self) -> None:
        """Requirement: Task record (a task that is ended and has not
        failed has a batch and a product lot)."""
        task = self.running()
        self.change(task, ended="2025-03-04", failed="on")
        task = Task.objects.get(pk=task.pk)
        done = self.change(task, note="Notiz")
        self.assertEqual(done.status_code, 302)
        task.refresh_from_db()
        self.assertEqual((task.note, task.state), ("Notiz", "failed"))

    def test_a_batch_on_a_failed_task_is_refused(self) -> None:
        """Requirement: Task forms (a batch on a failed task)."""
        task = self.running(batch="B-8")
        done = self.change(task, ended="2025-03-04", failed="on")
        self.assertEqual(done.status_code, 200)
        errors = context_form(done).errors
        self.assertTrue("batch" in errors or "failed" in errors,
                        sorted(errors))
        task.refresh_from_db()
        self.assertEqual((task.failed, task.batch, task.ended),
                         (False, "B-8", None))
        self.assertEqual(task.history.count(), 1)

    def test_the_flag_can_be_turned_off(self) -> None:
        task = self.running()
        self.change(task, ended="2025-03-04", failed="on")
        task = Task.objects.get(pk=task.pk)
        data = edit_data(task, ended="")
        del data["failed"]
        self.assertEqual(self.client.post(
            task_url(task, "edit"), data).status_code, 302)
        task.refresh_from_db()
        self.assertEqual((task.failed, task.state), (False, "running"))

    def test_the_new_form_has_no_failed_flag(self) -> None:
        self.client.post(NEW, task_form_data(failed="on"))
        self.assertFalse(self.only_task().failed)
