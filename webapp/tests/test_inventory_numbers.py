"""Tests of items without an article number (end-product-inventory:
Items, Delivery notes, Consumption, Item list, Item page, Inventory forms
and Inventory in the admin; production-planning: Matching tasks and
articles)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import Refused, book_note, create_item
from inventory.models import EnteredConsumption, Item

from . import field_value, make_item, make_task, make_user, page, table
from .inventory_support import (COMPOUND_PAGE, DELIVERIES, LIST, NEW_ITEM,
                                NEW_LOT, NEW_NOTE, TODAY, FormCase,
                                InventoryCase, fresh, item_url, note_data,
                                snapshot)

ADMIN_ITEMS = "/lab/admin/inventory/item/"


def numberless(user, name: str = "Neuverbindung 9", size: str = "10",
               unit: str = "mg", quantity: int = 4) -> Item:
    return make_item(user, None, name, size, unit, quantity)


def edit_data(item: Item, **over: str) -> dict[str, str]:
    data = {"name": item.name, "category": item.category,
            "note": item.note, "status": item.status,
            "stocked_on": item.stocked_on.isoformat()
            if item.stocked_on else ""}
    data.update(over)
    return data


def datalist(root, ident: str) -> dict[str, str]:
    """The options of the ``datalist`` ``ident``, value to label."""
    found = root.find("datalist", id=ident)
    if found is None:
        return {}
    return {option.get("value"): option.get("label", "")
            for option in found.find_all("option")}


class ItemTests(InventoryCase):

    def test_two_items_without_a_number_of_one_size(self) -> None:
        first = numberless(self.kl)
        second = numberless(self.kl)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(Item.objects.filter(
            article_number__isnull=True).count(), 2)

    def test_an_empty_number_is_none(self) -> None:
        item = create_item(self.kl, article_number="", name="Probe",
                           size=Decimal("10"), unit="mg", quantity=1)
        self.assertIsNone(fresh(item).article_number)

    def test_shown_as_container_and_name(self) -> None:
        self.assertEqual(str(numberless(self.kl)), "10 mg Neuverbindung 9")
        self.assertEqual(str(self.item("CH-0012", "Zimtsäure")),
                         "CH-0012 10 µmol Zimtsäure")

    def test_a_delivery_line_is_refused(self) -> None:
        item = numberless(self.kl)
        before = snapshot()
        for historical in (False, True):
            with self.subTest(historical=historical), \
                    self.assertRaises(Refused) as refused:
                book_note(self.kl, date=date(2026, 3, 12),
                          lines=[(item, 2)], historical=historical)
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

    def test_no_compound_and_no_lots(self) -> None:
        from inventory.figures import bulk
        from inventory.models import Lot
        item = numberless(self.kl)
        self.lot("CH-0012")
        self.assertEqual(bulk(item, Lot.objects.all()).lots, [])


class EditTests(FormCase):

    def test_a_number_is_entered_once(self) -> None:
        item = numberless(self.kl)
        response = self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(item).article_number, "CH-0021")
        changed = [record.diff_against(record.prev_record).changed_fields
                   for record in fresh(item).history.all()
                   if record.prev_record is not None]
        self.assertIn(["article_number"], changed)
        self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0022"))
        self.assertEqual(fresh(item).article_number, "CH-0021")

    def test_the_page_history_shows_the_number(self) -> None:
        item = numberless(self.kl)
        self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        history = page(self.client.get(item_url(item))).find(
            "ul", "lab-history")
        self.assertIn("Artikelnr.", history.text())
        self.assertIn("CH-0021", history.text())

    def test_the_field_shows_only_while_there_is_none(self) -> None:
        item = numberless(self.kl)
        numbered = self.item("CH-0012")
        self.assertEqual(field_value(page(self.client.get(
            item_url(item, "edit"))), "article_number"), "")
        self.assertIsNone(field_value(page(self.client.get(
            item_url(numbered, "edit"))), "article_number"))

    def test_a_number_taken_is_refused(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        item = numberless(self.kl, size="10", unit="umol")
        response = self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0012"))
        self.refused(response, "article_number")
        self.assertIsNone(fresh(item).article_number)

    def test_another_size_of_the_article_is_fine(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        item = numberless(self.kl, size="50", unit="umol")
        self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0012"))
        self.assertEqual(fresh(item).article_number, "CH-0012")

    def test_left_empty_the_item_keeps_none(self) -> None:
        item = numberless(self.kl)
        self.client.post(item_url(item, "edit"), edit_data(
            item, article_number="", note="geprüft"))
        stored = fresh(item)
        self.assertIsNone(stored.article_number)
        self.assertEqual(stored.note, "geprüft")

    def test_new_item_without_a_number(self) -> None:
        response = self.client.post(NEW_ITEM, {
            "article_number": "", "name": "Neuverbindung 9",
            "category": "", "size": "10", "unit": "mg", "quantity": "4",
            "note": ""})
        item = Item.objects.get(name="Neuverbindung 9")
        self.assertRedirects(response, item_url(item),
                             fetch_redirect_response=False)
        self.assertIsNone(item.article_number)
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
        before = snapshot()
        response = self.client.post(NEW_NOTE, note_data((item, 2)))
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

    def test_numbers_and_not_keys(self) -> None:
        for path in (NEW_ITEM, NEW_LOT):
            with self.subTest(path=path):
                root = page(self.client.get(path))
                control = root.find("input", name="article_number")
                options = datalist(root, control.get("list"))
                self.assertEqual(options.get("CH-0012"), "(E)-Zimtsäure")
                self.assertNotIn("cinnamic-acid", options)
                self.assertNotIn("1-phenylethanol", options)

    def test_the_edit_form_offers_the_numbers(self) -> None:
        item = numberless(self.kl)
        root = page(self.client.get(item_url(item, "edit")))
        control = root.find("input", name="article_number")
        self.assertIn("CH-0012", datalist(root, control.get("list")))

    def test_the_task_form_keeps_every_identifier(self) -> None:
        root = page(self.client.get("/lab/tasks/new/"))
        control = root.find("input", name="product")
        options = datalist(root, control.get("list"))
        self.assertIn("cinnamic-acid", options)
        self.assertIn("CH-0012", options)


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

    def test_a_numbered_name_still_links_its_compound(self) -> None:
        self.item("CH-0012", "Zimtsäure")
        header, rows = table(page(self.client.get(LIST)))
        self.assertRegex(rows[0][header[1]].find("a").get("href"),
                         COMPOUND_PAGE)

    def test_the_search_finds_them_by_name(self) -> None:
        numberless(self.kl, "Neuverbindung 9")
        self.item("CH-0012", "Zimtsäure")
        header, rows = table(page(self.client.get(LIST + "?q=neuverb")))
        self.assertEqual([row[header[1]].text() for row in rows],
                         ["Neuverbindung 9"])


class PageTests(FormCase):

    def test_page_of_a_position_without_a_number(self) -> None:
        item = numberless(self.kl)
        root = page(self.client.get(item_url(item)))
        self.assertEqual(root.find("h1").text(), "Neuverbindung 9")
        metadata = root.find("dl", "metadata")
        terms = [dt.text() for dt in metadata.find_all("dt")]
        values = [dd.text() for dd in metadata.find_all("dd")]
        self.assertEqual(values[terms.index("Verbindung")], "–")
        links = {a.text(): a.get("href") for a in
                 root.find("div", "lab-actions").find_all("a")}
        self.assertEqual(links.get("Artikelnr. eintragen"),
                         item_url(item, "edit"))
        self.assertNotIn("Abgabe buchen", links)
        self.assertNotIn("Verbrauch nachtragen", links)
        self.assertIn("Abfüllen", links)
        self.assertFalse([a for a in root.find_all("a") if a.get(
            "href", "").startswith("/lab/inventory/bulk/new/")])

    def test_a_numbered_page_keeps_its_links(self) -> None:
        item = self.item("CH-0012", "Zimtsäure")
        root = page(self.client.get(item_url(item)))
        self.assertEqual(root.find("h1").text(), "CH-0012 · Zimtsäure")
        links = [a.text() for a in
                 root.find("div", "lab-actions").find_all("a")]
        self.assertIn("Abgabe buchen", links)
        self.assertNotIn("Artikelnr. eintragen", links)


class AdminTests(InventoryCase):

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(make_user("boss", "BO", is_staff=True,
                                          is_superuser=True))

    def test_editable_while_there_is_none(self) -> None:
        item = numberless(self.kl)
        numbered = self.item("CH-0012")
        names = [{e.get("name") for e in page(self.client.get(
            f"{ADMIN_ITEMS}{record.pk}/change/")).find_all("input")}
            for record in (item, numbered)]
        self.assertIn("article_number", names[0])
        self.assertNotIn("article_number", names[1])


    def test_a_number_entered_in_the_admin(self) -> None:
        item = numberless(self.kl)
        self.client.post(f"{ADMIN_ITEMS}{item.pk}/change/", {
            "name": item.name, "category": "", "note": "",
            "status": "active", "stocked_on": "",
            "article_number": "CH-0021"})
        self.assertEqual(fresh(item).article_number, "CH-0021")

    def test_a_stale_change_page_keeps_the_number(self) -> None:
        from django.test import Client
        item = numberless(self.kl)
        self.assertEqual(self.client.get(
            f"{ADMIN_ITEMS}{item.pk}/change/").status_code, 200)
        other = Client()
        other.force_login(self.kl)
        other.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        self.client.post(f"{ADMIN_ITEMS}{item.pk}/change/", {
            "name": item.name, "category": "", "note": "neu",
            "status": "active", "stocked_on": "", "article_number": ""})
        stored = fresh(item)
        self.assertEqual((stored.article_number, stored.note),
                         ("CH-0021", "neu"))

    def test_a_number_taken_refuses_the_whole_change(self) -> None:
        self.item("CH-0012", size="10", unit="umol")
        item = numberless(self.kl, size="10", unit="umol")
        response = self.client.post(f"{ADMIN_ITEMS}{item.pk}/change/", {
            "name": item.name, "category": "", "note": "neu",
            "status": "active", "stocked_on": "",
            "article_number": "CH-0012"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("article_number",
                      response.context["adminform"].form.errors)
        stored = fresh(item)
        self.assertEqual((stored.article_number, stored.note), (None, ""))

    def test_a_number_entered_twice_keeps_the_first(self) -> None:
        from django.test import Client
        item = numberless(self.kl)
        other = Client()
        other.force_login(self.kl)
        other.post(item_url(item, "edit"), edit_data(
            item, article_number="CH-0021"))
        self.client.post(f"{ADMIN_ITEMS}{item.pk}/change/", {
            "name": item.name, "category": "", "note": "",
            "status": "active", "stocked_on": "",
            "article_number": "CH-0022"})
        self.assertEqual(fresh(item).article_number, "CH-0021")


class PlanningTests(InventoryCase):

    def test_a_position_without_a_number_is_planned_nowhere(self) -> None:
        from planning.plan import Plan, task_priority
        item = numberless(self.kl, "1-Phenylethanol", size="100",
                          quantity=8)
        task = make_task(self.kl, product="1-phenylethanol",
                         priority="low")
        found = Plan(TODAY)
        self.assertNotIn(None, found.items)
        self.assertNotIn(item, [entry for items in found.items.values()
                                for entry in items])
        self.assertEqual(found.articles_of(task), [])
        self.assertFalse(task_priority(task, TODAY).computed)
        self.assertNotIn("1-Phenylethanol", page(self.client.get(
            "/lab/planning/?all=1")).find("main").text())
