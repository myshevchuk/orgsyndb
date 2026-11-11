"""Tests of the computed priority on the task list, the task page and the
task form (task-tracker: Task list, Task page, Task forms;
production-planning: Computed priority on tasks)."""

from datetime import date, timedelta

from . import (build_index, field_value, make_task, numbers, substance_for,
               table, task_form_data, task_url)
from .inventory_support import TODAY
from .planning_support import (PLAN, PlanningCase, article_links, count_days,
                               has_date, has_days, metadata, titles)

NEW = "/lab/tasks/new/"
HELP_DE = "Gilt, solange keine Prognose die Priorität berechnet."
HELP_EN = "Applies while no forecast computes the priority."
NO_FORECAST_DE = "Kein Verbrauch, keine Prognose."
NO_FORECAST_EN = "No consumption, no forecast."


class TasksCase(PlanningCase):
    """An article NV-1 of 10 containers: slack 11.65 days, priority high;
    its time is 21 days by default."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def listing(self, query: str = ""):
        return self.get("/lab/tasks/" + query)

    def rows(self, query: str = ""):
        header, rows = table(self.listing(query))
        return {row[header[0]].text(): row for row in rows}

    def shown(self, query: str = "") -> list[str]:
        return numbers(self.listing(query))


class ListPriorityTests(TasksCase):

    def setUp(self) -> None:
        super().setUp()
        self.computed = make_task(self.kl, substance="NV-1", priority="low")
        self.running_entered = make_task(
            self.kl, substance="Aspirin", priority="high",
            started=TODAY - timedelta(days=3))
        self.medium = make_task(self.kl, substance="Aspirin",
                                priority="medium")

    def test_computed_over_entered(self) -> None:
        """Scenario: Computed over entered."""
        self.assertEqual(
            self.shown(), [self.computed.number,
                           self.running_entered.number,
                           self.medium.number])
        self.assertEqual(
            self.shown("?priority=high"),
            [self.computed.number, self.running_entered.number])
        cell = self.rows()[self.computed.number]["Priorität"]
        self.assertIn("hoch", cell.text())
        self.assertIn("berechnet", cell.text())
        self.assertNotIn("manuell", cell.text())
        self.assertIn("11 Tage", titles(cell))

    def test_the_other_tasks_show_the_entered_priority(self) -> None:
        rows = self.rows()
        for task, label in ((self.running_entered, "hoch"),
                            (self.medium, "mittel")):
            with self.subTest(task=task.number):
                cell = rows[task.number]["Priorität"]
                self.assertIn(label, cell.text())
                self.assertIn("manuell", cell.text())
                self.assertNotIn("berechnet", cell.text())

    def test_an_ended_task_keeps_its_entered_priority(self) -> None:
        """Scenario: Ended task keeps its entered priority."""
        ended = make_task(self.kl, substance="NV-1", priority="low",
                          started=date(2026, 9, 1), ended=date(2026, 9, 20),
                          report=True, qc_list=True)
        cell = self.rows("?state=all")[ended.number]["Priorität"]
        self.assertIn("niedrig", cell.text())
        self.assertIn("manuell", cell.text())
        self.assertNotIn("berechnet", cell.text())

    def test_a_cancelled_task_keeps_its_entered_priority(self) -> None:
        cancelled = make_task(self.kl, substance="NV-1", priority="low",
                              cancelled=True)
        cell = self.rows("?state=cancelled")[cancelled.number]["Priorität"]
        self.assertIn("niedrig", cell.text())
        self.assertIn("manuell", cell.text())

    def test_a_running_task_has_the_priority_of_its_own_slack(self) -> None:
        running = self.running("NV-1", 14, priority="low")
        cell = self.rows()[running.number]["Priorität"]
        self.assertIn("mittel", cell.text())
        self.assertIn("berechnet", cell.text())
        self.assertIn("25 Tage", titles(cell))

    def test_a_substance_without_demand_keeps_its_entered_priority(
            self) -> None:
        self.item("NV-0", size="1", unit="mg", quantity=3)
        task = make_task(self.kl, substance="NV-0", priority="low")
        cell = self.rows()[task.number]["Priorität"]
        self.assertIn("niedrig", cell.text())
        self.assertIn("manuell", cell.text())

    def test_the_english_marks_and_title(self) -> None:
        self.use_index(build_index("en"))
        rows = self.rows()
        cell = rows[self.computed.number]["Priority"]
        self.assertIn("high", cell.text())
        self.assertIn("computed", cell.text())
        self.assertIn("11 days", titles(cell))
        entered = rows[self.medium.number]["Priority"]
        self.assertIn("medium", entered.text())
        self.assertIn("entered", entered.text())


class PriorityFilterTests(TasksCase):

    def test_the_filter_compares_the_computed_priority(self) -> None:
        computed = make_task(self.kl, substance="NV-1", priority="low")
        entered_low = make_task(self.kl, substance="Aspirin", priority="low")
        self.assertEqual(self.shown("?priority=high"), [computed.number])
        self.assertEqual(self.shown("?priority=low"), [entered_low.number])
        self.assertEqual(self.shown("?priority=medium"), [])

    def test_a_computed_medium_is_found_under_medium(self) -> None:
        running = self.running("NV-1", 14, priority="high")
        self.assertEqual(self.shown("?priority=medium"), [running.number])
        self.assertEqual(self.shown("?priority=high"), [])

    def test_an_ended_task_is_found_by_its_entered_priority(self) -> None:
        ended = make_task(self.kl, substance="NV-1", priority="low",
                          started=date(2026, 9, 1), ended=date(2026, 9, 20))
        self.assertEqual(self.shown("?state=ended&priority=low"),
                         [ended.number])
        self.assertEqual(self.shown("?state=ended&priority=high"), [])

    def test_the_form_keeps_the_value(self) -> None:
        self.assertEqual(
            field_value(self.listing("?priority=high"), "priority"), "high")


class ListOrderTests(PlanningCase):
    """Rows go by computed or entered priority, then by slack, tasks
    without one last, then by state, start date and number."""

    def setUp(self) -> None:
        super().setUp()
        for quantity in (5, 10, 15):
            self.planned_item(f"NV-{quantity}", quantity=quantity)

    def shown(self, query: str = "") -> list[str]:
        return numbers(self.get("/lab/tasks/" + query))

    def test_the_smaller_slack_comes_first(self) -> None:
        """NV-10 has a slack of 11.65 days, NV-5 one of -24.3."""
        ten = make_task(self.kl, substance="NV-10")
        five = make_task(self.kl, substance="NV-5")
        self.assertEqual(self.shown(), [five.number, ten.number])

    def test_a_task_without_a_slack_comes_after_those_with_one(self) -> None:
        entered = make_task(self.kl, substance="Aspirin", priority="high")
        ten = make_task(self.kl, substance="NV-10", priority="low")
        five = make_task(self.kl, substance="NV-5", priority="low")
        self.assertEqual(self.shown(),
                         [five.number, ten.number, entered.number])

    def test_the_priority_comes_before_the_slack(self) -> None:
        fifteen = make_task(self.kl, substance="NV-15")
        entered = make_task(self.kl, substance="Aspirin", priority="high")
        self.assertEqual(self.shown(), [entered.number, fifteen.number])
        ten = make_task(self.kl, substance="NV-10")
        self.assertEqual(self.shown(),
                         [ten.number, entered.number, fifteen.number])

    def test_a_computed_low_comes_after_an_entered_medium(self) -> None:
        self.planned_item("NV-25", quantity=25)
        low = make_task(self.kl, substance="NV-25", priority="high")
        medium = make_task(self.kl, substance="Aspirin", priority="medium")
        self.assertEqual(self.shown(), [medium.number, low.number])

    def test_equal_slack_goes_by_state(self) -> None:
        """A task that starts today needs the whole time, as a planned
        one does."""
        planned = make_task(self.kl, substance="NV-10")
        running = make_task(self.kl, substance="NV-10", started=TODAY)
        self.assertEqual(self.shown(), [running.number, planned.number])

    def test_equal_slack_then_goes_by_start_date_then_number(self) -> None:
        """Two tasks started more than the synthesis time ago have no
        time left; their slack is the same."""
        late = make_task(self.kl, substance="NV-10",
                         started=TODAY - timedelta(days=30))
        early = make_task(self.kl, substance="NV-10",
                          started=TODAY - timedelta(days=40))
        same = make_task(self.kl, substance="NV-10",
                         started=TODAY - timedelta(days=40))
        self.assertEqual(self.shown(),
                         [early.number, same.number, late.number])

    def test_a_planned_task_outranks_a_running_one_of_the_same_article(
            self) -> None:
        """Its slack is smaller: the running task has done some of its
        work."""
        running = make_task(self.kl, substance="NV-15",
                            started=TODAY - timedelta(days=4))
        planned = make_task(self.kl, substance="NV-15")
        self.assertEqual(self.shown(), [planned.number, running.number])

    def test_tasks_of_entered_priority_keep_the_old_order(self) -> None:
        cancelled = make_task(self.kl, substance="Aspirin", cancelled=True)
        ended = make_task(self.kl, substance="Aspirin",
                          started=date(2026, 9, 1), ended=date(2026, 9, 2))
        planned = make_task(self.kl, substance="Aspirin")
        running = make_task(self.kl, substance="Aspirin",
                            started=date(2026, 9, 1))
        self.assertEqual(
            self.shown("?state=all"),
            [running.number, planned.number, ended.number,
             cancelled.number])


class PagePriorityTests(TasksCase):

    def test_computed_priority_on_the_page(self) -> None:
        task = make_task(self.kl, substance="NV-1", priority="low")
        cell = metadata(self.get(task_url(task)))["Priorität"]
        self.assertIn("hoch", cell.text())
        self.assertIn("berechnet", cell.text())
        self.assertIn("11 Tage", titles(cell))

    def test_entered_priority_on_the_page(self) -> None:
        task = make_task(self.kl, substance="Aspirin", priority="low")
        cell = metadata(self.get(task_url(task)))["Priorität"]
        self.assertIn("niedrig", cell.text())
        self.assertIn("manuell", cell.text())
        self.assertNotIn("berechnet", cell.text())

    def test_an_ended_task_shows_its_entered_priority(self) -> None:
        task = make_task(self.kl, substance="NV-1", priority="low",
                         started=date(2026, 9, 1), ended=date(2026, 9, 20))
        cell = metadata(self.get(task_url(task)))["Priorität"]
        self.assertIn("niedrig", cell.text())
        self.assertIn("manuell", cell.text())

    def test_the_english_page(self) -> None:
        self.use_index(build_index("en"))
        task = make_task(self.kl, substance="NV-1", priority="low")
        cell = metadata(self.get(task_url(task)))["Priority"]
        self.assertIn("computed", cell.text())
        self.assertIn("11 days", titles(cell))


class PageForecastTests(TasksCase):

    def test_forecast_of_the_substance(self) -> None:
        """Scenario: Forecast of the substance."""
        task = make_task(self.kl, substance="NV-1")
        root = self.get(task_url(task))
        links = article_links(root)
        self.assertEqual([a.text() for a in links], ["NV-1"])
        self.assertEqual([a.get("href") for a in links], [PLAN])
        text = root.text()
        self.assertTrue(has_days(text, 60), text)
        self.assertTrue(has_days(text, 21), text)
        self.assertTrue(has_date(text, date(2026, 11, 15)), text)
        self.assertEqual(count_days(text, 11), 2, text)

    def test_the_slack_of_a_running_task_is_its_own(self) -> None:
        task = self.running("NV-1", 14)
        text = self.get(task_url(task)).text()
        self.assertEqual(count_days(text, 11), 1, text)
        self.assertTrue(has_days(text, 25), text)
        self.assertNotIn("verspätet", text)

    def test_a_late_task_is_marked(self) -> None:
        self.planned_item("NV-5", quantity=5)
        task = make_task(self.kl, substance="NV-5")
        self.assertIn("verspätet", self.get(task_url(task)).text())
        running = self.running("NV-5", 3)
        self.assertIn("verspätet", self.get(task_url(running)).text())

    def test_a_task_in_time_is_not_marked(self) -> None:
        task = make_task(self.kl, substance="NV-1")
        self.assertNotIn("verspätet", self.get(task_url(task)).text())

    def test_an_ended_task_shows_the_article_and_no_slack_of_its_own(
            self) -> None:
        self.planned_item("NV-5", quantity=5)
        task = make_task(self.kl, substance="NV-5", started=date(2026, 9, 1),
                         ended=date(2026, 9, 20), report=True, qc_list=True)
        text = self.get(task_url(task)).text()
        self.assertTrue(has_days(text, 24), text)
        self.assertNotIn("verspätet", text)

    def test_the_english_page(self) -> None:
        self.use_index(build_index("en"))
        self.planned_item("NV-5", quantity=5)
        task = make_task(self.kl, substance="NV-5")
        text = self.get(task_url(task)).text()
        self.assertIn("late", text)
        self.assertTrue(has_days(text, 24), text)

    def test_an_article_without_a_forecast(self) -> None:
        self.item("NV-0", size="1", unit="mg", quantity=3)
        task = make_task(self.kl, substance="NV-0")
        root = self.get(task_url(task))
        self.assertIn(NO_FORECAST_DE, root.text())
        links = article_links(root)
        self.assertEqual([a.text() for a in links], ["NV-0"])
        self.assertNotIn("Tage", root.text())

    def test_the_english_text_without_a_forecast(self) -> None:
        self.use_index(build_index("en"))
        self.item("NV-0", size="1", unit="mg", quantity=3)
        task = make_task(self.kl, substance="NV-0")
        self.assertIn(NO_FORECAST_EN, self.get(task_url(task)).text())

    def test_a_substance_without_an_article(self) -> None:
        task = make_task(self.kl, substance="Aspirin")
        root = self.get(task_url(task))
        self.assertNotIn(NO_FORECAST_DE, root.text())
        self.assertEqual(article_links(root), [])


class FormTests(TasksCase):

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.kl)

    def test_the_priority_field_says_when_it_applies(self) -> None:
        task = make_task(self.kl, substance="Aspirin")
        for path in (NEW, task_url(task, "edit")):
            with self.subTest(path=path):
                root = self.get(path)
                self.assertIn(HELP_DE, root.text())
                help_text = root.find(cls="lab-help", id="id_priority_"
                                                         "helptext")
                self.assertIsNotNone(help_text)
                self.assertEqual(help_text.text(), HELP_DE)

    def test_the_english_help_text(self) -> None:
        self.use_index(build_index("en"))
        self.assertIn(HELP_EN, self.get(NEW).text())

    def test_substance_from_the_query(self) -> None:
        """Scenario: Substance from the query."""
        root = self.get(NEW + "?substance=cinnamic-acid")
        self.assertEqual(field_value(root, "substance"), "cinnamic-acid")

    def test_without_a_query_the_substance_is_empty(self) -> None:
        self.assertIn(field_value(self.get(NEW), "substance"), (None, ""))

    def test_a_substance_with_special_characters(self) -> None:
        root = self.get(NEW + "?substance=A%26B+%22x%22")
        self.assertEqual(field_value(root, "substance"), 'A&B "x"')

    def test_the_form_saves_the_substance_from_its_field(self) -> None:
        from tasks.models import Task
        substance_for("NV-1")
        done = self.client.post(NEW + "?substance=cinnamic-acid",
                                task_form_data(substance="nv-1"))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(Task.objects.get().substance.key, "nv-1")

    def test_other_fields_keep_their_defaults(self) -> None:
        root = self.get(NEW + "?substance=cinnamic-acid")
        self.assertEqual(field_value(root, "priority"), "medium")
