"""Tests of the stock levels (end-product-inventory: Stock levels)."""

from decimal import Decimal

from django.test import SimpleTestCase

from inventory.figures import level

from . import build_index, compound, page, table, text_field
from .inventory_support import (LEVELS, LIST, InventoryCase, item_url,
                                num)


class LevelFunctionTests(SimpleTestCase):

    def test_thresholds(self) -> None:
        """Scenario: Thresholds."""
        shown = [level(quantity, 4) for quantity in (0, 1, 2, 3, 4, 7, 8)]
        self.assertEqual(
            shown, ["out", "critical", "low", "low", "watch", "watch", None])

    def test_thresholds_follow_the_mean_per_quarter(self) -> None:
        shown = [level(quantity, Decimal("2.5"))
                 for quantity in (0, 1, 2, 3, 4, 5, 6)]
        self.assertEqual(shown, ["out", "critical", "low", "watch",
                                 "watch", None, None])

    def test_the_edges_belong_to_the_milder_level(self) -> None:
        self.assertEqual(level(2, 4), "low")
        self.assertEqual(level(4, 4), "watch")
        self.assertEqual(level(8, 4), None)

    def test_levels_compare_the_unrounded_mean(self) -> None:
        mean = Decimal("4.04")
        self.assertEqual(level(2, mean), "critical")
        self.assertEqual(level(4, mean), "low")
        self.assertEqual(level(8, mean), "watch")
        self.assertEqual(level(9, mean), None)

    def test_without_a_mean_only_an_empty_item_has_a_level(self) -> None:
        self.assertEqual(level(0, None), "out")
        self.assertIsNone(level(2, None))

    def test_a_mean_of_zero_is_no_mean(self) -> None:
        self.assertEqual(level(0, 0), "out")
        self.assertIsNone(level(2, 0))
        self.assertIsNone(level(2, Decimal("0")))


class ItemLevelTests(InventoryCase):

    def test_thresholds_of_items(self) -> None:
        """Scenario: Thresholds (through the items)."""
        expected = {0: "out", 1: "critical", 2: "low", 3: "low",
                    4: "watch", 7: "watch", 8: None}
        for quantity, want in expected.items():
            with self.subTest(quantity=quantity):
                item = self.item(f"L-{quantity}", quantity=quantity)
                self.with_mean_quarter(item, 4)
                self.assertEqual(self.consumption(item).level, want)

    def test_the_mean_is_the_mean_of_the_item(self) -> None:
        item = self.item("L-1", quantity=5)
        self.with_mean_quarter(item, 2)
        self.assertEqual(self.consumption(item).level, None)
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

    def test_an_item_without_a_level_has_no_level_class(self) -> None:
        cell = self.leveled()[8]
        self.assertFalse([c for c in cell.classes if c.startswith("level-")])
        for label in LEVELS.values():
            self.assertNotIn(label, cell.text())
        self.assertEqual(num(cell), 8)

    def test_an_item_with_a_level_carries_one_class_only(self) -> None:
        cell = self.leveled()[2]
        self.assertEqual([c for c in cell.classes if c.startswith("level-")],
                         ["level-low"])

    def test_english_labels(self) -> None:
        self.use_index(build_index("en", [
            compound("cinnamic-acid", name="(E)-Cinnamic acid",
                     item_number="CH-0012")],
            fields=[text_field("item_number")]))
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
