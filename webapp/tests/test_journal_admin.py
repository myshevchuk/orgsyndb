"""Tests of the journal in the admin (lab-journal: Journal in the
admin)."""

from typing import Any

from . import make_user, page
from .journal_support import ENTRIES, NOTEBOOKS, JournalCase, entry_of


def editable(response: Any) -> set[str]:
    """The names of the controls a page offers for editing."""
    return {e.get("name") for e in
            page(response).find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in (
                "submit", "hidden", "button")}


class AdminCase(JournalCase):

    def setUp(self) -> None:
        self.client.force_login(self.staff)

    def change(self, base: str, record: Any) -> str:
        return f"{base}{record.pk}/change/"


class AccessTests(AdminCase):

    def test_staff_enter(self) -> None:
        """Requirement: Journal in the admin (it lists the notebooks and
        the entries for staff)."""
        for path in (NOTEBOOKS, ENTRIES):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_anonymous_users_are_sent_to_the_admin_sign_in(self) -> None:
        """Requirement: Journal in the admin (for staff)."""
        self.client.logout()
        for path in (NOTEBOOKS, ENTRIES):
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertEqual(done.status_code, 302)
                self.assertTrue(
                    done["Location"].startswith("/lab/admin/login/"))

    def test_users_without_staff_status_are_kept_out(self) -> None:
        """Requirement: Journal in the admin (for staff)."""
        self.client.force_login(self.kl)
        for path in (NOTEBOOKS, ENTRIES):
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertIn(done.status_code, (302, 403))
                if done.status_code == 302:
                    self.assertTrue(
                        done["Location"].startswith("/lab/admin/login/"))


class NotebookAdminTests(AdminCase):

    def test_the_notebooks_are_listed(self) -> None:
        """Requirement: Journal in the admin (the admin lists the
        notebooks)."""
        text = self.client.get(NOTEBOOKS).content.decode()
        for code in ("AE-1", "AE-2"):
            with self.subTest(code=code):
                self.assertIn(code, text)

    def test_search_by_code(self) -> None:
        """Requirement: Journal in the admin (with search by code)."""
        text = self.client.get(f"{NOTEBOOKS}?q=AE-2").content.decode()
        self.assertIn("AE-2", text)
        self.assertNotIn("AE-1", text)

    def test_the_change_history_of_a_notebook(self) -> None:
        """Requirement: Journal in the admin (the change history of
        each)."""
        worker = make_user("lab-worker-xy", "XY")
        self.first._history_user = worker
        self.first.note = "geändert"
        self.first.save()
        done = self.client.get(f"{NOTEBOOKS}{self.first.pk}/history/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-xy", done.content.decode())

    def test_the_code_is_read_only_once_a_notebook_exists(self) -> None:
        """Requirement: Journal in the admin (the code read-only once a
        notebook exists)."""
        done = self.client.get(self.change(NOTEBOOKS, self.first))
        self.assertEqual(done.status_code, 200)
        names = editable(done)
        self.assertIn("user", names)
        self.assertIn("note", names)
        self.assertNotIn("code", names)
        self.assertIn("AE-1", done.content.decode())

    def test_the_code_is_entered_when_a_notebook_is_added(self) -> None:
        """Requirement: Journal in the admin (read-only once a notebook
        exists, so editable when it is added)."""
        self.assertIn("code", editable(self.client.get(NOTEBOOKS + "add/")))

    def test_a_notebook_is_added(self) -> None:
        """Requirement: Journal in the admin (the notebooks)."""
        from journal.models import Notebook
        done = self.client.post(NOTEBOOKS + "add/", {
            "code": "AD-1", "user": str(self.kl.pk), "note": ""})
        self.assertEqual(done.status_code, 302)
        self.assertTrue(Notebook.objects.filter(code="AD-1").exists())

    def test_a_posted_code_is_ignored(self) -> None:
        """Requirement: Journal in the admin (the code read-only once a
        notebook exists)."""
        from journal.models import Notebook
        self.client.post(self.change(NOTEBOOKS, self.first), {
            "code": "XX-1", "user": str(self.kl.pk), "note": "Neu"})
        self.assertTrue(Notebook.objects.filter(code="AE-1").exists())
        self.assertFalse(Notebook.objects.filter(code="XX-1").exists())
        self.first.refresh_from_db()
        self.assertEqual(self.first.note, "Neu")

    def test_a_notebook_with_entries_cannot_be_deleted(self) -> None:
        """Requirement: Journal in the admin (a notebook with entries
        cannot be deleted)."""
        from journal.models import Entry, Notebook
        entry_of("AE-1/1")
        done = self.client.post(
            f"{NOTEBOOKS}{self.first.pk}/delete/", {"post": "yes"})
        self.assertNotEqual(done.status_code, 302)
        self.assertTrue(Notebook.objects.filter(code="AE-1").exists())
        self.assertEqual(Entry.objects.count(), 1)

    def test_a_notebook_without_entries_can_be_deleted(self) -> None:
        """Requirement: Journal in the admin (a notebook with entries
        cannot be deleted; one without can)."""
        from journal.models import Notebook
        done = self.client.post(
            f"{NOTEBOOKS}{self.second.pk}/delete/", {"post": "yes"})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(Notebook.objects.filter(code="AE-2").exists())


class EntryAdminTests(AdminCase):
    """Requirement: Journal in the admin (the entries read-only, with no
    way to add or change one)."""

    def setUp(self) -> None:
        super().setUp()
        self.entry = entry_of("AE-1/5")

    def test_the_entries_are_listed(self) -> None:
        self.assertIn("AE-1", self.client.get(ENTRIES).content.decode())

    def test_entries_read_only(self) -> None:
        """Scenario: Entries read-only."""
        from journal.models import Entry
        before = Entry.objects.count()
        self.assertEqual(self.client.get(ENTRIES + "add/").status_code,
                         403)
        done = self.client.post(ENTRIES + "add/", {
            "notebook": str(self.first.pk), "number": "7"})
        self.assertEqual(done.status_code, 403)
        self.assertEqual(Entry.objects.count(), before)
        self.assertFalse(Entry.objects.filter(number=7).exists())

    def test_the_change_page_offers_no_field(self) -> None:
        """Requirement: Journal in the admin (read-only, no way to change
        one)."""
        done = self.client.get(self.change(ENTRIES, self.entry))
        self.assertEqual(done.status_code, 200)
        names = editable(done)
        self.assertFalse(names & {"notebook", "number"}, names)
        self.assertNotIn("_save", names)
        self.assertIsNone(page(done).find("input", name="_save"))

    def test_a_posted_change_is_refused(self) -> None:
        """Requirement: Journal in the admin (no way to change one)."""
        done = self.client.post(self.change(ENTRIES, self.entry), {
            "notebook": str(self.second.pk), "number": "9"})
        self.assertEqual(done.status_code, 403)
        self.entry.refresh_from_db()
        self.assertEqual((self.entry.notebook, self.entry.number),
                         (self.first, 5))

    def test_a_posted_deletion_is_refused(self) -> None:
        """Requirement: Journal in the admin (read-only, no way to delete
        one: only `demo_data --replace` deletes entries)."""
        from journal.models import Entry
        done = self.client.post(f"{ENTRIES}{self.entry.pk}/delete/",
                                {"post": "yes"})
        self.assertEqual(done.status_code, 403)
        self.assertTrue(Entry.objects.filter(pk=self.entry.pk).exists())
