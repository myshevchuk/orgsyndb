"""Tests of the imports page (collection-import: Imports page)."""

import re
from datetime import timedelta
from typing import Any

from django.test import override_settings

from . import berlin, build_index, frozen, page, table, ticking
from .collection_support import (IMPORTS, SEQUENCES, TOKEN, ImportCase,
                                 demo_collection, make_import, manifest,
                                 post, refused)
from .demo_support import DAY, SeededCase, noon

COLUMNS_DE = ["Empfangen", "Commit", "Anlass", "Ergebnis", "Release",
              "Fehler"]
COLUMNS_EN = ["Received", "Commit", "Trigger", "Outcome", "Release",
              "Errors"]
TRIGGERS_DE = {"commit": "Commit", "registry": "Register",
               "tooling": "Werkzeuge", "catch-up": "Nachholen"}
TRIGGERS_EN = {"commit": "Commit", "registry": "Registry",
               "tooling": "Tooling", "catch-up": "Catch-up"}


def intro(root: Any) -> str:
    """The text of the page outside its tables."""
    return root.text(skip=lambda node: node.tag == "table")


def has_number(text: str, number: int) -> bool:
    """Whether ``text`` holds ``number`` as a word of its own."""
    return re.search(rf"(?<![\w-]){number}(?![\w-])", text) is not None


def row_of(rows: list[dict[str, Any]], commit: str) -> dict[str, Any]:
    """The row of the table whose commit cell is the first ten digits of
    ``commit``."""
    (found,) = [row for row in rows if row["Commit"].text() == commit[:10]]
    return found


class AccessTests(ImportCase):

    def test_the_page_needs_no_sign_in(self) -> None:
        """Requirement: Imports page (no sign-in)."""
        self.assertEqual(self.client.get(IMPORTS).status_code, 200)

    def test_the_heading(self) -> None:
        """Requirement: Imports page (the heading `Importe`)."""
        make_import()
        response = self.client.get(IMPORTS)
        self.assertEqual(page(response).find("h1").text(), "Importe")

    def test_the_heading_in_english(self) -> None:
        """Requirement: Imports page (`Imports`)."""
        self.use_index(build_index("en"))
        make_import()
        response = self.client.get(IMPORTS)
        self.assertEqual(page(response).find("h1").text(), "Imports")


class NothingImportedTests(ImportCase):

    def test_nothing_imported(self) -> None:
        """Scenario: Nothing imported."""
        response = self.client.get(IMPORTS)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        self.assertIn("Noch keine Importe.", root.text())
        self.assertIsNone(root.find("table"))

    def test_nothing_imported_in_english(self) -> None:
        """Requirement: Imports page (`No imports yet.`)."""
        self.use_index(build_index("en"))
        root = page(self.client.get(IMPORTS))
        self.assertIn("No imports yet.", root.text())
        self.assertIsNone(root.find("table"))

    def test_the_table_replaces_the_text(self) -> None:
        """Requirement: Imports page (without imports the table is
        replaced by the text)."""
        make_import(outcome="refused")
        root = page(self.client.get(IMPORTS))
        self.assertNotIn("Noch keine Importe.", root.text())
        self.assertIsNotNone(root.find("table"))


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class ImportsListedTests(SeededCase):

    def test_imports_listed(self) -> None:
        """Scenario: Imports listed."""
        from collection.models import Import
        body = manifest()
        done = post(self.client, body)
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        errors = ["OSDB-0002.md:title: error: missing", "build failed"]
        with frozen(noon(DAY + timedelta(days=1))):
            report = post(self.client, refused(
                errors, base=done.json()["import"],
                trigger="registry"))
        self.assertEqual(report.json()["outcome"], "refused")
        self.assertEqual(Import.objects.count(), 2)
        response = self.client.get(IMPORTS)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        header, rows = table(root)
        self.assertEqual(header, COLUMNS_DE)
        self.assertEqual(len(rows), 2)
        newest, oldest = rows
        self.assertEqual(newest["Commit"].text(), Import.objects.get(
            outcome="refused").commit[:10])
        self.assertEqual(newest["Ergebnis"].text(), "Abgelehnt")
        self.assertEqual(newest["Anlass"].text(), "Register")
        self.assertEqual(newest["Release"].text(), "")
        for error in errors:
            self.assertIn(error, newest["Fehler"].text())
        self.assertLess(newest["Fehler"].text().index(errors[0]),
                        newest["Fehler"].text().index(errors[1]))
        self.assertEqual(oldest["Commit"].text(), body["commit"][:10])
        self.assertEqual(oldest["Ergebnis"].text(), "Angenommen")
        self.assertEqual(oldest["Anlass"].text(), "Commit")
        self.assertEqual(oldest["Release"].text(), body["release"])
        self.assertEqual(oldest["Fehler"].text(), "")
        self.assertTrue(newest["Empfangen"].text())
        self.assertTrue(oldest["Empfangen"].text())
        above = intro(root)
        self.assertIn(body["commit"][:10], above)
        self.assertNotIn(body["commit"][:11], above)
        self.assertIn(body["release"], above)
        self.assertTrue(has_number(above, 9), above)
        self.assertTrue(has_number(above, SEQUENCES), above)
        self.assertIn(str(DAY.year), above)
        self.assertNotIn("Noch keine Importe.", root.text())


class ListTests(ImportCase):

    def test_newest_first(self) -> None:
        """Requirement: Imports page (a table lists the imports newest
        first)."""
        with ticking(berlin(2026, 11, 9, 8)):
            first = make_import()
            second = make_import(outcome="refused")
            third = make_import(base=first)
        _header, rows = table(page(self.client.get(IMPORTS)))
        self.assertEqual([row["Commit"].text() for row in rows],
                         [third.commit[:10], second.commit[:10],
                          first.commit[:10]])

    def test_every_trigger_has_its_word(self) -> None:
        """Requirement: Imports page (`Anlass`: `Commit`, `Register`,
        `Werkzeuge` or `Nachholen`)."""
        made = {trigger: make_import(trigger=trigger)
                for trigger in TRIGGERS_DE}
        _header, rows = table(page(self.client.get(IMPORTS)))
        for trigger, word in TRIGGERS_DE.items():
            with self.subTest(trigger=trigger):
                self.assertEqual(
                    row_of(rows, made[trigger].commit)["Anlass"].text(),
                    word)

    def test_the_english_page(self) -> None:
        """Requirement: Imports page (the English words)."""
        self.use_index(build_index("en"))
        made = {trigger: make_import(trigger=trigger)
                for trigger in TRIGGERS_EN}
        refusal = make_import(outcome="refused",
                              errors="a: error: b\nc: error: d")
        header, rows = table(page(self.client.get(IMPORTS)))
        self.assertEqual(header, COLUMNS_EN)
        for trigger, word in TRIGGERS_EN.items():
            with self.subTest(trigger=trigger):
                row = row_of(rows, made[trigger].commit)
                self.assertEqual(row["Trigger"].text(), word)
                self.assertEqual(row["Outcome"].text(), "Accepted")
        row = row_of(rows, refusal.commit)
        self.assertEqual(row["Outcome"].text(), "Refused")
        self.assertIn("a: error: b", row["Errors"].text())
        self.assertIn("c: error: d", row["Errors"].text())

    def test_errors_one_per_line(self) -> None:
        """Requirement: Imports page (`Fehler`, a refused import's
        errors, one per line)."""
        refusal = make_import(outcome="refused",
                              errors="first: error: one\nsecond: error: two")
        root = page(self.client.get(IMPORTS))
        _header, rows = table(root)
        cell = row_of(rows, refusal.commit)["Fehler"]
        self.assertIn("first: error: one", cell.text())
        self.assertIn("second: error: two", cell.text())
        self.assertLess(cell.text().index("first: error: one"),
                        cell.text().index("second: error: two"))


class LatestAcceptedTests(ImportCase):

    def test_the_line_names_the_latest_accepted_import(self) -> None:
        """Requirement: Imports page (the latest accepted import's
        commit, release and the numbers of procedures and sequences not
        withdrawn)."""
        with frozen(berlin(2026, 11, 20, 14, 35)):
            first = self.accept()
            data = demo_collection()
            data["procedures"] = [p for p in data["procedures"]
                                  if p["id"] not in ("OSDB-0003",
                                                     "OSDB-0006")]
            second = self.accept(data)
            report = self.send(refused(["x: error: y"],
                                       base=second.pk))
        self.assertEqual(report.json()["outcome"], "refused")
        root = page(self.client.get(IMPORTS))
        above = intro(root)
        self.assertIn(second.commit[:10], above)
        self.assertIn(second.release, above)
        self.assertNotIn(first.commit[:10], above)
        self.assertTrue(has_number(above, 7), above)
        self.assertFalse(has_number(above, 9), above)
        self.assertTrue(has_number(above, 2), above)
        self.assertEqual(len(table(root)[1]), 3)

    def test_without_an_accepted_import_there_is_no_line(self) -> None:
        """Requirement: Imports page (the line, when an import was
        accepted)."""
        refusal = make_import(outcome="refused")
        root = page(self.client.get(IMPORTS))
        self.assertNotIn(refusal.commit[:10], intro(root))
        self.assertEqual(len(table(root)[1]), 1)
