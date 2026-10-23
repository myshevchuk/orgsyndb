"""Unit tests of site/assets/js/search-terms.js under Node (site-search
"Query normalisation"). They skip, naming node, when it is absent."""

import json
import subprocess
import unittest
from typing import Any

import pipeline_support as ps
from pipeline_support import SEARCH_TERMS

RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"),
                    { filename: process.argv[1] });
const calls = JSON.parse(fs.readFileSync(0, "utf8"));
const out = calls.map(([name, arg]) => globalThis.OrgSynSearch[name](arg));
process.stdout.write(JSON.stringify(out));
"""


def call_search_terms(calls: list[tuple[str, Any]]) -> list[Any]:
    """Load search-terms.js as a classic script and make each call."""
    node = ps.require_node()
    if not SEARCH_TERMS.is_file():
        raise AssertionError(
            "site/assets/js/search-terms.js does not exist")
    done = subprocess.run(
        [node, "-e", RUNNER, str(SEARCH_TERMS)], input=json.dumps(calls),
        capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"node failed: {done.stderr}")
    return json.loads(done.stdout)


class NormalisedTermsTests(unittest.TestCase):
    def test_terms_lose_everything_but_letters_and_numbers(self) -> None:
        """Scenario: Normalised terms."""
        ps.require_node()
        text = SEARCH_TERMS.read_text(encoding="utf-8") \
            if SEARCH_TERMS.is_file() else ""
        self.assertNotRegex(text, r"(?m)^\s*(import|export)\b",
                            "search-terms.js must be a classic script")
        cases = [("CC(=O)O c1ccccc1", "CCOO c1ccccc1"),
                 ("50-78-2", "50782"),
                 ("  sample-data  ", "sampledata"),
                 ("α-pinene", "αpinene"),
                 ("(E)-chalcone", "Echalcone")]
        got = call_search_terms([("normaliseTerm", term)
                                 for term, _ in cases])
        self.assertEqual(got, [want for _, want in cases])


class CleanedResultTests(unittest.TestCase):
    def test_only_the_smiles_index_is_removed(self) -> None:
        """Scenario: Cleaned result."""
        result = {"meta": {"id": "OSDB-0001", "smiles_index": "x y"},
                  "excerpt": "e"}
        got = call_search_terms([("cleanResult", result)])
        self.assertEqual(got, [{"meta": {"id": "OSDB-0001"},
                                "excerpt": "e"}])


LIST_RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"),
                    { filename: process.argv[1] });
const calls = JSON.parse(fs.readFileSync(0, "utf8"));
const out = calls.map(([row, filters]) =>
  globalThis.OrgSynListFilter.rowMatches(row, filters));
process.stdout.write(JSON.stringify(out));
"""


class ListFilterTests(unittest.TestCase):
    def test_rows_match_every_set_filter(self) -> None:
        """Scenario: List filter matching (site-theme "List tools")."""
        node = ps.require_node()
        if not ps.LIST_FILTER.is_file():
            raise AssertionError("site/assets/js/list-filter.js does not exist")
        row = {"reactionTypes": "hydrolysis", "status": "draft"}
        multi = {"reactionTypes": "acylation hydrolysis", "status": "checked"}
        cases = [((row, {"reactionType": "", "status": ""}), True),
                 ((row, {"reactionType": "hydrolysis", "status": ""}), True),
                 ((row, {"reactionType": "hydro", "status": ""}), False),
                 ((row, {"reactionType": "", "status": "checked"}), False),
                 ((row, {"reactionType": "hydrolysis",
                         "status": "draft"}), True),
                 ((multi, {"reactionType": "acylation",
                           "status": "checked"}), True),
                 (({}, {"reactionType": "acylation", "status": ""}), False)]
        done = subprocess.run(
            [node, "-e", LIST_RUNNER, str(ps.LIST_FILTER)],
            input=json.dumps([call for call, _ in cases]),
            capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout),
                         [want for _, want in cases])
