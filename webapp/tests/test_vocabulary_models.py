"""Tests of the vocabularies' records (lab-registry: Vocabularies)."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from vocabulary.models import ChemicalClass, Group, Project, ReactionType

from . import make_class, make_group, make_substance, make_user

TREES = [ChemicalClass, Group, Project]
ALL = [ChemicalClass, Group, Project, ReactionType]
TABLES = {ChemicalClass: "vocabulary_chemicalclass",
          Group: "vocabulary_group", Project: "vocabulary_project",
          ReactionType: "vocabulary_reactiontype"}


def errors(model: Any, **fields: Any) -> dict[str, list[str]]:
    """The errors of ``full_clean`` for an unsaved term of ``model``
    with ``fields`` over a valid key and label."""
    term = model(**{"key": "term", "label": "Term", **fields})
    try:
        term.full_clean()
    except ValidationError as error:
        return error.message_dict
    return {}


class TermFieldTests(TestCase):

    def test_the_four_vocabularies_have_their_tables(self) -> None:
        for model, table in TABLES.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.db_table, table)

    def test_a_term_has_a_key_and_two_labels(self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                term = model.objects.create(
                    key="aldehydes", label="Aldehydes",
                    label_de="Aldehyde")
                term.refresh_from_db()
                self.assertEqual(
                    (term.key, term.label, term.label_de),
                    ("aldehydes", "Aldehydes", "Aldehyde"))

    def test_the_german_label_is_optional(self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                self.assertEqual(errors(model), {})
                self.assertEqual(errors(model, label_de=""), {})

    def test_the_trees_have_a_parent_of_their_own_vocabulary(self) -> None:
        for model in TREES:
            with self.subTest(model=model.__name__):
                field = model._meta.get_field("parent")
                self.assertIs(field.related_model, model)
                self.assertTrue(field.null)
                self.assertTrue(field.blank)

    def test_the_reaction_types_are_a_flat_list(self) -> None:
        names = {field.name for field in ReactionType._meta.get_fields()}
        self.assertNotIn("parent", names)

    def test_a_term_has_no_parent_by_default(self) -> None:
        for model in TREES:
            with self.subTest(model=model.__name__):
                self.assertIsNone(model.objects.create(
                    key="top", label="Top").parent)


class TermKeyTests(TestCase):

    def test_the_key_pattern(self) -> None:
        for model in ALL:
            for key in ("a", "aldehydes", "carboxylic-acids", "a1-b2-c3",
                        "2024"):
                with self.subTest(model=model.__name__, key=key):
                    self.assertNotIn("key", errors(model, key=key))
            for key in ("", "Aldehydes", "two words", "-a", "a-", "a--b",
                        "a_b", "ä", "teaching 2", "a/b"):
                with self.subTest(model=model.__name__, key=key):
                    self.assertIn("key", errors(model, key=key))

    def test_the_key_has_at_most_50_characters(self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                self.assertNotIn("key", errors(model, key="k" * 50))
                self.assertIn("key", errors(model, key="k" * 51))

    def test_the_label_is_required_and_has_at_most_100_characters(
            self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                self.assertNotIn("label", errors(model, label="l" * 100))
                self.assertIn("label", errors(model, label="l" * 101))
                self.assertIn("label", errors(model, label=""))

    def test_the_german_label_has_at_most_100_characters(self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                self.assertNotIn("label_de",
                                 errors(model, label_de="l" * 100))
                self.assertIn("label_de",
                              errors(model, label_de="l" * 101))

    def test_the_key_is_unique_in_its_vocabulary(self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                model.objects.create(key="taken", label="One")
                self.assertTrue(errors(model, key="taken"))
                with self.assertRaises(IntegrityError), \
                        transaction.atomic():
                    model.objects.create(key="taken", label="Two")

    def test_the_same_key_may_stand_in_two_vocabularies(self) -> None:
        for model in ALL:
            model.objects.create(key="shared", label="Shared")
        self.assertEqual(sum(model.objects.filter(key="shared").count()
                             for model in ALL), len(ALL))


class TermProtectionTests(TestCase):

    def test_a_term_with_children_cannot_be_deleted(self) -> None:
        for model in TREES:
            with self.subTest(model=model.__name__):
                parent = model.objects.create(key="top", label="Top")
                child = model.objects.create(key="sub", label="Sub",
                                             parent=parent)
                with self.assertRaises(ProtectedError):
                    parent.delete()
                self.assertTrue(model.objects.filter(pk=parent.pk).exists())
                child.delete()
                parent.delete()

    def test_a_group_of_a_substance_cannot_be_deleted(self) -> None:
        group = make_group("reagents")
        make_substance("acetone", group=group)
        with self.assertRaises(ProtectedError):
            group.delete()
        self.assertTrue(Group.objects.filter(key="reagents").exists())

    def test_a_chemical_class_of_a_substance_cannot_be_deleted(
            self) -> None:
        term = make_class("ketones")
        make_substance("acetone", classes=[term])
        with self.assertRaises(ProtectedError):
            term.delete()
        self.assertTrue(ChemicalClass.objects.filter(key="ketones").exists())

    def test_a_term_in_no_use_can_be_deleted(self) -> None:
        for model in ALL:
            with self.subTest(model=model.__name__):
                model.objects.create(key="free", label="Free").delete()
                self.assertFalse(model.objects.filter(key="free").exists())


class TermHistoryTests(TestCase):

    def test_each_vocabulary_keeps_a_history(self) -> None:
        kl = make_user("kl", "KL")
        for model in ALL:
            with self.subTest(model=model.__name__):
                term = model(key="top", label="Top")
                term._history_user = kl
                term.save()
                term.label = "Changed"
                term._history_user = kl
                term.save()
                records = list(term.history.order_by("history_id"))
                self.assertEqual([r.history_type for r in records],
                                 ["+", "~"])
                self.assertEqual([r.label for r in records],
                                 ["Top", "Changed"])
                self.assertEqual(records[-1].history_user, kl)
