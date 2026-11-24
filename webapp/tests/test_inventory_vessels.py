"""Tests of the vessels, their movements and the bookings that change
them (end-product-inventory: Vessels; Item movements)."""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import translation

from inventory.bookings import (correct_vessel, fill, open_vessel,
                                record_batch, reverse, reverse_withdrawal,
                                transfer, withdraw, write_off_flasks)
from inventory.figures import convert
from inventory.models import Batch, Movement, Vessel, VesselMovement
from tasks.models import Task, TaskStep

from . import (berlin, make_batch, make_item, make_task, make_vessel,
               make_withdrawal, past, substance_for, ticking)
from .inventory_support import TODAY, InventoryCase, fresh, newest_movement
from .task_support import StepCase, make_product_batch, steps_of

MW = Decimal("148.16")


def newest(vessel: Vessel) -> VesselMovement:
    return vessel.movements.order_by("-pk").first()


class ConvertTests(SimpleTestCase):

    def test_units_of_one_kind_convert_by_their_factors(self) -> None:
        cases = [("1", "g", "mg", "1000"), ("2500", "mg", "g", "2.5"),
                 ("1", "mmol", "umol", "1000"),
                 ("500", "umol", "mmol", "0.5"),
                 ("3.5", "mg", "mg", "3.5"), ("2", "g", "g", "2"),
                 ("7", "umol", "umol", "7"), ("2", "mmol", "mmol", "2")]
        for amount, unit, to, want in cases:
            with self.subTest(unit=unit, to=to):
                self.assertEqual(
                    convert(Decimal(amount), unit, to, None), Decimal(want))

    def test_mass_and_amount_of_substance_convert_through_the_mass(
            self) -> None:
        cases = [("10", "umol", "mg", "1.4816"),
                 ("1", "mmol", "g", "0.14816"),
                 ("1", "mmol", "mg", "148.16"),
                 ("1000", "umol", "g", "0.14816"),
                 ("148.16", "mg", "mmol", "1"),
                 ("148.16", "mg", "umol", "1000"),
                 ("0.14816", "g", "mmol", "1")]
        for amount, unit, to, want in cases:
            with self.subTest(unit=unit, to=to):
                self.assertEqual(
                    convert(Decimal(amount), unit, to, MW), Decimal(want))

    def test_the_result_is_not_rounded(self) -> None:
        shown = convert(Decimal("1"), "mg", "umol", MW)
        self.assertAlmostEqual(float(shown), 1000 / 148.16, places=9)
        self.assertGreater(len(shown.as_tuple().digits), 6)

    def test_a_float_molar_mass_is_accepted(self) -> None:
        shown = convert(Decimal("10"), "umol", "mg", 148.16)
        self.assertAlmostEqual(float(shown), 1.4816, places=9)

    def test_without_a_molar_mass_the_kinds_do_not_convert(self) -> None:
        for unit, to in (("mg", "umol"), ("umol", "g"), ("g", "mmol"),
                         ("mmol", "mg")):
            for mass in (None, Decimal("0")):
                with self.subTest(unit=unit, to=to, mass=mass):
                    self.assertIsNone(convert(Decimal("5"), unit, to, mass))

    def test_the_mass_does_not_matter_within_a_kind(self) -> None:
        self.assertEqual(convert(Decimal("1"), "g", "mg", MW),
                         Decimal("1000"))


class VesselModelTests(InventoryCase):
    """Requirement: Vessels (the fields)."""

    def test_a_vessel_keeps_its_fields(self) -> None:
        made = make_vessel(self.kl, article="CH-0012", unit="g",
                           amount="2", location="Kühlraum", note="Rest")
        vessel = Vessel.objects.get(pk=made.pk)
        self.assertEqual(
            (vessel.batch, vessel.unit, vessel.flask, vessel.location,
             vessel.note), (made.batch, "g", False, "Kühlraum", "Rest"))
        self.assertEqual(vessel.amount, Decimal("2000"))

    def test_the_four_units_and_six_places(self) -> None:
        self.assertEqual(
            {value for value, _ in Vessel._meta.get_field("unit").choices},
            {"mg", "g", "umol", "mmol"})
        self.assertEqual(Vessel._meta.get_field("amount").decimal_places, 6)

    def test_location_and_note_are_optional(self) -> None:
        vessel = fresh(make_vessel(self.kl, article="CH-0012"))
        self.assertEqual((vessel.location, vessel.note, vessel.flask),
                         ("", "", False))
        self.assertEqual(Vessel._meta.get_field("location").max_length, 100)

    def test_a_vessel_names_its_batch_by_a_protected_key(self) -> None:
        field = Vessel._meta.get_field("batch")
        self.assertIs(field.remote_field.model, Batch)
        self.assertEqual(field.remote_field.on_delete.__name__, "PROTECT")
        self.assertEqual(field.remote_field.related_name, "vessels")

    def test_a_vessel_has_the_substance_of_its_batch(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012")
        self.assertEqual(vessel.substance, vessel.batch.substance)
        names = {field.name for field in Vessel._meta.get_fields()}
        self.assertNotIn("substance", names)

    def test_the_article_number_is_the_substances(self) -> None:
        make_item(self.kl, "CH-0012")
        self.assertEqual(
            make_vessel(self.kl, article="CH-0012").article_number,
            "CH-0012")
        self.assertIsNone(
            make_vessel(self.kl, article="acetophenone").article_number)

    def test_a_vessel_shows_as_its_batch_and_its_id(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012", number="KL0412")
        self.assertEqual(str(vessel), f"KL0412 #{vessel.pk}")

    def test_the_amount_is_shown_in_its_unit_to_three_places(self) -> None:
        cases = [("g", "1", "1"), ("mg", "47.5", "47.5"),
                 ("mmol", "2.5", "2.5"), ("mg", "0.0005", "0.001"),
                 ("g", "0.0005", "0.001")]
        for unit, amount, want in cases:
            with self.subTest(unit=unit, amount=amount):
                vessel = make_vessel(self.kl, article="CH-0012", unit=unit,
                                     amount=amount)
                self.assertEqual(vessel.shown_amount, Decimal(want))

    def test_the_unit_is_labelled(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012", unit="umol")
        self.assertEqual(vessel.unit_label, "µmol")

    def test_the_history_leaves_out_the_amount(self) -> None:
        names = {f.name for f in Vessel.history.model._meta.get_fields()}
        self.assertNotIn("amount", names)
        self.assertIn("location", names)

    def test_a_vessel_keeps_a_history(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012")
        self.assertEqual(vessel.history.get().history_user, self.kl)

    def test_a_vessel_at_zero_is_used_up(self) -> None:
        self.assertEqual(
            make_vessel(self.kl, article="CH-0012", amount="0").amount, 0)


class VesselKindTests(InventoryCase):
    """Requirement: Vessels (a vessel's kind)."""

    def kinds(self) -> list[str]:
        make_item(self.kl, "CH-0012")
        made = make_batch(self.kl, "CH-0012", number="KL0412")
        flask = make_vessel(self.kl, made, flask=True)
        stored = make_vessel(self.kl, made, location="Regal")
        intermediate = make_vessel(self.kl, article="acetophenone")
        reagent = make_vessel(self.kl, article="acetophenone",
                              source="bought", supplier="Sigma")
        return [vessel.kind for vessel in
                (flask, stored, intermediate, reagent)]

    def test_kinds_of_vessels(self) -> None:
        """Scenario: Kinds of vessels."""
        self.assertEqual(self.kinds(), ["flask", "end-product",
                                        "intermediate", "reagent"])

    def test_the_labels(self) -> None:
        make_item(self.kl, "CH-0012")
        made = make_batch(self.kl, "CH-0012", number="KL0412")
        flask = make_vessel(self.kl, made, flask=True)
        stored = make_vessel(self.kl, made)
        intermediate = make_vessel(self.kl, article="acetophenone")
        reagent = make_vessel(self.kl, article="acetophenone",
                              source="bought")
        with translation.override("de"):
            self.assertEqual(
                [v.kind_label for v in (flask, stored, intermediate,
                                        reagent)],
                ["Kolben", "Endprodukt", "Zwischenprodukt", "Reagenz"])
        with translation.override("en"):
            self.assertEqual(
                [str(v.kind_label) for v in (flask, stored, intermediate,
                                             reagent)],
                ["Flask", "End product", "Intermediate", "Reagent"])

    def test_a_flask_of_a_substance_without_an_article_is_a_flask(
            self) -> None:
        made = make_batch(self.kl, "acetophenone")
        self.assertEqual(make_vessel(self.kl, made, flask=True).kind,
                         "flask")

    def test_the_kind_follows_the_article_of_the_substance(self) -> None:
        vessel = make_vessel(self.kl, article="acetophenone")
        self.assertEqual(vessel.kind, "intermediate")
        make_item(self.kl, substance=vessel.substance, article="X-77")
        self.assertEqual(fresh(vessel).kind, "end-product")


class MovementKindTests(SimpleTestCase):
    """Requirement: Vessels (the movements' kinds)."""

    def test_the_kinds_and_their_german_labels(self) -> None:
        want = {"opening": "Anfangsmenge", "filling": "Abfüllung",
                "withdrawal": "Entnahme",
                "transfer_out": "Umfüllung (Abgang)",
                "transfer_in": "Umfüllung (Zugang)",
                "correction": "Korrektur", "remainder": "Restausbuchung",
                "reversal": "Storno"}
        self.assertEqual({value for value, _ in
                          VesselMovement.Kind.choices}, set(want))
        with translation.override("de"):
            self.assertEqual(
                {value: str(label) for value, label in
                 VesselMovement.Kind.choices}, want)

    def test_the_english_labels(self) -> None:
        want = {"opening": "Opening amount", "filling": "Filling",
                "withdrawal": "Withdrawal", "transfer_out": "Transfer out",
                "transfer_in": "Transfer in", "correction": "Correction",
                "remainder": "Remainder written off",
                "reversal": "Reversal"}
        with translation.override("en"):
            self.assertEqual(
                {value: str(label) for value, label in
                 VesselMovement.Kind.choices}, want)

    def test_the_references_of_a_movement(self) -> None:
        vessel = VesselMovement._meta.get_field("vessel")
        self.assertEqual(vessel.remote_field.related_name, "movements")
        step = VesselMovement._meta.get_field("task_step")
        self.assertIs(step.remote_field.model, TaskStep)
        self.assertEqual(step.remote_field.on_delete.__name__, "PROTECT")
        self.assertEqual(step.remote_field.related_name, "vessel_movements")
        self.assertTrue(step.null)
        for name, reverse_name in (("transfer", "transferred"),
                                   ("reverses", "reversal")):
            with self.subTest(field=name):
                field = VesselMovement._meta.get_field(name)
                self.assertTrue(field.one_to_one)
                self.assertIs(field.remote_field.model, VesselMovement)
                self.assertTrue(field.null)
                self.assertEqual(field.remote_field.related_name,
                                 reverse_name)

    def test_an_item_movement_names_a_vessel_movement(self) -> None:
        field = Movement._meta.get_field("vessel_movement")
        self.assertTrue(field.one_to_one)
        self.assertIs(field.remote_field.model, VesselMovement)
        self.assertTrue(field.null)
        self.assertEqual(field.remote_field.related_name, "item_movement")
        self.assertEqual(field.remote_field.on_delete.__name__, "PROTECT")
        names = {f.name for f in Movement._meta.get_fields()}
        self.assertNotIn("bulk_movement", names)

    def test_no_check_constraint_backs_the_vessel_movement(self) -> None:
        names = [c.name for c in Movement._meta.constraints]
        self.assertEqual([n for n in names if "vessel" in n], [])


class OpeningTests(InventoryCase):
    """The booking ``open_vessel``."""

    def test_a_stored_vessel_opens_with_its_amount(self) -> None:
        batch = make_batch(self.kl, "CH-0012", number="KL1")
        vessel = open_vessel(self.kl, batch, unit="g", amount=Decimal("2"),
                             location="Kühlschrank 2", note="Rest")
        stored = fresh(vessel)
        self.assertEqual(
            (stored.batch, stored.unit, stored.amount, stored.flask,
             stored.location, stored.note),
            (batch, "g", Decimal("2000"), False, "Kühlschrank 2", "Rest"))
        opening = stored.movements.get()
        self.assertEqual(
            (opening.kind, opening.amount, opening.amount_after,
             opening.user, opening.date),
            ("opening", Decimal("2000"), Decimal("2000"), self.kl, TODAY))
        self.assertIsNotNone(opening.booked_at)
        self.assertEqual(stored.history.get().history_user, self.kl)

    def test_the_amount_is_kept_in_the_base_unit(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        cases = [("mg", "5", "5"), ("g", "1", "1000"), ("umol", "5", "5"),
                 ("mmol", "2", "2000"), ("g", "0.0015", "1.5"),
                 ("mg", "0.000001", "0.000001")]
        for unit, amount, base in cases:
            with self.subTest(unit=unit, amount=amount):
                vessel = open_vessel(self.kl, batch, unit=unit,
                                     amount=Decimal(amount))
                self.assertEqual(fresh(vessel).amount, Decimal(base))
                self.assertEqual(vessel.movements.get().amount_after,
                                 Decimal(base))

    def test_the_date_may_be_given(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        vessel = open_vessel(self.kl, batch, unit="mg",
                             amount=Decimal("1"), date=date(2026, 11, 1))
        self.assertEqual(vessel.movements.get().date, date(2026, 11, 1))

    def test_a_vessel_opens_at_zero_used_up(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        vessel = open_vessel(self.kl, batch, unit="mg", amount=Decimal("0"))
        self.assertEqual(fresh(vessel).amount, 0)

    def test_refusals(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        cases = [("amount", {"amount": Decimal("-1"), "unit": "mg"}),
                 ("unit", {"amount": Decimal("1"), "unit": "kg"}),
                 ("unit", {"amount": Decimal("1"), "unit": ""}),
                 ("location", {"amount": Decimal("1"), "unit": "mg",
                               "location": "l" * 101}),
                 ("date", {"amount": Decimal("1"), "unit": "mg",
                           "date": date(2026, 11, 5)})]
        for field, kwargs in cases:
            with self.subTest(field=field), self.refusing(field):
                open_vessel(self.kl, batch, **kwargs)
        self.assertFalse(batch.vessels.exists())

    def test_a_batch_has_one_flask_at_most(self) -> None:
        """Requirement: Vessels (a batch has at most one flask; every
        other vessel is stored)."""
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        batch = record_batch(
            self.kl, substance=task.substance, number="KL1",
            task_step=task.steps.get(), amount=Decimal("2"), unit="g")
        open_vessel(self.kl, batch, unit="g", amount=Decimal("1"))
        flask = batch.vessels.get(flask=True)
        transfer(self.kl, flask, amount=Decimal("1"), location="Regal")
        self.assertEqual(batch.vessels.filter(flask=True).count(), 1)
        self.assertEqual(batch.vessels.filter(flask=False).count(), 2)


class CorrectionTests(InventoryCase):

    def test_correction_of_a_vessel(self) -> None:
        """Scenario: Correction of a vessel."""
        vessel = self.vessel(amount="50")
        movement = correct_vessel(self.kl, vessel, amount=Decimal("47.5"),
                                  note="nachgewogen")
        self.assertEqual(fresh(vessel).amount, Decimal("47.5"))
        latest = newest(vessel)
        self.assertEqual(latest.pk, movement.pk)
        self.assertEqual(latest.kind, VesselMovement.Kind.CORRECTION)
        self.assertEqual((latest.amount, latest.amount_after),
                         (Decimal("47.5"), Decimal("47.5")))
        self.assertEqual((latest.user, latest.note),
                         (self.kl, "nachgewogen"))
        self.assertEqual(latest.date, TODAY)

    def test_the_amount_is_in_the_unit_of_the_vessel(self) -> None:
        vessel = self.vessel(unit="g", amount="1")
        correct_vessel(self.kl, vessel, amount=Decimal("0.5"),
                       note="gewogen")
        self.assertEqual(fresh(vessel).amount, Decimal("500"))

    def test_a_note_is_required(self) -> None:
        vessel = self.vessel()
        for note in ("", "  "):
            with self.subTest(note=note), self.refusing("note"):
                correct_vessel(self.kl, vessel, amount=Decimal("40"),
                               note=note)

    def test_a_negative_amount_is_refused(self) -> None:
        vessel = self.vessel()
        with self.refusing("amount"):
            correct_vessel(self.kl, vessel, amount=Decimal("-1"), note="x")

    def test_a_vessel_corrected_to_zero_is_used_up(self) -> None:
        vessel = self.vessel()
        correct_vessel(self.kl, vessel, amount=Decimal("0"), note="leer")
        self.assertEqual(fresh(vessel).amount, 0)

    def test_a_used_up_vessel_may_be_corrected_upwards(self) -> None:
        vessel = self.vessel(amount="0")
        correct_vessel(self.kl, vessel, amount=Decimal("3"), note="Fund")
        self.assertEqual(fresh(vessel).amount, Decimal("3"))

    def test_the_date_may_be_given_and_not_lie_ahead(self) -> None:
        vessel = self.vessel()
        movement = correct_vessel(self.kl, vessel, amount=Decimal("40"),
                                  note="x", date=date(2026, 11, 1))
        self.assertEqual(movement.date, date(2026, 11, 1))
        with self.refusing("date"):
            correct_vessel(self.kl, vessel, amount=Decimal("30"), note="x",
                           date=date(2026, 11, 5))

    def test_the_amount_of_a_stale_vessel_is_not_trusted(self) -> None:
        vessel = self.vessel(amount="50")
        correct_vessel(self.kl, fresh(vessel), amount=Decimal("45"),
                       note="x")
        correct_vessel(self.kl, vessel, amount=Decimal("46"), note="y")
        self.assertEqual(newest(vessel).amount_after, Decimal("46"))


class ClosedFlaskCase(InventoryCase):
    """A task with a step, whose batch has a flask with ``2`` g of
    ``cinnamic-acid``, and an item of 10 µmol to fill."""

    def setUp(self) -> None:
        super().setUp()
        self.task = make_task(self.kl, "CH-0012", steps=1,
                              started=past(1))
        self.batch = make_product_batch(self.task, "2", "g", flask=True)
        self.flask = self.batch.vessels.get()
        self.step = self.task.steps.get()
        self.stocked = self.item("CH-0012", size="10", unit="umol",
                                 quantity=0)

    def close(self, how: str = "ended") -> None:
        """Close the task the way ``how`` says, and write off its
        flasks."""
        fields = {"ended": {"ended": past(1)},
                  "failed": {"ended": past(1), "failed": True},
                  "cancelled": {"cancelled": True}}[how]
        Task.objects.filter(pk=self.task.pk).update(**fields)
        write_off_flasks(self.kl, Task.objects.get(pk=self.task.pk))


class ClosedFlaskTests(ClosedFlaskCase):
    """Requirement: Vessels (a flask whose task is ended, failed or
    cancelled stays at zero)."""

    def test_a_closed_tasks_flask_stays_empty(self) -> None:
        """Scenario: A closed task's flask stays empty."""
        filling = fill(self.kl, self.stocked, count=5, vessel=self.flask)
        self.close()
        before_quantity = fresh(self.stocked).quantity
        with self.refusing():
            reverse(self.kl, filling, note="doppelt")
        with self.refusing():
            correct_vessel(self.kl, self.flask, amount=Decimal("1"),
                           note="nachgewogen")
        self.assertEqual(fresh(self.stocked).quantity, before_quantity)
        self.assertEqual(fresh(self.flask).amount, 0)

    def test_every_closing_state_keeps_the_flask_closed(self) -> None:
        for how in ("ended", "failed", "cancelled"):
            with self.subTest(how=how):
                Task.objects.filter(pk=self.task.pk).update(
                    ended=None, failed=False, cancelled=False)
                Vessel.objects.filter(pk=self.flask.pk).update(
                    amount=Decimal("2000"))
                self.close(how)
                with self.refusing():
                    correct_vessel(self.kl, self.flask,
                                   amount=Decimal("1"), note="x")
                self.assertEqual(fresh(self.flask).amount, 0)

    def test_a_withdrawal_from_it_is_not_reversed_back(self) -> None:
        withdrawal = make_withdrawal(self.kl, self.flask, self.step, "0.5")
        self.close()
        with self.refusing():
            reverse_withdrawal(self.kl, withdrawal)
        self.assertEqual(fresh(self.flask).amount, 0)

    def test_a_flask_of_an_open_task_takes_corrections(self) -> None:
        correct_vessel(self.kl, self.flask, amount=Decimal("1"), note="x")
        self.assertEqual(fresh(self.flask).amount, Decimal("1000"))

    def test_a_stored_vessel_of_a_closed_task_takes_corrections(
            self) -> None:
        stored = make_vessel(self.kl, self.batch, unit="g", amount="1",
                             location="Regal")
        self.close()
        correct_vessel(self.kl, stored, amount=Decimal("2"), note="x")
        self.assertEqual(fresh(stored).amount, Decimal("2000"))

    def test_a_filling_from_a_stored_vessel_reverses_after_the_task_closed(
            self) -> None:
        stored = make_vessel(self.kl, self.batch, unit="g", amount="1",
                             location="Regal")
        filling = fill(self.kl, self.stocked, count=5, vessel=stored)
        self.close()
        reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(stored).amount, Decimal("1000"))


class WriteOffTests(ClosedFlaskCase):
    """The service ``write_off_flasks`` (Vessels: `remainder`)."""

    def test_the_flask_is_written_off_whole(self) -> None:
        booked = write_off_flasks(self.kl, self.task)
        self.assertEqual(len(booked), 1)
        self.assertEqual(fresh(self.flask).amount, 0)
        remainder = newest(self.flask)
        self.assertEqual(remainder.pk, booked[0].pk)
        self.assertEqual(
            (remainder.kind, remainder.amount, remainder.amount_after,
             remainder.user, remainder.date),
            ("remainder", Decimal("2000"), Decimal("0"), self.kl, TODAY))

    def test_it_also_writes_off_what_is_left_after_a_transfer(self) -> None:
        """Scenario: Ending writes off the flask (the service)."""
        transfer(self.kl, self.flask, amount=Decimal("1.5"),
                 location="Kühlschrank 2")
        stored = self.batch.vessels.get(flask=False)
        write_off_flasks(self.kl, self.task)
        self.assertEqual(fresh(self.flask).amount, 0)
        self.assertEqual(
            (newest(self.flask).kind, newest(self.flask).amount),
            ("remainder", Decimal("500")))
        self.assertEqual(fresh(stored).amount, Decimal("1500"))

    def test_a_flask_without_an_amount_books_nothing(self) -> None:
        correct_vessel(self.kl, self.flask, amount=Decimal("0"), note="leer")
        count = self.flask.movements.count()
        self.assertEqual(write_off_flasks(self.kl, self.task), [])
        self.assertEqual(self.flask.movements.count(), count)

    def test_stored_vessels_and_other_tasks_flasks_are_left(self) -> None:
        stored = make_vessel(self.kl, self.batch, unit="g", amount="1",
                             location="Regal")
        other = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        other_flask = make_product_batch(other, "3", "g",
                                         flask=True).vessels.get()
        write_off_flasks(self.kl, self.task)
        self.assertEqual(fresh(stored).amount, Decimal("1000"))
        self.assertEqual(fresh(other_flask).amount, Decimal("3000"))

    def test_a_batch_recorded_without_a_step_has_no_flask_to_write_off(
            self) -> None:
        plain = make_batch(self.kl, "CH-0012", number="OLD1")
        vessel = make_vessel(self.kl, plain, location="Regal")
        write_off_flasks(self.kl, self.task)
        self.assertEqual(fresh(vessel).amount, Decimal("50"))

    def test_each_flask_of_the_tasks_batches_is_written_off(self) -> None:
        both = make_task(self.kl, "CH-0012", steps=2, started=past(1))
        first = make_product_batch(both, "1", "g", flask=True,
                                   number="K-A")
        second = make_batch(
            self.kl, "acetophenone", number="K-B",
            task_step=both.steps.get(position=1))
        other_flask = make_vessel(self.kl, second, unit="mg", amount="300",
                                  flask=True)
        booked = write_off_flasks(self.kl, both)
        self.assertEqual(len(booked), 2)
        self.assertEqual(fresh(first.vessels.get()).amount, 0)
        self.assertEqual(fresh(other_flask).amount, 0)

    def test_it_runs_on_a_task_that_is_already_closed(self) -> None:
        Task.objects.filter(pk=self.task.pk).update(ended=past(1))
        write_off_flasks(self.kl, Task.objects.get(pk=self.task.pk))
        self.assertEqual(fresh(self.flask).amount, 0)


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


class WithdrawalTests(WithdrawalCase):

    def test_withdrawal_and_its_reversal(self) -> None:
        """Scenario: Withdrawal and its reversal."""
        taken = withdraw(self.kl, self.vessel, task_step=self.second,
                         amount=Decimal("0.5"))
        self.assertEqual(fresh(self.vessel).amount, Decimal("1500"))
        self.assertEqual(
            (taken.kind, taken.amount, taken.amount_after, taken.task_step,
             taken.user, taken.reverses),
            ("withdrawal", Decimal("500"), Decimal("1500"), self.second,
             self.kl, None))
        returned = reverse_withdrawal(self.kl, taken)
        self.assertEqual(fresh(self.vessel).amount, Decimal("2000"))
        self.assertEqual(
            (returned.kind, returned.amount, returned.amount_after,
             returned.reverses, returned.user),
            ("reversal", Decimal("500"), Decimal("2000"), taken, self.kl))
        with self.refusing():
            reverse_withdrawal(self.kl, taken)

    def test_the_amount_is_in_the_unit_of_the_vessel(self) -> None:
        small = make_vessel(self.kl, substance=self.intermediate,
                            unit="mmol", amount="1")
        movement = withdraw(self.kl, small, task_step=self.second,
                            amount=Decimal("0.25"))
        self.assertEqual(fresh(small).amount, Decimal("750"))
        self.assertEqual(movement.amount, Decimal("250"))

    def test_the_whole_vessel_may_be_taken(self) -> None:
        withdraw(self.kl, self.vessel, task_step=self.second,
                 amount=Decimal("2"))
        self.assertEqual(fresh(self.vessel).amount, 0)

    def test_an_amount_above_the_vessel_is_refused(self) -> None:
        with self.refusing("amount"):
            withdraw(self.kl, self.vessel, task_step=self.second,
                     amount=Decimal("2.000001"))

    def test_a_second_withdrawal_cannot_take_more_than_is_left(self) -> None:
        withdraw(self.kl, self.vessel, task_step=self.second,
                 amount=Decimal("1.5"))
        with self.refusing("amount"):
            withdraw(self.kl, self.vessel, task_step=self.second,
                     amount=Decimal("0.6"))
        self.assertEqual(fresh(self.vessel).amount, Decimal("500"))

    def test_an_amount_of_zero_or_less_is_refused(self) -> None:
        for amount in ("0", "-1", "0.0000004"):
            with self.subTest(amount=amount), self.refusing("amount"):
                withdraw(self.kl, self.vessel, task_step=self.second,
                         amount=Decimal(amount))

    def test_a_date_in_the_future_is_refused(self) -> None:
        with self.refusing("date"):
            withdraw(self.kl, self.vessel, task_step=self.second,
                     amount=Decimal("1"), date=date(2026, 11, 5))

    def test_the_date_and_the_note_are_kept(self) -> None:
        movement = withdraw(self.kl, self.vessel, task_step=self.second,
                            amount=Decimal("1"), date=date(2026, 11, 1),
                            note="Ansatz")
        self.assertEqual((movement.date, movement.note),
                         (date(2026, 11, 1), "Ansatz"))

    def test_a_used_up_vessel_takes_no_withdrawal(self) -> None:
        empty = make_vessel(self.kl, substance=self.intermediate, unit="g",
                            amount="0")
        with self.refusing():
            withdraw(self.kl, empty, task_step=self.second,
                     amount=Decimal("1"))

    def test_a_step_of_a_planned_task_is_taken(self) -> None:
        planned = make_task(self.kl, "Aspirin", steps=1)
        step = planned.steps.get()
        movement = withdraw(self.kl, self.vessel, task_step=step,
                            amount=Decimal("1"))
        self.assertEqual(movement.task_step, step)

    def test_a_step_of_a_task_that_is_not_planned_or_running_is_refused(
            self) -> None:
        ended = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                          ended=past(1))
        cancelled = make_task(self.kl, "Aspirin", steps=1, cancelled=True)
        failed = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                           ended=past(1), failed=True)
        for task in (ended, cancelled, failed):
            with self.subTest(task=task.number), self.refusing("step"):
                withdraw(self.kl, self.vessel, task_step=task.steps.get(),
                         amount=Decimal("1"))

    def test_the_amount_of_a_stale_vessel_is_not_trusted(self) -> None:
        """Requirement: Vessels (one atomic conditional update)."""
        stale = make_vessel(self.kl, substance=self.intermediate, unit="mg",
                            amount="50")
        withdraw(self.kl, fresh(stale), task_step=self.second,
                 amount=Decimal("45"))
        self.assertEqual(stale.amount, Decimal("50"))
        with self.refusing("amount"):
            withdraw(self.kl, stale, task_step=self.second,
                     amount=Decimal("20"))
        self.assertEqual(fresh(stale).amount, Decimal("5"))

    def test_a_flask_of_an_open_task_is_withdrawn_from(self) -> None:
        flask = make_vessel(self.kl, substance=self.intermediate,
                            unit="g", amount="1", flask=True,
                            task_step=self.first)
        withdraw(self.kl, flask, task_step=self.second,
                 amount=Decimal("0.4"))
        self.assertEqual(fresh(flask).amount, Decimal("600"))

    def test_a_bought_bottle_is_opened_by_its_first_withdrawal(
            self) -> None:
        """Scenario: A bought bottle is opened by its first
        withdrawal."""
        with ticking(berlin(2026, 11, 24, 8)):
            batch = record_batch(
                self.kl, substance=substance_for("acetophenone"),
                source="bought", supplier="Sigma",
                amount=Decimal("100"), unit="g",
                location="Chemikalienschrank 1")
            vessel = batch.vessels.get()
            self.assertIsNone(vessel.opened_on)
            withdraw(self.kl, vessel, task_step=self.second,
                     amount=Decimal("5"), date=date(2026, 11, 20))
            self.assertEqual(fresh(vessel).opened_on, date(2026, 11, 20))
            withdraw(self.kl, fresh(vessel), task_step=self.second,
                     amount=Decimal("5"), date=date(2026, 11, 22))
            self.assertEqual(fresh(vessel).opened_on, date(2026, 11, 20))

    def test_a_correction_and_a_reversal_leave_opened_on(self) -> None:
        """Requirement: Vessels ("a correction, and the reversal of the
        movement, leave it as it is.")."""
        sealed = make_vessel(self.kl, article="CH-0012", source="bought",
                             supplier="Sigma", unit="g", amount="2")
        correct_vessel(self.kl, sealed, amount=Decimal("1.9"),
                       note="nachgewogen", date=date(2026, 11, 1))
        self.assertIsNone(fresh(sealed).opened_on)
        taken = withdraw(self.kl, fresh(sealed), task_step=self.second,
                         amount=Decimal("0.5"), date=date(2026, 11, 2))
        self.assertEqual(fresh(sealed).opened_on, date(2026, 11, 2))
        reverse_withdrawal(self.kl, taken)
        self.assertEqual(fresh(sealed).opened_on, date(2026, 11, 2))
        correct_vessel(self.kl, fresh(sealed), amount=Decimal("1.8"),
                       note="nachgewogen", date=date(2026, 11, 3))
        self.assertEqual(fresh(sealed).opened_on, date(2026, 11, 2))
        item = make_item(self.kl, "CH-0012", size="10", unit="umol",
                         quantity=0)
        bottle = make_vessel(self.kl, article="CH-0012", source="bought",
                             supplier="Sigma", unit="mg", amount="50")
        filling = fill(self.kl, item, count=1, vessel=bottle,
                       date=date(2026, 11, 2))
        self.assertEqual(fresh(bottle).opened_on, date(2026, 11, 2))
        reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(bottle).opened_on, date(2026, 11, 2))


class WithdrawalReversalTests(WithdrawalCase):

    def setUp(self) -> None:
        super().setUp()
        self.taken = withdraw(self.kl, self.vessel, task_step=self.second,
                              amount=Decimal("0.5"))

    def test_a_reversal_returns_what_was_taken_whatever_came_after(
            self) -> None:
        withdraw(self.kl, self.vessel, task_step=self.second,
                 amount=Decimal("1"))
        returned = reverse_withdrawal(self.kl, self.taken)
        self.assertEqual(fresh(self.vessel).amount, Decimal("1000"))
        self.assertEqual((returned.amount, returned.amount_after,
                          returned.reverses),
                         (Decimal("500"), Decimal("1000"), self.taken))

    def test_a_withdrawal_is_reversed_once(self) -> None:
        reverse_withdrawal(self.kl, self.taken)
        with self.refusing():
            reverse_withdrawal(self.kl, self.taken)
        self.assertEqual(VesselMovement.objects.filter(
            reverses=self.taken).count(), 1)

    def test_only_a_withdrawal_is_reversed(self) -> None:
        opening = self.vessel.movements.order_by("id").first()
        reversal = reverse_withdrawal(self.kl, self.taken)
        for movement in (opening, reversal):
            with self.subTest(kind=movement.kind), self.refusing():
                reverse_withdrawal(self.kl, movement)

    def test_a_reversed_withdrawal_stays_in_the_ledger(self) -> None:
        reverse_withdrawal(self.kl, self.taken)
        self.assertEqual(
            [m.kind for m in self.vessel.movements.order_by("-pk")],
            ["reversal", "withdrawal", "opening"])


class TransferCase(InventoryCase):
    """A made batch of ``cinnamic-acid`` (molar mass 148.16) with a flask
    of ``1000`` mg."""

    def setUp(self) -> None:
        super().setUp()
        self.batch = make_batch(self.kl, "CH-0012", number="KL0412")
        self.flask = make_vessel(self.kl, self.batch, unit="mg",
                                 amount="1000", flask=True)

    def stored(self, unit: str = "mg", amount: str = "10",
               location: str = "Regal") -> Vessel:
        return make_vessel(self.kl, self.batch, unit=unit, amount=amount,
                           location=location)


class TransferTests(TransferCase):
    """Requirement: Vessels (`transfer_out` and `transfer_in`)."""

    def test_a_transfer_into_a_new_vessel(self) -> None:
        """Scenario: Transfer into a new vessel."""
        flask = make_vessel(self.kl, make_batch(self.kl, "CH-0012",
                                                number="KL9"),
                            unit="g", amount="2", flask=True)
        out, into = transfer(self.kl, flask, amount=Decimal("1.5"),
                             location="Kühlschrank 2")
        self.assertEqual(fresh(flask).amount, Decimal("500"))
        target = into.vessel
        self.assertEqual(
            (target.batch, target.unit, target.amount, target.location,
             target.flask), (flask.batch, "g", Decimal("1500"),
                             "Kühlschrank 2", False))
        self.assertEqual(list(target.movements.all()), [into])
        self.assertEqual(into.kind, "transfer_in")
        self.assertEqual(into.transfer, out)
        self.assertEqual(out.kind, "transfer_out")
        self.assertEqual(out.vessel, flask)

    def test_the_movements_hold_their_amounts_and_their_vessels_amounts(
            self) -> None:
        target = self.stored(amount="100")
        out, into = transfer(self.kl, self.flask, amount=Decimal("250"),
                             target=target, note="umgefüllt")
        self.assertEqual((out.amount, out.amount_after),
                         (Decimal("250"), Decimal("750")))
        self.assertEqual((into.amount, into.amount_after),
                         (Decimal("250"), Decimal("350")))
        for movement in (out, into):
            with self.subTest(kind=movement.kind):
                self.assertEqual((movement.user, movement.date),
                                 (self.kl, TODAY))
        self.assertEqual(out.note, "umgefüllt")
        self.assertEqual(fresh(self.flask).amount, Decimal("750"))
        self.assertEqual(fresh(target).amount, Decimal("350"))

    def test_the_two_movements_name_each_other_one_way(self) -> None:
        out, into = transfer(self.kl, self.flask, amount=Decimal("1"),
                             target=self.stored())
        self.assertEqual(fresh(into).transfer, out)
        self.assertIsNone(fresh(out).transfer)
        self.assertEqual(fresh(out).transferred, into)

    def test_the_date_may_be_given(self) -> None:
        out, into = transfer(self.kl, self.flask, amount=Decimal("1"),
                             target=self.stored(), date=date(2026, 11, 1))
        self.assertEqual((out.date, into.date),
                         (date(2026, 11, 1), date(2026, 11, 1)))
        target = self.stored()
        with self.refusing("date"):
            transfer(self.kl, self.flask, amount=Decimal("1"),
                     target=target, date=date(2026, 11, 5))

    def test_transfer_across_units(self) -> None:
        """Scenario: Transfer across units."""
        target = self.stored(unit="umol", amount="100")
        out, into = transfer(self.kl, self.flask, amount=Decimal("148.16"),
                             target=target)
        self.assertEqual(fresh(self.flask).amount, Decimal("851.84"))
        self.assertEqual(fresh(target).amount, Decimal("1100"))
        self.assertEqual(out.amount, Decimal("148.16"))
        self.assertEqual(into.amount, Decimal("1000"))

    def test_the_amount_is_in_the_unit_of_the_source(self) -> None:
        flask = make_vessel(self.kl, make_batch(self.kl, "CH-0012",
                                                number="KL8"),
                            unit="g", amount="2", flask=True)
        target = make_vessel(self.kl, flask.batch, unit="mg", amount="1",
                             location="Regal")
        out, into = transfer(self.kl, flask, amount=Decimal("0.5"),
                             target=target)
        self.assertEqual((out.amount, into.amount),
                         (Decimal("500"), Decimal("500")))
        self.assertEqual(fresh(flask).amount, Decimal("1500"))

    def test_the_converted_amount_is_rounded_half_up_to_six_places(
            self) -> None:
        target = self.stored(unit="umol", amount="1")
        out, into = transfer(self.kl, self.flask, amount=Decimal("1"),
                             target=target)
        self.assertEqual(out.amount, Decimal("1"))
        self.assertEqual(into.amount, Decimal("6.749460"))
        self.assertEqual(fresh(target).amount, Decimal("7.749460"))

    def test_half_is_rounded_up(self) -> None:
        heavy = make_batch(self.kl, substance=substance_for(
            "heavy-1", mw="100"), number="HV1")
        source = make_vessel(self.kl, heavy, unit="umol", amount="1",
                             location="A")
        target = make_vessel(self.kl, heavy, unit="mg", amount="1",
                             location="B")
        out, into = transfer(self.kl, source, amount=Decimal("0.000005"),
                             target=target)
        self.assertEqual(out.amount, Decimal("0.000005"))
        self.assertEqual(into.amount, Decimal("0.000001"))

    def test_a_new_vessel_takes_the_unit_of_the_source(self) -> None:
        flask = make_vessel(self.kl, make_batch(self.kl, "CH-0012",
                                                number="KL7"),
                            unit="mmol", amount="2", flask=True)
        _out, into = transfer(self.kl, flask, amount=Decimal("0.5"),
                              location="Regal")
        self.assertEqual((into.vessel.unit, into.vessel.amount),
                         ("mmol", Decimal("500")))

    def test_the_whole_amount_may_be_transferred(self) -> None:
        out, _into = transfer(self.kl, self.flask, amount=Decimal("1000"),
                              location="Regal")
        self.assertEqual(fresh(self.flask).amount, 0)
        self.assertEqual(out.amount_after, Decimal("0"))

    def test_a_stored_vessel_passes_amounts_to_another(self) -> None:
        source = self.stored(amount="300", location="A")
        target = self.stored(amount="5", location="B")
        transfer(self.kl, source, amount=Decimal("100"), target=target)
        self.assertEqual((fresh(source).amount, fresh(target).amount),
                         (Decimal("200"), Decimal("105")))

    def test_an_amount_above_the_source_is_refused(self) -> None:
        with self.refusing("amount"):
            transfer(self.kl, self.flask, amount=Decimal("1000.000001"),
                     location="Regal")

    def test_an_amount_of_zero_or_less_is_refused(self) -> None:
        for amount in ("0", "-1"):
            with self.subTest(amount=amount), self.refusing("amount"):
                transfer(self.kl, self.flask, amount=Decimal(amount),
                         location="Regal")

    def test_a_used_up_source_is_refused(self) -> None:
        empty = self.stored(amount="0")
        with self.refusing():
            transfer(self.kl, empty, amount=Decimal("1"), location="Regal")

    def test_an_amount_that_converts_to_zero_is_refused_whole(self) -> None:
        heavy = make_batch(self.kl, substance=substance_for(
            "heavy-2", mw="16000"), number="HV2")
        source = make_vessel(self.kl, heavy, unit="mg", amount="1",
                             location="A")
        target = make_vessel(self.kl, heavy, unit="umol", amount="1",
                             location="B")
        with self.refusing():
            transfer(self.kl, source, amount=Decimal("0.000001"),
                     target=target)
        self.assertEqual((fresh(source).amount, fresh(target).amount),
                         (Decimal("1"), Decimal("1")))

    def test_without_a_molar_mass_the_kinds_do_not_convert(self) -> None:
        """Scenario: Transfer without a molar mass."""
        batch = make_batch(self.kl, "X-9", number="XN1")
        source = make_vessel(self.kl, batch, unit="mg", amount="50",
                             flask=True)
        target = make_vessel(self.kl, batch, unit="umol", amount="5",
                             location="Regal")
        with self.refusing("target"):
            transfer(self.kl, source, amount=Decimal("10"), target=target)
        self.assertEqual((fresh(source).amount, fresh(target).amount),
                         (Decimal("50"), Decimal("5")))

    def test_units_of_one_kind_need_no_molar_mass(self) -> None:
        batch = make_batch(self.kl, "X-9", number="XN2")
        source = make_vessel(self.kl, batch, unit="g", amount="1",
                             flask=True)
        target = make_vessel(self.kl, batch, unit="mg", amount="5",
                             location="Regal")
        transfer(self.kl, source, amount=Decimal("0.25"), target=target)
        self.assertEqual((fresh(source).amount, fresh(target).amount),
                         (Decimal("750"), Decimal("255")))

    def test_a_target_of_another_batch_is_refused(self) -> None:
        other = make_vessel(self.kl, make_batch(self.kl, "CH-0012",
                                                number="KL5"),
                            location="Regal")
        with self.refusing("target"):
            transfer(self.kl, self.flask, amount=Decimal("1"), target=other)

    def test_a_flask_takes_no_transfer(self) -> None:
        """Requirement: Vessels (the target is a stored vessel)."""
        source = self.stored(amount="10")
        with self.refusing("target"):
            transfer(self.kl, source, amount=Decimal("1"),
                     target=self.flask)
        self.assertEqual(fresh(self.flask).amount, Decimal("1000"))

    def test_a_refused_transfer_changes_nothing(self) -> None:
        target = self.stored()
        before = (fresh(self.flask).amount, fresh(target).amount,
                  VesselMovement.objects.count(), Vessel.objects.count())
        with self.refusing("amount"):
            transfer(self.kl, self.flask, amount=Decimal("5000"),
                     target=target)
        self.assertEqual(
            (fresh(self.flask).amount, fresh(target).amount,
             VesselMovement.objects.count(), Vessel.objects.count()),
            before)

    def test_the_amount_of_a_stale_source_is_not_trusted(self) -> None:
        target = self.stored()
        transfer(self.kl, fresh(self.flask), amount=Decimal("900"),
                 target=target)
        self.assertEqual(self.flask.amount, Decimal("1000"))
        with self.refusing("amount"):
            transfer(self.kl, self.flask, amount=Decimal("200"),
                     target=target)
        self.assertEqual(fresh(self.flask).amount, Decimal("100"))

    def test_a_new_vessel_has_a_history(self) -> None:
        _out, into = transfer(self.kl, self.flask, amount=Decimal("1"),
                              location="Regal")
        self.assertEqual(into.vessel.history.get().history_user, self.kl)

    def test_transfers_are_not_reversed(self) -> None:
        out, _into = transfer(self.kl, self.flask, amount=Decimal("1"),
                              location="Regal")
        with self.refusing():
            reverse_withdrawal(self.kl, out)

    def test_a_transfer_out_of_a_sealed_bottle_sets_opened_on(self) -> None:
        """Requirement: Vessels ("The first filling, withdrawal or
        transfer out of a sealed vessel sets its `opened_on` to that
        movement's date in the transaction that books it")."""
        bought = make_batch(self.kl, "CH-0012", source="bought",
                            supplier="Sigma")
        bottle = make_vessel(self.kl, bought, unit="g", amount="2",
                             location="Schrank")
        self.assertIsNone(bottle.opened_on)
        transfer(self.kl, bottle, amount=Decimal("0.5"),
                 location="Regal", date=date(2026, 11, 1))
        self.assertEqual(fresh(bottle).opened_on, date(2026, 11, 1))
        transfer(self.kl, fresh(bottle), amount=Decimal("0.5"),
                 location="Regal 2", date=date(2026, 11, 3))
        self.assertEqual(fresh(bottle).opened_on, date(2026, 11, 1))

    def test_a_vessel_made_by_a_transfer_has_the_transfers_date(
            self) -> None:
        """Requirement: Vessels ("A vessel of a bought batch opens
        sealed, unless a transfer makes it: a vessel a transfer makes is
        opened on the transfer's date.")."""
        bought = make_batch(self.kl, "CH-0012", source="bought",
                            supplier="Sigma")
        bottle = make_vessel(self.kl, bought, unit="g", amount="2",
                             location="Schrank")
        _out, into = transfer(self.kl, bottle, amount=Decimal("0.5"),
                              location="Regal", date=date(2026, 11, 2))
        self.assertEqual(fresh(into.vessel).opened_on, date(2026, 11, 2))
        _out2, made_into = transfer(
            self.kl, self.flask, amount=Decimal("100"), location="Regal",
            date=date(2026, 11, 2))
        self.assertIsNone(fresh(made_into.vessel).opened_on)


class FillingFromVesselTests(InventoryCase):
    """Requirement: Filling from bulk (the booking)."""

    def test_filling_with_conversion(self) -> None:
        """Scenario: Filling with conversion (the booking)."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=2)
        vessel = self.vessel("CH-0012", "mg", "50")
        movement = fill(self.kl, item, count=5, vessel=vessel)
        self.assertEqual(fresh(item).quantity, 7)
        self.assertEqual(fresh(vessel).amount, Decimal("42.592"))
        taken = newest(vessel)
        self.assertEqual(taken.kind, VesselMovement.Kind.FILLING)
        self.assertEqual((taken.amount, taken.amount_after),
                         (Decimal("7.408"), Decimal("42.592")))
        self.assertEqual(taken.user, self.kl)
        movement = Movement.objects.get(pk=movement.pk)
        self.assertEqual(movement.vessel_movement, taken)
        self.assertEqual((movement.kind, movement.count), ("filling", 5))
        self.assertEqual(taken.item_movement, movement)

    def test_a_vessel_is_required(self) -> None:
        """Scenario: No filling without a vessel (the booking)."""
        item = self.item("CH-0012", quantity=0)
        with self.refusing("vessel"):
            fill(self.kl, item, count=3, vessel=None)
        self.assertEqual(fresh(item).quantity, 0)

    def test_the_amount_may_be_named(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50")
        movement = fill(self.kl, item, count=5, vessel=vessel,
                        amount=Decimal("7.4"))
        self.assertEqual(fresh(vessel).amount, Decimal("42.6"))
        self.assertEqual(movement.vessel_movement.amount, Decimal("7.4"))

    def test_small_filling_from_a_vessel_in_grams(self) -> None:
        """Scenario: Small filling from a vessel in grams."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        vessel = self.vessel("CH-0012", "g", "1")
        fill(self.kl, item, count=1, vessel=vessel)
        self.assertEqual(fresh(vessel).amount, Decimal("998.5184"))
        self.assertEqual(fresh(vessel).shown_amount, Decimal("0.999"))

    def test_a_named_amount_is_in_the_unit_of_the_vessel(self) -> None:
        item = self.item("X-1", size="10", unit="mg", quantity=0)
        vessel = self.vessel("X-1", "g", "1")
        fill(self.kl, item, count=1, vessel=vessel, amount=Decimal("0.05"))
        self.assertEqual(fresh(vessel).amount, Decimal("950"))

    def test_units_of_one_kind_need_no_molar_mass(self) -> None:
        item = self.item("X-1", size="10", unit="mg", quantity=0)
        vessel = self.vessel("X-1", "g", "1")
        fill(self.kl, item, count=5, vessel=vessel)
        self.assertEqual(fresh(vessel).amount, Decimal("950"))
        item = self.item("X-2", size="2", unit="mmol", quantity=0)
        vessel = self.vessel("X-2", "umol", "10000")
        fill(self.kl, item, count=3, vessel=vessel)
        self.assertEqual(fresh(vessel).amount, Decimal("4000"))

    def test_the_count_is_multiplied_by_the_size(self) -> None:
        item = self.item("CH-0012", size="2.5", unit="umol", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50")
        fill(self.kl, item, count=3, vessel=vessel)
        self.assertEqual(fresh(vessel).amount, Decimal("48.8888"))

    def test_the_proposal_rounds_half_up_to_six_places(self) -> None:
        item = self.item("T-1", size="0.001", unit="umol", quantity=0,
                         mw="2.5")
        vessel = self.vessel("T-1", "mg", "1")
        movement = fill(self.kl, item, count=1, vessel=vessel)
        self.assertEqual(movement.vessel_movement.amount,
                         Decimal("0.000003"))
        self.assertEqual(fresh(vessel).amount, Decimal("0.999997"))

    def test_without_a_molar_mass_the_amount_is_required(self) -> None:
        item = self.item("X-1", size="10", unit="umol", quantity=0)
        vessel = self.vessel("X-1", "mg", "50")
        with self.refusing("amount"):
            fill(self.kl, item, count=2, vessel=vessel)
        fill(self.kl, item, count=2, vessel=vessel, amount=Decimal("3"))
        self.assertEqual(fresh(vessel).amount, Decimal("47"))
        self.assertEqual(fresh(item).quantity, 2)

    def test_an_amount_above_the_vessel_refuses_both(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "5")
        with self.refusing():
            fill(self.kl, item, count=5, vessel=vessel)
        with self.refusing():
            fill(self.kl, item, count=1, vessel=vessel,
                 amount=Decimal("5.000001"))

    def test_the_whole_vessel_may_be_taken(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "5")
        fill(self.kl, item, count=1, vessel=vessel, amount=Decimal("5"))
        self.assertEqual(fresh(vessel).amount, 0)
        self.assertEqual(fresh(item).quantity, 1)

    def test_an_amount_that_rounds_to_zero_refuses_both(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "5")
        for amount in ("0", "0.0000004", "-1"):
            with self.subTest(amount=amount), self.refusing():
                fill(self.kl, item, count=1, vessel=vessel,
                     amount=Decimal(amount))

    def test_a_proposal_that_rounds_to_zero_refuses_both(self) -> None:
        item = self.item("T-2", size="0.001", unit="umol", quantity=0,
                         mw="0.001")
        vessel = self.vessel("T-2", "mg", "5")
        with self.refusing():
            fill(self.kl, item, count=1, vessel=vessel)

    def test_a_used_up_vessel_is_refused(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "0")
        with self.refusing():
            fill(self.kl, item, count=1, vessel=vessel,
                 amount=Decimal("1"))

    def test_a_vessel_of_another_substance_is_refused(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0013", "mg", "50")
        with self.refusing():
            fill(self.kl, item, count=1, vessel=vessel,
                 amount=Decimal("1"))

    def test_the_amount_of_a_stale_vessel_is_not_trusted(self) -> None:
        item = self.item("CH-0012", quantity=0)
        stale = self.vessel("CH-0012", "mg", "50")
        fill(self.kl, item, count=1, vessel=fresh(stale),
             amount=Decimal("45"))
        self.assertEqual(stale.amount, Decimal("50"))
        with self.refusing():
            fill(self.kl, item, count=1, vessel=stale,
                 amount=Decimal("20"))
        self.assertEqual(fresh(stale).amount, Decimal("5"))

    def test_a_flask_is_filled_from_like_any_vessel(self) -> None:
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        flask = self.vessel("CH-0012", "g", "2", flask=True)
        fill(self.kl, item, count=5, vessel=flask)
        self.assertEqual(fresh(flask).amount, Decimal("1992.592"))

    def test_the_item_movement_names_the_vessel_movement(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50")
        fill(self.kl, item, count=5, vessel=vessel)
        self.assertEqual(newest_movement(item).vessel_movement.vessel,
                         vessel)

    def test_reversing_a_filling_returns_the_amount(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50")
        filling = fill(self.kl, item, count=5, vessel=vessel)
        reversal = reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(vessel).amount, Decimal("50"))
        returned = newest(vessel)
        self.assertEqual(returned.kind, VesselMovement.Kind.REVERSAL)
        self.assertEqual((returned.amount, returned.amount_after),
                         (Decimal("7.408"), Decimal("50")))
        self.assertEqual(returned.user, self.kl)
        self.assertEqual(fresh(item).quantity, 0)
        self.assertEqual(fresh(reversal).vessel_movement, returned)

    def test_a_refused_reversal_leaves_the_vessel(self) -> None:
        item = self.item("CH-0012", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50")
        filling = fill(self.kl, item, count=5, vessel=vessel)
        self.deliver(item, 4)
        with self.refusing():
            reverse(self.kl, filling, note="doppelt")
        self.assertEqual(fresh(vessel).amount, Decimal("42.592"))

    def test_a_filling_from_a_sealed_bottle_sets_opened_on(self) -> None:
        """Requirement: Vessels ("The first filling, withdrawal or
        transfer out of a sealed vessel sets its `opened_on` to that
        movement's date in the transaction that books it")."""
        item = self.item("CH-0012", size="10", unit="umol", quantity=0)
        vessel = self.vessel("CH-0012", "mg", "50", source="bought",
                             supplier="Sigma")
        self.assertIsNone(vessel.opened_on)
        fill(self.kl, item, count=1, vessel=vessel, date=date(2026, 11, 1))
        self.assertEqual(fresh(vessel).opened_on, date(2026, 11, 1))
        fill(self.kl, item, count=1, vessel=fresh(vessel),
             date=date(2026, 11, 3))
        self.assertEqual(fresh(vessel).opened_on, date(2026, 11, 1))
        made = self.vessel("CH-0012", "mg", "50")
        fill(self.kl, item, count=1, vessel=made, date=date(2026, 11, 1))
        self.assertIsNone(fresh(made).opened_on)


class AdminDeletionTests(InventoryCase):
    """Requirement: Batches (a batch a step made is deleted by no one
    outside the demo reset), through the admin."""

    def setUp(self) -> None:
        super().setUp()
        from . import make_user
        self.boss = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        self.client.force_login(self.boss)

    def delete(self, batch: Batch):
        return self.client.post(
            f"/lab/admin/inventory/batch/{batch.pk}/delete/",
            {"post": "yes"})

    def test_a_batch_made_by_a_step_is_not_deleted(self) -> None:
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        batch = make_batch(self.kl, "CH-0012", task_step=task.steps.get())
        self.delete(batch)
        self.assertTrue(Batch.objects.filter(pk=batch.pk).exists())

    def test_a_batch_without_a_step_and_vessels_is_deleted(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        self.delete(batch)
        self.assertFalse(Batch.objects.filter(pk=batch.pk).exists())

    def test_a_batch_with_a_vessel_is_not_deleted(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012")
        self.delete(vessel.batch)
        self.assertTrue(Batch.objects.filter(pk=vessel.batch_id).exists())
