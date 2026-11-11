"""Tests of the task page (task-tracker: Task page, Change history)."""

import re

from django.test import TestCase

from tasks.models import Task

from . import (NOT_IN_COLLECTION, IndexMixin, build_index, demo_index,
               edit_data, make_article, make_task, make_user, page, past,
               procedure, sequence, substance_for, task_form_data,
               task_url)


class PageCase(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")

    def setUp(self) -> None:
        self.use_index(demo_index())

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
            started=past(3, 11), steps_total=5, steps_done=2,
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
            self.use_index(build_index(language))
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
        self.use_index(build_index("en"))
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


class SequenceTests(PageCase):

    def test_task_with_a_sequence(self) -> None:
        """Scenario: Task with a sequence."""
        task = make_task(self.kl, sequence="SEQ-0001",
                         sequence_steps=["OSDB-0001", "OSDB-0002"],
                         steps_total=2, steps_done=1, started=past(1))
        root = self.show(task)
        self.assertIsNone(root.find("a", href=task_url(task, "edit")))
        items = root.find("ol").find_all("li")
        self.assertEqual(len(items), 2)
        first, second = items
        self.assertIn("OSDB-0001", first.text())
        self.assertIn("erledigt", first.text())
        self.assertIn("OSDB-0002", second.text())
        self.assertNotIn("erledigt", second.text())
        self.assertEqual(
            [a.get("href") for a in first.find_all("a")],
            ["/procedures/osdb-0001/"])
        self.assertEqual(
            [a.get("href") for a in second.find_all("a")],
            ["/procedures/osdb-0002/"])
        self.assertEqual(first.find("a").text(), "OSDB-0001")

    def test_done_steps_follow_steps_done(self) -> None:
        for done, marked in ((0, 0), (2, 2)):
            with self.subTest(done=done):
                task = make_task(self.kl, sequence="SEQ-0001",
                                 sequence_steps=["OSDB-0001", "OSDB-0002"],
                                 steps_total=2, steps_done=done,
                                 started=past(1))
                items = self.show(task).find("ol").find_all("li")
                self.assertEqual(
                    sum("erledigt" in i.text() for i in items), marked)

    def test_the_sequence_links_to_its_page(self) -> None:
        task = make_task(self.kl, sequence="SEQ-0001",
                         sequence_steps=["OSDB-0001"], steps_total=1)
        root = self.show(task)
        links = root.find_all("a", href="/sequences/seq-0001/")
        self.assertEqual([a.text() for a in links], ["SEQ-0001"])

    def test_a_task_without_a_sequence_lists_no_steps(self) -> None:
        self.assertIsNone(self.show(make_task(self.kl)).find("ol"))

    def test_procedure_missing_from_the_index(self) -> None:
        task = make_task(self.kl, sequence="SEQ-0001",
                         sequence_steps=["OSDB-0001", "OSDB-9999"],
                         steps_total=2)
        items = self.show(task).find("ol").find_all("li")
        self.assertEqual(len(items[0].find_all("a")), 1)
        self.assertIn("OSDB-9999", items[1].text())
        self.assertIn(NOT_IN_COLLECTION["de"], items[1].text())
        self.assertEqual(items[1].find_all("a"), [])
        self.assertNotIn(NOT_IN_COLLECTION["de"], items[0].text())

    def test_sequence_missing_from_the_index(self) -> None:
        task = make_task(self.kl, sequence="SEQ-9999",
                         sequence_steps=["OSDB-0001"], steps_total=1)
        root = self.show(task)
        self.assertIn("SEQ-9999", root.text())
        self.assertIn(NOT_IN_COLLECTION["de"], root.text())
        self.assertEqual(
            [a for a in root.find_all("a")
             if re.match(r"/sequences/[^/]+/\Z", a.get("href", ""))], [])
        self.assertEqual(len(root.find("ol").find_all("li")), 1)

    def test_the_steps_come_from_the_task_not_the_index(self) -> None:
        task = make_task(self.kl, sequence="SEQ-0001",
                         sequence_steps=["OSDB-0001", "OSDB-0002"],
                         steps_total=2)
        self.use_index(build_index(
            "de", procedures=[procedure("OSDB-0001"), procedure("OSDB-0002"),
                              procedure("OSDB-0003")],
            sequences=[sequence("SEQ-0001", ["OSDB-0003"])]))
        items = self.show(task).find("ol").find_all("li")
        self.assertEqual([i.find("a").text() for i in items],
                         ["OSDB-0001", "OSDB-0002"])

    def test_missing_procedure_in_english(self) -> None:
        self.use_index(build_index("en"))
        task = make_task(self.kl, sequence="SEQ-0001",
                         sequence_steps=["OSDB-0001"], steps_total=1,
                         steps_done=1, started=past(1))
        item = self.show(task).find("ol").find("li")
        self.assertIn(NOT_IN_COLLECTION["en"], item.text())
        self.assertIn("done", item.text())


class HistoryTests(PageCase):

    def change_priority(self, creator, changer) -> Task:
        self.client.force_login(creator)
        substance_for("Aspirin")
        self.client.post("/lab/tasks/new/", task_form_data(
            substance="aspirin", priority="medium"))
        task = Task.objects.get()
        self.client.force_login(changer)
        done = self.client.post(task_url(task, "edit"),
                                edit_data(task, priority="high"))
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
        self.use_index(build_index("en"))
        task = self.change_priority(self.kl, self.kl)
        text = self.show(task).text()
        for expected in ("Priority", "medium", "high", "Created"):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
