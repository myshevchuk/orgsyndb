"""Tests of the details of an article in the planning list
(production-planning: Planning list), which ``/lab/planning/<article
number>/detail/`` answers with."""

import math
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from inventory.bookings import reverse

from . import Element, make_task, page
from .collection_support import accept
from .inventory_support import (LEVELS, TODAY, has_amount, has_number,
                                item_url, newest_movement, num)
from .main_lists_support import (heading_of, key_number, replaced,
                                 texts_of_links, unsorted_reasons)
from .planning_support import (CONTAINER_COLUMNS_DE, CONTAINER_COLUMNS_EN,
                               DETAIL_KEYS_DE, DETAIL_KEYS_EN, HTMX, PLAN,
                               WINDOW, PlanningCase, container_rows,
                               containers_of, detail_url, details,
                               details_of, has_date, has_word, pane_of,
                               quarters_back, rows_by_article, task_texts)
from .test_inventory_dialogs import current, vary_of
from .widget_support import kv_rows

class InspectorCase(PlanningCase):

    def three(self) -> None:
        """Three articles in the order of the list with ``all=1``:
        ``NV-10``, ``NV-15`` and ``NV-25``."""
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-10", quantity=10)

    def block(self, article: str, query: str = "?all=1",
              signed_in: bool = False) -> Element:
        """The pane of ARTICLE as the details endpoint answers."""
        return self.pane(article, query, signed_in)


class EndpointTests(InspectorCase):
    """The endpoint ``/lab/planning/<article number>/detail/``."""

    def setUp(self) -> None:
        super().setUp()
        self.three()

    def test_htmx_gets_the_pane_alone(self) -> None:
        response = self.client.get(detail_url("NV-15", "?all=1"), **HTMX)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for tag in ("html", "head", "body", "main", "nav", "script"):
            self.assertEqual(root.find_all(tag), [], tag)
        found = [c for c in root.children if isinstance(c, Element)]
        self.assertEqual([(e.get("id"), e.get("data-item")) for e in found],
                         [("item-detail", "NV-15")])

    def test_the_page_is_public(self) -> None:
        self.assertEqual(
            self.client.get(detail_url("NV-15"), **HTMX).status_code, 200)

    def test_an_article_the_list_lacks_has_details_too(self) -> None:
        """``NV-25`` is listed only with ``all=1``."""
        self.assertNotIn("NV-25", rows_by_article(self.get(PLAN)))
        found = self.pane("NV-25", "")
        self.assertEqual(found.get("data-item"), "NV-25")

    def test_the_address_keeps_the_query_of_the_row(self) -> None:
        for query, wanted in (
                ("?all=1", f"{PLAN}?all=1&selected=NV-15"),
                ("?all=1&show=late",
                 f"{PLAN}?all=1&show=late&selected=NV-15"),
                ("?show=high", f"{PLAN}?show=high&selected=NV-15"),
                ("", f"{PLAN}?selected=NV-15")):
            with self.subTest(query=query):
                response = self.client.get(detail_url("NV-15", query),
                                           **HTMX)
                self.assertEqual(replaced(self, response), wanted)

    def test_the_address_keeps_the_filters_and_the_order_of_the_page(
            self) -> None:
        response = self.client.get(
            detail_url("NV-15", "?all=1"),
            **current(f"{PLAN}?all=1&show=high&sort=priority&dir=desc"
                      "&selected=NV-10"))
        self.assertEqual(
            replaced(self, response),
            f"{PLAN}?all=1&show=high&sort=priority&dir=desc"
            "&selected=NV-15")

    def test_another_host_is_not_trusted(self) -> None:
        response = self.client.get(
            detail_url("NV-15", "?all=1"),
            **current(f"{PLAN}?show=late&sort=priority", host="evil.example"))
        self.assertEqual(replaced(self, response),
                         f"{PLAN}?all=1&selected=NV-15")

    def test_without_htmx_the_list_is_the_answer(self) -> None:
        for query, wanted in (("?all=1", {"all": ["1"]}),
                              ("?all=1&show=late",
                               {"all": ["1"], "show": ["late"]}),
                              ("", {})):
            with self.subTest(query=query):
                response = self.client.get(detail_url("NV-15", query))
                self.assertEqual(response.status_code, 302)
                found = urlsplit(response["Location"])
                self.assertEqual(found.path, PLAN)
                self.assertEqual(parse_qs(found.query),
                                 {**wanted, "selected": ["NV-15"]})

    def test_an_article_without_a_forecast_is_not_found(self) -> None:
        self.item("NV-0", size="1", unit="mg", quantity=10)
        self.assertEqual(
            self.client.get(detail_url("NV-15"), **HTMX).status_code, 200)
        for number in ("NV-0", "XX-0000", "nv-15", "NV-1", "NV-150"):
            for extra in ({}, HTMX):
                with self.subTest(number=number, htmx=bool(extra)):
                    self.assertEqual(
                        self.client.get(detail_url(number, "?all=1"),
                                        **extra).status_code, 404)

    def test_the_answer_varies_on_the_headers_it_reads(self) -> None:
        response = self.client.get(detail_url("NV-15"), **HTMX)
        self.assertLessEqual({"hx-request", "hx-current-url"},
                             vary_of(response))

    def test_the_path_is_one_segment_whatever_the_number(self) -> None:
        number = "XY 1&2+3#4/5"
        self.planned_item(number, quantity=12, name="Sonderfall")
        found = self.pane(number)
        self.assertEqual(found.get("data-item"), number)
        self.assertIn("Sonderfall", found.text())
        response = self.client.get(detail_url(number, "?all=1"), **HTMX)
        found = urlsplit(replaced(self, response))
        self.assertEqual(found.path, PLAN)
        self.assertEqual(parse_qs(found.query),
                         {"all": ["1"], "selected": [number]})


class PaneTests(InspectorCase):
    """What the pane shows: the article as heading and two parts."""

    def test_the_heading_names_the_article_and_its_number(self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        heading = heading_of(self.pane("NV-1"))
        self.assertIn("Probe Eins", heading.text())
        self.assertIn("NV-1", heading.text())

    def test_the_heading_names_the_shown_name_of_the_substance(self) -> None:
        self.demo_item()
        self.assertIn("(E)-Zimtsäure",
                      heading_of(self.pane("CH-0012")).text())
        accept(language="en")
        self.assertIn("(E)-Cinnamic acid",
                      heading_of(self.pane("CH-0012")).text())

    def test_both_parts_in_german_and_english(self) -> None:
        self.planned_item("NV-1", quantity=10)
        found = self.pane("NV-1")
        self.assertTrue(containers_of(found).find("table"))
        self.assertTrue(details_of(found).find("table"))
        accept(language="en")
        found = self.pane("NV-1")
        self.assertTrue(containers_of(found).find("table"))
        self.assertTrue(details_of(found).find("table"))

    def test_the_list_page_holds_the_pane_of_its_selection(self) -> None:
        self.three()
        root = self.get(PLAN + "?all=1&selected=NV-15")
        found = pane_of(root)
        self.assertEqual(found.get("data-item"), "NV-15")
        by_endpoint = self.pane("NV-15")
        self.assertEqual(
            [row["Bedarf/Jahr"].text()
             for row in container_rows(found)],
            [row["Bedarf/Jahr"].text()
             for row in container_rows(by_endpoint)])
        self.assertEqual(
            {key: cell.text() for key, cell in details(found).items()},
            {key: cell.text() for key, cell in details(by_endpoint).items()})

    def test_only_the_selected_article_is_in_the_page(self) -> None:
        self.three()
        root = self.get(PLAN + "?all=1&selected=NV-15")
        self.assertEqual(len(root.find_all(id="item-detail")), 1)
        self.assertEqual(len(root.find_all("table", cls="kv-table")), 2)
        for article in ("NV-10", "NV-25"):
            self.assertNotIn(f"/lab/planning/{article}/",
                             " ".join(a.get("href", "") for a in
                                      pane_of(root).find_all("a")))

    def test_the_container_table_sorts_in_the_browser(self) -> None:
        self.three()
        found = self.pane("NV-10")
        self.assertEqual(unsorted_reasons(found), [])
        grid = containers_of(found).find("table")
        self.assertIn("data-sortable", grid.attrs)
        self.assertIn("sortable-table", grid.get("data-controller").split())
        self.assertTrue(grid.get("id"))
        self.assertIsNone(details_of(found).find("table")
                          .get("data-sortable"))

    def test_the_stock_and_the_runway_carry_their_values_as_keys(
            self) -> None:
        """Compound cells key on their value (web-app: Widgets)."""
        self.planned_item("NV-1", size="1", quantity=10)
        (row,) = container_rows(self.pane("NV-1"))
        self.assertEqual(row["Bestand"].get("data-sort"), "10")
        self.assertEqual(num(row["Reichweite"]), 60)
        self.assertEqual(math.floor(key_number(
            row["Reichweite"].get("data-sort"))), 60)

    def test_a_missing_runway_has_no_numeric_key(self) -> None:
        self.planned_item("NV-1", size="1", quantity=10)
        self.item("NV-1", "NV-1", "5", "mg", 3)
        _, unused = container_rows(self.pane("NV-1"))
        self.assertIn(unused["Reichweite"].get("data-sort"),
                      (None, "", "–"))

    def test_the_link_to_the_substance_page_is_in_the_pane(self) -> None:
        self.demo_item()
        links = texts_of_links(self.pane("CH-0012"))
        self.assertEqual(links["(E)-Zimtsäure"],
                         "/lab/registry/substances/cinnamic-acid/")


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
        for article, item in (("NV-1", first), ("NV-2", second)):
            with self.subTest(article=article):
                rows = container_rows(self.pane(article))
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

    def test_the_part_names_the_priority(self) -> None:
        self.three()
        for article, label in (("NV-10", "hoch"), ("NV-15", "mittel"),
                               ("NV-25", "niedrig")):
            with self.subTest(article=article):
                found = details_of(self.block(article))
                self.assertTrue(has_word(found.text(), label), found.text())
                for other in {"hoch", "mittel", "niedrig"} - {label}:
                    self.assertFalse(has_word(found.text(), other),
                                     found.text())

    def test_the_priority_in_english(self) -> None:
        accept(language="en")
        self.three()
        found = details_of(self.block("NV-10"))
        self.assertTrue(has_word(found.text(), "high"), found.text())

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
        cells = {a: details(self.pane(a))["Synthesedauer"].text()
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
        self.assertIn("default", details(self.pane("NV-1"))
                      ["Synthesis time"].text())
        self.assertIn("longest of the last 3 syntheses",
                      details(self.pane("NV-3"))
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
        shown = {a: num(details(self.pane(a))["Reichweite"])
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
        cell = details(self.pane("NV-1"))["Aufgaben"]
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
        self.assertIn(task.number, details(self.pane("NV-2"))
                      ["Aufgaben"].text())
        self.assertNotIn(task.number, self.pane("NV-1").text())
