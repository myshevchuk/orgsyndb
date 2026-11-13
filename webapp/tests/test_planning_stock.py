"""Tests of starting a synthesis from stock (production-planning:
Starting from stock, Planning list)."""

from datetime import timedelta
from typing import Any

from planning.plan import Plan
from tasks.models import Task

from . import (field_value, load_demo_registry, make_demo_accounts,
               make_demo_notebooks, make_task, task_form_data)
from .collection_support import (accept, import_collection, longer_collection,
                                 reordered_collection, without_ids)
from .inventory_support import TODAY
from .planning_support import NEW_TASK, PLAN, PlanningCase, rows_by_article

ASA = "acetylsalicylic-acid"
CINNAMIC = "cinnamic-acid"


def key_of(value: Any) -> Any:
    """The key of a sequence or a substance, or None for None."""
    return getattr(value, "key", value)


class StockCase(PlanningCase):
    """The planning case with the demo registry and a collection that
    holds the demo's sequences and, for ``cinnamic-acid`` (article
    ``CH-0012``), the three-step ``SEQ-0003`` and the two-step
    ``SEQ-0004`` (``longer_collection``): the article of ``CH-0010``
    is made by ``SEQ-0001`` alone, whose intermediate is
    ``salicylic-acid``."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        load_demo_registry()
        make_demo_accounts()
        make_demo_notebooks()
        import_collection(longer_collection())

    def asa(self, quantity: int = 10) -> Any:
        """The item of the article ``CH-0010``, whose priority is high
        with ten containers."""
        return self.planned_item("CH-0010", quantity=quantity)

    def cinnamic(self, quantity: int = 10) -> Any:
        return self.planned_item("CH-0012", quantity=quantity)

    def stock(self, key: str, amount: str = "5", **extra: Any) -> Any:
        """An open lot of the substance ``key``, of ``amount`` g."""
        return self.lot(key, "g", amount, **extra)

    def starts(self, article: str = "CH-0010") -> list[tuple[Any, ...]]:
        """The ``starts`` of the article's row as (the sequence's key,
        step, the key of the intermediate or None)."""
        plan = Plan(TODAY)
        row = plan.row(plan.forecast(article))
        return [(key_of(sequence), step, key_of(intermediate))
                for sequence, step, intermediate in row.starts]

    def english(self) -> None:
        """Make the site English: an accepted English import, received
        after every other import."""
        from collection.models import Import
        record = accept(language="en")
        last = Import.objects.order_by("-received_at").first().received_at
        Import.objects.filter(pk=record.pk).update(
            received_at=last + timedelta(seconds=1))

    def actions(self, article: str = "CH-0010", signed_in: bool = True
                ) -> Any:
        root = self.get(PLAN + "?all=1", signed_in)
        return list(rows_by_article(root)[article].values())[-1]

    def new_task_links(self, article: str = "CH-0010",
                       signed_in: bool = True) -> list[str]:
        return [a.get("href") for a in self.actions(
            article, signed_in).find_all("a")
            if a.get("href", "").startswith(NEW_TASK)]


class StartStepTests(StockCase):
    """The step each proposed sequence starts at."""

    def test_a_stocked_intermediate_skips_a_step(self) -> None:
        """Requirement: Starting from stock (the last step whose
        preceding step's intermediate has an open lot)."""
        self.asa()
        self.stock("salicylic-acid")
        self.assertEqual(self.starts(), [("SEQ-0001", 2, "salicylic-acid")])

    def test_nothing_in_stock_starts_at_the_first_step(self) -> None:
        """Scenario: Nothing in stock (step 1 when no step has one; the
        intermediate is none)."""
        self.asa()
        self.assertEqual(self.starts(), [("SEQ-0001", 1, None)])

    def test_a_used_up_lot_does_not_count(self) -> None:
        """Requirement: Starting from stock (a lot whose amount is above
        zero)."""
        self.asa()
        self.stock("salicylic-acid", "0")
        self.assertEqual(self.starts(), [("SEQ-0001", 1, None)])

    def test_a_bought_lot_counts(self) -> None:
        """Requirement: Starting from stock (whatever its source)."""
        self.asa()
        self.stock("salicylic-acid", source="bought", supplier="ChemPur")
        self.assertEqual(self.starts(), [("SEQ-0001", 2, "salicylic-acid")])

    def test_any_one_open_lot_is_enough(self) -> None:
        """Requirement: Starting from stock (has an open lot)."""
        self.asa()
        self.stock("salicylic-acid", "0")
        self.stock("salicylic-acid", "0.001")
        self.assertEqual(self.starts(), [("SEQ-0001", 2, "salicylic-acid")])

    def test_a_lot_of_another_substance_does_not_count(self) -> None:
        """Requirement: Starting from stock (the intermediate of step
        `k - 1`, not any substance the sequence mentions)."""
        self.asa()
        self.stock("methyl-salicylate")
        self.stock("acetic-anhydride")
        self.assertEqual(self.starts(), [("SEQ-0001", 1, None)])

    def test_the_intermediate_is_the_first_product_the_next_step_takes(
            self) -> None:
        """Requirement: Starting from stock (the intermediate as
        Sequence continuity defines it: the first of the step's
        products that the next step takes)."""
        import_collection(reordered_collection())
        self.asa()
        self.stock("salicylic-acid")
        self.assertEqual(self.starts(), [("SEQ-0001", 1, None)])
        self.stock("acetic-anhydride")
        self.assertEqual(self.starts(),
                         [("SEQ-0001", 2, "acetic-anhydride")])

    def test_a_sequence_of_another_target_is_not_proposed(self) -> None:
        """Requirement: Starting from stock (each sequence whose target
        is the article's substance)."""
        self.asa()
        self.stock("4-acetylbiphenyl")
        self.stock("ethyl-cinnamate")
        self.assertEqual(self.starts(), [("SEQ-0001", 1, None)])

    def test_a_withdrawn_sequence_is_not_proposed(self) -> None:
        """Requirement: Starting from stock (each sequence that is not
        withdrawn); Requirement: Planning list (when it proposes none,
        the plain action)."""
        import_collection(without_ids("SEQ-0001"))
        self.asa()
        self.stock("salicylic-acid")
        self.assertEqual(self.starts(), [])
        self.assertEqual(self.new_task_links(),
                         [NEW_TASK + f"?substance={ASA}"])

    def test_an_article_no_sequence_makes_has_no_start(self) -> None:
        """Requirement: Planning list (no sequence targets the
        substance)."""
        self.planned_item("NV-1", quantity=10)
        self.assertEqual(self.starts("NV-1"), [])

    def test_the_proposals_come_in_the_order_of_the_ids(self) -> None:
        """Requirement: Starting from stock (each sequence, in order of
        ID)."""
        self.cinnamic()
        self.assertEqual(self.starts("CH-0012"),
                         [("SEQ-0003", 1, None), ("SEQ-0004", 1, None)])

    def test_the_latest_step_with_a_lot_is_proposed(self) -> None:
        """Requirement: Starting from stock (the last step `k`)."""
        self.cinnamic()
        self.stock("benzaldehyde")
        self.assertEqual(self.starts("CH-0012"), [
            ("SEQ-0003", 2, "benzaldehyde"), ("SEQ-0004", 1, None)])
        self.stock("ethyl-cinnamate")
        self.assertEqual(self.starts("CH-0012"), [
            ("SEQ-0003", 3, "ethyl-cinnamate"),
            ("SEQ-0004", 2, "ethyl-cinnamate")])

    def test_a_later_intermediate_alone_skips_the_earlier_steps(
            self) -> None:
        """Requirement: Starting from stock (the last step `k` such that
        the intermediate of step `k - 1` has an open lot, whether or
        not an earlier one has)."""
        self.cinnamic()
        self.stock("ethyl-cinnamate")
        self.assertEqual(self.starts("CH-0012"), [
            ("SEQ-0003", 3, "ethyl-cinnamate"),
            ("SEQ-0004", 2, "ethyl-cinnamate")])

    def test_the_target_itself_is_not_an_intermediate(self) -> None:
        """Requirement: Starting from stock (the intermediate of a step
        before the last, not the target)."""
        self.cinnamic()
        self.stock(CINNAMIC)
        self.assertEqual(self.starts("CH-0012"), [
            ("SEQ-0003", 1, None), ("SEQ-0004", 1, None)])

    def test_plan_synthesis_stays_a_flag(self) -> None:
        """Requirement: Planning list (the synthesis action is offered
        when the priority is high or medium, no task is planned or
        running and every open lot converts)."""
        self.asa()
        self.stock("salicylic-acid")
        plan = Plan(TODAY)
        row = plan.row(plan.forecast("CH-0010"))
        self.assertIs(row.plan_synthesis, True)
        self.assertEqual(len(row.starts), 1)
        make_task(self.kl, substance=ASA)
        plan = Plan(TODAY)
        self.assertIs(plan.row(plan.forecast("CH-0010")).plan_synthesis,
                      False)


class ActionTests(StockCase):
    """The synthesis action of the planning list."""

    def test_a_stocked_intermediate_names_the_step(self) -> None:
        """Scenario: A stocked intermediate skips a step."""
        self.asa()
        self.stock("salicylic-acid")
        cell = self.actions()
        self.assertIn(
            "Synthese planen über SEQ-0001 ab Stufe 2, Salicylsäure "
            "vorrätig", cell.text())
        self.assertEqual(self.new_task_links(), [
            NEW_TASK + f"?substance={ASA}&sequence=SEQ-0001&start_step=2"])

    def test_nothing_in_stock_names_the_sequence_alone(self) -> None:
        """Scenario: Nothing in stock."""
        self.asa()
        self.stock("salicylic-acid", "0")
        text = self.actions().text()
        self.assertIn("Synthese planen über SEQ-0001", text)
        self.assertNotIn("ab Stufe", text)
        self.assertNotIn("vorrätig", text)
        self.assertEqual(self.new_task_links(), [
            NEW_TASK + f"?substance={ASA}&sequence=SEQ-0001&start_step=1"])

    def test_the_english_text(self) -> None:
        """Requirement: Planning list (`Plan synthesis via <ID> from
        step <k>, <name> in stock`)."""
        self.english()
        self.asa()
        self.stock("salicylic-acid")
        self.assertIn(
            "Plan synthesis via SEQ-0001 from step 2, Salicylic acid in "
            "stock", self.actions().text())

    def test_the_english_text_without_stock(self) -> None:
        """Requirement: Planning list (`Plan synthesis via <ID>`)."""
        self.english()
        self.asa()
        text = self.actions().text()
        self.assertIn("Plan synthesis via SEQ-0001", text)
        self.assertNotIn("from step", text)

    def test_each_sequence_has_its_own_action_in_the_order_of_the_ids(
            self) -> None:
        """Requirement: Planning list (for each sequence that Starting
        from stock proposes)."""
        self.cinnamic()
        self.stock("ethyl-cinnamate")
        text = self.actions("CH-0012").text()
        name = "(E)-Zimtsäureethylester vorrätig"
        first = f"Synthese planen über SEQ-0003 ab Stufe 3, {name}"
        second = f"Synthese planen über SEQ-0004 ab Stufe 2, {name}"
        self.assertIn(first, text)
        self.assertIn(second, text)
        self.assertLess(text.index(first), text.index(second))
        self.assertEqual(self.new_task_links("CH-0012"), [
            NEW_TASK + f"?substance={CINNAMIC}&sequence=SEQ-0003"
            "&start_step=3",
            NEW_TASK + f"?substance={CINNAMIC}&sequence=SEQ-0004"
            "&start_step=2"])

    def test_the_action_is_not_a_link_for_a_visitor(self) -> None:
        """Requirement: Planning list (linking for a signed-in user)."""
        self.asa()
        self.stock("salicylic-acid")
        cell = self.actions(signed_in=False)
        self.assertIn("Synthese planen über SEQ-0001 ab Stufe 2",
                      cell.text())
        self.assertEqual(self.new_task_links(signed_in=False), [])

    def test_a_task_under_way_stops_the_offer(self) -> None:
        """Requirement: Planning list (no matching task is planned or
        running)."""
        self.asa()
        self.stock("salicylic-acid")
        self.assertIn("ab Stufe 2", self.actions().text())
        make_task(self.kl, substance=ASA)
        self.assertNotIn("Synthese planen", self.actions().text())

    def test_a_low_priority_stops_the_offer(self) -> None:
        """Requirement: Planning list (the priority is high or
        medium)."""
        self.asa()
        self.stock("salicylic-acid")
        self.assertIn("ab Stufe 2", self.actions().text())
        self.parameters(high_days=5, medium_days=10)
        self.assertNotIn("Synthese planen", self.actions().text())


class FormFromListTests(StockCase):
    """The new-task form the action leads to."""

    def test_the_form_is_filled_in_and_saves_a_task_of_the_article(
            self) -> None:
        """Scenario: Created task matches its article (with the
        sequence and the step the action names)."""
        self.asa()
        self.stock("salicylic-acid")
        (link,) = self.new_task_links()
        form = self.get(link, signed_in=True)
        data = {name: field_value(form, name) for name in (
            "substance", "sequence", "start_step")}
        self.assertEqual(data, {"substance": ASA, "sequence": "SEQ-0001",
                                "start_step": "2"})
        done = self.client.post(NEW_TASK, task_form_data(**data))
        self.assertEqual(done.status_code, 302)
        task = Task.objects.get()
        self.assertEqual((task.sequence.key, task.start_step), (
            "SEQ-0001", 2))
        row = rows_by_article(self.get(PLAN + "?all=1", True))["CH-0010"]
        self.assertIn(task.number, row["Aufgaben"].text())
        self.assertNotIn("Synthese planen", row["Maßnahmen"].text())
