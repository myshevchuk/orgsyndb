"""Tests of the planning list (production-planning: Planning list):
its main table, its filter form, its order, its selection and its
parameters widget; the details of an article are in
``test_planning_inspector``."""

from datetime import date, timedelta
from urllib.parse import parse_qs, quote, urlsplit

from tasks.models import Task

from . import Element, field_value, make_task, page, task_form_data
from .collection_support import accept
from .inventory_support import (VESSELS, TODAY, has_number,
                                item_url, num)
from .main_lists_support import (head_of, hidden_fields, query_of, rows_of)
from .planning_support import (COLUMNS_DE, COLUMNS_EN, HTMX, PARAMETERS_TITLES,
                               PLAN, SHOW_DE, SHOW_EN, SHOW_VALUES, WINDOW,
                               PlanningCase, detail_url, has_date, has_word,
                               list_table, pane_of, priority_of,
                               rows_by_article, task_texts)
from .test_inventory_dialogs import RESTORE, vary_of
from .test_inventory_live_lists import LiveListAssertions
from .widget_support import grid, kv_rows, title_of, widget, widgets

CHECK_DE = "Bulk prüfen"
PLAN_DE = "Synthese planen"
NEW_TASK = "/lab/tasks/new/"
FORM_OOB = ["#planning-count:morph", "#item-head:morph",
            "#item-detail:morph", "#filter-selected:morph"]
LINK_OOB = ["#planning-count:morph", "#item-head:morph",
            "#item-detail:morph", "#filters:morph"]
NO_MATCH = "Keine Zeile passt zum Filter."
URGENT = "Kein Artikel braucht eine Synthese oder eine andere Maßnahme."
EVERY = "Kein Artikel hat eine Prognose."


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


class MainTableTests(ListCase):
    """The list as a main table in the split layout."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-10", quantity=10)

    def test_the_list_is_a_main_table_in_the_split_layout(self) -> None:
        root = self.get(PLAN)
        found = list_table(root)
        self.assertEqual(len(root.find_all("table", cls="main-table")), 1)
        layout = root.find("div", cls="item-layout")
        self.assertIsNotNone(layout)
        self.assertIn(found, list(layout.walk()))
        self.assertIn(pane_of(root), list(layout.walk()))
        self.assertIs(rows_of(root).closest("table"), found)
        self.assertIs(head_of(root).closest("table"), found)
        self.assertIn("lab-frame", root.find("body").classes)

    def test_the_list_is_no_widget(self) -> None:
        root = self.get(PLAN)
        shown = [title_of(w) for w in widgets(root)]
        self.assertNotIn("Planungsliste", shown)
        node = list_table(root).parent
        while node is not None:
            self.assertNotIn("widget", node.classes)
            node = node.parent

    def test_the_main_table_carries_no_script_attributes(self) -> None:
        root = self.get(PLAN + "?all=1")
        found = list_table(root)
        self.assertNotIn("data-sortable", found.attrs)
        for name in ("data-article", "data-priority", "data-action",
                     "data-late"):
            with self.subTest(attribute=name):
                self.assertEqual(
                    root.find_all(attrs={name: True}), [])
        self.assertEqual(found.find_all(attrs={"data-sortable": True}), [])

    def test_the_count_is_the_number_of_rows(self) -> None:
        for query, rows in (("", 2), ("?all=1", 3), ("?all=1&show=high", 1)):
            with self.subTest(query=query):
                root = self.get(PLAN + query)
                self.assertEqual(root.find("h1").text(), "Planung")
                count = root.find(id="planning-count")
                self.assertIsNotNone(count)
                self.assertEqual(num(count), rows)
                self.assertRegex(root.find("h1").parent.text(),
                                 rf"Planung\D{{0,5}}{rows}\b")

    def test_the_default_order_is_marked_in_the_latest_start(self) -> None:
        root = self.get(PLAN + "?all=1")
        header, _ = grid(list_table(root))
        marks = {cell.text(): cell.get("aria-sort") for cell in
                 head_of(root).find_all("th")}
        self.assertEqual(marks["Spätester Start"], "ascending")
        self.assertEqual([name for name, mark in marks.items() if mark],
                         ["Spätester Start"])
        self.assertEqual(list(rows_by_article(root)),
                         ["NV-10", "NV-15", "NV-25"])

    def test_german_columns(self) -> None:
        header, _ = grid(list_table(self.get(PLAN)))
        self.assertEqual(header, COLUMNS_DE)

    def test_english_columns(self) -> None:
        accept(language="en")
        header, _ = grid(list_table(self.get(PLAN)))
        self.assertEqual(header, COLUMNS_EN)

    def test_every_row_has_a_cell_for_each_column(self) -> None:
        rows = rows_by_article(self.get(PLAN))
        self.assertEqual(len(rows), 2)
        for article, row in rows.items():
            with self.subTest(article=article):
                self.assertEqual(list(row), COLUMNS_DE)

    def test_the_old_markup_is_gone(self) -> None:
        root = self.get(PLAN)
        for name in ("lab-parameters", "planning-cell", "planning-grid",
                     "planning-filters", "planning-inspector",
                     "planning-block", "planning-select", "planning-table",
                     "planning-list"):
            with self.subTest(cls=name):
                self.assertEqual(root.find_all(cls=name), [])

    def test_a_row_requests_the_details_of_its_article(self) -> None:
        rows = rows_by_article(self.get(PLAN))
        for article, row in rows.items():
            with self.subTest(article=article):
                self.assertEqual(row.element.get("data-item"), article)
                self.assertEqual(row.element.get("hx-trigger"),
                                 "item-select")
                self.assertEqual(urlsplit(row.element.get("hx-get")).path,
                                 detail_url(article))

    def test_the_list_comes_before_the_parameters(self) -> None:
        root = self.get(PLAN)
        walked = list(root.walk())
        self.assertLess(walked.index(list_table(root)),
                        walked.index(widget(root, *PARAMETERS_TITLES)))
        self.assertNotIn(widget(root, *PARAMETERS_TITLES),
                         list(pane_of(root).walk()))

    def test_the_planning_list_opens_in_the_details_view(self) -> None:
        layout = self.get(PLAN).find("div", cls="item-layout")
        self.assertIsNotNone(layout)
        self.assertEqual(layout.get("data-view"), "details")

    def test_the_parameters_widget_stays_when_nothing_is_listed(
            self) -> None:
        for query in ("?show=late", "?all=1&show=late"):
            with self.subTest(query=query):
                self.assertIsNotNone(
                    widget(self.get(PLAN + query), *PARAMETERS_TITLES))


class FilterFormTests(LiveListAssertions, ListCase):
    """The filter form: the choice ``Anzeigen`` and the check box
    ``Alle Artikel``."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-10", quantity=10)
        self.planned_item("NV-15", quantity=15)

    def form(self, query: str = "", **extra: str) -> tuple[Element, Element]:
        root = page(self.client.get(PLAN + query, **extra))
        form = root.find("form", id="filters")
        self.assertIsNotNone(form)
        return root, form

    def test_the_form_is_a_get_form_with_a_submit_button(self) -> None:
        _, form = self.form()
        self.assertEqual(form.get("method"), "get")
        self.assertEqual(form.get("action"), PLAN)
        self.assertIsNotNone(form.find("button", type="submit"))

    def test_the_choice_offers_four_filters(self) -> None:
        _, form = self.form()
        select = form.find("select", name="show")
        self.assertIsNotNone(select)
        options = select.find_all("option")
        self.assertEqual([o.text() for o in options], SHOW_DE)
        self.assertEqual([o.get("value") for o in options], SHOW_VALUES)
        label = select.closest("label")
        self.assertIsNotNone(label)
        self.assertIn("Anzeigen", label.text())

    def test_the_choice_in_english(self) -> None:
        accept(language="en")
        _, form = self.form()
        select = form.find("select", name="show")
        self.assertEqual([o.text() for o in select.find_all("option")],
                         SHOW_EN)

    def test_the_form_keeps_the_values(self) -> None:
        for query, shown, ticked in (
                ("", "", ""), ("?show=high", "high", ""),
                ("?all=1&show=late", "late", "on"),
                ("?show=bogus", "", ""), ("?all=1", "", "on")):
            with self.subTest(query=query):
                root, _ = self.form(query)
                self.assertEqual(field_value(root, "show"), shown)
                self.assertEqual(field_value(root, "all"), ticked)

    def test_the_check_box_is_named_all_articles(self) -> None:
        _, form = self.form()
        box = form.find("input", name="all")
        self.assertEqual((box.get("type"), box.get("value")),
                         ("checkbox", "1"))
        self.assertIn("Alle Artikel", box.closest("label").text())

    def test_the_form_is_live(self) -> None:
        root, form = self.form()
        entries = self.assert_live_element(
            form, root, expected_get=PLAN, target="#item-rows",
            required_oob=set(FORM_OOB))
        self.assertEqual(entries, FORM_OOB)
        self.assertEqual(
            form.get("hx-trigger"),
            "submit, change target:(select, input[type=checkbox])")
        self.assert_scoped_triggers(form, has_search=False, has_select=True,
                                    has_checkbox=True)
        self.assertIsNotNone(root.find(id="planning-count"))

    def test_the_header_links_update_the_list_in_place(self) -> None:
        root, _ = self.form()
        links = head_of(root).find_all("a")
        self.assertEqual(len(links), 6)
        for link in links:
            with self.subTest(link=link.text()):
                entries = self.assert_live_element(
                    link, root, expected_get=link.get("href"),
                    target="#item-rows", required_oob=set(LINK_OOB))
                self.assertEqual(entries, LINK_OOB)

    def test_the_header_links_keep_the_filters_and_the_selection(
            self) -> None:
        root = self.get(PLAN + "?all=1&show=high&selected=NV-15")
        links = head_of(root).find_all("a")
        self.assertTrue(links)
        for link in links:
            with self.subTest(link=link.text()):
                found = query_of(link.get("href"))
                self.assertEqual(found.get("all"), ["1"])
                self.assertEqual(found.get("show"), ["high"])
                self.assertEqual(found.get("selected"), ["NV-10"])

    def test_the_form_holds_the_order_unless_it_is_the_default(self) -> None:
        for query, held in (
                ("", {}), ("?sort=start", {}), ("?sort=nothing", {}),
                ("?sort=priority", {"sort": "priority"}),
                ("?sort=priority&dir=desc",
                 {"sort": "priority", "dir": "desc"}),
                ("?sort=start&dir=desc", {"sort": "start", "dir": "desc"})):
            with self.subTest(query=query):
                fields = hidden_fields(self.get(PLAN + query))
                found = {name: value for name, value in fields.items()
                         if name in ("sort", "dir")}
                self.assertEqual(found, held)

    def test_the_old_filter_buttons_and_link_are_gone(self) -> None:
        root = self.get(PLAN)
        self.assertEqual(root.find_all("button",
                                       attrs={"data-plan-filter": True}), [])
        self.assertEqual(root.find_all(cls="planning-filter"), [])
        texts = {a.text() for a in root.find("main").find_all("a")}
        for gone in ("Alle Artikel", "Nur dringende Artikel"):
            self.assertNotIn(gone, texts)
        accept(language="en")
        texts = {a.text() for a in self.get(PLAN).find("main").find_all("a")}
        for gone in ("All articles", "Urgent articles only"):
            self.assertNotIn(gone, texts)


class ServerFilterTests(ListCase):
    """The choice ``Anzeigen``, which filters on the server."""

    def three(self) -> None:
        """``NV-5`` of high priority with a late task, ``NV-10`` of high
        priority with neither an action nor a late task, and ``NV-1`` of
        low priority with an action."""
        self.planned_item("NV-5", quantity=5)
        self.running("NV-5", 3)
        self.planned_item("NV-10", quantity=10)
        self.running("NV-10", 14)
        self.planned_item("NV-1", quantity=1)
        self.vessel("NV-1", "mg", "20")

    def test_filters_on_the_server(self) -> None:
        """Scenario: Filters on the server."""
        self.three()
        every = self.shown("?all=1")
        self.assertEqual(sorted(every), ["NV-1", "NV-10", "NV-5"])
        for show, wanted in (("high", {"NV-10", "NV-5"}),
                             ("action", {"NV-1"}),
                             ("late", {"NV-5"}),
                             ("bogus", {"NV-1", "NV-10", "NV-5"}),
                             ("", {"NV-1", "NV-10", "NV-5"})):
            with self.subTest(show=show):
                root = self.get(PLAN + f"?all=1&show={show}")
                rows = list(rows_by_article(root))
                self.assertEqual(set(rows), wanted)
                self.assertEqual(rows, [a for a in every if a in wanted])
                self.assertEqual(num(root.find(id="planning-count")),
                                 len(wanted))

    def test_the_choice_works_without_all(self) -> None:
        self.three()
        self.assertEqual(self.shown("?show=late"), ["NV-5"])
        self.assertEqual(self.shown("?show=action"), ["NV-1"])
        self.assertEqual(sorted(self.shown("?show=high")),
                         ["NV-10", "NV-5"])

    def test_a_filter_that_matches_no_row(self) -> None:
        """Scenario: A filter that matches no row."""
        self.planned_item("NV-15", quantity=15)
        self.assertEqual(self.shown(), ["NV-15"])
        for extra in ({}, HTMX):
            with self.subTest(htmx=bool(extra)):
                root = page(self.client.get(PLAN + "?show=late", **extra))
                body = rows_of(root)
                rows = body.find_all("tr")
                self.assertEqual(len(rows), 1)
                cells = rows[0].find_all(("td", "th"))
                self.assertEqual(len(cells), 1)
                self.assertEqual(cells[0].text(), NO_MATCH)
                self.assertEqual(cells[0].get("colspan"), "7")
                self.assertNotIn("data-item", rows[0].attrs)
                self.assertEqual(rows_by_article(root), {})
                found = pane_of(root)
                self.assertNotIn("data-item", found.attrs)
                self.assertNotIn("Gebinde & Bedarf", found.text())
                self.assertEqual(num(root.find(id="planning-count")), 0)


class SortingTests(ListCase):
    """The list sorts on the server."""

    NAMES = {"NV-10": "Zeta", "NV-15": "Alpha", "NV-25": "Mid"}

    def setUp(self) -> None:
        super().setUp()
        for article, quantity in (("NV-25", 25), ("NV-15", 15),
                                  ("NV-10", 10)):
            self.planned_item(article, quantity=quantity,
                              name=self.NAMES[article])

    def order(self, query: str) -> list[str]:
        return list(rows_by_article(self.get(PLAN + "?all=1" + query)))

    def expected(self, key, descending: bool = False) -> list[str]:
        """The articles in the default order, sorted by KEY, rows of
        equal key keeping that order."""
        default = self.order("")
        return sorted(default, key=key, reverse=descending)

    def test_by_the_article_name(self) -> None:
        self.assertEqual(self.order("&sort=article"),
                         ["NV-15", "NV-25", "NV-10"])
        self.assertEqual(self.order("&sort=article&dir=desc"),
                         ["NV-10", "NV-25", "NV-15"])

    def test_by_the_runway_in_days(self) -> None:
        for descending in (False, True):
            with self.subTest(descending=descending):
                query = "&sort=runway" + ("&dir=desc" if descending else "")
                self.assertEqual(self.order(query), self.expected(
                    lambda a: self.forecast(a).runway, descending))
        self.assertEqual(self.order("&sort=runway&dir=desc"),
                         ["NV-25", "NV-15", "NV-10"])

    def test_by_the_synthesis_time_in_days(self) -> None:
        self.synthesis("NV-15", 40, TODAY - timedelta(days=100))
        for descending in (False, True):
            with self.subTest(descending=descending):
                query = ("&sort=synthesis"
                         + ("&dir=desc" if descending else ""))
                self.assertEqual(self.order(query), self.expected(
                    lambda a: self.forecast(a).synthesis_days, descending))
        self.assertEqual(self.order("&sort=synthesis")[-1], "NV-15")

    def test_by_the_latest_start(self) -> None:
        self.assertEqual(self.order("&sort=start&dir=desc"),
                         ["NV-25", "NV-15", "NV-10"])
        self.assertEqual(self.order("&sort=start"),
                         ["NV-10", "NV-15", "NV-25"])

    def test_by_the_priority_rank(self) -> None:
        self.assertEqual(self.order("&sort=priority"),
                         ["NV-10", "NV-15", "NV-25"])
        self.assertEqual(self.order("&sort=priority&dir=desc"),
                         ["NV-25", "NV-15", "NV-10"])

    def test_equal_priorities_keep_the_default_order(self) -> None:
        self.planned_item("NV-12", quantity=12)
        self.planned_item("NV-11", quantity=11)
        default = self.order("")
        for query in ("&sort=priority", "&sort=priority&dir=desc"):
            with self.subTest(query=query):
                rows = rows_by_article(self.get(PLAN + "?all=1" + query))
                by_priority: dict[str, list[str]] = {}
                for article, row in rows.items():
                    by_priority.setdefault(priority_of(row), []).append(
                        article)
                for group in by_priority.values():
                    self.assertEqual(
                        group, [a for a in default if a in group])

    def test_by_the_first_task_with_articles_without_one_last(self) -> None:
        first = make_task(self.kl, substance="NV-25")
        second = make_task(self.kl, substance="NV-10")
        self.assertLess(first.number, second.number)
        self.assertEqual(self.order("&sort=tasks"),
                         ["NV-25", "NV-10", "NV-15"])
        self.assertEqual(self.order("&sort=tasks&dir=desc"),
                         ["NV-10", "NV-25", "NV-15"])

    def test_the_actions_do_not_sort(self) -> None:
        self.assertEqual(self.order("&sort=actions"), self.order(""))
        root = self.get(PLAN + "?all=1")
        cell = next(c for c in head_of(root).find_all("th")
                    if c.text() == "Maßnahmen")
        self.assertIsNone(cell.find("a"))

    def test_the_order_in_force_is_marked_and_linked(self) -> None:
        root = self.get(PLAN + "?all=1&sort=priority&dir=desc")
        marks = {c.text(): c.get("aria-sort") for c in
                 head_of(root).find_all("th")}
        self.assertEqual(marks["Priorität"], "descending")
        self.assertEqual([n for n, m in marks.items() if m], ["Priorität"])
        link = next(c for c in head_of(root).find_all("th")
                    if c.text() == "Priorität").find("a")
        self.assertEqual(query_of(link.get("href")).get("dir"), None)
        self.assertEqual(query_of(link.get("href")).get("sort"),
                         ["priority"])

    def test_sorting_keeps_the_selected_article(self) -> None:
        root = self.get(PLAN + "?all=1&selected=NV-15&sort=priority&dir=desc")
        marked = [tr.get("data-item") for tr in
                  rows_of(root).find_all("tr")
                  if tr.get("aria-current") == "true"]
        self.assertEqual(marked, ["NV-15"])
        self.assertEqual(pane_of(root).get("data-item"), "NV-15")


class ArticleCellTests(ListCase):
    """The ``Artikel`` column."""

    def link_of(self, cell: Element, name: str) -> Element:
        links = [a for a in cell.find_all("a") if a.text() == name]
        self.assertEqual(len(links), 1, cell.text())
        return links[0]

    def test_the_name_links_the_substance_and_the_number_stands_by(
            self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        cell = self.articles()["NV-1"]["Artikel"]
        link = self.link_of(cell, "Probe Eins")
        self.assertEqual(link.get("href"), "/lab/registry/substances/nv-1/")
        self.assertTrue(has_word(cell.text(), "NV-1"), cell.text())

    def test_every_link_of_the_cell_leads_to_the_substance(self) -> None:
        self.planned_item("NV-1", quantity=10, name="Probe Eins")
        cell = self.articles()["NV-1"]["Artikel"]
        links = cell.find_all("a")
        self.assertTrue(links)
        for link in links:
            self.assertEqual(link.get("href"),
                             "/lab/registry/substances/nv-1/")

    def test_the_name_is_that_of_the_substance(self) -> None:
        self.item("NV-1", "Erste", "5", "mg", 1)
        self.planned_item("NV-1", size="10", quantity=10)
        cell = self.articles("?all=1")["NV-1"]["Artikel"]
        self.link_of(cell, "Erste")

    def test_the_name_is_in_the_language_of_the_page(self) -> None:
        self.demo_item()
        link = self.link_of(self.articles()["CH-0012"]["Artikel"],
                            "(E)-Zimtsäure")
        self.assertEqual(link.get("href"),
                         "/lab/registry/substances/cinnamic-acid/")
        accept(language="en")
        self.link_of(self.articles()["CH-0012"]["Article"],
                     "(E)-Cinnamic acid")

    def test_the_row_carries_the_lists_all_and_show(self) -> None:
        self.planned_item("NV-1", quantity=10)
        for query, wanted in (("?all=1", {"all": ["1"]}),
                              ("?all=1&show=high",
                               {"all": ["1"], "show": ["high"]}),
                              ("?show=high", {"show": ["high"]}),
                              ("", {}),
                              ("?show=bogus", {})):
            with self.subTest(query=query):
                row = self.articles(query)["NV-1"]
                self.assertEqual(query_of(row.element.get("hx-get")),
                                 wanted)

    def test_the_number_is_percent_encoded_as_one_path_segment(
            self) -> None:
        """Scenario: An article number with reserved characters."""
        number = "XY 1&2+3#4/5"
        self.planned_item(number, quantity=12, name="Sonderfall")
        selected = quote(number, safe="")
        root = self.get(f"{PLAN}?all=1&selected={selected}")
        rows = rows_by_article(root)
        self.assertEqual(list(rows), [number])
        row = rows[number]
        href = row.element.get("hx-get")
        shown = urlsplit(href)
        self.assertEqual(shown.path.split("/"),
                         ["", "lab", "planning", selected, "detail", ""])
        self.assertEqual(parse_qs(shown.query), {"all": ["1"]})
        for raw in (" ", "#", "&", "+"):
            self.assertNotIn(raw, shown.path)
        self.assertEqual(row.element.get("aria-current"), "true")
        found = pane_of(root)
        self.assertEqual(found.get("data-item"), number)
        self.assertIn("Sonderfall", found.text())
        response = self.client.get(href, **HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(pane_of(page(response)).get("data-item"), number)
        redirect = self.client.get(href)
        self.assertEqual(redirect.status_code, 302)
        where = urlsplit(redirect["Location"])
        self.assertEqual(where.path, PLAN)
        self.assertEqual(parse_qs(where.query),
                         {"all": ["1"], "selected": [number]})

    def test_a_selection_by_hand_with_special_characters(self) -> None:
        number = "XY 1&2+3#4"
        self.planned_item(number, quantity=12, name="Sonderfall")
        root = self.get(PLAN + "?all=1&selected=" + quote(number, safe=""))
        self.assertEqual(pane_of(root).get("data-item"), number)


class SelectedArticleTests(ListCase):
    """The details follow the selection."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-25", quantity=25)
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-10", quantity=10)

    def marked(self, root: Element) -> list[str]:
        return [article for article, row in rows_by_article(root).items()
                if row.element.get("aria-current") == "true"]

    def test_the_details_follow_the_selection(self) -> None:
        """Scenario: The details follow the selection."""
        root = self.get(PLAN + "?all=1&selected=NV-15")
        self.assertEqual(self.marked(root), ["NV-15"])
        self.assertEqual(pane_of(root).get("data-item"), "NV-15")
        self.assertIn("NV-15", pane_of(root).text())
        again = self.get(PLAN + "?all=1&selected=XX-0000")
        self.assertEqual(self.marked(again), ["NV-10"])
        self.assertEqual(pane_of(again).get("data-item"), "NV-10")

    def test_the_first_row_is_selected_without_a_selection(self) -> None:
        root = self.get(PLAN + "?all=1")
        self.assertEqual(self.marked(root), ["NV-10"])
        self.assertEqual(pane_of(root).get("data-item"), "NV-10")

    def test_the_order_of_selected_and_all_is_free(self) -> None:
        root = self.get(PLAN + "?selected=NV-15&all=1")
        self.assertEqual(pane_of(root).get("data-item"), "NV-15")

    def test_a_selection_the_list_lacks_falls_back_to_the_first_row(
            self) -> None:
        """NV-25 has a forecast, but it is not listed without ``all``."""
        root = self.get(PLAN + "?selected=NV-25")
        self.assertEqual(self.marked(root), ["NV-10"])
        self.assertEqual(pane_of(root).get("data-item"), "NV-10")

    def test_an_empty_selection_falls_back_to_the_first_row(self) -> None:
        root = self.get(PLAN + "?all=1&selected=")
        self.assertEqual(pane_of(root).get("data-item"), "NV-10")

    def test_a_selection_must_be_the_article_number_itself(self) -> None:
        for wrong in ("nv-15", "NV-1", "NV-150"):
            with self.subTest(selected=wrong):
                root = self.get(PLAN + "?all=1&selected=" + quote(wrong))
                self.assertEqual(pane_of(root).get("data-item"), "NV-10")

    def test_only_the_selected_row_carries_aria_current(self) -> None:
        root = self.get(PLAN + "?all=1&selected=NV-25")
        marked = [e for e in root.walk() if e.get("aria-current") == "true"]
        self.assertEqual(len(marked), 1)
        self.assertIs(marked[0], rows_by_article(root)["NV-25"].element)

    def test_the_selection_is_kept_in_the_filter_form(self) -> None:
        root = self.get(PLAN + "?all=1&selected=NV-15")
        form = root.find("form", id="filters")
        self.assertIsNotNone(form)
        fields = form.find_all("input", name="selected")
        self.assertEqual([f.get("value") for f in fields], ["NV-15"])
        self.assertEqual([f.get("type") for f in fields], ["hidden"])

    def test_without_an_article_the_form_names_no_selection(self) -> None:
        form = self.get(PLAN + "?show=late").find("form", id="filters")
        self.assertIsNotNone(form)
        self.assertEqual(form.find_all("input", name="selected"), [])


class CanonicalAddressTests(LiveListAssertions, ListCase):
    """The address the live list pushes."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_item("NV-5", quantity=5)
        self.running("NV-5", 3)
        self.planned_item("NV-25", quantity=25)

    def test_the_canonical_address(self) -> None:
        """Scenario: The canonical address."""
        res = self.client.get(
            PLAN + "?all=1&show=late&sort=priority&dir=desc", **HTMX)
        self.assert_push_url(
            res, PLAN,
            {"all": "1", "show": "late", "sort": "priority", "dir": "desc",
             "selected": "NV-5"},
            exact_url=(PLAN + "?all=1&show=late&sort=priority&dir=desc"
                       "&selected=NV-5"))
        res = self.client.get(PLAN + "?show=bogus&sort=start", **HTMX)
        self.assert_push_url(res, PLAN, {"selected": "NV-5"},
                             exact_url=PLAN + "?selected=NV-5")

    def test_an_empty_list_pushes_no_selection(self) -> None:
        res = self.client.get(PLAN + "?show=action&all=1&selected=NV-5",
                              **HTMX)
        self.assert_push_url(res, PLAN, {"all": "1", "show": "action"},
                             exact_url=PLAN + "?all=1&show=action")
        res = self.client.get(PLAN + "?show=action&sort=start", **HTMX)
        self.assertEqual(res["HX-Push-Url"], PLAN + "?show=action")

    def test_the_default_order_is_not_pushed(self) -> None:
        for query, pushed in (
                ("?sort=start", "?selected=NV-5"),
                ("?sort=start&dir=desc", "?sort=start&dir=desc&selected=NV-5"),
                ("?sort=article", "?sort=article&selected=NV-5"),
                ("?sort=actions", "?selected=NV-5")):
            with self.subTest(query=query):
                res = self.client.get(PLAN + query, **HTMX)
                self.assertEqual(res["HX-Push-Url"], PLAN + pushed)

    def test_restore_and_plain_requests_push_nothing(self) -> None:
        query = "?all=1&show=late"
        htmx, restore, plain = (self.client.get(PLAN + query, **extra)
                                for extra in (HTMX, RESTORE, {}))
        self.assertIn("HX-Push-Url", htmx)
        self.assertNotIn("HX-Push-Url", restore)
        self.assertNotIn("HX-Push-Url", plain)
        for res in (htmx, restore, plain):
            self.assertLessEqual({"hx-request", "hx-history-restore-request"},
                                 vary_of(res))
            root = page(res)
            self.assertIsNotNone(root.find("html"))
            self.assertIsNotNone(root.find("main", id="main"))
            self.assertIsNotNone(root.find("form", id="filters"))




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
    """The row that says why the list has none."""

    def assertMessage(self, query: str, message: str,
                      language: str = "de") -> None:
        root = self.get(PLAN + query)
        body = rows_of(root)
        rows = body.find_all("tr")
        self.assertEqual(len(rows), 1, query)
        cells = rows[0].find_all(("td", "th"))
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0].text(), message)
        self.assertEqual(cells[0].get("colspan"), "7")
        self.assertNotIn("data-item", rows[0].attrs)
        self.assertEqual(rows_by_article(root), {})
        found = pane_of(root)
        self.assertNotIn("data-item", found.attrs)
        self.assertTrue(found.text())
        self.assertNotIn("Gebinde & Bedarf", found.text())
        self.assertIsNotNone(list_table(root))
        self.assertEqual(num(root.find(id="planning-count")), 0)

    def test_an_empty_inventory_lists_nothing(self) -> None:
        self.assertMessage("", URGENT)
        self.assertMessage("?all=1", EVERY)

    def test_the_message_of_the_urgent_list(self) -> None:
        self.assertMessage("", URGENT)
        self.assertNotIn(EVERY, self.get(PLAN).find("main").text())

    def test_the_message_of_the_list_of_all(self) -> None:
        self.assertMessage("?all=1", EVERY)
        self.assertNotIn(URGENT, self.get(PLAN + "?all=1").find("main").text())

    def test_nothing_urgent_leaves_the_message(self) -> None:
        self.planned_item("NV-25", quantity=25)
        self.assertMessage("", URGENT)
        self.assertEqual(self.shown("?all=1"), ["NV-25"])

    def test_an_article_without_a_forecast_is_no_row(self) -> None:
        self.item("NV-0", size="1", unit="mg", quantity=10)
        self.assertMessage("?all=1", EVERY)

    def test_a_filter_the_list_survives_without_says_so(self) -> None:
        self.planned_item("NV-15", quantity=15)
        self.planned_item("NV-25", quantity=25)
        self.assertMessage("?show=late", NO_MATCH)
        self.assertMessage("?all=1&show=late", NO_MATCH)
        self.assertMessage("?show=high", NO_MATCH)

    def test_a_filter_on_a_list_without_a_row_gives_the_plain_message(
            self) -> None:
        self.assertMessage("?show=late", URGENT)
        self.assertMessage("?all=1&show=late", EVERY)
        self.planned_item("NV-25", quantity=25)
        self.assertMessage("?show=late", URGENT)

    def test_the_messages_are_not_shown_with_rows(self) -> None:
        self.planned_item("NV-10", quantity=10)
        for query in ("", "?all=1", "?show=high"):
            with self.subTest(query=query):
                text = self.get(PLAN + query).find("main").text()
                for message in (URGENT, EVERY, NO_MATCH):
                    self.assertNotIn(message, text)

    def test_the_english_messages(self) -> None:
        accept(language="en")
        self.assertMessage(
            "", "No article needs a synthesis or another action.")
        self.assertMessage("?all=1", "No article has a forecast.")
        self.planned_item("NV-15", quantity=15)
        self.assertMessage("?show=late", "No row matches the filter.")

    def test_the_parameters_stay(self) -> None:
        self.assertIsNotNone(
            widget(self.get(PLAN), *PARAMETERS_TITLES))


class PageTests(ListCase):

    def test_the_page_is_German_or_English_by_the_index(self) -> None:
        self.assertEqual(
            page(self.client.get(PLAN)).find("html").get("lang"), "de")
        accept(language="en")
        self.assertEqual(
            page(self.client.get(PLAN)).find("html").get("lang"), "en")
