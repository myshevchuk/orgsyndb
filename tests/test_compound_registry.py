"""The compound registry as the validator reads it (compound-registry,
"Registry checks"), driven through registry variant runs."""

import tempfile
import unittest
from pathlib import Path

from support import (FIXTURES, STATIC_DIR, ValidatorTestCase,
                     adding_substance, edit_registry, fixture_run,
                     registry_copy, registry_variant_run, run_validator,
                     setting_terms, setting_substance, substance, term,
                     valid_set_run, without_substance)


class UnknownCompoundTests(ValidatorTestCase):
    def test_a_missing_substance_is_an_unknown_compound(self) -> None:
        """Scenario: Unknown compound."""
        result = registry_variant_run(edit_registry(
            without_substance("ethyl-acetate")))
        self.assert_one(result, "error", "products[1].compound",
                        'unknown compound "ethyl-acetate"',
                        path_suffix="OSDB-0100-baseline.md")

    def test_each_procedure_that_names_it_draws_one_error(self) -> None:
        """Scenario: Unknown compound (one error for each procedure)."""
        with registry_copy() as registry:
            edit_registry(without_substance("ethyl-acetate"))(registry)
            result = fixture_run("valid/md", registry=registry)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 2, result.stdout)
        self.assertEqual(
            sorted(Path(p.path).name for p in result.problems),
            sorted(path.name for path in
                   (FIXTURES / "valid" / "md").glob("*.md")))
        for problem in result.problems:
            self.assertEqual(problem.severity, "error")
            self.assertIn('unknown compound "ethyl-acetate"',
                          problem.message)

    def test_a_substrate_is_looked_up_in_the_registry_too(self) -> None:
        """Requirement: Registry checks (the compound keys are the
        substances' keys, for substrates as for products)."""
        with registry_copy() as registry:
            edit_registry(without_substance("acetic-acid"))(registry)
            result = fixture_run("valid/md", registry=registry)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), 1, result.stdout)
        self.assertEqual(result.problems[0].field, "substrates")
        self.assertIn('unknown compound "acetic-acid"',
                      result.problems[0].message)

    def test_a_procedure_names_a_compound_by_its_substances_key(self) -> None:
        """Requirement: Registry checks (a procedure names a compound by
        its substance's key)."""
        def rename(table: dict) -> None:
            (found,) = [s for s in table["substances"]
                        if s["key"] == "ethyl-acetate"]
            found["key"] = "ethyl-ethanoate"
            table["substances"].sort(key=lambda s: s["key"])
        result = registry_variant_run(edit_registry(rename))
        self.assert_one(result, "error", "products[1].compound",
                        'unknown compound "ethyl-acetate"')


class SubstanceKeyTests(ValidatorTestCase):
    def test_a_substance_named_like_the_tabs_directory_is_an_error(
            self) -> None:
        """Scenario: A substance named like the tabs directory."""
        with registry_copy() as registry:
            edit_registry(adding_substance(substance("group", "Group")))(
                registry)
            result = fixture_run("baseline", registry=registry)
            self.assert_one(result, "error", "substances", "group",
                            path_suffix="registry.json")
            self.assertEqual(result.problems[0].path, str(registry))

    def test_the_problem_carries_the_registry_argument_as_given(
            self) -> None:
        """Requirement: Problem report format (the registry's path)."""
        with registry_copy() as registry:
            edit_registry(adding_substance(substance("group")))(registry)
            with tempfile.TemporaryDirectory() as cwd:
                relative = Path("sub") / "registry.json"
                (Path(cwd) / "sub").mkdir()
                (Path(cwd) / relative).write_bytes(registry.read_bytes())
                result = run_validator(
                    ["--static-dir", STATIC_DIR, "--registry", relative,
                     FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_one(result, "error", "substances", "group")
        self.assertEqual(result.problems[0].path, str(relative))


class NoValueChecksTests(ValidatorTestCase):
    def test_the_validator_checks_no_substance_value(self) -> None:
        """Requirement: Registry checks (it checks no substance's
        values)."""
        result = registry_variant_run(edit_registry(
            setting_substance(
                "ethyl-acetate", mw=-3, cas="not a cas number",
                formula="", name="", name_de="", smiles=None,
                article_number="no pattern", short_name="  "),
            setting_substance("ethanol", mw=0, group="no-such-group",
                              chemical_classes=[])))
        self.assert_clean(result)

    def test_a_substance_without_a_structure_image_draws_no_report(
            self) -> None:
        """Requirement: Structure images by key (no check reports a
        substance without an image)."""
        with tempfile.TemporaryDirectory() as empty:
            result = fixture_run("baseline",
                                 extra=["--static-dir", empty])
        self.assert_clean(result)

    def test_unused_substances_draw_nothing(self) -> None:
        """Requirement: Registry checks (substances no procedure
        names)."""
        result = registry_variant_run(edit_registry(
            adding_substance(substance("unused-substance"))))
        self.assert_clean(result)

    def test_the_summary_counts_procedures_only(self) -> None:
        """Requirement: Problem report format (the summary counts the
        Markdown procedure files and sequence files)."""
        result = valid_set_run()
        self.assert_clean(result)
        self.assertIn("validated 4 files", result.stderr)

    def test_vocabularies_of_the_registry_are_not_examined_for_style(
            self) -> None:
        """Requirement: Registry checks (the vocabularies are those
        procedure fields and reaction types name)."""
        result = registry_variant_run(edit_registry(setting_terms(
            "reaction-types", term("esterification", "Esterification",
                                   tree=False),
            term("Odd_Key", "Odd", tree=False))))
        self.assert_clean(result)


if __name__ == "__main__":
    unittest.main()
