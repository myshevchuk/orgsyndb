"""General procedures without a build (general-procedures "Scope
entries", procedure-schema "Scheme image", localization "Procedure
variants"): the validator's rules for ``scope`` and ``scheme_image``, and
the fixtures the other tests build on."""

import tomllib
import unittest

import support
from pipeline_support import REPO, TEST_COLLECTION
from support import (COMPOUNDS, GENERAL, STATIC_DIR, ValidatorTestCase,
                     apply_edits, fixture_run, general_variant_run,
                     insert_line, remove_line, replace_block, replace_text)
from test_localization import germanised, run

ENTRY_3 = ('{ substrates = ["ethanol"], products = '
           '[{ compound = "methyl-benzoate", yield_percent = 72.5 }] }')
ONE_PRODUCT = 'products = [{ compound = "ethyl-acetate", yield_percent = 85 }]'
PRODUCT_NOTE = ("must be a number followed by min, h or d, "
                'e.g. "2 h"')


def general_text() -> str:
    return GENERAL.read_text(encoding="utf-8")


def front_matter(text: str) -> dict:
    return tomllib.loads(text.split("+++\n")[1])


def in_entry(old: str, new: str):
    """An edit of one fragment of the general baseline's scope."""
    return replace_text(old, new)


class GeneralBaselineTests(ValidatorTestCase):
    def test_the_general_baseline_is_valid(self) -> None:
        """Scenario: General baseline is valid."""
        self.assert_clean(fixture_run("general"))

    def test_the_baseline_has_the_shape_the_specification_gives(
            self) -> None:
        """Harness: three entries, the first with every optional key, the
        second with two products, the third with none."""
        data = front_matter(general_text())
        entries = data["scope"]
        self.assertEqual(len(entries), 3)
        optional = {"scale", "time", "temperature", "note"}
        self.assertEqual(optional, set(entries[0]) & optional)
        self.assertEqual(len(entries[1]["products"]), 2)
        self.assertEqual(set(entries[2]) & optional, set())
        for key in ("products", "substrates"):
            self.assertNotIn(key, data)
        self.assertNotIn("scheme_image", data)
        self.assertIn("scale", data)

    def test_the_baseline_has_all_eight_sections(self) -> None:
        """Harness: the baseline's body sections."""
        text = general_text()
        for name in ("Summary", "Reagents", "Procedure",
                     "Workup and Purification", "Characterization",
                     "Notes", "Hazards and Waste Disposal", "References"):
            self.assertEqual(text.count(f"\n## {name}\n"), 1, name)

    def test_its_compounds_are_in_the_fixture_registry(self) -> None:
        """Harness: every compound it names is registered, and one of its
        products sets a structure image."""
        entries = front_matter(general_text())["scope"]
        keys = [e["compound"] for entry in entries
                for e in entry["products"]]
        keys += [key for entry in entries for key in entry["substrates"]]
        images = []
        for key in keys:
            path = COMPOUNDS / f"{key}.toml"
            self.assertTrue(path.is_file(), f"{key} is not registered")
        for entry in entries:
            for product in entry["products"]:
                compound = tomllib.loads(
                    (COMPOUNDS / f"{product['compound']}.toml").read_text(
                        encoding="utf-8"))
                if "structure_image" in compound:
                    images.append(compound["structure_image"])
        self.assertTrue(images, "no product sets structure_image")
        for image in images:
            self.assertTrue((STATIC_DIR / image).is_file(), image)


class ScopeProblemTests(ValidatorTestCase):
    def test_top_level_products_in_a_general_procedure(self) -> None:
        """Scenario: Top-level products in a general procedure."""
        result = general_variant_run("OSDB-0140-general-products.md",
                                     insert_line(ONE_PRODUCT))
        self.assert_one(result, "error", "products",
                        "a general procedure lists them in scope")

    def test_top_level_substrates_in_a_general_procedure(self) -> None:
        """Requirement: Scope entries (top-level substrates)."""
        result = general_variant_run(
            "OSDB-0140-general-substrates.md",
            insert_line('substrates = ["acetic-acid"]'))
        self.assert_one(result, "error", "substrates",
                        "a general procedure lists them in scope")

    def test_entry_without_substrates(self) -> None:
        """Scenario: Entry without substrates."""
        result = general_variant_run(
            "OSDB-0140-no-substrates.md",
            in_entry('{ substrates = ["acetic-acid"], products = [{ '
                     'compound = "benzyl-acetate"',
                     '{ products = [{ compound = "benzyl-acetate"'))
        self.assert_one(result, "error", "scope[2].substrates",
                        "required field missing")

    def test_time_without_a_unit(self) -> None:
        """Scenario: Time without a unit."""
        result = general_variant_run(
            "OSDB-0140-bad-time.md",
            in_entry('time = "2 h"', 'time = "2 hours"'))
        self.assert_one(result, "error", "scope[1].time",
                        '"2 hours" ' + PRODUCT_NOTE)

    def test_temperature_as_a_string(self) -> None:
        """Scenario: Temperature as a string."""
        result = general_variant_run(
            "OSDB-0140-temperature-string.md",
            in_entry("temperature = 80", 'temperature = "80 °C"'))
        self.assert_one(result, "error", "scope[1].temperature",
                        "must be a number in °C, unquoted, e.g. 80")

    def test_unknown_compound_in_an_entry(self) -> None:
        """Scenario: Unknown compound in an entry."""
        result = general_variant_run(
            "OSDB-0140-unknown.md",
            in_entry('compound = "methyl-benzoate"',
                     'compound = "no-such-compound"'))
        self.assert_one(result, "error", "scope[3].products[1].compound",
                        'unknown compound "no-such-compound"')

    def test_empty_scope(self) -> None:
        """Scenario: Empty scope."""
        result = general_variant_run("OSDB-0140-empty-scope.md",
                                     replace_block("scope", "scope = []"))
        self.assert_one(result, "error", "scope", "must not be empty")

    def test_scope_that_is_not_an_array(self) -> None:
        """Requirement: Scope entries (not an array)."""
        for value in ('"acetic-acid"', '{ substrates = ["acetic-acid"] }',
                      "5"):
            with self.subTest(value=value):
                result = general_variant_run(
                    "OSDB-0140-scope-not-array.md",
                    replace_block("scope", f"scope = {value}"))
                self.assert_one(result, "error", "scope",
                                "must be an array of tables")

    def test_entry_that_is_not_a_table(self) -> None:
        """Requirement: Scope entries (an entry that is not a table)."""
        result = general_variant_run(
            "OSDB-0140-entry-not-table.md",
            replace_block("scope", 'scope = ["acetic-acid"]'))
        self.assert_one(result, "error", "scope[1]", "must be a table")

    def test_unknown_key_in_an_entry_is_a_warning(self) -> None:
        """Requirement: Scope entries (any other key is a warning)."""
        result = general_variant_run(
            "OSDB-0140-entry-unknown-key.md",
            in_entry('note = "Reflux.", ',
                     'note = "Reflux.", solvent = "water", '))
        self.assert_one(result, "warning", "scope[1].solvent",
                        "unknown field")

    def test_unknown_key_in_an_entry_product_is_a_warning(self) -> None:
        """Requirement: Scope entries (a key inside a product)."""
        result = general_variant_run(
            "OSDB-0140-product-unknown-key.md",
            in_entry('compound = "propyl-acetate", yield_percent = 64.5',
                     'compound = "propyl-acetate", yield_percent = 64.5, '
                     'yeild = 1'))
        self.assert_one(result, "warning", "scope[2].products[2].yeild",
                        "unknown field")

    def test_entry_without_products(self) -> None:
        """Requirement: Scope entries (products are required)."""
        result = general_variant_run(
            "OSDB-0140-no-products.md",
            in_entry('{ substrates = ["ethanol"], products = [{ compound = '
                     '"methyl-benzoate", yield_percent = 72.5 }] }',
                     '{ substrates = ["ethanol"] }'))
        self.assert_one(result, "error", "scope[3].products",
                        "required field missing")

    def test_entry_with_an_empty_products_list(self) -> None:
        """Requirement: Scope entries (products as at the top level)."""
        result = general_variant_run(
            "OSDB-0140-empty-products.md",
            in_entry(ENTRY_3, '{ substrates = ["ethanol"], products = [] }'))
        self.assert_one(result, "error", "scope[3].products",
                        "must not be empty")

    def test_entry_with_an_empty_substrates_list(self) -> None:
        """Requirement: Scope entries (substrates are non-empty)."""
        result = general_variant_run(
            "OSDB-0140-empty-substrates.md",
            in_entry('{ substrates = ["ethanol"], products = [{ compound = '
                     '"methyl-benzoate"',
                     '{ substrates = [], products = [{ compound = '
                     '"methyl-benzoate"'))
        self.assert_one(result, "error", "scope[3].substrates", "")

    def test_unknown_substrate_in_an_entry(self) -> None:
        """Requirement: Scope entries (substrates are registry keys)."""
        result = general_variant_run(
            "OSDB-0140-unknown-substrate.md",
            in_entry('substrates = ["acetic-acid", "ethanol"]',
                     'substrates = ["acetic-acid", "no-such-compound"]'))
        self.assert_one(result, "error", "scope[1].substrates",
                        'unknown compound "no-such-compound"')

    def test_substrate_that_is_a_product_of_its_own_entry(self) -> None:
        """Requirement: Scope entries (against the entry's products)."""
        result = general_variant_run(
            "OSDB-0140-substrate-is-product.md",
            in_entry('substrates = ["acetic-acid", "ethanol"]',
                     'substrates = ["acetic-acid", "ethyl-acetate"]'))
        self.assert_one(result, "error", "scope[1].substrates",
                        "ethyl-acetate is also a product")

    def test_substrate_named_twice_in_an_entry(self) -> None:
        """Requirement: Scope entries (a key named twice)."""
        result = general_variant_run(
            "OSDB-0140-substrate-twice.md",
            in_entry('substrates = ["acetic-acid", "ethanol"]',
                     'substrates = ["ethanol", "ethanol"]'))
        self.assert_one(result, "error", "scope[1].substrates",
                        "lists ethanol twice")

    def test_product_listed_twice_in_an_entry(self) -> None:
        """Requirement: Scope entries (products as at the top level,
        a product listed twice)."""
        result = general_variant_run(
            "OSDB-0140-product-twice.md",
            in_entry('{ compound = "propyl-acetate", yield_percent = 64.5 }',
                     '{ compound = "benzyl-acetate", yield_percent = 5 }'))
        self.assert_one(result, "error", "scope[2].products",
                        "lists benzyl-acetate twice")

    def test_a_compound_may_be_a_substrate_and_a_product_of_two_entries(
            self) -> None:
        """Requirement: Scope entries (each entry is checked on its own)."""
        result = general_variant_run(
            "OSDB-0140-across-entries.md",
            in_entry('substrates = ["ethanol"], products = [{ compound = '
                     '"methyl-benzoate"',
                     'substrates = ["ethyl-acetate"], products = [{ '
                     'compound = "methyl-benzoate"'))
        self.assert_clean(result)

    def test_a_compound_may_be_a_product_of_two_entries(self) -> None:
        """Requirement: Scope entries (the same product in two entries)."""
        result = general_variant_run(
            "OSDB-0140-product-in-two.md",
            in_entry('{ compound = "methyl-benzoate", yield_percent = 72.5 '
                     '}', '{ compound = "ethyl-acetate", yield_percent = 72.5'
                     ' }'))
        self.assert_clean(result)

    def test_yield_of_an_entry_product_out_of_range(self) -> None:
        """Requirement: Scope entries (products as at the top level,
        yield range)."""
        result = general_variant_run(
            "OSDB-0140-yield-high.md",
            in_entry("yield_percent = 85", "yield_percent = 100.5"))
        self.assert_one(result, "error", "scope[1].products[1].yield_percent",
                        "must be between 0 and 100")

    def test_yield_of_an_entry_product_as_a_string(self) -> None:
        """Requirement: Scope entries (products as at the top level,
        yield type)."""
        result = general_variant_run(
            "OSDB-0140-yield-string.md",
            in_entry("yield_percent = 78", 'yield_percent = "78"'))
        self.assert_one(result, "error", "scope[2].products[1].yield_percent",
                        "must be a number")

    def test_scale_of_an_entry_needs_a_unit(self) -> None:
        """Requirement: Scope entries (scale with unit)."""
        result = general_variant_run(
            "OSDB-0140-entry-scale.md",
            in_entry('scale = "20 mmol"', 'scale = "20"'))
        self.assert_one(result, "error", "scope[1].scale",
                        "must be a number followed by a unit")

    def test_note_must_be_a_non_empty_string(self) -> None:
        """Requirement: Scope entries (note)."""
        for value in ('""', "5"):
            with self.subTest(note=value):
                result = general_variant_run(
                    "OSDB-0140-entry-note.md",
                    in_entry('note = "Reflux."', f"note = {value}"))
                self.assert_one(result, "error", "scope[1].note", "")

    def test_times_that_are_a_number_and_a_unit_pass(self) -> None:
        """Requirement: Scope entries (time)."""
        for value in ("30 min", "1.5 h", "1,5 h", "2 d", "10  min", "0 h"):
            with self.subTest(time=value):
                result = general_variant_run(
                    "OSDB-0140-time.md",
                    in_entry('time = "2 h"', f'time = "{value}"'))
                self.assert_clean(result)

    def test_times_that_are_not_are_rejected(self) -> None:
        """Requirement: Scope entries (time, rejected forms)."""
        for value in ("2h", "2 H", "2 hours", "h", "1.5.2 h", "-2 h",
                      " 2 h", "2 h ", "2 s", ""):
            with self.subTest(time=value):
                result = general_variant_run(
                    "OSDB-0140-time.md",
                    in_entry('time = "2 h"', f'time = "{value}"'))
                self.assert_one(result, "error", "scope[1].time",
                                f'"{value}" ' + PRODUCT_NOTE)

    def test_time_that_is_not_a_string_is_rejected(self) -> None:
        """Requirement: Scope entries (time is a string)."""
        result = general_variant_run(
            "OSDB-0140-time-number.md",
            in_entry('time = "2 h"', "time = 2"))
        self.assert_one(result, "error", "scope[1].time", "")

    def test_temperatures_that_are_numbers_pass(self) -> None:
        """Requirement: Scope entries (temperature)."""
        for value in ("80", "80.5", "-20", "0", "-0.5"):
            with self.subTest(temperature=value):
                result = general_variant_run(
                    "OSDB-0140-temperature.md",
                    in_entry("temperature = 80", f"temperature = {value}"))
                self.assert_clean(result)

    def test_temperatures_that_are_not_numbers_are_rejected(self) -> None:
        """Requirement: Scope entries (temperature, rejected values)."""
        for value in ("true", '"80"', "inf", "-inf", "nan", "[80]"):
            with self.subTest(temperature=value):
                result = general_variant_run(
                    "OSDB-0140-temperature.md",
                    in_entry("temperature = 80", f"temperature = {value}"))
                self.assert_one(result, "error", "scope[1].temperature",
                                "must be a number in °C, unquoted, e.g. 80")

    def test_scale_stays_required_for_a_general_procedure(self) -> None:
        """Requirement: Required front-matter fields (scale)."""
        result = general_variant_run("OSDB-0140-no-scale.md",
                                     remove_line("scale"))
        self.assert_one(result, "error", "scale", "required field missing")

    def test_a_procedure_without_scope_still_needs_products(self) -> None:
        """Requirement: Required front-matter fields (products)."""
        result = general_variant_run(
            "OSDB-0140-no-scope.md", replace_block("scope", ""))
        self.assert_one(result, "error", "products", "required field missing")

    def test_problems_are_numbered_from_one_in_entry_order(self) -> None:
        """Requirement: Scope entries (entries are numbered from 1)."""
        result = general_variant_run(
            "OSDB-0140-three-problems.md",
            in_entry('time = "2 h"', 'time = "2 hours"'),
            in_entry('compound = "benzyl-acetate"',
                     'compound = "no-such-compound"'),
            in_entry('compound = "methyl-benzoate"',
                     'compound = "no-such-compound"'))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(
            [(p.field, p.severity) for p in result.problems],
            [("scope[1].time", "error"),
             ("scope[2].products[1].compound", "error"),
             ("scope[3].products[1].compound", "error")])


class SchemeImageTests(ValidatorTestCase):
    def test_scheme_image_missing(self) -> None:
        """Scenario: Scheme image missing."""
        result = general_variant_run(
            "OSDB-0140-missing-scheme.md",
            insert_line('scheme_image = "structures/missing.svg"'))
        self.assert_one(result, "error", "scheme_image", "not found")

    def test_an_existing_scheme_image_passes(self) -> None:
        """Requirement: Scheme image (an existing file)."""
        self.assertTrue((STATIC_DIR / "structures"
                         / "ethyl-acetate.svg").is_file())
        result = general_variant_run(
            "OSDB-0140-scheme.md",
            insert_line('scheme_image = "structures/ethyl-acetate.svg"'))
        self.assert_clean(result)

    def test_a_specific_procedure_may_set_one(self) -> None:
        """Requirement: Scheme image (any procedure)."""
        result = support.variant_run(
            "OSDB-0100-scheme.md",
            insert_line('scheme_image = "structures/ethyl-acetate.svg"'))
        self.assert_clean(result)
        result = support.variant_run(
            "OSDB-0100-missing-scheme.md",
            insert_line('scheme_image = "structures/missing.svg"'))
        self.assert_one(result, "error", "scheme_image", "not found")

    def test_the_path_rules_of_the_structure_image(self) -> None:
        """Requirement: Scheme image (the rules of Structure image
        path)."""
        for value, message in (
                ("structures/ethyl-acetate.jpg", "must end in .svg or .png"),
                ("ethyl-acetate.svg",
                 "must be a relative path under structures/"),
                ("structures/../structures/ethyl-acetate.svg",
                 "must be a relative path under structures/")):
            with self.subTest(scheme_image=value):
                result = general_variant_run(
                    "OSDB-0140-scheme-path.md",
                    insert_line(f'scheme_image = "{value}"'))
                self.assert_one(result, "error", "scheme_image", message)

    def test_wrong_prefix_or_suffix_is_not_checked_for_existence(
            self) -> None:
        """Requirement: Scheme image (existence left unchecked)."""
        for value in ("ethyl-acetate.jpg", "structures/missing.jpg"):
            with self.subTest(scheme_image=value):
                result = general_variant_run(
                    "OSDB-0140-scheme-path.md",
                    insert_line(f'scheme_image = "{value}"'))
                self.assertEqual(len(result.problems), 1, result.stdout)
                self.assertNotIn("not found", result.stdout)

    def test_a_scheme_image_that_is_not_a_string(self) -> None:
        """Requirement: Scheme image (wrong type)."""
        result = general_variant_run("OSDB-0140-scheme-number.md",
                                    insert_line("scheme_image = 5"))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual([(p.field, p.severity) for p in result.problems],
                         [("scheme_image", "error")])


def general(*edits) -> str:
    return apply_edits(general_text(), edits)


def scheme(path: str = "structures/ethyl-acetate.svg"):
    return insert_line(f'scheme_image = "{path}"')


class GeneralVariantTests(ValidatorTestCase):
    def pair(self, german: str, english: str | None = None
             ) -> support.Result:
        return run({"OSDB-0140-general.md": english or general(),
                    "OSDB-0140-general.de.md": germanised(german)})

    def shared_error(self, result: support.Result, field: str) -> None:
        errors = [p for p in result.problems if p.field == field]
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(errors, result.stdout)
        self.assertTrue(all(p.path.endswith(".de.md") for p in errors),
                        result.stdout)
        self.assertIn("OSDB-0140-general.md", errors[0].message)

    def test_a_translation_shares_the_scope_but_not_the_notes(self) -> None:
        """Scenario: A translation shares its ID and facts (scope)."""
        translated = general(
            replace_text('note = "Reflux."', 'note = "Unter Rückfluss."'),
            support.replace_line("title", 'title = "Acetatester"'),
            support.replace_line("hazards",
                                 'hazards = ["Entzündbare Flüssigkeit"]'))
        self.assert_clean(self.pair(translated))

    def test_a_note_may_be_missing_from_a_translation(self) -> None:
        """Requirement: Procedure variants (notes are not compared)."""
        self.assert_clean(self.pair(general(
            replace_text(', note = "Reflux."', ""))))
        self.assert_clean(self.pair(general(), general(
            replace_text(', note = "Reflux."', ""))))

    def test_a_differing_scope_is_an_error_on_the_translation(self) -> None:
        """Scenario: A translation shares its ID and facts (a differing
        scope)."""
        for change in (
                replace_text("yield_percent = 85", "yield_percent = 80"),
                replace_text('time = "2 h"', 'time = "3 h"'),
                replace_text("temperature = 80", "temperature = 70"),
                replace_text('scale = "20 mmol"', 'scale = "10 mmol"'),
                replace_text('{ substrates = ["acetic-acid"], products',
                             '{ substrates = ["acetic-acid"], time = '
                             '"1 h", products'),
                replace_text('compound = "benzyl-acetate"',
                             'compound = "propyl-acetate"'),
                replace_text('substrates = ["acetic-acid", "ethanol"]',
                             'substrates = ["ethanol", "acetic-acid"]'),
                replace_block("scope", "scope = [" + ENTRY_3 + "]")):
            with self.subTest(change=change):
                self.shared_error(self.pair(general(change)), "scope")

    def test_scope_numbers_agree_by_value(self) -> None:
        """Requirement: Procedure variants (85 and 85.0)."""
        self.assert_clean(self.pair(general(
            replace_text("yield_percent = 85", "yield_percent = 85.0"))))
        self.assert_clean(self.pair(general(
            replace_text("temperature = 80", "temperature = 80.0"))))

    def test_scheme_images_are_shared(self) -> None:
        """Requirement: Procedure variants (scheme_image)."""
        self.assert_clean(self.pair(general(scheme()), general(scheme())))
        other = "structures/trans-stilbene.svg"
        self.shared_error(self.pair(general(scheme(other)),
                                    general(scheme())), "scheme_image")
        self.shared_error(self.pair(general(), general(scheme())),
                          "scheme_image")
        self.shared_error(self.pair(general(scheme()), general()),
                          "scheme_image")


class CollectionGeneralProcedureTests(ValidatorTestCase):
    """The test collection's general procedure and its compounds, as the
    demo will hold them (sample-procedures "Demo general procedure")."""

    ENGLISH = (TEST_COLLECTION / "md" / "procedures"
               / "OSDB-0009-benzylic-alcohols.md")
    GERMAN = ENGLISH.with_name("OSDB-0009-benzylic-alcohols.de.md")
    SCOPE = [
        {"substrates": ["4-acetylbiphenyl"], "time": "30 min",
         "products": [{"compound": "1-biphenyl-4-yl-ethanol",
                       "yield_percent": 90}]},
        {"substrates": ["acetophenone"], "time": "20 min",
         "products": [{"compound": "1-phenylethanol",
                       "yield_percent": 85}]},
        {"substrates": ["4-bromoacetophenone"], "time": "30 min",
         "scale": "5 mmol",
         "products": [{"compound": "1-4-bromophenyl-ethanol",
                       "yield_percent": 88}]},
    ]
    COMPOUNDS = {
        "acetophenone": ["Acetophenone", "Acetophenon", "C8H8O", 120.15,
                         "CC(=O)c1ccccc1", "98-86-2"],
        "1-phenylethanol": ["1-Phenylethanol", "1-Phenylethanol", "C8H10O",
                            122.17, "CC(O)c1ccccc1", "98-85-1"],
        "1-4-bromophenyl-ethanol": [
            "1-(4-Bromophenyl)ethanol", "1-(4-Bromphenyl)ethanol",
            "C8H9BrO", 201.06, "CC(O)c1ccc(Br)cc1", "5391-88-8"],
    }

    def read(self, path) -> dict:
        self.assertTrue(path.is_file(), f"{path.name} is missing")
        return front_matter(path.read_text(encoding="utf-8"))

    def test_both_variants_carry_the_stated_scope(self) -> None:
        """Scenario: The demo's general procedure (the test collection)."""
        for path in (self.ENGLISH, self.GERMAN):
            data = self.read(path)
            with self.subTest(file=path.name):
                self.assertEqual(data["id"], "OSDB-0009")
                self.assertEqual(data["reaction_types"], ["reduction"])
                self.assertEqual(data["tags"],
                                 ["sample-data", "sodium-borohydride"])
                self.assertEqual(data["scale"], "10 mmol")
                self.assertEqual(data["scheme_image"],
                                 "structures/aryl-ketone-reduction.svg")
                self.assertNotIn("products", data)
                self.assertNotIn("substrates", data)
                notes = [entry.pop("note", None) for entry in data["scope"]]
                self.assertEqual(data["scope"], self.SCOPE)
                self.assertEqual([n is None for n in notes],
                                 [True, True, False])
                self.assertTrue(notes[2].strip())
        english, german = (self.read(p)["scope"] for p in
                           (self.ENGLISH, self.GERMAN))
        self.assertNotEqual(english[2]["note"], german[2]["note"])

    def test_the_compound_files_hold_the_stated_values(self) -> None:
        """Scenario: The demo's general procedure (compounds)."""
        keys = ["name", "name_de", "formula", "mw", "smiles", "cas"]
        for key, values in self.COMPOUNDS.items():
            path = TEST_COLLECTION / "compounds" / f"{key}.toml"
            with self.subTest(compound=key):
                self.assertTrue(path.is_file(), f"{path.name} is missing")
                text = path.read_text(encoding="utf-8")
                data = tomllib.loads(text)
                self.assertEqual(list(data)[:len(keys)], keys)
                self.assertEqual(list(data.values())[:len(keys)], values)
                self.assertEqual(
                    [line.split(" = ")[0]
                     for line in text.splitlines()][:len(keys)], keys)

    def test_the_scheme_image_is_part_of_the_collection(self) -> None:
        """Harness: the scheme image exists in the test collection."""
        self.assertTrue((TEST_COLLECTION / "static" / "structures"
                         / "aryl-ketone-reduction.svg").is_file())

    def test_the_english_dates_keep_it_off_the_recent_list(self) -> None:
        """Requirement: Demo general procedure (lastmod)."""
        english = self.read(self.ENGLISH)["lastmod"]
        others = [front_matter(p.read_text(encoding="utf-8"))["lastmod"]
                  for p in self.ENGLISH.parent.glob("OSDB-*.md")
                  if p.name.count(".") == 1 and p != self.ENGLISH]
        self.assertTrue(others)
        self.assertLessEqual(english, min(others))
        german = [front_matter(p.read_text(encoding="utf-8"))
                  for p in self.ENGLISH.parent.glob("OSDB-*.de.md")]
        self.assertEqual(
            {d[key] for d in german for key in ("date", "lastmod")},
            {german[0]["lastmod"]})

    def test_the_collection_validates(self) -> None:
        """Harness: the collection's procedures and compounds are valid."""
        result = support.run_validator([
            "--vocabulary", REPO / "site" / "data" / "reaction_types.toml",
            "--settings", TEST_COLLECTION / "orgsyndb.toml",
            "--static-dir", TEST_COLLECTION / "static",
            "--compounds", TEST_COLLECTION / "compounds",
            TEST_COLLECTION / "md" / "procedures"])
        self.assert_clean(result)


if __name__ == "__main__":
    unittest.main()
