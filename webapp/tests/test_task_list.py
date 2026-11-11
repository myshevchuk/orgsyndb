"""Tests of the task list (task-tracker: Task list)."""

from datetime import date
from urllib.parse import quote

from django.test import TestCase

from . import (IndexMixin, build_index, demo_index, field_value,
               make_task, make_user, numbers, page, past, table, task_url)

COLUMNS_DE = ["Nr.", "Produkt", "Priorität", "Bearbeitung", "Beginn",
              "Ende", "Fortschritt", "Charge", "Bericht", "QC-Liste",
              "Status"]
COLUMNS_EN = ["No.", "Product", "Priority", "Assignee", "Started", "Ended",
              "Progress", "Batch", "Report", "QC list", "State"]
MIDDLE_DOT = "·"


class ListCase(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")

    def setUp(self) -> None:
        self.use_index(demo_index())

    def listing(self, query: str = ""):
        response = self.client.get("/lab/tasks/" + query)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def shown(self, query: str = "") -> list[str]:
        return numbers(self.listing(query))


class DefaultViewTests(ListCase):

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.planned = make_task(cls.kl, substance="Alpha", priority="low")
        cls.running = make_task(cls.kl, substance="Beta", priority="high",
                                started=past(1))
        cls.done = make_task(cls.kl, substance="Gamma", started=past(1),
                             ended=past(2), report=True, qc_list=True)
        cls.followup = make_task(cls.kl, substance="Delta", priority="low",
                                 started=past(1), ended=past(2),
                                 qc_list=True)
        cls.cancelled = make_task(cls.kl, substance="Epsilon",
                                  cancelled=True)

    def test_default_view(self) -> None:
        """Scenario: Default view."""
        root = self.listing()
        self.assertEqual(numbers(root), [self.running.number,
                                         self.planned.number,
                                         self.followup.number])
        header, rows = table(root)
        by_number = {row[header[0]].text(): row for row in rows}
        self.assertIn("Nacharbeit",
                      by_number[self.followup.number]["Status"].text())
        self.assertNotIn("Nacharbeit",
                         by_number[self.running.number]["Status"].text())
        self.assertNotIn("Nacharbeit",
                         by_number[self.planned.number]["Status"].text())
        self.assertIn(f"1 geplant {MIDDLE_DOT} 1 in Arbeit {MIDDLE_DOT} "
                      "1 Nacharbeit", root.text())

    def test_state_filters(self) -> None:
        expected = {
            "": [self.running, self.planned, self.followup],
            "?state=active": [self.running, self.planned, self.followup],
            "?state=planned": [self.planned],
            "?state=running": [self.running],
            "?state=followup": [self.followup],
            "?state=ended": [self.done, self.followup],
            "?state=cancelled": [self.cancelled],
            "?state=all": [self.running, self.done, self.cancelled,
                           self.planned, self.followup],
        }
        for query, tasks in expected.items():
            with self.subTest(query=query):
                self.assertEqual(self.shown(query),
                                 [t.number for t in tasks])

    def test_filters_keep_their_values_in_the_form(self) -> None:
        root = self.listing("?state=running&person=KL&priority=high&q=be")
        self.assertEqual(field_value(root, "state"), "running")
        self.assertEqual(field_value(root, "person"), "KL")
        self.assertEqual(field_value(root, "priority"), "high")
        self.assertEqual(field_value(root, "q"), "be")

    def test_the_form_shows_the_defaults(self) -> None:
        root = self.listing()
        self.assertEqual(field_value(root, "state"), "active")
        self.assertIn(field_value(root, "q"), (None, ""))

    def test_unknown_filter_values_are_ignored(self) -> None:
        default = self.shown()
        for query in ("?state=bogus", "?priority=urgent", "?person=ZZ",
                      "?state=&priority=&person=", "?state=ALL"):
            with self.subTest(query=query):
                self.assertEqual(self.shown(query), default)
        self.assertEqual(field_value(self.listing("?state=bogus"), "state"),
                         "active")

    def test_priority_filter(self) -> None:
        self.assertEqual(self.shown("?priority=high"),
                         [self.running.number])
        self.assertEqual(self.shown("?state=all&priority=low"),
                         [self.planned.number, self.followup.number])
        self.assertEqual(self.shown("?priority=medium"), [])

    def test_the_link_to_a_new_task_is_for_signed_in_users(self) -> None:
        root = self.listing()
        self.assertIsNone(root.find("a", href="/lab/tasks/new/"))
        self.client.force_login(self.kl)
        root = self.listing()
        links = root.find_all("a", href="/lab/tasks/new/")
        self.assertEqual([a.text() for a in links], ["Neue Aufgabe"])


class ColumnTests(ListCase):

    def test_columns(self) -> None:
        make_task(self.kl, substance="Probe")
        header, _ = table(self.listing())
        self.assertEqual(header, COLUMNS_DE)

    def test_a_row(self) -> None:
        task = make_task(self.kl, substance="Probe", priority="high",
                         assignee=self.ae, started=date(2025, 11, 3),
                         steps_total=5, steps_done=2, batch="B-17",
                         report=True)
        header, rows = table(self.listing())
        row = rows[0]
        link = row["Nr."].find("a")
        self.assertEqual(link.text(), task.number)
        self.assertEqual(link.get("href"), task_url(task))
        self.assertIn("Probe", row["Produkt"].text())
        self.assertEqual(
            [a.get("href") for a in row["Produkt"].find_all("a")],
            ["/lab/registry/substances/probe/"])
        self.assertIn("hoch", row["Priorität"].text())
        self.assertIn("manuell", row["Priorität"].text())
        cell = row["Bearbeitung"]
        self.assertEqual(cell.text(), "AE")
        titled = [e for e in [cell, *cell.walk()] if e.get("title")]
        self.assertEqual([e.get("title") for e in titled], ["Anna Eisele"])
        self.assertEqual(row["Beginn"].text(), "03.11.2025")
        self.assertEqual(row["Ende"].text(), "")
        self.assertIn("2/5", row["Fortschritt"].text())
        self.assertIsNotNone(row["Fortschritt"].find("progress"))
        self.assertEqual(row["Charge"].text(), "B-17")
        self.assertEqual(row["Bericht"].text(), "ja")
        self.assertEqual(row["QC-Liste"].text(), "nein")
        self.assertIn("In Arbeit", row["Status"].text())

    def test_title_is_the_user_name_without_a_full_name(self) -> None:
        plain = make_user("plain", "PL")
        make_task(self.kl, assignee=plain)
        _, rows = table(self.listing())
        cell = rows[0]["Bearbeitung"]
        titles = [e.get("title") for e in [cell, *cell.walk()]
                  if e.get("title")]
        self.assertEqual(titles, ["plain"])

    def test_a_row_without_assignee_or_total(self) -> None:
        make_task(self.kl, substance="Probe")
        _, rows = table(self.listing())
        row = rows[0]
        self.assertEqual(row["Bearbeitung"].text(), "")
        self.assertEqual(row["Fortschritt"].text(), "")
        self.assertIsNone(row["Fortschritt"].find("progress"))
        self.assertEqual(row["Beginn"].text(), "")
        self.assertEqual(row["Bericht"].text(), "nein")
        self.assertEqual(row["QC-Liste"].text(), "nein")
        self.assertIn("Geplant", row["Status"].text())

    def test_state_badges(self) -> None:
        make_task(self.kl, substance="P")
        make_task(self.kl, substance="R", started=past(1))
        make_task(self.kl, substance="E", started=past(1), ended=past(2),
                  report=True, qc_list=True)
        make_task(self.kl, substance="C", cancelled=True)
        _, rows = table(self.listing("?state=all"))
        labels = {r["Produkt"].text().split()[0]: r["Status"].text()
                  for r in rows}
        self.assertIn("Geplant", labels["P"])
        self.assertIn("In Arbeit", labels["R"])
        self.assertIn("Abgeschlossen", labels["E"])
        self.assertIn("Verworfen", labels["C"])

    def test_english_columns_and_texts(self) -> None:
        self.use_index(build_index("en"))
        make_task(self.kl, substance="Probe", priority="high",
                  assignee=self.ae, started=date(2025, 11, 3),
                  steps_total=5, steps_done=2, report=True)
        root = self.listing()
        header, rows = table(root)
        self.assertEqual(header, COLUMNS_EN)
        row = rows[0]
        self.assertIn("high", row["Priority"].text())
        self.assertIn("entered", row["Priority"].text())
        self.assertEqual(row["Started"].text(), "2025-11-03")
        self.assertEqual(row["Report"].text(), "yes")
        self.assertEqual(row["QC list"].text(), "no")
        self.assertIn("Running", row["State"].text())
        self.assertIn(f"0 planned {MIDDLE_DOT} 1 running {MIDDLE_DOT} "
                      "0 follow-up", root.text())

    def test_english_follow_up_and_new_task_link(self) -> None:
        self.use_index(build_index("en"))
        make_task(self.kl, substance="Probe", started=past(1), ended=past(2))
        self.client.force_login(self.kl)
        root = self.listing()
        _, rows = table(root)
        self.assertIn("Follow-up", rows[0]["State"].text())
        self.assertEqual(
            [a.text() for a in root.find_all("a", href="/lab/tasks/new/")],
            ["New task"])


class SubstanceLinkTests(ListCase):

    def test_a_substance_links_to_its_page_in_the_german_name(self) -> None:
        """Scenario: A task's substance."""
        make_task(self.kl, substance="CH-0012")
        make_task(self.kl, substance="Aspirin")
        _, rows = table(self.listing())
        cinnamic = next(r for r in rows
                        if "Zimtsäure" in r["Produkt"].text())
        self.assertEqual(cinnamic["Produkt"].text(), "(E)-Zimtsäure")
        self.assertEqual(
            [a.get("href") for a in cinnamic["Produkt"].find_all("a")],
            ["/lab/registry/substances/cinnamic-acid/"])

    def test_the_name_is_english_on_an_english_site(self) -> None:
        self.use_index(build_index("en"))
        make_task(self.kl, substance="CH-0012")
        _, rows = table(self.listing())
        self.assertEqual(rows[0]["Product"].text(), "(E)-Cinnamic acid")


class OrderTests(ListCase):

    def test_priority_comes_first(self) -> None:
        low = make_task(self.kl, priority="low", started=past(1))
        medium = make_task(self.kl, priority="medium", started=past(1))
        high_followup = make_task(self.kl, priority="high",
                                  started=past(1), ended=past(2))
        high_planned = make_task(self.kl, priority="high")
        self.assertEqual(
            self.shown(),
            [high_planned.number, high_followup.number, medium.number,
             low.number])

    def test_state_order_within_a_priority(self) -> None:
        cancelled = make_task(self.kl, cancelled=True)
        ended = make_task(self.kl, started=past(1), ended=past(2))
        planned = make_task(self.kl)
        running = make_task(self.kl, started=past(3))
        self.assertEqual(
            self.shown("?state=all"),
            [running.number, planned.number, ended.number,
             cancelled.number])

    def test_start_date_then_number(self) -> None:
        late = make_task(self.kl, started=past(20))
        early = make_task(self.kl, started=past(2))
        middle_a = make_task(self.kl, started=past(10))
        middle_b = make_task(self.kl, started=past(10))
        self.assertEqual(
            self.shown(),
            [early.number, middle_a.number, middle_b.number, late.number])

    def test_tasks_without_a_start_date_come_last(self) -> None:
        none_b = make_task(self.kl, cancelled=True)
        late = make_task(self.kl, cancelled=True, started=past(20))
        none_a = make_task(self.kl, cancelled=True)
        early = make_task(self.kl, cancelled=True, started=past(2))
        self.assertEqual(
            self.shown("?state=cancelled"),
            [early.number, late.number, none_b.number, none_a.number])

    def test_number_breaks_ties(self) -> None:
        tasks = [make_task(self.kl) for _ in range(4)]
        self.assertEqual(self.shown(), [t.number for t in tasks])


class CountTests(ListCase):

    def test_counts_of_an_empty_list(self) -> None:
        text = self.listing().text()
        self.assertIn(f"0 geplant {MIDDLE_DOT} 0 in Arbeit {MIDDLE_DOT} "
                      "0 Nacharbeit", text)

    def test_counts_by_state(self) -> None:
        for _ in range(2):
            make_task(self.kl)
        for _ in range(3):
            make_task(self.kl, started=past(1))
        make_task(self.kl, started=past(1), ended=past(2))
        make_task(self.kl, started=past(1), ended=past(2), report=True)
        make_task(self.kl, started=past(1), ended=past(2), report=True,
                  qc_list=True)
        make_task(self.kl, cancelled=True)
        self.assertIn(f"2 geplant {MIDDLE_DOT} 3 in Arbeit {MIDDLE_DOT} "
                      "2 Nacharbeit", self.listing().text())

    def test_there_is_no_paging(self) -> None:
        for _ in range(60):
            make_task(self.kl)
        self.assertEqual(len(self.shown()), 60)


class FilterTests(ListCase):

    def make(self, who, **fields):
        return make_task(self.kl, assignee=who, **fields)

    def test_filters(self) -> None:
        """Scenario: Filters."""
        found = [
            self.make(self.kl, substance="CH-0012", started=past(1)),
            self.make(self.kl, substance="cinnamic-acid"),
            self.make(self.kl, substance="Zimt-Derivat"),
            self.make(self.kl, substance="Aspirin",
                      note="Vorstufe von Zimts\u00e4ure"),
            self.make(self.kl, substance="Aspirin", batch="ZIMT-7",
                      cancelled=True),
        ]
        self.make(self.kl, substance="Aspirin")
        self.make(self.ae, substance="CH-0012")
        self.make(None, substance="CH-0012")
        self.make(self.kl, substance="Aspirin", note="nichts")
        root = self.listing("?state=all&person=KL&q=zimt")
        self.assertEqual(sorted(numbers(root)),
                         sorted(t.number for t in found))
        self.assertEqual(field_value(root, "state"), "all")
        self.assertEqual(field_value(root, "person"), "KL")
        self.assertEqual(field_value(root, "q"), "zimt")

    def test_text_is_found_regardless_of_case(self) -> None:
        match = self.make(None, substance="CH-0012")
        self.make(None, substance="Aspirin")
        for query in ("zimt", "ZIMT", "Zimt", "zIMTs\u00c4ure"):
            with self.subTest(query=query):
                self.assertEqual(self.shown(f"?q={query}"),
                                 [match.number])

    def test_text_is_found_in_every_field(self) -> None:
        by_product = self.make(None, substance="Ferrocen")
        by_batch = self.make(None, substance="A", batch="FC-0815")
        by_note = self.make(None, substance="B", note="mit Ferrocen-Rest")
        self.make(None, substance="C")
        self.assertEqual(self.shown("?q=ferrocen"),
                         [by_product.number, by_note.number])
        self.assertEqual(self.shown("?q=fc-08"), [by_batch.number])

    def test_text_is_found_in_the_number(self) -> None:
        tasks = [self.make(None) for _ in range(3)]
        self.assertEqual(self.shown(f"?q={tasks[1].number.lower()}"),
                         [tasks[1].number])
        self.assertEqual(self.shown("?q=t-00"),
                         [t.number for t in tasks])

    def test_text_is_found_in_the_substances_key_and_names(self) -> None:
        match = self.make(None, substance="CH-0012")
        self.make(None, substance="Aspirin")
        for query in ("cinnamic-ac", "(e)-cinnamic", "zimts\u00e4ure"):
            with self.subTest(query=query):
                self.assertEqual(self.shown(f"?q={quote(query)}"),
                                 [match.number])

    def test_the_article_number_is_no_text_of_the_task(self) -> None:
        self.make(None, substance="CH-0012")
        self.assertEqual(self.shown("?q=ch-0012"), [])

    def test_person_filter(self) -> None:
        mine = self.make(self.kl, substance="A")
        hers = self.make(self.ae, substance="B")
        nobody = self.make(None, substance="C")
        self.assertEqual(self.shown("?person=KL"), [mine.number])
        self.assertEqual(self.shown("?person=AE"), [hers.number])
        self.assertEqual(self.shown("?person=none"), [nobody.number])
        self.assertEqual(self.shown(),
                         [mine.number, hers.number, nobody.number])
        root = self.listing("?person=none")
        self.assertEqual(field_value(root, "person"), "none")

    def test_filters_combine(self) -> None:
        match = self.make(self.kl, substance="Zimt", priority="high",
                          started=past(1))
        self.make(self.kl, substance="Zimt", priority="low")
        self.make(self.ae, substance="Zimt", priority="high")
        self.make(self.kl, substance="Aspirin", priority="high")
        self.assertEqual(
            self.shown("?person=KL&priority=high&state=running&q=zimt"),
            [match.number])


class NoneInitialsTests(ListCase):

    def test_initials_none_name_an_account(self) -> None:
        """`none` is the unassigned filter; the initials NONE name an
        account."""
        nobody = make_user("nobody", "NONE")
        mine = make_task(self.kl, assignee=nobody)
        unassigned = make_task(self.kl, assignee=None)
        self.assertEqual(self.shown("?person=NONE"), [mine.number])
        self.assertEqual(self.shown("?person=none"), [unassigned.number])
