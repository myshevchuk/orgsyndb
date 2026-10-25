"""Integration tests of ``tools/orgsyndb export`` (org-export).

Each runs the program from a temporary application copy on a temporary
copy of the demo collection, and skips, naming the missing tool or cache,
unless Emacs, git and the pinned ox-hugo bootstrap are present.
"""

import datetime as dt
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pipeline_support as ps
from pipeline_support import (DEMO, OX_HUGO_PIN, REPO, TOMELR_PIN, Sandbox,
                              body_of, front_matter, make_path,
                              make_sandbox, read_only_dir, snapshot)

PRODUCT = {"name": "Propyl acetate", "formula": "C5H10O2", "mw": 102.13,
           "smiles": "CCCOC(C)=O"}


class ExportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ps.require_exporter()

    def sandbox(self, **kwargs) -> Sandbox:
        return make_sandbox(self, **kwargs)

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
        checkout = sandbox.app / ".emacs-batch" / "elpa" / "ox-hugo"
        parent = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD^"],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(checkout), "-c", "advice.detachedHead=false",
             "checkout", "-q", parent], check=True, capture_output=True,
            timeout=60)
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
        text = (REPO / "tools" / "export.el").read_text(encoding="utf-8")
        self.assertNotIn("package-vc", text)
        self.assertNotIn("(require 'package)", text)


class ExportWithoutOrgTests(unittest.TestCase):
    def test_export_with_neither_emacs_nor_git(self) -> None:
        """Scenario: Export with neither Emacs nor git."""
        sandbox = make_sandbox(self)
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
        checked = sandbox.validator("--org-root", "org/procedures",
                                    "build/export", "md/procedures")
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
