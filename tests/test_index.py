"""The collection index: ``pipeline.index_data`` (collection-index
"Index data") and ``tools/orgsyndb index`` (build-script "index
subcommand").

The pure tests call ``index_data`` in-process on temporary copies of the
test collection and the demo; the program tests run the application
copy's ``tools/orgsyndb`` as the other program tests do.
"""

import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import Any

from pipeline_support import (DEMO, TEST_COLLECTION, make_path,
                              make_sandbox, pipeline, pipeline_function,
                              snapshot)


def copy_collection(case: unittest.TestCase, source: Path) -> Path:
    """Copy the collection ``source``, without its generated directories,
    to a temporary directory removed on clean-up."""
    base = Path(tempfile.mkdtemp(prefix="orgsyndb index "))
    case.addCleanup(shutil.rmtree, base, True)
    root = base / "collection copy"
    shutil.copytree(source, root, symlinks=True,
                    ignore=shutil.ignore_patterns("build", "public", "pdf"))
    return root


def index_of(root: Path) -> dict[str, Any]:
    return pipeline_function("index_data")(root)


def entry(entries: list[dict[str, Any]], path: str) -> dict[str, Any]:
    """The entry of ``entries`` whose ``path`` is ``path``."""
    found = [item for item in entries if item["path"] == path]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} entries have the path {path}")
    return found[0]


class IndexOfTheTestCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = copy_collection(self, TEST_COLLECTION)
        self.index = index_of(self.root)

    def test_keys(self) -> None:
        """Index data: the index has these keys and nothing else."""
        self.assertEqual(set(self.index),
                         {"site_language", "schema", "fields",
                          "vocabularies", "compounds", "procedures",
                          "sequences"})
        self.assertEqual(self.index["site_language"],
                         pipeline().site_language(
                             pipeline().APP / "site"))

    def test_index_of_the_test_collection(self) -> None:
        """Scenario: Index of the test collection."""
        compounds = self.index["compounds"]
        keys = [item["key"] for item in compounds]
        self.assertEqual(len(keys), 20)
        self.assertEqual(keys, sorted(keys))
        anhydride = entry(compounds, "compounds/acetic-anhydride.toml")
        self.assertEqual(anhydride["key"], "acetic-anhydride")
        self.assertEqual(anhydride["data"]["name_de"], "Essigsäureanhydrid")

        procedures = self.index["procedures"]
        self.assertEqual(len(procedures), 18)
        self.assertTrue(all(item["format"] == "md" for item in procedures))
        german = entry(procedures, "md/procedures/OSDB-0002-aspirin.de.md")
        self.assertEqual((german["id"], german["language"], german["format"]),
                         ("OSDB-0002", "de", "md"))
        plain = entry(procedures, "md/procedures/OSDB-0002-aspirin.md")
        self.assertIsNone(plain["language"])
        self.assertEqual(plain["front_matter"]["status"], "draft")
        self.assertEqual(plain["front_matter"]["date"],
                         "2026-10-19T23:46:11+02:00")

        self.assertEqual(len(self.index["sequences"]), 4)

        declared = self.index["fields"]["procedure"]
        self.assertEqual([item["key"] for item in declared],
                         ["notebook", "project", "working_time",
                          "inert_atmosphere"])
        project = next(item for item in declared if item["key"] == "project")
        self.assertEqual(project["vocabulary"], "projects")
        self.assertFalse(any("column" in item for item in declared))

        self.assertEqual(set(self.index["vocabularies"]),
                         {"chemical-classes", "inventory-groups", "projects",
                          "reaction-types"})

    def test_entries_are_ordered_and_complete(self) -> None:
        """Index data: procedures and sequences ordered by ID, then path,
        each with the keys of its kind."""
        for name in ("procedures", "sequences"):
            entries = self.index[name]
            with self.subTest(name=name):
                order = [(item["id"], item["path"]) for item in entries]
                self.assertEqual(order, sorted(order))
        for item in self.index["procedures"]:
            self.assertEqual(set(item), {"id", "language", "path", "format",
                                         "front_matter"})
        for item in self.index["sequences"]:
            self.assertEqual(set(item), {"id", "language", "path",
                                         "front_matter"})
        sequence = entry(self.index["sequences"],
                         "md/sequences/SEQ-0001-aspirin-from-wintergreen.md")
        self.assertEqual(sequence["id"], "SEQ-0001")
        self.assertEqual(sequence["front_matter"]["target"],
                         "acetylsalicylic-acid")
        for item in self.index["compounds"]:
            self.assertEqual(set(item), {"key", "path", "data"})

    def test_declarations(self) -> None:
        """Index data: declarations carry their type's options, defaults
        applied, and a procedure declaration none of the withheld ones."""
        compound = {item["key"]: item
                    for item in self.index["fields"]["compound"]}
        self.assertEqual(list(compound),
                         ["item_number", "short_name", "chemical_class",
                          "stock", "in_house", "group"])
        self.assertEqual(compound["item_number"], {
            "key": "item_number", "type": "text", "label": "Item no.",
            "label_de": "Artikelnr.", "required": True, "column": True,
            "pattern": r"CH-\d{4}", "unique": True, "search": True,
            "beside": True})
        self.assertEqual(compound["stock"], {
            "key": "stock", "type": "number", "label": "Stock",
            "label_de": "Bestand", "required": False, "column": False,
            "min": 0, "max": None, "unit": "g", "unique": False,
            "beside": False})
        self.assertEqual(compound["in_house"], {
            "key": "in_house", "type": "boolean", "label": "Made in house",
            "label_de": "Eigene Herstellung", "required": False,
            "column": False, "facet": True})
        self.assertEqual(compound["group"], {
            "key": "group", "type": "choice", "label": "Group",
            "label_de": "Gruppe", "required": True, "column": False,
            "vocabulary": "inventory-groups", "multiple": False,
            "facet": True, "tabs": True})
        procedure = {item["key"]: item
                     for item in self.index["fields"]["procedure"]}
        self.assertEqual(procedure["notebook"], {
            "key": "notebook", "type": "text", "label": "Lab notebook",
            "label_de": "Laborjournal", "required": False,
            "pattern": r"[A-Z]{2}-\d+/\d+", "unique": True})
        self.assertEqual(procedure["project"], {
            "key": "project", "type": "choice", "label": "Project",
            "label_de": "Projekt", "required": False,
            "vocabulary": "projects", "multiple": False, "facet": True})
        self.assertEqual(procedure["working_time"], {
            "key": "working_time", "type": "number", "label": "Working time",
            "label_de": "Arbeitszeit", "required": False, "min": 0,
            "max": None, "unit": "h", "unique": False})

    def test_vocabularies(self) -> None:
        """Index data: each vocabulary maps its values, in file order, to
        their label, label_de and parent."""
        projects = self.index["vocabularies"]["projects"]
        source = tomllib.loads(
            (self.root / "vocabularies" / "projects.toml").read_text())
        self.assertEqual(list(projects), list(source))
        self.assertEqual(projects["first-year-practical"], {
            "label": "First-year practical", "label_de": "Grundpraktikum",
            "parent": "teaching"})
        self.assertIsNone(projects["teaching"]["parent"])
        reaction_types = self.index["vocabularies"]["reaction-types"]
        self.assertIn("acylation", reaction_types)
        self.assertEqual(set(reaction_types["acylation"]),
                         {"label", "label_de", "parent"})

    def test_strict_json(self) -> None:
        """Index data: the table serializes to strict JSON."""
        text = json.dumps(self.index, allow_nan=False, ensure_ascii=False)
        self.assertEqual(json.loads(text), self.index)


class SchemaTests(unittest.TestCase):
    def test_schema_keys(self) -> None:
        """Scenario: Schema keys."""
        schema = index_of(copy_collection(self, TEST_COLLECTION))["schema"]
        validate = pipeline().validate
        procedure = schema["procedure"]
        self.assertEqual(set(schema), {"procedure", "compound", "sequence"})
        self.assertEqual(set(procedure),
                         {"required", "optional", "entry", "product",
                          "statuses", "languages", "shared", "sections"})
        self.assertEqual(procedure["required"], list(validate.REQUIRED_KEYS))
        self.assertEqual(procedure["optional"], list(validate.OPTIONAL_KEYS))
        self.assertEqual(procedure["entry"],
                         ["substrates", "products", "scale", "time",
                          "temperature", "note"])
        self.assertEqual(procedure["entry"],
                         list(validate.SCOPE_ENTRY_KEYS))
        self.assertEqual(procedure["product"], ["compound", "yield_percent"])
        self.assertEqual(procedure["product"], list(validate.PRODUCT_KEYS))
        self.assertEqual(procedure["statuses"], list(validate.STATUSES))
        self.assertEqual(procedure["languages"], list(validate.LANGUAGES))
        self.assertEqual(procedure["shared"], list(validate.SHARED_FIELDS))
        self.assertEqual(procedure["sections"],
                         {language: list(names) for language, names
                          in validate.SECTIONS_BY_LANGUAGE.items()})
        self.assertEqual(schema["compound"], {
            "required": list(validate.COMPOUND_REQUIRED_KEYS),
            "optional": list(validate.COMPOUND_OPTIONAL_KEYS)})
        self.assertEqual(schema["sequence"], {
            "keys": list(validate.SEQUENCE_KEYS),
            "step": list(validate.STEP_KEYS)})

        self.assertEqual(procedure["statuses"],
                         ["draft", "checked", "retired"])
        self.assertEqual(procedure["sections"]["de"][0], "Zusammenfassung")
        self.assertEqual(len(procedure["sections"]["de"]), 8)
        self.assertEqual(schema["compound"]["required"],
                         ["name", "formula", "mw", "smiles"])

    def test_validator_uses_the_entry_and_product_keys(self) -> None:
        """Index data: the scope-entry and product keys are the ones the
        validator accepts; any other key is an unknown field."""
        validate = pipeline().validate
        product = {"compound": "acetone", "yield_percent": 50}
        scope = [{"substrates": ["ethanol"], "products": [product],
                  "scale": "5 mmol", "time": "2 h", "temperature": 25,
                  "note": "x", "colour": "red"}]
        problems = validate.check_scope(scope,
                                        frozenset({"acetone", "ethanol"}))
        self.assertEqual([(p.field, p.message) for p in problems],
                         [("scope[1].colour", "unknown field")])
        problems = validate.check_products([dict(product, extra=1)],
                                           frozenset({"acetone"}))
        self.assertEqual([(p.field, p.message) for p in problems],
                         [("products[1].extra", "unknown field")])


class OrgProceduresTests(unittest.TestCase):
    def test_org_procedures_by_name(self) -> None:
        """Scenario: Org procedures by name."""
        index = index_of(copy_collection(self, DEMO))
        german = entry(index["procedures"],
                       "org/procedures/OSDB-0007-ethyl-cinnamate.de.org")
        self.assertEqual(german, {
            "id": "OSDB-0007", "language": "de",
            "path": "org/procedures/OSDB-0007-ethyl-cinnamate.de.org",
            "format": "org", "front_matter": None})
        org = [item for item in index["procedures"]
               if item["format"] == "org"]
        self.assertEqual(len(org), 8)
        self.assertFalse(any("error" in item for item in org))


class BrokenContentTests(unittest.TestCase):
    def test_broken_content_files_are_listed(self) -> None:
        """Scenario: Broken content files are listed."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "compounds" / "broken.toml").write_text("name = \n")
        procedures = root / "md" / "procedures"
        (procedures / "OSDB-0990-broken.md").write_text("No front matter.\n")
        (procedures / "notes.txt").write_text("notes\n")
        (procedures / "OSDB-12-short.md").write_text("+++\n+++\n")
        index = index_of(root)

        broken = entry(index["compounds"], "compounds/broken.toml")
        self.assertIsNone(broken["data"])
        self.assertIn("TOML", broken["error"])
        others = [item for item in index["compounds"]
                  if item["key"] != "broken"]
        self.assertEqual(len(others), 20)
        self.assertTrue(all(isinstance(item["data"], dict)
                            and "error" not in item for item in others))

        unparsed = entry(index["procedures"],
                         "md/procedures/OSDB-0990-broken.md")
        self.assertIsNone(unparsed["front_matter"])
        self.assertIsInstance(unparsed["error"], str)
        self.assertTrue(unparsed["error"])
        paths = [item["path"] for item in index["procedures"]]
        self.assertNotIn("md/procedures/notes.txt", paths)
        self.assertNotIn("md/procedures/OSDB-12-short.md", paths)

    def test_entries_left_out(self) -> None:
        """Index data: dotfiles, subdirectories, names the patterns do
        not accept and other suffixes are left out without a report."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "compounds" / ".hidden.toml").write_text('name = "x"\n')
        (root / "compounds" / "Upper.toml").write_text('name = "x"\n')
        (root / "compounds" / "notes.md").write_text("x\n")
        (root / "compounds" / "nested").mkdir()
        (root / "md" / "procedures" / "nested.md").mkdir()
        (root / "md" / "sequences" / "OSDB-0001-x.md").write_text("+++\n+++\n")
        index = index_of(root)
        self.assertEqual(len(index["compounds"]), 20)
        self.assertEqual(len(index["procedures"]), 18)
        self.assertEqual(len(index["sequences"]), 4)

    def test_non_finite_numbers(self) -> None:
        """Scenario: Non-finite numbers."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "compounds" / "odd.toml").write_text(
            'name = "Odd"\nformula = "C"\nmw = nan\nsmiles = "C"\n'
            "limits = [inf, -inf, 1.5]\n")
        index = index_of(root)
        odd = entry(index["compounds"], "compounds/odd.toml")
        self.assertIsNone(odd["data"]["mw"])
        self.assertEqual(odd["data"]["limits"], [None, None, 1.5])
        json.dumps(index, allow_nan=False)

    def test_dates_and_times(self) -> None:
        """Index data: TOML dates and times appear as ISO 8601 text."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "compounds" / "dated.toml").write_text(
            'name = "Dated"\nformula = "C"\nmw = 12.0\nsmiles = "C"\n'
            "made = 2026-01-15\nat = 09:30:00\nlocal = 2026-01-15T09:30:00\n"
            "nested = [{ when = 2026-01-15T09:30:00+01:00 }]\n")
        data = entry(index_of(root)["compounds"],
                     "compounds/dated.toml")["data"]
        self.assertEqual((data["made"], data["at"], data["local"]),
                         ("2026-01-15", "09:30:00", "2026-01-15T09:30:00"))
        self.assertEqual(data["nested"],
                         [{"when": "2026-01-15T09:30:00+01:00"}])


class EmptyAndBrokenCollectionTests(unittest.TestCase):
    def test_empty_collection(self) -> None:
        """Scenario: Empty collection."""
        root = Path(tempfile.mkdtemp(prefix="orgsyndb index "))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "orgsyndb.toml").write_text("format = 1\n")
        index = index_of(root)
        self.assertEqual((index["compounds"], index["procedures"],
                          index["sequences"]), ([], [], []))
        self.assertEqual(index["fields"], {"compound": [], "procedure": []})
        self.assertEqual(index["vocabularies"], {})

    def test_broken_declaration(self) -> None:
        """Scenario: Broken declaration."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "vocabularies" / "projects.toml").unlink()
        with self.assertRaises(pipeline().validate.ConfigError) as caught:
            index_of(root)
        self.assertIn("projects", str(caught.exception))

    def test_broken_reaction_types(self) -> None:
        """Index data: the reaction types are read strictly."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "vocabularies" / "reaction-types.toml").write_text(
            "[acylation]\n")
        with self.assertRaises(pipeline().validate.ConfigError) as caught:
            index_of(root)
        self.assertIn("reaction-types.toml", str(caught.exception))

    def test_nothing_written(self) -> None:
        """Scenario: Nothing written."""
        root = copy_collection(self, DEMO)
        before = snapshot(root)
        index_of(root)
        self.assertFalse((root / "build").exists())
        self.assertEqual(snapshot(root), before)


class IndexSubcommandTests(unittest.TestCase):
    def test_index_of_the_demo(self) -> None:
        """Scenario: Index of the demo."""
        sandbox = make_sandbox(self, collection=DEMO)
        result = sandbox.build("index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("\n"), 1)
        self.assertTrue(result.stdout.endswith("\n"))
        self.assertNotIn("==>", result.stdout)
        self.assertNotIn("NaN", result.stdout)
        self.assertNotIn("\\u", result.stdout)
        self.assertIn("ä", result.stdout)
        self.assertEqual(json.loads(result.stdout), index_of(sandbox.root))
        self.assertFalse((sandbox.root / "build").exists())

    def test_no_external_tool(self) -> None:
        """Scenario: No external tool."""
        sandbox = make_sandbox(self, collection=DEMO)
        path = make_path(self, ("python3",))
        result = sandbox.build("index",
                               env=sandbox.env(PATH=str(path.directory)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.sudo_calls(), [])

    def test_arguments_are_refused(self) -> None:
        """Scenario: Arguments are refused."""
        sandbox = make_sandbox(self)
        result = sandbox.build("index", "compounds")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("usage", result.stderr.lower())

    def test_configuration_error(self) -> None:
        """Scenario: Configuration error."""
        sandbox = make_sandbox(self)
        (sandbox.root / "vocabularies" / "projects.toml").unlink()
        result = sandbox.build("index")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.assertIn("projects", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_found_from_a_subdirectory(self) -> None:
        """collection "Choosing the collection": index finds the
        collection above the working directory."""
        sandbox = make_sandbox(self)
        result = sandbox.program(
            "index", cwd=sandbox.root / "md" / "procedures")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["compounds"]), 20)


if __name__ == "__main__":
    unittest.main()
