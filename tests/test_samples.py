"""The seed and sample procedures (sample-procedures)."""

import copy
import json
import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

import sample_support as sup
import test_theme_static as tts
from pipeline_support import DEMO, FIXTURES, REPO, snapshot_digest

ORG_SEED = DEMO / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
MD_SEED = DEMO / "md" / "procedures" / "OSDB-0002-aspirin.md"
COLLECTION = FIXTURES / "collection"
DEMO_REGISTRY = REPO / "webapp" / "demo" / "registry.json"
# The demo's accounts (lab-demo "Demo accounts") and, per sample ID, the
# user names the nine oldest procedures credit (sample-procedures "Sample
# marking"). Every further sample credits demo accounts.
DEMO_ACCOUNTS = {"aschmidt": "Anna Schmidt", "jkoch": "Jonas Koch",
                 "klehmann": "Katrin Lehmann", "mwolf": "Miriam Wolf",
                 "tbauer": "Tobias Bauer"}
DEMO_CREDITS = {
    "OSDB-0001": ["klehmann", "tbauer"], "OSDB-0002": ["klehmann", "aschmidt"],
    "OSDB-0003": ["tbauer", "jkoch"], "OSDB-0004": ["aschmidt", "mwolf"],
    "OSDB-0005": ["mwolf"], "OSDB-0006": ["jkoch", "klehmann"],
    "OSDB-0007": ["aschmidt"], "OSDB-0008": ["aschmidt", "tbauer"],
    "OSDB-0009": ["mwolf"]}
USER_NAME = re.compile(r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$")


def accounts_of(path: Path) -> dict[str, str]:
    """The user names and names of the snapshot ``path``'s accounts."""
    table = json.loads(path.read_text(encoding="utf-8"))
    return {a["username"]: a["name"] for a in table["accounts"]}


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
                    self.assertIn(author, accounts_of(DEMO_REGISTRY))
                self.assertIn(sample.terms["unverified"],
                              " ".join(sample.summary.split()))


class DemoAuthorsTests(unittest.TestCase):
    """Requirement: Sample marking (the demo's authors are those of the
    demo accounts), with lab-demo "Demo accounts"."""

    def test_the_demo_registry_lists_the_demo_accounts(self) -> None:
        """Scenario: Seeds are marked as samples (the demo's registry
        lists its five accounts)."""
        table = json.loads(DEMO_REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(
            table.get("accounts"),
            [{"username": user, "name": name}
             for user, name in sorted(DEMO_ACCOUNTS.items())])

    def test_the_demos_digest_covers_its_accounts(self) -> None:
        """Requirement: Snapshot (`accounts` is inside the digest)."""
        table = json.loads(DEMO_REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(table["digest"], snapshot_digest(table))
        without = {k: v for k, v in table.items() if k != "accounts"}
        self.assertNotEqual(table["digest"], snapshot_digest(without))

    def test_each_procedure_credits_its_demo_accounts(self) -> None:
        """Requirement: Sample marking (the demo's procedures credit
        the demo accounts, `A.` to `klehmann` and so on)."""
        found = set()
        for sample in samples():
            ident = sample.data["id"]
            with self.subTest(sample=sample.path.name):
                authors = sample.data["authors"]
                self.assertTrue(authors)
                self.assertLessEqual(set(authors), set(DEMO_ACCOUNTS))
                if ident in DEMO_CREDITS:
                    self.assertEqual(authors, DEMO_CREDITS[ident])
            found.add(ident)
        self.assertLessEqual(set(DEMO_CREDITS), found)


class SampleQuantityTests(unittest.TestCase):
    def test_reagent_tables_are_consistent(self) -> None:
        """Scenario: Seed tables are consistent."""
        for sample in samples():
            with self.subTest(sample=sample.path.name):
                self.assertEqual(sup.quantity_violations(sample), [])


class ReagentsInRegistryTests(unittest.TestCase):
    """Requirement: Reagents in the registry."""

    def test_every_row_is_a_registry_substance(self) -> None:
        """Scenario: Every row is a registry substance."""
        registry = sup.read_registry(DEMO)
        self.assertEqual(
            sup.reagent_violations(samples(), registry), [])

    def test_every_sample_lists_reagents(self) -> None:
        """Requirement: Reagents in the registry (the substrates are rows
        of the table, and so are the solvents and the workup
        chemicals)."""
        for sample in samples():
            with self.subTest(sample=sample.path.name):
                self.assertGreater(len(sample.table), 1)

    def test_the_demo_lists_solvents_and_auxiliaries(self) -> None:
        """Requirement: Quantities agree (a row of `–` in `mmol` and
        `Equiv` is a solvent or an auxiliary)."""
        rows = [row for sample in samples() for row in sample.table[1:]]
        self.assertTrue([row for row in rows if row[4:] == ["–", "–"]])

    def sample(self, name: str, table: list[list[str]],
               data: dict | None = None) -> sup.Sample:
        language = "de" if ".de." in name else "en"
        return sup.Sample(Path(name), data or {}, None, "",
                          [sup.TERMS[language]["header"], *table])

    def test_the_checker_rejects_what_the_spec_forbids(self) -> None:
        """Scenario: Every row is a registry substance (checker)."""
        registry = {"water": {"cas": "7732-18-5"},
                    "ethanol": {"cas": "64-17-5"},
                    "ethanol-twin": {"cas": "64-17-5"},
                    "ether": {"cas": "60-29-7"}}
        english = ["Ether", "60-29-7", "74.12", "10 mL", "–", "–"]
        other = ["Water", "7732-18-5", "18.02", "1 mL", "–", "–"]
        german = ["Ether", "60-29-7", "74,12", "10 mL", "–", "–"]
        good = [self.sample("OSDB-0990-x.md", [english, other]),
                self.sample("OSDB-0990-x.de.md", [german, other])]
        self.assertEqual(sup.reagent_violations(good, registry), [])
        broken = {
            "a CAS no substance has": [
                self.sample("OSDB-0990-x.md",
                            [english[:1] + ["67-64-1"] + english[2:]])],
            "a CAS two substances have": [
                self.sample("OSDB-0990-x.md",
                            [["Ethanol", "64-17-5", "46.07", "1 mL", "–",
                              "–"]])],
            "German rows in another order": [
                good[0], self.sample("OSDB-0990-x.de.md", [other, german])],
            "a German row less": [
                good[0], self.sample("OSDB-0990-x.de.md", [german])],
            "a German table without its original": [good[1]],
        }
        for name, found in broken.items():
            with self.subTest(case=name):
                self.assertNotEqual(
                    sup.reagent_violations(found, registry), [])

    def test_a_substrate_must_be_a_row(self) -> None:
        """Requirement: Reagents in the registry (the substrates of a
        procedure are rows of its Reagents table)."""
        registry = {"ether": {"cas": "60-29-7"},
                    "water": {"cas": "7732-18-5"}}
        row = ["Water", "7732-18-5", "18.02", "1 mL", "–", "–"]
        found = [self.sample("OSDB-0990-x.md", [row],
                             {"substrates": ["ether"]})]
        self.assertNotEqual(sup.reagent_violations(found, registry), [])
        found = [self.sample("OSDB-0990-x.md", [row],
                             {"substrates": ["water"]})]
        self.assertEqual(sup.reagent_violations(found, registry), [])


class CompoundWeightTests(unittest.TestCase):
    def test_compound_weights_agree_with_formulas(self) -> None:
        """Scenario: Seed tables are consistent (compound weights)."""
        registry = sup.read_registry(DEMO)
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
                  "kat.", "kat."],
                 ["Ethanol", "64-17-5", "46,07", "20 mL", "–", "–"]]
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

    def test_a_solvent_row_is_exempt_but_for_its_cas_number(self) -> None:
        """Scenario: Translated sample tables are consistent (checker,
        solvent row): a row of `–` in `mmol` and `Equiv` is exempt from
        every rule but the check digit."""
        german = self.german()
        self.assertEqual(german.table[-1][4:], ["–", "–"])

        def with_solvent(row: list[str]) -> sup.Sample:
            return german._replace(table=[*german.table[:-1], row])

        for row in (["Ethanol", "64-17-5", "46,07", "20 g", "–", "–"],
                    ["Ethanol", "64-17-5", "99,99", "20 mL", "–", "–"],
                    ["Magnesiumsulfat", "7487-88-9", "120,37", "ca. 2 g",
                     "–", "–"]):
            with self.subTest(row=row):
                self.assertEqual(
                    sup.quantity_violations(with_solvent(row)), [])
        self.assertNotEqual(sup.quantity_violations(
            with_solvent(["Ethanol", "64-17-6", "46,07", "20 mL", "–",
                          "–"])), [], "the check digit of a solvent row")

    def test_a_row_with_one_dash_is_no_solvent_row(self) -> None:
        """Scenario: Translated sample tables are consistent (checker,
        solvent row): only a row with `–` in both columns is exempt."""
        german = self.german()
        for mmol, equiv in (("–", "2,0"), ("100", "–")):
            row = ["Ethanol", "64-17-5", "46,07", "20 mL", mmol, equiv]
            with self.subTest(mmol=mmol, equiv=equiv):
                self.assertNotEqual(sup.quantity_violations(
                    german._replace(table=[*german.table[:-1], row])), [])


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
# The chains the requirement names: the sample that makes the compound and
# the sample that starts from it, by the compound.
CHAINS = {("OSDB-0001", "OSDB-0002"): "salicylic-acid",
          ("OSDB-0004", "OSDB-0005"): "4-acetylbiphenyl",
          ("OSDB-0004", "OSDB-0009"): "4-acetylbiphenyl",
          ("OSDB-0007", "OSDB-0008"): "ethyl-cinnamate"}
ORG_SAMPLES = {"OSDB-0001", "OSDB-0003", "OSDB-0004", "OSDB-0007"}
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
    def test_set_formats_and_chains(self) -> None:
        """Scenario: Set, counts and chain."""
        registry = sup.read_registry(DEMO)
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
        by_id = {s.data["id"]: s for s in found}
        org = {i for i, s in by_id.items() if s.path.suffix == ".org"}
        markdown = {i for i, s in by_id.items() if s.path.suffix == ".md"}
        self.assertLessEqual(ORG_SAMPLES, org, "the Org samples named")
        self.assertIn("OSDB-0009", markdown, "the general procedure")
        self.assertTrue(markdown - {"OSDB-0009"}, "no Markdown sample")
        self.assertGreaterEqual(
            len({r for s in found for r in s.data.get("reaction_types", [])}),
            5)
        for (maker, user), key in CHAINS.items():
            with self.subTest(chain=f"{maker} -> {user}"):
                self.assertEqual(by_id[maker].path.suffix, ".org")
                self.assertEqual(by_id[user].path.suffix, ".md")
                self.assertIn(key, sup.product_keys(by_id[maker].data))
                self.assertIn(key, sup.substrate_keys(by_id[user].data))
        for sample in found:
            with self.subTest(sample=sample.path.name):
                self.assertTrue(
                    set(sample.data.get("tags", [])) - {"sample-data"},
                    "no tag besides sample-data")
        for key in sorted(sup.named_compounds_of(DEMO)):
            with self.subTest(compound=key):
                self.assertIn(key, registry)
                self.assertTrue(sup.cas_ok(registry[key].get("cas", "")))


class StructureImageSampleTests(unittest.TestCase):
    def table(self) -> dict:
        return json.loads(DEMO_REGISTRY.read_text(encoding="utf-8"))

    def test_the_registry_gives_every_smiles_a_molfile(self) -> None:
        """Scenario: Structure image is present (the registry)."""
        substances = {e["key"]: e for e in self.table()["substances"]}
        drawn = [key for key, e in substances.items() if e.get("smiles")]
        self.assertTrue(drawn, "no demo substance has a smiles")
        for key in drawn:
            with self.subTest(compound=key):
                self.assertIsInstance(substances[key].get("molfile"), str)
                self.assertIn("M  END", substances[key]["molfile"])
        self.assertIn("molfile", substances["new-compound-7"])
        self.assertIsNone(substances["new-compound-7"]["molfile"])

    def test_isopentyl_acetate_has_its_image_beside_the_registry(
            self) -> None:
        """Scenario: Structure image is present (the files beside the
        registry)."""
        self.assertIn("isopentyl-acetate", sup.read_registry(DEMO))
        directory = REPO / "webapp" / "demo" / "substances"
        self.assertEqual(sorted(relative_files(directory)),
                         ["isopentyl-acetate/structure.svg"])
        entry = {e["key"]: e for e in self.table()["substances"]}[
            "isopentyl-acetate"]
        self.assertIsInstance(entry["molfile"], str)

    def test_the_demo_collection_keeps_no_structure_image_by_key(
            self) -> None:
        """Scenario: Structure image is present (no file of
        `examples/demo/static/structures/` is named after a
        substance)."""
        keys = {e["key"] for e in self.table()["substances"]}
        names = sorted(p.name for p in
                       (DEMO / "static" / "structures").iterdir())
        self.assertIn("aryl-ketone-reduction.svg", names)
        for key in keys:
            for suffix in (".svg", ".png"):
                self.assertNotIn(key + suffix, names)
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
        """Scenario: Every sample has a German translation (every sample
        file without a language code has a twin)."""
        originals = [p for p in sample_files()
                     if sup.language_of(p) == "en"]
        self.assertTrue(originals)
        for original in originals:
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
        registry = sup.read_registry(DEMO)
        for key, values in GENERAL_COMPOUNDS.items():
            with self.subTest(compound=key):
                self.assertIn(key, registry)
                self.assertEqual([registry[key][k] for k in keys], values)

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
        self.assertTrue(others)
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


def converted_name(path: Path) -> str:
    """The name of the test collection's file for the demo sample file
    ``path``: ``<stem>.md`` for an Org sample, else the same name."""
    return path.stem + ".md" if path.suffix == ".org" else path.name


def relative_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix()
            for p in root.rglob("*") if p.is_file()}


SEQUENCES = DEMO / "md" / "sequences"
DEMO_SEQUENCES = {
    "SEQ-0001-aspirin-from-wintergreen": {
        "id": "SEQ-0001", "slug": "seq-0001",
        "title": "Aspirin from oil of wintergreen",
        "title_de": "Aspirin aus Wintergrünöl",
        "target": "acetylsalicylic-acid",
        "steps": [{"procedure": "OSDB-0001"}, {"procedure": "OSDB-0002"}],
        "notes": "dried before the acetylation"},
    "SEQ-0002-biphenylyl-ethanol": {
        "id": "SEQ-0002", "slug": "seq-0002",
        "title": "1-(Biphenyl-4-yl)ethanol from 4′-bromoacetophenone",
        "title_de": "1-(Biphenyl-4-yl)ethanol aus 4′-Bromacetophenon",
        "target": "1-biphenyl-4-yl-ethanol",
        "steps": [{"procedure": "OSDB-0004"},
                  {"procedure": "OSDB-0009",
                   "product": "1-biphenyl-4-yl-ethanol"}],
        "notes": None},
}


read_sequence = sup.read_sequence


class DemoSequenceTests(unittest.TestCase):
    def test_the_named_sequences_and_their_variants_exist(self) -> None:
        """Scenario: The demo's sequences (the two named sequences, each
        in English and German, among others)."""
        names = {p.name for p in SEQUENCES.glob("*")}
        self.assertLessEqual(
            {f"{stem}{suffix}" for stem in DEMO_SEQUENCES
             for suffix in (".md", ".de.md")}, names)

    def test_the_demo_holds_sequences_of_three_and_four_steps(self) -> None:
        """Scenario: The demo's sequences (a sequence of three steps and
        one of four)."""
        lengths = {len(read_sequence(path)[0]["steps"])
                   for path in sup.sequence_files(DEMO)}
        self.assertLessEqual({3, 4}, lengths)

    def test_every_sequence_is_chained_with_a_german_variant(self) -> None:
        """Scenario: The demo's sequences (every sequence with a `.de`
        variant sharing its steps and target, its steps chained)."""
        self.assertTrue(sup.sequence_files(DEMO))
        self.assertEqual(sup.sequence_violations(DEMO), [])

    def test_every_file_is_a_sequence_or_its_german_variant(self) -> None:
        """Scenario: The demo's sequences (every sequence has a `.de`
        variant, and no variant lacks its sequence)."""
        english = {p.name for p in sup.sequence_files(DEMO)}
        german = {p.name for p in sup.sequence_files(DEMO, "de")}
        self.assertEqual({n.replace(".de.md", ".md") for n in german},
                         english)
        self.assertEqual(english | german,
                         {p.name for p in SEQUENCES.glob("*")})

    def test_each_sequence_has_the_stated_title_target_and_steps(
            self) -> None:
        """Scenario: The demo's sequences (the English files)."""
        for stem, wanted in DEMO_SEQUENCES.items():
            path = SEQUENCES / f"{stem}.md"
            with self.subTest(sequence=stem):
                self.assertTrue(path.is_file(), f"{path.name} is missing")
                data, body = read_sequence(path)
                for key in ("id", "slug", "title", "target", "steps"):
                    self.assertEqual(data.get(key), wanted[key], key)
                self.assertNotIn("authors", data)
                self.assertTrue(body.strip())
                if wanted["notes"]:
                    self.assertIn(wanted["notes"], " ".join(body.split()))

    def test_the_german_variants_share_target_and_steps(self) -> None:
        """Scenario: The demo's sequences (the German variants of the
        two named sequences)."""
        for stem, wanted in DEMO_SEQUENCES.items():
            path = SEQUENCES / f"{stem}.de.md"
            with self.subTest(sequence=stem):
                self.assertTrue(path.is_file(), f"{path.name} is missing")
                data, body = read_sequence(path)
                english, english_body = read_sequence(
                    SEQUENCES / f"{stem}.md")
                self.assertEqual(data["title"], wanted["title_de"])
                for key in ("id", "slug", "target", "steps"):
                    self.assertEqual(data.get(key), wanted[key], key)
                self.assertTrue(body.strip())
                self.assertNotEqual(body, english_body)
                self.assertNotIn("## Notes", body)

    def test_every_target_has_an_article_number(self) -> None:
        """Requirement: Demo sequences (each sequence's target is a
        substance with an article number)."""
        registry = sup.read_registry(DEMO)
        for path in sup.sequence_files(DEMO):
            with self.subTest(sequence=path.name):
                target = read_sequence(path)[0]["target"]
                self.assertIn("article_number", registry[target])

    def test_the_substances_carried_between_steps_are_intermediates(
            self) -> None:
        """Requirement: Demo sequences (a substance that one step makes
        and the next starts from has the group `intermediates`)."""
        registry = sup.read_registry(DEMO)
        by_id = {s.data["id"]: s for s in samples() if s.language == "en"}
        carried = 0
        for path in sup.sequence_files(DEMO):
            runs = [sup.step_run(by_id, step)
                    for step in read_sequence(path)[0]["steps"]]
            for before, after in zip(runs, runs[1:]):
                for key in set(before[1]) & set(after[0]):
                    carried += 1
                    with self.subTest(sequence=path.name, compound=key):
                        self.assertEqual(registry[key]["group"],
                                         "intermediates")
        self.assertGreater(carried, 0)

    def test_dates_are_berlin_offset_datetimes(self) -> None:
        """Requirement: Demo sequences (dates like the samples')."""
        files = sorted(SEQUENCES.glob("*.md"))
        self.assertTrue(files)
        for path in files:
            data, _ = read_sequence(path)
            with self.subTest(file=path.name):
                for key in ("date", "lastmod"):
                    value = data[key]
                    self.assertIsNotNone(value.tzinfo)
                    self.assertIn(value.utcoffset().total_seconds(),
                                  (3600, 7200))
                self.assertGreaterEqual(data["lastmod"], data["date"])

    def test_the_steps_name_samples_of_the_demo(self) -> None:
        """Requirement: Demo sequences (they validate with the demo's
        procedures): a step names a sample, a general procedure's by the
        product of exactly one entry."""
        samples = {s.data["id"]: s for s in sup.sample_procedures(DEMO)}
        files = sup.sequence_files(DEMO)
        self.assertTrue(files)
        for path in files:
            data, _ = read_sequence(path)
            for step in data["steps"]:
                with self.subTest(sequence=path.name, step=step):
                    sample = samples[step["procedure"]]
                    entries = sample.data.get("scope")
                    self.assertNotIn("entry", step)
                    self.assertEqual("product" in step, entries is not None)
                    if entries is None:
                        self.assertEqual(set(step), {"procedure"})
                        continue
                    named = [entry for entry in entries
                             if step["product"] in
                             [p["compound"] for p in entry["products"]]]
                    self.assertEqual(len(named), 1,
                                     "a product of exactly one entry")


class DemoFieldTests(unittest.TestCase):
    def test_the_demo_declares_its_fields(self) -> None:
        """Scenario: The demo declares its fields."""
        self.assertEqual(sup.field_violations(DEMO), [])

    def test_the_demo_names_its_registry(self) -> None:
        """Scenario: The demo collection matches init (the demo's
        settings)."""
        settings = tomllib.loads(
            (DEMO / "orgsyndb.toml").read_text(encoding="utf-8"))
        self.assertEqual(settings["registry"],
                         "../../webapp/demo/registry.json")
        self.assertEqual(list(settings["fields"]), ["procedure"])
        self.assertEqual((DEMO / settings["registry"]).resolve(),
                         (REPO / "webapp" / "demo"
                          / "registry.json").resolve())

    def test_the_demo_holds_no_compound_and_vocabulary_files(self) -> None:
        """Scenario: Samples live in the demo collection."""
        for name in ("compounds", "vocabularies"):
            self.assertFalse((DEMO / name).exists(), name)

    def test_the_chemical_classes_of_the_demo(self) -> None:
        """Requirement: Demo collection (the vocabularies: every term has
        a German label, every class a substance has is a term, and some
        class has two ancestors)."""
        classes = sup.read_vocabulary(DEMO, "chemical-classes")
        self.assertTrue(classes)
        for key, term in classes.items():
            with self.subTest(term=key):
                self.assertTrue(term.get("label_de", "").strip())
                self.assertIn(term.get("parent", key), classes)
        for key, compound in sup.read_registry(DEMO).items():
            with self.subTest(compound=key):
                self.assertLessEqual(set(compound["chemical_classes"]),
                                     set(classes))
        self.assertTrue(any(sup.vocabulary_depth(classes, key) == 2
                            for key in classes))

    def test_the_reaction_types_of_the_demo(self) -> None:
        """Requirement: Demo collection (every term has a German label;
        every reaction type a sample names is a term)."""
        values = sup.read_vocabulary(DEMO, "reaction-types")
        for value, entry in values.items():
            with self.subTest(value=value):
                self.assertTrue(entry.get("label_de", "").strip())
        named = {r for sample in samples()
                 for r in sample.data.get("reaction_types", [])}
        self.assertTrue(named)
        self.assertLessEqual(named, set(values))

    def test_the_inventory_groups_of_the_demo(self) -> None:
        """Requirement: Demo collection (the groups)."""
        self.assertEqual(sup.terms_of(DEMO, "inventory-groups"),
                         sorted(sup.INVENTORY_GROUPS))

    def test_the_projects_of_the_demo(self) -> None:
        """Requirement: Demo collection (the projects)."""
        self.assertEqual(sup.terms_of(DEMO, "projects"),
                         sorted(sup.PROJECTS))

    def test_the_demo_procedure_fields(self) -> None:
        """Scenario: The demo declares its fields (the procedure
        fields)."""
        settings = tomllib.loads(
            (DEMO / "orgsyndb.toml").read_text(encoding="utf-8"))
        self.assertEqual(list(settings["fields"]), ["procedure"])
        declared = settings["fields"]["procedure"]
        self.assertEqual(
            [d["key"] for d in declared],
            ["working_time", "inert_atmosphere"])
        self.assertEqual(
            [{k: v for k, v in d.items() if k not in ("label", "label_de")}
             for d in declared], sup.DEMO_PROCEDURE_DECLARATIONS)
        self.assertEqual(
            {d["key"]: (d.get("label"), d.get("label_de"))
             for d in declared}, sup.DEMO_PROCEDURE_LABELS)
        self.assertEqual([d["key"] for d in declared
                          if d.get("required")], [])

    def test_the_demo_declares_neither_journal_field(self) -> None:
        """Requirement: Demo collection (the declarations: `notebook`
        and `project` are built in, so the demo declares neither)."""
        for path in (DEMO, COLLECTION):
            settings = tomllib.loads(
                (path / "orgsyndb.toml").read_text(encoding="utf-8"))
            declared = [d["key"] for d in settings["fields"]["procedure"]]
            with self.subTest(collection=path.name):
                self.assertNotIn("notebook", declared)
                self.assertNotIn("project", declared)
                self.assertEqual(declared,
                                 ["working_time", "inert_atmosphere"])

    def test_the_demo_registry_lists_the_demo_notebooks(self) -> None:
        """Requirement: Demo collection (the registry lists the notebooks
        `AE-1`, `AE-2`, `CE-1` and `CE-3`), with lab-demo "Demo
        notebooks"."""
        table = json.loads(DEMO_REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(table.get("notebooks"), sup.DEMO_NOTEBOOKS)
        self.assertEqual(table["digest"], snapshot_digest(table))
        without = {k: v for k, v in table.items() if k != "notebooks"}
        self.assertNotEqual(table["digest"], snapshot_digest(without))

    def test_every_sample_names_a_notebook_of_the_registry(self) -> None:
        """Requirement: Demo collection (every `notebook` a sample sets
        names one of the registry's notebooks)."""
        codes = {n["code"] for n in sup.read_snapshot(DEMO)["notebooks"]}
        values = sup.procedure_values(DEMO)
        for number, variants in values.items():
            for variant in variants:
                with self.subTest(procedure=number):
                    self.assertIn(variant["notebook"].split("/")[0], codes)

    def test_the_demo_procedure_values(self) -> None:
        """Scenario: The demo declares its fields (the procedures'
        values)."""
        values = sup.procedure_values(DEMO)
        self.assertLessEqual(set(DEMO_CREDITS), set(values))
        for number, variants in values.items():
            with self.subTest(procedure=number):
                self.assertEqual(len(variants), 2)
                self.assertEqual(variants[0], variants[1])
                self.assertIn("notebook", variants[0])
                self.assertIn("project", variants[0])
        self.assertEqual(
            values["OSDB-0002"],
            [{"notebook": "AE-1/2", "project": "first-year-practical",
              "working_time": 2.5, "inert_atmosphere": False}] * 2)
        self.assertEqual(
            {v[0]["project"] for v in values.values()},
            set(sup.PROJECT_VALUES))

    def test_the_demo_values_are_the_stated_ones(self) -> None:
        """Scenario: The demo's registry and fields (the values)."""
        registry = sup.read_registry(DEMO)
        numbers = {key: compound["article_number"]
                   for key, compound in registry.items()
                   if "article_number" in compound}
        for key, number in sup.DEMO_NUMBERS.items():
            self.assertEqual(numbers.get(key), number, key)
        for key, number in numbers.items():
            with self.subTest(compound=key):
                if key != "new-compound-7":
                    self.assertRegex(number, r"^CH-\d{4}$")
                self.assertEqual(registry[key]["group"], "final-products")
        self.assertEqual(registry["acetic-acid"]["short_name"], "AcOH")
        self.assertEqual(registry["methyl-salicylate"]["chemical_classes"],
                         ["esters", "phenols"])
        self.assertEqual(registry["new-compound-7"]["article_number"],
                         "NV-0007")
        for key in ("formula", "mw", "smiles", "cas"):
            self.assertNotIn(key, registry["new-compound-7"])

    def test_every_substance_has_a_german_name(self) -> None:
        """Requirement: Demo collection (every substance has a
        `name_de`)."""
        for key, compound in sup.read_registry(DEMO).items():
            with self.subTest(compound=key):
                self.assertTrue(compound.get("name_de", "").strip())

    def test_the_demo_groups_of_the_compounds(self) -> None:
        """Scenario: The demo's registry and fields (the group values):
        a substance that one sample makes and another starts from has the
        group `intermediates` unless it has an article number."""
        registry = sup.read_registry(DEMO)
        for key, compound in registry.items():
            with self.subTest(compound=key):
                self.assertIn(compound.get("group"), sup.GROUP_VALUES)
        self.assertEqual(sup.chain_group_violations(DEMO, registry), [])
        for key in ("salicylic-acid", "4-acetylbiphenyl", "ethyl-cinnamate"):
            with self.subTest(chain=key):
                self.assertEqual(registry[key]["group"], "intermediates")
        self.assertEqual(
            {registry[key]["group"] for key in registry
             if "article_number" in registry[key]}, {"final-products"})

    def test_the_registry_covers_the_samples(self) -> None:
        """Scenario: Samples live in the demo collection (every key the
        samples name is a substance; every substance is named by a
        sample, carries the CAS number of a Reagents row, is
        `new-compound-7` or has the group `reagents` or
        `starting-materials`; some substance of those groups is named by
        no sample)."""
        self.assertEqual(sup.coverage_violations(DEMO), [])


class ProcedureFieldCheckerTests(unittest.TestCase):
    """The checker must reject what the spec forbids, or the demo tests
    above would hold nothing."""

    def collection(self) -> Path:
        """A temporary copy of the test collection."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "collection"
        shutil.copytree(COLLECTION, root)
        return root

    def edit(self, root: Path, old: str, new: str, *,
             variants: tuple[str, ...] = (".md", ".de.md")) -> None:
        """Replace ``old`` by ``new`` in the ``variants`` of
        OSDB-0001."""
        for suffix in variants:
            path = (root / "md" / "procedures"
                    / f"OSDB-0001-salicylic-acid{suffix}")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(old), 1, old)
            path.write_text(text.replace(old, new), encoding="utf-8")

    def test_the_test_collection_meets_the_demo_rules(self) -> None:
        """Scenario: The demo declares its fields (as mirrored in the
        test collection)."""
        self.assertEqual(sup.field_violations(COLLECTION), [])

    def test_each_rule_is_enforced(self) -> None:
        """Scenario: The demo declares its fields (checker, rejected)."""
        cases = {
            "variants that disagree": (
                'notebook = "AE-1/1"', 'notebook = "AE-1/9"',
                (".de.md",), "variants set"),
            "a notebook that breaks its pattern": (
                'notebook = "AE-1/1"', 'notebook = "AE1/1"',
                (".md", ".de.md"), "notebook is"),
            "a project outside the demo's set": (
                'project = "first-year-practical"',
                'project = "teaching"', (".md", ".de.md"), "project is"),
            "a quoted working time": (
                "working_time = 3", 'working_time = "3"',
                (".md", ".de.md"), "working_time is"),
            "a flag that is no boolean": (
                "inert_atmosphere = false", 'inert_atmosphere = "false"',
                (".md", ".de.md"), "inert_atmosphere is"),
            "a notebook the registry lacks": (
                'notebook = "AE-1/1"', 'notebook = "ZZ-1/1"',
                (".md", ".de.md"), "names no notebook"),
            "a notebook set twice": (
                'notebook = "AE-1/1"', 'notebook = "AE-1/2"',
                (".md", ".de.md"), "notebooks are"),
            "no notebook": (
                'notebook = "AE-1/1"\n', "", (".md", ".de.md"),
                "sets no notebook"),
        }
        for name, case in cases.items():
            old, new, variants, expected = case
            with self.subTest(case=name):
                root = self.collection()
                self.edit(root, old, new, variants=variants)
                violations = sup.field_violations(root)
                self.assertTrue(
                    any(expected in line for line in violations),
                    violations)

    def test_a_registry_without_a_group_value_is_rejected(self) -> None:
        """Scenario: The demo's registry and fields (checker, rejected
        registry)."""
        root = self.collection()
        path = root / "registry.json"
        table = json.loads(path.read_text(encoding="utf-8"))
        for entry in table["substances"]:
            if entry["group"] == "intermediates":
                entry["group"] = "reagents"
        path.write_text(json.dumps(table), encoding="utf-8")
        self.assertTrue(any("intermediates" in line for line in
                            sup.field_violations(root)))

    def test_a_vocabulary_term_without_a_german_label_is_rejected(
            self) -> None:
        """Scenario: The demo's registry and fields (checker, no
        `label_de`)."""
        root = self.collection()
        path = root / "registry.json"
        table = json.loads(path.read_text(encoding="utf-8"))
        table["vocabularies"]["projects"][0]["label_de"] = None
        path.write_text(json.dumps(table), encoding="utf-8")
        self.assertNotEqual(sup.field_violations(root), [])

    def test_a_compound_declaration_is_rejected(self) -> None:
        """Scenario: The demo's registry and fields (checker, a
        declared compound field)."""
        root = self.collection()
        path = root / "orgsyndb.toml"
        path.write_text(path.read_text(encoding="utf-8")
                        + '\n[[fields.compound]]\nkey = "x"\n',
                        encoding="utf-8")
        self.assertNotEqual(sup.field_violations(root), [])

    def test_a_journal_declaration_is_rejected(self) -> None:
        """Scenario: The demo declares its fields (checker, a declared
        journal field)."""
        for key in ("notebook", "project"):
            with self.subTest(key=key):
                root = self.collection()
                path = root / "orgsyndb.toml"
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + f'\n[[fields.procedure]]\nkey = "{key}"\n'
                    'type = "text"\nlabel = "X"\n', encoding="utf-8")
                self.assertNotEqual(sup.field_violations(root), [])

    def test_a_registry_without_the_notebooks_is_rejected(self) -> None:
        """Scenario: The demo's registry and fields (checker, no
        notebooks)."""
        root = self.collection()
        path = root / "registry.json"
        table = json.loads(path.read_text(encoding="utf-8"))
        del table["notebooks"]
        path.write_text(json.dumps(table), encoding="utf-8")
        self.assertTrue(any("notebooks" in line for line in
                            sup.field_violations(root)))

    def test_a_missing_declaration_is_rejected(self) -> None:
        """Scenario: The demo declares its fields (checker, no
        declaration)."""
        root = self.collection()
        path = root / "orgsyndb.toml"
        text = path.read_text(encoding="utf-8")
        path.write_text(text[:text.index("[[fields.procedure]]")],
                        encoding="utf-8")
        self.assertNotEqual(sup.field_violations(root), [])


class RegistryRuleCheckerTests(unittest.TestCase):
    """The rules for the registry's substances and the sequences must be
    enforced, or the demo tests would hold nothing."""

    def collection(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "collection"
        shutil.copytree(COLLECTION, root)
        return root

    def edit_registry(self, root: Path, change) -> None:
        path = root / "registry.json"
        table = json.loads(path.read_text(encoding="utf-8"))
        change({entry["key"]: entry for entry in table["substances"]},
               table)
        path.write_text(json.dumps(table), encoding="utf-8")

    def edit_sequence(self, root: Path, old: str, new: str,
                      suffixes: tuple[str, ...] = (".md", ".de.md")) -> None:
        for suffix in suffixes:
            path = (root / "md" / "sequences"
                    / f"SEQ-0001-aspirin-from-wintergreen{suffix}")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(old), 1, old)
            path.write_text(text.replace(old, new), encoding="utf-8")

    def test_the_test_collection_meets_the_rules(self) -> None:
        """Scenario: The demo's sequences (as mirrored in the test
        collection)."""
        root = self.collection()
        self.assertEqual(sup.sequence_violations(root), [])
        self.assertEqual(sup.coverage_violations(root), [])

    def test_each_sequence_rule_is_enforced(self) -> None:
        """Scenario: The demo's sequences (checker, rejected)."""
        steps = ('steps = [{ procedure = "OSDB-0001" }, '
                 '{ procedure = "OSDB-0002" }]')
        self.assertIn(steps, (COLLECTION / "md" / "sequences" /
                              "SEQ-0001-aspirin-from-wintergreen.md"
                              ).read_text(encoding="utf-8"))
        cases = {
            "a step that starts from nothing the step before made": (
                steps, 'steps = [{ procedure = "OSDB-0002" }, '
                '{ procedure = "OSDB-0001" }]', (".md", ".de.md")),
            "a target that the last step does not make": (
                'target = "acetylsalicylic-acid"',
                'target = "salicylic-acid"', (".md", ".de.md")),
            "a German variant with other steps": (
                steps, 'steps = [{ procedure = "OSDB-0001" }]',
                (".de.md",)),
            "a German variant with another target": (
                'target = "acetylsalicylic-acid"',
                'target = "isopentyl-acetate"', (".de.md",)),
            "a step that names no sample": (
                steps, 'steps = [{ procedure = "OSDB-0001" }, '
                '{ procedure = "OSDB-0777" }]', (".md", ".de.md")),
        }
        for name, (old, new, suffixes) in cases.items():
            with self.subTest(case=name):
                root = self.collection()
                self.edit_sequence(root, old, new, suffixes)
                self.assertNotEqual(sup.sequence_violations(root), [])

    def test_a_sequence_without_a_german_variant_is_rejected(self) -> None:
        """Scenario: The demo's sequences (checker, no variant)."""
        root = self.collection()
        (root / "md" / "sequences"
         / "SEQ-0001-aspirin-from-wintergreen.de.md").unlink()
        self.assertTrue(any("German variant" in line for line in
                            sup.sequence_violations(root)))

    def test_a_target_without_an_article_number_is_rejected(self) -> None:
        """Requirement: Demo sequences (each sequence's target is a
        substance with an article number)."""
        root = self.collection()
        self.edit_registry(root, lambda by_key, table: by_key[
            "acetylsalicylic-acid"].update(article_number=None))
        self.assertTrue(any("article number" in line for line in
                            sup.sequence_violations(root)))

    def test_a_carried_substance_that_is_no_intermediate_is_rejected(
            self) -> None:
        """Requirement: Demo sequences (a substance that one step makes
        and the next starts from has the group `intermediates`); Demo
        collection (the same unless it has an article number)."""
        root = self.collection()
        self.edit_registry(root, lambda by_key, table: by_key[
            "salicylic-acid"].update(group="reagents"))
        self.assertTrue(any("salicylic-acid" in line for line in
                            sup.sequence_violations(root)))
        self.assertTrue(any("salicylic-acid" in line for line in
                            sup.field_violations(root)))

    def test_an_article_number_rule_is_enforced(self) -> None:
        """Scenario: The demo's registry and fields (checker, article
        numbers): each of the form `CH-<nnnn>` but that of
        `new-compound-7`, and had by final products only."""
        cases = {
            "a form that is none": lambda by_key, table: by_key[
                "cinnamic-acid"].update(article_number="CH-12"),
            "the named number gone": lambda by_key, table: by_key[
                "cinnamic-acid"].update(article_number=None),
            "an article number on a starting material": lambda by_key,
            table: by_key["acetone"].update(article_number="CH-0099"),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                root = self.collection()
                self.edit_registry(root, change)
                self.assertNotEqual(sup.field_violations(root), [])

    def test_an_orphan_substance_is_rejected(self) -> None:
        """Scenario: Samples live in the demo collection (checker): a
        substance that no sample names or lists and that is no
        commercial chemical, and a key that a sample names but the
        registry lacks."""
        root = self.collection()

        def add(by_key: dict, table: dict) -> None:
            table["substances"].append(
                {**by_key["acetone"], "key": "orphan",
                 "cas": "50-00-0", "group": "intermediates"})

        self.edit_registry(root, add)
        self.assertTrue(any("orphan" in line for line in
                            sup.coverage_violations(root)))
        root = self.collection()

        def remove(by_key: dict, table: dict) -> None:
            table["substances"].remove(by_key["benzaldehyde"])

        self.edit_registry(root, remove)
        self.assertTrue(any("benzaldehyde" in line for line in
                            sup.coverage_violations(root)))

    def test_a_registry_of_named_substances_only_is_rejected(self) -> None:
        """Scenario: Samples live in the demo collection (checker): some
        commercial chemical is named by no sample."""
        root = self.collection()
        named = sup.named_compounds_of(root)

        def keep_named(by_key: dict, table: dict) -> None:
            table["substances"] = [
                e for e in table["substances"]
                if e["key"] in named or e["key"] == "new-compound-7"]

        self.edit_registry(root, keep_named)
        self.assertTrue(any("commercial" in line for line in
                            sup.coverage_violations(root)))


class TestCollectionTests(unittest.TestCase):
    def test_the_collection_mirrors_the_demo(self) -> None:
        """Scenario: The test collection mirrors the demo."""
        self.assertTrue(COLLECTION.is_dir(), f"{COLLECTION} is missing")
        self.assertFalse((COLLECTION / "org").exists(), "org/ exists")
        copied = [".gitignore",
                  *sorted(f"static/{p}" for p in relative_files(
                      DEMO / "static"))]
        self.assertIn("static/structures/aryl-ketone-reduction.svg", copied)
        for relative in copied:
            with self.subTest(file=relative):
                self.assertTrue((COLLECTION / relative).is_file(),
                                f"{relative} is missing")
                self.assertEqual((COLLECTION / relative).read_bytes(),
                                 (DEMO / relative).read_bytes())
        self.assertEqual(
            {p for p in relative_files(COLLECTION / "static")},
            relative_files(DEMO / "static"), "static/ files")
        images = relative_files(REPO / "webapp" / "demo" / "substances")
        self.assertEqual(images, {"isopentyl-acetate/structure.svg"})
        self.assertEqual(
            relative_files(COLLECTION / "substances"), images,
            "substances/ files")
        for relative in sorted(images):
            with self.subTest(file=f"substances/{relative}"):
                self.assertEqual(
                    (COLLECTION / "substances" / relative).read_bytes(),
                    (REPO / "webapp" / "demo" / "substances" / relative
                     ).read_bytes())
        demo_table = json.loads(DEMO_REGISTRY.read_text(encoding="utf-8"))
        test_table = json.loads(
            (COLLECTION / "registry.json").read_text(encoding="utf-8"))
        for table in (demo_table, test_table):
            table.pop("accounts", None)
            table.pop("digest")
        self.assertEqual(test_table, demo_table)
        self.assertEqual(test_table["notebooks"], sup.DEMO_NOTEBOOKS)
        test_accounts = accounts_of(COLLECTION / "registry.json")
        self.assertEqual(
            {user: name for user, name in test_accounts.items()
             if user in DEMO_ACCOUNTS}, DEMO_ACCOUNTS)
        self.assertIn("a.example", test_accounts)
        self.assertEqual(test_accounts["ae.mueller"], "Ä. Müller")
        demo = tomllib.loads(
            (DEMO / "orgsyndb.toml").read_text(encoding="utf-8"))
        test = tomllib.loads(
            (COLLECTION / "orgsyndb.toml").read_text(encoding="utf-8"))
        self.assertEqual(test.pop("registry"), "registry.json")
        demo.pop("registry")
        self.assertEqual(test, demo)
        for name in ("compounds", "vocabularies"):
            self.assertFalse((COLLECTION / name).exists(), name)
        sequences = relative_files(DEMO / "md" / "sequences")
        self.assertTrue(sequences, "the demo's sequences")
        for relative in sorted(sequences):
            with self.subTest(file=relative):
                self.assertTrue(
                    (COLLECTION / "md" / "sequences" / relative).is_file(),
                    f"md/sequences/{relative} is missing")
                self.assertEqual(
                    (COLLECTION / "md" / "sequences" / relative
                     ).read_bytes(),
                    (DEMO / "md" / "sequences" / relative).read_bytes())
        self.assertEqual(
            relative_files(COLLECTION / "md" / "sequences"), sequences,
            "md/sequences/ files")
        names = [converted_name(p) for p in sample_files()]
        self.assertTrue(names, "the demo's samples")
        self.assertEqual(len(set(names)), len(names),
                         "two sample files of one converted name")
        self.assertEqual(
            relative_files(COLLECTION / "md" / "procedures"), set(names))
        for path in [p for p in sample_files() if p.suffix == ".md"]:
            with self.subTest(file=path.name):
                self.assertEqual(
                    (COLLECTION / "md" / "procedures"
                     / path.name).read_bytes(), path.read_bytes())

    def test_the_collections_procedures_credit_the_demo_accounts(
            self) -> None:
        """Requirement: Sample marking (the test collection's copies of
        the demo's procedures credit the same accounts, which its
        registry lists)."""
        accounts = accounts_of(COLLECTION / "registry.json")
        for path in sorted((COLLECTION / "md" / "procedures").glob("*.md")):
            data = sup.read_markdown(path).data
            with self.subTest(file=path.name):
                if data["id"] in DEMO_CREDITS:
                    self.assertEqual(data["authors"],
                                     DEMO_CREDITS[data["id"]])
                self.assertTrue(data["authors"])
                for author in data["authors"]:
                    self.assertIn(author, DEMO_ACCOUNTS)
                    self.assertIn(author, accounts)
                    self.assertRegex(author, USER_NAME)

    def test_converted_samples_agree_with_their_org_sources(self) -> None:
        """Scenario: Converted samples agree with their Org sources."""
        self.assertTrue(COLLECTION.is_dir(), f"{COLLECTION} is missing")
        orgs = sorted((DEMO / "org" / "procedures").glob("OSDB-*.org"))
        self.assertTrue(orgs, "no Org sample")
        for org in orgs:
            converted = COLLECTION / "md" / "procedures" / (
                org.stem + ".md")
            with self.subTest(sample=converted.name):
                self.assertTrue(converted.is_file(),
                                f"{converted.name} is missing")
                self.assertEqual(
                    sup.agreement_differences(org, converted), [])
