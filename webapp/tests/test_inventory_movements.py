"""Tests of the movements of an item's containers (end-product-inventory:
Item movements)."""

from datetime import date

from inventory.bookings import (Refused, book_note, correct, fill, reverse,
                                reverse_historical)
from inventory.models import DeliveryNote, Item, Movement

from .inventory_support import (InventoryCase, TODAY, fresh, newest_movement,
                                snapshot)


class RefusedTests(InventoryCase):

    def test_a_refusal_is_a_validation_error(self) -> None:
        from django.core.exceptions import ValidationError
        self.assertTrue(issubclass(Refused, ValidationError))


class DeliveryTests(InventoryCase):

    def test_delivery(self) -> None:
        """Scenario: Delivery."""
        item = self.item(quantity=5)
        note = book_note(self.kl, date=TODAY, number="LS-2026-117",
                         recipient="Produktion", lines=[(item, 2)])
        self.assertEqual(fresh(item).quantity, 3)
        movement = newest_movement(item)
        self.assertEqual(movement.kind, Movement.Kind.DELIVERY)
        self.assertEqual((movement.count, movement.quantity_after), (2, 3))
        self.assertEqual(movement.user, self.kl)
        self.assertEqual(movement.delivery_note, note)
        self.assertEqual(movement.date, TODAY)
        self.assertIsNotNone(movement.booked_at)
        self.assertIsNone(movement.reverses)
        self.assertIsNone(movement.bulk_movement)

    def test_the_note_is_stored_with_its_fields(self) -> None:
        item = self.item()
        made = book_note(self.kl, date=date(2026, 10, 15), number="LS-1",
                         recipient="Produktion", note="Eilig",
                         lines=[(item, 2)])
        note = DeliveryNote.objects.get(pk=made.pk)
        self.assertEqual(
            (note.number, note.date, note.recipient, note.note),
            ("LS-1", date(2026, 10, 15), "Produktion", "Eilig"))
        self.assertFalse(note.historical)
        self.assertFalse(note.reversed)
        self.assertEqual(note.created_by, self.kl)
        self.assertIsNotNone(note.created_at)
        line = note.lines.get()
        self.assertEqual((line.item, line.count), (item, 2))

    def test_the_movement_is_dated_as_the_note(self) -> None:
        item = self.item()
        self.deliver(item, 2, date(2026, 8, 12))
        self.assertEqual(newest_movement(item).date, date(2026, 8, 12))

    def test_the_whole_quantity_may_be_delivered(self) -> None:
        item = self.item(quantity=5)
        self.deliver(item, 5)
        self.assertEqual(fresh(item).quantity, 0)
        self.assertEqual(newest_movement(item).quantity_after, 0)

    def test_more_than_the_quantity_is_refused(self) -> None:
        item = self.item(quantity=5)
        before = snapshot()
        with self.assertRaises(Refused):
            self.deliver(item, 6)
        self.assertEqual(snapshot(), before)

    def test_a_count_of_zero_or_less_is_refused(self) -> None:
        item = self.item(quantity=5)
        before = snapshot()
        for count in (0, -1):
            with self.subTest(count=count), self.assertRaises(Refused):
                self.deliver(item, count)
        self.assertEqual(snapshot(), before)

    def test_a_note_dated_after_today_is_refused(self) -> None:
        item = self.item()
        before = snapshot()
        with self.assertRaises(Refused):
            self.deliver(item, 1, date(2026, 11, 5))
        self.assertEqual(snapshot(), before)

    def test_the_quantity_of_a_stale_instance_is_not_trusted(self) -> None:
        item = self.item(quantity=5)
        item.quantity = 100
        before = snapshot()
        with self.assertRaises(Refused):
            self.deliver(item, 6)
        self.assertEqual(snapshot(), before)
        item.quantity = 0
        self.deliver(item, 2)
        self.assertEqual(fresh(item).quantity, 3)

    def test_concurrent_deliveries(self) -> None:
        """Scenario: Concurrent deliveries."""
        item = self.item(quantity=5)
        first, second = Item.objects.get(pk=item.pk), \
            Item.objects.get(pk=item.pk)
        self.assertEqual((first.quantity, second.quantity), (5, 5))
        self.deliver(first, 4)
        before = snapshot()
        with self.assertRaises(Refused):
            self.deliver(second, 4)
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(item).quantity, 1)
        self.assertEqual(item.movements.filter(kind="delivery").count(), 1)
        self.assertEqual(DeliveryNote.objects.count(), 1)

    def test_the_movements_keep_their_booking_order(self) -> None:
        item = self.item(quantity=9)
        self.deliver(item, 1, date(2026, 10, 15))
        self.deliver(item, 2, date(2026, 8, 1))
        counts = [m.quantity_after for m in item.movements.order_by("pk")]
        self.assertEqual(counts, [9, 8, 6])
        booked = [m.booked_at for m in item.movements.order_by("pk")]
        self.assertEqual(booked, sorted(booked))


class FillingTests(InventoryCase):

    def test_a_filling_adds_containers(self) -> None:
        item = self.item(quantity=2)
        movement = fill(self.kl, item, count=5, note="Charge 7")
        self.assertEqual(fresh(item).quantity, 7)
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual(movement.item, item)
        self.assertEqual(movement.kind, Movement.Kind.FILLING)
        self.assertEqual((movement.count, movement.quantity_after), (5, 7))
        self.assertEqual((movement.user, movement.note),
                         (self.kl, "Charge 7"))
        self.assertEqual(movement.date, TODAY)
        self.assertIsNone(movement.bulk_movement)
        self.assertIsNone(movement.delivery_note)

    def test_the_date_may_be_given(self) -> None:
        item = self.item()
        movement = fill(self.kl, item, count=1, date=date(2026, 9, 1))
        self.assertEqual(movement.date, date(2026, 9, 1))

    def test_a_count_of_zero_or_less_is_refused(self) -> None:
        item = self.item()
        before = snapshot()
        for count in (0, -3):
            with self.subTest(count=count), self.assertRaises(Refused):
                fill(self.kl, item, count=count)
        self.assertEqual(snapshot(), before)

    def test_a_date_after_today_is_refused(self) -> None:
        item = self.item()
        before = snapshot()
        with self.assertRaises(Refused):
            fill(self.kl, item, count=1, date=date(2026, 11, 5))
        self.assertEqual(snapshot(), before)

    def test_the_quantity_of_a_stale_instance_is_not_trusted(self) -> None:
        item = self.item(quantity=5)
        item.quantity = 100
        fill(self.kl, item, count=1)
        self.assertEqual(fresh(item).quantity, 6)
        self.assertEqual(newest_movement(item).quantity_after, 6)


class CorrectionTests(InventoryCase):

    def test_a_correction_sets_the_counted_quantity(self) -> None:
        item = self.item(quantity=5)
        movement = correct(self.kl, item, count=4, note="nachgezählt")
        self.assertEqual(fresh(item).quantity, 4)
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual(movement.kind, Movement.Kind.CORRECTION)
        self.assertEqual((movement.count, movement.quantity_after), (4, 4))
        self.assertEqual((movement.user, movement.note),
                         (self.kl, "nachgezählt"))
        self.assertEqual(movement.date, TODAY)

    def test_a_correction_may_raise_the_quantity_or_empty_it(self) -> None:
        item = self.item(quantity=5)
        correct(self.kl, item, count=9, note="mehr gefunden")
        self.assertEqual(fresh(item).quantity, 9)
        correct(self.kl, item, count=0, note="leer")
        self.assertEqual(fresh(item).quantity, 0)

    def test_a_note_is_required(self) -> None:
        item = self.item(quantity=5)
        before = snapshot()
        with self.assertRaises(Refused):
            correct(self.kl, item, count=4, note="")
        self.assertEqual(snapshot(), before)

    def test_a_negative_count_is_refused(self) -> None:
        item = self.item(quantity=5)
        before = snapshot()
        with self.assertRaises(Refused):
            correct(self.kl, item, count=-1, note="x")
        self.assertEqual(snapshot(), before)

    def test_the_date_may_be_given_but_not_after_today(self) -> None:
        item = self.item(quantity=5)
        movement = correct(self.kl, item, count=4, note="x",
                           date=date(2026, 11, 1))
        self.assertEqual(movement.date, date(2026, 11, 1))
        before = snapshot()
        with self.assertRaises(Refused):
            correct(self.kl, item, count=3, note="x",
                    date=date(2026, 11, 5))
        self.assertEqual(snapshot(), before)


class ReversalTests(InventoryCase):

    def test_reversing_a_delivery(self) -> None:
        """Scenario: Reversing a delivery."""
        item = self.item(quantity=5)
        delivery = self.deliver_movement(item, 2, date(2026, 8, 12))
        self.assertEqual(fresh(item).quantity, 3)
        self.assertEqual(self.consumption(item).quarters[(2026, 3)], 2)
        movement = reverse(self.kl, delivery, note="falsch gebucht")
        self.assertEqual(fresh(item).quantity, 5)
        self.assertEqual(
            self.consumption(item).quarters.get((2026, 3), 0), 0)
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual(movement.kind, Movement.Kind.REVERSAL)
        self.assertEqual(movement.reverses, delivery)
        self.assertEqual(movement.quantity_after, 5)
        self.assertEqual((movement.user, movement.note),
                         (self.kl, "falsch gebucht"))
        self.assertEqual(movement.date, TODAY)
        self.assertEqual(Movement.objects.get(pk=delivery.pk).reversal,
                         movement)
        before = snapshot()
        with self.assertRaises(Refused):
            reverse(self.kl, delivery, note="noch einmal")
        self.assertEqual(snapshot(), before)

    def test_a_second_reversal_from_another_instance_is_refused(
            self) -> None:
        item = self.item(quantity=5)
        delivery = self.deliver_movement(item, 2)
        first = Movement.objects.get(pk=delivery.pk)
        second = Movement.objects.get(pk=delivery.pk)
        reverse(self.kl, first, note="falsch")
        with self.assertRaises(Refused):
            reverse(self.kl, second, note="falsch")
        self.assertEqual(fresh(item).quantity, 5)

    def test_the_note_of_the_delivery_keeps_its_line(self) -> None:
        item = self.item(quantity=5)
        delivery = self.deliver_movement(item, 2)
        reverse(self.kl, delivery, note="falsch")
        note = delivery.delivery_note
        self.assertEqual(note.lines.get().count, 2)
        self.assertEqual(Movement.objects.get(pk=delivery.pk).delivery_note,
                         note)

    def test_reversing_a_filling_takes_the_containers_back(self) -> None:
        item = self.item(quantity=0)
        filling = fill(self.kl, item, count=5)
        reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(item).quantity, 0)
        newest = newest_movement(item)
        self.assertEqual((newest.kind, newest.reverses, newest.quantity_after),
                         ("reversal", filling, 0))

    def test_a_filling_whose_containers_are_gone_is_refused(self) -> None:
        item = self.item(quantity=0)
        filling = fill(self.kl, item, count=5)
        self.deliver(item, 4)
        before = snapshot()
        with self.assertRaises(Refused):
            reverse(self.kl, filling, note="doppelt")
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(item).quantity, 1)

    def test_a_filling_still_there_may_be_reversed_after_deliveries(
            self) -> None:
        item = self.item(quantity=5)
        filling = fill(self.kl, item, count=3)
        self.deliver(item, 4)
        reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(item).quantity, 1)

    def test_a_note_is_required(self) -> None:
        item = self.item(quantity=5)
        delivery = self.deliver_movement(item, 2)
        before = snapshot()
        with self.assertRaises(Refused):
            reverse(self.kl, delivery, note="")
        self.assertEqual(snapshot(), before)

    def test_only_deliveries_and_fillings_can_be_reversed(self) -> None:
        item = self.item(quantity=5)
        opening = item.movements.get()
        correction = correct(self.kl, item, count=4, note="x")
        delivery = self.deliver_movement(item, 1)
        reversal = reverse(self.kl, delivery, note="x")
        before = snapshot()
        for movement in (opening, correction, reversal):
            with self.subTest(kind=movement.kind), \
                    self.assertRaises(Refused):
                reverse(self.kl, movement, note="x")
        self.assertEqual(snapshot(), before)

    def test_a_historical_note_has_no_movement_to_reverse(self) -> None:
        item = self.item(quantity=5)
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         lines=[(item, 2)])
        self.assertEqual(item.movements.count(), 1)
        reverse_historical(self.kl, note, note="falsch")
        self.assertEqual(item.movements.count(), 1)
        self.assertEqual(fresh(item).quantity, 5)
