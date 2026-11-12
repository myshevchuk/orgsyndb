"""The collection half of a manifest: ``pipeline.manifest_data`` and
``tools/orgsyndb manifest`` (build-script "manifest subcommand").

The pure tests call ``manifest_data`` in-process on temporary copies of
the Markdown-only test collection; the program tests run the application
copy's ``tools/orgsyndb`` as the other program tests do. The demo test
exports the demo's Org procedures and so needs Emacs; it also keeps
``webapp/demo/manifest.json``, which the lab application's demo data
and tests apply, from drifting from what the program prints.
"""

import json
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

import pipeline_support as ps
from pipeline_support import (DEMO, REPO, TEST_COLLECTION,
                              keep_registry_inside, make_path, make_sandbox,
                              pipeline, pipeline_function, snapshot)

FIXTURE = REPO / "webapp" / "demo" / "manifest.json"
PROCEDURE_KEYS = {"id", "source", "title", "title_de", "reaction_type",
                  "general", "entries"}
SEQUENCE_KEYS = {"id", "title", "title_de", "target", "steps"}
IDS = [f"OSDB-{number:04d}" for number in range(1, 10)]
FRONT_MATTER = ('+++\nid = "{id}"\ntitle = "{title}"\n'
                'reaction_types = ["hydrolysis"]\n'
                'substrates = ["ethyl-cinnamate"]\n'
                'products = [{{ compound = "cinnamic-acid", '
                'yield_percent = 90 }}]\n+++\n')


def copy_collection(case: unittest.TestCase, source: Path) -> Path:
    """Copy the collection ``source``, without its generated
    directories, to a temporary directory removed on clean-up, its
    registry a file of the copy."""
    base = Path(tempfile.mkdtemp(prefix="orgsyndb manifest "))
    case.addCleanup(shutil.rmtree, base, True)
    root = base / "collection copy"
    shutil.copytree(source, root, symlinks=True,
                    ignore=shutil.ignore_patterns("build", "public", "pdf"))
    keep_registry_inside(source, root)
    return root


def manifest_of(root: Path) -> dict[str, Any]:
    return pipeline_function("manifest_data")(root)


def by_id(items: list[dict[str, Any]], ident: str) -> dict[str, Any]:
    """The table of ``items`` whose ``id`` is ``ident``."""
    (found,) = [item for item in items if item["id"] == ident]
    return found


def site_app(case: unittest.TestCase, locale: str) -> unittest.mock._patch:
    """A patch that gives the application's site the ``locale``."""
    app = Path(tempfile.mkdtemp(prefix="orgsyndb app "))
    case.addCleanup(shutil.rmtree, app, True)
    (app / "site").mkdir()
    (app / "site" / "hugo.toml").write_text(f'locale = "{locale}"\n',
                                            encoding="utf-8")
    return unittest.mock.patch.object(pipeline(), "APP", app)


class ManifestDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = copy_collection(self, TEST_COLLECTION)
        self.data = manifest_of(self.root)

    def test_keys(self) -> None:
        """Requirement: manifest subcommand (the table's keys)."""
        self.assertEqual(set(self.data),
                         {"language", "procedures", "sequences"})
        self.assertEqual(self.data["language"], pipeline().site_language(
            pipeline().APP / "site"))

    def test_it_serializes_as_strict_json(self) -> None:
        """Requirement: manifest subcommand (strict JSON)."""
        text = json.dumps(self.data, allow_nan=False)
        self.assertEqual(json.loads(text), self.data)

    def test_procedures_are_ordered_by_id(self) -> None:
        """Requirement: manifest subcommand (one table per procedure
        ID, ordered by ID)."""
        procedures = self.data["procedures"]
        self.assertEqual([p["id"] for p in procedures], IDS)
        for procedure in procedures:
            with self.subTest(id=procedure["id"]):
                self.assertEqual(set(procedure), PROCEDURE_KEYS)

    def test_a_specific_procedure_has_one_entry(self) -> None:
        """Requirement: manifest subcommand (one entry of the top-level
        substrates and products, in file order)."""
        aspirin = by_id(self.data["procedures"], "OSDB-0002")
        self.assertEqual(aspirin["source"], "md")
        self.assertFalse(aspirin["general"])
        self.assertEqual(aspirin["reaction_type"], "acylation")
        self.assertEqual(aspirin["entries"], [{
            "substrates": ["salicylic-acid", "acetic-anhydride"],
            "products": [{"compound": "acetylsalicylic-acid",
                          "yield_percent": 75}]}])

    def test_a_general_procedure_has_an_entry_per_scope_line(self) -> None:
        """Requirement: manifest subcommand (one entry per element of
        `scope`, in file order)."""
        general = by_id(self.data["procedures"], "OSDB-0009")
        self.assertTrue(general["general"])
        self.assertEqual([e["substrates"] for e in general["entries"]],
                         [["4-acetylbiphenyl"], ["acetophenone"],
                          ["4-bromoacetophenone"]])
        self.assertEqual(general["entries"][0]["products"], [
            {"compound": "1-biphenyl-4-yl-ethanol", "yield_percent": 90}])
        self.assertEqual(
            [e["products"][0]["compound"] for e in general["entries"]],
            ["1-biphenyl-4-yl-ethanol", "1-phenylethanol",
             "1-4-bromophenyl-ethanol"])
        for entry in general["entries"]:
            self.assertEqual(set(entry), {"substrates", "products"})

    def test_a_substrate_order_is_the_files(self) -> None:
        """Requirement: manifest subcommand (`substrates`, a list of
        keys in file order)."""
        path = (self.root / "md" / "procedures"
                / "OSDB-0002-aspirin.de.md")
        path.write_text(path.read_text(encoding="utf-8").replace(
            'substrates = ["salicylic-acid", "acetic-anhydride"]',
            'substrates = ["acetic-anhydride", "salicylic-acid"]'),
            encoding="utf-8")
        data = manifest_of(self.root)
        self.assertEqual(
            by_id(data["procedures"], "OSDB-0002")["entries"][0][
                "substrates"], ["acetic-anhydride", "salicylic-acid"])

    def test_the_site_language_picks_the_title(self) -> None:
        """Scenario: Titles in both languages (a German site)."""
        with site_app(self, "de"):
            data = manifest_of(self.root)
        self.assertEqual(data["language"], "de")
        aspirin = by_id(data["procedures"], "OSDB-0002")
        self.assertEqual(aspirin["title"], "Aspirin (Acetylsalicylsäure)")
        self.assertEqual(aspirin["title_de"], "Aspirin (Acetylsalicylsäure)")

    def test_an_english_site_publishes_the_other_variant(self) -> None:
        """Requirement: manifest subcommand (`title`, that variant's
        title, `title_de`, the title of the `.de` file)."""
        with site_app(self, "en"):
            data = manifest_of(self.root)
        self.assertEqual(data["language"], "en")
        aspirin = by_id(data["procedures"], "OSDB-0002")
        self.assertEqual(aspirin["title"], "Aspirin (acetylsalicylic acid)")
        self.assertEqual(aspirin["title_de"], "Aspirin (Acetylsalicylsäure)")
        sequence = by_id(data["sequences"], "SEQ-0002")
        self.assertEqual(sequence["title"],
                         "1-(Biphenyl-4-yl)ethanol from 4′-bromoacetophenone")
        self.assertEqual(
            sequence["title_de"],
            "1-(Biphenyl-4-yl)ethanol aus 4′-Bromacetophenon")

    def test_no_german_file_gives_no_german_title(self) -> None:
        """Requirement: manifest subcommand (`title_de`, or `null` when
        the ID has no file tagged `de`)."""
        (self.root / "md" / "procedures"
         / "OSDB-0003-isopentyl-acetate.de.md").unlink()
        (self.root / "md" / "sequences"
         / "SEQ-0001-aspirin-from-wintergreen.de.md").unlink()
        with site_app(self, "en"):
            data = manifest_of(self.root)
        found = by_id(data["procedures"], "OSDB-0003")
        self.assertEqual(found["title"], "Isopentyl acetate")
        self.assertIsNone(found["title_de"])
        self.assertIsNone(by_id(data["sequences"], "SEQ-0001")["title_de"])

    def test_sequences(self) -> None:
        """Requirement: manifest subcommand (`sequences`: one table per
        ID, ordered, with `target` and `steps`)."""
        sequences = self.data["sequences"]
        self.assertEqual([s["id"] for s in sequences],
                         ["SEQ-0001", "SEQ-0002"])
        for sequence in sequences:
            with self.subTest(id=sequence["id"]):
                self.assertEqual(set(sequence), SEQUENCE_KEYS)
        first, second = sequences
        self.assertEqual(first["target"], "acetylsalicylic-acid")
        self.assertEqual(first["steps"], [
            {"procedure": "OSDB-0001", "entry": None},
            {"procedure": "OSDB-0002", "entry": None}])
        self.assertEqual(second["target"], "1-biphenyl-4-yl-ethanol")
        self.assertEqual(second["steps"], [
            {"procedure": "OSDB-0004", "entry": None},
            {"procedure": "OSDB-0009", "entry": 1}])

    def edit_files(self, directory: str, pattern: str, old: str,
                   new: str) -> None:
        """Replace ``old`` by ``new`` in each file of ``md/<directory>/``
        that ``pattern`` matches, which must hold ``old`` once."""
        paths = sorted((self.root / "md" / directory).glob(pattern))
        self.assertTrue(paths, pattern)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(old), 1, f"{path.name}: {old!r}")
            path.write_text(text.replace(old, new), encoding="utf-8")

    def second_step_of_seq_0002(self) -> dict[str, Any]:
        steps = by_id(manifest_of(self.root)["sequences"],
                      "SEQ-0002")["steps"]
        self.assertEqual(steps[0], {"procedure": "OSDB-0004",
                                    "entry": None})
        return steps[1]

    def test_a_step_gives_the_entry_its_product_names(self) -> None:
        """Requirement: manifest subcommand (`steps`, tables of
        `procedure` and `entry`, the number of the entry the step
        names)."""
        for sequence in self.data["sequences"]:
            for step in sequence["steps"]:
                self.assertEqual(set(step), {"procedure", "entry"})
        self.assertEqual(self.second_step_of_seq_0002(),
                         {"procedure": "OSDB-0009", "entry": 1})

    def test_a_reordered_scope_table_gives_the_new_number(self) -> None:
        """Scenario: A reordered scope table (the manifest's step gives
        entry 3)."""
        entry_1 = ('  { substrates = ["4-acetylbiphenyl"], time = "30 min", '
                   'products = [{ compound = "1-biphenyl-4-yl-ethanol", '
                   "yield_percent = 90 }] },\n")
        self.edit_files("procedures", "OSDB-0009-*.md", entry_1, "")
        self.edit_files("procedures", "OSDB-0009-*.md", "]\nhazards",
                        entry_1 + "]\nhazards")
        data = manifest_of(self.root)
        general = by_id(data["procedures"], "OSDB-0009")
        self.assertEqual(
            [e["products"][0]["compound"] for e in general["entries"]],
            ["1-phenylethanol", "1-4-bromophenyl-ethanol",
             "1-biphenyl-4-yl-ethanol"])
        self.assertEqual(self.second_step_of_seq_0002(),
                         {"procedure": "OSDB-0009", "entry": 3})

    def test_a_step_named_by_its_signature_gives_its_entry(self) -> None:
        """Requirement: manifest subcommand (`entry`, the number of the
        entry the step names, by its substrates and products)."""
        self.edit_files(
            "sequences", "SEQ-0002-*.md",
            'product = "1-biphenyl-4-yl-ethanol"',
            'substrates = ["4-acetylbiphenyl"], '
            'products = ["1-biphenyl-4-yl-ethanol"]')
        self.assertEqual(self.second_step_of_seq_0002(),
                         {"procedure": "OSDB-0009", "entry": 1})

    def test_a_step_of_the_second_entry(self) -> None:
        """Requirement: manifest subcommand (`entry`, the number of the
        entry the step names)."""
        self.edit_files("sequences", "SEQ-0002-*.md",
                        'product = "1-biphenyl-4-yl-ethanol"',
                        'product = "1-phenylethanol"')
        self.assertEqual(self.second_step_of_seq_0002(),
                         {"procedure": "OSDB-0009", "entry": 2})

    def test_the_export_holds_the_org_procedures(self) -> None:
        """Requirement: manifest subcommand (the files of
        `build/export/`: `source` is `org` for an export)."""
        export = self.root / "build" / "export"
        export.mkdir(parents=True)
        (export / "OSDB-0050-from-org.md").write_text(
            FRONT_MATTER.format(id="OSDB-0050", title="From Org"),
            encoding="utf-8")
        data = manifest_of(self.root)
        self.assertEqual([p["id"] for p in data["procedures"]],
                         [*IDS, "OSDB-0050"])
        found = by_id(data["procedures"], "OSDB-0050")
        self.assertEqual((found["source"], found["title"]),
                         ("org", "From Org"))
        self.assertEqual(by_id(data["procedures"], "OSDB-0002")["source"],
                         "md")

    def test_the_source_is_the_published_variant(self) -> None:
        """Requirement: manifest subcommand (`source`: `org` when the
        variant the site publishes is an export)."""
        export = self.root / "build" / "export"
        export.mkdir(parents=True)
        (export / "OSDB-0050-from-org.de.md").write_text(
            FRONT_MATTER.format(id="OSDB-0050", title="Aus Org"),
            encoding="utf-8")
        (self.root / "md" / "procedures" / "OSDB-0050-from-org.md"
         ).write_text(FRONT_MATTER.format(id="OSDB-0050", title="Plain"),
                      encoding="utf-8")
        with site_app(self, "en"):
            published = by_id(manifest_of(self.root)["procedures"],
                              "OSDB-0050")
        self.assertEqual((published["source"], published["title"],
                          published["title_de"]), ("md", "Plain", "Aus Org"))
        with site_app(self, "de"):
            published = by_id(manifest_of(self.root)["procedures"],
                              "OSDB-0050")
        self.assertEqual((published["source"], published["title"]),
                         ("org", "Aus Org"))

    def test_files_the_validator_does_not_name_are_left_out(self) -> None:
        """Requirement: manifest subcommand (only files whose names the
        file-name patterns accept)."""
        procedures = self.root / "md" / "procedures"
        (procedures / "notes.md").write_text("no front matter\n")
        (procedures / "OSDB-0099-Not A Slug.md").write_text("x\n")
        (procedures / "osdb-0098-lower.md").write_text("x\n")
        sequences = self.root / "md" / "sequences"
        (sequences / "SEQ-0099-Not A Slug.md").write_text("x\n")
        data = manifest_of(self.root)
        self.assertEqual([p["id"] for p in data["procedures"]], IDS)
        self.assertEqual([s["id"] for s in data["sequences"]],
                         ["SEQ-0001", "SEQ-0002"])

    def test_no_registry_is_read_and_no_value_checked(self) -> None:
        """Requirement: manifest subcommand (it reads no registry and
        checks no value)."""
        (self.root / "registry.json").unlink()
        path = (self.root / "md" / "procedures"
                / "OSDB-0002-aspirin.de.md")
        path.write_text(path.read_text(encoding="utf-8").replace(
            "acylation", "no-such-type").replace(
            "acetylsalicylic-acid", "no-such-substance"),
            encoding="utf-8")
        found = by_id(manifest_of(self.root)["procedures"], "OSDB-0002")
        self.assertEqual(found["reaction_type"], "no-such-type")
        self.assertEqual(found["entries"][0]["products"][0]["compound"],
                         "no-such-substance")

    def test_nothing_is_written(self) -> None:
        """Requirement: manifest subcommand (it writes no file)."""
        before = snapshot(self.root)
        manifest_of(self.root)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "build").exists())


class ManifestSubcommandTests(unittest.TestCase):
    def test_markdown_only(self) -> None:
        """Scenario: Markdown only."""
        sandbox = make_sandbox(self)
        path = make_path(self, ("python3",))
        result = sandbox.build("manifest",
                               env=sandbox.env(PATH=str(path.directory)))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual([p["id"] for p in data["procedures"]], IDS)
        self.assertEqual([s["id"] for s in data["sequences"]],
                         ["SEQ-0001", "SEQ-0002"])
        self.assertEqual(path.sudo_calls(), [])
        self.assertFalse((sandbox.root / "build").exists())

    def test_the_output_is_one_line_of_json(self) -> None:
        """Requirement: manifest subcommand (one line of strict JSON,
        non-ASCII characters as themselves, no step line, no file)."""
        sandbox = make_sandbox(self)
        before = snapshot(sandbox.root)
        result = sandbox.build("manifest")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("\n"), 1)
        self.assertTrue(result.stdout.endswith("\n"))
        self.assertNotIn("==>", result.stdout)
        self.assertNotIn("NaN", result.stdout)
        self.assertNotIn("\\u", result.stdout)
        self.assertIn("ä", result.stdout)
        self.assertEqual(snapshot(sandbox.root), before)
        with unittest.mock.patch.object(
                pipeline(), "APP", sandbox.app):
            self.assertEqual(json.loads(result.stdout),
                             manifest_of(sandbox.root))

    def test_the_program_is_found_from_a_subdirectory(self) -> None:
        """Requirement: Entry point conventions (the subcommand is
        listed, and finds its collection like the others)."""
        sandbox = make_sandbox(self)
        result = sandbox.program(
            "manifest", cwd=sandbox.root / "md" / "procedures")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            len(json.loads(result.stdout)["procedures"]), 9)

    def test_org_sources_need_the_export(self) -> None:
        """Scenario: Org sources need the export."""
        sandbox = make_sandbox(self, collection=DEMO)
        self.assertFalse((sandbox.root / "build").exists())
        result = sandbox.build("manifest")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.assertIn("build/export/", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_a_file_without_front_matter_is_named(self) -> None:
        """Requirement: manifest subcommand (a procedure or sequence
        file with no front matter it can read fails, naming the file)."""
        for directory, name in (("procedures", "OSDB-0050-broken.md"),
                                ("sequences", "SEQ-0050-broken.md")):
            with self.subTest(directory=directory):
                sandbox = make_sandbox(self)
                (sandbox.root / "md" / directory / name).write_text(
                    "no front matter here\n", encoding="utf-8")
                result = sandbox.build("manifest")
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                                result.stderr)
                self.assertIn(name, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_arguments_are_refused(self) -> None:
        """Scenario: Arguments are refused."""
        sandbox = make_sandbox(self)
        result = sandbox.build("manifest", "all")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("usage", result.stderr.lower())
        self.assertNotIn("unknown subcommand", result.stderr)
        self.assertEqual(result.stdout, "")


class DemoManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ps.require_exporter()

    def test_the_manifest_of_the_demo(self) -> None:
        """Scenario: Manifest of the demo (and `webapp/demo/manifest.json`,
        which the lab application applies)."""
        sandbox = make_sandbox(self, collection=DEMO)
        exported = sandbox.build("export")
        self.assertEqual(exported.returncode, 0, exported.stderr)
        result = sandbox.build("manifest")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("\n"), 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["language"], "de")
        procedures = data["procedures"]
        self.assertEqual([p["id"] for p in procedures], IDS)
        self.assertEqual(by_id(procedures, "OSDB-0001")["source"], "org")
        self.assertEqual(by_id(procedures, "OSDB-0002")["source"], "md")
        general = by_id(procedures, "OSDB-0009")
        self.assertEqual(len(general["entries"]), 3)
        self.assertEqual(general["entries"][0], {
            "substrates": ["4-acetylbiphenyl"],
            "products": [{"compound": "1-biphenyl-4-yl-ethanol",
                          "yield_percent": 90}]})
        self.assertEqual(by_id(data["sequences"], "SEQ-0002")["steps"], [
            {"procedure": "OSDB-0004", "entry": None},
            {"procedure": "OSDB-0009", "entry": 1}])
        aspirin = by_id(procedures, "OSDB-0002")
        german = (DEMO / "md" / "procedures" / "OSDB-0002-aspirin.de.md")
        title = ps.front_matter(german.read_text(encoding="utf-8"))["title"]
        self.assertEqual((aspirin["title"], aspirin["title_de"]),
                         (title, title))
        self.assertEqual(data, json.loads(FIXTURE.read_text(
            encoding="utf-8")),
            "webapp/demo/manifest.json has drifted from "
            "the manifest of the demo")


if __name__ == "__main__":
    unittest.main()
