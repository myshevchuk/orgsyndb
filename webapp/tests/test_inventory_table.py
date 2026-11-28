"""Tests of the item list's table: its columns and order, the filters
above it, the stock menu, the view controls, the two views and the
cookie that remembers the view, the consumption heat, the box that
keeps the headers in view and the stylesheet's rules for the views
(end-product-inventory: Item list, Consumption heat)."""

import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from django.test import SimpleTestCase

from inventory.models import Item

from . import field_value, make_substance, page, table
from .collection_support import accept
from .inventory_support import LIST, InventoryCase, fresh
from .main_lists_support import must_outer_split, outer_split
from .test_inventory_colours import (CSS, MINIMUM, balanced, contrast,
                                     split_schemes)

SORTS = ("number", "name", "category", "container", "stock", "mean_year",
         "this_year", "coverage", "compartment", "box", "bulk")
COLUMNS = ["Artikelnr.", "Name", "Kategorie", "Gebinde", "Bestand",
           "Ø Jahr", "Abgegeben", "Reichweite", "Fach", "Box",
           "Bulk"]
KEYS = ["number", "name", "category", "container", "stock", "mean_year",
        "this_year", "coverage", "compartment", "box", "bulk"]
SORTED_COLUMNS = dict(zip(KEYS, COLUMNS))
COOKIE = "item-list-view"
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


def body_rows(root) -> list:
    """The rows of the body of the page's first table, without those of
    the tables inside its cells."""
    grid = root.find("table")
    return [tr for tr in grid.find("tbody").find_all("tr")
            if tr.closest("table") is grid]


class TableCase(InventoryCase):

    def remember(self, view: str | None) -> None:
        """Set the cookie that remembers the view to VIEW, or leave it
        out when VIEW is None."""
        if view is None:
            self.client.cookies.pop(COOKIE, None)
        else:
            self.client.cookies[COOKIE] = view

    def listing(self, query: str = "", view: str | None = None):
        """The list's page, after setting the cookie that remembers the
        view to VIEW unless that is None."""
        if view is not None:
            self.remember(view)
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
        accept(language="en")
        self.item("T-1")
        root = self.listing()
        header, _ = table(root)
        self.assertEqual(header, [
            "Article no.", "Name", "Category", "Container", "Stock",
            "Mean per year", "Delivered", "Coverage", "Compartment", "Box",
            "Bulk"])
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

    def test_both_views_show_every_column_in_order(self) -> None:
        """Requirement: Item list (both views show every column)."""
        self.means_item("T-1", note="Notiz")
        for view in (None, "table", "details"):
            with self.subTest(view=view):
                root = self.listing(view=view)
                header, rows = table(root)
                self.assertEqual(header, COLUMNS)
                self.assertNotIn("Bemerkung", header)
                cells = [c for c in root.find("tbody").find("tr").children
                         if not isinstance(c, str) and c.tag == "td"]
                self.assertEqual([[n[4:] for n in c.classes
                                   if n.startswith("col-")
                                   and n != "col-strong"][0]
                                  for c in cells], KEYS)

    def test_no_cell_or_header_is_the_table_views_own(self) -> None:
        self.item("T-1")
        self.item(None, "Ohne Nummer")
        for view in (None, "table", "details"):
            root = self.listing(view=view)
            grid = root.find("table")
            for tr in [tr for tr in grid.find_all("tr")
                       if tr.closest("table") is grid]:
                for cell in tr.children:
                    if isinstance(cell, str) or cell.tag not in ("th", "td"):
                        continue
                    with self.subTest(view=view, row=tr.text()[:30]):
                        self.assertNotIn("table-only", cell.classes)
            self.assertEqual([e.tag for e in root.walk()
                              if "table-only" in e.classes], [])

    def test_no_note_cell_holds_an_items_note(self) -> None:
        self.means_item("T-1", note="Notiz im Bestand")
        root = self.listing()
        self.assertNotIn("Notiz im Bestand", root.find("tbody").text())
        self.assertEqual([e.tag for e in root.walk()
                          if "col-note" in e.classes], [])

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
        self.assertEqual(self.articles(), ["A-2", "A-3", "A-1", "A-4"])

    def test_the_category_order_marks_its_starts(self) -> None:
        self.item("A-2", category="Ester")
        self.item("A-1", category="Säuren")
        self.item("A-3", category="Ester")
        self.item("A-4")
        root = self.listing()
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
        self.item("A-1", category="Säuren")
        self.item("A-2")
        first = self.item("A-3", category="Ester")
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
        selected = [str(first.pk)]
        self.assertEqual(self.header_link(root, "Kategorie"),
                         {"sort": ["category"], "dir": ["desc"],
                          "selected": selected})
        self.assertEqual(self.header_link(root, "Artikelnr."),
                         {"sort": ["number"], "selected": selected})
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
                 "Bulk, Artikelnr., Gebinde aufsteigend")):
            with self.subTest(query=query):
                self.assertEqual(self.summary(self.listing(query)),
                                 f"1 von 1 Artikel · {order}")

    def test_the_english_order_line(self) -> None:
        accept(language="en")
        self.item("S-1")
        self.item("S-2")
        self.assertEqual(self.summary(self.listing()),
                         "2 of 2 items · Category, Article no., Container "
                         "ascending")

    def test_containers_and_locations_in_their_order(self) -> None:
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
        self.item("T-1", name="beta", category="Zwei")
        self.item("T-2", name="Alpha", category="eins")
        self.item("T-3", name="Gamma")
        self.assertEqual(self.articles("?sort=name"), ["T-2", "T-1", "T-3"])
        self.assertEqual(self.articles("?sort=category"),
                         ["T-2", "T-1", "T-3"])
        self.assertEqual(self.articles("?sort=category&dir=desc"),
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

    def test_bulk_by_its_amount(self) -> None:
        """Masses by mg, then amounts of substance by µmol, items
        without bulk last, whatever the number of containers the bulk
        fills: here the order by amount is the reverse of the order by
        fill count."""
        self.item("CH-0001", size="10", unit="mg")
        self.item("CH-0002", size="1", unit="mg")
        self.item("CH-0003", size="10", unit="umol")
        self.item("CH-0004", size="10", unit="mg")
        self.item("CH-0005", size="10", unit="mg")
        self.vessel("CH-0001", "mg", "50")
        self.vessel("CH-0002", "mg", "20")
        self.vessel("CH-0003", "umol", "5")
        self.vessel("CH-0004", "g", "1")
        self.vessel("CH-0004", "umol", "3")
        self.assertEqual(self.articles("?sort=bulk"),
                         ["CH-0002", "CH-0001", "CH-0004", "CH-0003",
                          "CH-0005"])
        self.assertEqual(self.articles("?sort=bulk&dir=desc"),
                         ["CH-0003", "CH-0004", "CH-0001", "CH-0002",
                          "CH-0005"])

    def test_ties_keep_the_default_order(self) -> None:
        for article in ("E-2", "E-3", "E-1"):
            self.item(article, category="Gleich")
        for query in ("?sort=category", "?sort=category&dir=desc"):
            with self.subTest(query=query):
                self.assertEqual(self.articles(query), ["E-1", "E-2", "E-3"])

    def test_the_header_links_keep_the_filters(self) -> None:
        """The list the filters leave empty names no selection."""
        self.item("K-1", category="Grün")
        root = self.listing(f"?category={quote('Grün')}&q=k&stock=watch"
                            "&sort=name&dir=desc")
        self.assertEqual(self.articles(f"?category={quote('Grün')}"
                                       "&stock=watch"), [])
        self.assertEqual(self.header_link(root, "Name"), {
            "category": ["Grün"], "q": ["k"], "stock": ["watch"],
            "sort": ["name"]})
        self.assertEqual(self.header_link(root, "Bulk"), {
            "category": ["Grün"], "q": ["k"], "stock": ["watch"],
            "sort": ["bulk"]})

    def test_the_header_links_keep_the_filters_and_the_selection(
            self) -> None:
        self.item("K-1", category="Grün")
        second = self.item("K-2", category="Grün")
        root = self.listing(f"?category={quote('Grün')}&q=k"
                            f"&sort=name&dir=desc&selected={second.pk}")
        for column in ("Name", "Bulk"):
            with self.subTest(column=column):
                link = self.header_link(root, column)
                self.assertEqual(link.get("selected"), [str(second.pk)])
                self.assertEqual(link.get("q"), ["k"])


class FilterTests(TableCase):

    def test_filters(self) -> None:
        """Scenario: Filters."""
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

    def test_the_filters_keep_the_order_and_reset_to_it(self) -> None:
        self.item("CH-0012", "(E)-Zimtsäure", "100", "mg")
        first = self.item("CH-0016", "Isopentylacetat", "100", "mg")
        self.item("CH-0010", "Aspirin", "1", "g")
        root = self.listing(f"?container={quote('100 mg')}"
                            "&sort=name&dir=desc")
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["CH-0016", "CH-0012"])
        selected = [str(first.pk)]
        self.assertEqual(self.header_link(root, "Name"),
                         {"container": ["100 mg"], "sort": ["name"],
                          "selected": selected})
        self.assertEqual(query_of(self.reset_link(root).get("href")),
                         {"sort": ["name"], "dir": ["desc"],
                          "selected": selected})
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
        self.assertNotIn("data-submit", category.attrs)
        triggers = [part.strip() for part in
                    (form.get("hx-trigger") or "").split(",")]
        self.assertIn("change target:select", triggers)
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
        form = root.find("form", id="filters")
        triggers = [part.strip() for part in
                    (form.get("hx-trigger") or "").split(",")]
        button = root.find("button", attrs={"popovertarget": "more-filters"})
        self.assertEqual(button.text(), "Weitere Filter")
        popup = root.find(id="more-filters")
        self.assertIn("popover", popup.attrs)
        for name, label in (("container", "Gebinde"),
                            ("compartment", "Fach"), ("box", "Box")):
            with self.subTest(name=name):
                control = popup.find("select", name=name)
                self.assertEqual(control.get("form"), "filters")
                self.assertEqual(control.get("id"), f"filter-{name}")
                self.assertNotIn("data-submit", control.attrs)
                self.assertIn(f"change from:#filter-{name}", triggers)
                self.assertIn(label, control.parent.text())
        self.assertEqual([(o.get("value"), o.text()) for o in popup.find(
            "select", name="compartment").find_all("option")],
            [("", "Alle"), ("2", "2"), ("10", "10")])

    def test_locations(self) -> None:
        """Scenario: Locations."""
        kept(self.item("L-1"), "2", "7")
        kept(self.item("L-2"), "10", "7")
        header, rows = table(self.listing())
        self.assertEqual([(row["Fach"].text(), row["Box"].text())
                          for row in rows], [("2", "7"), ("10", "7")])
        for query, wanted in (("?compartment=2", ["L-1"]),
                              ("?box=7", ["L-1", "L-2"])):
            with self.subTest(query=query):
                root = self.listing(query)
                header, rows = table(root)
                self.assertEqual([row[header[0]].text() for row in rows],
                                 wanted)
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

    def test_the_default_order_is_not_kept(self) -> None:
        """Main lists: the filter form keeps the order only while it is
        not the default; the item list's default is the category."""
        item = self.item("O-1")
        for query in ("", "?sort=category", "?sort=nothing"):
            with self.subTest(query=query):
                form = self.listing(query).find("form", id="filters")
                self.assertEqual(
                    {i.get("name"): i.get("value") for i in
                     form.find_all("input", type="hidden")},
                    {"selected": str(item.pk)})

    def test_an_order_that_is_not_the_default_is_kept(self) -> None:
        item = self.item("O-1")
        for query, kept in (
                ("?sort=name", {"sort": "name"}),
                ("?sort=category&dir=desc",
                 {"sort": "category", "dir": "desc"}),
                ("?sort=name&dir=desc", {"sort": "name", "dir": "desc"})):
            with self.subTest(query=query):
                form = self.listing(query).find("form", id="filters")
                self.assertEqual(
                    {i.get("name"): i.get("value") for i in
                     form.find_all("input", type="hidden")},
                    {**kept, "selected": str(item.pk)})

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

    def counts(self, popup) -> dict[str, tuple[str, str]]:
        """The count and the link of each level the menu offers."""
        found = {}
        for link in popup.find_all("a"):
            for level in LEVEL_VALUES:
                if link.find(cls=f"level-{level}") is not None:
                    found[level] = (link.find("span", "count").text(),
                                    link.get("href"))
        return found

    def test_levels_with_their_counts(self) -> None:
        """Scenario: Levels with their counts."""
        self.with_mean_quarter(self.item("O-1", quantity=20,
                                         category="A"), 1)
        self.with_mean_quarter(self.item("O-2", quantity=20,
                                         category="A"), 1)
        self.with_mean_quarter(self.item("L-1", quantity=3,
                                         category="A"), 4)
        dormant = self.with_mean_quarter(self.item("D-1", category="B"), 1)
        Item.objects.filter(pk=dormant.pk).update(status="discontinued")
        _, popup = self.menu(self.listing("?category=A"))
        found = self.counts(popup)
        self.assertEqual(sorted(found), sorted(LEVEL_VALUES))
        self.assertEqual({level: count for level, (count, _)
                          in found.items()},
                         {"out": "0", "critical": "0", "low": "1",
                          "watch": "0", "ok": "2", "undelivered": "0",
                          "dormant": "0"})
        link = query_of(found["low"][1])
        self.assertEqual((link["category"], link["stock"]),
                         (["A"], ["low"]))

    def test_the_menu_counts_all_items_the_filters_admit(self) -> None:
        self.with_mean_quarter(self.item("O-1", quantity=20,
                                         category="A"), 1)
        self.with_mean_quarter(self.item("L-1", quantity=3,
                                         category="A"), 4)
        self.item("D-1", category="B")
        root = self.listing("?category=A")
        button, popup = self.menu(root)
        self.assertEqual(button.text(), "Alle (2)")
        entries = self.entries(popup)
        self.assertEqual(entries[0][1], "2")
        self.assertEqual(query_of(entries[0][2])["category"], ["A"])
        self.assertNotIn("stock", query_of(entries[0][2]))

    def test_one_level_exactly(self) -> None:
        """Scenario: One level exactly."""
        for article, quantity in (("A-1", 0), ("A-2", 1), ("A-3", 3)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        self.assertEqual(self.articles("?stock=critical"), ["A-2"])

    def test_the_menu_marks_the_level_in_force(self) -> None:
        for article, quantity in (("A-1", 0), ("A-2", 1), ("A-3", 3)):
            self.with_mean_quarter(self.item(article, quantity=quantity), 4)
        button, popup = self.menu(self.listing("?stock=critical"))
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
        self.assertIn("Details", note)
        self.assertIsNone(re.search(r"\bOrt\b", note), note)
        for name in ("Fach", "Box", "Bulk"):
            self.assertNotIn(name, note)


class PopupTests(TableCase):

    def test_no_popup_inside_the_table(self) -> None:
        """The location and the statistics are in the details, not in
        popups."""
        self.item("C-1", quantity=3)
        self.enter(self.item("C-2"), 2026, 1, 3)
        self.vessel("C-1", "mg", "50", location="Kühlschrank 2")
        root = self.listing()
        grid = root.find("table")
        self.assertEqual([e.tag for e in grid.walk()
                          if "popover" in e.attrs
                          or "popovertarget" in e.attrs], [])
        self.assertEqual([e.tag for e in grid.find_all("button")], [])
        _, rows = table(root)
        self.assertEqual([row["Abgegeben"].text() for row in rows],
                         ["0", "3"])

    def test_the_menus_stay_popups(self) -> None:
        self.item("C-1")
        root = self.listing()
        self.assertEqual(sorted(e.get("id") for e in root.walk()
                                if "popover" in e.attrs),
                         ["more-filters", "stock-menu"])


class ViewControlTests(TableCase):

    def test_the_removed_controls_are_gone(self) -> None:
        """Requirement: Item list (no menu hides a column or sets the
        row height or the heat)."""
        self.item("V-1")
        for view in (None, "table", "details"):
            with self.subTest(view=view):
                root = self.listing(view=view)
                self.assertIsNone(root.find(id="columns-menu"))
                self.assertIsNone(root.find("button", attrs={
                    "popovertarget": "columns-menu"}))
                self.assertEqual([e.get("id") for e in root.walk()
                                  if e.get("id", "").startswith("column-")],
                                 [])
                self.assertNotIn("Spalten", [b.text() for b in
                                             root.find_all("button")])
                self.assertIsNone(root.find(cls="lab-columns"))
                self.assertIsNone(root.find("details", cls="lab-view-menu"))
                self.assertIsNone(root.find(cls="lab-view-controls"))
                self.assertIsNone(root.find(id="row-height"))
                self.assertIsNone(root.find(id="heat-switch"))
                self.assertIsNone(root.find(cls="heat-legend"))
                self.assertEqual([e.tag for e in root.walk()
                                  if "data-remember" in e.attrs], [])

    def test_the_old_switch_is_gone(self) -> None:
        item = self.item("V-1")
        for query in ("", f"?detail={item.pk}", f"?selected={item.pk}"):
            with self.subTest(query=query):
                root = self.listing(query)
                self.assertIsNone(root.find(id="detail-switch"))
                self.assertEqual(
                    [e.get("data-remember") for e in root.walk()
                     if e.get("data-remember") == "item-list:detail"], [])

    def test_signed_in_extras_keep_their_places(self) -> None:
        self.client.force_login(self.kl)
        self.item("V-1")
        root = self.listing()
        header, rows = table(root)
        self.assertEqual(header, COLUMNS)
        box = rows[0]["Artikelnr."].find("input", type="checkbox")
        self.assertEqual(box.get("form"), "pick")


class ViewTests(TableCase):
    """The two views, the switch between them and the cookie that
    remembers the view."""

    def radios(self, root) -> dict[str, Any]:
        found = root.find_all("input", type="radio", name="view")
        self.assertEqual(
            sorted(r.get("id") for r in found),
            ["view-details", "view-details-wide", "view-table"])
        return {r.get("id"): r for r in found}

    def label_of(self, root, control) -> str:
        wrapping = control.closest("label")
        if wrapping is not None:
            return wrapping.text()
        named = [e for e in root.find_all("label")
                 if e.get("for") == control.get("id")]
        self.assertEqual(len(named), 1)
        return named[0].text()

    def test_the_switch_is_a_fieldset_of_three_radios(self) -> None:
        """Layout picker: the table, and the details with either side
        larger, each an icon with a hidden label."""
        self.item("V-1")
        root = self.listing()
        radios = self.radios(root)
        fieldset = radios["view-table"].closest("fieldset")
        self.assertIsNotNone(fieldset)
        self.assertIn("view-switch", fieldset.classes)
        self.assertIn("layout-picker", fieldset.classes)
        self.assertEqual(fieldset.find_all("input"), list(radios.values()))
        self.assertEqual(fieldset.find("legend").text(), "Ansicht")
        wanted = {
            "view-table": ("table", None, "Tabelle"),
            "view-details": ("details", "first", "Details, Tabelle größer"),
            "view-details-wide": ("details", "second",
                                  "Details, Details größer"),
        }
        for key, (value, major, label) in wanted.items():
            with self.subTest(radio=key):
                radio = radios[key]
                self.assertIs(radio.closest("fieldset"), fieldset)
                self.assertEqual(radio.get("value"), value)
                self.assertEqual(radio.get("data-major"), major)
                self.assertEqual(self.label_of(root, radio), label)
                icons = [svg for svg in radio.closest("label").find_all(
                    "svg") if "layout-icon" in svg.classes]
                self.assertEqual(len(icons), 1)
                hidden = radio.closest("label").find(
                    "span", cls="visually-hidden")
                self.assertIsNotNone(hidden)
                self.assertEqual(hidden.text(), label)
        self.assertIsNotNone(fieldset.closest("main"))
        self.assertIsNotNone(outer_split(root))

    def test_the_larger_area_toggle_is_gone(self) -> None:
        self.item("V-1")
        root = self.listing()
        self.assertEqual(root.find_all("button", cls="pane-toggle"), [])
        self.assertNotIn("Größere Fläche", root.text())
        self.assertNotIn("split#toggle", " ".join(
            e.get("data-lab-action") or "" for e in root.walk()))

    def test_the_switch_belongs_to_no_form(self) -> None:
        self.item("V-1")
        for radio in self.radios(self.listing()).values():
            with self.subTest(radio=radio.get("id")):
                self.assertIsNone(radio.closest("form"))
                self.assertIsNone(radio.get("form"))
                self.assertIsNone(radio.get("data-remember"))

    def test_the_view_comes_from_the_cookie(self) -> None:
        """Scenario: The view from the cookie."""
        self.item("V-1")
        for cookie, view in ((None, "table"), ("details", "details"),
                             ("table", "table"), ("other", "table"),
                             ("", "table")):
            with self.subTest(cookie=cookie):
                self.remember(cookie)
                root = self.listing()
                radios = self.radios(root)
                self.assertEqual(
                    [radio.get("value") for radio in radios.values()
                     if "checked" in radio.attrs], [view])
                self.assertEqual(
                    must_outer_split(root).get("data-view"), view)

    def test_the_details_radio_checked_follows_the_split_cookie(
            self) -> None:
        """The two details buttons stand for the two sides: the one
        for the larger side, as the split cookie has it, is checked."""
        self.item("V-1")
        self.remember("details")
        for cookie, want in ((None, "view-details"),
                             ("first", "view-details"),
                             ("second", "view-details-wide"),
                             ("other", "view-details")):
            with self.subTest(split=cookie):
                if cookie is None:
                    self.client.cookies.pop("item-list-split", None)
                else:
                    self.client.cookies["item-list-split"] = cookie
                root = self.listing()
                self.assertEqual(
                    [name for name, radio in self.radios(root).items()
                     if "checked" in radio.attrs], [want])
                if cookie == "second":
                    self.assertEqual(
                        must_outer_split(root).get("data-major"),
                        "second")
        self.client.cookies.pop("item-list-split", None)
        self.remember("table")
        self.client.cookies["item-list-split"] = "second"
        root = self.listing()
        self.assertEqual(
            [name for name, radio in self.radios(root).items()
             if "checked" in radio.attrs], ["view-table"])

    def test_the_cookie_does_not_change_the_rows(self) -> None:
        self.item("V-1")
        self.item("V-2")
        wanted = self.articles()
        for cookie in ("details", "table", "other"):
            with self.subTest(cookie=cookie):
                self.listing(view=cookie)
                self.assertEqual(self.articles(), wanted)

    def test_no_link_or_form_names_a_view(self) -> None:
        """Scenario: The view from the cookie (the links)."""
        self.client.force_login(self.kl)
        self.item("V-1", category="Ester")
        self.item("V-2", category="Säuren")
        for cookie in (None, "details", "table", "other"):
            with self.subTest(cookie=cookie):
                self.remember(cookie)
                root = self.listing("?category=Ester&stock=ok&sort=name")
                for link in root.find_all("a"):
                    href = link.get("href", "")
                    self.assertNotIn("view", parse_qs(urlsplit(href).query),
                                     href)
                for form in root.find_all("form"):
                    self.assertNotIn("view", parse_qs(
                        urlsplit(form.get("action", "")).query))
                    self.assertEqual(form.find_all(
                        ("input", "select", "textarea", "button"),
                        name="view"), [])
                self.assertEqual(
                    [c.get("id") for c in root.find_all(
                        ("input", "select", "textarea", "button"),
                        name="view")
                     if c.closest("form") is not None
                     or c.get("form") is not None], [])

    def test_a_view_in_the_address_is_not_read(self) -> None:
        self.item("V-1")
        for query in ("?view=details", "?view=table"):
            with self.subTest(query=query):
                self.remember(None)
                root = self.listing(query)
                self.assertEqual(
                    must_outer_split(root).get("data-view"), "table")
                for radio in self.radios(root).values():
                    self.assertEqual("checked" in radio.attrs,
                                     radio.get("value") == "table")
                root = self.listing(query, view="details")
                self.assertEqual(
                    must_outer_split(root).get("data-view"), "details")


class GeneratedRuleTests(TableCase):
    """The page's head holds no rule that hides a column."""

    def test_the_head_holds_no_rule_per_column(self) -> None:
        self.item("G-1")
        for view in (None, "details", "table"):
            with self.subTest(view=view):
                root = self.listing(view=view)
                self.assertEqual(
                    [e.text() for e in root.find("head").find_all("style")
                     if "#column-" in e.text() or ".col-" in e.text()],
                    [])


class SelectionKeptTests(TableCase):
    """The links and the field of the page that name the selected row
    (Item list: Scenario "The selection kept")."""

    def setUp(self) -> None:
        super().setUp()
        self.second = self.item("A-2", category="Ester")
        self.third = self.item("A-3", category="Ester")
        self.other = self.item("A-1", category="Säuren")

    def carriers(self, root) -> dict[str, list[str | None]]:
        """The ``selected`` that the form's field, the stock levels'
        links, the headers' links and the reset link name, each as the
        list of values, with None for a link that names none."""
        form = root.find("form", id="filters")
        found: dict[str, list[str | None]] = {
            "field": [i.get("value") for i in
                      form.find_all("input", name="selected")]}

        def selected(links) -> list[str | None]:
            return [(query_of(a.get("href")).get("selected") or [None])[0]
                    for a in links]

        found["stock levels"] = selected(
            root.find(id="stock-menu").find_all("a"))
        found["headers"] = selected(root.find("thead").find_all("a"))
        found["reset"] = selected(
            [a for a in root.find_all("a") if a.text() == "Zurücksetzen"])
        return found

    def assert_names(self, root, item) -> None:
        for name, values in self.carriers(root).items():
            with self.subTest(carrier=name):
                self.assertTrue(values, f"the page has no {name}")
                self.assertEqual(set(values), {str(item.pk)})

    def test_the_selection_kept(self) -> None:
        """Scenario: The selection kept."""
        for view in (None, "details"):
            self.remember(view)
            for query, wanted in (
                    (f"?category=Ester&selected={self.third.pk}",
                     self.third),
                    ("?category=Ester", self.second),
                    (f"?category=Ester&selected={self.other.pk}",
                     self.second)):
                with self.subTest(query=query, view=view):
                    self.assert_names(self.listing(query), wanted)

    def test_an_empty_list_names_no_selection(self) -> None:
        for view in (None, "details"):
            self.remember(view)
            for query in ("?category=Basen",
                          f"?category=Basen&selected={self.third.pk}"):
                with self.subTest(query=query, view=view):
                    root = self.listing(query)
                    carried = self.carriers(root)
                    self.assertEqual(carried["field"], [])
                    self.assertTrue(carried["stock levels"])
                    self.assertTrue(carried["headers"])
                    self.assertEqual(len(carried["reset"]), 1)
                    for name, values in carried.items():
                        self.assertEqual([v for v in values
                                          if v is not None], [], name)

    def test_the_first_row_stands_in_without_a_selection(self) -> None:
        root = self.listing()
        first = root.find("tbody").find("tr").get("data-item")
        for name, values in self.carriers(root).items():
            if name != "reset":
                with self.subTest(carrier=name):
                    self.assertEqual(set(values), {first})

    def test_the_first_row_of_the_order_in_force_stands_in(self) -> None:
        root = self.listing("?sort=number&dir=desc")
        self.assertEqual(root.find("tbody").find("tr").get("data-item"),
                         str(self.third.pk))
        for name, values in self.carriers(root).items():
            if name != "reset":
                with self.subTest(carrier=name):
                    self.assertEqual(set(values), {str(self.third.pk)})

    def test_the_links_keep_their_filters(self) -> None:
        root = self.listing(f"?category=Ester&sort=name"
                            f"&selected={self.third.pk}")
        stock = [query_of(a.get("href")) for a in
                 root.find(id="stock-menu").find_all("a")]
        self.assertTrue(stock)
        for query in stock:
            self.assertEqual(query.get("category"), ["Ester"])
            self.assertEqual(query.get("selected"), [str(self.third.pk)])
        reset = [a for a in root.find_all("a")
                 if a.text() == "Zurücksetzen"][0]
        self.assertEqual(query_of(reset.get("href")), {
            "sort": ["name"], "selected": [str(self.third.pk)]})

    def test_the_field_is_hidden_and_belongs_to_the_filter_form(
            self) -> None:
        root = self.listing(f"?selected={self.third.pk}")
        found = root.find("form", id="filters").find_all("input",
                                                         name="selected")
        self.assertEqual([f.get("type") for f in found], ["hidden"])
        self.assertEqual(len(root.find_all("input", name="selected")), 1)


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

    def test_the_hint_line_shows_the_scale(self) -> None:
        self.item("S-1")
        for view in (None, "details"):
            with self.subTest(view=view):
                root = self.listing(view=view)
                notes = root.find_all(cls="lab-table-note")
                self.assertEqual(len(notes), 1)
                note = notes[0]
                swatches = [e for e in note.walk() if heat_of(e)]
                self.assertEqual([heat_of(e) for e in swatches], HEATS)
                text = note.text()
                self.assertLess(text.index("wenig"), text.index("viel"))
                self.assertLess(text.index("Bestand"), text.index("wenig"))
                self.assertEqual(
                    [e for e in root.walk() if heat_of(e)
                     and e.closest("table") is None
                     and e not in swatches], [])

    def test_the_english_scale(self) -> None:
        accept(language="en")
        self.item("S-1")
        note = self.listing().find(cls="lab-table-note")
        self.assertEqual([heat_of(e) for e in note.walk() if heat_of(e)],
                         HEATS)
        text = note.text()
        self.assertLess(text.index("little"), text.index("much"))
        self.assertNotIn("Colour consumption", text)

    def test_the_heat_is_always_on_its_cells(self) -> None:
        item = self.item("H-1")
        self.enter(item, 2026, 1, 3)
        self.with_mean_quarter(self.item("H-2"), 2)
        header, rows = table(self.listing())
        for column in ("Ø Jahr", "Abgegeben"):
            with self.subTest(column=column):
                self.assertTrue(
                    any(heat_of(row[column]) for row in rows))


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


def blanked(text: str) -> str:
    """TEXT with its comments replaced by spaces, so that places in it
    stay places in TEXT."""
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group()), text,
                  flags=re.DOTALL)


def located(text: str) -> list[tuple[int, str, str]]:
    """Each style rule of TEXT as its place, its selector and its body,
    the place being an index into TEXT."""
    return [(m.start(), " ".join(m.group(1).split()), m.group(2))
            for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", blanked(text))
            if not m.group(1).strip().startswith("@")]


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
        for part in (".lab-toolbar", ".lab-table-note"):
            self.assertIn(part, hidden)

    def test_no_rule_serves_a_removed_control_or_mark(self) -> None:
        names = ("#row-height", "#heat-switch", ".lab-view-menu",
                 ".lab-view-controls", ".heat-legend", ".table-only",
                 ".lab-columns", "#columns-menu", ".projected",
                 ".col-note", ".col-fill")
        for _, selector, _ in located(self.text):
            for name in names:
                with self.subTest(selector=selector, name=name):
                    self.assertIsNone(re.search(
                        re.escape(name) + r"(?![\w-])", selector))
            with self.subTest(selector=selector):
                self.assertNotIn(".category-table td:first-child",
                                 selector)

    def test_one_rule_makes_the_strong_columns_bold(self) -> None:
        bold = [body for _, selector, body in located(self.text)
                for part in selector.split(",")
                if " ".join(part.split()) == ".main-table td.col-strong"
                and re.search(r"font-weight:\s*(600|700|bold)\b", body)]
        self.assertEqual(len(bold), 1, bold)

    def test_the_name_caps_are_for_the_screen_alone(self) -> None:
        spans = screen_blocks(blanked(self.text))
        capped = [(start, selector)
                  for start, selector, body in located(self.text)
                  if re.search(r"text-overflow:\s*ellipsis", body)
                  and re.search(r"(?<![-\w])max-width:", body)
                  and re.search(r"overflow:\s*hidden", body)
                  and re.search(r"\.main-table|td|col-", selector)
                  and "note-lines" not in selector]
        self.assertTrue(capped, "no rule caps the width of a name")
        for place, selector in capped:
            with self.subTest(selector=selector):
                self.assertTrue(any(a <= place < b for a, b in spans))

    def test_no_rule_names_the_old_pane_layout(self) -> None:
        names = (".item-layout", ".split-detail-", ".split-vessel-",
                 ".split-movements-", ".detail-figures",
                 ".detail-location", ".detail-lots")
        for _, selector, _ in located(self.text):
            for name in names:
                with self.subTest(selector=selector, name=name):
                    self.assertNotIn(name, selector)

    def test_the_view_rules_take_the_outer_split_alone(self) -> None:
        """The two views zoom the list's own split, never one nested in
        its pane."""
        parts = [" ".join(part.split())
                 for _, selector, _ in located(self.text)
                 for part in selector.split(",")
                 if "[data-view" in part
                 or "[value=\"details\"]:checked" in part]
        self.assertTrue(parts)
        named = [part for part in parts if re.search(r"\.split(?![\w])",
                                                     part)]
        self.assertTrue(named, "no view rule names the split")
        for part in named:
            with self.subTest(selector=part):
                self.assertIn(".split--outer", part)

    def test_the_stylesheet_holds_no_rule_per_column(self) -> None:
        """The rules that hide a column of ``Spalten`` come with the
        page, not with the stylesheet."""
        for selector, _ in rules(self.text):
            with self.subTest(selector=selector):
                self.assertNotIn("#column-", selector)

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

    def screen_rules(self, needle: str) -> list[tuple[str, str]]:
        """The rules inside an ``@media screen`` block whose selector
        holds NEEDLE."""
        spans = screen_blocks(blanked(self.text))
        return [(selector, body)
                for start, selector, body in located(self.text)
                if needle in selector
                and any(a <= start < b for a, b in spans)]

    def hiding(self, needle: str) -> list[tuple[int, str, str]]:
        """Each rule of the stylesheet whose selector holds NEEDLE and
        whose body hides, as its place, one selector of its list and its
        body."""
        return [(start, part.strip(), body)
                for start, selector, body in located(self.text)
                for part in selector.split(",")
                if needle in part
                and re.search(r"display:\s*none", body)]

    def test_the_views_do_not_depend_on_the_old_switch(self) -> None:
        for _, selector, _ in located(self.text):
            with self.subTest(selector=selector):
                self.assertNotIn("detail-switch", selector)

    def test_the_radio_rules_are_for_the_screen_alone(self) -> None:
        spans = screen_blocks(blanked(self.text))
        found = [start for start, selector, _ in located(self.text)
                 if "[value=\"details\"]:checked" in selector]
        self.assertTrue(found)
        for place in found:
            with self.subTest(at=place):
                self.assertTrue(any(a <= place < b for a, b in spans))

    def test_the_details_view_shows_the_pane(self) -> None:
        shown = [(part.strip(), body)
                 for start, selector, body in located(self.text)
                 for part in selector.split(",")
                 if "#item-detail" in part
                 and re.search(r"display:\s*(?!none\b)[a-z]", body)]
        self.assertTrue(any(
            re.search(r"\[data-view=[\"']?details[\"']?\]", part)
            and "[data-scripted]" in part for part, _ in shown), shown)
        self.assertTrue(any(
            "input[name=\"view\"][value=\"details\"]:checked" in part
            and ":not([data-scripted])" in part for part, _ in shown),
            shown)

    def test_the_table_fills_its_box(self) -> None:
        """The table stretches to the width of its box."""
        ours = (".main-table", "table.main-table")
        widths = [(start, part.strip(), width.strip())
                  for start, selector, body in located(self.text)
                  for part in selector.split(",")
                  for width in re.findall(r"(?<![-\w])width:\s*([^;}]+)",
                                          body)
                  if part.strip() in ours]
        self.assertTrue(widths, "no rule sets the width of .main-table")
        start, part, width = widths[-1]
        self.assertEqual(width, "100%")

    def test_the_marked_row_is_marked_in_both_views(self) -> None:
        marks = [(part.strip(), body)
                 for _, selector, body in located(self.text)
                 for part in selector.split(",")
                 if re.search(r"\btr\[aria-current", part)]
        self.assertTrue(marks, "no rule marks the row")
        both = [part for part, body in marks
                if not re.search(r"view-|data-view|detail-switch", part)
                and re.search(r"background|box-shadow", body)]
        self.assertTrue(both, marks)

    def test_the_pane_is_hidden_without_the_switch_and_on_paper(
            self) -> None:
        """Item list: on paper the table prints without the details."""
        spans = screen_blocks(blanked(self.text))
        printed = [
            (selector, body) for start, selector, body
            in located(self.text)
            if re.search(r"#item-detail\s*(,|\Z)", selector)
            and ":checked" not in selector
            and not any(a <= start < b for a, b in spans)]
        self.assertTrue(any(re.search(r"display:\s*none", body)
                            for _, body in printed), printed)

    def test_a_pane_in_a_request_is_dimmed_and_takes_no_pointer(
            self) -> None:
        waiting = [body for selector, body in rules(self.text)
                   if "item-detail" in selector
                   and "htmx-request" in selector]
        self.assertTrue(waiting)
        self.assertTrue(any(re.search(r"pointer-events:\s*none", body)
                            for body in waiting), waiting)
        self.assertTrue(any(re.search(r"opacity:\s*0?\.\d+", body)
                            for body in waiting), waiting)

    def motion_spans(self) -> list[tuple[int, int]]:
        """The spans of the bodies of the blocks that apply only where
        the user has not asked for reduced motion."""
        text = blanked(self.text)
        spans = []
        for found in re.finditer(
                r"@media[^{}]*prefers-reduced-motion:\s*no-preference"
                r"[^{}]*\{", text):
            body, end = balanced(text, found.start())
            spans.append((end - len(body) - 1, end))
        return spans

    def named(self) -> dict[str, list[tuple[int, str]]]:
        """The names that rules give to view transitions, each with the
        places and selectors of the rules that give it."""
        found: dict[str, list[tuple[int, str]]] = {}
        for start, selector, body in located(self.text):
            for name in re.findall(
                    r"view-transition-name:\s*([\w-]+)", body):
                found.setdefault(name, []).append((start, selector))
        return found

    def test_the_table_box_and_the_pane_are_named_for_the_transition(
            self) -> None:
        names = self.named()
        boxed = [name for name, places in names.items()
                 if any("table-scroll" in selector
                        or "table-sticky" in selector
                        for _, selector in places)]
        paned = [name for name, places in names.items()
                 if any("item-detail" in selector
                        for _, selector in places)]
        self.assertTrue(boxed, "the table box has no name")
        self.assertTrue(paned, "the pane has no name")
        self.assertFalse(set(boxed) & set(paned))
        self.assertNotIn("none", boxed + paned)

    def test_the_transition_is_for_users_who_accept_motion(self) -> None:
        """The names and the snapshots' rules sit in
        ``prefers-reduced-motion: no-preference`` alone."""
        spans = self.motion_spans()
        self.assertTrue(spans, "no block for no-preference")
        places = [(place, selector)
                  for found in self.named().values()
                  for place, selector in found]
        places += [(start, selector)
                   for start, selector, _ in located(self.text)
                   if "::view-transition" in selector]
        self.assertTrue(places)
        for place, selector in places:
            with self.subTest(selector=selector):
                self.assertTrue(any(a <= place < b for a, b in spans))

    def test_the_tables_snapshots_are_drawn_unscaled(self) -> None:
        names = self.named()
        box = next((name for name, places in names.items()
                    if any("table-scroll" in selector
                           or "table-sticky" in selector
                           for _, selector in places)), None)
        self.assertIsNotNone(box, "the table box has no name")
        for side in ("old", "new"):
            with self.subTest(snapshot=side):
                found = [body for _, selector, body in located(self.text)
                         if re.search(
                             rf"::view-transition-{side}\(\s*{box}\s*\)",
                             selector)]
                self.assertTrue(found, f"no rule for the {side} snapshot")
                self.assertTrue(any(
                    re.search(r"object-fit:\s*none", body)
                    for body in found), found)
