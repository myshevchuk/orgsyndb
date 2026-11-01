"""Command-line behaviour of tools/validate.py (procedure-validation)."""

import ast
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import support
from support import (BASELINE, COMPOUNDS, FIXTURES, REACTION_TYPES, SETTINGS,
                     STATIC_DIR, VALIDATOR, ValidatorTestCase, append_text,
                     declaration, delete_reaction_types, edit_reaction_types,
                     fields_copy, fixture_run, replace_text, run_validator,
                     settings_variant_run, valid_set_run, variant_root,
                     write_reaction_types)

COMPOUND_FILES = len(list(COMPOUNDS.glob("*.toml")))
VALID_MD_FILES = len(list((FIXTURES / "valid" / "md").glob("*.md")))


def with_reaction_types(directory: Path) -> Path:
    """Put a copy of the fixture reaction types into the
    ``vocabularies/`` of ``directory``, a collection's root."""
    (directory / "vocabularies").mkdir(exist_ok=True)
    shutil.copyfile(REACTION_TYPES,
                    directory / "vocabularies" / REACTION_TYPES.name)
    return directory


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

    def test_vocabulary_option_is_refused(self) -> None:
        """Scenario: Vocabulary option is refused."""
        result = run_validator(
            ["--vocabulary", REACTION_TYPES, FIXTURES / "valid" / "md"])
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--vocabulary", result.stderr)
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
                collection = with_reaction_types(Path(cwd))
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
                 FIXTURES / "baseline"], cwd=with_reaction_types(Path(cwd)))
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
        with tempfile.TemporaryDirectory() as cwd, fields_copy() as copy:
            (Path(cwd) / "orgsyndb.toml").write_text(
                "format = 1\n" + settings, encoding="utf-8")
            result = run_validator(
                ["--settings", copy.settings, "--compounds", COMPOUNDS,
                 "--static-dir", STATIC_DIR, FIXTURES / "baseline"],
                cwd=Path(cwd))
        self.assert_clean(result)

    def test_a_missing_default_settings_file_declares_no_field(
            self) -> None:
        """Requirement: Default paths come from the working directory (a
        settings file that does not exist, `--settings` omitted)."""
        with tempfile.TemporaryDirectory() as cwd:
            with_reaction_types(Path(cwd))
            self.assertFalse((Path(cwd) / "orgsyndb.toml").exists())
            result = run_validator(
                ["--compounds", COMPOUNDS, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_clean(result)

    def test_an_empty_working_directory_has_no_reaction_types(self) -> None:
        """Requirement: Default paths come from the working directory
        (without `--settings`, the reaction types are the working
        directory's)."""
        with tempfile.TemporaryDirectory() as cwd:
            self.assertEqual(list(Path(cwd).iterdir()), [])
            result = run_validator(
                ["--compounds", COMPOUNDS, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_one(result, "error", "reaction_types",
                        'unknown reaction type "esterification"')

    def test_compounds_option_names_the_registry(self) -> None:
        """Requirement: Command-line interface (--compounds)."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            registry.mkdir()
            shutil.copy2(COMPOUNDS / "ethyl-acetate.toml", registry)
            result = run_validator(
                ["--settings", SETTINGS, "--static-dir", STATIC_DIR,
                 "--compounds", registry, BASELINE.parent])
        self.assert_clean(result)
        self.assertIn("validated 2 files: 0 errors, 0 warnings",
                      result.stderr)


class VocabularyErrorTests(ValidatorTestCase):
    def assert_configuration_error(self, result: support.Result,
                                   *needles: str) -> None:
        """Exit status 2, nothing on stdout, and a message on stderr that
        begins ``validate.py: error:`` and contains every needle."""
        self.assertEqual(result.returncode, 2,
                         f"stdout={result.stdout!r} "
                         f"stderr={result.stderr!r}")
        self.assertEqual(result.stdout, "")
        self.assertIn("validate.py: error:", result.stderr)
        for needle in needles:
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stderr)

    def run_on_valid_md(self, *steps: support.SettingsChange
                        ) -> support.Result:
        return settings_variant_run(*steps, roots=["valid/md"])

    def test_entry_without_label_is_a_configuration_error(self) -> None:
        """Scenario: Entry without a label."""
        result = self.run_on_valid_md(edit_reaction_types(replace_text(
            'label = "Reduction"', 'note = "no label"')))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        for needle in ("reaction-types.toml", "reduction", "label"):
            with self.subTest(needle=needle):
                self.assertIn(needle, result.stderr)

    def test_missing_vocabulary_file_is_no_configuration_error(
            self) -> None:
        """Scenario: Missing vocabulary file."""
        result = self.run_on_valid_md(delete_reaction_types())
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("validate.py: error:", result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), VALID_MD_FILES)
        self.assertEqual(len(result.problems), VALID_MD_FILES, result.stdout)
        for problem in result.problems:
            self.assertEqual(problem.field, "reaction_types", result.stdout)
            self.assertIn("unknown reaction type", problem.message)

    def test_vocabulary_that_is_not_toml_is_a_configuration_error(
            self) -> None:
        """Scenario: Not TOML."""
        result = self.run_on_valid_md(
            edit_reaction_types(append_text("[reduction")))
        self.assert_configuration_error(result, "reaction-types.toml")

    def test_vocabulary_that_is_not_utf_8_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (cannot be read as UTF-8)."""
        result = self.run_on_valid_md(write_reaction_types(
            b'[esterification]\nlabel = "Caf\xe9"\n'))
        self.assert_configuration_error(result, "reaction-types.toml")

    def test_vocabulary_key_that_is_not_a_slug_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (a top-level key that is not a slug)."""
        result = self.run_on_valid_md(edit_reaction_types(
            append_text('\n[Bad_Key]\nlabel = "Bad"')))
        self.assert_configuration_error(
            result, "reaction-types.toml", "Bad_Key")

    def test_a_value_that_is_not_a_table_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (an entry that is not a table)."""
        result = self.run_on_valid_md(write_reaction_types(
            'reduction = "Reduction"\n'))
        self.assert_configuration_error(
            result, "reaction-types.toml", "reduction")

    def test_a_label_that_is_empty_is_a_configuration_error(self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (a label that is not a non-empty string)."""
        for label in ('""', '" "', "5"):
            with self.subTest(label=label):
                result = self.run_on_valid_md(edit_reaction_types(
                    replace_text('label = "Reduction"',
                                 f"label = {label}")))
                self.assert_configuration_error(
                    result, "reaction-types.toml", "reduction", "label")

    def test_a_label_de_that_is_not_a_string_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (an empty or non-string label_de)."""
        for label_de in ('""', "5", "true"):
            with self.subTest(label_de=label_de):
                result = self.run_on_valid_md(edit_reaction_types(
                    replace_text('label = "Reduction"',
                                 f'label = "Reduction"\nlabel_de = '
                                 f"{label_de}")))
                self.assert_configuration_error(
                    result, "reaction-types.toml", "reduction", "label_de")

    def test_a_vocabulary_without_a_value_is_a_configuration_error(
            self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (no value)."""
        for content in ("", "# Nothing here yet.\n"):
            with self.subTest(content=content):
                result = self.run_on_valid_md(write_reaction_types(content))
                self.assert_configuration_error(
                    result, "reaction-types.toml")

    def test_a_broken_vocabulary_stops_a_run_without_procedures(
            self) -> None:
        """Requirement: Vocabulary file errors are configuration errors
        (the file is read whatever the content roots hold)."""
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "content"
            empty.mkdir()
            result = settings_variant_run(
                write_reaction_types("[reduction\n"), roots=[empty])
        self.assert_configuration_error(result, "reaction-types.toml")


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
