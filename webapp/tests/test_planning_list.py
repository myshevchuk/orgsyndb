"""Tests of the planning list (production-planning: Planning list)."""

import re
from datetime import date, timedelta
from decimal import Decimal

from inventory.bookings import reverse
from tasks.models import Task

from . import (build_index, field_value, make_task, page, table,
               task_form_data)
from .inventory_support import (BULK, LEVELS, TODAY, has_amount, has_number,
                                item_url, newest_movement, num)
from .planning_support import (COLUMNS_DE, COLUMNS_EN, PLAN, WINDOW,
                               PlanningCase, has_date, quarters_back,
                               rows_by_article)

CHECK_DE = "Bulk prüfen"
PLAN_DE = "Synthese planen"
NEW_TASK = "/lab/tasks/new/"


class ListCase(PlanningCase):

    def articles(self, query: str = "", signed_in: bool = False):
        """The rows of the list by article number."""
        root = self.get(PLAN + query, signed_in)
        if root.find("table") is None:
            return {}
        return rows_by_article(root)

    def shown(self, query: str = "") -> list[str]:
        return list(self.articles(query))

    def actions(self, article: str, signed_in: bool = False,
                query: str = "?all=1"):
        return self.articles(query, signed_in)[article]["Maßnahmen"]


class SelectionTests(ListCase):

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-10", quantity=10)
        self.item("NV-0", size="1", unit="mg", quantity=10)

    def test_high_and_medium_are_listed_ordered_by_slack(self) -> None:
        self.assertEqual(self.shown(), ["NV-10", "NV-15"])

    def test_all_lists_every_article_with_a_forecast(self) -> None:
        self.assertEqual(self.shown("?all=1"),
                         ["NV-10", "NV-15", "NV-25"])

    def test_a_late_article_comes_first(self) -> None:
        self.planned_item("NV-5", quantity=5)
        self.assertEqual(self.shown(), ["NV-5", "NV-10", "NV-15"])

    def test_equal_slack_goes_by_article_number(self) -> None:
        self.planned_item("NV-B", quantity=10)
        self.planned_item("NV-A", quantity=10)
        self.assertEqual(self.shown(), ["NV-10", "NV-A", "NV-B", "NV-15"])

    def test_an_article_is_one_row_whatever_its_sizes(self) -> None:
        self.planned_item("NV-10", size="5", quantity=10)
        self.assertEqual(self.shown().count("NV-10"), 1)

    def test_the_page_is_public(self) -> None:
        self.assertEqual(self.client.get(PLAN).status_code, 200)
        self.assertEqual(self.client.get(PLAN + "?all=1").status_code, 200)

    def test_the_bands_choose_the_rows(self) -> None:
        self.parameters(high_days=5, medium_days=20)
        self.assertEqual(self.shown(), ["NV-10"])
        self.assertEqual(self.shown("?all=1"),
                         ["NV-10", "NV-15", "NV-25"])


class ColumnTests(ListCase):

    def test_german_columns(self) -> None:
        self.planned_item("NV-1", quantity=10)
        header, _ = table(self.get(PLAN))
        self.assertEqual(header, COLUMNS_DE)

    def test_english_columns(self) -> None:
        self.use_index(build_index("en"))
        self.planned_item("NV-1", quantity=10)
        header, _ = table(self.get(PLAN))
        self.assertEqual(header, COLUMNS_EN)

    def test_the_row_of_an_article(self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        row = self.articles()["NV-1"]
        self.assertEqual(row["Name"].text(), "Probe Eins")
        self.assertEqual(num(row["Reichweite"]), 60)
        self.assertEqual(num(row["Synthesedauer"]), 21)
        self.assertTrue(has_date(row["Spätester Start"].text(),
                                 date(2026, 11, 15)))
        self.assertIn("hoch", row["Priorität"].text())

    def test_the_name_is_that_of_the_first_item(self) -> None:
        self.item("NV-1", "Erste", "5", "mg", 1)
        self.planned_item("NV-1", size="10", quantity=10, name="Zweite")
        self.assertEqual(self.articles("?all=1")["NV-1"]["Name"].text(),
                         "Erste")

    def test_the_containers_in_the_order_of_the_item_list(self) -> None:
        self.planned_item("NV-1", size="10", quantity=10)
        self.planned_item("NV-1", size="5", quantity=3)
        cell = self.articles()["NV-1"]["Gebinde"]
        text = cell.text()
        small = re.search(r"(?<![\d,.])5\s*mg", text)
        large = re.search(r"(?<![\d,.])10\s*mg", text)
        self.assertTrue(small and large, text)
        self.assertLess(small.start(), large.start())
        self.assertTrue(has_number(text, "3"), text)
        self.assertTrue(has_number(text, "10"), text)

    def test_the_containers_show_the_level_and_the_runway(self) -> None:
        item = self.planned_item("NV-1", quantity=1)
        level = self.consumption(item).level
        self.assertEqual(level, "critical")
        cell = self.articles()["NV-1"]["Gebinde"]
        self.assertIn(LEVELS[level], cell.text())
        self.assertTrue(has_number(cell.text(), "2"), cell.text())

    def test_the_runway_on_hand_of_each_size(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10)
        self.planned_item("NV-1", size="5", quantity=20)
        text = self.articles()["NV-1"]["Gebinde"].text()
        self.assertTrue(has_number(text, "60"), text)
        self.assertTrue(has_number(text, "140"), text)

    def test_the_demand_per_year_of_each_size(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10, per_quarter=9)
        self.planned_item("NV-1", size="5", quantity=10, per_quarter=10)
        text = self.articles()["NV-1"]["Bedarf/Jahr"].text()
        found = [Decimal(n.replace(",", "."))
                 for n in re.findall(r"\d+(?:,\d+)?", text)]
        self.assertEqual(found, [Decimal(36), Decimal(40)], text)

    def test_the_demand_per_year_is_rounded_half_up(self) -> None:
        """Sixteen quarters, one of 10 and fifteen of 9: 36.25 a year."""
        self.parameters(history_quarters=16)
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        for index, (year, quarter) in enumerate(quarters_back(16)):
            self.enter(item, year, quarter, 10 if index == 0 else 9)
        text = self.articles("?all=1")["NV-1"]["Bedarf/Jahr"].text()
        self.assertIn("36,3", text)
        self.assertNotIn("36,2", text)

    def test_the_english_numbers(self) -> None:
        self.use_index(build_index("en"))
        self.planned_item("NV-1", quantity=10)
        row = self.articles()["NV-1"]
        text = row["Demand per year"].text()
        self.assertEqual([Decimal(n) for n in re.findall(r"\d+(?:\.\d+)?",
                                                         text)], [36], text)
        self.assertTrue(has_date(row["Latest start"].text(),
                                 date(2026, 11, 15)))

    def test_the_last_delivery_is_the_latest_of_the_article(self) -> None:
        small = self.item("NV-1", "NV-1", "1", "mg", 30)
        large = self.item("NV-1", "NV-1", "5", "mg", 30)
        self.deliver(small, 1, date(2026, 8, 1))
        self.deliver(large, 1, date(2026, 9, 1))
        self.deliver(small, 1, date(2026, 7, 1))
        row = self.articles("?all=1")["NV-1"]
        self.assertTrue(has_date(row["Letzte Lieferung"].text(),
                                 date(2026, 9, 1)))

    def test_reversed_deliveries_are_not_the_last(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 30)
        self.deliver(item, 1, date(2026, 8, 1))
        self.deliver(item, 1, date(2026, 9, 1))
        reverse(self.kl, newest_movement(item), note="falsch")
        row = self.articles("?all=1")["NV-1"]
        text = row["Letzte Lieferung"].text()
        self.assertTrue(has_date(text, date(2026, 8, 1)), text)
        self.assertFalse(has_date(text, date(2026, 9, 1)), text)

    def test_the_bulk_is_the_usable_bulk(self) -> None:
        self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.lot("NV-2", "mg", "360")
        row = self.articles()["NV-2"]
        self.assertTrue(has_amount(row["Bulk"].text(), "340", "mg"),
                        row["Bulk"].text())
        self.assertEqual(num(row["Reichweite"]), 62)
        self.assertIn("hoch", row["Priorität"].text())
        self.assertTrue(has_date(row["Spätester Start"].text(),
                                 TODAY + timedelta(days=13)))

    def test_the_synthesis_time_follows_past_syntheses(self) -> None:
        self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        self.assertEqual(num(self.articles()["NV-1"]["Synthesedauer"]), 40)

    def test_the_latest_start_may_lie_in_the_past(self) -> None:
        self.planned_item("NV-7", quantity=7)
        text = self.articles()["NV-7"]["Spätester Start"].text()
        self.assertTrue(has_date(text, TODAY - timedelta(days=11)), text)


class ParametersLineTests(ListCase):

    def line(self, **over) -> str:
        if over:
            self.parameters(**over)
        self.planned_item("NV-1", quantity=10)
        root = self.get(PLAN)
        return root.text().replace(root.find("table").text(), "")

    def test_the_defaults_in_force(self) -> None:
        text = self.line()
        self.assertRegex(text, r"(?<![\d,.])(?:0,95|95)(?!\d)")
        for number in ("28", "21", "12", "6", "14", "56", "365"):
            with self.subTest(number=number):
                self.assertTrue(has_number(text, number), text)

    def test_the_parameters_in_force(self) -> None:
        text = self.line(certainty=0.9, buffer_days=33,
                         default_synthesis_days=17, history_quarters=9,
                         min_orders=7, high_days=10, medium_days=40,
                         target_days=222)
        self.assertRegex(text, r"(?<![\d,.])(?:0,9|90)(?!\d)")
        for number in ("33", "17", "9", "7", "10", "40", "222"):
            with self.subTest(number=number):
                self.assertTrue(has_number(text, number), text)


class TasksColumnTests(ListCase):

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def cell(self, article: str = "NV-1"):
        return self.articles("?all=1")[article]["Aufgaben"]

    def segments(self, cell, tasks) -> dict[str, str]:
        """The text of ``cell`` from each task's number to the next."""
        text = cell.text()
        spots = sorted((text.index(t.number), t.number) for t in tasks)
        ends = [s for s, _ in spots[1:]] + [len(text)]
        return {number: text[start:end]
                for (start, number), end in zip(spots, ends)}

    def test_planned_and_running_tasks_running_first_then_by_number(
            self) -> None:
        planned = make_task(self.kl, product="NV-1")
        running = self.running("NV-1", 14)
        other = make_task(self.kl, product="nv-1")
        make_task(self.kl, product="NV-1", cancelled=True)
        self.synthesis("NV-1", 10, date(2026, 9, 1))
        cell = self.cell()
        links = [a for a in cell.find_all("a")
                 if a.get("href", "").startswith("/lab/tasks/")]
        self.assertEqual([a.text() for a in links],
                         [running.number, planned.number, other.number])
        self.assertEqual([a.get("href") for a in links],
                         [f"/lab/tasks/{t.number}/"
                          for t in (running, planned, other)])

    def test_each_task_shows_its_state_and_expected_end(self) -> None:
        planned = make_task(self.kl, product="NV-1")
        running = self.running("NV-1", 14)
        parts = self.segments(self.cell(), [planned, running])
        self.assertIn("In Arbeit", parts[running.number])
        self.assertTrue(has_date(parts[running.number],
                                 TODAY + timedelta(days=7)),
                        parts[running.number])
        self.assertIn("Geplant", parts[planned.number])
        self.assertTrue(has_date(parts[planned.number],
                                 TODAY + timedelta(days=21)),
                        parts[planned.number])

    def test_the_expected_end_follows_the_synthesis_time(self) -> None:
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        planned = make_task(self.kl, product="NV-1")
        text = self.cell().text()
        self.assertTrue(has_date(text, TODAY + timedelta(days=40)), text)
        self.assertIn(planned.number, text)

    def test_a_running_task_past_its_time_ends_today(self) -> None:
        self.running("NV-1", 60)
        self.assertTrue(has_date(self.cell().text(), TODAY))

    def test_a_task_in_time_is_not_late(self) -> None:
        make_task(self.kl, product="NV-1")
        self.running("NV-1", 14)
        self.assertNotIn("verspätet", self.cell().text())

    def test_late_synthesis(self) -> None:
        """Scenario: Late synthesis."""
        self.planned_item("NV-5", quantity=5)
        task = self.running("NV-5", 3)
        self.assertIn("verspätet", self.cell("NV-5").text())
        self.assertIn(task.number, self.cell("NV-5").text())

    def test_only_the_late_task_is_marked(self) -> None:
        """Slack 38.5 days less the buffer: a planned task, which needs
        21 days, is late, a task started 20 days ago is not."""
        self.planned_item("NV-7", quantity=7)
        planned = make_task(self.kl, product="NV-7")
        running = self.running("NV-7", 20)
        parts = self.segments(self.cell("NV-7"), [planned, running])
        self.assertIn("verspätet", parts[planned.number])
        self.assertNotIn("verspätet", parts[running.number])

    def test_the_english_mark(self) -> None:
        self.use_index(build_index("en"))
        self.planned_item("NV-5", quantity=5)
        self.running("NV-5", 3)
        row = self.articles("?all=1")["NV-5"]
        self.assertIn("late", row["Tasks"].text())

    def test_a_task_of_a_compound_is_listed_with_the_article(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        task = make_task(self.kl, product="cinnamic-acid")
        self.assertIn(task.number, self.cell("CH-0012").text())

    def test_a_task_that_matches_two_articles_is_listed_with_both(
            self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        self.planned_item("cinnamic-acid", size="10", unit="umol",
                          quantity=10)
        task = make_task(self.kl, product="CH-0012")
        self.assertIn(task.number, self.cell("CH-0012").text())
        self.assertIn(task.number, self.cell("cinnamic-acid").text())

    def test_other_articles_tasks_are_not_listed(self) -> None:
        self.planned_item("NV-2", quantity=10)
        task = make_task(self.kl, product="NV-2")
        self.assertNotIn(task.number, self.cell("NV-1").text())

    def test_the_article_priority_ignores_its_tasks(self) -> None:
        self.running("NV-1", 14)
        self.assertIn("hoch", self.articles()["NV-1"]["Priorität"].text())


class ActionTests(ListCase):

    def test_actions(self) -> None:
        """Scenario: Actions."""
        first = self.planned_item("NV-1", quantity=1)
        self.lot("NV-1", "mg", "20")
        self.planned_item("NV-2", quantity=10)
        self.lot("NV-2", "umol", "1000")
        self.planned_item("NV-3", quantity=10)
        rows = self.articles(signed_in=True)
        self.assertEqual(set(rows), {"NV-1", "NV-2", "NV-3"})
        self.assertIn("niedrig", rows["NV-1"]["Priorität"].text())
        fill = [a for a in rows["NV-1"]["Maßnahmen"].find_all("a")
                if a.text() == "Abfüllen 1 mg"]
        self.assertEqual([a.get("href") for a in fill],
                         [item_url(first, "fill")])
        second = rows["NV-2"]["Maßnahmen"]
        self.assertTrue([a for a in second.find_all("a")
                         if a.text() == CHECK_DE and a.get("href") == BULK])
        self.assertNotIn(PLAN_DE, second.text())
        third = rows["NV-3"]["Maßnahmen"]
        plan_links = [a for a in third.find_all("a")
                      if a.text() == PLAN_DE]
        self.assertEqual([a.get("href") for a in plan_links],
                         [NEW_TASK + "?product=NV-3"])
        self.assertNotIn(CHECK_DE, third.text())
        self.assertNotIn("Abfüllen", third.text())

    def test_a_row_that_needs_nothing_offers_nothing(self) -> None:
        self.planned_item("NV-1", quantity=25)
        text = self.actions("NV-1").text()
        for label in ("Abfüllen", CHECK_DE, PLAN_DE):
            self.assertNotIn(label, text)

    def test_fill_is_due_below_the_buffer(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.lot("NV-1", "mg", "20")
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())
        self.parameters(buffer_days=61)
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text() == "Abfüllen 1 mg"]
        self.assertEqual([a.get("href") for a in links],
                         [item_url(item, "fill")])

    def test_fill_needs_a_container_in_the_lots(self) -> None:
        self.planned_item("NV-1", quantity=1)
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())
        self.lot("NV-1", "mg", "0.5")
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())
        self.lot("NV-1", "mg", "1")
        self.assertIn("Abfüllen 1 mg", self.actions("NV-1").text())

    def test_fill_is_not_offered_from_a_used_up_lot(self) -> None:
        self.planned_item("NV-1", quantity=1)
        self.lot("NV-1", "mg", "0")
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())

    def test_fill_is_decided_per_size(self) -> None:
        small = self.planned_item("NV-1", size="1", quantity=1)
        self.planned_item("NV-1", size="5", quantity=40)
        self.lot("NV-1", "mg", "20")
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text().startswith("Abfüllen")]
        self.assertEqual([(a.text(), a.get("href")) for a in links],
                         [("Abfüllen 1 mg", item_url(small, "fill"))])

    def test_fill_for_each_size_that_is_low(self) -> None:
        small = self.planned_item("NV-1", size="1", quantity=1)
        large = self.planned_item("NV-1", size="5", quantity=1)
        self.lot("NV-1", "mg", "50")
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text().startswith("Abfüllen")]
        self.assertEqual([(a.text(), a.get("href")) for a in links],
                         [("Abfüllen 1 mg", item_url(small, "fill")),
                          ("Abfüllen 5 mg", item_url(large, "fill"))])

    def test_fill_is_not_offered_for_a_lot_that_does_not_convert(
            self) -> None:
        self.planned_item("NV-1", quantity=1)
        self.lot("NV-1", "umol", "1000")
        text = self.actions("NV-1").text()
        self.assertNotIn("Abfüllen", text)
        self.assertIn(CHECK_DE, text)

    def test_the_size_is_shown_as_the_item_list_shows_it(self) -> None:
        self.planned_item("NV-1", size="2.5", quantity=1)
        self.lot("NV-1", "mg", "50")
        self.assertIn("Abfüllen 2,5 mg", self.actions("NV-1").text())

    def test_check_bulk_for_a_lot_that_does_not_convert(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.lot("NV-1", "umol", "1000")
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text() == CHECK_DE]
        self.assertEqual([a.get("href") for a in links], [BULK])

    def test_check_bulk_is_not_offered_for_a_used_up_lot(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.lot("NV-1", "umol", "0")
        self.assertNotIn(CHECK_DE, self.actions("NV-1").text())

    def test_check_bulk_is_not_offered_when_every_lot_converts(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.lot("NV-1", "g", "1")
        self.assertNotIn(CHECK_DE, self.actions("NV-1").text())

    def test_plan_synthesis_for_high_and_medium(self) -> None:
        self.planned_item("NV-10", quantity=10)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-25", quantity=25)
        for article, offered in (("NV-10", True), ("NV-15", True),
                                 ("NV-25", False)):
            with self.subTest(article=article):
                links = [a for a in self.actions(
                    article, True).find_all("a") if a.text() == PLAN_DE]
                self.assertEqual(
                    [a.get("href") for a in links],
                    [NEW_TASK + f"?product={article}"] if offered else [])

    def test_plan_synthesis_is_for_signed_in_users(self) -> None:
        self.planned_item("NV-1", quantity=10)
        cell = self.actions("NV-1")
        self.assertFalse([a for a in cell.find_all("a")
                          if a.get("href", "").startswith(NEW_TASK)])
        cell = self.actions("NV-1", True)
        self.assertTrue([a for a in cell.find_all("a")
                         if a.get("href", "").startswith(NEW_TASK)])

    def test_a_planned_or_running_task_stops_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.planned_item("NV-2", quantity=10)
        self.planned_item("NV-3", quantity=10)
        make_task(self.kl, product="NV-1")
        self.running("NV-2", 5)
        for article in ("NV-1", "NV-2"):
            with self.subTest(article=article):
                self.assertNotIn(PLAN_DE,
                                 self.actions(article, True).text())
        self.assertIn(PLAN_DE, self.actions("NV-3", True).text())

    def test_other_tasks_do_not_stop_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.synthesis("NV-1", 10, date(2026, 9, 1))
        make_task(self.kl, product="NV-1", cancelled=True)
        make_task(self.kl, product="NV-9")
        self.assertIn(PLAN_DE, self.actions("NV-1", True).text())

    def test_a_task_of_the_same_compound_stops_the_offer(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        make_task(self.kl, product="cinnamic-acid")
        self.assertNotIn(PLAN_DE, self.actions("CH-0012", True).text())

    def test_a_lot_that_does_not_convert_stops_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.lot("NV-1", "umol", "1000")
        text = self.actions("NV-1", True).text()
        self.assertNotIn(PLAN_DE, text)
        self.assertIn(CHECK_DE, text)

    def test_a_lot_that_converts_does_not_stop_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.lot("NV-1", "mg", "1.5")
        self.assertIn(PLAN_DE, self.actions("NV-1", True).text())

    def test_a_used_up_lot_that_does_not_convert_does_not_stop_it(
            self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.lot("NV-1", "umol", "0")
        self.assertIn(PLAN_DE, self.actions("NV-1", True).text())

    def test_an_article_to_be_listed_for_its_action_alone(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.planned_item("NV-2", quantity=25)
        self.lot("NV-2", "umol", "1000")
        self.assertEqual(self.shown(), ["NV-2"])

    def test_the_english_texts(self) -> None:
        self.use_index(build_index("en"))
        self.planned_item("NV-1", quantity=1)
        self.lot("NV-1", "mg", "20")
        self.planned_item("NV-2", quantity=10)
        self.lot("NV-2", "umol", "1000")
        self.planned_item("NV-3", quantity=10)
        rows = self.articles(signed_in=True)
        self.assertIn("Fill 1 mg", rows["NV-1"]["Actions"].text())
        self.assertIn("Check bulk", rows["NV-2"]["Actions"].text())
        self.assertIn("Plan synthesis", rows["NV-3"]["Actions"].text())
        self.assertNotIn("Plan synthesis", rows["NV-2"]["Actions"].text())


class CreatedTaskTests(ListCase):

    def test_created_task_matches_its_article(self) -> None:
        """Scenario: Created task matches its article."""
        self.planned_item("NV-3", quantity=10)
        self.client.force_login(self.kl)
        row = self.articles(signed_in=True)["NV-3"]
        link = [a for a in row["Maßnahmen"].find_all("a")
                if a.text() == PLAN_DE][0]
        form = self.get(link.get("href"))
        product = field_value(form, "product")
        self.assertEqual(product, "NV-3")
        done = self.client.post(NEW_TASK, task_form_data(product=product))
        self.assertEqual(done.status_code, 302)
        task = Task.objects.get()
        row = self.articles(signed_in=True)["NV-3"]
        self.assertIn(task.number, row["Aufgaben"].text())
        self.assertNotIn(PLAN_DE, row["Maßnahmen"].text())

    def test_the_task_of_a_compound_article(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        self.client.force_login(self.kl)
        row = self.articles(signed_in=True)["CH-0012"]
        link = [a for a in row["Maßnahmen"].find_all("a")
                if a.text() == PLAN_DE][0]
        self.assertEqual(link.get("href"), NEW_TASK + "?product=CH-0012")


class PageTests(ListCase):

    def test_the_page_has_no_script(self) -> None:
        self.planned_item("NV-1", quantity=10)
        response = self.client.get(PLAN)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script", response.content.decode().lower())
        self.assertIsNone(page(response).find("script"))

    def test_the_page_is_German_or_English_by_the_index(self) -> None:
        self.assertEqual(
            page(self.client.get(PLAN)).find("html").get("lang"), "de")
        self.use_index(build_index("en"))
        self.assertEqual(
            page(self.client.get(PLAN)).find("html").get("lang"), "en")

    def test_an_empty_inventory_lists_nothing(self) -> None:
        response = self.client.get(PLAN)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        if root.find("table") is not None:
            self.assertEqual(rows_by_article(root), {})
