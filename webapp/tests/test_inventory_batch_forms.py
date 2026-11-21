"""Tests of the forms that record batches, change them and open their
vessels (end-product-inventory: Inventory forms, Batches, Vessels)."""

from datetime import date
from decimal import Decimal

from inventory.models import Batch, Vessel, VesselMovement
from tasks.models import TaskStep

from . import (context_form, datalist, field_value, make_batch, make_item,
               make_task, make_vessel, make_substance, page, past,
               substance_for)
from .inventory_support import (NEW_BATCH, batch_data, batch_url,
                                fresh, snapshot, vessel_url)
from .journal_support import entries_named, entry_of
from .task_support import TODAY_ISO, StepCase, steps_of

FORM_FIELDS = {"substance", "source", "number", "journal_entry", "date",
               "supplier", "supplier_article_number", "supplier_batch",
               "note", "amount", "unit", "location"}


def names_of(root, anchor: str) -> set[str]:
    """The names of the controls of the form that holds ``anchor``."""
    form = root.find(("input", "select", "textarea"), name=anchor
                     ).closest("form")
    return {e.get("name") for e in
            form.find_all(("input", "select", "textarea"))
            if e.get("name") and e.get("type") not in ("submit", "button")
            and e.get("name") != "csrfmiddlewaretoken"}


class BatchFormCase(StepCase):
    """The demo registry, the demo notebooks, the demo collection and a
    signed-in ``kl``; a clock at 2026-11-04."""

    def setUp(self) -> None:
        super().setUp()
        self.cinnamic = substance_for("CH-0012")

    def refused_at(self, response, *fields: str) -> None:
        """The form is shown again with an error at one of ``fields``."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(errors, "the form shows no error")
        self.assertTrue(set(errors) & set(fields),
                        f"errors at {sorted(errors)}, not at {fields}")


class NewBatchFormTests(BatchFormCase):

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = names_of(page(self.client.get(NEW_BATCH)), "substance")
        self.assertLessEqual(FORM_FIELDS, names)
        self.assertNotIn("step", names)

    def test_the_substance_comes_from_the_url(self) -> None:
        root = page(self.client.get(f"{NEW_BATCH}?substance=cinnamic-acid"))
        self.assertEqual(field_value(root, "substance"), "cinnamic-acid")

    def test_the_source_is_made_by_default(self) -> None:
        root = page(self.client.get(NEW_BATCH))
        self.assertEqual(field_value(root, "source"), "made")
        options = root.find("select", name="source").find_all("option")
        self.assertEqual(
            {o.get("value"): o.text() for o in options if o.get("value")},
            {"made": "hergestellt", "bought": "gekauft"})

    def test_the_date_is_today_by_default(self) -> None:
        root = page(self.client.get(NEW_BATCH))
        self.assertEqual(field_value(root, "date"), TODAY_ISO)

    def test_the_substance_offers_every_substance(self) -> None:
        make_substance("no-article", "No article")
        options = datalist(page(self.client.get(NEW_BATCH)), "substance")
        self.assertEqual(options["cinnamic-acid"], "(E)-Zimtsäure")
        self.assertEqual(options["no-article"], "No article")

    def test_the_location_offers_the_locations_in_use(self) -> None:
        make_vessel(self.kl, article="A-1", location="Kühlraum")
        make_vessel(self.kl, article="A-2", location="Regal 3")
        make_vessel(self.kl, article="A-3", location="Kühlraum")
        make_vessel(self.kl, article="A-4")
        options = datalist(page(self.client.get(NEW_BATCH)), "location")
        self.assertEqual(set(options) - {""}, {"Kühlraum", "Regal 3"})

    def test_a_made_batch(self) -> None:
        done = self.client.post(NEW_BATCH, batch_data(
            number="KL0412FA", date="2026-10-30", note="Rest"))
        batch = Batch.objects.get()
        self.assertRedirects(done, batch_url(batch),
                             fetch_redirect_response=False)
        self.assertEqual(
            (batch.substance.key, batch.source, batch.number, batch.date,
             batch.note, batch.task_step, batch.journal_entry),
            ("cinnamic-acid", "made", "KL0412FA", date(2026, 10, 30),
             "Rest", None, None))
        self.assertFalse(batch.vessels.exists())
        self.assertEqual(batch.history.get().history_user, self.kl)
        self.assertMessageNames(done, "KL0412FA")

    def test_a_bought_batch(self) -> None:
        """Scenario: Made and bought batches (the form)."""
        done = self.client.post(NEW_BATCH, batch_data(
            source="bought", number="", supplier="Sigma",
            supplier_article_number="C80857", supplier_batch="MKCK1234",
            date="2026-11-02"))
        batch = Batch.objects.get()
        self.assertRedirects(done, batch_url(batch),
                             fetch_redirect_response=False)
        self.assertEqual(
            (batch.source, batch.supplier, batch.supplier_article_number,
             batch.supplier_batch, batch.number, batch.date),
            ("bought", "Sigma", "C80857", "MKCK1234", "",
             date(2026, 11, 2)))
        self.assertMessageNames(done, "MKCK1234")

    def test_the_source_is_made_when_none_is_chosen(self) -> None:
        data = batch_data()
        del data["source"]
        self.client.post(NEW_BATCH, data)
        self.assertEqual(Batch.objects.get().source, "made")

    def test_an_amount_opens_a_stored_vessel(self) -> None:
        self.client.post(NEW_BATCH, batch_data(
            amount="50", unit="mg", location="Kühlraum"))
        vessel = Batch.objects.get().vessels.get()
        self.assertEqual(
            (vessel.flask, vessel.unit, vessel.amount, vessel.location),
            (False, "mg", Decimal("50"), "Kühlraum"))
        opening = vessel.movements.get()
        self.assertEqual(
            (opening.kind, opening.amount, opening.amount_after,
             opening.user), ("opening", Decimal("50"), Decimal("50"),
                             self.kl))

    def test_the_amount_is_in_the_unit_chosen(self) -> None:
        cases = [("g", "1", "1000"), ("mmol", "2,5", "2500"),
                 ("umol", "5", "5"), ("mg", "47,5", "47.5")]
        for index, (unit, amount, base) in enumerate(cases):
            with self.subTest(unit=unit):
                self.client.post(NEW_BATCH, batch_data(
                    number=f"U-{index}", unit=unit, amount=amount))
                vessel = Batch.objects.get(number=f"U-{index}"
                                           ).vessels.get()
                self.assertEqual((vessel.unit, vessel.amount),
                                 (unit, Decimal(base)))

    def test_a_batch_without_an_amount_has_no_yield_and_no_vessel(
            self) -> None:
        self.client.post(NEW_BATCH, batch_data(amount=""))
        batch = Batch.objects.get()
        self.assertIsNone(batch.yield_amount)
        self.assertEqual(Vessel.objects.count(), 0)

    def test_an_amount_without_its_unit_is_refused(self) -> None:
        before = snapshot()
        self.refused_at(self.client.post(NEW_BATCH, batch_data(
            amount="5", unit="")), "unit", "amount")
        self.assertEqual(snapshot(), before)

    def test_refused_fields(self) -> None:
        cases = {"substance": ["", "no-such-substance", "CH-0012"],
                 "unit": ["kg"], "amount": ["-1", "x"],
                 "number": ["n" * 31, ""], "location": ["l" * 101],
                 "supplier": ["s" * 101], "source": ["stolen"],
                 "date": ["x", "2026-13-01", "2026-11-05"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    extra = {"amount": "5"} if field in (
                        "unit", "location") else {}
                    self.refused(self.client.post(NEW_BATCH, batch_data(
                        **{**extra, field: value})), field)
        self.assertEqual(Batch.objects.count(), 0)
        self.assertEqual(Vessel.objects.count(), 0)
        self.assertEqual(VesselMovement.objects.count(), 0)

    def test_the_supplier_fields_have_their_lengths(self) -> None:
        for field in ("supplier_article_number", "supplier_batch"):
            with self.subTest(field=field):
                self.refused(self.client.post(NEW_BATCH, batch_data(
                    source="bought", number="", **{field: "x" * 51})),
                    field)
        self.assertEqual(Batch.objects.count(), 0)

    def test_a_bought_batch_with_a_number_is_refused(self) -> None:
        self.refused(self.client.post(NEW_BATCH, batch_data(
            source="bought", number="KL1", supplier="Sigma")), "number")
        self.assertEqual(Batch.objects.count(), 0)

    def test_numbers_unique_regardless_of_case(self) -> None:
        """Scenario: Numbers unique regardless of case."""
        make_batch(self.kl, "CH-0012", number="KL0412FA")
        make_substance("acetophenone")
        self.refused(self.client.post(NEW_BATCH, batch_data(
            substance="acetophenone", number="kl0412fa")), "number")
        self.assertEqual(Batch.objects.count(), 1)

    def test_a_substance_without_an_article_takes_a_batch(self) -> None:
        make_substance("acetophenone")
        self.client.post(NEW_BATCH, batch_data(substance="acetophenone"))
        self.assertEqual(Batch.objects.get().substance.key, "acetophenone")

    def test_a_journal_entry_is_created_on_first_naming(self) -> None:
        self.assertEqual(entries_named("AE-1/9"), 0)
        self.client.post(NEW_BATCH, batch_data(journal_entry="AE-1/9"))
        self.assertEqual(entries_named("AE-1/9"), 1)
        batch = Batch.objects.get()
        self.assertEqual(str(batch.journal_entry), "AE-1/9")

    def test_an_entry_that_exists_is_reused(self) -> None:
        entry = entry_of("AE-1/9")
        self.client.post(NEW_BATCH, batch_data(
            number="AE1009FA", journal_entry="AE-1/9"))
        self.client.post(NEW_BATCH, batch_data(
            number="AE1009FB", journal_entry="AE-1/9"))
        self.assertEqual(entries_named("AE-1/9"), 1)
        self.assertEqual(entry.batches.count(), 2)

    def test_an_entry_of_no_notebook_is_refused(self) -> None:
        for value in ("ZZ-1/1", "AE-1", "AE-1/0", "x"):
            with self.subTest(value=value):
                self.refused(self.client.post(NEW_BATCH, batch_data(
                    journal_entry=value)), "journal_entry")
        self.assertEqual(Batch.objects.count(), 0)
        self.assertEqual(entries_named("AE-1/9"), 0)

    def test_the_form_keeps_what_was_typed(self) -> None:
        done = self.client.post(NEW_BATCH, batch_data(
            number="KL-9", amount="-1"))
        self.assertEqual(field_value(page(done), "number"), "KL-9")


class FromStepFormTests(BatchFormCase):
    """The new-batch form requested and posted with ``?step=<id>``."""

    def setUp(self) -> None:
        super().setUp()
        self.task = self.follow()
        self.first, self.second = steps_of(self.task)

    def url(self, step: TaskStep) -> str:
        return f"{NEW_BATCH}?step={step.pk}"

    def post(self, step: TaskStep, **data: str):
        return self.client.post(self.url(step), batch_data(**{
            "substance": step.products()[0].key, "step": str(step.pk),
            "amount": "2", "unit": "g", **data}))

    def test_the_form_is_filled_in_from_the_step(self) -> None:
        """Scenario: A batch from a step."""
        entry = entry_of("AE-1/9")
        TaskStep.objects.filter(pk=self.second.pk).update(
            journal_entry=entry)
        response = self.client.get(self.url(self.second))
        root = page(response)
        self.assertEqual(
            (field_value(root, "substance"), field_value(root, "source"),
             field_value(root, "date")),
            ("1-biphenyl-4-yl-ethanol", "made", TODAY_ISO))
        self.assertEqual(field_value(root, "step"), str(self.second.pk))
        self.assertIn("AE-1/9", response.content.decode())
        for control in root.find_all(("input", "select", "textarea"),
                                     name="journal_entry"):
            self.assertTrue({"disabled", "readonly"} & set(control.attrs),
                            "the step's entry is editable")

    def test_the_first_product_of_the_entry_is_filled_in(self) -> None:
        root = page(self.client.get(self.url(self.first)))
        self.assertEqual(field_value(root, "substance"),
                         "4-acetylbiphenyl")

    def test_a_step_without_an_entry_fills_in_the_tasks_substance(
            self) -> None:
        plain = make_task(self.kl, "Aspirin", steps=2, started=past(1))
        root = page(self.client.get(self.url(plain.steps.get(position=2))))
        self.assertEqual(field_value(root, "substance"), "aspirin")
        self.assertEqual(field_value(root, "source"), "made")

    def test_the_amount_is_required(self) -> None:
        """Scenario: A batch from a step (posting without an amount)."""
        self.refused(self.post(self.first, amount=""), "amount")
        self.assertEqual(Batch.objects.count(), 0)

    def test_the_yield_goes_into_the_flask(self) -> None:
        done = self.post(self.first, number="KL0412", amount="2", unit="g")
        batch = Batch.objects.get()
        self.assertRedirects(done, batch_url(batch),
                             fetch_redirect_response=False)
        self.assertEqual(
            (batch.task_step, batch.source, batch.yield_amount,
             batch.yield_unit, batch.substance.key),
            (self.first, "made", Decimal("2000"), "g", "4-acetylbiphenyl"))
        vessel = batch.vessels.get()
        self.assertEqual((vessel.flask, vessel.amount, vessel.location),
                         (True, Decimal("2000"), ""))
        self.assertEqual(vessel.movements.get().kind, "opening")
        self.assertMessageNames(done, "KL0412")

    def test_a_location_makes_a_stored_vessel(self) -> None:
        self.post(self.first, location="Kühlschrank 2")
        batch = Batch.objects.get()
        vessel = batch.vessels.get()
        self.assertEqual((vessel.flask, vessel.location, vessel.amount),
                         (False, "Kühlschrank 2", Decimal("2000")))
        self.assertEqual(batch.yield_amount, Decimal("2000"))

    def test_the_steps_entry_is_the_batchs(self) -> None:
        entry = entry_of("CE-3/2")
        TaskStep.objects.filter(pk=self.first.pk).update(
            journal_entry=entry)
        self.post(self.first, journal_entry="AE-1/9")
        self.assertEqual(Batch.objects.get().journal_entry, entry)
        self.assertEqual(entries_named("AE-1/9"), 0)

    def test_a_substance_the_step_does_not_make_is_refused(self) -> None:
        self.refused(self.post(self.first, substance="cinnamic-acid"),
                     "substance")
        self.assertEqual(Batch.objects.count(), 0)

    def test_an_entry_makes_its_products_and_not_its_substrates(
            self) -> None:
        self.refused(self.post(self.second,
                               substance="4-acetylbiphenyl"), "substance")
        self.assertEqual(self.post(self.second).status_code, 302)
        self.assertEqual(Batch.objects.get().task_step, self.second)

    def test_fractions_of_one_entry(self) -> None:
        """Scenario: Fractions of one entry."""
        entry = entry_of("CE-3/2")
        TaskStep.objects.filter(pk=self.first.pk).update(
            journal_entry=entry)
        for number in ("CE3002FA", "CE3002FB"):
            self.assertEqual(self.post(self.first, number=number
                                       ).status_code, 302)
        self.refused(self.post(self.first, substance="cinnamic-acid",
                               number="CE3002FC"), "substance")
        self.assertEqual(
            sorted(entry.batches.values_list("number", flat=True)),
            ["CE3002FA", "CE3002FB"])

    def test_a_step_of_an_ended_task_is_refused(self) -> None:
        """Scenario: Not from an ended task."""
        ended = make_task(self.kl, "Aspirin", steps=1, started=past(2),
                          ended=past(1))
        step = ended.steps.get()
        response = self.client.post(self.url(step), batch_data(
            substance="aspirin", step=str(step.pk), amount="2", unit="g"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(context_form(response).errors)
        self.assertEqual(Batch.objects.count(), 0)

    def test_the_step_comes_from_the_query_and_the_form_alike(self) -> None:
        self.post(self.first)
        self.assertEqual(Batch.objects.get().task_step, self.first)

    def test_a_step_may_make_several_batches(self) -> None:
        self.post(self.first, number="KL1")
        self.post(self.first, number="KL2")
        self.assertEqual(self.first.batches.count(), 2)


class BatchEditFormTests(BatchFormCase):

    def setUp(self) -> None:
        super().setUp()
        self.entry = entry_of("AE-1/9")
        self.made = make_batch(
            self.kl, "CH-0012", number="KL0412", date=date(2026, 10, 1),
            note="alt", journal_entry=self.entry, yield_amount="2",
            yield_unit="g")
        self.bought = make_batch(
            self.kl, "CH-0012", source="bought", supplier="Sigma",
            supplier_article_number="C1", supplier_batch="M1",
            date=date(2026, 10, 2), note="gekauft")

    def data(self, **over: str) -> dict[str, str]:
        data = {"number": "KL0412", "journal_entry": "AE-1/9",
                "date": "2026-10-01", "note": "alt"}
        data.update(over)
        return data

    def test_the_form_of_a_made_batch(self) -> None:
        root = page(self.client.get(batch_url(self.made, "edit")))
        names = names_of(root, "number")
        self.assertLessEqual({"number", "journal_entry", "date", "note"},
                             names)
        for fixed in ("substance", "source", "task_step", "step",
                      "supplier", "supplier_article_number",
                      "supplier_batch"):
            self.assertNotIn(fixed, names)
        self.assertEqual(field_value(root, "number"), "KL0412")
        self.assertEqual(field_value(root, "journal_entry"), "AE-1/9")
        self.assertEqual(field_value(root, "date"), "2026-10-01")
        self.assertEqual(field_value(root, "note"), "alt")

    def test_the_form_of_a_bought_batch(self) -> None:
        root = page(self.client.get(batch_url(self.bought, "edit")))
        names = names_of(root, "supplier")
        self.assertLessEqual({"supplier", "supplier_article_number",
                              "supplier_batch", "date", "note"}, names)
        for fixed in ("substance", "source", "number", "journal_entry"):
            self.assertNotIn(fixed, names)
        self.assertEqual(field_value(root, "supplier"), "Sigma")
        self.assertEqual(field_value(root, "supplier_batch"), "M1")

    def test_changing_a_made_batch(self) -> None:
        self.client.force_login(self.ae)
        done = self.client.post(batch_url(self.made, "edit"), self.data(
            number="KL0413", journal_entry="CE-3/5", date="2026-09-01",
            note="neu"))
        self.assertRedirects(done, batch_url(self.made),
                             fetch_redirect_response=False)
        batch = fresh(self.made)
        self.assertEqual(
            (batch.number, str(batch.journal_entry), batch.date, batch.note),
            ("KL0413", "CE-3/5", date(2026, 9, 1), "neu"))
        self.assertEqual(entries_named("CE-3/5"), 1)
        self.assertEqual(batch.number_key, "kl0413")
        self.assertEqual(batch.history.count(), 2)
        self.assertEqual(batch.history.first().history_user, self.ae)
        self.assertMessageNames(done, "KL0413")

    def test_the_entry_may_be_cleared(self) -> None:
        self.client.post(batch_url(self.made, "edit"), self.data(
            journal_entry=""))
        self.assertIsNone(fresh(self.made).journal_entry)

    def test_changing_a_bought_batch(self) -> None:
        done = self.client.post(batch_url(self.bought, "edit"), {
            "supplier": "Merck", "supplier_article_number": "C2",
            "supplier_batch": "M2", "date": "2026-09-01", "note": "neu"})
        self.assertRedirects(done, batch_url(self.bought),
                             fetch_redirect_response=False)
        batch = fresh(self.bought)
        self.assertEqual(
            (batch.supplier, batch.supplier_article_number,
             batch.supplier_batch, batch.date, batch.note),
            ("Merck", "C2", "M2", date(2026, 9, 1), "neu"))

    def test_substance_source_and_step_are_fixed(self) -> None:
        make_substance("other")
        task = make_task(self.kl, "CH-0012", steps=1, started=past(1))
        step = task.steps.get()
        made = make_batch(self.kl, "CH-0012", number="KL77",
                          task_step=step)
        other = make_task(self.kl, "Aspirin", steps=1).steps.get()
        self.client.post(batch_url(made, "edit"), {
            "number": "KL78", "journal_entry": "", "date": "", "note": "",
            "substance": "other", "source": "bought",
            "task_step": str(other.pk), "step": str(other.pk)})
        batch = fresh(made)
        self.assertEqual(
            (batch.number, batch.substance.key, batch.source,
             batch.task_step), ("KL78", "cinnamic-acid", "made", step))

    def test_a_number_another_batch_has_is_refused_regardless_of_case(
            self) -> None:
        make_batch(self.kl, "CH-0012", number="KL0500")
        before = snapshot()
        self.refused(self.client.post(batch_url(self.made, "edit"),
                                      self.data(number="kl0500")), "number")
        self.assertEqual(snapshot(), before)

    def test_a_batch_may_keep_its_number_in_another_case(self) -> None:
        self.client.post(batch_url(self.made, "edit"), self.data(
            number="kl0412"))
        batch = fresh(self.made)
        self.assertEqual((batch.number, batch.number_key),
                         ("kl0412", "kl0412"))

    def test_a_renamed_batch_frees_its_old_number(self) -> None:
        self.client.post(batch_url(self.made, "edit"), self.data(
            number="KL0999"))
        done = self.client.post(f"{NEW_BATCH}", batch_data(number="KL0412"))
        self.assertEqual(done.status_code, 302)
        self.refused(self.client.post(NEW_BATCH, batch_data(
            number="kl0999")), "number")

    def test_the_number_is_required_and_has_30_characters_at_most(
            self) -> None:
        for number in ("", "n" * 31):
            with self.subTest(number=number):
                self.refused(self.client.post(
                    batch_url(self.made, "edit"), self.data(
                        number=number)), "number")
        self.assertEqual(fresh(self.made).number, "KL0412")

    def test_an_entry_of_no_notebook_is_refused(self) -> None:
        self.refused(self.client.post(batch_url(self.made, "edit"),
                                      self.data(journal_entry="ZZ-1/1")),
                     "journal_entry")
        self.assertEqual(str(fresh(self.made).journal_entry), "AE-1/9")

    def test_a_date_in_the_future_is_refused(self) -> None:
        self.refused(self.client.post(batch_url(self.made, "edit"),
                                      self.data(date="2026-11-05")), "date")

    def test_a_refused_edit_changes_nothing(self) -> None:
        before = snapshot()
        self.refused(self.client.post(batch_url(self.made, "edit"),
                                      self.data(number="n" * 31)), "number")
        self.assertEqual(snapshot(), before)

    def test_an_unknown_batch_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            "/lab/inventory/batches/999999/edit/").status_code, 404)


class NewVesselFormTests(BatchFormCase):
    """Requirement: Inventory forms (`/lab/inventory/batches/<id>/vessels/
    new/`)."""

    def setUp(self) -> None:
        super().setUp()
        self.batch = make_batch(self.kl, "CH-0012", number="KL0412")
        self.url = batch_url(self.batch, "vessels/new")

    def data(self, **over: str) -> dict[str, str]:
        data = {"amount": "5", "unit": "g", "location": "Regal 3",
                "note": "Reserve"}
        data.update(over)
        return data

    def test_the_form_holds_the_fields_of_the_spec(self) -> None:
        names = names_of(page(self.client.get(self.url)), "amount")
        self.assertEqual(names, {"amount", "unit", "location", "note"})

    def test_the_location_offers_the_locations_in_use(self) -> None:
        make_vessel(self.kl, self.batch, location="Kühlraum")
        make_vessel(self.kl, self.batch, location="Regal 3")
        options = datalist(page(self.client.get(self.url)), "location")
        self.assertEqual(set(options) - {""}, {"Kühlraum", "Regal 3"})

    def test_a_new_stored_vessel(self) -> None:
        done = self.client.post(self.url, self.data())
        self.assertEqual(done.status_code, 302)
        self.assertIn(done["Location"], {batch_url(self.batch),
                                         vessel_url(self.batch.vessels.get())})
        vessel = self.batch.vessels.get()
        self.assertEqual(
            (vessel.flask, vessel.unit, vessel.amount, vessel.location,
             vessel.note),
            (False, "g", Decimal("5000"), "Regal 3", "Reserve"))
        opening = vessel.movements.get()
        self.assertEqual((opening.kind, opening.amount, opening.user),
                         ("opening", Decimal("5000"), self.kl))

    def test_the_amount_is_in_the_unit_chosen(self) -> None:
        for unit, amount, base in (("mmol", "2,5", "2500"),
                                   ("mg", "47,5", "47.5")):
            with self.subTest(unit=unit):
                self.client.post(self.url, self.data(unit=unit,
                                                     amount=amount))
                vessel = self.batch.vessels.order_by("-pk").first()
                self.assertEqual((vessel.unit, vessel.amount),
                                 (unit, Decimal(base)))

    def test_refused_fields(self) -> None:
        cases = {"amount": ["", "-1", "x"], "unit": ["", "kg"],
                 "location": ["l" * 101]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.refused(self.client.post(
                        self.url, self.data(**{field: value})), field)
        self.assertEqual(self.batch.vessels.count(), 0)

    def test_a_vessel_of_zero_may_be_entered(self) -> None:
        self.client.post(self.url, self.data(amount="0"))
        self.assertEqual(self.batch.vessels.get().amount, 0)

    def test_an_unknown_batch_answers_404(self) -> None:
        self.assertEqual(self.client.get(
            "/lab/inventory/batches/999999/vessels/new/").status_code, 404)

    def test_the_item_of_the_substance_sees_the_vessel(self) -> None:
        item = make_item(self.kl, "CH-0012")
        self.client.post(self.url, self.data(amount="50", unit="mg"))
        text = page(self.client.get(
            f"/lab/inventory/items/{item.pk}/")).text()
        self.assertIn("KL0412", text)
