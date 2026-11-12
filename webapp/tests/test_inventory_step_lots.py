"""Tests of the lots a task step makes (end-product-inventory: Bulk lots,
Bulk lot page, Inventory forms)."""

from datetime import date
from decimal import Decimal

from django.db.models import ProtectedError

from inventory.models import Lot
from tasks.models import Task, TaskStep

from . import (context_form, edit_data, field_value, make_lot, make_task,
               page, past, substance_for, task_url)
from .inventory_support import lot_data, lot_url
from .task_support import NEW_LOT, TODAY_ISO, StepCase, steps_of


class StepLotCase(StepCase):
    """A running task of ``1-biphenyl-4-yl-ethanol`` following
    ``SEQ-0002``, whose steps are ``self.first`` and ``self.second``."""

    def setUp(self) -> None:
        super().setUp()
        for key in ("4-acetylbiphenyl", "cinnamic-acid"):
            substance_for(key)
        self.task = self.follow()
        self.first, self.second = steps_of(self.task)

    def form(self, step: TaskStep, **data: str):
        """Post the new-lot form from ``step`` with ``lot_data`` over
        ``data``."""
        return self.client.post(f"{NEW_LOT}?step={step.pk}",
                                lot_data(**data))

    def refused(self, response, field: str) -> None:
        self.assertEqual(response.status_code, 200)
        self.assertIn(field, context_form(response).errors)


class MadeByStepTests(StepLotCase):

    def test_a_lot_made_by_a_step(self) -> None:
        """Scenario: A lot made by a step."""
        done = self.form(self.first, substance="4-acetylbiphenyl",
                         unit="g", amount="2")
        lot = Lot.objects.get()
        self.assertRedirects(done, lot_url(lot),
                             fetch_redirect_response=False)
        self.assertEqual(lot.task_step, self.first)
        self.assertEqual(
            (lot.substance.key, lot.source, lot.unit, lot.amount),
            ("4-acetylbiphenyl", "made", "g", Decimal("2000")))
        opening = lot.movements.get()
        self.assertEqual((opening.kind, opening.user, opening.amount_after),
                         ("opening", self.kl, Decimal("2000")))

    def test_a_substance_the_step_does_not_make_is_refused(self) -> None:
        """Scenario: A lot made by a step (recording one of
        `cinnamic-acid` from that step is refused with an error at the
        substance)."""
        self.refused(self.form(self.first, substance="cinnamic-acid"),
                     "substance")
        self.assertEqual(Lot.objects.count(), 0)

    def test_an_entry_makes_its_products_and_not_its_substrates(
            self) -> None:
        """Requirement: Bulk lots (`task_step`, whose entry has the lot's
        substance among its products)."""
        self.refused(self.second_lot("4-acetylbiphenyl"), "substance")
        self.assertEqual(Lot.objects.count(), 0)
        self.assertEqual(self.second_lot("1-biphenyl-4-yl-ethanol")
                         .status_code, 302)
        self.assertEqual(Lot.objects.get().task_step, self.second)

    def second_lot(self, key: str):
        return self.form(self.second, substance=key)

    def test_a_step_without_an_entry_makes_the_tasks_substance(
            self) -> None:
        """Requirement: Bulk lots (for a step without an entry, whose
        task makes the lot's substance)."""
        plain = make_task(self.kl, "Aspirin", steps=2, started=past(1))
        step = plain.steps.get(position=1)
        self.refused(self.form(step, substance="cinnamic-acid"),
                     "substance")
        self.assertEqual(self.form(step, substance="aspirin").status_code,
                         302)
        self.assertEqual(Lot.objects.get().task_step, step)

    def test_a_step_may_make_several_lots(self) -> None:
        for amount in ("1", "2"):
            self.form(self.first, substance="4-acetylbiphenyl",
                      amount=amount)
        self.assertEqual(
            Lot.objects.filter(task_step=self.first).count(), 2)

    def test_a_lot_without_the_query_is_made_by_no_step(self) -> None:
        self.client.post(NEW_LOT, lot_data())
        self.assertIsNone(Lot.objects.get().task_step)

    def test_the_step_comes_from_the_query_and_not_from_the_form(
            self) -> None:
        self.client.post(NEW_LOT, {**lot_data(),
                                   "task_step": str(self.first.pk)})
        self.assertIsNone(Lot.objects.get().task_step)

    def test_the_lot_names_its_step_by_a_protected_nullable_key(
            self) -> None:
        """Requirement: Bulk lots (`task_step`)."""
        field = Lot._meta.get_field("task_step")
        self.assertIs(field.remote_field.model, TaskStep)
        self.assertEqual(field.remote_field.on_delete.__name__, "PROTECT")
        self.assertTrue(field.null)

    def test_a_step_that_made_a_lot_cannot_be_deleted(self) -> None:
        self.form(self.first, substance="4-acetylbiphenyl")
        with self.assertRaises(ProtectedError):
            self.first.delete()
        self.assertTrue(TaskStep.objects.filter(pk=self.first.pk).exists())


class StepFormFillTests(StepLotCase):
    """The new-lot form requested with ``?step=<id>``."""

    def fields(self, step: TaskStep) -> dict[str, str | None]:
        root = page(self.client.get(f"{NEW_LOT}?step={step.pk}"))
        return {name: field_value(root, name) for name in
                ("substance", "source", "batch", "made_on")}

    def test_the_first_product_of_the_entry_and_today(self) -> None:
        """Requirement: Inventory forms (`?step=<id>` fills in the first
        product of the step's entry, and today)."""
        self.assertEqual(self.fields(self.first), {
            "substance": "4-acetylbiphenyl", "source": "made",
            "batch": "", "made_on": TODAY_ISO})

    def test_the_tasks_batch_when_the_substance_is_the_tasks(self) -> None:
        """Requirement: Inventory forms (its task's batch when the
        substance is the task's)."""
        self.client.post(task_url(self.task, "edit"), self.edited(
            batch="B-9"))
        self.assertEqual(self.fields(self.second), {
            "substance": "1-biphenyl-4-yl-ethanol", "source": "made",
            "batch": "B-9", "made_on": TODAY_ISO})
        self.assertEqual(self.fields(self.first)["batch"], "")

    def edited(self, **fields: str) -> dict[str, str]:
        return edit_data(Task.objects.get(pk=self.task.pk), **fields)

    def test_a_step_without_an_entry_fills_in_the_tasks_substance(
            self) -> None:
        """Requirement: Inventory forms (the task's substance for a step
        without an entry, its task's batch)."""
        plain = make_task(self.kl, "Aspirin", steps=2, started=past(1),
                          batch="B-3")
        self.assertEqual(self.fields(plain.steps.get(position=2)), {
            "substance": "aspirin", "source": "made", "batch": "B-3",
            "made_on": TODAY_ISO})


class LotFixityTests(StepLotCase):

    def test_the_step_is_fixed_once_the_lot_is_created(self) -> None:
        """Requirement: Bulk lots (the substance, source, unit and
        `task_step` are fixed once the lot is created)."""
        lot = make_lot(self.kl, substance=substance_for("4-acetylbiphenyl"),
                       task_step=self.first)
        self.client.post(lot_url(lot, "edit"), {
            "batch": "B-2", "location": "", "made_on": "", "note": "x",
            "task_step": str(self.second.pk)})
        lot = Lot.objects.get(pk=lot.pk)
        self.assertEqual((lot.batch, lot.task_step), ("B-2", self.first))

    def test_the_edit_form_does_not_offer_the_step(self) -> None:
        lot = make_lot(self.kl, substance=substance_for("4-acetylbiphenyl"),
                       task_step=self.first)
        root = page(self.client.get(lot_url(lot, "edit")))
        self.assertIsNone(root.find(("input", "select"), name="task_step"))


class LotPageTests(StepLotCase):

    def lot_made_by(self, step: TaskStep, **extra):
        return make_lot(self.kl, substance=substance_for(
            "4-acetylbiphenyl"), task_step=step, **extra)

    def test_the_page_links_the_task_of_the_step_that_made_the_lot(
            self) -> None:
        """Requirement: Bulk lot page (the step that made the lot,
        linking to its task)."""
        lot = self.lot_made_by(self.first)
        self.client.logout()
        root = page(self.client.get(lot_url(lot)))
        self.assertIn(task_url(self.task),
                      [a.get("href") for a in root.find_all("a")])
        self.assertIn(self.task.number, root.text())

    def test_a_lot_made_by_no_step_links_no_task_without_a_batch(
            self) -> None:
        lot = make_lot(self.kl, substance=substance_for(
            "4-acetylbiphenyl"))
        root = page(self.client.get(lot_url(lot)))
        self.assertNotIn(task_url(self.task),
                         [a.get("href") for a in root.find_all("a")])

    def test_the_task_is_named_as_made_on_another_day(self) -> None:
        lot = self.lot_made_by(self.first, made_on=date(2026, 11, 1))
        self.assertIn(self.task.number,
                      page(self.client.get(lot_url(lot))).text())


class BookedStepTests(StepCase):
    """The review's cases: steps with lots keep their chemistry, and an
    ended task keeps its product lot."""

    def test_a_sequence_with_a_lot_cannot_be_cleared(self) -> None:
        """Requirement: Task record (a sequence changes only while no
        step has made a lot or taken a withdrawal)."""
        task = self.follow()
        first = steps_of(task)[0]
        make_lot(task.created_by, substance=first.entry.substances.filter(
            role="product").first().substance, source="made",
            task_step=first, amount="2", unit="g")
        response = self.client.post(task_url(task, "edit"), edit_data(
            task, sequence="", steps_total="2"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("sequence", context_form(response).errors)
        self.assertEqual(steps_of(Task.objects.get())[0].entry_id,
                         first.entry_id)

    def test_the_batch_of_the_only_product_lot_stays(self) -> None:
        """Requirement: Inventory forms (a batch change that would leave
        an ended task without its product lot is refused)."""
        from .task_support import make_product_lot
        task = make_task(self.kl, substance="Aspirin", batch="B-7",
                         started=date(2026, 10, 1),
                         ended=date(2026, 10, 20))
        lot = make_product_lot(task)
        data = {"batch": "B-8", "location": "", "made_on": "", "note": ""}
        response = self.client.post(lot_url(lot, "edit"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("batch", context_form(response).errors)
        self.assertEqual(Lot.objects.get(pk=lot.pk).batch, "B-7")
        make_product_lot(task)
        response = self.client.post(lot_url(lot, "edit"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Lot.objects.get(pk=lot.pk).batch, "B-8")
