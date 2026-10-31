"""Command-line behaviour of tools/validate.py (procedure-validation)."""

import ast
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import support
from support import (BASELINE, COMPOUNDS, FIXTURES, STATIC_DIR, VALIDATOR,
                     ValidatorTestCase, declaration, fixture_run,
                     run_validator, valid_set_run, variant_root)

COMPOUND_FILES = len(list(COMPOUNDS.glob("*.toml")))


class CommandLineInterfaceTests(ValidatorTestCase):
    def test_no_roots_is_a_usage_error(self) -> None:
        """Scenario: No roots given."""
        result = run_validator([])
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stderr.strip(), "")

    def test_org_root_option_is_refused(self) -> None:
        """Scenario: Org root option is refused."""
        result = run_validator(["--org-root", FIXTURES / "valid" / "org",
                                FIXTURES / "valid" / "md"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--org-root", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_root_that_is_not_a_directory_is_a_usage_error(self) -> None:
        """Scenario: Root is not a directory."""
        result = run_validator([FIXTURES / "does-not-exist"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("validate.py: error:", result.stderr)
        self.assertIn("not a directory", result.stderr)

    def test_validator_imports_only_the_standard_library(self) -> None:
        """Scenario: Only standard-library imports."""
        self.assertTrue(VALIDATOR.is_file(),
                        "tools/validate.py does not exist")
        tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names.add((node.module or "").split(".")[0])
        self.assertTrue(names, "no imports found")
        self.assertEqual(names - set(sys.stdlib_module_names), set())


class DefaultPathTests(ValidatorTestCase):
    def test_default_vocabulary_resolves_from_the_script_location(
            self) -> None:
        """Scenario: Run from an unrelated working directory."""
        edit = support.replace_line(
            "reaction_types", 'reaction_types = ["reductive-amination"]')
        with variant_root("OSDB-0100-baseline.md", edit) as root:
            with tempfile.TemporaryDirectory() as cwd:
                result = run_validator(
                    ["--compounds", COMPOUNDS, "--static-dir", STATIC_DIR,
                     root], cwd=Path(cwd))
        self.assertEqual([p for p in result.problems
                          if p.field == "reaction_types"], [],
                         result.stdout)
        self.assert_clean(result)

    def test_default_static_and_registry_are_the_working_directorys(
            self) -> None:
        """Scenario: Default static and registry directories are the
        working directory's."""
        compound = (COMPOUNDS / "ethyl-acetate.toml").read_text(
            encoding="utf-8")
        self.assertIn('structure_image = "structures/ethyl-acetate.svg"',
                      compound)
        with variant_root("OSDB-0100-baseline.md") as root:
            with tempfile.TemporaryDirectory() as cwd:
                collection = Path(cwd)
                structures = collection / "static" / "structures"
                structures.mkdir(parents=True)
                shutil.copy2(STATIC_DIR / "structures"
                             / "ethyl-acetate.svg", structures)
                (collection / "compounds").mkdir()
                (collection / "compounds" / "ethyl-acetate.toml"
                 ).write_text(compound, encoding="utf-8")
                result = run_validator([root], cwd=collection)
                (structures / "ethyl-acetate.svg").unlink()
                missing_image = run_validator([root], cwd=collection)
                (collection / "compounds" / "ethyl-acetate.toml").unlink()
                missing_registry = run_validator([root], cwd=collection)
        self.assert_clean(result)
        self.assert_one(missing_image, "error", "structure_image",
                        "not found", path_suffix="ethyl-acetate.toml")
        self.assert_one(missing_registry, "error", "products[1].compound",
                        'unknown compound "ethyl-acetate"')

    def test_missing_registry_defines_no_compound(self) -> None:
        """Scenario: Missing registry."""
        result = fixture_run(
            "baseline", compounds=FIXTURES / "no-such-registry")
        self.assert_one(result, "error", "products[1].compound",
                        'unknown compound "ethyl-acetate"')

    def test_default_settings_file_is_the_working_directorys(self) -> None:
        """Scenario: Default settings file is the working directory's."""
        settings = declaration("item_number", "text", "Item no.",
                               "required = true")
        with tempfile.TemporaryDirectory() as cwd:
            (Path(cwd) / "orgsyndb.toml").write_text(
                "format = 1\n" + settings, encoding="utf-8")
            result = run_validator(
                ["--compounds", COMPOUNDS, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.problems), COMPOUND_FILES,
                         result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), COMPOUND_FILES)
        for problem in result.problems:
            self.assertEqual(problem.field, "item_number", result.stdout)
            self.assertEqual(problem.severity, "error", result.stdout)
            self.assertIn("required field missing", problem.message)
        self.assertEqual(
            sorted(Path(p.path).name for p in result.problems),
            sorted(path.name for path in COMPOUNDS.glob("*.toml")))

    def test_the_settings_option_outranks_the_working_directory(
            self) -> None:
        """Requirement: Command-line interface (--settings)."""
        settings = declaration("item_number", "text", "Item no.",
                               "required = true")
        with tempfile.TemporaryDirectory() as cwd:
            (Path(cwd) / "orgsyndb.toml").write_text(
                "format = 1\n" + settings, encoding="utf-8")
            result = run_validator(
                ["--settings", FIXTURES / "fields" / "orgsyndb.toml",
                 "--compounds", COMPOUNDS, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_clean(result)

    def test_a_missing_default_settings_file_declares_no_field(
            self) -> None:
        """Requirement: Default paths resolve from the script location (a
        settings file that does not exist, `--settings` omitted)."""
        with tempfile.TemporaryDirectory() as cwd:
            self.assertEqual(list(Path(cwd).iterdir()), [])
            result = run_validator(
                ["--compounds", COMPOUNDS, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_clean(result)

    def test_compounds_option_names_the_registry(self) -> None:
        """Requirement: Command-line interface (--compounds)."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            registry.mkdir()
            shutil.copy2(COMPOUNDS / "ethyl-acetate.toml", registry)
            result = run_validator(
                ["--vocabulary", FIXTURES / "reaction_types.toml",
                 "--static-dir", STATIC_DIR, "--compounds", registry,
                 BASELINE.parent])
        self.assert_clean(result)
        self.assertIn("validated 2 files: 0 errors, 0 warnings",
                      result.stderr)


class VocabularyErrorTests(ValidatorTestCase):
    def test_entry_without_label_is_a_configuration_error(self) -> None:
        """Scenario: Entry without a label."""
        result = run_validator(
            ["--vocabulary", FIXTURES / "bad-vocabulary.toml",
             FIXTURES / "valid" / "md"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("label", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_vocabulary_file_is_a_configuration_error(self) -> None:
        """Scenario: Missing vocabulary file."""
        result = run_validator(
            ["--vocabulary", FIXTURES / "no-such-vocabulary.toml",
             FIXTURES / "valid" / "md"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("validate.py: error:", result.stderr)

    def test_vocabulary_that_is_not_toml_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors (not valid TOML)."""
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "vocabulary.toml"
            bad.write_text("[esterification\nlabel = 1\n")
            result = run_validator(
                ["--vocabulary", bad, FIXTURES / "valid" / "md"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("validate.py: error:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_vocabulary_key_that_is_not_a_slug_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors (top-level key not a slug)."""
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "vocabulary.toml"
            bad.write_text('[Bad_Key]\nlabel = "Bad"\n')
            result = run_validator(
                ["--vocabulary", bad, FIXTURES / "valid" / "md"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("validate.py: error:", result.stderr)
        self.assertEqual(result.stdout, "")


class ProblemReportFormatTests(ValidatorTestCase):
    def test_problem_line_has_path_field_severity_and_message(self) -> None:
        """Scenario: Line shape."""
        result = fixture_run("invalid/yield-out-of-range")
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout)
        self.assertRegex(
            lines[0],
            r"^.+/OSDB-0110-yield-out-of-range\.md:"
            r"products\[1\]\.yield_percent: error: .+$")

    def test_summary_line_goes_to_stderr(self) -> None:
        """Scenario: Summary line."""
        result = valid_set_run()
        self.assertIn(f"validated {4 + COMPOUND_FILES} files: "
                      "0 errors, 0 warnings", result.stderr)

    def test_identical_input_gives_byte_identical_output(self) -> None:
        """Scenario: Deterministic output."""
        roots = sorted(p.name for p in (FIXTURES / "invalid").iterdir()
                       if p.is_dir())
        self.assertGreaterEqual(len(roots), 5)
        args = [f"invalid/{name}" for name in roots]
        first = fixture_run(*args)
        second = fixture_run(*args)
        self.assertNotEqual(first.stdout, "")
        self.assertEqual(first.stdout, second.stdout)


class ExitStatusTests(ValidatorTestCase):
    def test_warnings_alone_exit_zero(self) -> None:
        """Scenario: Warnings alone do not fail."""
        result = fixture_run("warn/missing-section")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.problems), 1, result.stdout)
        self.assertEqual(result.problems[0].severity, "warning")

    def test_any_error_exits_one(self) -> None:
        """Scenario: Any error fails."""
        self.assertEqual(
            fixture_run("invalid/unknown-reaction-type").returncode, 1)


class FileDiscoveryTests(ValidatorTestCase):
    def test_subdirectory_in_content_root_is_an_error(self) -> None:
        """Scenario: Subdirectory in a content root."""
        result = fixture_run("invalid/subdirectory")
        self.assert_one(result, "error", "file_name",
                        "subdirectories are not supported",
                        path_suffix="nested")

    def test_stray_file_in_content_root_is_a_warning(self) -> None:
        """Scenario: Stray file in a content root."""
        result = fixture_run("warn/stray-file")
        self.assert_one(result, "warning", "file_name",
                        "not a procedure file; ignored",
                        path_suffix="notes.txt")

    def test_section_index_and_dotfiles_are_skipped(self) -> None:
        """Scenario: Hugo section index and dotfiles are skipped."""
        source = next((FIXTURES / "valid" / "md").glob("OSDB-0001-*.md"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "content"
            root.mkdir()
            (root / source.name).write_text(
                source.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "_index.md").write_text("Section page, no front "
                                            "matter.\n", encoding="utf-8")
            (root / ".gitkeep").write_text("", encoding="utf-8")
            result = fixture_run(root)
        self.assert_clean(result)
        self.assertIn(f"validated {1 + COMPOUND_FILES} files",
                      result.stderr)


class FrontMatterParsingTests(ValidatorTestCase):
    def test_yaml_delimiters_are_rejected(self) -> None:
        """Scenario: YAML front matter instead of TOML."""
        result = support.variant_run("OSDB-0100-no-front-matter.md",
                                     support.swap_delimiters())
        self.assert_one(result, "error", "front_matter",
                        "must begin with a +++ line")

    def test_unparseable_toml_is_one_front_matter_error(self) -> None:
        """Scenario: Unparseable TOML."""
        result = fixture_run("invalid/invalid-toml")
        self.assert_one(result, "error", "front_matter", "invalid TOML",
                        path_suffix="OSDB-0134-invalid-toml.md")


if __name__ == "__main__":
    unittest.main()
