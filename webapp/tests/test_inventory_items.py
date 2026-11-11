"""Tests of the inventory's items (end-product-inventory: Items)."""

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction

from inventory.models import Article, Item, Movement, Unit

from . import make_substance, page, table
from .inventory_support import (COMPOUND_PAGE, LIST, MICRO, NEW_ITEM,
                                FormCase, InventoryCase, fresh, item_data,
                                item_url, snapshot)

SUBSTANCE = "/lab/registry/substances/cinnamic-acid/"


class FieldTests(InventoryCase):

    def test_an_item_keeps_its_fields(self) -> None:
        made = self.item("CH-0012", "Zimtsäure", size="2.5", unit="mg",
                         quantity=7, category="Endprodukt", note="Notiz")
        item = Item.objects.get(pk=made.pk)
        self.assertEqual(
            (item.article.article_number, item.article.category,
             item.article.substance.name, item.unit, item.quantity,
             item.note),
            ("CH-0012", "Endprodukt", "Zimtsäure", "mg", 7, "Notiz"))
        self.assertEqual(item.size, Decimal("2.5"))

    def test_an_item_is_a_size_of_an_article(self) -> None:
        item = self.item("CH-0012")
        self.assertIsInstance(item.article, Article)
        self.assertEqual(item.article.substance.key, "cinnamic-acid")

    def test_the_article_holds_what_the_item_no_longer_does(self) -> None:
        names = {field.name for field in Item._meta.get_fields()}
        self.assertIn("article", names)
        for gone in ("inventory", "article_number", "name", "category"):
            with self.subTest(field=gone):
                self.assertNotIn(gone, names)

    def test_the_article_is_protected(self) -> None:
        field = Item._meta.get_field("article")
        self.assertEqual(field.remote_field.on_delete.__name__, "PROTECT")

    def test_category_and_note_are_optional(self) -> None:
        item = self.item("CH-0012", size="1", unit="g", quantity=1)
        self.assertEqual((item.article.category, item.note), ("", ""))

    def test_the_four_units(self) -> None:
        self.assertEqual({u.value: str(u.label) for u in Unit},
                         {"mg": "mg", "umol": f"{MICRO}mol", "g": "g",
                          "mmol": "mmol"})
        self.assertEqual(Unit.MG.value, "mg")
        self.assertEqual(Unit.UMOL.value, "umol")
        self.assertEqual(Unit.G.value, "g")
        self.assertEqual(Unit.MMOL.value, "mmol")

    def test_every_unit_makes_an_item(self) -> None:
        for number, unit in enumerate(("mg", "umol", "g", "mmol")):
            with self.subTest(unit=unit):
                item = self.item(f"U-{number}", unit=unit)
                self.assertEqual(fresh(item).unit, unit)

    def test_the_size_keeps_three_places(self) -> None:
        item = self.item("S-1", size="0.001")
        self.assertEqual(fresh(item).size, Decimal("0.001"))
        self.assertEqual(Item._meta.get_field("size").decimal_places, 3)

    def test_the_quantity_may_be_zero(self) -> None:
        self.assertEqual(fresh(self.item("Q-0", quantity=0)).quantity, 0)


class NewItemFormTests(FormCase):
    """What a new item's form refuses; the booking behind it."""

    def test_a_negative_quantity_is_refused(self) -> None:
        before = snapshot()
        response = self.client.post(NEW_ITEM, item_data(quantity="-1"))
        self.refused(response, "quantity")
        self.assertEqual(snapshot(), before)

    def test_the_opening_count_is_the_first_movement(self) -> None:
        """Scenario: New item (the opening count)."""
        response = self.client.post(NEW_ITEM, item_data())
        item = Item.objects.get()
        movement = item.movements.get()
        self.assertEqual(movement.kind, Movement.Kind.OPENING)
        self.assertEqual(movement.kind, "opening")
        self.assertEqual((movement.count, movement.quantity_after), (12, 12))
        self.assertEqual(movement.user, self.kl)
        self.assertEqual(movement.date, date(2026, 11, 4))
        self.assertIsNotNone(movement.booked_at)
        self.assertIsNone(movement.delivery_note)
        self.assertIsNone(movement.bulk_movement)
        self.assertIsNone(movement.reverses)
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)

    def test_an_empty_item_has_an_opening_movement_too(self) -> None:
        self.client.post(NEW_ITEM, item_data(quantity="0"))
        movement = Item.objects.get().movements.get()
        self.assertEqual((movement.kind, movement.count), ("opening", 0))

    def test_the_booking_user_is_in_the_history(self) -> None:
        self.client.post(NEW_ITEM, item_data())
        entry = Item.objects.get().history.get()
        self.assertEqual(entry.history_user, self.kl)
        self.assertEqual(entry.history_type, "+")

    def test_one_article_in_two_sizes(self) -> None:
        """Scenario: One article in two sizes."""
        for size in ("10", "50"):
            done = self.client.post(NEW_ITEM, item_data(size=size))
            self.assertEqual(done.status_code, 302)
        before = snapshot()
        response = self.client.post(NEW_ITEM, item_data(size="10"))
        self.refused(response, "size")
        self.assertEqual(snapshot(), before)
        self.assertEqual(Item.objects.count(), 2)
        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(
            {item.article.pk for item in Item.objects.all()},
            {Article.objects.get().pk})

    def test_a_trailing_zero_is_the_same_size(self) -> None:
        self.client.post(NEW_ITEM, item_data(size="10", unit="mg"))
        response = self.client.post(NEW_ITEM, item_data(size="10.000",
                                                        unit="mg"))
        self.refused(response, "size")

    def test_the_same_size_in_another_unit_is_another_item(self) -> None:
        self.client.post(NEW_ITEM, item_data(size="10", unit="umol"))
        self.client.post(NEW_ITEM, item_data(size="10", unit="mg"))
        self.assertEqual(Item.objects.count(), 2)

    def test_another_article_may_share_size_and_unit(self) -> None:
        make_substance("benzaldehyde")
        self.client.post(NEW_ITEM, item_data(size="10", unit="umol"))
        self.client.post(NEW_ITEM, item_data(
            substance="benzaldehyde", article_number="CH-0013",
            size="10", unit="umol"))
        self.assertEqual(Item.objects.count(), 2)


class IdentityTests(InventoryCase):

    def test_the_identity_is_article_size_and_unit(self) -> None:
        constraint = next(c for c in Item._meta.constraints
                          if c.name == "inventory_item_identity")
        self.assertEqual(tuple(constraint.fields),
                         ("article", "size", "unit"))

    def test_the_same_size_in_another_unit_is_another_item(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.item("CH-0012", size="10", unit="mg")
        self.assertEqual(Item.objects.count(), 2)

    def test_another_article_may_share_size_and_unit(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.item("CH-0013", size="10", unit="umol")
        self.assertEqual(Item.objects.count(), 2)

    def test_a_trailing_zero_is_the_same_size(self) -> None:
        self.item("CH-0012", size="10", unit="mg")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.item("CH-0012", size="10.000", unit="mg")

    def test_the_sizes_of_an_article_share_its_substance(self) -> None:
        small = self.item("CH-0012", size="10", unit="umol")
        large = self.item("CH-0012", size="50", unit="umol")
        self.assertEqual(small.article, large.article)
        self.assertEqual(Article.objects.count(), 1)


class SubstanceThroughTheArticleTests(InventoryCase):

    def test_substance_through_the_article(self) -> None:
        """Scenario: Substance through the article."""
        item = self.item("CH-0012", "Zimtsäure")
        self.assertEqual(item.article.substance.key, "cinnamic-acid")
        root = page(self.client.get(item_url(item)))
        links = [a for a in root.find_all("a")
                 if a.get("href") == SUBSTANCE]
        self.assertTrue(links)
        self.assertIn("Zimtsäure", root.text())

    def test_the_name_links_to_the_substance_in_the_list(self) -> None:
        self.item("CH-0012", "Zimtsäure")
        _, rows = table(page(self.client.get(LIST)))
        cell = rows[0]["Name"]
        self.assertEqual([a.get("href") for a in cell.find_all("a")],
                         [SUBSTANCE])
        self.assertIn("Zimtsäure", cell.text())

    def test_each_size_links_its_substance(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.item("CH-0012", size="50", unit="mg")
        _, rows = table(page(self.client.get(LIST)))
        hrefs = [a.get("href") for row in rows
                 for a in row["Name"].find_all("a")]
        self.assertEqual(hrefs, [SUBSTANCE] * 2)

    def test_the_site_page_is_linked_from_the_substance_alone(self) -> None:
        item = self.item("CH-0012", "Zimtsäure")
        for path in (LIST, item_url(item)):
            with self.subTest(path=path):
                root = page(self.client.get(path))
                self.assertFalse([a for a in root.find_all("a")
                                  if COMPOUND_PAGE.match(a.get("href", ""))])

    def test_the_name_is_german_on_a_german_site(self) -> None:
        item = self.item("CH-0012")
        self.assertEqual(item.article.substance.name_de, "(E)-Zimtsäure")
        _, rows = table(page(self.client.get(LIST)))
        self.assertEqual(rows[0]["Name"].text(), "(E)-Zimtsäure")
