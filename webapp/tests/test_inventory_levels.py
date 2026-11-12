"""Tests of the stock levels (end-product-inventory: Stock levels)."""

from decimal import Decimal

from django.test import SimpleTestCase

from inventory.figures import level

from . import page, table
from .collection_support import accept
from .inventory_support import (LEVELS, LIST, InventoryCase, item_url,
                                num, visible_text)


class LevelFunctionTests(SimpleTestCase):

    def test_thresholds(self) -> None:
        """Scenario: Thresholds."""
        shown = [level(quantity, 4) for quantity in (0, 1, 2, 3, 4, 7, 8)]
        self.assertEqual(
            shown, ["out", "critical", "low", "low", "watch", "watch", "ok"])

    def test_thresholds_follow_the_mean_per_quarter(self) -> None:
        shown = [level(quantity, Decimal("2.5"))
                 for quantity in (0, 1, 2, 3, 4, 5, 6)]
        self.assertEqual(shown, ["out", "critical", "low", "watch",
                                 "watch", "ok", "ok"])

    def test_the_edges_belong_to_the_milder_level(self) -> None:
        self.assertEqual(level(2, 4), "low")
        self.assertEqual(level(4, 4), "watch")
        self.assertEqual(level(8, 4), "ok")

    def test_levels_compare_the_unrounded_mean(self) -> None:
        mean = Decimal("4.04")
        self.assertEqual(level(2, mean), "critical")
        self.assertEqual(level(4, mean), "low")
        self.assertEqual(level(8, mean), "watch")
        self.assertEqual(level(9, mean), "ok")

    def test_without_a_mean_a_stocked_item_is_ok(self) -> None:
        self.assertEqual(level(0, None), "out")
        self.assertEqual(level(2, None), "ok")
        self.assertEqual(level(2, Decimal("0")), "ok")

    def test_set_aside_by_hand(self) -> None:
        """Scenario: Set aside by hand (the rule)."""
        for status in ("not_needed", "discontinued"):
            with self.subTest(status=status):
                self.assertEqual(level(0, 4, status=status), "dormant")
                self.assertEqual(level(1, 4, status=status), "dormant")
                self.assertEqual(level(9, None, status=status,
                                       consumed=False), "dormant")

    def test_nothing_recent_is_dormant(self) -> None:
        self.assertEqual(level(0, 4, recent=False), "dormant")
        self.assertEqual(level(5, 4, recent=False), "dormant")

    def test_no_consumption_is_undelivered(self) -> None:
        self.assertEqual(level(2, None, consumed=False), "undelivered")
        self.assertEqual(level(0, None, consumed=False), "undelivered")

    def test_the_order_of_urgency(self) -> None:
        from inventory.models import LEVEL_ORDER, Level
        self.assertEqual(sorted(Level.values, key=LEVEL_ORDER.get),
                         ["out", "critical", "low", "watch", "ok",
                          "undelivered", "dormant"])


class ItemLevelTests(InventoryCase):

    def test_thresholds_of_items(self) -> None:
        """Scenario: Thresholds (through the items)."""
        expected = {0: "out", 1: "critical", 2: "low", 3: "low",
                    4: "watch", 7: "watch", 8: "ok"}
        for quantity, want in expected.items():
            with self.subTest(quantity=quantity):
                item = self.item(f"L-{quantity}", quantity=quantity)
                self.with_mean_quarter(item, 4)
                self.assertEqual(self.consumption(item).level, want)

    def test_no_consumption(self) -> None:
        """Scenario: No consumption."""
        found = self.consumption(self.item("U-1", quantity=2))
        self.assertEqual(found.level, "undelivered")
        self.assertIsNone(found.coverage)

    def test_entered_zeros_are_no_consumption(self) -> None:
        item = self.item("U-0", quantity=2)
        self.enter_year(item, 2025, 0)
        self.assertEqual(self.consumption(item).level, "undelivered")

    def test_set_aside_by_hand(self) -> None:
        """Scenario: Set aside by hand."""
        from inventory.models import Item
        gone = self.with_mean_quarter(self.item("D-1", quantity=0), 4)
        idle = self.with_mean_quarter(self.item("D-2", quantity=1), 4)
        Item.objects.filter(pk=gone.pk).update(status="discontinued")
        Item.objects.filter(pk=idle.pk).update(status="not_needed")
        for item in (gone, idle):
            with self.subTest(item=item.article.article_number):
                found = self.consumption(item)
                self.assertEqual(found.level, "dormant")
                self.assertIsNone(found.coverage)

    def test_nothing_asked_for_in_two_years(self) -> None:
        """Scenario: Nothing asked for in two years."""
        old = self.item("D-3", quantity=5)
        self.enter(old, 2024, 4, 5)
        recent = self.item("D-4", quantity=5)
        self.enter(recent, 2025, 1, 5)
        self.assertEqual(self.consumption(old).level, "dormant")
        self.assertNotEqual(self.consumption(recent).level, "dormant")

    def test_a_delivery_this_year_wakes_an_item(self) -> None:
        item = self.item("D-5", quantity=5)
        self.enter(item, 2024, 4, 5)
        self.deliver(item, 1)
        self.assertNotEqual(self.consumption(item).level, "dormant")

    def test_the_mean_is_the_mean_of_the_item(self) -> None:
        item = self.item("L-1", quantity=5)
        self.with_mean_quarter(item, 2)
        self.assertEqual(self.consumption(item).level, "ok")
        other = self.item("L-3", quantity=5)
        self.with_mean_quarter(other, 6)
        self.assertEqual(self.consumption(other).level, "low")


class LevelCellTests(InventoryCase):

    def cells(self, language: str = "de") -> dict[str, object]:
        root = page(self.client.get(LIST))
        header, rows = table(root)
        stock = "Bestand" if language == "de" else "Stock"
        return {row[header[0]].text(): row[stock] for row in rows}

    def leveled(self) -> dict[int, object]:
        for quantity in (0, 1, 2, 4, 8):
            self.with_mean_quarter(
                self.item(f"L-{quantity}", quantity=quantity), 4)
        return {int(k[2:]): v for k, v in self.cells().items()}

    def test_the_cell_carries_the_class_and_the_label(self) -> None:
        cells = self.leveled()
        want = {0: "out", 1: "critical", 2: "low", 4: "watch"}
        for quantity, name in want.items():
            with self.subTest(level=name):
                cell = cells[quantity]
                self.assertIn(f"level-{name}", cell.classes)
                self.assertIn(LEVELS[name], cell.text())
                self.assertEqual(num(cell), quantity)

    def test_a_full_stock_is_ok(self) -> None:
        cell = self.leveled()[8]
        self.assertIn("level-ok", cell.classes)
        self.assertEqual(cell.get("title"), LEVELS["ok"])
        self.assertEqual(num(cell), 8)

    def test_numbers_alone(self) -> None:
        """Scenario: Numbers alone."""
        self.with_mean_quarter(self.item("L-3", quantity=3), 4)
        cell = self.cells()["L-3"]
        self.assertIn("level-low", cell.classes)
        self.assertEqual(cell.get("title"), LEVELS["low"])
        hidden = cell.find("span", "visually-hidden")
        self.assertEqual(hidden.text().strip(), LEVELS["low"])
        self.assertEqual(visible_text(cell), "3")

    def test_every_cell_carries_one_level(self) -> None:
        self.leveled()
        self.item("U-1", quantity=2)
        for article, cell in self.cells().items():
            with self.subTest(article=article):
                self.assertEqual(len([c for c in cell.classes
                                      if c.startswith("level-")]), 1)

    def test_an_item_with_a_level_carries_one_class_only(self) -> None:
        cell = self.leveled()[2]
        self.assertEqual([c for c in cell.classes if c.startswith("level-")],
                         ["level-low"])

    def test_english_labels(self) -> None:
        accept(language="en")
        for quantity in (0, 1, 2, 4):
            self.with_mean_quarter(
                self.item(f"L-{quantity}", quantity=quantity), 4)
        cells = {int(k[2:]): v for k, v in self.cells("en").items()}
        for quantity, name in {0: "out", 1: "critical", 2: "low",
                               4: "watch"}.items():
            with self.subTest(level=name):
                self.assertIn(f"level-{name}", cells[quantity].classes)
                self.assertIn(name, cells[quantity].text())

    def test_the_item_page_shows_the_quantity_with_its_level(self) -> None:
        item = self.with_mean_quarter(self.item("L-2", quantity=2), 4)
        root = page(self.client.get(item_url(item)))
        shown = root.find(cls="level-low")
        self.assertIsNotNone(shown)
        self.assertIn(LEVELS["low"], shown.text())
        self.assertEqual(num(shown), 2)
