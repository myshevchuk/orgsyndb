"""Tests of the placement of popups and of the address of the item
list's details in ``lab.js`` under Node (end-product-inventory: Item
list). They skip, naming node, when it is absent.

The script runs with ``vm`` in a fresh context that defines neither
``document`` nor ``window``, so only its pure functions take part.
"""

import json
import shutil
import subprocess
from unittest import TestCase, skipUnless
from urllib.parse import parse_qs

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
const search = context.OrgSynLab.detailSearch;
process.stdout.write(JSON.stringify(
  typeof search === "function"
    ? cases.map(([text, id]) => search(text, id)) : null));
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
class DetailSearchTests(TestCase):
    """``OrgSynLab.detailSearch(search, id)`` takes SEARCH, the query
    string of an address as ``location.search`` holds it, with or
    without its leading ``?``, and ID, an item's id as a number or as
    text, or null; it returns the query string with the parameter
    ``detail`` set to ID, or removed when ID is null, every other
    parameter kept, as ``?`` and the parameters, or as ``""`` when none
    is left."""

    def search(self, *cases: tuple) -> list[str]:
        done = subprocess.run(
            [NODE, "-e", SEARCH_RUNNER, str(SCRIPT)],
            input=json.dumps(cases), capture_output=True, text=True,
            check=True)
        found = json.loads(done.stdout)
        self.assertIsNotNone(found, "OrgSynLab.detailSearch is not defined")
        return found

    def test_setting_detail(self) -> None:
        found = self.search(("", 5), ("?", 5), ("?category=Ester", 5),
                            ("category=Ester", "7"))
        self.assertEqual(found, ["?detail=5", "?detail=5",
                                 "?category=Ester&detail=5",
                                 "?category=Ester&detail=7"])

    def test_replacing_detail(self) -> None:
        found = self.search(("?detail=3", 5),
                            ("?q=zimt&detail=3&stock=low", 5),
                            ("detail=3&detail=4", 5))
        self.assertTrue(all(text.startswith("?") for text in found))
        self.assertEqual([parse_qs(text[1:]) for text in found], [
            {"detail": ["5"]},
            {"q": ["zimt"], "detail": ["5"], "stock": ["low"]},
            {"detail": ["5"]}])

    def test_removing_detail(self) -> None:
        found = self.search(("?detail=3", None), ("detail=3", None),
                            ("", None), ("?", None))
        self.assertEqual(found, ["", "", "", ""])

    def test_removing_detail_keeps_the_other_parameters(self) -> None:
        found = self.search(("?category=Ester&detail=3", None),
                            ("?detail=3&q=zimt&stock=low", None),
                            ("?q=zimt", None))
        self.assertTrue(all(text.startswith("?") for text in found))
        self.assertEqual([parse_qs(text[1:]) for text in found], [
            {"category": ["Ester"]},
            {"q": ["zimt"], "stock": ["low"]},
            {"q": ["zimt"]}])

    def test_values_stay_as_they_were_meant(self) -> None:
        found = self.search(
            ("?category=S%C3%A4uren&q=a%26b+c&detail=3", 9),
            ("?category=S%C3%A4uren&q=a%26b+c&detail=3", None))
        self.assertEqual([parse_qs(text[1:]) for text in found], [
            {"category": ["Säuren"], "q": ["a&b c"], "detail": ["9"]},
            {"category": ["Säuren"], "q": ["a&b c"]}])

    def test_repeated_parameters_are_kept(self) -> None:
        found = self.search(("?item=1&item=2&detail=3", 4),
                            ("?item=1&item=2&detail=3", None))
        self.assertEqual([parse_qs(text[1:]) for text in found], [
            {"item": ["1", "2"], "detail": ["4"]},
            {"item": ["1", "2"]}])
