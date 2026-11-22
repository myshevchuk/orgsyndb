"""Tests of the bookings against a closing task (end-product-inventory:
Vessels, Inventory forms; task-tracker: Task record, Tasks in the admin;
the design's "Bookings against a closing task").

The first classes check that a booking prepared while the task was
open and stored after it closed is refused. The last ones overlap a
booking with a closure through two connections.
"""

import threading
from datetime import date
from decimal import Decimal
from typing import Any, Callable
from unittest import mock

from django.db import close_old_connections, connection, transaction
from django.test import Client, TransactionTestCase

from inventory.bookings import (correct_vessel, fill, record_batch, reverse,
                                reverse_withdrawal, transfer, withdraw)
from inventory.models import Batch, Item, Vessel, VesselMovement
from tasks.models import Task, TaskStep

from . import (make_item, make_task, make_user, past, substance_for,
               task_url)
from .inventory_support import NEW_BATCH, TODAY, InventoryCase, batch_data
from .inventory_support import snapshot as inventory_snapshot
from .task_support import make_product_batch

CLOSINGS = {"ended": {"ended": past(1)},
            "failed": {"ended": past(1), "failed": True},
            "cancelled": {"cancelled": True}}


def close(task: Task, how: str) -> None:
    """Close TASK the way HOW says, without writing its flasks off, as a
    closure that committed between a booking's preparation and its
    storing leaves it."""
    Task.objects.filter(pk=task.pk).update(**CLOSINGS[how])


class PreparedWhileOpenTests(InventoryCase):
    """Requirement: Vessels (recording a batch from a step and every
    booking on a flask check the task's state in the transaction that
    books, so one prepared while the task was open and stored after it
    closed is refused and changes nothing)."""

    def setUp(self) -> None:
        super().setUp()
        self.task = make_task(self.kl, "CH-0012", steps=2, started=past(1))
        self.step = self.task.steps.get(position=2)
        self.flask = make_product_batch(self.task, "2", "g", flask=True
                                        ).vessels.get()
        self.stocked = self.item("CH-0012", size="10", unit="umol",
                                 quantity=0)
        self.other = make_task(self.kl, "Aspirin", steps=1,
                               started=past(1))

    def prepared_flask(self) -> Vessel:
        """The flask as a caller read it while the task was open, its
        batch, step and task cached."""
        flask = Vessel.objects.select_related(
            "batch__task_step__task").get(pk=self.flask.pk)
        self.assertEqual(flask.batch.task_step.task.state, "running")
        return flask

    def test_a_batch_prepared_while_the_task_was_open_is_refused(
            self) -> None:
        for how in CLOSINGS:
            with self.subTest(how=how):
                task = make_task(self.kl, "CH-0012", steps=1,
                                 started=past(1))
                step = TaskStep.objects.select_related("task").get(
                    task=task)
                self.assertEqual(step.task.state, "running")
                close(task, how)
                with self.refusing():
                    record_batch(
                        self.kl, substance=task.substance,
                        number=f"K-{how}", task_step=step,
                        amount=Decimal("1"), unit="g")
        self.assertEqual(Batch.objects.count(), 1)

    def test_a_batch_form_opened_while_the_task_was_open(self) -> None:
        """The form is shown while the task runs, the task then ends, and
        the post is refused."""
        from . import context_form, field_value, page
        self.client.force_login(self.kl)
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        step = task.steps.get()
        url = f"{NEW_BATCH}?step={step.pk}"
        root = page(self.client.get(url))
        self.assertEqual(field_value(root, "substance"), "cinnamic-acid")
        close(task, "ended")
        before = inventory_snapshot()
        done = self.client.post(url, batch_data(
            step=str(step.pk), amount="1", unit="g", number="K-1"))
        self.assertEqual(done.status_code, 200)
        self.assertTrue(context_form(done).errors)
        self.assertEqual(inventory_snapshot(), before)

    def test_bookings_on_a_flask_prepared_while_the_task_was_open_are_refused(
            self) -> None:
        for how in CLOSINGS:
            Task.objects.filter(pk=self.task.pk).update(
                ended=None, failed=False, cancelled=False)
            flask = self.prepared_flask()
            close(self.task, how)
            self.assertEqual(Vessel.objects.get(pk=flask.pk).amount,
                             Decimal("2000"))
            attempts: dict[str, Callable[[], Any]] = {
                "fill": lambda: fill(self.kl, self.stocked, count=1,
                                     vessel=flask),
                "withdraw": lambda: withdraw(
                    self.kl, flask, task_step=self.other.steps.get(),
                    amount=Decimal("0.5")),
                "transfer": lambda: transfer(
                    self.kl, flask, amount=Decimal("1"),
                    location="Regal"),
                "correct": lambda: correct_vessel(
                    self.kl, flask, amount=Decimal("1"), note="x"),
            }
            for name, attempt in attempts.items():
                with self.subTest(how=how, booking=name), self.refusing():
                    attempt()

    def test_a_reversal_prepared_while_the_task_was_open_is_refused(
            self) -> None:
        filling = fill(self.kl, self.stocked, count=1, vessel=self.flask)
        taken = withdraw(self.kl, self.flask,
                         task_step=self.other.steps.get(),
                         amount=Decimal("0.5"))
        close(self.task, "ended")
        with self.refusing():
            reverse(self.kl, filling, note="doppelt")
        with self.refusing():
            reverse_withdrawal(self.kl, taken)
        self.assertEqual(Item.objects.get(pk=self.stocked.pk).quantity, 1)

    def test_a_stored_vessel_of_the_closed_task_is_not_affected(
            self) -> None:
        batch = self.flask.batch
        from . import make_vessel
        stored = make_vessel(self.kl, batch, unit="g", amount="1",
                             location="Regal")
        close(self.task, "ended")
        fill(self.kl, self.stocked, count=1, vessel=stored)
        correct_vessel(self.kl, stored, amount=Decimal("0.5"), note="x")
        self.assertEqual(Vessel.objects.get(pk=stored.pk).amount,
                         Decimal("500"))


class OverlapTests(TransactionTestCase):
    """Two connections overlap a booking with a closure, either winning
    (Vessels: this holds for bookings and closures that overlap)."""

    TIMEOUT = 20

    def setUp(self) -> None:
        self.kl = make_user("kl", "KL", "Klara", "Lehmann")
        self.boss = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        self.cinnamic = substance_for("CH-0012")
        self.task = make_task(self.kl, self.cinnamic, steps=2,
                              started=past(1))
        self.step = self.task.steps.get(position=2)

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

    def end(self, task: Task) -> Any:
        """The response to the end action of TASK, posted by a client of
        its own."""
        client = Client()
        client.force_login(self.kl)
        try:
            return client.post(task_url(task, "end"))
        finally:
            close_old_connections()

    def blocked(self, outcome: dict[str, Any]) -> bool:
        """Whether the thread of OUTCOME is still waiting after a moment
        in which a request that took no lock would have finished."""
        return not outcome["done"].wait(1.0)

    # -- a booking first, the closure second ----------------------------

    def test_a_batch_recording_committed_first_is_seen_by_the_closure(
            self) -> None:
        held, release, booker, booked = self.holding(
            lambda: record_batch(
                self.kl, substance=self.cinnamic, number="KL0412",
                task_step=self.step, amount=Decimal("2"), unit="g"))
        self.assertTrue(held.wait(self.TIMEOUT))
        closer, closed = self.run_in_thread(lambda: self.end(self.task))
        self.assertTrue(self.blocked(closed), "the closure did not wait")
        release.set()
        booker.join(self.TIMEOUT)
        closer.join(self.TIMEOUT)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", closed, closed.get("error"))
        self.assertEqual(closed["result"].status_code, 302)
        task = Task.objects.get(pk=self.task.pk)
        self.assertEqual(task.state, "ended")
        flask = Batch.objects.get(number="KL0412").vessels.get()
        self.assertEqual(flask.amount, 0)
        self.assertEqual(flask.movements.order_by("-pk").first().kind,
                         "remainder")

    def test_a_flask_booking_committed_first_leaves_the_closure_the_rest(
            self) -> None:
        flask = make_product_batch(self.task, "2", "g", flask=True
                                   ).vessels.get()
        item = make_item(self.kl, "CH-0012", size="10", unit="umol",
                         quantity=0)
        held, release, booker, booked = self.holding(
            lambda: fill(self.kl, item, count=1, vessel=flask,
                         amount=Decimal("0.5")))
        self.assertTrue(held.wait(self.TIMEOUT))
        closer, closed = self.run_in_thread(lambda: self.end(self.task))
        self.assertTrue(self.blocked(closed), "the closure did not wait")
        release.set()
        booker.join(self.TIMEOUT)
        closer.join(self.TIMEOUT)
        self.assertNotIn("error", booked, booked.get("error"))
        self.assertNotIn("error", closed, closed.get("error"))
        self.assertEqual(Task.objects.get(pk=self.task.pk).state, "ended")
        self.assertEqual(Item.objects.get(pk=item.pk).quantity, 1)
        remainder = VesselMovement.objects.get(vessel=flask,
                                               kind="remainder")
        self.assertEqual(remainder.amount, Decimal("1500"))
        self.assertEqual(Vessel.objects.get(pk=flask.pk).amount, 0)

    # -- the closure first, the booking second --------------------------

    def hold_closure(self, task: Task) -> tuple[
            threading.Event, threading.Event, threading.Thread,
            dict[str, Any]]:
        """Start the end action of TASK and hold its transaction open at
        its first remainder; return the ``held`` and ``release``
        events."""
        held, release = threading.Event(), threading.Event()
        real_save = VesselMovement.save

        def save(movement: VesselMovement, *args: Any, **kwargs: Any
                 ) -> Any:
            if movement.kind == VesselMovement.Kind.REMAINDER \
                    and not held.is_set():
                held.set()
                release.wait(self.TIMEOUT)
            return real_save(movement, *args, **kwargs)

        patcher = mock.patch.object(VesselMovement, "save", save)
        patcher.start()
        self.addCleanup(patcher.stop)
        thread, outcome = self.run_in_thread(lambda: self.end(task))
        return held, release, thread, outcome

    def test_a_batch_recording_after_the_closure_is_refused(self) -> None:
        make_product_batch(self.task, "2", "g", flask=True)
        held, release, closer, closed = self.hold_closure(self.task)
        self.assertTrue(held.wait(self.TIMEOUT))
        before = Batch.objects.count()
        booker, booked = self.run_in_thread(lambda: record_batch(
            self.kl, substance=self.cinnamic, number="KL0413",
            task_step=self.step, amount=Decimal("1"), unit="g"))
        self.assertTrue(self.blocked(booked), "the booking did not wait")
        release.set()
        closer.join(self.TIMEOUT)
        booker.join(self.TIMEOUT)
        self.assertNotIn("error", closed, closed.get("error"))
        self.assertEqual(closed["result"].status_code, 302)
        self.assertEqual(Task.objects.get(pk=self.task.pk).state, "ended")
        from inventory.bookings import Refused
        self.assertIsInstance(booked.get("error"), Refused)
        self.assertEqual(Batch.objects.count(), before)

    def test_a_flask_booking_after_the_closure_is_refused(self) -> None:
        flask = make_product_batch(self.task, "2", "g", flask=True
                                   ).vessels.get()
        item = make_item(self.kl, "CH-0012", size="10", unit="umol",
                         quantity=0)
        held, release, closer, closed = self.hold_closure(self.task)
        self.assertTrue(held.wait(self.TIMEOUT))
        booker, booked = self.run_in_thread(lambda: fill(
            self.kl, item, count=1, vessel=flask, amount=Decimal("0.5")))
        self.assertTrue(self.blocked(booked), "the booking did not wait")
        release.set()
        closer.join(self.TIMEOUT)
        booker.join(self.TIMEOUT)
        from inventory.bookings import Refused
        self.assertIsInstance(booked.get("error"), Refused)
        self.assertEqual(Item.objects.get(pk=item.pk).quantity, 0)
        self.assertEqual(Vessel.objects.get(pk=flask.pk).amount, 0)

    def test_a_flask_correction_after_the_closure_is_refused(self) -> None:
        flask = make_product_batch(self.task, "2", "g", flask=True
                                   ).vessels.get()
        held, release, closer, closed = self.hold_closure(self.task)
        self.assertTrue(held.wait(self.TIMEOUT))
        booker, booked = self.run_in_thread(lambda: correct_vessel(
            self.kl, flask, amount=Decimal("1"), note="nachgewogen"))
        self.assertTrue(self.blocked(booked), "the booking did not wait")
        release.set()
        closer.join(self.TIMEOUT)
        booker.join(self.TIMEOUT)
        from inventory.bookings import Refused
        self.assertIsInstance(booked.get("error"), Refused)
        self.assertEqual(Vessel.objects.get(pk=flask.pk).amount, 0)

    # -- the admin loses to a batch that committed first -----------------

    def admin_post(self, task: Task, **over: Any) -> Any:
        """The response to the admin's change form of TASK posted as it
        stands with OVER applied, by a client of its own."""
        client = Client()
        client.force_login(self.boss)
        url = f"/lab/admin/tasks/task/{task.pk}/change/"
        try:
            page = client.get(url)
            form = page.context["adminform"].form
            data: dict[str, Any] = {}
            for name in form.fields:
                value = form[name].value()
                if value is True:
                    data[name] = "on"
                elif value is None:
                    data[name] = ""
                elif value is not False:
                    data[name] = (value.isoformat()
                                  if isinstance(value, date) else value)
            data.update({"steps-TOTAL_FORMS": "0",
                         "steps-INITIAL_FORMS": "0",
                         "steps-MIN_NUM_FORMS": "0",
                         "steps-MAX_NUM_FORMS": "1000"})
            data.update(over)
            return client.post(url, data)
        finally:
            close_old_connections()

    def test_an_admin_failure_loses_to_a_batch_that_committed_first(
            self) -> None:
        held, release, booker, booked = self.holding(
            lambda: record_batch(
                self.kl, substance=self.cinnamic, number="KL0412",
                task_step=self.step, amount=Decimal("2"), unit="g"))
        self.assertTrue(held.wait(self.TIMEOUT))
        closer, closed = self.run_in_thread(lambda: self.admin_post(
            self.task, ended=TODAY.isoformat(), failed="on"))
        self.assertTrue(self.blocked(closed), "the admin did not wait")
        release.set()
        booker.join(self.TIMEOUT)
        closer.join(self.TIMEOUT)
        self.assertNotIn("error", closed, closed.get("error"))
        response = closed["result"]
        self.assertEqual(response.status_code, 200)
        errors = response.context["adminform"].form.errors
        self.assertTrue({"failed", "ended"} & set(errors), sorted(errors))
        task = Task.objects.get(pk=self.task.pk)
        self.assertEqual((task.state, task.failed), ("running", False))
        flask = Batch.objects.get(number="KL0412").vessels.get()
        self.assertEqual(flask.amount, Decimal("2000"))

    def test_an_admin_substance_change_loses_to_a_batch_that_committed_first(
            self) -> None:
        other = substance_for("Aspirin")
        held, release, booker, booked = self.holding(
            lambda: record_batch(
                self.kl, substance=self.cinnamic, number="KL0412",
                task_step=self.step, amount=Decimal("2"), unit="g"))
        self.assertTrue(held.wait(self.TIMEOUT))
        changer, changed = self.run_in_thread(lambda: self.admin_post(
            self.task, substance=other.pk))
        self.assertTrue(self.blocked(changed), "the admin did not wait")
        release.set()
        booker.join(self.TIMEOUT)
        changer.join(self.TIMEOUT)
        self.assertNotIn("error", changed, changed.get("error"))
        response = changed["result"]
        self.assertEqual(response.status_code, 200)
        self.assertIn("substance", response.context["adminform"].form.errors)
        self.assertEqual(Task.objects.get(pk=self.task.pk).substance,
                         self.cinnamic)
