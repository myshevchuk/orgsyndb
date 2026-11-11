"""The collection's registry source and its reader (compound-registry,
"Registry source" and "Reading the registry"): ``pipeline.registry``."""

import json
import os
import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

from pipeline_support import (captured, closed_address, pipeline,
                              pipeline_function, serve_snapshot,
                              snapshot_digest)
from support import REGISTRY, load_snapshot, write_snapshot


class RegistryCase(unittest.TestCase):
    """A temporary collection, whose registry the tests name."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="orgsyndb registry "))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.table = load_snapshot(REGISTRY)
        patch = unittest.mock.patch.dict(os.environ)
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop("ORGSYNDB_REGISTRY", None)

    def name(self, value: str | None, file: bool = True) -> Path:
        """Write ``orgsyndb.toml`` naming ``value`` as the registry
        (none when ``value`` is None), and, with ``file``, the fixture
        registry as ``registry.json``."""
        text = "format = 1\n"
        if value is not None:
            text += f"registry = {json.dumps(value)}\n"
        (self.root / "orgsyndb.toml").write_text(text, encoding="utf-8")
        if file:
            shutil.copyfile(REGISTRY, self.root / "registry.json")
        return self.root

    def read(self, **options: Any) -> dict[str, Any]:
        return pipeline_function("registry")(self.root, **options)

    def read_with_stderr(self, **options: Any) -> tuple[dict, str]:
        found, _out, err = captured(
            lambda: pipeline_function("registry")(self.root, **options))
        return found, err

    def error(self) -> Exception:
        return pipeline().validate.ConfigError

    def kept(self) -> Path:
        return self.root / "build" / "registry.json"

    def source(self) -> Path:
        return self.root / "build" / "registry.source"

    def other_table(self) -> dict[str, Any]:
        table = {**self.table, "substances": self.table["substances"][:3]}
        table["digest"] = snapshot_digest(table)
        return table


class PathSourceTests(RegistryCase):
    def test_a_registry_named_by_a_path(self) -> None:
        """Scenario: Registry named by a path."""
        self.name("registry.json")
        self.assertEqual(self.read(), self.table)

    def test_the_path_is_relative_to_the_collection(self) -> None:
        """Requirement: Registry source (a path relative to the
        collection directory)."""
        self.name("shared/snapshots/registry.json", file=False)
        target = self.root / "shared" / "snapshots"
        target.mkdir(parents=True)
        shutil.copyfile(REGISTRY, target / "registry.json")
        self.assertEqual(self.read(), self.table)

    def test_an_absolute_path_is_taken_as_it_is(self) -> None:
        """Requirement: Registry source (relative unless it is
        absolute)."""
        self.name(str(REGISTRY), file=False)
        self.assertEqual(self.read(), self.table)

    def test_a_path_outside_the_collection(self) -> None:
        """Requirement: Registry source (a path relative to the
        collection, `..` included)."""
        inner = self.root / "inner"
        inner.mkdir()
        shutil.copyfile(REGISTRY, self.root / "registry.json")
        (inner / "orgsyndb.toml").write_text(
            'format = 1\nregistry = "../registry.json"\n',
            encoding="utf-8")
        self.root = inner
        self.assertEqual(self.read(), self.table)

    def test_the_copy_the_tools_read(self) -> None:
        """Requirement: Reading the registry (it writes the snapshot to
        `build/registry.json` and the source to
        `build/registry.source`)."""
        self.name("registry.json")
        self.read()
        self.assertEqual(load_snapshot(self.kept()), self.table)
        self.assertEqual(self.source().read_text(encoding="utf-8").strip(),
                         "registry.json")

    def test_the_kept_file_may_be_the_registry_itself(self) -> None:
        """Requirement: Reading the registry (unless the path is that
        file)."""
        self.name("build/registry.json", file=False)
        (self.root / "build").mkdir()
        shutil.copyfile(REGISTRY, self.kept())
        before = self.kept().read_bytes()
        self.assertEqual(self.read(), self.table)
        self.assertEqual(self.kept().read_bytes(), before)

    def test_nothing_is_written_with_store_false(self) -> None:
        """Requirement: Reading the registry (with `store` false it
        writes no file)."""
        self.name("registry.json")
        self.assertEqual(self.read(store=False), self.table)
        self.assertFalse((self.root / "build").exists())


class EnvironmentTests(RegistryCase):
    def test_the_environment_wins(self) -> None:
        """Scenario: The environment wins."""
        self.name("registry.json")
        other = self.root / "other.json"
        write_snapshot(other, self.other_table())
        os.environ["ORGSYNDB_REGISTRY"] = str(other)
        self.assertEqual(self.read()["substances"],
                         self.other_table()["substances"])

    def test_the_environment_names_the_source(self) -> None:
        """Requirement: Reading the registry (the source as the
        collection or `ORGSYNDB_REGISTRY` names it)."""
        self.name("registry.json")
        os.environ["ORGSYNDB_REGISTRY"] = str(REGISTRY)
        self.read()
        self.assertEqual(self.source().read_text(encoding="utf-8").strip(),
                         str(REGISTRY))

    def test_an_empty_variable_is_not_set(self) -> None:
        """Requirement: Registry source (when set and not empty)."""
        self.name("registry.json")
        os.environ["ORGSYNDB_REGISTRY"] = ""
        self.assertEqual(self.read(), self.table)

    def test_the_environment_serves_a_collection_that_names_none(
            self) -> None:
        """Requirement: Registry source (the variable takes the place of
        the setting)."""
        self.name(None)
        os.environ["ORGSYNDB_REGISTRY"] = str(REGISTRY)
        self.assertEqual(self.read(), self.table)


class NoRegistryTests(RegistryCase):
    def test_no_registry_named(self) -> None:
        """Scenario: No registry named."""
        self.name(None)
        with self.assertRaisesRegex(self.error(), "registry"):
            self.read()

    def test_a_registry_that_is_no_text(self) -> None:
        """Requirement: Registry source (a value of another type, or an
        empty one, is a configuration error naming `registry`)."""
        for value in ("3", "true", "[1]", '""', '"  "'):
            with self.subTest(value=value):
                (self.root / "orgsyndb.toml").write_text(
                    f"format = 1\nregistry = {value}\n", encoding="utf-8")
                with self.assertRaisesRegex(self.error(), "registry"):
                    self.read()

    def test_a_missing_registry_file(self) -> None:
        """Requirement: Reading the registry (a file that is not
        readable)."""
        self.name("no-such-registry.json", file=False)
        with self.assertRaisesRegex(self.error(), "no-such-registry.json"):
            self.read()


class NotASnapshotTests(RegistryCase):
    def refused(self, text: str | bytes) -> None:
        self.name("registry.json")
        path = self.root / "registry.json"
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(self.error(), "registry.json"):
            self.read()

    def test_not_a_snapshot(self) -> None:
        """Scenario: Not a snapshot."""
        self.refused('{"format": 2}')

    def test_content_that_is_no_snapshot(self) -> None:
        """Requirement: Reading the registry (any other content)."""
        for name, mutate in {
                "format 0": lambda t: t.update(format=0),
                "format a string": lambda t: t.update(format="1"),
                "substances a table": lambda t: t.update(substances={}),
                "a substance that is a string":
                    lambda t: t.update(substances=["x"]),
                "vocabularies a list": lambda t: t.update(vocabularies=[]),
                "a vocabulary that is a table":
                    lambda t: t["vocabularies"].update(projects={}),
                "a term that is a string":
                    lambda t: t["vocabularies"].update(projects=["x"]),
        }.items():
            with self.subTest(case=name):
                table = json.loads(json.dumps(self.table))
                mutate(table)
                self.refused(json.dumps(table))

    def test_the_keys_and_vocabularies_the_snapshot_states(self) -> None:
        """Requirement: Reading the registry (`format` is `1` and
        `vocabularies` and `substances` have the shapes lab-registry
        "Snapshot" states: all four vocabularies)."""
        cases: dict[str, Any] = {
            "no substances": lambda t: t.pop("substances"),
            "no vocabularies": lambda t: t.pop("vocabularies"),
            "format true": lambda t: t.update(format=True)}
        for name in ("chemical-classes", "inventory-groups", "projects",
                     "reaction-types"):
            cases[f"no {name}"] = (
                lambda t, name=name: t["vocabularies"].pop(name))
        for case, mutate in cases.items():
            with self.subTest(case=case):
                table = json.loads(json.dumps(self.table))
                mutate(table)
                self.refused(json.dumps(table))

    def test_a_parent_that_is_no_term(self) -> None:
        """Requirement: Reading the registry (a term's `parent` is null
        or the key of another term of its vocabulary)."""
        cases = {
            "a list": [{"key": "a", "label": "A", "parent": []}],
            "missing above another": [
                {"key": "a", "label": "A", "parent": "b"},
                {"key": "b", "label": "B", "parent": "zz"}]}
        for case, terms in cases.items():
            with self.subTest(case=case):
                table = json.loads(json.dumps(self.table))
                table["vocabularies"]["chemical-classes"] = terms
                self.refused(json.dumps(table))

    def test_a_file_that_is_not_json(self) -> None:
        """Requirement: Reading the registry (not UTF-8 JSON)."""
        self.refused("{")
        self.refused(b'{"format": 1, "x": "Caf\xe9"}')
        self.refused("")

    def test_a_json_value_that_is_not_a_table(self) -> None:
        """Requirement: Reading the registry (a table of the snapshot's
        keys)."""
        for text in ("[]", "1", "null", '"snapshot"'):
            with self.subTest(text=text):
                self.refused(text)


class AddressTests(RegistryCase):
    def serve(self, table: dict | None = None):
        server = serve_snapshot(self, self.table if table is None
                                else table)
        self.name(server.url, file=False)
        return server

    def test_fetched_and_kept(self) -> None:
        """Scenario: Fetched and kept."""
        server = self.serve()
        self.assertEqual(self.read(), self.table)
        self.assertEqual(load_snapshot(self.kept()), self.table)
        self.assertEqual(self.source().read_text(encoding="utf-8").strip(),
                         server.url)
        self.assertEqual(len(server.hosts), 1)

    def test_offline_with_a_copy(self) -> None:
        """Scenario: Offline with a copy."""
        server = self.serve()
        self.read()
        server.stop()
        found, err = self.read_with_stderr()
        self.assertEqual(found, self.table)
        self.assertIn(server.url, err)
        self.assertIn(self.table["digest"], err)

    def test_offline_without_a_copy(self) -> None:
        """Scenario: Offline without a copy."""
        address = closed_address()
        self.name(address, file=False)
        with self.assertRaises(self.error()) as caught:
            self.read()
        self.assertIn(address, str(caught.exception))

    def test_a_copy_of_another_registry(self) -> None:
        """Scenario: A copy of another registry."""
        self.serve()
        self.read()
        address = closed_address()
        os.environ["ORGSYNDB_REGISTRY"] = address
        with self.assertRaises(self.error()) as caught:
            self.read()
        self.assertIn(address, str(caught.exception))

    def test_a_copy_of_a_file_is_no_copy_of_an_address(self) -> None:
        """Requirement: Reading the registry (the copy of the same
        source only)."""
        self.name("registry.json")
        self.read()
        address = closed_address()
        self.name(address, file=False)
        with self.assertRaises(self.error()) as caught:
            self.read()
        self.assertIn(address, str(caught.exception))

    def test_an_answer_that_is_no_snapshot_falls_back_to_the_copy(
            self) -> None:
        """Requirement: Reading the registry (the request fails, or the
        answer is not a snapshot)."""
        server = self.serve()
        self.read()
        for status, body in ((200, b'{"format": 2}'), (200, b"nonsense"),
                             (500, b"{}"), (404, None)):
            with self.subTest(status=status):
                server.status, server.body = status, body
                found, err = self.read_with_stderr()
                self.assertEqual(found, self.table)
                self.assertIn(server.url, err)
                self.assertEqual(load_snapshot(self.kept()), self.table)

    def test_an_answer_that_is_no_snapshot_without_a_copy(self) -> None:
        """Requirement: Reading the registry (without a copy it raises
        `validate.ConfigError` naming the address)."""
        server = self.serve()
        server.body = b'{"format": 2}'
        with self.assertRaises(self.error()) as caught:
            self.read()
        self.assertIn(server.url, str(caught.exception))
        self.assertFalse(self.kept().exists())

    def test_a_new_answer_replaces_the_copy(self) -> None:
        """Requirement: Reading the registry (`build/registry.json` holds
        the registry the tools last read)."""
        server = self.serve()
        self.read()
        server.table = self.other_table()
        self.assertEqual(self.read(), self.other_table())
        self.assertEqual(load_snapshot(self.kept()), self.other_table())

    def test_store_false_writes_no_file(self) -> None:
        """Requirement: Reading the registry (with `store` false it
        writes no file)."""
        self.serve()
        self.assertEqual(self.read(store=False), self.table)
        self.assertFalse((self.root / "build").exists())

    def test_store_false_falls_back_to_a_copy_and_leaves_it(self) -> None:
        """Requirement: Reading the registry (with `store` false it
        falls back to a copy as above)."""
        server = self.serve()
        self.read()
        before = (self.kept().read_bytes(), self.source().read_bytes())
        server.stop()
        found, err = self.read_with_stderr(store=False)
        self.assertEqual(found, self.table)
        self.assertIn(server.url, err)
        self.assertEqual(
            (self.kept().read_bytes(), self.source().read_bytes()), before)

    def test_store_false_without_a_copy_raises(self) -> None:
        """Requirement: Reading the registry (`store` false, nothing to
        fall back to)."""
        address = closed_address()
        self.name(address, file=False)
        with self.assertRaises(self.error()) as caught:
            self.read(store=False)
        self.assertIn(address, str(caught.exception))
        self.assertFalse((self.root / "build").exists())

    def test_the_request_is_a_get_of_the_address(self) -> None:
        """Requirement: Reading the registry (it requests the
        snapshot)."""
        server = self.serve()
        self.read()
        self.assertTrue(server.hosts)


if __name__ == "__main__":
    unittest.main()
