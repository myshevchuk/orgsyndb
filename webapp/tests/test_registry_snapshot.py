"""Tests of the registry's snapshot (lab-registry: Snapshot)."""

import hashlib
import json
from typing import Any

from django.test import TestCase

from registry import snapshot
from registry.models import Substance

from . import (IndexMixin, load_demo_registry, make_article, make_group,
               make_substance)
from .collection_support import make_import
from .registry_support import (SNAPSHOT, RegistryCase, wipe_registry,
                               without_digest)

VOCABULARIES = ["chemical-classes", "inventory-groups", "projects",
                "reaction-types"]
TERM_KEYS = {"key", "label", "label_de", "parent"}
SUBSTANCE_KEYS = {"key", "name", "name_de", "short_name", "group",
                  "chemical_classes", "formula", "mw", "smiles", "cas",
                  "note", "article_number"}


def digest_of(table: dict[str, Any]) -> str:
    """The digest the specification gives for ``table``."""
    return hashlib.sha256(json.dumps(
        without_digest(table), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()


class ShapeTests(RegistryCase):

    def test_the_top_level(self) -> None:
        built = snapshot.build()
        self.assertEqual(set(built), {"format", "digest", "vocabularies",
                                      "substances", "import"})
        self.assertEqual(built["format"], 1)
        self.assertEqual(set(built["vocabularies"]), set(VOCABULARIES))

    def test_it_serializes(self) -> None:
        built = snapshot.build()
        self.assertEqual(json.loads(json.dumps(built)), built)

    def test_the_terms_of_a_tree(self) -> None:
        groups = snapshot.build()["vocabularies"]["inventory-groups"]
        self.assertEqual([set(term) for term in groups],
                         [TERM_KEYS] * len(groups))
        by_key = {term["key"]: term for term in groups}
        self.assertEqual(by_key["reagents"], {
            "key": "reagents", "label": "Reagents",
            "label_de": "Reagenzien", "parent": "purchased"})
        self.assertIsNone(by_key["purchased"]["parent"])

    def test_the_reaction_types_have_no_parent(self) -> None:
        from vocabulary.models import ReactionType
        ReactionType.objects.create(key="acylation", label="Acylation",
                                    label_de="Acylierung")
        found = snapshot.build()["vocabularies"]["reaction-types"]
        self.assertEqual(found, [{"key": "acylation", "label": "Acylation",
                                  "label_de": "Acylierung"}])

    def test_empty_terms_and_vocabularies(self) -> None:
        built = snapshot.build()["vocabularies"]
        self.assertEqual(built["projects"], [])
        self.assertEqual(built["reaction-types"], [])
        self.assertEqual(len(built["chemical-classes"]), 4)

    def test_a_substance(self) -> None:
        found = {s["key"]: s for s in snapshot.build()["substances"]}
        self.assertEqual(found["cinnamic-acid"], {
            "key": "cinnamic-acid", "name": "(E)-Cinnamic acid",
            "name_de": "(E)-Zimtsäure", "short_name": "ZS",
            "group": "final-products",
            "chemical_classes": ["carboxylic-acids"], "formula": "C9H8O2",
            "mw": 148.16, "smiles": "OC(=O)/C=C/c1ccccc1",
            "cas": "140-10-3", "note": "Notiz",
            "article_number": "CH-0012"})
        for entry in found.values():
            self.assertEqual(set(entry), SUBSTANCE_KEYS)

    def test_the_molar_mass_is_a_number(self) -> None:
        found = {s["key"]: s for s in snapshot.build()["substances"]}
        mw = found["cinnamic-acid"]["mw"]
        self.assertIsInstance(mw, (int, float))
        self.assertNotIsInstance(mw, bool)
        self.assertEqual(mw, 148.16)

    def test_missing_values_are_null(self) -> None:
        found = {s["key"]: s for s in snapshot.build()["substances"]}
        self.assertEqual(found["new-compound-7"], {
            "key": "new-compound-7", "name": "New compound 7",
            "name_de": None, "short_name": None, "group": "intermediates",
            "chemical_classes": [], "formula": None, "mw": None,
            "smiles": None, "cas": None, "note": None,
            "article_number": None})

    def test_an_article_without_a_number_is_null(self) -> None:
        make_article(self.records["acetophenone"])
        found = {s["key"]: s for s in snapshot.build()["substances"]}
        self.assertIsNone(found["acetophenone"]["article_number"])

    def test_empty_text_is_null_in_the_terms_too(self) -> None:
        make_group("plain", "Plain", label_de="")
        by_key = {t["key"]: t for t in snapshot.build()[
            "vocabularies"]["inventory-groups"]}
        self.assertIsNone(by_key["plain"]["label_de"])

    def test_the_group_and_classes_are_keys(self) -> None:
        make_substance("two", classes=["ketones", "carboxylic-acids"],
                       group=make_group("reagents"))
        found = {s["key"]: s for s in snapshot.build()["substances"]}
        self.assertEqual(found["two"]["group"], "reagents")
        self.assertEqual(found["two"]["chemical_classes"],
                         ["carboxylic-acids", "ketones"])

    def test_an_empty_registry(self) -> None:
        wipe_registry()
        built = snapshot.build()
        self.assertEqual(built["substances"], [])
        self.assertEqual(built["vocabularies"],
                         {name: [] for name in VOCABULARIES})
        self.assertEqual(built["digest"], digest_of(built))


class ImportTests(RegistryCase):
    """Requirement: Snapshot (`import`, the latest accepted import,
    outside the digest)."""

    def test_no_import_is_null(self) -> None:
        from collection.models import Import
        self.assertIsNone(snapshot.build()["import"])
        make_import(outcome="refused")
        self.assertEqual(Import.objects.count(), 1)
        self.assertIsNone(snapshot.build()["import"])

    def test_the_latest_accepted_import(self) -> None:
        first = make_import()
        second = make_import(base=first, release="000002-b-c",
                             language="en")
        make_import(outcome="refused")
        found = snapshot.build()["import"]
        self.assertEqual(found, {
            "id": second.pk, "build": str(second.build),
            "commit": second.commit, "snapshot": second.snapshot,
            "tooling": second.tooling, "release": "000002-b-c",
            "language": "en"})
        self.assertIsInstance(found["id"], int)
        self.assertIsInstance(found["build"], str)

    def test_it_serializes_with_an_import(self) -> None:
        make_import()
        built = snapshot.build()
        self.assertEqual(json.loads(json.dumps(built)), built)

    def test_an_import_is_outside_the_digest(self) -> None:
        before = snapshot.build()
        make_import()
        after = snapshot.build()
        self.assertIsNotNone(after["import"])
        self.assertEqual(after["digest"], before["digest"])
        self.assertEqual(after["digest"], digest_of(after))

    def test_the_answer_over_http_names_the_import(self) -> None:
        record = make_import()
        answer = self.client.get(SNAPSHOT).json()
        self.assertEqual(answer["import"]["id"], record.pk)
        self.assertEqual(answer, snapshot.build())


class OrderTests(RegistryCase):

    def test_substances_are_ordered_by_key(self) -> None:
        make_substance("zeta")
        make_substance("0-first")
        keys = [s["key"] for s in snapshot.build()["substances"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(keys[0], "0-first")

    def test_a_substances_classes_are_ordered_by_key(self) -> None:
        make_substance("many", classes=["ketones", "carbonyl-compounds",
                                        "aryl-ketones"])
        found = {s["key"]: s for s in snapshot.build()["substances"]}
        self.assertEqual(found["many"]["chemical_classes"],
                         ["aryl-ketones", "carbonyl-compounds", "ketones"])

    def test_a_parent_precedes_its_children(self) -> None:
        for name, terms in snapshot.build()["vocabularies"].items():
            seen: set[str] = set()
            for term in terms:
                with self.subTest(vocabulary=name, key=term["key"]):
                    if term.get("parent") is not None:
                        self.assertIn(term["parent"], seen)
                seen.add(term["key"])

    def test_a_parent_precedes_its_children_though_it_sorts_after_them(
            self) -> None:
        make_group("zz-parent", "Parent")
        make_group("aa-child", "Child", make_group("zz-parent"))
        keys = [t["key"] for t in snapshot.build()[
            "vocabularies"]["inventory-groups"]]
        self.assertLess(keys.index("zz-parent"), keys.index("aa-child"))

    def test_siblings_follow_in_key_order(self) -> None:
        make_group("a-sibling", "A", make_group("purchased"))
        for name, terms in snapshot.build()["vocabularies"].items():
            siblings: dict[Any, list[str]] = {}
            for term in terms:
                siblings.setdefault(term.get("parent"), []).append(
                    term["key"])
            for parent, keys in siblings.items():
                with self.subTest(vocabulary=name, parent=parent):
                    self.assertEqual(keys, sorted(keys))


class DigestTests(RegistryCase):

    def test_the_digest_is_the_sha256_of_the_table(self) -> None:
        built = snapshot.build()
        self.assertRegex(built["digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(built["digest"], digest_of(built))

    def test_the_digest_with_characters_beyond_ascii(self) -> None:
        make_substance("umlaut", "Ätherische Öle", name_de="Äther")
        built = snapshot.build()
        self.assertEqual(built["digest"], digest_of(built))

    def test_the_same_registry_gives_the_same_digest(self) -> None:
        self.assertEqual(snapshot.build(), snapshot.build())

    def test_a_change_changes_the_digest(self) -> None:
        before = snapshot.build()["digest"]
        found = Substance.objects.get(key="acetophenone")
        found.note = "changed"
        found.save()
        self.assertNotEqual(snapshot.build()["digest"], before)

    def test_a_change_of_a_term_changes_the_digest(self) -> None:
        before = snapshot.build()["digest"]
        from vocabulary.models import Group
        Group.objects.filter(key="reagents").update(label="Changed")
        self.assertNotEqual(snapshot.build()["digest"], before)

    def test_a_change_of_an_article_number_changes_the_digest(self) -> None:
        before = snapshot.build()["digest"]
        from inventory.models import Article
        Article.objects.filter(substance__key="cinnamic-acid").update(
            article_number="CH-9999")
        self.assertNotEqual(snapshot.build()["digest"], before)


class DemoRegistryTests(IndexMixin, TestCase):

    def test_same_registry_same_digest(self) -> None:
        """Scenario: Same registry, same digest."""
        load_demo_registry()
        first = snapshot.build()
        wipe_registry()
        self.assertEqual(Substance.objects.count(), 0)
        load_demo_registry()
        second = snapshot.build()
        self.assertEqual(first, second)
        self.assertEqual(first["digest"], second["digest"])
        found = Substance.objects.get(key="cinnamic-acid")
        found.note = "changed"
        found.save()
        self.assertNotEqual(snapshot.build()["digest"], first["digest"])


class DemoImportTests(IndexMixin, TestCase):

    def test_an_import_changes_no_digest(self) -> None:
        """Scenario: An import changes no digest."""
        from django.test import override_settings
        from .collection_support import TOKEN, manifest, post
        self.use_index(None)
        load_demo_registry()
        first = snapshot.build()
        with override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN):
            done = post(self.client, manifest())
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        second = snapshot.build()
        self.assertEqual(first["digest"], second["digest"])
        self.assertIsNone(first["import"])
        self.assertEqual(second["import"]["id"], done.json()["import"])
        from collection.models import Import
        record = Import.objects.get()
        self.assertEqual((second["import"]["commit"],
                          second["import"]["release"]),
                         (record.commit, record.release))


class HttpTests(IndexMixin, TestCase):

    def setUp(self) -> None:
        self.use_index(None)
        load_demo_registry()

    def test_snapshot_over_http(self) -> None:
        """Scenario: Snapshot over HTTP."""
        response = self.client.get(SNAPSHOT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0],
                         "application/json")
        body = response.json()
        found = {s["key"]: s for s in body["substances"]}
        self.assertEqual(found["cinnamic-acid"]["article_number"],
                         "CH-0012")
        self.assertEqual(found["cinnamic-acid"]["mw"], 148.16)
        groups = [t["key"] for t in body["vocabularies"]["inventory-groups"]]
        self.assertLess(groups.index("purchased"),
                        groups.index("starting-materials"))

    def test_the_answer_is_the_snapshot(self) -> None:
        self.assertEqual(self.client.get(SNAPSHOT).json(), snapshot.build())

    def test_the_answer_follows_the_registry(self) -> None:
        before = self.client.get(SNAPSHOT).json()["digest"]
        make_substance("added-later")
        after = self.client.get(SNAPSHOT).json()
        self.assertNotEqual(after["digest"], before)
        self.assertIn("added-later", [s["key"] for s in after["substances"]])
