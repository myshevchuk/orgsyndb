"""The collection index: ``pipeline.index_data`` (collection-index
"Index data") and ``tools/orgsyndb index`` (build-script "index
subcommand").

The pure tests call ``index_data`` in-process on temporary copies of the
test collection and the demo; the program tests run the application
copy's ``tools/orgsyndb`` as the other program tests do.
"""

import json
import os
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

from pipeline_support import (DEMO, TEST_COLLECTION, closed_address,
                              compounds_of, keep_registry_inside, make_path,
                              make_sandbox, name_registry, pipeline,
                              pipeline_function, serve_snapshot, snapshot,
                              snapshot_digest)
from support import load_snapshot


def copy_collection(case: unittest.TestCase, source: Path) -> Path:
    """Copy the collection ``source``, without its generated directories,
    to a temporary directory removed on clean-up, its registry a file of
    the copy."""
    base = Path(tempfile.mkdtemp(prefix="orgsyndb index "))
    case.addCleanup(shutil.rmtree, base, True)
    root = base / "collection copy"
    shutil.copytree(source, root, symlinks=True,
                    ignore=shutil.ignore_patterns("build", "public", "pdf"))
    keep_registry_inside(source, root)
    return root


def index_of(root: Path) -> dict[str, Any]:
    return pipeline_function("index_data")(root)


def entry(entries: list[dict[str, Any]], path: str) -> dict[str, Any]:
    """The entry of ``entries`` whose ``path`` is ``path``."""
    found = [item for item in entries if item["path"] == path]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} entries have the path {path}")
    return found[0]


def compound(entries: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """The entry of ``entries`` whose ``key`` is ``key``."""
    (found,) = [item for item in entries if item["key"] == key]
    return found


class IndexOfTheTestCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = copy_collection(self, TEST_COLLECTION)
        self.index = index_of(self.root)

    def test_keys(self) -> None:
        """Index data: the index has these keys and nothing else."""
        self.assertEqual(set(self.index),
                         {"site_language", "schema", "registry", "fields",
                          "vocabularies", "compounds", "procedures",
                          "sequences"})
        self.assertEqual(self.index["site_language"],
                         pipeline().site_language(
                             pipeline().APP / "site"))

    def test_index_of_the_test_collection(self) -> None:
        """Scenario: Index of the test collection."""
        compounds = self.index["compounds"]
        keys = [item["key"] for item in compounds]
        self.assertEqual(len(keys), 21)
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(
            keys, [s["key"] for s in load_snapshot(
                TEST_COLLECTION / "registry.json")["substances"]])
        anhydride = compound(compounds, "acetic-anhydride")
        self.assertEqual(anhydride["data"]["name_de"], "Essigsäureanhydrid")
        self.assertIsNone(anhydride["url"])
        self.assertEqual(self.index["registry"]["source"], "registry.json")

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
        self.assertEqual(
            [item["key"] for item in self.index["fields"]["compound"]],
            ["article_number", "short_name", "chemical_class", "group"])

        self.assertEqual(set(self.index["vocabularies"]),
                         {"chemical-classes", "inventory-groups", "projects",
                          "reaction-types"})

    def test_registry(self) -> None:
        """Index data: `registry` gives the source and the digest."""
        self.assertEqual(
            self.index["registry"],
            {"source": "registry.json",
             "digest": load_snapshot(TEST_COLLECTION / "registry.json")[
                 "digest"]})

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

    def test_compounds_hold_the_staged_data(self) -> None:
        """Index data: each substance has `key`, `data` as the build
        stages it, and `url`."""
        table = load_snapshot(self.root / "registry.json")
        expected = compounds_of(table, self.root / "static")
        self.assertEqual(
            {item["key"]: item["data"] for item in self.index["compounds"]},
            expected)
        for item in self.index["compounds"]:
            self.assertEqual(set(item), {"key", "data", "url"})
            self.assertIsNone(item["url"])
        self.assertEqual(
            compound(self.index["compounds"], "isopentyl-acetate")[
                "data"]["structure_image"],
            "structures/isopentyl-acetate.svg")
        self.assertEqual(
            compound(self.index["compounds"], "acetylsalicylic-acid")[
                "data"]["article_number"], "CH-0010")
        self.assertNotIn("structure_image", compound(
            self.index["compounds"], "salicylic-acid")["data"])

    def test_a_substance_without_a_value_leaves_it_out(self) -> None:
        """Index data: the data leaves out a value the substance
        lacks."""
        data = compound(self.index["compounds"], "new-compound-7")["data"]
        for key in ("formula", "mw", "smiles", "cas", "short_name"):
            self.assertNotIn(key, data)
        self.assertEqual(data["article_number"], "NV-0007")

    def test_declarations(self) -> None:
        """Index data: the registry fields in their order, with the
        options of their type; procedure declarations with theirs,
        defaults applied."""
        compound_fields = {item["key"]: item
                           for item in self.index["fields"]["compound"]}
        self.assertEqual(list(compound_fields),
                         ["article_number", "short_name", "chemical_class",
                          "group"])
        self.assertEqual(compound_fields["article_number"], {
            "key": "article_number", "type": "text", "label": "Article no.",
            "label_de": "Artikelnr.", "column": True, "search": True,
            "beside": True})
        self.assertEqual(compound_fields["short_name"], {
            "key": "short_name", "type": "text", "label": "Short name",
            "label_de": "Kurzname", "column": False, "search": True,
            "beside": True})
        self.assertEqual(compound_fields["chemical_class"], {
            "key": "chemical_class", "type": "choice",
            "label": "Chemical class", "label_de": "Stoffklasse",
            "column": True, "vocabulary": "chemical-classes",
            "multiple": True, "facet": True, "tabs": False})
        self.assertEqual(compound_fields["group"], {
            "key": "group", "type": "choice", "label": "Group",
            "label_de": "Gruppe", "column": False,
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
        """Index data: each vocabulary maps its terms, in the snapshot's
        order, to their label, label_de and parent."""
        table = load_snapshot(self.root / "registry.json")
        vocabularies = self.index["vocabularies"]
        for name, terms in table["vocabularies"].items():
            with self.subTest(vocabulary=name):
                self.assertEqual(list(vocabularies[name]),
                                 [term["key"] for term in terms])
                for term in terms:
                    self.assertEqual(
                        vocabularies[name][term["key"]],
                        {"label": term["label"],
                         "label_de": term.get("label_de"),
                         "parent": term.get("parent")})
        self.assertEqual(vocabularies["projects"]["first-year-practical"], {
            "label": "First-year practical", "label_de": "Grundpraktikum",
            "parent": "teaching"})
        self.assertIsNone(vocabularies["projects"]["teaching"]["parent"])
        self.assertEqual(
            set(vocabularies["reaction-types"]["acylation"]),
            {"label", "label_de", "parent"})
        self.assertIsNone(vocabularies["reaction-types"]["acylation"][
            "parent"])

    def test_strict_json(self) -> None:
        """Index data: the table serializes to strict JSON."""
        text = json.dumps(self.index, allow_nan=False, ensure_ascii=False)
        self.assertEqual(json.loads(text), self.index)


class RegistryAtAnAddressTests(unittest.TestCase):
    def test_pages_of_a_registry_at_an_address(self) -> None:
        """Scenario: Pages of a registry at an address."""
        table = load_snapshot(TEST_COLLECTION / "registry.json")
        server = serve_snapshot(self, table)
        root = copy_collection(self, TEST_COLLECTION)
        name_registry(root, server.url)
        index = index_of(root)
        self.assertEqual(
            compound(index["compounds"], "acetic-anhydride")["url"],
            f"{server.origin}/lab/registry/substances/"
            "acetic-anhydride/")
        for item in index["compounds"]:
            self.assertEqual(
                item["url"],
                f"{server.origin}/lab/registry/substances/"
                f"{item['key']}/")
        self.assertEqual(index["registry"],
                         {"source": server.url, "digest": table["digest"]})
        self.assertFalse((root / "build").exists())

    def test_the_environment_names_the_registry(self) -> None:
        """Requirement: Index data (the registry as the collection or
        `ORGSYNDB_REGISTRY` names it)."""
        table = load_snapshot(TEST_COLLECTION / "registry.json")
        server = serve_snapshot(self, table)
        root = copy_collection(self, TEST_COLLECTION)
        with unittest.mock.patch.dict(
                os.environ, {"ORGSYNDB_REGISTRY": server.url}):
            index = index_of(root)
        self.assertEqual(index["registry"]["source"], server.url)
        self.assertTrue(all(item["url"] for item in index["compounds"]))

    def test_an_address_that_does_not_answer_is_a_configuration_error(
            self) -> None:
        """Requirement: Index data (raises `validate.ConfigError` when
        the registry cannot be read)."""
        root = copy_collection(self, TEST_COLLECTION)
        address = closed_address()
        name_registry(root, address)
        with self.assertRaises(pipeline().validate.ConfigError) as caught:
            index_of(root)
        self.assertIn(address, str(caught.exception))
        self.assertFalse((root / "build").exists())

    def test_a_registry_that_is_not_a_snapshot(self) -> None:
        """Requirement: Index data (raises `validate.ConfigError` when
        the registry cannot be read)."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "registry.json").write_text('{"format": 2}',
                                            encoding="utf-8")
        with self.assertRaises(pipeline().validate.ConfigError) as caught:
            index_of(root)
        self.assertIn("registry.json", str(caught.exception))


class SchemaTests(unittest.TestCase):
    def test_schema_keys(self) -> None:
        """Scenario: Schema keys."""
        schema = index_of(copy_collection(self, TEST_COLLECTION))["schema"]
        validate = pipeline().validate
        procedure = schema["procedure"]
        self.assertEqual(set(schema), {"procedure", "sequence"})
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
        self.assertEqual(schema["sequence"], {
            "keys": list(validate.SEQUENCE_KEYS),
            "step": list(validate.STEP_KEYS)})

        self.assertEqual(procedure["statuses"],
                         ["draft", "checked", "retired"])
        self.assertEqual(procedure["sections"]["de"][0], "Zusammenfassung")
        self.assertEqual(len(procedure["sections"]["de"]), 8)
        self.assertNotIn("compound", schema)

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


def write_registry(root: Path, **vocabularies: list) -> None:
    """Make ``root/registry.json`` a snapshot without substances, with
    the given vocabularies (``reaction_types`` and so on)."""
    names = {"chemical-classes": [], "inventory-groups": [],
             "projects": [], "reaction-types": []}
    for name, terms in vocabularies.items():
        names[name.replace("_", "-")] = terms
    table: dict[str, Any] = {"format": 1, "vocabularies": names,
                             "substances": []}
    table["digest"] = snapshot_digest(table)
    (root / "registry.json").write_text(json.dumps(table), encoding="utf-8")


class BrokenContentTests(unittest.TestCase):
    def test_broken_content_files_are_listed(self) -> None:
        """Scenario: Broken content files are listed."""
        root = copy_collection(self, TEST_COLLECTION)
        procedures = root / "md" / "procedures"
        (procedures / "OSDB-0990-broken.md").write_text("No front matter.\n")
        (procedures / "notes.txt").write_text("notes\n")
        (procedures / "OSDB-12-short.md").write_text("+++\n+++\n")
        index = index_of(root)

        unparsed = entry(index["procedures"],
                         "md/procedures/OSDB-0990-broken.md")
        self.assertIsNone(unparsed["front_matter"])
        self.assertIsInstance(unparsed["error"], str)
        self.assertTrue(unparsed["error"])
        paths = [item["path"] for item in index["procedures"]]
        self.assertNotIn("md/procedures/notes.txt", paths)
        self.assertNotIn("md/procedures/OSDB-12-short.md", paths)
        self.assertEqual(len(index["compounds"]), 21)

    def test_entries_left_out(self) -> None:
        """Index data: dotfiles, subdirectories, names the patterns do
        not accept and other suffixes are left out without a report."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "md" / "procedures" / ".hidden.md").write_text("x\n")
        (root / "md" / "procedures" / "nested.md").mkdir()
        (root / "md" / "sequences" / "OSDB-0001-x.md").write_text("+++\n+++\n")
        index = index_of(root)
        self.assertEqual(len(index["procedures"]), 18)
        self.assertEqual(len(index["sequences"]), 4)

    def test_a_compound_directory_is_not_read(self) -> None:
        """Requirement: Registry source (a `compounds/` directory is read
        as if it were absent)."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "compounds").mkdir()
        (root / "compounds" / "extra.toml").write_text('name = "Extra"\n')
        (root / "vocabularies").mkdir()
        (root / "vocabularies" / "projects.toml").write_text(
            '[extra]\nlabel = "Extra"\n')
        index = index_of(root)
        self.assertEqual(len(index["compounds"]), 21)
        self.assertNotIn("extra", index["vocabularies"]["projects"])

    def test_non_finite_numbers(self) -> None:
        """Scenario: Non-finite numbers."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "md" / "procedures" / "OSDB-0990-odd.md").write_text(
            "+++\nlimits = [inf, -inf, 1.5]\nworking_time = nan\n+++\n")
        index = index_of(root)
        odd = entry(index["procedures"], "md/procedures/OSDB-0990-odd.md")
        self.assertIsNone(odd["front_matter"]["working_time"])
        self.assertEqual(odd["front_matter"]["limits"], [None, None, 1.5])
        json.dumps(index, allow_nan=False)

    def test_dates_and_times(self) -> None:
        """Index data: TOML dates and times appear as ISO 8601 text."""
        root = copy_collection(self, TEST_COLLECTION)
        (root / "md" / "procedures" / "OSDB-0991-dated.md").write_text(
            "+++\nmade = 2026-01-15\nat = 09:30:00\n"
            "local = 2026-01-15T09:30:00\n"
            "nested = [{ when = 2026-01-15T09:30:00+01:00 }]\n+++\n")
        data = entry(index_of(root)["procedures"],
                     "md/procedures/OSDB-0991-dated.md")["front_matter"]
        self.assertEqual((data["made"], data["at"], data["local"]),
                         ("2026-01-15", "09:30:00", "2026-01-15T09:30:00"))
        self.assertEqual(data["nested"],
                         [{"when": "2026-01-15T09:30:00+01:00"}])


class EmptyAndBrokenCollectionTests(unittest.TestCase):
    def test_empty_collection(self) -> None:
        """Scenario: Empty collection."""
        root = Path(tempfile.mkdtemp(prefix="orgsyndb index "))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "orgsyndb.toml").write_text(
            'format = 1\nregistry = "registry.json"\n')
        write_registry(root)
        index = index_of(root)
        self.assertEqual((index["compounds"], index["procedures"],
                          index["sequences"]), ([], [], []))
        self.assertEqual(index["fields"]["procedure"], [])
        self.assertEqual(
            [f["key"] for f in index["fields"]["compound"]],
            ["article_number", "short_name", "chemical_class", "group"])
        self.assertEqual(index["vocabularies"], {
            "chemical-classes": {}, "inventory-groups": {}, "projects": {},
            "reaction-types": {}})

    def test_a_collection_that_names_no_registry(self) -> None:
        """Requirement: Index data (raises `validate.ConfigError` when
        the registry cannot be read: none is named)."""
        root = Path(tempfile.mkdtemp(prefix="orgsyndb index "))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "orgsyndb.toml").write_text("format = 1\n")
        with unittest.mock.patch.dict(os.environ):
            os.environ.pop("ORGSYNDB_REGISTRY", None)
            with self.assertRaises(
                    pipeline().validate.ConfigError) as caught:
                index_of(root)
        self.assertIn("registry", str(caught.exception))

    def test_broken_declaration(self) -> None:
        """Scenario: A declaration names a missing vocabulary."""
        root = copy_collection(self, TEST_COLLECTION)
        text = (root / "orgsyndb.toml").read_text(encoding="utf-8")
        self.assertEqual(text.count('vocabulary = "projects"'), 1)
        (root / "orgsyndb.toml").write_text(
            text.replace('vocabulary = "projects"',
                         'vocabulary = "storage"'), encoding="utf-8")
        with self.assertRaises(pipeline().validate.ConfigError) as caught:
            index_of(root)
        self.assertIn("storage", str(caught.exception))

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
        text = (sandbox.root / "orgsyndb.toml").read_text(encoding="utf-8")
        (sandbox.root / "orgsyndb.toml").write_text(
            text.replace('vocabulary = "projects"',
                         'vocabulary = "storage"'), encoding="utf-8")
        result = sandbox.build("index")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.assertIn("storage", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_registry_unreachable(self) -> None:
        """Scenario: Registry unreachable."""
        sandbox = make_sandbox(self)
        address = closed_address()
        result = sandbox.build("index",
                               env=sandbox.env(ORGSYNDB_REGISTRY=address))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(result.stderr.startswith("orgsyndb: error:"),
                        result.stderr)
        self.assertIn(address, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((sandbox.root / "build").exists())

    def test_the_index_of_a_registry_at_an_address(self) -> None:
        """Requirement: index subcommand (the JSON form of
        `index_data`)."""
        server = serve_snapshot(
            self, load_snapshot(TEST_COLLECTION / "registry.json"))
        sandbox = make_sandbox(self)
        result = sandbox.build("index",
                               env=sandbox.env(ORGSYNDB_REGISTRY=server.url))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["registry"]["source"], server.url)
        self.assertTrue(all(item["url"] for item in data["compounds"]))
        self.assertFalse((sandbox.root / "build").exists())

    def test_found_from_a_subdirectory(self) -> None:
        """collection "Choosing the collection": index finds the
        collection above the working directory."""
        sandbox = make_sandbox(self)
        result = sandbox.program(
            "index", cwd=sandbox.root / "md" / "procedures")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["compounds"]), 21)


if __name__ == "__main__":
    unittest.main()
