"""The seed and sample procedures (sample-procedures)."""

import copy
import re
import unittest

import sample_support as sup
from pipeline_support import DEMO, FIXTURES, REPO

ORG_SEED = DEMO / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
MD_SEED = DEMO / "md" / "procedures" / "OSDB-0002-aspirin.md"


def samples() -> list[sup.Sample]:
    found = sup.sample_procedures(DEMO)
    if not found:
        raise AssertionError("no procedure is tagged sample-data")
    return found


class SeedProcedureTests(unittest.TestCase):
    def test_seeds_exist_with_their_link(self) -> None:
        """Scenario: Seeds exist with their link."""
        self.assertTrue(ORG_SEED.is_file(), f"{ORG_SEED.name} is missing")
        self.assertTrue(MD_SEED.is_file(), f"{MD_SEED.name} is missing")
        org, md = sup.read_org(ORG_SEED), sup.read_markdown(MD_SEED)
        self.assertEqual(org.data.get("id"), "OSDB-0001")
        self.assertEqual(md.data.get("id"), "OSDB-0002")
        self.assertEqual(org.data.get("reaction_types"), ["hydrolysis"])
        self.assertEqual(md.data.get("reaction_types"), ["acylation"])
        self.assertEqual(md.data.get("precursors"), ["OSDB-0001"])


class SampleMarkingTests(unittest.TestCase):
    def test_samples_are_marked_as_samples(self) -> None:
        """Scenario: Seeds are marked as samples."""
        for sample in samples():
            with self.subTest(sample=sample.path.name):
                self.assertEqual(sample.data.get("status"), "draft")
                self.assertIn("sample-data", sample.data.get("tags", []))
                authors = sample.data.get("authors", [])
                self.assertTrue(authors)
                for author in authors:
                    self.assertRegex(author, r"^[A-Z]\. Example$")
                self.assertIsNotNone(sample.ai_model,
                                     "ai model absent or none")
                self.assertIn(sample.terms["unverified"],
                              " ".join(sample.summary.split()))


class SampleQuantityTests(unittest.TestCase):
    def test_reagent_tables_are_consistent(self) -> None:
        """Scenario: Seed tables are consistent."""
        for sample in samples():
            with self.subTest(sample=sample.path.name):
                self.assertEqual(sup.quantity_violations(sample), [])


class QuantityRuleCheckerTests(unittest.TestCase):
    """The checker must reject what the spec forbids, or the tests above
    would hold nothing."""

    def good(self) -> sup.Sample:
        sample = sup.read_org(FIXTURES / "export"
                              / "OSDB-0901-table-first.org")
        table = [sup.HEADER,
                 ["Methyl salicylate", "119-36-8", "152.15", "7.61 g (6 mL)",
                  "50.0", "1.0"],
                 ["Sodium hydroxide", "1310-73-2", "40.00", "6.00 g", "150",
                  "3.0"],
                 ["Phosphoric acid, 85 %", "7664-38-2", "97.99", "5 drops",
                  "cat.", "cat."]]
        data = copy.deepcopy(sample.data)
        data["scale"] = "50 mmol"
        data["product"] = {"formula": "C7H6O3", "mw": 138.12}
        return sample._replace(data=data, table=table)

    def test_a_consistent_table_has_no_violation(self) -> None:
        """Scenario: Seed tables are consistent (checker, accepted)."""
        self.assertEqual(sup.quantity_violations(self.good()), [])

    def test_each_rule_is_enforced(self) -> None:
        """Scenario: Seed tables are consistent (checker, rejected)."""
        base = self.good()

        def with_cell(row: int, col: int, value: str) -> sup.Sample:
            table = [list(r) for r in base.table]
            table[row][col] = value
            return base._replace(table=table)

        broken = {
            "mass vs mmol": with_cell(2, 4, "100"),
            "equiv": with_cell(2, 5, "2.0"),
            "CAS digit": with_cell(1, 1, "119-36-9"),
            "second limiting": with_cell(2, 5, "1.0"),
            "scale": base._replace(data=base.data | {"scale": "60 mmol"}),
            "product weight": base._replace(data=base.data | {
                "product": {"formula": "C7H6O3", "mw": 140.0}}),
            "columns": base._replace(table=[["Reagent"]]),
        }
        for rule, sample in broken.items():
            with self.subTest(rule=rule):
                self.assertNotEqual(sup.quantity_violations(sample), [])

    def german(self) -> sup.Sample:
        """The good table as a German translation writes it."""
        base = self.good()
        table = [sup.TERMS["de"]["header"],
                 ["Methylsalicylat", "119-36-8", "152,15", "7,61 g (6 mL)",
                  "50,0", "1,0"],
                 ["Natriumhydroxid", "1310-73-2", "40,00", "6,00 g", "150",
                  "3,0"],
                 ["Phosphorsäure, 85 %", "7664-38-2", "97,99", "5 Tropfen",
                  "kat.", "kat."]]
        return base._replace(path=base.path.with_suffix(".de.org"),
                             table=table)

    def test_a_german_table_is_read_with_decimal_commas(self) -> None:
        """Scenario: Translated sample tables are consistent (checker)."""
        german = self.german()
        self.assertEqual(german.language, "de")
        self.assertEqual(sup.quantity_violations(german), [])
        table = [list(r) for r in german.table]
        table[2][4] = "100"
        self.assertNotEqual(
            sup.quantity_violations(german._replace(table=table)), [])
        self.assertNotEqual(sup.quantity_violations(
            german._replace(table=self.good().table)), [],
            "a German sample must use the German columns")


EXPECTED_SAMPLES = {
    "org/procedures/OSDB-0003-isopentyl-acetate.org": (
        "OSDB-0003", "esterification", [], "C7H14O2", "123-92-2"),
    "org/procedures/OSDB-0004-4-acetylbiphenyl.org": (
        "OSDB-0004", "cross-coupling", [], "C14H12O", "92-91-1"),
    "org/procedures/OSDB-0005-1-biphenyl-4-yl-ethanol.org": (
        "OSDB-0005", "reduction", ["OSDB-0004"], "C14H14O", "3562-73-0"),
    "org/procedures/OSDB-0006-dibenzylideneacetone.org": (
        "OSDB-0006", "aldol-condensation", [], "C17H14O", "538-58-9"),
    "org/procedures/OSDB-0007-ethyl-cinnamate.org": (
        "OSDB-0007", "olefination", [], "C11H12O2", "103-36-6"),
    "md/procedures/OSDB-0008-cinnamic-acid.md": (
        "OSDB-0008", "hydrolysis", ["OSDB-0007"], "C9H8O2", "140-10-3"),
}
LONG_SAMPLE = DEMO / "org" / "procedures" / "OSDB-0004-4-acetylbiphenyl.org"
STRUCTURE_SAMPLE = (DEMO / "org" / "procedures"
                    / "OSDB-0003-isopentyl-acetate.org")


class ThemeSampleSetTests(unittest.TestCase):
    def test_set_counts_and_chains(self) -> None:
        """Scenario: Set, counts and chain."""
        for relative, (ident, reaction, precursors, formula, cas) in (
                EXPECTED_SAMPLES.items()):
            path = DEMO / relative
            with self.subTest(file=relative):
                self.assertTrue(path.is_file(), f"{relative} is missing")
                sample = (sup.read_org(path) if path.suffix == ".org"
                          else sup.read_markdown(path))
                self.assertEqual(sample.data.get("id"), ident)
                self.assertEqual(sample.data.get("reaction_types"),
                                 [reaction])
                self.assertEqual(sample.data.get("precursors", []),
                                 precursors)
                product = sample.data.get("product", {})
                self.assertEqual(product.get("formula"), formula)
                self.assertEqual(product.get("cas"), cas)
        found = [s for s in samples() if s.language == "en"]
        self.assertEqual(
            sum(s.path.suffix == ".org" for s in found), 6,
            "number of Org samples")
        self.assertEqual(
            sum(s.path.suffix == ".md" for s in found), 2,
            "number of Markdown samples")
        self.assertGreaterEqual(
            len({r for s in found for r in s.data.get("reaction_types", [])}),
            5)
        for sample in found:
            with self.subTest(sample=sample.path.name):
                self.assertTrue(sup.cas_ok(
                    sample.data.get("product", {}).get("cas", "")))
                self.assertTrue(
                    set(sample.data.get("tags", [])) - {"sample-data"},
                    "no tag besides sample-data")


class StructureImageSampleTests(unittest.TestCase):
    def test_isopentyl_acetate_sets_its_structure_image(self) -> None:
        """Scenario: Structure image is set."""
        self.assertTrue(STRUCTURE_SAMPLE.is_file(),
                        f"{STRUCTURE_SAMPLE.name} is missing")
        sample = sup.read_org(STRUCTURE_SAMPLE)
        self.assertEqual(sample.data.get("structure_image"),
                         "structures/osdb-0003.svg")
        self.assertTrue((DEMO / "static" / "structures"
                         / "osdb-0003.svg").is_file(),
                        "examples/demo/static/structures/osdb-0003.svg is "
                        "missing")


class LongSampleTests(unittest.TestCase):
    def test_the_acetylbiphenyl_sample_is_long(self) -> None:
        """Scenario: Long sample."""
        self.assertTrue(LONG_SAMPLE.is_file(), f"{LONG_SAMPLE.name} missing")
        text = LONG_SAMPLE.read_text(encoding="utf-8")
        sections = sup.org_sections(text)

        def numbered(name: str) -> int:
            return len(re.findall(r"(?m)^\d+\. ", sections.get(name, "")))

        self.assertGreaterEqual(numbered("Procedure"), 15)
        self.assertGreaterEqual(numbered("Notes"), 6)
        rows = sup.read_org(LONG_SAMPLE).table[1:]
        full = [r for r in rows if len(r) == 6 and r[4] != "cat."]
        self.assertGreaterEqual(len(full), 4)
        self.assertGreaterEqual(max((len(r[0]) for r in rows), default=0), 40)


class GermanSampleTests(unittest.TestCase):
    def test_every_sample_has_a_german_translation(self) -> None:
        """Scenario: Every sample has a German translation."""
        for relative in EXPECTED_SAMPLES:
            original = DEMO / relative
            translation = original.with_suffix(".de" + original.suffix)
            with self.subTest(file=translation.name):
                self.assertTrue(translation.is_file(),
                                f"{translation.name} is missing")
                read = (sup.read_org if original.suffix == ".org"
                        else sup.read_markdown)
                english, german = read(original), read(translation)
                self.assertEqual(german.language, "de")
                for key in ("id", "status", "reaction_types", "tags",
                            "yield_percent", "precursors",
                            "structure_image", "authors"):
                    self.assertEqual(german.data.get(key),
                                     english.data.get(key), key)
                for key in ("formula", "mw", "smiles", "cas"):
                    self.assertEqual(
                        german.data.get("product", {}).get(key),
                        english.data.get("product", {}).get(key), key)
                self.assertTrue(german.data.get("product", {}).get("name"))
                self.assertEqual(len(german.table), len(english.table))

    def test_the_german_long_sample_is_long(self) -> None:
        """Scenario: Every sample has a German translation (long
        sample)."""
        path = LONG_SAMPLE.with_suffix(".de.org")
        sections = sup.org_sections(path.read_text(encoding="utf-8"))
        terms = sup.TERMS["de"]

        def numbered(name: str) -> int:
            return len(re.findall(r"(?m)^\d+\. ", sections.get(name, "")))

        self.assertGreaterEqual(numbered(terms["procedure"]), 15)
        self.assertGreaterEqual(numbered(terms["notes"]), 6)
