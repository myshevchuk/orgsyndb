"""Tests of the inventory forms and their permissions (end-product-
inventory: Inventory forms; web-app: Permissions)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import book_note, fill
from inventory.models import (DeliveryNote, EnteredConsumption, Item, Lot,
                              LotMovement, Movement)

from . import (build_index, context_form, demo_data, field_value, page,
               sent_messages)
from .inventory_support import (LIST, MICRO, NEW_ITEM, NEW_LOT, NEW_NOTE,
                                TODAY, FormCase, InventoryCase, fill_data,
                                fresh, item_data, item_url, lot_data, lot_url,
                                movement_url, newest_movement, note_data,
                                note_url, snapshot)


def form_names(root, anchor: str) -> set[str]:
    """The names of the controls of the form that holds ``anchor``."""
    form = root.find(("input", "select", "textarea"), name=anchor
                     ).closest("form")
    return {e.get("name") for e in
            form.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in ("submit", "button")
            and e.get("name") != "csrfmiddlewaretoken"}


def datalist(root, field: str) -> dict[str, str]:
    control = root.find("input", name=field)
    listed = control.get("list")
    assert listed, f"the input {field} names no datalist"
    found = root.find("datalist", id=listed)
    assert found is not None
    return {o.get("value"): o.get("label") or o.text()
            for o in found.find_all("option")}


class PermissionTests(InventoryCase):

    def paths(self) -> dict[str, dict[str, str]]:
        item = self.item("CH-0012", quantity=9)
        movement = self.deliver_movement(item, 1)
        historical = book_note(self.kl, date=date(2025, 3, 12),
                               historical=True, lines=[(item, 1)])
        lot = self.lot("CH-0012")
        today = TODAY.isoformat()
        return {
            NEW_ITEM: item_data(article_number="CH-0099"),
            item_url(item, "edit"): {"name": "X", "category": "",
                                     "status": "active",
                                     "note": ""},
            NEW_NOTE: note_data((item, 1)),
            note_url(historical, "reverse"): {"note": "x"},
            note_url(movement.delivery_note, "edit"): {
                "number": "N-1", "recipient": "", "note": ""},
            item_url(item, "fill"): fill_data(),
            item_url(item, "correct"): {"count": "1", "date": today,
                                        "note": "x"},
            movement_url(movement): {"note": "x"},
            item_url(item, "consumption"): {"year": "2026", "quarter": "1",
                                            "count": "3"},
            NEW_LOT: lot_data(article_number="CH-0099"),
            lot_url(lot, "edit"): {"batch": "X", "location": "",
                                   "made_on": "", "note": ""},
            lot_url(lot, "correct"): {"amount": "1", "date": today,
                                      "note": "x"},
        }

    def test_form_without_sign_in(self) -> None:
        """Scenario: Form without sign-in (every inventory form)."""
        paths = self.paths()
        before = snapshot()
        for path, data in paths.items():
            login = f"/lab/accounts/login/?next={path}"
            with self.subTest(path=path, method="GET"):
                done = self.client.get(path)
                self.assertEqual(done.status_code, 302)
                self.assertEqual(done["Location"], login)
            with self.subTest(path=path, method="POST"):
                done = self.client.post(path, data)
                self.assertEqual(done.status_code, 302)
                self.assertEqual(done["Location"], login)
        self.assertEqual(snapshot(), before)

    def test_the_pages_that_show_data_need_no_sign_in(self) -> None:
        item = self.item("CH-0012", quantity=9)
        note = self.deliver(item, 1)
        lot = self.lot("CH-0012")
        for path in (LIST, "/lab/inventory/end-products/bulk/",
                     "/lab/inventory/deliveries/", item_url(item),
                     lot_url(lot), note_url(note)):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_unknown_records_answer_404_to_a_signed_in_user(self) -> None:
        item = self.item("CH-0012", quantity=9)
        movement = self.deliver_movement(item, 1)
        self.client.force_login(self.kl)
        missing = [
            "/lab/inventory/items/9999/edit/",
            "/lab/inventory/items/9999/fill/",
            "/lab/inventory/items/9999/correct/",
            "/lab/inventory/items/9999/consumption/",
            f"/lab/inventory/items/9999/movements/{movement.pk}/reverse/",
            f"/lab/inventory/items/{item.pk}/movements/9999/reverse/",
            "/lab/inventory/deliveries/9999/edit/",
            "/lab/inventory/deliveries/9999/reverse/",
            "/lab/inventory/bulk/9999/edit/",
            "/lab/inventory/bulk/9999/correct/"]
        before = snapshot()
        for path in missing:
            with self.subTest(path=path, method="GET"):
                self.assertEqual(self.client.get(path).status_code, 404)
            with self.subTest(path=path, method="POST"):
                self.assertEqual(self.client.post(path, {"note": "x"}
                                                  ).status_code, 404)
        self.assertEqual(snapshot(), before)


class NewItemTests(FormCase):

    def test_new_item(self) -> None:
        """Scenario: New item."""
        done = self.client.post(NEW_ITEM, item_data())
        item = Item.objects.get()
        self.assertEqual(
            (item.article_number, item.name, item.unit, item.quantity),
            ("CH-0012", "Zimtsäure", "umol", 12))
        self.assertEqual(item.size, Decimal("10"))
        movement = item.movements.get()
        self.assertEqual((movement.kind, movement.count, movement.user),
                         ("opening", 12, self.kl))
        self.assertRedirects(done, item_url(item),
                             fetch_redirect_response=False)

    def test_the_message_names_the_record(self) -> None:
        done = self.client.post(NEW_ITEM, item_data())
        self.assertMessageNames(done, "CH-0012", "Zimtsäure")
        text = sent_messages(done)[0].message
        shown = self.client.get(item_url(Item.objects.get()))
        self.assertIn(text, page(shown).text())

    def test_all_fields_are_saved(self) -> None:
        self.client.post(NEW_ITEM, item_data(
            category="Endprodukt", size="2,5", unit="mg", quantity="0",
            note="Zeile eins\nZeile zwei"))
        item = Item.objects.get()
        self.assertEqual((item.category, item.unit, item.quantity),
                         ("Endprodukt", "mg", 0))
        self.assertEqual(item.size, Decimal("2.5"))
        self.assertIn("Zeile zwei", item.note)
        self.assertEqual(item.inventory, "end-products")

    def test_a_decimal_point_is_accepted_too(self) -> None:
        self.client.post(NEW_ITEM, item_data(size="2.5"))
        self.assertEqual(Item.objects.get().size, Decimal("2.5"))

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = form_names(page(self.client.get(NEW_ITEM)), "article_number")
        self.assertEqual(names, {"article_number", "name", "category", "size",
                                 "unit", "quantity", "stocked_on",
                                 "compartment", "box", "note"})

    def test_the_unit_choices(self) -> None:
        root = page(self.client.get(NEW_ITEM))
        options = root.find("select", name="unit").find_all("option")
        self.assertEqual(
            {o.get("value"): o.text() for o in options if o.get("value")},
            {"mg": "mg", "umol": f"{MICRO}mol", "g": "g", "mmol": "mmol"})

    def test_the_article_number_offers_the_compounds(self) -> None:
        options = datalist(page(self.client.get(NEW_ITEM)), "article_number")
        numbered = [entry for entry in demo_data()["compounds"]
                    if "item_number" in entry["data"]]
        self.assertTrue(numbered)
        for entry in numbered:
            data = entry["data"]
            with self.subTest(identifier=data["item_number"]):
                self.assertEqual(options[data["item_number"]],
                                 data["name_de"])
        self.assertEqual(len(options), len(numbered))

    def test_the_category_offers_the_categories_in_use(self) -> None:
        self.item("A-1", category="Endprodukt")
        self.item("A-2", category="Zwischenstufe")
        self.item("A-3", category="Endprodukt")
        self.item("A-4")
        options = datalist(page(self.client.get(NEW_ITEM)), "category")
        self.assertEqual(set(options) - {""}, {"Endprodukt", "Zwischenstufe"})

    def test_one_article_in_two_sizes(self) -> None:
        """Scenario: One article in two sizes (the form)."""
        self.client.post(NEW_ITEM, item_data(size="10"))
        self.client.post(NEW_ITEM, item_data(size="50"))
        self.assertEqual(Item.objects.count(), 2)
        self.refused(self.client.post(NEW_ITEM, item_data(size="10")),
                     "size")
        self.assertEqual(Item.objects.count(), 2)
        self.assertEqual(Movement.objects.count(), 2)

    def test_the_same_size_in_another_unit_is_allowed(self) -> None:
        self.client.post(NEW_ITEM, item_data(size="10", unit="umol"))
        self.client.post(NEW_ITEM, item_data(size="10", unit="mg"))
        self.assertEqual(Item.objects.count(), 2)

    def test_the_limits_are_accepted(self) -> None:
        self.client.post(NEW_ITEM, item_data(
            article_number="a" * 30, name="n" * 200, category="c" * 100,
            size="0,001", quantity="0"))
        self.assertEqual(Item.objects.count(), 1)

    def test_refused_fields(self) -> None:
        cases = {
            "article_number": ["a" * 31],
            "name": ["", "n" * 201],
            "category": ["c" * 101],
            "size": ["", "0", "-1", "abc", "1,2345"],
            "unit": ["", "kg"],
            "quantity": ["", "-1", "x", "1,5"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.refused(self.client.post(
                        NEW_ITEM, item_data(**{field: value})), field)
        self.assertEqual(Item.objects.count(), 0)
        self.assertEqual(Movement.objects.count(), 0)

    def test_the_form_keeps_what_was_typed(self) -> None:
        done = self.client.post(NEW_ITEM, item_data(
            name="Probe", size="0", note="Notiz"))
        root = page(done)
        self.assertEqual(field_value(root, "name"), "Probe")
        self.assertEqual(field_value(root, "size"), "0")
        self.assertEqual(field_value(root, "note"), "Notiz")

    def test_a_refused_form_sends_no_message(self) -> None:
        done = self.client.post(NEW_ITEM, item_data(name=""))
        self.assertEqual(sent_messages(done), [])

    def test_the_creator_is_the_signed_in_user(self) -> None:
        self.client.force_login(self.ae)
        self.client.post(NEW_ITEM, item_data())
        self.assertEqual(Item.objects.get().movements.get().user, self.ae)
        self.assertEqual(Item.objects.get().history.get().history_user,
                         self.ae)


class ItemEditTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item("CH-0012", name="Alt", size="10",
                                unit="umol", quantity=7, category="K",
                                note="alt")

    def test_the_form_shows_the_item(self) -> None:
        root = page(self.client.get(item_url(self.target, "edit")))
        self.assertEqual(field_value(root, "name"), "Alt")
        self.assertEqual(field_value(root, "category"), "K")
        self.assertEqual(field_value(root, "note"), "alt")

    def test_the_form_holds_the_fields_that_may_change(self) -> None:
        root = page(self.client.get(item_url(self.target, "edit")))
        self.assertEqual(form_names(root, "name"),
                         {"name", "category", "status", "stocked_on",
                          "compartment", "box", "note"})

    def test_changing_an_item(self) -> None:
        self.client.force_login(self.ae)
        done = self.client.post(item_url(self.target, "edit"), {
            "name": "Neu", "category": "Z", "note": "neu",
            "status": "active", "stocked_on": "2019-01-02"})
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        item = fresh(self.target)
        self.assertEqual((item.name, item.category, item.note),
                         ("Neu", "Z", "neu"))
        self.assertEqual(item.history.count(), 2)
        self.assertEqual(item.history.first().history_user, self.ae)
        self.assertMessageNames(done, "CH-0012", "Neu")

    def test_fixed_identity(self) -> None:
        """Scenario: Fixed identity."""
        self.client.post(item_url(self.target, "edit"), {
            "name": "Neu", "category": "", "note": "", "status": "active",
            "article_number": "CH-9999", "size": "99", "unit": "g",
            "quantity": "77"})
        item = fresh(self.target)
        self.assertEqual(item.name, "Neu")
        self.assertEqual(
            (item.article_number, item.size, item.unit, item.quantity),
            ("CH-0012", Decimal("10"), "umol", 7))
        self.assertEqual(item.movements.count(), 1)

    def test_a_refused_edit_changes_nothing(self) -> None:
        before = snapshot()
        done = self.client.post(item_url(self.target, "edit"), {
            "name": "", "category": "x", "note": "x"})
        self.refused(done, "name")
        self.assertEqual(snapshot(), before)
        done = self.client.post(item_url(self.target, "edit"), {
            "name": "n" * 201, "category": "", "note": ""})
        self.refused(done, "name")
        done = self.client.post(item_url(self.target, "edit"), {
            "name": "x", "category": "c" * 101, "note": ""})
        self.refused(done, "category")


class NoteFormTests(FormCase):

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = form_names(page(self.client.get(NEW_NOTE)), "number")
        expected = {"number", "date", "recipient", "note", "historical"}
        for index in range(10):
            expected |= {f"item_{index}", f"count_{index}"}
        self.assertEqual(names, expected)

    def test_the_historical_check_box(self) -> None:
        root = page(self.client.get(NEW_NOTE))
        box = root.find("input", name="historical")
        self.assertEqual(box.get("type"), "checkbox")
        self.assertIn("nachgetragen – Bestand bleibt unverändert",
                      root.text())
        self.use_index(build_index("en"))
        self.assertIn("entered later – stock unchanged",
                      page(self.client.get(NEW_NOTE)).text())

    def test_an_item_in_the_url_fills_the_first_row(self) -> None:
        item = self.item()
        root = page(self.client.get(f"{NEW_NOTE}?item={item.pk}"))
        self.assertEqual(field_value(root, "item_0"), str(item.pk))
        self.assertIn(field_value(root, "item_1"), (None, ""))

    def test_booking_a_note(self) -> None:
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=3)
        done = self.client.post(NEW_NOTE, note_data(
            (first, 2), (second, 3), number="LS-2026-117",
            recipient="Produktion", note="Eilig"))
        note = DeliveryNote.objects.get()
        self.assertRedirects(done, note_url(note),
                             fetch_redirect_response=False)
        self.assertEqual(
            (note.number, note.date, note.recipient, note.note,
             note.created_by, note.historical),
            ("LS-2026-117", TODAY, "Produktion", "Eilig", self.kl, False))
        self.assertEqual((fresh(first).quantity, fresh(second).quantity),
                         (3, 0))
        self.assertEqual(note.lines.count(), 2)
        self.assertMessageNames(done, "LS-2026-117")

    def test_rows_left_empty_are_ignored(self) -> None:
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=5)
        data = note_data()
        data.update({"item_3": str(first.pk), "count_3": "1",
                     "item_7": str(second.pk), "count_7": "2"})
        self.client.post(NEW_NOTE, data)
        self.assertEqual(DeliveryNote.objects.get().lines.count(), 2)
        self.assertEqual((fresh(first).quantity, fresh(second).quantity),
                         (4, 3))

    def test_all_ten_rows_can_be_used(self) -> None:
        items = [self.item(f"CH-{n:04d}", quantity=5) for n in range(10)]
        self.client.post(NEW_NOTE, note_data(*[(i, 1) for i in items]))
        self.assertEqual(DeliveryNote.objects.get().lines.count(), 10)

    def test_a_note_without_a_number_is_allowed(self) -> None:
        item = self.item()
        self.client.post(NEW_NOTE, note_data((item, 1)))
        self.assertIn(DeliveryNote.objects.get().number, ("", None))
        self.client.post(NEW_NOTE, note_data((item, 1)))
        self.assertEqual(DeliveryNote.objects.count(), 2)

    def test_the_note_page_shows_the_message(self) -> None:
        item = self.item()
        done = self.client.post(NEW_NOTE, note_data((item, 1), number="LS-1"),
                                follow=True)
        shown = [str(m) for m in done.context["messages"]]
        self.assertEqual(len(shown), 1)
        self.assertIn("LS-1", shown[0])
        self.assertIn(shown[0], page(done).text())

    def test_one_line_too_many_refuses_the_note(self) -> None:
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=3)
        before = snapshot()
        done = self.client.post(NEW_NOTE, note_data((first, 2), (second, 4)))
        self.refused(done, "count_1")
        self.assertNotIn("count_0", context_form(done).errors)
        self.assertEqual(snapshot(), before)
        self.assertEqual(DeliveryNote.objects.count(), 0)

    def test_a_historical_note_changes_no_quantity(self) -> None:
        item = self.item(quantity=5)
        done = self.client.post(NEW_NOTE, note_data(
            (item, 4), date="2025-03-12", historical="on"))
        note = DeliveryNote.objects.get()
        self.assertTrue(note.historical)
        self.assertRedirects(done, note_url(note),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(item).quantity, 5)
        self.assertEqual(item.movements.count(), 1)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 4)

    def test_a_historical_note_may_exceed_the_quantity(self) -> None:
        item = self.item(quantity=1)
        self.client.post(NEW_NOTE, note_data(
            (item, 4), date="2025-03-12", historical="on"))
        self.assertEqual(DeliveryNote.objects.count(), 1)

    def test_historical_note_in_a_quarter_with_an_entered_value(self) -> None:
        """Scenario: Historical note in a quarter with an entered value."""
        item = self.item(quantity=5)
        self.enter(item, 2025, 1, 6)
        before = snapshot()
        done = self.client.post(NEW_NOTE, note_data(
            (item, 4), date="2025-03-12", historical="on"))
        self.refused(done, "count_0")
        self.assertEqual(snapshot(), before)

    def test_the_conflicting_line_is_the_one_marked(self) -> None:
        first = self.item("CH-0001")
        second = self.item("CH-0002")
        self.enter(second, 2025, 1, 6)
        done = self.client.post(NEW_NOTE, note_data(
            (first, 1), (second, 1), date="2025-03-12", historical="on"))
        self.refused(done, "count_1")
        self.assertNotIn("count_0", context_form(done).errors)

    def test_refused_fields(self) -> None:
        item = self.item("CH-0001", quantity=5)
        other = self.item("CH-0002", quantity=5)
        self.deliver(other, 1, number="LS-TAKEN")
        cases = [
            ("a note without a line", note_data(), None),
            ("a count of zero", note_data((item, 0)), "count_0"),
            ("a negative count", note_data((item, -1)), "count_0"),
            ("a count that is no number", note_data((item, "x")), "count_0"),
            ("a count without an item", note_data(count_0="1"), None),
            ("an item without a count", note_data(item_0=str(item.pk)),
             None),
            ("an unknown item", note_data(item_0="9999", count_0="1"),
             "item_0"),
            ("an item twice", note_data((item, 1), (item, 1)), None),
            ("a date after today", note_data((item, 1),
                                             date="2026-11-05"), "date"),
            ("no date", note_data((item, 1), date=""), "date"),
            ("a long number", note_data((item, 1), number="n" * 31),
             "number"),
            ("a taken number", note_data((item, 1), number="LS-TAKEN"),
             "number"),
            ("a long recipient", note_data((item, 1),
                                           recipient="r" * 101),
             "recipient")]
        before = snapshot()
        for name, data, field in cases:
            with self.subTest(name):
                self.refused(self.client.post(NEW_NOTE, data), field)
        self.assertEqual(snapshot(), before)

    def test_the_limits_are_accepted(self) -> None:
        item = self.item(quantity=5)
        self.client.post(NEW_NOTE, note_data(
            (item, 1), number="n" * 30, recipient="r" * 100))
        self.assertEqual(DeliveryNote.objects.count(), 1)

    def test_the_form_keeps_what_was_typed(self) -> None:
        item = self.item(quantity=1)
        done = self.client.post(NEW_NOTE, note_data(
            (item, 4), recipient="Produktion", number="LS-1",
            note="Eilig"))
        root = page(done)
        self.assertEqual(field_value(root, "recipient"), "Produktion")
        self.assertEqual(field_value(root, "number"), "LS-1")
        self.assertEqual(field_value(root, "note"), "Eilig")
        self.assertEqual(field_value(root, "item_0"), str(item.pk))
        self.assertEqual(field_value(root, "count_0"), "4")
        self.assertEqual(sent_messages(done), [])


class NoteEditTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.stocked = self.item(quantity=9)
        self.target = self.deliver(self.stocked, 2, number="LS-1",
                                   recipient="Alt", note="alt")

    def test_the_form_shows_the_note(self) -> None:
        root = page(self.client.get(note_url(self.target, "edit")))
        self.assertEqual(field_value(root, "number"), "LS-1")
        self.assertEqual(field_value(root, "recipient"), "Alt")
        self.assertEqual(field_value(root, "note"), "alt")
        self.assertEqual(form_names(root, "number"),
                         {"number", "recipient", "note"})

    def test_changing_a_note(self) -> None:
        self.client.force_login(self.ae)
        done = self.client.post(note_url(self.target, "edit"), {
            "number": "LS-2", "recipient": "Neu", "note": "neu"})
        self.assertRedirects(done, note_url(self.target),
                             fetch_redirect_response=False)
        note = fresh(self.target)
        self.assertEqual((note.number, note.recipient, note.note),
                         ("LS-2", "Neu", "neu"))
        self.assertEqual(note.history.count(), 2)
        self.assertEqual(note.history.first().history_user, self.ae)
        self.assertMessageNames(done, "LS-2")

    def test_date_kind_and_lines_are_fixed(self) -> None:
        other = self.item("CH-0002", quantity=9)
        self.client.post(note_url(self.target, "edit"), {
            "number": "LS-1", "recipient": "Alt", "note": "alt",
            "date": "2026-01-01", "historical": "on",
            "item_0": str(other.pk), "count_0": "5"})
        note = fresh(self.target)
        self.assertEqual((note.date, note.historical), (TODAY, False))
        line = note.lines.get()
        self.assertEqual((line.item, line.count), (self.stocked, 2))
        self.assertEqual(fresh(other).quantity, 9)

    def test_its_own_number_is_not_taken(self) -> None:
        done = self.client.post(note_url(self.target, "edit"), {
            "number": "LS-1", "recipient": "Neu", "note": ""})
        self.assertEqual(done.status_code, 302)

    def test_a_taken_number_is_refused(self) -> None:
        self.deliver(self.stocked, 1, number="LS-TAKEN")
        before = snapshot()
        self.refused(self.client.post(note_url(self.target, "edit"), {
            "number": "LS-TAKEN", "recipient": "", "note": ""}), "number")
        self.assertEqual(snapshot(), before)

    def test_limits(self) -> None:
        for field, value in (("number", "n" * 31), ("recipient", "r" * 101)):
            with self.subTest(field=field):
                data = {"number": "LS-1", "recipient": "", "note": ""}
                data[field] = value
                self.refused(self.client.post(
                    note_url(self.target, "edit"), data), field)

    def test_a_number_may_be_removed(self) -> None:
        self.client.post(note_url(self.target, "edit"), {
            "number": "", "recipient": "", "note": ""})
        self.assertIn(fresh(self.target).number, ("", None))


class HistoricalReversalFormTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.stocked = self.item(quantity=5)
        self.target = book_note(self.kl, date=date(2025, 3, 12),
                                historical=True, number="ALT-1",
                                lines=[(self.stocked, 4)])

    def test_the_form_asks_for_a_note(self) -> None:
        root = page(self.client.get(note_url(self.target, "reverse")))
        self.assertEqual(form_names(root, "note"), {"note"})

    def test_marking_a_historical_note_reversed(self) -> None:
        done = self.client.post(note_url(self.target, "reverse"),
                                {"note": "doppelt erfasst"})
        self.assertRedirects(done, note_url(self.target),
                             fetch_redirect_response=False)
        note = fresh(self.target)
        self.assertTrue(note.reversed)
        self.assertEqual(note.reversal_note, "doppelt erfasst")
        self.assertMessageNames(done, "ALT-1")
        self.assertEqual(
            self.consumption(self.stocked).quarters.get((2025, 1), 0), 0)

    def test_a_note_is_required(self) -> None:
        before = snapshot()
        self.refused(self.client.post(note_url(self.target, "reverse"),
                                      {"note": ""}), "note")
        self.assertEqual(snapshot(), before)

    def test_a_current_note_is_not_reversed_whole(self) -> None:
        current = self.deliver(self.stocked, 1, number="LS-1")
        before = snapshot()
        self.client.post(note_url(current, "reverse"), {"note": "x"})
        self.assertEqual(snapshot(), before)

    def test_a_reversed_note_is_not_reversed_again(self) -> None:
        self.client.post(note_url(self.target, "reverse"), {"note": "x"})
        before = snapshot()
        self.client.post(note_url(self.target, "reverse"), {"note": "y"})
        self.assertEqual(snapshot(), before)


class FillFormTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item("CH-0012", size="10", unit="umol",
                                quantity=2)

    def url(self, action: str = "fill") -> str:
        return item_url(self.target, action)

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(self.url()))
        self.assertEqual(form_names(root, "count"),
                         {"count", "date", "lot", "amount", "note"})
        buttons = root.find_all(("button", "input"), name="propose")
        self.assertEqual(len(buttons), 1)
        shown = buttons[0].text() or buttons[0].get("value")
        self.assertEqual(shown, "Menge vorschlagen")

    def test_the_english_button(self) -> None:
        self.use_index(build_index("en"))
        root = page(self.client.get(self.url()))
        button = root.find(("button", "input"), name="propose")
        self.assertEqual(button.text() or button.get("value"),
                         "Propose amount")

    def test_filling_without_a_lot(self) -> None:
        done = self.client.post(self.url(), fill_data(
            count="5", note="Charge 7", date="2026-11-01"))
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.target).quantity, 7)
        movement = newest_movement(self.target)
        self.assertEqual((movement.kind, movement.count, movement.note,
                          movement.date, movement.user),
                         ("filling", 5, "Charge 7", date(2026, 11, 1),
                          self.kl))
        self.assertIsNone(movement.bulk_movement)
        self.assertMessageNames(done, "CH-0012", "Probe")

    def test_the_lots_offered_are_the_open_ones_of_the_article(self) -> None:
        open_lot = self.lot("CH-0012", "mg", "50")
        used = self.lot("CH-0012", "mg", "0")
        other = self.lot("CH-0013", "mg", "50")
        root = page(self.client.get(self.url()))
        values = [o.get("value") for o in
                  root.find("select", name="lot").find_all("option")]
        self.assertIn("", values)
        self.assertIn(str(open_lot.pk), values)
        self.assertNotIn(str(used.pk), values)
        self.assertNotIn(str(other.pk), values)

    def test_propose_amount(self) -> None:
        """Scenario: Filling with conversion (the button)."""
        lot = self.lot("CH-0012", "mg", "50")
        before = snapshot()
        done = self.client.post(self.url(), fill_data(
            count="5", lot=str(lot.pk), propose="1"))
        self.assertEqual(done.status_code, 200)
        root = page(done)
        self.assertEqual(field_value(root, "amount"), "7,408")
        self.assertEqual(field_value(root, "count"), "5")
        self.assertEqual(field_value(root, "lot"), str(lot.pk))
        self.assertFalse(context_form(done).errors)
        self.assertEqual(snapshot(), before)
        self.assertEqual(sent_messages(done), [])

    def test_booking_the_proposal(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        done = self.client.post(self.url(), fill_data(
            count="5", lot=str(lot.pk), amount="7,408"))
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.target).quantity, 7)
        self.assertEqual(fresh(lot).amount, Decimal("42.592"))
        movement = newest_movement(self.target)
        self.assertEqual(movement.bulk_movement,
                         lot.movements.order_by("-pk").first())
        self.assertEqual(movement.bulk_movement.kind, "filling")

    def test_an_empty_amount_books_the_proposal(self) -> None:
        lot = self.lot("CH-0012", "g", "1")
        self.client.post(self.url(), fill_data(count="1", lot=str(lot.pk)))
        self.assertEqual(fresh(lot).amount, Decimal("998.5184"))

    def test_the_amount_is_in_the_unit_of_the_lot_with_a_comma(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        self.client.post(self.url(), fill_data(
            count="5", lot=str(lot.pk), amount="7,4"))
        self.assertEqual(fresh(lot).amount, Decimal("42.6"))

    def test_the_button_replaces_the_amount_typed(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        done = self.client.post(self.url(), fill_data(
            count="5", lot=str(lot.pk), amount="1", propose="1"))
        self.assertEqual(field_value(page(done), "amount"), "7,408")

    def test_the_proposal_follows_the_count(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        done = self.client.post(self.url(), fill_data(
            count="10", lot=str(lot.pk), propose="1"))
        self.assertEqual(field_value(page(done), "amount"), "14,816")

    def test_the_proposal_is_shown_in_the_unit_of_the_lot(self) -> None:
        stock = self.item("X-1", size="10", unit="mg", quantity=0)
        lot = self.lot("X-1", "g", "1")
        done = self.client.post(item_url(stock, "fill"), fill_data(
            count="5", lot=str(lot.pk), propose="1"))
        self.assertEqual(field_value(page(done), "amount"), "0,05")

    def test_without_a_molar_mass_the_proposal_is_refused(self) -> None:
        stock = self.item("X-1", size="10", unit="umol", quantity=0)
        lot = self.lot("X-1", "mg", "50")
        before = snapshot()
        done = self.client.post(item_url(stock, "fill"), fill_data(
            count="5", lot=str(lot.pk), propose="1"))
        self.refused(done, "amount")
        self.assertEqual(snapshot(), before)

    def test_without_a_molar_mass_the_amount_is_required(self) -> None:
        stock = self.item("X-1", size="10", unit="umol", quantity=0)
        lot = self.lot("X-1", "mg", "50")
        before = snapshot()
        self.refused(self.client.post(item_url(stock, "fill"), fill_data(
            count="5", lot=str(lot.pk))), "amount")
        self.assertEqual(snapshot(), before)
        self.client.post(item_url(stock, "fill"), fill_data(
            count="5", lot=str(lot.pk), amount="3"))
        self.assertEqual(fresh(lot).amount, Decimal("47"))

    def test_an_amount_above_the_lot_refuses_both(self) -> None:
        lot = self.lot("CH-0012", "mg", "5")
        before = snapshot()
        self.refused(self.client.post(self.url(), fill_data(
            count="5", lot=str(lot.pk))), "amount")
        self.refused(self.client.post(self.url(), fill_data(
            count="1", lot=str(lot.pk), amount="5,1")), "amount")
        self.assertEqual(snapshot(), before)

    def test_an_amount_of_zero_is_refused(self) -> None:
        lot = self.lot("CH-0012", "mg", "5")
        before = snapshot()
        self.refused(self.client.post(self.url(), fill_data(
            count="1", lot=str(lot.pk), amount="0")), "amount")
        self.assertEqual(snapshot(), before)

    def test_a_lot_that_is_not_open_or_not_of_the_article(self) -> None:
        used = self.lot("CH-0012", "mg", "0")
        other = self.lot("CH-0013", "mg", "50")
        before = snapshot()
        for lot in (used, other):
            with self.subTest(lot=lot.pk):
                self.refused(self.client.post(self.url(), fill_data(
                    count="1", lot=str(lot.pk), amount="1")), "lot")
        self.refused(self.client.post(self.url(), fill_data(
            count="1", lot="9999", amount="1")), "lot")
        self.assertEqual(snapshot(), before)

    def test_refused_fields(self) -> None:
        before = snapshot()
        for field, value in (("count", "0"), ("count", "-1"),
                             ("count", "x"), ("count", ""),
                             ("date", "2026-11-05")):
            with self.subTest(field=field, value=value):
                self.refused(self.client.post(
                    self.url(), fill_data(**{field: value})), field)
        self.assertEqual(snapshot(), before)


class CorrectFormTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item(quantity=5)

    def data(self, **over: str) -> dict[str, str]:
        data = {"count": "4", "date": TODAY.isoformat(), "note": "gezählt"}
        data.update(over)
        return data

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(item_url(self.target, "correct")))
        self.assertEqual(form_names(root, "count"),
                         {"count", "date", "note"})

    def test_correcting_the_count(self) -> None:
        done = self.client.post(item_url(self.target, "correct"),
                                self.data())
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.target).quantity, 4)
        movement = newest_movement(self.target)
        self.assertEqual((movement.kind, movement.count, movement.note,
                          movement.user),
                         ("correction", 4, "gezählt", self.kl))
        self.assertMessageNames(done, "CH-0001", "Probe")

    def test_correction_needs_a_note(self) -> None:
        """Scenario: Correction needs a note."""
        before = snapshot()
        done = self.client.post(item_url(self.target, "correct"),
                                self.data(note=""))
        self.refused(done, "note")
        self.assertEqual(snapshot(), before)

    def test_refused_fields(self) -> None:
        before = snapshot()
        for field, value in (("count", "-1"), ("count", "x"),
                             ("count", ""), ("date", "2026-11-05"),
                             ("note", "   ")):
            with self.subTest(field=field, value=value):
                self.refused(self.client.post(
                    item_url(self.target, "correct"),
                    self.data(**{field: value})), field)
        self.assertEqual(snapshot(), before)

    def test_zero_is_a_count(self) -> None:
        self.client.post(item_url(self.target, "correct"),
                         self.data(count="0"))
        self.assertEqual(fresh(self.target).quantity, 0)


class MovementReversalFormTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item(quantity=5)
        self.delivery = self.deliver_movement(self.target, 2)

    def test_the_form_asks_for_a_note(self) -> None:
        root = page(self.client.get(movement_url(self.delivery)))
        self.assertEqual(form_names(root, "note"), {"note"})

    def test_reversing_a_delivery(self) -> None:
        done = self.client.post(movement_url(self.delivery),
                                {"note": "falsch gebucht"})
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.target).quantity, 5)
        reversal = newest_movement(self.target)
        self.assertEqual((reversal.kind, reversal.reverses, reversal.note,
                          reversal.user),
                         ("reversal", self.delivery, "falsch gebucht",
                          self.kl))
        self.assertMessageNames(done, "CH-0001", "Probe")

    def test_reversing_a_filling(self) -> None:
        filling = fill(self.kl, self.target, count=3)
        self.client.post(movement_url(filling), {"note": "doppelt"})
        self.assertEqual(fresh(self.target).quantity, 3)

    def test_a_note_is_required(self) -> None:
        before = snapshot()
        self.refused(self.client.post(movement_url(self.delivery),
                                      {"note": ""}), "note")
        self.assertEqual(snapshot(), before)

    def test_a_second_reversal_changes_nothing(self) -> None:
        self.client.post(movement_url(self.delivery), {"note": "x"})
        before = snapshot()
        self.client.post(movement_url(self.delivery), {"note": "y"})
        self.assertEqual(snapshot(), before)
        self.assertEqual(self.target.movements.filter(
            kind="reversal").count(), 1)

    def test_a_filling_whose_containers_are_gone_changes_nothing(
            self) -> None:
        filling = fill(self.kl, self.target, count=3)
        self.deliver(self.target, 5)
        before = snapshot()
        self.client.post(movement_url(filling), {"note": "x"})
        self.assertEqual(snapshot(), before)

    def test_the_opening_cannot_be_reversed(self) -> None:
        opening = self.target.movements.get(kind="opening")
        before = snapshot()
        self.client.post(movement_url(opening), {"note": "x"})
        self.assertEqual(snapshot(), before)


class ConsumptionFormTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item()

    def url(self) -> str:
        return item_url(self.target, "consumption")

    def data(self, **over: str) -> dict[str, str]:
        data = {"year": "2026", "quarter": "2", "count": "4"}
        data.update(over)
        return data

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(self.url()))
        self.assertEqual(form_names(root, "year"),
                         {"year", "quarter", "count"})

    def test_entered_consumption_replaced(self) -> None:
        """Scenario: Entered consumption replaced."""
        done = self.client.post(self.url(), self.data(count="4"))
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.client.post(self.url(), self.data(count="5"))
        entered = EnteredConsumption.objects.get(item=self.target)
        self.assertEqual((entered.year, entered.quarter, entered.count),
                         (2026, 2, 5))
        self.assertMessageNames(done, "CH-0001", "Probe")

    def test_an_empty_count_removes_the_value(self) -> None:
        self.client.post(self.url(), self.data(count="4"))
        self.client.post(self.url(), self.data(count="4", quarter="3"))
        done = self.client.post(self.url(), self.data(count=""))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(
            list(EnteredConsumption.objects.values_list("quarter", "count")),
            [(3, 4)])

    def test_zero_is_a_value(self) -> None:
        self.client.post(self.url(), self.data(count="0"))
        self.assertEqual(EnteredConsumption.objects.get().count, 0)

    def test_refused_fields(self) -> None:
        before = snapshot()
        for field, value in (("count", "-1"), ("count", "x"),
                             ("quarter", "0"), ("quarter", "5"),
                             ("quarter", ""), ("year", ""),
                             ("year", "x")):
            with self.subTest(field=field, value=value):
                self.refused(self.client.post(
                    self.url(), self.data(**{field: value})), field)
        self.assertEqual(snapshot(), before)

    def test_a_quarter_with_historical_notes_is_refused(self) -> None:
        book_note(self.kl, date=date(2025, 3, 12), historical=True,
                  lines=[(self.target, 4)])
        before = snapshot()
        self.refused(self.client.post(self.url(), self.data(
            year="2025", quarter="1")))
        self.assertEqual(snapshot(), before)
        self.client.post(self.url(), self.data(year="2025", quarter="2"))
        self.assertEqual(EnteredConsumption.objects.count(), 1)

    def test_it_changes_no_quantity(self) -> None:
        self.client.post(self.url(), self.data())
        self.assertEqual(fresh(self.target).quantity, 5)
        self.assertEqual(self.target.movements.count(), 1)


class NewLotTests(FormCase):

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = form_names(page(self.client.get(NEW_LOT)), "article_number")
        self.assertEqual(names, {"article_number", "unit", "amount", "batch",
                                 "location", "made_on", "note"})

    def test_the_article_number_comes_from_the_url(self) -> None:
        root = page(self.client.get(f"{NEW_LOT}?article=CH-0012"))
        self.assertEqual(field_value(root, "article_number"), "CH-0012")

    def test_the_article_number_offers_the_compounds(self) -> None:
        options = datalist(page(self.client.get(NEW_LOT)), "article_number")
        self.assertEqual(options["CH-0012"], "(E)-Zimtsäure")

    def test_the_location_offers_the_locations_in_use(self) -> None:
        self.lot("A-1", location="Kühlraum")
        self.lot("A-2", location="Regal 3")
        self.lot("A-3", location="Kühlraum")
        self.lot("A-4")
        options = datalist(page(self.client.get(NEW_LOT)), "location")
        self.assertEqual(set(options) - {""}, {"Kühlraum", "Regal 3"})

    def test_new_bulk_lot(self) -> None:
        done = self.client.post(NEW_LOT, lot_data(
            batch="B-1", location="Kühlraum", made_on="2026-10-01",
            note="Rest"))
        lot = Lot.objects.get()
        self.assertRedirects(done, lot_url(lot),
                             fetch_redirect_response=False)
        self.assertEqual(
            (lot.inventory, lot.article_number, lot.unit, lot.batch,
             lot.location, lot.made_on, lot.note),
            ("end-products", "CH-0012", "mg", "B-1", "Kühlraum",
             date(2026, 10, 1), "Rest"))
        self.assertEqual(lot.amount, Decimal("50"))
        movement = lot.movements.get()
        self.assertEqual((movement.kind, movement.amount,
                          movement.amount_after, movement.user),
                         ("opening", Decimal("50"), Decimal("50"),
                          self.kl))
        self.assertMessageNames(done, "CH-0012", "B-1")

    def test_the_amount_is_in_the_unit_of_the_lot(self) -> None:
        cases = [("g", "1", "1000"), ("mmol", "2,5", "2500"),
                 ("umol", "5", "5"), ("mg", "47,5", "47.5")]
        for unit, amount, base in cases:
            with self.subTest(unit=unit):
                self.client.post(NEW_LOT, lot_data(
                    unit=unit, amount=amount, article_number=f"U-{unit}"))
                lot = Lot.objects.get(article_number=f"U-{unit}")
                self.assertEqual(lot.unit, unit)
                self.assertEqual(lot.amount, Decimal(base))

    def test_refused_fields(self) -> None:
        cases = {"article_number": [""], "unit": ["", "kg"],
                 "amount": ["", "-1", "x"], "batch": ["b" * 101],
                 "location": ["l" * 101], "made_on": ["x", "2026-13-01"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.refused(self.client.post(
                        NEW_LOT, lot_data(**{field: value})), field)
        self.assertEqual(Lot.objects.count(), 0)
        self.assertEqual(LotMovement.objects.count(), 0)

    def test_the_form_keeps_what_was_typed(self) -> None:
        done = self.client.post(NEW_LOT, lot_data(batch="B-9", amount="-1"))
        self.assertEqual(field_value(page(done), "batch"), "B-9")
        self.assertEqual(sent_messages(done), [])

    def test_a_lot_of_zero_may_be_entered(self) -> None:
        self.client.post(NEW_LOT, lot_data(amount="0"))
        self.assertEqual(Lot.objects.get().amount, 0)


class LotEditTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.lot("CH-0012", "mg", "50", batch="B-1",
                               location="Alt", made_on=date(2026, 10, 1),
                               note="alt")

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(lot_url(self.target, "edit")))
        self.assertEqual(form_names(root, "batch"),
                         {"batch", "location", "made_on", "note"})
        self.assertEqual(field_value(root, "batch"), "B-1")
        self.assertEqual(field_value(root, "location"), "Alt")
        self.assertEqual(field_value(root, "note"), "alt")

    def test_changing_a_lot(self) -> None:
        self.client.force_login(self.ae)
        done = self.client.post(lot_url(self.target, "edit"), {
            "batch": "B-2", "location": "Neu", "made_on": "2026-09-01",
            "note": "neu"})
        self.assertRedirects(done, lot_url(self.target),
                             fetch_redirect_response=False)
        lot = fresh(self.target)
        self.assertEqual((lot.batch, lot.location, lot.made_on, lot.note),
                         ("B-2", "Neu", date(2026, 9, 1), "neu"))
        self.assertEqual(lot.history.count(), 2)
        self.assertEqual(lot.history.first().history_user, self.ae)
        self.assertMessageNames(done, "CH-0012", "B-2")

    def test_article_unit_and_amount_are_fixed(self) -> None:
        self.client.post(lot_url(self.target, "edit"), {
            "batch": "B-2", "location": "", "made_on": "", "note": "",
            "article_number": "CH-9999", "unit": "g", "amount": "7"})
        lot = fresh(self.target)
        self.assertEqual(
            (lot.article_number, lot.unit, lot.amount, lot.batch),
            ("CH-0012", "mg", Decimal("50"), "B-2"))
        self.assertEqual(lot.movements.count(), 1)

    def test_a_refused_edit_changes_nothing(self) -> None:
        before = snapshot()
        self.refused(self.client.post(lot_url(self.target, "edit"), {
            "batch": "b" * 101, "location": "", "made_on": "",
            "note": ""}), "batch")
        self.assertEqual(snapshot(), before)


class LotCorrectionFormTests(FormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.lot("CH-0012", "mg", "50")

    def data(self, **over: str) -> dict[str, str]:
        data = {"amount": "47,5", "date": TODAY.isoformat(),
                "note": "nachgewogen"}
        data.update(over)
        return data

    def url(self) -> str:
        return lot_url(self.target, "correct")

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = form_names(page(self.client.get(self.url())), "amount")
        self.assertEqual(names, {"amount", "date", "note"})

    def test_correction_of_a_lot(self) -> None:
        """Scenario: Correction of a lot (the form)."""
        done = self.client.post(self.url(), self.data())
        self.assertRedirects(done, lot_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.target).amount, Decimal("47.5"))
        newest = self.target.movements.order_by("-pk").first()
        self.assertEqual((newest.kind, newest.note, newest.user),
                         ("correction", "nachgewogen", self.kl))
        self.assertMessageNames(done, "CH-0012")

    def test_the_amount_is_in_the_unit_of_the_lot(self) -> None:
        lot = self.lot("X-1", "g", "1")
        self.client.post(lot_url(lot, "correct"), self.data(amount="0,5"))
        self.assertEqual(fresh(lot).amount, Decimal("500"))

    def test_a_note_is_required(self) -> None:
        before = snapshot()
        self.refused(self.client.post(self.url(), self.data(note="")),
                     "note")
        self.assertEqual(snapshot(), before)

    def test_refused_fields(self) -> None:
        before = snapshot()
        for field, value in (("amount", "-1"), ("amount", "x"),
                             ("amount", ""), ("date", "2026-11-05")):
            with self.subTest(field=field, value=value):
                self.refused(self.client.post(
                    self.url(), self.data(**{field: value})), field)
        self.assertEqual(snapshot(), before)


class StaleEditTests(FormCase):
    """An edit of a record's metadata keeps the count, amount or state
    a booking changed after the record was loaded."""

    def test_an_item_edit_keeps_a_delivery_booked_meanwhile(self) -> None:
        from inventory.forms import ItemEditForm
        item = self.item(quantity=5)
        form = ItemEditForm({"name": "Neu", "category": "", "note": "",
                             "status": "active"}, instance=fresh(item))
        self.assertTrue(form.is_valid())
        self.deliver(item, 2)
        form.save()
        self.assertEqual(fresh(item).quantity, 3)
        self.assertEqual(fresh(item).name, "Neu")

    def test_a_lot_edit_keeps_a_correction_booked_meanwhile(self) -> None:
        from inventory.bookings import correct_lot
        from inventory.forms import LotEditForm
        lot = self.lot(amount="50")
        form = LotEditForm({"batch": "B-1", "location": "", "made_on": "",
                            "note": ""}, instance=fresh(lot))
        self.assertTrue(form.is_valid())
        correct_lot(self.kl, lot, amount=Decimal("40"), note="gewogen")
        form.save()
        self.assertEqual(fresh(lot).amount, Decimal("40"))
        self.assertEqual(fresh(lot).batch, "B-1")

    def test_a_note_edit_keeps_a_reversal_booked_meanwhile(self) -> None:
        from inventory.bookings import reverse_historical
        from inventory.forms import NoteEditForm
        item = self.item()
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         lines=[(item, 4)])
        form = NoteEditForm({"number": "", "recipient": "Produktion",
                             "note": ""}, instance=fresh(note))
        self.assertTrue(form.is_valid())
        reverse_historical(self.kl, note, note="falsch")
        form.save()
        self.assertTrue(fresh(note).reversed)
        self.assertEqual(fresh(note).recipient, "Produktion")
