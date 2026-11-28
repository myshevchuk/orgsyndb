"""Tests of items whose article has no article number
(end-product-inventory: Items, Delivery notes, Consumption, Item list,
Item page, Inventory forms, Inventory in the admin)."""

from datetime import date
from typing import Any

from inventory.bookings import Refused, book_note
from inventory.models import Article, EnteredConsumption, Item

from . import (datalist, field_value, make_article, make_item, make_substance,
               make_user, make_vessel, page, table)
from .collection_support import accept
from .inventory_support import (DELIVERIES, LIST, MICRO, NEW_BATCH, NEW_ITEM,
                                NEW_NOTE, SUBSTANCE_PAGE, FormCase,
                                InventoryCase, fresh, has_amount,
                                has_number, historical_line, item_data,
                                item_url, note_data, snapshot)
from .main_lists_support import must_pane

ADMIN_ITEMS = "/lab/admin/inventory/item/"
ADMIN_ARTICLES = "/lab/admin/inventory/article/"


def numberless(user: Any, name: str = "Neuverbindung 9", size: str = "10",
               unit: str = "mg", quantity: int = 4) -> Item:
    """An item of an article without an article number, of the
    substance that ``substance_for`` makes of ``name``."""
    return make_item(user, None, name, size, unit, quantity)


def edit_data(item: Item, **over: str) -> dict[str, str]:
    """The edit form's fields as the item stands: the article's
    category, the article number left out, and the item's own fields."""
    data = {"category": item.article.category, "note": item.note,
            "status": item.status, "compartment": item.compartment,
            "box": item.box,
            "stocked_on": item.stocked_on.isoformat()
            if item.stocked_on else ""}
    data.update(over)
    return data


class ItemTests(InventoryCase):

    def test_two_articles_without_a_number_may_share_a_size(self) -> None:
        first = numberless(self.kl)
        second = numberless(self.kl, "Brücke 3")
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(Article.objects.filter(
            article_number__isnull=True).count(), 2)

    def test_shown_as_container_and_name(self) -> None:
        self.assertEqual(str(numberless(self.kl)), "10 mg Neuverbindung 9")
        self.assertEqual(str(self.item("CH-0012", "Zimtsäure")),
                         "CH-0012 10 µmol Zimtsäure")

    def test_a_delivery_line_is_refused(self) -> None:
        """Scenario: First delivery needs the article number."""
        item = numberless(self.kl)
        lines = [historical_line(item, 2)]
        before = snapshot()
        for historical in (False, True):
            with self.subTest(historical=historical), \
                    self.assertRaises(Refused) as refused:
                book_note(self.kl, date=date(2026, 3, 12), lines=lines,
                          historical=historical)
            self.assertEqual(refused.exception.line, 0)
        self.assertUnchanged(before)
        self.assertEqual(fresh(item).quantity, 4)

    def test_an_entered_value_is_refused_zero_included(self) -> None:
        item = numberless(self.kl)
        for count in (3, 0):
            with self.subTest(count=count), self.assertRaises(Refused):
                self.enter(item, 2026, 2, count)
        self.assertFalse(EnteredConsumption.objects.filter(
            item=item).exists())

    def test_a_delivery_line_of_a_numbered_article_is_booked(self) -> None:
        item = self.item("CH-0012", quantity=5)
        self.deliver(item, 2)
        self.assertEqual(fresh(item).quantity, 3)

    def test_an_article_given_a_number_can_be_delivered(self) -> None:
        item = numberless(self.kl, quantity=5)
        make_article(item.article.substance, "CH-0021")
        self.assertEqual(fresh(item).article.article_number, "CH-0021")
        self.deliver(item, 2)
        self.assertEqual(fresh(item).quantity, 3)

    def test_the_vessels_of_its_substance_are_its_bulk(self) -> None:
        item = numberless(self.kl, size="10", unit="mg")
        make_vessel(self.kl, substance=item.article.substance, amount="50")
        make_vessel(self.kl, article="CH-0012", amount="90")
        header, rows = table(page(self.client.get(LIST)))
        cell = next(r for r in rows
                    if r["Name"].text() == "Neuverbindung 9")[
                        "Bulk verfügbar"]
        self.assertTrue(has_amount(cell.text(), "50", "mg"), cell.text())
        self.assertNotIn("90", cell.text())


class EditTests(FormCase):

    def test_a_number_is_entered_once(self) -> None:
        """Scenario: Article number entered once."""
        item = numberless(self.kl)
        response = self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(item).article.article_number, "CH-0021")
        article = fresh(item).article
        changed = [record.diff_against(record.prev_record).changed_fields
                   for record in article.history.all()
                   if record.prev_record is not None]
        self.assertIn(["article_number"], changed)
        self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0022"))
        self.assertEqual(fresh(item).article.article_number, "CH-0021")

    def test_the_field_shows_only_while_there_is_none(self) -> None:
        item = numberless(self.kl)
        numbered = self.item("CH-0012")
        self.assertEqual(field_value(page(self.client.get(
            item_url(item, "edit"))), "article_number"), "")
        self.assertIsNone(field_value(page(self.client.get(
            item_url(numbered, "edit"))), "article_number"))

    def test_a_number_taken_is_refused(self) -> None:
        """Scenario: Article number taken."""
        self.item("CH-0012", size="10", unit="umol")
        item = numberless(self.kl, size="10", unit="umol")
        response = self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0012"))
        self.refused(response, "article_number")
        self.assertIsNone(fresh(item).article.article_number)

    def test_one_number_for_every_size(self) -> None:
        """Scenario: One number for every size."""
        first = numberless(self.kl, size="10", unit="umol")
        second = make_item(self.kl, None, "Neuverbindung 9", "50", "umol",
                           substance=first.article.substance)
        self.client.post(item_url(first, "edit"), edit_data(
            first, article_number="CH-0021"))
        for item in (first, second):
            with self.subTest(item=item.pk):
                self.assertEqual(fresh(item).article.article_number,
                                 "CH-0021")
        _, rows = table(page(self.client.get(LIST)))
        self.assertEqual([row["Artikelnr."].text() for row in rows],
                         ["CH-0021", "CH-0021"])

    def test_left_empty_the_item_keeps_none(self) -> None:
        item = numberless(self.kl)
        self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="", note="geprüft"))
        stored = fresh(item)
        self.assertIsNone(stored.article.article_number)
        self.assertEqual(stored.note, "geprüft")

    def test_a_new_item_without_a_number(self) -> None:
        """Scenario: New item without an article number."""
        make_substance("new-compound-9", "Neuverbindung 9")
        response = self.client.post(NEW_ITEM, item_data(
            substance="new-compound-9", article_number="", size="10",
            unit="mg", quantity="4"))
        item = Item.objects.get()
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)
        self.assertEqual(item.article.substance.key, "new-compound-9")
        self.assertIsNone(item.article.article_number)
        self.assertEqual(item.quantity, 4)


class NoteFormTests(FormCase):

    def test_rows_offer_only_items_with_a_number(self) -> None:
        numbered = self.item("CH-0012")
        item = numberless(self.kl)
        select = page(self.client.get(NEW_NOTE)).find("select",
                                                      name="item_0")
        offered = {option.get("value") for option in
                   select.find_all("option")}
        self.assertIn(str(numbered.pk), offered)
        self.assertNotIn(str(item.pk), offered)

    def test_the_delivery_filter_leaves_them_out(self) -> None:
        numbered = self.item("CH-0012")
        item = numberless(self.kl)
        select = page(self.client.get(DELIVERIES)).find("select",
                                                        name="item")
        offered = {option.get("value") for option in
                   select.find_all("option")}
        self.assertIn(str(numbered.pk), offered)
        self.assertNotIn(str(item.pk), offered)

    def test_a_posted_line_is_refused(self) -> None:
        item = numberless(self.kl, quantity=5)
        data = note_data((item, 2))
        before = snapshot()
        response = self.client.post(NEW_NOTE, data)
        self.refused(response, "item_0")
        self.assertUnchanged(before)

    def test_the_consumption_form_refuses(self) -> None:
        item = numberless(self.kl)
        for count in ("3", "0"):
            with self.subTest(count=count):
                response = self.client.post(
                    item_url(item, "consumption"),
                    {"year": "2026", "quarter": "2", "count": count})
                self.refused(response)
        self.assertFalse(EnteredConsumption.objects.filter(
            item=item).exists())


class DatalistTests(FormCase):

    def test_keys_labelled_with_names(self) -> None:
        """Scenario: Substances offered."""
        make_substance("no-article", "No article")
        for path in (NEW_ITEM, NEW_BATCH):
            with self.subTest(path=path):
                options = datalist(page(self.client.get(path)),
                                   "substance")
                self.assertEqual(options.get("cinnamic-acid"),
                                 "(E)-Zimtsäure")
                self.assertEqual(options.get("no-article"), "No article")
                self.assertNotIn("CH-0012", options)

    def test_the_task_form_offers_the_substances_too(self) -> None:
        root = page(self.client.get("/lab/tasks/new/"))
        options = datalist(root, "substance")
        self.assertEqual(options.get("cinnamic-acid"), "(E)-Zimtsäure")
        self.assertNotIn("CH-0012", options)

    def test_the_edit_form_names_no_substance(self) -> None:
        item = numberless(self.kl)
        root = page(self.client.get(item_url(item, "edit")))
        self.assertIsNone(root.find("input", name="substance"))


class ListTests(InventoryCase):

    def test_items_without_a_number_come_last_by_name(self) -> None:
        self.item("CH-0012", "Zimtsäure")
        late = numberless(self.kl, "Neuverbindung 9")
        self.item("CH-0001", "Bromphenylethanol")
        early = numberless(self.kl, "Brücke 3")
        header, rows = table(page(self.client.get(LIST)))
        self.assertEqual([row[header[1]].text() for row in rows],
                         ["Bromphenylethanol", "Zimtsäure", "Brücke 3",
                          "Neuverbindung 9"])
        self.assertEqual([row[header[0]].text() for row in rows][2:],
                         ["", ""])
        for row, item in zip(rows[2:], (early, late)):
            self.assertEqual(row[header[1]].find("a").get("href"),
                             item_url(item))

    def test_a_numbered_name_links_its_substance(self) -> None:
        self.item("CH-0012", "Zimtsäure")
        header, rows = table(page(self.client.get(LIST)))
        self.assertRegex(rows[0][header[1]].find("a").get("href"),
                         SUBSTANCE_PAGE)

    def test_the_search_finds_them_by_name(self) -> None:
        numberless(self.kl, "Neuverbindung 9")
        self.item("CH-0012", "Zimtsäure")
        header, rows = table(page(self.client.get(LIST + "?q=neuverb")))
        self.assertEqual([row[header[1]].text() for row in rows],
                         ["Neuverbindung 9"])


class PageTests(FormCase):

    def test_page_of_a_position_without_a_number(self) -> None:
        """Scenario: Page of a position without an article number."""
        substance = make_substance("new-compound-9", "Neuverbindung 9")
        item = make_item(self.kl, None, size="10", unit="mg", quantity=4,
                         substance=substance)
        root = page(self.client.get(item_url(item)))
        self.assertEqual(root.find("h1").text(), "Neuverbindung 9")
        self.assertIn("/lab/registry/substances/new-compound-9/",
                      [a.get("href") for a in root.find_all("a")])
        links = {a.text(): a.get("href") for a in
                 root.find("div", "lab-actions").find_all("a")}
        self.assertEqual(links.get("Artikelnr. eintragen"),
                         item_url(item, "edit"))
        self.assertNotIn("Abgabe buchen", links)
        self.assertNotIn("Verbrauch nachtragen", links)
        self.assertIn("Abfüllen", links)
        self.assertFalse([a for a in root.find_all("a") if a.get(
            "href", "").startswith("/lab/inventory/batches/new/")])

    def test_a_numbered_page_keeps_its_links(self) -> None:
        item = self.item("CH-0012", "Zimtsäure")
        root = page(self.client.get(item_url(item)))
        self.assertEqual(root.find("h1").text(),
                         "CH-0012 · (E)-Zimtsäure")
        links = [a.text() for a in
                 root.find("div", "lab-actions").find_all("a")]
        self.assertIn("Abgabe buchen", links)
        self.assertNotIn("Artikelnr. eintragen", links)


class AdminTests(InventoryCase):
    """The article number in the admin, entered through an item's
    article (end-product-inventory: Inventory in the admin)."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(make_user("boss", "BO", is_staff=True,
                                          is_superuser=True))

    def change(self, item: Item) -> str:
        return f"{ADMIN_ARTICLES}{item.article.pk}/change/"

    def names(self, item: Item) -> set[str]:
        return {e.get("name") for e in page(self.client.get(
            self.change(item))).find_all("input")}

    def test_article_number_in_the_admin(self) -> None:
        """Scenario: Article number in the admin."""
        item = numberless(self.kl)
        numbered = self.item("CH-0012")
        self.assertIn("article_number", self.names(item))
        self.assertNotIn("article_number", self.names(numbered))
        self.assertIn("CH-0012", self.client.get(
            self.change(numbered)).content.decode("utf-8"))

    def test_a_number_entered_in_the_admin(self) -> None:
        item = numberless(self.kl)
        self.client.post(self.change(item), {
            "category": "", "article_number": "CH-0021"})
        self.assertEqual(fresh(item).article.article_number, "CH-0021")

    def test_a_stale_change_page_keeps_the_number(self) -> None:
        """Scenario: A stale change page keeps the number."""
        from django.test import Client
        item = numberless(self.kl)
        self.assertEqual(self.client.get(
            self.change(item)).status_code, 200)
        other = Client()
        other.force_login(self.kl)
        other.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        self.client.post(self.change(item), {
            "category": "Neu", "article_number": ""})
        stored = fresh(item).article
        self.assertEqual((stored.article_number, stored.category),
                         ("CH-0021", "Neu"))

    def test_a_number_taken_refuses_the_whole_change(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        item = numberless(self.kl, size="10", unit="umol")
        response = self.client.post(self.change(item), {
            "category": "Neu", "article_number": "CH-0012"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("article_number",
                      response.context["adminform"].form.errors)
        stored = fresh(item).article
        self.assertEqual((stored.article_number, stored.category),
                         (None, ""))

    def test_a_number_entered_twice_keeps_the_first(self) -> None:
        from django.test import Client
        item = numberless(self.kl)
        other = Client()
        other.force_login(self.kl)
        other.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        self.client.post(self.change(item), {
            "category": "", "article_number": "CH-0022"})
        self.assertEqual(fresh(item).article.article_number, "CH-0021")


class BulkOfAnItemTests(InventoryCase):
    """Requirement: Filling from bulk (an item's bulk is the amount in
    the open vessels of its substance, flasks among them), here in the
    list's column, the selected item's details and the item page.

    The list's cell shows the amount by unit alone; the number of
    containers the bulk would fill shows in the details and on the item
    page."""

    def bulk_cells(self) -> dict[str, object]:
        header, rows = table(page(self.client.get(LIST)))
        return {f"{row[header[0]].text()} "
                f"{row['Gebinde'].text().replace(' ', '')}":
                row["Bulk verfügbar"]
                for row in rows}

    def details(self, item: Any) -> str:
        """The text of the details the list holds with ITEM selected."""
        root = page(self.client.get(f"{LIST}?selected={item.pk}"))
        return must_pane(root).text()

    def assertFills(self, text: str, count: str) -> None:
        """TEXT names COUNT containers, as `33 Gebinde` or `Gebinde: 33`
        do."""
        self.assertRegex(
            text, rf"(?<![\d,.]){count}\s*Gebinde|"
                  rf"Gebinde\W{{0,3}}{count}(?![\d,.])")

    def test_containers_from_bulk(self) -> None:
        """Scenario: Containers from bulk."""
        item = self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50")
        cell = self.bulk_cells()[f"CH-0012 10{MICRO}mol"]
        self.assertTrue(has_amount(cell.text(), "50", "mg"), cell.text())
        self.assertFills(self.details(item), "33")

    def test_the_cell_shows_the_amount_and_no_count(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50")
        text = self.bulk_cells()[f"CH-0012 10{MICRO}mol"].text()
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertNotIn("→", text)
        self.assertNotIn("Gebinde", text)
        self.assertFalse(has_number(text, "33"), text)

    def test_the_english_cell_shows_no_count_either(self) -> None:
        accept(language="en")
        self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50")
        header, rows = table(page(self.client.get(LIST)))
        text = rows[0]["Bulk available"].text()
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertNotIn("→", text)
        self.assertNotIn("container", text)
        self.assertFalse(has_number(text, "33"), text)

    def test_vessels_are_not_pooled(self) -> None:
        """Scenario: Vessels are not pooled."""
        item = self.item("X-1", size="10", unit="mg")
        self.vessel("X-1", "mg", "6")
        self.vessel("X-1", "mg", "6")
        cell = self.bulk_cells()["X-1 10mg"]
        self.assertTrue(has_amount(cell.text(), "12", "mg"), cell.text())
        self.assertFills(self.details(item), "0")

    def test_a_flask_counts_like_any_open_vessel(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50", flask=True)
        cell = self.bulk_cells()[f"CH-0012 10{MICRO}mol"]
        self.assertTrue(has_amount(cell.text(), "50", "mg"), cell.text())
        self.assertFills(self.details(item), "33")

    def test_the_vessels_of_several_batches_add_up_in_the_amount(
            self) -> None:
        item = self.item("X-1", size="10", unit="mg")
        self.vessel("X-1", "mg", "25", flask=True)
        self.vessel("X-1", "mg", "25", location="Regal")
        cell = self.bulk_cells()["X-1 10mg"]
        self.assertTrue(has_amount(cell.text(), "50", "mg"), cell.text())
        self.assertFills(self.details(item), "4")

    def test_the_division_is_exact(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "148.16")
        self.assertFills(self.details(item), "100")

    def test_each_size_counts_its_own_containers(self) -> None:
        small = self.item("CH-0012", size="10", unit="umol")
        large = self.item("CH-0012", size="50", unit="umol")
        self.vessel("CH-0012", "mg", "50")
        self.assertFills(self.details(small), "33")
        self.assertFills(self.details(large), "6")

    def test_the_amount_is_shown_by_unit(self) -> None:
        item = self.item("X-1", size="10", unit="mg")
        self.vessel("X-1", "mg", "50")
        self.vessel("X-1", "g", "1")
        text = self.bulk_cells()["X-1 10mg"].text()
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertTrue(has_amount(text, "1", "g"), text)
        self.assertFalse(has_number(text, "105"), text)
        self.assertFills(self.details(item), "105")

    def test_a_vessel_that_does_not_convert_is_left_out(self) -> None:
        item = self.item("X-9", size="10", unit="umol")
        self.vessel("X-9", "umol", "35")
        self.vessel("X-9", "mg", "500")
        text = self.bulk_cells()[f"X-9 10{MICRO}mol"].text()
        self.assertTrue(has_amount(text, "35", MICRO + "mol"), text)
        self.assertTrue(has_amount(text, "500", "mg"), text)
        self.assertFills(self.details(item), "3")

    def test_used_up_vessels_and_other_articles_are_left_out(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.vessel("X-1", "mg", "0")
        self.vessel("X-2", "mg", "90")
        text = self.bulk_cells()["X-1 10mg"].text()
        self.assertNotIn("90", text)
        self.assertNotIn("mg", text)

    def test_an_item_without_vessels_shows_no_bulk(self) -> None:
        self.item("X-1", size="10", unit="mg")
        self.assertNotIn("mg", self.bulk_cells()["X-1 10mg"].text())

    def test_the_item_page_shows_the_open_vessels(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50", number="B-7")
        self.vessel("CH-0012", "mg", "0", number="B-USED")
        self.vessel("CH-0013", "mg", "20", number="B-OTHER")
        text = page(self.client.get(item_url(item))).text()
        self.assertIn("B-7", text)
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertFills(text, "33")
        self.assertNotIn("B-USED", text)
        self.assertNotIn("B-OTHER", text)

    def test_the_item_page_names_a_flask_and_a_stored_vessel(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50", number="B-7", flask=True)
        self.vessel("CH-0012", "mg", "20", number="B-8", location="Regal 3")
        text = page(self.client.get(item_url(item))).text()
        for shown in ("B-7", "B-8", "Regal 3"):
            self.assertIn(shown, text)

    def test_a_vessel_belongs_to_every_size_of_its_article(self) -> None:
        small = self.item("CH-0012", size="10", unit="umol")
        large = self.item("CH-0012", size="50", unit="umol")
        self.vessel("CH-0012", "mg", "50", number="B-7")
        for item in (small, large):
            with self.subTest(item=item.pk):
                self.assertIn("B-7", page(self.client.get(
                    item_url(item))).text())

    def test_made_and_bought_vessels_side_by_side(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol")
        self.vessel("CH-0012", "mg", "50", source="made", number="M-1")
        self.vessel("CH-0012", "mg", "20", source="bought",
                    supplier="Sigma", supplier_batch="S-1")
        text = page(self.client.get(item_url(item))).text()
        self.assertTrue(has_amount(text, "50", "mg"), text)
        self.assertTrue(has_amount(text, "20", "mg"), text)
