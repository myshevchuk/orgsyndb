"""Tests for shared list helpers and django-cotton component integration."""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qsl, urlsplit

from django.template import engines
from django.template.loader import get_template
from django.test import SimpleTestCase

from orgsyndb_web import lists
from orgsyndb_web.lists import clean_choice, sort_rows

from . import parse


def _reset_loaders(engine) -> None:
    """Reset every loader cache, including django-cotton's cached dirs."""
    for loader in engine.template_loaders:
        loader.reset()
        for inner in getattr(loader, "loaders", ()):
            inner.reset()
            get_dirs = getattr(inner, "get_dirs", None)
            if hasattr(get_dirs, "cache_clear"):
                get_dirs.cache_clear()


class ListHelpersTests(SimpleTestCase):

    def test_clean_choice_accepts_allowed_and_falls_back(self) -> None:
        allowed = {"active", "ended", "all"}
        self.assertEqual(clean_choice("ended", allowed, "active"), "ended")
        self.assertEqual(clean_choice("unknown", allowed, "active"), "active")
        self.assertEqual(clean_choice("", allowed), "")

    def test_sort_rows_places_missing_values_last_and_is_stable(self) -> None:
        rows = [("a", 2), ("b", None), ("c", 1), ("d", 2), ("e", None)]
        self.assertEqual(
            sort_rows(rows, lambda r: r[1]),
            [("c", 1), ("a", 2), ("d", 2), ("b", None), ("e", None)],
        )
        self.assertEqual(
            sort_rows(rows, lambda r: r[1], descending=True),
            [("a", 2), ("d", 2), ("c", 1), ("b", None), ("e", None)],
        )


class CottonPartialCompatibilityTests(SimpleTestCase):
    """Verify django-cotton components work alongside Django 6.0 template
    partials through the configured template backend."""

    def test_partialdef_inside_split_layout_slot_resolves_by_name(
            self) -> None:
        engine = engines["django"].engine
        with TemporaryDirectory() as tmpdir:
            tpl_path = Path(tmpdir) / "probe_list.html"
            tpl_path.write_text(
                '<c-split-layout view="details" cookie="probe-cookie" '
                'split scroll_id="category-table-scroll">'
                '<table class="main-table"><tbody></tbody></table>'
                '<c-slot name="detail">'
                '{% partialdef detail inline %}'
                '<aside id="item-detail" data-item="{{ key }}">'
                '{{ label }}</aside>'
                '{% endpartialdef %}'
                '</c-slot>'
                '</c-split-layout>',
                encoding="utf-8",
            )
            orig_dirs = list(engine.dirs)
            engine.dirs = [tmpdir, *orig_dirs]
            _reset_loaders(engine)
            try:
                full_tpl = get_template("probe_list.html")
                full_root = parse(
                    full_tpl.render({"key": "k-1", "label": "Demo"}))
                layout = full_root.find("div", cls="item-layout")
                self.assertIsNotNone(layout)
                self.assertIn("item-layout--split", layout.classes)
                self.assertEqual(layout.get("data-view"), "details")
                self.assertEqual(layout.get("data-cookie"), "probe-cookie")
                scroll = full_root.find("div", id="category-table-scroll")
                self.assertIsNotNone(scroll)
                self.assertIn("table-scroll", scroll.classes)
                self.assertIn("table-sticky", scroll.classes)
                self.assertIsNotNone(full_root.find("aside", id="item-detail"))

                part_tpl = get_template("probe_list.html#detail")
                part_root = parse(
                    part_tpl.render({"key": "k-2", "label": "Only detail"}))
                self.assertIsNone(part_root.find("div", cls="item-layout"))
                aside = part_root.find("aside", id="item-detail")
                self.assertIsNotNone(aside)
                self.assertEqual(aside.get("data-item"), "k-2")
                self.assertEqual(aside.text(), "Only detail")
            finally:
                engine.dirs = orig_dirs
                _reset_loaders(engine)

    def test_migrated_list_partials_resolve_through_backend(self) -> None:
        for name in ("inventory/category_list.html#detail",
                     "inventory/bulk_list.html#detail",
                     "inventory/note_list.html#detail",
                     "inventory/item_list.html#detail"):
            with self.subTest(partial=name):
                rendered = get_template(name).render({})
                root = parse(rendered)
                self.assertIsNone(root.find("div", cls="item-layout"))
                self.assertIsNotNone(root.find("aside", id="item-detail"))


# ---------------------------------------------------------------------------
# The column model (web-app: Main lists, Sorting)
#
# The tests name the API of ``orgsyndb_web.lists`` this way:
#   SortColumn(key, label, value=None, sortable=True): a column; VALUE
#     gives the ordering key of a row, None for a row without one.
#   Order.from_query(query, columns, default_key, default_descending=False):
#     the order a query's ``sort`` and ``dir`` put a list in.
#   Order.key, .descending, .is_default
#   Order.link(key, filters=(), selected=""): the query a header links to.
#   Order.aria_sort(key): ``ascending``, ``descending`` or empty.
#   Order.pairs(): the ``sort`` and ``dir`` pairs of the canonical address.
#   Order.ordered(rows): ROWS, given in the default order, in this order.
#   sort_value(shown): the ordering key of a shown value, None for none.


def pairs_of(link: str) -> list[tuple[str, str]]:
    """The query pairs of LINK, in order, whether or not it has a path."""
    return parse_qsl(urlsplit(link).query, keep_blank_values=True)


def columns() -> list:
    """Three columns: ``name``, ``date`` and ``actions``, which does not
    sort."""
    return [
        lists.SortColumn("name", "Name", lambda row: row["name"].casefold()),
        lists.SortColumn("date", "Date", lambda row: row.get("date")),
        lists.SortColumn("actions", "Actions", sortable=False),
    ]


def order_of(query: dict[str, str], default: str = "name",
             descending: bool = False):
    return lists.Order.from_query(query, columns(), default, descending)


class OrderParsingTests(SimpleTestCase):
    """Sorting: ``sort`` names a column that sorts, ``dir=desc`` reverses,
    anything else is the default order."""

    def test_without_sort_the_list_is_in_its_default_order(self) -> None:
        order = order_of({}, "date", True)
        self.assertEqual((order.key, order.descending, order.is_default),
                         ("date", True, True))

    def test_sort_names_a_column_ascending(self) -> None:
        order = order_of({"sort": "date"})
        self.assertEqual((order.key, order.descending, order.is_default),
                         ("date", False, False))

    def test_dir_desc_puts_the_column_in_descending_order(self) -> None:
        order = order_of({"sort": "date", "dir": "desc"})
        self.assertEqual((order.key, order.descending, order.is_default),
                         ("date", True, False))

    def test_any_other_dir_is_ascending(self) -> None:
        for value in ("asc", "up", "", "DESC"):
            with self.subTest(dir=value):
                order = order_of({"sort": "date", "dir": value})
                self.assertFalse(order.descending)

    def test_an_unknown_key_is_the_default_order(self) -> None:
        for query in ({"sort": "nothing"}, {"sort": ""},
                      {"sort": "nothing", "dir": "desc"}):
            with self.subTest(query=query):
                order = order_of(query, "date", True)
                self.assertEqual(
                    (order.key, order.descending, order.is_default),
                    ("date", True, True))

    def test_a_column_that_does_not_sort_is_the_default_order(self) -> None:
        order = order_of({"sort": "actions"}, "name")
        self.assertEqual((order.key, order.descending, order.is_default),
                         ("name", False, True))

    def test_dir_alone_leaves_the_default_order(self) -> None:
        order = order_of({"dir": "desc"}, "name")
        self.assertEqual((order.key, order.descending, order.is_default),
                         ("name", False, True))

    def test_the_default_column_in_the_other_direction_is_not_default(
            self) -> None:
        self.assertFalse(order_of({"sort": "name", "dir": "desc"}).is_default)
        self.assertFalse(
            order_of({"sort": "date"}, "date", True).is_default)

    def test_the_default_column_in_the_default_direction_is_default(
            self) -> None:
        self.assertTrue(order_of({"sort": "name"}).is_default)
        self.assertTrue(
            order_of({"sort": "date", "dir": "desc"}, "date", True)
            .is_default)


class HeaderLinkTests(SimpleTestCase):
    """The header link of a column: descending when the column is in
    force ascending, ascending otherwise, keeping filters and the
    selected record."""

    def test_a_column_in_force_ascending_links_to_descending(self) -> None:
        link = order_of({"sort": "date"}).link("date")
        self.assertEqual(pairs_of(link), [("sort", "date"), ("dir", "desc")])

    def test_a_column_in_force_descending_links_to_ascending(self) -> None:
        link = order_of({"sort": "date", "dir": "desc"}).link("date")
        self.assertEqual(pairs_of(link), [("sort", "date")])

    def test_a_column_out_of_force_links_to_ascending(self) -> None:
        link = order_of({"sort": "date", "dir": "desc"}).link("name")
        self.assertEqual(pairs_of(link), [("sort", "name")])

    def test_the_default_order_is_in_force_without_sort(self) -> None:
        order = order_of({}, "date", True)
        self.assertEqual(pairs_of(order.link("date")), [("sort", "date")])
        self.assertEqual(pairs_of(order.link("name")), [("sort", "name")])
        ascending = order_of({}, "name")
        self.assertEqual(pairs_of(ascending.link("name")),
                         [("sort", "name"), ("dir", "desc")])

    def test_the_link_keeps_the_filters_and_the_selection(self) -> None:
        link = order_of({"sort": "date"}).link(
            "name", filters=[("q", "KL"), ("state", "all")], selected="7")
        self.assertEqual(pairs_of(link), [
            ("q", "KL"), ("state", "all"), ("sort", "name"),
            ("selected", "7")])

    def test_the_link_names_no_selection_when_there_is_none(self) -> None:
        link = order_of({}).link("date", filters=[("q", "a b")])
        self.assertEqual(pairs_of(link), [("q", "a b"), ("sort", "date")])
        self.assertNotIn("selected", link)

    def test_values_are_encoded(self) -> None:
        link = order_of({}).link("date", filters=[("q", "a&b=c")])
        self.assertEqual(pairs_of(link)[0], ("q", "a&b=c"))


class AriaSortTests(SimpleTestCase):

    def test_the_column_in_force_ascending(self) -> None:
        order = order_of({"sort": "date"})
        self.assertEqual(order.aria_sort("date"), "ascending")
        self.assertEqual(order.aria_sort("name"), "")
        self.assertEqual(order.aria_sort("actions"), "")

    def test_the_column_in_force_descending(self) -> None:
        order = order_of({"sort": "date", "dir": "desc"})
        self.assertEqual(order.aria_sort("date"), "descending")
        self.assertEqual(order.aria_sort("name"), "")

    def test_the_default_column_without_sort(self) -> None:
        self.assertEqual(order_of({}, "date", True).aria_sort("date"),
                         "descending")
        self.assertEqual(order_of({}).aria_sort("name"), "ascending")


class CanonicalPairsTests(SimpleTestCase):
    """The canonical address names the order unless it is the default."""

    def test_the_default_order_is_not_named(self) -> None:
        self.assertEqual(order_of({}).pairs(), [])
        self.assertEqual(order_of({"sort": "name"}).pairs(), [])
        self.assertEqual(order_of({"sort": "nothing"}).pairs(), [])
        self.assertEqual(
            order_of({"sort": "date", "dir": "desc"}, "date", True).pairs(),
            [])

    def test_another_column_is_named(self) -> None:
        self.assertEqual(order_of({"sort": "date"}).pairs(),
                         [("sort", "date")])

    def test_a_descending_order_names_dir(self) -> None:
        self.assertEqual(
            order_of({"sort": "date", "dir": "desc"}).pairs(),
            [("sort", "date"), ("dir", "desc")])

    def test_the_default_column_in_the_other_direction_is_named(
            self) -> None:
        self.assertEqual(order_of({"sort": "date"}, "date", True).pairs(),
                         [("sort", "date")])
        self.assertEqual(
            order_of({"sort": "name", "dir": "desc"}).pairs(),
            [("sort", "name"), ("dir", "desc")])


class OrderedRowsTests(SimpleTestCase):
    """Rows given in the default order are ordered by the column in
    force; equal values keep the default order and rows without a value
    come last in either direction."""

    ROWS = [{"name": "Delta", "date": date(2026, 3, 4)},
            {"name": "alpha", "date": date(2026, 1, 2)},
            {"name": "Charlie", "date": None},
            {"name": "bravo", "date": date(2026, 1, 2)},
            {"name": "echo", "date": None}]

    def names(self, query: dict[str, str], default: str = "date",
              descending: bool = True) -> list[str]:
        order = order_of(query, default, descending)
        return [row["name"] for row in order.ordered(self.ROWS)]

    def test_ascending_with_rows_without_a_value_last(self) -> None:
        self.assertEqual(self.names({"sort": "date"}),
                         ["alpha", "bravo", "Delta", "Charlie", "echo"])

    def test_descending_keeps_rows_without_a_value_last(self) -> None:
        self.assertEqual(
            self.names({"sort": "date", "dir": "desc"}),
            ["Delta", "alpha", "bravo", "Charlie", "echo"])

    def test_equal_values_keep_the_default_order_both_ways(self) -> None:
        for query in ({"sort": "date"}, {"sort": "date", "dir": "desc"}):
            with self.subTest(query=query):
                found = self.names(query)
                self.assertLess(found.index("alpha"), found.index("bravo"))
                self.assertLess(found.index("Charlie"), found.index("echo"))

    def test_text_in_the_values_of_its_column(self) -> None:
        self.assertEqual(
            self.names({"sort": "name"}),
            ["alpha", "bravo", "Charlie", "Delta", "echo"])
        self.assertEqual(
            self.names({"sort": "name", "dir": "desc"}),
            ["echo", "Delta", "Charlie", "bravo", "alpha"])

    def test_the_default_order_leaves_rows_given_in_it_alone(self) -> None:
        rows = sorted(self.ROWS, key=lambda row: row["name"].casefold())
        order = order_of({}, "name")
        self.assertEqual(order.ordered(rows), rows)


# ---------------------------------------------------------------------------
# Column values (web-app: Main lists, "A column orders its rows by the
# value its cells show")


def ordered(shown: list, descending: bool = False) -> list:
    """SHOWN, ordered ascending or DESCENDING by ``sort_value`` as a list
    does, values without a key last in their order."""
    return sort_rows(shown, lists.sort_value, descending=descending)


class SortValueTests(SimpleTestCase):

    def test_numbers_by_value(self) -> None:
        self.assertEqual(ordered(["10", "2", "-3,5", "2,25", "1.5"]),
                         ["-3,5", "1.5", "2", "2,25", "10"])

    def test_native_numbers_order_with_shown_ones(self) -> None:
        self.assertEqual(ordered([10, "2", 3.5, "-1"]),
                         ["-1", "2", 3.5, 10])

    def test_masses_by_their_value_in_mg(self) -> None:
        self.assertEqual(
            ordered(["1 g", "500 mg", "2 g", "250 mg", "1000 mg"]),
            ["250 mg", "500 mg", "1 g", "1000 mg", "2 g"])

    def test_amounts_of_substance_by_their_value_in_umol(self) -> None:
        self.assertEqual(
            ordered(["1 mmol", "20 µmol", "0,5 mmol", "2000 µmol"]),
            ["20 µmol", "0,5 mmol", "1 mmol", "2000 µmol"])

    def test_masses_come_before_amounts_of_substance(self) -> None:
        """Amounts across units: a gram of mass before a micromole, however
        the numbers compare."""
        self.assertEqual(
            ordered(["20 µmol", "1 g", "500 mg", "1 µmol", "5000 g"]),
            ["500 mg", "1 g", "5000 g", "1 µmol", "20 µmol"])

    def test_descending_reverses_the_whole_order(self) -> None:
        self.assertEqual(
            ordered(["20 µmol", "1 g", "500 mg"], descending=True),
            ["20 µmol", "1 g", "500 mg"])

    def test_dates_by_their_order(self) -> None:
        self.assertEqual(
            ordered(["2026-03-04", "01.01.2026", "2025-12-31",
                     "2026-01-02T09:15"]),
            ["2025-12-31", "01.01.2026", "2026-01-02T09:15", "2026-03-04"])

    def test_native_dates_order_with_shown_ones(self) -> None:
        self.assertEqual(
            ordered([date(2026, 3, 4), "2026-01-02", date(2026, 2, 1)]),
            ["2026-01-02", date(2026, 2, 1), date(2026, 3, 4)])

    def test_numbers_and_dates_come_before_text(self) -> None:
        self.assertEqual(
            ordered(["Abgabe", "2026-01-02", "7", "zeta"]),
            ["7", "2026-01-02", "Abgabe", "zeta"])

    def test_text_regardless_of_case(self) -> None:
        self.assertEqual(ordered(["beta", "Alpha", "gamma", "Delta"]),
                         ["Alpha", "beta", "Delta", "gamma"])

    def test_text_that_differs_in_case_only_is_equal(self) -> None:
        """Rows of equal value keep their order."""
        self.assertEqual(ordered(["b", "A", "B", "a"]),
                         ["A", "a", "b", "B"])

    def test_a_run_of_digits_orders_by_its_value(self) -> None:
        for low, high in (("#2", "#10"), ("AE-1/2", "AE-1/10"),
                          ("Fach 2", "Fach 10"), ("a9", "a10"),
                          ("KL0412", "KL0413")):
            with self.subTest(low=low, high=high):
                self.assertEqual(ordered([high, low]), [low, high])

    def test_digits_in_the_middle_of_text(self) -> None:
        self.assertEqual(
            ordered(["Box 10b", "Box 2c", "Box 2a", "box 1"]),
            ["box 1", "Box 2a", "Box 2c", "Box 10b"])

    def test_empty_and_dash_have_no_key(self) -> None:
        for shown in ("", "–", None):
            with self.subTest(shown=shown):
                self.assertIsNone(lists.sort_value(shown))

    def test_values_have_a_key(self) -> None:
        for shown in ("0", 0, "a", "2026-01-02", "1 g", date(2026, 1, 2)):
            with self.subTest(shown=shown):
                self.assertIsNotNone(lists.sort_value(shown))

    def test_empty_and_dash_come_last_in_either_direction(self) -> None:
        shown = ["b", "–", "a", "", "2"]
        self.assertEqual(ordered(shown), ["2", "a", "b", "–", ""])
        self.assertEqual(ordered(shown, descending=True),
                         ["b", "a", "2", "–", ""])

    def test_numbers_dates_and_text_in_both_directions(self) -> None:
        """The scenario of the browser's sorter, the same on the server."""
        keys = ["Abgabe", "10", "2026-01-02T09:15", "–", "-3,5",
                "01.01.2026", "", "2"]
        self.assertEqual(ordered(keys), [
            "-3,5", "2", "10", "01.01.2026", "2026-01-02T09:15", "Abgabe",
            "–", ""])
        self.assertEqual(ordered(keys, descending=True), [
            "Abgabe", "2026-01-02T09:15", "01.01.2026", "10", "2", "-3,5",
            "–", ""])

    def test_equal_values_keep_their_order(self) -> None:
        rows = [("b", 1), ("a", 2), ("b", 3), ("a", 4)]
        for descending in (False, True):
            with self.subTest(descending=descending):
                found = sort_rows(rows, lambda row: lists.sort_value(row[0]),
                                  descending=descending)
                firsts = [row for row in found if row[0] == "a"]
                self.assertEqual(firsts, [("a", 2), ("a", 4)])
                seconds = [row for row in found if row[0] == "b"]
                self.assertEqual(seconds, [("b", 1), ("b", 3)])
