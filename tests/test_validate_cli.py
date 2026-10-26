"""Command-line behaviour of tools/validate.py (procedure-validation)."""

import ast
import sys
import tempfile
import unittest
from pathlib import Path

import support
from support import (FIXTURES, VALIDATOR, ValidatorTestCase,
                     fixture_run, run_validator, valid_set_run,
                     variant_root)


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
                result = run_validator([root], cwd=Path(cwd))
        self.assertEqual([p for p in result.problems
                          if p.field == "reaction_types"], [],
                         result.stdout)
        self.assert_clean(result)

    def test_default_static_directory_is_the_working_directorys(
            self) -> None:
        """Scenario: Default static directory is the working directory's."""
        edit = support.insert_line(
            'structure_image = "structures/osdb-0100.svg"')
        with variant_root("OSDB-0100-baseline.md", edit) as root:
            with tempfile.TemporaryDirectory() as cwd:
                structures = Path(cwd) / "static" / "structures"
                structures.mkdir(parents=True)
                (structures / "osdb-0100.svg").write_text("<svg/>\n")
                result = run_validator([root], cwd=Path(cwd))
                (structures / "osdb-0100.svg").unlink()
                missing = run_validator([root], cwd=Path(cwd))
        self.assert_clean(result)
        self.assert_one(missing, "error", "structure_image", "not found")


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
            r"^.+/OSDB-0110-yield-out-of-range\.md:yield_percent: "
            r"error: .+$")

    def test_summary_line_goes_to_stderr(self) -> None:
        """Scenario: Summary line."""
        result = valid_set_run()
        self.assertIn("validated 4 files: 0 errors, 0 warnings",
                      result.stderr)

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
        self.assertIn("validated 1 files", result.stderr)


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
