"""Tests of ``manage.py registry_load`` (lab-registry: Loading a
registry)."""

import copy
import re
import tempfile
from pathlib import Path
from typing import Any

from django.core.management.base import CommandError
from django.test import TestCase

from inventory.models import Article
from registry import snapshot
from registry.models import Substance, SubstanceClass
from vocabulary.models import ChemicalClass, Group, Project, ReactionType

from . import DEMO_REGISTRY, make_group, make_substance
from .registry_support import (demo_registry, load, load_refused,
                               small_snapshot, without_digest, write_json)

TERMS = (ChemicalClass, Group, Project, ReactionType)


def counts() -> tuple[int, int, int]:
    """The terms, substances and articles the database holds."""
    return (sum(model.objects.count() for model in TERMS),
            Substance.objects.count(), Article.objects.count())


def shown(out: str, number: int) -> bool:
    return re.search(rf"(?<![\d.,]){number}(?![\d.,]\d)", out) is not None


class LoadCase(TestCase):

    def setUp(self) -> None:
        self.directory = Path(self.enterContext(
            tempfile.TemporaryDirectory()))

    def file(self, data: Any) -> Path:
        return write_json(self.directory, data)

    def refused(self, data: Any) -> CommandError:
        """Load ``data``; it is refused, with a message, nothing
        changes and the exit status is 1."""
        before = counts()
        error = load_refused(self.file(data))
        self.assertTrue(str(error).strip())
        self.assertEqual(error.returncode, 1)
        self.assertEqual(counts(), before)
        return error


class RoundTripTests(LoadCase):

    def test_round_trip(self) -> None:
        """Scenario: Round trip."""
        load(DEMO_REGISTRY)
        self.assertEqual(without_digest(snapshot.build(), "accounts"),
                         without_digest(demo_registry(), "accounts"))
        self.assertIsNone(snapshot.build()["import"])
        self.assertEqual(snapshot.build().get("accounts"), [])

    def loaded_with(self, accounts: Any) -> None:
        """Load the small snapshot with ``accounts`` as its `accounts`:
        it loads, and creates no account."""
        from django.contrib.auth import get_user_model
        data = small_snapshot()
        data["accounts"] = accounts
        load(self.file(data))
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(snapshot.build().get("accounts"), [])

    def test_the_accounts_of_a_snapshot_are_ignored(self) -> None:
        """Requirement: Loading a registry (it ignores `accounts`, which
        it does not create)."""
        self.loaded_with([{"username": "z.new", "name": "Z. New"}])

    def test_accounts_that_are_no_list_are_ignored_too(self) -> None:
        """Requirement: Loading a registry (it ignores `accounts`)."""
        self.loaded_with("not a list")

    def test_the_import_of_a_snapshot_is_ignored(self) -> None:
        """Requirement: Loading a registry (it ignores `digest` and
        `import`)."""
        from collection.models import Import
        data = demo_registry()
        data["import"] = {
            "id": 7, "build": "6f1c2d3e-1111-4222-8333-444455556666",
            "commit": "a" * 40, "snapshot": "d" * 64, "tooling": "b" * 40,
            "release": "000007-bbbbbbbbbb-aaaaaaaaaa", "language": "de"}
        load(self.file(data))
        self.assertEqual(Import.objects.count(), 0)
        self.assertIsNone(snapshot.build()["import"])
        self.assertEqual(without_digest(snapshot.build(), "accounts"),
                         without_digest(demo_registry(), "accounts"))

    def test_the_counts_are_printed(self) -> None:
        data = demo_registry()
        out, _err = load(DEMO_REGISTRY)
        terms = sum(len(found) for found in data["vocabularies"].values())
        articles = sum(1 for s in data["substances"]
                       if s["article_number"])
        for number in (terms, len(data["substances"]), articles):
            with self.subTest(number=number):
                self.assertTrue(shown(out, number), out)
        self.assertEqual(counts(), (terms, len(data["substances"]),
                                    articles))

    def test_a_small_registry(self) -> None:
        out, _err = load(self.file(small_snapshot()))
        self.assertEqual(counts(), (5, 2, 1))
        acetone = Substance.objects.get(key="acetone")
        self.assertEqual(
            (acetone.name, acetone.name_de, acetone.group.key,
             str(acetone.mw), acetone.cas),
            ("Acetone", "Aceton", "reagents", "58.080", "67-64-1"))
        self.assertEqual({t.key for t in acetone.chemical_classes.all()},
                         {"ketones"})
        self.assertEqual(Article.objects.get().article_number, "CH-0099")
        self.assertEqual(Article.objects.get().substance, acetone)
        self.assertEqual(Group.objects.get().label_de, "Reagenzien")
        self.assertEqual(ChemicalClass.objects.get(key="ketones").parent,
                         ChemicalClass.objects.get(
                             key="carbonyl-compounds"))
        mystery = Substance.objects.get(key="mystery")
        self.assertIsNone(mystery.mw)
        self.assertEqual(mystery.chemical_classes.count(), 2)
        self.assertEqual(SubstanceClass.objects.count(), 3)
        for number in (5, 2, 1):
            self.assertTrue(shown(out, number), out)

    def test_a_substance_without_a_number_has_no_article(self) -> None:
        load(self.file(small_snapshot()))
        self.assertFalse(Article.objects.filter(
            substance__key="mystery").exists())

    def test_a_blank_article_number_makes_no_article(self) -> None:
        data = small_snapshot()
        for entry in data["substances"]:
            if entry["key"] == "acetone":
                entry["article_number"] = "  "
        load(self.file(data))
        self.assertTrue(Substance.objects.filter(key="acetone").exists())
        self.assertFalse(Article.objects.filter(
            substance__key="acetone").exists())

    def test_empty_text_is_stored_as_none_or_empty(self) -> None:
        load(self.file(small_snapshot()))
        mystery = Substance.objects.get(key="mystery")
        for field in ("name_de", "short_name", "formula", "smiles", "cas",
                      "note"):
            with self.subTest(field=field):
                self.assertFalse(getattr(mystery, field))

    def test_each_record_has_its_creation_in_the_history(self) -> None:
        load(self.file(small_snapshot()))
        records = [*Substance.objects.all(), *Article.objects.all(),
                   *(term for model in TERMS
                     for term in model.objects.all())]
        self.assertEqual(len(records), 5 + 2 + 1)
        for record in records:
            with self.subTest(record=str(record)):
                entry = record.history.get()
                self.assertEqual(entry.history_type, "+")
                self.assertIsNone(entry.history_user)

    def test_the_digest_is_ignored(self) -> None:
        data = small_snapshot()
        data["digest"] = "0" * 64
        load(self.file(data))
        self.assertEqual(counts(), (5, 2, 1))
        self.assertNotEqual(snapshot.build()["digest"], "0" * 64)

    def test_a_file_without_a_digest_loads(self) -> None:
        load(self.file(small_snapshot()))
        self.assertEqual(counts(), (5, 2, 1))

    def test_the_registry_a_loaded_file_makes_is_reproducible(self) -> None:
        load(self.file(small_snapshot()))
        built = snapshot.build()
        self.assertEqual(without_digest(built, "accounts"),
                         small_snapshot())

    def test_a_missing_vocabulary_is_empty(self) -> None:
        data = small_snapshot()
        del data["vocabularies"]["projects"]
        del data["vocabularies"]["reaction-types"]
        load(self.file(data))
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(ReactionType.objects.count(), 0)


class RefusalTests(LoadCase):

    def test_registry_not_empty(self) -> None:
        """Scenario: Registry not empty."""
        make_substance("existing")
        error = load_refused(self.file(demo_registry()))
        self.assertTrue(str(error).strip())
        self.assertEqual(error.returncode, 1)
        self.assertEqual(list(Substance.objects.values_list(
            "key", flat=True)), ["existing"])
        self.assertEqual(Article.objects.count(), 0)

    def test_a_term_alone_makes_the_registry_not_empty(self) -> None:
        for model in TERMS:
            with self.subTest(model=model.__name__):
                model.objects.create(key="existing", label="Existing")
                self.refused(small_snapshot())
                model.objects.all().delete()

    def test_an_unknown_format(self) -> None:
        for value in (2, 0, "1", None):
            with self.subTest(format=value):
                data = small_snapshot()
                data["format"] = value
                error = self.refused(data)
                self.assertIn("format", str(error))

    def test_a_missing_format(self) -> None:
        data = small_snapshot()
        del data["format"]
        self.refused(data)

    def test_an_unknown_group(self) -> None:
        data = small_snapshot()
        data["substances"][1]["group"] = "no-such-group"
        error = self.refused(data)
        self.assertIn("mystery", str(error))
        self.assertIn("group", str(error))

    def test_an_unknown_chemical_class(self) -> None:
        data = small_snapshot()
        data["substances"][0]["chemical_classes"] = ["ketones", "nope"]
        error = self.refused(data)
        self.assertIn("acetone", str(error))
        self.assertIn("chemical_classes", str(error))

    def test_an_unknown_parent(self) -> None:
        data = small_snapshot()
        data["vocabularies"]["chemical-classes"][1]["parent"] = "nope"
        error = self.refused(data)
        self.assertIn("ketones", str(error))
        self.assertIn("parent", str(error))

    def test_a_substance_value_a_form_would_refuse(self) -> None:
        cases = [("key", "Bad Key"), ("key", ""), ("key", "k" * 101),
                 ("key", "group"),
                 ("name", ""), ("name", "n" * 201), ("mw", 0),
                 ("mw", -1.5), ("mw", 1.2345), ("cas", "140-10-4"),
                 ("cas", "1-1-1"), ("short_name", "s" * 51),
                 ("formula", "f" * 101), ("name_de", "n" * 201)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                data = small_snapshot()
                data["substances"][1][field] = value
                error = self.refused(data)
                self.assertIn(field, str(error))
                if field != "key":
                    self.assertIn("mystery", str(error))

    def test_a_cas_number_taken_twice(self) -> None:
        data = small_snapshot()
        data["substances"][1]["cas"] = "67-64-1"
        error = self.refused(data)
        self.assertIn("cas", str(error))

    def test_a_substance_key_taken_twice(self) -> None:
        data = small_snapshot()
        data["substances"].append(copy.deepcopy(data["substances"][0]))
        data["substances"][2]["cas"] = None
        data["substances"][2]["article_number"] = None
        error = self.refused(data)
        self.assertIn("acetone", str(error))

    def test_an_article_number_taken_twice(self) -> None:
        data = small_snapshot()
        data["substances"][1]["article_number"] = "CH-0099"
        error = self.refused(data)
        self.assertIn("CH-0099", str(error))

    def test_an_article_number_of_more_than_30_characters(self) -> None:
        data = small_snapshot()
        data["substances"][1]["article_number"] = "A" * 31
        self.refused(data)

    def test_a_term_value_a_form_would_refuse(self) -> None:
        cases = [("key", "Bad Key"), ("key", "k" * 51), ("label", ""),
                 ("label", "l" * 101), ("label_de", "l" * 101)]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                data = small_snapshot()
                data["vocabularies"]["projects"][0][field] = value
                error = self.refused(data)
                self.assertIn(field, str(error))

    def test_a_term_key_taken_twice_in_a_vocabulary(self) -> None:
        data = small_snapshot()
        data["vocabularies"]["inventory-groups"].append(
            copy.deepcopy(data["vocabularies"]["inventory-groups"][0]))
        self.refused(data)

    def test_the_message_names_the_record(self) -> None:
        data = small_snapshot()
        data["vocabularies"]["projects"][0]["key"] = "Bad Key"
        self.assertIn("Bad Key", str(self.refused(data)))

    def test_nothing_is_written_when_the_last_substance_fails(self) -> None:
        data = demo_registry()
        data["substances"][-1]["mw"] = -1
        self.refused(data)
        self.assertEqual(counts(), (0, 0, 0))
        self.assertEqual(SubstanceClass.objects.count(), 0)

    def test_nothing_is_written_for_a_broken_reference_at_the_end(
            self) -> None:
        data = demo_registry()
        data["substances"][-1]["group"] = "no-such-group"
        self.refused(data)
        self.assertEqual(counts(), (0, 0, 0))

    def test_a_refused_file_leaves_a_registry_it_may_not_fill(self) -> None:
        make_group("kept")
        self.refused(small_snapshot())
        self.assertEqual(list(Group.objects.values_list("key", flat=True)),
                         ["kept"])
