"""tools/build.fish without Emacs or Hugo: usage, conventions, tool
checks, validate pass-through, clean and check-deps (build-script).

These are the "fish tests": they skip only when fish is missing. A
missing tools/build.fish fails them, because it is this change's
deliverable.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import support
from pipeline_support import (BOOTSTRAP_HINT, BUILD_FISH, REPO, Run,
                              make_path, make_sandbox, run_script,
                              snapshot)

SUBCOMMANDS = ["export", "validate", "build", "serve", "pdf", "new",
               "clean", "check-deps", "help"]
VALIDATE_ARGS = ["--vocabulary", "tests/fixtures/reaction_types.toml",
                 "--static-dir", "tests/fixtures/static"]


class FishTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("fish") is None:
            raise unittest.SkipTest("fish not found")

    def temp_dir(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix="orgsyndb fish "))
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def run_real(self, *args: str | Path, cwd: Path | None = None,
                 env: dict[str, str] | None = None) -> Run:
        """Run the real repository's tools/build.fish."""
        return run_script(BUILD_FISH, args, cwd=cwd or self.temp_dir(),
                          env=env or dict(os.environ))


class UsageTests(FishTestCase):
    def test_unknown_subcommand_is_a_usage_error(self) -> None:
        """Scenario: Unknown subcommand."""
        result = self.run_real("frobnicate")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("frobnicate", result.stderr)
        self.assertIn("usage", result.stderr.lower())

    def test_no_subcommand_is_a_usage_error(self) -> None:
        """Scenario: No subcommand."""
        result = self.run_real()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("usage", result.stderr.lower())

    def test_help_names_every_subcommand(self) -> None:
        """Scenario: Help."""
        result = self.run_real("help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in SUBCOMMANDS:
            with self.subTest(subcommand=name):
                self.assertIn(name, result.stdout)

    def test_script_is_invoked_through_a_symlink(self) -> None:
        """Scenario: Invoked through a symlink."""
        self.assertTrue(BUILD_FISH.is_file(),
                        "tools/build.fish does not exist")
        directory = self.temp_dir()
        link = directory / "link to build"
        link.symlink_to(BUILD_FISH)
        result = run_script(link, ["help"], cwd=directory,
                            env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stderr)


class SyntaxTests(FishTestCase):
    def test_scripts_pass_no_execute_and_indent_check(self) -> None:
        """Scenario: Syntax and formatting."""
        indent = shutil.which("fish_indent")
        if indent is None:
            self.skipTest("fish_indent not found")
        for script in (BUILD_FISH, REPO / "tools" / "hooks" / "pre-commit"):
            self.assertTrue(script.is_file(),
                            f"{script.relative_to(REPO)} does not exist")
            for command in (["fish", "--no-execute", str(script)],
                            [indent, "--check", str(script)]):
                with self.subTest(script=script.name, command=command[0]):
                    done = subprocess.run(command, capture_output=True,
                                          text=True, timeout=60)
                    self.assertEqual(done.returncode, 0, done.stderr)


class MissingToolTests(FishTestCase):
    def repo_and_path(self, tools: tuple[str, ...], **kwargs):
        sandbox = make_sandbox(self, **kwargs)
        return sandbox, make_path(self, tools)

    def assert_stopped(self, result: Run, sandbox, path, package: str):
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"sudo dnf install {package}", result.stderr)
        self.assertFalse((sandbox.root / "build").exists())
        self.assertEqual(path.sudo_calls(), [])

    def test_hugo_missing_stops_build_before_its_first_step(self) -> None:
        """Scenario: Hugo missing."""
        sandbox, path = self.repo_and_path(
            ("fish", "python3", "emacs", "git"))
        env = sandbox.env(PATH=str(path.directory))
        result = sandbox.build("build", env=env)
        self.assert_stopped(result, sandbox, path, "hugo")

    def test_git_missing_stops_export_although_ox_hugo_is_installed(
            self) -> None:
        """Scenario: git missing although ox-hugo is installed."""
        elpa = REPO / ".emacs-batch" / "elpa"
        if not (elpa / "ox-hugo").is_dir():
            self.skipTest(BOOTSTRAP_HINT)
        sandbox, path = self.repo_and_path(("fish", "python3", "emacs"))
        env = sandbox.env(PATH=str(path.directory))
        result = sandbox.build("export", env=env)
        self.assert_stopped(result, sandbox, path, "git")

    def test_validate_with_arguments_needs_only_python(self) -> None:
        """Scenario: validate with arguments needs only Python."""
        path = make_path(self, ("fish", "python3"))
        env = dict(os.environ, PATH=str(path.directory))
        result = self.run_real(
            "validate", *VALIDATE_ARGS, "tests/fixtures/valid/md",
            "tests/fixtures/valid/export",
            cwd=REPO, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("not found", result.stderr)


class ValidatePassThroughTests(FishTestCase):
    def test_arguments_reach_the_validator_unchanged(self) -> None:
        """Scenario: Arguments pass through to the validator."""
        args = [*VALIDATE_ARGS, "tests/fixtures/invalid/missing-title"]
        build = REPO / "build"
        before = snapshot(build) if build.exists() else None
        result = self.run_real("validate", *args, cwd=REPO)
        direct = support.run_validator(args, cwd=REPO)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, direct.stdout)
        self.assertNotEqual(result.stdout, "")
        after = snapshot(build) if build.exists() else None
        self.assertEqual(after, before)


class CleanTests(FishTestCase):
    def test_clean_keeps_sources_and_caches_and_clean_all_removes_them(
            self) -> None:
        """Scenarios: Clean keeps sources and caches; Clean all, twice."""
        sandbox = make_sandbox(self, link_caches=False)
        root = sandbox.root
        generated = ["build/export", "public/pagefind", "pdf",
                     "site/resources/_gen", ".emacs-batch/elpa",
                     ".tools/pagefind-1.5.2"]
        for name in generated:
            (root / name).mkdir(parents=True, exist_ok=True)
            (root / name / "marker").write_text("x\n")
        (root / "site" / ".hugo_build.lock").write_text("")
        kept = {n: snapshot(root / n) for n in ("org", "md", "templates")}
        hugo_toml = root / "site" / "hugo.toml"
        config = hugo_toml.read_bytes() if hugo_toml.exists() else None

        result = sandbox.build("clean")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("build", "public", "pdf", "site/.hugo_build.lock",
                     "site/resources"):
            self.assertFalse((root / name).exists(), name)
        self.assertTrue((root / ".emacs-batch" / "elpa" / "marker").is_file())
        self.assertTrue((root / ".tools" / "pagefind-1.5.2").is_dir())
        for name, files in kept.items():
            self.assertEqual(snapshot(root / name), files, name)
        if config is not None:
            self.assertEqual(hugo_toml.read_bytes(), config)

        for attempt in (1, 2):
            result = sandbox.build("clean", "--all")
            self.assertEqual(result.returncode, 0,
                             f"attempt {attempt}: {result.stderr}")
        self.assertFalse((root / ".emacs-batch").exists())
        self.assertFalse((root / ".tools").exists())


class CheckDepsTests(FishTestCase):
    def run_check(self, tools: tuple[str, ...], stubs: tuple[str, ...] = ()):
        sandbox = make_sandbox(self)
        path = make_path(self, tools, stubs)
        env = sandbox.env(PATH=str(path.directory))
        return sandbox.build("check-deps", env=env), path

    def test_two_missing_tools_are_named_in_one_dnf_line(self) -> None:
        """Scenario: Two tools missing."""
        result, path = self.run_check(("fish", "python3", "emacs", "git"))
        lines = result.stdout.splitlines()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(any(ln.startswith("missing hugo") for ln in lines))
        self.assertTrue(
            any(ln.startswith("missing weasyprint") for ln in lines))
        self.assertEqual(lines[-1], "sudo dnf install hugo weasyprint")
        self.assertEqual(path.sudo_calls(), [])

    def test_nothing_missing_exits_zero_without_a_dnf_line(self) -> None:
        """Scenario: Nothing missing."""
        result, path = self.run_check(("fish", "python3"),
                                      ("emacs", "git", "hugo", "weasyprint"))
        self.assertEqual(result.returncode, 0, result.stderr)
        for line in result.stdout.splitlines():
            self.assertFalse(line.startswith(("missing ", "sudo ")), line)
        self.assertEqual(path.sudo_calls(), [])
