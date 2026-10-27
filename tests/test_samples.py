"""The seed and sample procedures (sample-procedures)."""

import copy
import re
import tempfile
import unittest
from pathlib import Path

import sample_support as sup
from pipeline_support import DEMO, FIXTURES, REPO

ORG_SEED = DEMO / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
MD_SEED = DEMO / "md" / "procedures" / "OSDB-0002-aspirin.md"
COLLECTION = FIXTURES / "collection"


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
    "md/procedures/OSDB-0005-1-biphenyl-4-yl-ethanol.md": (
        "OSDB-0005", "reduction", ["OSDB-0004"], "C14H14O", "3562-73-0"),
    "md/procedures/OSDB-0006-dibenzylideneacetone.md": (
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
            sum(s.path.suffix == ".org" for s in found), 4,
            "number of Org samples")
        self.assertEqual(
            sum(s.path.suffix == ".md" for s in found), 4,
            "number of Markdown samples")
        self.assertGreaterEqual(
            len({r for s in found for r in s.data.get("reaction_types", [])}),
            5)
        by_id = {s.data.get("id"): s for s in found}
        for sample in found:
            for precursor in sample.data.get("precursors", []):
                with self.subTest(chain=f"{precursor} -> {sample.path.name}"):
                    self.assertEqual(by_id[precursor].path.suffix, ".org")
                    self.assertEqual(sample.path.suffix, ".md")
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


ORG_SOURCE = """\
#+TITLE: Test acetate
#+CREATED: [2026-07-20 Mon 09:58:17]
#+LAST_MODIFIED: [2026-07-20 Mon 10:04:12]
#+AI_MODEL: model-x
#+HUGO_SLUG: osdb-0990
#+HUGO_TAGS: sample-data first second
#+HUGO_CUSTOM_FRONT_MATTER: :id "OSDB-0990"
#+HUGO_CUSTOM_FRONT_MATTER: :yield_percent 70
#+HUGO_CUSTOM_FRONT_MATTER: :product '((name . "Test") (formula . "C2H4"))

* Summary
A sample with /italic/ text, a C=O stretch and an E/Z ratio that
is wrapped
at a column.

* Reagents
| Reagent | CAS      |
|---------+----------|
| Water   | 7732-18-5 |
"""
MD_SOURCE = """\
+++
id = "OSDB-0990"
slug = "osdb-0990"
title = "Test acetate"
date = 2026-07-20T09:58:17+02:00
lastmod = 2026-07-20T10:04:12+02:00
yield_percent = 70
tags = ["sample-data", "first", "second"]
ai_model = "model-x"

[product]
name = "Test"
formula = "C2H4"
+++

## Summary

A sample with *italic* text, a C=O stretch and an E/Z ratio that is
wrapped at a column.

## Reagents

| Reagent | CAS |
|---|---|
| Water | 7732-18-5 |
"""


class AgreementCheckerTests(unittest.TestCase):
    """The agreement check must reject what the spec forbids, or the
    collection tests would hold nothing."""

    def differences(self, markdown: str,
                    source: str = ORG_SOURCE) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            org, md = Path(tmp, "OSDB-0990-test.org"), Path(
                tmp, "OSDB-0990-test.md")
            org.write_text(source, encoding="utf-8")
            md.write_text(markdown, encoding="utf-8")
            return sup.agreement_differences(org, md)

    def test_rewrapping_and_emphasis_markers_are_accepted(self) -> None:
        """Scenario: The agreement check (checker, accepted)."""
        self.assertEqual(self.differences(MD_SOURCE), [])

    def test_each_disagreement_is_rejected(self) -> None:
        """Scenario: The agreement check (checker, rejected)."""
        broken = {
            "changed word": MD_SOURCE.replace("stretch", "stretches"),
            "C=O as CO": MD_SOURCE.replace("C=O", "CO"),
            "E/Z as EZ": MD_SOURCE.replace("E/Z", "EZ"),
            "changed Reagents cell": MD_SOURCE.replace(
                "7732-18-5", "7732-18-6"),
            "renamed heading": MD_SOURCE.replace(
                "## Summary", "## Abstract"),
            "lastmod a minute later": MD_SOURCE.replace(
                "10:04:12+02:00", "10:05:12+02:00"),
            "summer date with +01:00": MD_SOURCE.replace(
                "09:58:17+02:00", "09:58:17+01:00"),
            "extra front-matter key": MD_SOURCE.replace(
                "yield_percent = 70\n", "yield_percent = 70\nscale = \"1\"\n"),
        }
        for change, markdown in broken.items():
            with self.subTest(change=change):
                self.assertNotEqual(markdown, MD_SOURCE)
                self.assertNotEqual(self.differences(markdown), [])

    def test_ai_model_only_where_the_source_names_one(self) -> None:
        """Scenario: The agreement check (checker, no AI model)."""
        source = ORG_SOURCE.replace("#+AI_MODEL: model-x\n", "")
        self.assertNotEqual(source, ORG_SOURCE)
        self.assertEqual(self.differences(
            MD_SOURCE.replace('ai_model = "model-x"\n', ""), source), [])
        self.assertNotEqual(self.differences(MD_SOURCE, source), [])

    def test_fall_back_hour_takes_the_exported_instants(self) -> None:
        """Scenario: The agreement check (checker, fall-back hour)."""
        source = ORG_SOURCE.replace(
            "[2026-07-20 Mon 09:58:17]", "[2026-10-25 Sun 02:50:00]"
        ).replace("[2026-07-20 Mon 10:04:12]", "[2026-10-25 Sun 02:10:00]")
        markdown = MD_SOURCE.replace(
            "2026-07-20T09:58:17+02:00", "2026-10-25T02:50:00+02:00"
        ).replace("2026-07-20T10:04:12+02:00", "2026-10-25T02:10:00+01:00")
        self.assertEqual(self.differences(markdown, source), [])
        self.assertNotEqual(self.differences(markdown.replace(
            "2026-10-25T02:10:00+01:00", "2026-10-25T02:10:00+02:00"),
            source), [], "lastmod must not be earlier than date")
        self.assertNotEqual(self.differences(markdown.replace(
            "2026-10-25T02:50:00+02:00", "2026-10-25T02:50:00+01:00"),
            source), [], "date must be the earliest instant")


def sample_files() -> list[Path]:
    """The demo's sample procedure files, Org and Markdown."""
    return sorted(
        [*(DEMO / "org" / "procedures").glob("OSDB-*.org"),
         *(DEMO / "md" / "procedures").glob("OSDB-*.md")])


def relative_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix()
            for p in root.rglob("*") if p.is_file()}


class TestCollectionTests(unittest.TestCase):
    def test_the_collection_mirrors_the_demo(self) -> None:
        """Scenario: The test collection mirrors the demo."""
        self.assertTrue(COLLECTION.is_dir(), f"{COLLECTION} is missing")
        self.assertFalse((COLLECTION / "org").exists(), "org/ exists")
        copied = ["orgsyndb.toml", ".gitignore",
                  *sorted(f"static/{p}" for p in relative_files(
                      DEMO / "static"))]
        self.assertIn("static/structures/osdb-0003.svg", copied)
        for relative in copied:
            with self.subTest(file=relative):
                self.assertTrue((COLLECTION / relative).is_file(),
                                f"{relative} is missing")
                self.assertEqual((COLLECTION / relative).read_bytes(),
                                 (DEMO / relative).read_bytes())
        self.assertEqual(
            {p for p in relative_files(COLLECTION / "static")},
            relative_files(DEMO / "static"), "static/ files")
        names = {p.stem + ".md" if p.suffix == ".org" else p.name
                 for p in sample_files()}
        self.assertEqual(len(names), 16)
        self.assertEqual(
            relative_files(COLLECTION / "md" / "procedures"), names)
        for path in sample_files():
            if path.suffix == ".md":
                with self.subTest(file=path.name):
                    self.assertEqual(
                        (COLLECTION / "md" / "procedures"
                         / path.name).read_bytes(), path.read_bytes())

    def test_converted_samples_agree_with_their_org_sources(self) -> None:
        """Scenario: Converted samples agree with their Org sources."""
        self.assertTrue(COLLECTION.is_dir(), f"{COLLECTION} is missing")
        orgs = sorted((DEMO / "org" / "procedures").glob("OSDB-*.org"))
        self.assertEqual(len(orgs), 8)
        for org in orgs:
            converted = COLLECTION / "md" / "procedures" / (
                org.stem + ".md")
            with self.subTest(sample=converted.name):
                self.assertTrue(converted.is_file(),
                                f"{converted.name} is missing")
                self.assertEqual(
                    sup.agreement_differences(org, converted), [])
