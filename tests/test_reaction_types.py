"""The collection's reaction types (reaction-types): the vocabulary file
the validator reads, the starter vocabulary in ``templates/``, the
reaction-type data the build stages for the site, and the labels the
built site takes from the collection.
"""

import json
import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

import catalogue_support as cs
import pipeline_support as ps
from pipeline_support import TEST_COLLECTION, pipeline, pipeline_function
from support import (BASELINE, COMPOUNDS, FIXTURES, SETTINGS,
                     STARTER_REACTION_TYPES, STATIC_DIR, ValidatorTestCase,
                     append_text, delete_procedure_vocabulary,
                     delete_reaction_types, edit_procedure,
                     edit_procedure_settings, edit_reaction_types,
                     insert_line, procedure_declaration,
                     procedure_field_run, replace_line, replace_text,
                     run_validator, settings_variant_run, variant_root,
                     write_reaction_types)

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STARTER_VALUES = ["acylation", "aldol-condensation", "cross-coupling",
                  "esterification", "olefination", "protection",
                  "reduction", "reductive-amination"]
UNKNOWN = 'unknown reaction type "esterification"'
FILE = "vocabularies/reaction-types.toml"


def side_reaction_declaration() -> str:
    """The declaration of the procedure field ``side_reaction``, a
    ``choice`` over the vocabulary ``reaction-types``."""
    return procedure_declaration("side_reaction", "choice", "Side reaction",
                                 'vocabulary = "reaction-types"')


class ReactionTypeVocabularyTests(ValidatorTestCase):
    """Requirement: Reaction-type vocabulary."""

    def assert_configuration_error(self, result, *needles: str) -> None:
        """Exit status 2, nothing on stdout, and every needle on
        stderr."""
        self.assertEqual(result.returncode, 2,
                         f"stdout={result.stdout!r} "
                         f"stderr={result.stderr!r}")
        self.assertEqual(result.stdout, "")
        for needle in needles:
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stderr)

    def test_the_working_directorys_reaction_types(self) -> None:
        """Scenario: The working directory's reaction types."""
        edit = replace_line("reaction_types",
                            'reaction_types = ["reductive-amination"]')
        with tempfile.TemporaryDirectory() as cwd:
            directory = Path(cwd)
            (directory / "vocabularies").mkdir()
            (directory / "vocabularies" / "reaction-types.toml").write_text(
                '[reductive-amination]\nlabel = "Reductive amination"\n',
                encoding="utf-8")
            args = ["--compounds", COMPOUNDS, "--static-dir", STATIC_DIR]
            with variant_root(BASELINE.name, edit) as root:
                first = run_validator([*args, root], cwd=directory)
            second = run_validator([*args, FIXTURES / "baseline"],
                                   cwd=directory)
        self.assert_clean(first)
        self.assert_one(second, "error", "reaction_types", UNKNOWN)
        self.assertIn(FILE, second.problems[0].message)

    def test_the_settings_file_outranks_the_working_directory(self) -> None:
        """Requirement: Reaction-type vocabulary (from the directory of
        the settings file it reads)."""
        with tempfile.TemporaryDirectory() as cwd:
            directory = Path(cwd)
            (directory / "vocabularies").mkdir()
            (directory / "vocabularies" / "reaction-types.toml").write_text(
                '[reductive-amination]\nlabel = "Reductive amination"\n',
                encoding="utf-8")
            result = run_validator(
                ["--settings", SETTINGS, "--compounds", COMPOUNDS,
                 "--static-dir", STATIC_DIR, FIXTURES / "baseline"],
                cwd=directory)
        self.assert_clean(result)

    def test_a_collection_without_reaction_types(self) -> None:
        """Scenario: A collection without reaction types."""
        result = settings_variant_run(delete_reaction_types())
        problem = self.assert_one(result, "error", "reaction_types",
                                  UNKNOWN)
        self.assertIn(FILE, problem.message)

    def test_a_vocabularies_directory_without_the_file(self) -> None:
        """Requirement: Reaction-type vocabulary (a collection without
        the file has no reaction type)."""
        def empty_directory(copy) -> None:
            for path in copy.vocabularies.iterdir():
                path.unlink()
        result = settings_variant_run(empty_directory)
        self.assert_one(result, "error", "reaction_types", UNKNOWN)

    def test_a_collection_of_compounds_alone_validates(self) -> None:
        """Requirement: Reaction-type vocabulary (a missing file is no
        configuration error)."""
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "content"
            empty.mkdir()
            result = settings_variant_run(delete_reaction_types(),
                                          roots=[empty])
        self.assert_clean(result)

    def test_a_declared_field_names_the_reaction_types(self) -> None:
        """Scenario: A declared field names the reaction types."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(side_reaction_declaration())),
            edit_procedure(BASELINE.name,
                           insert_line('side_reaction = "reduction"')))
        self.assert_clean(result)

    def test_a_declared_field_checks_its_value_against_the_file(
            self) -> None:
        """Requirement: Reaction-type vocabulary (a declared field reads
        the vocabulary as any declaration does)."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(side_reaction_declaration())),
            edit_procedure(BASELINE.name,
                           insert_line('side_reaction = "oxidation"')))
        problem = self.assert_one(result, "error", "side_reaction",
                                  "oxidation")
        self.assertTrue(problem.path.endswith(BASELINE.name), problem.path)

    def test_a_declared_field_needs_the_file(self) -> None:
        """Scenario: A declared field needs the file."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(side_reaction_declaration())),
            delete_procedure_vocabulary("reaction-types"))
        self.assert_configuration_error(
            result, "validate.py: error:", "side_reaction",
            "reaction-types.toml")

    def test_a_broken_file_is_an_error_though_no_declaration_names_it(
            self) -> None:
        """Requirement: Reaction-type vocabulary (the validator reads the
        file whether or not a declaration names it)."""
        result = settings_variant_run(write_reaction_types("[reduction\n"))
        self.assert_configuration_error(
            result, "validate.py: error:", "reaction-types.toml")

    def test_nested_reaction_types_are_refused(self) -> None:
        """Scenario: Nested reaction types are refused."""
        result = settings_variant_run(edit_reaction_types(replace_text(
            "[reduction]\n", '[reduction]\nparent = "esterification"\n')))
        self.assert_configuration_error(
            result, "validate.py: error:", "reaction-types.toml",
            "reduction", "parent")

    def test_a_parent_is_refused_whatever_it_names(self) -> None:
        """Requirement: Reaction-type vocabulary (no value takes
        `parent`)."""
        for parent in ('"oxidation"', '"reduction"', "5"):
            with self.subTest(parent=parent):
                result = settings_variant_run(edit_reaction_types(
                    replace_text("[reduction]\n",
                                 f"[reduction]\nparent = {parent}\n")))
                self.assert_configuration_error(
                    result, "validate.py: error:", "reaction-types.toml",
                    "reduction", "parent")

    def test_an_entry_key_outside_the_vocabulary_format(self) -> None:
        """Scenario: An entry key outside the vocabulary format."""
        result = settings_variant_run(edit_reaction_types(replace_text(
            "[reduction]\n", '[reduction]\nnote = "x"\n')))
        self.assert_configuration_error(
            result, "reaction-types.toml", "reduction", "note")


class StarterReactionTypesTests(ValidatorTestCase):
    """Requirement: Starter reaction types."""

    def starter(self) -> dict:
        self.assertTrue(STARTER_REACTION_TYPES.is_file(),
                        "templates/reaction-types.toml does not exist")
        return tomllib.loads(
            STARTER_REACTION_TYPES.read_text(encoding="utf-8"))

    def test_the_starter_vocabulary_is_well_formed_and_complete(
            self) -> None:
        """Scenario: The starter vocabulary is well formed and
        complete."""
        data = self.starter()
        for key, entry in data.items():
            with self.subTest(value=key):
                self.assertRegex(key, SLUG)
                self.assertIsInstance(entry, dict)
                self.assertEqual(sorted(entry), ["label", "label_de"])
                for name in ("label", "label_de"):
                    self.assertIsInstance(entry[name], str)
                    self.assertNotEqual(entry[name].strip(), "")
        self.assertLessEqual(set(STARTER_VALUES), set(data))
        first = STARTER_REACTION_TYPES.read_text(
            encoding="utf-8").splitlines()[0]
        self.assertTrue(first.startswith("#"), first)

    def test_the_starter_vocabulary_comments_state_its_purpose(
            self) -> None:
        """Requirement: Starter reaction types (it starts with comment
        lines)."""
        self.starter()
        lines = STARTER_REACTION_TYPES.read_text(
            encoding="utf-8").splitlines()
        comment = []
        for line in lines:
            if not line.startswith("#"):
                break
            comment.append(line)
        self.assertGreaterEqual(len(comment), 2, "no comment block")
        self.assertIn("reaction type", " ".join(comment).lower())

    def test_the_validator_accepts_the_starter_vocabulary(self) -> None:
        """Scenario: The validator accepts the starter vocabulary."""
        self.starter()
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "content"
            empty.mkdir()
            result = settings_variant_run(
                write_reaction_types(STARTER_REACTION_TYPES.read_bytes()),
                roots=[empty])
        self.assert_clean(result)

    def test_the_starter_vocabulary_names_the_stub_reaction_type(
            self) -> None:
        """Requirement: Starter reaction types (`new` stubs name a value
        a new collection has)."""
        self.assertIn("esterification", self.starter())


def copy_collection_settings(target: Path) -> Path:
    """Copy the test collection's ``orgsyndb.toml`` and ``vocabularies/``
    into ``target`` and return the copy of the settings file."""
    target.mkdir(parents=True)
    shutil.copyfile(TEST_COLLECTION / "orgsyndb.toml",
                    target / "orgsyndb.toml")
    shutil.copytree(TEST_COLLECTION / "vocabularies",
                    target / "vocabularies")
    return target / "orgsyndb.toml"


class ReactionTypeDataTests(unittest.TestCase):
    """Requirement: Reaction-type data for the site."""

    def temporary(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="reaction types "))
        self.addCleanup(shutil.rmtree, directory, True)
        return directory

    def edited_copy(self, *edits) -> Path:
        """A copy of the test collection's settings and vocabularies whose
        ``reaction-types.toml`` has the text ``edits`` applied."""
        settings = copy_collection_settings(self.temporary() / "collection")
        path = settings.parent / "vocabularies" / "reaction-types.toml"
        text = path.read_text(encoding="utf-8")
        for edit in edits:
            text = edit(text)
        path.write_text(text, encoding="utf-8")
        return settings

    def test_labels_in_either_language(self) -> None:
        """Scenario: Labels in either language."""
        reaction_types_data = pipeline_function("reaction_types_data")
        keys = list(tomllib.loads(
            (TEST_COLLECTION / "vocabularies" / "reaction-types.toml"
             ).read_text(encoding="utf-8")))
        self.assertIn("aldol-condensation", keys)
        results = {language: reaction_types_data(
            TEST_COLLECTION / "orgsyndb.toml", language)
            for language in ("en", "de")}
        for language, data in results.items():
            with self.subTest(language=language):
                self.assertIsInstance(data, dict)
                self.assertEqual(sorted(data), sorted(keys))
                for key, entry in data.items():
                    self.assertEqual(list(entry), ["label"], key)
                    self.assertIsInstance(entry["label"], str)
        self.assertEqual(results["en"]["aldol-condensation"],
                         {"label": "Aldol condensation"})
        self.assertEqual(results["de"]["aldol-condensation"],
                         {"label": "Aldolkondensation"})

    def test_the_data_is_plain_json(self) -> None:
        """Requirement: Reaction-type data for the site (the build stages
        it as JSON)."""
        data = pipeline_function("reaction_types_data")(
            TEST_COLLECTION / "orgsyndb.toml", "en")
        self.assertEqual(json.loads(json.dumps(data)), data)

    def test_a_value_without_a_german_label(self) -> None:
        """Scenario: A value without a German label."""
        settings = self.edited_copy(lambda text: re.sub(
            r'(\[esterification\]\nlabel = "[^"]*"\n)label_de = "[^"]*"\n',
            r"\1", text, count=1))
        text = (settings.parent / "vocabularies" / "reaction-types.toml"
                ).read_text(encoding="utf-8")
        self.assertIn('[esterification]\nlabel = "Esterification"\n\n', text)
        data = pipeline_function("reaction_types_data")(settings, "de")
        self.assertEqual(data["esterification"], {"label": "Esterification"})
        self.assertEqual(data["aldol-condensation"],
                         {"label": "Aldolkondensation"})

    def test_no_reaction_types(self) -> None:
        """Scenario: No reaction types."""
        reaction_types_data = pipeline_function("reaction_types_data")
        directory = self.temporary()
        (directory / "orgsyndb.toml").write_text("format = 1\n",
                                                 encoding="utf-8")
        for language in ("en", "de"):
            with self.subTest(language=language):
                self.assertEqual(reaction_types_data(
                    directory / "orgsyndb.toml", language), {})

    def test_a_vocabularies_directory_without_the_file_gives_no_reaction_types(
            self) -> None:
        """Requirement: Reaction-type data for the site (a file that does
        not exist gives an empty table)."""
        directory = self.temporary()
        (directory / "orgsyndb.toml").write_text("format = 1\n",
                                                 encoding="utf-8")
        (directory / "vocabularies").mkdir()
        self.assertEqual(pipeline_function("reaction_types_data")(
            directory / "orgsyndb.toml", "en"), {})

    def test_a_broken_vocabulary(self) -> None:
        """Scenario: A broken vocabulary."""
        settings = self.edited_copy(replace_text(
            "[reduction]\n", '[reduction]\nparent = "oxidation"\n'))
        with self.assertRaises(pipeline().validate.ConfigError):
            pipeline_function("reaction_types_data")(settings, "en")

    def test_every_rule_of_the_vocabulary_is_checked(self) -> None:
        """Requirement: Reaction-type data for the site (it raises
        `validate.ConfigError` when the file breaks a rule)."""
        error = pipeline().validate.ConfigError
        cases = {
            "a parent": replace_text(
                "[reduction]\n", '[reduction]\nparent = "esterification"\n'),
            "an unknown key": replace_text(
                "[reduction]\n", '[reduction]\nnote = "x"\n'),
            "an empty label_de": replace_text(
                "[reduction]\n", '[reduction]\nlabel_de = " "\n'),
            "not TOML": lambda text: text + "[reduction\n",
        }
        for name, edit in cases.items():
            with self.subTest(case=name):
                settings = self.edited_copy(edit)
                with self.assertRaises(error):
                    pipeline_function("reaction_types_data")(settings, "en")

    def test_the_data_is_read_beside_the_settings_file(self) -> None:
        """Requirement: Reaction-type data for the site (the file of the
        directory of the settings file)."""
        self.assertEqual(
            pipeline_function("reaction_types_data")(SETTINGS, "de"),
            {"esterification": {"label": "Esterification"},
             "reduction": {"label": "Reduction"}})


class ReactionTypeSiteTests(cs.CatalogueCase):
    """Scenario: The site takes its labels from the collection."""

    LOCALE = "en"
    NEW_LABEL = "Ester formation"
    OTHER_LABEL = "Acyl transfer"

    @classmethod
    def prepare(cls) -> None:
        path = cls.sandbox.root / "vocabularies" / "reaction-types.toml"
        text = path.read_text(encoding="utf-8")
        old = '[esterification]\nlabel = "Esterification"\n'
        if text.count(old) != 1:
            raise AssertionError("the test collection's esterification "
                                 "entry has changed")
        other = '[acylation]\nlabel = "Acylation"\n'
        if text.count(other) != 1:
            raise AssertionError("the test collection's acylation entry "
                                 "has changed")
        path.write_text(text.replace(
            old, f'[esterification]\nlabel = "{cls.NEW_LABEL}"\n').replace(
            other, f'[acylation]\nlabel = "{cls.OTHER_LABEL}"\n'),
            encoding="utf-8")

    def esterifications(self) -> list[ps.Content]:
        found = [item for item in self.content()
                 if item.data["reaction_types"] == ["esterification"]]
        self.assertTrue(found, "no published procedure is an esterification")
        return found

    def test_the_term_page_and_the_list_use_the_collections_label(
            self) -> None:
        """Scenario: The site takes its labels from the collection (the
        term page and the list)."""
        page = self.page("reaction_types/esterification/index.html")
        self.assertEqual(page.find("h1").norm(), self.NEW_LABEL)
        directory = self.page("reaction_types/index.html")
        links = {link.target: link.node.norm() for link in directory.links(
            directory.find("ul", "term-list"))}
        self.assertEqual(links["/reaction_types/esterification/"],
                         self.NEW_LABEL)

    def test_the_panel_and_the_table_row_use_the_collections_label(
            self) -> None:
        """Scenario: The site takes its labels from the collection (the
        metadata panel and the procedure table row)."""
        table = self.page("procedures/index.html")
        rows = {ps.row_cells(row)[0].norm(): ps.row_cells(row)
                for row in ps.catalogue_rows(table)}
        for item in self.esterifications():
            with self.subTest(procedure=item.id):
                page = self.page(f"procedures/{item.slug}/index.html")
                pairs = {pair.label: pair for pair in page.definition_pairs(
                    page.find("dl", "metadata"))}
                self.assertEqual(pairs["Reaction type"].definition.norm(),
                                 self.NEW_LABEL)
                self.assertEqual(rows[item.id][2].norm(), self.NEW_LABEL)

    def test_a_sequence_page_uses_the_collections_label(self) -> None:
        """Requirement: Reaction-type data for the site (wherever the site
        shows a label: the steps of a sequence)."""
        shown = []
        for path in sorted((self.public / "sequences").glob("*/index.html")):
            page = ps.load_page(self.public, path)
            shown += [span.norm() for span in
                      page.find_all("span", "sequence-step__type")]
        self.assertIn(self.OTHER_LABEL, shown)
        self.assertNotIn("Acylation", shown)

    def test_the_facet_uses_the_collections_label(self) -> None:
        """Requirement: Reaction-type data for the site (wherever the site
        shows a label: the catalogue's reaction-type facet)."""
        facet = dict(ps.facet_values(self.page("procedures/index.html"),
                                     "type"))
        self.assertEqual(facet["esterification"], self.NEW_LABEL)


if __name__ == "__main__":
    unittest.main()
