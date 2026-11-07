"""Tests of the demo data's levels and planning on each seeding day
(lab-demo: Demo inventory "Levels on any seeding day", Demo planning
"Any seeding day")."""

from typing import Any

from . import table
from .demo_support import (ITEMS, LEVELS, NUMBERLESS, PLAN, SEEDING_DAYS,
                           SeededCase)

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

    def rows(self: Any, query: str = "") -> dict[str, dict[str, Any]]:
        header, rows = table(self.get(PLAN + query))
        return {row[header[0]].text(): row for row in rows}

    def priority(self: Any, row: dict[str, Any]) -> str:
        span = row["Priorität"].find("span", cls="priority")
        self.assertIsNotNone(span)
        return next(name.removeprefix("priority--")
                    for name in span.classes
                    if name.startswith("priority--"))

    def tasks(self: Any, row: dict[str, Any]) -> list[Any]:
        """The tasks the row lists, each with its line's text."""
        from tasks.models import Task
        found = []
        for line in row["Aufgaben"].find_all("li"):
            number = line.find("a").text()
            found.append((Task.objects.get(number=number), line.text()))
        return found

    def test_listed_articles(self: Any) -> None:
        self.assertEqual(set(self.rows()), LISTED)

    def test_all_articles(self: Any) -> None:
        rows = self.rows("?all=1")
        self.assertEqual(set(rows), LISTED | ALSO_WITH_ALL)
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
                            and task.sequence == "SEQ-0001"
                            for task, _text in self.tasks(row)))
        self.assertNotIn(PLAN_SYNTHESIS, row["Maßnahmen"].text())

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
        self.assertEqual([item.name for item in items], [NUMBERLESS[0]])
        for item in items:
            with self.subTest(item=str(item)):
                text = self.get(f"/lab/inventory/items/{item.pk}/").text()
                self.assertIn("Kein Verbrauch, keine Prognose.", text)

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
