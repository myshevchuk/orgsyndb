"""Tests of what the ten main lists share (web-app: Main lists): the main
table, sorting, the canonical address, the selection, the views, the
details endpoints and the two table classes.

What belongs to one list is in the tests of that list: the item list in
``test_inventory_table``, the planning list in ``test_planning_list``.
"""

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit

from django.contrib.auth import get_user_model

from . import (Element, make_batch, make_task, make_vessel, page, past,
               substance_for)
from .demo_support import SeededCase
from .inventory_support import InventoryCase
from .main_lists_support import (HTMX, LOT_TABLE, MAIN_LISTS, MainList,
                                 aria_sorts, body_rows, cells,
                                 has_ancestor_class, head_cells,
                                 hidden_fields, in_detail_pane, lists_records,
                                 lot_keys, lot_marked, lot_tables,
                                 main_table, main_tables, marked,
                                 must_outer_split, must_pane,
                                 pane_head, pane_widgets, path_of, query_of,
                                 replaced, row_keys, split_panes,
                                 unsorted_reasons)


# The pages of the demo data set that tests of a visitor have read.
PAGES: dict[str, Element] = {}


def per_list(test: Callable[..., None]) -> Callable[[Any], None]:
    """The test method TEST, which takes a main list, as a method that
    runs it for each of the ten lists, each in its own subtest."""
    def run(self: Any) -> None:
        for spec in MAIN_LISTS.values():
            with self.subTest(list=spec.name):
                test(self, spec)
    run.__name__ = test.__name__
    run.__doc__ = test.__doc__
    return run


# The lists whose details hold a lot table and whose address names a lot.
CATEGORY_LISTS = ("intermediate", "chemical")


def link_of(cell: Element) -> Element:
    """The link of the header cell CELL; fail when it holds none."""
    found = cell.find("a")
    assert found is not None, f"the header {cell.text()!r} holds no link"
    return found


class MainListCase(SeededCase):
    """The demo data set, which fills each of the ten lists."""

    def fetch(self, path: str, **extra: Any) -> Element:
        """The parsed page at PATH. A page of a visitor without cookies
        is read once for the whole run, since no test changes the data
        set, which keeps the many requests of these tests cheap."""
        shared = not extra and not self.client.cookies
        if shared and path in PAGES:
            return PAGES[path]
        response = self.client.get(path, **extra)
        self.assertEqual(response.status_code, 200, path)
        root = page(response)
        if shared:
            PAGES[path] = root
        return root

    def keys_of(self, spec: MainList, query: str = "") -> list[str]:
        return row_keys(self.fetch(spec.path + query))

    def other_key(self, spec: MainList) -> str:
        """A sort key that sorts and is not the default one."""
        return next(key for key in spec.sorted_keys if key != spec.default)


# ---------------------------------------------------------------------------
# The main table


class MainTableTests(MainListCase):
    """The main table, its header, its body and its details pane."""

    @per_list
    def test_each_list_shows_one_main_table(self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        grid = main_table(root)
        self.assertEqual(len([found for found in main_tables(root)
                              if not in_detail_pane(found)]), 1)
        self.assertEqual(len(grid.find_all("table")), 0)
        head = root.find(id="item-head")
        body = root.find(id="item-rows")
        for found, tag in ((head, "thead"), (body, "tbody")):
            self.assertIsNotNone(found)
            self.assertEqual(found.tag, tag)
            self.assertIs(found.closest("table"), grid)
        self.assertEqual(len(head_cells(root)), len(spec.keys))

    @per_list
    def test_each_row_selects_its_record_from_its_endpoint(
            self, spec: MainList) -> None:
        rows = body_rows(self.fetch(spec.path))
        self.assertTrue(rows)
        for row in rows[:30]:
            key = row.get("data-item")
            self.assertTrue(key)
            self.assertEqual(path_of(row.get("hx-get") or ""),
                             spec.details(key))
            self.assertEqual(row.get("hx-trigger"), "item-select")

    @per_list
    def test_the_rows_are_unique_by_their_keys(self, spec: MainList) -> None:
        keys = self.keys_of(spec)
        self.assertEqual(len(keys), len(set(keys)))

    @per_list
    def test_the_pane_holds_the_selected_record(self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        found = must_pane(root)
        self.assertIsNotNone(found)
        self.assertEqual(found.get("data-item"), row_keys(root)[0])
        self.assertEqual(marked(root), row_keys(root)[:1])

    @per_list
    def test_the_count_the_rows_and_the_pane_are_refreshed_parts(
            self, spec: MainList) -> None:
        """The parts that a dialog's save refreshes (Form dialogs)."""
        root = self.fetch(spec.path)
        for name in (spec.count, "item-rows", "item-detail"):
            with self.subTest(part=name):
                found = root.find(id=name)
                self.assertIsNotNone(found)
                self.assertIn("data-refresh", found.attrs)

    @per_list
    def test_the_page_is_framed_and_varies_on_the_cookie(
            self, spec: MainList) -> None:
        response = self.client.get(spec.path)
        root = page(response)
        self.assertIn("lab-frame", root.find("body").classes)
        self.assertIn("cookie", {
            name.strip().lower()
            for name in response.get("Vary", "").split(",")})


# ---------------------------------------------------------------------------
# The split


SPLIT_COOKIES = {
    "item": "item-list-split", "bulk": "bulk-list-split",
    "delivery": "delivery-list-split",
    "intermediate": "intermediate-list-split",
    "chemical": "chemical-list-split", "batch": "batch-list-split",
    "vessel": "vessel-list-split", "planning": "planning-list-split",
    "task": "task-list-split", "substance": "substance-list-split",
}
# The values of the controller `master-detail` on the outer split.
OUTER_VALUES = {
    "data-master-detail-level-value": "outer",
    "data-master-detail-rows-value": "item-rows",
    "data-master-detail-pane-value": "item-detail",
    "data-master-detail-param-value": "selected",
}


class SplitTests(MainListCase):
    """Each main list is one outer split of its table and its details
    pane, and a cookie remembers which side is larger."""

    @per_list
    def test_the_table_and_the_pane_are_the_two_panes_of_one_split(
            self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        outer = must_outer_split(root)
        direction, major = spec.layout
        other = "rows" if direction == "columns" else "columns"
        self.assertIn("split", outer.classes)
        self.assertIn(f"split--{direction}", outer.classes)
        self.assertNotIn(f"split--{other}", outer.classes)
        self.assertEqual(outer.get("data-major"), major)
        self.assertEqual(set((outer.get("data-controller") or "").split()),
                         {"split", "master-detail"})
        self.assertEqual(outer.get("data-split-cookie-value"),
                         SPLIT_COOKIES[spec.name])
        for name, value in OUTER_VALUES.items():
            self.assertEqual(outer.get(name), value, name)
        first, second = split_panes(outer)
        self.assertIn(main_table(root), list(first.walk()))
        self.assertIn(must_pane(root), list(second.walk()))
        self.assertEqual(len(split_panes(outer)), 2)

    @per_list
    def test_the_split_names_the_views_cookie_and_carries_the_view(
            self, spec: MainList) -> None:
        self.client.cookies[spec.cookie] = "details"
        outer = must_outer_split(self.fetch(spec.path))
        self.assertEqual(outer.get("data-view"), "details")
        self.assertIn(spec.cookie, outer.attrs.values())

    @per_list
    def test_the_old_layout_is_gone(self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        for name in ("item-layout", "item-layout--split"):
            self.assertEqual(root.find_all(cls=name), [], name)
        self.assertEqual(
            [node.tag for node in root.walk()
             if "split-list" in (node.get("data-controller") or "").split()
             or any(name.startswith("data-split-list")
                    for name in node.attrs)], [])
        self.assertEqual(len(root.find_all("div", cls="split--outer")), 1)

    @per_list
    def test_the_page_has_the_toggle(self, spec: MainList) -> None:
        for view in ("details", "table"):
            with self.subTest(view=view):
                self.client.cookies[spec.cookie] = view
                root = self.fetch(spec.path)
                found = [button for button in root.find_all("button")
                         if "split#toggle" in (
                             button.get("data-lab-action") or "")]
                self.assertEqual(len(found), 1)
                self.assertIsNotNone(found[0].closest("main"))
                self.assertTrue(
                    found[0].closest("form") is None
                    or found[0].get("type") == "button")

    @per_list
    def test_the_cookie_gives_the_larger_side(self, spec: MainList) -> None:
        direction, major = spec.layout
        flipped = "second" if major == "first" else "first"
        for cookie, wanted in ((None, major), (flipped, flipped),
                               (major, major), ("bogus", major),
                               ("", major), ("FIRST", major),
                               ("table", major)):
            with self.subTest(cookie=cookie):
                name = SPLIT_COOKIES[spec.name]
                self.client.cookies.pop(name, None)
                if cookie is not None:
                    self.client.cookies[name] = cookie
                outer = must_outer_split(self.fetch(spec.path))
                self.assertEqual(outer.get("data-major"), wanted)
                self.assertIn(f"split--{direction}", outer.classes)

    @per_list
    def test_another_lists_cookie_changes_nothing(
            self, spec: MainList) -> None:
        _, major = spec.layout
        flipped = "second" if major == "first" else "first"
        for name, cookie in SPLIT_COOKIES.items():
            if name != spec.name:
                self.client.cookies[cookie] = flipped
        self.client.cookies[spec.cookie] = "details"
        outer = must_outer_split(self.fetch(spec.path))
        self.assertEqual(outer.get("data-major"), major)

    def test_the_planning_list_keeps_its_details_view_with_a_split(
            self) -> None:
        spec = MAIN_LISTS["planning"]
        outer = must_outer_split(self.fetch(spec.path))
        self.assertEqual(outer.get("data-view"), "details")

    @per_list
    def test_only_the_category_lists_name_a_lot(self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        names = {name for name in hidden_fields(root)}
        linked = {name for cell in head_cells(root)
                  for link in cell.find_all("a")
                  for name in query_of(link.get("href"))}
        if spec.name in CATEGORY_LISTS:
            self.assertIn("lot", names)
            self.assertIn("lot", linked)
        else:
            self.assertNotIn("lot", names)
            self.assertNotIn("lot", linked)

    @per_list
    def test_a_pane_holds_no_split_but_the_category_lists(
            self, spec: MainList) -> None:
        pane = must_pane(self.fetch(spec.path))
        nested = pane.find_all("div", cls="split")
        if spec.name in ("intermediate", "chemical"):
            self.assertEqual(len(nested), 1)
            self.assertNotIn("split--outer", nested[0].classes)
        else:
            self.assertEqual(nested, [])


# ---------------------------------------------------------------------------
# The panes


PAGES_OF = {
    "item": r"^/lab/inventory/items/{key}/$",
    "bulk": r"^/lab/inventory/vessels/{key}/$",
    "delivery": r"^/lab/inventory/deliveries/{key}/$",
    "intermediate": r"^/lab/registry/substances/{key}/$",
    "chemical": r"^/lab/registry/substances/{key}/$",
    "batch": r"^/lab/inventory/batches/{key}/$",
    "vessel": r"^/lab/inventory/vessels/{key}/$",
    # The planning list is keyed by article number: its pane links to the
    # page of the article's substance.
    "planning": r"^/lab/registry/substances/[a-z0-9-]+/$",
    "task": r"^/lab/tasks/{key}/$",
    "substance": r"^/lab/registry/substances/{key}/$",
}


class PaneWidgetTests(MainListCase):
    """Every details pane of a record is a head with the record's title
    and its data in widgets (web-app: Main lists, Views)."""

    def selected(self, spec: MainList, count: int = 3) -> list[Element]:
        """The panes of the first COUNT records of the list, as the list's
        page holds them."""
        return [must_pane(self.fetch(
            f"{spec.path}?selected={quote(key)}"))
            for key in self.keys_of(spec)[:count]]

    @per_list
    def test_the_head_titles_the_record_and_links_to_its_page(
            self, spec: MainList) -> None:
        for pane in self.selected(spec):
            key = pane.get("data-item")
            with self.subTest(record=key):
                head = pane_head(pane)
                self.assertIsNotNone(head, "the pane has no head")
                self.assertEqual(len(pane.find_all(
                    id="item-detail-title")), 1)
                title = head.find("h2", id="item-detail-title")
                self.assertIsNotNone(title)
                link = title.find("a")
                self.assertIsNotNone(link, "the title links nowhere")
                self.assertRegex(path_of(link.get("href")), PAGES_OF[
                    spec.name].format(key=re.escape(key)))

    @per_list
    def test_the_data_is_in_widgets_with_h3_headings(
            self, spec: MainList) -> None:
        for pane in self.selected(spec):
            with self.subTest(record=pane.get("data-item")):
                found = pane_widgets(pane)
                self.assertTrue(found, "the pane holds no widget")
                for each in found:
                    head = each.find(cls="widget__head")
                    self.assertIsNotNone(head)
                    self.assertIsNotNone(head.find("h3"), head.text())
                    self.assertIsNone(head.find("h2"), head.text())
                    self.assertIsNotNone(
                        has_ancestor_class(each, "widget-grid"),
                        head.text())

    @per_list
    def test_the_titles_are_the_only_h2_of_a_pane(
            self, spec: MainList) -> None:
        for pane in self.selected(spec):
            with self.subTest(record=pane.get("data-item")):
                self.assertLessEqual(
                    {h.get("id") for h in pane.find_all("h2")},
                    {"item-detail-title", "lot-detail-title"})

    @per_list
    def test_the_details_endpoint_answers_the_same_head_and_widgets(
            self, spec: MainList) -> None:
        key = self.keys_of(spec)[1]
        path = spec.details(key) + ("?all=1" if spec.name == "planning"
                                    else "")
        found = must_pane(page(self.client.get(path, **HTMX)))
        head = pane_head(found)
        self.assertIsNotNone(head)
        self.assertIsNotNone(head.find("h2", id="item-detail-title"))
        self.assertTrue(pane_widgets(found))

    @per_list
    def test_an_empty_list_has_a_note_and_no_head(
            self, spec: MainList) -> None:
        if "q" not in spec.searches:
            return
        found = must_pane(self.fetch(f"{spec.path}?q=no-such-text-9"))
        self.assertIsNone(pane_head(found))
        self.assertEqual(pane_widgets(found), [])


# ---------------------------------------------------------------------------
# Sorting


class HeaderTests(MainListCase):
    """The header: ``aria-sort``, the links and the filter form."""

    @per_list
    def test_the_default_column_is_in_force_without_sort(
            self, spec: MainList) -> None:
        for query in ("", "?sort=nothing", "?dir=desc", "?sort="):
            with self.subTest(query=query):
                sorts = aria_sorts(self.fetch(spec.path + query))
                wanted = [None] * len(spec.keys)
                wanted[spec.keys.index(spec.default)] = (
                    "descending" if spec.descending else "ascending")
                self.assertEqual(sorts, wanted)

    @per_list
    def test_a_column_that_does_not_sort_is_the_default_order(
            self, spec: MainList) -> None:
        for key in spec.unsorted:
            with self.subTest(key=key):
                plain = self.fetch(spec.path)
                asked = self.fetch(f"{spec.path}?sort={key}")
                self.assertEqual(row_keys(asked), row_keys(plain))
                self.assertEqual(aria_sorts(asked), aria_sorts(plain))

    @per_list
    def test_the_requested_column_is_in_force(self, spec: MainList) -> None:
        for key in spec.sorted_keys:
            for direction, shown in (("", "ascending"),
                                     ("&dir=desc", "descending")):
                if direction and key not in (spec.default,
                                             self.other_key(spec)):
                    continue
                with self.subTest(sort=key, dir=shown):
                    root = self.fetch(
                        f"{spec.path}?sort={key}{direction}")
                    wanted = [None] * len(spec.keys)
                    wanted[spec.keys.index(key)] = shown
                    self.assertEqual(aria_sorts(root), wanted)

    @per_list
    def test_the_links_toggle_and_keep_the_selection(
            self, spec: MainList) -> None:
        for query, forced, descending in (
                ("", spec.default, spec.descending),
                (f"?sort={self.other_key(spec)}",
                 self.other_key(spec), False),
                (f"?sort={self.other_key(spec)}&dir=desc",
                 self.other_key(spec), True)):
            with self.subTest(query=query):
                root = self.fetch(spec.path + query)
                chosen = must_pane(root).get("data-item")
                for key, cell in zip(spec.keys, head_cells(root)):
                    if key in spec.unsorted:
                        self.assertIsNone(cell.find("a"), key)
                        continue
                    link = link_of(cell)
                    wanted = {"sort": [key], "selected": [chosen]}
                    if spec.name in CATEGORY_LISTS:
                        # The lot is part of the address (Lists by
                        # substance), so the links keep it.
                        wanted["lot"] = lot_marked(root)
                    if key == forced and not descending:
                        wanted["dir"] = ["desc"]
                    self.assertEqual(query_of(link.get("href")), wanted,
                                     key)

    @per_list
    def test_the_headers_update_the_list_in_place(
            self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        for key, cell in zip(spec.keys, head_cells(root)):
            if key in spec.unsorted:
                continue
            with self.subTest(key=key):
                link = link_of(cell)
                self.assertEqual(link.get("hx-get"), link.get("href"))

    @per_list
    def test_the_filter_form_keeps_an_order_that_is_not_the_default(
            self, spec: MainList) -> None:
        other = self.other_key(spec)
        plain = hidden_fields(self.fetch(spec.path))
        self.assertNotIn("sort", plain)
        self.assertNotIn("dir", plain)
        found = hidden_fields(self.fetch(f"{spec.path}?sort={other}"))
        self.assertEqual(found.get("sort"), other)
        self.assertNotIn("dir", found)
        found = hidden_fields(
            self.fetch(f"{spec.path}?sort={other}&dir=desc"))
        self.assertEqual((found.get("sort"), found.get("dir")),
                         (other, "desc"))

    @per_list
    def test_the_filter_form_names_no_order_that_is_the_default(
            self, spec: MainList) -> None:
        query = f"?sort={spec.default}" + (
            "&dir=desc" if spec.descending else "")
        found = hidden_fields(self.fetch(spec.path + query))
        self.assertNotIn("sort", found)
        self.assertNotIn("dir", found)

    def test_header_links_keep_filters_and_selection(self) -> None:
        """Scenario: Header links keep filters and selection."""
        from tasks.models import Task
        own = Task.objects.filter(assignee__initials="KL").first()
        self.assertIsNotNone(own)
        root = self.fetch(
            f"/lab/tasks/?state=all&person=KL&selected={own.number}")
        links = [cell.find("a") for cell in head_cells(root)
                 if cell.find("a") is not None]
        self.assertTrue(links, "the task list has no header links")
        for link in links:
            found = query_of(link.get("href"))
            self.assertEqual(found.get("state"), ["all"])
            self.assertEqual(found.get("person"), ["KL"])
            self.assertEqual(found.get("selected"), [own.number])
        self.assertEqual(must_pane(root).get("data-item"), own.number)
        other = self.fetch(
            f"/lab/tasks/?state=all&person=KL&sort=number&dir=desc"
            f"&selected={own.number}")
        form = hidden_fields(other)
        self.assertEqual((form.get("sort"), form.get("dir")),
                         ("number", "desc"))

    def test_an_unknown_key_in_the_substance_and_planning_lists(self) -> None:
        """Scenario: An unknown sort key."""
        registry = self.fetch("/lab/registry/?sort=nothing")
        by_name = aria_sorts(registry)
        self.assertEqual(by_name[0], "ascending")
        self.assertEqual(by_name.count(None), len(by_name) - 1)
        planning = self.fetch("/lab/planning/?sort=actions")
        cells = head_cells(planning)
        self.assertEqual(cells[3].get("aria-sort"), "ascending")
        self.assertEqual(cells[3].text(), "Spätester Start")
        self.assertEqual(cells[6].text(), "Maßnahmen")
        self.assertIsNone(cells[6].find("a"))
        self.assertIsNone(cells[6].get("aria-sort"))


# ---------------------------------------------------------------------------
# Selection


class SelectionTests(MainListCase):
    """Selection: ``selected`` names one of the records listed, else the
    first; the selected row carries ``aria-current``."""

    @per_list
    def test_selected_names_a_record_listed(self, spec: MainList) -> None:
        keys = self.keys_of(spec)
        second = keys[1]
        root = self.fetch(f"{spec.path}?selected={second}")
        self.assertEqual(marked(root), [second])
        self.assertEqual(must_pane(root).get("data-item"), second)

    @per_list
    def test_without_selected_the_first_record_is_selected(
            self, spec: MainList) -> None:
        for query in ("", "?selected=", "?selected=no-such-record-0"):
            with self.subTest(query=query):
                root = self.fetch(spec.path + query)
                first = row_keys(root)[0]
                self.assertEqual(marked(root), [first])
                self.assertEqual(must_pane(root).get("data-item"), first)

    @per_list
    def test_sorting_keeps_the_selected_record(self, spec: MainList) -> None:
        second = self.keys_of(spec)[1]
        root = self.fetch(
            f"{spec.path}?sort={self.other_key(spec)}&selected={second}")
        self.assertEqual(marked(root), [second])
        self.assertEqual(must_pane(root).get("data-item"), second)

    @per_list
    def test_the_selected_row_is_the_only_one_marked(
            self, spec: MainList) -> None:
        second = self.keys_of(spec)[1]
        root = self.fetch(f"{spec.path}?selected={second}")
        marks = [e for e in root.walk()
                 if e.get("aria-current") == "true"
                 and e.tag == "tr" and not in_detail_pane(e)]
        self.assertEqual(len(marks), 1)

    def test_selecting_a_record_of_a_new_split_list(self) -> None:
        """Scenario: Selecting a record of a new split list."""
        for name in ("task", "substance", "batch", "vessel"):
            with self.subTest(list=name):
                spec = MAIN_LISTS[name]
                second = self.keys_of(spec)[1]
                root = self.fetch(f"{spec.path}?selected={second}")
                rows = body_rows(root)
                self.assertEqual(
                    [row.get("data-item") for row in rows
                     if row.get("aria-current") == "true"], [second])
                for row in rows:
                    self.assertEqual(path_of(row.get("hx-get")),
                                     spec.details(row.get("data-item")))
                    self.assertEqual(row.get("hx-trigger"), "item-select")
                self.assertEqual(must_pane(root).get("data-item"), second)
                self.assertTrue(must_pane(root).text())


# ---------------------------------------------------------------------------
# Views


class ViewTests(MainListCase):
    """The views ``Tabelle`` and ``Details`` and the cookie that
    remembers the one last chosen."""

    def view_of(self, spec: MainList, cookie: str | None) -> str:
        self.client.cookies.pop(spec.cookie, None)
        if cookie is not None:
            self.client.cookies[spec.cookie] = cookie
        root = self.fetch(spec.path)
        layout = must_outer_split(root)
        chosen = [radio.get("value") for radio in root.find_all(
            "input", attrs={"name": "view"}) if "checked" in radio.attrs]
        self.assertEqual(chosen, [layout.get("data-view")])
        return layout.get("data-view")

    @per_list
    def test_a_list_opens_in_the_view_its_cookie_names(
            self, spec: MainList) -> None:
        self.assertEqual(self.view_of(spec, "details"), "details")
        self.assertEqual(self.view_of(spec, "table"), "table")

    @per_list
    def test_without_a_cookie_a_list_opens_in_its_own_view(
            self, spec: MainList) -> None:
        self.assertEqual(self.view_of(spec, None), spec.opens)
        self.assertEqual(self.view_of(spec, "bogus"), spec.opens)

    def test_views_from_the_cookie(self) -> None:
        """Scenario: Views from the cookie."""
        self.assertEqual(self.view_of(MAIN_LISTS["task"], None), "table")
        self.assertEqual(self.view_of(MAIN_LISTS["task"], "details"),
                         "details")
        self.assertEqual(self.view_of(MAIN_LISTS["planning"], None),
                         "details")
        self.assertEqual(self.view_of(MAIN_LISTS["planning"], "table"),
                         "table")

    @per_list
    def test_the_views_are_named_table_and_details(
            self, spec: MainList) -> None:
        root = self.fetch(spec.path)
        switch = root.find("fieldset", cls="view-switch")
        self.assertIsNotNone(switch)
        self.assertEqual([label.text() for label in
                          switch.find_all("label")],
                         ["Tabelle", "Details"])


# ---------------------------------------------------------------------------
# Details endpoints


class DetailsEndpointTests(MainListCase):
    """The details endpoints of the five lists that gain one."""

    NEW = ("task", "substance", "batch", "vessel", "planning")

    def test_details_requested_without_htmx_redirect_to_the_list(
            self) -> None:
        """Scenario: Details requested without htmx."""
        for name in self.NEW:
            spec = MAIN_LISTS[name]
            with self.subTest(list=name):
                key = self.keys_of(spec)[1]
                response = self.client.get(spec.details(key))
                self.assertEqual(response.status_code, 302)
                found = urlsplit(response["Location"])
                self.assertEqual(found.path, spec.path)
                self.assertIn(key, query_of(response["Location"])
                              .get("selected", []))

    def test_an_unknown_key_answers_404(self) -> None:
        for name in self.NEW:
            spec = MAIN_LISTS[name]
            with self.subTest(list=name):
                for extra in ({}, HTMX):
                    response = self.client.get(
                        spec.details("no-such-record-9"), **extra)
                    self.assertEqual(response.status_code, 404)

    def test_htmx_gets_the_pane_alone_and_the_list_address(self) -> None:
        for name in self.NEW:
            spec = MAIN_LISTS[name]
            with self.subTest(list=name):
                key = self.keys_of(spec)[1]
                response = self.client.get(spec.details(key), **HTMX)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                for tag in ("html", "head", "body", "main", "nav"):
                    self.assertEqual(root.find_all(tag), [])
                found = [c for c in root.children if isinstance(c, Element)]
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].get("id"), "item-detail")
                self.assertEqual(found[0].get("data-item"), key)
                replace = response["HX-Replace-Url"]
                self.assertEqual(urlsplit(replace).path, spec.path)
                self.assertEqual(query_of(replace).get("selected"), [key])

    def test_a_nested_level_answers_with_its_own_pane(self) -> None:
        """Scenario: Split-view detail response sets HX-Replace-Url (a
        nested level)."""
        for name in ("intermediate", "chemical"):
            spec = MAIN_LISTS[name]
            with self.subTest(list=name):
                key = self.keys_of(spec)[1]
                lots = lot_keys(self.fetch(f"{spec.path}?selected={key}"))
                self.assertGreater(len(lots), 0)
                path = f"{spec.details(key)}lots/{lots[-1]}/"
                current = {**HTMX, "HTTP_HX_CURRENT_URL":
                           f"http://testserver{spec.path}?q=&selected=x"}
                response = self.client.get(path, **current)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                for tag in ("html", "head", "body", "main", "nav"):
                    self.assertEqual(root.find_all(tag), [])
                found = [c for c in root.children if isinstance(c, Element)]
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].get("id"), "lot-detail")
                self.assertEqual(found[0].get("data-item"), lots[-1])
                self.assertEqual(root.find_all(id="item-detail"), [])
                varied = {part.strip().lower() for part in
                          response.get("Vary", "").split(",")}
                self.assertLessEqual({"hx-request", "hx-current-url"},
                                     varied)
                address = replaced(self, response)
                self.assertEqual(urlsplit(address).path, spec.path)
                self.assertEqual(query_of(address).get("selected"), [key])
                self.assertEqual(query_of(address).get("lot"), [lots[-1]])
                foreign = self.client.get(path, **{
                    **HTMX, "HTTP_HX_CURRENT_URL":
                    f"http://evil.example{spec.path}?q=x"})
                self.assertEqual(query_of(replaced(self, foreign)),
                                 {"selected": [key], "lot": [lots[-1]]})

    @per_list
    def test_a_list_with_no_record_has_a_note_in_its_pane(
            self, spec: MainList) -> None:
        if "q" not in spec.searches:
            return
        root = self.fetch(f"{spec.path}?q=no-such-text-9")
        self.assertEqual(row_keys(root), [])
        found = must_pane(root)
        self.assertIsNotNone(found)
        self.assertNotIn("data-item", found.attrs)
        self.assertTrue(found.text())


# ---------------------------------------------------------------------------
# One look


class MainTableLookTests(MainListCase):
    """The look all ten main tables share: bold columns, whole names in
    the tooltip of a name that the screen cuts, and the planning list's
    article on one line."""

    LIMIT = 40

    def columns(self, spec: MainList, root: Element) -> list[
            tuple[str, Element, list[Element]]]:
        """Each column of the main table as its key, its header and its
        cells in the first LIMIT rows."""
        rows = [cells(row) for row in body_rows(root)[:self.LIMIT]]
        self.assertTrue(rows, spec.name)
        for row in rows:
            self.assertEqual(len(row), len(spec.keys), spec.name)
        return [(key, head, [row[index] for row in rows])
                for index, (key, head)
                in enumerate(zip(spec.keys, head_cells(root)))]

    @per_list
    def test_the_header_and_cells_of_two_columns_are_strong(
            self, spec: MainList) -> None:
        for key, head, body in self.columns(spec, self.fetch(spec.path)):
            with self.subTest(column=key):
                strong = key in spec.strong
                self.assertEqual("col-strong" in head.classes, strong)
                for cell in body:
                    self.assertEqual("col-strong" in cell.classes, strong,
                                     cell.text())

    @per_list
    def test_a_capped_name_cell_shows_its_whole_name_in_its_title(
            self, spec: MainList) -> None:
        if not spec.capped:
            return
        found = 0
        for key, _, body in self.columns(spec, self.fetch(spec.path)):
            if key != spec.capped:
                continue
            for cell in body:
                links = cell.find_all("a")
                name = links[-1].text() if links else cell.text()
                if not name:
                    continue
                found += 1
                with self.subTest(name=name):
                    title = cell.get("title")
                    self.assertTrue(title, "the cell has no title")
                    self.assertIn(name, " ".join(title.split()))
        self.assertTrue(found, f"{spec.name} has no cell with a name")

    def test_a_name_that_the_screen_cuts_shows_whole_in_the_title(
            self) -> None:
        """The longest name of the demo data set, in each list that has
        capped cells, is in the title of its cell."""
        for spec in MAIN_LISTS.values():
            if not spec.capped:
                continue
            with self.subTest(list=spec.name):
                root = self.fetch(spec.path)
                names = []
                for row in body_rows(root):
                    cell = cells(row)[spec.keys.index(spec.capped)]
                    links = cell.find_all("a")
                    names.append((links[-1].text() if links
                                  else cell.text(), cell))
                longest, cell = max(names, key=lambda pair: len(pair[0]))
                self.assertGreater(len(longest), 10)
                self.assertIn(longest, " ".join(
                    (cell.get("title") or "").split()))

    def test_the_planning_article_is_one_line_number_first(self) -> None:
        spec = MAIN_LISTS["planning"]
        root = self.fetch(spec.path)
        index = spec.keys.index("article")
        rows = body_rows(root)
        self.assertTrue(rows)
        for row in rows[:self.LIMIT]:
            number = row.get("data-item")
            cell = cells(row)[index]
            with self.subTest(number=number):
                self.assertEqual(
                    [e.tag for e in cell.walk() if "kv-sub" in e.classes],
                    [])
                self.assertEqual(
                    [e.tag for e in cell.walk()
                     if e.tag in ("br", "div", "p", "ul", "ol")], [])
                text = cell.text()
                links = cell.find_all("a")
                self.assertTrue(links)
                name = links[-1].text()
                self.assertTrue(text.startswith(number), text)
                self.assertLess(text.index(number), text.index(name))


# ---------------------------------------------------------------------------
# The two table classes


class TableClassesTests(MainListCase):
    """Every table of the pages under ``/lab/`` is a main table or an
    auxiliary one."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        from accounts.models import AccessToken
        cls.user = get_user_model().objects.get(username="klehmann")
        AccessToken.create_for(cls.user, "Laptop")

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.user)

    def assert_classes(self, root: Element, path: str, main: int = 0,
                       lots: int = 0) -> None:
        """Every table of ROOT carries exactly one of the classes, MAIN
        of them is a main table outside the details pane, and LOTS of
        them, the lot tables of a category list, is one inside it."""
        mains = in_pane = 0
        for grid in root.find_all("table"):
            found = grid.classes & {"main-table", "aux-table"}
            self.assertEqual(len(found), 1,
                             f"{path}: a table has classes {grid.classes}")
            if "main-table" in found:
                if in_detail_pane(grid):
                    in_pane += 1
                    self.assertEqual(grid.get("id"), LOT_TABLE, path)
                else:
                    mains += 1
        self.assertEqual(mains, main, path)
        self.assertEqual(in_pane, lots, path)

    @staticmethod
    def lots_of(spec: MainList) -> int:
        """The lot tables a details pane of the list holds: one in the
        category lists, whose rows are substances with open vessels."""
        return 1 if spec.name in ("intermediate", "chemical") else 0

    @per_list
    def test_the_main_lists_hold_one_main_table_each(
            self, spec: MainList) -> None:
        self.assert_classes(self.fetch(spec.path), spec.path, 1,
                            self.lots_of(spec))

    @per_list
    def test_the_details_of_each_list_hold_auxiliary_tables(
            self, spec: MainList) -> None:
        keys = self.keys_of(spec)
        for key in dict.fromkeys([*keys[:4], *keys[-2:]]):
            path = spec.details(key) if spec.name != "planning" \
                else spec.details(key) + "?all=1"
            response = self.client.get(path, **HTMX)
            self.assertEqual(response.status_code, 200, path)
            self.assert_classes(page(response), path, 0, self.lots_of(spec))

    @per_list
    def test_a_lot_table_is_a_main_table_that_sorts_in_the_browser(
            self, spec: MainList) -> None:
        if not self.lots_of(spec):
            return
        found = lot_tables(self.fetch(spec.path))
        self.assertEqual(len(found), 1)
        grid = found[0]
        self.assertEqual(grid.get("id"), LOT_TABLE)
        self.assertEqual(unsorted_reasons(grid.closest("aside")), [])
        self.assertIn("data-sortable", grid.attrs)
        self.assertIn("sortable-table",
                      (grid.get("data-controller") or "").split())

    def test_the_other_pages_hold_auxiliary_tables(self) -> None:
        """Scenario: Two table classes (the pages other than lists)."""
        from collection.models import Import
        from inventory.models import (Batch, DeliveryLine, DeliveryNote,
                                      Item, Vessel)
        from journal.models import Notebook
        from tasks.models import Task
        batch = next(b for b in Batch.objects.order_by("pk")
                     if b.vessels.exists()
                     and DeliveryLine.objects.filter(batch=b).exists())
        task = max(Task.objects.order_by("pk"),
                   key=lambda found: found.steps.count())
        self.assertGreater(task.steps.count(), 1)
        item = Item.objects.order_by("pk").first()
        paths = [
            "/lab/",
            f"/lab/inventory/items/{item.pk}/",
            f"/lab/inventory/batches/{batch.pk}/",
            f"/lab/inventory/vessels/{batch.vessels.first().pk}/",
            f"/lab/inventory/deliveries/{DeliveryNote.objects.first().pk}/",
            f"/lab/tasks/{task.number}/",
            "/lab/registry/substances/acetylsalicylic-acid/",
            "/lab/registry/substances/cinnamic-acid/",
            f"/lab/inventory/items/{item.pk}/consumption/",
            "/lab/inventory/deliveries/new/",
            "/lab/journal/",
            f"/lab/journal/{Notebook.objects.first().code}/",
            "/lab/collection/",
            "/lab/registry/groups/",
            "/lab/accounts/tokens/",
        ]
        self.assertTrue(Import.objects.exists())
        self.assertTrue(Vessel.objects.exists())
        for path in paths:
            with self.subTest(path=path):
                self.assert_classes(self.fetch(path), path)

    def test_key_value_tables_are_auxiliary_tables(self) -> None:
        root = self.fetch("/lab/registry/substances/cinnamic-acid/")
        found = root.find_all("table", cls="kv-table")
        self.assertTrue(found)
        for grid in found:
            self.assertIn("aux-table", grid.classes)
            self.assertNotIn("main-table", grid.classes)


# ---------------------------------------------------------------------------
# Sorting, with records of the tests' own


class SortingScenarioTests(InventoryCase):
    """The scenarios of web-app: Main lists, Sorting, on records the test
    makes."""

    BATCHES = "/lab/inventory/batches/"
    VESSELS = "/lab/inventory/vessels/"
    ITEMS = "/lab/inventory/end-products/"

    def keys(self, path: str) -> list[str]:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return row_keys(page(response))

    def make_batches(self) -> tuple[Any, Any, Any]:
        """Batches dated 2026-01-02 and 2026-03-04, and one undated, of
        three substances named so that the default order differs from the
        orders the tests ask for."""
        early = make_batch(self.kl, "CH-0012", number="KL-1",
                           date=date(2026, 1, 2))
        late = make_batch(self.kl, "CH-0013", number="KL-2",
                          date=date(2026, 3, 4))
        none = make_batch(self.kl, "CH-0016", number="KL-3")
        return early, late, none

    def test_sorting_by_a_column(self) -> None:
        """Scenario: Sorting by a column."""
        early, late, none = self.make_batches()
        ids = [str(late.pk), str(early.pk), str(none.pk)]
        for query in ("", "?sort=date&dir=desc"):
            with self.subTest(query=query):
                response = self.client.get(self.BATCHES + query)
                root = page(response)
                self.assertEqual(row_keys(root), ids)
                header = head_cells(root)[5]
                self.assertEqual(header.get("aria-sort"), "descending")
                self.assertEqual(
                    query_of(link_of(header).get("href")),
                    {"sort": ["date"], "selected": [str(late.pk)]})
        root = page(self.client.get(self.BATCHES + "?sort=date"))
        self.assertEqual(row_keys(root),
                         [str(early.pk), str(late.pk), str(none.pk)])
        header = head_cells(root)[5]
        self.assertEqual(header.get("aria-sort"), "ascending")
        self.assertEqual(
            query_of(link_of(header).get("href")),
            {"sort": ["date"], "dir": ["desc"],
             "selected": [str(early.pk)]})
        self.assertEqual([i for i, sort in enumerate(aria_sorts(root))
                          if sort], [5])

    def test_the_canonical_address_omits_the_default_order(self) -> None:
        """Scenario: The canonical address omits the default order."""
        self.make_batches()
        self.item("CH-0012", category="Ester")
        found = {}
        for query in ("?sort=date&dir=desc", "?sort=yield"):
            response = self.client.get(self.BATCHES + query, **HTMX)
            found[query] = (response["HX-Push-Url"],
                            row_keys(page(response))[0])
        self.assertEqual(
            found["?sort=date&dir=desc"][0],
            f"{self.BATCHES}?selected={found['?sort=date&dir=desc'][1]}")
        self.assertEqual(
            found["?sort=yield"][0],
            f"{self.BATCHES}?sort=yield&selected={found['?sort=yield'][1]}")
        response = self.client.get(self.ITEMS + "?sort=category", **HTMX)
        pushed = urlsplit(response["HX-Push-Url"])
        self.assertEqual(pushed.path, self.ITEMS)
        self.assertEqual(sorted(query_of(response["HX-Push-Url"])),
                         ["selected"])

    CHEMICALS = "/lab/inventory/chemicals/"

    def amounts(self) -> dict[str, Any]:
        """Open vessels of 1 g, 500 mg and 20 µmol of one article."""
        return {
            "1 g": make_vessel(self.kl, unit="g", amount="1",
                               article="CH-0012", date=date(2026, 1, 1)),
            "500 mg": make_vessel(self.kl, unit="mg", amount="500",
                                  article="CH-0012",
                                  date=date(2026, 2, 1)),
            "20 µmol": make_vessel(self.kl, unit="umol", amount="20",
                                   article="CH-0012",
                                   date=date(2026, 3, 1)),
        }

    def chemicals(self, opened: str, sealed: str) -> dict[str, str]:
        """Two commercial chemicals named OPENED and SEALED, the first
        with a bottle opened on 2026-05-01 and the second with a sealed
        one; the key of the first and of the second by their names."""
        from inventory.models import Vessel
        first = make_vessel(self.kl, unit="mg", amount="5", article=opened,
                            source="bought", supplier="Sigma")
        second = make_vessel(self.kl, unit="mg", amount="5",
                             article=sealed, source="bought",
                             supplier="Sigma")
        Vessel.objects.filter(pk=first.pk).update(
            opened_on=date(2026, 5, 1))
        return {"opened": first.batch.substance.key,
                "sealed": second.batch.substance.key}

    def test_amounts_across_units_and_text_after_values(self) -> None:
        """Scenario: Amounts across units and text after values."""
        self.amounts()
        response = self.client.get(self.VESSELS + "?sort=amount")
        root = page(response)
        shown = [cell.text() for row in body_rows(root)
                 for cell in row.find_all("td")
                 if cell.text() in ("500 mg", "1 g", "20 µmol")]
        self.assertEqual(shown, ["500 mg", "1 g", "20 µmol"])
        found = self.chemicals("benzaldehyde", "acetophenone")
        self.assertEqual(self.keys(self.CHEMICALS),
                         [found["sealed"], found["opened"]])
        self.assertEqual(self.keys(self.CHEMICALS + "?sort=opened"),
                         [found["opened"], found["sealed"]])

    def test_descending_puts_text_first(self) -> None:
        """Scenario: Descending puts text first."""
        found = self.chemicals("acetophenone", "benzaldehyde")
        self.assertEqual(self.keys(self.CHEMICALS),
                         [found["opened"], found["sealed"]])
        self.assertEqual(self.keys(self.CHEMICALS + "?sort=opened&dir=desc"),
                         [found["sealed"], found["opened"]])

    def test_sorting_text_with_numbers_in_it(self) -> None:
        """Scenario: Sorting text with numbers in it."""
        from inventory.models import Vessel
        older = make_batch(self.kl, "CH-0012", number="KL-1",
                           date=date(2026, 1, 1))
        newer = make_batch(self.kl, "CH-0012", number="KL-2",
                           date=date(2026, 2, 1))
        for pk, batch in ((10, older), (2, newer)):
            vessel = Vessel(pk=pk, batch=batch, unit="mg",
                            amount=Decimal("50"))
            vessel._history_user = self.kl
            vessel.save()
        self.assertEqual(self.keys(self.VESSELS), ["10", "2"])
        self.assertEqual(self.keys(self.VESSELS + "?sort=vessel"),
                         ["2", "10"])
        self.assertEqual(self.keys(self.VESSELS + "?sort=vessel&dir=desc"),
                         ["10", "2"])

    def test_sorting_the_substance_list_by_its_columns(self) -> None:
        """Substance names sort regardless of case, then by key."""
        substance_for("zz-1", "zebra")
        substance_for("aa-1", "Alpha")
        substance_for("mm-1", "middle")
        response = self.client.get("/lab/registry/?sort=name&dir=desc")
        keys = row_keys(page(response))
        self.assertEqual(keys[:3], ["zz-1", "mm-1", "aa-1"])
        self.assertEqual(
            row_keys(page(self.client.get("/lab/registry/")))[:3],
            ["aa-1", "mm-1", "zz-1"])


class ColumnOrderTests(InventoryCase):
    """The orders of columns whose cells hold more than a number or a
    text (web-app: Main lists, "A column orders its rows by the value
    its cells show")."""

    TASKS = "/lab/tasks/"
    BATCHES = "/lab/inventory/batches/"

    def numbers(self, path: str) -> list[str]:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return row_keys(page(response))

    def test_a_task_state_by_the_order_of_states(self) -> None:
        from tasks.models import Task
        ended = make_task(self.kl, "Aspirin", started=past(1), ended=past(2),
                          report=True, qc_list=True)
        planned = make_task(self.kl, "Aspirin")
        cancelled = make_task(self.kl, "Aspirin", cancelled=True)
        running = make_task(self.kl, "Aspirin", started=past(1))
        wanted = [running, planned, ended, cancelled]
        self.assertEqual(Task.objects.count(), 4)
        self.assertEqual(
            self.numbers(f"{self.TASKS}?state=all&sort=state"),
            [t.number for t in wanted])
        self.assertEqual(
            self.numbers(f"{self.TASKS}?state=all&sort=state&dir=desc"),
            [t.number for t in wanted[::-1]])

    def test_a_priority_by_its_rank(self) -> None:
        low = make_task(self.kl, "Aspirin", priority="low")
        high = make_task(self.kl, "Aspirin", priority="high")
        medium = make_task(self.kl, "Aspirin", priority="medium")
        self.assertEqual(self.numbers(self.TASKS),
                         [t.number for t in (high, medium, low)])
        self.assertEqual(self.numbers(f"{self.TASKS}?sort=priority"),
                         [t.number for t in (high, medium, low)])
        self.assertEqual(
            self.numbers(f"{self.TASKS}?sort=priority&dir=desc"),
            [t.number for t in (low, medium, high)])

    def test_a_progress_by_the_share_of_steps_done(self) -> None:
        quarter = make_task(self.kl, "Aspirin", steps=4, done=1,
                            started=past(1))
        whole = make_task(self.kl, "Aspirin", steps=2, done=2,
                          started=past(1))
        half = make_task(self.kl, "Aspirin", steps=2, done=1,
                         started=past(1))
        none = make_task(self.kl, "Aspirin", started=past(1))
        self.assertEqual(
            self.numbers(f"{self.TASKS}?sort=progress"),
            [t.number for t in (quarter, half, whole, none)])
        self.assertEqual(
            self.numbers(f"{self.TASKS}?sort=progress&dir=desc"),
            [t.number for t in (whole, half, quarter, none)])

    def test_a_yield_by_its_value_in_the_smallest_unit(self) -> None:
        gram = make_batch(self.kl, "CH-0012", number="KL-1",
                          yield_amount="1", yield_unit="g")
        milli = make_batch(self.kl, "CH-0012", number="KL-2",
                           yield_amount="500", yield_unit="mg")
        none = make_batch(self.kl, "CH-0012", number="KL-3")
        self.assertEqual(
            self.numbers(f"{self.BATCHES}?sort=yield"),
            [str(b.pk) for b in (milli, gram, none)])
        self.assertEqual(
            self.numbers(f"{self.BATCHES}?sort=yield&dir=desc"),
            [str(b.pk) for b in (gram, milli, none)])

    def test_a_stock_of_several_units_by_its_masses_then_its_moles(
            self) -> None:
        """Masses summed in mg, then amounts of substance summed in
        µmol, then batches without a stock, in either direction."""
        def batch(number: str, *vessels: tuple[str, str]) -> Any:
            found = make_batch(self.kl, "CH-0012", number=number)
            for unit, amount in vessels:
                make_vessel(self.kl, found, unit=unit, amount=amount)
            return found
        mixed = batch("KL-1", ("g", "2"), ("mg", "30"))
        gram = batch("KL-2", ("g", "1"))
        moles = batch("KL-3", ("umol", "5"))
        empty = batch("KL-4")
        self.assertEqual(
            self.numbers(f"{self.BATCHES}?sort=stock"),
            [str(b.pk) for b in (gram, mixed, moles, empty)])
        self.assertEqual(
            self.numbers(f"{self.BATCHES}?sort=stock&dir=desc"),
            [str(b.pk) for b in (moles, mixed, gram, empty)])

    def test_a_batch_by_its_number_regardless_of_digits(self) -> None:
        low = make_batch(self.kl, "CH-0012", number="KL2",
                         date=date(2026, 1, 1))
        high = make_batch(self.kl, "CH-0012", number="KL10",
                          date=date(2026, 2, 1))
        self.assertEqual(self.numbers(self.BATCHES),
                         [str(high.pk), str(low.pk)])
        self.assertEqual(self.numbers(f"{self.BATCHES}?sort=batch"),
                         [str(low.pk), str(high.pk)])


class PaneTablesTests(MainListCase):
    """The tables in the details of every main list sort in the browser
    (web-app: Widgets, "Widget and pane tables sort in the browser")."""

    DATE = re.compile(r"\A(\d{2})\.(\d{2})\.(\d{4})(?: (\d{2}):(\d{2}))?\Z")
    ISO = re.compile(r"\A\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?\Z")

    def panes(self, spec: MainList) -> list[Element]:
        keys = self.keys_of(spec)
        found = []
        for key in dict.fromkeys([*keys[:5], *keys[-3:]]):
            path = spec.details(key) + ("?all=1" if spec.name == "planning"
                                        else "")
            response = self.client.get(path, **HTMX)
            self.assertEqual(response.status_code, 200, path)
            found.append(must_pane(page(response)))
        return found

    @per_list
    def test_every_record_table_of_a_pane_is_sortable(
            self, spec: MainList) -> None:
        tables = 0
        for found in self.panes(spec):
            self.assertEqual(unsorted_reasons(found), [])
            tables += len([t for t in found.find_all("table")
                           if lists_records(t)])
        if spec.name != "item":
            self.assertGreater(tables, 0)

    @per_list
    def test_a_cell_shows_a_date_exactly_when_its_key_is_one(
            self, spec: MainList) -> None:
        for found in self.panes(spec):
            for grid in found.find_all("table"):
                if not lists_records(grid):
                    continue
                for cell in grid.find_all("td"):
                    shown = self.DATE.match(cell.text())
                    key = cell.get("data-sort") or ""
                    if shown:
                        day, month, year, hour, minute = shown.groups()
                        wanted = f"{year}-{month}-{day}" + (
                            f"T{hour}:{minute}" if hour else "")
                        self.assertEqual(key, wanted, cell.text())
                    elif not re.search(r"\d{2}\.\d{2}\.\d{4}", cell.text()):
                        self.assertFalse(self.ISO.match(key),
                                         f"{cell.text()!r} keys {key!r}")


