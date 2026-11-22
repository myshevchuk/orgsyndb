"""Tests of the planning list (production-planning: Planning list):
the list widget, its filters and the parameters widget; the inspector is
in ``test_planning_inspector``."""

import math
from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit

from tasks.models import Task

from . import (Element, field_value, make_task, page, task_form_data)
from .collection_support import accept
from .inventory_support import (VESSELS, TODAY, has_number,
                                item_url, num)
from .planning_support import (COLUMNS_DE, COLUMNS_EN, FILTERS_DE,
                               FILTERS_EN, PARAMETERS_TITLES, PLAN, WINDOW,
                               PlanningCase, blocks, has_date, has_word,
                               list_table, list_widget, rows_by_article,
                               task_texts)
from .widget_support import (count_of, grid, kv_rows, title_of, widget,
                             widgets)

CHECK_DE = "Bulk prüfen"
PLAN_DE = "Synthese planen"
NEW_TASK = "/lab/tasks/new/"


class ListCase(PlanningCase):

    def articles(self, query: str = "", signed_in: bool = False):
        """The rows of the list by article number."""
        return rows_by_article(self.get(PLAN + query, signed_in))

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


class ListWidgetTests(ListCase):
    """The list as the widget ``Planungsliste``."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-10", quantity=10)

    def test_the_list_is_a_widget_with_a_sortable_table(self) -> None:
        found = list_widget(self.get(PLAN))
        self.assertEqual(found.tag, "section")
        self.assertEqual(title_of(found), "Planungsliste")
        tables = found.find_all("table")
        self.assertEqual(len(tables), 1)
        self.assertIn("data-sortable", tables[0].attrs)
        self.assertTrue(tables[0].get("id"))

    def test_the_count_is_the_number_of_rows(self) -> None:
        self.assertEqual(count_of(list_widget(self.get(PLAN))), 2)
        self.assertEqual(count_of(list_widget(self.get(PLAN + "?all=1"))), 3)

    def test_no_header_carries_aria_sort_and_the_rows_keep_slack_order(
            self) -> None:
        root = self.get(PLAN + "?all=1")
        found = list_table(root)
        self.assertEqual([e for e in found.walk() if "aria-sort" in e.attrs],
                         [])
        self.assertEqual(list(rows_by_article(root)),
                         ["NV-10", "NV-15", "NV-25"])

    def test_german_columns(self) -> None:
        header, _ = grid(list_table(self.get(PLAN)))
        self.assertEqual(header, COLUMNS_DE)

    def test_english_columns(self) -> None:
        accept(language="en")
        root = self.get(PLAN)
        self.assertEqual(title_of(list_widget(root)), "Planning list")
        header, _ = grid(list_table(root))
        self.assertEqual(header, COLUMNS_EN)

    def test_every_row_has_a_cell_for_each_column(self) -> None:
        rows = rows_by_article(self.get(PLAN))
        self.assertEqual(len(rows), 2)
        for article, row in rows.items():
            with self.subTest(article=article):
                self.assertEqual(list(row), COLUMNS_DE)

    def test_the_old_markup_is_gone(self) -> None:
        root = self.get(PLAN)
        for name in ("lab-parameters", "planning-cell"):
            with self.subTest(cls=name):
                self.assertEqual(root.find_all(cls=name), [])

    def test_the_list_comes_before_the_inspector_and_the_parameters(
            self) -> None:
        root = self.get(PLAN)
        walked = list(root.walk())
        first = walked.index(list_widget(root))
        self.assertLess(first, walked.index(widget(root, *PARAMETERS_TITLES)))
        for article, found in blocks(root).items():
            with self.subTest(article=article):
                self.assertLess(first, walked.index(found))

    def test_the_list_and_the_inspector_share_one_grid(self) -> None:
        root = self.get(PLAN)
        grids = root.find_all(cls="planning-grid")
        self.assertEqual(len(grids), 1)
        inside = list(grids[0].walk())
        self.assertTrue(any(list_widget(root) is node for node in inside))
        self.assertEqual(sorted(blocks(root)), ["NV-10", "NV-15"])
        for article, found in blocks(root).items():
            with self.subTest(article=article):
                self.assertTrue(any(found is node for node in inside))


class FilterTests(ListCase):
    """The filter buttons, which the script reveals."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-10", quantity=10)
        self.planned_item("NV-15", quantity=15)

    def buttons(self, root: Element) -> list[Element]:
        return list_widget(root).find_all("button")

    def group(self, root: Element) -> Element:
        """The nearest ancestor of the first button that carries
        ``hidden``, inside the widget."""
        found = list_widget(root)
        node = self.buttons(root)[0].parent
        while node is not found and "hidden" not in node.attrs:
            node = node.parent
        self.assertIn("hidden", node.attrs,
                      "the buttons are in no group that carries hidden")
        return node

    def test_four_buttons_in_the_order_of_the_spec(self) -> None:
        root = self.get(PLAN)
        self.assertEqual([b.text() for b in self.buttons(root)], FILTERS_DE)

    def test_the_english_buttons(self) -> None:
        accept(language="en")
        root = self.get(PLAN)
        self.assertEqual([b.text() for b in self.buttons(root)], FILTERS_EN)

    def test_the_group_is_hidden_until_the_script_reveals_it(self) -> None:
        root = self.get(PLAN)
        group = self.group(root)
        inside = list(group.walk())
        for found in self.buttons(root):
            with self.subTest(button=found.text()):
                self.assertTrue(any(found is node for node in inside))

    def test_all_is_active_when_the_page_loads(self) -> None:
        root = self.get(PLAN)
        self.assertEqual([b.get("aria-pressed") for b in self.buttons(root)],
                         ["true", "false", "false", "false"])

    def test_every_row_shows_without_the_script(self) -> None:
        root = self.get(PLAN + "?all=1")
        rows = rows_by_article(root)
        self.assertTrue(rows)
        for article, row in rows.items():
            with self.subTest(article=article):
                self.assertNotIn("hidden", row.element.attrs)


class ArticleCellTests(ListCase):
    """The ``Artikel`` column."""

    def link_of(self, cell: Element, name: str) -> Element:
        links = [a for a in cell.find_all("a") if a.text() == name]
        self.assertEqual(len(links), 1, cell.text())
        return links[0]

    def selected(self, href: str, **wanted: list[str]) -> None:
        shown = urlsplit(href)
        self.assertEqual((shown.path, shown.fragment), (PLAN, ""), href)
        self.assertEqual(parse_qs(shown.query), wanted, href)

    def test_the_name_links_the_selection_and_the_number_stands_by(
            self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        cell = self.articles()["NV-1"]["Artikel"]
        self.selected(self.link_of(cell, "Probe Eins").get("href"),
                      selected=["NV-1"])
        self.assertTrue(has_word(cell.text(), "NV-1"), cell.text())

    def test_every_link_of_the_cell_selects_the_article(self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        cell = self.articles()["NV-1"]["Artikel"]
        links = cell.find_all("a")
        self.assertTrue(links)
        for link in links:
            with self.subTest(text=link.text()):
                self.selected(link.get("href"), selected=["NV-1"])

    def test_the_link_keeps_all(self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        self.planned_item("NV-25", quantity=25, name="Probe Fünf")
        rows = self.articles("?all=1")
        for article, name in (("NV-1", "Probe Eins"), ("NV-25", "Probe Fünf")):
            with self.subTest(article=article):
                self.selected(
                    self.link_of(rows[article]["Artikel"], name).get("href"),
                    selected=[article], all=["1"])

    def test_the_number_is_url_encoded(self) -> None:
        """Article numbers are free text: a space, an ampersand, a plus
        sign and a number sign must not end the value."""
        number = "XY 1&2+3#4"
        self.planned_item(number, quantity=10, name="Sonderfall")
        rows = self.articles("?all=1")
        self.assertEqual(list(rows), [number])
        href = self.link_of(rows[number]["Artikel"], "Sonderfall").get("href")
        self.selected(href, selected=[number], all=["1"])
        for raw in (" ", "#"):
            self.assertNotIn(raw, href)

    def test_the_name_is_that_of_the_substance(self) -> None:
        self.item("NV-1", "Erste", "5", "mg", 1)
        self.planned_item("NV-1", size="10", quantity=10)
        cell = self.articles("?all=1")["NV-1"]["Artikel"]
        self.link_of(cell, "Erste")

    def test_the_name_is_in_the_language_of_the_page(self) -> None:
        self.demo_item()
        self.link_of(self.articles()["CH-0012"]["Artikel"], "(E)-Zimtsäure")
        accept(language="en")
        self.link_of(self.articles()["CH-0012"]["Article"],
                     "(E)-Cinnamic acid")

    def test_the_english_link(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        cell = self.articles("?all=1")["NV-1"]["Article"]
        self.selected(self.link_of(cell, "Probe Eins").get("href"),
                      selected=["NV-1"], all=["1"])


class RowAttributeTests(ListCase):
    """The attributes the filters read."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-10", quantity=10)
        self.running("NV-10", 14)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-1", quantity=1)
        self.vessel("NV-1", "mg", "20")
        self.planned_item("NV-5", quantity=5)
        self.running("NV-5", 3)
        self.planned_item("NV-7", quantity=7)
        make_task(self.kl, substance="NV-7")
        self.vessel("NV-7", "umol", "1000")

    def attributes(self, query: str = "?all=1", signed_in: bool = False
                   ) -> dict[str, tuple[str | None, ...]]:
        return {article: tuple(row.element.get(name) for name in (
            "data-priority", "data-action", "data-late"))
            for article, row in self.articles(query, signed_in).items()}

    def test_priority_action_and_late(self) -> None:
        late = self.forecast("NV-7").priority
        self.assertEqual(self.attributes(), {
            "NV-10": ("high", None, None),
            "NV-15": ("medium", "1", None),
            "NV-25": ("low", None, None),
            "NV-1": ("low", "1", None),
            "NV-5": ("high", None, "1"),
            "NV-7": (late, "1", "1")})

    def test_an_action_is_one_whether_or_not_the_user_may_follow_it(
            self) -> None:
        self.assertEqual(self.attributes(signed_in=True),
                         self.attributes(signed_in=False))
        self.assertEqual(self.attributes(signed_in=True)["NV-15"][1], "1")

    def test_the_attributes_follow_the_cells(self) -> None:
        """A row has ``data-action`` when its ``Maßnahmen`` holds an
        action and ``data-late`` when its ``Aufgaben`` marks a task."""
        rows = self.articles("?all=1")
        self.assertEqual(len(rows), 6)
        for article, row in rows.items():
            with self.subTest(article=article):
                self.assertEqual(row.element.get("data-action") == "1",
                                 row["Maßnahmen"].text() != "–")
                self.assertEqual(row.element.get("data-late") == "1",
                                 "verspätet" in row["Aufgaben"].text())

    def test_the_attributes_are_the_same_in_english(self) -> None:
        german = self.attributes()
        self.assertEqual(len(german), 6)
        accept(language="en")
        self.assertEqual(self.attributes(), german)


class SortKeyTests(ListCase):
    """The ``data-sort`` keys of the list's cells."""

    COLUMNS = ("Reichweite", "Synthesedauer", "Spätester Start", "Priorität")

    def keys(self, query: str = "?all=1") -> dict[str, list[str | None]]:
        return {article: [row[name].get("data-sort")
                          for name in self.COLUMNS]
                for article, row in self.articles(query).items()}

    def test_the_keys_of_an_article(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.assertEqual(self.keys()["NV-1"],
                         ["60", "21", "2026-11-15", "1"])

    def test_the_keys_are_the_same_in_english(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=10)
        rows = self.articles("?all=1")
        self.assertEqual([rows["NV-1"][name].get("data-sort") for name in (
            "Runway", "Synthesis time", "Latest start", "Priority")],
            ["60", "21", "2026-11-15", "1"])

    def test_the_priority_rank(self) -> None:
        self.planned_item("NV-10", quantity=10)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-25", quantity=25)
        self.assertEqual({article: found[3] for article, found
                          in self.keys().items()},
                         {"NV-10": "1", "NV-15": "2", "NV-25": "3"})

    def test_the_runway_is_rounded_down_not_to_the_nearest(self) -> None:
        rounded_up = 0
        for quantity in range(2, 12):
            self.planned_item(f"NV-{quantity}", quantity=quantity)
        for article, found in self.keys().items():
            runway = self.forecast(article).runway
            with self.subTest(article=article, runway=runway):
                self.assertEqual(found[0], str(math.floor(runway)))
            rounded_up += round(runway) != math.floor(runway)
        self.assertGreater(rounded_up, 0, "no runway has a fraction of "
                           "one half or more; the test checks nothing")

    def test_the_synthesis_time_is_in_whole_days(self) -> None:
        self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        self.assertEqual(self.keys()["NV-1"][1], "40")

    def test_a_missing_latest_start_is_a_dash_and_the_runway_digits(
            self) -> None:
        item = self.item("NV-9", "NV-9", "1", "mg", 10)
        for year, quarter in WINDOW:
            self.enter(item, year, quarter,
                       1 if (year, quarter) == WINDOW[-5] else 0)
        self.vessel("NV-9", "mg", "3000")
        found = self.forecast("NV-9")
        self.assertIsNone(found.latest_start)
        runway, _, start, _ = self.keys()["NV-9"]
        self.assertEqual(start, "–")
        self.assertRegex(runway, r"\A\d+\Z")
        self.assertEqual(runway, str(math.floor(found.runway)))

    def test_the_keys_are_numbers_and_dates_not_text(self) -> None:
        self.planned_item("NV-1", quantity=10)
        runway, synthesis, start, priority = self.keys()["NV-1"]
        self.assertRegex(runway, r"\A\d+\Z")
        self.assertRegex(synthesis, r"\A\d+\Z")
        self.assertRegex(start, r"\A\d{4}-\d{2}-\d{2}\Z")
        self.assertRegex(priority, r"\A[123]\Z")


class RowValueTests(ListCase):

    def test_the_row_of_an_article(self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        row = self.articles()["NV-1"]
        self.assertEqual(num(row["Reichweite"]), 60)
        self.assertEqual(num(row["Synthesedauer"]), 21)
        self.assertTrue(has_date(row["Spätester Start"].text(),
                                 date(2026, 11, 15)))
        self.assertIn("hoch", row["Priorität"].text())

    def test_the_english_numbers(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=10)
        row = self.articles()["NV-1"]
        self.assertEqual(num(row["Runway"]), 60)
        self.assertTrue(has_date(row["Latest start"].text(),
                                 date(2026, 11, 15)))
        self.assertIn("high", row["Priority"].text())

    def test_the_synthesis_time_follows_past_syntheses(self) -> None:
        self.planned_item("NV-1", quantity=10)
        for days in (30, 35, 40):
            self.synthesis("NV-1", days, TODAY - timedelta(days=days * 3))
        self.assertEqual(num(self.articles()["NV-1"]["Synthesedauer"]), 40)

    def test_the_runway_counts_the_usable_bulk(self) -> None:
        self.planned_item("NV-2", size="10", quantity=0)
        large = self.item("NV-2", "NV-2", "20", "mg", 0)
        for year, quarter in WINDOW:
            self.enter(large, year, quarter, 9)
        self.vessel("NV-2", "mg", "360")
        row = self.articles()["NV-2"]
        self.assertEqual(num(row["Reichweite"]), 62)
        self.assertIn("hoch", row["Priorität"].text())
        self.assertTrue(has_date(row["Spätester Start"].text(),
                                 TODAY + timedelta(days=13)))

    def test_the_latest_start_may_lie_in_the_past(self) -> None:
        self.planned_item("NV-7", quantity=7)
        text = self.articles()["NV-7"]["Spätester Start"].text()
        self.assertTrue(has_date(text, TODAY - timedelta(days=11)), text)

    def test_no_latest_start_is_a_dash(self) -> None:
        item = self.item("NV-9", "NV-9", "1", "mg", 10)
        for year, quarter in WINDOW:
            self.enter(item, year, quarter,
                       1 if (year, quarter) == WINDOW[-5] else 0)
        self.vessel("NV-9", "mg", "3000")
        self.assertEqual(
            self.articles("?all=1")["NV-9"]["Spätester Start"].text(), "–")

    def test_a_rough_runway_is_marked(self) -> None:
        self.planned_item("NV-1", quantity=10)
        item = self.item("NV-2", "NV-2", "1", "mg", 10)
        self.orders(item, *[(date(2026, month, 10), size) for month, size
                            in enumerate([2, 3, 5, 8, 17, 23, 31, 40, 59],
                                         1)])
        rows = self.articles("?all=1")
        self.assertTrue(has_word(rows["NV-1"]["Reichweite"].text(), "grob"))
        self.assertFalse(has_word(rows["NV-2"]["Reichweite"].text(), "grob"))

    def test_the_english_mark(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=10)
        text = self.articles()["NV-1"]["Runway"].text()
        self.assertTrue(has_word(text, "rough"), text)


class ParametersWidgetTests(ListCase):
    """The parameters in a collapsible widget, closed on load."""

    def test_the_paragraph_of_parameters_is_gone(self) -> None:
        self.planned_item("NV-1", quantity=10)
        root = self.get(PLAN)
        self.assertEqual(root.find_all(cls="lab-parameters"), [])

    def found(self, **over: object) -> Element:
        if over:
            self.parameters(**over)
        self.planned_item("NV-1", quantity=10)
        return widget(self.get(PLAN), *PARAMETERS_TITLES)

    def body(self, found: Element) -> str:
        return found.text(lambda node: "widget__head" in node.classes)

    def note(self, found: Element) -> str:
        return found.find(cls="widget__note").text()

    def test_a_closed_collapsible_widget(self) -> None:
        """Scenario: Parameters closed."""
        found = self.found()
        self.assertEqual(found.tag, "details")
        self.assertIn("widget", found.classes)
        self.assertNotIn("open", found.attrs)
        self.assertEqual(title_of(found), "Planungsparameter")
        head = found.find(cls="widget__head")
        self.assertIsNotNone(head)
        self.assertEqual(head.tag, "summary")
        self.assertIs(head.parent, found)

    def test_the_title_in_english(self) -> None:
        accept(language="en")
        self.assertEqual(title_of(self.found()), "Planning parameters")

    def test_the_default_parameters_are_in_the_body(self) -> None:
        """Scenario: Parameters closed (95 %, 28 days, 21 days, 12
        quarters, 6 orders, 14 and 56 days and 365 days)."""
        body = self.body(self.found())
        self.assertRegex(body, r"(?<![\d,.])95\s*%")
        for number in ("28", "21", "12", "6", "14", "56", "365"):
            with self.subTest(number=number):
                self.assertTrue(has_number(body, number), body)

    def test_the_parameters_in_force_are_in_the_body(self) -> None:
        body = self.body(self.found(
            certainty=0.9, buffer_days=33, default_synthesis_days=17,
            history_quarters=9, min_orders=7, high_days=10, medium_days=40,
            target_days=222))
        self.assertRegex(body, r"(?<![\d,.])90\s*%")
        for number in ("33", "17", "9", "7", "10", "40", "222"):
            with self.subTest(number=number):
                self.assertTrue(has_number(body, number), body)

    def test_the_body_is_a_key_value_table_of_the_parameters(self) -> None:
        rows = kv_rows(self.found())
        self.assertGreaterEqual(len(rows), 7, rows)
        for key, value in rows:
            with self.subTest(key=key):
                self.assertTrue(key)
                self.assertTrue(value.text())

    def test_the_note_states_the_parameters_in_short(self) -> None:
        note = self.note(self.found())
        self.assertRegex(note, r"(?<![\d,.])95\s*%")
        self.assertTrue(has_number(note, "28"), note)

    def test_the_note_follows_the_settings(self) -> None:
        note = self.note(self.found(certainty=0.9, buffer_days=33))
        self.assertRegex(note, r"(?<![\d,.])90\s*%")
        self.assertTrue(has_number(note, "33"), note)

    def test_the_content_is_in_the_page_though_the_widget_is_closed(
            self) -> None:
        found = self.found()
        self.assertNotIn("open", found.attrs)
        self.assertTrue(found.find("table"))


class TasksColumnTests(ListCase):

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-1", quantity=10)

    def cell(self, article: str = "NV-1"):
        return self.articles("?all=1")[article]["Aufgaben"]

    def test_planned_and_running_tasks_running_first_then_by_number(
            self) -> None:
        planned = make_task(self.kl, substance="NV-1")
        running = self.running("NV-1", 14)
        other = make_task(self.kl, substance="nv-1")
        make_task(self.kl, substance="NV-1", cancelled=True)
        self.synthesis("NV-1", 10, date(2026, 9, 1))
        cell = self.cell()
        links = [a for a in cell.find_all("a")
                 if a.get("href", "").startswith("/lab/tasks/")]
        self.assertEqual([a.text() for a in links],
                         [running.number, planned.number, other.number])
        self.assertEqual([a.get("href") for a in links],
                         [f"/lab/tasks/{t.number}/"
                          for t in (running, planned, other)])

    def test_each_task_shows_its_state(self) -> None:
        planned = make_task(self.kl, substance="NV-1")
        running = self.running("NV-1", 14)
        parts = task_texts(self.cell())
        self.assertEqual(set(parts), {planned.number, running.number})
        self.assertIn("In Arbeit", parts[running.number])
        self.assertIn("Geplant", parts[planned.number])

    def test_the_expected_end_is_not_in_the_list(self) -> None:
        """It is in the inspector."""
        make_task(self.kl, substance="NV-1")
        self.running("NV-1", 14)
        text = self.cell().text()
        for day in (TODAY + timedelta(days=21), TODAY + timedelta(days=7)):
            self.assertFalse(has_date(text, day), text)

    def test_a_task_in_time_is_not_late(self) -> None:
        make_task(self.kl, substance="NV-1")
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
        planned = make_task(self.kl, substance="NV-7")
        running = self.running("NV-7", 20)
        parts = task_texts(self.cell("NV-7"))
        self.assertIn("verspätet", parts[planned.number])
        self.assertNotIn("verspätet", parts[running.number])

    def test_the_english_mark(self) -> None:
        accept(language="en")
        self.planned_item("NV-5", quantity=5)
        self.running("NV-5", 3)
        row = self.articles("?all=1")["NV-5"]
        self.assertIn("late", row["Tasks"].text())

    def test_no_task_reads_a_dash(self) -> None:
        self.assertEqual(self.cell().text(), "–")

    def test_a_task_of_the_substance_is_listed_with_the_article(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        task = make_task(self.kl, substance="cinnamic-acid")
        self.assertIn(task.number, self.cell("CH-0012").text())

    def test_other_articles_tasks_are_not_listed(self) -> None:
        self.planned_item("NV-2", quantity=10)
        task = make_task(self.kl, substance="NV-2")
        self.assertNotIn(task.number, self.cell("NV-1").text())

    def test_the_article_priority_ignores_its_tasks(self) -> None:
        self.running("NV-1", 14)
        self.assertIn("hoch", self.articles()["NV-1"]["Priorität"].text())


class NoActionTests(ListCase):

    def test_no_action_reads_a_dash(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.assertEqual(self.actions("NV-1").text(), "–")

    def test_an_action_does_not_read_a_dash(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.assertNotIn("–", self.actions("NV-1").text())


class ActionTests(ListCase):

    def test_actions(self) -> None:
        """Scenario: Actions."""
        first = self.planned_item("NV-1", quantity=1)
        self.vessel("NV-1", "mg", "20")
        self.planned_item("NV-2", quantity=10)
        self.vessel("NV-2", "umol", "1000")
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
                         if a.text() == CHECK_DE and a.get("href") == VESSELS])
        self.assertNotIn(PLAN_DE, second.text())
        third = rows["NV-3"]["Maßnahmen"]
        plan_links = [a for a in third.find_all("a")
                      if a.text() == PLAN_DE]
        self.assertEqual([a.get("href") for a in plan_links],
                         [NEW_TASK + "?substance=nv-3"])
        self.assertNotIn(CHECK_DE, third.text())
        self.assertNotIn("Abfüllen", third.text())

    def test_a_row_that_needs_nothing_offers_nothing(self) -> None:
        self.planned_item("NV-1", quantity=25)
        text = self.actions("NV-1").text()
        for label in ("Abfüllen", CHECK_DE, PLAN_DE):
            self.assertNotIn(label, text)

    def test_fill_is_due_below_the_buffer(self) -> None:
        item = self.planned_item("NV-1", quantity=10)
        self.vessel("NV-1", "mg", "20")
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())
        self.parameters(buffer_days=61)
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text() == "Abfüllen 1 mg"]
        self.assertEqual([a.get("href") for a in links],
                         [item_url(item, "fill")])

    def test_fill_needs_a_container_in_the_vessels(self) -> None:
        self.planned_item("NV-1", quantity=1)
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())
        self.vessel("NV-1", "mg", "0.5")
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())
        self.vessel("NV-1", "mg", "1")
        self.assertIn("Abfüllen 1 mg", self.actions("NV-1").text())

    def test_fill_is_not_offered_from_a_used_up_vessel(self) -> None:
        self.planned_item("NV-1", quantity=1)
        self.vessel("NV-1", "mg", "0")
        self.assertNotIn("Abfüllen", self.actions("NV-1").text())

    def test_fill_is_decided_per_size(self) -> None:
        small = self.planned_item("NV-1", size="1", quantity=1)
        self.planned_item("NV-1", size="5", quantity=40)
        self.vessel("NV-1", "mg", "20")
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text().startswith("Abfüllen")]
        self.assertEqual([(a.text(), a.get("href")) for a in links],
                         [("Abfüllen 1 mg", item_url(small, "fill"))])

    def test_fill_for_each_size_that_is_low(self) -> None:
        small = self.planned_item("NV-1", size="1", quantity=1)
        large = self.planned_item("NV-1", size="5", quantity=1)
        self.vessel("NV-1", "mg", "50")
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text().startswith("Abfüllen")]
        self.assertEqual([(a.text(), a.get("href")) for a in links],
                         [("Abfüllen 1 mg", item_url(small, "fill")),
                          ("Abfüllen 5 mg", item_url(large, "fill"))])

    def test_fill_is_not_offered_for_a_vessel_that_does_not_convert(
            self) -> None:
        self.planned_item("NV-1", quantity=1)
        self.vessel("NV-1", "umol", "1000")
        text = self.actions("NV-1").text()
        self.assertNotIn("Abfüllen", text)
        self.assertIn(CHECK_DE, text)

    def test_the_size_is_shown_as_the_item_list_shows_it(self) -> None:
        self.planned_item("NV-1", size="2.5", quantity=1)
        self.vessel("NV-1", "mg", "50")
        self.assertIn("Abfüllen 2,5 mg", self.actions("NV-1").text())

    def test_check_bulk_for_a_vessel_that_does_not_convert(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.vessel("NV-1", "umol", "1000")
        links = [a for a in self.actions("NV-1").find_all("a")
                 if a.text() == CHECK_DE]
        self.assertEqual([a.get("href") for a in links], [VESSELS])

    def test_check_bulk_is_not_offered_for_a_used_up_vessel(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.vessel("NV-1", "umol", "0")
        self.assertNotIn(CHECK_DE, self.actions("NV-1").text())

    def test_check_bulk_is_not_offered_when_every_vessel_converts(
            self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.vessel("NV-1", "g", "1")
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
                    [NEW_TASK + f"?substance={article.lower()}"]
                    if offered else [])

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
        make_task(self.kl, substance="NV-1")
        self.running("NV-2", 5)
        for article in ("NV-1", "NV-2"):
            with self.subTest(article=article):
                self.assertNotIn(PLAN_DE,
                                 self.actions(article, True).text())
        self.assertIn(PLAN_DE, self.actions("NV-3", True).text())

    def test_other_tasks_do_not_stop_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.synthesis("NV-1", 10, date(2026, 9, 1))
        make_task(self.kl, substance="NV-1", cancelled=True)
        make_task(self.kl, substance="NV-9")
        self.assertIn(PLAN_DE, self.actions("NV-1", True).text())

    def test_a_task_of_the_same_substance_stops_the_offer(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        make_task(self.kl, substance="cinnamic-acid")
        self.assertNotIn(PLAN_DE, self.actions("CH-0012", True).text())

    def test_a_vessel_that_does_not_convert_stops_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.vessel("NV-1", "umol", "1000")
        text = self.actions("NV-1", True).text()
        self.assertNotIn(PLAN_DE, text)
        self.assertIn(CHECK_DE, text)

    def test_a_vessel_that_converts_does_not_stop_the_offer(self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.vessel("NV-1", "mg", "1.5")
        self.assertIn(PLAN_DE, self.actions("NV-1", True).text())

    def test_a_used_up_vessel_that_does_not_convert_does_not_stop_it(
            self) -> None:
        self.planned_item("NV-1", quantity=10)
        self.vessel("NV-1", "umol", "0")
        self.assertIn(PLAN_DE, self.actions("NV-1", True).text())

    def test_an_article_to_be_listed_for_its_action_alone(self) -> None:
        self.planned_item("NV-1", quantity=25)
        self.planned_item("NV-2", quantity=25)
        self.vessel("NV-2", "umol", "1000")
        self.assertEqual(self.shown(), ["NV-2"])

    def test_the_english_texts(self) -> None:
        accept(language="en")
        self.planned_item("NV-1", quantity=1)
        self.vessel("NV-1", "mg", "20")
        self.planned_item("NV-2", quantity=10)
        self.vessel("NV-2", "umol", "1000")
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
        key = field_value(form, "substance")
        self.assertEqual(key, "nv-3")
        done = self.client.post(NEW_TASK, task_form_data(substance=key))
        self.assertEqual(done.status_code, 302)
        task = Task.objects.get()
        row = self.articles(signed_in=True)["NV-3"]
        self.assertIn(task.number, row["Aufgaben"].text())
        self.assertNotIn(PLAN_DE, row["Maßnahmen"].text())

    def test_the_task_of_a_demo_article(self) -> None:
        self.planned_item("CH-0012", size="10", unit="umol", quantity=10)
        self.client.force_login(self.kl)
        row = self.articles(signed_in=True)["CH-0012"]
        link = [a for a in row["Maßnahmen"].find_all("a")
                if a.text() == PLAN_DE][0]
        self.assertEqual(link.get("href"),
                         NEW_TASK + "?substance=cinnamic-acid")


class EmptyListTests(ListCase):
    URGENT = "Kein Artikel braucht eine Synthese oder eine andere Maßnahme."
    EVERY = "Kein Artikel hat eine Prognose."

    def message(self, query: str = "") -> str:
        return self.get(PLAN + query).find("main").text()

    def assertNoList(self, query: str = "") -> None:
        root = self.get(PLAN + query)
        self.assertEqual(
            root.find_all("table", attrs={"data-sortable": True}), [])
        self.assertEqual(rows_by_article(root), {})
        self.assertEqual(root.find_all(attrs={"data-article": True}), [])
        shown = [title_of(w) for w in widgets(root)]
        for title in ("Gebinde & Bedarf", "Planungsdetails"):
            self.assertNotIn(title, shown)

    def test_an_empty_inventory_lists_nothing(self) -> None:
        self.assertNoList()
        self.assertNoList("?all=1")

    def test_the_message_of_the_urgent_list(self) -> None:
        self.assertIn(self.URGENT, self.message())
        self.assertNotIn(self.EVERY, self.message())

    def test_the_message_of_the_list_of_all(self) -> None:
        self.assertIn(self.EVERY, self.message("?all=1"))
        self.assertNotIn(self.URGENT, self.message("?all=1"))

    def test_nothing_urgent_leaves_no_table_and_no_inspector(self) -> None:
        self.planned_item("NV-25", quantity=25)
        self.assertNoList()
        self.assertIn(self.URGENT, self.message())
        self.assertEqual(self.shown("?all=1"), ["NV-25"])
        self.assertNotIn(self.EVERY, self.message("?all=1"))

    def test_an_article_without_a_forecast_is_no_row(self) -> None:
        self.item("NV-0", size="1", unit="mg", quantity=10)
        self.assertNoList("?all=1")
        self.assertIn(self.EVERY, self.message("?all=1"))

    def test_the_messages_are_not_shown_with_rows(self) -> None:
        self.planned_item("NV-10", quantity=10)
        for query in ("", "?all=1"):
            with self.subTest(query=query):
                text = self.message(query)
                self.assertNotIn(self.URGENT, text)
                self.assertNotIn(self.EVERY, text)

    def test_the_english_messages(self) -> None:
        accept(language="en")
        self.assertIn("No article needs a synthesis or another action.",
                      self.message())
        self.assertIn("No article has a forecast.", self.message("?all=1"))
        self.assertNoList()


class PageTests(ListCase):

    def test_the_page_is_German_or_English_by_the_index(self) -> None:
        self.assertEqual(
            page(self.client.get(PLAN)).find("html").get("lang"), "de")
        accept(language="en")
        self.assertEqual(
            page(self.client.get(PLAN)).find("html").get("lang"), "en")
