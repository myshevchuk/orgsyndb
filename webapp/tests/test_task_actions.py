"""Tests of the buttons on the task page (task-tracker: Task actions)."""

from datetime import date, datetime, timezone

from django.contrib import messages

from . import (berlin, done_days, frozen, make_task, page, past,
               sent_messages, substance_for, task_steps, task_url)
from .collection_support import accept
from .task_support import TaskCase, history_text, make_product_lot

ACTIONS = ("start", "step", "end", "fail", "report", "qc-list")
LABELS_DE = {"start": "Beginnen", "step": "Stufe erledigt",
             "end": "Abschließen", "fail": "Fehlgeschlagen",
             "report": "Bericht erledigt", "qc-list": "Auf QC-Liste"}
LABELS_EN = {"start": "Start", "step": "Step done", "end": "End",
             "fail": "Failed", "report": "Report done",
             "qc-list": "On QC list"}
TODAY = date(2026, 11, 4)


class ActionCase(TaskCase):

    def act(self, task, action: str, moment=None):
        with frozen(moment or berlin(2026, 11, 4)):
            return self.client.post(task_url(task, action))

    def offered(self, task) -> dict:
        root = page(self.client.get(task_url(task)))
        prefix = task_url(task)
        found = {}
        for form in root.find_all("form"):
            action = form.get("action", "")
            if action.startswith(prefix) and action != task_url(
                    task, "edit"):
                self.assertEqual(form.get("method", "").lower(), "post")
                found[action[len(prefix):].strip("/")] = form
        return found


class StartTests(ActionCase):

    def test_start_sets_today(self) -> None:
        task = make_task(self.kl)
        done = self.act(task, "start")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual(task.started, TODAY)
        self.assertEqual(task.state, "running")
        self.assertEqual(len(sent_messages(done)), 1)
        self.assertNotEqual(sent_messages(done)[0].level, messages.ERROR)

    def test_the_message_shows_on_the_page(self) -> None:
        task = make_task(self.kl)
        done = self.act(task, "start")
        text = sent_messages(done)[0].message
        shown = self.client.get(task_url(task))
        self.assertIn(text, page(shown).text())

    def test_today_is_the_date_in_berlin(self) -> None:
        task = make_task(self.kl)
        late = datetime(2026, 11, 3, 23, 30, tzinfo=timezone.utc)
        self.act(task, "start", late)
        task.refresh_from_db()
        self.assertEqual(task.started, TODAY)

    def test_the_change_is_recorded(self) -> None:
        task = make_task(self.kl)
        self.act(task, "start")
        newest = task.history.first()
        self.assertEqual(newest.history_type, "~")
        self.assertEqual(newest.history_user, self.kl)
        self.assertEqual(newest.started, TODAY)

    def test_start_does_not_apply_to_other_states(self) -> None:
        for state, fields in (
                ("running", {"started": past(1)}),
                ("ended", {"started": past(1), "ended": past(2)}),
                ("cancelled", {"cancelled": True})):
            with self.subTest(state=state):
                task = make_task(self.kl, **fields)
                before = (task.started, task.ended, task.history.count())
                done = self.act(task, "start")
                self.assertRedirects(done, task_url(task),
                                     fetch_redirect_response=False)
                task.refresh_from_db()
                self.assertEqual(
                    (task.started, task.ended, task.history.count()),
                    before)
                self.assertEqual(sent_messages(done)[0].level,
                                 messages.ERROR)


class StepTests(ActionCase):

    def test_step_marks_the_first_open_step_done_today(self) -> None:
        """Requirement: Task actions (`step` marks its first step not
        done as done today)."""
        task = make_task(self.kl, started=past(1), steps=3)
        done = self.act(task, "step")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        self.assertEqual(done_days(task), [TODAY, None, None])
        self.assertNotEqual(sent_messages(done)[0].level, messages.ERROR)
        self.act(task, "step", berlin(2026, 11, 5))
        self.assertEqual(done_days(task),
                         [TODAY, date(2026, 11, 5), None])

    def test_step_skips_the_steps_done(self) -> None:
        """Requirement: Task actions (its first such step)."""
        task = make_task(self.kl, started=past(1), steps=3)
        task.steps.filter(position=1).update(done_on=past(2))
        task.steps.filter(position=3).update(done_on=past(3))
        self.act(task, "step")
        self.assertEqual(done_days(task), [past(2), TODAY, past(3)])

    def test_the_change_is_recorded_in_the_steps_history(self) -> None:
        """Requirement: Task actions (records the change in its
        history)."""
        task = make_task(self.kl, started=past(1), steps=2)
        self.act(task, "step")
        first = task.steps.get(position=1)
        newest = first.history.first()
        self.assertEqual((newest.history_type, newest.done_on,
                          newest.history_user), ("~", TODAY, self.kl))
        self.assertEqual(task.steps.get(position=2).history.count(), 1)

    def test_action_out_of_state(self) -> None:
        """Scenario: Action out of state."""
        task = make_task(self.kl, steps=2)
        before = task.history.count()
        step_records = sum(s.history.count() for s in task.steps.all())
        done = self.act(task, "step")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual(done_days(task), [None, None])
        self.assertIsNone(task.started)
        self.assertEqual(task.history.count(), before)
        self.assertEqual(
            sum(s.history.count() for s in task.steps.all()), step_records)
        error = sent_messages(done)
        self.assertEqual([m.level for m in error], [messages.ERROR])
        shown = page(self.client.get(task_url(task)))
        self.assertIn(error[0].message, shown.text())

    def test_step_needs_a_step_left(self) -> None:
        task = make_task(self.kl, started=past(1), steps=2, done=2)
        done = self.act(task, "step")
        self.assertEqual(done_days(task), [past(2), past(2)])
        self.assertEqual(sent_messages(done)[0].level, messages.ERROR)

    def test_step_needs_steps(self) -> None:
        task = make_task(self.kl, started=past(1))
        done = self.act(task, "step")
        self.assertEqual(task.steps.count(), 0)
        self.assertEqual(sent_messages(done)[0].level, messages.ERROR)

    def test_step_does_not_apply_to_ended_or_cancelled_tasks(self) -> None:
        for fields in ({"ended": past(2)}, {"cancelled": True}):
            with self.subTest(fields=fields):
                task = make_task(self.kl, started=past(1), steps=3,
                                 done=1, **fields)
                self.act(task, "step")
                self.assertEqual(done_days(task),
                                 [past(2), None, None])

    def test_step_on_a_task_with_a_sequence(self) -> None:
        """Requirement: Task actions (the steps of a sequence)."""
        self.create(sequence="SEQ-0002", started="2025-03-01")
        task = self.only_task()
        self.act(task, "step")
        self.assertEqual(task_steps(task), [
            (("OSDB-0004", 1), self.first, TODAY),
            (("OSDB-0009", 1), self.first, None)])


class EndTests(ActionCase):

    def test_end_completes_the_open_steps(self) -> None:
        """Requirement: Task actions (`end` marks every step not done as
        done today)."""
        task = make_task(self.kl, started=past(1), steps=4, done=1,
                         batch="B-7")
        make_product_lot(task)
        done = self.act(task, "end", berlin(2026, 11, 6))
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual(task.ended, date(2026, 11, 6))
        self.assertEqual(done_days(task), [past(2)] + [date(2026, 11, 6)] * 3)
        self.assertEqual(task.state, "ended")
        self.assertEqual(task.progress, 100)

    def test_end_without_steps(self) -> None:
        task = make_task(self.kl, started=past(1), batch="B-7")
        make_product_lot(task)
        self.act(task, "end")
        task.refresh_from_db()
        self.assertEqual(task.ended, TODAY)
        self.assertEqual(task.steps.count(), 0)
        self.assertIsNone(task.progress)

    def test_end_does_not_apply_to_other_states(self) -> None:
        for fields in ({}, {"started": past(1), "ended": past(2)},
                       {"started": past(1), "cancelled": True}):
            with self.subTest(fields=fields):
                task = make_task(self.kl, steps=3, **fields)
                before = (task.ended, done_days(task))
                done = self.act(task, "end")
                task.refresh_from_db()
                self.assertEqual((task.ended, done_days(task)), before)
                self.assertEqual(sent_messages(done)[0].level,
                                 messages.ERROR)

    def test_the_steps_changes_are_recorded(self) -> None:
        """Requirement: Task actions (records the change in its
        history)."""
        task = make_task(self.kl, started=past(1), steps=2, batch="B-7")
        make_product_lot(task)
        self.act(task, "end")
        for step in task.steps.all():
            with self.subTest(position=step.position):
                newest = step.history.first()
                self.assertEqual((newest.history_type, newest.history_user),
                                 ("~", self.kl))

    def test_steps_through_actions(self) -> None:
        """Scenario: Steps through actions."""
        with frozen(berlin(2026, 11, 3)):
            self.create(steps_total="2", batch="B-7")
        task = self.only_task()
        make_product_lot(task)
        self.act(task, "start", berlin(2026, 11, 4))
        self.act(task, "step", berlin(2026, 11, 5, 15))
        self.act(task, "end", berlin(2026, 11, 6))
        task.refresh_from_db()
        self.assertEqual(task.started, date(2026, 11, 4))
        self.assertEqual(task.ended, date(2026, 11, 6))
        self.assertEqual(done_days(task),
                         [date(2026, 11, 5), date(2026, 11, 6)])
        text = history_text(page(self.client.get(task_url(task))))
        for day in ("06.11.2026", "05.11.2026", "04.11.2026",
                    "03.11.2026"):
            with self.subTest(day=day):
                self.assertIn(day, text)
        positions = [text.index(day) for day in
                     ("06.11.2026", "05.11.2026", "04.11.2026",
                      "03.11.2026")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Stufe 1", text[text.index("05.11.2026"):
                                      text.index("04.11.2026")])
        self.assertIn("Stufe 2", text[:text.index("05.11.2026")])
        self.assertEqual(task.steps.get(position=1).history.count(), 2)
        self.assertEqual(task.steps.get(position=2).history.count(), 2)
        self.assertIn("Angelegt", text)


class ProductLotTests(ActionCase):
    """Requirement: Task record (a task that is ended and has not failed
    has a batch and a product lot) and Task actions (`end`)."""

    def running(self, **fields):
        return make_task(self.kl, "Aspirin", started=past(1), steps=2,
                         **fields)

    def test_ending_needs_a_product_lot(self) -> None:
        """Scenario: Ending needs a product lot."""
        task = self.running(batch="B-7")
        done = self.act(task, "end")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertIsNone(task.ended)
        self.assertEqual(task.state, "running")
        self.assertEqual(done_days(task), [None, None])
        self.assertEqual(task.history.count(), 1)
        self.assertEqual([m.level for m in sent_messages(done)],
                         [messages.ERROR])
        make_product_lot(task)
        self.act(task, "end")
        task.refresh_from_db()
        self.assertEqual(task.ended, TODAY)
        self.assertEqual(task.state, "ended")

    def test_ending_needs_a_batch(self) -> None:
        task = self.running()
        make_product_lot(task, batch="B-7")
        done = self.act(task, "end")
        task.refresh_from_db()
        self.assertIsNone(task.ended)
        self.assertEqual(sent_messages(done)[0].level, messages.ERROR)

    def test_only_a_made_lot_of_the_substance_and_the_batch_counts(
            self) -> None:
        """Requirement: Task record (a made lot of its substance whose
        batch is the task's batch)."""
        task = self.running(batch="B-7")
        make_product_lot(task, source="bought", supplier="Sigma")
        make_product_lot(task, substance=substance_for("Probe"))
        make_product_lot(task, batch="B-8")
        make_product_lot(task, batch="B-77")
        self.act(task, "end")
        task.refresh_from_db()
        self.assertIsNone(task.ended)

    def test_a_lot_of_a_step_with_another_batch_is_no_product_lot(
            self) -> None:
        task = self.running(batch="B-7")
        make_product_lot(task, batch="B-8", task_step=task.steps.first())
        self.act(task, "end")
        task.refresh_from_db()
        self.assertIsNone(task.ended)


class FailTests(ActionCase):

    def running(self, **fields):
        return make_task(self.kl, "Aspirin", started=past(1), steps=2,
                         done=1, **fields)

    def test_a_failed_synthesis(self) -> None:
        """Scenario: A failed synthesis."""
        task = self.running(batch="B-8")
        done = self.act(task, "fail")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertEqual((task.ended, task.batch, task.failed),
                         (TODAY, "", True))
        self.assertEqual(task.state, "failed")
        self.assertFalse(task.needs_follow_up)
        self.assertEqual(len(sent_messages(done)), 1)
        self.assertNotEqual(sent_messages(done)[0].level, messages.ERROR)

    def test_the_steps_stay_as_they_are(self) -> None:
        """Requirement: Task actions (`fail` leaves its steps as they
        are)."""
        task = self.running(batch="B-8")
        self.act(task, "fail")
        task.refresh_from_db()
        self.assertEqual(task.ended, TODAY)
        self.assertEqual(done_days(task), [past(2), None])

    def test_a_task_without_a_batch_fails_too(self) -> None:
        task = self.running()
        self.act(task, "fail")
        task.refresh_from_db()
        self.assertEqual((task.failed, task.batch, task.ended),
                         (True, "", TODAY))

    def test_the_change_is_recorded(self) -> None:
        """Requirement: Task actions (records the change in its
        history)."""
        task = self.running(batch="B-8")
        self.act(task, "fail")
        newest = task.history.first()
        self.assertEqual((newest.history_type, newest.history_user,
                          newest.failed, newest.batch, newest.ended),
                         ("~", self.kl, True, "", TODAY))

    def test_the_page_shows_the_state(self) -> None:
        task = self.running(batch="B-8")
        self.act(task, "fail")
        text = page(self.client.get(task_url(task))).text()
        self.assertIn("Fehlgeschlagen", text)
        self.assertNotIn("Nacharbeit", text)

    def test_a_task_with_a_product_lot_cannot_fail(self) -> None:
        """Requirement: Task actions (`fail` on a running task without a
        product lot)."""
        task = self.running(batch="B-8")
        make_product_lot(task)
        done = self.act(task, "fail")
        task.refresh_from_db()
        self.assertEqual((task.failed, task.batch, task.ended),
                         (False, "B-8", None))
        self.assertEqual(task.history.count(), 1)
        self.assertEqual([m.level for m in sent_messages(done)],
                         [messages.ERROR])

    def test_fail_does_not_apply_to_other_states(self) -> None:
        for state, fields in (
                ("planned", {}),
                ("ended", {"started": past(1), "ended": past(2),
                           "failed": True}),
                ("cancelled", {"started": past(1), "cancelled": True})):
            with self.subTest(state=state):
                task = make_task(self.kl, "Aspirin", batch="B-8",
                                 **fields)
                before = (task.failed, task.batch, task.ended,
                          task.history.count())
                done = self.act(task, "fail")
                self.assertRedirects(done, task_url(task),
                                     fetch_redirect_response=False)
                task.refresh_from_db()
                self.assertEqual((task.failed, task.batch, task.ended,
                                  task.history.count()), before)
                self.assertEqual(sent_messages(done)[-1].level,
                                 messages.ERROR)

    def test_an_ended_task_that_has_not_failed_cannot_fail(self) -> None:
        task = make_task(self.kl, "Aspirin", started=past(1),
                         ended=past(2), batch="B-8")
        self.act(task, "fail")
        task.refresh_from_db()
        self.assertFalse(task.failed)
        self.assertEqual(task.batch, "B-8")

    def test_no_action_applies_to_a_failed_task(self) -> None:
        task = self.running(batch="B-8")
        self.act(task, "fail")
        for action in ("start", "step", "end", "fail", "report",
                       "qc-list"):
            with self.subTest(action=action):
                done = self.act(task, action)
                self.assertEqual(sent_messages(done)[-1].level,
                                 messages.ERROR)
        self.assertEqual(set(self.offered(task)), set())


class FlagTests(ActionCase):

    def test_report_and_qc_list_set_their_flags(self) -> None:
        task = make_task(self.kl, started=past(1), ended=past(2))
        done = self.act(task, "report")
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        task.refresh_from_db()
        self.assertTrue(task.report)
        self.assertFalse(task.qc_list)
        self.assertTrue(task.needs_follow_up)
        self.act(task, "qc-list")
        task.refresh_from_db()
        self.assertTrue(task.qc_list)
        self.assertFalse(task.needs_follow_up)
        self.assertEqual(task.history.filter(history_type="~").count(), 2)

    def test_flag_actions_need_an_ended_task_with_the_flag_off(self) -> None:
        cases = [({}, "report"), ({"started": past(1)}, "qc-list"),
                 ({"started": past(1), "ended": past(2), "report": True},
                  "report"),
                 ({"started": past(1), "ended": past(2), "qc_list": True},
                  "qc-list"),
                 ({"started": past(1), "ended": past(2),
                   "cancelled": True}, "report")]
        for fields, action in cases:
            with self.subTest(fields=fields, action=action):
                task = make_task(self.kl, **fields)
                before = (task.report, task.qc_list, task.history.count())
                done = self.act(task, action)
                task.refresh_from_db()
                self.assertEqual(
                    (task.report, task.qc_list, task.history.count()),
                    before)
                self.assertEqual(sent_messages(done)[0].level,
                                 messages.ERROR)


class ButtonTests(ActionCase):

    def test_the_actions_that_apply_are_offered(self) -> None:
        cases = [
            ({}, {"start"}),
            ({"started": past(1), "steps": 2}, {"step", "fail"}),
            ({"started": past(1), "steps": 2, "done": 2}, {"fail"}),
            ({"started": past(1)}, {"fail"}),
            ({"started": past(1), "steps": 2, "batch": "B-7",
              "lot": True}, {"step", "end"}),
            ({"started": past(1), "batch": "B-7", "lot": True}, {"end"}),
            ({"started": past(1), "ended": past(2)},
             {"report", "qc-list"}),
            ({"started": past(1), "ended": past(2), "report": True},
             {"qc-list"}),
            ({"started": past(1), "ended": past(2), "qc_list": True},
             {"report"}),
            ({"started": past(1), "ended": past(2), "report": True,
              "qc_list": True}, set()),
            ({"cancelled": True}, set()),
            ({"started": past(1), "cancelled": True}, set()),
            ({"started": past(1), "ended": past(2), "failed": True},
             set()),
        ]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                fields = dict(fields)
                lot = fields.pop("lot", False)
                task = make_task(self.kl, **fields)
                if lot:
                    make_product_lot(task)
                self.assertEqual(set(self.offered(task)), expected)

    def stocked(self):
        """A running task with a batch and its product lot."""
        task = make_task(self.kl, started=past(1), steps=2, batch="B-7")
        make_product_lot(task)
        return task

    def test_buttons_are_labelled(self) -> None:
        task = make_task(self.kl, started=past(1), steps=2)
        planned = make_task(self.kl)
        ended = make_task(self.kl, started=past(1), ended=past(2))
        for shown in (self.offered(task), self.offered(planned),
                      self.offered(ended), self.offered(self.stocked())):
            for action, form in shown.items():
                with self.subTest(action=action):
                    self.assertEqual(form.find("button").text(),
                                     LABELS_DE[action])

    def test_buttons_are_labelled_in_english(self) -> None:
        accept(language="en")
        task = make_task(self.kl, started=past(1), steps=2)
        ended = make_task(self.kl, started=past(1), ended=past(2))
        shown = {**self.offered(task), **self.offered(ended),
                 **self.offered(make_task(self.kl)),
                 **self.offered(self.stocked())}
        self.assertEqual(set(shown), set(ACTIONS))
        for action, form in shown.items():
            with self.subTest(action=action):
                self.assertEqual(form.find("button").text(),
                                 LABELS_EN[action])

    def test_nothing_is_offered_without_a_sign_in(self) -> None:
        tasks = [make_task(self.kl), make_task(self.kl, started=past(1)),
                 make_task(self.kl, started=past(1), ended=past(2))]
        self.client.logout()
        for task in tasks:
            with self.subTest(task=task.number):
                self.assertEqual(self.offered(task), {})


class ConcurrencyTests(ActionCase):

    def test_an_action_writes_only_its_own_fields(self) -> None:
        """A change committed between an action's read and its save
        survives the save."""
        from dataclasses import replace
        from unittest import mock

        from tasks import views
        from tasks.models import Task
        task = make_task(self.kl, started=past(1), ended=past(2))
        report = views.ACTIONS["report"]

        def meanwhile(current):
            Task.objects.filter(pk=current.pk).update(qc_list=True)
            return report.change(current)

        with mock.patch.dict(views.ACTIONS,
                             {"report": replace(report, change=meanwhile)}):
            self.act(task, "report")
        task.refresh_from_db()
        self.assertTrue(task.report)
        self.assertTrue(task.qc_list)
