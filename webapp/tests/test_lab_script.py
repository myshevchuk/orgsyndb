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
GONE_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context,
                { filename: process.argv[1] });
process.stdout.write(JSON.stringify(
  Object.keys(context.OrgSynLab).sort()));
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
    one, at the place of the first."""

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
class ExportTests(TestCase):

    def test_the_detail_search_is_gone(self) -> None:
        done = subprocess.run(
            [NODE, "-e", GONE_RUNNER, str(SCRIPT)],
            capture_output=True, text=True, check=True)
        exported = json.loads(done.stdout)
        self.assertIn("place", exported)
        self.assertIn("paramSearch", exported)
        self.assertNotIn("detailSearch", exported)
