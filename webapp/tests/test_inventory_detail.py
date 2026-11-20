"""Tests of the details of one item that the item list shows beside its
table: in the list, in the view that loads them in place and in the rows
that ask for them (end-product-inventory: Item list).

The details are one element, ``#item-detail``, that carries the id of
its item as ``data-item``; the row of that item carries
``aria-current="true"``.
"""

import re
from datetime import date
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from . import Element, berlin, page, table, ticking
from .inventory_support import (
    LIST,
    SUBSTANCE_PAGE,
    InventoryCase,
    has_amount,
    has_number,
    item_url,
    lot_url,
)
from .test_inventory_table import body_rows

HTMX = {"HTTP_HX_REQUEST": "true"}
LOT_PAGE = re.compile(r"^/lab/inventory/bulk/\d+/$")
MISSING = "nicht hinterlegt"
ACTIONS = ("Artikelnr. eintragen", "Abgabe buchen", "Abfüllen",
           "Bestand korrigieren", "Verbrauch nachtragen", "Bearbeiten")


def detail_url(item: Any) -> str:
    return f"/lab/inventory/items/{item.pk}/detail/"


def pane_of(root: Element) -> Element:
    """The one element with the id ``item-detail`` of a page."""
    found = root.find_all(id="item-detail")
    assert len(found) == 1, f"{len(found)} elements are #item-detail"
    return found[0]


def chosen_rows(root: Element) -> list[Element]:
    """The rows of the list's table marked as chosen."""
    return [row for row in root.find_all("tr")
            if row.get("aria-current") == "true"]


def definition(pane: Element, term: str) -> Element | None:
    """The ``dd`` that follows the ``dt`` ``term`` in the pane."""
    for dt in pane.find_all("dt"):
        if dt.text() == term:
            siblings = dt.parent.children
            for node in siblings[siblings.index(dt) + 1:]:
                if isinstance(node, Element) and node.tag == "dd":
                    return node
    return None


def links(pane: Element) -> dict[str, str]:
    """The links of the pane by their text."""
    return {a.text(): a.get("href") for a in pane.find_all("a")}


def outline(node: Element) -> tuple:
    """The structure of an element, white space made one space and
    attributes in order."""
    return (node.tag, tuple(sorted(node.attrs.items())), tuple(
        outline(child) if isinstance(child, Element) else
        " ".join(child.split())
        for child in node.children
        if isinstance(child, Element) or child.strip()))


class DetailCase(InventoryCase):

    def listing(self, query: str = "") -> Element:
        response = self.client.get(LIST + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def pane(self, query: str = "") -> Element:
        return pane_of(self.listing(query))

    def shown(self, query: str = "") -> str | None:
        """The id of the item whose details the list shows."""
        return self.pane(query).get("data-item")


class DetailsOfAnItemTests(DetailCase):

    def test_details_of_an_item(self) -> None:
        """Scenario: Details of an item."""
        item = self.item("CH-0012", "(E)-Zimtsäure", "100", "mg",
                         quantity=5)
        self.enter_year(item, 2024, 4)
        for quarter, count in ((1, 6), (2, 5), (3, 7)):
            self.enter(item, 2026, quarter, count)
        self.deliver(item, 2, date(2026, 10, 15))
        lot = self.lot("CH-0012", "mg", "50", batch="B-7",
                       location="Kühlschrank 2")
        root = self.listing(f"?detail={item.pk}")
        pane = pane_of(root)
        self.assertEqual(pane.get("data-item"), str(item.pk))
        self.assertIsNone(pane.closest("table"))
        self.assertIsNotNone(pane.closest("main"))
        text = pane.text()
        for shown in ("CH-0012", "(E)-Zimtsäure", "100 mg"):
            self.assertIn(shown, text)
        self.assertEqual([a.get("href") for a in pane.find_all("a")
                          if SUBSTANCE_PAGE.search(a.get("href", ""))],
                         ["/lab/registry/substances/cinnamic-acid/"])
        _, rows = table(root)
        level = next(name[6:] for name in rows[0]["Bestand"].classes
                     if name.startswith("level-"))
        stock = pane.find(cls=f"level-{level}")
        self.assertIsNotNone(stock, level)
        self.assertTrue(has_number(stock.text(), "3"), stock.text())
        self.assertEqual(text.count(MISSING), 2)
        self.assertIn("Kühlschrank 2", text)
        batch = [a for a in pane.find_all("a")
                 if a.get("href") == lot_url(lot)]
        self.assertEqual(len(batch), 1)
        self.assertIn("B-7", batch[0].text())
        self.assertTrue(has_amount(text, "50", "mg"), text)
        header, years = table(pane)
        self.assertEqual(header, ["Jahr", "Q1", "Q2", "Q3", "Q4", "Summe"])
        self.assertEqual([[cell.text() for cell in year.values()]
                          for year in years],
                         [["2024", "4", "4", "4", "4", "16"],
                          ["2025", "0", "0", "0", "0", "0"],
                          ["2026", "6", "5", "7", "2", "20"]])
        entered = pane.find(cls="entered-years").text()
        self.assertIn("2024", entered)
        self.assertIn("2026", entered)
        self.assertNotIn("2025", entered)
        self.assertIn(item_url(item), links(pane).values())

    def test_the_quarters_of_the_current_year(self) -> None:
        item = self.item("CH-0012", "(E)-Zimtsäure", quantity=6)
        for quarter, count in ((1, 6), (2, 5), (3, 7)):
            self.enter(item, 2026, quarter, count)
        self.deliver(item, 2, date(2026, 10, 15))
        pane = self.pane(f"?detail={item.pk}")
        bars = pane.find_all(cls="quarter-bar")
        self.assertEqual(len(bars), 4)
        self.assertEqual(["current" in bar.classes for bar in bars],
                         [False, False, False, True])
        self.assertIn("laufend", bars[3].text())

    def test_quarters_to_come_are_empty(self) -> None:
        item = self.item("Q-1")
        self.enter(item, 2026, 1, 3)
        with ticking(berlin(2026, 5, 4, 8)):
            pane = self.pane(f"?detail={item.pk}")
        _, years = table(pane)
        self.assertEqual([cell.text() for cell in years[2].values()],
                         ["2026", "3", "0", "", "", "3"])
        bars = pane.find_all(cls="quarter-bar")
        self.assertEqual(["current" in bar.classes for bar in bars],
                         [False, True, False, False])
        self.assertIsNone(bars[2].find(cls="bar"))

    def test_the_means_and_the_coverage(self) -> None:
        item = self.means_item()
        pane = self.pane(f"?detail={item.pk}")
        self.assertEqual(definition(pane, "Ø Jahr").text(), "18,0")
        self.assertEqual(definition(pane, "Ø Quartal").text(), "4,5")
        self.assertEqual(definition(pane, "2026 bis 4. November").text(),
                         "13")
        self.assertNotIn("projected",
                         definition(pane, "Ø Jahr").classes)
        self.assertTrue(has_number(pane.text(), "0,7"), pane.text())

    def test_means_there_are_not_show_a_dash(self) -> None:
        item = self.item("N-1")
        pane = self.pane(f"?detail={item.pk}")
        self.assertEqual(definition(pane, "Ø Jahr").text(), "–")
        self.assertEqual(definition(pane, "Ø Quartal").text(), "–")

    def test_projected_means_are_marked(self) -> None:
        item = self.item("P-1", quantity=3)
        self.enter(item, 2026, 2, 6)
        pane = self.pane(f"?detail={item.pk}")
        for term in ("Ø Jahr", "Ø Quartal"):
            with self.subTest(term=term):
                self.assertIn("projected", definition(pane, term).classes)

    def test_the_locations_that_are_set(self) -> None:
        item = self.item("CH-0012", quantity=1, compartment="2", box="7")
        self.lot("CH-0012", "mg", "50")
        pane = self.pane(f"?detail={item.pk}")
        self.assertEqual(definition(pane, "Fach").text(), "2")
        self.assertEqual(definition(pane, "Box").text(), "7")
        self.assertEqual(pane.text().count(MISSING), 1)

    def test_an_item_without_lots_links_none(self) -> None:
        item = self.item(None, "Neuverbindung 9", quantity=2)
        pane = self.pane(f"?detail={item.pk}")
        self.assertEqual([a for a in pane.find_all("a")
                          if LOT_PAGE.match(a.get("href", ""))], [])
        self.assertIn("10 µmol", pane.text())
        self.assertEqual(pane.text().count(MISSING), 2)

    def test_the_lots_of_the_substance_only(self) -> None:
        item = self.item("CH-0012", "(E)-Zimtsäure")
        mine = self.lot("CH-0012", "mg", "50", batch="B-7")
        self.lot("CH-0001", "mg", "20", batch="B-9")
        pane = self.pane(f"?detail={item.pk}")
        self.assertEqual([a.get("href") for a in pane.find_all("a")
                          if LOT_PAGE.match(a.get("href", ""))],
                         [lot_url(mine)])

    def test_the_head_marks_a_new_item_and_its_status(self) -> None:
        fresh = self.item("N-1", stocked_on=date(2026, 2, 1))
        old = self.item("N-2")
        set_aside = self.item("N-3", status="discontinued")
        self.assertIsNotNone(
            self.pane(f"?detail={fresh.pk}").find("sup", "mark-new"))
        self.assertIsNone(
            self.pane(f"?detail={old.pk}").find("sup", "mark-new"))
        self.assertIn("auslaufend",
                      self.pane(f"?detail={set_aside.pk}").text())
        self.assertNotIn("auslaufend",
                         self.pane(f"?detail={old.pk}").text())

    def test_the_note_shows(self) -> None:
        item = self.item("N-1", note="Kühl lagern")
        self.assertIn("Kühl lagern",
                      self.pane(f"?detail={item.pk}").text())


class ChosenItemTests(DetailCase):

    def test_details_of_the_first_item(self) -> None:
        """Scenario: Details of the first item."""
        first = self.item("A-1", category="Säuren")
        second = self.item("A-2", category="Ester")
        for query, wanted in (
                ("", second), (f"?detail={second.pk + 999}", second),
                (f"?category={quote('Säuren')}&detail={second.pk}", first)):
            with self.subTest(query=query):
                self.assertEqual(self.shown(query), str(wanted.pk))
        root = self.listing(f"?category=Basen&detail={second.pk}")
        self.assertEqual(root.find_all(attrs={"data-item": True}), [])
        self.assertEqual(chosen_rows(root), [])

    def test_a_listed_item_is_chosen_wherever_it_stands(self) -> None:
        self.item("A-1", category="Säuren")
        second = self.item("A-2", category="Ester")
        third = self.item("A-3", category="Basen")
        for chosen in (second, third):
            with self.subTest(item=chosen.pk):
                self.assertEqual(self.shown(f"?detail={chosen.pk}"),
                                 str(chosen.pk))

    def test_a_detail_that_names_no_item_falls_back(self) -> None:
        first = self.item("A-1")
        for value in ("abc", "", "-1", "1.5", "99999999", "9" * 5000):
            with self.subTest(detail=value):
                self.assertEqual(self.shown(f"?detail={value}"),
                                 str(first.pk))

    def test_an_item_the_filters_leave_out_is_not_chosen(self) -> None:
        listed = self.item("A-1", category="Ester")
        left_out = self.item("A-2", category="Säuren")
        for query in (f"?category=Ester&detail={left_out.pk}",
                      f"?q=A-1&detail={left_out.pk}"):
            with self.subTest(query=query):
                root = self.listing(query)
                self.assertEqual(pane_of(root).get("data-item"),
                                 str(listed.pk))
                self.assertEqual([row.get("data-item")
                                  for row in chosen_rows(root)],
                                 [str(listed.pk)])

    def test_the_chosen_row_is_marked(self) -> None:
        self.item("A-1", category="Ester")
        second = self.item("A-2", category="Säuren")
        for query, wanted in (("", "A-1"), (f"?detail={second.pk}", "A-2")):
            with self.subTest(query=query):
                root = self.listing(query)
                header, rows = table(root)
                marked = chosen_rows(root)
                self.assertEqual(len(marked), 1)
                self.assertEqual(marked[0].get("data-item"),
                                 pane_of(root).get("data-item"))
                self.assertEqual(
                    [row[header[0]].text() for row in rows
                     if row[header[0]].parent is marked[0]], [wanted])

    def test_no_item_no_details(self) -> None:
        lone = self.item("A-0")
        self.assertEqual(self.shown(f"?detail={lone.pk}"), str(lone.pk))
        lone.delete()
        for query in ("", "?detail=5"):
            with self.subTest(query=query):
                root = self.listing(query)
                self.assertEqual(root.find_all(attrs={"data-item": True}),
                                 [])
                self.assertEqual(chosen_rows(root), [])
        item = self.item("A-1")
        root = self.listing(f"?q=nothing&detail={item.pk}")
        self.assertEqual(root.find_all(attrs={"data-item": True}), [])
        self.assertEqual(chosen_rows(root), [])

    def test_a_list_cut_by_the_filters_chooses_its_own_first_row(
            self) -> None:
        """The details always belong to a row of the table."""
        self.item("A-1")
        second = self.item("A-2")
        root = self.listing("?q=A-2")
        self.assertEqual([row.get("data-item") for row in chosen_rows(root)],
                         [str(second.pk)])
        self.assertEqual(pane_of(root).get("data-item"), str(second.pk))


class RowTests(DetailCase):

    def test_rows_ask_for_their_details_and_the_body_takes_them(
            self) -> None:
        """Scenario: Another item in place (the list's attributes)."""
        items = [self.item("A-1", category="Ester"),
                 self.item("A-2", category="Ester"),
                 self.item(None, "Neuverbindung 9")]
        root = self.listing("?category=Ester")
        grid = root.find("table")
        body = grid.find("tbody")
        self.assertEqual(
            {name: body.get(name) for name in (
                "hx-target", "hx-swap", "hx-sync", "hx-indicator")},
            {"hx-target": "#item-detail", "hx-swap": "outerHTML",
             "hx-sync": "this:replace", "hx-indicator": "#item-detail"})
        rows = body_rows(root)
        self.assertEqual([row.get("data-item") for row in rows],
                         [str(item.pk) for item in items[:2]])
        for row, item in zip(rows, items[:2]):
            with self.subTest(item=item.pk):
                self.assertEqual(row.get("hx-get"), detail_url(item))
                self.assertEqual(row.get("hx-trigger"), "item-select")

    def test_every_row_of_the_whole_list_is_asking(self) -> None:
        items = [self.item("A-1"), self.item(None, "Neuverbindung 9")]
        rows = body_rows(self.listing())
        self.assertEqual(sorted(row.get("data-item") or "" for row in rows),
                         sorted(str(item.pk) for item in items))
        for row in rows:
            with self.subTest(row=row.get("data-item")):
                self.assertEqual(row.get("hx-get"),
                                 f"/lab/inventory/items/"
                                 f"{row.get('data-item')}/detail/")
                self.assertEqual(row.get("hx-trigger"), "item-select")


class LinkTests(DetailCase):

    def actions(self, item: Any) -> dict[str, str]:
        found = links(self.pane(f"?detail={item.pk}"))
        return {text: href for text, href in found.items()
                if text in ACTIONS}

    def test_links_in_the_details(self) -> None:
        """Scenario: Links in the details."""
        item = self.item(None, "Neuverbindung 9")
        self.client.force_login(self.kl)
        self.assertEqual(self.actions(item), {
            "Artikelnr. eintragen": item_url(item, "edit"),
            "Abfüllen": item_url(item, "fill"),
            "Bestand korrigieren": item_url(item, "correct"),
            "Bearbeiten": item_url(item, "edit")})
        self.client.logout()
        self.assertEqual(self.actions(item), {})

    def test_the_links_of_an_item_with_an_article_number(self) -> None:
        item = self.item("CH-0012")
        self.deliver(item, 1)
        self.client.force_login(self.kl)
        self.assertEqual(self.actions(item), {
            "Abgabe buchen": f"/lab/inventory/deliveries/new/?item={item.pk}",
            "Abfüllen": item_url(item, "fill"),
            "Bestand korrigieren": item_url(item, "correct"),
            "Verbrauch nachtragen": item_url(item, "consumption"),
            "Bearbeiten": item_url(item, "edit")})

    def test_no_reversals_in_the_details(self) -> None:
        item = self.item("CH-0012")
        self.deliver(item, 1)
        self.client.force_login(self.kl)
        pane = self.pane(f"?detail={item.pk}")
        self.assertEqual([a.get("href") for a in pane.find_all("a")
                          if "/reverse/" in a.get("href", "")], [])
        self.assertNotIn("Stornieren", links(pane))

    def test_everyone_may_open_the_items_page(self) -> None:
        item = self.item("CH-0012")
        for signed_in in (False, True):
            with self.subTest(signed_in=signed_in):
                if signed_in:
                    self.client.force_login(self.kl)
                self.assertIn(item_url(item),
                              links(self.pane(f"?detail={item.pk}"))
                              .values())


class DetailViewTests(DetailCase):

    def test_htmx_gets_the_pane_alone(self) -> None:
        item = self.item("CH-0012", "(E)-Zimtsäure")
        response = self.client.get(detail_url(item), **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        elements = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].get("id"), "item-detail")
        self.assertEqual(elements[0].get("data-item"), str(item.pk))
        self.assertIn("(E)-Zimtsäure", elements[0].text())

    def test_another_item_in_place(self) -> None:
        """Scenario: Another item in place."""
        self.item("A-1", category="Säuren")
        self.item("A-2", category="Ester")
        third = self.item("A-3", category="Ester")
        self.enter(third, 2026, 1, 3)
        self.lot("A-3", "mg", "50", batch="B-3", location="Regal 1")
        root = self.listing("?category=Ester")
        row = next((r for r in body_rows(root)
                    if r.get("data-item") == str(third.pk)), None)
        self.assertIsNotNone(row, "no row names the item")
        loaded = self.client.get(row.get("hx-get"), **HTMX)
        self.assertEqual(loaded.status_code, 200)
        pane = page(loaded)
        alone = [c for c in pane.children if isinstance(c, Element)]
        self.assertEqual(len(alone), 1)
        self.assertEqual(alone[0].get("data-item"), str(third.pk))
        listed = self.pane(f"?category=Ester&detail={third.pk}")
        self.assertEqual(outline(alone[0]), outline(listed))
        plain = self.client.get(row.get("hx-get"))
        self.assertIn(plain.status_code, (302, 303))
        target = urlsplit(plain["Location"])
        self.assertEqual(target.path, LIST)
        self.assertEqual(parse_qs(target.query)["detail"], [str(third.pk)])

    def test_the_loaded_pane_matches_the_lists_for_each_item(self) -> None:
        items = [self.means_item("A-1"), self.item(None, "Neuverbindung 9"),
                 self.item("A-3", status="discontinued", compartment="2")]
        self.lot("A-1", "mg", "50", batch="B-1")
        for item in items:
            with self.subTest(item=item.pk):
                loaded = page(self.client.get(detail_url(item), **HTMX))
                alone = [c for c in loaded.children
                         if isinstance(c, Element)]
                self.assertEqual(len(alone), 1)
                self.assertEqual(
                    outline(alone[0]),
                    outline(self.pane(f"?detail={item.pk}")))

    def test_the_loaded_pane_follows_the_user(self) -> None:
        item = self.item(None, "Neuverbindung 9")
        before = page(self.client.get(detail_url(item), **HTMX))
        self.assertEqual({a.text() for a in before.find_all("a")}
                         & set(ACTIONS), set())
        self.client.force_login(self.kl)
        after = page(self.client.get(detail_url(item), **HTMX))
        self.assertLessEqual({"Artikelnr. eintragen", "Bearbeiten"},
                             {a.text() for a in after.find_all("a")})

    def test_without_htmx_it_redirects_to_the_list(self) -> None:
        item = self.item("CH-0012")
        for extra in ({}, {"HTTP_HX_REQUEST": "false"}):
            with self.subTest(extra=extra):
                response = self.client.get(detail_url(item), **extra)
                self.assertIn(response.status_code, (302, 303))
                target = urlsplit(response["Location"])
                self.assertEqual(target.path, LIST)
                self.assertEqual(parse_qs(target.query)["detail"],
                                 [str(item.pk)])

    def test_the_answer_varies_with_the_header(self) -> None:
        item = self.item("CH-0012")
        for extra in (HTMX, {}):
            with self.subTest(extra=extra):
                response = self.client.get(detail_url(item), **extra)
                varied = {name.strip().lower() for name in
                          response.get("Vary", "").split(",")}
                self.assertIn("hx-request", varied)

    def test_an_unknown_item_is_not_found(self) -> None:
        item = self.item("CH-0012")
        self.assertEqual(self.client.get(detail_url(item), **HTMX)
                         .status_code, 200)
        for extra in (HTMX, {}):
            with self.subTest(extra=extra):
                response = self.client.get(
                    f"/lab/inventory/items/{item.pk + 999}/detail/",
                    **extra)
                self.assertEqual(response.status_code, 404)

    def test_the_list_loads_its_own_url_for_an_item_it_lists(self) -> None:
        item = self.item("CH-0012")
        row = body_rows(self.listing())[0]
        self.assertEqual(row.get("hx-get"), detail_url(item))
        self.assertEqual(self.client.get(row.get("hx-get"),
                                         **HTMX).status_code, 200)
