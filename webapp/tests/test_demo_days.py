"""Tests of the demo data's levels and planning on each seeding day
(lab-demo: Demo inventory "Levels on any seeding day", Demo planning
"Any seeding day")."""

from typing import Any

from . import table
from .demo_support import (ITEMS, LEVELS, NUMBERLESS, PLAN, SEEDING_DAYS,
                           SeededCase)
from .planning_support import priority_of, rows_by_article, task_texts

LISTED = {"CH-0012", "CH-0013", "CH-0010", "CH-0016", "NV-0007"}
ALSO_WITH_ALL = {"CH-0001", "CH-0002"}
LATE = "verspätet"
PLAN_SYNTHESIS = "Synthese planen"
CHECK_BULK = "Bulk prüfen"
FILL = "Abfüllen "
ROUGH = "grob"
# Days a slack keeps from the edges of its priority band.
MARGIN = 10


class DayChecks:
    """The checks of one seeding day; mixed into a SeededCase per day."""

    def rows(self: Any, query: str = "") -> dict[str, Any]:
        return rows_by_article(self.get(PLAN + query))

    def priority(self: Any, row: Any) -> str:
        return priority_of(row)

    def tasks(self: Any, row: Any) -> list[Any]:
        """The tasks the row lists, each with the text of its line."""
        from tasks.models import Task
        return [(Task.objects.get(number=number), text)
                for number, text in task_texts(row["Aufgaben"]).items()]

    def test_listed_articles(self: Any) -> None:
        rows = set(self.rows())
        self.assertLessEqual(LISTED, rows)
        self.assertFalse(rows & ALSO_WITH_ALL)

    def test_all_articles(self: Any) -> None:
        rows = self.rows("?all=1")
        self.assertLessEqual(LISTED | ALSO_WITH_ALL, set(rows))
        self.assertNotIn(None, rows)
        self.assertNotIn(NUMBERLESS[0], self.get(PLAN + "?all=1").text())

    def test_ch_0012(self: Any) -> None:
        from tasks.models import State
        row = self.rows()["CH-0012"]
        self.assertEqual(self.priority(row), "high")
        self.assertTrue(any(task.state == State.RUNNING and LATE in text
                            for task, text in self.tasks(row)))
        self.assertNotIn(ROUGH, row["Reichweite"].text())

    def test_ch_0013(self: Any) -> None:
        row = self.rows()["CH-0013"]
        self.assertEqual(self.priority(row), "high")
        self.assertEqual(self.tasks(row), [])
        self.assertIn(PLAN_SYNTHESIS, row["Maßnahmen"].text())

    def test_ch_0010(self: Any) -> None:
        from tasks.models import State
        row = self.rows()["CH-0010"]
        self.assertEqual(self.priority(row), "medium")
        self.assertTrue(any(task.state == State.PLANNED
                            and task.sequence is not None
                            and task.sequence.key == "SEQ-0001"
                            for task, _text in self.tasks(row)))
        self.assertNotIn(PLAN_SYNTHESIS, row["Maßnahmen"].text())

    def stocked_actions(self: Any) -> Any:
        """The actions of the row of ``CH-0010`` for a signed-in user
        once its planned task is cancelled."""
        from tasks.models import Task
        self.client.force_login(self.account("klehmann"))
        Task.objects.filter(sequence__key="SEQ-0001", started=None,
                            ended=None, cancelled=False).update(
                                cancelled=True)
        return self.rows()["CH-0010"]["Maßnahmen"]

    def test_ch_0010_offers_a_synthesis_from_stock(self: Any) -> None:
        """Scenario: A stocked intermediate skips a step (the demo
        data set, its planned task of `SEQ-0001` cancelled)."""
        cell = self.stocked_actions()
        self.assertIn("Synthese planen über SEQ-0001 ab Stufe 2, "
                      "Salicylsäure vorrätig", cell.text())
        self.assertEqual(
            [a.get("href") for a in cell.find_all("a")
             if a.get("href", "").startswith("/lab/tasks/new/")],
            ["/lab/tasks/new/?substance=acetylsalicylic-acid"
             "&sequence=SEQ-0001&start_step=2"])

    def test_ch_0010_offers_the_first_step_without_stock(self: Any
                                                          ) -> None:
        """Scenario: Nothing in stock (every salicylic-acid vessel at
        zero)."""
        from inventory.models import Vessel
        self.stocked_actions()
        Vessel.objects.filter(batch__substance__key="salicylic-acid"
                              ).update(amount=0)
        cell = self.rows()["CH-0010"]["Maßnahmen"]
        self.assertIn("Synthese planen über SEQ-0001", cell.text())
        self.assertNotIn("ab Stufe", cell.text())
        self.assertEqual(
            [a.get("href") for a in cell.find_all("a")
             if a.get("href", "").startswith("/lab/tasks/new/")],
            ["/lab/tasks/new/?substance=acetylsalicylic-acid"
             "&sequence=SEQ-0001&start_step=1"])

    def test_ch_0016(self: Any) -> None:
        row = self.rows()["CH-0016"]
        self.assertEqual(self.priority(row), "low")
        self.assertIn(FILL, row["Maßnahmen"].text())

    def test_nv_0007(self: Any) -> None:
        row = self.rows()["NV-0007"]
        actions = row["Maßnahmen"].text()
        self.assertIn(CHECK_BULK, actions)
        self.assertNotIn(PLAN_SYNTHESIS, actions)

    def test_ch_0001_and_ch_0002(self: Any) -> None:
        from tasks.models import State
        rows = self.rows("?all=1")
        self.assertEqual(self.priority(rows["CH-0001"]), "low")
        self.assertIn(ROUGH, rows["CH-0001"]["Reichweite"].text())
        self.assertEqual(self.priority(rows["CH-0002"]), "low")
        running = [(task, text) for task, text in self.tasks(rows["CH-0002"])
                   if task.state == State.RUNNING]
        self.assertTrue(running)
        self.assertFalse(any(LATE in text for _task, text in running))

    def test_the_position_without_a_number_has_no_forecast(
            self: Any) -> None:
        items = self.items(None)
        self.assertEqual([item.article.substance.key for item in items],
                         [NUMBERLESS[1]])
        self.assertEqual([item.article.substance.name for item in items],
                         [NUMBERLESS[0]])
        for item in items:
            with self.subTest(item=str(item)):
                text = self.get(f"/lab/inventory/items/{item.pk}/").text()
                self.assertIn("Kein Verbrauch, keine Prognose.", text)

    def test_no_flask_of_a_closed_task_holds_an_amount(self: Any) -> None:
        """Requirement: Demo tasks and parameters (no flask of a task
        that is ended, failed or cancelled holding an amount), on every
        seeding day."""
        from inventory.models import Vessel
        from tasks.models import State
        for flask in Vessel.objects.filter(flask=True).select_related(
                "batch__task_step__task"):
            task = flask.batch.task_step.task
            if task.state in (State.ENDED, State.FAILED, State.CANCELLED):
                self.assertEqual(flask.amount, 0, (flask.pk, task.number))

    def test_every_filling_names_a_vessel(self: Any) -> None:
        """Requirement: Demo inventory (fillings, each from a vessel and
        naming its movement), on every seeding day."""
        from inventory.models import Movement
        for filling in Movement.objects.filter(kind="filling"):
            self.assertIsNotNone(filling.vessel_movement, filling.pk)

    def test_slack_lies_well_inside_its_band(self: Any) -> None:
        """Each article's slack lies at least ten days inside the band of
        its priority, and the late task's slack is below minus ten, so
        that another seeding day does not move it across."""
        from planning.plan import Plan
        plan = Plan(self.DAY)
        bands = {"high": (None, 14), "medium": (14, 56), "low": (56, None)}
        for article in LISTED - {"NV-0007"} | ALSO_WITH_ALL:
            found = plan.forecast(article)
            low, high = bands[found.priority]
            with self.subTest(article=article):
                if low is not None:
                    self.assertGreaterEqual(found.slack - low, MARGIN)
                if high is not None:
                    self.assertGreaterEqual(high - found.slack, MARGIN)
        late = [line for line in plan.task_lines(plan.forecast("CH-0012"))
                if line.late]
        self.assertTrue(late)
        self.assertTrue(all(plan.task_slack(line.task) < -MARGIN
                            for line in late))

    def test_levels(self: Any) -> None:
        header, rows = table(self.get(ITEMS))
        cells = [row["Bestand"] for row in rows]
        classes = [cell.classes for cell in cells]
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertTrue(any(f"level-{level}" in found
                                    for found in classes))
        self.assertTrue(all(any(name.startswith("level-")
                                for name in found)
                            for found in classes))


for _day in SEEDING_DAYS:
    _name = f"Seeded{_day:%Y%m%d}Tests"
    globals()[_name] = type(_name, (DayChecks, SeededCase),
                            {"DAY": _day, "__module__": __name__})
del _day, _name
