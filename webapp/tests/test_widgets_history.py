"""Tests of the change history as a collapsible widget on the item,
batch, vessel, delivery note and task pages (web-app: Widgets, Change
history)."""

import re
from typing import Any

from . import Element, berlin, frozen, make_task, page
from .collection_support import accept
from .inventory_support import (FormCase, batch_url, item_url, note_url,
                                vessel_url)
from .task_support import TaskCase
from .widget_support import (count_of, history_entries, history_rows,
                             history_widget, title_of, widgets)

CREATED = "Angelegt"
NO_CHANGE = "Kein Feld geändert"
TITLE = "Änderungen"


def has_token(text: str, token: str) -> bool:
    """Whether ``token`` stands in ``text`` as a word of its own."""
    return re.search(rf"(?<![\w.,]){re.escape(token)}(?![\w.,])",
                     text) is not None


class HistoryAssertions:
    """The checks every page's history widget passes."""

    def assertClosedWidget(self, root: Element) -> Element:
        """The page holds one collapsible widget, closed, titled
        ``Änderungen`` and called ``history``; return it."""
        collapsible = [w for w in widgets(root) if w.tag == "details"]
        self.assertEqual(len(collapsible), 1,
                         [w.tag for w in widgets(root)])
        found = history_widget(root)
        self.assertIs(found, collapsible[0])
        self.assertEqual(found.tag, "details")
        self.assertNotIn("open", found.attrs)
        self.assertEqual(found.get("id"), "history")
        head = found.find(cls="widget__head")
        self.assertIsNotNone(head)
        self.assertEqual(head.tag, "summary")
        self.assertIs(head.parent, found)
        self.assertEqual(title_of(found), TITLE)
        titled = [w for w in widgets(root) if title_of(w) == TITLE]
        self.assertEqual(len(titled), 1)
        grid = found.find("table")
        self.assertIsNotNone(grid)
        self.assertIn("aux-table", grid.classes)
        self.assertNotIn("main-table", grid.classes)
        for name in ("data-sortable", "data-controller"):
            self.assertNotIn(name, grid.attrs, "the history is not sortable")
        return found

    def assertCountIsEntries(self, root: Element) -> int:
        """The title bar's count is the number of the history's
        entries; return it."""
        found = history_widget(root)
        entries = history_entries(root)
        self.assertEqual(count_of(found), len(entries), entries)
        return len(entries)

    def assertCreationOnly(self, root: Element) -> None:
        """The history is the creation of the record and nothing
        else."""
        rows = history_rows(root)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0].change, CREATED)
        self.assertEqual(rows[0].subject, "")
        self.assertEqual(count_of(history_widget(root)), 1)


class ItemHistoryTests(HistoryAssertions, FormCase):

    EDIT = {"category": "", "note": "", "status": "active",
            "stocked_on": "2019-01-02", "compartment": "", "box": ""}

    def show(self, item: Any) -> Element:
        response = self.client.get(item_url(item))
        self.assertEqual(response.status_code, 200)
        return page(response)

    def edit(self, item: Any, **over: str) -> None:
        done = self.client.post(item_url(item, "edit"),
                                {**self.EDIT, **over})
        self.assertEqual(done.status_code, 302)

    def moved_item(self) -> Any:
        """An item created with compartment ``1`` and box ``A``, which
        ``KL`` changed to ``2`` and ``B`` in one save."""
        item = self.item("CH-0012", compartment="1", box="A")
        self.edit(item, compartment="2", box="B")
        return item

    def test_change_history_as_a_collapsible_widget(self) -> None:
        """Scenario: Change history as a collapsible widget."""
        root = self.show(self.moved_item())
        found = self.assertClosedWidget(root)
        self.assertEqual(count_of(found), 2)
        rows = history_rows(root)
        self.assertEqual(len(rows), 3, rows)
        self.assertEqual(rows[2].change, CREATED)
        compartment = [r for r in rows[:2] if "Fach" in r.change]
        box = [r for r in rows[:2] if "Box" in r.change]
        self.assertEqual(len(compartment), 1, rows)
        self.assertEqual(len(box), 1, rows)
        for row in rows[:2]:
            self.assertIn("KL", row.user)
            self.assertEqual(row.subject, "")
        self.assertEqual(rows[0].time, rows[1].time)
        self.assertTrue(has_token(compartment[0].change, "1"), compartment)
        self.assertTrue(has_token(compartment[0].change, "2"), compartment)
        self.assertNotIn("Box", compartment[0].change)
        self.assertTrue(has_token(box[0].change, "A"), box)
        self.assertTrue(has_token(box[0].change, "B"), box)
        self.assertNotIn("Fach", box[0].change)

    def test_the_cells_of_a_save_span_its_rows(self) -> None:
        """One row per changed field, its time, user and subject cells
        spanning them."""
        found = history_widget(self.show(self.moved_item()))
        rows = [tr for tr in found.find("table").find_all("tr")
                if tr.find("td")]
        self.assertEqual(len(rows), 3)
        first = [c for c in rows[0].children
                 if isinstance(c, Element) and c.tag in ("td", "th")]
        second = [c for c in rows[1].children
                  if isinstance(c, Element) and c.tag in ("td", "th")]
        self.assertEqual(len(first), 4)
        for cell in first[:3]:
            self.assertEqual(cell.get("rowspan"), "2", cell.text())
        self.assertEqual(len(second), 1)

    def test_the_history_table_has_four_columns(self) -> None:
        found = history_widget(self.show(self.moved_item()))
        head = found.find("thead")
        self.assertIsNotNone(head)
        self.assertEqual(len(head.find_all("th")), 4)

    def test_a_save_is_one_entry_however_many_fields_it_changes(
            self) -> None:
        entries = history_entries(self.show(self.moved_item()))
        self.assertEqual(len(entries), 2)
        self.assertEqual(len(entries[0].changes), 2)
        self.assertEqual(entries[1].changes, [CREATED])

    def test_a_new_item_has_its_creation(self) -> None:
        root = self.show(self.item("CH-0012"))
        self.assertClosedWidget(root)
        self.assertCreationOnly(root)
        self.assertIn("KL", history_rows(root)[0].user)

    def test_the_entries_run_from_the_newest(self) -> None:
        item = self.item("CH-0012")
        self.edit(item, note="eins")
        self.edit(item, note="zwei")
        rows = history_rows(self.show(item))
        self.assertEqual(len(rows), 3, rows)
        self.assertIn("zwei", rows[0].change)
        self.assertIn("eins", rows[1].change)
        self.assertEqual(rows[2].change, CREATED)

    def test_the_count_is_the_number_of_entries(self) -> None:
        item = self.item("CH-0012", compartment="1", box="A")
        self.edit(item, compartment="2", box="B")
        self.edit(item, compartment="3", box="C", note="neu")
        root = self.show(item)
        self.assertEqual(self.assertCountIsEntries(root), 3)
        self.assertEqual(len(history_rows(root)), 6)

    def test_a_save_that_changes_nothing(self) -> None:
        item = self.item("CH-0012")
        self.edit(item)
        entries = history_entries(self.show(item))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].changes, [NO_CHANGE])
        self.assertEqual(entries[0].subject, "")
        self.assertEqual(entries[1].changes, [CREATED])

    def test_an_entered_value_is_headed_with_its_quarter(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        rows = history_rows(self.show(item))
        self.assertEqual(len(rows), 2, rows)
        self.assertEqual(rows[0].subject, "Verbrauch Q3 2026")
        self.assertNotIn("Verbrauch", rows[0].change)
        self.assertRegex(rows[0].change, r"– → 400(?!\d)")
        self.assertEqual(rows[1].subject, "")

    def test_the_history_is_public(self) -> None:
        item = self.item("CH-0012")
        self.client.logout()
        root = self.show(item)
        self.assertClosedWidget(root)
        self.assertCreationOnly(root)

    def test_the_rows_are_in_the_page_whether_it_is_open_or_not(
            self) -> None:
        root = self.show(self.moved_item())
        found = history_widget(root)
        self.assertNotIn("open", found.attrs)
        self.assertEqual(len(found.find_all("tr")), 4)

    def test_an_english_page_names_the_creation(self) -> None:
        accept(language="en")
        root = self.show(self.item("CH-0012"))
        self.assertEqual(history_rows(root)[0].change, "Created")
        self.assertEqual(count_of(history_widget(root)), 1)


class RecordHistoryTests(HistoryAssertions, FormCase):
    """The batch, vessel and delivery note pages share the template."""

    def show(self, path: str) -> Element:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_the_batch_page(self) -> None:
        root = self.show(batch_url(self.batch("CH-0012")))
        self.assertClosedWidget(root)
        self.assertCreationOnly(root)
        self.assertIn("KL", history_rows(root)[0].user)

    def test_the_vessel_page(self) -> None:
        root = self.show(vessel_url(self.vessel("CH-0012")))
        self.assertClosedWidget(root)
        self.assertCreationOnly(root)
        self.assertIn("KL", history_rows(root)[0].user)

    def test_the_delivery_note_page(self) -> None:
        note = self.deliver(self.item("CH-0012", quantity=5), 1)
        root = self.show(note_url(note))
        self.assertClosedWidget(root)
        self.assertCreationOnly(root)
        self.assertIn("KL", history_rows(root)[0].user)

    def test_a_changed_batch_lists_its_change(self) -> None:
        batch = self.batch("CH-0012", note="alt")
        batch.note = "neu"
        batch._history_user = self.ae
        batch.save()
        root = self.show(batch_url(batch))
        self.assertClosedWidget(root)
        self.assertEqual(self.assertCountIsEntries(root), 2)
        rows = history_rows(root)
        self.assertIn("AE", rows[0].user)
        self.assertTrue(has_token(rows[0].change, "neu"), rows[0])
        self.assertTrue(has_token(rows[0].change, "alt"), rows[0])
        self.assertEqual(rows[1].change, CREATED)

    def test_a_changed_vessel_lists_its_change(self) -> None:
        vessel = self.vessel("CH-0012", location="A1")
        vessel.location = "B2"
        vessel._history_user = self.ae
        vessel.save()
        root = self.show(vessel_url(vessel))
        self.assertClosedWidget(root)
        self.assertEqual(self.assertCountIsEntries(root), 2)
        rows = history_rows(root)
        self.assertIn("AE", rows[0].user)
        self.assertTrue(has_token(rows[0].change, "B2"), rows[0])
        self.assertTrue(has_token(rows[0].change, "A1"), rows[0])


class TaskHistoryTests(HistoryAssertions, TaskCase):
    """The task page includes the same widget in place of its own
    list."""

    def make(self, steps: str = "3") -> Any:
        with frozen(berlin(2026, 11, 1)):
            self.create(steps_total=steps, started="2026-11-01")
        return self.only_task()

    def show(self, task: Any) -> Element:
        self.client.logout()
        response = self.client.get(f"/lab/tasks/{task.number}/")
        self.assertEqual(response.status_code, 200)
        return page(response)

    def test_the_task_page_holds_the_widget(self) -> None:
        root = self.show(make_task(self.kl))
        self.assertClosedWidget(root)
        self.assertCountIsEntries(root)
        self.assertCreationOnly(root)

    def test_the_task_page_has_one_history(self) -> None:
        root = self.show(self.make())
        self.assertEqual(
            len([h for h in root.find_all("h2") if h.text() in (
                TITLE, "History")]), 1)
        self.assertEqual(len(history_widget(root).find_all("table")), 1)

    def test_a_removed_step(self) -> None:
        """Scenario: Removed step in a task's history."""
        task = self.make("3")
        self.client.force_login(self.kl)
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_total="2")
        root = self.show(task)
        rows = history_rows(root)
        removed = [r for r in rows if r.subject == "Stufe 3 entfernt"]
        self.assertEqual(len(removed), 1, [r.subject for r in rows])
        self.assertEqual(removed[0].change, "")
        self.assertIn("02.11.2026", removed[0].time)
        for row in rows[:rows.index(removed[0])]:
            self.assertIn("02.11.2026", row.time)
        self.assertEqual([r.subject for r in rows].count(
            "Stufe 2 entfernt"), 0)

    def test_a_removed_step_in_english(self) -> None:
        task = self.make("3")
        self.client.force_login(self.kl)
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_total="2")
        accept(language="en")
        rows = history_rows(self.show(task))
        removed = [r for r in rows if r.subject == "Step 3 removed"]
        self.assertEqual(len(removed), 1, [r.subject for r in rows])
        self.assertEqual(removed[0].change, "")

    def test_a_step_s_change_is_headed_with_its_position(self) -> None:
        task = self.make("2")
        self.client.force_login(self.kl)
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_done="1")
        rows = history_rows(self.show(task))
        newest = [r for r in rows if "02.11.2026" in r.time]
        self.assertTrue(newest, rows)
        self.assertEqual(newest[0].subject, "Stufe 1")
        self.assertNotIn(newest[0].change, ("", CREATED))

    def test_the_creation_of_the_task_and_its_steps(self) -> None:
        entries = history_entries(self.show(self.make("2")))
        created = {e.subject for e in entries if e.changes == [CREATED]}
        self.assertLessEqual({"", "Stufe 1", "Stufe 2"}, created)
        self.assertEqual(count_of(history_widget(self.show(
            self.only_task()))), len(entries))

    def test_the_entries_run_from_the_newest(self) -> None:
        task = self.make("2")
        self.client.force_login(self.kl)
        with frozen(berlin(2026, 11, 3)):
            self.change(self.only_task(), priority="high")
        with frozen(berlin(2026, 11, 4)):
            self.change(self.only_task(), steps_done="2")
        rows = history_rows(self.show(task))
        days = [next(d for d in ("04.11.2026", "03.11.2026", "01.11.2026")
                     if d in r.time) for r in rows]
        self.assertEqual(days, sorted(days, key=(
            "04.11.2026", "03.11.2026", "01.11.2026").index))
        self.assertEqual(days[0], "04.11.2026")
        self.assertEqual(days[-1], "01.11.2026")
