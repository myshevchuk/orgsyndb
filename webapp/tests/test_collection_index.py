"""Tests of the reader of the collection index (web-app: Collection
index)."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from django.test import SimpleTestCase

from orgsyndb_web import index

from . import (IndexMixin, build_index, compound, demo_data, demo_index,
               procedure, sequence, stamp, write_index)


class DemoLookupTests(IndexMixin, SimpleTestCase):

    def setUp(self) -> None:
        self.use_index(demo_index())

    def test_lookups_in_the_demo_collection(self) -> None:
        """Scenario: Lookups in the demo collection."""
        self.assertTrue(index.has_compound("cinnamic-acid"))
        self.assertFalse(index.has_compound("CH-0012"))
        self.assertEqual(index.procedure_for("OSDB-0008"), "OSDB-0008")
        found = index.sequence_for("SEQ-0001")
        self.assertEqual(found.id, "SEQ-0001")
        self.assertEqual(list(found.steps), ["OSDB-0001", "OSDB-0002"])
        self.assertIsNone(index.procedure_for("OSDB-9999"))
        self.assertIsNone(index.sequence_for("SEQ-9999"))

    def test_the_language_is_the_sites(self) -> None:
        self.assertEqual(index.current().language, "de")

    def test_second_sequence_has_its_own_steps(self) -> None:
        self.assertEqual(list(index.sequence_for("SEQ-0002").steps),
                         ["OSDB-0004", "OSDB-0009"])

    def test_every_demo_compound_key_is_listed_and_no_item_number(
            self) -> None:
        for entry in demo_data()["compounds"]:
            data = entry["data"]
            with self.subTest(key=entry["key"]):
                self.assertTrue(index.has_compound(entry["key"]))
                if "item_number" in data:
                    self.assertFalse(index.has_compound(
                        data["item_number"]))

    def test_an_unknown_key_is_not_listed(self) -> None:
        self.assertFalse(index.has_compound("no-such-compound"))
        self.assertFalse(index.has_compound(""))


class CompoundTests(IndexMixin, SimpleTestCase):
    """The index keeps the compound keys and nothing else of them."""

    def test_the_keys_alone(self) -> None:
        self.use_index(build_index("de", [
            compound("a", name="Acid", name_de="Säure", mw=18,
                     item_number="N-1"),
            compound("b")]))
        self.assertTrue(index.has_compound("a"))
        self.assertTrue(index.has_compound("b"))
        self.assertFalse(index.has_compound("c"))
        self.assertFalse(index.has_compound("N-1"))
        self.assertFalse(index.has_compound("Acid"))

    def test_no_compound_is_resolved_from_text(self) -> None:
        """The application takes no name, molar mass or identifier from
        the index."""
        self.assertFalse(hasattr(index, "compound_for"))


class SequenceTests(IndexMixin, SimpleTestCase):

    def steps(self, language: str, files: list[tuple[str | None, list[str]]]
              ) -> list[str] | None:
        self.use_index(build_index(language, sequences=[
            sequence("SEQ-0007", steps, code) for code, steps in files]))
        found = index.sequence_for("SEQ-0007")
        return None if found is None else list(found.steps)

    def test_file_in_the_site_language_wins(self) -> None:
        self.assertEqual(self.steps("de", [("en", ["E"]), ("de", ["D"]),
                                           (None, ["N"])]), ["D"])
        self.assertEqual(self.steps("en", [("de", ["D"]), ("en", ["E"]),
                                           (None, ["N"])]), ["E"])

    def test_file_without_a_language_code_comes_next(self) -> None:
        self.assertEqual(self.steps("de", [("en", ["E"]), (None, ["N"])]),
                         ["N"])
        self.assertEqual(self.steps("en", [("de", ["D"]), (None, ["N"])]),
                         ["N"])

    def test_file_in_another_language_comes_last(self) -> None:
        self.assertEqual(self.steps("de", [("en", ["E"])]), ["E"])
        self.assertEqual(self.steps("en", [("de", ["D"])]), ["D"])

    def test_steps_keep_their_order(self) -> None:
        self.assertEqual(self.steps("de", [(None, ["C", "A", "B"])]),
                         ["C", "A", "B"])


class ProcedureTests(IndexMixin, SimpleTestCase):

    def test_procedure_ids(self) -> None:
        self.use_index(build_index("de", procedures=[
            procedure("OSDB-0001", "de"), procedure("OSDB-0001"),
            procedure("OSDB-0002")]))
        self.assertEqual(index.procedure_for("OSDB-0001"), "OSDB-0001")
        self.assertEqual(index.procedure_for("OSDB-0002"), "OSDB-0002")
        self.assertIsNone(index.procedure_for("OSDB-0003"))


class MissingIndexTests(IndexMixin, SimpleTestCase):

    def assert_empty(self) -> None:
        self.assertEqual(index.current().language, "de")
        self.assertFalse(index.has_compound("cinnamic-acid"))
        self.assertIsNone(index.procedure_for("OSDB-0001"))
        self.assertIsNone(index.sequence_for("SEQ-0001"))

    def test_missing_file(self) -> None:
        self.use_index(None)
        self.assert_empty()

    def test_malformed_file(self) -> None:
        for text in ("{not json", "", "[1, 2]", "null"):
            with self.subTest(text=text):
                path = self.use_index(None)
                path.write_text(text)
                stamp(path)
                self.assert_empty()

    def test_unreadable_file(self) -> None:
        self.use_index(Path(tempfile.mkdtemp(prefix="osdb-dir-")))
        self.assert_empty()

    def test_missing_keys_are_no_data(self) -> None:
        self.use_index({"site_language": "en"})
        self.assertEqual(index.current().language, "en")
        self.assertFalse(index.has_compound("cinnamic-acid"))
        self.assertIsNone(index.sequence_for("SEQ-0001"))

    def test_empty_table_is_german(self) -> None:
        self.use_index({})
        self.assert_empty()

    def test_a_problem_is_logged_once_per_change_of_the_file(self) -> None:
        path = self.use_index(None)
        with self.assertLogs(level="WARNING") as logged:
            for _ in range(3):
                index.current()
            self.assertEqual(len(logged.records), 1)
            path.write_text("{not json")
            stamp(path)
            for _ in range(3):
                index.current()
            self.assertEqual(len(logged.records), 2)
            write_index(path, build_index("en"))
            for _ in range(3):
                self.assertEqual(index.current().language, "en")
            self.assertEqual(len(logged.records), 2)


class ReplacementTests(IndexMixin, SimpleTestCase):

    def test_index_replaced(self) -> None:
        """Scenario: Index replaced."""
        path = self.use_index(build_index("en"))
        self.assertEqual(index.current().language, "en")
        write_index(path, build_index("de"))
        self.assertEqual(index.current().language, "de")

    def test_replaced_content_is_looked_up(self) -> None:
        path = self.use_index(build_index("de", [compound("a")]))
        self.assertTrue(index.has_compound("a"))
        write_index(path, build_index("de", [compound("b")]))
        self.assertFalse(index.has_compound("a"))
        self.assertTrue(index.has_compound("b"))

    @unittest.skipUnless(hasattr(os, "symlink"), "no symlinks")
    def test_release_behind_a_symlink_changes(self) -> None:
        directory = Path(tempfile.mkdtemp(prefix="osdb-releases-"))
        self.addCleanup(shutil.rmtree, directory, True)
        first = write_index(directory / "first.json", build_index("en"))
        second = write_index(directory / "second.json", build_index("de"))
        os.utime(second, ns=(first.stat().st_atime_ns,
                             first.stat().st_mtime_ns))
        link = directory / "current.json"
        link.symlink_to(first.name)
        self.use_index(link)
        self.assertEqual(index.current().language, "en")
        link.unlink()
        link.symlink_to(second.name)
        self.assertEqual(index.current().language, "de")
