"""Tests of the inventory in the admin (end-product-inventory: Inventory
in the admin)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import book_note, correct, create_lot, fill
from inventory.models import (DeliveryNote, Item, Lot, LotMovement,
                              Movement)

from . import make_item, make_user, page
from .inventory_support import InventoryCase

ADMIN = "/lab/admin/inventory/"
ITEMS = ADMIN + "item/"
LOTS = ADMIN + "lot/"
NOTES = ADMIN + "deliverynote/"
MOVEMENTS = ADMIN + "movement/"


def editable(response) -> set[str]:
    """The names of the controls a page offers for editing."""
    root = page(response)
    return {e.get("name") for e in
            root.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in (
                "submit", "hidden", "button")}


class AdminCase(InventoryCase):

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.worker = make_user("lab-worker-xy", "XY")

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.staff)

    def stocked(self, article: str = "CH-0012", name: str = "Zimtsäure",
                quantity: int = 9) -> Item:
        return make_item(self.worker, article, name, quantity=quantity)

    def delete(self, base: str, record) -> int:
        return self.client.post(f"{base}{record.pk}/delete/",
                                {"post": "yes"}).status_code


class AccessTests(AdminCase):

    def test_staff_enter(self) -> None:
        for path in (ITEMS, LOTS, NOTES, MOVEMENTS):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_anonymous_users_are_sent_to_the_admin_sign_in(self) -> None:
        self.client.logout()
        for path in (ITEMS, LOTS, NOTES, MOVEMENTS):
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertEqual(done.status_code, 302)
                self.assertTrue(
                    done["Location"].startswith("/lab/admin/login/"))

    def test_users_without_staff_status_are_kept_out(self) -> None:
        self.client.force_login(self.worker)
        for path in (ITEMS, LOTS, NOTES, MOVEMENTS):
            with self.subTest(path=path):
                done = self.client.get(path)
                self.assertIn(done.status_code, (302, 403))
                if done.status_code == 302:
                    self.assertTrue(
                        done["Location"].startswith("/lab/admin/login/"))


class ListTests(AdminCase):

    def test_items_are_listed(self) -> None:
        self.stocked("CH-0012", "Zimtsäure")
        self.stocked("CH-0013", "Benzaldehyd")
        text = self.client.get(ITEMS).content.decode("utf-8")
        self.assertIn("CH-0012", text)
        self.assertIn("CH-0013", text)

    def test_search_items_by_article_number(self) -> None:
        self.stocked("CH-0012", "Zimtsäure")
        self.stocked("CH-0013", "Benzaldehyd")
        text = self.client.get(f"{ITEMS}?q=ch-0013").content.decode()
        self.assertIn("CH-0013", text)
        self.assertNotIn("CH-0012", text)

    def test_search_items_by_name(self) -> None:
        self.stocked("CH-0012", "Zimtsäure")
        self.stocked("CH-0013", "Benzaldehyd")
        text = self.client.get(f"{ITEMS}?q=benzald").content.decode()
        self.assertIn("CH-0013", text)
        self.assertNotIn("CH-0012", text)

    def test_search_lots_by_article_number(self) -> None:
        self.lot("CH-0012", batch="B-ONE")
        self.lot("CH-0013", batch="B-TWO")
        text = self.client.get(f"{LOTS}?q=ch-0013").content.decode()
        self.assertIn("CH-0013", text)
        self.assertNotIn("CH-0012", text)

    def test_movements_and_notes_are_listed(self) -> None:
        item = self.stocked()
        self.deliver(item, 2, number="LS-ADMIN-1")
        self.assertIn("LS-ADMIN-1",
                      self.client.get(NOTES).content.decode())
        done = self.client.get(MOVEMENTS)
        self.assertEqual(done.status_code, 200)
        self.assertIn("CH-0012", done.content.decode())


class HistoryTests(AdminCase):

    def test_the_change_history_of_an_item(self) -> None:
        item = self.stocked()
        done = self.client.get(f"{ITEMS}{item.pk}/history/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-xy", done.content.decode("utf-8"))

    def test_the_change_history_of_a_lot(self) -> None:
        lot = create_lot(self.worker, article_number="CH-0012", unit="mg",
                         amount=Decimal("5"))
        done = self.client.get(f"{LOTS}{lot.pk}/history/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-xy", done.content.decode("utf-8"))

    def test_the_change_history_of_a_note(self) -> None:
        item = self.stocked()
        note = book_note(self.worker, date=date(2026, 11, 4),
                         lines=[(item, 1)])
        done = self.client.get(f"{NOTES}{note.pk}/history/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("lab-worker-xy", done.content.decode("utf-8"))


class ReadOnlyTests(AdminCase):

    def test_the_fixed_fields_of_an_item_are_read_only(self) -> None:
        item = self.stocked()
        names = editable(self.client.get(f"{ITEMS}{item.pk}/change/"))
        self.assertIn("name", names)
        for fixed in ("article_number", "size", "unit", "quantity"):
            with self.subTest(field=fixed):
                self.assertNotIn(fixed, names)

    def test_the_item_page_shows_its_fixed_fields(self) -> None:
        item = self.stocked("CH-0012")
        text = self.client.get(
            f"{ITEMS}{item.pk}/change/").content.decode("utf-8")
        self.assertIn("CH-0012", text)

    def test_the_fixed_fields_of_a_lot_are_read_only(self) -> None:
        lot = self.lot("CH-0012", batch="B-1")
        names = editable(self.client.get(f"{LOTS}{lot.pk}/change/"))
        self.assertIn("batch", names)
        for fixed in ("article_number", "unit", "amount"):
            with self.subTest(field=fixed):
                self.assertNotIn(fixed, names)

    def test_a_note_keeps_its_date_kind_and_lines(self) -> None:
        item = self.stocked()
        note = self.deliver(item, 1, number="LS-1")
        done = self.client.get(f"{NOTES}{note.pk}/change/")
        self.assertEqual(done.status_code, 200)
        names = editable(done)
        self.assertIn("number", names)
        self.assertIn("recipient", names)
        self.assertNotIn("date", names)
        self.assertNotIn("historical", names)
        self.assertFalse([n for n in names if n.startswith("lines")], names)
        self.assertIn("CH-0012", done.content.decode("utf-8"))

    def test_a_movement_is_shown_and_not_editable(self) -> None:
        item = self.stocked()
        movement = item.movements.get()
        done = self.client.get(f"{MOVEMENTS}{movement.pk}/change/")
        self.assertEqual(done.status_code, 200)
        self.assertEqual(editable(done), set())

    def test_a_posted_change_of_a_movement_is_ignored(self) -> None:
        item = self.stocked()
        correct(self.worker, item, count=4, note="gezählt")
        movement = item.movements.get(kind="correction")
        self.client.post(f"{MOVEMENTS}{movement.pk}/change/", {
            "note": "geändert", "count": "99", "quantity_after": "99"})
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual((movement.note, movement.count), ("gezählt", 4))
        self.assertEqual(Item.objects.get(pk=item.pk).quantity, 4)

    def test_a_posted_change_of_the_fixed_fields_is_ignored(self) -> None:
        item = self.stocked()
        self.client.post(f"{ITEMS}{item.pk}/change/", {
            "name": "Neu", "article_number": "CH-9999", "size": "99",
            "unit": "g", "quantity": "77"})
        item = Item.objects.get(pk=item.pk)
        self.assertEqual(
            (item.article_number, item.unit, item.quantity),
            ("CH-0012", "umol", 9))
        self.assertEqual(str(item.size), "10.000")


class DeletionTests(AdminCase):

    def test_deleting_a_booked_item(self) -> None:
        """Scenario: Deleting a booked item."""
        item = self.stocked()
        self.deliver(item, 1)
        self.delete(ITEMS, item)
        self.assertTrue(Item.objects.filter(pk=item.pk).exists())
        self.assertEqual(item.movements.count(), 2)

    def test_an_item_with_a_correction_or_filling_stays(self) -> None:
        for number, action in enumerate((
                lambda item: correct(self.worker, item, count=3, note="x"),
                lambda item: fill(self.worker, item, count=1))):
            with self.subTest(action=number):
                item = self.stocked(f"CH-1{number}")
                action(item)
                self.delete(ITEMS, item)
                self.assertTrue(Item.objects.filter(pk=item.pk).exists())

    def test_an_item_with_a_line_of_a_historical_note_stays(self) -> None:
        item = self.stocked()
        book_note(self.worker, date=date(2025, 3, 12), historical=True,
                  lines=[(item, 1)])
        self.delete(ITEMS, item)
        self.assertTrue(Item.objects.filter(pk=item.pk).exists())

    def test_an_item_with_only_its_opening_count_is_deleted(self) -> None:
        item = self.stocked()
        other = self.stocked("CH-0013")
        self.assertEqual(self.delete(ITEMS, item), 302)
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())
        self.assertFalse(Movement.objects.filter(item_id=item.pk).exists())
        self.assertTrue(Item.objects.filter(pk=other.pk).exists())
        self.assertEqual(other.movements.count(), 1)

    def test_the_bulk_action_does_not_delete_a_booked_item(self) -> None:
        item = self.stocked()
        self.deliver(item, 1)
        self.client.post(ITEMS, {"action": "delete_selected",
                                 "_selected_action": [item.pk],
                                 "post": "yes"})
        self.assertTrue(Item.objects.filter(pk=item.pk).exists())

    def test_a_lot_with_only_its_opening_is_deleted(self) -> None:
        lot = self.lot("CH-0012")
        self.assertEqual(self.delete(LOTS, lot), 302)
        self.assertFalse(Lot.objects.filter(pk=lot.pk).exists())
        self.assertFalse(LotMovement.objects.filter(lot_id=lot.pk).exists())

    def test_a_lot_with_a_filling_stays(self) -> None:
        item = self.stocked()
        lot = self.lot("CH-0012", "mg", "50")
        fill(self.worker, item, count=1, lot=lot)
        self.delete(LOTS, lot)
        self.assertTrue(Lot.objects.filter(pk=lot.pk).exists())
        self.assertEqual(lot.movements.count(), 2)

    def test_the_bulk_action_does_not_delete_a_used_lot(self) -> None:
        item = self.stocked()
        lot = self.lot("CH-0012", "mg", "50")
        fill(self.worker, item, count=1, lot=lot)
        self.client.post(LOTS, {"action": "delete_selected",
                                "_selected_action": [lot.pk],
                                "post": "yes"})
        self.assertTrue(Lot.objects.filter(pk=lot.pk).exists())

    def test_a_delivery_note_is_never_deleted(self) -> None:
        item = self.stocked()
        note = self.deliver(item, 1)
        historical = book_note(self.worker, date=date(2025, 3, 12),
                               historical=True, lines=[(item, 1)])
        for each in (note, historical):
            with self.subTest(historical=each.historical):
                self.assertNotEqual(self.delete(NOTES, each), 302)
                self.client.post(NOTES, {"action": "delete_selected",
                                         "_selected_action": [each.pk],
                                         "post": "yes"})
                self.assertTrue(
                    DeliveryNote.objects.filter(pk=each.pk).exists())

    def test_a_movement_is_never_deleted(self) -> None:
        item = self.stocked()
        self.deliver(item, 1)
        for movement in item.movements.all():
            with self.subTest(kind=movement.kind):
                self.assertIn(self.delete(MOVEMENTS, movement), (403, 404))
                self.client.post(MOVEMENTS, {
                    "action": "delete_selected",
                    "_selected_action": [movement.pk], "post": "yes"})
                self.assertTrue(
                    Movement.objects.filter(pk=movement.pk).exists())

    def test_a_lot_movement_is_never_deleted(self) -> None:
        lot = self.lot("CH-0012")
        movement = lot.movements.get()
        done = self.client.post(f"{ADMIN}lotmovement/{movement.pk}/delete/",
                                {"post": "yes"})
        self.assertIn(done.status_code, (403, 404))
        self.assertTrue(LotMovement.objects.filter(pk=movement.pk).exists())


class HistoryRestoreTests(AdminCase):
    """Old versions are shown, never restored."""

    def test_an_old_version_of_a_note_is_not_restored(self) -> None:
        from inventory.bookings import reverse_historical
        item = self.stocked()
        note = book_note(self.worker, date=date(2025, 3, 12),
                         historical=True, lines=[(item, 4)])
        reverse_historical(self.worker, note, note="falsch")
        first = note.history.order_by("history_id").first()
        url = f"{NOTES}{note.pk}/history/{first.history_id}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        done = self.client.post(url, {"number": "", "recipient": "",
                                      "note": ""})
        self.assertEqual(done.status_code, 403)
        self.assertTrue(DeliveryNote.objects.get(pk=note.pk).reversed)

    def test_a_deleted_item_is_not_restored(self) -> None:
        item = self.stocked()
        record = item.history.order_by("history_id").first()
        self.assertIn(self.delete(ITEMS, item), (200, 302))
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())
        done = self.client.post(
            f"{ITEMS}{item.pk}/history/{record.history_id}/",
            {"name": item.name, "category": "", "note": ""})
        self.assertEqual(done.status_code, 403)
        self.assertFalse(Item.objects.filter(pk=item.pk).exists())


class DeletionCheckTests(AdminCase):
    """The deletion itself checks that nothing but the opening was
    booked, whatever the page showed before."""

    def request(self):
        from django.test import RequestFactory
        request = RequestFactory().post("/")
        request.user = self.staff
        return request

    def test_an_item_booked_after_the_check_is_not_deleted(self) -> None:
        from django.contrib import admin
        from django.core.exceptions import PermissionDenied
        item = self.stocked()
        correct(self.worker, item, count=3, note="gezählt")
        with self.assertRaises(PermissionDenied):
            admin.site._registry[Item].delete_model(self.request(), item)
        self.assertTrue(Item.objects.filter(pk=item.pk).exists())
        self.assertEqual(Movement.objects.filter(item=item).count(), 2)

    def test_a_lot_booked_after_the_check_is_not_deleted(self) -> None:
        from django.contrib import admin
        from django.core.exceptions import PermissionDenied
        from inventory.bookings import correct_lot
        lot = create_lot(self.worker, article_number="CH-0012", unit="mg",
                         amount=Decimal("50"))
        spare = create_lot(self.worker, article_number="CH-0012",
                           unit="mg", amount=Decimal("5"))
        correct_lot(self.worker, lot, amount=Decimal("40"), note="gewogen")
        with self.assertRaises(PermissionDenied):
            admin.site._registry[Lot].delete_queryset(
                self.request(), Lot.objects.filter(pk__in=[lot.pk,
                                                           spare.pk]))
        self.assertEqual(Lot.objects.count(), 2)
        self.assertEqual(LotMovement.objects.count(), 3)
