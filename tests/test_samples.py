"""The seed and sample procedures (sample-procedures)."""

import copy
import unittest

import sample_support as sup
from pipeline_support import FIXTURES, REPO

ORG_SEED = REPO / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
MD_SEED = REPO / "md" / "procedures" / "OSDB-0002-aspirin.md"


def samples() -> list[sup.Sample]:
    found = sup.sample_procedures(REPO)
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
                self.assertIn("not experimentally verified", sample.summary)


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
