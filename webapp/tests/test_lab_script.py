"""Tests of the placement of popups and of the address of the item
list's selection in ``lab.js`` under Node (end-product-inventory: Item
list). They skip, naming node, when it is absent.

The script runs with ``vm`` in a fresh context that defines neither
``document`` nor ``window``, so only its pure functions take part.
"""

import json
import shutil
import subprocess
from unittest import TestCase, skipUnless
from urllib.parse import parse_qsl

from . import REPO

SCRIPT = REPO / "webapp" / "orgsyndb_web" / "static" / "lab.js"
NODE = shutil.which("node")
RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const place = context.OrgSynLab.place;
process.stdout.write(JSON.stringify(
  cases.map(([anchor, size, view]) => place(anchor, size, view))));
"""
SEARCH_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const search = context.OrgSynLab.paramSearch;
process.stdout.write(JSON.stringify(
  typeof search === "function"
    ? cases.map(([text, name, value]) => search(text, name, value))
    : null));
"""
NARROW_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const narrow = context.OrgSynLab.narrowBatches;
process.stdout.write(JSON.stringify(
  typeof narrow === "function"
    ? cases.map(([key, groups, chosen]) => narrow(key, groups, chosen))
    : null));
"""
GONE_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
process.stdout.write(JSON.stringify(
  Object.keys(context.OrgSynLab).sort()));
"""
SORT_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const order = context.OrgSynLab.sortOrder;
process.stdout.write(JSON.stringify(
  typeof order === "function"
    ? cases.map(([keys, descending, locale]) =>
        Array.from(order(keys, descending, locale)))
    : null));
"""
FILTER_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const shows = context.OrgSynLab.planFilterShows;
process.stdout.write(JSON.stringify(
  typeof shows === "function"
    ? cases.map(([row, filter]) => shows(row, filter))
    : null));
"""
STEP_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const step = context.OrgSynLab.planStep;
process.stdout.write(JSON.stringify(
  typeof step === "function"
    ? cases.map(([shown, current, key]) => step(shown, current, key))
    : null));
"""
SWEDISH_RUNNER = r"""
process.stdout.write(JSON.stringify(
  Intl.Collator.supportedLocalesOf(["sv"]).length > 0));
"""
SIZE = {"width": 300, "height": 200}


def anchor(left: int, top: int, width: int = 60,
           height: int = 24) -> dict[str, int]:
    return {"left": left, "top": top, "right": left + width,
            "bottom": top + height}


@skipUnless(NODE, "node is not installed")
class PlaceTests(TestCase):

    def place(self, *cases: tuple) -> list[dict[str, float]]:
        done = subprocess.run(
            [NODE, "-e", RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        return json.loads(done.stdout)

    def test_placing_a_popup(self) -> None:
        """Scenario: Placing a popup."""
        window = {"width": 1000, "height": 800}
        low = {"width": 1000, "height": 300}
        found = self.place((anchor(20, 20), SIZE, window),
                           (anchor(930, 760), SIZE, window),
                           (anchor(100, 150), SIZE, low))
        self.assertEqual(found[0], {"left": 20, "top": 52})
        self.assertEqual(found[1], {"left": 684, "top": 552})
        self.assertEqual(found[2], {"left": 100, "top": 84})

    def test_a_popup_taller_than_the_window(self) -> None:
        window = {"width": 1000, "height": 300}
        found = self.place((anchor(100, 150), SIZE | {"height": 400},
                            window))
        self.assertEqual(found[0], {"left": 100, "top": 16})

    def test_the_left_edge(self) -> None:
        window = {"width": 1000, "height": 800}
        found = self.place((anchor(4, 300), SIZE, window))
        self.assertEqual(found[0], {"left": 16, "top": 332})

    def test_a_popup_wider_than_the_window(self) -> None:
        window = {"width": 320, "height": 800}
        found = self.place((anchor(200, 100), SIZE | {"width": 400},
                            window))
        self.assertEqual(found[0], {"left": 16, "top": 132})


@skipUnless(NODE, "node is not installed")
class ParamSearchTests(TestCase):
    """``OrgSynLab.paramSearch(search, name, value)`` takes SEARCH, the
    query string of an address as ``location.search`` holds it, with or
    without its leading ``?``, NAME, a parameter's name, and VALUE, a
    number or text, or null; it returns the query string with the
    parameter NAME set to VALUE, or removed when VALUE is null, every
    other parameter kept in its order, as ``?`` and the parameters, or
    as ``""`` when none is left. Repeated occurrences of NAME become
    one, at the place of the first; a name is compared decoded, so an
    encoded spelling of NAME is the same parameter."""

    def search(self, *cases: tuple) -> list[str]:
        done = subprocess.run(
            [NODE, "-e", SEARCH_RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        found = json.loads(done.stdout)
        self.assertIsNotNone(found, "OrgSynLab.paramSearch is not defined")
        return found

    def pairs(self, *cases: tuple) -> list[list[tuple[str, str]]]:
        """The parameters of each answer, in order."""
        found = self.search(*cases)
        for text in found:
            self.assertTrue(text.startswith("?"), text)
        return [parse_qsl(text[1:], keep_blank_values=True)
                for text in found]

    def test_setting_a_parameter(self) -> None:
        found = self.search(("", "selected", 5), ("?", "selected", 5),
                            ("?category=Ester", "selected", 5),
                            ("category=Ester", "selected", "7"))
        self.assertEqual(found, ["?selected=5", "?selected=5",
                                 "?category=Ester&selected=5",
                                 "?category=Ester&selected=7"])

    def test_any_name_will_do(self) -> None:
        found = self.search(("?q=zimt", "stock", "low"),
                            ("?q=zimt&stock=low", "q", None),
                            ("?q=zimt&stock=low", "stock", None))
        self.assertEqual(found, ["?q=zimt&stock=low", "?stock=low",
                                 "?q=zimt"])

    def test_replacing_a_parameter(self) -> None:
        found = self.pairs(("?selected=3", "selected", 5),
                           ("?q=zimt&selected=3&stock=low", "selected", 5),
                           ("selected=3&selected=4", "selected", 5))
        self.assertEqual(found, [
            [("selected", "5")],
            [("q", "zimt"), ("selected", "5"), ("stock", "low")],
            [("selected", "5")]])

    def test_an_encoded_name_is_the_same_parameter(self) -> None:
        found = self.pairs(
            ("?selected=NV-1&%73elected=NV-2", "selected", "NV-3"),
            ("?q=zimt&sel%65cted=NV-2", "selected", "NV-3"))
        self.assertEqual(found, [[("selected", "NV-3")],
                                 [("q", "zimt"), ("selected", "NV-3")]])

    def test_removing_a_parameter(self) -> None:
        found = self.search(("?selected=3", "selected", None),
                            ("selected=3", "selected", None),
                            ("", "selected", None), ("?", "selected", None),
                            ("?selected=3&selected=4", "selected", None))
        self.assertEqual(found, ["", "", "", "", ""])

    def test_removing_a_parameter_keeps_the_others(self) -> None:
        found = self.pairs(("?category=Ester&selected=3", "selected", None),
                           ("?selected=3&q=zimt&stock=low", "selected",
                            None),
                           ("?q=zimt", "selected", None))
        self.assertEqual(found, [
            [("category", "Ester")],
            [("q", "zimt"), ("stock", "low")],
            [("q", "zimt")]])

    def test_the_others_keep_their_order(self) -> None:
        found = self.pairs(
            ("?sort=name&dir=desc&category=Ester", "selected", 5),
            ("?sort=name&selected=1&dir=desc&category=Ester", "selected",
             None))
        self.assertEqual(found, [
            [("sort", "name"), ("dir", "desc"), ("category", "Ester"),
             ("selected", "5")],
            [("sort", "name"), ("dir", "desc"), ("category", "Ester")]])

    def test_repeated_occurrences_become_one_at_the_first_place(
            self) -> None:
        found = self.pairs(
            ("?q=a&selected=1&stock=low&selected=2", "selected", 9),
            ("?selected=1&q=a&selected=2", "selected", 9))
        self.assertEqual(found, [
            [("q", "a"), ("selected", "9"), ("stock", "low")],
            [("selected", "9"), ("q", "a")]])

    def test_values_stay_as_they_were_meant(self) -> None:
        found = self.pairs(
            ("?category=S%C3%A4uren&q=a%26b+c&selected=3", "selected", 9),
            ("?category=S%C3%A4uren&q=a%26b+c&selected=3", "selected",
             None),
            ("?q=a", "category", "Säuren & Ester"))
        self.assertEqual(found, [
            [("category", "Säuren"), ("q", "a&b c"), ("selected", "9")],
            [("category", "Säuren"), ("q", "a&b c")],
            [("q", "a"), ("category", "Säuren & Ester")]])

    def test_repeated_other_parameters_are_kept(self) -> None:
        found = self.pairs(("?item=1&item=2&selected=3", "selected", 4),
                           ("?item=1&item=2&selected=3", "selected", None))
        self.assertEqual(found, [
            [("item", "1"), ("item", "2"), ("selected", "4")],
            [("item", "1"), ("item", "2")]])


@skipUnless(NODE, "node is not installed")
class NarrowBatchesTests(TestCase):
    """``OrgSynLab.narrowBatches(key, groups, chosen)`` takes KEY, the
    key of the substance chosen in a row or typed on the new-item form,
    the empty string for none, GROUPS, the keys of the batch choice's
    optgroups, and CHOSEN, the key of the group of the batch chosen, or
    null for none; it returns ``{hidden, clear}``: the keys of the
    groups to hide, and whether the batch chosen is to be cleared
    (end-product-inventory: Inventory forms, "Batches narrowed to the
    item")."""

    def narrow(self, *cases: tuple) -> list[dict]:
        done = subprocess.run(
            [NODE, "-e", NARROW_RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        found = json.loads(done.stdout)
        self.assertIsNotNone(found,
                             "OrgSynLab.narrowBatches is not defined")
        return found

    def test_the_groups_of_other_substances_are_hidden(self) -> None:
        """Scenario: Batches narrowed to the item."""
        found = self.narrow(
            ("cinnamic-acid", ["acetophenone", "cinnamic-acid"], None),
            ("cinnamic-acid", ["cinnamic-acid"], None),
            ("acetophenone", ["acetophenone", "cinnamic-acid", "no-article"],
             None))
        self.assertEqual(found, [
            {"hidden": ["acetophenone"], "clear": False},
            {"hidden": [], "clear": False},
            {"hidden": ["cinnamic-acid", "no-article"], "clear": False}])

    def test_a_batch_that_is_hidden_is_cleared(self) -> None:
        """Scenario: Batches narrowed to the item (nothing chosen)."""
        found = self.narrow(
            ("cinnamic-acid", ["acetophenone", "cinnamic-acid"],
             "acetophenone"),
            ("acetophenone", ["acetophenone", "cinnamic-acid"],
             "cinnamic-acid"))
        self.assertEqual(found, [
            {"hidden": ["acetophenone"], "clear": True},
            {"hidden": ["cinnamic-acid"], "clear": True}])

    def test_a_batch_that_stays_offered_is_kept(self) -> None:
        found = self.narrow(
            ("cinnamic-acid", ["acetophenone", "cinnamic-acid"],
             "cinnamic-acid"))
        self.assertEqual(found,
                         [{"hidden": ["acetophenone"], "clear": False}])

    def test_without_a_substance_nothing_is_hidden(self) -> None:
        found = self.narrow(
            ("", ["acetophenone", "cinnamic-acid"], None),
            ("", ["acetophenone", "cinnamic-acid"], "acetophenone"),
            ("", [], None))
        self.assertEqual(found, [{"hidden": [], "clear": False}] * 3)

    def test_a_substance_that_has_no_group_hides_them_all(self) -> None:
        found = self.narrow(
            ("typed-by-hand", ["acetophenone", "cinnamic-acid"], None),
            ("typed-by-hand", ["acetophenone", "cinnamic-acid"],
             "acetophenone"))
        self.assertEqual(found, [
            {"hidden": ["acetophenone", "cinnamic-acid"], "clear": False},
            {"hidden": ["acetophenone", "cinnamic-acid"], "clear": True}])

    def test_the_groups_keep_their_order(self) -> None:
        found = self.narrow(("b", ["d", "a", "b", "c"], None))
        self.assertEqual(found, [{"hidden": ["d", "a", "c"],
                                  "clear": False}])

    def test_no_groups_hide_nothing(self) -> None:
        found = self.narrow(("cinnamic-acid", [], None),
                            ("cinnamic-acid", [], "acetophenone"))
        self.assertEqual(found[0], {"hidden": [], "clear": False})
        self.assertEqual(found[1], {"hidden": [], "clear": True})


@skipUnless(NODE, "node is not installed")
class ExportTests(TestCase):

    def test_the_detail_search_is_gone(self) -> None:
        done = subprocess.run(
            [NODE, "-e", GONE_RUNNER, str(SCRIPT)],
            capture_output=True, text=True, check=True)
        exported = json.loads(done.stdout)
        self.assertIn("place", exported)
        self.assertIn("paramSearch", exported)
        self.assertNotIn("detailSearch", exported)

    def test_the_narrowing_is_exported(self) -> None:
        done = subprocess.run(
            [NODE, "-e", GONE_RUNNER, str(SCRIPT)],
            capture_output=True, text=True, check=True)
        self.assertIn("narrowBatches", json.loads(done.stdout))

    def test_the_planning_helpers_are_exported(self) -> None:
        done = subprocess.run(
            [NODE, "-e", GONE_RUNNER, str(SCRIPT)],
            capture_output=True, text=True, check=True)
        exported = json.loads(done.stdout)
        self.assertIn("planFilterShows", exported)
        self.assertIn("planStep", exported)


@skipUnless(NODE, "node is not installed")
class SortOrderTests(TestCase):
    """``OrgSynLab.sortOrder(keys, descending, locale)`` takes KEYS, the
    sort keys of a table's rows in their page order, as strings, whether
    to sort DESCENDING, and a LOCALE, a language tag; it returns the
    indices of the rows in their new order (web-app: Widgets)."""

    def order(self, keys: list[str], descending: bool = False,
              locale: str = "de") -> list[int]:
        return self.orders((keys, descending, locale))[0]

    def orders(self, *cases: tuple) -> list[list[int]]:
        done = subprocess.run(
            [NODE, "-e", SORT_RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        found = json.loads(done.stdout)
        self.assertIsNotNone(found, "lab.js exports no sortOrder")
        return found

    def sorted_keys(self, keys: list[str], descending: bool = False,
                    locale: str = "de") -> list[str]:
        return [keys[i] for i in self.order(keys, descending, locale)]

    def test_numbers_dates_and_text(self) -> None:
        """Scenario: Numbers, dates and text."""
        keys = ["Abgabe", "10", "2026-01-02T09:15", "–", "-3,5",
                "01.01.2026", "", "2"]
        ascending, descending = self.orders((keys, False, "de"),
                                            (keys, True, "de"))
        self.assertEqual([keys[i] for i in ascending], [
            "-3,5", "2", "10", "01.01.2026", "2026-01-02T09:15", "Abgabe",
            "–", ""])
        self.assertEqual([keys[i] for i in descending], [
            "Abgabe", "2026-01-02T09:15", "01.01.2026", "10", "2", "-3,5",
            "–", ""])
        self.assertEqual(ascending, [4, 7, 1, 5, 2, 0, 3, 6])
        self.assertEqual(descending, [0, 2, 5, 1, 7, 4, 3, 6])

    def test_equal_keys_keep_their_order(self) -> None:
        """Scenario: Equal keys keep their order."""
        self.assertEqual(self.order(["b", "a", "b", "a"]), [1, 3, 0, 2])

    def test_equal_keys_keep_their_order_descending_too(self) -> None:
        self.assertEqual(self.order(["b", "a", "b", "a"], True),
                         [0, 2, 1, 3])
        self.assertEqual(self.order(["2", "1", "2", "1"], True),
                         [0, 2, 1, 3])

    def test_a_decimal_comma_and_a_decimal_point_are_numbers(self) -> None:
        keys = ["1,5", "1.25", "-0,5", "-1.5", "0", "10,0", "9"]
        self.assertEqual(self.sorted_keys(keys), [
            "-1.5", "-0,5", "0", "1.25", "1,5", "9", "10,0"])

    def test_the_same_value_in_two_forms_is_equal(self) -> None:
        self.assertEqual(self.order(["1,5", "1.5", "1,50"]), [0, 1, 2])
        self.assertEqual(self.order(["1.5", "1,5", "1,50"]), [0, 1, 2])
        self.assertEqual(self.order(["1,5", "1.5"], True), [0, 1])

    def test_numbers_compare_by_value_not_by_text(self) -> None:
        self.assertEqual(self.sorted_keys(["9", "10", "100", "2"]),
                         ["2", "9", "10", "100"])
        self.assertEqual(self.sorted_keys(["9", "10", "100", "2"], True),
                         ["100", "10", "9", "2"])

    def test_a_sign_is_part_of_the_number(self) -> None:
        keys = ["+2", "-2", "1", "-10"]
        self.assertEqual(self.sorted_keys(keys), ["-10", "-2", "1", "+2"])

    def test_a_number_with_a_unit_is_text(self) -> None:
        """The text of a cell is its key only as a whole."""
        keys = ["10 mg", "Abgabe", "5", "2026-01-02"]
        self.assertEqual(self.sorted_keys(keys),
                         ["5", "2026-01-02", "10 mg", "Abgabe"])

    def test_a_lone_sign_is_text(self) -> None:
        keys = ["-", "5", "+"]
        self.assertEqual(self.sorted_keys(keys)[0], "5")

    def test_dates_in_both_forms_by_their_order(self) -> None:
        keys = ["31.12.2025", "2026-01-01", "15.02.2025", "2025-03-09"]
        self.assertEqual(self.sorted_keys(keys), [
            "15.02.2025", "2025-03-09", "31.12.2025", "2026-01-01"])
        self.assertEqual(self.sorted_keys(keys, True), [
            "2026-01-01", "31.12.2025", "2025-03-09", "15.02.2025"])

    def test_a_german_date_is_not_read_as_text(self) -> None:
        """Read as text, ``31.12.2025`` would follow ``01.01.2026``."""
        self.assertEqual(self.order(["01.01.2026", "31.12.2025"]), [1, 0])

    def test_dates_with_times(self) -> None:
        keys = ["2026-01-02T10:05", "02.01.2026 09:15",
                "2026-01-02T09:15", "03.01.2026 00:00", "2026-01-02"]
        self.assertEqual(self.sorted_keys(keys), [
            "2026-01-02", "02.01.2026 09:15", "2026-01-02T09:15",
            "2026-01-02T10:05", "03.01.2026 00:00"])

    def test_a_date_without_a_time_precedes_that_days_times(self) -> None:
        self.assertEqual(self.order(["2026-01-02T00:01", "2026-01-02"]),
                         [1, 0])
        self.assertEqual(self.order(["02.01.2026 00:01", "02.01.2026"]),
                         [1, 0])

    def test_one_moment_in_two_forms_is_equal(self) -> None:
        self.assertEqual(self.order(
            ["2026-01-02T09:15", "02.01.2026 09:15"]), [0, 1])
        self.assertEqual(self.order(
            ["02.01.2026 09:15", "2026-01-02T09:15"]), [0, 1])
        self.assertEqual(self.order(
            ["02.01.2026 09:15", "2026-01-02T09:15"], True), [0, 1])
        self.assertEqual(self.order(["2026-01-02", "02.01.2026"]), [0, 1])

    def test_a_year_alone_is_a_number_and_precedes_dates(self) -> None:
        self.assertEqual(self.order(["2025-01-01", "2026"]), [1, 0])

    def test_the_groups_numbers_dates_text(self) -> None:
        keys = ["Zebra", "2026-05-05", "7", "apfel", "01.01.2000", "-1"]
        self.assertEqual(self.sorted_keys(keys), [
            "-1", "7", "01.01.2000", "2026-05-05", "apfel", "Zebra"])

    def test_descending_reverses_the_groups(self) -> None:
        keys = ["Zebra", "2026-05-05", "7", "apfel", "01.01.2000", "-1"]
        self.assertEqual(self.sorted_keys(keys, True), [
            "Zebra", "apfel", "2026-05-05", "01.01.2000", "7", "-1"])

    def test_a_dash_and_an_empty_key_come_last_either_way(self) -> None:
        keys = ["–", "b", "", "a", "–", "3"]
        ascending, descending = self.orders((keys, False, "de"),
                                            (keys, True, "de"))
        self.assertEqual([keys[i] for i in ascending],
                         ["3", "a", "b", "–", "", "–"])
        self.assertEqual([keys[i] for i in descending],
                         ["b", "a", "3", "–", "", "–"])

    def test_a_dash_and_an_empty_key_keep_their_order_among_themselves(
            self) -> None:
        for descending in (False, True):
            with self.subTest(descending=descending):
                self.assertEqual(
                    self.order(["", "–", "", "–"], descending),
                    [0, 1, 2, 3])
                self.assertEqual(
                    self.order(["–", "", "–"], descending), [0, 1, 2])

    def test_nothing_but_dashes_and_empty_keys(self) -> None:
        self.assertEqual(self.order(["–", ""]), [0, 1])
        self.assertEqual(self.order(["", "–"], True), [0, 1])

    def test_no_rows_and_one_row(self) -> None:
        self.assertEqual(self.order([]), [])
        self.assertEqual(self.order([], True), [])
        self.assertEqual(self.order(["x"]), [0])
        self.assertEqual(self.order(["–"], True), [0])

    def test_the_result_is_a_permutation_of_the_indices(self) -> None:
        keys = ["b", "3", "", "01.01.2026", "–", "a", "3", "b"]
        for descending in (False, True):
            with self.subTest(descending=descending):
                self.assertEqual(sorted(self.order(keys, descending)),
                                 list(range(len(keys))))

    def test_a_long_run_of_equal_keys_keeps_its_order(self) -> None:
        keys = ["a", "b"] * 30
        self.assertEqual(self.order(keys),
                         list(range(0, 60, 2)) + list(range(1, 60, 2)))
        self.assertEqual(self.order(keys, True),
                         list(range(1, 60, 2)) + list(range(0, 60, 2)))

    def test_text_follows_the_collation_of_the_language(self) -> None:
        keys = ["Zebra", "Äpfel", "apfel", "Birne"]
        self.assertEqual(self.sorted_keys(keys, locale="de"),
                         ["apfel", "Äpfel", "Birne", "Zebra"])
        self.assertEqual(self.sorted_keys(keys, True, locale="de"),
                         ["Zebra", "Birne", "Äpfel", "apfel"])

    def test_text_is_not_ordered_by_code_unit(self) -> None:
        """Code-unit order puts every capital before every small
        letter."""
        self.assertEqual(self.sorted_keys(["b", "A", "a", "B"]),
                         ["a", "A", "b", "B"])

    def test_the_language_changes_the_order(self) -> None:
        done = subprocess.run([NODE, "-e", SWEDISH_RUNNER],
                              capture_output=True, text=True, check=True)
        if not json.loads(done.stdout):
            self.skipTest("node has no Swedish collation")
        keys = ["Zebra", "Äpfel", "Apfel"]
        self.assertEqual(self.sorted_keys(keys, locale="de"),
                         ["Apfel", "Äpfel", "Zebra"])
        self.assertEqual(self.sorted_keys(keys, locale="sv"),
                         ["Apfel", "Zebra", "Äpfel"])

    def test_a_language_node_lacks_falls_back(self) -> None:
        keys = ["b", "a", "3"]
        self.assertEqual(self.sorted_keys(keys, locale="tlh"),
                         ["3", "a", "b"])


@skipUnless(NODE, "node is not installed")
class PlanFilterTests(TestCase):
    """``OrgSynLab.planFilterShows(row, filter)`` tells whether the
    planning list's filter FILTER, one of ``"all"``, ``"high"``,
    ``"action"`` and ``"late"``, shows ROW, an object with ``priority``,
    a string (``"high"``, ``"medium"`` or ``"low"``), and the booleans
    ``action`` and ``late``; it returns a boolean (production-planning:
    Planning list)."""

    ROWS = [{"priority": priority, "action": action, "late": late}
            for priority in ("high", "medium", "low")
            for action in (False, True) for late in (False, True)]

    def shows(self, *cases: tuple) -> list[bool]:
        done = subprocess.run(
            [NODE, "-e", FILTER_RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        found = json.loads(done.stdout)
        self.assertIsNotNone(found, "lab.js exports no planFilterShows")
        return found

    def test_all_shows_every_row(self) -> None:
        found = self.shows(*[(row, "all") for row in self.ROWS])
        self.assertEqual(len(found), len(self.ROWS))
        for row, shown in zip(self.ROWS, found):
            with self.subTest(row=row):
                self.assertIs(shown, True)

    def test_high_shows_the_rows_of_high_priority(self) -> None:
        found = self.shows(*[(row, "high") for row in self.ROWS])
        for row, shown in zip(self.ROWS, found):
            with self.subTest(row=row):
                self.assertIs(shown, row["priority"] == "high")

    def test_action_shows_the_rows_with_an_action(self) -> None:
        found = self.shows(*[(row, "action") for row in self.ROWS])
        for row, shown in zip(self.ROWS, found):
            with self.subTest(row=row):
                self.assertIs(shown, row["action"])

    def test_late_shows_the_rows_with_a_late_task(self) -> None:
        found = self.shows(*[(row, "late") for row in self.ROWS])
        for row, shown in zip(self.ROWS, found):
            with self.subTest(row=row):
                self.assertIs(shown, row["late"])

    def test_a_filter_looks_at_its_own_attribute_only(self) -> None:
        quiet = {"priority": "low", "action": False, "late": False}
        found = self.shows(
            ({**quiet, "late": True}, "action"),
            ({**quiet, "action": True}, "late"),
            ({**quiet, "action": True, "late": True}, "high"),
            ({**quiet, "priority": "medium"}, "high"))
        self.assertEqual(found, [False, False, False, False])


@skipUnless(NODE, "node is not installed")
class PlanStepTests(TestCase):
    """``OrgSynLab.planStep(shown, current, key)`` takes SHOWN, a list of
    booleans, one for each row of the planning list in its current order,
    whether the row shows; CURRENT, the index of the selected row, or -1
    for none; and KEY, ``"ArrowUp"`` or ``"ArrowDown"``. It returns the
    index of the nearest row that shows before (up) or after (down)
    CURRENT, and CURRENT when there is none (production-planning:
    Planning list)."""

    def step(self, shown: list[bool], current: int, key: str) -> int:
        return self.steps((shown, current, key))[0]

    def steps(self, *cases: tuple) -> list[int]:
        done = subprocess.run(
            [NODE, "-e", STEP_RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        found = json.loads(done.stdout)
        self.assertIsNotNone(found, "lab.js exports no planStep")
        return found

    def test_down_moves_to_the_next_row(self) -> None:
        self.assertEqual(self.step([True] * 4, 1, "ArrowDown"), 2)

    def test_up_moves_to_the_previous_row(self) -> None:
        self.assertEqual(self.step([True] * 4, 2, "ArrowUp"), 1)

    def test_the_last_row_stays_on_down(self) -> None:
        self.assertEqual(self.step([True] * 3, 2, "ArrowDown"), 2)

    def test_the_first_row_stays_on_up(self) -> None:
        self.assertEqual(self.step([True] * 3, 0, "ArrowUp"), 0)

    def test_rows_that_do_not_show_are_skipped(self) -> None:
        shown = [True, False, False, True, True]
        self.assertEqual(self.steps(
            (shown, 0, "ArrowDown"), (shown, 3, "ArrowUp"),
            (shown, 3, "ArrowDown"), (shown, 4, "ArrowUp")),
            [3, 0, 4, 3])

    def test_no_further_row_that_shows_stays_put(self) -> None:
        shown = [True, True, False, False]
        self.assertEqual(self.step(shown, 1, "ArrowDown"), 1)
        shown = [False, False, True, True]
        self.assertEqual(self.step(shown, 2, "ArrowUp"), 2)

    def test_a_selected_row_that_does_not_show_moves_by_position(
            self) -> None:
        shown = [True, False, True]
        self.assertEqual(self.steps((shown, 1, "ArrowDown"),
                                    (shown, 1, "ArrowUp")), [2, 0])

    def test_without_a_selection_down_gives_the_first_row_that_shows(
            self) -> None:
        self.assertEqual(self.steps(
            ([True, True], -1, "ArrowDown"),
            ([False, False, True, True], -1, "ArrowDown")), [0, 2])

    def test_without_a_selection_up_stays_without_one(self) -> None:
        self.assertEqual(self.step([True, True], -1, "ArrowUp"), -1)

    def test_nothing_shows(self) -> None:
        self.assertEqual(self.steps(
            ([False, False], 0, "ArrowDown"), ([False, False], 1, "ArrowUp"),
            ([False, False], -1, "ArrowDown"), ([], -1, "ArrowDown")),
            [0, 1, -1, -1])

    def test_one_row(self) -> None:
        self.assertEqual(self.steps(([True], 0, "ArrowDown"),
                                    ([True], 0, "ArrowUp")), [0, 0])


LIVE_LIST_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");

const listeners = [];
class FakeElement {
  constructor(tag, attrs = {}, parent = null) {
    this.tagName = tag.toUpperCase();
    this.attrs = { ...attrs };
    this.id = attrs.id || "";
    this.parent = parent;
    this.hidden = false;
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  hasAttribute(name) { return name in this.attrs; }
  setAttribute(name, val) { this.attrs[name] = String(val); }
  matches(selector) {
    if (selector === "form.lab-filters[hx-get]") {
      return this.tagName === "FORM"
        && (this.attrs.class || "").split(/\s+/).includes("lab-filters")
        && "hx-get" in this.attrs;
    }
    if (selector === "a[href][hx-get]") {
      return this.tagName === "A" && "href" in this.attrs
        && "hx-get" in this.attrs;
    }
    if (selector === "#filter-q") return this.id === "filter-q";
    if (selector === "tr[data-item][hx-get]") {
      return this.tagName === "TR" && "data-item" in this.attrs
        && "hx-get" in this.attrs;
    }
    return false;
  }
  closest(selector) {
    for (let el = this; el; el = el.parent) {
      if (el.matches(selector)) return el;
    }
    return null;
  }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  addEventListener() {}
}

const form = new FakeElement("form", {
  id: "filters", class: "lab-filters", "hx-get": "/lab/inventory/",
  "hx-sync": "#main:replace",
});
const search = new FakeElement("input", {
  id: "filter-q", name: "q", type: "search",
}, form);
search.name = "q";
search.type = "search";
search.value = "";
const category = new FakeElement("select", { name: "category" }, form);
category.name = "category";
category.type = "select-one";
category.value = "";
form.elements = [search, category];

const tbody = new FakeElement("tbody", {
  id: "item-rows", "hx-sync": "#main:replace",
});
const row = new FakeElement("tr", {
  "data-item": "42", "hx-get": "/lab/inventory/items/42/detail/",
}, tbody);
const link = new FakeElement("a", {
  href: "/lab/inventory/?sort=name", "hx-get": "/lab/inventory/?sort=name",
  "hx-sync": "#main:replace",
});
const spanInLink = new FakeElement("span", {}, link);
const plainLink = new FakeElement("a", { href: "/lab/inventory/items/1/" });

const doc = {
  documentElement: { dataset: {}, lang: "de", classList: { toggle() {}, add() {}, remove() {} } },
  body: { dataset: {} },
  addEventListener(type, fn, capture = false) {
    listeners.push({ type, fn, capture: Boolean(capture) });
  },
  querySelectorAll() { return []; },
  querySelector(sel) {
    if (sel === "form.lab-filters[hx-get]") return form;
    return null;
  },
  getElementById(id) {
    if (id === "filters") return form;
    if (id === "filter-q") return search;
    return null;
  },
  cookie: "",
};

const win = {
  document: doc,
  Element: FakeElement,
  HTMLElement: FakeElement,
  addEventListener() {},
  matchMedia() { return { matches: false }; },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  location: { pathname: "/lab/inventory/", search: "", hash: "", href: "http://testserver/lab/inventory/" },
  history: { replaceState() {} },
  navigator: {},
};

const context = vm.createContext({
  window: win, document: doc, Element: FakeElement, HTMLElement: FakeElement,
  localStorage: win.localStorage, location: win.location, history: win.history,
  URL, URLSearchParams, Set, Map, CustomEvent: class {},
});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });

function fire(type, event, captureOnly = false) {
  let prevented = false;
  let stopped = false;
  const ev = {
    type,
    preventDefault() { prevented = true; },
    stopPropagation() { stopped = true; },
    stopImmediatePropagation() { stopped = true; },
    ...event,
  };
  for (const item of listeners) {
    if (item.type !== type) continue;
    if (captureOnly && !item.capture) continue;
    item.fn(ev);
  }
  return { prevented, stopped };
}

// 1. Stale delayed search timer cancelled after a newer sort click
fire("input", { target: search });
const sortConfirm = fire("htmx:confirm", {
  target: link,
  detail: { elt: link, triggeringEvent: { type: "click" } },
});
const staleSearch = fire("htmx:confirm", {
  target: form,
  detail: { elt: form, triggeringEvent: { type: "input" } },
});
// 2. Fresh input after the sort click is NOT cancelled, and survives an
// older sort response morphing #filters before the debounce expires
search.value = "abc";
fire("input", { target: search });
fire("htmx:oobBeforeSwap", { target: form, detail: { target: form } });
search.value = "";
fire("htmx:oobAfterSwap", { target: form, detail: { target: form } });
const preservedSearch = search.value;
const freshSearch = fire("htmx:confirm", {
  target: form,
  detail: { elt: form, triggeringEvent: { type: "input" } },
});
fire("htmx:afterSettle", { target: tbody, detail: { target: tbody } });
// 3. Reset click clears #filter-q when no newer input arrived after Reset
fire("htmx:confirm", {
  target: link,
  detail: { elt: link, triggeringEvent: { type: "click" } },
});
fire("htmx:oobBeforeSwap", { target: form, detail: { target: form } });
search.value = "";
fire("htmx:oobAfterSwap", { target: form, detail: { target: form } });
const resetSearch = search.value;
fire("htmx:afterSettle", { target: tbody, detail: { target: tbody } });
// 4. Row selection cancelling an in-flight filter restores applied controls
category.value = "Ester";
fire("htmx:confirm", {
  target: form,
  detail: { elt: form, triggeringEvent: { type: "change" } },
});
fire("htmx:beforeRequest", { target: form, detail: { elt: form } });
fire("htmx:confirm", {
  target: row,
  detail: { elt: row, triggeringEvent: { type: "item-select" } },
});
const restoredCategory = category.value;
// 5. Modified and non-primary clicks on a[href][hx-get] stop propagation
const clicks = {
  ctrl: fire("click", { target: spanInLink, ctrlKey: true, button: 0 }, true),
  meta: fire("click", { target: link, metaKey: true, button: 0 }, true),
  shift: fire("click", { target: link, shiftKey: true, button: 0 }, true),
  alt: fire("click", { target: link, altKey: true, button: 0 }, true),
  middle: fire("click", { target: link, button: 1 }, true),
  plainLeft: fire("click", { target: link, button: 0 }, true),
  nonHtmxCtrl: fire("click", { target: plainLink, ctrlKey: true, button: 0 }, true),
};

process.stdout.write(JSON.stringify({
  sortPrevented: sortConfirm.prevented,
  staleSearchPrevented: staleSearch.prevented,
  preservedSearch,
  freshSearchPrevented: freshSearch.prevented,
  resetSearch,
  restoredCategory,
  clicks,
}));
"""


@skipUnless(NODE, "node is not installed")
class LiveListScriptTests(TestCase):
    """Live-list event guards in ``lab.js`` (web-app: Live lists)."""

    def test_stale_search_cancellation_and_modified_clicks(self) -> None:
        done = subprocess.run(
            [NODE, "-e", LIVE_LIST_RUNNER, str(SCRIPT)],
            capture_output=True, text=True, check=True)
        result = json.loads(done.stdout)
        self.assertFalse(result["sortPrevented"])
        self.assertTrue(result["staleSearchPrevented"])
        self.assertEqual(result["preservedSearch"], "abc")
        self.assertFalse(result["freshSearchPrevented"])
        self.assertEqual(result["resetSearch"], "")
        self.assertEqual(result["restoredCategory"], "")
        for key in ("ctrl", "meta", "shift", "alt", "middle"):
            with self.subTest(click=key):
                self.assertTrue(result["clicks"][key]["stopped"])
                self.assertFalse(result["clicks"][key]["prevented"])
        self.assertFalse(result["clicks"]["plainLeft"]["stopped"])
        self.assertFalse(result["clicks"]["nonHtmxCtrl"]["stopped"])

    def test_no_data_submit_auto_submit_handler(self) -> None:
        runner = r"""
const fs = require("fs");
const vm = require("vm");

const listeners = [];
class FakeElement {
  constructor(tag, attrs = {}, parent = null) {
    this.tagName = tag.toUpperCase();
    this.attrs = { ...attrs };
    this.id = attrs.id || "";
    this.parent = parent;
    this.hidden = false;
  }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  hasAttribute(name) { return name in this.attrs; }
  setAttribute(name, val) { this.attrs[name] = String(val); }
  matches(selector) {
    if (selector === "[data-submit]") return "data-submit" in this.attrs;
    return false;
  }
  closest() { return null; }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  addEventListener() {}
}

let submitCalls = 0;
const submitBtn = new FakeElement("button", { type: "submit" });
const plainForm = new FakeElement("form", {
  method: "get", action: "/lab/other/",
});
plainForm.requestSubmit = () => { submitCalls += 1; };
plainForm.querySelectorAll = (sel) => (
  sel === "button[type=submit]" ? [submitBtn] : []
);
const control = new FakeElement("select", { "data-submit": "" }, plainForm);
control.form = plainForm;

const doc = {
  documentElement: {
    clientWidth: 1000, dataset: {}, lang: "de",
    classList: { toggle() {}, add() {}, remove() {} },
  },
  body: { dataset: {} },
  addEventListener(type, fn, capture = false) {
    listeners.push({ type, fn, capture: Boolean(capture) });
  },
  querySelectorAll(sel) {
    if (sel === "[data-submit]") return [control];
    return [];
  },
  querySelector() { return null; },
  getElementById() { return null; },
  cookie: "",
};

const win = {
  document: doc,
  Element: FakeElement,
  HTMLElement: FakeElement,
  addEventListener() {},
  matchMedia() { return { matches: false }; },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  location: {
    pathname: "/lab/other/",
    search: "",
    hash: "",
    href: "http://testserver/lab/other/",
  },
  history: { replaceState() {} },
  navigator: {},
  innerHeight: 800,
};

const context = vm.createContext({
  window: win, document: doc, Element: FakeElement, HTMLElement: FakeElement,
  localStorage: win.localStorage, location: win.location, history: win.history,
  URL, URLSearchParams, Set, Map, CustomEvent: class {},
});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });

const ev = {
  type: "change",
  target: control,
  bubbles: true,
  preventDefault() {},
  stopPropagation() {},
  stopImmediatePropagation() {},
};
for (const item of listeners) {
  if (item.type === "change") item.fn(ev);
}

process.stdout.write(JSON.stringify({
  submitHidden: submitBtn.hidden,
  submitCalls,
}));
"""
        done = subprocess.run(
            [NODE, "-e", runner, str(SCRIPT)],
            capture_output=True, text=True, check=True)
        result = json.loads(done.stdout)
        self.assertEqual(result, {"submitHidden": False, "submitCalls": 0})
