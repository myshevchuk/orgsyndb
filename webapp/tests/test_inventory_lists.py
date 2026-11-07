"""Tests of the item, bulk and delivery lists (end-product-inventory: Item
list, Bulk list, Delivery list)."""

from datetime import date, datetime, timezone
from urllib.parse import quote

from inventory.bookings import book_note, reverse, reverse_historical

from . import build_index, field_value, frozen, page, table
from .inventory_support import (BULK, COMPOUND_PAGE, DELIVERIES, LEVELS, LIST,
                                MICRO, NEW_ITEM, NEW_LOT, NEW_NOTE,
                                InventoryCase, has_amount, has_number,
                                item_url, note_blocks, note_url, num)

COLUMNS_DE = ["Artikelnr.", "Name", "Kategorie", "Gebinde", "Bestand",
              "Ø Jahr", "Abgegeben", "Reichweite", "Lagerort", "Fach", "Box",
              "Bulk verfügbar", "Bemerkung"]
COLUMNS_EN = ["Article no.", "Name", "Category", "Container", "Stock",
              "Mean per year", "Delivered", "Coverage", "Location",
              "Compartment", "Box", "Bulk available", "Note"]
BULK_DE = ["Artikelnr.", "Name", "Charge", "Menge", "Ort", "Datum",
           "Bemerkung"]
BULK_EN = ["Article no.", "Name", "Batch", "Amount", "Location", "Date",
           "Note"]


class ListCase(InventoryCase):

    def listing(self, query: str = ""):
        response = self.client.get(LIST + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def rows(self, query: str = ""):
        return table(self.listing(query))[1]

    def articles(self, query: str = "") -> list[str]:
        root = self.listing(query)
        if root.find("table") is None:
            return []
        header, rows = table(root)
        return [row[header[0]].text() for row in rows]

    def keys(self, query: str = "") -> list[str]:
        """Each row as the article number and the container."""
        root = self.listing(query)
        header, rows = table(root)
        return [f"{r[header[0]].text()} {r['Gebinde'].text()}"
                for r in rows]


class ItemColumnTests(ListCase):

    def test_columns(self) -> None:
        self.item()
        self.assertEqual(table(self.listing())[0], COLUMNS_DE)

    def test_english_columns(self) -> None:
        self.use_index(build_index("en"))
        self.item()
        self.assertEqual(table(self.listing())[0], COLUMNS_EN)

    def test_a_row(self) -> None:
        item = self.means_item("CH-0012", name="Zimtsäure",
                               category="Endprodukt", note="Notiz")
        row = self.rows()[0]
        link = row["Artikelnr."].find("a")
        self.assertEqual(link.text(), "CH-0012")
        self.assertEqual(link.get("href"), item_url(item))
        self.assertEqual([a.get("href") for a in row["Name"].find_all("a")
                          if COMPOUND_PAGE.match(a.get("href", ""))],
                         ["/compounds/cinnamic-acid/"])
        self.assertIn("Zimtsäure", row["Name"].text())
        self.assertEqual(row["Kategorie"].text(), "Endprodukt")
        self.assertTrue(has_amount(row["Gebinde"].text(), "10",
                                   MICRO + "mol"), row["Gebinde"].text())
        stock = row["Bestand"]
        self.assertEqual(num(stock), 3)
        self.assertIn("level-low", stock.classes)
        self.assertEqual(num(row["Ø Jahr"]), 18)
        self.assertEqual(num(row["Abgegeben"]), 13)
        self.assertEqual(num(row["Reichweite"]), num("0,7"))
        self.assertEqual(row["Bemerkung"].text(), "Notiz")

    def test_the_means_show_one_decimal_place(self) -> None:
        self.means_item("CH-0012")
        row = self.rows()[0]
        self.assertEqual(row["Reichweite"].text(), "0,7")
        self.assertRegex(row["Ø Jahr"].text(), r"^18(,0)?$")

    def test_the_figures_round_half_up(self) -> None:
        year = self.item("R-2", quantity=9)
        self.enter(year, 2022, 1, 9)
        cover = self.item("R-3", quantity=2)
        self.enter(cover, 2025, 1, 32)
        rows = {r["Artikelnr."].text(): r for r in self.rows()}
        self.assertEqual(num(rows["R-2"]["Ø Jahr"]), num("2,3"))
        self.assertEqual(num(rows["R-3"]["Reichweite"]), num("0,3"))

    def test_an_item_without_a_mean_has_empty_figures(self) -> None:
        self.item("N-1", quantity=2)
        row = self.rows()[0]
        for column in ("Ø Jahr", "Reichweite"):
            with self.subTest(column=column):
                self.assertIsNone(num(row[column]))

    def test_the_size_shows_without_trailing_zeros(self) -> None:
        self.item("S-1", size="2.5", unit="mg")
        self.item("S-2", size="10", unit="g")
        rows = {r["Artikelnr."].text(): r["Gebinde"].text()
                for r in self.rows()}
        self.assertTrue(has_amount(rows["S-1"], "2,5", "mg"), rows)
        self.assertTrue(has_amount(rows["S-2"], "10", "g"), rows)

    def test_english_numbers(self) -> None:
        self.use_index(build_index("en"))
        self.means_item("CH-0012")
        row = self.rows()[0]
        self.assertEqual(row["Mean per year"].text(), "18.0")
        self.assertEqual(row["Coverage"].text(), "0.7")

    def test_an_item_outside_the_collection_has_no_compound_link(
            self) -> None:
        self.item("X-9999", name="Neu")
        row = self.rows()[0]
        self.assertFalse([a for a in row["Name"].find_all("a")
                          if COMPOUND_PAGE.match(a.get("href", ""))])
        self.assertIn("Neu", row["Name"].text())


class ItemOrderTests(ListCase):

    def test_rows_are_ordered_by_article_and_container(self) -> None:
        for article, size, unit in (
                ("CH-0002", "10", "umol"), ("CH-0001", "50", "mg"),
                ("CH-0001", "5", "g"), ("CH-0001", "100", "mg"),
                ("CH-0001", "20", "mg"), ("CH-0001", "10", "umol")):
            self.item(article, size=size, unit=unit)
        self.assertEqual(
            [k.replace(" ", "") for k in self.keys()],
            ["CH-000120mg", "CH-000150mg", "CH-0001100mg", "CH-00015g",
             f"CH-000110{MICRO}mol", f"CH-000210{MICRO}mol"])

    def test_urgent_items_first(self) -> None:
        """Scenario: Urgent items first."""
        for article, quantity in (("A-1", 7), ("A-2", 8), ("A-3", 0),
                                  ("A-4", 2)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        self.assertEqual(self.articles(), ["A-1", "A-2", "A-3", "A-4"])
        self.assertEqual(self.articles("?sort=stock"),
                         ["A-3", "A-4", "A-1", "A-2"])

    def test_the_levels_follow_one_another(self) -> None:
        for article, quantity in (("A-1", 7), ("A-2", 8), ("A-3", 0),
                                  ("A-4", 2), ("A-5", 1)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        self.assertEqual(self.articles("?sort=stock"),
                         ["A-3", "A-5", "A-4", "A-1", "A-2"])

    def test_the_smaller_coverage_comes_first_within_a_level(self) -> None:
        self.with_mean_quarter(self.item("B-1", quantity=3), 4)
        self.enter(self.item("B-2", quantity=4), 2025, 1, 32)
        self.assertEqual(self.articles(), ["B-1", "B-2"])
        self.assertEqual(self.articles("?sort=stock"), ["B-2", "B-1"])

    def test_items_without_a_coverage_come_last_in_their_level(
            self) -> None:
        self.with_mean_quarter(self.item("C-1", quantity=20), 4)
        self.with_mean_quarter(self.item("C-2", quantity=8), 4)
        self.item("C-3", quantity=2)
        self.assertEqual(self.articles("?sort=stock"),
                         ["C-2", "C-1", "C-3"])

    def test_an_empty_item_with_a_mean_comes_before_one_without(
            self) -> None:
        self.item("D-1", quantity=0)
        self.with_mean_quarter(self.item("D-2", quantity=0), 4)
        self.assertEqual(self.articles("?sort=stock"), ["D-2", "D-1"])

    def test_ties_keep_the_order_of_the_list(self) -> None:
        for article in ("E-2", "E-3", "E-1"):
            self.item(article, quantity=0)
        self.assertEqual(self.articles("?sort=stock"),
                         ["E-1", "E-2", "E-3"])


class ItemFilterTests(ListCase):

    def leveled(self) -> None:
        for quantity in (0, 1, 2, 4, 8):
            self.with_mean_quarter(
                self.item(f"L-{quantity}", quantity=quantity), 4)
        self.item("L-N", quantity=3)

    def test_each_level_exactly(self) -> None:
        self.leveled()
        expected = {"out": ["L-0"], "critical": ["L-1"], "low": ["L-2"],
                    "watch": ["L-4"], "ok": ["L-8"],
                    "undelivered": ["L-N"], "dormant": []}
        for level, want in expected.items():
            with self.subTest(level=level):
                self.assertEqual(self.articles(f"?stock={level}"), want)

    def test_no_filter_lists_every_item(self) -> None:
        self.leveled()
        self.assertEqual(len(self.articles()), 6)

    def test_category_filter(self) -> None:
        self.item("K-1", category="Endprodukt")
        self.item("K-2", category="Zwischenstufe")
        self.item("K-3", category="Endprodukt")
        self.item("K-4")
        self.assertEqual(self.articles("?category=Endprodukt"),
                         ["K-1", "K-3"])
        self.assertEqual(self.articles("?category=Zwischenstufe"), ["K-2"])

    def test_text_filter(self) -> None:
        self.item("AB-1", name="Probe Eins")
        self.item("AB-2", name="Beta", category="Grün")
        self.item("AB-3", name="Gamma", note="Hinweis Xyz")
        self.item("CH-0012", name="Probe Vier")
        cases = {"ab-1": ["AB-1"], "BETA": ["AB-2"], "grün": ["AB-2"],
                 "GRÜN": ["AB-2"], "xyz": ["AB-3"],
                 "(e)-zimts": ["CH-0012"], "probe": ["AB-1", "CH-0012"],
                 "nichts": []}
        for text, want in cases.items():
            with self.subTest(q=text):
                self.assertEqual(self.articles(f"?q={quote(text)}"), want)

    def test_filters_combine(self) -> None:
        self.with_mean_quarter(
            self.item("F-1", quantity=0, category="Endprodukt"), 4)
        self.with_mean_quarter(
            self.item("F-2", quantity=0, category="Zwischenstufe"), 4)
        self.with_mean_quarter(
            self.item("F-3", quantity=8, category="Endprodukt"), 4)
        self.assertEqual(
            self.articles("?category=Endprodukt&stock=out&q=f-"), ["F-1"])

    def test_filters_keep_their_values_in_the_form(self) -> None:
        self.item("G-1", category="Grün")
        root = self.listing(f"?category={quote("Grün")}&stock=low&q=g-")
        self.assertEqual(field_value(root, "category"), "Grün")
        self.assertEqual(field_value(root, "stock"), "low")
        self.assertEqual(field_value(root, "q"), "g-")


class ItemListFurnishingTests(ListCase):

    def summary(self, root):
        """The line that counts the items, which must precede the
        table."""
        line = root.find("p", "list-summary")
        elements = list(root.walk())
        self.assertLess(elements.index(line),
                        elements.index(root.find("table")))
        return line.text().split(" · ")[0]

    def test_the_count_is_above_the_table(self) -> None:
        for number in range(7):
            self.item(f"C-{number}")
        self.assertEqual(self.summary(self.listing()), "7 von 7 Artikeln")

    def test_the_count_follows_the_filter(self) -> None:
        for number in range(7):
            self.item(f"C-{number}", category="Eins" if number < 3 else "")
        self.assertEqual(self.summary(self.listing("?category=Eins")),
                         "3 von 7 Artikeln")

    def test_one_item(self) -> None:
        self.item("C-1")
        self.assertEqual(self.summary(self.listing()), "1 von 1 Artikel")

    def test_the_stock_menu_names_the_levels_above_the_table(self) -> None:
        self.item("C-1")
        root = self.listing()
        menu = root.find(id="stock-menu")
        elements = list(root.walk())
        self.assertLess(elements.index(menu),
                        elements.index(root.find("table")))
        names = [strong.text() for strong in menu.find_all("strong")]
        self.assertEqual(names[1:], [label[0].upper() + label[1:]
                                     for label in LEVELS.values()])

    def test_the_link_to_a_new_item_is_for_signed_in_users(self) -> None:
        self.item()
        self.assertIsNone(self.listing().find("a", href=NEW_ITEM))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_ITEM)
        self.assertEqual([a.text() for a in links], ["Neuer Artikel"])

    def test_english_link(self) -> None:
        self.use_index(build_index("en"))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_ITEM)
        self.assertEqual([a.text() for a in links], ["New item"])

    def test_the_inventory_redirects_to_the_list(self) -> None:
        done = self.client.get("/lab/inventory/")
        self.assertIn(done.status_code, (301, 302))
        self.assertEqual(done["Location"], LIST)

    def test_an_empty_list_is_served(self) -> None:
        response = self.client.get(LIST)
        self.assertEqual(response.status_code, 200)

    def test_the_calendar_is_the_one_in_berlin(self) -> None:
        item = self.item("Y-1", quantity=5)
        self.enter_year(item, 2026, 8)
        late = datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc)
        with frozen(late):
            row = self.rows()[0]
        self.assertEqual(num(row["Ø Jahr"]), 32)
        self.assertEqual(num(row["Abgegeben"]), 0)
        self.assertNotIn("projected", row["Ø Jahr"].classes)
        before = datetime(2026, 12, 31, 22, 30, tzinfo=timezone.utc)
        with frozen(before):
            row = self.rows()[0]
        self.assertIn("projected", row["Ø Jahr"].classes)
        self.assertEqual(num(row["Abgegeben"]), 32)


class SectionTabTests(ListCase):

    TABS = [(LIST, "Artikel"), (BULK, "Bulk"), (DELIVERIES, "Lieferungen")]

    def tabs(self, path: str):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        nav = page(response).find("nav", cls="section-tabs")
        self.assertIsNotNone(nav, f"{path} has no section tabs")
        return nav.find_all("a")

    def test_the_three_lists_carry_the_tabs(self) -> None:
        for current, _ in self.TABS:
            with self.subTest(path=current):
                links = self.tabs(current)
                self.assertEqual([(a.get("href"), a.text()) for a in links],
                                 self.TABS)
                self.assertEqual(
                    [a.get("aria-current") for a in links],
                    ["page" if href == current else None
                     for href, _ in self.TABS])

    def test_english_tabs(self) -> None:
        self.use_index(build_index("en"))
        self.assertEqual([a.text() for a in self.tabs(LIST)],
                         ["Items", "Bulk", "Deliveries"])


class BulkListTests(InventoryCase):

    def listing(self, query: str = ""):
        response = self.client.get(BULK + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def rows(self, query: str = "") -> dict[str, dict]:
        """The rows by batch."""
        header, rows = table(self.listing(query))
        return {r["Charge"].text(): r for r in rows}

    def batches(self, query: str = "") -> list[str]:
        header, rows = table(self.listing(query))
        return [r["Charge"].text() for r in rows]

    def test_columns(self) -> None:
        self.lot()
        self.assertEqual(table(self.listing())[0], BULK_DE)

    def test_english_columns(self) -> None:
        self.use_index(build_index("en"))
        self.lot()
        self.assertEqual(table(self.listing())[0], BULK_EN)

    def test_a_row(self) -> None:
        self.item("CH-0012", name="Zimtsäure")
        self.lot("CH-0012", "mg", "50", batch="B-1", location="Kühlraum",
                 made_on=date(2026, 10, 1), note="Rest")
        row = self.rows()["B-1"]
        self.assertEqual(row["Artikelnr."].text(), "CH-0012")
        self.assertEqual(row["Name"].text(), "Zimtsäure")
        self.assertTrue(has_amount(row["Menge"].text(), "50", "mg"))
        self.assertEqual(row["Ort"].text(), "Kühlraum")
        self.assertEqual(row["Datum"].text(), "01.10.2026")
        self.assertEqual(row["Bemerkung"].text(), "Rest")

    def test_the_amount_shows_in_the_unit_of_the_lot(self) -> None:
        self.lot("X-1", "g", "1", batch="B-G")
        self.lot("X-1", "mmol", "2.5", batch="B-M")
        rows = self.rows()
        self.assertTrue(has_amount(rows["B-G"]["Menge"].text(), "1", "g"))
        self.assertTrue(
            has_amount(rows["B-M"]["Menge"].text(), "2,5", "mmol"))

    def test_the_amount_shows_three_places_rounded_half_up(self) -> None:
        self.lot("X-1", "mg", "7.4085", batch="B-1")
        self.assertTrue(has_amount(self.rows()["B-1"]["Menge"].text(),
                                   "7,409", "mg"))

    def test_the_name_is_the_first_items_in_the_lists_order(self) -> None:
        self.item("X-1", name="Zweiter", size="10", unit="umol")
        self.item("X-1", name="Erster", size="50", unit="mg")
        self.lot("X-1", "mg", "5", batch="B-1")
        self.assertEqual(self.rows()["B-1"]["Name"].text(), "Erster")

    def test_the_name_is_empty_without_an_item(self) -> None:
        self.lot("X-9", "mg", "5", batch="B-1")
        self.assertEqual(self.rows()["B-1"]["Name"].text(), "")

    def test_rows_are_ordered_by_article_then_date(self) -> None:
        self.lot("X-2", batch="B-5", made_on=date(2020, 1, 1))
        self.lot("X-1", batch="B-2", made_on=date(2026, 5, 1))
        self.lot("X-1", batch="B-3")
        self.lot("X-1", batch="B-1", made_on=date(2025, 1, 1))
        self.assertEqual(self.batches(), ["B-1", "B-2", "B-3", "B-5"])

    def test_used_up_lots(self) -> None:
        """Scenario: Used-up lots."""
        self.lot("X-1", "mg", "5", batch="B-OPEN")
        self.lot("X-1", "mg", "0", batch="B-USED")
        self.assertEqual(self.batches(), ["B-OPEN"])
        self.assertEqual(sorted(self.batches("?empty=1")),
                         ["B-OPEN", "B-USED"])

    def test_the_link_to_a_new_lot_is_for_signed_in_users(self) -> None:
        self.lot()
        self.assertIsNone(self.listing().find("a", href=NEW_LOT))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_LOT)
        self.assertEqual([a.text() for a in links], ["Neues Bulk"])


class DeliveryListTests(InventoryCase):

    def listing(self, query: str = ""):
        response = self.client.get(DELIVERIES + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def numbers(self, query: str = "") -> list[str]:
        return [link.text() for link, _ in note_blocks(self.listing(query))]

    def test_newest_date_first_then_newest_booking(self) -> None:
        item = self.item(quantity=20)
        self.deliver(item, 1, date(2026, 10, 1), number="LS-1")
        self.deliver(item, 1, date(2026, 10, 20), number="LS-2")
        self.deliver(item, 1, date(2026, 10, 20), number="LS-3")
        self.deliver(item, 1, date(2026, 10, 10), number="LS-4")
        self.assertEqual(self.numbers(), ["LS-3", "LS-2", "LS-4", "LS-1"])

    def test_the_number_links_to_the_page_of_the_note(self) -> None:
        item = self.item(quantity=20)
        note = self.deliver(item, 1, number="LS-1")
        link, _ = note_blocks(self.listing())[0]
        self.assertEqual(link.get("href"), note_url(note))

    def test_a_note_without_a_number_shows_its_id(self) -> None:
        item = self.item(quantity=20)
        note = self.deliver(item, 1)
        link, _ = note_blocks(self.listing())[0]
        self.assertEqual(link.text(), f"#{note.pk}")

    def test_a_note_with_its_lines(self) -> None:
        first = self.item("CH-0012", name="Zimtsäure", size="10",
                          unit="umol", quantity=20)
        second = self.item("X-1", name="Anderes", size="2.5", unit="mg",
                           quantity=20)
        book_note(self.kl, date=date(2026, 10, 15), number="LS-9",
                  recipient="Produktion", lines=[(first, 2), (second, 7)])
        text = self.listing().text()
        for expected in ("LS-9", "15.10.2026", "Produktion", "CH-0012",
                         "Zimtsäure", "X-1", "Anderes"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_amount(text, "10", MICRO + "mol"), text)
        self.assertTrue(has_amount(text, "2,5", "mg"), text)
        self.assertTrue(has_number(text, "7"), text)

    def test_the_marks(self) -> None:
        item = self.item("X-1", quantity=50)
        other = self.item("X-2", quantity=50)
        book_note(self.kl, date=date(2025, 3, 1), number="H-1",
                  historical=True, lines=[(item, 1)])
        gone = book_note(self.kl, date=date(2025, 3, 2), number="H-2",
                         historical=True, lines=[(item, 1)])
        reverse_historical(self.kl, gone, note="falsch")
        self.deliver(item, 1, date(2026, 10, 1), number="C-1")
        some = book_note(self.kl, date=date(2026, 10, 3), number="C-3",
                         lines=[(item, 1), (other, 1)])
        reverse(self.kl, item.movements.get(delivery_note=some),
                note="falsch")
        blocks = {link.text(): block.text()
                  for link, block in note_blocks(self.listing())}
        self.assertEqual(set(blocks), {"H-1", "H-2", "C-1", "C-3"})
        self.assertIn("nachgetragen", blocks["H-1"])
        self.assertNotIn("storniert", blocks["H-1"])
        self.assertIn("nachgetragen", blocks["H-2"])
        self.assertIn("storniert", blocks["H-2"])
        self.assertNotIn("nachgetragen", blocks["C-1"])
        self.assertNotIn("storniert", blocks["C-1"])
        self.assertNotIn("nachgetragen", blocks["C-3"])
        self.assertIn("teilweise storniert", blocks["C-3"])

    def test_a_note_with_all_lines_reversed_shows_reversed(self) -> None:
        item = self.item("X-1", quantity=50)
        other = self.item("X-2", quantity=50)
        keep = self.deliver(item, 1, date(2026, 10, 1), number="C-1")
        note = book_note(self.kl, date=date(2026, 10, 2), number="C-2",
                         lines=[(item, 1), (other, 1)])
        for each in (item, other):
            reverse(self.kl, each.movements.get(delivery_note=note),
                    note="falsch")
        blocks = {link.text(): block.text()
                  for link, block in note_blocks(self.listing())}
        self.assertIn("storniert", blocks["C-2"])
        self.assertNotIn("teilweise", blocks["C-2"])
        self.assertNotIn("storniert", blocks["C-1"])
        self.assertEqual(keep.number, "C-1")

    def test_deliveries_of_one_item(self) -> None:
        """Scenario: Deliveries of one item."""
        item = self.item("X-1", quantity=20)
        other = self.item("X-2", quantity=20)
        self.deliver(item, 1, date(2026, 10, 1), number="LS-1")
        self.deliver(other, 1, date(2026, 10, 2), number="LS-2")
        self.deliver(item, 1, date(2026, 10, 3), number="LS-3")
        self.assertEqual(self.numbers(f"?item={item.pk}"), ["LS-3", "LS-1"])

    def test_the_item_filter_lists_historical_notes_too(self) -> None:
        item = self.item("X-1", quantity=20)
        book_note(self.kl, date=date(2025, 3, 1), number="H-1",
                  historical=True, lines=[(item, 1)])
        self.deliver(item, 1, date(2026, 10, 1), number="LS-1")
        self.assertEqual(self.numbers(f"?item={item.pk}"), ["LS-1", "H-1"])

    def test_text_filter(self) -> None:
        item = self.item(quantity=20)
        self.deliver(item, 1, number="LS-2026-117", recipient="Produktion")
        self.deliver(item, 1, number="AB-1", recipient="Labor Nord")
        self.deliver(item, 1, number="CD-2", recipient="Anderes",
                     note="Produktion eilig")
        cases = {"ls-2026": ["LS-2026-117"], "LS-": ["LS-2026-117"],
                 "produktion": ["LS-2026-117"], "NORD": ["AB-1"],
                 "-": ["CD-2", "AB-1", "LS-2026-117"], "nichts": []}
        for text, want in cases.items():
            with self.subTest(q=text):
                self.assertEqual(self.numbers(f"?q={quote(text)}"), want)

    def test_filters_keep_their_values_in_the_form(self) -> None:
        item = self.item(quantity=20)
        self.deliver(item, 1, number="LS-1")
        root = self.listing(f"?q=ls&item={item.pk}")
        self.assertEqual(field_value(root, "q"), "ls")
        self.assertEqual(field_value(root, "item"), str(item.pk))

    def test_the_link_to_a_new_note_is_for_signed_in_users(self) -> None:
        self.assertIsNone(self.listing().find("a", href=NEW_NOTE))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_NOTE)
        self.assertEqual([a.text() for a in links], ["Neuer Lieferschein"])

    def test_english_link(self) -> None:
        self.use_index(build_index("en"))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_NOTE)
        self.assertEqual([a.text() for a in links], ["New delivery note"])
