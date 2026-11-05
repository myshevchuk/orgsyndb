"""Tests of the delivery notes (end-product-inventory: Delivery notes,
and the historical-note rules of Consumption)."""

from datetime import date

from inventory.bookings import (Refused, book_note, enter_consumption,
                                reverse, reverse_historical)
from inventory.models import (DeliveryLine, DeliveryNote, EnteredConsumption,
                              Movement)

from .inventory_support import (InventoryCase, TODAY, fresh, newest_movement,
                                snapshot)


class CurrentNoteTests(InventoryCase):

    def test_note_with_several_lines(self) -> None:
        """Scenario: Note with several lines."""
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=3)
        note = book_note(self.kl, date=TODAY,
                         lines=[(first, 2), (second, 3)])
        self.assertEqual((fresh(first).quantity, fresh(second).quantity),
                         (3, 0))
        self.assertEqual(
            sorted((line.item_id, line.count) for line in note.lines.all()),
            sorted([(first.pk, 2), (second.pk, 3)]))
        for item, count in ((first, 2), (second, 3)):
            movement = item.movements.get(kind="delivery")
            self.assertEqual((movement.delivery_note, movement.count),
                             (note, count))

    def test_one_line_too_many_refuses_the_note(self) -> None:
        """Scenario: One line too many refuses the note."""
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=3)
        before = snapshot()
        with self.assertRaises(Refused):
            book_note(self.kl, date=TODAY, lines=[(first, 2), (second, 4)])
        self.assertEqual(snapshot(), before)
        self.assertEqual(DeliveryNote.objects.count(), 0)
        self.assertEqual((fresh(first).quantity, fresh(second).quantity),
                         (5, 3))

    def test_a_stale_second_line_refuses_the_whole_note(self) -> None:
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=5)
        stale = type(second).objects.get(pk=second.pk)
        self.deliver(second, 4)
        before = snapshot()
        with self.assertRaises(Refused):
            book_note(self.kl, date=TODAY, lines=[(first, 2), (stale, 4)])
        self.assertEqual(snapshot(), before)

    def test_a_note_needs_a_line(self) -> None:
        before = snapshot()
        with self.assertRaises(Refused):
            book_note(self.kl, date=TODAY, lines=[])
        self.assertEqual(snapshot(), before)

    def test_no_item_twice_in_one_note(self) -> None:
        item = self.item(quantity=9)
        before = snapshot()
        with self.assertRaises(Refused):
            book_note(self.kl, date=TODAY, lines=[(item, 1), (item, 2)])
        self.assertEqual(snapshot(), before)

    def test_a_line_needs_a_count_above_zero(self) -> None:
        item = self.item(quantity=9)
        other = self.item("CH-0002", quantity=9)
        before = snapshot()
        for count in (0, -1):
            with self.subTest(count=count), self.assertRaises(Refused):
                book_note(self.kl, date=TODAY,
                          lines=[(other, 1), (item, count)])
        self.assertEqual(snapshot(), before)

    def test_a_date_after_today_is_refused(self) -> None:
        item = self.item()
        before = snapshot()
        with self.assertRaises(Refused):
            book_note(self.kl, date=date(2026, 11, 5), lines=[(item, 1)])
        self.assertEqual(snapshot(), before)

    def test_the_date_may_be_today(self) -> None:
        item = self.item()
        self.assertEqual(self.deliver(item, 1, TODAY).date, TODAY)

    def test_a_note_in_a_quarter_with_an_entered_value_adds_to_it(
            self) -> None:
        item = self.item(quantity=9)
        self.enter(item, 2025, 2, 5)
        self.deliver(item, 2, date(2025, 5, 10))
        self.assertEqual(self.consumption(item).quarters[(2025, 2)], 7)


class NumberTests(InventoryCase):

    def test_a_number_is_unique_among_notes(self) -> None:
        item = self.item(quantity=9)
        self.deliver(item, 1, number="LS-1")
        before = snapshot()
        with self.assertRaises(Refused):
            self.deliver(item, 1, number="LS-1")
        self.assertEqual(snapshot(), before)

    def test_notes_without_a_number_do_not_collide(self) -> None:
        item = self.item(quantity=9)
        self.deliver(item, 1)
        self.deliver(item, 1)
        self.assertEqual(DeliveryNote.objects.count(), 2)
        numbers = DeliveryNote.objects.values_list("number", flat=True)
        self.assertTrue(all(n in ("", None) for n in numbers))

    def test_a_historical_note_shares_the_numbers(self) -> None:
        item = self.item(quantity=9)
        self.deliver(item, 1, number="LS-1")
        with self.assertRaises(Refused):
            book_note(self.kl, date=date(2025, 3, 12), number="LS-1",
                      historical=True, lines=[(item, 1)])


class HistoricalNoteTests(InventoryCase):

    def historical(self, item, count, day=date(2025, 3, 12), **extra):
        return book_note(self.kl, date=day, historical=True,
                         lines=[(item, count)], **extra)

    def test_historical_note(self) -> None:
        """Scenario: Historical note."""
        item = self.item(quantity=5)
        note = self.historical(item, 4)
        self.assertTrue(DeliveryNote.objects.get(pk=note.pk).historical)
        self.assertEqual(fresh(item).quantity, 5)
        self.assertEqual(item.movements.count(), 1)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 4)
        self.assertEqual(note.lines.get().count, 4)

    def test_its_lines_may_exceed_the_quantity(self) -> None:
        item = self.item(quantity=1)
        self.historical(item, 8)
        self.assertEqual(fresh(item).quantity, 1)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 8)

    def test_a_historical_note_in_a_quarter_with_an_entered_value(
            self) -> None:
        """Scenario: Historical note in a quarter with an entered value."""
        item = self.item(quantity=5)
        self.enter(item, 2025, 1, 6)
        before = snapshot()
        with self.assertRaises(Refused):
            self.historical(item, 4)
        self.assertEqual(snapshot(), before)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 6)

    def test_the_quarters_edges(self) -> None:
        item = self.item(quantity=5)
        self.enter(item, 2025, 1, 6)
        self.enter(item, 2025, 3, 6)
        for day in (date(2025, 1, 1), date(2025, 3, 31),
                    date(2025, 7, 1)):
            with self.subTest(refused=day), self.assertRaises(Refused):
                self.historical(item, 1, day)
        for day in (date(2024, 12, 31), date(2025, 4, 1),
                    date(2025, 6, 30)):
            with self.subTest(allowed=day):
                self.historical(item, 1, day)

    def test_one_conflicting_line_refuses_the_whole_note(self) -> None:
        first = self.item("CH-0001")
        second = self.item("CH-0002")
        self.enter(second, 2025, 1, 6)
        before = snapshot()
        with self.assertRaises(Refused):
            book_note(self.kl, date=date(2025, 3, 12), historical=True,
                      lines=[(first, 1), (second, 1)])
        self.assertEqual(snapshot(), before)

    def test_an_entered_value_of_another_item_does_not_matter(self) -> None:
        first = self.item("CH-0001")
        second = self.item("CH-0002")
        self.enter(second, 2025, 1, 6)
        self.historical(first, 4)

    def test_entered_value_removed_for_old_notes(self) -> None:
        """Scenario: Entered value removed for old notes."""
        item = self.item(quantity=5)
        self.enter(item, 2025, 1, 6)
        self.enter(item, 2025, 1, None)
        self.assertEqual(EnteredConsumption.objects.count(), 0)
        self.historical(item, 4)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 4)

    def test_an_entered_value_is_refused_beside_a_historical_note(
            self) -> None:
        item = self.item(quantity=5)
        self.historical(item, 4)
        before = snapshot()
        with self.assertRaises(Refused):
            enter_consumption(self.kl, item, year=2025, quarter=1, count=6)
        self.assertEqual(snapshot(), before)

    def test_it_is_refused_for_the_quarter_of_the_note_only(self) -> None:
        item = self.item(quantity=5)
        self.historical(item, 4)
        self.enter(item, 2025, 2, 6)
        self.enter(item, 2024, 1, 6)
        other = self.item("CH-0002")
        self.enter(other, 2025, 1, 6)
        self.assertEqual(EnteredConsumption.objects.count(), 3)

    def test_removing_a_value_beside_a_historical_note_is_no_conflict(
            self) -> None:
        item = self.item(quantity=5)
        self.historical(item, 4)
        self.enter(item, 2025, 1, None)

    def test_a_reversed_historical_note_makes_room(self) -> None:
        item = self.item(quantity=5)
        note = self.historical(item, 4)
        reverse_historical(self.kl, note, note="falsch")
        self.enter(item, 2025, 1, 6)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 6)

    def test_a_current_note_does_not_block_an_entered_value(self) -> None:
        item = self.item(quantity=9)
        self.deliver(item, 2, date(2025, 3, 12))
        self.enter(item, 2025, 1, 6)
        self.assertEqual(self.consumption(item).quarters[(2025, 1)], 8)


class HistoricalReversalTests(InventoryCase):

    def note(self, item=None):
        item = item or self.item(quantity=5)
        return book_note(self.kl, date=date(2025, 3, 12), historical=True,
                         lines=[(item, 4)])

    def test_a_historical_note_is_marked_reversed(self) -> None:
        note = self.note()
        reverse_historical(self.kl, note, note="falsch eingetragen")
        note = DeliveryNote.objects.get(pk=note.pk)
        self.assertTrue(note.reversed)
        self.assertEqual(note.reversal_note, "falsch eingetragen")
        self.assertTrue(note.historical)

    def test_its_lines_no_longer_count(self) -> None:
        item = self.item(quantity=5)
        note = self.note(item)
        reverse_historical(self.kl, note, note="falsch")
        self.assertEqual(
            self.consumption(item).quarters.get((2025, 1), 0), 0)
        self.assertEqual(note.lines.count(), 1)

    def test_a_note_is_required(self) -> None:
        note = self.note()
        before = snapshot()
        with self.assertRaises(Refused):
            reverse_historical(self.kl, note, note="")
        self.assertEqual(snapshot(), before)

    def test_it_is_reversed_once(self) -> None:
        note = self.note()
        reverse_historical(self.kl, note, note="falsch")
        stale = DeliveryNote.objects.get(pk=note.pk)
        before = snapshot()
        with self.assertRaises(Refused):
            reverse_historical(self.kl, stale, note="noch einmal")
        self.assertEqual(snapshot(), before)

    def test_a_current_note_is_not_reversed_whole(self) -> None:
        item = self.item(quantity=5)
        note = self.deliver(item, 2)
        before = snapshot()
        with self.assertRaises(Refused):
            reverse_historical(self.kl, note, note="falsch")
        self.assertEqual(snapshot(), before)

    def test_a_current_note_is_reversed_line_by_line(self) -> None:
        first = self.item("CH-0001", quantity=5)
        second = self.item("CH-0002", quantity=5)
        note = book_note(self.kl, date=TODAY, lines=[(first, 2), (second, 3)])
        reverse(self.kl, first.movements.get(kind="delivery"), note="x")
        self.assertFalse(DeliveryNote.objects.get(pk=note.pk).reversed)
        self.assertEqual((fresh(first).quantity, fresh(second).quantity),
                         (5, 2))


class RecordTests(InventoryCase):

    def test_a_note_keeps_a_history(self) -> None:
        item = self.item()
        note = self.deliver(item, 1)
        entry = note.history.get()
        self.assertEqual((entry.history_user, entry.history_type),
                         (self.kl, "+"))

    def test_no_line_is_stored_for_a_refused_note(self) -> None:
        item = self.item(quantity=1)
        with self.assertRaises(Refused):
            self.deliver(item, 2)
        self.assertEqual(DeliveryLine.objects.count(), 0)
        self.assertEqual(Movement.objects.count(), 1)
        self.assertEqual(newest_movement(item).kind, "opening")
