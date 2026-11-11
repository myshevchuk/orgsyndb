"""Tests of the item list's table: its columns and order, the filters
above it, the stock menu, the popups, the view controls, the
consumption heat and the box that keeps the headers in view
(end-product-inventory: Item list, Consumption heat)."""

import re
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from django.test import SimpleTestCase

from inventory.models import Item

from . import (berlin, build_index, field_value, make_substance, page, table,
               ticking)
from .inventory_support import LIST, InventoryCase, fresh, item_url, lot_url
from .test_inventory_colours import (CSS, MINIMUM, balanced, contrast,
                                     split_schemes)

SORTS = ("number", "name", "category", "container", "stock", "mean_year",
         "this_year", "coverage", "compartment", "box", "bulk", "note")
COLUMNS = ["Artikelnr.", "Name", "Kategorie", "Gebinde", "Bestand",
           "Ø Jahr", "Abgegeben", "Reichweite", "Lagerort", "Fach", "Box",
           "Bulk verfügbar", "Bemerkung"]
KEYS = ["number", "name", "category", "container", "stock", "mean_year",
        "this_year", "coverage", "location", "compartment", "box", "bulk",
        "note"]
SORTED_COLUMNS = {key: column for key, column in zip(KEYS, COLUMNS)
                  if key != "location"}
# The columns the view controls may hide, and those hidden at first.
OPTIONAL = [key for key in KEYS if key not in ("number", "name", "stock")]
HIDDEN = {"compartment", "box", "note"}
LEVEL_VALUES = ["out", "critical", "low", "watch", "ok", "undelivered",
                "dormant"]
LEVEL_LABELS = ["aufgebraucht", "kritisch", "niedrig", "beobachten",
                "ausreichend", "noch nie abgegeben", "ruhend"]
HEATS = [f"heat-{n}" for n in range(1, 6)]


def kept(item: Item, compartment: str, box: str = "") -> Item:
    Item.objects.filter(pk=item.pk).update(compartment=compartment, box=box)
    return fresh(item)


def query_of(href: str) -> dict[str, list[str]]:
    """The parameters of HREF, a link to the item list."""
    parts = urlsplit(href)
    if parts.path:
        assert parts.path == LIST, href
    return parse_qs(parts.query)


def heat_of(cell) -> str | None:
    found = [name for name in HEATS if name in cell.classes]
    assert len(found) <= 1, cell.classes
    return found[0] if found else None


def outside_popups(element) -> str:
    """The text of ELEMENT without that of the popups inside it."""
    return element.text(lambda node: "popover" in node.attrs)


def body_rows(root) -> list:
    """The rows of the body of the page's first table, without those of
    the tables inside its cells."""
    grid = root.find("table")
    return [tr for tr in grid.find("tbody").find_all("tr")
            if tr.closest("table") is grid]


def popup_of(root, button):
    """The popup BUTTON opens, which must lie in the button's cell."""
    target = button.get("popovertarget")
    assert target, "the button opens no popup"
    found = root.find(id=target)
    assert found is not None, target
    assert "popover" in found.attrs, target
    assert found.closest("td") is button.closest("td"), target
    return found


class TableCase(InventoryCase):

    def listing(self, query: str = ""):
        response = self.client.get(LIST + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def articles(self, query: str = "") -> list[str]:
        header, rows = table(self.listing(query))
        return [row[header[0]].text() for row in rows]

    def keys(self, query: str = "") -> list[str]:
        """Each row as its article number, or name, and container."""
        header, rows = table(self.listing(query))
        return [" ".join([row[header[0]].text() or row[header[1]].text(),
                          row["Gebinde"].text()]) for row in rows]

    def headers(self, root) -> dict[str, object]:
        """The header cells of the table's first row by their text."""
        first = root.find("table").find("thead").find("tr")
        return {th.text(lambda node: node.tag == "small"): th
                for th in first.find_all("th")}

    def header_link(self, root, column: str) -> dict[str, list[str]]:
        return query_of(self.headers(root)[column].find("a").get("href"))

    def summary(self, root) -> str:
        return root.find("p", "list-summary").text()

    def reset_link(self, root):
        found = [a for a in root.find_all("a") if a.text() == "Zurücksetzen"]
        self.assertLessEqual(len(found), 1)
        return found[0] if found else None


class ColumnTests(TableCase):

    def test_the_columns_and_their_units(self) -> None:
        self.item("T-1")
        root = self.listing()
        header, _ = table(root)
        self.assertEqual(header, COLUMNS)
        units = {name: th.find("small").text()
                 for name, th in self.headers(root).items()
                 if th.find("small")}
        self.assertEqual(units, {
            "Bestand": "Gebinde", "Ø Jahr": "Gebinde / Jahr",
            "Abgegeben": "2026 · Gebinde", "Reichweite": "Quartale"})

    def test_the_english_columns(self) -> None:
        self.use_index(build_index("en"))
        self.item("T-1")
        root = self.listing()
        header, _ = table(root)
        self.assertEqual(header, [
            "Article no.", "Name", "Category", "Container", "Stock",
            "Mean per year", "Delivered", "Coverage", "Location",
            "Compartment", "Box", "Bulk available", "Note"])
        units = [th.find("small").text()
                 for th in self.headers(root).values() if th.find("small")]
        self.assertEqual(units, ["containers", "containers / year",
                                 "2026 · containers", "quarters"])

    def test_every_cell_names_its_column(self) -> None:
        self.item("T-1")
        self.item(None, "Ohne Nummer")
        grid = self.listing().find("table")
        for tr in [tr for tr in grid.find_all("tr")
                   if tr.closest("table") is grid]:
            cells = [c for c in tr.children
                     if not isinstance(c, str) and c.tag in ("th", "td")]
            with self.subTest(row=tr.text()[:30]):
                self.assertEqual(len(cells), len(KEYS))
                for key, cell in zip(KEYS, cells):
                    self.assertIn(f"col-{key}", cell.classes)

    def test_the_heading_counts_the_inventory(self) -> None:
        self.item("T-1", category="A")
        self.item("T-2", category="B")
        heading = self.listing("?category=A").find(cls="lab-heading")
        self.assertEqual(heading.find("h1").text(), "Endprodukte")
        self.assertIn("2 Artikel", heading.text())


class SortTests(TableCase):

    def test_by_category_first(self) -> None:
        """Scenario: By category first."""
        self.item("A-2", category="Ester")
        self.item("A-1", category="Säuren")
        self.item("A-3", category="Ester")
        self.item("A-4")
        root = self.listing()
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["A-2", "A-3", "A-1", "A-4"])
        body = body_rows(root)
        self.assertEqual(["category-start" in tr.classes for tr in body],
                         [False, False, True, True])
        self.assertEqual(self.headers(root)["Kategorie"].get("aria-sort"),
                         "ascending")
        self.assertEqual(self.summary(root), "4 von 4 Artikeln · "
                         "Kategorie, Artikelnr., Gebinde aufsteigend")

    def test_categories_start_in_descending_order_too(self) -> None:
        self.item("A-1", category="Ester")
        self.item("A-2", category="Säuren")
        self.item("A-3", category="Säuren")
        body = body_rows(self.listing("?sort=category&dir=desc"))
        self.assertEqual(["category-start" in tr.classes for tr in body],
                         [False, False, True])

    def test_only_the_category_order_marks_categories(self) -> None:
        self.item("A-1", category="Ester")
        self.item("A-2", category="Säuren")
        body = body_rows(self.listing("?sort=number"))
        self.assertFalse(any("category-start" in tr.classes
                             for tr in body))

    def test_sizes_by_amount(self) -> None:
        """Scenario: Sizes by amount."""
        self.item("CH-0012", size="1", unit="g")
        self.item("CH-0012", size="100", unit="mg")
        self.item("CH-0012", size="500", unit="mg")
        self.assertEqual(self.keys(), ["CH-0012 100 mg", "CH-0012 500 mg",
                                       "CH-0012 1 g"])
        self.assertEqual(self.keys("?sort=number"), self.keys())

    def test_sorting_by_a_column(self) -> None:
        """Scenario: Sorting by a column."""
        self.item("A-1", category="Säuren")
        self.item("A-2")
        self.item("A-3", category="Ester")
        root = self.listing("?sort=category")
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["A-3", "A-1", "A-2"])
        descending = self.listing("?sort=category&dir=desc")
        header, rows = table(descending)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["A-1", "A-3", "A-2"])
        headers = self.headers(root)
        self.assertEqual(headers["Kategorie"].get("aria-sort"), "ascending")
        self.assertEqual(self.header_link(root, "Kategorie"),
                         {"sort": ["category"], "dir": ["desc"]})
        self.assertEqual(self.header_link(root, "Artikelnr."),
                         {"sort": ["number"]})
        self.assertIsNone(headers["Lagerort"].find("a"))
        self.assertEqual([name for name, th in headers.items()
                          if th.get("aria-sort") is not None],
                         ["Kategorie"])
        self.assertEqual(self.summary(descending).split(" · ", 1)[1],
                         "Kategorie absteigend, Artikelnr., Gebinde "
                         "aufsteigend")

    def test_the_order_line_names_the_tie_breakers(self) -> None:
        self.item("S-1")
        for query, order in (
                ("?sort=number", "Artikelnr., Gebinde aufsteigend"),
                ("?sort=number&dir=desc",
                 "Artikelnr. absteigend, Gebinde aufsteigend"),
                ("?sort=container", "Gebinde, Artikelnr. aufsteigend"),
                ("?sort=stock&dir=desc",
                 "Bestand absteigend, Artikelnr., Gebinde aufsteigend"),
                ("?sort=bulk",
                 "Bulk verfügbar, Artikelnr., Gebinde aufsteigend")):
            with self.subTest(query=query):
                self.assertEqual(self.summary(self.listing(query)),
                                 f"1 von 1 Artikel · {order}")

    def test_the_english_order_line(self) -> None:
        self.use_index(build_index("en"))
        self.item("S-1")
        self.item("S-2")
        self.assertEqual(self.summary(self.listing()),
                         "2 of 2 items · Category, Article no., Container "
                         "ascending")

    def test_containers_and_locations_in_their_order(self) -> None:
        """Scenario: Containers and locations in their order."""
        kept(self.item("C-1", size="1", unit="g"), "10")
        kept(self.item("C-2", size="100", unit="mg"), "2")
        kept(self.item("C-3", size="10", unit="umol"), "")
        kept(self.item("C-4", size="250", unit="mg"), "3")
        for query in ("?sort=container", "?sort=compartment"):
            with self.subTest(query=query):
                self.assertEqual(self.articles(query),
                                 ["C-2", "C-4", "C-1", "C-3"])

    def test_every_column_sorts_both_ways(self) -> None:
        self.item("S-1")
        self.item("S-2")
        for key, column in SORTED_COLUMNS.items():
            for direction, shown in (("", "ascending"),
                                     ("&dir=desc", "descending")):
                with self.subTest(sort=key, dir=shown):
                    root = self.listing(f"?sort={key}{direction}")
                    self.assertEqual(self.headers(root)[column]
                                     .get("aria-sort"), shown)
                    link = self.header_link(root, column)
                    self.assertEqual(link["sort"], [key])
                    self.assertEqual(link.get("dir"),
                                     None if direction else ["desc"])

    def test_the_default_order_is_by_category(self) -> None:
        self.item("B-2")
        self.item("B-1")
        self.item(None, "Zeta")
        self.item(None, "alpha")
        for query in ("", "?sort=xyz", "?sort=category", "?dir=up",
                      "?sort=urgency"):
            with self.subTest(query=query):
                root = self.listing(query)
                self.assertEqual(self.headers(root)["Kategorie"]
                                 .get("aria-sort"), "ascending")
                self.assertEqual(self.keys(query), [
                    "B-1 10 µmol", "B-2 10 µmol", "alpha 10 µmol",
                    "Zeta 10 µmol"])

    def test_descending_article_numbers_keep_the_rest_last(self) -> None:
        self.item("B-1", size="5", unit="mg")
        self.item("B-1", size="1", unit="g")
        self.item("B-2")
        self.item(None, "Zeta")
        self.item(None, "alpha")
        self.assertEqual(self.keys("?sort=number&dir=desc"), [
            "B-2 10 µmol", "B-1 5 mg", "B-1 1 g", "alpha 10 µmol",
            "Zeta 10 µmol"])

    def test_text_regardless_of_case(self) -> None:
        self.item("T-1", name="beta", note="Zwei")
        self.item("T-2", name="Alpha", note="eins")
        self.item("T-3", name="Gamma")
        self.assertEqual(self.articles("?sort=name"), ["T-2", "T-1", "T-3"])
        self.assertEqual(self.articles("?sort=note"), ["T-2", "T-1", "T-3"])
        self.assertEqual(self.articles("?sort=note&dir=desc"),
                         ["T-1", "T-2", "T-3"])

    def test_locations_regardless_of_case_and_empty_last(self) -> None:
        kept(self.item("L-1"), "", "b")
        kept(self.item("L-2"), "", "A")
        kept(self.item("L-3"), "", "")
        kept(self.item("L-4"), "", "a10")
        kept(self.item("L-5"), "", "a9")
        self.assertEqual(self.articles("?sort=box"),
                         ["L-2", "L-5", "L-4", "L-1", "L-3"])
        self.assertEqual(self.articles("?sort=box&dir=desc"),
                         ["L-1", "L-4", "L-5", "L-2", "L-3"])

    def test_numbers_with_items_without_a_value_last(self) -> None:
        self.with_mean_quarter(self.item("N-1", quantity=20), 4)
        self.with_mean_quarter(self.item("N-2", quantity=2), 1)
        self.item("N-3", quantity=2)
        self.item("N-4")
        for key in ("mean_year", "coverage"):
            with self.subTest(sort=key):
                ascending = self.articles(f"?sort={key}")
                descending = self.articles(f"?sort={key}&dir=desc")
                self.assertEqual(ascending[2:], ["N-3", "N-4"])
                self.assertEqual(descending[2:], ["N-3", "N-4"])
                self.assertEqual(ascending[:2], descending[1::-1])
        self.assertEqual(self.articles("?sort=mean_year"),
                         ["N-2", "N-1", "N-3", "N-4"])

    def test_this_years_zero_is_a_value(self) -> None:
        self.item("Y-1")
        self.enter(self.item("Y-2"), 2026, 1, 3)
        self.enter(self.item("Y-3"), 2026, 1, 1)
        self.assertEqual(self.articles("?sort=this_year"),
                         ["Y-1", "Y-3", "Y-2"])
        self.assertEqual(self.articles("?sort=this_year&dir=desc"),
                         ["Y-2", "Y-3", "Y-1"])

    def test_stock_by_level_then_coverage(self) -> None:
        for article, quantity in (("A-1", 7), ("A-2", 8), ("A-3", 0),
                                  ("A-4", 2), ("A-5", 1)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        self.assertEqual(self.articles("?sort=stock"),
                         ["A-3", "A-5", "A-4", "A-1", "A-2"])
        self.assertEqual(self.articles("?sort=stock&dir=desc"),
                         ["A-2", "A-1", "A-4", "A-5", "A-3"])

    def test_bulk_by_the_containers_it_fills(self) -> None:
        self.item("CH-0001", size="10", unit="mg")
        self.item("CH-0002", size="10", unit="mg")
        self.item("CH-0010", size="10", unit="mg")
        self.lot("CH-0001", "mg", "50")
        self.lot("CH-0002", "mg", "5")
        self.assertEqual(self.articles("?sort=bulk"),
                         ["CH-0002", "CH-0001", "CH-0010"])
        self.assertEqual(self.articles("?sort=bulk&dir=desc"),
                         ["CH-0001", "CH-0002", "CH-0010"])

    def test_ties_keep_the_default_order(self) -> None:
        for article in ("E-2", "E-3", "E-1"):
            self.item(article, category="Gleich")
        for query in ("?sort=category", "?sort=category&dir=desc"):
            with self.subTest(query=query):
                self.assertEqual(self.articles(query), ["E-1", "E-2", "E-3"])

    def test_the_header_links_keep_the_filters(self) -> None:
        self.item("K-1", category="Grün")
        root = self.listing(f"?category={quote('Grün')}&q=k&stock=watch"
                            "&sort=name&dir=desc")
        self.assertEqual(self.header_link(root, "Name"), {
            "category": ["Grün"], "q": ["k"], "stock": ["watch"],
            "sort": ["name"]})
        self.assertEqual(self.header_link(root, "Bulk verfügbar"), {
            "category": ["Grün"], "q": ["k"], "stock": ["watch"],
            "sort": ["bulk"]})


class FilterTests(TableCase):

    def test_filters_above_the_table(self) -> None:
        """Scenario: Filters above the table."""
        self.item("CH-0012", "(E)-Zimtsäure", "100", "mg",
                  category="Säuren", note="Kühlschrank")
        self.item("CH-0010", "Aspirin", "1", "g", category="Säuren")
        self.item("CH-0016", "Isopentylacetat", "100", "mg",
                  category="Ester")
        for query, wanted, name, value in (
                ("?q=ZIMT", ["CH-0012"], "q", "ZIMT"),
                (f"?q={quote('kühl')}", ["CH-0012"], "q", "kühl"),
                ("?category=Ester", ["CH-0016"], "category", "Ester"),
                (f"?container={quote('100 mg')}", ["CH-0016", "CH-0012"],
                 "container", "100 mg")):
            with self.subTest(query=query):
                root = self.listing(query)
                header, rows = table(root)
                self.assertEqual([row[header[0]].text() for row in rows],
                                 wanted)
                self.assertEqual(field_value(root, name), value)
        root = self.listing(f"?container={quote('100 mg')}"
                            "&sort=name&dir=desc")
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["CH-0016", "CH-0012"])
        self.assertEqual(self.header_link(root, "Name"),
                         {"container": ["100 mg"], "sort": ["name"]})
        self.assertEqual(query_of(self.reset_link(root).get("href")),
                         {"sort": ["name"], "dir": ["desc"]})
        self.assertIsNone(self.reset_link(self.listing()))

    def test_the_form_above_the_table(self) -> None:
        self.item("F-1", category="Ester")
        root = self.listing()
        self.assertEqual(len(root.find("thead").find_all("tr")), 1)
        form = root.find("form", id="filters")
        self.assertEqual(form.get("method"), "get")
        self.assertEqual(form.get("action"), LIST)
        self.assertIsNone(form.closest("table"))
        search = form.find("input", name="q")
        self.assertEqual(search.get("type"), "search")
        self.assertIn("Artikel suchen", search.parent.text())
        category = form.find("select", name="category")
        self.assertIn("Kategorie", category.parent.text())
        self.assertIn("data-submit", category.attrs)
        self.assertEqual([(o.get("value"), o.text())
                          for o in category.find_all("option")],
                         [("", "Alle Kategorien"), ("Ester", "Ester")])
        self.assertEqual(form.find("button", type="submit").text(),
                         "Filtern")
        for name in ("number", "name", "note"):
            self.assertIsNone(root.find(("input", "select"), name=name))

    def test_the_more_filters(self) -> None:
        kept(self.item("G-1", size="2.5", unit="mg"), "2", "7")
        kept(self.item("G-2", size="10", unit="umol"), "10", "7")
        root = self.listing()
        button = root.find("button", attrs={"popovertarget": "more-filters"})
        self.assertEqual(button.text(), "Weitere Filter")
        popup = root.find(id="more-filters")
        self.assertIn("popover", popup.attrs)
        for name, label in (("container", "Gebinde"),
                            ("compartment", "Fach"), ("box", "Box")):
            with self.subTest(name=name):
                control = popup.find("select", name=name)
                self.assertEqual(control.get("form"), "filters")
                self.assertIn("data-submit", control.attrs)
                self.assertIn(label, control.parent.text())
        self.assertEqual([(o.get("value"), o.text()) for o in popup.find(
            "select", name="compartment").find_all("option")],
            [("", "Alle"), ("2", "2"), ("10", "10")])

    def test_locations(self) -> None:
        """Scenario: Locations."""
        kept(self.item("L-1"), "2", "7")
        kept(self.item("L-2"), "10", "7")
        for query, wanted in (("?compartment=2", ["L-1"]),
                              ("?box=7", ["L-1", "L-2"])):
            with self.subTest(query=query):
                root = self.listing(query)
                header, rows = table(root)
                self.assertEqual([row[header[0]].text() for row in rows],
                                 wanted)
                for row in rows:
                    shown = popup_of(root, row["Lagerort"].find("button"))
                    self.assertIn(row["Fach"].text(), shown.text())
                    self.assertIn("7", shown.text())
                self.assertEqual(root.find("button", attrs={
                    "popovertarget": "more-filters"}).text(),
                    "Weitere Filter (1)")

    def test_the_container_choice(self) -> None:
        self.item("G-1", size="2.5", unit="mg")
        self.item("G-2", size="10", unit="umol")
        self.item("G-3", size="1", unit="g")
        self.item("G-4", size="2.5", unit="mg")
        root = self.listing(f"?container={quote('10 umol')}")
        options = root.find("select", name="container").find_all("option")
        self.assertEqual([(o.get("value"), o.text()) for o in options], [
            ("", "Alle"), ("2.5 mg", "2,5 mg"), ("1 g", "1 g"),
            ("10 umol", "10 µmol")])
        self.assertEqual(field_value(root, "container"), "10 umol")
        self.assertEqual(self.articles(f"?container={quote('2.5 mg')}"),
                         ["G-1", "G-4"])

    def test_the_search_finds_the_substances_names(self) -> None:
        self.item("CH-0012")
        self.item("CH-0001")
        for text in ("zimts", "CINNAMIC", "(e)-cinn"):
            with self.subTest(q=text):
                self.assertEqual(self.articles(f"?q={quote(text)}"),
                                 ["CH-0012"])

    def test_the_search_finds_the_substances_key(self) -> None:
        self.item("CH-0012")
        self.item("CH-0001")
        self.assertEqual(self.articles("?q=bromophenyl-ethanol"),
                         ["CH-0001"])

    def test_the_search_finds_the_short_name(self) -> None:
        self.item("S-1", substance=make_substance("s-1", short_name="ZS"))
        self.item("S-2")
        self.assertEqual(self.articles("?q=zs"), ["S-1"])

    def test_the_search_finds_the_article_number_and_category(self) -> None:
        self.item("S-1", category="Säuren")
        self.item("S-2")
        self.assertEqual(self.articles("?q=s-1"), ["S-1"])
        self.assertEqual(self.articles(f"?q={quote('säur')}"), ["S-1"])

    def test_the_filters_keep_the_order_and_the_level(self) -> None:
        self.item("O-1")
        root = self.listing("?sort=coverage&dir=desc&q=o&stock=ok")
        form = root.find("form", id="filters")
        hidden = {i.get("name"): i.get("value") for i in
                  form.find_all("input", type="hidden")}
        self.assertEqual(hidden, {"sort": "coverage", "dir": "desc",
                                  "stock": "ok"})
        self.assertEqual(field_value(root, "q"), "o")

    def test_without_a_reversed_order_no_dir_is_kept(self) -> None:
        self.item("O-1")
        form = self.listing().find("form", id="filters")
        self.assertEqual({i.get("name"): i.get("value") for i in
                          form.find_all("input", type="hidden")},
                         {"sort": "category"})

    def test_the_column_filters_are_gone(self) -> None:
        self.item("CH-0012", "(E)-Zimtsäure", note="Kühlschrank")
        self.item("CH-0010", "Aspirin")
        for query in ("?number=0012", "?name=zimt", "?note=kühl",
                      "?level=out"):
            with self.subTest(query=query):
                self.assertEqual(self.articles(query),
                                 ["CH-0010", "CH-0012"])


class StockMenuTests(TableCase):

    def menu(self, root):
        button = root.find("button", attrs={"popovertarget": "stock-menu"})
        self.assertIsNotNone(button)
        popup = root.find(id="stock-menu")
        self.assertIn("popover", popup.attrs)
        return button, popup

    def entries(self, popup) -> list[tuple[str, str, str]]:
        """Each entry's label, count and link."""
        found = []
        for link in popup.find_all("a"):
            found.append((link.find("strong").text(),
                          link.find("span", "count").text(),
                          link.get("href")))
        return found

    def test_stock_menu_with_counts(self) -> None:
        """Scenario: Stock menu with counts."""
        self.with_mean_quarter(self.item("O-1", quantity=20,
                                         category="A"), 1)
        self.with_mean_quarter(self.item("O-2", quantity=20,
                                         category="A"), 1)
        self.with_mean_quarter(self.item("L-1", quantity=3,
                                         category="A"), 4)
        dormant = self.with_mean_quarter(self.item("D-1", category="B"), 1)
        Item.objects.filter(pk=dormant.pk).update(status="discontinued")
        root = self.listing("?category=A")
        button, popup = self.menu(root)
        self.assertEqual(button.text(), "Alle (3)")
        entries = self.entries(popup)
        self.assertEqual([label for label, _, _ in entries],
                         ["Alle Bestandsstatus", "Aufgebraucht",
                          "Kritisch", "Niedrig", "Beobachten",
                          "Ausreichend", "Noch nie abgegeben", "Ruhend"])
        self.assertEqual([count for _, count, _ in entries],
                         ["3", "0", "0", "1", "0", "2", "0", "0"])
        self.assertEqual(query_of(entries[3][2]),
                         {"category": ["A"], "stock": ["low"],
                          "sort": ["category"]})
        self.assertEqual(query_of(entries[0][2]),
                         {"category": ["A"], "sort": ["category"]})

    def test_one_level_exactly(self) -> None:
        """Scenario: One level exactly."""
        for article, quantity in (("A-1", 0), ("A-2", 1), ("A-3", 3)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        root = self.listing("?stock=critical")
        self.assertEqual(self.articles("?stock=critical"), ["A-2"])
        button, popup = self.menu(root)
        self.assertEqual(button.text(), "Kritisch (1)")
        current = [link for link in popup.find_all("a")
                   if link.get("aria-current") == "true"]
        self.assertEqual([link.find("strong").text() for link in current],
                         ["Kritisch"])
        self.assertEqual(self.entries(popup)[0][1], "3")

    def test_each_level_shows_its_colour_and_meaning(self) -> None:
        self.item("M-1")
        _, popup = self.menu(self.listing())
        links = popup.find_all("a")[1:]
        self.assertEqual(len(links), 7)
        for level, link in zip(LEVEL_VALUES, links):
            with self.subTest(level=level):
                self.assertIsNotNone(link.find(cls=f"level-{level}"))
                self.assertTrue(link.find("small").text())
        self.assertEqual(links[1].find("small").text(),
                         "unter dem halben Durchschnitt je Quartal")

    def test_an_unknown_level_lists_everything(self) -> None:
        self.item("U-1")
        root = self.listing("?stock=urgent")
        button, popup = self.menu(root)
        self.assertEqual(button.text(), "Alle (1)")
        self.assertEqual(self.articles("?stock=urgent"), ["U-1"])

    def test_the_legend_is_gone(self) -> None:
        self.item("G-1")
        root = self.listing()
        self.assertIsNone(root.find("dl", "level-legend"))
        note = root.find("p", "lab-table-note").text()
        self.assertIn("Bestandsstatus", note)
        self.assertIn("Ort", note)
        self.assertIn("Abgegeben", note)


class PopupTests(TableCase):

    def test_location_popup(self) -> None:
        """Scenario: Location popup."""
        item = self.item("CH-0012", "(E)-Zimtsäure", "100", "mg",
                         quantity=3)
        lot = self.lot("CH-0012", "mg", "50", batch="B-7",
                       location="Kühlschrank 2")
        root = self.listing()
        _, rows = table(root)
        cell = rows[0]["Lagerort"]
        button = cell.find("button")
        self.assertEqual(outside_popups(cell), "Ort")
        self.assertEqual(button.get("type"), "button")
        self.assertIn("Lagerort", button.get("aria-label"))
        self.assertIn("(E)-Zimtsäure", button.get("aria-label"))
        popup = popup_of(root, button)
        heading = popup.find("h2")
        self.assertEqual(heading.text(), "Lagerort · (E)-Zimtsäure")
        text = popup.text()
        for shown in ("CH-0012", "100 mg", "3 Gebinde", "Fertige Gebinde",
                      "Bulk, separat gelagert", "Kühlschrank 2"):
            self.assertIn(shown, text)
        self.assertEqual(text.count("nicht hinterlegt"), 2)
        links = {a.get("href"): a.text() for a in popup.find_all("a")}
        self.assertIn("B-7", links[lot_url(lot)])
        self.assertIn(item_url(item), links)

    def test_a_kept_item_and_a_lot_without_location(self) -> None:
        kept(self.item("CH-0012", quantity=1), "2", "7")
        self.lot("CH-0012", "mg", "50")
        root = self.listing()
        _, rows = table(root)
        popup = popup_of(root, rows[0]["Lagerort"].find("button"))
        values = [dd.text() for dd in popup.find("dl").find_all("dd")]
        self.assertEqual(values, ["2", "7"])
        self.assertEqual(popup.text().count("nicht hinterlegt"), 1)

    def test_no_bulk_section_without_lots(self) -> None:
        self.item(None, "Neuverbindung 9", quantity=2)
        root = self.listing()
        _, rows = table(root)
        popup = popup_of(root, rows[0]["Lagerort"].find("button"))
        self.assertNotIn("Bulk", popup.text())
        self.assertIn("10 µmol · 2 Gebinde", popup.text())

    def test_statistics_popup(self) -> None:
        """Scenario: Statistics popup."""
        item = self.item("CH-0012", "(E)-Zimtsäure", quantity=6)
        self.enter_year(item, 2024, 4)
        for quarter, count in ((1, 6), (2, 5), (3, 7)):
            self.enter(item, 2026, quarter, count)
        self.deliver(item, 2, date(2026, 10, 15))
        root = self.listing()
        _, rows = table(root)
        cell = rows[0]["Abgegeben"]
        button = cell.find("button")
        self.assertEqual(button.text(), "20")
        self.assertEqual(outside_popups(cell), "20")
        popup = popup_of(root, button)
        self.assertEqual(popup.find("h2").text(),
                         "Abgegeben · (E)-Zimtsäure")
        header, years = table(popup)
        self.assertEqual(header, ["Jahr", "Q1", "Q2", "Q3", "Q4", "Summe"])
        self.assertEqual([[cell.text() for cell in year.values()]
                          for year in years],
                         [["2024", "4", "4", "4", "4", "16"],
                          ["2025", "0", "0", "0", "0", "0"],
                          ["2026", "6", "5", "7", "2", "20"]])
        bars = popup.find_all(cls="quarter-bar")
        self.assertEqual(len(bars), 4)
        self.assertEqual(["current" in bar.classes for bar in bars],
                         [False, False, False, True])
        self.assertIn("laufend", bars[3].text())
        entered = popup.find(cls="entered-years").text()
        self.assertIn("2024", entered)
        self.assertIn("2026", entered)
        self.assertNotIn("2025", entered)
        self.assertIn(item_url(item), [a.get("href")
                                        for a in popup.find_all("a")])

    def test_quarters_to_come_are_empty(self) -> None:
        item = self.item("Q-1")
        self.enter(item, 2026, 1, 3)
        with ticking(berlin(2026, 5, 4, 8)):
            root = self.listing()
        _, rows = table(root)
        popup = popup_of(root, rows[0]["Abgegeben"].find("button"))
        _, years = table(popup)
        self.assertEqual([cell.text() for cell in years[2].values()],
                         ["2026", "3", "0", "", "", "3"])
        bars = popup.find_all(cls="quarter-bar")
        self.assertEqual(["current" in bar.classes for bar in bars],
                         [False, True, False, False])
        self.assertIsNone(bars[2].find(cls="bar"))

    def test_the_means_in_the_statistics(self) -> None:
        item = self.means_item()
        root = self.listing()
        _, rows = table(root)
        popup = popup_of(root, rows[0]["Abgegeben"].find("button"))
        figures = {dt.text(): dt.parent.find("dd")
                   for dt in popup.find_all("dt")}
        self.assertEqual(figures["Ø Jahr"].text(), "18,0")
        self.assertEqual(figures["Ø Quartal"].text(), "4,5")
        self.assertEqual(figures["2026 bis 4. November"].text(), "13")
        self.assertNotIn("projected", figures["Ø Jahr"].classes)
        self.assertEqual(fresh(item).quantity, 3)

    def test_projected_means_are_marked(self) -> None:
        item = self.item("P-1", quantity=3)
        self.enter(item, 2026, 2, 6)
        root = self.listing()
        _, rows = table(root)
        popup = popup_of(root, rows[0]["Abgegeben"].find("button"))
        figures = {dt.text(): dt.parent.find("dd")
                   for dt in popup.find_all("dt")}
        for name in ("Ø Jahr", "Ø Quartal"):
            self.assertIn("projected", figures[name].classes)

    def test_every_popup_closes_itself(self) -> None:
        self.item("C-1")
        root = self.listing()
        popups = [e for e in root.walk() if "popover" in e.attrs]
        self.assertEqual(len(popups), 5)
        for popup in popups:
            if popup.closest("td") is None:
                continue
            with self.subTest(popup=popup.get("id")):
                close = popup.find("button", attrs={
                    "popovertarget": popup.get("id"),
                    "popovertargetaction": "hide"})
                self.assertIsNotNone(close)
                self.assertEqual(close.get("aria-label"), "Schließen")


class ViewControlTests(TableCase):

    def test_view_controls(self) -> None:
        """Scenario: View controls."""
        self.item("V-1")
        root = self.listing()
        columns = root.find(id="columns-menu")
        self.assertIn("popover", columns.attrs)
        self.assertIsNotNone(root.find("button", attrs={
            "popovertarget": "columns-menu"}))
        boxes = columns.find_all("input", type="checkbox")
        self.assertEqual([box.get("id") for box in boxes],
                         [f"column-{key}" for key in OPTIONAL])
        self.assertEqual({box.get("id")[7:] for box in boxes
                          if "checked" not in box.attrs}, HIDDEN)
        labels = {box.get("id")[7:]: box.parent.text() for box in boxes}
        self.assertEqual(labels["location"], "Lagerort")
        self.assertEqual(labels["note"], "Bemerkung")
        height = root.find("select", id="row-height")
        self.assertEqual([(o.get("value"), o.text(), "selected" in o.attrs)
                          for o in height.find_all("option")],
                         [("compact", "Kompakt", True),
                          ("tight", "Sehr kompakt", False)])
        heat = root.find("input", id="heat-switch")
        self.assertEqual(heat.get("type"), "checkbox")
        self.assertIn("checked", heat.attrs)
        self.assertIn("Verbrauch einfärben", heat.parent.text())
        for control in [*boxes, height, heat]:
            with self.subTest(control=control.get("id")):
                self.assertTrue(control.get("data-remember"))
                self.assertIsNone(control.closest("form"))
                self.assertIsNone(control.get("form"))
                self.assertIsNone(control.get("name"))
        remembered = [c.get("data-remember") for c in [*boxes, height, heat]]
        self.assertEqual(len(set(remembered)), len(remembered))

    def test_signed_in_extras_keep_their_places(self) -> None:
        self.client.force_login(self.kl)
        self.item("V-1")
        root = self.listing()
        header, rows = table(root)
        self.assertEqual(header, COLUMNS)
        box = rows[0]["Artikelnr."].find("input", type="checkbox")
        self.assertEqual(box.get("form"), "pick")


class HeatTests(TableCase):

    def test_fifths_of_the_consuming_items(self) -> None:
        """Scenario: Fifths of the consuming items."""
        for article, count in (("H-0", 0), ("H-1", 1), ("H-2", 2),
                               ("H-2b", 2), ("H-5", 5), ("H-9", 9)):
            item = self.item(article)
            if count:
                self.enter(item, 2026, 1, count)
        header, rows = table(self.listing())
        heats = {row[header[0]].text(): heat_of(row["Abgegeben"])
                 for row in rows}
        self.assertEqual(heats, {"H-0": None, "H-1": "heat-1",
                                 "H-2": "heat-2", "H-2b": "heat-2",
                                 "H-5": "heat-4", "H-9": "heat-5"})
        header, rows = table(self.listing("?q=h-9"))
        self.assertEqual(heat_of(rows[0]["Abgegeben"]), "heat-5")

    def test_the_mean_per_year_has_its_own_fifths(self) -> None:
        for article, mean in (("M-1", 1), ("M-2", 2), ("M-3", 3)):
            self.with_mean_quarter(self.item(article), mean)
        self.item("M-4")
        header, rows = table(self.listing())
        self.assertEqual([heat_of(row["Ø Jahr"]) for row in rows],
                         ["heat-1", "heat-2", "heat-4", None])
        self.assertEqual([heat_of(row["Abgegeben"]) for row in rows],
                         [None] * 4)

    def test_one_consuming_item(self) -> None:
        self.enter(self.item("O-1"), 2026, 1, 4)
        header, rows = table(self.listing())
        self.assertEqual(heat_of(rows[0]["Abgegeben"]), "heat-1")

    def test_the_switch_shows_the_scale(self) -> None:
        self.item("S-1")
        root = self.listing()
        scale = root.find(cls="heat-legend")
        self.assertIsNotNone(scale)
        self.assertEqual([heat_of(e) for e in scale.walk()
                          if heat_of(e)], HEATS)
        text = scale.text()
        self.assertLess(text.index("wenig"), text.index("viel"))
        self.assertIsNotNone(scale.find("input", id="heat-switch"))

    def test_the_english_scale(self) -> None:
        self.use_index(build_index("en"))
        self.item("S-1")
        scale = self.listing().find(cls="heat-legend")
        text = scale.text()
        self.assertIn("Colour consumption", text)
        self.assertLess(text.index("little"), text.index("much"))


class StickyTests(TableCase):

    def test_a_table_that_keeps_its_headers(self) -> None:
        """Scenario: A table that keeps its headers."""
        self.item("T-1")
        root = self.listing()
        box = root.find("table").parent
        self.assertEqual(box.tag, "div")
        self.assertLessEqual({"table-scroll", "table-sticky"}, box.classes)
        self.assertEqual(len(root.find("thead").find_all("tr")), 1)
        header, _ = table(root)
        self.assertNotIn("Ø Quartal", header)


def screen_blocks(text: str) -> list[tuple[int, int]]:
    """The spans of the bodies of the ``@media screen`` blocks of TEXT."""
    spans = []
    for found in re.finditer(r"@media\s+screen\s*\{", text):
        body, end = balanced(text, found.start())
        spans.append((end - len(body) - 1, end))
    return spans


def rules(text: str) -> list[tuple[str, str]]:
    """Each style rule of TEXT, inside at-rules or not, as its selector
    and its body, comments left out."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    found = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        selector = match.group(1).strip()
        if not selector.startswith("@"):
            found.append((" ".join(selector.split()), match.group(2)))
    return found


class StylesheetTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.text = Path(CSS).read_text(encoding="utf-8")

    def test_the_sticky_rules_are_for_the_screen(self) -> None:
        """Scenario: A table that keeps its headers (the stylesheet)."""
        spans = screen_blocks(self.text)
        places = [found.start() for found in
                  re.finditer(r"table-sticky", self.text)]
        self.assertTrue(places)
        for place in places:
            with self.subTest(at=place):
                self.assertTrue(any(start <= place < end
                                    for start, end in spans))
        screen = "".join(self.text[start:end] for start, end in spans)
        self.assertIn("position: sticky", screen)

    def test_paper_leaves_the_controls_out(self) -> None:
        printed = ""
        for found in re.finditer(r"@media\s+print\s*\{", self.text):
            printed += balanced(self.text, found.start())[0]
        hidden = " ".join(selector for selector, body in rules(printed)
                          if re.search(r"display:\s*none", body))
        for part in (".lab-toolbar", ".lab-view-controls",
                     ".lab-table-note"):
            self.assertIn(part, hidden)

    def test_paper_keeps_the_delivered_numbers(self) -> None:
        """print.css hides every button; the numbers of Abgegeben sit in
        buttons and must print."""
        printed = ""
        for found in re.finditer(r"@media\s+print\s*\{", self.text):
            printed += balanced(self.text, found.start())[0]
        self.assertTrue(any(
            ".stat-button" in selector
            and re.search(r"display:\s*inline", body)
            for selector, body in rules(printed)))

    def test_unchecked_columns_are_hidden(self) -> None:
        """Scenario: View controls (the stylesheet)."""
        found = rules(self.text)
        for key in OPTIONAL:
            with self.subTest(column=key):
                self.assertTrue(any(
                    f"#column-{key}:not(:checked)" in selector
                    and f".col-{key}" in selector
                    and re.search(r"display:\s*none", body)
                    for selector, body in found), key)

    def test_the_switch_drops_the_heat(self) -> None:
        found = rules(self.text)
        dropped = [body for selector, body in found
                   if "#heat-switch:not(:checked)" in selector]
        self.assertTrue(dropped)
        self.assertTrue(any(re.search(r"background(-color)?:\s*"
                                      r"(none|transparent)", body)
                            for body in dropped))

    def test_the_tight_rows(self) -> None:
        self.assertTrue(any('#row-height option[value="tight"]:checked'
                            in selector for selector, _ in
                            rules(self.text)))

    def heat_tokens(self, text: str) -> dict[str, str]:
        tokens = {}
        for found in re.finditer(r":root\s*\{", text):
            body, _ = balanced(text, found.start())
            tokens.update(re.findall(
                r"(--heat-[1-5]-(?:bg|fg))\s*:\s*(#[0-9a-fA-F]{6})\s*;",
                body))
        return tokens

    def test_readable_in_both_schemes(self) -> None:
        """Scenario: Readable in both schemes."""
        light, dark = split_schemes(self.text)
        names = {f"--heat-{n}-{part}" for n in range(1, 6)
                 for part in ("bg", "fg")}
        for scheme, tokens in (("light", self.heat_tokens(light)),
                               ("dark", self.heat_tokens(dark))):
            self.assertEqual(set(tokens), names, scheme)
            for n in range(1, 6):
                with self.subTest(scheme=scheme, heat=n):
                    self.assertGreaterEqual(contrast(
                        tokens[f"--heat-{n}-bg"],
                        tokens[f"--heat-{n}-fg"]), MINIMUM)
        for n in range(1, 6):
            with self.subTest(rule=n):
                body = re.search(rf"\.heat-{n}\s*\{{([^}}]*)\}}",
                                 self.text).group(1)
                self.assertIn(f"var(--heat-{n}-bg)", body)
                self.assertIn(f"var(--heat-{n}-fg)", body)

    def test_the_heats_darken_in_the_light_scheme(self) -> None:
        from .test_inventory_colours import luminance
        light, _ = split_schemes(self.text)
        tokens = self.heat_tokens(light)
        shades = [luminance(tokens[f"--heat-{n}-bg"]) for n in range(1, 6)]
        self.assertEqual(shades, sorted(shades, reverse=True))
