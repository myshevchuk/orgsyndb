"""Tests of the inventory's items (end-product-inventory: Items)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import Refused, create_item
from inventory.models import END_PRODUCTS, Item, Movement, Unit

from . import page, table
from .inventory_support import (COMPOUND_PAGE, LIST, MICRO, InventoryCase,
                                fresh, item_url, snapshot)


class FieldTests(InventoryCase):

    def test_an_item_keeps_its_fields(self) -> None:
        made = create_item(
            self.kl, article_number="CH-0012", name="Zimtsäure",
            category="Endprodukt", size=Decimal("2.5"), unit="mg",
            quantity=7, note="Notiz")
        item = Item.objects.get(pk=made.pk)
        self.assertEqual(item.inventory, END_PRODUCTS)
        self.assertEqual(END_PRODUCTS, "end-products")
        self.assertEqual(
            (item.article_number, item.name, item.category, item.unit,
             item.quantity, item.note),
            ("CH-0012", "Zimtsäure", "Endprodukt", "mg", 7, "Notiz"))
        self.assertEqual(item.size, Decimal("2.5"))

    def test_category_and_note_are_optional(self) -> None:
        item = create_item(self.kl, article_number="CH-0012", name="Z",
                           size=Decimal("1"), unit="g", quantity=1)
        self.assertEqual((item.category, item.note), ("", ""))

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

    def test_a_negative_quantity_is_refused(self) -> None:
        before = snapshot()
        with self.assertRaises(Refused):
            self.item("Q-1", quantity=-1)
        self.assertEqual(snapshot(), before)


class IdentityTests(InventoryCase):

    def test_one_article_in_two_sizes(self) -> None:
        """Scenario: One article in two sizes."""
        self.item("CH-0012", size="10", unit="umol")
        self.item("CH-0012", size="50", unit="umol")
        before = snapshot()
        with self.assertRaises(Refused):
            self.item("CH-0012", size="10", unit="umol")
        self.assertEqual(snapshot(), before)
        self.assertEqual(Item.objects.count(), 2)

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
        with self.assertRaises(Refused):
            self.item("CH-0012", size="10.000", unit="mg")


class OpeningTests(InventoryCase):

    def test_the_opening_count_is_the_first_movement(self) -> None:
        item = create_item(self.kl, article_number="CH-0012", name="Z",
                           size=Decimal("10"), unit="umol", quantity=12)
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

    def test_an_empty_item_has_an_opening_movement_too(self) -> None:
        movement = self.item("Q-0", quantity=0).movements.get()
        self.assertEqual((movement.kind, movement.count), ("opening", 0))

    def test_the_opening_date_may_be_given(self) -> None:
        item = self.item("CH-0012", day=date(2025, 3, 12))
        self.assertEqual(item.movements.get().date, date(2025, 3, 12))

    def test_the_opening_date_is_never_after_today(self) -> None:
        before = snapshot()
        with self.assertRaises(Refused):
            self.item("CH-0012", day=date(2026, 11, 5))
        self.assertEqual(snapshot(), before)

    def test_the_booking_user_is_in_the_history(self) -> None:
        item = self.item("CH-0012")
        entry = item.history.get()
        self.assertEqual(entry.history_user, self.kl)
        self.assertEqual(entry.history_type, "+")


class CompoundTests(InventoryCase):

    def test_compound_through_the_article_number(self) -> None:
        """Scenario: Compound through the article number."""
        item = self.item("CH-0012", name="Zimtsäure")
        root = page(self.client.get(item_url(item)))
        links = [a for a in root.find_all("a")
                 if a.get("href") == "/compounds/cinnamic-acid/"]
        self.assertTrue(links)
        self.assertIn("(E)-Zimtsäure", root.text())

    def test_the_name_links_to_the_compound_in_the_list(self) -> None:
        self.item("CH-0012", name="Zimtsäure")
        _, rows = table(page(self.client.get(LIST)))
        cell = rows[0]["Name"]
        links = [a for a in cell.find_all("a")
                 if COMPOUND_PAGE.match(a.get("href", ""))]
        self.assertEqual([a.get("href") for a in links],
                         ["/compounds/cinnamic-acid/"])
        self.assertIn("Zimtsäure", cell.text())

    def test_an_article_links_its_compound_once(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.item("CH-0012", size="50", unit="mg")
        _, rows = table(page(self.client.get(LIST)))
        hrefs = [a.get("href") for row in rows
                 for a in row["Name"].find_all("a")
                 if COMPOUND_PAGE.match(a.get("href", ""))]
        self.assertEqual(hrefs, ["/compounds/cinnamic-acid/"])
        self.assertIn("same-article", rows[1]["Name"].parent.classes)

    def test_an_article_outside_the_collection_has_no_compound(
            self) -> None:
        item = self.item("X-9999", name="Neu")
        for path in (LIST, item_url(item)):
            with self.subTest(path=path):
                root = page(self.client.get(path))
                self.assertFalse([a for a in root.find_all("a")
                                  if COMPOUND_PAGE.match(a.get("href", ""))])
