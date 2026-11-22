"""Tests of the stock by batch: the shares an item keeps, the movements
that change them, the delivery lines that name a batch, and the readers
of those lines (end-product-inventory: Stock by batch, Items, Item
movements, Delivery notes)."""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import translation

from inventory.bookings import (Refused, book_note, correct, create_item,
                                fill, reverse, reverse_historical)
from inventory.figures import counted_lines
from inventory.models import (Batch, DeliveryLine, DeliveryNote, Item,
                              Movement)

from .inventory_support import (TODAY, BatchStock, InventoryCase, expected,
                                fresh, newest_movement, set_shares, share,
                                shares, stock_snapshot)


class StockCase(InventoryCase):
    """Two batches of ``cinnamic-acid``, ``KL0412`` and ``KL0413``, and
    helpers to put an item in a state and to read its shares."""

    def setUp(self) -> None:
        super().setUp()
        self.a = self.batch("CH-0012", number="KL0412")
        self.b = self.batch("CH-0012", number="KL0413")

    def holding(self, *pairs: tuple[Batch | None, int], size: str = "10",
                unit: str = "umol") -> Item:
        """An item of ``CH-0012`` holding PAIRS, each a batch, None for
        unknown, and its containers."""
        item = self.item("CH-0012", quantity=0, size=size, unit=unit)
        set_shares(item, *pairs)
        return item

    def assertConsistent(self, item: Item) -> None:
        """The quantity of ``item`` is the sum of its shares."""
        total = sum(BatchStock.objects.filter(item=item).values_list(
            "quantity", flat=True))
        self.assertEqual(fresh(item).quantity, total)

    def assertShares(self, item: Item, *pairs: tuple[Batch | None, int]
                     ) -> None:
        """``item`` holds PAIRS, each a batch, None for unknown, and its
        containers, and no other containers; its quantity is their
        sum."""
        self.assertEqual(shares(item), expected(*pairs))
        self.assertEqual(fresh(item).quantity, sum(n for _, n in pairs))
        self.assertConsistent(item)

    def vessel_of(self, batch: Batch) -> Any:
        """A stored vessel of ``batch`` that holds enough for any
        filling of these tests."""
        return self.vessel("CH-0012", "g", "50", batch=batch)

    def newest(self, item: Item, count: int) -> list[Movement]:
        """The ``count`` newest movements of ``item``, newest first."""
        return list(item.movements.order_by("-pk")[:count])


class ShareModelTests(StockCase):

    def new_item(self, **extra: object) -> Item:
        from registry.models import Substance
        return create_item(
            self.kl, substance=Substance.objects.get(key="cinnamic-acid"),
            article_number="CH-0012", size=Decimal("10"), unit="umol",
            **{"quantity": 0, **extra})

    def test_a_new_item_has_its_share_of_unknown_batch(self) -> None:
        """Scenario: Opening count of unknown batch."""
        item = self.new_item(quantity=4)
        stock = BatchStock.objects.get(item=item)
        self.assertEqual((stock.batch, stock.quantity), (None, 4))
        opening = item.movements.get()
        self.assertEqual((opening.kind, opening.count, opening.batch),
                         ("opening", 4, None))
        self.assertShares(item, (None, 4))

    def test_an_item_without_containers_has_its_row_of_unknown_batch(
            self) -> None:
        item = self.new_item(quantity=0)
        self.assertEqual(
            list(BatchStock.objects.filter(item=item).values_list(
                "batch", "quantity")), [(None, 0)])

    def test_an_opening_count_goes_into_its_batch(self) -> None:
        """Scenario: Opening count of a batch (the booking)."""
        item = self.new_item(quantity=4, batch=self.a)
        self.assertShares(item, (self.a, 4))
        opening = item.movements.get()
        self.assertEqual((opening.kind, opening.count, opening.batch,
                          opening.quantity_after),
                         ("opening", 4, self.a, 4))
        self.assertEqual(
            BatchStock.objects.get(item=item, batch=None).quantity, 0)

    def test_the_batch_of_another_substance_is_refused(self) -> None:
        other = self.batch("acetophenone", number="AP1")
        before = stock_snapshot()
        with self.refusing("batch"):
            self.new_item(quantity=4, batch=other)
        self.assertEqual(Item.objects.count(), 0)
        self.assertEqual(stock_snapshot(), before)

    def test_a_batch_row_appears_with_the_first_booking_into_it(
            self) -> None:
        item = self.new_item(quantity=2)
        self.assertFalse(BatchStock.objects.filter(batch=self.a).exists())
        fill(self.kl, item, count=1, vessel=self.vessel_of(self.a),
             amount=Decimal("1"))
        self.assertEqual(BatchStock.objects.get(batch=self.a).item, item)

    def test_a_share_is_reached_from_its_item_and_its_batch(self) -> None:
        item = self.new_item(quantity=3, batch=self.a)
        self.assertEqual(
            {(s.batch_id, s.quantity) for s in item.stocks.all()},
            {(None, 0), (self.a.pk, 3)})
        self.assertEqual(self.a.stocks.get().item, item)
        self.assertEqual(list(self.a.item_movements.all()),
                         list(item.movements.all()))
        book_note(self.kl, date=TODAY, historical=True,
                  lines=[(item, self.a, 1)])
        self.assertEqual(self.a.delivery_lines.get().item, item)

    def test_a_batch_has_one_share_of_an_item(self) -> None:
        item = self.holding((self.a, 2))
        with self.assertRaises(IntegrityError), transaction.atomic():
            BatchStock.objects.create(item=item, batch=self.a, quantity=1)

    def test_an_item_has_one_share_of_unknown_batch(self) -> None:
        item = self.holding((None, 2))
        with self.assertRaises(IntegrityError), transaction.atomic():
            BatchStock.objects.create(item=item, batch=None, quantity=1)

    def test_a_batch_may_have_a_share_in_each_item(self) -> None:
        first = self.holding((self.a, 2))
        second = self.holding((self.a, 1), size="50")
        self.assertEqual(share(first, self.a), 2)
        self.assertEqual(share(second, self.a), 1)

    def test_a_share_is_never_negative(self) -> None:
        item = self.holding((self.a, 2))
        with self.assertRaises(IntegrityError), transaction.atomic():
            BatchStock.objects.filter(item=item, batch=self.a).update(
                quantity=-1)

    def test_a_batch_with_a_share_is_protected(self) -> None:
        self.holding((self.a, 0))
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.a.delete()

    def test_a_batch_a_movement_names_is_protected(self) -> None:
        item = self.new_item(quantity=1, batch=self.a)
        BatchStock.objects.filter(item=item).delete()
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.a.delete()

    def test_a_batch_a_line_names_is_protected(self) -> None:
        item = self.holding((self.a, 1))
        book_note(self.kl, date=TODAY, historical=True,
                  lines=[(item, self.a, 1)])
        BatchStock.objects.filter(item=item).delete()
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.a.delete()

    def test_the_shares_go_with_their_item(self) -> None:
        item = self.new_item(quantity=3, batch=self.a)
        item.delete()
        self.assertFalse(BatchStock.objects.exists())
        self.assertTrue(Batch.objects.filter(pk=self.a.pk).exists())

    def test_the_assignment_kind(self) -> None:
        self.assertEqual(Movement.Kind.ASSIGNMENT, "assignment")
        with translation.override("en"):
            self.assertEqual(str(Movement.Kind.ASSIGNMENT.label),
                             "Assignment")
        with translation.override("de"):
            self.assertEqual(str(Movement.Kind.ASSIGNMENT.label),
                             "Zuordnung")


class FillingShareTests(StockCase):

    def test_fillings_into_their_batches(self) -> None:
        """Scenario: Fillings into their batches."""
        item = self.item("CH-0012", quantity=0)
        first = fill(self.kl, item, count=3, vessel=self.vessel_of(self.a),
                     amount=Decimal("1"))
        second = fill(self.kl, item, count=2, vessel=self.vessel_of(self.b),
                      amount=Decimal("1"))
        self.assertShares(item, (self.a, 3), (self.b, 2), (None, 0))
        self.assertEqual((first.batch, second.batch), (self.a, self.b))
        self.assertEqual(second.quantity_after, 5)

    def test_a_filling_leaves_the_other_shares_alone(self) -> None:
        item = self.holding((None, 4), (self.b, 1))
        fill(self.kl, item, count=2, vessel=self.vessel_of(self.a),
             amount=Decimal("1"))
        self.assertShares(item, (None, 4), (self.b, 1), (self.a, 2))

    def test_reversing_a_filling_takes_it_from_its_batch(self) -> None:
        item = self.holding((None, 1))
        filling = fill(self.kl, item, count=2, vessel=self.vessel_of(self.a),
                       amount=Decimal("1"))
        book_note(self.kl, date=TODAY, lines=[(item, self.b, 1)])
        reversal = reverse(self.kl, filling, note="doppelt")
        self.assertShares(item)
        self.assertEqual((reversal.batch, reversal.quantity_after),
                         (self.a, 0))

    def test_a_filling_whose_batch_is_emptied_is_not_reversed(self) -> None:
        """Scenario: A filling's batch emptied."""
        item = self.holding((None, 3))
        filling = fill(self.kl, item, count=2, vessel=self.vessel_of(self.a),
                       amount=Decimal("1"))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 2)])
        with self.refusing(shares=True):
            reverse(self.kl, filling, note="doppelt")
        self.assertShares(item, (None, 3))

    def test_a_filling_is_not_reversed_when_a_delivery_took_some(
            self) -> None:
        item = self.holding((None, 3))
        filling = fill(self.kl, item, count=2, vessel=self.vessel_of(self.a),
                       amount=Decimal("1"))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 1)])
        with self.refusing(shares=True):
            reverse(self.kl, filling, note="doppelt")
        self.assertShares(item, (None, 3), (self.a, 1))


class DeliveryShareTests(StockCase):

    def test_a_delivery_takes_from_its_batch(self) -> None:
        item = self.holding((self.a, 4), (None, 5))
        note = book_note(self.kl, date=TODAY, number="LS-1",
                         lines=[(item, self.a, 3)])
        self.assertShares(item, (self.a, 1), (None, 5))
        delivery = newest_movement(item)
        self.assertEqual((delivery.kind, delivery.count, delivery.batch,
                          delivery.quantity_after, delivery.delivery_note),
                         ("delivery", 3, self.a, 6, note))
        self.assertFalse(item.movements.filter(kind="assignment").exists())

    def test_a_delivery_from_containers_of_unknown_batch(self) -> None:
        """Scenario: Delivery from containers of unknown batch."""
        item = self.holding((self.a, 1), (None, 5))
        note = book_note(self.kl, date=TODAY, number="LS-1",
                         lines=[(item, self.a, 3)])
        self.assertShares(item, (None, 3))
        delivery, assignment = self.newest(item, 2)
        self.assertEqual(
            (delivery.kind, delivery.count, delivery.quantity_after,
             delivery.batch, delivery.delivery_note),
            ("delivery", 3, 3, self.a, note))
        self.assertEqual(
            (assignment.kind, assignment.count, assignment.quantity_after,
             assignment.batch, assignment.delivery_note),
            ("assignment", 2, 6, self.a, note))
        self.assertLess(assignment.pk, delivery.pk)

    def test_the_assignment_is_dated_and_booked_as_its_note(self) -> None:
        item = self.holding((None, 5))
        note = book_note(self.kl, date=date(2026, 10, 15),
                         lines=[(item, self.a, 2)])
        delivery, assignment = self.newest(item, 2)
        self.assertEqual((assignment.date, delivery.date),
                         (note.date, note.date))
        self.assertEqual((assignment.user, delivery.user),
                         (self.kl, self.kl))
        self.assertIsNotNone(assignment.booked_at)
        self.assertIsNone(assignment.reverses)
        self.assertIsNone(assignment.vessel_movement)

    def test_the_whole_share_of_unknown_batch_may_be_assigned(self) -> None:
        item = self.holding((None, 2))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 2)])
        self.assertShares(item)
        delivery, assignment = self.newest(item, 2)
        self.assertEqual((assignment.count, delivery.count, delivery.kind),
                         (2, 2, "delivery"))

    def test_the_share_of_a_batch_stays_at_zero(self) -> None:
        item = self.holding((self.a, 2))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 2)])
        self.assertEqual(
            BatchStock.objects.get(item=item, batch=self.a).quantity, 0)

    def test_the_row_of_a_batch_is_made_by_the_assignment(self) -> None:
        item = self.holding((None, 3))
        self.assertFalse(BatchStock.objects.filter(batch=self.a).exists())
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 1)])
        self.assertEqual(
            BatchStock.objects.get(item=item, batch=self.a).quantity, 0)
        self.assertShares(item, (None, 2))

    def test_too_few_even_with_unknown_batch(self) -> None:
        """Scenario: Too few even with unknown batch."""
        item = self.holding((self.a, 1), (None, 1))
        with self.refusing("count", shares=True) as caught:
            book_note(self.kl, date=TODAY, lines=[(item, self.a, 3)])
        self.assertEqual(caught.exception.line, 0)
        self.assertEqual(DeliveryNote.objects.count(), 0)
        self.assertEqual(Movement.objects.filter(kind="assignment").count(),
                         0)
        self.assertShares(item, (self.a, 1), (None, 1))

    def test_a_refusal_leaves_no_row_of_the_batch(self) -> None:
        item = self.holding((None, 1))
        with self.refusing("count", shares=True):
            book_note(self.kl, date=TODAY, lines=[(item, self.b, 2)])
        self.assertFalse(BatchStock.objects.filter(batch=self.b).exists())

    def test_the_shares_of_other_batches_cannot_be_delivered(self) -> None:
        item = self.holding((self.b, 5))
        with self.refusing("count", shares=True):
            book_note(self.kl, date=TODAY, lines=[(item, self.a, 1)])

    def test_a_reversed_delivery_returns_to_its_batch(self) -> None:
        """Scenario: A reversed delivery returns to its batch."""
        item = self.holding((self.a, 1), (None, 5))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 3)])
        delivery = newest_movement(item)
        reversal = reverse(self.kl, delivery, note="falsch gebucht")
        self.assertShares(item, (self.a, 3), (None, 3))
        self.assertEqual((reversal.batch, reversal.quantity_after,
                          reversal.reverses), (self.a, 6, delivery))

    def test_a_reversal_leaves_the_assignment_in_place(self) -> None:
        item = self.holding((None, 5))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 3)])
        delivery, assignment = self.newest(item, 2)
        reverse(self.kl, delivery, note="falsch")
        self.assertTrue(Movement.objects.filter(pk=assignment.pk).exists())
        self.assertEqual(
            Movement.objects.filter(kind="assignment").count(), 1)
        self.assertShares(item, (self.a, 3), (None, 2))

    def test_an_assignment_is_not_reversed_on_its_own(self) -> None:
        item = self.holding((None, 5))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 3)])
        assignment = self.newest(item, 2)[1]
        self.assertEqual(assignment.kind, "assignment")
        self.assertFalse(assignment.reversible)
        with self.refusing(shares=True):
            reverse(self.kl, assignment, note="x")

    def test_concurrent_deliveries_of_one_batch(self) -> None:
        """Scenario: Concurrent deliveries of one batch."""
        item = self.holding((self.a, 5))
        first, second = Item.objects.get(pk=item.pk), \
            Item.objects.get(pk=item.pk)
        book_note(self.kl, date=TODAY, lines=[(first, self.a, 4)])
        with self.refusing("count", shares=True):
            book_note(self.kl, date=TODAY, lines=[(second, self.a, 4)])
        self.assertShares(item, (self.a, 1))
        self.assertEqual(item.movements.filter(kind="delivery").count(), 1)
        self.assertEqual(DeliveryNote.objects.count(), 1)

    def test_one_item_in_two_batches_in_one_note(self) -> None:
        item = self.holding((None, 5))
        note = book_note(self.kl, date=TODAY,
                         lines=[(item, self.a, 2), (item, self.b, 1)])
        self.assertEqual(
            sorted((line.batch_id, line.count) for line in note.lines.all()),
            sorted([(self.a.pk, 2), (self.b.pk, 1)]))
        booked = [(m.kind, m.batch, m.count, m.quantity_after)
                  for m in item.movements.order_by("pk")][1:]
        self.assertEqual(booked, [
            ("assignment", self.a, 2, 5), ("delivery", self.a, 2, 3),
            ("assignment", self.b, 1, 3), ("delivery", self.b, 1, 2)])
        self.assertShares(item, (None, 2))

    def test_the_lines_of_one_item_share_the_share_of_unknown_batch(
            self) -> None:
        item = self.holding((None, 3))
        with self.refusing("count", shares=True) as caught:
            book_note(self.kl, date=TODAY,
                      lines=[(item, self.a, 2), (item, self.b, 2)])
        self.assertEqual(caught.exception.line, 1)
        self.assertEqual(Movement.objects.filter(kind="assignment").count(),
                         0)

    def test_a_refused_line_undoes_the_assignments_before_it(self) -> None:
        first = self.holding((None, 5))
        second = self.holding((None, 1), size="50")
        with self.refusing("count", shares=True) as caught:
            book_note(self.kl, date=TODAY,
                      lines=[(first, self.a, 2), (second, self.a, 2)])
        self.assertEqual(caught.exception.line, 1)
        self.assertShares(first, (None, 5))
        self.assertEqual(first.movements.count(), 1)

    def test_a_historical_note_moves_no_stock(self) -> None:
        item = self.holding((self.a, 1), (None, 2))
        before = (stock_snapshot(), item.movements.count())
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         lines=[(item, self.a, 4), (item, self.b, 9)])
        self.assertEqual((stock_snapshot(), item.movements.count()), before)
        self.assertEqual(
            sorted((line.batch_id, line.count) for line in note.lines.all()),
            sorted([(self.a.pk, 4), (self.b.pk, 9)]))
        self.assertEqual(Movement.objects.filter(kind="assignment").count(),
                         0)


class CorrectionShareTests(StockCase):

    def test_the_correction_of_one_share(self) -> None:
        """Scenario: Correction of one share."""
        item = self.holding((self.a, 3), (None, 2))
        movement = correct(self.kl, item, count=0, note="nachgezählt")
        self.assertShares(item, (self.a, 3))
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual(
            (movement.kind, movement.batch, movement.count,
             movement.quantity_after, movement.note),
            ("correction", None, 0, 3, "nachgezählt"))

    def test_the_correction_of_the_share_of_a_batch(self) -> None:
        item = self.holding((self.a, 3), (None, 2))
        movement = correct(self.kl, item, count=5, note="mehr", batch=self.a)
        self.assertShares(item, (self.a, 5), (None, 2))
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual(
            (movement.batch, movement.count, movement.quantity_after),
            (self.a, 5, 7))

    def test_a_correction_may_lower_a_share(self) -> None:
        item = self.holding((self.a, 3), (None, 2))
        movement = correct(self.kl, item, count=1, note="weniger",
                           batch=self.a)
        self.assertShares(item, (self.a, 1), (None, 2))
        self.assertEqual(movement.quantity_after, 3)

    def test_a_correction_may_open_the_share_of_a_batch(self) -> None:
        item = self.holding((None, 2))
        correct(self.kl, item, count=4, note="gefunden", batch=self.b)
        self.assertShares(item, (self.b, 4), (None, 2))

    def test_a_share_corrected_to_zero_stays_as_a_row(self) -> None:
        item = self.holding((self.a, 3))
        correct(self.kl, item, count=0, note="leer", batch=self.a)
        self.assertEqual(
            BatchStock.objects.get(item=item, batch=self.a).quantity, 0)
        self.assertShares(item)

    def test_a_refused_correction_changes_no_share(self) -> None:
        item = self.holding((self.a, 3), (None, 2))
        for count, note in ((-1, "x"), (1, ""), (1, "  ")):
            with self.subTest(count=count, note=note), \
                    self.refusing(shares=True):
                correct(self.kl, item, count=count, note=note,
                        batch=self.a)
        self.assertShares(item, (self.a, 3), (None, 2))


class NoteLineTests(StockCase):

    def test_a_line_without_its_batch_is_refused(self) -> None:
        """Scenario: A row needs its batch (the booking)."""
        item = self.holding((self.a, 5))
        for historical in (False, True):
            for lines in ([(item, None, 1)],
                          [(item, self.a, 1), (item, None, 1)]):
                with self.subTest(historical=historical,
                                  lines=len(lines)), \
                        self.refusing("batch", shares=True) as caught:
                    book_note(self.kl, date=TODAY, historical=historical,
                              lines=lines)
                self.assertEqual(caught.exception.line, len(lines) - 1)
        self.assertEqual(DeliveryNote.objects.count(), 0)

    def test_a_batch_of_another_substance_is_refused(self) -> None:
        """Scenario: A batch of another substance (the booking)."""
        other = self.batch("acetophenone", number="AP1")
        item = self.holding((self.a, 5))
        for historical in (False, True):
            with self.subTest(historical=historical), \
                    self.refusing("batch", shares=True) as caught:
                book_note(self.kl, date=TODAY, historical=historical,
                          lines=[(item, self.a, 1), (item, other, 1)])
            self.assertEqual(caught.exception.line, 1)
        self.assertEqual(DeliveryNote.objects.count(), 0)

    def test_an_item_and_batch_twice_are_refused(self) -> None:
        """Scenario: Two batches of one item (the second note)."""
        item = self.holding((self.a, 5))
        for historical in (False, True):
            with self.subTest(historical=historical), \
                    self.refusing("batch", shares=True) as caught:
                book_note(self.kl, date=TODAY, historical=historical,
                          lines=[(item, self.a, 1), (item, self.a, 1)])
            self.assertEqual(caught.exception.line, 1)

    def test_two_batches_of_one_item_in_a_note(self) -> None:
        """Scenario: Two batches of one item."""
        item = self.holding((self.a, 3), (self.b, 1))
        first = book_note(self.kl, date=TODAY,
                          lines=[(item, self.a, 2), (item, self.b, 1)])
        self.assertEqual(first.lines.count(), 2)
        with self.refusing("batch", shares=True) as caught:
            book_note(self.kl, date=TODAY,
                      lines=[(item, self.a, 1), (item, self.a, 1)])
        self.assertEqual(caught.exception.line, 1)
        self.assertEqual(DeliveryNote.objects.count(), 1)

    def test_the_lines_keep_their_batches(self) -> None:
        item = self.holding((self.a, 3), (self.b, 1))
        note = book_note(self.kl, date=TODAY,
                         lines=[(item, self.a, 2), (item, self.b, 1)])
        self.assertEqual(
            [(line.item, line.batch, line.count)
             for line in note.lines.order_by("pk")],
            [(item, self.a, 2), (item, self.b, 1)])
        old = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                        lines=[(item, self.b, 4)])
        self.assertEqual(old.lines.get().batch, self.b)

    def test_an_item_without_a_number_is_still_refused_at_its_line(
            self) -> None:
        from .test_inventory_numbers import numberless
        item = numberless(self.kl)
        batch = self.batch(substance=item.article.substance)
        with self.refusing("item") as caught:
            book_note(self.kl, date=TODAY, lines=[(item, batch, 1)])
        self.assertEqual(caught.exception.line, 0)

    def test_a_line_names_one_batch_of_an_item_once(self) -> None:
        item = self.holding((self.a, 3))
        note = book_note(self.kl, date=TODAY, lines=[(item, self.a, 1)])
        with self.assertRaises(IntegrityError), transaction.atomic():
            DeliveryLine.objects.create(delivery_note=note, item=item,
                                        batch=self.a, count=1)
        DeliveryLine.objects.create(delivery_note=note, item=item,
                                    batch=self.b, count=1)

    def test_the_database_lets_an_old_line_lack_its_batch(self) -> None:
        self.assertTrue(DeliveryLine._meta.get_field("batch").null)


class InvariantTests(StockCase):

    def test_the_quantity_is_the_sum_of_the_shares_after_each_booking(
            self) -> None:
        from registry.models import Substance
        item = create_item(
            self.kl, substance=Substance.objects.get(key="cinnamic-acid"),
            article_number="CH-0012", size=Decimal("10"), unit="umol",
            quantity=4)

        def check(label: str) -> None:
            with self.subTest(after=label):
                self.assertConsistent(item)

        check("opening")
        filling = fill(self.kl, item, count=3, vessel=self.vessel_of(self.a),
                       amount=Decimal("1"))
        check("filling")
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 5)])
        check("delivery with an assignment")
        delivery = newest_movement(item)
        reverse(self.kl, delivery, note="falsch")
        check("reversal of a delivery")
        correct(self.kl, item, count=7, note="gezählt")
        check("correction of unknown")
        correct(self.kl, item, count=2, note="gezählt", batch=self.b)
        check("correction of a batch")
        book_note(self.kl, date=date(2025, 3, 12), historical=True,
                  lines=[(item, self.a, 9)])
        check("historical note")
        with self.refusing(shares=True):
            book_note(self.kl, date=TODAY, lines=[(item, self.b, 99)])
        check("refused delivery")
        correct(self.kl, item, count=0, note="leer", batch=self.a)
        correct(self.kl, item, count=0, note="leer")
        with self.refusing(shares=True):
            reverse(self.kl, filling, note="zu spät")
        check("refused reversal of a filling")

    def test_every_movement_reports_the_quantity_after_it(self) -> None:
        item = self.holding((None, 5))
        book_note(self.kl, date=TODAY, lines=[(item, self.a, 3)])
        fill(self.kl, item, count=2, vessel=self.vessel_of(self.b),
             amount=Decimal("1"))
        correct(self.kl, item, count=1, note="gezählt", batch=self.a)
        last = newest_movement(item)
        self.assertEqual(last.quantity_after, fresh(item).quantity)
        self.assertConsistent(item)


class ReaderTests(StockCase):
    """The readers of delivery lines keep the siblings of a line whose
    delivery is reversed (Delivery notes)."""

    def two_lines(self) -> tuple[Item, Movement]:
        """An item with a note of 2 of ``KL0412`` and 3 of ``KL0413``
        dated in the third quarter of 2026, and the delivery of the
        first line."""
        item = self.holding((self.a, 2), (self.b, 3))
        book_note(self.kl, date=date(2026, 8, 12),
                  lines=[(item, self.a, 2), (item, self.b, 3)])
        return item, item.movements.get(kind="delivery", batch=self.a)

    def test_one_of_two_batch_lines_reversed_keeps_the_other(self) -> None:
        """Scenario: One of two batch lines reversed (consumption)."""
        item, delivery = self.two_lines()
        self.assertEqual(self.consumption(item).quarters[(2026, 3)], 5)
        reverse(self.kl, delivery, note="falsch gebucht")
        self.assertEqual(self.consumption(item).quarters[(2026, 3)], 3)
        self.assertEqual(
            [(line.batch_id, line.count) for line in counted_lines(item)],
            [(self.b.pk, 3)])

    def test_the_sibling_stays_for_every_item_too(self) -> None:
        item, delivery = self.two_lines()
        reverse(self.kl, delivery, note="falsch")
        self.assertEqual(
            [(line.item_id, line.batch_id) for line in counted_lines()],
            [(item.pk, self.b.pk)])

    def test_both_lines_go_when_both_deliveries_are_reversed(self) -> None:
        item, delivery = self.two_lines()
        reverse(self.kl, delivery, note="falsch")
        reverse(self.kl, item.movements.get(kind="delivery", batch=self.b),
                note="falsch")
        self.assertEqual(counted_lines(item), [])
        self.assertEqual(
            self.consumption(item).quarters.get((2026, 3), 0), 0)

    def test_a_line_that_needed_an_assignment_goes_with_its_delivery(
            self) -> None:
        item = self.holding((None, 5))
        book_note(self.kl, date=date(2026, 8, 12),
                  lines=[(item, self.a, 2), (item, self.b, 1)])
        reverse(self.kl, item.movements.get(kind="delivery", batch=self.a),
                note="falsch")
        self.assertEqual(
            [(line.batch_id, line.count) for line in counted_lines(item)],
            [(self.b.pk, 1)])

    def test_lines_of_a_historical_note_count_one_by_one(self) -> None:
        item = self.holding((None, 5))
        note = book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         lines=[(item, self.a, 4), (item, self.b, 1)])
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 5)
        reverse_historical(self.kl, note, note="falsch")
        self.assertEqual(counted_lines(item), [])
        self.assertEqual(
            self.consumption(item).quarters.get((2025, 1), 0), 0)
