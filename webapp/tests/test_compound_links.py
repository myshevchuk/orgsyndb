"""Tests of compound links and the compound datalist (web-app: Compound
links)."""

import re

from django.test import TestCase

from . import (NOT_IN_COLLECTION, IndexMixin, build_index, compound,
               demo_data, demo_index, make_task, make_user, page, table,
               task_url, text_field)

# A compound's own page; the site's /compounds/ section link is not one.
COMPOUND_PAGE = re.compile(r"/compounds/[^/]+/\Z")


class LinkCase(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")
        cls.known = make_task(cls.kl, product="CH-0012")
        cls.unknown = make_task(cls.kl, product="Neuverbindung 7")

    def product_cells(self) -> dict:
        _, rows = table(page(self.client.get("/lab/tasks/")))
        return {row["Nr."].text(): row["Produkt"] if "Produkt" in row
                else row["Product"] for row in rows}


class ProductLinkTests(LinkCase):

    def setUp(self) -> None:
        self.use_index(demo_index())

    def test_known_and_unknown_products_in_the_list(self) -> None:
        """Scenario: Known and unknown products."""
        cells = self.product_cells()
        known = cells[self.known.number]
        links = known.find_all("a")
        self.assertEqual([a.get("href") for a in links],
                         ["/compounds/cinnamic-acid/"])
        self.assertEqual(links[0].text(), "(E)-Zimtsäure")
        self.assertNotIn(NOT_IN_COLLECTION["de"], known.text())
        unknown = cells[self.unknown.number]
        self.assertIn("Neuverbindung 7", unknown.text())
        self.assertIn(NOT_IN_COLLECTION["de"], unknown.text())
        self.assertEqual(unknown.find_all("a"), [])

    def test_known_and_unknown_products_on_the_task_page(self) -> None:
        root = page(self.client.get(task_url(self.known)))
        heading = root.find("h1")
        self.assertIn("(E)-Zimtsäure", heading.text())
        self.assertEqual(
            [a.get("href") for a in root.find_all("a")
             if COMPOUND_PAGE.match(a.get("href", ""))],
            ["/compounds/cinnamic-acid/"])
        root = page(self.client.get(task_url(self.unknown)))
        self.assertIn("Neuverbindung 7", root.find("h1").text())
        self.assertIn(NOT_IN_COLLECTION["de"], root.text())
        self.assertEqual(
            [a for a in root.find_all("a")
             if COMPOUND_PAGE.match(a.get("href", ""))], [])

    def test_a_product_named_by_key_is_linked(self) -> None:
        make_task(self.kl, product="cinnamic-acid")
        links = [a for cell in self.product_cells().values()
                 for a in cell.find_all("a")
                 if a.get("href") == "/compounds/cinnamic-acid/"]
        self.assertEqual(len(links), 2)


class MarkTests(LinkCase):

    def test_without_an_index_every_product_shows_as_entered(self) -> None:
        self.use_index(None)
        for number, cell in self.product_cells().items():
            with self.subTest(number=number):
                self.assertEqual(cell.find_all("a"), [])
                self.assertIn(NOT_IN_COLLECTION["de"], cell.text())
        self.assertIn("CH-0012",
                      self.product_cells()[self.known.number].text())

    def test_english_mark_and_name(self) -> None:
        self.use_index(build_index("en", [
            compound("cinnamic-acid", name="(E)-Cinnamic acid",
                     name_de="(E)-Zimtsäure", item_number="CH-0012")]))
        cells = {row["No."].text(): row["Product"] for row in
                 table(page(self.client.get("/lab/tasks/")))[1]}
        known = cells[self.known.number]
        self.assertEqual([a.text() for a in known.find_all("a")],
                         ["(E)-Cinnamic acid"])
        unknown = cells[self.unknown.number]
        self.assertIn(NOT_IN_COLLECTION["en"], unknown.text())
        self.assertEqual(unknown.find_all("a"), [])

    def test_an_ambiguous_identifier_finds_no_compound(self) -> None:
        self.use_index(build_index("de", [
            compound("c", name="Cee", item_number="X-1"),
            compound("d", name="Dee", catalogue="X-1")],
            fields=[text_field("item_number"), text_field("catalogue")]))
        task = make_task(self.kl, product="X-1")
        cell = self.product_cells()[task.number]
        self.assertEqual(cell.find_all("a"), [])
        self.assertIn(NOT_IN_COLLECTION["de"], cell.text())


class DatalistTests(LinkCase):

    def options(self, path: str = "/lab/tasks/new/") -> dict[str, str]:
        self.client.force_login(self.kl)
        root = page(self.client.get(path))
        field = root.find("input", name="product")
        self.assertIsNotNone(field)
        listed = field.get("list")
        self.assertTrue(listed, "the product input names no datalist")
        datalist = root.find("datalist", id=listed)
        self.assertIsNotNone(datalist)
        return {o.get("value"): o.get("label") or o.text()
                for o in datalist.find_all("option")}

    def test_each_identifier_of_each_compound_is_offered(self) -> None:
        self.use_index(demo_index())
        options = self.options()
        for entry in demo_data()["compounds"]:
            data = entry["data"]
            for identifier in (entry["key"], data["item_number"]):
                with self.subTest(identifier=identifier):
                    self.assertEqual(options[identifier], data["name_de"])
        self.assertEqual(len(options), 2 * len(demo_data()["compounds"]))

    def test_the_edit_form_offers_them_too(self) -> None:
        self.use_index(demo_index())
        options = self.options(task_url(self.known, "edit"))
        self.assertEqual(options["CH-0012"], "(E)-Zimtsäure")

    def test_labels_are_in_the_language_of_the_site(self) -> None:
        self.use_index(build_index("en", [
            compound("cinnamic-acid", name="(E)-Cinnamic acid",
                     name_de="(E)-Zimtsäure", item_number="CH-0012")]))
        self.assertEqual(self.options(),
                         {"cinnamic-acid": "(E)-Cinnamic acid",
                          "CH-0012": "(E)-Cinnamic acid"})

    def test_without_an_index_the_datalist_is_empty(self) -> None:
        self.use_index(None)
        self.client.force_login(self.kl)
        root = page(self.client.get("/lab/tasks/new/"))
        field = root.find("input", name="product")
        self.assertIsNotNone(field)
        listed = field.get("list")
        datalist = root.find("datalist", id=listed) if listed else None
        self.assertTrue(datalist is None or not datalist.find_all("option"))
