"""The seed and sample procedures (sample-procedures)."""

import copy
import re
import tempfile
import tomllib
import unittest
from pathlib import Path

import sample_support as sup
import test_theme_static as tts
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
        self.assertEqual(
            [e["compound"] for e in org.data.get("products", [])],
            ["salicylic-acid"])
        self.assertEqual(org.data.get("substrates"), ["methyl-salicylate"])
        self.assertEqual(
            [e["compound"] for e in md.data.get("products", [])],
            ["acetylsalicylic-acid"])
        self.assertEqual(md.data.get("substrates"),
                         ["salicylic-acid", "acetic-anhydride"])
        self.assertEqual(
            set(md.data) & {"product", "yield_percent", "precursors",
                            "structure_image"}, set())


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


class CompoundWeightTests(unittest.TestCase):
    def test_compound_weights_agree_with_formulas(self) -> None:
        """Scenario: Seed tables are consistent (compound weights)."""
        registry = sup.read_registry(DEMO / "compounds")
        self.assertTrue(registry, "the demo registry holds no compound")
        for key, compound in registry.items():
            with self.subTest(compound=key):
                self.assertEqual(sup.compound_violations(key, compound), [])

    def test_the_weight_checker_rejects_what_the_spec_forbids(self) -> None:
        """Scenario: Seed tables are consistent (compound checker)."""
        good = {"formula": "C7H6O3", "mw": 138.12, "cas": "69-72-7"}
        self.assertEqual(sup.compound_violations("x", good), [])
        for change in ({"mw": 138.2}, {"mw": 140.0}, {"cas": "69-72-8"},
                       {"formula": "C7H6O"}):
            with self.subTest(change=change):
                self.assertNotEqual(
                    sup.compound_violations("x", good | change), [])
        boron = {"formula": "C6H7BO2", "mw": 121.93, "cas": "98-80-6"}
        self.assertEqual(sup.compound_violations("boron", boron), [])


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
        "OSDB-0003", "esterification", "isopentyl-acetate",
        ["isopentyl-alcohol", "acetic-acid"], "C7H14O2", "123-92-2"),
    "org/procedures/OSDB-0004-4-acetylbiphenyl.org": (
        "OSDB-0004", "cross-coupling", "4-acetylbiphenyl",
        ["4-bromoacetophenone", "phenylboronic-acid"], "C14H12O",
        "92-91-1"),
    "md/procedures/OSDB-0005-1-biphenyl-4-yl-ethanol.md": (
        "OSDB-0005", "reduction", "1-biphenyl-4-yl-ethanol",
        ["4-acetylbiphenyl"], "C14H14O", "3562-73-0"),
    "md/procedures/OSDB-0006-dibenzylideneacetone.md": (
        "OSDB-0006", "aldol-condensation", "dibenzylideneacetone",
        ["benzaldehyde", "acetone"], "C17H14O", "538-58-9"),
    "org/procedures/OSDB-0007-ethyl-cinnamate.org": (
        "OSDB-0007", "olefination", "ethyl-cinnamate",
        ["benzaldehyde", "ethyl-triphenylphosphoranylidene-acetate"],
        "C11H12O2", "103-36-6"),
    "md/procedures/OSDB-0008-cinnamic-acid.md": (
        "OSDB-0008", "hydrolysis", "cinnamic-acid", ["ethyl-cinnamate"],
        "C9H8O2", "140-10-3"),
}
CHAINS = {("OSDB-0001", "OSDB-0002"), ("OSDB-0004", "OSDB-0005"),
          ("OSDB-0004", "OSDB-0009"), ("OSDB-0007", "OSDB-0008")}
GENERAL_SAMPLE = "md/procedures/OSDB-0009-benzylic-alcohols.md"
GENERAL_SCOPE = [
    {"substrates": ["4-acetylbiphenyl"], "time": "30 min",
     "products": [{"compound": "1-biphenyl-4-yl-ethanol",
                   "yield_percent": 90}]},
    {"substrates": ["acetophenone"], "time": "20 min",
     "products": [{"compound": "1-phenylethanol", "yield_percent": 85}]},
    {"substrates": ["4-bromoacetophenone"], "time": "30 min",
     "scale": "5 mmol",
     "products": [{"compound": "1-4-bromophenyl-ethanol",
                   "yield_percent": 88}]},
]
GENERAL_COMPOUNDS = {
    "acetophenone": ["Acetophenone", "Acetophenon", "C8H8O", 120.15,
                     "CC(=O)c1ccccc1", "98-86-2"],
    "1-phenylethanol": ["1-Phenylethanol", "1-Phenylethanol", "C8H10O",
                        122.17, "CC(O)c1ccccc1", "98-85-1"],
    "1-4-bromophenyl-ethanol": [
        "1-(4-Bromophenyl)ethanol", "1-(4-Bromphenyl)ethanol", "C8H9BrO",
        201.06, "CC(O)c1ccc(Br)cc1", "5391-88-8"],
}
LONG_SAMPLE = DEMO / "org" / "procedures" / "OSDB-0004-4-acetylbiphenyl.org"
STRUCTURE_SAMPLE = (DEMO / "org" / "procedures"
                    / "OSDB-0003-isopentyl-acetate.org")


class ThemeSampleSetTests(unittest.TestCase):
    def test_set_counts_and_chains(self) -> None:
        """Scenario: Set, counts and chain."""
        registry = sup.read_registry(DEMO / "compounds")
        for relative, (ident, reaction, product, substrates, formula,
                       cas) in EXPECTED_SAMPLES.items():
            path = DEMO / relative
            with self.subTest(file=relative):
                self.assertTrue(path.is_file(), f"{relative} is missing")
                sample = (sup.read_org(path) if path.suffix == ".org"
                          else sup.read_markdown(path))
                self.assertEqual(sample.data.get("id"), ident)
                self.assertEqual(sample.data.get("reaction_types"),
                                 [reaction])
                self.assertEqual(
                    [e["compound"] for e in sample.data.get("products", [])],
                    [product])
                self.assertEqual(sample.data.get("substrates"), substrates)
                self.assertEqual(registry[product].get("formula"), formula)
                self.assertEqual(registry[product].get("cas"), cas)
        found = [s for s in samples() if s.language == "en"]
        self.assertEqual(
            sum(s.path.suffix == ".org" for s in found), 4,
            "number of Org samples")
        self.assertEqual(
            sum(s.path.suffix == ".md" for s in found), 5,
            "number of Markdown samples")
        self.assertGreaterEqual(
            len({r for s in found for r in s.data.get("reaction_types", [])}),
            5)
        makers = {key: s for s in found
                  for key in sup.product_keys(s.data)}
        chains = set()
        for sample in found:
            for key in sup.substrate_keys(sample.data):
                if key in makers:
                    maker = makers[key]
                    chains.add((maker.data["id"], sample.data["id"]))
                    with self.subTest(chain=f"{key} -> {sample.path.name}"):
                        self.assertEqual(maker.path.suffix, ".org")
                        self.assertEqual(sample.path.suffix, ".md")
        self.assertEqual(chains, CHAINS)
        used = {c for o in found for c in sup.substrate_keys(o.data)}
        made_and_used = [
            s.data["id"] for s in found
            if any(k in makers for k in sup.substrate_keys(s.data))
            and any(k in used for k in sup.product_keys(s.data))]
        self.assertEqual(made_and_used, [], "a procedure needing both links")
        for sample in found:
            with self.subTest(sample=sample.path.name):
                self.assertTrue(
                    set(sample.data.get("tags", [])) - {"sample-data"},
                    "no tag besides sample-data")
        for key, compound in registry.items():
            with self.subTest(compound=key):
                self.assertTrue(sup.cas_ok(compound.get("cas", "")))


class StructureImageSampleTests(unittest.TestCase):
    def test_isopentyl_acetate_sets_its_structure_image(self) -> None:
        """Scenario: Structure image is set."""
        compound = DEMO / "compounds" / "isopentyl-acetate.toml"
        self.assertTrue(compound.is_file(), f"{compound.name} is missing")
        self.assertEqual(
            tomllib.loads(compound.read_text(encoding="utf-8")).get(
                "structure_image"), "structures/isopentyl-acetate.svg")
        self.assertTrue((DEMO / "static" / "structures"
                         / "isopentyl-acetate.svg").is_file(),
                        "examples/demo/static/structures/"
                        "isopentyl-acetate.svg is missing")
        self.assertFalse((DEMO / "static" / "structures"
                          / "osdb-0003.svg").exists())


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
        for relative in [*EXPECTED_SAMPLES, GENERAL_SAMPLE]:
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
                            "products", "substrates", "authors",
                            "scheme_image"):
                    self.assertEqual(german.data.get(key),
                                     english.data.get(key), key)
                self.assertEqual(sup.scope_without_notes(german.data),
                                 sup.scope_without_notes(english.data))
                self.assertTrue(sup.product_keys(german.data))
                self.assertEqual(
                    set(german.data) & {"product", "yield_percent",
                                        "precursors", "structure_image"},
                    set())
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


class DemoGeneralProcedureTests(unittest.TestCase):
    """Scenario: The demo's general procedure."""

    def read(self, suffix: str) -> sup.Sample:
        path = (DEMO / "md" / "procedures"
                / f"OSDB-0009-benzylic-alcohols{suffix}.md")
        self.assertTrue(path.is_file(), f"{path.name} is missing")
        return sup.read_markdown(path)

    def test_the_procedure_carries_the_stated_scope(self) -> None:
        """Scenario: The demo's general procedure (the procedure)."""
        for suffix in ("", ".de"):
            sample = self.read(suffix)
            data = sample.data
            with self.subTest(variant=suffix or "en"):
                self.assertEqual(data["id"], "OSDB-0009")
                self.assertEqual(data["reaction_types"], ["reduction"])
                self.assertEqual(data["tags"],
                                 ["sample-data", "sodium-borohydride"])
                self.assertEqual(data["scale"], "10 mmol")
                self.assertEqual(data["scheme_image"],
                                 "structures/aryl-ketone-reduction.svg")
                self.assertNotIn("products", data)
                self.assertNotIn("substrates", data)
                self.assertEqual(sup.scope_without_notes(data),
                                 GENERAL_SCOPE)
                notes = [entry.get("note") for entry in data["scope"]]
                self.assertEqual([n is None for n in notes],
                                 [True, True, False])
                self.assertTrue(notes[2].strip())

    def test_the_scheme_image_is_safe_svg(self) -> None:
        """Scenario: The demo's general procedure (the image)."""
        path = DEMO / "static" / "structures" / "aryl-ketone-reduction.svg"
        self.assertTrue(path.is_file(), f"{path.name} is missing")
        check = tts.StructureImageTests(
            "test_every_shipped_image_is_safe_svg").check
        self.assertEqual(check(path), [])

    def test_the_registry_holds_the_three_compounds(self) -> None:
        """Scenario: The demo's general procedure (the compounds)."""
        keys = ["name", "name_de", "formula", "mw", "smiles", "cas"]
        registry = sup.read_registry(DEMO / "compounds")
        for key, values in GENERAL_COMPOUNDS.items():
            with self.subTest(compound=key):
                self.assertIn(key, registry)
                self.assertEqual(list(registry[key]), keys)
                self.assertEqual(list(registry[key].values()), values)

    def test_the_reagents_table_describes_entry_one(self) -> None:
        """Requirement: Demo general procedure (the Reagents table)."""
        for suffix in ("", ".de"):
            sample = self.read(suffix)
            with self.subTest(variant=suffix or "en"):
                self.assertEqual(sup.quantity_violations(sample), [])
                limiting = sample.table[1]
                self.assertEqual(limiting[0], "4-Acetylbiphenyl")
                self.assertEqual(sup.number(limiting[4]), 10.0)

    def test_it_is_not_among_the_newest(self) -> None:
        """Requirement: Demo general procedure (lastmod)."""
        def modified(sample: sup.Sample):
            if sample.path.suffix == ".md":
                return sample.data["lastmod"]
            keywords = sup.read_org_keywords(sample.path)
            return sup.berlin_instants(keywords["LAST_MODIFIED"])[-1]

        general = modified(self.read(""))
        others = [modified(s) for s in samples()
                  if s.language == "en" and s.data["id"] != "OSDB-0009"]
        self.assertEqual(len(others), 8)
        self.assertLessEqual(general, min(others))


ORG_SOURCE = """\
#+TITLE: Test acetate
#+CREATED: [2026-07-20 Mon 09:58:17]
#+LAST_MODIFIED: [2026-07-20 Mon 10:04:12]
#+AI_MODEL: model-x
#+HUGO_SLUG: osdb-0990
#+HUGO_TAGS: sample-data first second
#+HUGO_CUSTOM_FRONT_MATTER: :id "OSDB-0990"
#+HUGO_CUSTOM_FRONT_MATTER: :substrates '("water")
#+HUGO_CUSTOM_FRONT_MATTER: :products '(((compound . "test") (yield_percent . 70)))

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
substrates = ["water"]
products = [{ compound = "test", yield_percent = 70 }]
tags = ["sample-data", "first", "second"]
ai_model = "model-x"
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
                "substrates = [\"water\"]\n",
                "substrates = [\"water\"]\nscale = \"1\"\n"),
            "changed product yield": MD_SOURCE.replace(
                "yield_percent = 70", "yield_percent = 71"),
            "changed substrates": MD_SOURCE.replace(
                'substrates = ["water"]', 'substrates = ["steam"]'),
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
                      DEMO / "static")),
                  *sorted(f"compounds/{p}" for p in relative_files(
                      DEMO / "compounds"))]
        self.assertIn("static/structures/isopentyl-acetate.svg", copied)
        self.assertIn("compounds/salicylic-acid.toml", copied)
        for relative in copied:
            with self.subTest(file=relative):
                self.assertTrue((COLLECTION / relative).is_file(),
                                f"{relative} is missing")
                self.assertEqual((COLLECTION / relative).read_bytes(),
                                 (DEMO / relative).read_bytes())
        self.assertEqual(
            {p for p in relative_files(COLLECTION / "static")},
            relative_files(DEMO / "static"), "static/ files")
        self.assertEqual(
            relative_files(COLLECTION / "compounds"),
            relative_files(DEMO / "compounds"), "compounds/ files")
        names = {p.stem + ".md" if p.suffix == ".org" else p.name
                 for p in sample_files()}
        self.assertEqual(len(names), 18)
        self.assertEqual(
            relative_files(COLLECTION / "md" / "procedures"), names)
        markdown = [p for p in sample_files() if p.suffix == ".md"]
        self.assertEqual(len(markdown), 10)
        for path in markdown:
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
