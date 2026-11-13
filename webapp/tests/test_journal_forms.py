"""Tests of the journal's forms (lab-journal: Journal forms)."""

from typing import Any

from registry import snapshot

from . import context_form, field_value, page, sent_messages
from .collection_support import accept
from .journal_support import (JOURNAL, NEW_NOTEBOOK, JournalCase,
                              control_names, entry_of, notebook_url)


class FormCase(JournalCase):
    """A test case whose client is signed in as ``kl``."""

    def setUp(self) -> None:
        self.client.force_login(self.kl)

    def new_data(self, **over: str) -> dict[str, str]:
        """The new-notebook form's fields as the page offers them for the
        code ``KL-1``, with ``over`` applied."""
        root = page(self.client.get(NEW_NOTEBOOK))
        data = {"code": "KL-1", "user": field_value(root, "user"),
                "note": ""}
        data.update(over)
        return data

    def refused(self, response: Any, field: str) -> None:
        """The form is shown again with an error at ``field``."""
        self.assertEqual(response.status_code, 200)
        self.assertIn(field, context_form(response).errors)


class NewFormTests(FormCase):

    def test_it_needs_a_sign_in(self) -> None:
        """Requirement: Journal forms (a signed-in user registers
        notebooks)."""
        from journal.models import Notebook
        self.client.logout()
        before = Notebook.objects.count()
        got = self.client.get(NEW_NOTEBOOK)
        self.assertIn(got.status_code, (302, 403))
        done = self.client.post(NEW_NOTEBOOK, {"code": "KL-1",
                                               "user": str(self.kl.pk)})
        self.assertIn(done.status_code, (302, 403))
        self.assertEqual(Notebook.objects.count(), before)

    def test_the_form_holds_the_code_the_owner_and_the_note(self) -> None:
        """Requirement: Journal forms (`/lab/journal/new/`: the code; the
        owner; and the note)."""
        root = page(self.client.get(NEW_NOTEBOOK))
        form = root.find("input", name="code").closest("form")
        self.assertEqual(control_names(form), {"code", "user", "note"})

    def test_the_owner_is_a_choice_of_every_account(self) -> None:
        """Requirement: Journal forms (the owner, a choice of every
        account shown as initials and display name, the signed-in user's
        selected)."""
        root = page(self.client.get(NEW_NOTEBOOK))
        options = root.find("select", name="user").find_all("option")
        values = {o.get("value"): o.text() for o in options}
        self.assertLessEqual({str(self.kl.pk), str(self.ae.pk),
                              str(self.staff.pk)}, set(values))
        self.assertIn("KL", values[str(self.kl.pk)])
        self.assertIn("Klara Lehmann", values[str(self.kl.pk)])
        self.assertIn("AE", values[str(self.ae.pk)])
        self.assertIn("Anna Eisele", values[str(self.ae.pk)])
        self.assertEqual(field_value(root, "user"), str(self.kl.pk))

    def test_the_selected_owner_is_the_signed_in_user(self) -> None:
        """Requirement: Journal forms (the signed-in user's selected)."""
        self.client.force_login(self.ae)
        root = page(self.client.get(NEW_NOTEBOOK))
        self.assertEqual(field_value(root, "user"), str(self.ae.pk))

    def test_registering_a_notebook(self) -> None:
        """Scenario: Registering a notebook."""
        from journal.models import Notebook
        before = snapshot.build()["digest"]
        done = self.client.post(NEW_NOTEBOOK, self.new_data())
        found = Notebook.objects.get(code="KL-1")
        self.assertEqual(found.user, self.kl)
        record = found.history.get()
        self.assertEqual((record.history_type, record.history_user),
                         ("+", self.kl))
        self.assertRedirects(done, notebook_url("KL-1"),
                             fetch_redirect_response=False)
        self.assertEqual(
            self.client.get(notebook_url("KL-1")).status_code, 200)
        self.assertNotEqual(snapshot.build()["digest"], before)

    def test_every_field_is_saved(self) -> None:
        """Requirement: Journal forms (the code, the owner and the
        note)."""
        from journal.models import Notebook
        self.client.post(NEW_NOTEBOOK, self.new_data(
            code="XY-7", user=str(self.ae.pk), note="Blaues Heft"))
        found = Notebook.objects.get(code="XY-7")
        self.assertEqual((found.user, found.note),
                         (self.ae, "Blaues Heft"))

    def test_the_note_may_be_empty(self) -> None:
        """Requirement: Journal forms (`note`, which may be empty)."""
        from journal.models import Notebook
        self.client.post(NEW_NOTEBOOK, self.new_data())
        self.assertEqual(Notebook.objects.get(code="KL-1").note, "")

    def test_the_message(self) -> None:
        """Requirement: Journal forms (a saved form leads to the
        notebook's page with the message `Laborjournal <code>
        gespeichert.`)."""
        done = self.client.post(NEW_NOTEBOOK, self.new_data())
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Laborjournal KL-1 gespeichert."])

    def test_the_message_in_english(self) -> None:
        """Requirement: Journal forms (`Lab notebook <code> saved.`)."""
        accept(language="en")
        done = self.client.post(NEW_NOTEBOOK, self.new_data())
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Lab notebook KL-1 saved."])

    def test_a_bad_code(self) -> None:
        """Scenario: A bad code."""
        from journal.models import Notebook
        before = Notebook.objects.count()
        for code in ("KL/1", "AE-1"):
            with self.subTest(code=code):
                self.refused(self.client.post(
                    NEW_NOTEBOOK, self.new_data(code=code)), "code")
        self.assertEqual(Notebook.objects.count(), before)

    def test_codes_that_break_the_pattern(self) -> None:
        """Requirement: Journal forms (a code that breaks its pattern
        shows an error at its field and saves nothing)."""
        from journal.models import Notebook
        before = Notebook.objects.count()
        for code in ("", "kl-1", "KL_1", "KL-", "-KL", "KL--1", "KL 1",
                     "A" * 21):
            with self.subTest(code=code):
                self.refused(self.client.post(
                    NEW_NOTEBOOK, self.new_data(code=code)), "code")
        self.assertEqual(Notebook.objects.count(), before)

    def test_a_code_of_twenty_characters(self) -> None:
        """Requirement: Journal forms (at most 20 characters)."""
        from journal.models import Notebook
        self.client.post(NEW_NOTEBOOK, self.new_data(code="A" * 20))
        self.assertTrue(Notebook.objects.filter(code="A" * 20).exists())

    def test_an_owner_that_is_no_account(self) -> None:
        """Requirement: Journal forms (the owner, a choice of every
        account)."""
        from journal.models import Notebook
        before = Notebook.objects.count()
        self.refused(self.client.post(
            NEW_NOTEBOOK, self.new_data(user="99999")), "user")
        self.refused(self.client.post(
            NEW_NOTEBOOK, self.new_data(user="")), "user")
        self.assertEqual(Notebook.objects.count(), before)

    def test_the_snapshot_lists_the_new_notebook(self) -> None:
        """Requirement: Notebooks and entries (the snapshot lists the
        notebooks, each as its `code` and `user`)."""
        self.client.post(NEW_NOTEBOOK, self.new_data(note="Eins"))
        listed = {n["code"]: n["user"]
                  for n in snapshot.build()["notebooks"]}
        self.assertEqual(listed, {"AE-1": "kl", "AE-2": "ae",
                                  "KL-1": "kl"})


class EditFormTests(FormCase):

    def test_it_needs_a_sign_in(self) -> None:
        """Requirement: Journal forms (a signed-in user edits
        notebooks)."""
        self.client.logout()
        path = notebook_url("AE-1", "edit")
        self.assertIn(self.client.get(path).status_code, (302, 403))
        done = self.client.post(path, {"user": str(self.ae.pk),
                                       "note": "Geändert"})
        self.assertIn(done.status_code, (302, 403))
        self.first.refresh_from_db()
        self.assertEqual((self.first.user, self.first.note),
                         (self.kl, ""))

    def test_an_unknown_code_answers_404(self) -> None:
        """Requirement: Journal pages (an unknown code answers 404)."""
        path = notebook_url("ZZ-9", "edit")
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(path, {
            "user": str(self.kl.pk), "note": ""}).status_code, 404)

    def test_the_form_holds_the_owner_and_the_note(self) -> None:
        """Requirement: Journal forms (`/lab/journal/<code>/edit/`: the
        owner and the note, the code shown and not editable)."""
        root = page(self.client.get(notebook_url("AE-2", "edit")))
        form = root.find("select", name="user").closest("form")
        self.assertEqual(control_names(form), {"user", "note"})
        self.assertIn("AE-2", root.text())
        self.assertEqual(field_value(root, "user"), str(self.ae.pk))
        self.assertEqual(field_value(root, "note"), "Zweites Buch")

    def test_a_change_is_saved_with_its_history(self) -> None:
        """Requirement: Journal forms (each saved with its change
        history)."""
        from journal.models import Notebook
        done = self.client.post(notebook_url("AE-2", "edit"), {
            "user": str(self.kl.pk), "note": "Neu"})
        self.assertRedirects(done, notebook_url("AE-2"),
                             fetch_redirect_response=False)
        found = Notebook.objects.get(code="AE-2")
        self.assertEqual((found.user, found.note), (self.kl, "Neu"))
        newest = found.history.order_by("-history_id").first()
        self.assertEqual((newest.history_type, newest.history_user),
                         ("~", self.kl))

    def test_the_message(self) -> None:
        """Requirement: Journal forms (`Laborjournal <code>
        gespeichert.`)."""
        done = self.client.post(notebook_url("AE-2", "edit"), {
            "user": str(self.ae.pk), "note": "Zweites Buch"})
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Laborjournal AE-2 gespeichert."])

    def test_the_message_in_english(self) -> None:
        """Requirement: Journal forms (`Lab notebook <code> saved.`)."""
        accept(language="en")
        done = self.client.post(notebook_url("AE-2", "edit"), {
            "user": str(self.ae.pk), "note": "Zweites Buch"})
        self.assertEqual([str(m) for m in sent_messages(done)],
                         ["Lab notebook AE-2 saved."])

    def test_the_code_cannot_be_changed(self) -> None:
        """Requirement: Journal forms (the code shown and not editable):
        a posted code is ignored."""
        from journal.models import Notebook
        self.client.post(notebook_url("AE-2", "edit"), {
            "code": "XX-1", "user": str(self.ae.pk), "note": "x"})
        self.assertTrue(Notebook.objects.filter(code="AE-2").exists())
        self.assertFalse(Notebook.objects.filter(code="XX-1").exists())

    def test_an_owner_that_is_no_account(self) -> None:
        """Requirement: Journal forms (the owner, a choice of every
        account)."""
        done = self.client.post(notebook_url("AE-2", "edit"), {
            "user": "99999", "note": "x"})
        self.refused(done, "user")
        self.second.refresh_from_db()
        self.assertEqual((self.second.user, self.second.note),
                         (self.ae, "Zweites Buch"))

    def test_the_owner_changes_the_snapshot_and_the_note_does_not(
            self) -> None:
        """Scenario: Notebooks in the snapshot (the digest follows the
        owner, not the note)."""
        before = snapshot.build()["digest"]
        self.client.post(notebook_url("AE-2", "edit"), {
            "user": str(self.ae.pk), "note": "Anderes"})
        self.assertEqual(snapshot.build()["digest"], before)
        self.client.post(notebook_url("AE-2", "edit"), {
            "user": str(self.kl.pk), "note": "Anderes"})
        after = snapshot.build()
        self.assertNotEqual(after["digest"], before)
        self.assertEqual(
            {n["code"]: n["user"] for n in after["notebooks"]}["AE-2"],
            "kl")

    def test_a_notebook_with_entries_can_be_edited(self) -> None:
        """Requirement: Journal forms (the owner and the note, whatever
        the notebook holds)."""
        entry_of("AE-2/3")
        done = self.client.post(notebook_url("AE-2", "edit"), {
            "user": str(self.kl.pk), "note": "Mit Eintrag"})
        self.assertEqual(done.status_code, 302)
        self.second.refresh_from_db()
        self.assertEqual(self.second.note, "Mit Eintrag")

    def test_the_list_follows_the_form(self) -> None:
        """Requirement: Journal pages (the list shows the notebooks the
        forms save)."""
        self.client.post(NEW_NOTEBOOK, self.new_data(code="BB-1"))
        text = self.client.get(JOURNAL).content.decode("utf-8")
        self.assertIn("BB-1", text)
