"""tools/orgsyndb without Emacs or Hugo: usage, conventions, tool checks,
validate arguments, clean and check-deps (build-script), and the
collection rules that need no build (collection).

A missing tools/orgsyndb fails them, because it is a deliverable.
"""

import ast
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from pipeline_support import (BOOTSTRAP_HINT, DEMO, GIT_QUIET, HOOK,
                              ORGSYNDB, PIPELINE, REPO, TOOLS, Run,
                              make_path, make_sandbox, pipeline_function,
                              require_pagefind, require_tool, run_script,
                              snapshot)

SUBCOMMANDS = ["export", "validate", "build", "serve", "pdf", "new", "init",
               "clean", "check-deps", "help"]


class ProgramTestCase(unittest.TestCase):
    def temp_dir(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix="orgsyndb program "))
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def run_real(self, *args: str | Path, cwd: Path | None = None,
                 env: dict[str, str] | None = None) -> Run:
        """Run the real application's tools/orgsyndb."""
        return run_script(ORGSYNDB, args, cwd=cwd or self.temp_dir(),
                          env=env or dict(os.environ))


class UsageTests(ProgramTestCase):
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
        for form in ("help", "-h", "--help"):
            result = self.run_real(form)
            with self.subTest(form=form):
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in [*SUBCOMMANDS, "-C"]:
                    self.assertIn(name, result.stdout)

    def test_program_is_invoked_through_a_symlink(self) -> None:
        """Scenario: Invoked through a symlink."""
        self.assertTrue(ORGSYNDB.is_file(), "tools/orgsyndb does not exist")
        directory = self.temp_dir()
        link = directory / "link to orgsyndb"
        link.symlink_to(ORGSYNDB)
        result = run_script(link, ["help"], cwd=directory,
                            env=dict(os.environ))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_subcommand_option_is_a_usage_error(self) -> None:
        """Scenario: Unknown subcommand (an unknown option)."""
        sandbox = make_sandbox(self)
        result = sandbox.build("clean", "--frobnicate")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("--frobnicate", result.stderr)
        self.assertIn("usage", result.stderr.lower())

    def test_port_out_of_range_is_a_usage_error(self) -> None:
        """Scenario: Port out of range."""
        sandbox = make_sandbox(self)
        for port in ("70000", "0", "eighty"):
            result = sandbox.build("serve", "--port", port)
            with self.subTest(port=port):
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse((sandbox.root / "build").exists())


class SourceTests(unittest.TestCase):
    def test_program_compiles_and_hook_parses(self) -> None:
        """Scenario: Syntax and formatting."""
        for script in (ORGSYNDB, HOOK):
            self.assertTrue(script.is_file(),
                            f"{script.relative_to(REPO)} does not exist")
            self.assertTrue(os.access(script, os.X_OK),
                            f"{script.relative_to(REPO)} is not executable")
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(ORGSYNDB), cfile=str(Path(tmp) / "x.pyc"),
                               doraise=True)
        done = subprocess.run(["sh", "-n", str(HOOK)], capture_output=True,
                              text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(HOOK.read_text().splitlines()[0], "#!/bin/sh")

    def test_only_standard_library_imports(self) -> None:
        """Scenario: Only standard-library imports."""
        tree = ast.parse(ORGSYNDB.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        extra = names - set(sys.stdlib_module_names) - {"pipeline",
                                                        "validate"}
        self.assertEqual(extra, set())
        self.assertTrue(ORGSYNDB.read_text().startswith(
            "#!/usr/bin/env python3\n"))

    def test_python_does_not_read_org(self) -> None:
        """Scenario: No Org reading in Python."""
        for script in (PIPELINE, TOOLS / "validate.py", ORGSYNDB):
            text = script.read_text(encoding="utf-8")
            for needle in ("--org-root", "export-plan", "lint_org",
                           "cross_check", "export_instants"):
                with self.subTest(script=script.name, needle=needle):
                    self.assertNotIn(needle, text)

    def test_no_fish_is_left(self) -> None:
        """Scenario: No fish."""
        found = []
        for path in sorted(TOOLS.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            first = path.read_bytes().split(b"\n", 1)[0]
            if path.suffix == ".fish" or (first.startswith(b"#!")
                                          and b"fish" in first):
                found.append(str(path.relative_to(REPO)))
        self.assertEqual(found, [])


class HookWithoutCollectionTests(ProgramTestCase):
    def test_hook_without_a_collection_lets_the_commit_through(self) -> None:
        """Scenario: Hook without a collection lets the commit through."""
        directory = self.temp_dir()

        def git(*args: str | Path) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", *GIT_QUIET, *map(str, args)],
                                  cwd=directory, capture_output=True,
                                  text=True, timeout=120)

        self.assertEqual(git("init", "-q").returncode, 0)
        self.assertEqual(
            git("config", "core.hooksPath", HOOK.parent).returncode, 0)
        (directory / "notes.txt").write_text("notes\n", encoding="utf-8")
        self.assertEqual(git("add", "notes.txt").returncode, 0)
        result = git("commit", "-q", "-m", "add notes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no OrgSynDB collection", result.stderr)


class OrgSourceDetectionTests(unittest.TestCase):
    def test_org_sources_are_decided_by_entry_names(self) -> None:
        """Scenario: Org sources by entry names."""
        has_org_sources = pipeline_function("has_org_sources")
        base = Path(tempfile.mkdtemp(prefix="orgsyndb sources "))
        self.addCleanup(shutil.rmtree, base, True)
        cases = {"empty": None, "dotfile": ".gitkeep",
                 "stray file": "notes.txt", "subdirectory": "nested/",
                 "source": "OSDB-0001-a.org"}
        found = {"absent": has_org_sources(str(base / "absent"))}
        for case, entry in cases.items():
            root = base / case
            root.mkdir()
            if entry is not None and entry.endswith("/"):
                (root / entry).mkdir()
            elif entry is not None:
                (root / entry).write_text("x\n", encoding="utf-8")
            found[case] = has_org_sources(str(root))
        self.assertEqual(found, {"absent": False, "empty": False,
                                 "dotfile": False, "stray file": True,
                                 "subdirectory": True, "source": True})


class MissingToolTests(ProgramTestCase):
    def repo_and_path(self, tools: tuple[str, ...],
                      stubs: tuple[str, ...] = (), **kwargs):
        sandbox = make_sandbox(self, **kwargs)
        return sandbox, make_path(self, tools, stubs)

    def assert_stopped(self, result: Run, sandbox, path, tool: str):
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f"{tool} not found; install it with your "
                      "system's package manager", result.stderr)
        self.assertFalse((sandbox.root / "build").exists())
        self.assertEqual(path.sudo_calls(), [])

    def test_hugo_missing_stops_build_before_its_first_step(self) -> None:
        """Scenario: Hugo missing."""
        sandbox, path = self.repo_and_path(("python3",))
        env = sandbox.env(PATH=str(path.directory))
        result = sandbox.build("build", env=env)
        self.assert_stopped(result, sandbox, path, "hugo")

    def test_git_missing_stops_export_although_ox_hugo_is_installed(
            self) -> None:
        """Scenario: git missing although ox-hugo is installed."""
        elpa = REPO / ".emacs-batch" / "elpa"
        if not (elpa / "ox-hugo").is_dir():
            self.skipTest(BOOTSTRAP_HINT)
        sandbox, path = self.repo_and_path(("python3",), ("emacs",),
                                           collection=DEMO)
        env = sandbox.env(PATH=str(path.directory))
        result = sandbox.build("export", env=env)
        self.assert_stopped(result, sandbox, path, "git")

    def test_emacs_missing_with_org_sources_stops_build(self) -> None:
        """Scenario: Emacs missing with Org sources."""
        sandbox, path = self.repo_and_path(("python3", "git", "hugo"),
                                           collection=DEMO)
        env = sandbox.env(PATH=str(path.directory))
        result = sandbox.build("build", env=env)
        self.assert_stopped(result, sandbox, path, "emacs")

    def test_markdown_only_collection_builds_without_emacs_and_git(
            self) -> None:
        """Scenario: Markdown-only collection builds without Emacs and
        git."""
        require_tool("hugo")
        require_pagefind()
        sandbox, path = self.repo_and_path(("python3", "hugo"))
        env = sandbox.env(PATH=str(path.directory))
        result = sandbox.build("build", env=env)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        public = sandbox.root / "public"
        self.assertTrue((public / "index.html").is_file())
        self.assertTrue(
            (public / "procedures" / "osdb-0002" / "index.html").is_file())

    def test_collection_error_comes_before_missing_tools(self) -> None:
        """Scenario: Collection error comes before missing tools."""
        path = make_path(self, ("python3",))
        env = dict(os.environ, PATH=str(path.directory))
        result = self.run_real("-C", self.temp_dir(), "build", env=env)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("orgsyndb.toml", result.stderr)
        self.assertNotIn("not found", result.stderr)
        self.assertEqual(path.sudo_calls(), [])


class ValidateArgumentTests(ProgramTestCase):
    def test_arguments_are_refused(self) -> None:
        """Scenario: Arguments are refused."""
        sandbox = make_sandbox(self)
        for form in (["-C", str(sandbox.root)],
                     [f"--collection={sandbox.root}"]):
            result = self.run_real(*form, "validate", "md/procedures")
            with self.subTest(form=form[0]):
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("validate.py", result.stderr)
                self.assertFalse((sandbox.root / "build").exists())


class CleanTests(ProgramTestCase):
    def test_clean_keeps_sources_and_caches_and_clean_all_removes_them(
            self) -> None:
        """Scenarios: Clean keeps sources and caches; Clean all, twice."""
        sandbox = make_sandbox(self, collection=DEMO, link_caches=False)
        root, app = sandbox.root, sandbox.app
        generated = [root / "build/export", root / "public/pagefind",
                     root / "pdf", app / ".emacs-batch/elpa",
                     app / ".tools/pagefind-1.5.2"]
        for path in generated:
            path.mkdir(parents=True, exist_ok=True)
            (path / "marker").write_text("x\n")
        kept = {path: snapshot(path) for path in (
            root / "org", root / "md", root / "static", app / "site",
            app / "templates")}
        marker = (root / "orgsyndb.toml").read_bytes()

        result = sandbox.build("clean")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("build", "public", "pdf"):
            self.assertFalse((root / name).exists(), name)
        self.assertTrue((app / ".emacs-batch" / "elpa" / "marker").is_file())
        self.assertTrue((app / ".tools" / "pagefind-1.5.2").is_dir())
        for path, files in kept.items():
            self.assertEqual(snapshot(path), files, str(path))
        self.assertEqual((root / "orgsyndb.toml").read_bytes(), marker)

        for attempt in (1, 2):
            result = sandbox.build("clean", "--all")
            self.assertEqual(result.returncode, 0,
                             f"attempt {attempt}: {result.stderr}")
        self.assertFalse((app / ".emacs-batch").exists())
        self.assertFalse((app / ".tools").exists())


class CheckDepsTests(ProgramTestCase):
    def run_check(self, tools: tuple[str, ...], stubs: tuple[str, ...] = ()):
        sandbox = make_sandbox(self)
        path = make_path(self, tools, stubs)
        env = sandbox.env(PATH=str(path.directory))
        return sandbox.program("check-deps", env=env), path

    def test_two_missing_tools_are_named_in_one_line(self) -> None:
        """Scenario: Two tools missing."""
        result, path = self.run_check(("python3",), ("emacs", "git"))
        lines = result.stdout.splitlines()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(any(ln.startswith("missing hugo") for ln in lines))
        self.assertTrue(
            any(ln.startswith("missing weasyprint") for ln in lines))
        self.assertEqual(lines[-1],
                         "install with your package manager: hugo weasyprint")
        self.assertEqual(path.sudo_calls(), [])

    def test_nothing_missing_exits_zero_without_an_install_line(self) -> None:
        """Scenario: Nothing missing."""
        result, path = self.run_check(("python3",), ("hugo", "weasyprint"))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        for line in lines:
            self.assertFalse(line.startswith(("missing ", "install ")), line)
        for tool in ("python3", "hugo", "weasyprint"):
            self.assertIn(f"ok      {tool}", lines)
        for tool in ("emacs", "git"):
            self.assertIn(f"optional {tool} (not installed; only for Org "
                          "procedures)", lines)
        self.assertEqual(path.sudo_calls(), [])


# --- collection --------------------------------------------------------------

class MarkerTests(ProgramTestCase):
    def collection_with(self, text: str) -> Path:
        directory = self.temp_dir() / "a collection"
        directory.mkdir()
        (directory / "orgsyndb.toml").write_text(text, encoding="utf-8")
        return directory

    def test_unknown_format_is_refused(self) -> None:
        """Scenario: Unknown format."""
        directory = self.collection_with("format = 2\n")
        result = self.run_real("-C", directory, "validate")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("orgsyndb.toml", result.stderr)
        self.assertIn("format", result.stderr)
        self.assertFalse((directory / "build").exists())

    def test_unknown_key_is_refused(self) -> None:
        """Scenario: Unknown key."""
        directory = self.collection_with('format = 1\ntitle = "X"\n')
        result = self.run_real("-C", directory, "validate")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("title", result.stderr)

    def test_malformed_markers_are_refused(self) -> None:
        """Scenario: Unknown format (missing, mistyped, invalid TOML)."""
        for text in ("", 'format = "1"\n', "format = 1.0\n", "format = \n",
                     "format = true\n"):
            directory = self.collection_with(text)
            result = self.run_real("-C", directory, "build")
            with self.subTest(text=text):
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("orgsyndb.toml", result.stderr)
                self.assertEqual(sorted(p.name for p in directory.iterdir()),
                                 ["orgsyndb.toml"])


class ChoosingTheCollectionTests(ProgramTestCase):
    def test_no_collection_found(self) -> None:
        """Scenario: No collection found."""
        directory = self.temp_dir()
        result = self.run_real("build", cwd=directory)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("-C", result.stderr)
        self.assertIn("init", result.stderr)
        self.assertEqual(list(directory.iterdir()), [])

    def test_option_names_a_directory_without_a_marker(self) -> None:
        """Scenario: Option names a directory without a marker."""
        directory = self.temp_dir()
        for form in (["-C", str(directory)], [f"--collection={directory}"],
                     ["--collection", str(directory)]):
            result = self.run_real(*form, "build")
            with self.subTest(form=form[0]):
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("orgsyndb.toml", result.stderr)
                self.assertEqual(list(directory.iterdir()), [])

    def test_option_without_a_directory_is_a_usage_error(self) -> None:
        """Scenario: Unknown subcommand (a malformed option)."""
        for args in (["-C"], ["--collection="], ["-x", "help"]):
            result = self.run_real(*args)
            with self.subTest(args=args):
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("usage", result.stderr.lower())

    def test_commands_without_a_collection_never_look_for_one(self) -> None:
        """Scenario: No collection found (commands that need none)."""
        directory = self.temp_dir()
        for args in (["help"], ["check-deps"]):
            result = self.run_real("-C", directory / "absent", *args,
                                   cwd=directory)
            with self.subTest(args=args):
                self.assertIn(result.returncode, (0, 1), result.stderr)
                self.assertNotIn("collection", result.stderr)


class InitTests(ProgramTestCase):
    def test_new_collection_takes_a_procedure(self) -> None:
        """Scenario: New collection takes a procedure."""
        target = self.temp_dir() / "parent dir" / "new collection"
        result = self.run_real("init", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), target.resolve())
        self.assertEqual(tomllib.loads(
            (target / "orgsyndb.toml").read_text(encoding="utf-8")),
            {"format": 1})
        self.assertEqual((target / ".gitignore").read_text(),
                         "/build/\n/public/\n/pdf/\n")
        for name in ("org/procedures", "md/procedures", "static/structures"):
            self.assertTrue((target / name).is_dir(), name)
        result = self.run_real("-C", target, "new", "--md", "Ethyl acetate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "md/procedures/OSDB-0001-ethyl-acetate.md")
        stub = target / "md" / "procedures" / "OSDB-0001-ethyl-acetate.md"
        self.assertTrue(stub.is_file())

    def test_existing_collection_is_refused(self) -> None:
        """Scenario: Existing collection is refused."""
        target = self.temp_dir() / "collection"
        self.assertEqual(self.run_real("init", target).returncode, 0)
        before = snapshot(target)
        result = self.run_real("init", target)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("orgsyndb.toml", result.stderr)
        self.assertEqual(snapshot(target), before)

    def test_missing_directory_argument_is_a_usage_error(self) -> None:
        """Scenario: Existing collection is refused (no DIR)."""
        result = self.run_real("init")
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_existing_gitignore_gets_only_the_missing_lines(self) -> None:
        """Scenario: Existing .gitignore is kept."""
        target = self.temp_dir()
        (target / ".gitignore").write_text("*.swp\n/public/")
        self.assertEqual(self.run_real("init", target).returncode, 0)
        self.assertEqual((target / ".gitignore").read_text(),
                         "*.swp\n/public/\n/build/\n/pdf/\n")

    def test_demo_collection_matches_init(self) -> None:
        """Scenario: The demo collection matches init."""
        target = self.temp_dir() / "fresh"
        self.assertEqual(self.run_real("init", target).returncode, 0)
        self.assertEqual((DEMO / ".gitignore").read_text(),
                         (target / ".gitignore").read_text())
        for path in (DEMO / "orgsyndb.toml", target / "orgsyndb.toml"):
            self.assertEqual(tomllib.loads(path.read_text()), {"format": 1})
