"""Tests of the placement of popups in ``lab.js`` under Node
(end-product-inventory: Item list). They skip, naming node, when it is
absent.

The script runs with ``vm`` in a fresh context that defines neither
``document`` nor ``window``, so only its pure functions take part.
"""

import json
import shutil
import subprocess
from unittest import TestCase, skipUnless

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
