"""Tests of the details of a task in the task list (task-tracker: Task
details; web-app: Main lists)."""

import re
from datetime import date
from typing import Any

from tasks.models import Task

from . import Element, make_task, page, past
from .main_lists_support import (body_of, cells, has_ancestor_class,
                                 headers_of, heading_of, HTMX, link_in,
                                 must_pane, pane_head, pane_widgets,
                                 record_tables, replaced, row_for,
                                 texts_of_links, unsorted_reasons)
from .task_support import StepCase, make_product_batch, steps_of
from .test_inventory_dialogs import current

TASKS = "/lab/tasks/"
OPEN_PAGE = "Aufgabenseite öffnen"
ISO = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")


def detail_url(task: Any) -> str:
    return f"{TASKS}{task.number}/detail/"


class TaskDetailsCase(StepCase):

    def listed(self, task: Any, query: str = "?state=all") -> Element:
        """The task list with ``selected`` naming TASK."""
        response = self.client.get(
            f"{TASKS}{query}&selected={task.number}")
        self.assertEqual(response.status_code, 200)
        return page(response)

    def details(self, task: Any, query: str = "?state=all") -> Element:
        found = must_pane(self.listed(task, query))
        self.assertIsNotNone(found, "the list has no #item-detail")
        self.assertEqual(found.get("data-item"), task.number)
        return found

    def sequenced(self) -> Any:
        """A task of ``SEQ-0002`` whose first step was done on
        2026-11-03."""
        task = self.follow("SEQ-0002")
        first = steps_of(task)[0]
        first.done_on = date(2026, 11, 3)
        first.save()
        return task

    def steps(self, found: Element) -> list[list[str]]:
        grids = [grid for grid in found.find_all("table")
                 if headers_of(grid) == ["Stufe", "Vorschrift", "Erledigt"]]
        self.assertEqual(len(grids), 1, "the pane has no steps table")
        return [[cell.text() for cell in cells(row)]
                for row in body_of(grids[0])]


class HeadAndWidgetsTests(TaskDetailsCase):

    def test_the_head_titles_the_task_and_the_data_is_in_widgets(
            self) -> None:
        task = self.sequenced()
        found = self.details(task)
        head = pane_head(found)
        self.assertIsNotNone(head, "the pane has no head")
        title = head.find("h2", id="item-detail-title")
        self.assertIsNotNone(title, "the head has no title")
        self.assertEqual(title.find("a").get("href"),
                         f"{TASKS}{task.number}/")
        self.assertTrue(pane_widgets(found))
        for each in pane_widgets(found):
            self.assertIsNotNone(each.find(cls="widget__head").find("h3"))
        for grid in record_tables(found):
            self.assertIsNotNone(has_ancestor_class(grid, "widget"))


class DetailsOfATaskTests(TaskDetailsCase):

    def test_details_of_a_task(self) -> None:
        """Scenario: Details of a task."""
        task = self.sequenced()
        self.client.logout()
        found = self.details(task)
        heading = heading_of(found)
        self.assertIn(task.number, heading.text())
        self.assertIn(task.substance.name, heading.text())
        self.assertEqual(link_in(heading).get("href"),
                         f"{TASKS}{task.number}/")
        self.assertEqual(self.steps(found), [
            ["1", "OSDB-0004", "03.11.2026"],
            ["2", "OSDB-0009 Eintrag 1", ""]])
        links = texts_of_links(found)
        self.assertEqual(links["OSDB-0004"], "/procedures/osdb-0004/")
        self.assertEqual(links["OSDB-0009"], "/procedures/osdb-0009/")
        self.assertEqual(links[OPEN_PAGE], f"{TASKS}{task.number}/")
        self.assertNotIn("Bearbeiten", links)

    def test_a_signed_in_user_may_edit(self) -> None:
        task = self.sequenced()
        links = texts_of_links(self.details(task))
        self.assertEqual(links["Bearbeiten"], f"{TASKS}{task.number}/edit/")

    def test_the_state_the_priority_and_the_progress(self) -> None:
        task = self.sequenced()
        root = self.listed(task)
        row = row_for(root, task.number)
        priority = cells(row)[2].text()
        self.assertTrue(priority)
        text = must_pane(root).text()
        self.assertIn(priority, text)
        self.assertIn("1/2", text)
        badge = must_pane(root).find(cls=f"badge--{task.state}")
        self.assertIsNotNone(badge)
        self.assertEqual(badge.text(), task.state_label)

    def test_a_task_that_needs_follow_up_says_so(self) -> None:
        task = make_task(self.kl, "Aspirin", started=past(1), ended=past(2),
                         qc_list=True)
        self.assertIn("Nacharbeit", self.details(task).text())
        done = make_task(self.kl, "Aspirin", started=past(1), ended=past(2),
                         report=True, qc_list=True)
        self.assertNotIn("Nacharbeit", self.details(done).text())

    def test_the_flags_read_yes_or_no(self) -> None:
        task = make_task(self.kl, "Aspirin", report=True, qc_list=False)
        text = self.details(task).text()
        self.assertRegex(text, r"(?<!\w)ja(?!\w)")
        self.assertRegex(text, r"(?<!\w)nein(?!\w)")

    def test_the_assignee_the_dates_and_the_note(self) -> None:
        task = make_task(self.kl, "Aspirin", assignee=self.ae,
                         started=past(1), ended=past(2), note="Rührt gut")
        text = self.details(task).text()
        for shown in ("AE", "01.03.2025", "02.03.2025", "Rührt gut"):
            self.assertIn(shown, text)

    def test_each_field_without_a_value_reads_a_dash(self) -> None:
        task = make_task(self.kl, "Aspirin")
        found = self.details(task)
        self.assertGreaterEqual(found.text().count("–"), 4)
        self.assertEqual(record_tables(found), [])

    def test_the_product_batches_link_their_pages(self) -> None:
        task = make_task(self.kl, "Aspirin", steps=1)
        batch = make_product_batch(task)
        links = texts_of_links(self.details(task))
        self.assertEqual(links[batch.number],
                         f"/lab/inventory/batches/{batch.pk}/")

    def test_a_task_without_steps_has_no_steps_table(self) -> None:
        task = make_task(self.kl, "Aspirin")
        self.assertEqual(record_tables(self.details(task)), [])

    def test_a_step_without_an_entry_has_its_position_alone(self) -> None:
        task = make_task(self.kl, "Aspirin", steps=2, done=1,
                         done_on=past(2))
        self.assertEqual(self.steps(self.details(task)),
                         [["1", "", "02.03.2025"], ["2", "", ""]])

    def test_the_steps_sort_in_the_browser(self) -> None:
        task = self.sequenced()
        found = self.details(task)
        self.assertEqual(unsorted_reasons(found), [])
        grid = next(grid for grid in found.find_all("table")
                    if headers_of(grid)[0] == "Stufe")
        rows = body_of(grid)
        self.assertEqual(cells(rows[0])[2].get("data-sort"), "2026-11-03")
        for cell in cells(rows[1])[2:]:
            self.assertFalse(ISO.match(cell.get("data-sort") or ""))


class EndpointTests(TaskDetailsCase):
    """``/lab/tasks/<number>/detail/``."""

    def test_htmx_gets_the_pane_alone(self) -> None:
        task = self.sequenced()
        response = self.client.get(detail_url(task), **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        found = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual([(e.get("id"), e.get("data-item")) for e in found],
                         [("item-detail", task.number)])

    def test_the_address_keeps_the_filters_of_the_page(self) -> None:
        task = self.sequenced()
        response = self.client.get(
            detail_url(task),
            **current(f"{TASKS}?state=all&person=KL&selected=T-999"))
        self.assertEqual(
            replaced(self, response),
            f"{TASKS}?state=all&person=KL&selected={task.number}")

    def test_without_htmx_the_list_is_the_answer(self) -> None:
        task = self.sequenced()
        self.assertRedirects(
            self.client.get(detail_url(task)),
            f"{TASKS}?selected={task.number}",
            fetch_redirect_response=False)

    def test_an_unknown_task_is_not_found(self) -> None:
        task = self.sequenced()
        self.assertEqual(self.client.get(
            detail_url(task), **HTMX).status_code, 200)
        for extra in ({}, HTMX):
            self.assertEqual(
                self.client.get(f"{TASKS}T-999999/detail/",
                                **extra).status_code, 404)

    def test_details_are_not_an_action(self) -> None:
        """Scenario: Details are not an action."""
        task = self.sequenced()
        found = self.client.get(detail_url(task), **HTMX)
        self.assertEqual(found.status_code, 200)
        self.assertEqual(page(found).find(id="item-detail")
                         .get("data-item"), task.number)
        before = list(Task.objects.values_list(
            "pk", "started", "ended", "cancelled", "failed"))
        for extra in ({}, HTMX):
            response = self.client.post(detail_url(task), {}, **extra)
            self.assertEqual(response.status_code, 405)
        self.assertEqual(
            list(Task.objects.values_list(
                "pk", "started", "ended", "cancelled", "failed")), before)

    def test_other_methods_are_refused_too(self) -> None:
        task = self.sequenced()
        self.assertEqual(self.client.get(detail_url(task),
                                         **HTMX).status_code, 200)
        for method in ("put", "delete", "patch"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(detail_url(task))
                self.assertEqual(response.status_code, 405)

    def test_an_action_still_reaches_the_task_action(self) -> None:
        task = make_task(self.kl, "Aspirin")
        self.client.force_login(self.kl)
        self.assertEqual(
            self.client.post(f"{TASKS}{task.number}/start/").status_code,
            302)
        self.assertIsNotNone(Task.objects.get(pk=task.pk).started)

    def test_the_answer_varies_on_the_headers_it_reads(self) -> None:
        task = self.sequenced()
        response = self.client.get(detail_url(task), **HTMX)
        found = {name.strip().lower()
                 for name in response.get("Vary", "").split(",")}
        self.assertLessEqual({"hx-request", "hx-current-url"}, found)
