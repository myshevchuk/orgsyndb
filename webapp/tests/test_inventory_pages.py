"""Tests of the item, bulk lot and delivery note pages (end-product-
inventory: Item page, Bulk lot page, Delivery list)."""

from collections import Counter
from datetime import date
from decimal import Decimal

from inventory.bookings import (book_note, correct, correct_lot, fill, reverse,
                                reverse_historical)

from . import page
from .inventory_support import (InventoryCase, MICRO, cells,
                                has_amount, has_number, item_url, ledger,
                                lot_url, movement_url, note_url, num)

QUARTERS = [(year, quarter) for year in (2024, 2025, 2026)
            for quarter in (1, 2, 3, 4)]


class PageCase(InventoryCase):

    def show(self, path: str):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return page(response)


class ItemHeadTests(PageCase):

    def test_the_heading_and_the_record(self) -> None:
        item = self.item("CH-0012", name="Zimtsäure", size="2.5",
                         unit="mg", quantity=7, category="Endprodukt",
                         note="Zeile eins")
        root = self.show(item_url(item))
        heading = root.find("h1").text()
        self.assertIn("CH-0012", heading)
        self.assertIn("Zimtsäure", heading)
        text = root.text()
        for expected in ("Endprodukt", "Zeile eins"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "2,5", "mg"), text)
        hrefs = [a.get("href") for a in root.find_all("a")]
        self.assertIn("/lab/registry/substances/cinnamic-acid/", hrefs)
        self.assertNotIn("/compounds/cinnamic-acid/", hrefs)

    def test_the_substance_is_named_by_language(self) -> None:
        from . import build_index
        item = self.item("CH-0012")
        self.assertIn("(E)-Zimtsäure", self.show(item_url(item)).text())
        self.use_index(build_index("en"))
        self.assertIn("(E)-Cinnamic acid",
                      self.show(item_url(item)).text())

    def test_the_figures(self) -> None:
        item = self.means_item("CH-0012", name="Zimtsäure")
        text = self.show(item_url(item)).text()
        self.assertTrue(has_number(text, "4,5"), text)
        self.assertTrue(has_number(text, "0,7"), text)
        self.assertRegex(text, r"(?<![\d,.])18(,0)?(?![\d,])")
        self.assertTrue(has_number(text, "13"), text)

    def test_the_english_page(self) -> None:
        from . import build_index
        self.use_index(build_index("en"))
        item = self.means_item("CH-0012")
        text = self.show(item_url(item)).text()
        self.assertIn("4.5", text)
        self.assertIn("0.7", text)

    def test_an_unknown_item_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/items/9999/").status_code, 404)

    def test_an_item_keeps_a_history(self) -> None:
        item = self.item("CH-0012")
        text = self.show(item_url(item)).text()
        self.assertIn("Angelegt", text)
        self.assertIn("KL", text)


class ChartTests(PageCase):

    def chart_item(self, article: str = "CH-0012"):
        item = self.item(article, name="Zimtsäure", quantity=40)
        self.enter(item, 2025, 1, 11)
        self.enter(item, 2025, 2, 13)
        self.enter(item, 2025, 3, 17)
        self.deliver(item, 7, date(2026, 2, 10), number="LS-1")
        self.deliver(item, 9, date(2026, 8, 20), number="LS-2")
        return item

    EXPECTED = {(2024, 1): 0, (2024, 2): 0, (2024, 3): 0, (2024, 4): 0,
                (2025, 1): 11, (2025, 2): 13, (2025, 3): 17, (2025, 4): 0,
                (2026, 1): 7, (2026, 2): 0, (2026, 3): 9, (2026, 4): 0}

    def bars(self, root) -> list[str]:
        svg = root.find("svg")
        self.assertIsNotNone(svg, "the page draws no chart")
        return [t.text() for t in svg.find_all("title")
                if t.parent is not svg]

    def test_chart_and_ledger(self) -> None:
        """Scenario: Chart and ledger."""
        root = self.show(item_url(self.chart_item()))
        titles = self.bars(root)
        self.assertEqual(len(titles), 12)
        for (year, _), total in sorted(self.EXPECTED.items()):
            matching = [t for t in titles
                        if str(year) in t and has_number(t, str(total))]
            self.assertTrue(matching, f"no bar for {year}: {total}")
            titles.remove(matching[0])
        self.assertEqual(titles, [])
        kinds = [kind for kind, _ in ledger(root)]
        self.assertEqual(kinds, ["delivery", "delivery", "opening"])

    def test_the_bars_have_distinct_titles(self) -> None:
        titles = self.bars(self.show(item_url(self.chart_item())))
        self.assertEqual(len(set(titles)), 12)

    def test_the_table_lists_the_same_values(self) -> None:
        root = self.show(item_url(self.chart_item()))
        grids = [t for t in root.find_all("table")
                 if len([r for r in t.find_all("tr") if r.find("td")]) == 12]
        self.assertEqual(len(grids), 1)
        triples = []
        for row in grids[0].find_all("tr"):
            if not row.find("td"):
                continue
            last = [num(c) or Decimal(0) for c in cells(row)[-3:]]
            triples.append(tuple(int(v) for v in last))
        expected = [(0, 0, 0)] * 4 + [(11, 0, 11), (13, 0, 13), (17, 0, 17),
                                      (0, 0, 0), (0, 7, 7), (0, 0, 0),
                                      (0, 9, 9), (0, 0, 0)]
        self.assertEqual(Counter(triples), Counter(expected))

    def test_the_mean_is_drawn_as_a_line(self) -> None:
        with_mean = self.show(item_url(self.chart_item("CH-0012")))
        item = self.item("CH-0013", quantity=40)
        self.enter_year(item, 2026, 0)
        without = self.show(item_url(item))
        tags = ("line", "polyline", "path")
        self.assertGreater(len(with_mean.find("svg").find_all(tags)),
                           len(without.find("svg").find_all(tags)))
        self.assertEqual(len(self.bars(without)), 12)

    def test_an_item_without_data_still_has_twelve_bars(self) -> None:
        root = self.show(item_url(self.item("CH-0014")))
        self.assertEqual(len(self.bars(root)), 12)


class LedgerTests(PageCase):

    def booked(self):
        item = self.item("CH-0012", quantity=10)
        filling = fill(self.kl, item, count=4, note="Charge 7")
        delivery = self.deliver_movement(item, 2)
        correction = correct(self.kl, item, count=9, note="gezählt")
        return item, filling, delivery, correction

    def test_the_movements_come_newest_first(self) -> None:
        item, *_ = self.booked()
        kinds = [kind for kind, _ in ledger(self.show(item_url(item)))]
        self.assertEqual(kinds, ["correction", "delivery", "filling",
                                 "opening"])

    def test_booking_order_decides_not_the_date(self) -> None:
        item = self.item("CH-0012", quantity=10)
        self.deliver(item, 1, date(2026, 10, 15), number="LS-LATE")
        self.deliver(item, 2, date(2026, 8, 1), number="LS-EARLY")
        rows = ledger(self.show(item_url(item)))
        self.assertEqual([kind for kind, _ in rows],
                         ["delivery", "delivery", "opening"])
        self.assertIn("LS-EARLY", rows[0][1].text())
        self.assertIn("LS-LATE", rows[1][1].text())

    def test_a_row_shows_the_booking(self) -> None:
        item = self.item("CH-0012", quantity=10)
        self.deliver(item, 2, date(2026, 10, 15), number="LS-9",
                     recipient="Produktion", note="Eilig", user=self.ae)
        _, row = ledger(self.show(item_url(item)))[0]
        text = row.text()
        for expected in ("15.10.2026", "AE", "LS-9", "Produktion", "Eilig"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_number(text, "2"), text)
        self.assertTrue(has_number(text, "8"), text)

    def test_notes_and_counts_of_the_other_kinds(self) -> None:
        item, *_ = self.booked()
        rows = dict(ledger(self.show(item_url(item))))
        self.assertIn("gezählt", rows["correction"].text())
        self.assertTrue(has_number(rows["correction"].text(), "9"))
        self.assertIn("Charge 7", rows["filling"].text())
        self.assertTrue(has_number(rows["filling"].text(), "14"))
        self.assertTrue(has_number(rows["opening"].text(), "10"))
        self.assertIn("KL", rows["opening"].text())

    def test_a_reversed_movement_is_marked(self) -> None:
        item, filling, delivery, _ = self.booked()
        reverse(self.kl, delivery, note="falsch gebucht")
        rows = ledger(self.show(item_url(item)))
        self.assertEqual([kind for kind, _ in rows],
                         ["reversal", "correction", "delivery", "filling",
                          "opening"])
        by_kind = {kind: row for kind, row in rows}
        self.assertIn("storniert", by_kind["delivery"].text())
        self.assertNotIn("storniert", by_kind["filling"].text())
        self.assertIn("falsch gebucht", by_kind["reversal"].text())

    def test_the_actions_of_a_signed_in_user(self) -> None:
        item, filling, delivery, correction = self.booked()
        self.assertFalse(self.actions(item))
        self.client.force_login(self.kl)
        links = self.actions(item)
        self.assertEqual(links, {
            "Abgabe buchen": f"/lab/inventory/deliveries/new/?item={item.pk}",
            "Abfüllen": item_url(item, "fill"),
            "Bestand korrigieren": item_url(item, "correct"),
            "Verbrauch nachtragen": item_url(item, "consumption"),
            "Bearbeiten": item_url(item, "edit")})
        reversals = self.reversals(item)
        self.assertEqual(
            sorted(reversals), sorted([movement_url(filling),
                                       movement_url(delivery)]))

    def test_a_reversed_movement_offers_no_reversal(self) -> None:
        item, filling, delivery, _ = self.booked()
        reverse(self.kl, delivery, note="falsch")
        self.client.force_login(self.kl)
        self.assertEqual(self.reversals(item), [movement_url(filling)])

    def test_english_links(self) -> None:
        from . import build_index
        self.use_index(build_index("en"))
        item, *_ = self.booked()
        self.client.force_login(self.kl)
        self.assertEqual(
            set(self.actions(item)),
            {"Book delivery", "Fill", "Correct count", "Enter consumption",
             "Edit"})

    def actions(self, item) -> dict[str, str]:
        wanted = {"Abgabe buchen", "Abfüllen", "Bestand korrigieren",
                  "Verbrauch nachtragen", "Bearbeiten", "Book delivery",
                  "Fill", "Correct count", "Enter consumption", "Edit"}
        root = self.show(item_url(item))
        return {a.text(): a.get("href") for a in root.find_all("a")
                if a.text() in wanted}

    def reversals(self, item) -> list[str]:
        root = self.show(item_url(item))
        return [a.get("href") for a in root.find_all("a")
                if a.get("href", "").endswith("/reverse/")
                and "/movements/" in a.get("href", "")]


class ItemHistoryTests(PageCase):

    def test_a_change_is_in_the_history(self) -> None:
        item = self.item("CH-0012", note="alt")
        self.client.force_login(self.ae)
        self.client.post(item_url(item, "edit"), {
            "category": "", "note": "neu", "status": "active",
            "stocked_on": "2019-01-02"})
        text = self.show(item_url(item)).text()
        for expected in ("alt", "neu", "AE", "KL", "Angelegt"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertLess(text.find("neu"), text.rfind("Angelegt"))


class LotPageTests(PageCase):

    def filled(self):
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        lot = self.lot("CH-0012", "mg", "50", batch="B-1",
                       location="Kühlraum", made_on=date(2026, 10, 1),
                       note="Rest")
        fill(self.kl, item, count=5, lot=lot)
        return item, lot

    def test_the_record(self) -> None:
        _, lot = self.filled()
        text = self.show(lot_url(lot)).text()
        for expected in ("CH-0012", "B-1", "Kühlraum", "01.10.2026", "Rest"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "42,592", "mg"), text)
        self.assertNotIn("aufgebraucht", text)

    def test_the_substance_the_source_and_the_supplier(self) -> None:
        self.item("CH-0012")
        lot = self.lot("CH-0012", "mg", "5", source="bought",
                       supplier="Sigma")
        root = self.show(lot_url(lot))
        self.assertIn("/lab/registry/substances/cinnamic-acid/",
                      [a.get("href") for a in root.find_all("a")])
        text = root.text()
        for expected in ("(E)-Zimtsäure", "CH-0012", "gekauft", "Sigma"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_a_lot_of_a_substance_without_an_article(self) -> None:
        lot = self.lot("acetophenone", "mg", "5", source="made")
        root = self.show(lot_url(lot))
        self.assertIn("/lab/registry/substances/acetophenone/",
                      [a.get("href") for a in root.find_all("a")])
        self.assertIn("hergestellt", root.text())
        self.assertNotRegex(root.text(), r"[A-Z]{2}-\d{4}")

    def test_lot_page_after_a_filling(self) -> None:
        """Scenario: Lot page after a filling."""
        item, lot = self.filled()
        rows = ledger(self.show(lot_url(lot)))
        self.assertEqual([kind for kind, _ in rows], ["filling", "opening"])
        newest = rows[0][1]
        self.assertIn(item_url(item),
                      [a.get("href") for a in newest.find_all("a")])
        text = newest.text()
        self.assertTrue(has_number(text, "7,408"), text)
        self.assertTrue(has_number(text, "42,592"), text)
        self.assertIn("KL", text)
        opening = rows[1][1].text()
        self.assertTrue(has_number(opening, "50"), opening)

    def test_a_used_up_lot_is_marked(self) -> None:
        lot = self.lot("CH-0012", "mg", "5")
        correct_lot(self.kl, lot, amount=Decimal("0"), note="leer")
        text = self.show(lot_url(lot)).text()
        self.assertIn("aufgebraucht", text)

    def test_the_amount_shows_in_the_unit_of_the_lot(self) -> None:
        lot = self.lot("X-1", "mmol", "2.5")
        self.assertTrue(has_amount(self.show(lot_url(lot)).text(), "2,5",
                                   "mmol"))

    def test_corrections_and_reversals_are_listed(self) -> None:
        item, lot = self.filled()
        correct_lot(self.kl, lot, amount=Decimal("40"), note="nachgewogen")
        reverse(self.kl, item.movements.get(kind="filling"), note="doppelt")
        rows = ledger(self.show(lot_url(lot)))
        self.assertEqual([kind for kind, _ in rows],
                         ["reversal", "correction", "filling", "opening"])
        self.assertIn("nachgewogen", rows[1][1].text())

    def test_the_actions_of_a_signed_in_user(self) -> None:
        lot = self.lot()
        root = self.show(lot_url(lot))
        self.assertIsNone(root.find("a", href=lot_url(lot, "correct")))
        self.assertIsNone(root.find("a", href=lot_url(lot, "edit")))
        self.client.force_login(self.kl)
        root = self.show(lot_url(lot))
        self.assertEqual([a.text() for a in root.find_all(
            "a", href=lot_url(lot, "correct"))], ["Korrigieren"])
        self.assertEqual([a.text() for a in root.find_all(
            "a", href=lot_url(lot, "edit"))], ["Bearbeiten"])

    def test_the_lot_keeps_a_history(self) -> None:
        lot = self.lot()
        self.assertIn("Angelegt", self.show(lot_url(lot)).text())

    def test_an_unknown_lot_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/bulk/9999/").status_code, 404)


class NotePageTests(PageCase):

    def test_a_current_note(self) -> None:
        first = self.item("CH-0012", name="Zimtsäure", quantity=9)
        second = self.item("X-1", name="Anderes", size="2.5", unit="mg",
                           quantity=9)
        note = book_note(self.kl, date=date(2026, 10, 15), number="LS-9",
                         recipient="Produktion", note="Eilig",
                         lines=[(first, 2), (second, 3)])
        root = self.show(note_url(note))
        self.assertIn("LS-9", root.find("h1").text())
        text = root.text()
        for expected in ("15.10.2026", "Produktion", "Eilig", "CH-0012",
                         "Zimtsäure", "X-1", "Anderes", "Abgabe", "KL",
                         "Angelegt"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "10", MICRO + "mol"), text)
        self.assertTrue(has_amount(text, "2,5", "mg"), text)
        self.assertNotIn("nachgetragen", text)

    def test_a_note_without_a_number_is_shown_by_its_id(self) -> None:
        item = self.item(quantity=9)
        note = self.deliver(item, 1)
        self.assertIn(f"#{note.pk}", self.show(note_url(note)).find(
            "h1").text())

    def test_a_historical_note(self) -> None:
        item = self.item(quantity=9)
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         number="ALT-1", lines=[(item, 4)])
        text = self.show(note_url(note)).text()
        self.assertIn("nachgetragen", text)
        self.assertIn("12.03.2025", text)
        self.assertNotIn("Abgabe", text)
        reverse_historical(self.kl, note, note="doppelt erfasst")
        text = self.show(note_url(note)).text()
        self.assertIn("storniert", text)

    def test_an_unknown_note_answers_404(self) -> None:
        self.assertEqual(
            self.client.get("/lab/inventory/deliveries/9999/").status_code,
            404)
