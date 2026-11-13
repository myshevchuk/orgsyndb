"""Tests of the journal's pages (lab-journal: Journal pages)."""

from typing import Any

from . import NOT_IN_COLLECTION, make_user, table, task_url
from .collection_support import accept, import_collection, without_ids
from .demo_support import SeededCase
from .journal_support import (JOURNAL, NEW_NOTEBOOK, JournalCase,
                              entry_of, make_notebook, notebook_url)

LIST_DE = ["Journal", "Inhaber", "Einträge", "Notiz"]
LIST_EN = ["Notebook", "Owner", "Entries", "Note"]
ENTRIES_DE = ["Eintrag", "Vorschrift", "Aufgabenschritte"]
ENTRIES_EN = ["Entry", "Procedure", "Task steps"]


def hrefs(element: Any) -> list[str]:
    return [a.get("href") for a in element.find_all("a")]


def rows_of(root: Any) -> dict[str, dict[str, Any]]:
    """The rows of the first table of ``root`` by the text of their
    first cell."""
    header, rows = table(root)
    return {row[header[0]].text(): row for row in rows}


class DemoJournalCase(SeededCase):
    """The demo data set, with its four notebooks and their entries."""

    def anonymous(self, path: str) -> Any:
        self.client.logout()
        return self.get(path)

    def signed_in(self, path: str) -> Any:
        self.client.force_login(self.account("klehmann"))
        return self.get(path)


class NotebookListTests(DemoJournalCase):

    def test_the_list_needs_no_sign_in(self) -> None:
        """Requirement: Journal pages (they need no sign-in)."""
        self.client.logout()
        self.assertEqual(self.client.get(JOURNAL).status_code, 200)

    def test_notebook_list(self) -> None:
        """Scenario: Notebook list."""
        root = self.anonymous(JOURNAL)
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["AE-1", "AE-2", "CE-1", "CE-3"])
        self.assertEqual(rows[0]["Inhaber"].text(), "KL Katrin Lehmann")
        self.assertNotIn(NEW_NOTEBOOK, hrefs(root))
        self.assertFalse([a for a in root.find_all("a")
                          if a.text() == "Neues Laborjournal"])

    def test_the_heading_and_the_columns(self) -> None:
        """Requirement: Journal pages (the heading `Laborjournale` and
        the columns `Journal`, `Inhaber`, `Einträge` and `Notiz`)."""
        root = self.anonymous(JOURNAL)
        self.assertEqual(root.find("h1").text(), "Laborjournale")
        self.assertEqual(table(root)[0], LIST_DE)

    def test_the_heading_and_the_columns_in_english(self) -> None:
        """Requirement: Journal pages (`Lab notebooks`, `Notebook`,
        `Owner`, `Entries` and `Note`)."""
        accept(language="en")
        root = self.anonymous(JOURNAL)
        self.assertEqual(root.find("h1").text(), "Lab notebooks")
        self.assertEqual(table(root)[0], LIST_EN)

    def test_a_code_links_to_its_page(self) -> None:
        """Requirement: Journal pages (its code linking to its page)."""
        for code, row in rows_of(self.anonymous(JOURNAL)).items():
            with self.subTest(code=code):
                self.assertEqual(hrefs(row["Journal"]),
                                 [notebook_url(code)])

    def test_the_owners(self) -> None:
        """Requirement: Journal pages (`Inhaber`, the account's initials
        and display name)."""
        owners = {code: row["Inhaber"].text() for code, row
                  in rows_of(self.anonymous(JOURNAL)).items()}
        self.assertEqual(owners, {
            "AE-1": "KL Katrin Lehmann", "AE-2": "AS Anna Schmidt",
            "CE-1": "JK Jonas Koch", "CE-3": "MW Miriam Wolf"})

    def test_the_number_of_entries(self) -> None:
        """Requirement: Journal pages (`Einträge`, the number of its
        entries)."""
        counts = {code: row["Einträge"].text() for code, row
                  in rows_of(self.anonymous(JOURNAL)).items()}
        self.assertEqual(counts, {"AE-1": "3", "AE-2": "4", "CE-1": "1",
                                  "CE-3": "2"})
        entry_of("CE-1/9")
        counts = {code: row["Einträge"].text() for code, row
                  in rows_of(self.anonymous(JOURNAL)).items()}
        self.assertEqual(counts["CE-1"], "2")

    def test_the_note(self) -> None:
        """Requirement: Journal pages (`Notiz`)."""
        from journal.models import Notebook
        notebook = Notebook.objects.get(code="CE-1")
        notebook.note = "Gelbes Heft"
        notebook.save()
        rows = rows_of(self.anonymous(JOURNAL))
        self.assertEqual(rows["CE-1"]["Notiz"].text(), "Gelbes Heft")
        self.assertEqual(rows["AE-1"]["Notiz"].text(), "")

    def test_the_notebooks_are_ordered_by_code(self) -> None:
        """Requirement: Journal pages (ordered by code)."""
        owner = self.account("jkoch")
        for code in ("B-1", "AA-1", "AE-10"):
            make_notebook(code, owner)
        codes = list(rows_of(self.anonymous(JOURNAL)))
        self.assertEqual(codes, sorted(codes))
        self.assertEqual(codes[0], "AA-1")
        self.assertIn("AE-10", codes)

    def test_the_new_link_is_for_signed_in_users(self) -> None:
        """Requirement: Journal pages (for a signed-in user it links
        `Neues Laborjournal` to `/lab/journal/new/`)."""
        root = self.signed_in(JOURNAL)
        links = [a for a in root.find_all("a")
                 if a.text() == "Neues Laborjournal"]
        self.assertEqual([a.get("href") for a in links], [NEW_NOTEBOOK])

    def test_the_new_link_in_english(self) -> None:
        """Requirement: Journal pages (`New lab notebook`)."""
        accept(language="en")
        root = self.signed_in(JOURNAL)
        links = [a for a in root.find_all("a")
                 if a.text() == "New lab notebook"]
        self.assertEqual([a.get("href") for a in links], [NEW_NOTEBOOK])


class NotebookPageTests(DemoJournalCase):

    def test_the_page_needs_no_sign_in(self) -> None:
        """Requirement: Journal pages (they need no sign-in)."""
        self.client.logout()
        self.assertEqual(
            self.client.get(notebook_url("AE-1")).status_code, 200)

    def test_an_unknown_code_answers_404(self) -> None:
        """Requirement: Journal pages (an unknown code answers 404)."""
        self.assertEqual(
            self.client.get(notebook_url("AE-1")).status_code, 200)
        for path in (notebook_url("ZZ-9"), notebook_url("ZZ-9", "edit")):
            with self.subTest(path=path):
                self.client.force_login(self.account("klehmann"))
                self.assertEqual(self.client.get(path).status_code, 404)
        self.client.logout()
        self.assertEqual(
            self.client.get(notebook_url("ZZ-9")).status_code, 404)

    def test_entries_of_a_notebook(self) -> None:
        """Scenario: Entries of a notebook."""
        root = self.anonymous(notebook_url("AE-1"))
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["AE-1/1", "AE-1/2", "AE-1/3"])
        for row, ident in zip(rows, ("OSDB-0001", "OSDB-0002",
                                     "OSDB-0003")):
            with self.subTest(ident=ident):
                self.assertEqual(row["Vorschrift"].text(), ident)
                self.assertEqual(hrefs(row["Vorschrift"]),
                                 [f"/procedures/{ident.lower()}/"])

    def test_the_heading_the_owner_and_the_note(self) -> None:
        """Requirement: Journal pages (the code as heading, the owner
        and the note)."""
        from journal.models import Notebook
        notebook = Notebook.objects.get(code="AE-1")
        notebook.note = "Kristallisationen"
        notebook.save()
        root = self.anonymous(notebook_url("AE-1"))
        self.assertEqual(root.find("h1").text(), "AE-1")
        text = root.text()
        self.assertIn("Katrin Lehmann", text)
        self.assertIn("Kristallisationen", text)

    def test_the_columns(self) -> None:
        """Requirement: Journal pages (`Eintrag`, `Vorschrift` and
        `Aufgabenschritte`)."""
        self.assertEqual(table(self.anonymous(notebook_url("AE-1")))[0],
                         ENTRIES_DE)

    def test_the_columns_in_english(self) -> None:
        """Requirement: Journal pages (`Entry`, `Procedure` and `Task
        steps`)."""
        accept(language="en")
        self.assertEqual(table(self.anonymous(notebook_url("AE-1")))[0],
                         ENTRIES_EN)

    def test_the_entries_are_in_order_of_number(self) -> None:
        """Requirement: Journal pages (in order of number, so 8 comes
        before 11)."""
        header, rows = table(self.anonymous(notebook_url("AE-2")))
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["AE-2/7", "AE-2/8", "AE-2/11", "AE-2/12"])
        self.assertEqual([row["Vorschrift"].text() for row in rows],
                         ["OSDB-0004", "OSDB-0005", "OSDB-0007",
                          "OSDB-0008"])

    def test_a_task_step_names_its_entry(self) -> None:
        """Requirement: Journal pages (`Aufgabenschritte`, each task
        step that names it as its task's number and `Stufe <n>`, linking
        to the task's page)."""
        from tasks.models import TaskStep
        step = TaskStep.objects.get(journal_entry__notebook__code="CE-3",
                                    journal_entry__number=2)
        rows = rows_of(self.anonymous(notebook_url("CE-3")))
        self.assertEqual(set(rows), {"CE-3/1", "CE-3/2"})
        cell = rows["CE-3/2"]["Aufgabenschritte"]
        self.assertIn(step.task.number, cell.text())
        self.assertIn("Stufe 1", cell.text())
        self.assertEqual(hrefs(cell), [task_url(step.task)])
        self.assertEqual(rows["CE-3/2"]["Vorschrift"].text(), "")
        self.assertEqual(rows["CE-3/1"]["Vorschrift"].text(), "OSDB-0009")
        self.assertEqual(rows["CE-3/1"]["Aufgabenschritte"].text(), "")

    def test_the_steps_in_english(self) -> None:
        """Requirement: Journal pages (`Step <n>`)."""
        accept(language="en")
        rows = rows_of(self.anonymous(notebook_url("CE-3")))
        self.assertRegex(rows["CE-3/2"]["Task steps"].text(),
                         r"T-\d+\W+Step 1")

    def test_a_procedure_and_a_step_name_one_entry(self) -> None:
        """Requirement: Journal pages (the procedures and the task steps
        that name it)."""
        from tasks.models import TaskStep
        step = TaskStep.objects.filter(
            journal_entry__isnull=True).order_by("pk").first()
        step.journal_entry = entry_of("AE-1/1")
        step.save()
        row = rows_of(self.anonymous(notebook_url("AE-1")))["AE-1/1"]
        self.assertEqual(row["Vorschrift"].text(), "OSDB-0001")
        self.assertEqual(hrefs(row["Aufgabenschritte"]),
                         [task_url(step.task)])

    def test_two_steps_name_one_entry(self) -> None:
        """Requirement: Journal pages (each task step that names it)."""
        from tasks.models import TaskStep
        steps = list(TaskStep.objects.filter(
            journal_entry__isnull=True).order_by("pk")[:2])
        for step in steps:
            step.journal_entry = entry_of("CE-1/9")
            step.save()
        row = rows_of(self.anonymous(notebook_url("CE-1")))["CE-1/9"]
        self.assertEqual(sorted(hrefs(row["Aufgabenschritte"])),
                         sorted(task_url(step.task) for step in steps))
        self.assertEqual(row["Vorschrift"].text(), "")

    def test_a_withdrawn_procedure_is_marked(self) -> None:
        """Requirement: Journal pages (a withdrawn procedure with the
        mark `nicht in der Sammlung` and no link)."""
        import_collection(without_ids("OSDB-0002", "SEQ-0001"))
        rows = rows_of(self.anonymous(notebook_url("AE-1")))
        gone = rows["AE-1/2"]["Vorschrift"]
        self.assertIn("OSDB-0002", gone.text())
        self.assertIn(NOT_IN_COLLECTION["de"], gone.text())
        self.assertEqual(gone.find_all("a"), [])
        kept = rows["AE-1/3"]["Vorschrift"]
        self.assertNotIn(NOT_IN_COLLECTION["de"], kept.text())
        self.assertEqual(hrefs(kept), ["/procedures/osdb-0003/"])

    def test_a_withdrawn_procedure_in_english(self) -> None:
        """Requirement: Journal pages (the mark in English)."""
        import_collection(without_ids("OSDB-0002", "SEQ-0001"))
        accept(language="en")
        gone = rows_of(self.anonymous(notebook_url("AE-1")))[
            "AE-1/2"]["Procedure"]
        self.assertIn(NOT_IN_COLLECTION["en"], gone.text())
        self.assertEqual(gone.find_all("a"), [])

    def test_an_entry_nothing_names_shows_empty_cells(self) -> None:
        """Requirement: Journal pages (an entry that no procedure or
        step names has no procedure and no step)."""
        entry_of("CE-1/9")
        row = rows_of(self.anonymous(notebook_url("CE-1")))["CE-1/9"]
        self.assertEqual(row["Vorschrift"].text(), "")
        self.assertEqual(row["Aufgabenschritte"].text(), "")

    def test_the_edit_link_is_for_signed_in_users(self) -> None:
        """Requirement: Journal pages (for a signed-in user it links
        `Bearbeiten` to `/lab/journal/<code>/edit/`)."""
        path = notebook_url("AE-1", "edit")
        root = self.anonymous(notebook_url("AE-1"))
        self.assertNotIn(path, hrefs(root))
        links = [a for a in self.signed_in(notebook_url("AE-1")
                                           ).find_all("a")
                 if a.text() == "Bearbeiten"]
        self.assertEqual([a.get("href") for a in links], [path])

    def test_the_edit_link_in_english(self) -> None:
        """Requirement: Journal pages (`Edit`)."""
        accept(language="en")
        links = [a for a in self.signed_in(notebook_url("AE-1")
                                           ).find_all("a")
                 if a.text() == "Edit"]
        self.assertEqual([a.get("href") for a in links],
                         [notebook_url("AE-1", "edit")])


class EmptyNotebookTests(JournalCase):

    def test_a_notebook_without_entries(self) -> None:
        """Requirement: Journal pages (a notebook without entries shows
        `Keine Einträge.`)."""
        root = self.get(notebook_url("AE-1"))
        self.assertIn("Keine Einträge.", root.text())
        self.assertEqual(root.find("h1").text(), "AE-1")

    def test_a_notebook_without_entries_in_english(self) -> None:
        """Requirement: Journal pages (`No entries.`)."""
        accept(language="en")
        self.assertIn("No entries.", self.get(notebook_url("AE-1")).text())

    def test_a_notebook_with_entries_shows_no_such_text(self) -> None:
        """Requirement: Journal pages (`Keine Einträge.` only for a
        notebook without entries)."""
        entry_of("AE-1/1")
        self.assertNotIn("Keine Einträge.",
                         self.get(notebook_url("AE-1")).text())

    def test_the_list_shows_a_notebook_without_entries(self) -> None:
        """Requirement: Journal pages (`Einträge`, the number of its
        entries, 0 for none)."""
        rows = rows_of(self.get(JOURNAL))
        self.assertEqual(rows["AE-1"]["Einträge"].text(), "0")
        self.assertEqual(rows["AE-2"]["Notiz"].text(), "Zweites Buch")

    def test_an_owner_without_a_full_name(self) -> None:
        """Requirement: Journal pages (`Inhaber`, the account's initials
        and display name, which is the user name without a full
        name)."""
        make_notebook("ZZ-1", make_user("nameless", "NL"))
        rows = rows_of(self.get(JOURNAL))
        self.assertEqual(rows["ZZ-1"]["Inhaber"].text(), "NL nameless")
