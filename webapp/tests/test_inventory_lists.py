"""Tests of the item, batch, vessel and delivery lists (end-product-
inventory: Item list, Batch list, Vessel list, Delivery list)."""

import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qs, quote, urlsplit

from inventory.bookings import book_note, reverse, reverse_historical

from . import field_value, frozen, make_substance, page, table
from .collection_support import accept
from .inventory_support import (BATCHES, COMPOUND_PAGE, DELIVERIES, LEVELS,
                                LIST, MICRO, NEW_BATCH, NEW_ITEM, NEW_NOTE,
                                SUBSTANCE_PAGE, VESSELS, InventoryCase,
                                batch_url, delivery_line, has_amount,
                                has_number, historical_line, item_url,
                                note_blocks, note_url, num, vessel_url)
from .journal_support import entry_of, make_notebook
from .main_lists_support import projected_marks, strong_columns

COLUMNS_DE = ["Artikelnr.", "Name", "Kategorie", "Gebinde", "Bestand",
              "Ø Jahr", "Abgegeben", "Reichweite", "Fach", "Box",
              "Bulk verfügbar"]
COLUMNS_EN = ["Article no.", "Name", "Category", "Container", "Stock",
              "Mean per year", "Delivered", "Coverage", "Compartment",
              "Box", "Bulk available"]
BATCHES_DE = ["Charge", "Name", "Artikelnr.", "Herkunft", "Laborjournal",
              "Datum", "Ausbeute", "Bestand"]
BATCHES_EN = ["Batch", "Name", "Article no.", "Source", "Lab notebook",
              "Date", "Yield", "Stock"]
VESSELS_DE = ["Gefäß", "Name", "Artikelnr.", "Art", "Charge", "Herkunft",
              "Menge", "Ort", "Datum", "Angebrochen"]
VESSELS_EN = ["Vessel", "Name", "Article no.", "Kind", "Batch", "Source",
              "Amount", "Location", "Date", "Opened"]


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
        accept(language="en")
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
                          if SUBSTANCE_PAGE.search(a.get("href", ""))],
                         ["/lab/registry/substances/cinnamic-acid/"])
        self.assertFalse([a for a in row["Name"].find_all("a")
                          if COMPOUND_PAGE.match(a.get("href", ""))])
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
        self.assertNotIn("Bemerkung", row)
        self.assertNotIn("Notiz", [cell.text() for cell in row.values()])

    def test_the_name_and_the_container_are_strong(self) -> None:
        self.means_item("CH-0012", name="Zimtsäure")
        root = self.listing()
        self.assertEqual(strong_columns(root),
                         (["Name", "Gebinde"], ["Name", "Gebinde"]))
        cell = table(root)[1][0]["Name"]
        self.assertIn("Zimtsäure", cell.get("title") or "")

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
        accept(language="en")
        self.means_item("CH-0012")
        row = self.rows()[0]
        self.assertEqual(row["Mean per year"].text(), "18.0")
        self.assertEqual(row["Coverage"].text(), "0.7")

    def test_an_item_outside_the_collection_links_its_substance(
            self) -> None:
        self.item("X-9999", name="Neu")
        row = self.rows()[0]
        self.assertEqual([a.get("href") for a in row["Name"].find_all("a")],
                         ["/lab/registry/substances/x-9999/"])
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
        self.item("CH-0012")
        cases = {"ab-1": ["AB-1"], "BETA": ["AB-2"], "grün": ["AB-2"],
                 "GRÜN": ["AB-2"], "xyz": ["AB-3"],
                 "(e)-zimts": ["CH-0012"], "cinnamic-acid": ["CH-0012"],
                 "probe": ["AB-1"], "nichts": []}
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
        accept(language="en")
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
            root = self.listing()
        row = table(root)[1][0]
        self.assertEqual(num(row["Ø Jahr"]), 32)
        self.assertEqual(num(row["Abgegeben"]), 0)
        self.assertEqual(projected_marks(root), [])
        before = datetime(2026, 12, 31, 22, 30, tzinfo=timezone.utc)
        with frozen(before):
            root = self.listing()
        row = table(root)[1][0]
        self.assertEqual(num(row["Abgegeben"]), 32)
        self.assertEqual(projected_marks(root), [])

    def test_a_projected_mean_is_not_marked(self) -> None:
        self.means_item("P-1")
        self.item("P-2", quantity=3)
        item = self.item("P-3", quantity=3)
        self.enter(item, 2026, 2, 6)
        root = self.listing()
        by_article = {r["Artikelnr."].text(): r for r in table(root)[1]}
        self.assertIsNotNone(num(by_article["P-3"]["Ø Jahr"]))
        self.assertEqual(projected_marks(root), [])
        self.assertNotIn("projected", by_article["P-3"]["Ø Jahr"].classes)
        self.assertNotIn("projected", by_article["P-3"]["Reichweite"].classes)


BULK = "/lab/inventory/end-products/bulk/"
INTERMEDIATES = "/lab/inventory/intermediates/"
CHEMICALS = "/lab/inventory/chemicals/"
HTMX = {"HTTP_HX_REQUEST": "true"}
DELIVERY_COOKIE = "delivery-list-view"
VIEWS = (None, "table", "details")


class SectionTabTests(ListCase):

    TABS = [(LIST, "Endprodukte"), (INTERMEDIATES, "Zwischenprodukte"),
            (CHEMICALS, "Handelschemikalien"), (BATCHES, "Chargen"),
            (VESSELS, "Alle Gefäße")]
    LISTS = [(LIST, LIST), (BULK, LIST), (DELIVERIES, LIST),
             (INTERMEDIATES, INTERMEDIATES), (CHEMICALS, CHEMICALS),
             (BATCHES, BATCHES), (VESSELS, VESSELS)]

    def tabs(self, path: str):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        nav = page(response).find("nav", cls="section-tabs")
        self.assertIsNotNone(nav, f"{path} has no section tabs")
        return nav.find_all("a")

    def test_the_five_lists_carry_the_tabs(self) -> None:
        """Requirement: Batch list ("The item list, the bulk list, the
        delivery list, the intermediate list, the commercial chemical list,
        the batch list and the vessel list carry section tabs `Endprodukte`,
        `Zwischenprodukte`, `Handelschemikalien`, `Chargen` and `Alle Gefäße`
        (`End products`, `Intermediates`, `Commercial chemicals`, `Batches`,
        `All vessels`), linking to `/lab/inventory/end-products/`,
        `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`,
        `/lab/inventory/batches/` and `/lab/inventory/vessels/`, in the
        site's `nav.section-tabs` markup.")."""
        for path, current in self.LISTS:
            with self.subTest(path=path):
                links = self.tabs(path)
                self.assertEqual([(a.get("href"), a.text()) for a in links],
                                 self.TABS)
                self.assertEqual(
                    [a.get("aria-current") for a in links],
                    ["page" if href == current else None
                     for href, _ in self.TABS])

    def test_english_tabs(self) -> None:
        accept(language="en")
        self.assertEqual(
            [a.text() for a in self.tabs(LIST)],
            ["End products", "Intermediates", "Commercial chemicals",
             "Batches", "All vessels"])


class OldAddressTests(InventoryCase):
    """The old `/lab/inventory/bulk/` addresses are gone."""

    def test_the_old_addresses_answer_404(self) -> None:
        vessel = self.vessel("CH-0012")
        self.client.force_login(self.kl)
        for path in ("/lab/inventory/bulk/", "/lab/inventory/bulk/new/",
                     f"/lab/inventory/bulk/{vessel.pk}/",
                     f"/lab/inventory/bulk/{vessel.pk}/edit/",
                     f"/lab/inventory/bulk/{vessel.pk}/correct/",
                     f"/lab/inventory/bulk/{vessel.pk}/withdraw/",
                     "/lab/inventory/bulk/movements/1/reverse/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)


class BatchListTests(InventoryCase):

    def listing(self, query: str = ""):
        response = self.client.get(BATCHES + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def rows(self, query: str = "") -> dict[str, dict]:
        """The rows by the batch as it shows."""
        header, rows = table(self.listing(query))
        return {r["Charge"].text(): r for r in rows}

    def numbers(self, query: str = "") -> list[str]:
        header, rows = table(self.listing(query))
        return [r["Charge"].text() for r in rows]

    def test_columns(self) -> None:
        self.batch()
        self.assertEqual(table(self.listing())[0], BATCHES_DE)

    def test_english_columns(self) -> None:
        accept(language="en")
        self.batch()
        self.assertEqual(table(self.listing())[0], BATCHES_EN)

    def test_the_name_and_the_stock_are_strong(self) -> None:
        self.batch()
        root = self.listing()
        self.assertEqual(strong_columns(root),
                         (["Name", "Bestand"], ["Name", "Bestand"]))
        cell = table(root)[1][0]["Name"]
        self.assertTrue(cell.get("title"))
        self.assertIn(cell.get("title"), cell.text())

    def test_batches_of_either_source(self) -> None:
        """Scenario: Batches of either source."""
        from . import make_batch, make_task, make_vessel, past
        make_notebook("AE-1", self.kl)
        self.item("CH-0012", name="Zimtsäure")
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        made = make_batch(
            self.kl, "CH-0012", number="KL0412", date=date(2026, 10, 30),
            task_step=task.steps.get(), journal_entry=entry_of("AE-1/9"),
            yield_amount="2", yield_unit="g")
        make_vessel(self.kl, made, unit="g", amount="2")
        bought = make_batch(
            self.kl, "acetophenone", source="bought", supplier="Sigma",
            supplier_batch="MKCK1234", date=date(2026, 11, 2))
        header, rows = table(self.listing())
        self.assertEqual([r["Charge"].text() for r in rows],
                         ["MKCK1234", "KL0412"])
        first, second = rows
        self.assertEqual(first["Artikelnr."].text(), "")
        self.assertEqual(first["Herkunft"].text(), "gekauft · Sigma")
        self.assertEqual(first["Bestand"].text(), "–")
        self.assertEqual([a.get("href") for a in first["Charge"].find_all(
            "a")], [batch_url(bought)])
        self.assertEqual(second["Artikelnr."].text(), "CH-0012")
        self.assertEqual(second["Herkunft"].text(),
                         f"hergestellt · {task.number}")
        self.assertEqual([a.get("href") for a in second["Herkunft"].find_all(
            "a")], [f"/lab/tasks/{task.number}/"])
        self.assertEqual(second["Laborjournal"].text(), "AE-1/9")
        self.assertEqual([a.get("href") for a in second[
            "Laborjournal"].find_all("a")], ["/lab/journal/AE-1/"])
        self.assertEqual(second["Datum"].text(), "30.10.2026")
        self.assertTrue(has_amount(second["Ausbeute"].text(), "2", "g"))
        self.assertTrue(has_amount(second["Bestand"].text(), "2", "g"))
        self.assertEqual([a.get("href") for a in second["Charge"].find_all(
            "a")], [batch_url(made)])
        self.assertEqual(second["Name"].text(), "Zimtsäure")
        self.assertEqual([a.get("href") for a in second["Name"].find_all(
            "a")], ["/lab/registry/substances/cinnamic-acid/"])

    def test_the_source_and_the_supplier(self) -> None:
        self.batch("X-1", number="B-M", source="made")
        self.batch("X-1", source="bought", supplier_batch="B-B")
        self.batch("X-1", source="bought", supplier="Sigma",
                   supplier_batch="B-S")
        rows = self.rows()
        self.assertEqual(rows["B-M"]["Herkunft"].text(), "hergestellt")
        self.assertEqual(rows["B-B"]["Herkunft"].text(), "gekauft")
        self.assertEqual(rows["B-S"]["Herkunft"].text(), "gekauft · Sigma")

    def test_the_source_in_english(self) -> None:
        accept(language="en")
        self.batch("X-1", number="B-M", source="made")
        self.batch("X-1", source="bought", supplier="Sigma",
                   supplier_batch="B-S")
        rows = {r["Batch"].text(): r for r in table(self.listing())[1]}
        self.assertEqual(rows["B-M"]["Source"].text(), "made")
        self.assertEqual(rows["B-S"]["Source"].text(), "bought · Sigma")

    def test_a_made_batch_without_a_step_names_no_task(self) -> None:
        self.batch("X-1", number="B-M")
        row = self.rows()["B-M"]
        self.assertEqual(row["Herkunft"].text(), "hergestellt")
        self.assertEqual(row["Herkunft"].find_all("a"), [])

    def test_a_bought_batch_without_a_supplier_batch_shows_its_id(
            self) -> None:
        batch = self.batch("X-1", source="bought", supplier="Sigma")
        self.assertIn(f"#{batch.pk}", self.rows())

    def test_batches_of_an_intermediate_have_no_article_number(self) -> None:
        self.item("CH-0012", name="Zimtsäure")
        self.batch("acetophenone", number="B-I")
        self.batch("CH-0012", source="bought", supplier="Sigma",
                   supplier_batch="B-C")
        rows = self.rows()
        self.assertEqual(rows["B-I"]["Artikelnr."].text(), "")
        self.assertEqual(rows["B-C"]["Artikelnr."].text(), "CH-0012")

    def test_the_article_of_an_article_without_a_number_is_empty(
            self) -> None:
        self.item(None, "Ohne Nummer")
        self.batch("Ohne Nummer", number="B-N")
        self.assertEqual(self.rows()["B-N"]["Artikelnr."].text(), "")

    def test_the_stock_is_the_amount_in_the_open_vessels_by_unit(
            self) -> None:
        from . import make_vessel
        batch = self.batch("X-1", number="B-S")
        make_vessel(self.kl, batch, unit="g", amount="1", flask=True)
        make_vessel(self.kl, batch, unit="g", amount="0.5", location="A")
        make_vessel(self.kl, batch, unit="mg", amount="30", location="B")
        make_vessel(self.kl, batch, unit="mg", amount="0", location="C")
        text = self.rows()["B-S"]["Bestand"].text()
        self.assertTrue(has_amount(text, "1,5", "g"), text)
        self.assertTrue(has_amount(text, "30", "mg"), text)

    def test_a_batch_with_only_used_up_vessels_shows_a_dash(self) -> None:
        from . import make_vessel
        batch = self.batch("X-1", number="B-U")
        make_vessel(self.kl, batch, amount="0")
        self.assertEqual(self.rows()["B-U"]["Bestand"].text(), "–")

    def test_the_yield_shows_three_places_rounded_half_up(self) -> None:
        self.batch("X-1", number="B-1", yield_amount="7.4085",
                   yield_unit="mg")
        self.assertTrue(has_amount(self.rows()["B-1"]["Ausbeute"].text(),
                                   "7,409", "mg"))

    def test_rows_are_ordered_by_date_newest_first_and_undated_last(
            self) -> None:
        self.batch("X-1", number="B-OLD", date=date(2020, 1, 1))
        self.batch("X-1", number="B-NEW", date=date(2026, 5, 1))
        self.batch("X-1", number="B-NONE1")
        self.batch("X-1", number="B-NONE2")
        self.batch("X-1", number="B-MID", date=date(2025, 1, 1))
        self.assertEqual(self.numbers(), ["B-NEW", "B-MID", "B-OLD",
                                          "B-NONE2", "B-NONE1"])

    def test_every_batch_is_listed_with_or_without_vessels(self) -> None:
        self.batch("X-1", number="B-1")
        self.vessel("X-2", number="B-2")
        self.assertEqual(sorted(self.numbers()), ["B-1", "B-2"])

    def test_searching_batches(self) -> None:
        """Scenario: Searching batches."""
        self.batch("CH-0012", number="KL0412", date=date(2026, 10, 30))
        self.batch("acetophenone", source="bought", supplier="Sigma",
                   supplier_batch="MKCK1234", date=date(2026, 11, 2))
        self.assertEqual(self.numbers("?q=kl04"), ["KL0412"])
        self.assertEqual(self.numbers("?q=sigma"), ["MKCK1234"])

    def test_the_search_covers_number_supplier_batch_supplier_and_substance(
            self) -> None:
        self.batch("CH-0012", number="KL0412")
        self.batch("acetophenone", source="bought", supplier="Merck",
                   supplier_batch="ZZ99")
        cases = {"kl0412": ["KL0412"], "KL04": ["KL0412"],
                 "zz9": ["ZZ99"], "merck": ["ZZ99"], "MERCK": ["ZZ99"],
                 "cinnamic": ["KL0412"], "zimt": ["KL0412"],
                 "acetophenone": ["ZZ99"], "nichts": []}
        for text, want in cases.items():
            with self.subTest(q=text):
                self.assertEqual(self.numbers(f"?q={quote(text)}"), want)

    def test_the_form_keeps_its_value(self) -> None:
        self.batch("X-1", number="KL1")
        self.assertEqual(field_value(self.listing("?q=kl"), "q"), "kl")

    def test_the_link_to_a_new_batch_is_for_signed_in_users(self) -> None:
        self.batch()
        self.assertIsNone(self.listing().find("a", href=NEW_BATCH))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["Neue Charge"])

    def test_the_english_link(self) -> None:
        accept(language="en")
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["New batch"])


class VesselListTests(InventoryCase):

    def listing(self, query: str = ""):
        response = self.client.get(VESSELS + query)
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
        self.vessel()
        self.assertEqual(table(self.listing())[0], VESSELS_DE)

    def test_english_columns(self) -> None:
        accept(language="en")
        self.vessel()
        self.assertEqual(table(self.listing())[0], VESSELS_EN)

    def test_a_row(self) -> None:
        self.item("CH-0012", name="Zimtsäure")
        vessel = self.vessel(
            "CH-0012", "mg", "50", number="B-1", location="Kühlraum",
            date=date(2026, 10, 1), note="Rest")
        row = self.rows()["B-1"]
        self.assertEqual(row["Gefäß"].text(), f"#{vessel.pk}")
        self.assertEqual([a.get("href") for a in row["Gefäß"].find_all("a")],
                         [vessel_url(vessel)])
        self.assertEqual(row["Artikelnr."].text(), "CH-0012")
        self.assertEqual(row["Name"].text(), "Zimtsäure")
        self.assertEqual([a.get("href") for a in row["Name"].find_all("a")],
                         ["/lab/registry/substances/cinnamic-acid/"])
        self.assertEqual(row["Art"].text(), "Endprodukt")
        self.assertEqual([a.get("href") for a in row["Charge"].find_all(
            "a")], [batch_url(vessel.batch)])
        self.assertEqual(row["Herkunft"].text(), "hergestellt")
        self.assertTrue(has_amount(row["Menge"].text(), "50", "mg"))
        self.assertEqual(row["Ort"].text(), "Kühlraum")
        self.assertEqual(row["Datum"].text(), "01.10.2026")
        self.assertNotIn("Bemerkung", row)
        self.assertNotIn("Rest", [cell.text() for cell in row.values()])

    def test_the_name_and_the_amount_are_strong(self) -> None:
        self.item("CH-0012", name="Zimtsäure")
        self.vessel("CH-0012", "mg", "50", number="B-1")
        root = self.listing()
        self.assertEqual(strong_columns(root),
                         (["Name", "Menge"], ["Name", "Menge"]))
        cell = table(root)[1][0]["Name"]
        self.assertEqual(cell.get("title"), "Zimtsäure")

    def test_the_source_and_the_supplier(self) -> None:
        self.vessel("X-1", number="B-M", source="made")
        self.vessel("X-1", source="bought", supplier_batch="B-B")
        self.vessel("X-1", source="bought", supplier="Sigma",
                    supplier_batch="B-S")
        rows = self.rows()
        self.assertEqual(rows["B-M"]["Herkunft"].text(), "hergestellt")
        self.assertEqual(rows["B-B"]["Herkunft"].text(), "gekauft")
        self.assertEqual(rows["B-S"]["Herkunft"].text(), "gekauft · Sigma")

    def test_the_amount_shows_in_the_unit_of_the_vessel(self) -> None:
        self.vessel("X-1", "g", "1", number="B-G")
        self.vessel("X-1", "mmol", "2.5", number="B-M")
        rows = self.rows()
        self.assertTrue(has_amount(rows["B-G"]["Menge"].text(), "1", "g"))
        self.assertTrue(
            has_amount(rows["B-M"]["Menge"].text(), "2,5", "mmol"))

    def test_the_amount_shows_three_places_rounded_half_up(self) -> None:
        self.vessel("X-1", "mg", "7.4085", number="B-1")
        self.assertTrue(has_amount(self.rows()["B-1"]["Menge"].text(),
                                   "7,409", "mg"))

    def test_the_name_is_the_substances(self) -> None:
        self.vessel("X-1", "mg", "5", number="B-1")
        self.assertEqual(self.rows()["B-1"]["Name"].text(), "X-1")

    def test_rows_are_ordered_by_name_then_batch_date_then_id(self) -> None:
        beta = make_substance("s1", "beta")
        alpha = make_substance("s2", "Alpha")
        gamma = make_substance("s3", "Gamma")
        self.vessel(substance=gamma, number="B-3", date=date(2020, 1, 1))
        self.vessel(substance=beta, number="B-2")
        self.vessel(substance=beta, number="B-1", date=date(2025, 1, 1))
        self.vessel(substance=alpha, number="B-0", date=date(2026, 5, 1))
        self.vessel(substance=beta, number="B-2b")
        self.assertEqual(self.batches(),
                         ["B-0", "B-1", "B-2", "B-2b", "B-3"])

    def test_used_up_vessels(self) -> None:
        """Scenario: Used-up vessels."""
        self.vessel("X-1", "mg", "5", number="B-OPEN")
        self.vessel("X-1", "mg", "0", number="B-USED")
        self.assertEqual(self.batches(), ["B-OPEN"])
        self.assertEqual(sorted(self.batches("?empty=1")),
                         ["B-OPEN", "B-USED"])

    def test_a_flask_is_listed_with_its_kind(self) -> None:
        self.vessel("X-1", "g", "2", number="B-F", flask=True)
        row = self.rows()["B-F"]
        self.assertEqual(row["Art"].text(), "Kolben")
        self.assertEqual(row["Ort"].text(), "")

    def test_vessels_by_kind(self) -> None:
        """Scenario: Vessels by kind."""
        self.item("CH-0012", name="Zimtsäure")
        from . import make_batch, make_vessel
        made = make_batch(self.kl, "CH-0012", number="KL0412")
        make_vessel(self.kl, made, unit="g", amount="2", flask=True)
        self.vessel("acetophenone", number="B-I")
        self.vessel("acetophenone", source="bought", supplier="Sigma",
                    supplier_batch="B-R")
        rows = self.rows()
        self.assertEqual({k: v["Art"].text() for k, v in rows.items()},
                         {"KL0412": "Kolben", "B-I": "Zwischenprodukt",
                          "B-R": "Handelschemikalie"})
        self.assertEqual(rows["KL0412"]["Artikelnr."].text(), "CH-0012")
        self.assertEqual(rows["B-I"]["Artikelnr."].text(), "")
        self.assertEqual(rows["B-R"]["Artikelnr."].text(), "")
        self.assertEqual(rows["B-R"]["Herkunft"].text(), "gekauft · Sigma")
        self.assertEqual(self.batches("?kind=commercial"), ["B-R"])

    def test_every_kind_has_its_filter(self) -> None:
        self.item("CH-0012", name="Zimtsäure")
        from . import make_batch, make_vessel
        made = make_batch(self.kl, "CH-0012", number="KL0412")
        make_vessel(self.kl, made, unit="g", amount="2", flask=True)
        make_vessel(self.kl, made, unit="g", amount="1", location="Regal")
        self.vessel("acetophenone", number="B-I")
        self.vessel("acetophenone", source="bought", supplier_batch="B-R")
        cases = {"flask": ["KL0412"], "end-product": ["KL0412"],
                 "intermediate": ["B-I"], "commercial": ["B-R"]}
        for kind, want in cases.items():
            with self.subTest(kind=kind):
                self.assertEqual(self.batches(f"?kind={kind}"), want)
        self.assertEqual(
            sorted(self.batches("?kind=flask")
                   + self.batches("?kind=end-product")), ["KL0412"] * 2)

    def test_another_kind_lists_every_kind(self) -> None:
        self.vessel("acetophenone", number="B-I")
        self.vessel("acetophenone", source="bought", supplier_batch="B-R")
        for query in ("?kind=other", "?kind=", ""):
            with self.subTest(query=query):
                self.assertEqual(sorted(self.batches(query)),
                                 ["B-I", "B-R"])

    def test_the_kind_filter_combines_with_used_up_vessels(self) -> None:
        self.vessel("acetophenone", "mg", "0", number="B-I")
        self.vessel("acetophenone", number="B-J")
        self.assertEqual(self.batches("?kind=intermediate"), ["B-J"])
        self.assertEqual(sorted(self.batches("?kind=intermediate&empty=1")),
                         ["B-I", "B-J"])

    def test_the_page_offers_each_kind_and_shows_the_one_in_force(
            self) -> None:
        self.vessel("acetophenone", number="B-I")
        root = self.listing("?kind=commercial")
        controls = [el for el in root.find("main").find_all(
            ("a", "option", "input"))
            if el.closest("nav") is None]
        offered = set()
        for el in controls:
            offered.update(re.findall(r"kind=([a-z-]+)", el.get("href", "")))
            if el.tag != "a" and el.get("value"):
                offered.add(el.get("value"))
        self.assertLessEqual({"flask", "end-product", "intermediate",
                              "commercial"}, offered)
        marked = [el for el in controls
                  if {"aria-current", "selected", "checked"} & set(el.attrs)]
        shown = " ".join(el.get("href", "") + el.get("value", "")
                         for el in marked)
        self.assertIn("commercial", shown)
        for other in ("flask", "end-product", "intermediate"):
            self.assertNotIn(other, shown)

    def test_the_link_to_a_new_batch_is_for_signed_in_users(self) -> None:
        self.vessel()
        self.assertIsNone(self.listing().find("a", href=NEW_BATCH))
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_BATCH)
        self.assertEqual([a.text() for a in links], ["Neue Charge"])


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
                  recipient="Produktion",
                  lines=[delivery_line(first, 2), delivery_line(second, 7)])
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
                  historical=True, lines=[historical_line(item, 1)])
        gone = book_note(self.kl, date=date(2025, 3, 2), number="H-2",
                         historical=True, lines=[historical_line(item, 1)])
        reverse_historical(self.kl, gone, note="falsch")
        self.deliver(item, 1, date(2026, 10, 1), number="C-1")
        some = book_note(self.kl, date=date(2026, 10, 3), number="C-3",
                         lines=[delivery_line(item, 1),
                                delivery_line(other, 1)])
        reverse(self.kl, item.movements.get(delivery_note=some,
                                            kind="delivery"),
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
                         lines=[delivery_line(item, 1),
                                delivery_line(other, 1)])
        for each in (item, other):
            reverse(self.kl, each.movements.get(delivery_note=note,
                                                kind="delivery"),
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
                  historical=True, lines=[historical_line(item, 1)])
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
        accept(language="en")
        self.client.force_login(self.kl)
        links = self.listing().find_all("a", href=NEW_NOTE)
        self.assertEqual([a.text() for a in links], ["New delivery note"])

    def test_heading_is_end_products(self) -> None:
        """Requirement: Delivery list ("`/lab/inventory/deliveries/` SHALL list
        the delivery notes, under the heading `Endprodukte`")."""
        self.assertEqual(self.listing().find("main").find("h1").text(),
                         "Endprodukte")
        accept(language="en")
        self.assertEqual(self.listing().find("main").find("h1").text(),
                         "End products")

    def test_view_cookie_and_selected(self) -> None:
        """Requirement: Delivery list ("The list shows its notes in the views
        `Tabelle` and `Details`, remembered in the cookie `delivery-list-view`,
        with one note selected by `selected=<id>`, as the item list does with
        its items")."""
        item = self.item(quantity=20)
        first = self.deliver(item, 1, date(2026, 10, 1), number="LS-1")
        second = self.deliver(item, 1, date(2026, 10, 2), number="LS-2")
        for cookie, want in ((None, "table"), ("table", "table"),
                             ("details", "details"), ("other", "table"),
                             ("", "table")):
            with self.subTest(cookie=cookie):
                if cookie is None:
                    self.client.cookies.pop(DELIVERY_COOKIE, None)
                else:
                    self.client.cookies[DELIVERY_COOKIE] = cookie
                root = self.listing()
                layout = root.find(attrs={"data-view": True})
                self.assertIsNotNone(layout)
                self.assertEqual(layout.get("data-view"), want)
                radios = {r.get("id"): r for r in root.find_all(
                    "input", type="radio", name="view")}
                self.assertEqual(sorted(radios),
                                 ["view-details", "view-table"])
                self.assertEqual(
                    [name for name, r in radios.items()
                     if "checked" in r.attrs],
                    [f"view-{want}"])
        for view in VIEWS:
            for query, target in (
                    ("", second),
                    (f"?selected={first.pk}", first),
                    ("?selected=999999", second),
                    (f"?q=LS-1&selected={second.pk}", first)):
                with self.subTest(view=view, query=query):
                    if view is None:
                        self.client.cookies.pop(DELIVERY_COOKIE, None)
                    else:
                        self.client.cookies[DELIVERY_COOKIE] = view
                    root = self.listing(query)
                    grid = root.find("table")
                    marked = [
                        tr for tr in grid.find("tbody").find_all("tr")
                        if tr.closest("table") is grid
                        and tr.get("aria-current") == "true"]
                    self.assertEqual(len(marked), 1)
                    self.assertEqual(
                        marked[0].get("hx-get"),
                        f"/lab/inventory/deliveries/{target.pk}/detail/")
                    aside = root.find("main").find("aside")
                    self.assertIsNotNone(aside)
                    self.assertIsNotNone(
                        aside.find("a", href=note_url(target)))

    def test_a_note_in_the_details_view(self) -> None:
        """Scenario: A note in the details view."""
        first = self.item("CH-0013", size="100", unit="mg", quantity=20)
        second = self.item("CH-0016", size="1", unit="g", quantity=20)
        batch1 = self.batch("CH-0013", number="KL13")
        batch2 = self.batch("CH-0016", number="KL16")
        self.deliver(first, 1, date(2026, 10, 20), number="LS-2026-200")
        note = book_note(
            self.kl, date=date(2026, 10, 15), number="LS-2026-156",
            recipient="Produktion",
            lines=[delivery_line(first, 2, batch1),
                   delivery_line(second, 3, batch2)])
        self.client.cookies[DELIVERY_COOKIE] = "details"
        root = self.listing(f"?selected={note.pk}")
        aside = root.find("main").find("aside")
        self.assertIsNotNone(aside)
        text = aside.text()
        for expected in ("LS-2026-156", "CH-0013", "KL13", "CH-0016", "KL16"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue(has_number(text, "2"), text)
        self.assertTrue(has_number(text, "3"), text)
        self.assertIsNotNone(aside.find("a", href=note_url(note)))
        detail = f"/lab/inventory/deliveries/{note.pk}/detail/"
        fragment = self.client.get(detail, **HTMX)
        self.assertEqual(fragment.status_code, 200)
        frag_root = page(fragment)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(frag_root.find_all(tag), [], tag)
        self.assertIn("LS-2026-156", frag_root.text())
        self.assertIsNotNone(frag_root.find("a", href=note_url(note)))
        plain = self.client.get(detail)
        self.assertIn(plain.status_code, (302, 303))
        target = urlsplit(plain["Location"])
        self.assertEqual(target.path, DELIVERIES)
        self.assertEqual(parse_qs(target.query), {"selected": [str(note.pk)]})
        self.assertEqual(
            self.client.get(
                f"/lab/inventory/deliveries/{note.pk + 999}/detail/",
                **HTMX).status_code,
            404)
