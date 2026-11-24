"""Tests of the forms that act on a vessel: withdrawal and its reversal,
transfer, correction and edit (end-product-inventory: Inventory forms,
Vessels, Vessel page)."""

from datetime import date
from decimal import Decimal

from inventory.bookings import fill, write_off_flasks
from inventory.models import Vessel, VesselMovement
from tasks.models import Task, TaskStep

from . import (berlin, context_form, field_value, make_batch, make_item,
               make_task, make_vessel, make_withdrawal, page, past,
               sent_messages, substance_for, table, ticking)
from .inventory_support import (TODAY, VESSELS, FormCase, fresh, snapshot,
                                vessel_movement_url, vessel_url)
from .task_support import (TODAY_ISO, StepCase, make_product_batch,
                           steps_of)

WITHDRAWAL = "withdrawal"


def names_of(root, anchor: str) -> set[str]:
    """The names of the controls of the form that holds ``anchor``."""
    form = root.find(("input", "select", "textarea"), name=anchor
                     ).closest("form")
    return {e.get("name") for e in
            form.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in ("submit", "button")
            and e.get("name") != "csrfmiddlewaretoken"}


def newest(vessel: Vessel) -> VesselMovement:
    return vessel.movements.order_by("-pk").first()


class WithdrawalCase(StepCase):
    """A running task following ``SEQ-0002`` with the steps
    ``self.first`` and ``self.second``, and a vessel of ``2`` g of
    ``4-acetylbiphenyl``, the intermediate the first step makes."""

    def setUp(self) -> None:
        super().setUp()
        self.intermediate = substance_for("4-acetylbiphenyl")
        self.task = self.follow()
        self.first, self.second = steps_of(self.task)
        self.vessel = make_vessel(self.kl, substance=self.intermediate,
                                  unit="g", amount="2")

    def withdraw(self, step: TaskStep | None = None, amount: str = "0.5",
                 vessel: Vessel | None = None, **data: str):
        """Post the withdrawal form of ``vessel`` into ``step``, given as
        the query and as the field ``step``."""
        vessel = vessel or self.vessel
        step = step or self.second
        return self.client.post(
            f"{vessel_url(vessel, 'withdraw')}?step={step.pk}",
            {"step": str(step.pk), "amount": amount, "date": TODAY_ISO,
             **data})


class WithdrawalFormTests(WithdrawalCase):

    def test_withdrawal_and_its_reversal(self) -> None:
        """Scenario: Withdrawal and its reversal (the forms)."""
        done = self.withdraw(amount="0.5")
        self.assertRedirects(done, vessel_url(self.vessel),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.vessel).amount, Decimal("1500"))
        taken = newest(self.vessel)
        self.assertEqual(
            (taken.kind, taken.amount, taken.amount_after, taken.task_step,
             taken.user), (WITHDRAWAL, Decimal("500"), Decimal("1500"),
                           self.second, self.kl))
        self.assertIsNone(taken.reverses)

        done = self.client.post(vessel_movement_url(taken))
        self.assertRedirects(done, vessel_url(self.vessel),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.vessel).amount, Decimal("2000"))
        returned = newest(self.vessel)
        self.assertEqual(
            (returned.kind, returned.amount, returned.amount_after,
             returned.reverses, returned.user),
            (VesselMovement.Kind.REVERSAL, Decimal("500"),
             Decimal("2000"), taken, self.kl))

        before = snapshot()
        self.client.post(vessel_movement_url(taken))
        self.assertEqual(snapshot(), before)

    def test_the_movement_keeps_its_date_and_the_message_names_the_vessel(
            self) -> None:
        done = self.withdraw(date="2026-11-01")
        self.assertEqual(newest(self.vessel).date.isoformat(), "2026-11-01")
        self.assertIn(f"#{self.vessel.pk}", str(sent_messages(done)[-1]))

    def test_the_amount_is_in_the_unit_of_the_vessel(self) -> None:
        small = make_vessel(self.kl, substance=self.intermediate,
                            unit="mmol", amount="1")
        self.withdraw(vessel=small, amount="0.25")
        self.assertEqual(fresh(small).amount, Decimal("750"))
        self.assertEqual(newest(small).amount, Decimal("250"))

    def test_the_whole_vessel_may_be_taken(self) -> None:
        self.withdraw(amount="2")
        self.assertEqual(fresh(self.vessel).amount, 0)
        self.assertIn("aufgebraucht",
                      page(self.client.get(vessel_url(self.vessel))).text())

    def test_an_amount_above_the_vessel_is_refused(self) -> None:
        before = snapshot()
        self.refused(self.withdraw(amount="2.000001"), "amount")
        self.assertEqual(snapshot(), before)

    def test_a_second_withdrawal_cannot_take_more_than_is_left(self) -> None:
        self.withdraw(amount="1.5")
        before = snapshot()
        self.refused(self.withdraw(amount="0.6"), "amount")
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(self.vessel).amount, Decimal("500"))

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

    def test_a_used_up_vessel_takes_no_withdrawal(self) -> None:
        self.assertEqual(self.withdraw(amount="2").status_code, 302)
        before = snapshot()
        done = self.withdraw(amount="1")
        self.assertNotEqual(done.status_code, 302)
        self.assertEqual(snapshot(), before)

    def test_the_step_may_be_chosen_in_the_form(self) -> None:
        done = self.client.post(vessel_url(self.vessel, "withdraw"), {
            "step": str(self.first.pk), "amount": "1", "date": TODAY_ISO})
        self.assertRedirects(done, vessel_url(self.vessel),
                             fetch_redirect_response=False)
        self.assertEqual(newest(self.vessel).task_step, self.first)

    def test_a_step_of_a_planned_task_is_taken(self) -> None:
        planned = make_task(self.kl, "Aspirin", steps=1)
        step = planned.steps.get()
        self.withdraw(step=step)
        self.assertEqual(newest(self.vessel).task_step, step)

    def test_a_step_of_a_task_that_is_not_planned_or_running_is_refused(
            self) -> None:
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
        root = page(self.client.get(vessel_url(self.vessel, "withdraw")))
        offered = {option.get("value") for option in root.find(
            "select", name="step").find_all("option")}
        self.assertLessEqual(
            {str(self.first.pk), str(self.second.pk),
             str(planned.steps.get().pk)}, offered)
        self.assertNotIn(str(ended.steps.get().pk), offered)

    def test_the_step_in_the_query_is_filled_in(self) -> None:
        root = page(self.client.get(
            f"{vessel_url(self.vessel, 'withdraw')}?step={self.second.pk}"))
        self.assertEqual(field_value(root, "step"), str(self.second.pk))

    def test_the_form_needs_a_signed_in_user(self) -> None:
        self.client.logout()
        before = snapshot()
        path = f"{vessel_url(self.vessel, 'withdraw')}?step={self.second.pk}"
        for response in (self.client.get(path), self.withdraw()):
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/", response["Location"])
        self.assertEqual(snapshot(), before)

    def test_an_unknown_vessel_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            vessel_url(self.vessel, "withdraw")).status_code, 200)
        self.assertEqual(self.client.get(
            "/lab/inventory/vessels/999999/withdraw/").status_code, 404)

    def test_the_old_address_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            f"/lab/inventory/bulk/{self.vessel.pk}/withdraw/").status_code,
            404)


class ReversalViewTests(WithdrawalCase):

    def setUp(self) -> None:
        super().setUp()
        self.withdraw(amount="0.5")
        self.taken = newest(self.vessel)

    def test_a_reversal_returns_what_was_taken_whatever_came_after(
            self) -> None:
        self.withdraw(amount="1")
        self.client.post(vessel_movement_url(self.taken))
        self.assertEqual(fresh(self.vessel).amount, Decimal("1000"))
        returned = newest(self.vessel)
        self.assertEqual((returned.amount, returned.amount_after,
                          returned.reverses),
                         (Decimal("500"), Decimal("1000"), self.taken))

    def test_a_withdrawal_is_reversed_once(self) -> None:
        self.client.post(vessel_movement_url(self.taken))
        before = snapshot()
        self.client.post(vessel_movement_url(self.taken))
        self.assertEqual(snapshot(), before)
        self.assertEqual(VesselMovement.objects.filter(
            reverses=self.taken).count(), 1)

    def test_only_a_withdrawal_is_reversed_through_this_url(self) -> None:
        opening = self.vessel.movements.order_by("id").first()
        self.assertEqual(self.client.post(
            vessel_movement_url(self.taken)).status_code, 302)
        reversal = newest(self.vessel)
        self.assertEqual(reversal.kind, "reversal")
        for movement in (opening, reversal):
            before = snapshot()
            with self.subTest(kind=movement.kind):
                self.client.post(vessel_movement_url(movement))
                self.assertEqual(snapshot(), before)

    def test_the_url_takes_a_post_only(self) -> None:
        before = snapshot()
        self.assertEqual(self.client.get(
            vessel_movement_url(self.taken)).status_code, 405)
        self.assertEqual(snapshot(), before)

    def test_a_reversal_needs_a_signed_in_user(self) -> None:
        self.client.logout()
        before = snapshot()
        done = self.client.post(vessel_movement_url(self.taken))
        self.assertEqual(done.status_code, 302)
        self.assertIn("/accounts/login/", done["Location"])
        self.assertEqual(snapshot(), before)

    def test_an_unknown_movement_answers_404(self) -> None:
        self.assertEqual(self.client.post(
            "/lab/inventory/vessels/movements/999999/reverse/").status_code,
            404)

    def test_a_flask_of_a_closed_task_takes_no_reversal(self) -> None:
        """Requirement: Vessels (the reversal of a withdrawal from a
        closed task's flask is refused)."""
        task = make_task(self.kl, "CH-0012", steps=2, started=past(1))
        batch = make_product_batch(task, "2", "g", flask=True)
        flask = batch.vessels.get()
        withdrawal = make_withdrawal(self.kl, flask, self.second, "0.5")
        Task.objects.filter(pk=task.pk).update(ended=past(1))
        write_off_flasks(self.kl, Task.objects.get(pk=task.pk))
        before = snapshot()
        self.client.post(vessel_movement_url(withdrawal))
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(flask).amount, 0)


class VesselFormCase(FormCase):
    """A made batch of ``cinnamic-acid`` (molar mass 148.16) with a flask
    of ``1000`` mg."""

    def setUp(self) -> None:
        super().setUp()
        self.batch = make_batch(self.kl, "CH-0012", number="KL0412")
        self.flask = make_vessel(self.kl, self.batch, unit="mg",
                                 amount="1000", flask=True)

    def stored(self, unit: str = "mg", amount: str = "10",
               location: str = "Regal", batch=None) -> Vessel:
        return make_vessel(self.kl, batch or self.batch, unit=unit,
                           amount=amount, location=location)


class TransferFormTests(VesselFormCase):

    def url(self, vessel: Vessel | None = None) -> str:
        return vessel_url(vessel or self.flask, "transfer")

    def data(self, **over: str) -> dict[str, str]:
        data = {"amount": "250", "target": "", "location": "Regal 3",
                "date": TODAY_ISO, "note": "umgefüllt"}
        data.update(over)
        return data

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = names_of(page(self.client.get(self.url())), "amount")
        self.assertEqual(names, {"amount", "target", "location", "date",
                                 "note"})

    def test_the_targets_offered_are_the_stored_vessels_of_the_batch(
            self) -> None:
        mine = self.stored(location="Regal")
        other_batch = make_batch(self.kl, "CH-0012", number="KL5")
        foreign = self.stored(batch=other_batch)
        root = page(self.client.get(self.url()))
        values = [o.get("value") for o in
                  root.find("select", name="target").find_all("option")]
        self.assertIn("", values)
        self.assertIn(str(mine.pk), values)
        self.assertNotIn(str(foreign.pk), values)
        self.assertNotIn(str(self.flask.pk), values)

    def test_a_transfer_into_a_stored_vessel(self) -> None:
        target = self.stored(amount="100")
        done = self.client.post(self.url(), self.data(
            target=str(target.pk), location=""))
        self.assertRedirects(done, vessel_url(self.flask),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.flask).amount, Decimal("750"))
        self.assertEqual(fresh(target).amount, Decimal("350"))
        out = newest(self.flask)
        into = newest(target)
        self.assertEqual((out.kind, out.amount, out.user, out.note),
                         ("transfer_out", Decimal("250"), self.kl,
                          "umgefüllt"))
        self.assertEqual((into.kind, into.amount, into.transfer),
                         ("transfer_in", Decimal("250"), out))
        self.assertEqual(len(sent_messages(done)), 1)

    def test_a_transfer_into_a_new_vessel(self) -> None:
        """Scenario: Transfer into a new vessel (the form)."""
        done = self.client.post(self.url(), self.data(
            amount="750", location="Kühlschrank 2"))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(fresh(self.flask).amount, Decimal("250"))
        created = self.batch.vessels.get(flask=False)
        self.assertEqual(
            (created.unit, created.amount, created.location),
            ("mg", Decimal("750"), "Kühlschrank 2"))
        self.assertEqual([m.kind for m in created.movements.all()],
                         ["transfer_in"])

    def test_the_amount_is_in_the_unit_of_the_source(self) -> None:
        source = make_vessel(self.kl, make_batch(self.kl, "CH-0012",
                                                 number="KL6"),
                             unit="g", amount="2", flask=True)
        self.client.post(self.url(source), self.data(amount="0,5"))
        self.assertEqual(fresh(source).amount, Decimal("1500"))

    def test_transfer_across_units(self) -> None:
        target = self.stored(unit="umol", amount="100")
        self.client.post(self.url(), self.data(
            amount="148,16", target=str(target.pk), location=""))
        self.assertEqual(fresh(self.flask).amount, Decimal("851.84"))
        self.assertEqual(fresh(target).amount, Decimal("1100"))

    def test_an_amount_above_the_source_is_refused(self) -> None:
        before = snapshot()
        self.refused(self.client.post(self.url(), self.data(
            amount="1000,000001")), "amount")
        self.assertEqual(snapshot(), before)

    def test_refused_fields(self) -> None:
        before = snapshot()
        for field, value in (("amount", "0"), ("amount", "-1"),
                             ("amount", "x"), ("amount", ""),
                             ("date", "2026-11-05"),
                             ("location", "l" * 101)):
            with self.subTest(field=field, value=value):
                self.refused(self.client.post(
                    self.url(), self.data(**{field: value})), field)
        self.assertEqual(snapshot(), before)

    def test_a_target_the_form_does_not_offer_is_refused(self) -> None:
        foreign = self.stored(batch=make_batch(self.kl, "CH-0012",
                                               number="KL5"))
        before = snapshot()
        for target in (str(foreign.pk), str(self.flask.pk), "999999"):
            with self.subTest(target=target):
                self.refused(self.client.post(self.url(), self.data(
                    target=target, location="")), "target")
        self.assertEqual(snapshot(), before)

    def test_without_a_molar_mass_the_target_is_refused(self) -> None:
        """Scenario: Transfer without a molar mass."""
        batch = make_batch(self.kl, "X-9", number="XN1")
        source = make_vessel(self.kl, batch, unit="mg", amount="50",
                             flask=True)
        target = self.stored(unit="umol", amount="5", batch=batch)
        before = snapshot()
        self.refused(self.client.post(self.url(source), self.data(
            amount="10", target=str(target.pk), location="")), "target")
        self.assertEqual(snapshot(), before)

    def test_a_used_up_source_is_refused(self) -> None:
        empty = self.stored(amount="0")
        before = snapshot()
        response = self.client.post(self.url(empty), self.data(
            amount="1"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(context_form(response).errors)
        self.assertEqual(snapshot(), before)

    def test_the_form_needs_a_signed_in_user(self) -> None:
        self.client.logout()
        before = snapshot()
        for response in (self.client.get(self.url()),
                         self.client.post(self.url(), self.data())):
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/", response["Location"])
        self.assertEqual(snapshot(), before)

    def test_an_unknown_vessel_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            "/lab/inventory/vessels/999999/transfer/").status_code, 404)


class VesselEditFormTests(VesselFormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = make_vessel(
            self.kl, self.batch, unit="mg", amount="50", location="Alt",
            note="alt")

    def url(self) -> str:
        return vessel_url(self.target, "edit")

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        root = page(self.client.get(self.url()))
        self.assertEqual(names_of(root, "location"), {"location", "note"})
        self.assertEqual(field_value(root, "location"), "Alt")
        self.assertEqual(field_value(root, "note"), "alt")

    def test_changing_a_vessel(self) -> None:
        self.client.force_login(self.ae)
        done = self.client.post(self.url(), {"location": "Neu",
                                             "note": "neu"})
        self.assertRedirects(done, vessel_url(self.target),
                             fetch_redirect_response=False)
        vessel = fresh(self.target)
        self.assertEqual((vessel.location, vessel.note), ("Neu", "neu"))
        self.assertEqual(vessel.history.count(), 2)
        self.assertEqual(vessel.history.first().history_user, self.ae)
        self.assertEqual(len(sent_messages(done)), 1)

    def test_batch_unit_flask_and_amount_are_fixed(self) -> None:
        other = make_batch(self.kl, "CH-0012", number="KL5")
        self.client.post(self.url(), {
            "location": "", "note": "", "batch": str(other.pk),
            "unit": "g", "flask": "on", "amount": "7"})
        vessel = fresh(self.target)
        self.assertEqual(
            (vessel.batch, vessel.unit, vessel.flask, vessel.amount),
            (self.batch, "mg", False, Decimal("50")))
        self.assertEqual(vessel.movements.count(), 1)

    def test_a_refused_edit_changes_nothing(self) -> None:
        before = snapshot()
        self.refused(self.client.post(self.url(), {
            "location": "l" * 101, "note": ""}), "location")
        self.assertEqual(snapshot(), before)

    def test_an_unknown_vessel_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            "/lab/inventory/vessels/999999/edit/").status_code, 404)

    def test_a_made_vessel_is_never_sealed(self) -> None:
        """Scenario: A made vessel is never sealed."""
        with ticking(berlin(2026, 11, 24, 8)):
            done = self.client.post(self.url(), {
                "location": "Alt", "note": "alt",
                "opened_on": "2026-11-20"})
        self.assertRedirects(done, vessel_url(self.target),
                             fetch_redirect_response=False)
        self.assertIsNone(fresh(self.target).opened_on)

    def test_opening_date_entered_and_cleared(self) -> None:
        """Scenario: Opening date entered and cleared."""
        bought = make_vessel(
            self.kl, article="CH-0012", source="bought", supplier="Sigma",
            location="Alt", note="alt")
        url = vessel_url(bought, "edit")
        with ticking(berlin(2026, 11, 24, 8)):
            done = self.client.post(url, {
                "location": "Alt", "note": "alt",
                "opened_on": "2026-11-10"})
            self.assertRedirects(done, vessel_url(bought),
                                 fetch_redirect_response=False)
            self.assertEqual(fresh(bought).opened_on, date(2026, 11, 10))
            self.refused(self.client.post(url, {
                "location": "Alt", "note": "alt",
                "opened_on": "2026-11-25"}), "opened_on")
            self.assertEqual(fresh(bought).opened_on, date(2026, 11, 10))
            done = self.client.post(url, {
                "location": "Alt", "note": "alt", "opened_on": ""})
            self.assertRedirects(done, vessel_url(bought),
                                 fetch_redirect_response=False)
            self.assertIsNone(fresh(bought).opened_on)


class VesselCorrectionFormTests(VesselFormCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = make_vessel(self.kl, self.batch, unit="mg",
                                  amount="50", location="Regal")

    def data(self, **over: str) -> dict[str, str]:
        data = {"amount": "47,5", "date": TODAY.isoformat(),
                "note": "nachgewogen"}
        data.update(over)
        return data

    def url(self, vessel: Vessel | None = None) -> str:
        return vessel_url(vessel or self.target, "correct")

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = names_of(page(self.client.get(self.url())), "amount")
        self.assertEqual(names, {"amount", "date", "note"})

    def test_correction_of_a_vessel(self) -> None:
        """Scenario: Correction of a vessel (the form)."""
        done = self.client.post(self.url(), self.data())
        self.assertRedirects(done, vessel_url(self.target),
                             fetch_redirect_response=False)
        self.assertEqual(fresh(self.target).amount, Decimal("47.5"))
        latest = newest(self.target)
        self.assertEqual((latest.kind, latest.note, latest.user),
                         ("correction", "nachgewogen", self.kl))
        self.assertEqual(len(sent_messages(done)), 1)

    def test_the_amount_is_in_the_unit_of_the_vessel(self) -> None:
        vessel = make_vessel(self.kl, self.batch, unit="g", amount="1",
                             location="Regal")
        self.client.post(self.url(vessel), self.data(amount="0,5"))
        self.assertEqual(fresh(vessel).amount, Decimal("500"))

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

    def test_a_closed_tasks_flask_takes_no_correction(self) -> None:
        """Scenario: A closed task's flask stays empty (the form)."""
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        flask = make_product_batch(task, "2", "g", flask=True
                                   ).vessels.get()
        Task.objects.filter(pk=task.pk).update(ended=past(1))
        write_off_flasks(self.kl, Task.objects.get(pk=task.pk))
        before = snapshot()
        response = self.client.post(self.url(flask), self.data(
            amount="1000"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(context_form(response).errors)
        self.assertEqual(snapshot(), before)
        self.assertEqual(fresh(flask).amount, 0)

    def test_an_unknown_vessel_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            "/lab/inventory/vessels/999999/correct/").status_code, 404)


class VesselPageLinkTests(VesselFormCase):
    """Requirement: Vessel page (`Entnahme` and `Umfüllen` on an open
    vessel, `Korrigieren`, `Bearbeiten`)."""

    def hrefs(self, vessel: Vessel) -> dict[str, str]:
        root = page(self.client.get(vessel_url(vessel)))
        return {a.text(): a.get("href") for a in root.find_all("a")}

    def test_a_signed_in_user_sees_the_links_of_an_open_vessel(self) -> None:
        links = self.hrefs(self.flask)
        self.assertEqual(links["Korrigieren"],
                         vessel_url(self.flask, "correct"))
        self.assertEqual(links["Bearbeiten"], vessel_url(self.flask, "edit"))
        self.assertEqual(links["Entnahme"],
                         vessel_url(self.flask, "withdraw"))
        self.assertEqual(links["Umfüllen"],
                         vessel_url(self.flask, "transfer"))

    def test_a_used_up_vessel_offers_neither_withdrawal_nor_transfer(
            self) -> None:
        empty = self.stored(amount="0")
        links = self.hrefs(empty)
        self.assertIn("Korrigieren", links)
        self.assertIn("Bearbeiten", links)
        self.assertNotIn("Entnahme", links)
        self.assertNotIn("Umfüllen", links)

    def test_a_visitor_sees_no_link_to_a_form(self) -> None:
        self.client.logout()
        links = self.hrefs(self.flask)
        for text in ("Korrigieren", "Bearbeiten", "Entnahme", "Umfüllen"):
            self.assertNotIn(text, links)


class VesselOpenedDisplayTests(FormCase):
    """Requirement: Vessel list, Vessel page (`opened_on` / `versiegelt`)."""

    def setUp(self) -> None:
        super().setUp()
        self.made = make_vessel(self.kl, article="CH-0012", number="B-MADE")
        self.sealed = make_vessel(
            self.kl, article="CH-0012", source="bought", supplier="Sigma",
            supplier_batch="B-SEALED")
        self.opened = make_vessel(
            self.kl, article="CH-0012", source="bought", supplier="Sigma",
            supplier_batch="B-OPEN")
        item = make_item(self.kl, "CH-0012", size="10", unit="umol",
                         quantity=0)
        fill(self.kl, item, count=1, vessel=self.opened,
             date=date(2026, 11, 2))

    def test_the_vessel_list_shows_opened_on_and_sealed_for_bought_vessels(
            self) -> None:
        """Requirement: Vessel list ("with the columns `Gefäß`, `Name`,
        `Artikelnr.`, `Art`, `Charge`, `Herkunft`, `Menge`, `Ort`,
        `Datum`, `Angebrochen` and `Bemerkung` ... for a vessel of a
        bought batch its `opened_on` or `versiegelt`, and nothing for
        one of a made batch")."""
        header, rows = table(page(self.client.get(VESSELS)))
        self.assertIn("Angebrochen", header)
        by_batch = {row["Charge"].text(): row for row in rows}
        self.assertEqual(by_batch["B-SEALED"]["Angebrochen"].text(),
                         "versiegelt")
        self.assertEqual(by_batch["B-OPEN"]["Angebrochen"].text(),
                         "02.11.2026")
        self.assertEqual(by_batch["B-MADE"]["Angebrochen"].text(), "")

    def test_the_vessel_page_shows_opened_on_or_sealed(self) -> None:
        """Requirement: Vessel page ("for a vessel of a bought batch
        `Angebrochen am <date>` or `versiegelt`")."""
        sealed_text = page(self.client.get(vessel_url(self.sealed))).text()
        self.assertIn("versiegelt", sealed_text)
        opened_text = page(self.client.get(vessel_url(self.opened))).text()
        self.assertIn("Angebrochen am 02.11.2026", opened_text)
        made_text = page(self.client.get(vessel_url(self.made))).text()
        self.assertNotIn("Angebrochen am", made_text)
        self.assertNotIn("versiegelt", made_text)
