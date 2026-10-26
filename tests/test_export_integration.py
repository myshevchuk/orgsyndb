"""Integration tests of ``tools/orgsyndb export`` (org-export).

Each runs the program from a temporary application copy on a temporary
copy of the demo collection, and skips, naming the missing tool or cache,
unless Emacs, git and the pinned ox-hugo bootstrap are present.
"""

import datetime as dt
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pipeline_support as ps
from pipeline_support import (DEMO, FIXTURES, OX_HUGO_PIN, REPO, TOMELR_PIN,
                              Sandbox, body_of, front_matter, make_path,
                              make_sandbox, read_only_dir, snapshot)

PRODUCT = {"name": "Propyl acetate", "formula": "C5H10O2", "mw": 102.13,
           "smiles": "CCCOC(C)=O"}
NOTES_WARNING = ("org/procedures/notes.txt:file_name: warning: "
                 "not a procedure file; ignored")
PROBLEM_LINE = re.compile(r"^\S.*: (?:error|warning): ")


def report_lines(stdout: str) -> list[str]:
    """The lines of stdout that are not step lines."""
    return [line for line in stdout.splitlines()
            if not line.startswith("==> ")]


def check_out_ox_hugo_parent(sandbox: Sandbox) -> str:
    """Check out the parent of the pin in the copied ox-hugo checkout.

    Returns the parent's hash.
    """
    checkout = sandbox.app / ".emacs-batch" / "elpa" / "ox-hugo"
    parent = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD^"],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(checkout), "-c", "advice.detachedHead=false",
         "checkout", "-q", parent], check=True, capture_output=True,
        timeout=60)
    return parent


class ExportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ps.require_exporter()

    def sandbox(self, **kwargs) -> Sandbox:
        return make_sandbox(self, collection=DEMO, **kwargs)

    def export(self, sandbox: Sandbox, **kwargs):
        return sandbox.build("export", **kwargs)

    def exported(self, sandbox: Sandbox, stem: str) -> str:
        path = sandbox.export_dir() / f"{stem}.md"
        self.assertTrue(path.is_file(), f"{path.name} was not exported")
        return path.read_text(encoding="utf-8")

    def only_sources(self, sandbox: Sandbox, *names: str) -> None:
        """Make the given fixtures the only Org sources."""
        sandbox.clear_org()
        for name in names:
            sandbox.put_fixture(name)


class IsolationTests(ExportTestCase):
    def test_owners_directories_and_inherited_tmpdir_stay_untouched(
            self) -> None:
        """Scenario: Owner's directories and the inherited TMPDIR stay
        untouched."""
        sandbox = self.sandbox()
        self.only_sources(sandbox, "OSDB-0902-literal-text.org")
        (sandbox.home / ".config" / "emacs").mkdir(parents=True)
        tmpdir = sandbox.home.parent / "readonly tmp"
        tmpdir.mkdir()
        with read_only_dir(tmpdir):
            result = self.export(
                sandbox, env=sandbox.env(TMPDIR=str(tmpdir)))
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            created = sorted(str(p.relative_to(sandbox.home))
                             for p in sandbox.home.rglob("*"))
            self.assertEqual(created, [".config", ".config/emacs"])
            self.assertEqual(
                list((sandbox.home / ".config" / "emacs").iterdir()), [])
            self.assertEqual(list(tmpdir.iterdir()), [])


class PinTests(ExportTestCase):
    def head(self, sandbox: Sandbox, package: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(sandbox.app / ".emacs-batch" / "elpa"
                              / package), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def test_installed_checkouts_are_at_the_pins(self) -> None:
        """Scenario: Installed checkouts are at the pins."""
        sandbox = self.sandbox()
        self.assertEqual(self.export(sandbox).returncode, 0)
        self.assertEqual(self.head(sandbox, "ox-hugo"), OX_HUGO_PIN)
        self.assertEqual(self.head(sandbox, "tomelr"), TOMELR_PIN)

    def test_a_checkout_at_another_commit_stops_the_export(self) -> None:
        """Scenario: A checkout at another commit stops the export."""
        sandbox = self.sandbox(copy_emacs=True)
        first = self.export(sandbox)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        before = snapshot(sandbox.export_dir())
        parent = check_out_ox_hugo_parent(sandbox)
        result = self.export(sandbox)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        for needle in ("ox-hugo", OX_HUGO_PIN, parent, "clean --all"):
            self.assertIn(needle, output)
        self.assertEqual(snapshot(sandbox.export_dir()), before)


class OldEmacsTests(ExportTestCase):
    def test_an_old_emacs_is_refused(self) -> None:
        """Scenario: An old Emacs is refused."""
        sandbox = self.sandbox()
        first = self.export(sandbox)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        before = snapshot(sandbox.export_dir())
        bin_dir = Path(tempfile.mkdtemp(prefix="orgsyndb old emacs "))
        self.addCleanup(shutil.rmtree, bin_dir, True)
        def quoted(value: str) -> str:
            return "'" + value.replace("'", "'\\''") + "'"

        # The fake restores PATH, since a launcher such as Fedora's
        # re-executes Emacs by the bare name emacs.
        inherited = sandbox.env()["PATH"]
        pretend = ("(setq emacs-version \"28.2\" emacs-major-version 28 "
                   "emacs-minor-version 2)")
        fake = bin_dir / "emacs"
        fake.write_text("#!/bin/sh\n"
                        f"PATH={quoted(inherited)}; export PATH\n"
                        "a=\"$1\" b=\"$2\"; shift 2\n"
                        f"exec {quoted(shutil.which('emacs'))} \"$a\" "
                        f"\"$b\" --eval '{pretend}' \"$@\"\n")
        fake.chmod(0o755)
        path = f"{bin_dir}:{inherited}"
        result = self.export(sandbox, env=sandbox.env(PATH=path))
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("Emacs 29.1 or later is required; this is Emacs 28.2",
                      output)
        self.assertEqual(snapshot(sandbox.export_dir()), before)


class NoPackageElTests(unittest.TestCase):
    def test_no_package_el(self) -> None:
        """Scenario: No package.el."""
        for name in ("export.el", "osdb-org.el"):
            path = REPO / "tools" / name
            self.assertTrue(path.is_file(), f"tools/{name} does not exist")
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=name):
                self.assertNotIn("package-vc", text)
                self.assertNotIn("(require 'package)", text)


class ExportWithoutOrgTests(unittest.TestCase):
    def test_export_with_neither_emacs_nor_git(self) -> None:
        """Scenario: Export with neither Emacs nor git."""
        sandbox = make_sandbox(self, collection=DEMO)
        sandbox.clear_org()
        path = make_path(self, ("python3",))
        result = sandbox.build("export",
                               env=sandbox.env(PATH=str(path.directory)))
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        self.assertIn("==> export: no Org sources; Emacs is not needed",
                      result.stdout)
        self.assertTrue(sandbox.export_dir().is_dir())
        self.assertEqual(list(sandbox.export_dir().iterdir()), [])


class ExportedFrontMatterTests(ExportTestCase):
    def test_seed_export_validates_cleanly(self) -> None:
        """Scenario: Seed export validates cleanly."""
        sandbox = self.sandbox()
        for seed in ("org/procedures/OSDB-0001-salicylic-acid.org",
                     "md/procedures/OSDB-0002-aspirin.md"):
            self.assertTrue((sandbox.root / seed).is_file(),
                            f"{seed} does not exist")
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        checked = sandbox.validator("build/export", "md/procedures")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout, "")

    def test_table_written_first_in_the_source_is_emitted_last(self) -> None:
        """Scenario: Table written first in the source is emitted last."""
        sandbox = self.sandbox()
        self.only_sources(sandbox, "OSDB-0901-table-first.org")
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = front_matter(self.exported(sandbox, "OSDB-0901-table-first"))
        for key in ("scale", "yield_percent", "hazards", "precursors"):
            self.assertIn(key, data)
        self.assertEqual(data["scale"], "25 mmol")
        self.assertEqual(data["precursors"], ["OSDB-0001"])
        self.assertEqual(data["product"], PRODUCT)

    def test_ai_model_is_mapped_and_author_is_absent(self) -> None:
        """Scenario: AI model mapping."""
        sandbox = self.sandbox()
        self.only_sources(sandbox, "OSDB-0901-table-first.org",
                          "OSDB-0902-literal-text.org")
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        modelled = front_matter(
            self.exported(sandbox, "OSDB-0901-table-first"))
        human = front_matter(
            self.exported(sandbox, "OSDB-0902-literal-text"))
        self.assertEqual(modelled.get("ai_model"), "example-model-1")
        self.assertNotIn("ai_model", human)
        self.assertNotIn("author", modelled)
        self.assertNotIn("author", human)

    def test_seconds_survive(self) -> None:
        """Scenario: Seconds survive."""
        sandbox = self.sandbox()
        self.only_sources(sandbox, "OSDB-0901-table-first.org")
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = front_matter(self.exported(sandbox, "OSDB-0901-table-first"))
        self.assertEqual(
            data["lastmod"],
            dt.datetime(2026, 10, 19, 21, 0, 7,
                        tzinfo=dt.timezone(dt.timedelta(hours=2))))


class BodyOptionTests(ExportTestCase):
    def body(self, sandbox: Sandbox, **kwargs) -> str:
        self.only_sources(sandbox, "OSDB-0902-literal-text.org")
        result = self.export(sandbox, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return body_of(self.exported(sandbox, "OSDB-0902-literal-text"))

    def test_dollar_signs_and_latex_stay_literal(self) -> None:
        """Scenario: Dollar signs and LaTeX stay literal."""
        body = self.body(self.sandbox())
        for text in ("$5", "$10", "$x$", "\\\\(y^2\\\\)"):
            self.assertIn(text, body)
        self.assertNotIn("\\\\(x\\\\)", body)

    def test_only_braced_subscripts_are_interpreted(self) -> None:
        """Scenario: Only braced subscripts are interpreted."""
        body = self.body(self.sandbox())
        for text in ("H<sub>2</sub>O", "CO_2", "yield_percent"):
            self.assertIn(text, body)

    def test_source_blocks_are_not_evaluated(self) -> None:
        """Scenario: Source blocks are not evaluated."""
        sandbox = self.sandbox()
        marker = sandbox.work / "marker file"
        self.body(sandbox, env=sandbox.env(OSDB_TEST_MARKER=str(marker)))
        self.assertFalse(marker.exists())


class FreshExportDirectoryTests(ExportTestCase):
    def test_deleted_source_leaves_no_orphan(self) -> None:
        """Scenario: Deleted source leaves no orphan."""
        sandbox = self.sandbox()
        self.only_sources(sandbox, "OSDB-0901-table-first.org",
                          "OSDB-0902-literal-text.org")
        self.assertEqual(self.export(sandbox).returncode, 0)
        self.assertEqual(len(snapshot(sandbox.export_dir())), 2)
        (sandbox.root / "org" / "procedures"
         / "OSDB-0902-literal-text.org").unlink()
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(snapshot(sandbox.export_dir())),
                         ["OSDB-0901-table-first.md"])

    def test_failed_export_keeps_the_previous_directory(self) -> None:
        """Scenario: Failed export keeps the previous directory."""
        sandbox = self.sandbox()
        source = sandbox.put_fixture("OSDB-0901-table-first.org")
        self.assertEqual(self.export(sandbox).returncode, 0)
        before = snapshot(sandbox.export_dir())
        source.write_text(source.read_text(encoding="utf-8").replace(
            "[2026-10-19 Mon 17:42:05]", "[2026-10-19 Mon 17:42]"),
            encoding="utf-8")
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(snapshot(sandbox.export_dir()), before)

    def test_leftovers_from_a_crashed_run_are_recovered(self) -> None:
        """Scenario: Leftovers from a crashed run."""
        sandbox = self.sandbox()
        self.only_sources(sandbox, "OSDB-0901-table-first.org",
                          "OSDB-0902-literal-text.org")
        build = sandbox.root / "build"
        (build / ".export-previous").mkdir(parents=True)
        (build / ".export-previous" / "OSDB-0999-earlier.md").write_text(
            "earlier\n")
        (build / ".export-staging").mkdir()
        (build / ".export-staging" / "partial.md").write_text("half\n")
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(snapshot(build / "export")),
                         ["OSDB-0901-table-first.md",
                          "OSDB-0902-literal-text.md"])
        self.assertFalse((build / ".export-previous").exists())
        self.assertFalse((build / ".export-staging").exists())

    def test_no_sources_leaves_an_empty_export_directory(self) -> None:
        """Scenario: No Org sources."""
        sandbox = self.sandbox()
        sandbox.clear_org()
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(sandbox.export_dir().is_dir())
        self.assertEqual(list(sandbox.export_dir().iterdir()), [])


class IdempotenceTests(ExportTestCase):
    def test_re_export_without_changes_is_byte_identical(self) -> None:
        """Scenario: Re-export without changes."""
        sandbox = self.sandbox()
        self.assertEqual(self.export(sandbox).returncode, 0)
        first = snapshot(sandbox.export_dir())
        self.assertNotEqual(first, {})
        self.assertEqual(self.export(sandbox).returncode, 0)
        self.assertEqual(snapshot(sandbox.export_dir()), first)

    def test_re_export_of_a_named_paragraph_is_byte_identical(self) -> None:
        """Scenario: Re-export of a named paragraph."""
        sandbox = self.sandbox()
        sandbox.put_fixture("OSDB-0903-named-paragraph.org")
        self.assertEqual(self.export(sandbox).returncode, 0)
        name = "OSDB-0903-named-paragraph.md"
        first = (sandbox.export_dir() / name).read_bytes()
        self.assertRegex(first.decode("utf-8"), r'id="org[0-9a-f]{7}"')
        self.assertEqual(self.export(sandbox).returncode, 0)
        self.assertEqual((sandbox.export_dir() / name).read_bytes(), first)

    def test_other_sources_do_not_change_a_files_anchors(self) -> None:
        """Scenario: Other sources do not change a file's anchors."""
        sandbox = self.sandbox()
        seeds = DEMO / "org" / "procedures"
        self.assertTrue(any(seeds.glob("OSDB-*.org")),
                        "org/procedures/ holds no seed")
        self.only_sources(sandbox, "OSDB-0903-named-paragraph.org")
        self.assertEqual(self.export(sandbox).returncode, 0)
        name = "OSDB-0903-named-paragraph.md"
        alone = (sandbox.export_dir() / name).read_bytes()
        sandbox.put_fixture("OSDB-0902-literal-text.org")
        for seed in seeds.glob("OSDB-*.org"):
            shutil.copy2(seed, sandbox.root / "org" / "procedures")
        self.assertEqual(self.export(sandbox).returncode, 0)
        self.assertEqual((sandbox.export_dir() / name).read_bytes(), alone)


class OrgErrorTests(unittest.TestCase):
    """Org problems stop the program before any package is installed."""

    @classmethod
    def setUpClass(cls) -> None:
        for tool in ("emacs", "git"):
            ps.require_tool(tool)

    def sandbox_with(self, fixture: str) -> Sandbox:
        """A test-collection copy holding the Org fixture, no ox-hugo."""
        sandbox = make_sandbox(self, link_caches=False)
        target = sandbox.root / "org" / "procedures"
        target.mkdir(parents=True)
        shutil.copy2(FIXTURES / fixture, target)
        return sandbox

    def test_org_errors_stop_validate_before_any_package_is_installed(
            self) -> None:
        """Scenario: Org errors stop validate before any package is
        installed."""
        sandbox = self.sandbox_with(
            "org-invalid/missing-seconds/org/OSDB-0204-missing-seconds.org")
        result = sandbox.build("validate")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(report_lines(result.stdout), [
            "org/procedures/OSDB-0204-missing-seconds.org:#+CREATED: error: "
            '"[2026-10-19 Mon 17:42]" must have the form '
            "[YYYY-MM-DD Day hh:mm:ss]"])
        self.assertIn(
            "the Org sources have errors; build/export/ is unchanged",
            result.stderr)
        self.assertFalse((sandbox.app / ".emacs-batch").exists())
        self.assertFalse(sandbox.export_dir().exists())

    def test_conflicting_front_matter_stops_the_export(self) -> None:
        """Scenario: Conflicting front matter stops the export."""
        sandbox = self.sandbox_with(
            "org-invalid/custom-ai-model/org/"
            "OSDB-0216-custom-ai-model.org")
        result = sandbox.build("export")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(report_lines(result.stdout), [
            "org/procedures/OSDB-0216-custom-ai-model.org:"
            "#+HUGO_CUSTOM_FRONT_MATTER: error: must not set :ai_model; "
            "the export writes it from #+AI_MODEL"])
        self.assertIn("the Org sources have errors", result.stderr)
        self.assertFalse(sandbox.export_dir().exists())


class ExportElTests(unittest.TestCase):
    """tools/export.el run directly."""

    @classmethod
    def setUpClass(cls) -> None:
        ps.require_tool("emacs")

    def run_export_el(self, org_root: Path, staging: Path):
        base = org_root.parent
        return subprocess.run(
            ["emacs", "-Q", "--batch", "-l", str(REPO / "tools/export.el"),
             str(org_root), str(staging)],
            cwd=base, capture_output=True, text=True, timeout=300)

    def workspace(self) -> Path:
        base = Path(tempfile.mkdtemp(prefix="orgsyndb export el "))
        self.addCleanup(shutil.rmtree, base, True)
        return base

    def test_emacs_stdout_holds_only_problem_lines(self) -> None:
        """Scenario: Emacs's stdout holds only problem lines."""
        base = self.workspace()
        root = base / "org root"
        root.mkdir()
        staging = base / "staging dir"
        staging.mkdir()
        shutil.copy2(FIXTURES / "org-invalid/wrong-weekday/org"
                     / "OSDB-0206-wrong-weekday.org", root)
        (root / "notes.txt").write_text("notes\n", encoding="utf-8")
        done = self.run_export_el(root, staging)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(
            done.stdout,
            f"{root}/OSDB-0206-wrong-weekday.org:#+CREATED: error: "
            'weekday "Tue" does not match 2026-10-19 (Mon)\n'
            f"{root}/notes.txt:file_name: warning: not a procedure file; "
            "ignored\n")
        self.assertEqual(list(staging.iterdir()), [])

    def test_org_root_that_is_not_a_directory_is_refused(self) -> None:
        """Scenario: ORG_ROOT that is not a directory."""
        base = self.workspace()
        staging = base / "staging dir"
        staging.mkdir()
        done = self.run_export_el(base / "absent", staging)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        output = done.stdout + done.stderr
        self.assertIn("export.el: error:", output)
        self.assertIn("is not a directory", output)


class OrgRootTests(unittest.TestCase):
    def test_org_root_that_is_not_a_directory_keeps_the_export(self) -> None:
        """Scenario: Org root that is not a directory."""
        sandbox = make_sandbox(self)
        first = sandbox.build("export")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        (sandbox.export_dir() / "keep.md").write_bytes(b"keep\n")
        (sandbox.root / "org").mkdir()
        (sandbox.root / "org" / "procedures").write_text(
            "not a directory\n", encoding="utf-8")
        path = make_path(self, ("python3",))
        result = sandbox.build("export",
                               env=sandbox.env(PATH=str(path.directory)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("orgsyndb: error: org/procedures is not a directory",
                      result.stderr)
        self.assertEqual(snapshot(sandbox.export_dir()),
                         {"keep.md": b"keep\n"})


class OrgReportTests(ExportTestCase):
    def with_notes(self, **kwargs) -> Sandbox:
        """A demo-collection copy with a stray file among the sources."""
        sandbox = self.sandbox(**kwargs)
        (sandbox.root / "org" / "procedures" / "notes.txt").write_text(
            "notes\n", encoding="utf-8")
        return sandbox

    def test_warnings_alone_do_not_stop_the_export(self) -> None:
        """Scenario: Warnings alone do not stop the export."""
        sandbox = self.with_notes()
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report_lines(result.stdout), [NOTES_WARNING])
        stems = sorted(path.stem for path in
                       (sandbox.root / "org" / "procedures").glob("*.org"))
        self.assertEqual(
            sorted(path.name for path in sandbox.export_dir().iterdir()),
            sorted(f"{stem}.md" for stem in stems))

    def test_warnings_followed_by_an_export_failure(self) -> None:
        """Scenario: Warnings followed by an export failure."""
        sandbox = self.with_notes(copy_emacs=True)
        first = self.export(sandbox)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        before = snapshot(sandbox.export_dir())
        check_out_ox_hugo_parent(sandbox)
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(report_lines(result.stdout), [NOTES_WARNING])
        self.assertIn("clean --all", result.stderr)
        self.assertIn("export failed; Emacs output is in build/export.log",
                      result.stderr)
        self.assertNotIn("the Org sources have errors", result.stderr)
        self.assertEqual(snapshot(sandbox.export_dir()), before)

    def test_stubs_from_new_pass_the_org_checks(self) -> None:
        """Scenario: Stubs from new pass the Org checks."""
        sandbox = self.sandbox()
        stems = []
        for args in (["Test product"], ["--lang", "de", "Prüfprodukt"]):
            made = sandbox.build("new", *args)
            self.assertEqual(made.returncode, 0, made.stderr)
            stems.append(Path(made.stdout.strip()).stem)
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([line for line in result.stdout.splitlines()
                          if PROBLEM_LINE.match(line)], [])
        for stem in stems:
            self.exported(sandbox, stem)


class ExportedDateTests(ExportTestCase):
    def test_exported_dates_match_the_fixture_exports(self) -> None:
        """Scenario: Exported dates match the fixture exports."""
        sandbox = make_sandbox(self)
        target = sandbox.root / "org" / "procedures"
        target.mkdir(parents=True)
        stems = ("OSDB-0003-propyl-acetate", "OSDB-0004-ambiguous-hour")
        for stem in stems:
            shutil.copy2(FIXTURES / "valid" / "org" / f"{stem}.org", target)
        result = self.export(sandbox)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        exported = {}
        for stem in stems:
            got = front_matter(self.exported(sandbox, stem))
            want = front_matter((FIXTURES / "valid" / "export"
                                 / f"{stem}.md").read_text(encoding="utf-8"))
            with self.subTest(stem=stem):
                for key in ("date", "lastmod"):
                    self.assertEqual(got[key].isoformat(),
                                     want[key].isoformat())
                self.assertEqual("ai_model" in got, "ai_model" in want)
                self.assertEqual(got.get("ai_model"), want.get("ai_model"))
            exported[stem] = got
        ambiguous = exported["OSDB-0004-ambiguous-hour"]
        self.assertEqual(ambiguous["date"].isoformat(),
                         "2026-10-25T02:50:00+02:00")
        self.assertEqual(ambiguous["lastmod"].isoformat(),
                         "2026-10-25T02:10:00+01:00")
        self.assertEqual(ambiguous["ai_model"], "claude-sonnet-5-5")
