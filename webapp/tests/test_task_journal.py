"""Tests of a task step's journal entry (task-tracker: Task record, Task
page, Task forms)."""

from typing import Any

from django.test import TestCase

from tasks.models import Task, TaskStep

from . import (context_form, field_value, make_task, page, past,
               sent_messages, task_url)
from .collection_support import (accept, by_id, demo_collection,
                                 import_collection)
from .demo_support import SeededCase
from .journal_support import entries_named, entry_of, step_journal_url
from .task_support import TaskCase, history_text, steps_of
from .test_task_page import step_items


def hrefs(item: Any) -> list[str]:
    return [a.get("href") for a in item.find_all("a")]


def buttons(form: Any) -> list[str]:
    """The texts of the buttons that submit ``form``."""
    return [*(b.text() for b in form.find_all("button")
              if b.get("type", "submit") == "submit"),
            *(b.get("value") for b in form.find_all("input")
              if b.get("type") == "submit")]


def journal_links(item: Any) -> list[Any]:
    """The links of a step's list item to a notebook's page."""
    return [a for a in item.find_all("a")
            if a.get("href", "").startswith("/lab/journal/")]


class StepJournalCase(TaskCase):
    """A running task of ``aspirin`` with two plain steps, signed in as
    ``kl``."""

    def setUp(self) -> None:
        super().setUp()
        self.task = make_task(self.kl, "Aspirin", started=past(1), steps=2)
        self.first, self.second = steps_of(self.task)

    def post(self, step: Any, value: str) -> Any:
        return self.client.post(step_journal_url(step),
                                {"journal_entry": value})

    def named(self, step: Any) -> str | None:
        """The journal entry the step names now, written
        ``<code>/<number>``, or None."""
        found = TaskStep.objects.select_related(
            "journal_entry__notebook").get(pk=step.pk).journal_entry
        return None if found is None else str(found)


class StepRecordTests(StepJournalCase):
    """Requirement: Task record (a step's `journal_entry`)."""

    def test_a_step_names_no_entry_at_first(self) -> None:
        self.assertIsNone(self.named(self.first))

    def test_a_step_names_an_entry(self) -> None:
        entry = entry_of("AE-1/9")
        TaskStep.objects.filter(pk=self.first.pk).update(
            journal_entry=entry)
        self.assertEqual(self.named(self.first), "AE-1/9")
        self.assertEqual(list(entry.task_steps.all()),
                         [TaskStep.objects.get(pk=self.first.pk)])

    def test_the_entry_is_in_the_steps_history(self) -> None:
        """Requirement: Task record (tasks and their steps keep a change
        history)."""
        entry = entry_of("AE-1/9")
        step = TaskStep.objects.get(pk=self.first.pk)
        step.journal_entry = entry
        step._history_user = self.kl
        step.save()
        newest = step.history.order_by("-history_id").first()
        self.assertEqual(newest.history_type, "~")
        self.assertEqual(newest.journal_entry_id, entry.pk)


class SetByPostTests(StepJournalCase):
    """Requirement: Task page (a value `<code>/<number>` whose code is a
    notebook's makes the step name that entry)."""

    def test_a_value_makes_the_step_name_the_entry(self) -> None:
        done = self.post(self.second, "CE-3/5")
        self.assertRedirects(done, task_url(self.task),
                             fetch_redirect_response=False)
        self.assertEqual(self.named(self.second), "CE-3/5")
        self.assertEqual(entries_named("CE-3/5"), 1)
        self.assertIsNone(self.named(self.first))

    def test_the_message(self) -> None:
        """Requirement: Task page (`Laborjournal von Stufe <n>
        gespeichert.`)."""
        done = self.post(self.second, "CE-3/5")
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Laborjournal von Stufe 2 gespeichert."])

    def test_the_message_in_english(self) -> None:
        """Requirement: Task page (`Lab notebook of step <n> saved.`)."""
        accept(language="en")
        done = self.post(self.first, "CE-3/5")
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Lab notebook of step 1 saved."])

    def test_the_change_is_recorded_in_the_history(self) -> None:
        """Requirement: Task page (the change recorded in the step's
        history)."""
        self.post(self.second, "CE-3/5")
        step = TaskStep.objects.get(pk=self.second.pk)
        newest = step.history.order_by("-history_id").first()
        self.assertEqual(
            (newest.history_type, newest.history_user, newest.position),
            ("~", self.kl, 2))
        self.assertEqual(newest.journal_entry_id, step.journal_entry_id)

    def test_the_history_shows_the_change(self) -> None:
        """Requirement: Task page (the change history lists the steps'
        changes)."""
        self.post(self.second, "CE-3/5")
        text = history_text(page(self.client.get(task_url(self.task))))
        self.assertIn("Stufe 2", text)
        self.assertIn("CE-3/5", text)

    def test_the_page_shows_the_entry_under_the_step(self) -> None:
        """Requirement: Task page (`Laborjournal <entry>` linking to the
        notebook's page)."""
        self.post(self.second, "CE-3/5")
        root = page(self.client.get(task_url(self.task)))
        first, second = step_items(root)
        self.assertEqual(journal_links(first), [])
        links = journal_links(second)
        self.assertEqual([a.text() for a in links],
                         ["Laborjournal CE-3/5"])
        self.assertEqual(hrefs(second).count("/lab/journal/CE-3/"), 1)

    def test_the_entry_in_english(self) -> None:
        """Requirement: Task page (`Lab notebook <entry>`)."""
        self.post(self.second, "CE-3/5")
        accept(language="en")
        second = step_items(page(self.client.get(task_url(self.task))))[1]
        self.assertEqual([a.text() for a in journal_links(second)],
                         ["Lab notebook CE-3/5"])

    def test_another_value_replaces_the_entry(self) -> None:
        self.post(self.second, "CE-3/5")
        self.post(self.second, "AE-1/2")
        self.assertEqual(self.named(self.second), "AE-1/2")
        self.assertEqual(entries_named("CE-3/5"), 1)

    def test_an_empty_value_makes_the_step_name_none(self) -> None:
        """Requirement: Task page (an empty value makes it name none)."""
        self.post(self.second, "CE-3/5")
        self.client.get(task_url(self.task))
        done = self.post(self.second, "")
        self.assertRedirects(done, task_url(self.task),
                             fetch_redirect_response=False)
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Laborjournal von Stufe 2 gespeichert."])
        self.assertIsNone(self.named(self.second))
        self.assertEqual(entries_named("CE-3/5"), 1)
        step = TaskStep.objects.get(pk=self.second.pk)
        newest = step.history.order_by("-history_id").first()
        self.assertEqual((newest.history_type, newest.journal_entry_id),
                         ("~", None))

    def test_two_steps_may_name_one_entry(self) -> None:
        self.post(self.first, "CE-3/5")
        self.post(self.second, "CE-3/5")
        self.assertEqual(entries_named("CE-3/5"), 1)
        self.assertEqual(self.named(self.first), "CE-3/5")
        self.assertEqual(self.named(self.second), "CE-3/5")

    def test_whatever_the_state_of_the_task(self) -> None:
        """Requirement: Task page (whatever the task's state)."""
        planned = make_task(self.kl, "Aspirin", steps=1)
        cancelled = make_task(self.kl, "Aspirin", steps=1, cancelled=True)
        failed = make_task(self.kl, "Aspirin", started=past(2),
                           ended=past(1), steps=1, failed=True)
        for task in (planned, cancelled, failed):
            with self.subTest(task=task.number):
                (step,) = steps_of(task)
                done = self.post(step, "CE-3/6")
                self.assertRedirects(done, task_url(task),
                                     fetch_redirect_response=False)
                self.assertEqual(self.named(step), "CE-3/6")

    def test_an_unknown_step_answers_404(self) -> None:
        self.assertEqual(self.post(self.first, "CE-3/5").status_code, 302)
        done = self.client.post("/lab/tasks/steps/999999/journal/",
                                {"journal_entry": "CE-3/5"})
        self.assertEqual(done.status_code, 404)

    def test_a_sign_in_is_needed(self) -> None:
        """Requirement: Task page (for a signed-in user)."""
        self.client.logout()
        done = self.post(self.second, "CE-3/5")
        self.assertIn(done.status_code, (302, 403))
        self.assertIsNone(self.named(self.second))
        self.assertEqual(entries_named("CE-3/5"), 0)


class RefusedValueTests(StepJournalCase):
    """Requirement: Task page (any other value leads back with the error
    as a message and changes nothing)."""

    VALUES = ("ZZ-1/1", "CE-3", "CE-3/", "/5", "CE-3/0", "CE-3/05",
              "ce-3/5", "CE-3/x", "CE-3/5/6")

    def test_a_value_that_is_refused_leads_back_with_a_message(
            self) -> None:
        """Scenario: A step names an unknown notebook."""
        for value in self.VALUES:
            with self.subTest(value=value):
                done = self.post(self.second, value)
                self.assertRedirects(done, task_url(self.task),
                                     fetch_redirect_response=False)
                messages = [str(m) for m in sent_messages(done)]
                self.assertTrue(messages)
                self.assertNotIn("Laborjournal von Stufe 2 gespeichert.",
                                 messages)
                self.assertIsNone(self.named(self.second))

    def test_nothing_is_created(self) -> None:
        from journal.models import Entry
        before = Entry.objects.count()
        for value in self.VALUES:
            self.post(self.second, value)
        self.assertEqual(Entry.objects.count(), before)

    def test_the_step_keeps_the_entry_it_names(self) -> None:
        self.post(self.second, "CE-3/5")
        before = TaskStep.objects.get(pk=self.second.pk).history.count()
        for value in self.VALUES:
            self.post(self.second, value)
        self.assertEqual(self.named(self.second), "CE-3/5")
        self.assertEqual(
            TaskStep.objects.get(pk=self.second.pk).history.count(),
            before)


class StepFormOnThePageTests(StepJournalCase):
    """Requirement: Task page (a form per step, for a signed-in user,
    posting `journal_entry` to `/lab/tasks/steps/<id>/journal/`)."""

    def form_of(self, item: Any) -> Any:
        control = item.find(("input", "select", "textarea"),
                            name="journal_entry")
        self.assertIsNotNone(control, "the step has no journal form")
        return control.closest("form")

    def test_each_step_has_a_form_of_its_own(self) -> None:
        root = page(self.client.get(task_url(self.task)))
        for step, item in zip((self.first, self.second), step_items(root),
                              strict=True):
            with self.subTest(step=step.position):
                form = self.form_of(item)
                self.assertEqual(form.get("action"),
                                 step_journal_url(step))
                self.assertEqual(form.get("method", "").lower(), "post")

    def test_the_field_and_the_button(self) -> None:
        """Requirement: Task page (a field `Laborjournal` and a button
        `Speichern`)."""
        item = step_items(page(self.client.get(task_url(self.task))))[0]
        form = self.form_of(item)
        self.assertIn("Laborjournal", form.text())
        self.assertIn("Speichern", buttons(form))

    def test_the_field_and_the_button_in_english(self) -> None:
        """Requirement: Task page (`Lab notebook` and `Save`)."""
        accept(language="en")
        item = step_items(page(self.client.get(task_url(self.task))))[0]
        form = self.form_of(item)
        self.assertIn("Lab notebook", form.text())
        self.assertIn("Save", buttons(form))

    def test_the_field_holds_the_steps_entry(self) -> None:
        """Requirement: Task page (a field holding the step's entry)."""
        self.post(self.second, "CE-3/5")
        root = page(self.client.get(task_url(self.task)))
        first, second = step_items(root)
        self.assertEqual(field_value(first, "journal_entry"), "")
        self.assertEqual(field_value(second, "journal_entry"), "CE-3/5")

    def test_no_form_without_a_sign_in(self) -> None:
        """Requirement: Task page (for a signed-in user)."""
        for item in step_items(page(self.client.get(task_url(self.task)))):
            self.assertIsNotNone(item.find(
                ("input", "select", "textarea"), name="journal_entry"))
        self.client.logout()
        for item in step_items(page(self.client.get(task_url(self.task)))):
            self.assertIsNone(item.find(
                ("input", "select", "textarea"), name="journal_entry"))

    def test_the_form_is_there_whatever_the_state(self) -> None:
        """Requirement: Task page (whatever the task's state)."""
        cancelled = make_task(self.kl, "Aspirin", steps=1, cancelled=True)
        failed = make_task(self.kl, "Aspirin", started=past(2),
                           ended=past(1), steps=1, failed=True)
        for task in (cancelled, failed):
            with self.subTest(task=task.number):
                (item,) = step_items(page(self.client.get(task_url(task))))
                self.assertIsNotNone(item.find(
                    ("input", "select", "textarea"),
                    name="journal_entry"))

    def test_a_step_that_names_an_entry_shows_its_link_to_everyone(
            self) -> None:
        """Requirement: Task page (when the step names a journal entry,
        `Laborjournal <entry>`)."""
        self.post(self.first, "AE-2/3")
        self.client.logout()
        first = step_items(page(self.client.get(task_url(self.task))))[0]
        links = journal_links(first)
        self.assertEqual([a.text() for a in links],
                         ["Laborjournal AE-2/3"])
        self.assertEqual([a.get("href") for a in links],
                         ["/lab/journal/AE-2/"])


class StepSequenceTests(StepJournalCase):
    """Requirement: Task record (a step that names a journal entry is
    never removed, and the task's `sequence` is not set, changed or
    cleared while one of its steps names one), Task forms."""

    def refused(self, response: Any, field: str) -> None:
        self.assertEqual(response.status_code, 200)
        self.assertIn(field, context_form(response).errors)

    def test_a_journal_entry_holds_the_steps(self) -> None:
        """Scenario: A journal entry holds the steps."""
        self.post(self.second, "AE-1/9")
        done = self.change(self.task, steps_total="1")
        self.refused(done, "steps_total")
        self.assertEqual(Task.objects.get(pk=self.task.pk).steps.count(),
                         2)

    def test_a_step_without_an_entry_can_still_go(self) -> None:
        """Requirement: Task forms (a steps total that would remove a step
        naming a journal entry is refused; one that removes others
        is not)."""
        self.post(self.first, "AE-1/9")
        done = self.change(self.task, steps_total="1")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Task.objects.get(pk=self.task.pk).steps.count(),
                         1)
        self.assertEqual(self.named(self.first), "AE-1/9")

    def test_the_steps_total_may_grow(self) -> None:
        self.post(self.second, "AE-1/9")
        done = self.change(self.task, steps_total="3")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Task.objects.get(pk=self.task.pk).steps.count(),
                         3)
        self.assertEqual(self.named(self.second), "AE-1/9")

    def test_a_step_that_let_go_can_be_removed(self) -> None:
        """Requirement: Task record (a step that names a journal entry
        is never removed: one that names none is)."""
        self.post(self.second, "AE-1/9")
        self.assertEqual(self.named(self.second), "AE-1/9")
        self.post(self.second, "")
        done = self.change(self.task, steps_total="1")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Task.objects.get(pk=self.task.pk).steps.count(),
                         1)

    def test_no_steps_total_removes_every_step(self) -> None:
        """Requirement: Task forms (an empty total removes them all,
        unless a step names a journal entry)."""
        self.post(self.first, "AE-1/9")
        self.refused(self.change(self.task, steps_total=""),
                     "steps_total")
        self.assertEqual(Task.objects.get(pk=self.task.pk).steps.count(),
                         2)

    def test_a_save_keeps_the_entries(self) -> None:
        """Requirement: Task record (a save that leaves the steps leaves
        what they name)."""
        self.post(self.second, "AE-1/9")
        done = self.change(self.task, note="Eine Notiz", steps_done="1")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.named(self.second), "AE-1/9")
        self.assertEqual(self.named(self.first), None)

    def test_a_sequence_cannot_be_set(self) -> None:
        """Requirement: Task forms (a sequence set on a task with a step
        naming a journal entry is refused)."""
        self.post(self.first, "AE-1/9")
        done = self.change(self.task, sequence="SEQ-0001")
        self.refused(done, "sequence")
        task = Task.objects.get(pk=self.task.pk)
        self.assertIsNone(task.sequence)
        self.assertEqual(task.steps.count(), 2)

    def test_a_sequence_cannot_be_changed_or_cleared(self) -> None:
        """Requirement: Task forms (a sequence set, changed or cleared
        while a step names a journal entry)."""
        self.create(substance="1-biphenyl-4-yl-ethanol",
                    sequence="SEQ-0002", started="2025-03-01")
        task = Task.objects.exclude(pk=self.task.pk).get()
        first, second = steps_of(task)
        self.post(second, "AE-1/9")
        for sequence in ("SEQ-0001", ""):
            with self.subTest(sequence=sequence):
                self.refused(self.change(task, sequence=sequence),
                             "sequence")
        task = Task.objects.get(pk=task.pk)
        self.assertEqual(task.sequence.key, "SEQ-0002")
        self.assertEqual(self.named(second), "AE-1/9")

    def test_a_sequence_kept_is_no_change(self) -> None:
        """Requirement: Task record (a save that leaves `sequence` as it
        was leaves the steps as they were)."""
        self.create(substance="1-biphenyl-4-yl-ethanol",
                    sequence="SEQ-0002", started="2025-03-01")
        task = Task.objects.exclude(pk=self.task.pk).get()
        first, second = steps_of(task)
        self.post(second, "AE-1/9")
        done = self.change(task, note="Notiz")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.named(second), "AE-1/9")
        self.assertEqual(Task.objects.get(pk=task.pk).steps.count(), 2)

    def test_a_sequence_can_be_set_once_the_entry_is_let_go(self) -> None:
        self.post(self.first, "AE-1/9")
        self.assertEqual(self.named(self.first), "AE-1/9")
        self.post(self.first, "")
        done = self.change(self.task, sequence="SEQ-0001")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(
            Task.objects.get(pk=self.task.pk).sequence.key, "SEQ-0001")


class ImportAndStepTests(StepJournalCase):
    """Requirement: Notebooks and entries (an import and a task step that
    name a new entry make one entry and both name it)."""

    def test_a_step_names_an_entry_an_import_names_next(self) -> None:
        from collection.models import Procedure
        self.post(self.second, "AE-2/30")
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0001")["notebook"] = "AE-2/30"
        import_collection(data)
        self.assertEqual(entries_named("AE-2/30"), 1)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0001").journal_entry_id,
            TaskStep.objects.get(pk=self.second.pk).journal_entry_id)

    def test_an_import_names_an_entry_a_step_names_next(self) -> None:
        from collection.models import Procedure
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0001")["notebook"] = "AE-2/31"
        import_collection(data)
        self.post(self.second, "AE-2/31")
        self.assertEqual(entries_named("AE-2/31"), 1)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0001").journal_entry_id,
            TaskStep.objects.get(pk=self.second.pk).journal_entry_id)


class DemoStepTests(SeededCase):
    """Scenarios: A step's journal entry, A step names an unknown
    notebook."""

    def running(self) -> Any:
        return Task.objects.get(sequence__key="SEQ-0002",
                                started__isnull=False,
                                ended__isnull=True)

    def test_a_steps_journal_entry(self) -> None:
        """Scenario: A step's journal entry."""
        task = self.running()
        step = steps_of(task)[1]
        self.client.force_login(self.account("klehmann"))
        done = self.client.post(step_journal_url(step),
                                {"journal_entry": "CE-3/5"})
        self.assertRedirects(done, task_url(task),
                             fetch_redirect_response=False)
        root = page(self.client.get(task_url(task)))
        item = step_items(root)[1]
        links = [a for a in item.find_all("a")
                 if a.text() == "Laborjournal CE-3/5"]
        self.assertEqual([a.get("href") for a in links],
                         ["/lab/journal/CE-3/"])
        self.assertEqual(entries_named("CE-3/5"), 1)
        newest = TaskStep.objects.get(pk=step.pk).history.order_by(
            "-history_id").first()
        self.assertEqual(newest.history_type, "~")
        self.assertEqual(newest.history_user, self.account("klehmann"))
        self.assertEqual(newest.journal_entry_id,
                         TaskStep.objects.get(pk=step.pk).journal_entry_id)

    def test_a_step_names_an_unknown_notebook(self) -> None:
        """Scenario: A step names an unknown notebook."""
        task = self.running()
        step = steps_of(task)[1]
        self.client.force_login(self.account("klehmann"))
        for value in ("ZZ-1/1", "CE-3"):
            with self.subTest(value=value):
                done = self.client.post(step_journal_url(step),
                                        {"journal_entry": value})
                self.assertRedirects(done, task_url(task),
                                     fetch_redirect_response=False)
                self.assertTrue(sent_messages(done))
                self.assertIsNone(
                    TaskStep.objects.get(pk=step.pk).journal_entry)

    def test_the_done_first_step_names_its_entry(self) -> None:
        """Requirement: Demo notebooks (the done first step of the
        running task of `SEQ-0002` names the entry `CE-3/2`)."""
        first = steps_of(self.running())[0]
        self.assertIsNotNone(first.done_on)
        self.assertEqual(str(first.journal_entry), "CE-3/2")


class StepModelOnlyTests(TestCase):

    def test_the_field_is_a_foreign_key_to_the_entries(self) -> None:
        """Requirement: Task record (`journal_entry`, the journal entry
        it is written down in, or none)."""
        from django.db.models import PROTECT
        field = TaskStep._meta.get_field("journal_entry")
        self.assertTrue(field.null)
        self.assertEqual(field.remote_field.on_delete, PROTECT)
        self.assertEqual(field.remote_field.model._meta.label,
                         "journal.Entry")
        self.assertEqual(field.remote_field.related_name, "task_steps")
