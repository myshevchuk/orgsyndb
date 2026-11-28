"""Tests of the pages that show the stock by batch: the item page, the
delivery note and its list, and the batch page (end-product-inventory:
Item page, Delivery list, Batch page, Delivery notes)."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from inventory.bookings import (book_note, correct, fill, reverse,
                                reverse_historical)

from . import Element, make_batch, page
from .inventory_support import (InventoryCase, batch_url, count_after,
                                count_beside, has_number, item_url, ledger,
                                movement_url, note_url, set_shares)
from .main_lists_support import must_pane, row_for


class StockPageCase(InventoryCase):
    """Two batches of ``cinnamic-acid``."""

    def setUp(self) -> None:
        super().setUp()
        self.a = self.batch("CH-0012", number="KL0412")
        self.b = self.batch("CH-0012", number="KL0413")

    def show(self, path: str) -> Element:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def vessel_of(self, batch: Any) -> Any:
        """A stored vessel of ``batch`` that a filling with the amount
        1 empties, so that it is no open bulk."""
        return self.vessel("CH-0012", "g", "1", batch=batch)

    def filled(self, item: Any, count: int, batch: Any) -> Any:
        return fill(self.kl, item, count=count, vessel=self.vessel_of(batch),
                    amount=Decimal("1"))

    def in_ledger(self, root: Element) -> Callable[[Element], bool]:
        """A predicate that tells the rows of the movements on an item
        page."""
        rows = [row for _, row in ledger(root)]
        return lambda node: any(node is row for row in rows)

    def share_shown(self, root: Element, name: str, others: list[str]
                    ) -> int | None:
        """The count an item page shows with ``name``, the number of a
        batch or ``unbekannt``, outside its movements."""
        skip = self.in_ledger(root)

        def deepest(node: Element) -> bool:
            return "unbekannt" in node.text(skip) and not any(
                isinstance(child, Element) and "unbekannt" in child.text(skip)
                for child in node.children)

        main = root.find("main")
        found = ([a for a in main.find_all("a") if a.text() == name
                  and not self.within(a, skip)] if name != "unbekannt"
                 else [e for e in main.walk() if deepest(e)])
        for node in found:
            count = count_beside(node, name, others, skip)
            if count is not None:
                return count
        return None

    @staticmethod
    def within(node: Element, skip: Callable[[Element], bool]) -> bool:
        while node is not None:
            if skip(node):
                return True
            node = node.parent
        return False


class ItemPageStockTests(StockPageCase):

    def test_the_containers_by_batch(self) -> None:
        """Scenario: Containers by batch."""
        item = self.item("CH-0012", quantity=2)
        self.filled(item, 3, self.a)
        root = self.show(item_url(item))
        self.assertEqual(
            self.share_shown(root, "KL0412", ["unbekannt", "KL0413"]), 3)
        self.assertEqual(
            self.share_shown(root, "unbekannt", ["KL0412", "KL0413"]), 2)
        self.assertNotIn("KL0413", root.text())

    def test_the_batch_links_to_its_page(self) -> None:
        item = self.item("CH-0012", quantity=0)
        self.filled(item, 3, self.a)
        root = self.show(item_url(item))
        skip = self.in_ledger(root)
        links = [a for a in root.find("main").find_all("a")
                 if a.get("href") == batch_url(self.a)
                 and not self.within(a, skip)]
        self.assertTrue(links, "KL0412 is not among the containers")

    def test_a_batch_without_containers_is_not_among_them(self) -> None:
        item = self.item("CH-0012", quantity=0)
        self.filled(item, 3, self.a)
        book_note(self.kl, date=date(2026, 11, 1),
                  lines=[(item, self.a, 3)])
        root = self.show(item_url(item))
        skip = self.in_ledger(root)
        self.assertEqual(
            [a for a in root.find("main").find_all("a")
             if a.get("href") == batch_url(self.a)
             and not self.within(a, skip)], [])

    def test_no_containers_of_unknown_batch_are_not_listed(self) -> None:
        item = self.item("CH-0012", quantity=0)
        self.filled(item, 3, self.a)
        root = self.show(item_url(item))
        skip = self.in_ledger(root)
        self.assertNotIn("unbekannt", root.find("main").text(skip))

    def test_the_ledger_shows_the_batch_of_each_movement(self) -> None:
        item = self.item("CH-0012", quantity=5)
        self.filled(item, 1, self.a)
        book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                  lines=[(item, self.a, 3)])
        correct(self.kl, item, count=1, note="gezählt")
        rows = dict(ledger(self.show(item_url(item))))
        self.assertIn("unbekannt", rows["opening"].text())
        self.assertIn("unbekannt", rows["correction"].text())
        for kind in ("filling", "delivery", "assignment"):
            with self.subTest(kind=kind):
                self.assertIsNotNone(rows[kind].find(
                    "a", href=batch_url(self.a)))
                self.assertNotIn("unbekannt", rows[kind].text())

    def test_an_assignment_is_a_row_of_its_own(self) -> None:
        item = self.item("CH-0012", quantity=5)
        self.filled(item, 1, self.a)
        book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                  recipient="Produktion", lines=[(item, self.a, 3)])
        rows = ledger(self.show(item_url(item)))
        self.assertEqual([kind for kind, _ in rows],
                         ["delivery", "assignment", "filling", "opening"])
        delivery, assignment = rows[0][1], rows[1][1]
        for row in (delivery, assignment):
            with self.subTest(row=row.text()):
                self.assertIn("LS-1", row.text())
                self.assertIn("Produktion", row.text())
        self.assertTrue(has_number(assignment.text(), "2"))
        self.assertTrue(has_number(assignment.text(), "6"))
        self.assertTrue(has_number(delivery.text(), "3"))

    def test_an_assignment_is_not_offered_for_reversal(self) -> None:
        item = self.item("CH-0012", quantity=5)
        book_note(self.kl, date=date(2026, 11, 2),
                  lines=[(item, self.a, 3)])
        delivery, assignment = item.movements.order_by("-pk")[:2]
        self.client.force_login(self.kl)
        root = self.show(item_url(item))
        reversals = [a.get("href") for a in root.find_all("a")
                     if a.get("href", "").endswith("/reverse/")
                     and "/movements/" in a.get("href", "")]
        self.assertEqual(reversals, [movement_url(delivery)])

    def test_a_reversed_delivery_is_marked_and_its_assignment_is_not(
            self) -> None:
        item = self.item("CH-0012", quantity=5)
        book_note(self.kl, date=date(2026, 11, 2),
                  lines=[(item, self.a, 3)])
        reverse(self.kl, item.movements.get(kind="delivery"),
                note="falsch gebucht")
        rows = ledger(self.show(item_url(item)))
        self.assertEqual([kind for kind, _ in rows],
                         ["reversal", "delivery", "assignment", "opening"])
        by_kind = dict(rows)
        self.assertIn("storniert", by_kind["delivery"].text())
        self.assertNotIn("storniert", by_kind["assignment"].text())
        self.assertIsNotNone(by_kind["reversal"].find(
            "a", href=batch_url(self.a)))

    def test_the_containers_follow_a_reversed_delivery(self) -> None:
        item = self.item("CH-0012", quantity=5)
        book_note(self.kl, date=date(2026, 11, 2),
                  lines=[(item, self.a, 3)])
        reverse(self.kl, item.movements.get(kind="delivery"), note="falsch")
        root = self.show(item_url(item))
        self.assertEqual(self.share_shown(root, "KL0412", ["unbekannt"]), 3)
        self.assertEqual(self.share_shown(root, "unbekannt", ["KL0412"]), 2)


class NotePageStockTests(StockPageCase):

    def row_of(self, note: Any) -> str:
        """The text of the row of NOTE in the delivery list's table."""
        root = self.show("/lab/inventory/deliveries/")
        return row_for(root, str(note.pk)).text()

    def details_of(self, note: Any) -> Element:
        """The details pane of the delivery list with NOTE selected."""
        return must_pane(self.show(
            f"/lab/inventory/deliveries/?selected={note.pk}"))

    def lines_of(self, root: Element, *batches: Any) -> list[Element]:
        """The first row of a note's page that links each batch of
        BATCHES, in their order."""
        return [next(a.closest("tr") for a in root.find_all("a")
                     if a.get("href") == batch_url(batch))
                for batch in batches]

    def test_the_lines_name_their_batch(self) -> None:
        """Scenario: Lines name their batch."""
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2026, 11, 2),
                         number="LS-2026-117", lines=[(item, self.a, 2)])
        link = self.show(note_url(note)).find("a", href=batch_url(self.a))
        self.assertIsNotNone(link)
        self.assertEqual(link.text(), "KL0412")
        self.assertNotIn("KL0412", self.row_of(note))
        details = self.details_of(note)
        self.assertEqual(
            [a.text() for a in details.find_all("a")
             if a.get("href") == batch_url(self.a)], ["KL0412"])

    def test_a_bought_batch_is_shown_by_its_supplier_batch(self) -> None:
        bought = make_batch(self.kl, "CH-0012", source="bought",
                            supplier="Sigma", supplier_batch="MK99")
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                         lines=[(item, bought, 2)])
        link = self.show(note_url(note)).find("a", href=batch_url(bought))
        self.assertEqual(link.text(), "MK99")
        self.assertNotIn("MK99", self.row_of(note))
        self.assertEqual(
            [a.text() for a in self.details_of(note).find_all("a")
             if a.get("href") == batch_url(bought)], ["MK99"])

    def test_the_lines_of_one_item_show_each_batch(self) -> None:
        item = self.item("CH-0012", quantity=0)
        set_shares(item, (self.a, 2), (self.b, 3))
        note = book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                         lines=[(item, self.a, 2), (item, self.b, 3)])
        first, second = self.lines_of(self.show(note_url(note)), self.a,
                                      self.b)
        self.assertIsNot(first, second)
        self.assertTrue(has_number(first.text(), "2"), first.text())
        self.assertTrue(has_number(second.text(), "3"), second.text())
        row = self.row_of(note)
        self.assertNotIn("KL0412", row)
        self.assertNotIn("KL0413", row)
        first, second = self.lines_of(self.details_of(note), self.a, self.b)
        self.assertIsNot(first, second)
        self.assertTrue(has_number(first.text(), "2"), first.text())
        self.assertTrue(has_number(second.text(), "3"), second.text())

    def test_the_lines_of_a_historical_note_name_their_batch(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         number="ALT-1", lines=[(item, self.a, 4)])
        root = self.show(note_url(note))
        self.assertIsNotNone(root.find("a", href=batch_url(self.a)))
        self.assertIn("nachgetragen", root.text())
        self.assertNotIn("KL0412", self.row_of(note))
        self.assertIsNotNone(
            self.details_of(note).find("a", href=batch_url(self.a)))
        self.assertIn("nachgetragen", self.row_of(note))

    def test_a_line_shows_its_delivery_not_its_assignment(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2026, 11, 2),
                         lines=[(item, self.a, 3)])
        (row,) = self.lines_of(self.show(note_url(note)), self.a)
        self.assertIn("Abgabe", row.text())
        self.assertNotIn("Zuordnung", row.text())
        self.assertNotIn("storniert", row.text())

    def test_one_of_two_batch_lines_reversed(self) -> None:
        """Scenario: One of two batch lines reversed."""
        item = self.item("CH-0012", quantity=0)
        set_shares(item, (self.a, 2), (self.b, 3))
        note = book_note(self.kl, date=date(2026, 8, 12), number="LS-1",
                         lines=[(item, self.a, 2), (item, self.b, 3)])
        reverse(self.kl, item.movements.get(kind="delivery", batch=self.a),
                note="falsch gebucht")
        self.assertEqual(self.consumption(item).quarters[(2026, 3)], 3)
        root = self.show(note_url(note))
        self.assertIn("teilweise storniert", root.text())
        first, second = self.lines_of(root, self.a, self.b)
        self.assertIn("storniert", first.text())
        self.assertNotIn("storniert", second.text())
        self.assertIn("teilweise storniert", self.row_of(note))

    def test_a_note_with_an_assignment_is_not_reversed(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                         lines=[(item, self.a, 3)])
        self.assertNotIn("storniert", self.show(note_url(note)).text())
        self.assertNotIn("storniert", self.row_of(note))

    def test_a_note_whose_deliveries_are_reversed_is_reversed(self) -> None:
        first = self.item("CH-0012", quantity=5)
        second = self.item("CH-0012", size="50", quantity=5)
        note = book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                         lines=[(first, self.a, 2), (second, self.a, 1)])
        for each in (first, second):
            reverse(self.kl, each.movements.get(kind="delivery"),
                    note="falsch")
        text = self.show(note_url(note)).text()
        self.assertIn("storniert", text)
        self.assertNotIn("teilweise", text)
        self.assertIn("storniert", self.row_of(note))
        self.assertNotIn("teilweise", self.row_of(note))

    def test_a_note_with_one_delivery_reversed_is_partly_reversed(
            self) -> None:
        first = self.item("CH-0012", quantity=5)
        second = self.item("CH-0012", size="50", quantity=5)
        note = book_note(self.kl, date=date(2026, 11, 2), number="LS-1",
                         lines=[(first, self.a, 2), (second, self.a, 1)])
        reverse(self.kl, first.movements.get(kind="delivery"), note="falsch")
        self.assertIn("teilweise storniert", self.row_of(note))

    def test_a_reversed_historical_note_marks_its_lines(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         number="ALT-1",
                         lines=[(item, self.a, 4), (item, self.b, 1)])
        reverse_historical(self.kl, note, note="doppelt erfasst")
        self.assertIn("storniert", self.row_of(note))
        self.assertIn("storniert", self.show(note_url(note)).text())


class BatchPageStockTests(StockPageCase):

    def links_to(self, root: Element, item: Any) -> list[Element]:
        return [a for a in root.find("main").find_all("a")
                if a.get("href") == item_url(item)]

    def test_the_items_holding_containers_of_the_batch(self) -> None:
        first = self.item("CH-0012", quantity=0)
        second = self.item("CH-0012", size="50", quantity=0)
        empty = self.item("CH-0012", size="100", quantity=0)
        other = self.item("CH-0012", size="200", quantity=0)
        set_shares(first, (self.a, 3))
        set_shares(second, (self.a, 2), (None, 4))
        set_shares(other, (self.b, 5))
        from inventory.models import BatchStock
        BatchStock.objects.create(item=empty, batch=self.a, quantity=0)
        root = self.show(batch_url(self.a))
        for item, held in ((first, 3), (second, 2)):
            with self.subTest(item=item.pk):
                (link,) = self.links_to(root, item)
                self.assertEqual(
                    count_beside(link, link.text(), []), held)
        for item in (empty, other):
            with self.subTest(item=item.pk, listed=False):
                self.assertEqual(self.links_to(root, item), [])

    def test_where_a_batch_went(self) -> None:
        """Scenario: Where a batch went (the items and the lines)."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        vessel = self.vessel("CH-0012", "g", "2", batch=self.a)
        fill(self.kl, item, count=5, vessel=vessel, amount=Decimal("1"))
        note = book_note(self.kl, date=date(2026, 10, 15),
                         number="LS-2026-117", recipient="Produktion",
                         lines=[(item, self.a, 2)])
        old = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                        number="ALT-1", recipient="Labor",
                        lines=[(item, self.a, 1)])
        root = self.show(batch_url(self.a))
        delivered = next(a for a in root.find_all("a")
                         if a.get("href") == note_url(note)).closest("tr")
        self.assertIn("Produktion", delivered.text())
        self.assertIsNotNone(delivered.find("a", href=item_url(item)))
        self.assertTrue(has_number(delivered.text().replace(
            "LS-2026-117", ""), "2"), delivered.text())
        self.assertNotIn("nachgetragen", delivered.text())
        entered = next(a for a in root.find_all("a")
                       if a.get("href") == note_url(old)).closest("tr")
        self.assertIn("nachgetragen", entered.text())
        self.assertIn("Labor", entered.text())
        holding = [
            a for a in self.links_to(root, item)
            if not any(mark in (a.closest("tr") or a.parent).text()
                       for mark in ("LS-2026-117", "ALT-1",
                                    f"#{vessel.pk}"))]
        self.assertEqual(len(holding), 1)
        self.assertEqual(count_beside(holding[0], holding[0].text(), []), 3)

    def test_the_lines_come_newest_first_with_their_marks(self) -> None:
        item = self.item("CH-0012", quantity=0)
        set_shares(item, (self.a, 9))
        gone = book_note(self.kl, date=date(2025, 3, 2), historical=True,
                         number="H-2", lines=[(item, self.a, 1)])
        reverse_historical(self.kl, gone, note="falsch")
        kept = book_note(self.kl, date=date(2026, 3, 1), historical=True,
                         number="H-1", lines=[(item, self.a, 1)])
        undone = book_note(self.kl, date=date(2026, 10, 1), number="C-1",
                           lines=[(item, self.a, 1)])
        reverse(self.kl, item.movements.get(kind="delivery"), note="falsch")
        newest = book_note(self.kl, date=date(2026, 10, 15), number="C-2",
                           lines=[(item, self.a, 1)])
        root = self.show(batch_url(self.a))
        wanted = [newest, undone, kept, gone]
        order = [a.get("href") for a in root.find_all("a")
                 if a.get("href") in {note_url(n) for n in wanted}]
        self.assertEqual(order, [note_url(n) for n in wanted])
        rows = {a.text(): a.closest("tr").text() for a in root.find_all("a")
                if a.get("href") in {note_url(n) for n in wanted}}
        self.assertNotIn("storniert", rows["C-2"])
        self.assertNotIn("nachgetragen", rows["C-2"])
        self.assertIn("storniert", rows["C-1"])
        self.assertIn("nachgetragen", rows["H-1"])
        self.assertNotIn("storniert", rows["H-1"])
        self.assertIn("nachgetragen", rows["H-2"])
        self.assertIn("storniert", rows["H-2"])

    def test_a_line_of_a_historical_note_is_listed(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         number="ALT-1", lines=[(item, self.a, 4)])
        root = self.show(batch_url(self.a))
        self.assertIsNotNone(root.find("a", href=note_url(note)))
