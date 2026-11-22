"""Tests of the item's consumption as one piece that the item page and the
consumption form share: the change history of entered consumption, the
links per quarter, the form for a quarter and the consumption beside its
fields (end-product-inventory: Consumption, Item page, Inventory
forms)."""

import re
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlsplit


from inventory.bookings import (book_note, enter_consumption,
                                reverse_historical)

from . import (Element, berlin, field_value, frozen, page)
from .collection_support import accept
from .inventory_support import (LIST, FormCase, cells, has_number,
                                historical_line, item_url, num)
from .test_inventory_detail import detail_url, pane_of
from .test_inventory_dialogs import HTMX, controls_of, errors_at
from .widget_support import history_entries

LABEL = re.compile(r"Q([1-4]) (\d{4})")
CHANGE, ENTER = "Ändern", "Nachtragen"
HEADING = "Verbrauch Q{} {}"


def form_url(item: Any, year: Any = None, quarter: Any = None) -> str:
    """The consumption form of ``item``, for a quarter when ``year`` is
    given."""
    base = item_url(item, "consumption")
    return base if year is None else f"{base}?year={year}&quarter={quarter}"


def history_of(item: Any, year: int, quarter: int) -> list[Any]:
    """The history records of the entered consumption of a quarter, the
    oldest first."""
    from inventory.models import EnteredConsumption
    manager = getattr(EnteredConsumption, "history", None)
    assert manager is not None, "EnteredConsumption keeps no history"
    return list(manager.filter(item_id=item.pk, year=year,
                               quarter=quarter).order_by("history_id"))


def changed(text: str, old: str, new: str) -> bool:
    """Whether ``text`` shows a change of a count from ``old`` to ``new``
    (``–`` for none)."""
    return re.search(
        rf"(?<!\d){re.escape(old)} → {re.escape(new)}(?!\d)",
        text) is not None


def history_texts(root: Element) -> list[str]:
    """The text of each entry of the page's change history, in page
    order."""
    return [entry.text for entry in history_entries(root)]


def quarter_rows(root: Element) -> dict[tuple[int, int], Element]:
    """The rows of the table of quarters in ``root``, the first table
    with rows headed ``Q<n> <year>``, by year and quarter."""
    grids = root.find_all("table")
    assert grids, "no table of quarters"
    rows: dict[tuple[int, int], Element] = {}
    for grid in grids:
        for row in grid.find_all("tr"):
            head = row.find("th", scope="row")
            found = LABEL.match(head.text()) if head is not None else None
            if found:
                rows[(int(found.group(2)), int(found.group(1)))] = row
        if rows:
            break
    return rows


def figures_of(root: Element) -> dict[tuple[int, int], list[Any]]:
    """The entered value, deliveries and total of each row of the table
    of quarters."""
    return {key: [num(cell) for cell in cells(row)[1:4]]
            for key, row in quarter_rows(root).items()}


def bars_of(root: Element) -> list[str]:
    svg = root.find("svg")
    assert svg is not None, "no chart"
    return [t.text() for t in svg.find_all("title") if t.parent is not svg]


def link_of(row: Element) -> Element | None:
    """The one link a row of the table of quarters carries, or None."""
    found = row.find_all("a")
    assert len(found) <= 1, [a.text() for a in found]
    return found[0] if found else None


def outside_table(scope: Element) -> str:
    """The text of ``scope`` outside the chart and the table of
    quarters."""
    return scope.text(skip=lambda node: node.tag in ("table", "svg"))


def target_of(link: Element) -> str | None:
    """The ``hx-target`` that applies to ``link``, its own or an
    ancestor's."""
    node: Element | None = link
    while node is not None:
        if "hx-target" in node.attrs:
            return node.get("hx-target")
        node = node.parent
    return None


class WidgetCase(FormCase):
    """A signed-in user, who requests pages as pages."""

    def item_page(self, item: Any) -> Element:
        response = self.client.get(item_url(item))
        self.assertEqual(response.status_code, 200)
        return page(response)

    def scenario_item(self) -> Any:
        """An item with an article number, the entered value 40 for the
        third quarter of 2026, 0 for the second quarter of 2025, none for
        the second quarter of 2026, and a historical note with a line
        dated in the first quarter of 2026."""
        item = self.item("CH-0012", quantity=5)
        self.enter(item, 2026, 3, 40)
        self.enter(item, 2025, 2, 0)
        book_note(self.kl, date=date(2026, 2, 10), historical=True,
                  lines=[historical_line(item, 2)])
        return item


# ---------------------------------------------------------------------------
# 1.1 The history of entered consumption


class RecordedHistoryTests(WidgetCase):

    def test_entering_a_value_writes_a_creation_record(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        found = history_of(item, 2026, 3)
        self.assertEqual([r.history_type for r in found], ["+"])
        self.assertEqual(found[0].count, 400)
        self.assertEqual(found[0].history_user_id, self.kl.pk)

    def test_replacing_a_value_writes_a_record_naming_the_user(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        enter_consumption(self.ae, item, year=2026, quarter=3, count=40)
        found = history_of(item, 2026, 3)
        self.assertEqual([r.history_type for r in found], ["+", "~"])
        self.assertEqual([r.count for r in found], [400, 40])
        self.assertEqual([r.history_user_id for r in found],
                         [self.kl.pk, self.ae.pk])

    def test_removing_a_value_leaves_a_record_naming_the_user(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        enter_consumption(self.ae, item, year=2026, quarter=3, count=None)
        found = history_of(item, 2026, 3)
        self.assertEqual([r.history_type for r in found], ["+", "-"])
        self.assertEqual(found[-1].count, 400)
        self.assertEqual(found[-1].history_user_id, self.ae.pk)

    def test_each_quarter_has_its_own_records(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 4)
        self.enter(item, 2026, 2, 5)
        self.enter(item, 2026, 3, 6)
        self.assertEqual(len(history_of(item, 2026, 3)), 2)
        self.assertEqual(len(history_of(item, 2026, 2)), 1)

    def test_a_refused_value_writes_no_record(self) -> None:
        item = self.item("CH-0012")
        numberless = self.item(None, "Neuverbindung 9")
        for target, year, quarter in ((numberless, 2026, 2),
                                      (item, 2027, 1)):
            with self.subTest(item=target.pk, year=year):
                with self.assertRaises(Exception):
                    enter_consumption(self.kl, target, year=year,
                                      quarter=quarter, count=3)
                self.assertEqual(history_of(target, year, quarter), [])

    def test_the_form_names_the_user_in_the_history(self) -> None:
        item = self.item("CH-0012")
        self.client.force_login(self.ae)
        url = form_url(item)
        for count in ("4", "5", ""):
            done = self.client.post(url, {"year": "2026", "quarter": "2",
                                          "count": count})
            self.assertEqual(done.status_code, 302)
        found = history_of(item, 2026, 2)
        self.assertEqual([r.history_type for r in found], ["+", "~", "-"])
        self.assertEqual({r.history_user_id for r in found}, {self.ae.pk})


class ItemPageHistoryTests(WidgetCase):

    NOTE = {"category": "", "status": "active", "stocked_on": "2019-01-02"}

    def change_note(self, item: Any, note: str) -> None:
        done = self.client.post(item_url(item, "edit"),
                                {**self.NOTE, "note": note})
        self.assertEqual(done.status_code, 302)

    def entries(self, item: Any) -> list[str]:
        return history_texts(self.item_page(item))

    def test_history_of_entered_consumption(self) -> None:
        """Scenario: History of entered consumption."""
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        self.change_note(item, "geändert")
        self.enter(item, 2026, 3, 40)
        self.enter(item, 2026, 3, None)
        shown = self.entries(item)
        self.assertEqual(len(shown), 5, shown)
        heading = HEADING.format(3, 2026)
        for position, (old, new) in ((0, ("40", "–")), (1, ("400", "40")),
                                     (3, ("–", "400"))):
            with self.subTest(entry=position):
                self.assertIn(heading, shown[position])
                self.assertTrue(changed(shown[position], old, new),
                                shown[position])
        self.assertNotIn("Verbrauch", shown[2])
        self.assertIn("geändert", shown[2])
        self.assertNotIn("Verbrauch", shown[4])
        self.assertIn("Angelegt", shown[4])
        for position in range(5):
            with self.subTest(user=position):
                self.assertIn("KL", shown[position])

    def test_each_entry_names_its_user(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        enter_consumption(self.ae, item, year=2026, quarter=3, count=40)
        enter_consumption(self.ae, item, year=2026, quarter=3, count=None)
        shown = self.entries(item)
        self.assertIn("AE", shown[0])
        self.assertNotIn("KL", shown[0])
        self.assertIn("AE", shown[1])
        self.assertNotIn("KL", shown[1])
        self.assertIn("KL", shown[2])
        self.assertNotIn("AE", shown[2])

    def test_a_removed_value_keeps_its_history(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 7)
        self.enter(item, 2026, 3, None)
        shown = self.entries(item)
        self.assertEqual(len(shown), 3, shown)
        self.assertTrue(changed(shown[0], "7", "–"), shown[0])
        self.assertTrue(changed(shown[1], "–", "7"), shown[1])

    def test_a_value_entered_again_after_a_removal_starts_from_none(
            self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        self.enter(item, 2026, 3, None)
        self.enter(item, 2026, 3, 7)
        shown = self.entries(item)
        self.assertEqual(len(shown), 4, shown)
        self.assertTrue(changed(shown[0], "–", "7"), shown[0])
        self.assertTrue(changed(shown[1], "400", "–"), shown[1])
        self.assertTrue(changed(shown[2], "–", "400"), shown[2])

    def test_a_quarter_changes_from_its_own_earlier_value(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        self.enter(item, 2026, 2, 3)
        self.enter(item, 2026, 3, 40)
        shown = self.entries(item)
        self.assertIn(HEADING.format(3, 2026), shown[0])
        self.assertTrue(changed(shown[0], "400", "40"), shown[0])
        self.assertIn(HEADING.format(2, 2026), shown[1])
        self.assertTrue(changed(shown[1], "–", "3"), shown[1])

    def test_another_items_consumption_stays_out(self) -> None:
        item = self.item("CH-0012")
        other = self.item("CH-0001")
        self.enter(other, 2026, 3, 400)
        self.assertEqual(len(self.entries(item)), 1)
        self.assertNotIn("Verbrauch", self.entries(item)[0])

    def test_entries_at_one_moment_list_the_consumption_first(self) -> None:
        item = self.item("CH-0012")
        with frozen(berlin(2026, 11, 4, 9)):
            self.enter(item, 2026, 3, 5)
            self.change_note(item, "neu")
        shown = self.entries(item)
        self.assertEqual(len(shown), 3, shown)
        self.assertIn(HEADING.format(3, 2026), shown[0])
        self.assertTrue(changed(shown[0], "–", "5"), shown[0])
        self.assertNotIn("Verbrauch", shown[1])
        self.assertIn("neu", shown[1])
        self.assertIn("Angelegt", shown[2])

    def test_entries_of_one_quarter_at_one_moment_keep_their_order(
            self) -> None:
        item = self.item("CH-0012")
        with frozen(berlin(2026, 11, 4, 9)):
            self.enter(item, 2026, 3, 5)
            self.enter(item, 2026, 3, 6)
        shown = self.entries(item)
        self.assertTrue(changed(shown[0], "5", "6"), shown[0])
        self.assertTrue(changed(shown[1], "–", "5"), shown[1])

    def test_a_visitor_sees_the_consumption_history(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        self.client.logout()
        shown = self.entries(item)
        self.assertIn(HEADING.format(3, 2026), shown[0])
        self.assertTrue(changed(shown[0], "–", "400"), shown[0])

    def test_the_english_heading(self) -> None:
        item = self.item("CH-0012")
        self.enter(item, 2026, 3, 400)
        accept(language="en")
        shown = self.entries(item)
        self.assertIn("Consumption Q3 2026", shown[0])
        self.assertTrue(changed(shown[0], "–", "400"), shown[0])


# ---------------------------------------------------------------------------
# 1.3 The links of the item page


class ItemPageLinkTests(WidgetCase):

    def rows(self, item: Any) -> dict[tuple[int, int], Element]:
        return quarter_rows(self.item_page(item))

    def test_changing_a_quarters_entered_value(self) -> None:
        """Scenario: Changing a quarter's entered value."""
        item = self.scenario_item()
        rows = self.rows(item)
        for quarter, text in (((2026, 3), CHANGE), ((2025, 2), CHANGE),
                              ((2026, 2), ENTER)):
            with self.subTest(quarter=quarter):
                link = link_of(rows[quarter])
                self.assertIsNotNone(link, "the row has no link")
                self.assertEqual(link.text(), text)
                self.assertEqual(link.get("href"),
                                 form_url(item, *quarter))
                self.assertIn("data-dialog", link.attrs)
        self.assertEqual(
            form_url(item, 2026, 3),
            f"/lab/inventory/items/{item.pk}/consumption/"
            "?year=2026&quarter=3")

    def test_a_quarter_with_a_historical_note_has_no_link(self) -> None:
        rows = self.rows(self.scenario_item())
        self.assertIsNone(link_of(rows[(2026, 1)]))

    def test_every_other_quarter_has_a_link(self) -> None:
        item = self.scenario_item()
        rows = self.rows(item)
        self.assertEqual(len(rows), 12)
        for quarter, row in rows.items():
            if quarter == (2026, 1):
                continue
            with self.subTest(quarter=quarter):
                link = link_of(row)
                self.assertIsNotNone(link)
                self.assertEqual(link.get("href"), form_url(item, *quarter))
                self.assertEqual(link.text(), CHANGE if quarter in (
                    (2026, 3), (2025, 2)) else ENTER)

    def test_a_reversed_historical_note_frees_its_quarter(self) -> None:
        item = self.item("CH-0012", quantity=5)
        note = book_note(self.kl, date=date(2026, 2, 10), historical=True,
                         lines=[historical_line(item, 2)])
        self.assertIsNone(link_of(self.rows(item)[(2026, 1)]))
        reverse_historical(self.kl, note, note="falsch")
        link = link_of(self.rows(item)[(2026, 1)])
        self.assertIsNotNone(link)
        self.assertEqual(link.text(), ENTER)
        self.assertEqual(link.get("href"), form_url(item, 2026, 1))

    def test_a_quarter_to_come_has_no_link(self) -> None:
        with frozen(berlin(2026, 5, 10)):
            item = self.item("CH-0012", quantity=5)
            self.enter(item, 2026, 2, 3)
            rows = self.rows(item)
        self.assertIn((2026, 2), rows)
        link = link_of(rows[(2026, 2)])
        self.assertIsNotNone(link, "the current quarter has no link")
        self.assertEqual(link.text(), CHANGE)
        for quarter, row in rows.items():
            if quarter > (2026, 2):
                with self.subTest(quarter=quarter):
                    self.assertIsNone(link_of(row))
        self.assertIsNotNone(link_of(rows[(2026, 1)]))

    def test_the_current_quarter_has_a_link(self) -> None:
        item = self.item("CH-0012")
        link = link_of(self.rows(item)[(2026, 4)])
        self.assertIsNotNone(link)
        self.assertEqual(link.text(), ENTER)
        self.assertEqual(link.get("href"), form_url(item, 2026, 4))

    def test_a_visitor_sees_no_links(self) -> None:
        item = self.scenario_item()
        self.client.logout()
        root = self.item_page(item)
        for quarter, row in quarter_rows(root).items():
            with self.subTest(quarter=quarter):
                self.assertIsNone(link_of(row))
        self.assertEqual([a.get("href") for a in root.find_all("a")
                          if "year=" in a.get("href", "")], [])
        self.assertEqual(figures_of(root)[(2026, 3)][0], 40)

    def test_an_item_without_an_article_number_has_no_links(self) -> None:
        item = self.item(None, "Neuverbindung 9")
        root = self.item_page(item)
        rows = quarter_rows(root)
        self.assertEqual(len(rows), 12)
        for quarter, row in rows.items():
            with self.subTest(quarter=quarter):
                self.assertIsNone(link_of(row))
        self.assertEqual([a.get("href") for a in root.find_all("a")
                          if "year=" in a.get("href", "")], [])

    def test_the_english_links(self) -> None:
        item = self.scenario_item()
        accept(language="en")
        rows = self.rows(item)
        for quarter, text in (((2026, 3), "Change"), ((2026, 2), "Enter")):
            with self.subTest(quarter=quarter):
                link = link_of(rows[quarter])
                self.assertIsNotNone(link, "the row has no link")
                self.assertEqual(link.text(), text)
        self.assertIsNone(link_of(rows[(2026, 1)]))


class DetailsKeepTheirTableTests(WidgetCase):

    def test_the_details_pane_has_no_quarter_links(self) -> None:
        """The compact table of the item list's details carries no
        links."""
        self.item("A-0")
        item = self.scenario_item()
        for source, root in (
                ("list", page(self.client.get(f"{LIST}?selected={item.pk}"))),
                ("detail", page(self.client.get(detail_url(item), **HTMX)))):
            with self.subTest(source=source):
                pane = pane_of(root)
                self.assertEqual(pane.get("data-item"), str(item.pk))
                grid = pane.find("table", cls="detail-table")
                self.assertIsNotNone(grid)
                self.assertEqual(grid.find_all("a"), [])
                self.assertEqual(
                    [a.get("href") for a in pane.find_all("a")
                     if "year=" in a.get("href", "")], [])
                self.assertEqual(
                    [a.text() for a in pane.find_all("a")
                     if a.text() in (CHANGE, ENTER)], [])
                self.assertIsNone(pane.find("svg"))


# ---------------------------------------------------------------------------
# 1.4 The form for a quarter


class QuarterFormCase(WidgetCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item("CH-0012", quantity=30)
        self.enter(self.target, 2026, 3, 400)
        self.enter(self.target, 2025, 2, 0)

    def modes(self) -> list[tuple[str, dict[str, str]]]:
        return [("page", {}), ("dialog", HTMX)]

    def get(self, query: str, header: dict[str, str]) -> Element:
        response = self.client.get(item_url(self.target, "consumption")
                                   + query, **header)
        self.assertEqual(response.status_code, 200)
        root = page(response)
        return root if "HTTP_HX_REQUEST" in header else root.find("main")

    def assert_fixed(self, scope: Element, label: str) -> None:
        names = controls_of(scope)
        self.assertIn("count", names)
        self.assertNotIn("year", names)
        self.assertNotIn("quarter", names)
        self.assertIn(label, outside_table(scope))


class QuarterFormTests(QuarterFormCase):

    def test_the_form_is_fixed_to_the_quarter(self) -> None:
        """Scenario: The form for a quarter."""
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                scope = self.get("?year=2026&quarter=3", header)
                self.assert_fixed(scope, "Q3 2026")
                self.assertEqual(field_value(scope, "count"), "400")
                self.assertTrue(
                    has_number(outside_table(scope), "400"),
                    outside_table(scope))

    def test_a_stored_zero_is_filled_in_and_named(self) -> None:
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                scope = self.get("?year=2025&quarter=2", header)
                self.assert_fixed(scope, "Q2 2025")
                self.assertEqual(field_value(scope, "count"), "0")
                none = self.get("?year=2025&quarter=3", header)
                self.assertNotEqual(
                    outside_table(scope).replace("Q2 2025", "Q3 2025"),
                    outside_table(none))

    def test_a_quarter_without_a_value_has_an_empty_count(self) -> None:
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                scope = self.get("?year=2025&quarter=3", header)
                self.assert_fixed(scope, "Q3 2025")
                self.assertEqual(field_value(scope, "count"), "")
                self.assertFalse(has_number(outside_table(scope), "400"))
                other = self.get("?year=2025&quarter=4", header)
                self.assertEqual(
                    outside_table(scope).replace("Q3 2025", "Q4 2025"),
                    outside_table(other))

    def test_the_fixed_form_posts_with_its_query(self) -> None:
        scope = self.get("?year=2026&quarter=3", HTMX)
        form = scope.find("form")
        for attribute in ("hx-post", "action"):
            with self.subTest(attribute=attribute):
                parts = urlsplit(form.get(attribute))
                self.assertEqual(parts.path,
                                 item_url(self.target, "consumption"))
                self.assertEqual(parse_qs(parts.query),
                                 {"year": ["2026"], "quarter": ["3"]})

    def test_the_current_quarter_is_fixed_too(self) -> None:
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                scope = self.get("?year=2026&quarter=4", header)
                self.assert_fixed(scope, "Q4 2026")
                self.assertEqual(field_value(scope, "count"), "")

    def test_other_values_open_the_editable_form(self) -> None:
        for mode, header in self.modes():
            bare = self.get("", header)
            for query in ("?year=2026&quarter=9", "?year=abc&quarter=3",
                          "?year=2027&quarter=1", "?year=2026&quarter=0",
                          "?year=0&quarter=1", "?year=2026&quarter=Q3",
                          "?year=2026", "?quarter=3", "?year=&quarter="):
                with self.subTest(mode=mode, query=query):
                    scope = self.get(query, header)
                    names = controls_of(scope)
                    self.assertLessEqual({"year", "quarter", "count"}, names)
                    self.assertEqual(field_value(scope, "count"), "")
                    self.assertEqual(field_value(scope, "year"),
                                     field_value(bare, "year"))
                    self.assertEqual(field_value(scope, "quarter"),
                                     field_value(bare, "quarter"))
                    self.assertEqual(outside_table(scope),
                                     outside_table(bare))
                    self.assertFalse(has_number(outside_table(scope), "400"))

    def test_an_invalid_count_shows_the_fixed_form_again(self) -> None:
        url = form_url(self.target, 2026, 3)
        data = {"year": "2026", "quarter": "3", "count": "x"}
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                response = self.client.post(url, data, **header)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                scope = root if header else root.find("main")
                self.assert_fixed(scope, "Q3 2026")
                self.assertTrue(errors_at(scope, "count"))
                self.assertTrue(
                    has_number(outside_table(scope), "400"),
                    outside_table(scope))
                self.assertEqual(
                    self.target.entered_consumption.get(
                        year=2026, quarter=3).count, 400)

    def test_the_url_names_the_quarter_saved(self) -> None:
        """A post to the fixed form saves the quarter its URL names,
        whatever year and quarter the post holds."""
        url = form_url(self.target, 2026, 3)
        before = {(c.year, c.quarter): c.count
                  for c in self.target.entered_consumption.all()}
        response = self.client.post(
            url, {"year": "2025", "quarter": "2", "count": "41"})
        self.assertEqual(response.status_code, 302)
        after = {(c.year, c.quarter): c.count
                 for c in self.target.entered_consumption.all()}
        self.assertEqual(after, {**before, (2026, 3): 41})

    def test_a_refusal_shows_in_the_fixed_form(self) -> None:
        """A quarter that a historical note holds refuses a value, and the
        fixed form says why."""
        book_note(self.kl, date=date(2026, 2, 10), historical=True,
                  lines=[historical_line(self.target, 2)])
        url = form_url(self.target, 2026, 1)
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                response = self.client.post(
                    url, {"year": "2026", "quarter": "1", "count": "3"},
                    **header)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                scope = root if header else root.find("main")
                self.assertTrue(scope.find_all("ul", cls="errorlist"))
                self.assertFalse(self.target.entered_consumption.filter(
                    year=2026, quarter=1).exists())

    def test_an_oversized_query_opens_the_editable_form(self) -> None:
        scope = self.get("?year=" + "9" * 5000 + "&quarter=3", {})
        self.assertIsNotNone(scope.find("select", name="quarter"))

    def test_a_valid_post_replaces_the_quarters_value(self) -> None:
        url = form_url(self.target, 2026, 3)
        data = {"year": "2026", "quarter": "3", "count": "41"}
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                response = self.client.post(url, data, **header)
                self.assertEqual(response.status_code,
                                 204 if header else 302)
                found = self.target.entered_consumption.filter(
                    year=2026, quarter=3)
                self.assertEqual([c.count for c in found],
                                 [int(data["count"])])
                data = {**data, "count": "42"}
        self.assertEqual(
            self.target.entered_consumption.get(year=2025,
                                                quarter=2).count, 0)

    def test_an_empty_count_removes_the_quarters_value(self) -> None:
        done = self.client.post(
            form_url(self.target, 2026, 3),
            {"year": "2026", "quarter": "3", "count": ""})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(self.target.entered_consumption.filter(
            year=2026, quarter=3).exists())

    def test_the_english_form(self) -> None:
        accept(language="en")
        scope = self.get("?year=2026&quarter=3", HTMX)
        self.assert_fixed(scope, "Q3 2026")
        self.assertTrue(has_number(outside_table(scope), "400"))


# ---------------------------------------------------------------------------
# 1.5 The consumption beside the form's fields


class SectionTests(QuarterFormCase):

    QUERIES = ("", "?year=2026&quarter=3")

    def setUp(self) -> None:
        super().setUp()
        self.deliver(self.target, 7, date(2026, 2, 10))
        self.deliver(self.target, 4, date(2026, 8, 20))
        self.enter(self.target, 2025, 1, 11)
        book_note(self.kl, date=date(2026, 3, 5), historical=True,
                  lines=[historical_line(self.target, 3)])

    def test_the_section_shows_the_item_pages_chart_and_table(self) -> None:
        shown = self.item_page(self.target)
        self.assertEqual(len(bars_of(shown)), 12)
        self.assertEqual(figures_of(shown)[(2026, 1)], [0, 10, 10])
        for mode, header in self.modes():
            for query in self.QUERIES:
                with self.subTest(mode=mode, query=query):
                    scope = self.get(query, header)
                    self.assertIsNotNone(scope.find("svg"))
                    self.assertEqual(bars_of(scope), bars_of(shown))
                    self.assertEqual(figures_of(scope), figures_of(shown))

    def test_the_links_lead_to_the_form_for_their_quarter(self) -> None:
        for mode, header in self.modes():
            for query in self.QUERIES:
                with self.subTest(mode=mode, query=query):
                    rows = quarter_rows(self.get(query, header))
                    self.assertEqual(len(rows), 12)
                    for quarter, row in rows.items():
                        link = link_of(row)
                        if quarter == (2026, 1):
                            self.assertIsNone(link)
                            continue
                        self.assertIsNotNone(link, quarter)
                        self.assertEqual(
                            link.get("href"),
                            form_url(self.target, *quarter))
                        self.assertEqual(
                            link.text(), CHANGE if quarter in (
                                (2026, 3), (2025, 2), (2025, 1))
                            else ENTER)

    def test_in_the_dialog_the_links_replace_the_dialogs_body(self) -> None:
        for query in self.QUERIES:
            with self.subTest(query=query):
                rows = quarter_rows(self.get(query, HTMX))
                for quarter, row in rows.items():
                    link = link_of(row)
                    if link is None:
                        continue
                    self.assertEqual(link.get("hx-get"), link.get("href"))
                    self.assertEqual(target_of(link), "#lab-dialog-body")

    def test_on_the_page_the_links_are_plain(self) -> None:
        for query in self.QUERIES:
            with self.subTest(query=query):
                scope = self.get(query, {})
                rows = quarter_rows(scope)
                self.assertTrue(any(link_of(r) for r in rows.values()))
                for row in rows.values():
                    link = link_of(row)
                    if link is not None:
                        self.assertNotIn("hx-get", link.attrs)
                for element in scope.walk():
                    if element.tag == "table":
                        for link in element.find_all("a"):
                            self.assertNotIn("hx-get", link.attrs)

    def test_the_chart_titles_have_ids_of_their_own(self) -> None:
        shown = self.item_page(self.target).find("svg")
        self.assertIsNotNone(shown)
        partial = self.get("?year=2026&quarter=3", HTMX).find("svg")
        again = self.get("", HTMX).find("svg")
        for svg in (partial, again):
            self.assertIsNotNone(svg, "no chart in the dialog's form")
        for svg in (shown, partial, again):
            label = svg.get("aria-labelledby")
            self.assertTrue(label)
            titled = [t for t in svg.find_all("title")
                      if t.get("id") == label]
            self.assertEqual(len(titled), 1, label)
        self.assertNotEqual(shown.get("aria-labelledby"),
                            partial.get("aria-labelledby"))
        self.assertNotEqual(shown.get("aria-labelledby"),
                            again.get("aria-labelledby"))

    def test_the_section_keeps_the_fields(self) -> None:
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                scope = self.get("?year=2026&quarter=3", header)
                self.assertIn("count", controls_of(scope))
                self.assertEqual(len(scope.find_all("form")), 1)

    def test_an_error_shows_the_section_again(self) -> None:
        url = form_url(self.target, 2026, 3)
        data = {"year": "2026", "quarter": "3", "count": "x"}
        shown = self.item_page(self.target)
        for mode, header in self.modes():
            with self.subTest(mode=mode):
                root = page(self.client.post(url, data, **header))
                scope = root if header else root.find("main")
                self.assertEqual(figures_of(scope), figures_of(shown))
                self.assertEqual(bars_of(scope), bars_of(shown))
