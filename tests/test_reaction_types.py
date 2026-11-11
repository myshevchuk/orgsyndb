"""The collection's reaction types (reaction-types): the vocabulary of
the registry the validator reads, the reaction-type data the build stages
for the site, and the labels the built site takes from the registry.
"""

import json
import tempfile
import unittest
from pathlib import Path

import catalogue_support as cs
import pipeline_support as ps
import support
from pipeline_support import TEST_COLLECTION, pipeline_function
from support import (BASELINE, ValidatorTestCase, append_text, edit_procedure,
                     edit_procedure_settings, edit_registry, insert_line,
                     procedure_declaration, procedure_field_run,
                     registry_variant_run, replace_line, setting_terms,
                     term)

TEST_REGISTRY = TEST_COLLECTION / "registry.json"
UNKNOWN = 'unknown reaction type "esterification"'


def side_reaction_declaration() -> str:
    """The declaration of the procedure field ``side_reaction``, a
    ``choice`` over the vocabulary ``reaction-types``."""
    return procedure_declaration("side_reaction", "choice", "Side reaction",
                                 'vocabulary = "reaction-types"')


class ReactionTypeVocabularyTests(ValidatorTestCase):
    """Requirement: Reaction-type vocabulary."""

    def test_the_registrys_reaction_types(self) -> None:
        """Scenario: The registry's reaction types."""
        only = setting_terms("reaction-types", term(
            "reductive-amination", "Reductive amination", tree=False))
        edit = replace_line("reaction_types",
                            'reaction_types = ["reductive-amination"]')
        with support.registry_copy() as registry:
            edit_registry(only)(registry)
            with support.variant_root(BASELINE.name, edit) as root:
                first = support.fixture_run(root, registry=registry)
            second = support.fixture_run(
                support.FIXTURES / "baseline", registry=registry)
        self.assert_clean(first)
        problem = self.assert_one(second, "error", "reaction_types", UNKNOWN)
        self.assertNotIn("vocabularies/", problem.message)

    def test_a_registry_without_reaction_types(self) -> None:
        """Requirement: Reaction-type vocabulary (a registry without
        reaction types gives the collection none)."""
        result = registry_variant_run(edit_registry(
            setting_terms("reaction-types")))
        self.assert_one(result, "error", "reaction_types", UNKNOWN)

    def test_the_reaction_types_come_from_the_registry_alone(self) -> None:
        """Requirement: Reaction-type vocabulary (no file of the
        collection names them)."""
        with tempfile.TemporaryDirectory() as cwd:
            directory = Path(cwd)
            (directory / "vocabularies").mkdir()
            (directory / "vocabularies" / "reaction-types.toml").write_text(
                '[reductive-amination]\nlabel = "Reductive amination"\n',
                encoding="utf-8")
            result = support.run_validator(
                ["--registry", support.REGISTRY, "--static-dir",
                 support.STATIC_DIR, support.FIXTURES / "baseline"],
                cwd=directory)
        self.assert_clean(result)

    def test_a_declared_field_names_the_reaction_types(self) -> None:
        """Scenario: A declared field names the reaction types."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(side_reaction_declaration())),
            edit_procedure(BASELINE.name,
                           insert_line('side_reaction = "reduction"')))
        self.assert_clean(result)

    def test_a_declared_field_checks_its_value_against_the_registry(
            self) -> None:
        """Requirement: Reaction-type vocabulary (a declared field reads
        the vocabulary as any declaration does)."""
        result = procedure_field_run(
            edit_procedure_settings(append_text(side_reaction_declaration())),
            edit_procedure(BASELINE.name,
                           insert_line('side_reaction = "oxidation"')))
        problem = self.assert_one(result, "error", "side_reaction",
                                  "oxidation")
        self.assertIn("reaction-types", problem.message)
        self.assertTrue(problem.path.endswith(BASELINE.name), problem.path)


class ReactionTypeDataTests(unittest.TestCase):
    """Requirement: Reaction-type data for the site."""

    def registry(self) -> dict:
        return json.loads(TEST_REGISTRY.read_text(encoding="utf-8"))

    def data(self, registry: dict, language: str) -> dict:
        return pipeline_function("reaction_types_data")(registry, language)

    def test_labels_in_either_language(self) -> None:
        """Scenario: Labels in either language."""
        registry = self.registry()
        keys = [t["key"] for t in registry["vocabularies"]["reaction-types"]]
        self.assertIn("aldol-condensation", keys)
        results = {language: self.data(registry, language)
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
        data = self.data(self.registry(), "en")
        self.assertEqual(json.loads(json.dumps(data)), data)

    def test_a_term_without_a_german_label(self) -> None:
        """Scenario: A term without a German label."""
        registry = self.registry()
        for entry in registry["vocabularies"]["reaction-types"]:
            if entry["key"] == "esterification":
                entry["label_de"] = None
        data = self.data(registry, "de")
        self.assertEqual(data["esterification"], {"label": "Esterification"})
        self.assertEqual(data["aldol-condensation"],
                         {"label": "Aldolkondensation"})

    def test_a_german_label_is_used_only_on_a_german_site(self) -> None:
        """Requirement: Reaction-type data for the site (`label_de` when
        the language is `de`, `label` otherwise)."""
        registry = self.registry()
        self.assertEqual(self.data(registry, "en")["esterification"],
                         {"label": "Esterification"})
        self.assertEqual(self.data(registry, "de")["esterification"],
                         {"label": "Veresterung"})

    def test_no_reaction_types(self) -> None:
        """Scenario: No reaction types."""
        registry = self.registry()
        registry["vocabularies"]["reaction-types"] = []
        for language in ("en", "de"):
            with self.subTest(language=language):
                self.assertEqual(self.data(registry, language), {})

    def test_only_the_reaction_types_are_listed(self) -> None:
        """Requirement: Reaction-type data for the site (one key per
        reaction type of the registry)."""
        registry = self.registry()
        data = self.data(registry, "en")
        self.assertFalse(set(data) & {t["key"] for t in
                                      registry["vocabularies"]["projects"]})


class ReactionTypeSiteTests(cs.CatalogueCase):
    """Scenario: The site takes its labels from the registry."""

    LOCALE = "en"
    NEW_LABEL = "Ester formation"
    OTHER_LABEL = "Acyl transfer"

    @classmethod
    def prepare(cls) -> None:
        def relabel(table: dict) -> None:
            labels = {"esterification": cls.NEW_LABEL,
                      "acylation": cls.OTHER_LABEL}
            for entry in table["vocabularies"]["reaction-types"]:
                if entry["key"] in labels:
                    entry["label"] = labels[entry["key"]]
        ps.edit_snapshot(cls.sandbox, relabel)

    def esterifications(self) -> list[ps.Content]:
        found = [item for item in self.content()
                 if item.data["reaction_types"] == ["esterification"]]
        self.assertTrue(found, "no published procedure is an esterification")
        return found

    def test_the_term_page_and_the_list_use_the_collections_label(
            self) -> None:
        """Scenario: The site takes its labels from the registry (the
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
        """Scenario: The site takes its labels from the registry (the
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
