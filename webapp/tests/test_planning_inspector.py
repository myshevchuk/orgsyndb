"""Tests of the planning list's inspector and its selection
(production-planning: Planning list)."""

import math
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote

from inventory.bookings import reverse

from . import Element, make_task
from .collection_support import accept
from .inventory_support import (LEVELS, TODAY, has_amount, has_number,
                                item_url, newest_movement, num)
from .planning_support import (CONTAINER_COLUMNS_DE, CONTAINER_COLUMNS_EN,
                               DETAIL_KEYS_DE, DETAIL_KEYS_EN, PLAN, WINDOW,
                               PlanningCase, block_of, blocks,
                               container_rows, containers_of, details,
                               details_of, has_date, has_word,
                               quarters_back, rows_by_article, shown_blocks,
                               task_texts)
from .widget_support import count_of, kv_rows, title_of

NEW_BLOCK = "XX-0000"


class InspectorCase(PlanningCase):

    def three(self) -> None:
        """Three articles in the order of the list with ``all=1``:
        ``NV-10``, ``NV-15`` and ``NV-25``."""
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-10", quantity=10)

    def block(self, article: str, query: str = "?all=1",
              signed_in: bool = False) -> Element:
        return block_of(self.get(PLAN + query, signed_in), article)


class BlockTests(InspectorCase):

    def setUp(self) -> None:
        super().setUp()
        self.three()

    def test_one_block_per_row(self) -> None:
        for query in ("", "?all=1"):
            with self.subTest(query=query):
                root = self.get(PLAN + query)
                self.assertEqual(sorted(blocks(root)),
                                 sorted(rows_by_article(root)))
        self.assertEqual(sorted(blocks(self.get(PLAN))),
                         ["NV-10", "NV-15"])

    def test_every_block_holds_both_widgets_hidden_or_not(self) -> None:
        root = self.get(PLAN + "?all=1")
        self.assertEqual(len(blocks(root)), 3)
        for article, found in blocks(root).items():
            with self.subTest(article=article):
                self.assertEqual(title_of(containers_of(found)),
                                 "Gebinde & Bedarf")
                self.assertEqual(title_of(details_of(found)),
                                 "Planungsdetails")
                self.assertEqual(containers_of(found).tag, "section")
                self.assertEqual(details_of(found).tag, "section")

    def test_the_widgets_in_english(self) -> None:
        accept(language="en")
        found = self.block("NV-10")
        self.assertEqual(title_of(containers_of(found)),
                         "Containers and demand")
        self.assertEqual(title_of(details_of(found)), "Planning details")

    def test_the_first_row_is_selected_without_a_selection(self) -> None:
        root = self.get(PLAN + "?all=1")
        self.assertEqual(shown_blocks(root), ["NV-10"])
        self.assertEqual(self.marked(root), ["NV-10"])

    def marked(self, root: Element) -> list[str]:
        """The articles of the rows that carry ``aria-current="true"``."""
        return [article for article, row in rows_by_article(root).items()
                if row.element.get("aria-current") == "true"]

    def test_the_inspector_follows_the_selection(self) -> None:
        """Scenario: The inspector follows the selection."""
        root = self.get(PLAN + "?all=1&selected=NV-15")
        found = blocks(root)
        self.assertEqual(shown_blocks(root), ["NV-15"])
        for article in ("NV-10", "NV-25"):
            with self.subTest(article=article):
                self.assertIn("hidden", found[article].attrs)
        self.assertNotIn("hidden", found["NV-15"].attrs)
        self.assertEqual(self.marked(root), ["NV-15"])
        again = self.get(PLAN + f"?all=1&selected={NEW_BLOCK}")
        self.assertEqual(shown_blocks(again), ["NV-10"])
        self.assertEqual(self.marked(again), ["NV-10"])

    def test_the_selected_block_has_no_hidden_ancestor(self) -> None:
        root = self.get(PLAN + "?all=1&selected=NV-25")
        node = blocks(root)["NV-25"].parent
        while node is not None:
            self.assertNotIn("hidden", node.attrs, node.tag)
            node = node.parent

    def test_the_order_of_selected_and_all_is_free(self) -> None:
        root = self.get(PLAN + "?selected=NV-15&all=1")
        self.assertEqual(shown_blocks(root), ["NV-15"])

    def test_a_selection_the_list_lacks_falls_back_to_the_first_row(
            self) -> None:
        """NV-25 has a forecast, but it is not listed without ``all``."""
        root = self.get(PLAN + "?selected=NV-25")
        self.assertEqual(shown_blocks(root), ["NV-10"])
        self.assertEqual(self.marked(root), ["NV-10"])
        self.assertNotIn("NV-25", blocks(root))

    def test_an_empty_selection_falls_back_to_the_first_row(self) -> None:
        root = self.get(PLAN + "?all=1&selected=")
        self.assertEqual(shown_blocks(root), ["NV-10"])

    def test_a_selection_must_be_the_article_number_itself(self) -> None:
        for wrong in ("nv-15", "NV-1", "NV-150"):
            with self.subTest(selected=wrong):
                root = self.get(PLAN + "?all=1&selected=" + quote(wrong))
                self.assertEqual(shown_blocks(root), ["NV-10"])

    def test_only_the_selected_row_carries_aria_current(self) -> None:
        root = self.get(PLAN + "?all=1&selected=NV-25")
        marked = [e for e in root.walk()
                  if e.get("aria-current") == "true"]
        self.assertEqual(len(marked), 1)
        self.assertIs(marked[0], rows_by_article(root)["NV-25"].element)

    def test_the_link_loads_the_page_with_the_selection(self) -> None:
        """Without the script, the ``Artikel`` link selects."""
        for article in ("NV-10", "NV-15", "NV-25"):
            with self.subTest(article=article):
                link = rows_by_article(
                    self.get(PLAN + "?all=1"))[article]["Artikel"].find("a")
                root = self.get(link.get("href"))
                self.assertEqual(shown_blocks(root), [article])
                self.assertEqual(self.marked(root), [article])
                self.assertEqual(len(rows_by_article(root)), 3)

    def test_a_selection_with_special_characters(self) -> None:
        number = "XY 1&2+3#4"
        self.planned_item(number, quantity=12, name="Sonderfall")
        rows = rows_by_article(self.get(PLAN + "?all=1"))
        link = rows[number]["Artikel"].find("a")
        root = self.get(link.get("href"))
        self.assertEqual(shown_blocks(root), [number])
        self.assertEqual(self.marked(root), [number])
        for node in root.walk():
            self.assertNotIn("XY", node.get("id", ""), node.tag)

    def test_a_selection_with_special_characters_by_hand(self) -> None:
        number = "XY 1&2+3#4"
        self.planned_item(number, quantity=12, name="Sonderfall")
        root = self.get(PLAN + "?all=1&selected=" + quote(number, safe=""))
        self.assertEqual(shown_blocks(root), [number])


class ContainersTests(InspectorCase):

    def article(self) -> None:
        """``NV-1`` of two items, whose demands per year are 4.25 (10 mg)
        and 0.5 (5 mg): 17 and 2 containers in a history of sixteen
        quarters, which the mean of the whole history gives."""
        self.parameters(history_quarters=16)
        large = self.item("NV-1", "NV-1", "10", "mg", 10)
        small = self.item("NV-1", "NV-1", "5", "mg", 10)
        quarters = quarters_back(16)
        self.enter(large, *quarters[0], 16)
        self.enter(large, *quarters[-5], 1)
        self.enter(small, *quarters[0], 1)
        self.enter(small, *quarters[-5], 1)
        self.large, self.small = large, small

    def test_containers_and_demand_in_one_table(self) -> None:
        """Scenario: Containers and demand in one table."""
        self.article()
        entries = {e.item.pk: e for e in self.forecast("NV-1").items}
        self.assertEqual(
            [e.per_year for e in entries.values()],
            [Decimal("0.5"), Decimal("4.3")])
        rows = container_rows(self.block("NV-1"))
        self.assertEqual(len(rows), 2)
        small, large = rows
        self.assertEqual(list(small), CONTAINER_COLUMNS_DE)
        for row, item, size in ((small, self.small, "5"),
                                (large, self.large, "10")):
            with self.subTest(size=size):
                link = row["Gebinde"].find("a")
                self.assertEqual(link.get("href"), item_url(item))
                self.assertTrue(has_amount(link.text(), size, "mg"),
                                link.text())
                self.assertTrue(has_number(row["Bestand"].text(), "10"),
                                row["Bestand"].text())
                self.assertIn(LEVELS[self.consumption(item).level],
                              row["Bestand"].text())
                self.assertEqual(
                    num(row["Reichweite"]),
                    math.floor(entries[item.pk].runway_on_hand))
        self.assertEqual(num(small["Bedarf/Jahr"]), Decimal("0.5"))
        self.assertIn("0,5", small["Bedarf/Jahr"].text())
        self.assertEqual(num(large["Bedarf/Jahr"]), Decimal("4.3"))
        self.assertIn("4,3", large["Bedarf/Jahr"].text())
        self.assertNotIn("4,25", large["Bedarf/Jahr"].text())

    def test_the_columns_in_english_with_the_decimal_point(self) -> None:
        accept(language="en")
        self.article()
        rows = container_rows(self.block("NV-1"))
        self.assertEqual(list(rows[0]), CONTAINER_COLUMNS_EN)
        self.assertEqual(rows[0]["Demand per year"].text(), "0.5")
        self.assertEqual(rows[1]["Demand per year"].text(), "4.3")

    def test_the_rows_run_in_the_order_of_the_item_list(self) -> None:
        """The smaller size is listed first, whatever the order in which
        the items were made."""
        self.article()
        links = [row["Gebinde"].find("a").get("href")
                 for row in container_rows(self.block("NV-1"))]
        self.assertEqual(links, [item_url(self.small), item_url(self.large)])

    def test_the_widget_names_the_article_and_has_no_count(self) -> None:
        self.article()
        found = containers_of(self.block("NV-1"))
        self.assertEqual(found.find(cls="widget__note").text(), "NV-1")
        self.assertIsNone(count_of(found))

    def test_the_runway_on_hand_of_each_size(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10)
        self.planned_item("NV-1", size="5", quantity=20)
        rows = container_rows(self.block("NV-1"))
        self.assertEqual([num(r["Reichweite"]) for r in rows], [60, 140])
        self.assertEqual([num(r["Bestand"]) for r in rows], [10, 20])

    def test_the_demand_per_year_of_each_size(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10, per_quarter=9)
        self.planned_item("NV-1", size="5", quantity=10, per_quarter=10)
        rows = container_rows(self.block("NV-1"))
        self.assertEqual([num(r["Bedarf/Jahr"]) for r in rows], [36, 40])

    def test_the_demand_is_rounded_half_up(self) -> None:
        """Sixteen quarters, one of 10 and fifteen of 9: 36.25 a year."""
        self.parameters(history_quarters=16)
        item = self.item("NV-1", "NV-1", "1", "mg", 10)
        for index, (year, quarter) in enumerate(quarters_back(16)):
            self.enter(item, year, quarter, 10 if index == 0 else 9)
        (row,) = container_rows(self.block("NV-1"))
        self.assertIn("36,3", row["Bedarf/Jahr"].text())
        self.assertNotIn("36,2", row["Bedarf/Jahr"].text())

    def test_an_item_without_demand_has_dashes(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10)
        self.item("NV-1", "NV-1", "5", "mg", 3)
        used, unused = container_rows(self.block("NV-1"))
        self.assertEqual(num(used["Reichweite"]), 60)
        self.assertEqual(used["Bedarf/Jahr"].text(), "36")
        self.assertEqual(unused["Reichweite"].text(), "–")
        self.assertEqual(unused["Bedarf/Jahr"].text(), "–")
        self.assertTrue(has_number(unused["Bestand"].text(), "3"),
                        unused["Bestand"].text())

    def test_each_block_holds_the_items_of_its_own_article(self) -> None:
        first = self.planned_item("NV-1", size="1", quantity=10)
        second = self.planned_item("NV-2", size="5", quantity=11)
        root = self.get(PLAN + "?all=1")
        for article, item in (("NV-1", first), ("NV-2", second)):
            with self.subTest(article=article):
                rows = container_rows(block_of(root, article))
                self.assertEqual(
                    [r["Gebinde"].find("a").get("href") for r in rows],
                    [item_url(item)])


class DetailsTests(InspectorCase):

    def test_the_keys_in_german(self) -> None:
        self.planned_item("NV-1", quantity=10)
        keys = [key for key, _ in kv_rows(
            details_of(self.block("NV-1")))]
        self.assertEqual(keys, DETAIL_KEYS_DE)

    def test_the_keys_in_english(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=10)
        keys = [key for key, _ in kv_rows(
            details_of(self.block("NV-1")))]
        self.assertEqual(keys, DETAIL_KEYS_EN)

    def test_the_note_is_the_priority(self) -> None:
        self.three()
        root = self.get(PLAN + "?all=1")
        for article, label in (("NV-10", "hoch"), ("NV-15", "mittel"),
                               ("NV-25", "niedrig")):
            with self.subTest(article=article):
                found = details_of(block_of(root, article))
                self.assertEqual(found.find(cls="widget__note").text(),
                                 label)

    def test_the_note_in_english(self) -> None:
        accept(language="en")
        self.three()
        found = details_of(self.block("NV-10"))
        self.assertEqual(found.find(cls="widget__note").text(), "high")

    def test_the_substance_links_its_page_with_its_shown_name(self) -> None:
        self.demo_item()
        cell = self.details("CH-0012")["Substanz"]
        links = cell.find_all("a")
        self.assertEqual([(a.text(), a.get("href")) for a in links],
                         [("(E)-Zimtsäure",
                           "/lab/registry/substances/cinnamic-acid/")])

    def test_the_substance_in_english(self) -> None:
        accept(language="en")
        self.demo_item()
        cell = self.details("CH-0012")["Substance"]
        self.assertEqual([a.text() for a in cell.find_all("a")],
                         ["(E)-Cinnamic acid"])

    def details(self, article: str) -> dict[str, Element]:
        return details(self.block(article))

    def test_the_last_delivery_is_the_latest_of_the_article(self) -> None:
        small = self.item("NV-1", "NV-1", "1", "mg", 30)
        large = self.item("NV-1", "NV-1", "5", "mg", 30)
        self.deliver(small, 1, date(2026, 8, 1))
        self.deliver(large, 1, date(2026, 9, 1))
        self.deliver(small, 1, date(2026, 7, 1))
        self.assertTrue(has_date(
            self.details("NV-1")["Letzte Lieferung"].text(),
            date(2026, 9, 1)))

    def test_reversed_deliveries_are_not_the_last(self) -> None:
        item = self.item("NV-1", "NV-1", "1", "mg", 30)
        self.deliver(item, 1, date(2026, 8, 1))
        self.deliver(item, 1, date(2026, 9, 1))
        reverse(self.kl, newest_movement(item), note="falsch")
        text = self.details("NV-1")["Letzte Lieferung"].text()
        self.assertTrue(has_date(text, date(2026, 8, 1)), text)
        self.assertFalse(has_date(text, date(2026, 9, 1)), text)

    def test_no_delivery_is_a_dash(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.assertEqual(self.details("NV-1")["Letzte Lieferung"].text(),
                         "–")

    def test_the_bulk_is_the_usable_bulk_in_its_unit(self) -> None:
        self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.vessel("NV-2", "mg", "360")
        text = self.details("NV-2")["Bulk"].text()
        self.assertTrue(has_amount(text, "340", "mg"), text)

    def test_the_bulk_is_in_the_bulk_unit(self) -> None:
        self.demo_item()
        self.vessel("CH-0012", "umol", "100")
        found = self.forecast("CH-0012")
        self.assertEqual(found.bulk_unit_label, "µmol")
        self.assertGreater(found.usable_bulk, 0)
        text = self.details("CH-0012")["Bulk"].text()
        self.assertIn("µmol", text)
        self.assertNotIn("mg", text)

    def test_the_runway_is_marked_when_rough(self) -> None:
        self.planned_item("NV-1", quantity=10)
        item = self.item("NV-2", "NV-2", "1", "mg", 10)
        self.orders(item, *[(date(2026, month, 10), size) for month, size
                            in enumerate([2, 3, 5, 8, 17, 23, 31, 40, 59],
                                         1)])
        rough = self.details("NV-1")["Reichweite"].text()
        exact = self.details("NV-2")["Reichweite"].text()
        self.assertEqual(num(rough), 60)
        self.assertTrue(has_word(rough, "grob"), rough)
        self.assertFalse(has_word(exact, "grob"), exact)

    def test_the_synthesis_time_names_its_basis(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.planned_item("NV-2", quantity=10)
        self.planned_item("NV-3", quantity=10)
        self.synthesis("NV-2", 25, TODAY - timedelta(days=60))
        for days in (30, 35, 40):
            self.synthesis("NV-3", days, TODAY - timedelta(days=days * 3))
        root = self.get(PLAN + "?all=1")
        cells = {a: details(block_of(root, a))["Synthesedauer"].text()
                 for a in ("NV-1", "NV-2", "NV-3")}
        self.assertEqual([num(cells[a]) for a in ("NV-1", "NV-2", "NV-3")],
                         [21, 25, 40])
        self.assertIn("Vorgabe", cells["NV-1"])
        self.assertIn("die letzte Synthese", cells["NV-2"])
        self.assertIn("längste der letzten 3 Synthesen", cells["NV-3"])

    def test_the_basis_in_english(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=10)
        self.planned_item("NV-3", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-3", days, TODAY - timedelta(days=days * 3))
        root = self.get(PLAN + "?all=1")
        self.assertIn("default", details(block_of(root, "NV-1"))
                      ["Synthesis time"].text())
        self.assertIn("longest of the last 3 syntheses",
                      details(block_of(root, "NV-3"))
                      ["Synthesis time"].text())

    def test_the_latest_start(self) -> None:
        self.planned_item("NV-1", quantity=10)
        text = self.details("NV-1")["Spätester Start"].text()
        self.assertTrue(has_date(text, date(2026, 11, 15)), text)

    def test_no_latest_start_is_a_dash(self) -> None:
        item = self.item("NV-9", "NV-9", "1", "mg", 10)
        for year, quarter in WINDOW:
            self.enter(item, year, quarter,
                       1 if (year, quarter) == WINDOW[-5] else 0)
        self.vessel("NV-9", "mg", "3000")
        self.assertEqual(self.details("NV-9")["Spätester Start"].text(), "–")

    def test_each_block_shows_the_figures_of_its_own_article(self) -> None:
        self.three()
        root = self.get(PLAN + "?all=1")
        shown = {a: num(details(block_of(root, a))["Reichweite"])
                 for a in ("NV-10", "NV-15", "NV-25")}
        self.assertEqual(shown, {
            a: math.floor(self.forecast(a).runway)
            for a in ("NV-10", "NV-15", "NV-25")})
        self.assertEqual(len(set(shown.values())), 3)


class InspectorTasksTests(InspectorCase):
    """The ``Aufgaben`` row of ``Planungsdetails``."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def cell(self, article: str = "NV-1") -> Element:
        return details(self.block(article))["Aufgaben"]

    def test_no_task_is_a_dash(self) -> None:
        self.assertEqual(self.cell().text(), "–")

    def test_the_tasks_in_the_order_of_the_list(self) -> None:
        planned = make_task(self.kl, substance="NV-1")
        running = self.running("NV-1", 14)
        other = make_task(self.kl, substance="nv-1")
        make_task(self.kl, substance="NV-1", cancelled=True)
        root = self.get(PLAN + "?all=1")
        cell = details(block_of(root, "NV-1"))["Aufgaben"]
        links = [a for a in cell.find_all("a")
                 if a.get("href", "").startswith("/lab/tasks/")]
        self.assertEqual([a.text() for a in links],
                         [running.number, planned.number, other.number])
        self.assertEqual([a.get("href") for a in links],
                         [f"/lab/tasks/{t.number}/"
                          for t in (running, planned, other)])
        listed = rows_by_article(root)["NV-1"]["Aufgaben"]
        self.assertEqual(list(task_texts(listed)),
                         [running.number, planned.number, other.number])

    def test_each_task_shows_its_state_and_expected_end(self) -> None:
        planned = make_task(self.kl, substance="NV-1")
        running = self.running("NV-1", 14)
        parts = task_texts(self.cell())
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
        planned = make_task(self.kl, substance="NV-1")
        parts = task_texts(self.cell())
        self.assertTrue(has_date(parts[planned.number],
                                 TODAY + timedelta(days=40)),
                        parts[planned.number])

    def test_a_running_task_past_its_time_ends_today(self) -> None:
        task = self.running("NV-1", 60)
        self.assertTrue(has_date(task_texts(self.cell())[task.number],
                                 TODAY))

    def test_a_task_in_time_is_not_marked(self) -> None:
        make_task(self.kl, substance="NV-1")
        self.running("NV-1", 14)
        self.assertNotIn("verspätet", self.cell().text())

    def test_the_late_task_is_marked(self) -> None:
        self.planned_item("NV-7", quantity=7)
        planned = make_task(self.kl, substance="NV-7")
        running = self.running("NV-7", 20)
        parts = task_texts(self.cell("NV-7"))
        self.assertIn("verspätet", parts[planned.number])
        self.assertNotIn("verspätet", parts[running.number])

    def test_the_mark_in_english(self) -> None:
        accept(language="en")
        self.planned_item("NV-5", quantity=5)
        task = self.running("NV-5", 3)
        cell = details(self.block("NV-5"))["Tasks"]
        self.assertIn("late", task_texts(cell)[task.number])

    def test_the_tasks_of_other_articles_are_not_listed(self) -> None:
        self.planned_item("NV-2", quantity=10)
        task = make_task(self.kl, substance="NV-2")
        root = self.get(PLAN + "?all=1")
        self.assertIn(task.number, details(block_of(root, "NV-2"))
                      ["Aufgaben"].text())
        self.assertNotIn(task.number, block_of(root, "NV-1").text())
