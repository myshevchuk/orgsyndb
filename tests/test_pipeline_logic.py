"""Pure behaviour of tools/pipeline.py: next-ID, slugs, timestamps, stubs,
PDF job naming and the helper module's shape (build-script)."""

import ast
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zoneinfo
from pathlib import Path

import support
from pipeline_support import (GIT_QUIET, PIPELINE, REPO, Run, front_matter,
                              pipeline, run_pipeline, snapshot)

NOW = "2026-10-19T17:42:05+02:00"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def make_repo(case: unittest.TestCase, trees: bool = False) -> Path:
    """A temporary repository holding templates/ and, optionally, empty
    org/procedures/ and md/procedures/. The path contains a space."""
    base = Path(tempfile.mkdtemp(prefix="orgsyndb new "))
    case.addCleanup(shutil.rmtree, base, True)
    root = base / "repo copy"
    root.mkdir()
    shutil.copytree(REPO / "templates", root / "templates")
    if trees:
        (root / "org" / "procedures").mkdir(parents=True)
        (root / "md" / "procedures").mkdir(parents=True)
    return root


def new(root: Path, *args: str, env: dict[str, str] | None = None) -> Run:
    """Run ``pipeline.py new --repo ROOT ARGS...`` in a neutral cwd."""
    with tempfile.TemporaryDirectory() as cwd:
        return run_pipeline(["new", "--repo", root, *args],
                            cwd=Path(cwd), env=env)


def files_of(root: Path) -> set[str]:
    return {p for p in snapshot(root) if not p.startswith(".git/")}


def created(root: Path, before: set[str]) -> list[str]:
    return sorted(files_of(root) - before)


def git(root: Path, *args: str | Path) -> None:
    subprocess.run(["git", *GIT_QUIET, "-C", str(root), *map(str, args)],
                   check=True, capture_output=True, timeout=60)


class NextIdTests(unittest.TestCase):
    def test_next_id_is_one_above_the_highest_across_trees(self) -> None:
        """Scenario: Next ID across trees, exports and history."""
        names = ["OSDB-0001-a.org", "OSDB-0002-b.md", "OSDB-0007-c.md",
                 "OSDB-0004-d.md", "notes.txt", "osdb-0011-lowercase.md"]
        self.assertEqual(pipeline().next_id(names), "OSDB-0012")

    def test_first_id_when_no_name_begins_with_an_id(self) -> None:
        """Scenario: First ID."""
        self.assertEqual(pipeline().next_id(["notes.txt", "_index.md"]),
                         "OSDB-0001")
        self.assertEqual(pipeline().next_id([]), "OSDB-0001")

    def test_exhausted_id_space_is_an_error(self) -> None:
        """Scenario: ID space exhausted."""
        with self.assertRaises(ValueError):
            pipeline().next_id(["OSDB-9999-last.md"])


@unittest.skipUnless(shutil.which("git"), "git not found")
class NewWithGitHistoryTests(unittest.TestCase):
    def committed_repo(self) -> Path:
        root = make_repo(self, trees=True)
        git(root, "init", "-q")
        (root / "md" / "procedures" / "OSDB-0012-old.md").write_text("x\n")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "add old procedure")
        return root

    def test_deleted_committed_procedure_is_not_reused(self) -> None:
        """Scenario: Deleted committed procedure is not reused."""
        root = self.committed_repo()
        (root / "md" / "procedures" / "OSDB-0012-old.md").unlink()
        git(root, "commit", "-q", "-a", "-m", "delete old procedure")
        before = files_of(root)
        result = new(root, "--md", "--now", NOW, "Test product")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(created(root, before),
                         ["md/procedures/OSDB-0013-test-product.md"])

    def test_shallow_clone_warns_that_history_is_incomplete(self) -> None:
        """Scenario: Shallow clone warns."""
        origin = self.committed_repo()
        (origin / "md" / "procedures" / "OSDB-0012-old.md").unlink()
        git(origin, "commit", "-q", "-a", "-m", "delete old procedure")
        clone = origin.parent / "shallow clone"
        git(origin.parent, "clone", "-q", "--depth", "1", origin.as_uri(),
            clone)
        before = files_of(clone)
        result = new(clone, "--md", "--now", NOW, "Test product")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(created(clone, before)), 1)
        self.assertIn("shallow", result.stderr)


class SlugTests(unittest.TestCase):
    def test_slugs_follow_titles(self) -> None:
        """Scenario: Slugs from titles."""
        cases = {
            "4-tert-Butylcyclohexanol": "4-tert-butylcyclohexanol",
            "(E)-Chalcone": "e-chalcone",
            "Salicylic acid": "salicylic-acid",
            "Ethyl  acetate!": "ethyl-acetate",
        }
        for title, slug in cases.items():
            with self.subTest(title=title):
                self.assertEqual(pipeline().slugify(title), slug)

    def test_long_title_is_cut_at_a_word_boundary(self) -> None:
        """Scenario: Long and empty titles (long title)."""
        title = ("tetrahydro-methyl-cyclohexyl-acetate-derivative-"
                 "synthesis-ab")
        self.assertEqual(len(title), 60)
        slug = pipeline().slugify(title)
        self.assertLessEqual(len(slug), 40)
        self.assertRegex(slug, SLUG_RE)
        self.assertTrue(title.startswith(slug), slug)
        self.assertEqual(title[len(slug)], "-", slug)

    def test_title_without_ascii_letters_or_digits_is_an_error(self) -> None:
        """Scenario: Long and empty titles (empty title)."""
        with self.assertRaises(ValueError):
            pipeline().slugify("αβγ")


class TimestampTests(unittest.TestCase):
    def test_org_timestamps_in_summer_and_winter(self) -> None:
        """Scenario: Org timestamps in summer and winter."""
        utc = dt.timezone.utc
        self.assertEqual(
            pipeline().org_timestamp(dt.datetime(2026, 10, 19, 15, 42, 5,
                                                 tzinfo=utc)),
            "[2026-10-19 Mon 17:42:05]")
        self.assertEqual(
            pipeline().org_timestamp(dt.datetime(2026, 1, 5, 8, 0, 0,
                                                 tzinfo=utc)),
            "[2026-01-05 Mon 09:00:00]")

    def test_rfc3339_names_the_berlin_offset(self) -> None:
        """Scenario: Summer time (formatting of the instant)."""
        berlin = zoneinfo.ZoneInfo("Europe/Berlin")
        summer = dt.datetime(2026, 10, 19, 17, 42, 5, tzinfo=berlin)
        winter = dt.datetime(2026, 1, 5, 9, 0, 0, tzinfo=berlin)
        utc = dt.datetime(2026, 1, 5, 8, 0, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(pipeline().rfc3339(summer),
                         "2026-10-19T17:42:05+02:00")
        self.assertEqual(pipeline().rfc3339(winter),
                         "2026-01-05T09:00:00+01:00")
        self.assertEqual(pipeline().rfc3339(utc),
                         "2026-01-05T09:00:00+01:00")

    def test_fall_back_hour_out_of_wall_clock_order(self) -> None:
        """Scenario: Fall-back hour out of wall-clock order (function)."""
        berlin = zoneinfo.ZoneInfo("Europe/Berlin")

        def instants(hour: int, minute: int) -> list[dt.datetime]:
            wall = dt.datetime(2026, 10, 25, hour, minute)
            return sorted(
                (wall.replace(tzinfo=berlin, fold=fold) for fold in (0, 1)),
                key=lambda m: m.astimezone(dt.timezone.utc))

        date, lastmod = pipeline().export_instants(instants(2, 50),
                                                   instants(2, 10))
        self.assertEqual(pipeline().rfc3339(date),
                         "2026-10-25T02:50:00+02:00")
        self.assertEqual(pipeline().rfc3339(lastmod),
                         "2026-10-25T02:10:00+01:00")


class StubTests(unittest.TestCase):
    def test_org_stub_is_filled_and_valid(self) -> None:
        """Scenario: Org stub."""
        root = make_repo(self, trees=True)
        result = new(root, "--now", NOW, "Salicylic acid")
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
        self.assertTrue(stub.is_file(), result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "org/procedures/OSDB-0001-salicylic-acid.org")
        text = stub.read_text(encoding="utf-8")
        for line in ("#+TITLE: Salicylic acid",
                     "#+CREATED: [2026-10-19 Mon 17:42:05]",
                     "#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]",
                     "#+AI_MODEL: none", "#+HUGO_SLUG: osdb-0001"):
            self.assertIn(line + "\n", text)
        self.assertNotIn("OSDB-0000", text)
        self.assertNotIn("osdb-0000", text)
        checked = support.run_validator(["--org-root", stub.parent])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout, "")

    def test_org_stub_weekday_ignores_the_locale(self) -> None:
        """Scenario: Weekday independent of the locale."""
        root = make_repo(self, trees=True)
        env = dict(os.environ, LC_ALL="de_DE.UTF-8", LC_TIME="de_DE.UTF-8")
        result = new(root, "--now", NOW, "Salicylic acid", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
        self.assertIn("#+CREATED: [2026-10-19 Mon 17:42:05]\n",
                      stub.read_text(encoding="utf-8"))

    def test_markdown_stub_with_model_and_quoted_title(self) -> None:
        """Scenario: Markdown stub with an AI model and a quoted title."""
        root = make_repo(self)
        title = 'Bob\'s "best" ester'
        result = new(root, "--md", "--ai-model", "example-model-1",
                     "--now", NOW, title)
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "md" / "procedures" / "OSDB-0001-bob-s-best-ester.md"
        self.assertTrue(stub.is_file(), result.stdout + result.stderr)
        data = front_matter(stub.read_text(encoding="utf-8"))
        self.assertEqual(data["title"], title)
        moment = dt.datetime.fromisoformat(NOW)
        self.assertEqual(data["date"], moment)
        self.assertEqual(data["lastmod"], moment)
        self.assertEqual(data["ai_model"], "example-model-1")
        self.assertEqual(data["id"], "OSDB-0001")
        checked = support.run_validator([stub.parent])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout, "")

    def test_human_authored_markdown_stub_has_no_ai_model(self) -> None:
        """Scenario: Human-authored Markdown stub."""
        root = make_repo(self)
        result = new(root, "--md", "--now", NOW, "Test product")
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "md" / "procedures" / "OSDB-0001-test-product.md"
        self.assertTrue(stub.is_file(), result.stdout + result.stderr)
        self.assertNotIn("ai_model",
                         front_matter(stub.read_text(encoding="utf-8")))

    def test_invalid_ai_model_is_a_usage_error_and_creates_nothing(
            self) -> None:
        """Scenario: Invalid AI model identifier."""
        root = make_repo(self)
        before = files_of(root)
        result = new(root, "--ai-model", "two words", "Test product")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("--ai-model", result.stderr)
        self.assertEqual(files_of(root), before)

    def test_template_filling_rejects_a_missing_anchor_line(self) -> None:
        """Scenario: Template filling (design D1: ValueError on a missing
        anchor line)."""
        text = (REPO / "templates" / "procedure.org").read_text(
            encoding="utf-8")
        broken = re.sub(r"^#\+TITLE:.*\n", "", text, flags=re.M)
        now = dt.datetime.fromisoformat(NOW)
        with self.assertRaises(ValueError):
            pipeline().fill_template(broken, "org", "OSDB-0001", "T", now,
                                     None)


class PdfJobTests(unittest.TestCase):
    def test_job_names_follow_the_content_file(self) -> None:
        """Scenario: Job naming."""
        with tempfile.TemporaryDirectory(prefix="pdf jobs ") as tmp:
            public, out = Path(tmp) / "public", Path(tmp) / "pdf"
            page = public / "procedures" / "osdb-0002" / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text("<html></html>")
            jobs = pipeline().pdf_jobs(
                [(Path("md/procedures/OSDB-0002-aspirin.md"),
                  {"slug": "osdb-0002"})], public, out)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(Path(jobs[0].html), page)
            self.assertEqual(Path(jobs[0].pdf), out / "OSDB-0002-aspirin.pdf")

    def test_missing_page_is_an_error_naming_the_path(self) -> None:
        """Scenario: Missing page."""
        with tempfile.TemporaryDirectory(prefix="pdf jobs ") as tmp:
            public, out = Path(tmp) / "public", Path(tmp) / "pdf"
            public.mkdir()
            with self.assertRaises(ValueError) as caught:
                pipeline().pdf_jobs(
                    [(Path("md/procedures/OSDB-0002-aspirin.md"),
                      {"slug": "osdb-0002"})], public, out)
            expected = public / "procedures" / "osdb-0002" / "index.html"
            self.assertIn(str(expected), str(caught.exception))


class HelperModuleTests(unittest.TestCase):
    def test_only_standard_library_imports(self) -> None:
        """Scenario: Only standard-library imports."""
        self.assertTrue(PIPELINE.is_file(),
                        "tools/pipeline.py does not exist")
        tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names.add((node.module or "").split(".")[0])
        self.assertTrue(names, "no imports found")
        self.assertEqual(names - set(sys.stdlib_module_names) - {"validate"},
                         set())

    def test_unknown_subcommand_is_a_usage_error(self) -> None:
        """Scenario: Unknown CLI subcommand."""
        result = run_pipeline(["frobnicate"])
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stderr.strip(), "")
