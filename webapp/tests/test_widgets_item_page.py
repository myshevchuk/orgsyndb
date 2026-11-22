"""Tests of the item page as widgets: the figures strip, the widgets
with their titles, the sortable movements table and the forecast
widget (web-app: Widgets; end-product-inventory: Item page;
production-planning: Item forecast)."""

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from . import Element, page
from .collection_support import accept
from .inventory_support import (LEVELS, TODAY, has_amount, has_number,
                                item_url, set_shares, vessel_url)
from .planning_support import PlanningCase, has_date, has_days
from .widget_support import (ISO_DATE, ISO_MOMENT, carries, grid, item_widget,
                             kv, kv_rows, tile, tile_value, tiles,
                             title_of, widget, widgets)

PROJECTED = "hochgerechnet aus dem laufenden Jahr"
STOCK, COVERAGE = "Bestand", "Reichweite"
MEAN_QUARTER, MEAN_YEAR, THIS_YEAR = "Ø Quartal", "Ø Jahr", "lfd. Jahr"
BULK, LATEST = "Nutzbares Bulk", "Spätester Start"
LABELS = [STOCK, COVERAGE, MEAN_QUARTER, MEAN_YEAR, THIS_YEAR, BULK,
          LATEST]
CERTAINTY = r"(?<![\d,.])(?:0,9|90)(?!\d)"


def rough(text: str) -> bool:
    return re.search(r"(?<!\w)grob", text) is not None


class ItemPageCase(PlanningCase):

    def show(self, item: Any, signed_in: bool = False) -> Element:
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(item_url(item))
        self.assertEqual(response.status_code, 200)
        return page(response)


class WidgetTests(ItemPageCase):

    def test_the_item_page_shows_its_data_in_widgets(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        root = self.show(item)
        for title in ("Verbrauch", "Buchungen", "Bulk",
                      "Gebinde nach Charge", "Prognose"):
            with self.subTest(title=title):
                found = widget(root, title)
                self.assertEqual(found.tag, "section")
                head = found.find(cls="widget__head")
                self.assertIsNotNone(head)
                self.assertEqual(head.find("h2").text(), title)
        self.assertEqual(item_widget(root).tag, "section")
        self.assertEqual(widget(root, "Änderungen").tag, "details")

    def test_a_title_is_in_one_widget_only(self) -> None:
        root = self.show(self.planned_item("NV-1", quantity=10))
        titles = [title_of(w) for w in widgets(root)]
        self.assertGreaterEqual(len(titles), 7, titles)
        self.assertEqual(len(titles), len(set(titles)), titles)

    def test_every_widget_has_a_heading_of_the_outline(self) -> None:
        root = self.show(self.planned_item("NV-1", quantity=10))
        self.assertGreaterEqual(len(widgets(root)), 7)
        for found in widgets(root):
            with self.subTest(widget=title_of(found)):
                self.assertTrue(title_of(found))
                self.assertIsNotNone(found.find("h2"))

    def test_the_consumption_widget_holds_chart_and_quarters(self) -> None:
        item = self.item("CH-0012", quantity=5)
        self.enter(item, 2026, 3, 40)
        found = widget(self.show(item, signed_in=True), "Verbrauch")
        self.assertIsNotNone(found.find("svg"))
        labels = [th.text() for th in found.find_all("th", scope="row")]
        self.assertEqual(len(labels), 12, labels)
        self.assertIn("Q3 2026", labels)
        links = [a.get("href", "") for a in found.find_all("a")]
        self.assertTrue(any("year=2026" in href for href in links), links)

    def test_the_item_data_widget_holds_the_data_and_the_note(
            self) -> None:
        item = self.item("CH-0012", category="Endprodukt",
                         note="Zeile eins", compartment="2", box="7")
        found = item_widget(self.show(item))
        keys = kv(found)
        for key in ("Kategorie", "Gebinde", "Im Bestand seit", "Fach",
                    "Box"):
            with self.subTest(key=key):
                self.assertIn(key, keys)
        self.assertEqual(keys["Kategorie"].text(), "Endprodukt")
        self.assertEqual((keys["Fach"].text(), keys["Box"].text()),
                         ("2", "7"))
        self.assertIn("Zeile eins", found.text())

    def test_the_figures_are_not_in_the_item_data(self) -> None:
        """The stock, the means and the year have moved to the strip."""
        keys = kv(item_widget(self.show(self.means_item("CH-0012"))))
        for key in ("Bestand", "Ø Quartal", "Ø Jahr", "lfd. Jahr",
                    "Reichweite"):
            with self.subTest(key=key):
                self.assertNotIn(key, keys)

    def test_the_containers_by_batch(self) -> None:
        item = self.item("CH-0012", quantity=0)
        a, b = self.batch("CH-0012", number="KL0412"), self.batch(
            "CH-0012", number="KL0413")
        set_shares(item, (a, 3), (None, 2))
        found = widget(self.show(item), "Gebinde nach Charge")
        links = {link.text(): link for link in found.find_all("a")}
        self.assertEqual(set(links), {"KL0412"})
        self.assertEqual(links["KL0412"].get("href"),
                         f"/lab/inventory/batches/{a.pk}/")
        text = found.text()
        self.assertTrue(has_number(text, "3"), text)
        self.assertTrue(has_number(text, "2"), text)
        self.assertIn("unbekannt", text)
        self.assertNotIn(b.number, text)

    def test_the_bulk_widget_lists_the_open_vessels(self) -> None:
        item = self.item("CH-0012")
        vessel = self.vessel("CH-0012", "mg", "50")
        found = widget(self.show(item), "Bulk")
        hrefs = [a.get("href") for a in found.find_all("a")]
        self.assertIn(vessel_url(vessel), hrefs)
        self.assertTrue(has_amount(found.text(), "50", "mg"), found.text())

    def test_the_bulk_widget_without_a_vessel(self) -> None:
        found = widget(self.show(self.item("CH-0012")), "Bulk")
        self.assertIn("Kein offenes Gefäß.", found.text())

    def test_the_new_batch_link_is_in_the_bulk_widget(self) -> None:
        item = self.item("CH-0012")
        found = widget(self.show(item, signed_in=True), "Bulk")
        links = [a for a in found.find_all("a")
                 if a.get("href", "").startswith("/lab/inventory/batches/"
                                                 "new/")]
        self.assertEqual([a.text() for a in links], ["Neue Charge"])
        self.assertIn("cinnamic-acid", links[0].get("href"))

    def test_a_visitor_has_no_new_batch_link(self) -> None:
        item = self.item("CH-0012")
        root = self.show(item)
        self.assertEqual([a for a in root.find_all("a")
                          if a.text() == "Neue Charge"], [])

    def test_an_item_without_an_article_number_has_no_such_link(
            self) -> None:
        item = self.item(None, "Neuverbindung 9")
        root = self.show(item, signed_in=True)
        self.assertEqual([a for a in root.find_all("a")
                          if a.text() == "Neue Charge"], [])


class FiguresStripTests(ItemPageCase):

    def test_the_strip_holds_the_figures(self) -> None:
        item = self.means_item("CH-0012")
        root = self.show(item)
        found = tiles(root)
        self.assertEqual(len(found), len(LABELS), [t.text() for t in found])
        for label in LABELS:
            with self.subTest(label=label):
                tile(root, label)
        for label, shown in ((MEAN_QUARTER, "4,5"), (MEAN_YEAR, "18,0"),
                             (THIS_YEAR, "13"), (COVERAGE, "0,7")):
            with self.subTest(label=label):
                value = tile_value(tile(root, label), label)
                self.assertTrue(has_number(value, shown), value)

    def test_the_strip_is_one_element_of_the_page(self) -> None:
        root = self.show(self.item("CH-0012"))
        self.assertEqual(len(root.find_all(cls="figures-strip")), 1)

    def test_the_stock_tile_carries_the_level(self) -> None:
        item = self.means_item("CH-0012")
        level = self.consumption(item).level
        found = tile(self.show(item), STOCK)
        self.assertTrue(carries(found, "class", f"level-{level}"),
                        (level, found.text()))
        self.assertIn(LEVELS[level], found.text())
        self.assertTrue(has_number(tile_value(found, STOCK), "3"),
                        found.text())

    def test_the_stock_tile_of_every_level(self) -> None:
        never = self.item("L-1", quantity=5)
        out = self.item("L-2", quantity=0)
        self.enter_year(out, 2025, 5)
        seen = set()
        for item in (never, out):
            level = self.consumption(item).level
            seen.add(level)
            with self.subTest(level=level):
                found = tile(self.show(item), STOCK)
                self.assertTrue(carries(found, "class", f"level-{level}"),
                                found.text())
                self.assertIn(LEVELS[level], found.text())
        self.assertEqual(seen, {"undelivered", "out"})

    def test_a_dormant_item(self) -> None:
        item = self.item("D-1", quantity=4)
        from inventory.models import Item
        Item.objects.filter(pk=item.pk).update(status="discontinued")
        found = tile(self.show(item), STOCK)
        self.assertTrue(carries(found, "class", "level-dormant"))
        self.assertIn("ruhend", found.text())
        self.assertIn("4", found.text())

    def test_projected_figures_are_marked(self) -> None:
        item = self.item("P-1", quantity=3)
        self.enter(item, 2026, 2, 6)
        root = self.show(item)
        for label in (MEAN_QUARTER, MEAN_YEAR, COVERAGE):
            with self.subTest(label=label):
                found = tile(root, label)
                self.assertTrue(carries(found, "class", "projected"),
                                found.text())
                self.assertTrue(carries(found, "title", PROJECTED),
                                found.text())
        for label in (STOCK, THIS_YEAR):
            with self.subTest(label=label):
                self.assertFalse(carries(tile(root, label), "class",
                                         "projected"))

    def test_complete_years_are_not_marked(self) -> None:
        root = self.show(self.means_item("CH-0012"))
        for label in LABELS:
            with self.subTest(label=label):
                found = tile(root, label)
                self.assertFalse(carries(found, "class", "projected"))
                self.assertFalse(carries(found, "title", PROJECTED))

    def test_a_rough_figure_is_marked(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        found = tile(self.show(item), LATEST)
        self.assertTrue(has_date(found.text(), date(2026, 11, 15)),
                        found.text())
        self.assertTrue(rough(found.text()), found.text())

    def test_a_figure_of_the_order_model_is_not_rough(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        self.orders(item, *[(date(2026, month, 10), size) for month, size
                            in enumerate([2, 3, 5, 8, 17, 23, 31, 40, 59],
                                         1)])
        found = tile(self.show(item), LATEST)
        self.assertFalse(rough(found.text()), found.text())
        self.assertNotIn("–", tile_value(found, LATEST))

    def test_the_usable_bulk(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.vessel("NV-1", "mg", "6")
        found = tile(self.show(item), BULK)
        self.assertTrue(has_amount(found.text(), "5", "mg"), found.text())

    def test_a_missing_figure_reads_a_dash(self) -> None:
        item = self.item("N-1")
        root = self.show(item)
        for label in (MEAN_QUARTER, MEAN_YEAR, COVERAGE, LATEST):
            with self.subTest(label=label):
                self.assertEqual(
                    tile_value(tile(root, label), label), "–")
        self.assertEqual(len(tiles(root)), len(LABELS))

    def test_an_item_without_a_forecast_still_has_every_tile(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        root = self.show(item)
        self.assertEqual(len(tiles(root)), len(LABELS))
        self.assertEqual(tile_value(tile(root, LATEST), LATEST), "–")
        self.assertIn("Kein Verbrauch, keine Prognose.",
                      widget(root, "Prognose").text())

    def test_the_this_year_tile(self) -> None:
        found = tile(self.show(self.means_item("CH-0012")), THIS_YEAR)
        self.assertEqual(tile_value(found, THIS_YEAR), "13")

    def test_the_english_page_marks_a_projection(self) -> None:
        accept(language="en")
        item = self.item("P-1", quantity=3)
        self.enter(item, 2026, 2, 6)
        found = tile(self.show(item), "Mean per year")
        self.assertTrue(carries(found, "class", "projected"), found.text())
        self.assertTrue(carries(found, "title",
                                "projected from the current year"))


class MovementsTableTests(ItemPageCase):

    def table(self, root: Element) -> Element:
        found = root.find("table", id="movements")
        self.assertIsNotNone(found, "the page has no table #movements")
        return found

    def movements(self, item: Any) -> list[Any]:
        """The item's movements, newest booking first."""
        return list(item.movements.order_by("-id"))

    def scenario_item(self) -> Any:
        """Three movements booked in the order of the dates 2026-03-01,
        2026-01-15 and 2026-02-10."""
        item = self.item("CH-0012", quantity=5, day=date(2026, 3, 1))
        self.deliver(item, 1, date(2026, 1, 15))
        self.deliver(item, 1, date(2026, 2, 10))
        return item

    def test_server_order_without_the_script(self) -> None:
        """Scenario: Server order without the script."""
        root = self.show(self.scenario_item())
        found = self.table(root)
        self.assertIn("data-sortable", found.attrs)
        self.assertTrue(found.get("id"))
        self.assertEqual([e for e in [found, *found.walk()]
                          if "aria-sort" in e.attrs], [])
        _, rows = grid(found)
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["Datum"].get("data-sort") for row in rows],
                         ["2026-02-10", "2026-01-15", "2026-03-01"])
        self.assertEqual([row["Datum"].text() for row in rows],
                         ["10.02.2026", "15.01.2026", "01.03.2026"])

    def test_the_table_is_in_the_movements_widget(self) -> None:
        root = self.show(self.scenario_item())
        found = widget(root, "Buchungen")
        self.assertIs(found.find("table", id="movements"),
                      self.table(root))

    def test_no_header_carries_aria_sort_for_a_signed_in_user(self) -> None:
        root = self.show(self.scenario_item(), signed_in=True)
        found = self.table(root)
        self.assertEqual([e for e in found.walk()
                          if "aria-sort" in e.attrs], [])

    def test_every_sortable_table_has_an_id_of_its_own(self) -> None:
        root = self.show(self.scenario_item())
        sortable = root.find_all("table", attrs={"data-sortable": True})
        self.assertTrue(sortable)
        ids = [t.get("id") for t in sortable]
        self.assertTrue(all(ids), ids)
        self.assertEqual(len(ids), len(set(ids)))
        every = [e.get("id") for e in root.walk() if e.get("id")]
        for one in ids:
            self.assertEqual(every.count(one), 1, one)

    def test_every_collapsible_widget_has_an_id(self) -> None:
        root = self.show(self.scenario_item())
        collapsible = [w for w in widgets(root) if w.tag == "details"]
        self.assertTrue(collapsible, "the page has no collapsible widget")
        for found in collapsible:
            self.assertTrue(found.get("id"), title_of(found))

    def test_the_date_cells_carry_the_iso_date(self) -> None:
        item = self.scenario_item()
        _, rows = grid(self.table(self.show(item)))
        for row, movement in zip(rows, self.movements(item), strict=True):
            with self.subTest(date=movement.date):
                self.assertEqual(row["Datum"].get("data-sort"),
                                 movement.date.isoformat())

    def test_the_date_cells_carry_the_iso_date_in_english(self) -> None:
        accept(language="en")
        item = self.scenario_item()
        _, rows = grid(self.table(self.show(item)))
        header = next(iter(rows[0]))
        self.assertEqual([r[header].get("data-sort") for r in rows],
                         ["2026-02-10", "2026-01-15", "2026-03-01"])

    def test_the_booking_times_carry_an_iso_moment(self) -> None:
        item = self.scenario_item()
        _, rows = grid(self.table(self.show(item)))
        for row in rows:
            cell = row["Gebucht am"]
            with self.subTest(shown=cell.text()):
                key = cell.get("data-sort")
                self.assertIsNotNone(key)
                self.assertRegex(key, ISO_MOMENT.pattern + r"\Z")
                found = re.search(
                    r"(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2})",
                    cell.text())
                self.assertIsNotNone(found, cell.text())
                day, month, year, hour, minute = found.groups()
                self.assertEqual(
                    key, f"{year}-{month}-{day}T{hour}:{minute}")

    def test_the_amount_cells_carry_their_value(self) -> None:
        item = self.item("CH-0012", quantity=10, day=date(2026, 3, 1))
        self.deliver(item, 2, date(2026, 5, 1))
        self.filling(item, 4, date(2026, 6, 1))
        from inventory.bookings import correct
        correct(self.kl, item, count=3, note="gezählt")
        _, rows = grid(self.table(self.show(item)))
        movements = self.movements(item)
        self.assertGreaterEqual(len(rows), 4)
        for row, movement in zip(rows, movements, strict=True):
            for header, expected in (("Anzahl", movement.count),
                                     ("Bestand danach",
                                      movement.quantity_after)):
                with self.subTest(kind=movement.kind, header=header):
                    key = row[header].get("data-sort")
                    self.assertIsNotNone(key)
                    self.assertEqual(Decimal(key.replace(",", ".")),
                                     Decimal(expected))

    def test_rows_run_in_booking_order_whatever_the_dates(self) -> None:
        item = self.item("CH-0012", quantity=5, day=date(2026, 3, 1))
        self.deliver(item, 1, date(2026, 1, 15))
        self.deliver(item, 1, date(2026, 2, 10))
        self.deliver(item, 1, date(2026, 10, 10))
        _, rows = grid(self.table(self.show(item)))
        self.assertEqual([r["Datum"].get("data-sort") for r in rows], [
            "2026-10-10", "2026-02-10", "2026-01-15", "2026-03-01"])

    def test_the_movements_keep_their_kinds(self) -> None:
        item = self.scenario_item()
        _, rows = grid(self.table(self.show(item)))
        kinds = [row["Art"].text() for row in rows]
        self.assertEqual(kinds, ["Abgabe", "Abgabe", "Anfangsbestand"])

    def test_a_reversed_kind_sorts_with_its_kind(self) -> None:
        """The kind cell's key is the kind alone, so that the reversal
        mark does not split rows of one kind when sorted."""
        from inventory.bookings import reverse
        item = self.scenario_item()
        delivery = item.movements.filter(kind="delivery").order_by(
            "id").first()
        reverse(self.kl, delivery, note="falsch")
        _, rows = grid(self.table(self.show(item)))
        marked = [row["Art"] for row in rows
                  if "storniert" in row["Art"].text()]
        self.assertEqual(len(marked), 1)
        self.assertEqual(marked[0].get("data-sort"), "Abgabe")

    def test_the_date_key_is_a_key_sort_order_reads(self) -> None:
        """A date key is ``YYYY-MM-DD``, else ``sortOrder`` of lab.js
        would read it as text."""
        item = self.scenario_item()
        _, rows = grid(self.table(self.show(item)))
        for row in rows:
            self.assertRegex(row["Datum"].get("data-sort"),
                             ISO_DATE.pattern + r"\Z")


class ForecastWidgetTests(ItemPageCase):

    KEYS = ["Bedarfsmodell", "Reichweite des Bestands", "Nutzbares Bulk",
            "Reichweite", "Synthesedauer", "Spielraum", "Spätester Start",
            "Priorität", "Neue Synthese"]
    RHYTHM = ["Letzte Lieferung", "Lieferungen der letzten 365 Tage",
              "Übliches Intervall", "Nächste Lieferung erwartet"]

    def forecast(self, item: Any) -> Element:
        return widget(self.show(item), "Prognose")

    def bold(self, cell: Element) -> str:
        """The text of the cell's bold figures outside its ``kv-sub``
        lines."""
        subs = [e for e in cell.walk() if "kv-sub" in e.classes]
        inside = {id(n) for s in subs for n in (s, *s.walk())}
        return " ".join(e.text() for e in cell.find_all(("strong", "b"))
                        if id(e) not in inside)

    def sub(self, cell: Element) -> str:
        return " ".join(e.text() for e in cell.find_all(cls="kv-sub"))

    def test_the_forecast_is_a_key_value_widget(self) -> None:
        found = self.forecast(self.planned_item("NV-1", quantity=10))
        self.assertEqual(found.tag, "section")
        self.assertIsNotNone(found.find("table", cls="kv-table"))
        keys = kv(found)
        for key in self.KEYS:
            with self.subTest(key=key):
                self.assertIn(key, keys)

    def test_the_article_and_the_rhythm_keep_their_sub_headings(
            self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        found = self.forecast(item)
        headings = [h.text() for h in found.find_all("h3")]
        self.assertIn("Artikel NV-1", headings)
        self.assertIn("Lieferrhythmus", headings)

    def test_the_delivery_rhythm_is_in_the_widget(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        for day in (date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 31),
                    date(2026, 10, 1)):
            self.deliver(item, 1, day)
        found = self.forecast(item)
        keys = kv(found)
        for key in self.RHYTHM:
            with self.subTest(key=key):
                self.assertIn(key, keys)
        self.assertTrue(has_date(keys["Letzte Lieferung"].text(),
                                 date(2026, 10, 1)))
        self.assertTrue(has_number(
            keys["Lieferungen der letzten 365 Tage"].text(), "4"))
        self.assertTrue(has_days(keys["Übliches Intervall"].text(), 31))
        self.assertTrue(has_date(keys["Nächste Lieferung erwartet"].text(),
                                 date(2026, 11, 1)))

    def test_no_interval_without_three_deliveries(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 20)
        self.deliver(item, 2, date(2026, 8, 1))
        self.deliver(item, 2, date(2026, 9, 1))
        keys = kv(self.forecast(item))
        self.assertIn("weniger als drei Lieferungen",
                      keys["Übliches Intervall"].text())
        self.assertEqual(keys["Nächste Lieferung erwartet"].text(), "–")

    def test_each_figure_is_bold_and_its_parameters_are_beneath(
            self) -> None:
        keys = kv(self.forecast(self.planned_item("NV-1", quantity=10)))
        for key in ("Reichweite", "Spielraum", "Priorität",
                    "Neue Synthese", "Synthesedauer", "Spätester Start",
                    "Nutzbares Bulk", "Reichweite des Bestands"):
            with self.subTest(key=key):
                self.assertTrue(self.bold(keys[key]),
                                f"{key} shows no bold figure")
        for key in ("Reichweite", "Spielraum", "Priorität",
                    "Neue Synthese", "Synthesedauer", "Nutzbares Bulk",
                    "Reichweite des Bestands"):
            with self.subTest(key=key):
                self.assertTrue(self.sub(keys[key]),
                                f"{key} shows no .kv-sub line")

    def test_the_bold_figures(self) -> None:
        keys = kv(self.forecast(self.planned_item("NV-1", quantity=10)))
        self.assertTrue(has_days(self.bold(keys["Reichweite"]), 60),
                        self.bold(keys["Reichweite"]))
        self.assertTrue(has_days(self.bold(keys["Spielraum"]), 11),
                        self.bold(keys["Spielraum"]))
        self.assertTrue(has_days(self.bold(keys["Synthesedauer"]), 21),
                        self.bold(keys["Synthesedauer"]))
        self.assertTrue(has_date(self.bold(keys["Spätester Start"]),
                                 date(2026, 11, 15)),
                        self.bold(keys["Spätester Start"]))
        self.assertTrue(has_amount(self.bold(keys["Neue Synthese"]), "42",
                                   "mg"), self.bold(keys["Neue Synthese"]))
        self.assertIn("hoch", self.bold(keys["Priorität"]))

    def test_the_parameters_beneath_the_defaults(self) -> None:
        keys = kv(self.forecast(self.planned_item("NV-1", quantity=10)))
        self.assertRegex(self.sub(keys["Reichweite"]),
                         r"(?<![\d,.])(?:0,95|95)(?!\d)")
        self.assertTrue(has_number(self.sub(keys["Spielraum"]), "28"),
                        self.sub(keys["Spielraum"]))
        sub = self.sub(keys["Neue Synthese"])
        for shown in ("28", "365"):
            self.assertTrue(has_number(sub, shown), sub)
        self.assertRegex(sub, r"(?<![\d,.])(?:0,95|95)(?!\d)")
        sub = self.sub(keys["Priorität"])
        for shown in ("14", "56"):
            self.assertTrue(has_number(sub, shown), sub)
        self.assertIn("Vorgabe", self.sub(keys["Synthesedauer"]))

    def test_the_parameters_beneath_follow_the_settings(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.parameters(certainty=0.9, buffer_days=33, target_days=222)
        keys = kv(self.forecast(item))
        self.assertRegex(self.sub(keys["Reichweite"]), CERTAINTY)
        self.assertTrue(has_number(self.sub(keys["Spielraum"]), "33"),
                        self.sub(keys["Spielraum"]))
        sub = self.sub(keys["Neue Synthese"])
        for shown in ("33", "222"):
            self.assertTrue(has_number(sub, shown), sub)
        self.assertRegex(sub, CERTAINTY)
        self.assertRegex(self.sub(keys["Reichweite des Bestands"]),
                         CERTAINTY)

    def test_the_basis_of_the_synthesis_time_is_beneath(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        keys = kv(self.forecast(item))
        self.assertTrue(has_days(self.bold(keys["Synthesedauer"]), 40))
        self.assertIn("längste der letzten 3 Synthesen",
                      self.sub(keys["Synthesedauer"]))

    def test_a_rough_figure_keeps_its_mark(self) -> None:
        text = self.forecast(self.planned_item("NV-1", quantity=10)).text()
        self.assertGreaterEqual(len(re.findall(r"(?<!\w)grob", text)), 5)

    def test_the_demand_model(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        self.orders(item, *[(date(2026, month, 10), size) for month, size
                            in enumerate([2, 3, 5, 8, 17, 23, 31, 40, 59],
                                         1)])
        keys = kv(self.forecast(item))
        text = keys["Bedarfsmodell"].text()
        for shown in ("9", "17", "59"):
            self.assertTrue(has_number(text, shown), text)
        self.assertFalse(rough(text), text)

    def test_the_figures_of_an_article_of_two_sizes(self) -> None:
        small = self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        from .planning_support import WINDOW
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.vessel("NV-2", "mg", "360")
        for item in (small, large):
            with self.subTest(size=item.size):
                keys = kv(self.forecast(item))
                self.assertTrue(has_amount(
                    keys["Nutzbares Bulk"].text(), "340", "mg"),
                    keys["Nutzbares Bulk"].text())
                self.assertTrue(has_days(keys["Reichweite"].text(), 62))
                self.assertTrue(has_days(keys["Spielraum"].text(), 13))

    def test_an_item_without_a_forecast_says_so_in_the_widget(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        found = self.forecast(item)
        self.assertIn("Kein Verbrauch, keine Prognose.", found.text())
        self.assertEqual(kv_rows(found), [])

    def test_a_dormant_item_says_so_in_the_widget(self) -> None:
        from inventory.models import Item
        item = self.planned_item("NV-1", quantity=10)
        Item.objects.filter(pk=item.pk).update(status="discontinued")
        self.assertIn("Ruhend, keine Prognose.", self.forecast(item).text())

    def test_the_forecast_is_public(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.client.logout()
        self.assertIn("Spielraum", kv(self.forecast(item)))
        self.assertIn("Spielraum", kv(widget(
            self.show(item, signed_in=True), "Prognose")))

    def test_the_english_page(self) -> None:
        accept(language="en")
        item = self.planned_item("NV-1", quantity=10)
        found = widget(self.show(item), "Forecast")
        keys = kv(found)
        for key in ("Slack", "Latest start", "Priority", "New synthesis",
                    "Last delivery", "Next delivery expected"):
            with self.subTest(key=key):
                self.assertIn(key, keys)
