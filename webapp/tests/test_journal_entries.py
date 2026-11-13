"""Tests of ``journal.entries.entry_for``, which gives the entry a text
names and creates it when it is new (lab-journal: Notebooks and
entries)."""

from unittest import mock

from django.core.exceptions import ValidationError
from django.db import connection

from tasks.models import Task

from .demo_support import SeededCase
from .journal_support import (JournalCase, entries_named, entry_of,
                              step_journal_url)

HOLD = "orgsyndb_web.lock.hold"


class EntryForTests(JournalCase):

    def test_a_new_entry_is_created(self) -> None:
        """Requirement: Notebooks and entries (an entry is created when
        a task step or an import first names it)."""
        from journal.models import Entry
        found = entry_of("AE-1/9")
        self.assertIsInstance(found, Entry)
        self.assertEqual((found.notebook, found.number), (self.first, 9))
        self.assertEqual(str(found), "AE-1/9")
        self.assertEqual(entries_named("AE-1/9"), 1)

    def test_a_number_above_9999_is_refused(self) -> None:
        """Requirement: Notebooks and entries (a `number` from 1 to
        9999)."""
        from journal.models import Entry
        for value in ("AE-1/10000", "AE-1/9223372036854775808"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    entry_of(value)
        self.assertEqual(Entry.objects.count(), 0)

    def test_an_entry_is_reused(self) -> None:
        """Requirement: Notebooks and entries (reused whenever one names
        it again)."""
        from journal.models import Entry
        first = entry_of("AE-1/9")
        second = entry_of("AE-1/9")
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Entry.objects.count(), 1)

    def test_an_entry_that_exists_is_returned(self) -> None:
        """Requirement: Notebooks and entries (reused, whoever made
        it)."""
        from journal.models import Entry
        made = Entry.objects.create(notebook=self.second, number=4)
        self.assertEqual(entry_of("AE-2/4").pk, made.pk)
        self.assertEqual(Entry.objects.count(), 1)

    def test_the_numbers_of_one_notebook_are_apart(self) -> None:
        """Requirement: Notebooks and entries (unique within the
        notebook)."""
        found = {entry_of(text).pk for text in
                 ("AE-1/1", "AE-1/2", "AE-2/1", "AE-2/2", "AE-1/10")}
        self.assertEqual(len(found), 5)

    def test_the_number_is_read_as_a_number(self) -> None:
        """Requirement: Notebooks and entries (the number, from 1)."""
        self.assertEqual(entry_of("AE-1/100").number, 100)

    def test_a_malformed_value_is_refused(self) -> None:
        """Requirement: Notebooks and entries (`<code>/<number>`): a
        malformed value raises a validation error and creates nothing."""
        from journal.entries import entry_for
        from journal.models import Entry, Notebook
        for text in ("", "AE-1", "AE-1/", "/3", "AE-1/0", "AE-1/02",
                     "AE-1/-2", "AE-1/x", "AE-1/3/4", "AE-1 /3",
                     "ae-1/3", "AE 1/3", "AE-1/3.5"):
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    entry_for(text)
        self.assertEqual(Entry.objects.count(), 0)
        self.assertEqual(Notebook.objects.count(), 2)

    def test_an_unknown_notebook_is_refused(self) -> None:
        """Requirement: Notebooks and entries (an unknown notebook raises
        a validation error); no notebook is made for it."""
        from journal.entries import entry_for
        from journal.models import Entry, Notebook
        for text in ("ZZ-9/1", "AE-3/1", "AE/1"):
            with self.subTest(text=text):
                with self.assertRaises(ValidationError):
                    entry_for(text)
        self.assertEqual(Entry.objects.count(), 0)
        self.assertEqual(Notebook.objects.count(), 2)

    def test_the_lock_plays_no_part(self) -> None:
        """Requirement: Notebooks and entries (entries are not in the
        snapshot, so creating one takes no lock)."""
        calls = []
        with mock.patch(HOLD, side_effect=lambda: calls.append(
                connection.in_atomic_block)):
            entry_of("AE-1/9")
            entry_of("AE-1/9")
        self.assertEqual(calls, [])


class NamedTwiceTests(SeededCase):
    """Scenario: An entry named twice is one entry."""

    def test_an_entry_named_twice_is_one_entry(self) -> None:
        tasks = Task.objects.filter(steps__isnull=False).distinct(
            ).order_by("number")[:2]
        steps = [task.steps.order_by("position").first() for task in tasks]
        self.assertEqual(len({step.task_id for step in steps}), 2)
        self.client.force_login(self.account("klehmann"))
        for step in steps:
            done = self.client.post(step_journal_url(step),
                                    {"journal_entry": "AE-1/9"})
            self.assertEqual(done.status_code, 302)
        self.assertEqual(entries_named("AE-1/9"), 1)
        for step in steps:
            step.refresh_from_db()
            self.assertEqual(str(step.journal_entry), "AE-1/9")
        self.assertEqual(steps[0].journal_entry_id,
                         steps[1].journal_entry_id)
        self.assertEqual(Task.objects.filter(
            steps__journal_entry__number=9).distinct().count(), 2)
