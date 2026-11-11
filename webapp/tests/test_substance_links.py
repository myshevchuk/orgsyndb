"""Tests of the substance links and the substance datalist (web-app:
Substance links)."""

import re

from django.test import TestCase

from inventory.models import Item
from tasks.models import Task

from . import (IndexMixin, build_index, context_form, datalist, make_item,
               make_lot, make_substance, make_task, make_user, page,
               substance_for, table, task_url)
from .demo_support import SeededCase
from .inventory_support import item_data

SUBSTANCE_PAGE = "/lab/registry/substances/cinnamic-acid/"
COMPOUND_PAGE = re.compile(r"/compounds/[^/]+/\Z")


class LinkCase(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")
        cls.known = make_task(cls.kl, substance="CH-0012")
        cls.other = make_task(cls.kl, substance="Neuverbindung 7")

    def setUp(self) -> None:
        self.use_index(None)

    def product_cells(self) -> dict:
        _, rows = table(page(self.client.get("/lab/tasks/")))
        return {(row["Nr."] if "Nr." in row else row["No."]).text():
                row["Produkt"] if "Produkt" in row else row["Product"]
                for row in rows}


class TaskLinkTests(LinkCase):

    def test_a_task_links_the_name_of_its_substance(self) -> None:
        cells = self.product_cells()
        known = cells[self.known.number]
        links = known.find_all("a")
        self.assertEqual([a.get("href") for a in links], [SUBSTANCE_PAGE])
        self.assertEqual(links[0].text(), "(E)-Zimtsäure")
        other = cells[self.other.number]
        self.assertEqual(
            [a.get("href") for a in other.find_all("a")],
            ["/lab/registry/substances/neuverbindung-7/"])

    def test_the_task_page(self) -> None:
        root = page(self.client.get(task_url(self.known)))
        self.assertIn("(E)-Zimtsäure", root.find("h1").text())
        hrefs = [a.get("href") for a in root.find_all("a")]
        self.assertIn(SUBSTANCE_PAGE, hrefs)
        self.assertFalse([h for h in hrefs if COMPOUND_PAGE.match(h)])

    def test_no_substance_is_marked_as_outside_the_collection(self) -> None:
        for language, mark in (("de", "nicht in der Sammlung"),
                               ("en", "not in the collection")):
            self.use_index(build_index(language))
            with self.subTest(language=language):
                for cell in self.product_cells().values():
                    self.assertNotIn(mark, cell.text())

    def test_the_name_follows_the_language_of_the_site(self) -> None:
        self.use_index(build_index("en"))
        cells = {row["No."].text(): row["Product"] for row in
                 table(page(self.client.get("/lab/tasks/")))[1]}
        known = cells[self.known.number]
        self.assertEqual([a.text() for a in known.find_all("a")],
                         ["(E)-Cinnamic acid"])

    def test_the_link_does_not_depend_on_the_index(self) -> None:
        for index in (None, build_index("de")):
            self.use_index(index)
            with self.subTest(index=index is None):
                known = self.product_cells()[self.known.number]
                self.assertEqual(
                    [a.get("href") for a in known.find_all("a")],
                    [SUBSTANCE_PAGE])


class InventoryLinkTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")

    def setUp(self) -> None:
        self.use_index(None)

    def test_the_item_page_the_lot_page_and_the_bulk_list(self) -> None:
        item = make_item(self.kl, "CH-0012")
        lot = make_lot(self.kl, "CH-0012", batch="B-1")
        for path in (f"/lab/inventory/items/{item.pk}/",
                     f"/lab/inventory/bulk/{lot.pk}/",
                     "/lab/inventory/end-products/bulk/",
                     "/lab/inventory/end-products/"):
            with self.subTest(path=path):
                root = page(self.client.get(path))
                hrefs = [a.get("href") for a in root.find_all("a")]
                self.assertIn(SUBSTANCE_PAGE, hrefs)
                self.assertFalse([h for h in hrefs
                                  if COMPOUND_PAGE.match(h)])


class DatalistTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")
        substance_for("CH-0012")
        make_substance("acetophenone", "Acetophenone")

    def setUp(self) -> None:
        self.use_index(None)
        self.client.force_login(self.kl)

    def options(self, path: str) -> dict[str, str]:
        return datalist(page(self.client.get(path)), "substance")

    def test_every_substance_is_offered_by_key_with_its_name(self) -> None:
        for path in ("/lab/tasks/new/", "/lab/inventory/end-products/new/",
                     "/lab/inventory/bulk/new/"):
            with self.subTest(path=path):
                self.assertEqual(self.options(path), {
                    "cinnamic-acid": "(E)-Zimtsäure",
                    "acetophenone": "Acetophenone"})

    def test_the_edit_form_of_a_task_offers_them_too(self) -> None:
        task = make_task(self.kl, substance="CH-0012")
        self.assertEqual(self.options(task_url(task, "edit")), {
            "cinnamic-acid": "(E)-Zimtsäure",
            "acetophenone": "Acetophenone"})

    def test_labels_are_in_the_language_of_the_site(self) -> None:
        self.use_index(build_index("en"))
        self.assertEqual(self.options("/lab/tasks/new/"), {
            "cinnamic-acid": "(E)-Cinnamic acid",
            "acetophenone": "Acetophenone"})

    def test_a_new_substance_is_offered_at_once(self) -> None:
        make_substance("added", "Added")
        self.assertIn("added", self.options("/lab/tasks/new/"))

    def test_an_unknown_key_is_an_error_at_the_field(self) -> None:
        response = self.client.post(
            "/lab/inventory/end-products/new/",
            item_data(substance="no-such-substance"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("substance", context_form(response).errors)
        self.assertEqual(Item.objects.count(), 0)


class DemoLinkTests(SeededCase):

    def test_a_tasks_substance(self) -> None:
        """Scenario: A task's substance."""
        _, rows = table(self.get("/lab/tasks/?state=all"))
        cinnamic = [row for row in rows
                    if row["Produkt"].find("a") is not None
                    and row["Produkt"].find("a").get("href")
                    == SUBSTANCE_PAGE]
        self.assertTrue(cinnamic)
        self.assertEqual(
            len(cinnamic),
            Task.objects.filter(substance__key="cinnamic-acid").count())
        for row in cinnamic:
            self.assertEqual(row["Produkt"].find("a").text(),
                             "(E)-Zimtsäure")
