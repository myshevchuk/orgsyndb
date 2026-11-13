"""Tests of the notebooks and entries of the lab journal (lab-journal:
Notebooks and entries)."""

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from . import make_task, make_user
from .collection_support import (ImportCase, accepts, make_import,
                                 make_procedure, refuses)
from .journal_support import (JournalCase, entries_named, entry_of,
                              make_notebook)


class AppTests(TestCase):

    def test_the_app_is_installed(self) -> None:
        """Requirement: Notebooks and entries (the package `journal`)."""
        self.assertIn("journal",
                      [config.label for config in apps.get_app_configs()])
        names = {model.__name__ for model in
                 apps.get_app_config("journal").get_models()}
        self.assertLessEqual({"Notebook", "Entry"}, names)


class NotebookModelTests(JournalCase):

    def notebook(self, code: str, **fields):
        from journal.models import Notebook
        return Notebook(**{"code": code, "user": self.kl, **fields})

    def test_a_notebook_holds_its_fields(self) -> None:
        """Requirement: Notebooks and entries (`code`, `user` and
        `note`)."""
        from journal.models import Notebook
        found = Notebook.objects.get(code="AE-2")
        self.assertEqual((found.code, found.user, found.note),
                         ("AE-2", self.ae, "Zweites Buch"))

    def test_the_note_may_be_empty(self) -> None:
        """Requirement: Notebooks and entries (`note`, which may be
        empty)."""
        found = accepts(self, lambda: self.notebook("AE-3"))
        self.assertEqual(found.note, "")

    def test_a_code_is_taken_once(self) -> None:
        """Requirement: Notebooks and entries (`code`, unique)."""
        refuses(self, lambda: self.notebook("AE-1", user=self.ae))

    def test_codes_that_follow_the_pattern(self) -> None:
        """Requirement: Notebooks and entries (`code`, at most 20
        characters matching `^[A-Z0-9]+(-[A-Z0-9]+)*$`)."""
        for code in ("A", "KL-1", "A1-B2-C3", "7", "A" * 20,
                     "ABCDEFGHI-ABCDEFGHI"):
            with self.subTest(code=code):
                accepts(self, lambda: self.notebook(code))

    def test_codes_that_break_the_pattern(self) -> None:
        """Requirement: Notebooks and entries (`code`, as above)."""
        for code in ("", "ae-3", "AE_3", "AE-", "-AE", "AE--3", "AE 3",
                     "AE/3", "ÄE-3", "A" * 21):
            with self.subTest(code=code):
                refuses(self, lambda: self.notebook(code))

    def test_a_notebook_needs_an_owner(self) -> None:
        """Requirement: Notebooks and entries (`user`, the account whose
        notebook it is)."""
        refuses(self, lambda: self.notebook("AE-3", user=None))

    def test_an_account_lists_its_notebooks(self) -> None:
        """Requirement: Notebooks and entries (`user`, related name
        `notebooks`)."""
        self.assertEqual([n.code for n in self.kl.notebooks.all()],
                         ["AE-1"])
        self.assertEqual([n.code for n in self.ae.notebooks.all()],
                         ["AE-2"])

    def test_a_code_is_fixed_once_set(self) -> None:
        """Scenario: A code fixed once set."""
        from journal.models import Notebook
        self.first.code = "AE-9"
        with self.assertRaises(ValidationError):
            self.first.save()
        self.assertEqual(Notebook.objects.get(pk=self.first.pk).code,
                         "AE-1")
        self.assertFalse(Notebook.objects.filter(code="AE-9").exists())

    def test_the_other_fields_may_change(self) -> None:
        """Requirement: Notebooks and entries (`code` is fixed; `user`
        and `note` are not)."""
        from journal.models import Notebook
        found = Notebook.objects.get(code="AE-1")
        found.user = self.ae
        found.note = "Neu"
        found.save()
        found = Notebook.objects.get(code="AE-1")
        self.assertEqual((found.user, found.note, found.code),
                         (self.ae, "Neu", "AE-1"))

    def test_a_notebook_keeps_a_change_history(self) -> None:
        """Requirement: Notebooks and entries (notebooks keep a change
        history)."""
        from journal.models import Notebook
        found = make_notebook("AE-3", self.kl, by=self.kl)
        found.note = "Geändert"
        found._history_user = self.ae
        found.save()
        records = list(Notebook.objects.get(pk=found.pk).history
                       .order_by("history_id"))
        self.assertEqual([r.history_type for r in records], ["+", "~"])
        self.assertEqual([r.history_user for r in records],
                         [self.kl, self.ae])
        self.assertEqual((records[-1].code, records[-1].note),
                         ("AE-3", "Geändert"))

    def test_an_account_with_a_notebook_cannot_be_deleted(self) -> None:
        """Requirement: Notebooks and entries (an account that a notebook
        belongs to cannot be deleted)."""
        with self.assertRaises(ProtectedError):
            self.kl.delete()
        self.kl.refresh_from_db()
        self.assertEqual(self.kl.notebooks.count(), 1)

    def test_an_account_without_a_notebook_can_be_deleted(self) -> None:
        """Requirement: Notebooks and entries (only an account a notebook
        belongs to is kept)."""
        free = make_user("free", "FR")
        free.delete()
        self.assertFalse(type(free).objects.filter(username="free").exists())


class EntryModelTests(JournalCase):

    def entry(self, notebook, number: int):
        from journal.models import Entry
        return Entry(notebook=notebook, number=number)

    def test_an_entry_holds_its_fields(self) -> None:
        """Requirement: Notebooks and entries (an entry: its `notebook`
        and its `number`, written `<code>/<number>`)."""
        from journal.models import Entry
        made = Entry.objects.create(notebook=self.first, number=2)
        found = Entry.objects.get(pk=made.pk)
        self.assertEqual((found.notebook, found.number),
                         (self.first, 2))
        self.assertEqual(str(found), "AE-1/2")
        self.assertEqual(str(Entry.objects.create(
            notebook=self.second, number=11)), "AE-2/11")

    def test_a_notebook_lists_its_entries(self) -> None:
        """Requirement: Notebooks and entries (`notebook`, related name
        `entries`)."""
        for number in (3, 1, 2):
            self.entry(self.first, number).save()
        self.assertEqual(sorted(e.number for e in self.first.entries.all()),
                         [1, 2, 3])
        self.assertEqual(self.second.entries.count(), 0)

    def test_a_number_is_unique_within_its_notebook(self) -> None:
        """Requirement: Notebooks and entries (`number`, unique within
        the notebook)."""
        self.entry(self.first, 2).save()
        refuses(self, lambda: self.entry(self.first, 2))
        accepts(self, lambda: self.entry(self.second, 2))

    def test_a_number_counts_from_1(self) -> None:
        """Requirement: Notebooks and entries (`number`, from 1)."""
        refuses(self, lambda: self.entry(self.first, 0))
        accepts(self, lambda: self.entry(self.first, 1))

    def test_a_number_is_a_whole_number(self) -> None:
        """Requirement: Notebooks and entries (`number`, from 1)."""
        refuses(self, lambda: self.entry(self.first, -3))

    def test_a_notebook_with_an_entry_cannot_be_deleted(self) -> None:
        """Requirement: Notebooks and entries (a notebook that an entry
        belongs to cannot be deleted)."""
        from journal.models import Notebook
        self.entry(self.first, 1).save()
        with self.assertRaises(ProtectedError):
            self.first.delete()
        self.assertTrue(Notebook.objects.filter(code="AE-1").exists())

    def test_a_notebook_without_an_entry_can_be_deleted(self) -> None:
        """Requirement: Notebooks and entries (a notebook with no entry
        is not kept)."""
        from journal.models import Notebook
        self.first.delete()
        self.assertFalse(Notebook.objects.filter(code="AE-1").exists())


class EntryInUseTests(ImportCase):
    """Requirement: Notebooks and entries (an entry that a procedure or
    task step names cannot be deleted)."""

    def setUp(self) -> None:
        super().setUp()
        self.entry = entry_of("AE-1/9")

    def test_an_entry_a_procedure_names_stays(self) -> None:
        from journal.models import Entry
        make_procedure(make_import(), "OSDB-0002",
                       journal_entry=self.entry)
        with self.assertRaises(ProtectedError):
            self.entry.delete()
        self.assertTrue(Entry.objects.filter(pk=self.entry.pk).exists())

    def test_an_entry_a_task_step_names_stays(self) -> None:
        from journal.models import Entry
        from tasks.models import TaskStep

        task = make_task(make_user("kl", "KL"), steps=1)
        TaskStep.objects.filter(task=task).update(
            journal_entry=self.entry)
        with self.assertRaises(ProtectedError):
            self.entry.delete()
        self.assertTrue(Entry.objects.filter(pk=self.entry.pk).exists())

    def test_an_entry_nothing_names_can_be_deleted(self) -> None:
        from journal.models import Entry
        self.entry.delete()
        self.assertEqual(entries_named("AE-1/9"), 0)
        self.assertFalse(Entry.objects.exists())
