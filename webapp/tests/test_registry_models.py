"""Tests of the substance record (lab-registry: Substances)."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from registry.models import Substance, SubstanceClass

from . import (IndexMixin, build_index, make_article, make_class,
               make_group, make_item, make_lot, make_substance, make_task,
               make_user, page, table)

# Check digits that verify and ones that do not.
GOOD_CAS = ["140-10-3", "64-17-5", "50-00-0", "7732-18-5", "98-85-1"]
BAD_CHECK_CAS = ["140-10-4", "64-17-6", "50-00-1", "7732-18-6"]
BAD_FORM_CAS = ["1-10-3", "12345678-10-3", "140-1-3", "140103",
                "140-100-3", "140-10-33", "abc-de-f", "140-10-", " 140-10-3"]


def errors(**fields: Any) -> dict[str, list[str]]:
    """The errors of ``full_clean`` for an unsaved substance with
    ``fields`` over a valid key, name and group."""
    substance = Substance(**{"key": "acetone", "name": "Acetone",
                             "group": make_group(), **fields})
    try:
        substance.full_clean()
    except ValidationError as error:
        return error.message_dict
    return {}


class FieldTests(TestCase):

    def test_the_table_and_its_constraints(self) -> None:
        self.assertEqual(Substance._meta.db_table, "registry_substance")
        self.assertEqual(SubstanceClass._meta.db_table,
                         "registry_substanceclass")
        self.assertIn("registry_substance_cas_once",
                      {c.name for c in Substance._meta.constraints})
        self.assertIn("registry_substanceclass_once",
                      {c.name for c in SubstanceClass._meta.constraints})

    def test_a_substance_keeps_its_fields(self) -> None:
        group = make_group("final-products")
        acids = make_class("carboxylic-acids")
        made = Substance.objects.create(
            key="cinnamic-acid", name="(E)-Cinnamic acid",
            name_de="(E)-Zimtsäure", short_name="ZS", group=group,
            formula="C9H8O2", mw=Decimal("148.16"),
            smiles="OC(=O)/C=C/c1ccccc1", cas="140-10-3", note="Notiz")
        SubstanceClass.objects.create(substance=made, chemical_class=acids)
        found = Substance.objects.get(key="cinnamic-acid")
        self.assertEqual(
            (found.name, found.name_de, found.short_name, found.group,
             found.formula, found.mw, found.smiles, found.cas,
             found.note),
            ("(E)-Cinnamic acid", "(E)-Zimtsäure", "ZS", group, "C9H8O2",
             Decimal("148.16"), "OC(=O)/C=C/c1ccccc1", "140-10-3",
             "Notiz"))
        self.assertEqual(list(found.chemical_classes.all()), [acids])

    def test_only_the_key_name_and_group_are_required(self) -> None:
        self.assertEqual(errors(), {})
        made = Substance.objects.create(key="a", name="A",
                                        group=make_group())
        made.full_clean()
        self.assertIsNone(made.mw)
        self.assertFalse(made.name_de or made.short_name or made.formula
                         or made.smiles or made.cas or made.note)

    def test_the_group_is_required(self) -> None:
        self.assertIn("group", errors(group=None))

    def test_the_name_is_required_and_has_at_most_200_characters(
            self) -> None:
        self.assertNotIn("name", errors(name="n" * 200))
        self.assertIn("name", errors(name="n" * 201))
        self.assertIn("name", errors(name=""))

    def test_the_german_name_has_at_most_200_characters(self) -> None:
        self.assertNotIn("name_de", errors(name_de="n" * 200))
        self.assertIn("name_de", errors(name_de="n" * 201))
        self.assertNotIn("name_de", errors(name_de=""))

    def test_the_short_name_has_at_most_50_characters(self) -> None:
        self.assertNotIn("short_name", errors(short_name="s" * 50))
        self.assertIn("short_name", errors(short_name="s" * 51))

    def test_the_formula_has_at_most_100_characters(self) -> None:
        self.assertNotIn("formula", errors(formula="C" * 100))
        self.assertIn("formula", errors(formula="C" * 101))

    def test_smiles_and_note_are_text_of_any_length(self) -> None:
        self.assertEqual(errors(smiles="C" * 5000, note="n" * 5000), {})


class KeyTests(TestCase):

    def test_the_key_pattern(self) -> None:
        for key in ("a", "acetone", "1-4-bromophenyl-ethanol",
                    "new-compound-7", "2024"):
            with self.subTest(key=key):
                self.assertNotIn("key", errors(key=key))
        for key in ("", "Acetone", "two words", "-a", "a-", "a--b", "a_b",
                    "ä", "a/b", "A-1"):
            with self.subTest(key=key):
                self.assertIn("key", errors(key=key))

    def test_the_key_has_at_most_100_characters(self) -> None:
        self.assertNotIn("key", errors(key="k" * 100))
        self.assertIn("key", errors(key="k" * 101))

    def test_the_key_is_unique(self) -> None:
        make_substance("acetone")
        self.assertTrue(errors(key="acetone"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Substance.objects.create(key="acetone", name="Other",
                                     group=make_group())


class CasTests(TestCase):

    def test_a_cas_number_that_verifies(self) -> None:
        for cas in GOOD_CAS:
            with self.subTest(cas=cas):
                self.assertNotIn("cas", errors(cas=cas))

    def test_the_cas_number_is_optional(self) -> None:
        self.assertNotIn("cas", errors(cas=""))
        self.assertNotIn("cas", errors())

    def test_a_wrong_check_digit_is_refused(self) -> None:
        for cas in BAD_CHECK_CAS:
            with self.subTest(cas=cas):
                self.assertIn("cas", errors(cas=cas))

    def test_a_wrong_form_is_refused(self) -> None:
        for cas in BAD_FORM_CAS:
            with self.subTest(cas=cas):
                self.assertIn("cas", errors(cas=cas))

    def test_a_cas_number_is_unique_among_substances(self) -> None:
        make_substance("cinnamic-acid", cas="140-10-3")
        self.assertTrue(errors(cas="140-10-3"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Substance.objects.create(key="other", name="Other",
                                     group=make_group(), cas="140-10-3")

    def test_substances_without_a_cas_number_do_not_conflict(self) -> None:
        make_substance("a", cas="")
        make_substance("b", cas="")
        self.assertEqual(Substance.objects.filter(cas="").count(), 2)
        self.assertEqual(errors(cas=""), {})


class MolarMassTests(TestCase):

    def test_a_molar_mass_above_zero(self) -> None:
        for mw in ("148.16", "0.001", "9999999.999", "1", "18.015"):
            with self.subTest(mw=mw):
                self.assertNotIn("mw", errors(mw=Decimal(mw)))

    def test_a_molar_mass_of_zero_or_less_is_refused(self) -> None:
        for mw in ("0", "-1", "-0.001", "0.000"):
            with self.subTest(mw=mw):
                self.assertIn("mw", errors(mw=Decimal(mw)))

    def test_up_to_three_places(self) -> None:
        self.assertEqual(Substance._meta.get_field("mw").decimal_places, 3)
        self.assertIn("mw", errors(mw=Decimal("1.2345")))

    def test_the_molar_mass_is_optional(self) -> None:
        self.assertNotIn("mw", errors(mw=None))


class ClassTests(TestCase):

    def test_a_substance_has_one_row_per_class(self) -> None:
        made = make_substance("a")
        ketones = make_class("ketones")
        SubstanceClass.objects.create(substance=made,
                                      chemical_class=ketones)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SubstanceClass.objects.create(substance=made,
                                          chemical_class=ketones)

    def test_a_substance_may_have_several_classes(self) -> None:
        made = make_substance("a", classes=["ketones", "aryl-ketones"])
        self.assertEqual(
            {term.key for term in made.chemical_classes.all()},
            {"ketones", "aryl-ketones"})
        self.assertEqual(SubstanceClass.objects.filter(
            substance=made).count(), 2)

    def test_the_table_does_not_require_a_class(self) -> None:
        self.assertEqual(make_substance("a").chemical_classes.count(), 0)

    def test_many_substances_may_share_a_class(self) -> None:
        make_substance("a", classes=["ketones"])
        make_substance("b", classes=["ketones"])
        self.assertEqual(SubstanceClass.objects.count(), 2)


class DeletionTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def test_a_substance_in_use_by_a_task_cannot_be_deleted(self) -> None:
        made = make_substance("a")
        make_task(self.kl, made)
        with self.assertRaises(ProtectedError):
            made.delete()
        self.assertTrue(Substance.objects.filter(key="a").exists())

    def test_a_substance_with_a_lot_cannot_be_deleted(self) -> None:
        made = make_substance("a")
        make_lot(self.kl, substance=made)
        with self.assertRaises(ProtectedError):
            made.delete()

    def test_a_substance_with_an_article_cannot_be_deleted(self) -> None:
        made = make_substance("a")
        make_article(made, "A-1")
        with self.assertRaises(ProtectedError):
            made.delete()

    def test_a_substance_with_an_item_cannot_be_deleted(self) -> None:
        item = make_item(self.kl, "A-1")
        with self.assertRaises(ProtectedError):
            item.article.substance.delete()

    def test_a_substance_nothing_refers_to_can_be_deleted(self) -> None:
        made = make_substance("a")
        made.delete()
        self.assertFalse(Substance.objects.exists())


class HistoryTests(TestCase):

    def test_creation_and_changes_are_kept(self) -> None:
        kl = make_user("kl", "KL")
        made = Substance(key="a", name="A", group=make_group())
        made._history_user = kl
        made.save()
        made.note = "changed"
        made._history_user = kl
        made.save()
        records = list(made.history.order_by("history_id"))
        self.assertEqual([r.history_type for r in records], ["+", "~"])
        self.assertEqual([r.note for r in records], ["", "changed"])
        self.assertEqual(records[0].history_user, kl)
        self.assertEqual(records[0].key, "a")


class NameByLanguageTests(IndexMixin, TestCase):
    """Scenario: Name by language, read from the list page."""

    def names(self, language: str) -> list[str]:
        self.use_index(build_index(language))
        header, rows = table(page(self.client.get("/lab/registry/")))
        return sorted(row[header[0]].text() for row in rows)

    def setUp(self) -> None:
        make_substance("cinnamic-acid", "(E)-Cinnamic acid",
                       name_de="(E)-Zimtsäure")
        make_substance("acetophenone", "Acetophenone")

    def test_a_german_site_shows_the_german_name_when_there_is_one(
            self) -> None:
        self.assertEqual(self.names("de"),
                         ["(E)-Zimtsäure", "Acetophenone"])

    def test_an_english_site_shows_the_name(self) -> None:
        self.assertEqual(self.names("en"),
                         ["(E)-Cinnamic acid", "Acetophenone"])
