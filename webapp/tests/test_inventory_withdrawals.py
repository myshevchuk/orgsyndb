"""Tests of the withdrawals into task steps and their reversal
(end-product-inventory: Bulk lots, Bulk lot page, Inventory forms)."""

from decimal import Decimal

from inventory.models import Lot, LotMovement
from tasks.models import TaskStep

from . import (context_form, field_value, make_lot, make_task,
               make_withdrawal, page, past, sent_messages, substance_for,
               task_url)
from .inventory_support import fresh, has_amount, lot_url, snapshot
from .planning_support import metadata
from .task_support import TODAY_ISO, StepCase, steps_of

WITHDRAWAL = "withdrawal"


def reverse_url(movement: LotMovement) -> str:
    return f"/lab/inventory/bulk/movements/{movement.pk}/reverse/"


class WithdrawalCase(StepCase):
    """A running task following ``SEQ-0002`` with the steps
    ``self.first`` and ``self.second``, and a lot of ``2`` g of
    ``4-acetylbiphenyl``, the intermediate the first step makes."""

    def setUp(self) -> None:
        super().setUp()
        self.intermediate = substance_for("4-acetylbiphenyl")
        self.task = self.follow()
        self.first, self.second = steps_of(self.task)
        self.lot = make_lot(self.kl, substance=self.intermediate,
                            unit="g", amount="2")

    def withdraw(self, step: TaskStep | None = None, amount: str = "0.5",
                 lot: Lot | None = None, **data: str):
        """Post the withdrawal form of ``lot`` into ``step``, given as
        the query and as the field ``step``."""
        lot = lot or self.lot
        step = step or self.second
        return self.client.post(
            f"{lot_url(lot, 'withdraw')}?step={step.pk}",
            {"step": str(step.pk), "amount": amount, "date": TODAY_ISO,
             **data})

    def refused(self, response, field: str | None = None) -> None:
        """The form is shown again with errors and nothing changed."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(errors, "the form shows no error")
        if field is not None:
            self.assertIn(field, errors)

    def amount_shown(self, lot: Lot | None = None) -> str:
        root = page(self.client.get(lot_url(lot or self.lot)))
        return metadata(root)["Menge"].text()

    def newest(self, lot: Lot | None = None) -> LotMovement:
        return (lot or self.lot).movements.order_by("-pk").first()


class WithdrawalFormTests(WithdrawalCase):

    def test_withdrawal_and_its_reversal(self) -> None:
        """Scenario: Withdrawal and its reversal."""
        done = self.withdraw(amount="0.5")
        self.assertRedirects(done, lot_url(self.lot),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.lot).amount, Decimal("1500"))
        self.assertTrue(has_amount(self.amount_shown(), "1,5", "g"))
        taken = self.newest()
        self.assertEqual(
            (taken.kind, taken.amount, taken.amount_after, taken.task_step,
             taken.user), (WITHDRAWAL, Decimal("500"), Decimal("1500"),
                           self.second, self.kl))
        self.assertIsNone(taken.reverses)

        done = self.client.post(reverse_url(taken))
        self.assertRedirects(done, lot_url(self.lot),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.lot).amount, Decimal("2000"))
        self.assertTrue(has_amount(self.amount_shown(), "2", "g"))
        returned = self.newest()
        self.assertEqual(
            (returned.kind, returned.amount, returned.amount_after,
             returned.reverses, returned.user),
            (LotMovement.Kind.REVERSAL, Decimal("500"), Decimal("2000"),
             taken, self.kl))

        before = snapshot()
        self.client.post(reverse_url(taken))
        self.assertEqual(snapshot(), before)

    def test_the_kind_is_a_withdrawal(self) -> None:
        """Requirement: Bulk lots (`withdrawal`)."""
        self.assertEqual(LotMovement.Kind.WITHDRAWAL, WITHDRAWAL)
        from django.utils import translation
        with translation.override("en"):
            self.assertEqual(str(LotMovement.Kind.WITHDRAWAL.label),
                             "Withdrawal")
        with translation.override("de"):
            self.assertEqual(str(LotMovement.Kind.WITHDRAWAL.label),
                             "Entnahme")

    def test_the_movement_keeps_its_date_and_the_message_names_the_lot(
            self) -> None:
        done = self.withdraw(date="2026-11-01")
        self.assertEqual(self.newest().date.isoformat(), "2026-11-01")
        self.assertIn("4-Acetylbiphenyl", str(sent_messages(done)[-1]))

    def test_the_amount_is_in_the_unit_of_the_lot(self) -> None:
        small = make_lot(self.kl, substance=self.intermediate, unit="mmol",
                         amount="1")
        self.withdraw(lot=small, amount="0.25")
        self.assertEqual(fresh(small).amount, Decimal("750"))
        self.assertEqual(self.newest(small).amount, Decimal("250"))

    def test_the_whole_lot_may_be_taken(self) -> None:
        self.withdraw(amount="2")
        self.assertEqual(fresh(self.lot).amount, 0)
        self.assertIn("aufgebraucht",
                      page(self.client.get(lot_url(self.lot))).text())

    def test_an_amount_above_the_lot_is_refused(self) -> None:
        before = snapshot()
        self.refused(self.withdraw(amount="2.000001"), "amount")
        self.assertEqual(snapshot(), before)

    def test_a_second_withdrawal_cannot_take_more_than_is_left(self) -> None:
        self.withdraw(amount="1.5")
        before = snapshot()
        self.refused(self.withdraw(amount="0.6"), "amount")
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(self.lot).amount, Decimal("500"))

    def test_an_amount_of_zero_or_less_is_refused(self) -> None:
        before = snapshot()
        for amount in ("0", "-1"):
            with self.subTest(amount=amount):
                self.refused(self.withdraw(amount=amount), "amount")
        self.assertEqual(snapshot(), before)

    def test_a_date_in_the_future_is_refused(self) -> None:
        before = snapshot()
        self.refused(self.withdraw(date="2026-11-05"), "date")
        self.assertEqual(snapshot(), before)

    def test_a_used_up_lot_takes_no_withdrawal(self) -> None:
        self.assertEqual(self.withdraw(amount="1").status_code, 302)
        empty = make_lot(self.kl, substance=self.intermediate, unit="g",
                         amount="0")
        before = snapshot()
        done = self.withdraw(lot=empty, amount="1")
        self.assertNotEqual(done.status_code, 302)
        self.assertEqual(snapshot(), before)

    def test_the_step_may_be_chosen_in_the_form(self) -> None:
        """Requirement: Inventory forms (chosen among those tasks' steps
        or given as `?step=<id>`)."""
        done = self.client.post(lot_url(self.lot, "withdraw"), {
            "step": str(self.first.pk), "amount": "1", "date": TODAY_ISO})
        self.assertRedirects(done, lot_url(self.lot),
                             fetch_redirect_response=False)
        self.assertEqual(self.newest().task_step, self.first)

    def test_a_step_of_a_planned_task_is_taken(self) -> None:
        planned = make_task(self.kl, "Aspirin", steps=1)
        step = planned.steps.get()
        self.withdraw(step=step)
        self.assertEqual(self.newest().task_step, step)

    def test_a_step_of_a_task_that_is_not_planned_or_running_is_refused(
            self) -> None:
        """Requirement: Inventory forms (into a step of a task that is
        planned or running)."""
        ended = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                          ended=past(1))
        cancelled = make_task(self.kl, "Aspirin", steps=1, cancelled=True)
        failed = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                           ended=past(1), failed=True)
        before = snapshot()
        for task in (ended, cancelled, failed):
            with self.subTest(task=task.number):
                self.refused(self.withdraw(step=task.steps.get()), "step")
        self.assertEqual(snapshot(), before)

    def test_the_form_offers_the_steps_of_open_tasks(self) -> None:
        planned = make_task(self.kl, "Aspirin", steps=1)
        ended = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                          ended=past(1))
        root = page(self.client.get(lot_url(self.lot, "withdraw")))
        offered = {option.get("value") for option in root.find(
            "select", name="step").find_all("option")}
        self.assertLessEqual(
            {str(self.first.pk), str(self.second.pk),
             str(planned.steps.get().pk)}, offered)
        self.assertNotIn(str(ended.steps.get().pk), offered)

    def test_the_step_in_the_query_is_filled_in(self) -> None:
        root = page(self.client.get(
            f"{lot_url(self.lot, 'withdraw')}?step={self.second.pk}"))
        self.assertEqual(field_value(root, "step"), str(self.second.pk))

    def test_the_form_needs_a_signed_in_user(self) -> None:
        self.client.logout()
        before = snapshot()
        path = f"{lot_url(self.lot, 'withdraw')}?step={self.second.pk}"
        for response in (self.client.get(path), self.withdraw()):
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/", response["Location"])
        self.assertEqual(snapshot(), before)

    def test_an_unknown_lot_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            lot_url(self.lot, "withdraw")).status_code, 200)
        self.assertEqual(self.client.get(
            "/lab/inventory/bulk/999999/withdraw/").status_code, 404)

    def test_the_movement_names_a_protected_nullable_step(self) -> None:
        field = LotMovement._meta.get_field("task_step")
        self.assertIs(field.remote_field.model, TaskStep)
        self.assertEqual(field.remote_field.on_delete.__name__, "PROTECT")
        self.assertTrue(field.null)
        reverses = LotMovement._meta.get_field("reverses")
        self.assertTrue(reverses.one_to_one)
        self.assertIs(reverses.remote_field.model, LotMovement)
        self.assertEqual(reverses.remote_field.on_delete.__name__,
                         "PROTECT")
        self.assertTrue(reverses.null)


class ReversalTests(WithdrawalCase):

    def setUp(self) -> None:
        super().setUp()
        self.withdraw(amount="0.5")
        self.taken = self.newest()

    def test_a_reversal_returns_what_was_taken_whatever_came_after(
            self) -> None:
        self.withdraw(amount="1")
        self.client.post(reverse_url(self.taken))
        self.assertEqual(fresh(self.lot).amount, Decimal("1000"))
        returned = self.newest()
        self.assertEqual((returned.amount, returned.amount_after,
                          returned.reverses),
                         (Decimal("500"), Decimal("1000"), self.taken))

    def test_a_withdrawal_is_reversed_once(self) -> None:
        """Requirement: Bulk lots (each withdrawal reversed at most
        once)."""
        self.client.post(reverse_url(self.taken))
        before = snapshot()
        self.client.post(reverse_url(self.taken))
        self.assertEqual(snapshot(), before)
        self.assertEqual(LotMovement.objects.filter(
            reverses=self.taken).count(), 1)

    def test_only_a_withdrawal_is_reversed_through_this_url(self) -> None:
        """Requirement: Inventory forms (reverses a withdrawal not yet
        reversed)."""
        opening = self.lot.movements.order_by("id").first()
        self.assertEqual(self.client.post(
            reverse_url(self.taken)).status_code, 302)
        reversal = self.newest()
        self.assertEqual(reversal.kind, "reversal")
        for movement in (opening, reversal):
            before = snapshot()
            with self.subTest(kind=movement.kind):
                self.client.post(reverse_url(movement))
                self.assertEqual(snapshot(), before)

    def test_the_url_takes_a_post_only(self) -> None:
        before = snapshot()
        self.assertEqual(self.client.get(
            reverse_url(self.taken)).status_code, 405)
        self.assertEqual(snapshot(), before)

    def test_a_reversal_needs_a_signed_in_user(self) -> None:
        self.client.logout()
        before = snapshot()
        done = self.client.post(reverse_url(self.taken))
        self.assertEqual(done.status_code, 302)
        self.assertIn("/accounts/login/", done["Location"])
        self.assertEqual(snapshot(), before)

    def test_an_unknown_movement_answers_404(self) -> None:
        self.assertEqual(self.client.post(
            reverse_url(self.taken)).status_code, 302)
        self.assertEqual(self.client.post(
            "/lab/inventory/bulk/movements/999999/reverse/").status_code,
            404)


class LotPageTests(WithdrawalCase):

    def rows(self) -> list:
        root = page(self.client.get(lot_url(self.lot)))
        return [row for row in root.find_all("tr") if row.find("td")]

    def row_of(self, label: str) -> list:
        return [row for row in self.rows() if label in row.text()]

    def test_a_withdrawal_names_its_task_and_step(self) -> None:
        """Requirement: Bulk lot page (for a withdrawal, the task and
        step it went into, linking to the task)."""
        plain = make_task(self.kl, "Aspirin", steps=2, started=past(1))
        make_withdrawal(self.kl, self.lot, plain.steps.get(position=2),
                        "0.5")
        (row,) = self.row_of("Entnahme")
        self.assertIn(task_url(plain),
                      [a.get("href") for a in row.find_all("a")])
        self.assertIn(plain.number, row.text())
        self.assertIn("Stufe 2", row.text())

    def test_a_reversal_names_the_movement_it_reverses(self) -> None:
        """Requirement: Bulk lot page (for a reversal the movement it
        reverses)."""
        self.withdraw()
        self.client.post(reverse_url(self.newest()))
        (row,) = self.row_of("Storno")
        self.assertIn("Entnahme", row.text())

    def test_the_withdraw_link_is_for_a_signed_in_user_on_an_open_lot(
            self) -> None:
        """Requirement: Bulk lot page (`Entnahme`)."""
        path = lot_url(self.lot, "withdraw")
        root = page(self.client.get(lot_url(self.lot)))
        self.assertEqual([a.text() for a in root.find_all("a", href=path)],
                         ["Entnahme"])
        empty = make_lot(self.kl, substance=self.intermediate, unit="g",
                         amount="0")
        root = page(self.client.get(lot_url(empty)))
        self.assertIsNone(root.find("a", href=lot_url(empty, "withdraw")))
        self.client.logout()
        root = page(self.client.get(lot_url(self.lot)))
        self.assertIsNone(root.find("a", href=path))

    def test_a_withdrawal_not_reversed_has_the_button_stornieren(
            self) -> None:
        """Requirement: Bulk lot page (beside each withdrawal not yet
        reversed a button `Stornieren`)."""
        self.withdraw(amount="0.5")
        kept = self.newest()
        self.withdraw(amount="0.25")
        undone = self.newest()
        self.client.post(reverse_url(undone))
        root = page(self.client.get(lot_url(self.lot)))
        forms = {form.get("action"): form
                 for form in root.find_all("form")
                 if "/movements/" in form.get("action", "")}
        self.assertEqual(set(forms), {reverse_url(kept)})
        form = forms[reverse_url(kept)]
        self.assertEqual(form.get("method", "").lower(), "post")
        self.assertEqual(form.find("button").text(), "Stornieren")

    def test_nothing_is_offered_without_a_sign_in(self) -> None:
        self.withdraw()
        root = page(self.client.get(lot_url(self.lot)))
        self.assertIn("Stornieren", root.text())
        self.client.logout()
        root = page(self.client.get(lot_url(self.lot)))
        self.assertEqual([f for f in root.find_all("form")
                          if "/movements/" in f.get("action", "")], [])
        self.assertNotIn("Stornieren", root.text())

    def test_a_reversed_withdrawal_stays_in_the_ledger(self) -> None:
        self.withdraw()
        self.client.post(reverse_url(self.newest()))
        self.assertEqual(
            [LotMovement.objects.get(pk=row).kind for row in
             self.lot.movements.order_by("-pk").values_list(
                 "pk", flat=True)],
            ["reversal", "withdrawal", "opening"])
        self.assertEqual(len(self.row_of("Entnahme")), 2)
