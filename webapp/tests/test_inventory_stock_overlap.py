"""Tests of bookings that overlap on one item's shares through two
connections: a delivery against a correction, and a filling against a
correction, either winning (end-product-inventory: Stock by batch; the
design's "Shares as rows, the unknown share among them").

A booking that changes a share locks the item's row before it reads a
share, so the second booking waits for the first and then reads what the
first stored; neither ends in a server error or a deadlock, and the
shares and the quantity agree afterwards.
"""

import threading
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from django.db import connection, transaction
from django.test import TransactionTestCase

from inventory.bookings import Refused, book_note, correct, fill
from inventory.models import DeliveryNote, Item, Movement

from . import make_batch, make_item, make_user, make_vessel
from .inventory_support import BatchStock, expected, set_shares, shares

DAY = date(2026, 11, 4)


class OverlapTests(TransactionTestCase):
    """Two connections overlap two bookings on one item."""

    TIMEOUT = 20

    def setUp(self) -> None:
        self.kl = make_user("kl", "KL", "Klara", "Lehmann")
        self.a = make_batch(self.kl, "CH-0012", number="KL0412")
        self.b = make_batch(self.kl, "CH-0012", number="KL0413")
        self.item = make_item(self.kl, "CH-0012", size="10", unit="umol",
                              quantity=0)
        self.vessel = make_vessel(self.kl, self.a, unit="g", amount="50")

    # -- plumbing ----------------------------------------------------

    def run_in_thread(self, work: Callable[[], Any]
                      ) -> tuple[threading.Thread, dict[str, Any]]:
        """Run WORK in a thread of its own, with its own connection, and
        return the thread and a dict that gets its ``result`` or its
        ``error``."""
        outcome: dict[str, Any] = {"done": threading.Event()}

        def target() -> None:
            try:
                outcome["result"] = work()
            except BaseException as error:
                outcome["error"] = error
            finally:
                connection.close()
                outcome["done"].set()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        return thread, outcome

    def holding(self, booking: Callable[[], Any]
                ) -> tuple[threading.Event, threading.Event,
                           threading.Thread, dict[str, Any]]:
        """Run BOOKING in a transaction that stays open until the
        returned ``release`` event is set; the ``held`` event is set once
        BOOKING has run."""
        held, release = threading.Event(), threading.Event()

        def work() -> Any:
            with transaction.atomic():
                result = booking()
                held.set()
                release.wait(self.TIMEOUT)
            return result

        thread, outcome = self.run_in_thread(work)
        return held, release, thread, outcome

    def blocked(self, outcome: dict[str, Any]) -> bool:
        """Whether the thread of OUTCOME is still waiting after a moment
        in which a request that took no lock would have finished."""
        return not outcome["done"].wait(1.0)

    def finish(self, release: threading.Event, *threads: threading.Thread
               ) -> None:
        """Let the held booking go and wait for every thread; a thread
        that is still alive is a deadlock."""
        release.set()
        for thread in threads:
            thread.join(self.TIMEOUT)
            self.assertFalse(thread.is_alive(), "a booking is stuck")

    def assertConsistent(self) -> None:
        total = sum(BatchStock.objects.filter(item=self.item).values_list(
            "quantity", flat=True))
        self.assertEqual(Item.objects.get(pk=self.item.pk).quantity, total)

    def deliver(self, batch: Any, count: int) -> Callable[[], Any]:
        return lambda: book_note(self.kl, date=DAY,
                                 lines=[(self.item, batch, count)])

    def filling(self, count: int) -> Callable[[], Any]:
        return lambda: fill(self.kl, self.item, count=count,
                            vessel=self.vessel, amount=Decimal("1"))

    # -- a delivery against a correction ---------------------------------

    def test_a_correction_after_a_delivery_reads_what_it_stored(
            self) -> None:
        set_shares(self.item, (self.a, 2), (None, 4))
        held, release, booker, booked = self.holding(
            self.deliver(self.a, 3))
        self.assertTrue(held.wait(self.TIMEOUT))
        corrector, corrected = self.run_in_thread(lambda: correct(
            self.kl, self.item, count=10, note="gezählt"))
        self.assertTrue(self.blocked(corrected), "the correction did not wait")
        self.finish(release, booker, corrector)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", corrected, corrected.get("error"))
        self.assertEqual(shares(self.item), {None: 10})
        self.assertEqual(Item.objects.get(pk=self.item.pk).quantity, 10)
        self.assertEqual(corrected["result"].quantity_after, 10)
        self.assertConsistent()
        delivery = self.item.movements.get(kind="delivery")
        self.assertLess(delivery.pk, corrected["result"].pk)

    def test_a_delivery_after_a_correction_reads_what_it_stored(
            self) -> None:
        set_shares(self.item, (self.a, 2), (None, 4))
        held, release, booker, booked = self.holding(lambda: correct(
            self.kl, self.item, count=0, note="gezählt"))
        self.assertTrue(held.wait(self.TIMEOUT))
        deliverer, delivered = self.run_in_thread(self.deliver(self.a, 3))
        self.assertTrue(self.blocked(delivered), "the delivery did not wait")
        self.finish(release, booker, deliverer)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertIsInstance(delivered.get("error"), Refused)
        self.assertEqual(shares(self.item), expected((self.a, 2)))
        self.assertEqual(Item.objects.get(pk=self.item.pk).quantity, 2)
        self.assertEqual(DeliveryNote.objects.count(), 0)
        self.assertFalse(Movement.objects.filter(kind="assignment").exists())
        self.assertConsistent()

    def test_a_correction_of_the_batch_after_a_delivery_of_it(self) -> None:
        set_shares(self.item, (self.a, 3), (None, 2))
        held, release, booker, booked = self.holding(
            self.deliver(self.a, 5))
        self.assertTrue(held.wait(self.TIMEOUT))
        corrector, corrected = self.run_in_thread(lambda: correct(
            self.kl, self.item, count=4, note="gezählt", batch=self.a))
        self.assertTrue(self.blocked(corrected), "the correction did not wait")
        self.finish(release, booker, corrector)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", corrected, corrected.get("error"))
        self.assertEqual(shares(self.item), expected((self.a, 4)))
        self.assertEqual(corrected["result"].quantity_after, 4)
        self.assertConsistent()

    # -- a filling against a correction ---------------------------------

    def test_a_correction_after_a_filling_reads_what_it_stored(self) -> None:
        set_shares(self.item, (None, 3))
        held, release, booker, booked = self.holding(self.filling(2))
        self.assertTrue(held.wait(self.TIMEOUT))
        corrector, corrected = self.run_in_thread(lambda: correct(
            self.kl, self.item, count=1, note="gezählt", batch=self.a))
        self.assertTrue(self.blocked(corrected), "the correction did not wait")
        self.finish(release, booker, corrector)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", corrected, corrected.get("error"))
        self.assertEqual(shares(self.item), expected((self.a, 1), (None, 3)))
        self.assertEqual(Item.objects.get(pk=self.item.pk).quantity, 4)
        self.assertEqual(corrected["result"].quantity_after, 4)
        self.assertConsistent()

    def test_a_filling_after_a_correction_adds_to_what_it_stored(
            self) -> None:
        set_shares(self.item, (None, 3))
        held, release, booker, booked = self.holding(lambda: correct(
            self.kl, self.item, count=5, note="gezählt", batch=self.a))
        self.assertTrue(held.wait(self.TIMEOUT))
        filler, filled = self.run_in_thread(self.filling(2))
        self.assertTrue(self.blocked(filled), "the filling did not wait")
        self.finish(release, booker, filler)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", filled, filled.get("error"))
        self.assertEqual(shares(self.item), expected((self.a, 7), (None, 3)))
        self.assertEqual(Item.objects.get(pk=self.item.pk).quantity, 10)
        self.assertEqual(filled["result"].quantity_after, 10)
        self.assertConsistent()

    def test_a_correction_of_unknown_batch_after_a_filling_of_a_batch(
            self) -> None:
        set_shares(self.item, (None, 3))
        held, release, booker, booked = self.holding(self.filling(2))
        self.assertTrue(held.wait(self.TIMEOUT))
        corrector, corrected = self.run_in_thread(lambda: correct(
            self.kl, self.item, count=0, note="gezählt"))
        self.assertTrue(self.blocked(corrected), "the correction did not wait")
        self.finish(release, booker, corrector)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", corrected, corrected.get("error"))
        self.assertEqual(shares(self.item), expected((self.a, 2)))
        self.assertEqual(corrected["result"].quantity_after, 2)
        self.assertConsistent()

    # -- two first bookings into one batch ------------------------------

    def test_two_fillings_into_a_batch_make_its_row_once(self) -> None:
        set_shares(self.item, (None, 0))
        self.assertFalse(BatchStock.objects.filter(batch=self.a).exists())
        held, release, booker, booked = self.holding(self.filling(2))
        self.assertTrue(held.wait(self.TIMEOUT))
        second, filled = self.run_in_thread(self.filling(1))
        self.assertTrue(self.blocked(filled), "the second filling did not "
                        "wait")
        self.finish(release, booker, second)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", filled, filled.get("error"))
        self.assertEqual(
            BatchStock.objects.filter(item=self.item, batch=self.a).count(),
            1)
        self.assertEqual(shares(self.item), expected((self.a, 3)))
        self.assertConsistent()

    def test_two_deliveries_assigning_into_a_batch_make_its_row_once(
            self) -> None:
        set_shares(self.item, (None, 5))
        held, release, booker, booked = self.holding(
            self.deliver(self.b, 1))
        self.assertTrue(held.wait(self.TIMEOUT))
        second, delivered = self.run_in_thread(self.deliver(self.b, 2))
        self.assertTrue(self.blocked(delivered), "the second delivery did "
                        "not wait")
        self.finish(release, booker, second)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", delivered, delivered.get("error"))
        self.assertEqual(
            BatchStock.objects.filter(item=self.item, batch=self.b).count(),
            1)
        self.assertEqual(shares(self.item), {None: 2})
        self.assertEqual(Item.objects.get(pk=self.item.pk).quantity, 2)
        self.assertConsistent()

    def test_two_deliveries_that_together_take_too_much(self) -> None:
        set_shares(self.item, (self.a, 5))
        held, release, booker, booked = self.holding(
            self.deliver(self.a, 4))
        self.assertTrue(held.wait(self.TIMEOUT))
        second, delivered = self.run_in_thread(self.deliver(self.a, 4))
        self.assertTrue(self.blocked(delivered), "the second delivery did "
                        "not wait")
        self.finish(release, booker, second)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertIsInstance(delivered.get("error"), Refused)
        self.assertEqual(shares(self.item), expected((self.a, 1)))
        self.assertEqual(DeliveryNote.objects.count(), 1)
        self.assertConsistent()
