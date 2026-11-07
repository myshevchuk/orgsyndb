"""Tests of the items' locations and of ticking items into a delivery
note (end-product-inventory: Items, Item list, Delivery list, Item page
and Inventory forms)."""

from inventory.models import Item

from . import field_value, make_user, page, table
from .inventory_support import (DELIVERIES, LIST, NEW_ITEM, NEW_NOTE,
                                FormCase, InventoryCase, fresh, item_url,
                                note_data, note_url)

ADMIN_ITEMS = "/lab/admin/inventory/item/"


def kept(item: Item, compartment: str, box: str) -> Item:
    Item.objects.filter(pk=item.pk).update(compartment=compartment, box=box)
    return fresh(item)


def datalist(root, ident: str) -> list[str]:
    found = root.find("datalist", id=ident)
    return [] if found is None else [option.get("value") for option in
                                     found.find_all("option")]


def chosen_rows(root) -> list[str]:
    """The item chosen in each row of a note form, empty for none."""
    return [field_value(root, f"item_{row}") or "" for row in range(10)]


class ItemFormTests(FormCase):

    def test_a_new_item_with_its_location(self) -> None:
        self.client.post(NEW_ITEM, {
            "article_number": "CH-0012", "name": "Zimtsäure",
            "category": "", "size": "10", "unit": "umol", "quantity": "3",
            "stocked_on": "", "compartment": "2", "box": "7", "note": ""})
        item = Item.objects.get()
        self.assertEqual((item.compartment, item.box), ("2", "7"))

    def test_the_locations_are_optional(self) -> None:
        self.client.post(NEW_ITEM, {
            "article_number": "CH-0012", "name": "Zimtsäure",
            "category": "", "size": "10", "unit": "umol", "quantity": "3",
            "stocked_on": "", "compartment": "", "box": "", "note": ""})
        self.assertEqual((Item.objects.get().compartment,
                          Item.objects.get().box), ("", ""))

    def test_at_most_thirty_characters(self) -> None:
        item = self.item("CH-0012")
        for field in ("compartment", "box"):
            with self.subTest(field=field):
                response = self.client.post(item_url(item, "edit"), {
                    "name": item.name, "category": "", "note": "",
                    "status": "active", "stocked_on": "",
                    "compartment": "", "box": "", field: "x" * 31})
                self.refused(response, field)

    def test_the_edit_form_changes_them(self) -> None:
        item = self.item("CH-0012")
        self.client.post(item_url(item, "edit"), {
            "name": item.name, "category": "", "note": "",
            "status": "active", "stocked_on": "2019-01-02",
            "compartment": "3", "box": "12"})
        stored = fresh(item)
        self.assertEqual((stored.compartment, stored.box), ("3", "12"))

    def test_the_datalists_offer_the_values_in_use(self) -> None:
        kept(self.item("A-1"), "10", "7")
        kept(self.item("A-2"), "2", "7")
        kept(self.item("A-3"), "", "")
        for path in (NEW_ITEM, item_url(self.item("A-4"), "edit")):
            with self.subTest(path=path):
                root = page(self.client.get(path))
                self.assertEqual(root.find("input", name="compartment")
                                 .get("list"), "compartments")
                self.assertEqual(datalist(root, "compartments"),
                                 ["2", "10"])
                self.assertEqual(datalist(root, "boxes"), ["7"])

    def test_digits_of_other_scripts_are_text(self) -> None:
        kept(self.item("A-1"), "①", "²")
        kept(self.item("A-2"), "10", "7")
        kept(self.item("A-3"), "٣", "2")
        for path in (LIST, NEW_ITEM, item_url(self.item("A-4"), "edit")):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
        root = page(self.client.get(NEW_ITEM))
        self.assertEqual(datalist(root, "compartments"), ["10", "٣", "①"])

    def test_the_history_shows_them(self) -> None:
        item = self.item("CH-0012")
        item.compartment, item.box = "2", "7"
        item.save()
        self.client.post(item_url(item, "edit"), {
            "name": item.name, "category": "", "note": "",
            "status": "active", "stocked_on": "2019-01-02",
            "compartment": "3", "box": "12"})
        history = page(self.client.get(item_url(item))).find(
            "ul", "lab-history").text()
        for shown in ("Fach", "Box", "2", "3", "7", "12"):
            with self.subTest(shown=shown):
                self.assertIn(shown, history)
        self.assertNotIn("Kein Feld", history)

    def test_the_admin_edits_them(self) -> None:
        self.client.force_login(make_user("boss", "BO", is_staff=True,
                                          is_superuser=True))
        item = self.item("CH-0012")
        names = {e.get("name") for e in page(self.client.get(
            f"{ADMIN_ITEMS}{item.pk}/change/")).find_all("input")}
        self.assertLessEqual({"compartment", "box"}, names)


class ListTests(InventoryCase):

    def test_locations(self) -> None:
        """Scenario: Locations."""
        kept(self.item("A-1"), "2", "7")
        kept(self.item("A-2"), "10", "7")
        header, rows = table(page(self.client.get(LIST)))
        self.assertEqual(header[4:6], ["Fach", "Box"])
        self.assertEqual([(row["Fach"].text(), row["Box"].text())
                          for row in rows], [("2", "7"), ("10", "7")])
        for query, wanted in (("?compartment=2", ["A-1"]),
                              ("?box=7", ["A-1", "A-2"])):
            with self.subTest(query=query):
                header, rows = table(page(self.client.get(LIST + query)))
                self.assertEqual([row[header[0]].text() for row in rows],
                                 wanted)

    def test_the_filters_offer_the_values_in_use(self) -> None:
        kept(self.item("A-1"), "10", "7")
        kept(self.item("A-2"), "2", "7")
        root = page(self.client.get(LIST + "?compartment=10"))
        select = root.find("select", name="compartment")
        self.assertEqual([option.get("value") for option in
                          select.find_all("option")], ["", "2", "10"])
        self.assertEqual(field_value(root, "compartment"), "10")

    def test_no_check_boxes_for_visitors(self) -> None:
        self.item("CH-0012")
        root = page(self.client.get(LIST))
        self.assertEqual(root.find_all("input", type="checkbox"), [])
        self.assertIsNone(root.find("form", id="pick"))


class TickingTests(FormCase):

    def test_ticking_rows(self) -> None:
        """Scenario: Ticking rows."""
        first = self.item("CH-0012")
        second = self.item("CH-0010")
        self.item(None, "Neuverbindung 9")
        root = page(self.client.get(LIST))
        boxes = root.find_all("input", type="checkbox", name="item")
        self.assertEqual(sorted(box.get("value") for box in boxes),
                         sorted([str(first.pk), str(second.pk)]))
        form = root.find("form", id="pick")
        self.assertEqual(form.get("method"), "get")
        self.assertEqual(form.get("action"), NEW_NOTE)
        self.assertTrue(all(box.get("form") == "pick" for box in boxes))
        self.assertIsNone(form.closest("form"))
        self.assertEqual(form.find("button").text(),
                         "Lieferschein mit Auswahl")
        header, rows = table(root)
        self.assertEqual(sorted(row[header[0]].text() for row in rows
                                if row[header[0]].text()),
                         ["CH-0010", "CH-0012"])

    def test_a_note_from_the_selection(self) -> None:
        """Scenario: A note from the selection."""
        a = self.item("CH-0012")
        b = self.item("CH-0010")
        c = self.item(None, "Neuverbindung 9")
        root = page(self.client.get(
            f"{NEW_NOTE}?item={a.pk}&item={b.pk}&item={a.pk}&item={c.pk}"
            "&item=x&item=99999"))
        self.assertEqual(chosen_rows(root),
                         [str(a.pk), str(b.pk)] + [""] * 8)

    def test_one_item_still_fills_the_first_row(self) -> None:
        a = self.item("CH-0012")
        root = page(self.client.get(f"{NEW_NOTE}?item={a.pk}"))
        self.assertEqual(chosen_rows(root)[:2], [str(a.pk), ""])

    def test_ten_rows_at_most(self) -> None:
        items = [self.item(f"A-{n:02d}") for n in range(12)]
        query = "&".join(f"item={item.pk}" for item in items)
        root = page(self.client.get(f"{NEW_NOTE}?{query}"))
        self.assertEqual(chosen_rows(root),
                         [str(item.pk) for item in items[:10]])

    def test_the_selection_books_as_one_note(self) -> None:
        a = self.item("CH-0012", quantity=5)
        b = self.item("CH-0010", quantity=5)
        self.client.post(NEW_NOTE, note_data((a, 1), (b, 2)))
        self.assertEqual((fresh(a).quantity, fresh(b).quantity), (4, 3))

    def test_rows_name_the_location(self) -> None:
        """Scenario: Rows name the location."""
        kept(self.item("CH-0012", "(E)-Zimtsäure", "100", "mg"), "2", "7")
        kept(self.item("CH-0010", "Aspirin", "1", "g"), "", "4")
        self.item("CH-0016", "Isopentylacetat", "5", "g")
        labels = [option.text() for option in page(self.client.get(
            NEW_NOTE)).find("select", name="item_0").find_all("option")
            if option.get("value")]
        self.assertEqual(sorted(labels), sorted([
            "CH-0012 · 100 mg · (E)-Zimtsäure · Fach 2 / Box 7",
            "CH-0010 · 1 g · Aspirin · Box 4",
            "CH-0016 · 5 g · Isopentylacetat"]))


class PageTests(FormCase):

    def test_the_item_page_shows_the_locations(self) -> None:
        item = kept(self.item("CH-0012"), "2", "7")
        bare = self.item("CH-0010")
        for record, wanted in ((item, ("2", "7")), (bare, ("–", "–"))):
            with self.subTest(item=record.article_number):
                metadata = page(self.client.get(item_url(record))).find(
                    "dl", "metadata")
                terms = [dt.text() for dt in metadata.find_all("dt")]
                values = [dd.text() for dd in metadata.find_all("dd")]
                self.assertEqual((values[terms.index("Fach")],
                                  values[terms.index("Box")]), wanted)

    def test_a_pick_list(self) -> None:
        """Scenario: A pick list."""
        item = kept(self.item("CH-0012", quantity=5), "2", "7")
        note = self.deliver(item, 2)
        header, rows = table(page(self.client.get(note_url(note))))
        self.assertIn("Fach", header)
        self.assertEqual((rows[0]["Fach"].text(), rows[0]["Box"].text()),
                         ("2", "7"))
        self.assertTrue(DELIVERIES)
