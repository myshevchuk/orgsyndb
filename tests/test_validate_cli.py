"""Command-line behaviour of tools/validate.py (procedure-validation)."""

import ast
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import support
from support import (BASELINE, FIXTURES, REGISTRY, SETTINGS, STATIC_DIR,
                     VALIDATOR, ValidatorTestCase, edit_registry,
                     edit_registry_text, fixture_run, load_snapshot,
                     registry_variant_run, run_validator, setting_terms,
                     substance, term, valid_set_run, variant_root,
                     write_snapshot)


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

    def test_vocabulary_and_compound_options_are_refused(self) -> None:
        """Scenario: Vocabulary and compound options are refused."""
        for option, value in (("--vocabulary", REGISTRY),
                              ("--compounds", FIXTURES)):
            with self.subTest(option=option):
                result = run_validator(
                    [option, value, FIXTURES / "valid" / "md"])
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(option, result.stderr)
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

    def test_registry_option_names_the_registry(self) -> None:
        """Requirement: Command-line interface (--registry)."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            write_snapshot(registry, {
                "format": 1,
                "vocabularies": {
                    "chemical-classes": [], "inventory-groups": [],
                    "projects": [],
                    "reaction-types": [term("esterification",
                                            "Esterification",
                                            tree=False)]},
                "substances": [substance("ethyl-acetate")],
                "accounts": [{"username": "a.example",
                              "name": "A. Example"}]})
            result = run_validator(
                ["--settings", SETTINGS, "--static-dir", STATIC_DIR,
                 "--registry", registry, BASELINE.parent])
        self.assert_clean(result)
        self.assertIn("validated 1 files: 0 errors, 0 warnings",
                      result.stderr)


class DefaultPathTests(ValidatorTestCase):
    def test_default_static_and_registry_are_the_working_directorys(
            self) -> None:
        """Scenario: Default static and registry directories are the
        working directory's."""
        with variant_root("OSDB-0100-baseline.md") as root:
            with tempfile.TemporaryDirectory() as cwd:
                collection = Path(cwd)
                structures = collection / "static" / "structures"
                structures.mkdir(parents=True)
                shutil.copy2(STATIC_DIR / "structures"
                             / "ethyl-acetate.svg", structures)
                (collection / "build").mkdir()
                shutil.copyfile(REGISTRY,
                                collection / "build" / "registry.json")
                result = run_validator([root], cwd=collection)
        self.assert_clean(result)

    def test_missing_registry_is_a_configuration_error(self) -> None:
        """Scenario: Missing registry."""
        result = fixture_run(
            "baseline", registry=FIXTURES / "no-such-registry.json")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("validate.py: error:", result.stderr)
        self.assertIn("no-such-registry.json", result.stderr)

    def test_a_working_directory_without_a_registry_is_refused(
            self) -> None:
        """Requirement: Default paths come from the working directory
        (a default registry file that does not exist)."""
        with tempfile.TemporaryDirectory() as cwd:
            self.assertEqual(list(Path(cwd).iterdir()), [])
            result = run_validator(
                ["--static-dir", STATIC_DIR, FIXTURES / "baseline"],
                cwd=Path(cwd))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("validate.py: error:", result.stderr)
        self.assertIn("registry.json", result.stderr)

    def test_default_settings_file_is_the_working_directorys(self) -> None:
        """Scenario: Default settings file is the working directory's."""
        settings = support.procedure_declaration(
            "notebook", "text", "Lab notebook", "required = true")
        with tempfile.TemporaryDirectory() as cwd:
            (Path(cwd) / "orgsyndb.toml").write_text(
                "format = 1\n" + settings, encoding="utf-8")
            result = run_validator(
                ["--registry", REGISTRY, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_one(result, "error", "notebook",
                        "required field missing")

    def test_the_settings_option_outranks_the_working_directory(
            self) -> None:
        """Requirement: Command-line interface (--settings)."""
        settings = support.procedure_declaration(
            "notebook", "text", "Lab notebook", "required = true")
        with tempfile.TemporaryDirectory() as cwd:
            (Path(cwd) / "orgsyndb.toml").write_text(
                "format = 1\n" + settings, encoding="utf-8")
            result = run_validator(
                ["--settings", SETTINGS, "--registry", REGISTRY,
                 "--static-dir", STATIC_DIR, FIXTURES / "baseline"],
                cwd=Path(cwd))
        self.assert_clean(result)

    def test_a_missing_default_settings_file_declares_no_field(
            self) -> None:
        """Requirement: Default paths come from the working directory (a
        settings file that does not exist, `--settings` omitted)."""
        with tempfile.TemporaryDirectory() as cwd:
            self.assertFalse((Path(cwd) / "orgsyndb.toml").exists())
            result = run_validator(
                ["--registry", REGISTRY, "--static-dir", STATIC_DIR,
                 FIXTURES / "baseline"], cwd=Path(cwd))
        self.assert_clean(result)

    def test_a_named_settings_file_that_does_not_exist_is_refused(
            self) -> None:
        """Scenario: A named settings file that does not exist."""
        result = fixture_run(
            "baseline",
            extra=["--settings", FIXTURES / "no-such-settings.toml"])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("no-such-settings.toml", result.stderr)


class RegistryErrorTests(ValidatorTestCase):
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

    def test_a_registry_that_is_not_json(self) -> None:
        """Scenario: Not JSON."""
        result = registry_variant_run(edit_registry_text(
            support.append_text("{")))
        self.assert_configuration_error(result, "registry.json")

    def test_a_registry_that_is_not_utf_8(self) -> None:
        """Requirement: Registry errors are configuration errors (cannot
        be read as UTF-8 JSON)."""
        def change(registry: Path) -> None:
            registry.write_bytes(b'{"format": 1, "x": "Caf\xe9"}')
        self.assert_configuration_error(
            registry_variant_run(change), "registry.json")

    def test_a_table_that_is_not_a_snapshot(self) -> None:
        """Scenario: Not a snapshot (through the validator)."""
        cases = {
            "format 2": lambda t: t.update(format=2),
            "format a string": lambda t: t.update(format="1"),
            "no format": lambda t: t.pop("format"),
            "substances a table": lambda t: t.update(substances={}),
            "a substance that is no table":
                lambda t: t.update(substances=["ethyl-acetate"]),
            "vocabularies a list": lambda t: t.update(vocabularies=[]),
            "a vocabulary that is no list":
                lambda t: t["vocabularies"].update(projects={}),
        }
        for name, step in cases.items():
            with self.subTest(case=name):
                result = registry_variant_run(edit_registry(step))
                self.assert_configuration_error(result, "registry.json")

    def test_a_file_holding_a_list_is_not_a_snapshot(self) -> None:
        """Requirement: Reading the registry (a table of the snapshot's
        keys)."""
        def change(registry: Path) -> None:
            registry.write_text(json.dumps(["format", 1]),
                                encoding="utf-8")
        self.assert_configuration_error(
            registry_variant_run(change), "registry.json")

    def test_a_registry_without_reaction_types_makes_them_unknown(
            self) -> None:
        """Scenario: No reaction types."""
        result = registry_variant_run(edit_registry(
            setting_terms("reaction-types")))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("validate.py: error:", result.stderr)
        self.assert_one(result, "error", "reaction_types",
                        "unknown reaction type")

    def test_the_digest_is_not_checked(self) -> None:
        """Requirement: Reading the registry (a table is a snapshot by
        its format and the shapes of its vocabularies and substances)."""
        def change(registry: Path) -> None:
            table = load_snapshot(registry)
            table["digest"] = "0" * 64
            registry.write_text(json.dumps(table), encoding="utf-8")
        self.assert_clean(registry_variant_run(change))


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
        self.assertIn("validated 1 files: 0 errors, 0 warnings",
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
