"""The compound registry (compound-registry): its files, fields and
checks, driven through registry variant runs."""

import shutil
import tempfile
import unittest
from pathlib import Path

from support import (COMPOUNDS, FIXTURES, ValidatorTestCase, edit_compound,
                     fixture_run, registry_copy, registry_variant_run,
                     remove_line, replace_line, run_validator)

COMPOUND_FILES = len(list(COMPOUNDS.glob("*.toml")))
EDITED = "ethyl-acetate.toml"


def append_line(new_line: str):
    """A text edit appending ``new_line`` to a compound file."""
    return lambda text: text + new_line + "\n"


class CompoundFileTests(ValidatorTestCase):
    def test_badly_named_file_is_rejected(self) -> None:
        """Scenario: Badly named compound file."""
        def change(registry: Path) -> None:
            (registry / "Ethyl_Acetate.toml").write_text(
                (registry / EDITED).read_text(encoding="utf-8"),
                encoding="utf-8")
        result = registry_variant_run(change)
        self.assert_one(result, "error", "file_name",
                        "must be named <key>.toml",
                        path_suffix="Ethyl_Acetate.toml")

    def test_file_name_message_names_the_rule(self) -> None:
        """Requirement: Compound files (file name message)."""
        def change(registry: Path) -> None:
            (registry / "ethyl-acetate.txt").write_text(
                "name = 'x'\n", encoding="utf-8")
        result = registry_variant_run(change)
        self.assert_one(
            result, "error", "file_name",
            "must be named <key>.toml, the key lowercase and hyphenated",
            path_suffix="ethyl-acetate.txt")

    def test_unparseable_file_is_rejected(self) -> None:
        """Scenario: Unparseable compound file."""
        result = registry_variant_run(
            edit_compound("ethyl-acetate",
                          lambda text: 'name = "Ethyl acetate\n'))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(len(result.problems), 2, result.stdout)
        by_field = {problem.field: problem for problem in result.problems}
        self.assertEqual(set(by_field), {"toml", "products[1].compound"})
        toml, unknown = by_field["toml"], by_field["products[1].compound"]
        self.assertTrue(toml.path.endswith(EDITED), result.stdout)
        self.assertEqual(toml.severity, "error")
        self.assertIn("invalid TOML", toml.message)
        self.assertTrue(unknown.path.endswith("OSDB-0100-baseline.md"),
                        result.stdout)
        self.assertEqual(unknown.severity, "error")
        self.assertIn('unknown compound "ethyl-acetate"', unknown.message)

    def test_file_that_is_not_utf8_is_one_toml_error(self) -> None:
        """Requirement: Compound files (a file that is not UTF-8)."""
        def change(registry: Path) -> None:
            (registry / "unused-compound.toml").write_bytes(
                b'name = "Caf\xe9"\n')
        result = registry_variant_run(change)
        self.assert_one(result, "error", "toml", "",
                        path_suffix="unused-compound.toml")

    def test_subdirectory_is_rejected_and_not_read(self) -> None:
        """Requirement: Compound files (a subdirectory)."""
        def change(registry: Path) -> None:
            nested = registry / "nested"
            nested.mkdir()
            (nested / "unused-compound.toml").write_text(
                "not valid toml [\n", encoding="utf-8")
        result = registry_variant_run(change)
        self.assert_one(result, "error", "file_name",
                        "subdirectories are not supported",
                        path_suffix="nested")

    def test_dotfiles_and_unused_compounds_draw_nothing(self) -> None:
        """Scenario: Dotfiles and unused compounds."""
        def change(registry: Path) -> None:
            (registry / ".gitkeep").write_text("", encoding="utf-8")
            (registry / "unused-compound.toml").write_text(
                (registry / EDITED).read_text(encoding="utf-8"),
                encoding="utf-8")
        result = registry_variant_run(change)
        self.assert_clean(result)

    def test_the_summary_counts_the_compound_files(self) -> None:
        """Requirement: Problem report format (compound files count)."""
        result = fixture_run("baseline")
        self.assertIn(f"validated {1 + COMPOUND_FILES} files: "
                      "0 errors, 0 warnings", result.stderr)

    def test_key_pattern_is_enforced(self) -> None:
        """Requirement: Compound files (the key pattern)."""
        for name in ("-ethyl.toml", "ethyl--acetate.toml",
                     "ethyl acetate.toml", "Ethyl.toml", "ethyl_acetate.toml",
                     "ethyl.TOML"):
            with self.subTest(name=name):
                def change(registry: Path, name: str = name) -> None:
                    (registry / name).write_text(
                        (registry / EDITED).read_text(encoding="utf-8"),
                        encoding="utf-8")
                result = registry_variant_run(change)
                self.assert_one(result, "error", "file_name",
                                "must be named <key>.toml",
                                path_suffix=name)

    def test_digits_and_hyphens_make_a_key(self) -> None:
        """Requirement: Compound files (a key may start with a digit)."""
        def change(registry: Path) -> None:
            (registry / "1-2-dichloroethane.toml").write_text(
                (registry / EDITED).read_text(encoding="utf-8"),
                encoding="utf-8")
        self.assert_clean(registry_variant_run(change))

    def test_problems_carry_the_registry_argument_as_given(self) -> None:
        """Requirement: Problem report format (compound file path)."""
        with registry_copy() as registry:
            edit_compound("ethyl-acetate", replace_line("mw", "mw = 0"))(
                registry)
            result = run_validator(
                ["--vocabulary", FIXTURES / "reaction_types.toml",
                 "--static-dir", FIXTURES / "static",
                 "--compounds", registry, FIXTURES / "baseline"])
        self.assert_one(result, "error", "mw", "must be greater than 0")
        self.assertEqual(result.problems[0].path,
                         f"{registry}/ethyl-acetate.toml")


class CompoundFieldTests(ValidatorTestCase):
    def test_missing_formula_is_rejected(self) -> None:
        """Scenario: Missing formula."""
        result = registry_variant_run(
            edit_compound("ethyl-acetate", remove_line("formula")))
        self.assert_one(result, "error", "formula",
                        "required field missing", path_suffix=EDITED)

    def test_each_required_key_is_required(self) -> None:
        """Requirement: Compound fields (required keys)."""
        for key in ("name", "formula", "mw", "smiles"):
            with self.subTest(key=key):
                result = registry_variant_run(
                    edit_compound("ethyl-acetate", remove_line(key)))
                self.assert_one(result, "error", key,
                                "required field missing",
                                path_suffix=EDITED)

    def test_optional_keys_may_be_absent(self) -> None:
        """Requirement: Compound fields (optional keys)."""
        for key in ("name_de", "cas", "structure_image"):
            with self.subTest(key=key):
                result = registry_variant_run(
                    edit_compound("ethyl-acetate", remove_line(key)))
                self.assert_clean(result)

    def test_molecular_weight_of_zero_is_rejected(self) -> None:
        """Scenario: Molecular weight of zero."""
        result = registry_variant_run(
            edit_compound("ethyl-acetate", replace_line("mw", "mw = 0")))
        self.assert_one(result, "error", "mw", "must be greater than 0")

    def test_negative_and_infinite_weights_are_rejected(self) -> None:
        """Requirement: Compound fields (mw is finite and positive)."""
        for value in ("-88.11", "inf", "nan"):
            with self.subTest(mw=value):
                result = registry_variant_run(edit_compound(
                    "ethyl-acetate", replace_line("mw", f"mw = {value}")))
                self.assert_one(result, "error", "mw",
                                "must be greater than 0")

    def test_molecular_weight_that_is_not_a_number_is_rejected(
            self) -> None:
        """Requirement: Compound fields (mw message)."""
        for value in ('"88.11"', "true"):
            with self.subTest(mw=value):
                result = registry_variant_run(edit_compound(
                    "ethyl-acetate", replace_line("mw", f"mw = {value}")))
                self.assert_one(
                    result, "error", "mw",
                    "must be a number in g/mol, unquoted, e.g. 88.11")

    def test_integer_molecular_weight_passes(self) -> None:
        """Requirement: Compound fields (integer or float)."""
        result = registry_variant_run(
            edit_compound("ethyl-acetate", replace_line("mw", "mw = 88")))
        self.assert_clean(result)

    def test_empty_strings_are_rejected(self) -> None:
        """Requirement: Compound fields (non-empty strings)."""
        for key in ("name", "name_de", "formula", "smiles"):
            with self.subTest(key=key):
                result = registry_variant_run(edit_compound(
                    "ethyl-acetate", replace_line(key, f'{key} = ""')))
                self.assert_one(result, "error", key, "must not be empty")

    def test_empty_german_name_is_rejected(self) -> None:
        """Scenario: Empty German name."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line("name_de", 'name_de = ""')))
        self.assert_one(result, "error", "name_de", "must not be empty")

    def test_value_of_the_wrong_type_is_rejected(self) -> None:
        """Requirement: Compound fields (wrong type)."""
        for key in ("name", "name_de", "formula", "smiles"):
            with self.subTest(key=key):
                result = registry_variant_run(edit_compound(
                    "ethyl-acetate", replace_line(key, f"{key} = 5")))
                self.assert_one(result, "error", key, "must be a string")

    def test_cas_number_with_a_wrong_check_digit_is_rejected(self) -> None:
        """Scenario: CAS number with a wrong check digit."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line("cas", 'cas = "141-78-5"')))
        self.assert_one(result, "error", "cas", "check digit")

    def test_cas_number_of_the_wrong_form_is_rejected(self) -> None:
        """Requirement: Compound fields (cas message)."""
        for value in ('"141786"', '"141-78"', '"1-78-6"', '"141-7-6"',
                      '"64-17-5 "'):
            with self.subTest(cas=value):
                result = registry_variant_run(edit_compound(
                    "ethyl-acetate", replace_line("cas", f"cas = {value}")))
                self.assert_one(
                    result, "error", "cas",
                    'must have the form NNNNNNN-NN-N, e.g. "64-17-5"')

    def test_misspelt_key_is_a_warning(self) -> None:
        """Scenario: Misspelt key."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", append_line('smile = "CCOC(C)=O"')))
        self.assert_one(result, "warning", "smile", "unknown field",
                        path_suffix=EDITED)


class StructureImageTests(ValidatorTestCase):
    def test_missing_image_file_is_rejected(self) -> None:
        """Scenario: Image file missing."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line(
                "structure_image",
                'structure_image = "structures/missing.svg"')))
        self.assert_one(result, "error", "structure_image", "not found",
                        path_suffix=EDITED)

    def test_unsupported_image_type_is_rejected(self) -> None:
        """Scenario: Unsupported image type."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line(
                "structure_image",
                'structure_image = "structures/ethyl-acetate.jpg"')))
        self.assert_one(result, "error", "structure_image",
                        "must end in .svg or .png")

    def test_image_outside_the_structures_directory_is_rejected(
            self) -> None:
        """Scenario: Image outside the structures directory."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line(
                "structure_image",
                'structure_image = "ethyl-acetate.svg"')))
        self.assert_one(result, "error", "structure_image",
                        "must be a relative path under structures/")

    def test_parent_component_is_rejected(self) -> None:
        """Requirement: Structure image path (no .. component)."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line(
                "structure_image",
                'structure_image = "structures/../structures/'
                'ethyl-acetate.svg"')))
        self.assert_one(result, "error", "structure_image",
                        "must be a relative path under structures/")

    def test_wrong_prefix_or_suffix_is_not_checked_for_existence(
            self) -> None:
        """Scenario: Dependent checks are suppressed (structure image)."""
        for value in ("ethyl-acetate.jpg", "structures/missing.jpg"):
            with self.subTest(structure_image=value):
                result = registry_variant_run(edit_compound(
                    "ethyl-acetate", replace_line(
                        "structure_image",
                        f'structure_image = "{value}"')))
                self.assertEqual(len(result.problems), 1, result.stdout)
                self.assertNotIn("not found", result.stdout)

    def test_png_image_passes(self) -> None:
        """Requirement: Structure image path (.png)."""
        with tempfile.TemporaryDirectory() as tmp:
            static = Path(tmp) / "static"
            shutil.copytree(FIXTURES / "static", static)
            (static / "structures" / "ethyl-acetate.png").write_bytes(
                b"\x89PNG\r\n\x1a\n")
            with registry_copy() as registry:
                edit_compound("ethyl-acetate", replace_line(
                    "structure_image",
                    'structure_image = "structures/ethyl-acetate.png"'))(
                    registry)
                result = run_validator(
                    ["--vocabulary", FIXTURES / "reaction_types.toml",
                     "--static-dir", static, "--compounds", registry,
                     FIXTURES / "baseline"])
        self.assert_clean(result)

    def test_image_that_is_not_a_string_is_rejected(self) -> None:
        """Requirement: Compound fields (structure_image wrong type)."""
        result = registry_variant_run(edit_compound(
            "ethyl-acetate", replace_line(
                "structure_image", "structure_image = 5")))
        self.assert_one(result, "error", "structure_image",
                        "must be a string")


if __name__ == "__main__":
    unittest.main()
