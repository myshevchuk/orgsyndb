"""Tests of the batches and their recording (end-product-inventory:
Batches, Inventory forms)."""

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from inventory.bookings import record_batch
from inventory.models import Batch, Vessel, VesselMovement
from tasks.models import TaskStep

from . import (make_batch, make_item, make_task, make_vessel, past,
               substance_for)
from .inventory_support import TODAY, InventoryCase, fresh
from .journal_support import entry_of, make_notebook
from .task_support import StepCase, steps_of


class BatchModelTests(InventoryCase):
    """Requirement: Batches (the fields)."""

    def test_a_made_batch_keeps_its_fields(self) -> None:
        make_notebook("AE-1", self.kl)
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        step = task.steps.get()
        entry = entry_of("AE-1/9")
        made = make_batch(
            self.kl, "CH-0012", number="KL0412FA", date=date(2026, 10, 30),
            note="Rest", task_step=step, journal_entry=entry,
            yield_amount="2", yield_unit="g")
        batch = Batch.objects.get(pk=made.pk)
        self.assertEqual(
            (batch.substance.key, batch.source, batch.number,
             batch.task_step, batch.journal_entry, batch.date, batch.note,
             batch.yield_unit),
            ("cinnamic-acid", "made", "KL0412FA", step, entry,
             date(2026, 10, 30), "Rest", "g"))
        self.assertEqual(batch.yield_amount, Decimal("2000"))
        self.assertEqual(
            (batch.supplier, batch.supplier_article_number,
             batch.supplier_batch), ("", "", ""))

    def test_a_bought_batch_keeps_its_fields(self) -> None:
        made = make_batch(
            self.kl, "CH-0012", source="bought", supplier="Sigma",
            supplier_article_number="C80857", supplier_batch="MKCK1234",
            date=date(2026, 11, 2))
        batch = Batch.objects.get(pk=made.pk)
        self.assertEqual(
            (batch.source, batch.supplier, batch.supplier_article_number,
             batch.supplier_batch, batch.date),
            ("bought", "Sigma", "C80857", "MKCK1234", date(2026, 11, 2)))
        self.assertEqual((batch.number, batch.number_key), ("", ""))
        self.assertIsNone(batch.journal_entry)
        self.assertIsNone(batch.task_step)
        self.assertIsNone(batch.yield_amount)
        self.assertEqual(batch.yield_unit, "")

    def test_the_two_sources(self) -> None:
        self.assertEqual(
            {value for value, _ in Batch._meta.get_field("source").choices},
            {"made", "bought"})

    def test_the_lengths_of_the_texts(self) -> None:
        lengths = {"number": 30, "number_key": 100, "supplier": 100,
                   "supplier_article_number": 50, "supplier_batch": 50}
        for name, length in lengths.items():
            with self.subTest(field=name):
                self.assertEqual(Batch._meta.get_field(name).max_length,
                                 length)

    def test_the_key_is_not_editable(self) -> None:
        self.assertFalse(Batch._meta.get_field("number_key").editable)

    def test_the_yield_is_kept_in_a_base_unit_with_six_places(self) -> None:
        field = Batch._meta.get_field("yield_amount")
        self.assertEqual((field.max_digits, field.decimal_places, field.null),
                         (18, 6, True))
        self.assertEqual(
            {value for value, _ in
             Batch._meta.get_field("yield_unit").choices},
            {"mg", "g", "umol", "mmol"})

    def test_the_references_of_a_batch(self) -> None:
        for name, related in (("substance", "batches"),
                              ("journal_entry", "batches"),
                              ("task_step", "batches")):
            with self.subTest(field=name):
                field = Batch._meta.get_field(name)
                self.assertEqual(field.remote_field.related_name, related)
                self.assertEqual(field.remote_field.on_delete.__name__,
                                 "PROTECT")
        self.assertTrue(Batch._meta.get_field("journal_entry").null)
        self.assertTrue(Batch._meta.get_field("task_step").null)
        self.assertTrue(Batch._meta.get_field("date").null)

    def test_a_batch_keeps_a_history(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        self.assertEqual(batch.history.get().history_user, self.kl)

    def test_a_batch_of_any_substance(self) -> None:
        """Requirement: Batches (a batch may be of any substance,
        intermediates and reagents among them)."""
        from inventory.models import Article
        batch = make_batch(self.kl, "acetophenone")
        self.assertEqual(batch.substance.key, "acetophenone")
        self.assertFalse(Article.objects.exists())

    def test_made_and_bought_batches_of_one_substance_side_by_side(
            self) -> None:
        made = make_batch(self.kl, "CH-0012", number="KL1")
        bought = make_batch(self.kl, "CH-0012", source="bought",
                            supplier="Sigma")
        self.assertEqual(made.substance, bought.substance)
        self.assertEqual(
            sorted(made.substance.batches.values_list("source", flat=True)),
            ["bought", "made"])

    def test_a_journal_entry_names_several_batches(self) -> None:
        make_notebook("AE-1", self.kl)
        entry = entry_of("AE-1/9")
        make_batch(self.kl, "CH-0012", number="AE1009FA",
                   journal_entry=entry)
        make_batch(self.kl, "CH-0012", number="AE1009FB",
                   journal_entry=entry)
        self.assertEqual(
            sorted(entry.batches.values_list("number", flat=True)),
            ["AE1009FA", "AE1009FB"])


class BatchDisplayTests(InventoryCase):
    """Requirement: Batches (a batch shows as its number, a bought batch
    as its supplier's batch number, and either, when it has none, as
    `#<id>`)."""

    def test_a_made_batch_shows_as_its_number(self) -> None:
        self.assertEqual(str(make_batch(self.kl, number="KL0412FA")),
                         "KL0412FA")

    def test_a_bought_batch_shows_as_its_suppliers_batch(self) -> None:
        batch = make_batch(self.kl, source="bought", supplier="Sigma",
                           supplier_batch="MKCK1234")
        self.assertEqual(str(batch), "MKCK1234")

    def test_a_bought_batch_without_one_shows_as_its_id(self) -> None:
        batch = make_batch(self.kl, source="bought", supplier="Sigma")
        self.assertEqual(str(batch), f"#{batch.pk}")

    def test_the_yield_shows_in_its_unit_to_three_places_half_up(
            self) -> None:
        cases = [("2", "g", "2"), ("1500", "mg", "1500"),
                 ("0.0005", "g", "0.001"), ("0.0004", "g", "0"),
                 ("2.5", "mmol", "2.5"), ("1.2345", "mg", "1.235")]
        for amount, unit, want in cases:
            with self.subTest(amount=amount, unit=unit):
                batch = make_batch(self.kl, yield_amount=amount,
                                   yield_unit=unit)
                self.assertEqual(batch.shown_yield, Decimal(want))


class BatchNumberTests(InventoryCase):
    """Requirement: Batches (`number`, unique among made batches
    regardless of case and of their substance); the design's
    `number_key`."""

    def test_the_key_of_a_made_batch_is_its_casefolded_number(self) -> None:
        for number, key in (("KL0412FA", "kl0412fa"), ("Ab-1", "ab-1"),
                            ("Straße", "strasse")):
            with self.subTest(number=number):
                self.assertEqual(
                    fresh(make_batch(self.kl, number=number)).number_key,
                    key)

    def test_the_key_of_a_bought_batch_is_empty(self) -> None:
        batch = make_batch(self.kl, source="bought", supplier_batch="X1")
        self.assertEqual(fresh(batch).number_key, "")

    def test_a_save_sets_the_key_whatever_the_caller_wrote(self) -> None:
        batch = Batch(substance=substance_for("CH-0012"), source="made",
                      number="KL7", number_key="wrong")
        batch._history_user = self.kl
        batch.save()
        self.assertEqual(fresh(batch).number_key, "kl7")

    def test_a_rename_saves_the_key_with_the_number(self) -> None:
        batch = make_batch(self.kl, number="KL1")
        batch.number = "KL2"
        batch.save()
        self.assertEqual(fresh(batch).number_key, "kl2")

    def test_a_rename_frees_the_old_number_and_claims_the_new_key(
            self) -> None:
        batch = make_batch(self.kl, number="KL1")
        batch.number = "KL2"
        batch.save()
        make_batch(self.kl, number="kl1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_batch(self.kl, number="Kl2")

    def test_numbers_are_unique_regardless_of_case_and_substance(
            self) -> None:
        make_batch(self.kl, "CH-0012", number="KL0412FA")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_batch(self.kl, "acetophenone", number="kl0412fa")
        self.assertEqual(Batch.objects.count(), 1)

    def test_the_key_folds_the_sharp_s(self) -> None:
        """`Straße` and `STRASSE` collide, on SQLite as on
        PostgreSQL."""
        make_batch(self.kl, number="Straße")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_batch(self.kl, number="STRASSE")

    def test_the_booking_refuses_the_sharp_s_collision(self) -> None:
        record_batch(self.kl, substance=substance_for("CH-0012"),
                     number="Straße")
        with self.refusing("number"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         number="STRASSE")

    def test_bought_batches_share_no_key(self) -> None:
        make_batch(self.kl, source="bought", supplier_batch="X1")
        make_batch(self.kl, source="bought", supplier_batch="X1")
        make_batch(self.kl, source="bought")
        self.assertEqual(Batch.objects.filter(source="bought").count(), 3)

    def test_a_made_number_does_not_clash_with_a_bought_batch(self) -> None:
        make_batch(self.kl, source="bought", supplier_batch="KL1")
        make_batch(self.kl, number="KL1")
        self.assertEqual(Batch.objects.count(), 2)


class DeletionTests(StepCase):
    """Requirement: Batches (a batch that has vessels, or that a task
    step made, cannot be deleted)."""

    def test_a_batch_with_a_vessel_cannot_be_deleted(self) -> None:
        vessel = make_vessel(self.kl, article="CH-0012")
        with self.assertRaises(ProtectedError):
            vessel.batch.delete()
        self.assertTrue(Batch.objects.filter(pk=vessel.batch_id).exists())

    def test_a_batch_without_vessels_can_be_deleted(self) -> None:
        batch = make_batch(self.kl, "CH-0012")
        batch.delete()
        self.assertFalse(Batch.objects.exists())

    def test_a_step_that_made_a_batch_cannot_be_deleted(self) -> None:
        task = self.follow()
        first = steps_of(task)[0]
        make_batch(self.kl, substance=first.products()[0], task_step=first)
        with self.assertRaises(ProtectedError):
            first.delete()
        self.assertTrue(TaskStep.objects.filter(pk=first.pk).exists())

    def test_a_journal_entry_a_batch_names_cannot_be_deleted(self) -> None:
        entry = entry_of("AE-1/9")
        make_batch(self.kl, "CH-0012", journal_entry=entry)
        with self.assertRaises(ProtectedError):
            entry.delete()

    def test_a_substance_with_a_batch_cannot_be_deleted(self) -> None:
        batch = make_batch(self.kl, "acetophenone")
        with self.assertRaises(ProtectedError):
            batch.substance.delete()


class RecordWithoutStepTests(InventoryCase):
    """The booking ``record_batch`` without a task step (Batches,
    Inventory forms)."""

    def test_made_and_bought_batches(self) -> None:
        """Scenario: Made and bought batches."""
        cinnamic = substance_for("CH-0012")
        made = record_batch(self.kl, substance=cinnamic,
                            number="KL0412FA")
        bought = record_batch(
            self.kl, substance=cinnamic, source="bought", supplier="Sigma",
            supplier_article_number="C80857", supplier_batch="MKCK1234")
        self.assertEqual((str(made), made.source), ("KL0412FA", "made"))
        self.assertEqual((str(bought), bought.source, bought.supplier,
                          bought.supplier_article_number),
                         ("MKCK1234", "bought", "Sigma", "C80857"))
        self.assertEqual(Batch.objects.count(), 2)
        self.assertEqual(fresh(made).number_key, "kl0412fa")

    def test_the_batch_keeps_its_fields_and_a_history(self) -> None:
        batch = record_batch(
            self.kl, substance=substance_for("CH-0012"), number="KL1",
            date=date(2026, 10, 30), note="Rest")
        stored = fresh(batch)
        self.assertEqual((stored.date, stored.note, stored.task_step),
                         (date(2026, 10, 30), "Rest", None))
        self.assertEqual(stored.history.get().history_user, self.kl)

    def test_a_journal_entry_may_be_named(self) -> None:
        make_notebook("AE-1", self.kl)
        entry = entry_of("AE-1/9")
        batch = record_batch(self.kl, substance=substance_for("CH-0012"),
                             number="KL1", journal_entry=entry)
        self.assertEqual(fresh(batch).journal_entry, entry)

    def test_the_amount_is_optional_and_opens_no_vessel_without_one(
            self) -> None:
        batch = record_batch(self.kl, substance=substance_for("CH-0012"),
                             number="KL1")
        self.assertFalse(batch.vessels.exists())
        self.assertIsNone(fresh(batch).yield_amount)

    def test_an_amount_opens_one_stored_vessel(self) -> None:
        batch = record_batch(
            self.kl, substance=substance_for("CH-0012"), number="KL1",
            amount=Decimal("2"), unit="g", location="Kühlschrank 2")
        vessel = batch.vessels.get()
        self.assertEqual(
            (vessel.flask, vessel.unit, vessel.amount, vessel.location),
            (False, "g", Decimal("2000"), "Kühlschrank 2"))
        opening = vessel.movements.get()
        self.assertEqual(
            (opening.kind, opening.amount, opening.amount_after,
             opening.user, opening.date),
            ("opening", Decimal("2000"), Decimal("2000"), self.kl, TODAY))
        self.assertIsNone(fresh(batch).yield_amount)

    def test_a_bought_batch_with_an_amount_opens_a_vessel_too(self) -> None:
        batch = record_batch(
            self.kl, substance=substance_for("CH-0012"), source="bought",
            supplier="Sigma", amount=Decimal("5"), unit="mmol")
        vessel = batch.vessels.get()
        self.assertEqual((vessel.unit, vessel.amount, vessel.flask),
                         ("mmol", Decimal("5000"), False))

    def test_an_amount_without_its_unit_is_refused(self) -> None:
        with self.refusing():
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         number="KL1", amount=Decimal("2"), unit="")

    def test_an_unknown_unit_is_refused(self) -> None:
        with self.refusing("unit"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         number="KL1", amount=Decimal("2"), unit="kg")

    def test_a_made_batch_needs_a_number(self) -> None:
        with self.refusing("number"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         number="")

    def test_a_bought_batch_with_a_number_is_refused(self) -> None:
        with self.refusing("number"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         source="bought", number="KL1", supplier="Sigma")

    def test_a_number_of_more_than_30_characters_is_refused(self) -> None:
        with self.refusing("number"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         number="n" * 31)
        record_batch(self.kl, substance=substance_for("CH-0012"),
                     number="n" * 30)

    def test_the_supplier_fields_have_their_lengths(self) -> None:
        for field, length in (("supplier", 100),
                              ("supplier_article_number", 50),
                              ("supplier_batch", 50)):
            with self.subTest(field=field):
                with self.refusing(field):
                    record_batch(self.kl, substance=substance_for("CH-0012"),
                                 source="bought", **{field: "x" * (
                                     length + 1)})
                record_batch(self.kl, substance=substance_for("CH-0012"),
                             source="bought", **{field: "x" * length})

    def test_an_unknown_source_is_refused(self) -> None:
        with self.refusing("source"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         source="stolen", number="KL1")

    def test_a_date_in_the_future_is_refused(self) -> None:
        with self.refusing("date"):
            record_batch(self.kl, substance=substance_for("CH-0012"),
                         number="KL1", date=date(2026, 11, 5))
        record_batch(self.kl, substance=substance_for("CH-0012"),
                     number="KL1", date=TODAY)

    def test_numbers_unique_regardless_of_case(self) -> None:
        """Scenario: Numbers unique regardless of case."""
        record_batch(self.kl, substance=substance_for("CH-0012"),
                     number="KL0412FA")
        with self.refusing("number"):
            record_batch(self.kl, substance=substance_for("acetophenone"),
                         number="kl0412fa")
        self.assertEqual(Batch.objects.count(), 1)

    def test_the_refusal_names_the_batch_that_holds_the_number(self) -> None:
        """Design (Risks: the error names the batch that holds the
        number)."""
        from inventory.bookings import Refused
        record_batch(self.kl, substance=substance_for("CH-0012"),
                     number="KL0412FA")
        with self.assertRaises(Refused) as caught:
            record_batch(self.kl, substance=substance_for("acetophenone"),
                         number="kl0412fa")
        self.assertIn("KL0412FA", " ".join(
            caught.exception.message_dict["number"]))


class RecordFromStepTests(StepCase):
    """The booking ``record_batch`` from a task step (Batches,
    Inventory forms, production-planning: Batches of tasks)."""

    def setUp(self) -> None:
        super().setUp()
        self.intermediate = substance_for("4-acetylbiphenyl")
        self.product = substance_for("1-biphenyl-4-yl-ethanol")
        self.task = self.follow()
        self.first, self.second = steps_of(self.task)

    def record(self, step: TaskStep | None = None, **extra):
        step = step or self.first
        fields = {"substance": step.products()[0], "number": "KL0412",
                  "task_step": step, "amount": Decimal("2"), "unit": "g"}
        return record_batch(self.kl, **{**fields, **extra})

    def test_the_yield_goes_into_the_flask(self) -> None:
        """Scenario: Yield into the flask."""
        plain = make_task(self.kl, "CH-0012", steps=2, started=past(1))
        step = plain.steps.get(position=2)
        batch = record_batch(self.kl, substance=plain.substance,
                             number="KL0412", task_step=step,
                             amount=Decimal("2"), unit="g")
        stored = fresh(batch)
        self.assertEqual(
            (stored.source, stored.task_step, stored.yield_amount,
             stored.yield_unit, stored.shown_yield),
            ("made", step, Decimal("2000"), "g", Decimal("2")))
        vessel = batch.vessels.get()
        self.assertEqual(
            (vessel.flask, vessel.unit, vessel.amount, vessel.location),
            (True, "g", Decimal("2000"), ""))
        opening = vessel.movements.get()
        self.assertEqual(
            (opening.kind, opening.amount, opening.amount_after,
             opening.user), ("opening", Decimal("2000"), Decimal("2000"),
                             self.kl))

    def test_the_yield_may_be_stored_at_once(self) -> None:
        """Scenario: Yield stored at once."""
        make_item(self.kl, "CH-0012")
        plain = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        batch = record_batch(
            self.kl, substance=plain.substance, number="KL0412",
            task_step=plain.steps.get(), amount=Decimal("2"), unit="g",
            location="Kühlschrank 2")
        vessel = batch.vessels.get()
        self.assertEqual(
            (vessel.flask, vessel.location, vessel.amount, vessel.kind),
            (False, "Kühlschrank 2", Decimal("2000"), "end-product"))
        self.assertEqual(fresh(batch).yield_amount, Decimal("2000"))
        self.assertFalse(batch.vessels.filter(flask=True).exists())

    def test_the_yield_is_kept_in_the_base_unit_of_its_unit(self) -> None:
        for unit, amount, base in (("mg", "47.5", "47.5"), ("g", "1", "1000"),
                                   ("umol", "5", "5"),
                                   ("mmol", "2.5", "2500")):
            with self.subTest(unit=unit):
                batch = self.record(number=f"U-{unit}", amount=Decimal(
                    amount), unit=unit)
                stored = fresh(batch)
                self.assertEqual((stored.yield_unit, stored.yield_amount),
                                 (unit, Decimal(base)))
                vessel = batch.vessels.get()
                self.assertEqual((vessel.unit, vessel.amount),
                                 (unit, Decimal(base)))

    def test_the_amount_and_its_unit_are_required(self) -> None:
        with self.refusing("amount"):
            self.record(amount=None)
        with self.refusing():
            self.record(unit="")

    def test_a_yield_above_zero_is_required(self) -> None:
        for amount in ("0", "-1"):
            with self.subTest(amount=amount), self.refusing("amount"):
                self.record(amount=Decimal(amount))

    def test_an_unknown_unit_is_refused(self) -> None:
        with self.refusing("unit"):
            self.record(unit="kg")

    def test_the_step_that_made_it_and_its_journal_entry(self) -> None:
        """Requirement: Batches (names the step's journal entry when the
        step names one)."""
        entry = entry_of("CE-3/2")
        TaskStep.objects.filter(pk=self.first.pk).update(
            journal_entry=entry)
        batch = self.record(self.first)
        self.assertEqual((fresh(batch).task_step, fresh(batch).journal_entry),
                         (self.first, entry))
        other = self.record(self.second, number="KL0413")
        self.assertIsNone(fresh(other).journal_entry)

    def test_fractions_of_one_entry(self) -> None:
        """Scenario: Fractions of one entry."""
        entry = entry_of("CE-3/2")
        TaskStep.objects.filter(pk=self.first.pk).update(
            journal_entry=entry)
        for number in ("CE3002FA", "CE3002FB"):
            self.record(number=number)
        with self.refusing("substance"):
            self.record(substance=substance_for("cinnamic-acid"),
                        number="CE3002FC")
        self.assertEqual(
            sorted(entry.batches.values_list("number", flat=True)),
            ["CE3002FA", "CE3002FB"])
        for batch in entry.batches.all():
            self.assertEqual(batch.task_step, self.first)

    def test_an_entry_makes_its_products_and_not_its_substrates(
            self) -> None:
        with self.refusing("substance"):
            self.record(self.second, substance=self.intermediate)
        batch = self.record(self.second, substance=self.product)
        self.assertEqual(fresh(batch).task_step, self.second)

    def test_a_step_without_an_entry_makes_the_tasks_substance(
            self) -> None:
        plain = make_task(self.kl, "Aspirin", steps=2, started=past(1))
        step = plain.steps.get(position=1)
        with self.refusing("substance"):
            self.record(step, substance=substance_for("cinnamic-acid"))
        self.record(step, substance=substance_for("aspirin"))
        self.assertEqual(Batch.objects.get().task_step, step)

    def test_a_step_may_make_several_batches(self) -> None:
        self.record(number="KL1")
        self.record(number="KL2")
        self.assertEqual(self.first.batches.count(), 2)

    def test_a_bought_batch_is_not_made_by_a_step(self) -> None:
        with self.refusing():
            self.record(source="bought", number="", supplier="Sigma")

    def test_a_planned_or_running_task_takes_a_batch(self) -> None:
        planned = make_task(self.kl, "Aspirin", steps=1)
        running = make_task(self.kl, "Aspirin", steps=1, started=past(1))
        for number, task in (("P-1", planned), ("R-1", running)):
            with self.subTest(task=task.number):
                self.record(task.steps.get(), substance=task.substance,
                            number=number)
        self.assertEqual(Batch.objects.count(), 2)

    def test_a_step_of_a_task_that_is_closed_is_refused(self) -> None:
        """Scenario: Not from an ended task."""
        ended = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                          ended=past(1))
        cancelled = make_task(self.kl, "Aspirin", steps=1, cancelled=True)
        failed = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                           ended=past(1), failed=True)
        for task in (ended, cancelled, failed):
            with self.subTest(task=task.number), self.refusing():
                self.record(task.steps.get(), substance=task.substance)
        self.assertEqual(Batch.objects.count(), 0)

    def test_a_refused_recording_leaves_no_vessel(self) -> None:
        with self.refusing("substance"):
            self.record(substance=substance_for("cinnamic-acid"))
        self.assertEqual(Vessel.objects.count(), 0)
        self.assertEqual(VesselMovement.objects.count(), 0)

    def test_numbers_are_unique_regardless_of_case_here_too(self) -> None:
        self.record(number="KL0412FA")
        with self.refusing("number"):
            self.record(number="kl0412fa")
        self.assertEqual(Batch.objects.count(), 1)

    def test_the_booking_is_the_users_in_the_history(self) -> None:
        batch = self.record()
        self.assertEqual(batch.history.get().history_user, self.kl)
        self.assertEqual(batch.vessels.get().history.get().history_user,
                         self.kl)
