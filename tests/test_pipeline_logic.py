"""Pure behaviour of tools/pipeline.py: next-ID, slugs, timestamps, stubs,
PDF job naming and the helper module's shape (build-script)."""

import ast
import datetime as dt
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zoneinfo
from pathlib import Path

import field_support as fs
import support
from pipeline_support import (FIXTURES, GIT_QUIET, PIPELINE, REPO, Run,
                              TEST_COLLECTION, captured, front_matter,
                              pipeline, pipeline_function, snapshot)
from support import term

NOW = "2026-10-19T17:42:05+02:00"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def make_repo(case: unittest.TestCase, trees: bool = False,
              base: Path | None = None) -> Path:
    """A temporary collection holding orgsyndb.toml and, optionally, empty
    org/procedures/ and md/procedures/. The path contains a space; with
    ``base``, the collection is ``base/data``."""
    if base is None:
        base = Path(tempfile.mkdtemp(prefix="orgsyndb new "))
        case.addCleanup(shutil.rmtree, base, True)
        root = base / "collection copy"
    else:
        root = base / "data"
    root.mkdir()
    (root / "orgsyndb.toml").write_text("format = 1\n")
    if trees:
        (root / "org" / "procedures").mkdir(parents=True)
        (root / "md" / "procedures").mkdir(parents=True)
    return root


def new(root: Path, *words: str, md: bool = False,
        lang: str | None = None) -> Run:
    """Create a stub in ``root`` at ``NOW`` with ``new_procedure``.

    A UsageError gives exit status 2 with its message on stderr;
    otherwise stdout is the created path, as ``orgsyndb new`` prints it.
    """
    module = pipeline()
    try:
        relative, _, err = captured(
            module.new_procedure, root, words, md,
            dt.datetime.fromisoformat(NOW), lang)
    except module.UsageError as exc:
        return Run(2, "", str(exc))
    return Run(0, relative.as_posix() + "\n", err)


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
        result = new(root, "Test product", md=True)
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
        result = new(clone, "Test product", md=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(created(clone, before)), 1)
        self.assertIn("shallow", result.stderr)

    def test_collection_in_a_subdirectory_of_a_work_tree(self) -> None:
        """Scenario: Collection in a subdirectory of a work tree."""
        top = Path(tempfile.mkdtemp(prefix="orgsyndb work tree "))
        self.addCleanup(shutil.rmtree, top, True)
        root = make_repo(self, trees=True, base=top)
        git(top, "init", "-q")
        old = root / "md" / "procedures" / "OSDB-0012-old.md"
        old.write_text("x\n")
        git(top, "add", "-A")
        git(top, "commit", "-q", "-m", "add old procedure")
        old.unlink()
        git(top, "commit", "-q", "-a", "-m", "delete old procedure")
        before = files_of(top)
        result = new(root, "Test product", md=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(created(top, before),
                         ["data/md/procedures/OSDB-0013-test-product.md"])
        self.assertNotIn("warning", result.stderr)


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


class StubTests(unittest.TestCase):
    def test_org_stub_is_filled(self) -> None:
        """Scenario: Org stub."""
        root = make_repo(self, trees=True)
        result = new(root, "Salicylic acid")
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
        self.assertTrue(stub.is_file(), result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(),
                         "org/procedures/OSDB-0001-salicylic-acid.org")
        text = stub.read_text(encoding="utf-8")
        for line in ("#+TITLE: Salicylic acid",
                     "#+CREATED: [2026-10-19 Mon 17:42:05]",
                     "#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]",
                     "#+HUGO_SLUG: osdb-0001"):
            with self.subTest(line=line):
                self.assertEqual(text.splitlines().count(line), 1)
        self.assertNotRegex(text, r"(?im)^#\+AI_MODEL:")
        self.assertNotIn("OSDB-0000", text)
        self.assertNotIn("osdb-0000", text)

    def test_org_stub_weekday_ignores_the_locale(self) -> None:
        """Scenario: Weekday independent of the locale."""
        root = make_repo(self, trees=True)
        saved = locale.setlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
        except locale.Error:
            self.skipTest("locale de_DE.UTF-8 is not installed")
        self.addCleanup(locale.setlocale, locale.LC_TIME, saved)
        result = new(root, "Salicylic acid")
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "org" / "procedures" / "OSDB-0001-salicylic-acid.org"
        self.assertIn("#+CREATED: [2026-10-19 Mon 17:42:05]\n",
                      stub.read_text(encoding="utf-8"))

    def test_markdown_stub_with_quoted_title(self) -> None:
        """Scenario: Markdown stub with a quoted title."""
        root = make_repo(self)
        title = 'Bob\'s "best" ester'
        result = new(root, title, md=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        stub = root / "md" / "procedures" / "OSDB-0001-bob-s-best-ester.md"
        self.assertTrue(stub.is_file(), result.stdout + result.stderr)
        data = front_matter(stub.read_text(encoding="utf-8"))
        self.assertEqual(data["title"], title)
        moment = dt.datetime.fromisoformat(NOW)
        self.assertEqual(data["date"], moment)
        self.assertEqual(data["lastmod"], moment)
        self.assertEqual(data["id"], "OSDB-0001")
        self.assertNotIn("ai_model", data)
        with support.template_registry() as registry, \
                support.format_settings() as settings:
            checked = support.run_validator(
                ["--registry", registry, "--settings", settings,
                 stub.parent])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout, "")

    def test_template_filling_rejects_a_missing_anchor_line(self) -> None:
        """Scenario: Template filling (design D1: ValueError on a missing
        anchor line)."""
        text = (REPO / "templates" / "procedure.org").read_text(
            encoding="utf-8")
        broken = re.sub(r"^#\+TITLE:.*\n", "", text, flags=re.M)
        now = dt.datetime.fromisoformat(NOW)
        with self.assertRaises(ValueError):
            pipeline().fill_template(broken, "org", "OSDB-0001", "T", now)


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


FENCE = "`" * 3
LINKED_SOURCE = f"""+++
id = "OSDB-0001"
+++
## Procedure

Add the acid (Note 1). Stir the mixture (Note
2) and cool it (Note 3).

{FENCE}text
(Note 1)
{FENCE}

Keep `(Note 1)` literal.

## Notes {{#notes}}

1.  First note,
    continued.
2.  Second note.

A paragraph after the list.
3. Not a note.

## Hazards and Waste Disposal
"""
LINKED_RESULT = f"""+++
id = "OSDB-0001"
+++
## Procedure

Add the acid ([Note 1](#note-1)). Stir the mixture ([Note
2](#note-2)) and cool it (Note 3).

{FENCE}text
(Note 1)
{FENCE}

Keep `(Note 1)` literal.

## Notes {{#notes}}

1.  <span id="note-1"></span>First note,
    continued.
2.  <span id="note-2"></span>Second note.

A paragraph after the list.
3. Not a note.

## Hazards and Waste Disposal
"""


class NoteLinkTests(unittest.TestCase):
    """site-theme "Note references": pipeline.link_notes."""

    def test_notes_and_references_are_linked(self) -> None:
        """Scenario: Notes and references are linked."""
        self.assertEqual(pipeline().link_notes(LINKED_SOURCE), LINKED_RESULT)

    def test_german_notes_and_other_numbering(self) -> None:
        """Scenario: German notes, other numbering."""
        link = pipeline().link_notes
        self.assertEqual(
            link("## Durchführung\n\nRühren (Anmerkung 2).\n\n"
                 "## Anmerkungen\n\n1. Eins.\n1. Zwei.\n"),
            "## Durchführung\n\nRühren ([Anmerkung 2](#note-2)).\n\n"
            "## Anmerkungen\n\n1. <span id=\"note-1\"></span>Eins.\n"
            "1. <span id=\"note-2\"></span>Zwei.\n")
        self.assertEqual(
            link("## NOTES\n\n3. Three.\n4. Four.\n\n"
                 "See (Note 3) and (Note 1).\n"),
            "## NOTES\n\n3. <span id=\"note-3\"></span>Three.\n"
            "4. <span id=\"note-4\"></span>Four.\n\n"
            "See ([Note 3](#note-3)) and (Note 1).\n")
        plain = "## Procedure\n\nStir (Note 1).\n\n1. A step.\n"
        self.assertEqual(link(plain), plain)

    def test_nested_lists_and_fences_stay_inside_their_note(self) -> None:
        """Requirement: Note references (top-level items only)."""
        link = pipeline().link_notes
        nested = ("## Notes\n\n1. First\n   1. Detail\n2. Second\n\n"
                  "See (Note 2) and (Note 3).\n")
        self.assertEqual(
            link(nested),
            "## Notes\n\n1. <span id=\"note-1\"></span>First\n"
            "   1. Detail\n2. <span id=\"note-2\"></span>Second\n\n"
            "See ([Note 2](#note-2)) and (Note 3).\n")
        fenced = (f"## Notes\n\n1. First:\n\n   {FENCE}\n   2. not a note\n"
                  f"   {FENCE}\n\n2. Second\n\nSee (Note 2).\n")
        self.assertEqual(
            link(fenced),
            f"## Notes\n\n1. <span id=\"note-1\"></span>First:\n\n"
            f"   {FENCE}\n   2. not a note\n   {FENCE}\n\n"
            "2. <span id=\"note-2\"></span>Second\n\n"
            "See ([Note 2](#note-2)).\n")

    def test_an_escaped_backtick_opens_no_code_span(self) -> None:
        """Requirement: Note references (code spans as Markdown reads
        them)."""
        text = ("Use \\` for a backtick (Note 1), then `literal` and "
                "``(Note 1)`` and ```a `` b (Note 1)```.\n\n"
                "## Notes\n\n1. Only.\n")
        self.assertEqual(
            pipeline().link_notes(text),
            "Use \\` for a backtick ([Note 1](#note-1)), then `literal` "
            "and ``(Note 1)`` and ```a `` b (Note 1)```.\n\n"
            "## Notes\n\n1. <span id=\"note-1\"></span>Only.\n")

    def test_staging_links_the_notes(self) -> None:
        """Requirement: Note references (stage_content applies it)."""
        with tempfile.TemporaryDirectory(prefix="note links ") as tmp:
            source = Path(tmp) / "OSDB-0001-x.md"
            source.write_text(LINKED_SOURCE, encoding="utf-8")
            target = Path(tmp) / "staged"
            pipeline().stage_content([(source, {})], target)
            self.assertEqual(
                (target / "OSDB-0001-x.md").read_text(encoding="utf-8"),
                LINKED_RESULT)


SETTINGS_FILE = FIXTURES / "settings" / "orgsyndb.toml"
PROCEDURE_SETTINGS = FIXTURES / "procedure-fields" / "orgsyndb.toml"
TEST_SETTINGS = TEST_COLLECTION / "orgsyndb.toml"
TEST_REGISTRY = TEST_COLLECTION / "registry.json"
FIXTURE_REGISTRY = FIXTURES / "registry.json"


def load_registry(path: Path = TEST_REGISTRY) -> dict:
    """The snapshot file ``path`` as a table."""
    return json.loads(path.read_text(encoding="utf-8"))


def registry_with(**vocabularies: list[dict]) -> dict:
    """A snapshot holding the given vocabularies (``chemical_classes``
    for ``chemical-classes`` and so on) and no substance."""
    names = {"chemical-classes": [], "inventory-groups": [],
             "projects": [], "reaction-types": []}
    for name, terms in vocabularies.items():
        names[name.replace("_", "-")] = terms
    return {"format": 1, "vocabularies": names, "substances": [],
            "digest": "0" * 64}


def field_data(field: fs.Field) -> dict:
    """The field data of one field as the contract states it: a text
    field has ``search`` and ``beside``; a choice field has ``facet``,
    ``multiple``, ``tabs``, ``values`` and ``order``."""
    data: dict = {"key": field.key, "type": field.type,
                  "column": field.column, "label": field.label}
    if field.type == "text":
        data.update(search=field.search, beside=field.beside)
        return data
    data.update(
        facet=field.facet, multiple=field.multiple, tabs=field.tabs,
        values={key: {"label": path[-1], "path": list(path),
                      "ancestors": list(field.ancestors[key])}
                for key, path in field.paths.items()},
        order=list(field.order))
    return data


def procedure_field_data(field: fs.Field) -> dict:
    """The field data of one procedure field as the contract states
    it."""
    data: dict = {"key": field.key, "type": field.type,
                  "label": field.label}
    if field.type == "number" and field.unit:
        data["unit"] = field.unit
    if field.type in ("boolean", "choice"):
        data["facet"] = field.facet
    if field.type == "choice":
        data.update(
            multiple=field.multiple,
            values={key: {"label": path[-1], "path": list(path),
                          "ancestors": list(field.ancestors[key])}
                    for key, path in field.paths.items()},
            order=list(field.order))
    return data


class FieldDataTests(unittest.TestCase):
    """compound-fields "Field data for the site"."""

    def settings(self, text: str) -> Path:
        """An ``orgsyndb.toml`` holding ``text`` in a temporary
        collection."""
        root = make_repo(self)
        (root / "orgsyndb.toml").write_text(text, encoding="utf-8")
        return root / "orgsyndb.toml"

    def data(self, language: str = "en", registry: dict | None = None,
             settings: Path = SETTINGS_FILE) -> dict:
        return pipeline_function("fields_data")(
            settings, load_registry() if registry is None else registry,
            language)

    def test_field_data_in_both_languages(self) -> None:
        """Scenario: Field data in both languages."""
        for language in ("en", "de"):
            with self.subTest(language=language):
                data = self.data(language)
                self.assertEqual(list(data), ["compound", "procedure"])
                self.assertEqual(data["procedure"], [])
                self.assertEqual(
                    [f["key"] for f in data["compound"]],
                    ["article_number", "short_name", "chemical_class",
                     "group"])
                self.assertEqual(
                    data["compound"],
                    [field_data(f) for f in fs.registry_fields(
                        load_registry(), language)])

    def test_the_stated_values_of_the_scenario(self) -> None:
        """Scenario: Field data in both languages (the stated values)."""
        english = {f["key"]: f for f in self.data("en")["compound"]}
        german = {f["key"]: f for f in self.data("de")["compound"]}
        for fields in (english, german):
            self.assertIs(fields["chemical_class"]["multiple"], True)
            self.assertIs(fields["chemical_class"]["column"], True)
            self.assertIs(fields["chemical_class"]["facet"], True)
            self.assertIs(fields["group"]["tabs"], True)
            self.assertIs(fields["group"]["multiple"], False)
            for key in ("article_number", "short_name"):
                self.assertIs(fields[key]["search"], True, key)
                self.assertIs(fields[key]["beside"], True, key)
            self.assertEqual(
                fields["chemical_class"]["values"]["ketones"]["ancestors"],
                ["carbonyl-compounds"])
        self.assertEqual(
            english["chemical_class"]["values"]["ketones"],
            {"label": "Ketones",
             "path": ["Carbonyl compounds", "Ketones"],
             "ancestors": ["carbonyl-compounds"]})
        self.assertEqual(
            german["chemical_class"]["values"]["ketones"],
            {"label": "Ketone", "path": ["Carbonylverbindungen", "Ketone"],
             "ancestors": ["carbonyl-compounds"]})
        self.assertEqual(english["article_number"]["label"], "Article no.")
        self.assertEqual(german["article_number"]["label"], "Artikelnr.")
        self.assertEqual(english["short_name"]["label"], "Short name")
        self.assertEqual(german["short_name"]["label"], "Kurzname")
        self.assertEqual(english["chemical_class"]["label"],
                         "Chemical class")
        self.assertEqual(german["chemical_class"]["label"], "Stoffklasse")
        self.assertEqual(english["group"]["label"], "Group")
        self.assertEqual(german["group"]["label"], "Gruppe")

    def test_the_classes_of_a_branch_follow_their_parent(self) -> None:
        """Scenario: Field data in both languages (the `order` of
        `chemical_class` begins with `alcohols`, `aryl-halides`,
        `carbonyl-compounds`, `acid-derivatives`, `anhydrides` and
        `esters`)."""
        order = {f["key"]: f for f in self.data()["compound"]
                 }["chemical_class"]["order"]
        self.assertEqual(order[:6], [
            "alcohols", "aryl-halides", "carbonyl-compounds",
            "acid-derivatives", "anhydrides", "esters"])

    def test_a_field_carries_only_the_keys_its_type_has(self) -> None:
        """Requirement: Field data for the site (these keys and no
        other)."""
        keys = {field["key"]: set(field)
                for field in self.data()["compound"]}
        base = {"key", "type", "column", "label"}
        self.assertEqual(keys["article_number"], base | {"search", "beside"})
        self.assertEqual(keys["short_name"], base | {"search", "beside"})
        choice = base | {"facet", "multiple", "tabs", "values", "order"}
        self.assertEqual(keys["chemical_class"], choice)
        self.assertEqual(keys["group"], choice)

    def test_the_presentation_of_each_registry_field(self) -> None:
        """Requirement: Registry fields (the table of presentation)."""
        by_key = {f["key"]: f for f in self.data()["compound"]}
        self.assertEqual(
            {key: (f["type"], f["column"]) for key, f in by_key.items()},
            {"article_number": ("text", True),
             "short_name": ("text", False),
             "chemical_class": ("choice", True),
             "group": ("choice", False)})
        self.assertEqual(
            {key: (f["facet"], f["tabs"]) for key, f in by_key.items()
             if f["type"] == "choice"},
            {"chemical_class": (True, False), "group": (True, True)})

    def test_the_group_field_of_the_test_collection(self) -> None:
        """Requirement: Field data for the site (the `group` field)."""
        group = {f["key"]: f for f in self.data("de")["compound"]}["group"]
        self.assertEqual(set(group["values"]), {
            "purchased", "reagents", "starting-materials", "synthesised",
            "final-products", "intermediates"})
        self.assertEqual(
            group["values"]["reagents"],
            {"label": "Reagenzien", "path": ["Zugekauft", "Reagenzien"],
             "ancestors": ["purchased"]})
        self.assertEqual(
            group["values"]["synthesised"],
            {"label": "Selbst hergestellt",
             "path": ["Selbst hergestellt"], "ancestors": []})
        self.assertEqual(
            [key for key in group["order"] if key in
             ("purchased", "synthesised")],
            ["purchased", "synthesised"])

    def test_the_result_is_json(self) -> None:
        """Requirement: Field data for the site (the JSON that the build
        stages)."""
        for language in ("en", "de"):
            data = self.data(language)
            self.assertEqual(json.loads(json.dumps(data)), data)

    def test_labels_fall_back_to_the_english_one(self) -> None:
        """Requirement: Field data for the site (`label`, a term without
        `label_de`)."""
        registry = registry_with(chemical_classes=[
            term("top", "Top", "Oben"),
            term("middle", "Middle", None, "top"),
            term("bottom", "Bottom", "Unten", "middle")])
        data = self.data("de", registry)
        classes = {f["key"]: f for f in data["compound"]
                   }["chemical_class"]
        self.assertEqual(classes["values"], {
            "top": {"label": "Oben", "path": ["Oben"], "ancestors": []},
            "middle": {"label": "Middle", "path": ["Oben", "Middle"],
                       "ancestors": ["top"]},
            "bottom": {"label": "Unten",
                       "path": ["Oben", "Middle", "Unten"],
                       "ancestors": ["top", "middle"]}})

    def test_a_value_is_listed_at_every_level(self) -> None:
        """Requirement: Field data for the site (`values` holds every
        term of the vocabulary)."""
        classes = {f["key"]: f for f in self.data("de")["compound"]
                   }["chemical_class"]["values"]
        self.assertEqual(len(classes), 13)
        self.assertEqual(
            classes["aryl-ketones"],
            {"label": "Arylketone",
             "path": ["Carbonylverbindungen", "Ketone", "Arylketone"],
             "ancestors": ["carbonyl-compounds", "ketones"]})
        self.assertEqual(
            classes["anhydrides"]["path"],
            ["Carbonylverbindungen", "Carbonsäurederivate",
             "Anhydride"])
        self.assertEqual(classes["alcohols"]["ancestors"], [])

    def test_a_vocabulary_listed_out_of_order(self) -> None:
        """Scenario: Depth-first order."""
        registry = registry_with(chemical_classes=[
            term("esters", "Esters", None, "carbonyl-compounds"),
            term("alcohols", "Alcohols"),
            term("carbonyl-compounds", "Carbonyl compounds"),
            term("ketones", "Ketones", None, "carbonyl-compounds"),
            term("aryl-ketones", "Aryl ketones", None, "ketones")])
        classes = {f["key"]: f for f in self.data("en", registry)["compound"]
                   }["chemical_class"]
        self.assertEqual(classes["order"], [
            "alcohols", "carbonyl-compounds", "esters", "ketones",
            "aryl-ketones"])
        values = classes["values"]
        self.assertEqual(values["aryl-ketones"]["ancestors"],
                         ["carbonyl-compounds", "ketones"])
        self.assertEqual(values["esters"]["ancestors"],
                         ["carbonyl-compounds"])
        self.assertEqual(values["alcohols"]["ancestors"], [])

    def test_the_order_holds_every_value_once(self) -> None:
        """Requirement: Field data for the site (`order`: the keys of
        every term)."""
        field = {f["key"]: f for f in self.data()["compound"]
                 }["chemical_class"]
        self.assertEqual(len(field["order"]), len(set(field["order"])))
        self.assertEqual(set(field["order"]), set(field["values"]))
        for key in field["order"]:
            position = field["order"].index(key)
            for ancestor in field["values"][key]["ancestors"]:
                self.assertLess(field["order"].index(ancestor), position)
        self.assertEqual(field["order"].index("aryl-ketones"),
                         field["order"].index("ketones") + 1)

    def test_a_registry_without_terms_gives_fields_without_values(
            self) -> None:
        """Requirement: Field data for the site (`values` and `order` of
        an empty vocabulary)."""
        data = self.data("en", registry_with())
        self.assertEqual([f["key"] for f in data["compound"]],
                         ["article_number", "short_name", "chemical_class",
                          "group"])
        for field in data["compound"][2:]:
            self.assertEqual((field["values"], field["order"]), ({}, []))

    def test_no_settings_file(self) -> None:
        """Scenario: No settings file."""
        with tempfile.TemporaryDirectory(prefix="no settings ") as tmp:
            missing = Path(tmp) / "orgsyndb.toml"
            for language in ("en", "de"):
                data = self.data(language, settings=missing)
                self.assertEqual(data["procedure"], [])
                self.assertEqual(
                    [f["key"] for f in data["compound"]],
                    ["article_number", "short_name", "chemical_class",
                     "group"])

    def test_a_settings_file_that_declares_no_field(self) -> None:
        """Requirement: Field data for the site (declares no procedure
        field)."""
        path = self.settings("format = 1\n")
        data = self.data(settings=path)
        self.assertEqual(data["procedure"], [])
        self.assertEqual(len(data["compound"]), 4)

    def test_a_declaration_of_a_compound_field_is_a_configuration_error(
            self) -> None:
        """Requirement: Registry fields (a collection declares no
        compound field)."""
        path = self.settings(
            'format = 1\n\n[[fields.compound]]\nkey = "x"\n'
            'type = "text"\nlabel = "X"\n')
        with self.assertRaisesRegex(pipeline().validate.ConfigError,
                                    "fields.compound"):
            self.data(settings=path)

    def test_a_broken_declaration_is_a_configuration_error(self) -> None:
        """Requirement: Field data for the site (a rule of the procedure
        declarations)."""
        error = pipeline().validate.ConfigError
        head = "format = 1\n\n[[fields.procedure]]\n"
        cases = {
            "no label": head + 'key = "x"\ntype = "text"\n',
            "unknown option": head + (
                'key = "x"\ntype = "text"\nlabel = "X"\nsortable = true\n'),
            "tabs on a text field": head + (
                'key = "x"\ntype = "text"\nlabel = "X"\ntabs = true\n'),
            "a reserved key": head + (
                'key = "status"\ntype = "text"\nlabel = "Status"\n'),
            "a single table": (
                'format = 1\n\n[fields.procedure]\nkey = "x"\n'
                'type = "text"\nlabel = "X"\n'),
            "a misspelt entity": (
                'format = 1\n\n[[fields.reagent]]\nkey = "lot"\n'
                'type = "text"\nlabel = "Lot"\n'),
            "a vocabulary the registry lacks": head + (
                'key = "x"\ntype = "choice"\nlabel = "X"\n'
                'vocabulary = "storage"\n')}
        for name, text in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(error):
                    self.data(settings=self.settings(text))


class ProcedureFieldDataTests(unittest.TestCase):
    """procedure-fields "Procedure field data"."""

    settings = FieldDataTests.settings

    def data(self, language: str = "en", settings: Path = PROCEDURE_SETTINGS,
             registry: dict | None = None) -> dict:
        return pipeline_function("fields_data")(
            settings,
            load_registry(FIXTURE_REGISTRY) if registry is None
            else registry, language)

    def test_procedure_field_data_in_both_languages(self) -> None:
        """Scenario: Procedure field data in both languages."""
        for language in ("en", "de"):
            with self.subTest(language=language):
                data = self.data(language)
                self.assertEqual(list(data), ["compound", "procedure"])
                self.assertEqual(
                    [f["key"] for f in data["compound"]],
                    ["article_number", "short_name", "chemical_class",
                     "group"])
                self.assertEqual(
                    [f["key"] for f in data["procedure"]],
                    ["notebook", "working_time", "inert_atmosphere",
                     "project"])
                self.assertEqual(
                    data["procedure"],
                    [procedure_field_data(f) for f in fs.read_fields(
                        PROCEDURE_SETTINGS, load_registry(FIXTURE_REGISTRY),
                        language)])

    def test_the_stated_values_of_the_scenario(self) -> None:
        """Scenario: Procedure field data in both languages (the stated
        values)."""
        english = {f["key"]: f for f in self.data("en")["procedure"]}
        german = {f["key"]: f for f in self.data("de")["procedure"]}
        for fields in (english, german):
            self.assertEqual(fields["working_time"]["unit"], "h")
            self.assertIs(fields["project"]["multiple"], False)
            self.assertIs(fields["project"]["facet"], False)
            self.assertIs(fields["inert_atmosphere"]["facet"], False)
            self.assertEqual(fields["inert_atmosphere"]["label"],
                             "Inert atmosphere")
            self.assertEqual(fields["project"]["order"],
                             ["research", "teaching",
                              "first-year-practical"])
            for field in fields.values():
                for key in ("column", "search", "tabs"):
                    self.assertNotIn(key, field)
        self.assertEqual(
            english["project"]["values"]["first-year-practical"],
            {"label": "First-year practical",
             "path": ["Teaching", "First-year practical"],
             "ancestors": ["teaching"]})
        self.assertEqual(
            german["project"]["values"]["first-year-practical"],
            {"label": "Grundpraktikum",
             "path": ["Lehre", "Grundpraktikum"],
             "ancestors": ["teaching"]})

    def test_a_field_carries_only_the_keys_its_type_has(self) -> None:
        """Requirement: Procedure field data (these keys and no
        other)."""
        keys = {field["key"]: set(field)
                for field in self.data()["procedure"]}
        base = {"key", "type", "label"}
        self.assertEqual(keys["notebook"], base)
        self.assertEqual(keys["working_time"], base | {"unit"})
        self.assertEqual(keys["inert_atmosphere"], base | {"facet"})
        self.assertEqual(
            keys["project"],
            base | {"facet", "multiple", "values", "order"})

    def test_facet_and_multiple_are_taken_as_declared(self) -> None:
        """Requirement: Procedure field data (`facet`, `multiple`, as
        declared)."""
        path = self.settings(
            'format = 1\n\n[[fields.procedure]]\nkey = "flag"\n'
            'type = "boolean"\nlabel = "Flag"\nfacet = true\n\n'
            '[[fields.procedure]]\nkey = "note"\ntype = "text"\n'
            'label = "Note"\n\n[[fields.procedure]]\nkey = "category"\n'
            'type = "choice"\nlabel = "Category"\n'
            'vocabulary = "chemical-classes"\n'
            'facet = true\nmultiple = true\n\n'
            '[[fields.procedure]]\nkey = "count"\ntype = "number"\n'
            'label = "Count"\nmin = 0\n')
        data = self.data(settings=path)
        by_key = {f["key"]: f for f in data["procedure"]}
        self.assertIs(by_key["flag"]["facet"], True)
        self.assertIs(by_key["category"]["facet"], True)
        self.assertIs(by_key["category"]["multiple"], True)
        self.assertNotIn("facet", by_key["note"])
        self.assertEqual(set(by_key["count"]), {"key", "type", "label"})

    def test_a_choice_over_the_reaction_types(self) -> None:
        """Requirement: Procedure field data (`values` and `order` of a
        field over `reaction-types`)."""
        path = self.settings(
            'format = 1\n\n[[fields.procedure]]\nkey = "side_reaction"\n'
            'type = "choice"\nlabel = "Side reaction"\n'
            'vocabulary = "reaction-types"\n')
        (field,) = self.data("de", path)["procedure"]
        self.assertEqual(field["order"], ["esterification", "reduction"])
        self.assertEqual(
            field["values"]["reduction"],
            {"label": "Reduction", "path": ["Reduction"], "ancestors": []})

    def test_the_test_collection_procedure_fields(self) -> None:
        """Requirement: Procedure field data (the test collection)."""
        for language in ("en", "de"):
            with self.subTest(language=language):
                data = self.data(language, TEST_SETTINGS, load_registry())
                self.assertEqual(
                    [f["key"] for f in data["procedure"]],
                    ["notebook", "project", "working_time",
                     "inert_atmosphere"])
                by_key = {f["key"]: f for f in data["procedure"]}
                self.assertEqual(
                    set(by_key["project"]["order"]),
                    {"teaching", "first-year-practical",
                     "advanced-practical", "research", "biaryls",
                     "cinnamates"})
                self.assertIs(by_key["project"]["facet"], True)
                self.assertIs(by_key["inert_atmosphere"]["facet"], True)
                self.assertEqual(by_key["working_time"]["unit"], "h")
                self.assertNotIn("facet", by_key["notebook"])
                self.assertEqual(len(data["compound"]), 4)
        german = self.data("de", TEST_SETTINGS, load_registry())
        self.assertEqual(
            [f["label"] for f in german["procedure"]],
            ["Laborjournal", "Projekt", "Arbeitszeit", "Schutzgas"])

    def test_the_result_is_json(self) -> None:
        """Requirement: Procedure field data (the JSON that the build
        stages)."""
        for language in ("en", "de"):
            data = self.data(language)
            self.assertEqual(json.loads(json.dumps(data)), data)

    def test_a_vocabulary_the_registry_lacks_is_a_configuration_error(
            self) -> None:
        """Requirement: Procedure field data (a rule of the procedure
        declarations)."""
        path = self.settings(
            'format = 1\n\n[[fields.procedure]]\nkey = "category"\n'
            'type = "choice"\nlabel = "Category"\n'
            'vocabulary = "kinds"\n')
        with self.assertRaisesRegex(pipeline().validate.ConfigError,
                                    "kinds"):
            self.data(settings=path)


def specific(ident: str, product: str, *substrates: str,
             percent: int = 90) -> tuple[Path, dict]:
    """A specific procedure, as a ``(path, front matter)`` pair, that
    makes ``product`` at ``percent`` from ``substrates``; with no
    substrate it sets no ``substrates``."""
    data: dict = {"id": ident, "products": [
        {"compound": product, "yield_percent": percent}]}
    if substrates:
        data["substrates"] = list(substrates)
    return Path(f"{ident}.md"), data


def general(ident: str, *entries: tuple[list[str], dict[str, int]]
            ) -> tuple[Path, dict]:
    """A general procedure whose entries each start from the given
    substrates and make the given compounds at the given yields."""
    return Path(f"{ident}.md"), {"id": ident, "scope": [
        {"substrates": list(substrates), "products": [
            {"compound": key, "yield_percent": percent}
            for key, percent in products.items()]}
        for substrates, products in entries]}


def made_by(ident: str, percent: int, *substrates: dict,
            entry: int | None = None) -> dict:
    """A step of route data: procedure ``ident``, in ``entry`` of a
    general procedure, at ``percent``, starting from ``substrates``."""
    step: dict = {"procedure": ident}
    if entry is not None:
        step["entry"] = entry
    return {**step, "yield_percent": percent, "substrates": list(substrates)}


def leaf(key: str) -> dict:
    """A compound that no step makes, or that the cycle rule leaves
    without one."""
    return {"compound": key, "steps": [], "more": False}


def cut_off(key: str) -> dict:
    """A compound that the depth limit cuts off."""
    return {"compound": key, "steps": [], "more": True}


def expanded(key: str, *steps: dict) -> dict:
    """A compound with the steps that make it drawn below it."""
    return {"compound": key, "steps": list(steps), "more": False}


class RouteDataTests(unittest.TestCase):
    """synthesis-routes "Derived routes": ``pipeline.routes_data``."""

    def routes(self, *files: tuple[Path, dict], **limits: int) -> dict:
        return pipeline_function("routes_data")(list(files), **limits)

    def test_routes_of_the_test_collection(self) -> None:
        """Scenario: Routes of the test collection."""
        module = pipeline()
        files = module.choose_variants(module.content_files(
            [str(TEST_COLLECTION / "md" / "procedures")]), "en")
        self.assertEqual(len(files), 9)
        routes = pipeline_function("routes_data")(files)
        self.assertEqual(
            set(routes), {"acetylsalicylic-acid", "1-biphenyl-4-yl-ethanol",
                          "cinnamic-acid"})
        self.assertEqual(routes["acetylsalicylic-acid"], [
            made_by("OSDB-0002", 75,
                    expanded("salicylic-acid", made_by(
                        "OSDB-0001", 80, leaf("methyl-salicylate"))),
                    leaf("acetic-anhydride"))])
        acetylbiphenyl = expanded("4-acetylbiphenyl", made_by(
            "OSDB-0004", 85, leaf("4-bromoacetophenone"),
            leaf("phenylboronic-acid")))
        self.assertEqual(routes["1-biphenyl-4-yl-ethanol"], [
            made_by("OSDB-0005", 90, acetylbiphenyl),
            made_by("OSDB-0009", 90, acetylbiphenyl, entry=1)])
        self.assertEqual(routes["cinnamic-acid"], [
            made_by("OSDB-0008", 90, expanded("ethyl-cinnamate", made_by(
                "OSDB-0007", 80, leaf("benzaldehyde"),
                leaf("ethyl-triphenylphosphoranylidene-acetate"))))])
        self.assertEqual(json.loads(json.dumps(routes)), routes)

    def test_a_protection_and_its_removal_is_not_followed(self) -> None:
        """Scenario: A protection and its removal."""
        routes = self.routes(
            specific("OSDB-0001", "b", "a", percent=81),
            specific("OSDB-0002", "a", "b", percent=82),
            specific("OSDB-0003", "c", "b", percent=83))
        self.assertEqual(routes, {"c": [
            made_by("OSDB-0003", 83, expanded("b", made_by(
                "OSDB-0001", 81, leaf("a"))))]})

    def test_the_depth_limit_cuts_a_tree_off(self) -> None:
        """Scenario: The depth limit (a depth of 2)."""
        files = [specific(f"OSDB-000{n}", f"c{n}", f"c{n - 1}",
                          percent=60 + n) for n in range(1, 5)]
        routes = self.routes(*files, depth=2)
        self.assertEqual(set(routes), {"c2", "c3", "c4"})
        self.assertEqual(routes["c4"], [made_by("OSDB-0004", 64, expanded(
            "c3", made_by("OSDB-0003", 63, cut_off("c2"))))])
        self.assertEqual(routes["c3"], [made_by("OSDB-0003", 63, expanded(
            "c2", made_by("OSDB-0002", 62, cut_off("c1"))))])
        self.assertEqual(routes["c2"], [made_by("OSDB-0002", 62, expanded(
            "c1", made_by("OSDB-0001", 61, leaf("c0"))))])

    def test_a_depth_of_one_cuts_off_every_substrate_with_a_step(
            self) -> None:
        """Scenario: The depth limit (a depth of 1)."""
        files = [specific(f"OSDB-000{n}", f"c{n}", f"c{n - 1}",
                          percent=60 + n) for n in range(1, 5)]
        routes = self.routes(*files, depth=1)
        self.assertEqual(routes, {
            f"c{n}": [made_by(f"OSDB-000{n}", 60 + n, cut_off(f"c{n - 1}"))]
            for n in (2, 3, 4)})

    def test_the_default_depth_is_six(self) -> None:
        """Scenario: The depth limit (the default of the build)."""
        files = [specific(f"OSDB-{n:04d}", f"c{n}", f"c{n - 1}")
                 for n in range(1, 9)]
        tree = self.routes(*files)["c8"]
        for level in range(6):
            (step,) = tree
            self.assertEqual(step["procedure"], f"OSDB-{8 - level:04d}")
            (substrate,) = step["substrates"]
            self.assertEqual(substrate["compound"], f"c{7 - level}")
            tree = substrate["steps"]
        self.assertEqual(tree, [])
        self.assertEqual(substrate["more"], True)

    def stepped(self, budget: int) -> dict:
        return self.routes(
            specific("OSDB-0001", "r", "a", "b", percent=71),
            specific("OSDB-0002", "a", "x", percent=72),
            specific("OSDB-0003", "b", "y", percent=73),
            specific("OSDB-0004", "x", "z", percent=74),
            depth=6, budget=budget)

    def test_a_tree_within_the_budget_is_drawn_whole(self) -> None:
        """Scenario: The step budget (a budget of 4)."""
        self.assertEqual(self.stepped(4)["r"], [made_by(
            "OSDB-0001", 71,
            expanded("a", made_by("OSDB-0002", 72, expanded(
                "x", made_by("OSDB-0004", 74, leaf("z"))))),
            expanded("b", made_by("OSDB-0003", 73, leaf("y"))))])

    def test_a_tree_over_the_budget_is_drawn_to_a_smaller_depth(
            self) -> None:
        """Scenario: The step budget (a budget of 3)."""
        self.assertEqual(self.stepped(3)["r"], [made_by(
            "OSDB-0001", 71,
            expanded("a", made_by("OSDB-0002", 72, cut_off("x"))),
            expanded("b", made_by("OSDB-0003", 73, leaf("y"))))])

    def test_a_budget_below_the_first_level_draws_one_step(self) -> None:
        """Scenario: The step budget (a budget of 0)."""
        self.assertEqual(self.stepped(0)["r"], [made_by(
            "OSDB-0001", 71, cut_off("a"), cut_off("b"))])

    def test_the_budget_counts_the_steps_of_a_tree_at_every_level(
            self) -> None:
        """Scenario: The step budget (the size of a tree)."""
        files = [specific(f"OSDB-000{n}", f"c{n}", f"c{n - 1}")
                 for n in range(1, 4)]
        for budget, drawn in ((0, 1), (1, 1), (2, 2), (3, 3), (200, 3)):
            with self.subTest(budget=budget):
                tree = self.routes(*files, depth=6, budget=budget)["c3"]
                steps = 0
                while tree:
                    (step,) = tree
                    steps += 1
                    tree = step["substrates"][0]["steps"]
                self.assertEqual(steps, drawn)

    def test_steps_come_by_id_and_entry_and_may_start_from_nothing(
            self) -> None:
        """Scenario: Order, entries and a step from nothing."""
        routes = self.routes(
            specific("OSDB-0003", "t", "m", percent=40),
            general("OSDB-0001", (["m"], {"t": 60}), (["n"], {"t": 50})),
            specific("OSDB-0002", "m", percent=30))
        from_nothing = expanded("m", made_by("OSDB-0002", 30))
        self.assertEqual(routes, {"t": [
            made_by("OSDB-0001", 60, from_nothing, entry=1),
            made_by("OSDB-0001", 50, leaf("n"), entry=2),
            made_by("OSDB-0003", 40, from_nothing)]})
        self.assertNotIn("entry", routes["t"][2])

    def test_an_entry_is_a_step_of_its_own(self) -> None:
        """Requirement: Scope entries (the steps of a derived route take
        each entry on its own)."""
        routes = self.routes(
            general("OSDB-0001", (["a"], {"u": 61, "t": 62}),
                    (["b", "c"], {"v": 63})),
            specific("OSDB-0002", "w", "t", "v"),
            specific("OSDB-0003", "t", "b"))
        self.assertEqual(routes["w"], [made_by(
            "OSDB-0002", 90,
            expanded("t", made_by("OSDB-0001", 62, leaf("a"), entry=1),
                     made_by("OSDB-0003", 90, leaf("b"))),
            expanded("v", made_by("OSDB-0001", 63, leaf("b"), leaf("c"),
                                  entry=2)))])

    def test_only_the_compounds_of_a_route_deeper_than_one_step_are_keys(
            self) -> None:
        """Requirement: Derived routes (a compound whose steps all start
        from compounds that nothing makes is not a key)."""
        routes = self.routes(
            specific("OSDB-0001", "p", "a"),
            specific("OSDB-0002", "q", "p"),
            specific("OSDB-0003", "q", "a"))
        self.assertEqual(set(routes), {"q"})
        self.assertEqual(routes["q"], [
            made_by("OSDB-0002", 90, expanded("p", made_by(
                "OSDB-0001", 90, leaf("a")))),
            made_by("OSDB-0003", 90, leaf("a"))])

    def test_no_procedure_gives_no_routes(self) -> None:
        """Requirement: Derived routes (no procedure, no key)."""
        self.assertEqual(self.routes(), {})


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

    def test_module_has_no_command_line(self) -> None:
        """Scenario: No command-line interface."""
        text = PIPELINE.read_text(encoding="utf-8")
        self.assertFalse(os.access(PIPELINE, os.X_OK), "executable")
        self.assertFalse(text.startswith("#!"), "has a shebang")
        self.assertNotIn('if __name__ == "__main__":', text)
