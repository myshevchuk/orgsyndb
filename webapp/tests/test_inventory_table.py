"""Tests of the item list's table: sorting by its columns, the filter
row, the consumption heat, grouped sizes and the box that keeps the
headers in view (end-product-inventory: Item list, Consumption heat)."""

import re
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from django.test import SimpleTestCase

from inventory.models import Item

from . import build_index, field_value, page, table
from .inventory_support import LIST, InventoryCase, fresh
from .test_inventory_colours import (CSS, MINIMUM, balanced, contrast,
                                     split_schemes)

SORTS = ("number", "name", "category", "container", "compartment", "box",
         "stock", "mean_year", "this_year", "coverage", "bulk", "note")
COLUMNS = ["Artikelnr.", "Name", "Kategorie", "Gebinde", "Fach", "Box",
           "Bestand", "Ø Jahr", "lfd. Jahr", "Reichweite", "Bulk",
           "Bemerkung"]
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
        return {th.text(): th for th in first.find_all("th")}

    def header_link(self, root, column: str) -> dict[str, list[str]]:
        return query_of(self.headers(root)[column].find("a").get("href"))


class SortTests(TableCase):

    def test_sorting_by_a_column(self) -> None:
        """Scenario: Sorting by a column."""
        self.item("A-1", category="Säuren")
        self.item("A-2")
        self.item("A-3", category="Ester")
        root = self.listing("?sort=category")
        header, rows = table(root)
        self.assertEqual([row[header[0]].text() for row in rows],
                         ["A-3", "A-1", "A-2"])
        self.assertEqual(self.articles("?sort=category&dir=desc"),
                         ["A-1", "A-3", "A-2"])
        headers = self.headers(root)
        self.assertEqual(headers["Kategorie"].get("aria-sort"), "ascending")
        self.assertEqual(self.header_link(root, "Kategorie"),
                         {"sort": ["category"], "dir": ["desc"]})
        self.assertEqual(self.header_link(root, "Artikelnr."),
                         {"sort": ["number"]})
        self.assertEqual([name for name, th in headers.items()
                          if th.get("aria-sort") is not None],
                         ["Kategorie"])

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
        for key, column in zip(SORTS, COLUMNS):
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

    def test_the_default_order_is_by_article_number(self) -> None:
        self.item("B-2")
        self.item("B-1")
        self.item(None, "Zeta")
        self.item(None, "alpha")
        for query in ("", "?sort=xyz", "?sort=number", "?dir=up",
                      "?sort=urgency"):
            with self.subTest(query=query):
                root = self.listing(query)
                self.assertEqual(self.headers(root)["Artikelnr."]
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
            "B-2 10 µmol", "B-1 1 g", "B-1 5 mg", "alpha 10 µmol",
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
        self.assertEqual(self.header_link(root, "Bulk"), {
            "category": ["Grün"], "q": ["k"], "stock": ["watch"],
            "sort": ["bulk"]})


class FilterTests(TableCase):

    def test_column_filters(self) -> None:
        """Scenario: Column filters."""
        self.item("CH-0012", "(E)-Zimtsäure", "100", "mg",
                  note="Kühlschrank")
        self.item("CH-0010", "Aspirin", "1", "g")
        self.item("CH-0016", "Isopentylacetat", "100", "mg")
        for query, wanted, name, value in (
                ("?number=0012", ["CH-0012"], "number", "0012"),
                ("?name=ZIMT", ["CH-0012"], "name", "ZIMT"),
                (f"?container={quote('100 mg')}", ["CH-0012", "CH-0016"],
                 "container", "100 mg"),
                (f"?note={quote('kühl')}", ["CH-0012"], "note", "kühl")):
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
        reset = next(a for a in root.find_all("a")
                     if a.text() == "Zurücksetzen")
        self.assertEqual(query_of(reset.get("href")),
                         {"sort": ["name"], "dir": ["desc"]})

    def test_the_filter_row(self) -> None:
        self.item("F-1", category="Ester")
        root = self.listing()
        rows = root.find("table").find("thead").find_all("tr")
        self.assertEqual(len(rows), 2)
        cells = [c for c in rows[1].children
                 if not isinstance(c, str) and c.tag in ("th", "td")]
        self.assertEqual(len(cells), len(COLUMNS))
        controls = {}
        for column, cell in zip(COLUMNS, cells):
            found = cell.find_all(("input", "select"))
            if found:
                self.assertEqual(len(found), 1, column)
                control = found[0]
                self.assertEqual(control.get("form"), "filters")
                self.assertEqual(control.get("aria-label"), column)
                controls[column] = (control.tag, control.get("name"))
        self.assertEqual(controls, {
            "Artikelnr.": ("input", "number"), "Name": ("input", "name"),
            "Kategorie": ("select", "category"),
            "Gebinde": ("select", "container"),
            "Fach": ("select", "compartment"), "Box": ("select", "box"),
            "Bestand": ("select", "stock"),
            "Bemerkung": ("input", "note")})
        form = root.find("form", id="filters")
        self.assertEqual(form.get("method"), "get")
        self.assertIsNone(form.closest("table"))
        self.assertIsNotNone(form.find("input", name="q"))
        self.assertEqual(form.find("button").text(), "Filtern")

    def test_the_name_filter_finds_the_compound(self) -> None:
        self.item("CH-0012", "Probe")
        self.item("CH-0001", "Probe")
        self.assertEqual(self.articles(f"?name={quote('zimts')}"),
                         ["CH-0012"])

    def test_the_number_filter_skips_items_without_one(self) -> None:
        self.item("A-1")
        self.item(None, "A-1 Neu")
        self.assertEqual(self.articles("?number=a-1"), ["A-1"])

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

    def test_the_stock_choice(self) -> None:
        self.item("H-1")
        root = self.listing("?stock=dormant")
        options = root.find("select", name="stock").find_all("option")
        self.assertEqual([o.get("value") for o in options],
                         ["", "out", "critical", "low", "watch", "ok",
                          "undelivered", "dormant"])
        self.assertEqual([o.text() for o in options][1:], LEVEL_LABELS)
        self.assertEqual(field_value(root, "stock"), "dormant")

    def test_the_filters_keep_the_order(self) -> None:
        self.item("O-1")
        root = self.listing("?sort=coverage&dir=desc&q=o")
        form = root.find("form", id="filters")
        hidden = {i.get("name"): i.get("value") for i in
                  form.find_all("input", type="hidden")}
        self.assertEqual(hidden, {"sort": "coverage", "dir": "desc"})
        self.assertEqual(field_value(root, "q"), "o")

    def test_without_a_reversed_order_no_dir_is_kept(self) -> None:
        self.item("O-1")
        form = self.listing().find("form", id="filters")
        self.assertEqual({i.get("name"): i.get("value") for i in
                          form.find_all("input", type="hidden")},
                         {"sort": "number"})

    def test_the_level_filter_is_gone(self) -> None:
        for quantity in (0, 8):
            self.with_mean_quarter(
                self.item(f"L-{quantity}", quantity=quantity), 4)
        self.assertEqual(self.articles("?level=out"), ["L-0", "L-8"])
        root = self.listing()
        self.assertIsNone(root.find("select", name="level"))
        self.assertIsNone(root.find("select", name="sort"))


class HeatTests(TableCase):

    def test_fifths_of_the_consuming_items(self) -> None:
        """Scenario: Fifths of the consuming items."""
        for article, count in (("H-0", 0), ("H-1", 1), ("H-2", 2),
                               ("H-2b", 2), ("H-5", 5), ("H-9", 9)):
            item = self.item(article)
            if count:
                self.enter(item, 2026, 1, count)
        header, rows = table(self.listing())
        heats = {row[header[0]].text(): heat_of(row["lfd. Jahr"])
                 for row in rows}
        self.assertEqual(heats, {"H-0": None, "H-1": "heat-1",
                                 "H-2": "heat-2", "H-2b": "heat-2",
                                 "H-5": "heat-4", "H-9": "heat-5"})
        header, rows = table(self.listing("?number=h-9"))
        self.assertEqual(heat_of(rows[0]["lfd. Jahr"]), "heat-5")

    def test_the_mean_per_year_has_its_own_fifths(self) -> None:
        for article, mean in (("M-1", 1), ("M-2", 2), ("M-3", 3)):
            self.with_mean_quarter(self.item(article), mean)
        self.item("M-4")
        header, rows = table(self.listing())
        self.assertEqual([heat_of(row["Ø Jahr"]) for row in rows],
                         ["heat-1", "heat-2", "heat-4", None])
        self.assertEqual([heat_of(row["lfd. Jahr"]) for row in rows],
                         [None] * 4)

    def test_one_consuming_item(self) -> None:
        self.enter(self.item("O-1"), 2026, 1, 4)
        header, rows = table(self.listing())
        self.assertEqual(heat_of(rows[0]["lfd. Jahr"]), "heat-1")

    def test_the_legend_shows_the_scale(self) -> None:
        self.item("S-1")
        root = self.listing()
        scale = root.find(cls="heat-legend")
        self.assertIsNotNone(scale)
        self.assertEqual([heat_of(e) for e in scale.walk()
                          if heat_of(e)], HEATS)
        text = scale.text()
        self.assertLess(text.index("wenig"), text.index("viel"))

    def test_the_english_scale(self) -> None:
        self.use_index(build_index("en"))
        self.item("S-1")
        text = self.listing().find(cls="heat-legend").text()
        self.assertLess(text.index("little"), text.index("much"))


class GroupingTests(TableCase):

    def test_sizes_of_one_article_grouped(self) -> None:
        """Scenario: Sizes of one article grouped."""
        self.item("CH-0012", "(E)-Zimtsäure", "100", "mg")
        self.item("CH-0012", "(E)-Zimtsäure", "1", "g")
        self.item("CH-0010", "Aspirin", "1", "g")
        self.item(None, "Brücke 3")
        self.item(None, "Neuverbindung 9")
        root = self.listing()
        body = root.find("table").find("tbody").find_all("tr")
        self.assertEqual(self.keys(), [
            "CH-0010 1 g", "CH-0012 1 g", "CH-0012 100 mg",
            "Brücke 3 10 µmol", "Neuverbindung 9 10 µmol"])
        self.assertEqual(["same-article" in tr.classes for tr in body],
                         [False, False, True, False, False])
        name = [c for c in body[2].children
                if not isinstance(c, str) and c.tag == "td"][1]
        hidden = name.find("span", "visually-hidden")
        self.assertEqual(hidden.text(), "(E)-Zimtsäure")
        for tr in body[3:]:
            cell = [c for c in tr.children
                    if not isinstance(c, str) and c.tag == "td"][1]
            self.assertIsNotNone(cell.find("a"))
            self.assertIsNone(cell.find("span", "visually-hidden"))
        other = self.listing("?sort=name").find("table").find("tbody")
        self.assertFalse(any("same-article" in tr.classes
                             for tr in other.find_all("tr")))

    def test_grouped_in_descending_order_too(self) -> None:
        self.item("CH-0012", size="100", unit="mg")
        self.item("CH-0012", size="1", unit="g")
        self.item("CH-0010")
        body = self.listing("?sort=number&dir=desc").find(
            "table").find("tbody").find_all("tr")
        self.assertEqual(["same-article" in tr.classes for tr in body],
                         [False, True, False])


class StickyTests(TableCase):

    def test_a_table_that_keeps_its_headers(self) -> None:
        """Scenario: A table that keeps its headers."""
        self.item("T-1")
        root = self.listing()
        box = root.find("table").parent
        self.assertEqual(box.tag, "div")
        self.assertLessEqual({"table-scroll", "table-sticky"}, box.classes)
        self.assertEqual(len(root.find("thead").find_all("tr")), 2)
        header, _ = table(root)
        self.assertEqual(header, COLUMNS)

    def test_the_english_columns(self) -> None:
        self.use_index(build_index("en"))
        self.item("T-1")
        header, _ = table(self.listing())
        self.assertEqual(header, [
            "Article no.", "Name", "Category", "Container", "Compartment",
            "Box", "Stock", "Mean per year", "This year", "Coverage",
            "Bulk", "Note"])


def screen_blocks(text: str) -> list[tuple[int, int]]:
    """The spans of the bodies of the ``@media screen`` blocks of TEXT."""
    spans = []
    for found in re.finditer(r"@media\s+screen\s*\{", text):
        body, end = balanced(text, found.start())
        spans.append((end - len(body) - 1, end))
    return spans


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
        rule = re.search(r"([^{}]*)\{\s*display:\s*none;\s*\}", printed)
        self.assertIsNotNone(rule)
        self.assertIn(".filter-row", rule.group(1))
        self.assertIn(".lab-toolbar", rule.group(1))

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
