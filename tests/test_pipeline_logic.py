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

import support
from pipeline_support import (FIXTURES, GIT_QUIET, PIPELINE, REPO, Run,
                              TEST_COLLECTION, captured, front_matter,
                              pipeline, pipeline_function, snapshot)

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
        with support.template_registry() as registry:
            checked = support.run_validator(
                ["--compounds", registry, stub.parent])
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


FIELDS_SETTINGS = FIXTURES / "fields" / "orgsyndb.toml"
TEST_SETTINGS = TEST_COLLECTION / "orgsyndb.toml"


def fixture_fields(language: str) -> list[dict]:
    """The field data of the ``fields/`` fixtures that the contract
    states, in ``language``: ``en`` or ``de``."""
    german = language == "de"

    def shown(english: str, deutsch: str | None = None) -> str:
        return deutsch if german and deutsch is not None else english

    def values(entries: dict[str, tuple[str, ...]],
               ancestors: dict[str, list[str]]) -> dict[str, dict]:
        return {key: {"label": path[-1], "path": list(path),
                      "ancestors": ancestors.get(key, [])}
                for key, path in entries.items()}

    carbonyl = shown("Carbonyl compounds", "Carbonylverbindungen")
    return [
        {"key": "item_number", "type": "text", "column": True,
         "search": False, "label": shown("Item no.", "Artikelnr.")},
        {"key": "short_name", "type": "text", "column": False,
         "search": False, "label": "Short name"},
        {"key": "stock", "type": "number", "column": False,
         "label": shown("Stock", "Bestand"), "unit": "g"},
        {"key": "in_house", "type": "boolean", "column": False,
         "facet": False,
         "label": shown("Made in house", "Eigene Herstellung")},
        {"key": "chemical_class", "type": "choice", "column": True,
         "facet": False, "label": shown("Chemical class", "Stoffklasse"),
         "multiple": True,
         "values": values({
             "carbonyl-compounds": (carbonyl,),
             "ketones": (carbonyl, shown("Ketones", "Ketone")),
             "esters": (carbonyl, shown("Esters", "Ester")),
             "alcohols": (shown("Alcohols", "Alkohole"),)},
             {"ketones": ["carbonyl-compounds"],
              "esters": ["carbonyl-compounds"]}),
         "order": ["carbonyl-compounds", "ketones", "esters", "alcohols"]},
        {"key": "storage", "type": "choice", "column": False,
         "facet": False, "label": shown("Storage", "Lagerung"),
         "multiple": False,
         "values": values({
             "cabinet": (shown("Cabinet", "Schrank"),),
             "fridge": (shown("Fridge", "K\u00fchlschrank"),)}, {}),
         "order": ["cabinet", "fridge"]},
    ]


class FieldDataTests(unittest.TestCase):
    """compound-fields "Field data for the site"."""

    def settings(self, text: str,
                 vocabularies: dict[str, str] | None = None) -> Path:
        """An ``orgsyndb.toml`` holding ``text``, beside the
        ``vocabularies`` (name to text) in a temporary collection."""
        root = make_repo(self)
        (root / "orgsyndb.toml").write_text(text, encoding="utf-8")
        (root / "vocabularies").mkdir()
        for name, content in (vocabularies or {}).items():
            (root / "vocabularies" / f"{name}.toml").write_text(
                content, encoding="utf-8")
        return root / "orgsyndb.toml"

    def test_field_data_in_both_languages(self) -> None:
        """Scenario: Field data in both languages."""
        fields_data = pipeline_function("fields_data")
        for language in ("en", "de"):
            with self.subTest(language=language):
                data = fields_data(FIELDS_SETTINGS, language)
                self.assertEqual(list(data), ["compound"])
                self.assertEqual([f["key"] for f in data["compound"]],
                                 ["item_number", "short_name", "stock",
                                  "in_house", "chemical_class", "storage"])
                self.assertEqual(data["compound"],
                                 fixture_fields(language))

    def test_the_stated_values_of_the_scenario(self) -> None:
        """Scenario: Field data in both languages (the stated values)."""
        fields_data = pipeline_function("fields_data")
        english = {f["key"]: f for f in
                   fields_data(FIELDS_SETTINGS, "en")["compound"]}
        german = {f["key"]: f for f in
                  fields_data(FIELDS_SETTINGS, "de")["compound"]}
        self.assertEqual(english["stock"]["unit"], "g")
        self.assertIs(english["chemical_class"]["multiple"], True)
        self.assertIs(english["chemical_class"]["column"], True)
        self.assertIs(english["storage"]["multiple"], False)
        self.assertEqual(
            english["chemical_class"]["values"]["ketones"],
            {"label": "Ketones",
             "path": ["Carbonyl compounds", "Ketones"],
             "ancestors": ["carbonyl-compounds"]})
        self.assertEqual(
            german["chemical_class"]["values"]["ketones"],
            {"label": "Ketone", "path": ["Carbonylverbindungen", "Ketone"],
             "ancestors": ["carbonyl-compounds"]})
        self.assertEqual(english["short_name"]["label"], "Short name")
        self.assertEqual(german["short_name"]["label"], "Short name")
        for fields in (english, german):
            self.assertIs(fields["item_number"]["search"], False)
            self.assertIs(fields["short_name"]["search"], False)
            for key in ("in_house", "chemical_class", "storage"):
                self.assertIs(fields[key]["facet"], False, key)
            self.assertEqual(
                fields["chemical_class"]["values"]["alcohols"]["ancestors"],
                [])
            self.assertEqual(
                fields["chemical_class"]["order"],
                ["carbonyl-compounds", "ketones", "esters", "alcohols"])

    def test_a_field_carries_only_the_keys_its_type_has(self) -> None:
        """Requirement: Field data for the site (these keys and no
        other)."""
        data = pipeline_function("fields_data")(FIELDS_SETTINGS, "en")
        keys = {field["key"]: set(field) for field in data["compound"]}
        base = {"key", "type", "column", "label"}
        self.assertEqual(keys["item_number"], base | {"search"})
        self.assertEqual(keys["short_name"], base | {"search"})
        self.assertEqual(keys["in_house"], base | {"facet"})
        self.assertEqual(keys["stock"], base | {"unit"})
        choice = base | {"facet", "multiple", "values", "order"}
        self.assertEqual(keys["chemical_class"], choice)
        self.assertEqual(keys["storage"], choice)

    def test_facet_and_search_are_taken_as_declared(self) -> None:
        """Requirement: Field data for the site (`facet` and `search`, as
        declared)."""
        path = self.settings(
            'format = 1\n\n[[fields.compound]]\nkey = "tag"\n'
            'type = "text"\nlabel = "Tag"\nsearch = true\n\n'
            '[[fields.compound]]\nkey = "note"\ntype = "text"\n'
            'label = "Note"\n\n[[fields.compound]]\nkey = "flag"\n'
            'type = "boolean"\nlabel = "Flag"\nfacet = true\n\n'
            '[[fields.compound]]\nkey = "kind"\ntype = "choice"\n'
            'label = "Kind"\nvocabulary = "kinds"\nfacet = true\n',
            {"kinds": '[top]\nlabel = "Top"\n'})
        data = pipeline_function("fields_data")(path, "en")
        by_key = {f["key"]: f for f in data["compound"]}
        self.assertIs(by_key["tag"]["search"], True)
        self.assertIs(by_key["note"]["search"], False)
        self.assertIs(by_key["flag"]["facet"], True)
        self.assertIs(by_key["kind"]["facet"], True)
        self.assertNotIn("facet", by_key["tag"])
        self.assertNotIn("search", by_key["flag"])
        self.assertNotIn("search", by_key["kind"])

    def test_the_test_collection_facets_and_searches(self) -> None:
        """Requirement: Field data for the site (`facet` and `search` of
        the test collection)."""
        data = pipeline_function("fields_data")(TEST_SETTINGS, "en")
        flags = {f["key"]: (f.get("facet"), f.get("search"))
                 for f in data["compound"]}
        self.assertEqual(flags, {
            "item_number": (None, True), "short_name": (None, True),
            "chemical_class": (True, None), "stock": (None, None),
            "in_house": (True, None)})

    def test_a_number_without_a_unit_has_no_unit_key(self) -> None:
        """Requirement: Field data for the site (`unit`: only for a number
        field that declares one)."""
        path = self.settings(
            'format = 1\n\n[[fields.compound]]\nkey = "count"\n'
            'type = "number"\nlabel = "Count"\nmin = 0\nmax = 9\n')
        data = pipeline_function("fields_data")(path, "en")
        self.assertEqual(data, {"compound": [
            {"key": "count", "type": "number", "label": "Count",
             "column": False}]})

    def test_the_result_is_json(self) -> None:
        """Requirement: Field data for the site (the JSON that the build
        stages)."""
        fields_data = pipeline_function("fields_data")
        for language in ("en", "de"):
            data = fields_data(FIELDS_SETTINGS, language)
            self.assertEqual(json.loads(json.dumps(data)), data)

    def test_labels_fall_back_to_the_english_one(self) -> None:
        """Requirement: Field data for the site (labels, `label_de`
        absent)."""
        path = self.settings(
            'format = 1\n\n[[fields.compound]]\nkey = "kind"\n'
            'type = "choice"\nlabel = "Kind"\nvocabulary = "kinds"\n',
            {"kinds": '[top]\nlabel = "Top"\nlabel_de = "Oben"\n\n'
                      '[middle]\nlabel = "Middle"\nparent = "top"\n\n'
                      '[bottom]\nlabel = "Bottom"\nlabel_de = "Unten"\n'
                      'parent = "middle"\n'})
        data = pipeline_function("fields_data")(path, "de")
        (field,) = data["compound"]
        self.assertEqual(field["label"], "Kind")
        self.assertEqual(field["values"], {
            "top": {"label": "Oben", "path": ["Oben"], "ancestors": []},
            "middle": {"label": "Middle", "path": ["Oben", "Middle"],
                       "ancestors": ["top"]},
            "bottom": {"label": "Unten",
                       "path": ["Oben", "Middle", "Unten"],
                       "ancestors": ["top", "middle"]}})

    def test_a_value_is_listed_at_every_level(self) -> None:
        """Requirement: Field data for the site (`values` holds every
        value of the vocabulary)."""
        data = pipeline_function("fields_data")(TEST_SETTINGS, "de")
        fields = {f["key"]: f for f in data["compound"]}
        classes = fields["chemical_class"]["values"]
        self.assertEqual(len(classes), 13)
        self.assertEqual(
            classes["aryl-ketones"],
            {"label": "Arylketone",
             "path": ["Carbonylverbindungen", "Ketone", "Arylketone"],
             "ancestors": ["carbonyl-compounds", "ketones"]})
        self.assertEqual(
            classes["anhydrides"]["path"],
            ["Carbonylverbindungen", "Carbons\u00e4urederivate",
             "Anhydride"])
        self.assertEqual(classes["anhydrides"]["ancestors"],
                         ["carbonyl-compounds", "acid-derivatives"])
        self.assertEqual(classes["alcohols"]["path"], ["Alkohole"])
        self.assertEqual(classes["alcohols"]["ancestors"], [])

    def test_the_test_collection_field_data(self) -> None:
        """Scenario: Field data in both languages (the test
        collection)."""
        data = pipeline_function("fields_data")(TEST_SETTINGS, "en")
        self.assertEqual(
            [(f["key"], f["type"], f["column"])
             for f in data["compound"]],
            [("item_number", "text", True), ("short_name", "text", False),
             ("chemical_class", "choice", True), ("stock", "number", False),
             ("in_house", "boolean", False)])
        self.assertEqual(data["compound"][3]["unit"], "g")
        self.assertEqual(
            data["compound"][2]["values"]["aryl-ketones"]["path"],
            ["Carbonyl compounds", "Ketones", "Aryl ketones"])
        self.assertEqual(
            data["compound"][2]["values"]["aryl-ketones"]["ancestors"],
            ["carbonyl-compounds", "ketones"])

    def test_a_vocabulary_listed_out_of_order(self) -> None:
        """Scenario: Depth-first order."""
        path = self.settings(
            'format = 1\n\n[[fields.compound]]\nkey = "chemical_class"\n'
            'type = "choice"\nlabel = "Chemical class"\n'
            'vocabulary = "chemical-classes"\n',
            {"chemical-classes": (
                '[esters]\nlabel = "Esters"\nparent = "carbonyl-compounds"'
                '\n\n[alcohols]\nlabel = "Alcohols"\n\n'
                '[carbonyl-compounds]\nlabel = "Carbonyl compounds"\n\n'
                '[ketones]\nlabel = "Ketones"\n'
                'parent = "carbonyl-compounds"\n\n'
                '[aryl-ketones]\nlabel = "Aryl ketones"\n'
                'parent = "ketones"\n')})
        (field,) = pipeline_function("fields_data")(path, "en")["compound"]
        self.assertEqual(field.get("order"), [
            "alcohols", "carbonyl-compounds", "esters", "ketones",
            "aryl-ketones"])
        values = field["values"]
        self.assertEqual(values["aryl-ketones"].get("ancestors"),
                         ["carbonyl-compounds", "ketones"])
        self.assertEqual(values["esters"].get("ancestors"),
                         ["carbonyl-compounds"])
        self.assertEqual(values["alcohols"].get("ancestors"), [])

    def test_the_order_holds_every_value_once(self) -> None:
        """Requirement: Field data for the site (`order`: the keys of
        every value)."""
        data = pipeline_function("fields_data")(TEST_SETTINGS, "en")
        field = {f["key"]: f for f in data["compound"]}["chemical_class"]
        self.assertEqual(len(field["order"]), len(set(field["order"])))
        self.assertEqual(set(field["order"]), set(field["values"]))
        for key in field["order"]:
            ancestors = field["values"][key]["ancestors"]
            position = field["order"].index(key)
            for ancestor in ancestors:
                self.assertLess(field["order"].index(ancestor), position)
        self.assertEqual(field["order"].index("aryl-ketones"),
                         field["order"].index("ketones") + 1)

    def test_no_settings_file(self) -> None:
        """Scenario: No settings file."""
        fields_data = pipeline_function("fields_data")
        with tempfile.TemporaryDirectory(prefix="no settings ") as tmp:
            missing = Path(tmp) / "orgsyndb.toml"
            for language in ("en", "de"):
                self.assertEqual(fields_data(missing, language),
                                 {"compound": []})

    def test_a_settings_file_that_declares_no_field(self) -> None:
        """Requirement: Field data for the site (declares no field)."""
        path = self.settings("format = 1\n")
        self.assertEqual(pipeline_function("fields_data")(path, "en"),
                         {"compound": []})

    def test_a_broken_declaration_is_a_configuration_error(self) -> None:
        """Requirement: Field data for the site (a rule of the
        declarations)."""
        fields_data = pipeline_function("fields_data")
        error = pipeline().validate.ConfigError
        head = "format = 1\n\n[[fields.compound]]\n"
        cases = {
            "no label": head + 'key = "x"\ntype = "text"\n',
            "built-in key": head + (
                'key = "cas"\ntype = "text"\nlabel = "CAS"\n'),
            "unknown option": head + (
                'key = "x"\ntype = "text"\nlabel = "X"\ntabs = true\n'),
            "a single table": (
                'format = 1\n\n[fields.compound]\nkey = "x"\n'
                'type = "text"\nlabel = "X"\n')}
        for name, text in cases.items():
            with self.subTest(case=name):
                path = self.settings(text)
                with self.assertRaises(error):
                    fields_data(path, "en")

    def test_a_broken_vocabulary_is_a_configuration_error(self) -> None:
        """Requirement: Field data for the site (a rule of the
        vocabularies)."""
        fields_data = pipeline_function("fields_data")
        error = pipeline().validate.ConfigError
        text = ('format = 1\n\n[[fields.compound]]\nkey = "kind"\n'
                'type = "choice"\nlabel = "Kind"\nvocabulary = "kinds"\n')
        cases = {
            "missing": {},
            "no label": {"kinds": "[top]\nlabel_de = 'Oben'\n"},
            "cycle": {"kinds": '[a]\nlabel = "A"\nparent = "a"\n'},
            "empty": {"kinds": ""}}
        for name, vocabularies in cases.items():
            with self.subTest(case=name):
                path = self.settings(text, vocabularies)
                with self.assertRaises(error):
                    fields_data(path, "en")


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
