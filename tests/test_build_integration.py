"""Integration tests of build, validate, serve, pdf and the hook
(site-build, build-script, sample-procedures, collection).

Each runs tools/orgsyndb from a temporary application copy on a temporary
copy of the test collection, which has no Org sources. Tests skip, naming
the missing tool or cache, unless Hugo and the cached Pagefind binary
exist; the pdf tests also need WeasyPrint. The tests whose subject is the
export of Org sources copy the demo collection instead, and also skip
unless Emacs, git and the pinned ox-hugo bootstrap exist.
"""

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import unittest
import urllib.request
from pathlib import Path

import pipeline_support as ps
import support
from pipeline_support import (FIXTURES, Sandbox, front_matter, make_sandbox,
                              scan_page, snapshot)

BASELINE = FIXTURES / "baseline" / "OSDB-0100-baseline.md"
MISSING_TITLE = (FIXTURES / "invalid" / "missing-title"
                 / "OSDB-0101-missing-title.md")
PROBLEM_LINE = re.compile(r"^.+?:[^:\s]+: (error|warning): ")
SEEDS = ["OSDB-0001-salicylic-acid", "OSDB-0002-aspirin"]
# The locale of the shipped site/hugo.toml.
LOCALE = "de"


class BuildTestCase(unittest.TestCase):
    """A fresh copy of ``COLLECTION`` for each test."""

    COLLECTION = ps.TEST_COLLECTION

    @classmethod
    def setUpClass(cls) -> None:
        ps.require_builder()

    def setUp(self) -> None:
        self.sandbox: Sandbox = make_sandbox(self, collection=self.COLLECTION)

    def build(self, *args: str, **kwargs):
        return self.sandbox.build(*args, **kwargs)

    def assert_ok(self, result) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def public(self, *parts: str) -> Path:
        return self.sandbox.root / "public" / Path(*parts)

    def content_files(self) -> list[Path]:
        """The procedure content files of build/export/ and
        md/procedures/ that a build in the shipped locale, de, publishes:
        one per ID."""
        return [item.path for item in ps.read_content(self.sandbox, LOCALE)]

    def add_baseline(self, *extra_lines: str, date: str | None = None) -> Path:
        text = BASELINE.read_text(encoding="utf-8")
        text = apply(text, *[support.insert_line(ln) for ln in extra_lines])
        if date is not None:
            text = apply(text, support.replace_line("date", f"date = {date}"),
                         support.replace_line("lastmod", f"lastmod = {date}"))
        target = self.sandbox.md_dir() / BASELINE.name
        target.write_text(text, encoding="utf-8")
        return target


class DemoBuildTestCase(BuildTestCase):
    """A copy of the demo collection, whose Org sources are exported."""

    COLLECTION = ps.DEMO

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        ps.require_exporter()


def apply(text: str, *edits) -> str:
    return support.apply_edits(text, edits)


def problem_lines(stdout: str) -> list[str]:
    return [ln for ln in stdout.splitlines() if PROBLEM_LINE.match(ln)]


class OrgAndMarkdownSectionTests(DemoBuildTestCase):
    def test_org_and_markdown_sourced_pages_are_published(self) -> None:
        """Scenario: Org-sourced and Markdown-sourced pages."""
        self.assert_ok(self.build("build"))
        self.assertTrue(self.public("procedures", "osdb-0001",
                                    "index.html").is_file())
        self.assertTrue(self.public("procedures", "osdb-0002",
                                    "index.html").is_file())
        slugs = {front_matter(p.read_text(encoding="utf-8"))["slug"]
                 for p in self.content_files()}
        published = {p.name for p in self.public("procedures").iterdir()
                     if p.is_dir()}
        self.assertEqual(published, slugs)


class MergedSectionTests(BuildTestCase):
    def test_future_dated_procedure_is_published_indexed_and_printed(
            self) -> None:
        """Scenario: Future-dated procedure is published, indexed and
        printed."""
        ps.require_tool("weasyprint")
        self.add_baseline(date="2099-01-01T10:00:00+01:00")
        self.assert_ok(self.build("pdf"))
        self.assertTrue(self.public("procedures", "osdb-0100",
                                    "index.html").is_file())
        entry = json.loads(self.public("pagefind", "pagefind-entry.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(entry["languages"][LOCALE]["page_count"],
                         len(self.content_files()))
        self.assertTrue((self.sandbox.root / "pdf"
                         / "OSDB-0100-baseline.pdf").is_file())

    def test_expired_procedure_is_still_published(self) -> None:
        """Scenario: Expired procedure is still published."""
        self.add_baseline("expiryDate = 2026-02-01T10:00:00+01:00")
        result = self.build("build")
        self.assert_ok(result)
        self.assertTrue(any(
            "expiryDate: warning:" in ln and "unknown field" in ln
            for ln in result.stdout.splitlines()), result.stdout)
        self.assertTrue(self.public("procedures", "osdb-0100",
                                    "index.html").is_file())

    def test_stray_file_and_section_index_are_not_published(self) -> None:
        """Scenario: Stray file and section index are not published."""
        md = self.sandbox.md_dir()
        (md / "notes.txt").write_text("notes\n", encoding="utf-8")
        (md / "_index.md").write_text('+++\ntitle = "Hijack"\n+++\n',
                                      encoding="utf-8")
        self.assert_ok(self.build("build"))
        self.assertFalse(self.public("procedures", "notes.txt").exists())
        section = self.public("procedures", "index.html")
        text = section.read_text(encoding="utf-8") if section.exists() else ""
        self.assertNotIn("Hijack", text)


class LayoutContractTests(BuildTestCase):
    def test_one_indexed_body_per_procedure_page(self) -> None:
        """Scenario: One indexed body per procedure page."""
        self.assert_ok(self.build("build"))
        slugs = [front_matter(p.read_text(encoding="utf-8"))["slug"]
                 for p in self.content_files()]
        self.assertGreaterEqual(len(slugs), 2)
        procedure_pages = {self.public("procedures", slug, "index.html")
                           for slug in slugs}
        for page in sorted(self.public().rglob("*.html")):
            scan = scan_page(page.read_text(encoding="utf-8"))
            with self.subTest(page=str(page.relative_to(self.public()))):
                if page in procedure_pages:
                    self.assertEqual(len(scan.bodies), 1)
                    self.assertTrue({"Summary", "Zusammenfassung"}
                                    & set(scan.bodies[0].headings),
                                    scan.bodies[0].headings)
                else:
                    self.assertEqual(scan.bodies, [])

    def test_title_and_id_are_shown_outside_the_indexed_body(self) -> None:
        """Scenario: Title and ID shown."""
        self.assert_ok(self.build("build"))
        source = self.sandbox.md_dir() / "OSDB-0002-aspirin.de.md"
        title = front_matter(source.read_text(encoding="utf-8"))["title"]
        page = self.public("procedures", "osdb-0002", "index.html")
        outside = scan_page(page.read_text(encoding="utf-8")).outside_text
        self.assertIn(title, outside)
        self.assertIn("OSDB-0002", outside)


class NoRemoteFetchTests(BuildTestCase):
    def test_seed_build_fetches_nothing_remote(self) -> None:
        """Scenario: Seed build fetches nothing remote."""
        self.assert_ok(self.build("build"))
        found = []
        for path in sorted(self.public().rglob("*")):
            if path.suffix == ".html":
                for hit in ps.html_remote_fetches(
                        path.read_text(encoding="utf-8")):
                    found.append(f"{path.name}: {hit}")
            elif path.suffix == ".css":
                for hit in ps.css_remote_fetches(
                        path.read_text(encoding="utf-8")):
                    found.append(f"{path.name}: {hit}")
        self.assertEqual(found, [])


class SearchIndexTests(BuildTestCase):
    def test_bundle_location_and_page_count(self) -> None:
        """Scenario: Bundle location and page count."""
        self.assert_ok(self.build("build"))
        for name in ("pagefind.js", "pagefind-ui.js", "pagefind-ui.css"):
            self.assertTrue(self.public("pagefind", name).is_file(), name)
        entry = json.loads(self.public("pagefind", "pagefind-entry.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(entry["version"], "1.5.2")
        self.assertEqual(set(entry["languages"]), {LOCALE})
        self.assertEqual(entry["languages"][LOCALE]["page_count"],
                         len(self.content_files()))


class BuildSubcommandTests(BuildTestCase):
    def test_validation_error_stops_the_build_before_hugo(self) -> None:
        """Scenario: Validation error stops the build before Hugo."""
        self.assert_ok(self.build("build"))
        before = snapshot(self.public())
        shutil.copy2(MISSING_TITLE, self.sandbox.md_dir())
        result = self.build("build")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(snapshot(self.public()), before)


class SecondBuildTests(DemoBuildTestCase):
    def test_second_build_without_changes_keeps_the_export(self) -> None:
        """Scenario: Second build without changes."""
        self.assert_ok(self.build("build"))
        first = snapshot(self.sandbox.export_dir())
        self.assertNotEqual(first, {})
        self.assert_ok(self.build("build"))
        self.assertEqual(snapshot(self.sandbox.export_dir()), first)


class ValidateSubcommandTests(BuildTestCase):
    def test_seeds_validate(self) -> None:
        """Scenario: Seeds validate."""
        result = self.build("validate")
        self.assert_ok(result)
        self.assertEqual(problem_lines(result.stdout), [])

    def test_invalid_markdown_procedure_is_reported(self) -> None:
        """Scenario: Invalid Markdown procedure."""
        shutil.copy2(MISSING_TITLE, self.sandbox.md_dir())
        result = self.build("validate")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(any(
            ln.startswith("md/procedures/OSDB-0101-missing-title.md:"
                          "title: error:")
            for ln in result.stdout.splitlines()), result.stdout)


class ShippedTreeValidationTests(DemoBuildTestCase):
    def test_shipped_tree_validates_without_any_problem_line(self) -> None:
        """Scenario: Clean validation of the shipped tree."""
        result = self.build("validate")
        self.assert_ok(result)
        self.assertEqual(problem_lines(result.stdout), [])
        self.assertTrue(
            list(self.sandbox.root.glob("org/procedures/OSDB-*.org"))
            or list(self.sandbox.root.glob("md/procedures/OSDB-*.md")),
            "no shipped procedures to validate")


class ServeTests(BuildTestCase):
    def tearDown(self) -> None:
        process = getattr(self, "process", None)
        if process is not None and process.poll() is None:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    break
                try:
                    process.wait(timeout=10)
                    break
                except subprocess.TimeoutExpired:
                    continue
        super().tearDown()

    def test_site_and_search_bundle_are_served(self) -> None:
        """Scenario: Site and search bundle are served."""
        script = self.sandbox.app / "tools" / "orgsyndb"
        self.assertTrue(script.is_file(), "tools/orgsyndb does not exist")
        port = ps.free_port()
        self.process = subprocess.Popen(
            [str(script), "-C", str(self.sandbox.root), "serve", "--port",
             str(port)],
            cwd=self.sandbox.work, env=self.sandbox.env(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            start_new_session=True)
        lines: queue.Queue[str] = queue.Queue()

        def pump() -> None:
            for line in self.process.stdout:
                lines.put(line)

        threading.Thread(target=pump, daemon=True).start()
        expected = f"serving http://127.0.0.1:{port}/ (Ctrl-C to stop)"
        seen = []
        while True:
            try:
                line = lines.get(timeout=600).rstrip("\n")
            except queue.Empty:
                self.fail("no serving line:\n" + "\n".join(seen))
            seen.append(line)
            if line == expected:
                break
            if self.process.poll() is not None and lines.empty():
                self.fail("serve exited early:\n" + "\n".join(seen))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for path in ("/", "/procedures/osdb-0001/", "/pagefind/pagefind.js",
                     "/pagefind/pagefind-entry.json"):
            with self.subTest(path=path):
                with opener.open(f"http://127.0.0.1:{port}{path}",
                                 timeout=30) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(
                        response.headers.get("Cache-Control"), "no-cache")


class PdfTests(BuildTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        ps.require_tool("weasyprint")

    def test_one_pdf_per_procedure_and_no_stale_files(self) -> None:
        """Scenario: One PDF per procedure, no stale files."""
        pdf = self.sandbox.root / "pdf"
        pdf.mkdir()
        (pdf / "OSDB-0999-stale.pdf").write_bytes(b"%PDF-stale\n")
        result = self.build("pdf")
        self.assert_ok(result)
        stems = [p.stem for p in self.content_files()]
        for seed in SEEDS:
            self.assertIn(f"{seed}.{LOCALE}", stems)
        self.assertEqual(sorted(p.name for p in pdf.iterdir()),
                         sorted(f"{stem}.pdf" for stem in stems))
        for path in pdf.iterdir():
            self.assertTrue(path.read_bytes().startswith(b"%PDF-"),
                            path.name)
        self.assertNotIn("pkg_resources", result.stdout + result.stderr)

    def test_remote_stylesheet_fails_the_job(self) -> None:
        """Scenario: Remote stylesheet fails the job."""
        layout = self.sandbox.app / "site" / "layouts" / "baseof.html"
        self.assertTrue(layout.is_file(), "site/layouts/baseof.html missing")
        text = layout.read_text(encoding="utf-8")
        self.assertIn("<head>", text)
        layout.write_text(text.replace(
            "<head>", '<head><link rel="stylesheet" '
            'href="https://cdn.example.invalid/x.css">', 1),
            encoding="utf-8")
        result = self.build("pdf")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertRegex(result.stderr, r"OSDB-000[12]-[a-z-]+(\.de)?\.pdf")


class HookTests(BuildTestCase):
    def test_hook_refuses_an_invalid_commit(self) -> None:
        """Scenario: Hook refuses an invalid commit."""
        sandbox = self.sandbox
        hook = sandbox.app / "tools" / "hooks" / "pre-commit"
        self.assertTrue(hook.is_file(), "tools/hooks/pre-commit is missing")
        for args in (("init", "-q"),
                     ("config", "core.hooksPath", hook.parent)):
            self.assertEqual(sandbox.git(*args).returncode, 0)
        target = shutil.copy2(MISSING_TITLE, sandbox.md_dir())
        relative = Path(target).relative_to(sandbox.root)
        self.assertEqual(sandbox.git("add", "--", relative).returncode, 0)
        result = sandbox.git("commit", "-m", "add invalid procedure")
        self.assertNotEqual(result.returncode, 0,
                            result.stdout + result.stderr)
        head = sandbox.git("rev-parse", "--verify", "-q", "HEAD")
        if head.returncode == 0:
            listing = sandbox.git("ls-tree", "-r", "--name-only", "HEAD")
            self.assertNotIn(str(relative), listing.stdout.splitlines())

    def test_hook_through_a_symlink_accepts_a_valid_commit(self) -> None:
        """Scenario: Hook through a symlink accepts a valid commit."""
        sandbox = self.sandbox
        hook = sandbox.app / "tools" / "hooks" / "pre-commit"
        self.assertEqual(sandbox.git("init", "-q").returncode, 0)
        link = sandbox.root / ".git" / "hooks" / "pre-commit"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(hook)
        self.assertEqual(sandbox.git("add", "--", ".").returncode, 0)
        result = sandbox.git("commit", "-q", "-m", "add the demo")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("validated", result.stderr)

    def test_hook_validates_a_collection_in_a_subdirectory(self) -> None:
        """Scenario: Hook validates a collection in a subdirectory."""
        sandbox = self.sandbox
        top = sandbox.root.parent
        hook = sandbox.app / "tools" / "hooks" / "pre-commit"

        def git(*args: str | Path) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", *ps.GIT_QUIET, *map(str, args)],
                                  cwd=top, env=sandbox.env(),
                                  capture_output=True, text=True,
                                  timeout=900)

        for args in (("init", "-q"),
                     ("config", "core.hooksPath", hook.parent),
                     ("add", "--", sandbox.root.name)):
            done = git(*args)
            self.assertEqual(done.returncode, 0, done.stderr)
        target = shutil.copy2(MISSING_TITLE, sandbox.md_dir())
        relative = Path(target).relative_to(top)
        self.assertEqual(git("add", "--", relative).returncode, 0)
        result = git("commit", "-m", "add invalid procedure")
        self.assertNotEqual(result.returncode, 0,
                            result.stdout + result.stderr)
        self.assertIn("missing-title", result.stdout + result.stderr)
        self.assertNotEqual(git("rev-parse", "--verify", "-q",
                                "HEAD").returncode, 0)


class CollectionBuildTests(BuildTestCase):
    def test_the_applications_site_directory_is_untouched(self) -> None:
        """Scenario: The application's site directory is untouched."""
        site = self.sandbox.app / "site"
        before = snapshot(site)
        self.assert_ok(self.build("build"))
        self.assertEqual(snapshot(site), before)
        self.assertFalse((site / ".hugo_build.lock").exists())
        self.assertFalse((site / "resources").exists())
        self.assertTrue(self.public("index.html").is_file())

    def test_collection_is_found_from_a_subdirectory(self) -> None:
        """Scenario: Found from a subdirectory."""
        result = self.sandbox.program(
            "validate", cwd=self.sandbox.md_dir())
        self.assert_ok(result)
        self.assertTrue(self.sandbox.export_dir().is_dir())

    def test_structure_images_come_from_the_collection(self) -> None:
        """Scenario: The application's site directory is untouched
        (static files are the collection's)."""
        self.assert_ok(self.build("build"))
        for svg in sorted((self.sandbox.root / "static" / "structures")
                          .glob("*.svg")):
            with self.subTest(svg=svg.name):
                self.assertEqual(self.public("structures", svg.name)
                                 .read_bytes(), svg.read_bytes())

    def test_collection_path_with_a_comma_builds(self) -> None:
        """Scenario: Overlay parses to the contract (a comma in the path)."""
        moved = self.sandbox.root.with_name("collection, copy")
        self.sandbox.root.rename(moved)
        self.sandbox.root = moved
        self.assert_ok(self.build("build"))
        self.assertTrue(self.public("procedures", "osdb-0001",
                                    "index.html").is_file())
