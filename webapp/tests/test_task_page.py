"""Tests of the task page (task-tracker: Task page, Change history)."""

import re
from datetime import date

from tasks.models import Task

from . import (NOT_IN_COLLECTION, Element, berlin, frozen, make_article,
               make_lot, make_task, make_withdrawal, page, past,
               substance_for, task_form_data, task_url)
from .collection_support import (accept, changed_collection,
                                 import_collection, without_ids)
from .task_support import TaskCase, history_text, steps_of


class PageCase(TaskCase):

    def setUp(self) -> None:
        super().setUp()
        self.client.logout()

    def show(self, task: Task):
        response = self.client.get(task_url(task))
        self.assertEqual(response.status_code, 200)
        return page(response)


class DetailTests(PageCase):

    def test_unknown_number_answers_404(self) -> None:
        self.assertEqual(self.client.get("/lab/tasks/T-999/").status_code,
                         404)
        self.client.force_login(self.kl)
        self.assertEqual(
            self.client.get("/lab/tasks/T-999/edit/").status_code, 404)
        self.assertEqual(
            self.client.post("/lab/tasks/T-999/start/").status_code, 404)

    def test_the_page_shows_the_record(self) -> None:
        task = make_task(
            self.kl, substance="Probe", priority="high", assignee=self.ae,
            started=past(3, 11), steps=5, done=2,
            batch="B-17", report=True,
            note="Zeile eins\nZeile zwei")
        root = self.show(task)
        heading = root.find("h1").text()
        self.assertIn(task.number, heading)
        self.assertIn("Probe", heading)
        text = root.text()
        for expected in ("In Arbeit", "hoch", "03.11.2025", "B-17",
                         "Zeile eins", "Zeile zwei"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertTrue("Anna Eisele" in text or "AE" in text)
        self.assertTrue("Klara Lehmann" in text or "KL" in text)
        self.assertLessEqual({"ja", "nein"}, set(text.split()))
        self.assertIsNotNone(root.find("progress"))
        self.assertNotIn("Nacharbeit", text)

    def test_the_substance_links_to_its_page(self) -> None:
        task = make_task(self.kl, substance="CH-0012")
        root = self.show(task)
        self.assertIn("(E)-Zimtsäure", root.find("h1").text())
        self.assertIn("/lab/registry/substances/cinnamic-acid/",
                      [a.get("href") for a in root.find_all("a")])
        self.assertNotIn("/compounds/cinnamic-acid/",
                         [a.get("href") for a in root.find_all("a")])

    def test_an_article_without_items_matches(self) -> None:
        found = substance_for("CH-0099")
        make_article(found, "CH-0099")
        task = make_task(self.kl, substance=found)
        root = self.show(task)
        self.assertIn("/lab/planning/", [a.get("href")
                                         for a in root.find_all("a")])
        text = root.text()
        self.assertIn("CH-0099", text)
        self.assertIn("Kein Verbrauch, keine Prognose.", text)

    def test_no_substance_is_marked_as_missing_from_the_collection(
            self) -> None:
        """Every substance is in the registry."""
        for language in ("de", "en"):
            accept(language=language)
            task = make_task(self.kl, substance="Probe")
            self.assertNotIn(NOT_IN_COLLECTION[language],
                             self.show(task).text())

    def test_follow_up_is_shown(self) -> None:
        task = make_task(self.kl, started=past(1), ended=past(2),
                         report=True)
        text = self.show(task).text()
        self.assertIn("Abgeschlossen", text)
        self.assertIn("Nacharbeit", text)
        done = make_task(self.kl, started=past(1), ended=past(2),
                         report=True, qc_list=True)
        self.assertNotIn("Nacharbeit", self.show(done).text())

    def test_cancelled_state_is_shown(self) -> None:
        task = make_task(self.kl, started=past(1), ended=past(2),
                         cancelled=True)
        text = self.show(task).text()
        self.assertIn("Verworfen", text)
        self.assertNotIn("Nacharbeit", text)

    def test_planned_state_is_shown(self) -> None:
        self.assertIn("Geplant", self.show(make_task(self.kl)).text())

    def test_the_edit_link_is_for_signed_in_users(self) -> None:
        task = make_task(self.kl)
        path = task_url(task, "edit")
        self.assertIsNone(self.show(task).find("a", href=path))
        self.client.force_login(self.kl)
        links = self.show(task).find_all("a", href=path)
        self.assertEqual([a.text() for a in links], ["Bearbeiten"])

    def test_english_page(self) -> None:
        accept(language="en")
        task = make_task(self.kl, substance="Probe", priority="high",
                         started=past(3, 11))
        text = self.show(task).text()
        self.assertIn("Running", text)
        self.assertIn("2025-11-03", text)
        self.assertIn("high", text)
        self.client.force_login(self.kl)
        self.assertEqual(
            [a.text() for a in self.show(task).find_all(
                "a", href=task_url(task, "edit"))], ["Edit"])


def sequence_links(root) -> list[str]:
    return [a.get("href") for a in root.find_all("a")
            if re.match(r"/sequences/[^/]+/\Z", a.get("href", ""))]


class SequenceTests(PageCase):
    """The sequence and the steps the page lists (task-tracker: Task
    page)."""

    def follow(self, sequence: str, **fields: str) -> Task:
        """A task of ``sequence``, saved through the form."""
        self.client.force_login(self.kl)
        self.create(sequence=sequence, **fields)
        self.client.logout()
        return self.only_task()

    def steps(self, task: Task) -> list:
        return self.show(task).find("ol").find_all("li")

    def test_task_with_a_sequence(self) -> None:
        """Scenario: Task with a sequence."""
        task = self.follow("SEQ-0002")
        task.steps.filter(position=1).update(done_on=date(2026, 11, 3))
        root = self.show(task)
        self.assertIsNone(root.find("a", href=task_url(task, "edit")))
        first, second = self.steps(task)
        self.assertIn("OSDB-0004", first.text())
        self.assertIn("erledigt am 03.11.2026", first.text())
        self.assertNotIn("Eintrag", first.text())
        self.assertIn("OSDB-0009", second.text())
        self.assertIn("Eintrag 1", second.text())
        self.assertNotIn("erledigt", second.text())
        self.assertEqual([a.get("href") for a in first.find_all("a")],
                         ["/procedures/osdb-0004/"])
        self.assertEqual([a.get("href") for a in second.find_all("a")],
                         ["/procedures/osdb-0009/"])
        self.assertEqual(first.find("a").text(), "OSDB-0004")

    def test_the_sequence_links_to_its_page(self) -> None:
        """Requirement: Task page (the sequence's ID linking to
        `/sequences/<ID in lower case>/`)."""
        task = self.follow("SEQ-0001")
        links = self.show(task).find_all("a", href="/sequences/seq-0001/")
        self.assertEqual([a.text() for a in links], ["SEQ-0001"])

    def test_a_task_without_a_sequence_shows_none(self) -> None:
        root = self.show(make_task(self.kl))
        self.assertEqual(sequence_links(root), [])
        self.assertIsNone(root.find("ol"))

    def test_entry_numbers_only_for_general_procedures(self) -> None:
        """Requirement: Task page (`Eintrag <n>` appears only for an
        entry of a procedure the import marked general)."""
        from collection.models import ScopeEntry
        from tasks.models import TaskStep
        task = make_task(self.kl)
        for position, (procedure, number) in enumerate(
                (("OSDB-0009", 2), ("OSDB-0009", 3), ("OSDB-0002", 1)),
                start=1):
            TaskStep.objects.create(
                task=task, position=position, planned_import=self.first,
                entry=ScopeEntry.objects.get(procedure__key=procedure,
                                             position=number))
        first, second, third = self.steps(task)
        self.assertIn("Eintrag 2", first.text())
        self.assertIn("Eintrag 3", second.text())
        self.assertIn("OSDB-0002", third.text())
        self.assertNotIn("Eintrag", third.text())
        self.assertEqual([a.get("href") for a in third.find_all("a")],
                         ["/procedures/osdb-0002/"])

    def test_a_step_without_an_entry_shows_its_position(self) -> None:
        """Requirement: Task page (a step without an entry as `Stufe
        <n>`)."""
        task = make_task(self.kl, steps=3, done=1)
        first, second, third = self.steps(task)
        self.assertIn("Stufe 1", first.text())
        self.assertIn("erledigt am 02.03.2025", first.text())
        self.assertIn("Stufe 2", second.text())
        self.assertIn("Stufe 3", third.text())
        self.assertNotIn("erledigt", second.text() + third.text())
        for item in (first, second, third):
            self.assertEqual(item.find_all("a"), [])

    def test_the_steps_in_english(self) -> None:
        """Requirement: Task page (`Step <n>`, `Entry <n>`, `done on
        <date>`)."""
        task = self.follow("SEQ-0002")
        task.steps.filter(position=2).update(done_on=date(2026, 11, 3))
        plain = make_task(self.kl, steps=2, done=1)
        accept(language="en")
        first, second = self.steps(task)
        self.assertIn("OSDB-0004", first.text())
        self.assertIn("OSDB-0009", second.text())
        self.assertIn("Entry 1", second.text())
        self.assertIn("done on 2026-11-03", second.text())
        one, two = self.steps(plain)
        self.assertIn("Step 1", one.text())
        self.assertIn("done on 2025-03-02", one.text())
        self.assertIn("Step 2", two.text())

    def test_a_withdrawn_sequence_has_no_link(self) -> None:
        """Requirement: Task page (a withdrawn sequence shows with the
        mark and no link)."""
        task = self.follow("SEQ-0001")
        import_collection(without_ids("SEQ-0001"))
        root = self.show(task)
        self.assertIn("SEQ-0001", root.text())
        self.assertIn(NOT_IN_COLLECTION["de"], root.text())
        self.assertEqual(sequence_links(root), [])
        self.assertEqual(len(self.steps(task)), 2)

    def test_a_sequence_in_the_collection_is_not_marked(self) -> None:
        task = self.follow("SEQ-0001")
        self.assertNotIn(NOT_IN_COLLECTION["de"], self.show(task).text())

    def test_a_withdrawn_procedure_has_no_link(self) -> None:
        """Requirement: Task page (a withdrawn procedure shows with the
        mark and no link)."""
        from collection.models import ScopeEntry
        from tasks.models import TaskStep
        task = make_task(self.kl)
        for position, key in enumerate(("OSDB-0006", "OSDB-0008"),
                                       start=1):
            TaskStep.objects.create(
                task=task, position=position, planned_import=self.first,
                entry=ScopeEntry.objects.get(procedure__key=key))
        import_collection(without_ids("OSDB-0006"))
        gone, kept = self.steps(task)
        self.assertIn("OSDB-0006", gone.text())
        self.assertIn(NOT_IN_COLLECTION["de"], gone.text())
        self.assertEqual(gone.find_all("a"), [])
        self.assertEqual([a.get("href") for a in kept.find_all("a")],
                         ["/procedures/osdb-0008/"])
        self.assertNotIn(NOT_IN_COLLECTION["de"], kept.text())

    def test_a_withdrawn_entry(self) -> None:
        """Scenario: A withdrawn entry."""
        task = self.follow("SEQ-0002")
        import_collection(changed_collection("OSDB-0009"))
        first, second = self.steps(task)
        self.assertIn("OSDB-0009", second.text())
        self.assertIn("4-acetylbiphenyl >> 1-biphenyl-4-yl-ethanol",
                      second.text())
        self.assertIn(NOT_IN_COLLECTION["de"], second.text())
        self.assertNotIn("Eintrag 1", second.text())
        self.assertEqual(second.find_all("a"), [])
        self.assertIn("OSDB-0004", first.text())
        self.assertNotIn(NOT_IN_COLLECTION["de"], first.text())
        self.assertEqual([a.get("href") for a in first.find_all("a")],
                         ["/procedures/osdb-0004/"])

    def test_a_withdrawn_entry_of_a_specific_procedure(self) -> None:
        """Requirement: Task page (a step whose entry is withdrawn,
        shown by its procedure's ID and the entry's signature)."""
        task = self.follow("SEQ-0002")
        import_collection(changed_collection("OSDB-0004"))
        first, second = self.steps(task)
        self.assertIn("OSDB-0004", first.text())
        self.assertIn("4-bromoacetophenone + phenylboronic-acid >> "
                      "4-acetylbiphenyl", first.text())
        self.assertIn(NOT_IN_COLLECTION["de"], first.text())
        self.assertEqual(first.find_all("a"), [])
        self.assertNotIn(NOT_IN_COLLECTION["de"], second.text())

    def test_a_withdrawn_entry_in_english(self) -> None:
        task = self.follow("SEQ-0002")
        import_collection(changed_collection("OSDB-0009"))
        accept(language="en")
        second = self.steps(task)[1]
        self.assertIn(NOT_IN_COLLECTION["en"], second.text())
        self.assertNotIn("Entry 1", second.text())

    def test_the_steps_come_from_the_task_not_the_collection(self) -> None:
        """Requirement: Task record (the steps keep their entries)."""
        task = self.follow("SEQ-0001")
        import_collection(changed_collection("OSDB-0002"))
        items = self.steps(task)
        self.assertEqual([i.text().split()[0] for i in items],
                         ["OSDB-0001", "OSDB-0002"])

    def test_the_progress_counts_the_steps_done(self) -> None:
        """Requirement: Task page (progress)."""
        task = self.follow("SEQ-0001", started="2025-03-01")
        task.steps.filter(position=1).update(done_on=past(2))
        root = self.show(task)
        self.assertIn("50", root.find("progress").parent.text())


class HistoryTests(PageCase):

    def change_priority(self, creator, changer) -> Task:
        self.client.force_login(creator)
        substance_for("Aspirin")
        self.client.post("/lab/tasks/new/", task_form_data(
            substance="aspirin", priority="medium"))
        task = Task.objects.get()
        self.client.force_login(changer)
        done = self.change(task, priority="high")
        self.assertEqual(done.status_code, 302)
        self.client.logout()
        return task

    def test_history_of_a_change(self) -> None:
        """Scenario: History of a change."""
        task = self.change_priority(self.kl, self.kl)
        self.assertEqual(task.history.count(), 2)
        newest = task.history.first()
        self.assertEqual(newest.history_user, self.kl)
        self.assertEqual(newest.priority, "high")
        text = self.show(task).text()
        for expected in ("Priorität", "mittel", "hoch", "KL", "Angelegt"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_newest_entry_comes_first(self) -> None:
        task = self.change_priority(self.kl, self.kl)
        text = self.show(task).text()
        self.assertLess(text.find("mittel"), text.rfind("Angelegt"))

    def test_the_entry_names_the_user_who_changed_it(self) -> None:
        task = self.change_priority(self.kl, self.ae)
        self.assertEqual(task.history.first().history_user, self.ae)
        self.assertEqual(task.history.last().history_user, self.kl)
        self.assertIn("AE", self.show(task).text())

    def test_a_task_never_changed_shows_its_creation(self) -> None:
        self.assertIn("Angelegt", self.show(make_task(self.kl)).text())

    def test_english_history(self) -> None:
        accept(language="en")
        task = self.change_priority(self.kl, self.kl)
        text = self.show(task).text()
        for expected in ("Priority", "medium", "high", "Created"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)


class StepHistoryTests(PageCase):
    """The change history lists the task's changes and its steps'
    (task-tracker: Task page)."""

    def make(self, steps: str = "2") -> Task:
        self.client.force_login(self.kl)
        with frozen(berlin(2026, 11, 1)):
            self.create(steps_total=steps, started="2026-11-01")
        task = self.only_task()
        return task

    def test_a_steps_change_is_headed_with_its_position(self) -> None:
        """Requirement: Task page (a step's change is headed `Stufe
        <n>`)."""
        task = self.make()
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_done="1")
        self.client.logout()
        text = history_text(self.show(task))
        newest = text[text.index("02.11.2026"):text.index("01.11.2026")]
        self.assertIn("Stufe 1", newest)

    def test_the_history_runs_from_the_newest_change(self) -> None:
        """Requirement: Task page (newest first, the task's changes and
        its steps' together)."""
        task = self.make()
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_done="1")
        with frozen(berlin(2026, 11, 3)):
            self.change(self.only_task(), priority="high")
        with frozen(berlin(2026, 11, 4)):
            self.change(self.only_task(), steps_done="2")
        self.client.logout()
        text = history_text(self.show(task))
        positions = [text.index(day) for day in
                     ("04.11.2026", "03.11.2026", "02.11.2026",
                      "01.11.2026")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Stufe 2", text[:text.index("03.11.2026")])
        self.assertIn("Priorität", text[text.index("03.11.2026"):
                                         text.index("02.11.2026")])

    def test_a_removed_step(self) -> None:
        """Requirement: Task page (a removed step's `Stufe <n>
        entfernt`)."""
        task = self.make("3")
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_total="2")
        self.client.logout()
        text = history_text(self.show(task))
        newest = text[text.index("02.11.2026"):text.index("01.11.2026")]
        self.assertIn("Stufe 3 entfernt", newest)
        self.assertNotIn("Stufe 2 entfernt", text)

    def test_the_headings_in_english(self) -> None:
        """Requirement: Task page (`Step <n>`, `Step <n> removed`)."""
        task = self.make("3")
        with frozen(berlin(2026, 11, 2)):
            self.change(task, steps_total="2", steps_done="1")
        self.client.logout()
        accept(language="en")
        text = history_text(self.show(task))
        self.assertIn("Step 3 removed", text)
        self.assertIn("Step 1", text)

    def test_the_steps_of_a_sequence_are_in_the_history(self) -> None:
        """Requirement: Task record (tasks and their steps keep a change
        history)."""
        self.client.force_login(self.kl)
        self.create(sequence="SEQ-0001")
        task = self.only_task()
        self.client.logout()
        text = history_text(self.show(task))
        self.assertIn("Angelegt", text)
        self.assertIn("Stufe 1", text)
        self.assertIn("Stufe 2", text)


def lot_href(lot, action: str = "", step=None) -> str:
    path = f"/lab/inventory/bulk/{lot.pk}/" + (
        f"{action}/" if action else "")
    return f"{path}?step={step.pk}" if step else path


def step_items(root) -> list[Element]:
    """The items of the task page's list of steps, in order."""
    return [item for item in root.find("ol").children
            if isinstance(item, Element) and item.tag == "li"]


def hrefs(item: Element) -> list[str]:
    return [a.get("href") for a in item.find_all("a")]


class FailedPageTests(PageCase):

    def test_a_failed_task_shows_its_state_and_no_follow_up(self) -> None:
        """Requirement: Task record (the state `failed`; a failed task
        needs no follow-up)."""
        task = make_task(self.kl, started=past(1), ended=past(2),
                         failed=True)
        text = self.show(task).text()
        self.assertIn("Fehlgeschlagen", text)
        self.assertNotIn("Nacharbeit", text)
        self.assertNotIn("Abgeschlossen", text)

    def test_the_state_in_english(self) -> None:
        task = make_task(self.kl, started=past(1), ended=past(2),
                         failed=True)
        accept(language="en")
        text = self.show(task).text()
        self.assertIn("Failed", text)
        self.assertNotIn("Follow-up", text)

    def test_a_failed_task_offers_no_record_as_bulk(self) -> None:
        task = make_task(self.kl, started=past(1), ended=past(2),
                         failed=True)
        self.client.force_login(self.kl)
        self.assertNotIn("Als Bulk erfassen", self.show(task).text())


class StepLotsPageTests(PageCase):
    """Requirement: Task page (under each step the lots it made and the
    withdrawals booked into it, and the links to record either)."""

    def setUp(self) -> None:
        super().setUp()
        self.task = make_task(self.kl, "Aspirin", started=past(1), steps=2)
        self.first, self.second = steps_of(self.task)

    def sequence_task(self) -> Task:
        self.client.force_login(self.kl)
        self.create(substance="1-biphenyl-4-yl-ethanol",
                    sequence="SEQ-0002", started="2025-03-01")
        self.client.logout()
        return Task.objects.order_by("-pk").first()

    def test_a_step_lists_the_lots_it_made(self) -> None:
        lot = make_lot(self.kl, substance=self.task.substance,
                       task_step=self.first)
        first, second = step_items(self.show(self.task))
        self.assertIn(lot_href(lot), hrefs(first))
        self.assertNotIn(lot_href(lot), hrefs(second))

    def test_a_step_lists_the_withdrawals_into_it(self) -> None:
        lot = make_lot(self.kl, substance=self.task.substance)
        make_withdrawal(self.kl, lot, self.second, "1")
        first, second = step_items(self.show(self.task))
        self.assertIn(lot_href(lot), hrefs(second))
        self.assertNotIn(lot_href(lot), hrefs(first))

    def test_the_lots_of_other_tasks_are_not_listed(self) -> None:
        other = make_task(self.kl, "Aspirin", started=past(1), steps=1)
        lot = make_lot(self.kl, substance=other.substance,
                       task_step=other.steps.get())
        for item in step_items(self.show(self.task)):
            self.assertNotIn(lot_href(lot), hrefs(item))

    def test_each_step_of_an_open_task_offers_to_record_a_lot(self) -> None:
        """Requirement: Task page (`Los erfassen` to
        `/lab/inventory/bulk/new/?step=<id>`)."""
        self.client.force_login(self.kl)
        planned = make_task(self.kl, "Aspirin", steps=2)
        for task in (self.task, planned):
            items = step_items(self.show(task))
            for step, item in zip(steps_of(task), items, strict=True):
                with self.subTest(task=task.number, step=step.position):
                    links = [a for a in item.find_all("a")
                             if a.text() == "Los erfassen"]
                    self.assertEqual(
                        [a.get("href") for a in links],
                        [f"/lab/inventory/bulk/new/?step={step.pk}"])

    def test_the_link_in_english(self) -> None:
        self.client.force_login(self.kl)
        accept(language="en")
        item = step_items(self.show(self.task))[0]
        self.assertIn("Record a lot", [a.text() for a in item.find_all("a")])

    def test_no_links_to_record_without_a_sign_in(self) -> None:
        for item in step_items(self.show(self.task)):
            self.assertEqual([a for a in item.find_all("a")
                              if a.text() in ("Los erfassen",
                                              "Entnahme buchen")], [])

    def test_no_links_to_record_on_a_task_that_is_not_open(self) -> None:
        """Requirement: Task page (while the task is planned or
        running)."""
        self.client.force_login(self.kl)
        ended = make_task(self.kl, "Aspirin", started=past(2),
                          ended=past(1), steps=1, report=True,
                          qc_list=True)
        failed = make_task(self.kl, "Aspirin", started=past(2),
                           ended=past(1), steps=1, failed=True)
        cancelled = make_task(self.kl, "Aspirin", steps=1, cancelled=True)
        for task in (ended, failed, cancelled):
            with self.subTest(task=task.number):
                (item,) = step_items(self.show(task))
                self.assertEqual(
                    [a for a in item.find_all("a")
                     if a.text() in ("Los erfassen", "Entnahme buchen")],
                    [])

    def test_a_withdrawal_may_be_booked_from_the_open_lots_of_the_substrates(
            self) -> None:
        """Requirement: Task page (`Entnahme buchen`, listing the open
        lots of the step's substrates)."""
        task = self.sequence_task()
        first, second = steps_of(task)
        self.client.force_login(self.kl)
        open_lot = make_lot(self.kl, substance=substance_for(
            "4-acetylbiphenyl"))
        used_up = make_lot(self.kl, substance=substance_for(
            "4-acetylbiphenyl"), amount="0")
        other = make_lot(self.kl, substance=substance_for("cinnamic-acid"))
        items = step_items(self.show(task))
        self.assertIn("Entnahme buchen", items[1].text())
        self.assertIn(lot_href(open_lot, "withdraw", second),
                      hrefs(items[1]))
        for lot in (used_up, other):
            with self.subTest(lot=lot.pk):
                self.assertNotIn(lot_href(lot, "withdraw", second),
                                 hrefs(items[1]))
        self.assertNotIn(lot_href(open_lot, "withdraw", first),
                         hrefs(items[0]))

    def test_a_step_without_an_entry_offers_every_open_lot(self) -> None:
        self.client.force_login(self.kl)
        mine = make_lot(self.kl, substance=self.task.substance)
        other = make_lot(self.kl, substance=substance_for("cinnamic-acid"))
        used_up = make_lot(self.kl, substance=self.task.substance,
                           amount="0")
        first, second = step_items(self.show(self.task))
        for item, step in ((first, self.first), (second, self.second)):
            with self.subTest(step=step.position):
                self.assertIn("Entnahme buchen", item.text())
                self.assertIn(lot_href(mine, "withdraw", step), hrefs(item))
                self.assertIn(lot_href(other, "withdraw", step),
                              hrefs(item))
                self.assertNotIn(lot_href(used_up, "withdraw", step),
                                 hrefs(item))

    def test_the_withdrawal_link_in_english(self) -> None:
        self.client.force_login(self.kl)
        make_lot(self.kl, substance=self.task.substance)
        accept(language="en")
        item = step_items(self.show(self.task))[0]
        self.assertIn("Book a withdrawal", item.text())
