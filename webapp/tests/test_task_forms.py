"""Tests of the task forms (task-tracker: Task forms, Steps from a
sequence)."""

from django.test import TestCase

from tasks.models import Task

from . import (IndexMixin, build_index, context_form, demo_index,
               edit_data, field_value, make_task, make_user, page, past,
               procedure, sent_messages, sequence, substance_for,
               task_form_data, task_url)

NEW = "/lab/tasks/new/"
FIELDS = {"substance", "priority", "assignee", "started", "ended", "sequence",
          "steps_total", "steps_done", "batch", "report", "qc_list",
          "note"}


class FormCase(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")

    def setUp(self) -> None:
        self.use_index(demo_index())
        self.client.force_login(self.kl)
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
        self.use_index(build_index("en"))
        done = self.client.post(NEW, task_form_data(), follow=True)
        number = self.only_task().number
        self.assertIn(f"Task {number} saved.", page(done).text())

    def test_all_fields_are_saved(self) -> None:
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
        self.assertEqual((task.steps_total, task.steps_done), (5, 3))
        self.assertEqual(task.batch, "B-9")
        self.assertTrue(task.report)
        self.assertTrue(task.qc_list)
        self.assertFalse(task.cancelled)
        self.assertIn("Zeile zwei", task.note)
        self.assertEqual(task.state, "ended")

    def test_steps_done_defaults_to_zero(self) -> None:
        self.client.post(NEW, task_form_data(steps_total="4"))
        task = self.only_task()
        self.assertEqual((task.steps_total, task.steps_done), (4, 0))

    def test_without_a_total_steps_done_is_zero(self) -> None:
        self.client.post(NEW, task_form_data())
        task = self.only_task()
        self.assertIsNone(task.steps_total)
        self.assertEqual(task.steps_done, 0)

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(NEW))
        form = root.find("input", name="substance").closest("form")
        names = {e.get("name") for e in
                 form.find_all(("input", "select", "textarea"))}
        names.discard("csrfmiddlewaretoken")
        self.assertEqual(names, FIELDS)

    def test_cancelled_is_on_the_edit_form_only(self) -> None:
        task = make_task(self.kl)
        root = page(self.client.get(task_url(task, "edit")))
        form = root.find("input", name="substance").closest("form")
        names = {e.get("name") for e in
                 form.find_all(("input", "select", "textarea"))}
        names.discard("csrfmiddlewaretoken")
        self.assertEqual(names, FIELDS | {"cancelled"})

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
        self.client.post(NEW, task_form_data(
            started="2025-03-04", ended="2025-03-04"))
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
        for value in ("0", "-1", "two"):
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
                         steps_total=5, steps_done=2, batch="B-9",
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
                         report=True, qc_list=True)
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


class SequenceTests(FormCase):

    def test_steps_from_a_sequence(self) -> None:
        """Scenario: Steps from a sequence."""
        done = self.client.post(NEW, task_form_data(
            sequence="SEQ-0001", steps_total="7"))
        self.assertEqual(done.status_code, 302)
        task = self.only_task()
        self.assertEqual(task.steps_total, 2)
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0001", "OSDB-0002"])
        self.assertEqual(task.sequence, "SEQ-0001")

    def test_steps_from_a_sequence_without_a_posted_total(self) -> None:
        self.client.post(NEW, task_form_data(sequence="SEQ-0002"))
        task = self.only_task()
        self.assertEqual(task.steps_total, 2)
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0004", "OSDB-0009"])

    def test_steps_done_is_bounded_by_the_steps_of_the_sequence(
            self) -> None:
        done = self.client.post(NEW, task_form_data(
            sequence="SEQ-0001", steps_done="3"))
        self.refused(done, "steps_done")
        self.assertEqual(Task.objects.count(), 0)

    def test_a_sequence_the_index_lacks(self) -> None:
        done = self.client.post(NEW, task_form_data(sequence="SEQ-9999"))
        self.refused(done, "sequence")
        self.assertEqual(Task.objects.count(), 0)

    def test_without_an_index_no_sequence_can_be_chosen(self) -> None:
        self.use_index(None)
        done = self.client.post(NEW, task_form_data(sequence="SEQ-0001"))
        self.refused(done, "sequence")
        self.assertEqual(Task.objects.count(), 0)
        done = self.client.post(NEW, task_form_data(steps_total="3"))
        self.assertEqual(done.status_code, 302)

    def test_changing_the_sequence_reads_the_new_steps(self) -> None:
        self.client.post(NEW, task_form_data(sequence="SEQ-0001"))
        task = self.only_task()
        done = self.client.post(task_url(task, "edit"), edit_data(
            task, sequence="SEQ-0002"))
        self.assertEqual(done.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.sequence, "SEQ-0002")
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0004", "OSDB-0009"])
        self.assertEqual(task.steps_total, 2)

    def test_clearing_the_sequence_clears_the_steps(self) -> None:
        self.client.post(NEW, task_form_data(sequence="SEQ-0001"))
        task = self.only_task()
        self.client.post(task_url(task, "edit"), edit_data(
            task, sequence="", steps_total="3"))
        task.refresh_from_db()
        self.assertFalse(task.sequence)
        self.assertEqual(list(task.sequence_steps), [])
        self.assertEqual(task.steps_total, 3)

    def test_an_edit_that_leaves_the_sequence_reads_nothing(self) -> None:
        self.client.post(NEW, task_form_data(sequence="SEQ-0001"))
        task = self.only_task()
        self.use_index(build_index(
            "de", procedures=[procedure("OSDB-0003")],
            sequences=[sequence("SEQ-0001", ["OSDB-0003"])]))
        done = self.client.post(task_url(task, "edit"), edit_data(
            task, note="Nur eine Notiz"))
        self.assertEqual(done.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0001", "OSDB-0002"])
        self.assertEqual(task.steps_total, 2)
        self.assertEqual(task.note, "Nur eine Notiz")

    def test_sequence_gone_from_the_collection(self) -> None:
        """Scenario: Sequence gone from the collection."""
        self.client.post(NEW, task_form_data(
            sequence="SEQ-0001", started="2025-03-01",
            ended="2025-03-02"))
        task = self.only_task()
        self.use_index(build_index("de"))
        done = self.client.post(task_url(task, "edit"), edit_data(
            task, report="on"))
        self.assertEqual(done.status_code, 302)
        task.refresh_from_db()
        self.assertTrue(task.report)
        self.assertEqual(task.steps_total, 2)
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0001", "OSDB-0002"])
        self.assertEqual(task.sequence, "SEQ-0001")

    def test_sequence_gone_and_the_report_button(self) -> None:
        self.client.post(NEW, task_form_data(
            sequence="SEQ-0001", started="2025-03-01",
            ended="2025-03-02"))
        task = self.only_task()
        self.use_index(None)
        self.client.post(task_url(task, "report"))
        task.refresh_from_db()
        self.assertTrue(task.report)
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0001", "OSDB-0002"])

    def test_actions_read_nothing_from_the_index(self) -> None:
        self.client.post(NEW, task_form_data(sequence="SEQ-0001"))
        task = self.only_task()
        self.use_index(None)
        self.client.post(task_url(task, "start"))
        self.client.post(task_url(task, "step"))
        task.refresh_from_db()
        self.assertEqual(task.steps_done, 1)
        self.assertEqual(task.steps_total, 2)
        self.assertEqual(list(task.sequence_steps),
                         ["OSDB-0001", "OSDB-0002"])
