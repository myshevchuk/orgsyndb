"""Tests of the articles (end-product-inventory: Articles)."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from inventory.models import Article

from . import make_article, make_item, make_substance, make_user


def errors(**fields: Any) -> dict[str, list[str]]:
    """The errors of ``full_clean`` for an unsaved article of a new
    substance with ``fields``."""
    article = Article(**{"substance": make_substance("probe"), **fields})
    try:
        article.full_clean()
    except ValidationError as error:
        return error.message_dict
    return {}


class FieldTests(TestCase):

    def test_the_table(self) -> None:
        self.assertEqual(Article._meta.db_table, "inventory_article")

    def test_the_substance_is_the_primary_key(self) -> None:
        field = Article._meta.get_field("substance")
        self.assertTrue(field.primary_key)
        self.assertTrue(field.one_to_one)
        self.assertEqual(Article._meta.pk.name, "substance")
        self.assertEqual(field.related_model._meta.label,
                         "registry.Substance")

    def test_an_article_is_one_substance(self) -> None:
        substance = make_substance("a")
        article = make_article(substance, "A-1")
        self.assertEqual(article.pk, substance.pk)
        self.assertEqual(Article.objects.get(pk=substance.pk), article)

    def test_a_substance_has_at_most_one_article(self) -> None:
        substance = make_substance("a")
        make_article(substance, "A-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Article.objects.create(substance=substance,
                                   article_number="A-2")

    def test_a_substance_need_not_be_an_article(self) -> None:
        make_substance("a")
        self.assertFalse(Article.objects.exists())

    def test_an_article_keeps_its_fields(self) -> None:
        article = make_article(make_substance("a"), "CH-0012", "Säuren")
        found = Article.objects.get(pk=article.pk)
        self.assertEqual((found.article_number, found.category),
                         ("CH-0012", "Säuren"))

    def test_the_number_has_at_most_30_characters(self) -> None:
        self.assertNotIn("article_number",
                         errors(article_number="A" * 30))
        self.assertIn("article_number", errors(article_number="A" * 31))

    def test_the_number_and_the_category_are_optional(self) -> None:
        self.assertEqual(errors(), {})
        self.assertEqual(errors(article_number=None, category=""), {})

    def test_the_category_has_at_most_100_characters(self) -> None:
        self.assertNotIn("category", errors(category="c" * 100))
        self.assertIn("category", errors(category="c" * 101))


class NumberTests(TestCase):

    def test_a_number_is_unique_among_articles(self) -> None:
        make_article(make_substance("a"), "CH-0012")
        self.assertTrue(errors(article_number="CH-0012"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Article.objects.create(substance=make_substance("b"),
                                   article_number="CH-0012")

    def test_articles_without_a_number_do_not_conflict(self) -> None:
        make_article(make_substance("a"))
        make_article(make_substance("b"))
        self.assertEqual(Article.objects.filter(
            article_number__isnull=True).count(), 2)

    def test_an_article_has_none_until_it_is_given_one(self) -> None:
        article = make_article(make_substance("a"))
        self.assertIsNone(article.article_number)
        article.article_number = "CH-0021"
        article.save()
        self.assertEqual(Article.objects.get(pk=article.pk)
                         .article_number, "CH-0021")


class DeletionTests(TestCase):

    def test_an_article_with_items_cannot_be_deleted(self) -> None:
        kl = make_user("kl", "KL")
        item = make_item(kl, "CH-0012")
        with self.assertRaises(ProtectedError):
            item.article.delete()
        self.assertTrue(Article.objects.exists())

    def test_an_article_without_items_can_be_deleted(self) -> None:
        article = make_article(make_substance("a"), "A-1")
        article.delete()
        self.assertFalse(Article.objects.exists())


class HistoryTests(TestCase):

    def test_creation_and_changes_are_kept(self) -> None:
        kl = make_user("kl", "KL")
        article = Article(substance=make_substance("a"))
        article._history_user = kl
        article.save()
        article.article_number = "CH-0021"
        article.category = "Säuren"
        article._history_user = kl
        article.save()
        records = list(article.history.order_by("history_id"))
        self.assertEqual([r.history_type for r in records], ["+", "~"])
        self.assertEqual(records[0].history_user, kl)
        self.assertIsNone(records[0].article_number)
        self.assertEqual(records[1].article_number, "CH-0021")
        self.assertEqual(records[1].category, "Säuren")
