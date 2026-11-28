"""Tests of the details of a substance in the substance list (lab-
registry: Substance details; web-app: Main lists)."""

import re
from datetime import date
from decimal import Decimal
from typing import Any

from . import (Element, make_batch, make_class, make_group, make_item,
               make_substance, make_task, make_vessel, page)
from .demo_support import SeededCase
from .inventory_support import InventoryCase, batch_url, item_url
from .main_lists_support import (HTMX, body_of, cells, headers_of, heading_of,
                                 link_in, must_pane, key_number, replaced,
                                 texts_of_links, unsorted_reasons)
from .structure_support import ETHANOL
from .test_inventory_dialogs import current

REGISTRY = "/lab/registry/"
OPEN_PAGE = "Substanzseite öffnen"
ISO = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
COLUMNS = {"items": ["Gebinde", "Bestand"],
           "batches": ["Charge", "Datum", "Bestand"],
           "tasks": ["Nr.", "Status"]}


def detail_url(key: str) -> str:
    return f"{REGISTRY}substances/{key}/detail/"


def table_of(found: Element, kind: str) -> Element | None:
    """The table of the pane with the columns of KIND, None when the
    pane has none."""
    grids = [grid for grid in found.find_all("table")
             if headers_of(grid) == COLUMNS[kind]]
    assert len(grids) <= 1, f"{len(grids)} tables of {kind}"
    return grids[0] if grids else None


def rows_of(found: Element, kind: str) -> list[list[Element]]:
    grid = table_of(found, kind)
    assert grid is not None, f"the pane has no table of {kind}"
    return [cells(row) for row in body_of(grid)]


class DemoDetailsTests(SeededCase):
    """The details of a substance of the demo data set."""

    def test_details_of_a_substance(self) -> None:
        """Scenario: Details of a substance."""
        from inventory.models import Batch, Item
        from tasks.models import Task
        response = self.client.get(f"{REGISTRY}?selected=cinnamic-acid")
        found = must_pane(page(response))
        self.assertEqual(found.get("data-item"), "cinnamic-acid")
        heading = heading_of(found)
        self.assertEqual(heading.text(), "(E)-Zimtsäure")
        self.assertEqual(link_in(heading).get("href"),
                         f"{REGISTRY}substances/cinnamic-acid/")
        self.assertIn("CH-0012", found.text())
        links = [a.get("href") for a in found.find_all("a")]
        for item in Item.objects.filter(
                article__substance__key="cinnamic-acid"):
            self.assertIn(item_url(item), links)
        batches = Batch.objects.filter(substance__key="cinnamic-acid")
        self.assertTrue(batches.exists())
        for batch in batches:
            self.assertIn(batch_url(batch), links)
        for task in Task.objects.filter(substance__key="cinnamic-acid"):
            self.assertIn(f"/lab/tasks/{task.number}/", links)
        self.assertEqual(texts_of_links(found)[OPEN_PAGE],
                         f"{REGISTRY}substances/cinnamic-acid/")

    def test_the_demo_details_are_marked_data_item_with_the_key(self) -> None:
        for key in ("acetylsalicylic-acid", "1-biphenyl-4-yl-ethanol"):
            with self.subTest(key=key):
                found = self.client.get(detail_url(key), **HTMX)
                self.assertEqual(found.status_code, 200)
                self.assertEqual(
                    page(found).find(id="item-detail").get("data-item"),
                    key)


class SubstanceDetailsCase(InventoryCase):

    def listed(self, key: str, signed_in: bool = False,
               query: str = "") -> Element:
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(f"{REGISTRY}?selected={key}{query}")
        self.assertEqual(response.status_code, 200)
        return page(response)

    def details(self, key: str, signed_in: bool = False) -> Element:
        found = must_pane(self.listed(key, signed_in))
        self.assertIsNotNone(found, "the list has no #item-detail")
        self.assertEqual(found.get("data-item"), key)
        return found

    def acid(self) -> Any:
        """``cinnamic-acid`` with every field and the article
        ``CH-0012``."""
        make_group("final-products", "Final products",
                   label_de="Endprodukte")
        make_class("carboxylic-acids", "Carboxylic acids",
                   label_de="Carbonsäuren")
        return make_substance(
            "cinnamic-acid", "(E)-Cinnamic acid", name_de="(E)-Zimtsäure",
            short_name="ZS", group=make_group("final-products"),
            classes=["carboxylic-acids"], formula="C9H8O2", mw="148.16",
            cas="140-10-3")


class FieldsTests(SubstanceDetailsCase):

    def test_the_fields_of_a_substance(self) -> None:
        self.acid()
        self.item("CH-0012")
        text = self.details("cinnamic-acid").text()
        for shown in ("cinnamic-acid", "ZS", "Endprodukte", "Carbonsäuren",
                      "C9H8O2", "148,16", "140-10-3", "CH-0012"):
            self.assertIn(shown, text)

    def test_each_field_without_a_value_reads_a_dash(self) -> None:
        make_substance("bare", "Bare")
        text = self.details("bare").text()
        self.assertGreaterEqual(text.count("–"), 5)

    def test_the_heading_in_english(self) -> None:
        from .collection_support import accept
        accept(language="en")
        self.acid()
        self.assertEqual(self.details("cinnamic-acid")
                         .find(("h2", "h3")).text(), "(E)-Cinnamic acid")

    def test_a_substance_with_a_structure_shows_its_figure(self) -> None:
        make_substance("ethanol", "Ethanol", molfile=ETHANOL)
        make_substance("plain", "Plain")
        found = self.details("ethanol")
        figure = found.find("figure", cls="structure")
        self.assertIsNotNone(figure)
        self.assertEqual(
            figure.find("img").get("src"),
            f"{REGISTRY}substances/ethanol/structure.svg")
        self.assertIsNone(self.details("plain").find("figure",
                                                     cls="structure"))

    def test_a_visitor_sees_the_details_and_no_edit_link(self) -> None:
        self.acid()
        links = texts_of_links(self.details("cinnamic-acid"))
        self.assertNotIn("Bearbeiten", links)
        self.assertIn(OPEN_PAGE, links)

    def test_a_signed_in_user_may_edit(self) -> None:
        self.acid()
        links = texts_of_links(self.details("cinnamic-acid", True))
        self.assertEqual(links["Bearbeiten"],
                         f"{REGISTRY}substances/cinnamic-acid/edit/")


class TablesTests(SubstanceDetailsCase):

    def test_the_items_of_the_article(self) -> None:
        self.acid()
        small = self.item("CH-0012", size="10", unit="umol", quantity=5)
        large = self.item("CH-0012", size="1", unit="mg", quantity=2)
        found = self.details("cinnamic-acid")
        rows = rows_of(found, "items")
        hrefs = [row[0].find("a").get("href") for row in rows]
        self.assertCountEqual(hrefs, [item_url(small), item_url(large)])
        by_href = dict(zip(hrefs, rows))
        row = by_href[item_url(small)]
        self.assertIn("CH-0012", row[0].text())
        self.assertIn("10 µmol", row[0].text())
        self.assertIn("5", row[1].text())
        self.assertEqual(row[1].get("data-sort"), "5")

    def test_the_batches_newest_first_with_their_stock(self) -> None:
        self.acid()
        old = make_batch(self.kl, "CH-0012", number="KL-1",
                         date=date(2026, 1, 2))
        new = make_batch(self.kl, "CH-0012", number="KL-2",
                         date=date(2026, 3, 4))
        make_vessel(self.kl, new, unit="g", amount="2")
        make_vessel(self.kl, new, unit="mg", amount="500")
        make_vessel(self.kl, old, unit="mg", amount="0")
        rows = rows_of(self.details("cinnamic-acid"), "batches")
        self.assertEqual([row[0].find("a").get("href") for row in rows],
                         [batch_url(new), batch_url(old)])
        self.assertEqual(rows[0][1].text(), "04.03.2026")
        self.assertEqual(rows[0][1].get("data-sort"), "2026-03-04")
        self.assertIn("2 g", rows[0][2].text())
        self.assertIn("500 mg", rows[0][2].text())
        self.assertEqual(key_number(rows[0][2].get("data-sort")),
                         Decimal(2500))
        self.assertEqual(rows[1][2].text(), "–")

    def test_a_stock_of_amounts_of_substance_keys_on_micromoles(
            self) -> None:
        self.acid()
        batch = make_batch(self.kl, "CH-0012", number="KL-1")
        make_vessel(self.kl, batch, unit="umol", amount="20")
        (row,) = rows_of(self.details("cinnamic-acid"), "batches")
        self.assertEqual(key_number(row[2].get("data-sort")), Decimal(20))
        self.assertEqual(row[1].text(), "")
        self.assertFalse(ISO.match(row[1].get("data-sort") or ""))

    def test_the_tasks_with_their_state(self) -> None:
        self.acid()
        planned = make_task(self.kl, "cinnamic-acid")
        rows = rows_of(self.details("cinnamic-acid"), "tasks")
        self.assertEqual(
            [(row[0].find("a").get("href"), row[1].text())
             for row in rows],
            [(f"/lab/tasks/{planned.number}/", "Geplant")])

    def test_each_table_without_a_row_reads_none(self) -> None:
        """Scenario: Details of a bare substance."""
        make_substance("bare", "Bare")
        found = self.details("bare")
        self.assertEqual(found.find_all("table"), [])
        self.assertGreaterEqual(found.text().count("Keine"), 3)

    def test_a_table_without_a_row_reads_none_alone(self) -> None:
        self.acid()
        make_item(self.kl, "CH-0012", quantity=1)
        found = self.details("cinnamic-acid")
        self.assertIsNotNone(table_of(found, "items"))
        self.assertIsNone(table_of(found, "batches"))
        self.assertIsNone(table_of(found, "tasks"))
        self.assertEqual(found.text().count("Keine"), 2)

    def test_the_tables_sort_in_the_browser(self) -> None:
        self.acid()
        self.item("CH-0012")
        make_vessel(self.kl, make_batch(self.kl, "CH-0012", number="KL-1",
                                        date=date(2026, 1, 2)),
                    unit="mg", amount="5")
        make_task(self.kl, "cinnamic-acid")
        found = self.details("cinnamic-acid")
        self.assertEqual(len(found.find_all("table")), 3)
        self.assertEqual(unsorted_reasons(found), [])


class EndpointTests(SubstanceDetailsCase):
    """``/lab/registry/substances/<key>/detail/``."""

    def test_htmx_gets_the_pane_alone_without_a_sign_in(self) -> None:
        self.acid()
        response = self.client.get(detail_url("cinnamic-acid"), **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        found = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual([(e.get("id"), e.get("data-item")) for e in found],
                         [("item-detail", "cinnamic-acid")])

    def test_the_address_keeps_the_filters_of_the_page(self) -> None:
        self.acid()
        response = self.client.get(
            detail_url("cinnamic-acid"),
            **current(f"{REGISTRY}?q=zimt&sort=formula&dir=desc"
                      "&selected=other"))
        self.assertEqual(
            replaced(self, response),
            f"{REGISTRY}?q=zimt&sort=formula&dir=desc"
            "&selected=cinnamic-acid")

    def test_without_htmx_the_list_is_the_answer(self) -> None:
        self.acid()
        self.assertRedirects(
            self.client.get(detail_url("cinnamic-acid")),
            f"{REGISTRY}?selected=cinnamic-acid",
            fetch_redirect_response=False)

    def test_an_unknown_substance_is_not_found(self) -> None:
        self.acid()
        self.assertEqual(self.client.get(
            detail_url("cinnamic-acid"), **HTMX).status_code, 200)
        for extra in ({}, HTMX):
            self.assertEqual(
                self.client.get(detail_url("no-such-key"),
                                **extra).status_code, 404)

    def test_the_answer_varies_on_the_headers_it_reads(self) -> None:
        self.acid()
        response = self.client.get(detail_url("cinnamic-acid"), **HTMX)
        found = {name.strip().lower()
                 for name in response.get("Vary", "").split(",")}
        self.assertLessEqual({"hx-request", "hx-current-url"}, found)
