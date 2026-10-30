"""Unit tests of site/assets/js/catalogue-core.js under Node (site-catalogue
"Catalogue core functions", "Catalogue address", "Facet matching and
counts" and "Sort orders"; site-search "Catalogue text search"). They skip,
naming node, when it is absent.

The scripts run with ``vm`` in a fresh context that defines neither
``document``, ``window`` nor ``location``; it gets only the web platform's
``URLSearchParams`` and ``URL``. ``search-terms.js`` loads first, as in the
site's script.
"""

import json
import re
import subprocess
import unittest
from typing import Any

import pipeline_support as ps
from pipeline_support import CATALOGUE_CORE, SEARCH_TERMS

RUNNER = r"""
const fs = require("fs");
const vm = require("vm");
const scripts = process.argv.slice(1, 3);
const context = vm.createContext({ URLSearchParams, URL });
for (const script of scripts) {
  vm.runInContext(fs.readFileSync(script, "utf8"), context,
                  { filename: script });
}
const request = JSON.parse(fs.readFileSync(0, "utf8"));
const body = vm.runInContext(
  "(async (data) => {" + request.code + "\n})", context);
Promise.resolve(body(request.data)).then(
  (value) => {
    process.stdout.write(JSON.stringify(value === undefined ? null : value));
  },
  (error) => {
    console.error(error && error.stack ? error.stack : String(error));
    process.exit(1);
  });
"""

KNOWN = {"type": ["hydrolysis", "acylation"],
         "kind": ["specific", "general"],
         "status": ["draft", "checked", "retired"],
         "tag": ["sample-data", "cinnamate"],
         "author": ["a. example", "ä. müller"]}
DEFAULT_STATE = {"q": "", "type": [], "kind": [], "status": [], "tag": [],
                 "author": [], "sort": None, "view": "table"}


def evaluate(code: str, data: Any = None) -> Any:
    """Run ``code``, the body of an async function of ``data``, in the
    context that holds both scripts, and return its JSON result."""
    node = ps.require_node()
    for script in (SEARCH_TERMS, CATALOGUE_CORE):
        if not script.is_file():
            raise AssertionError(f"{script.relative_to(ps.REPO)} "
                                 "does not exist")
    done = subprocess.run(
        [node, "-e", RUNNER, str(SEARCH_TERMS), str(CATALOGUE_CORE)],
        input=json.dumps({"code": code, "data": data}),
        capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"node failed: {done.stderr}")
    return json.loads(done.stdout)


def state(**changes: Any) -> dict[str, Any]:
    """The default state with ``changes``."""
    return {**DEFAULT_STATE, **changes}


class ClassicScriptTests(unittest.TestCase):
    def test_the_core_is_a_classic_script_without_the_dom(self) -> None:
        """Scenario: A classic script without the DOM."""
        ps.require_node()
        self.assertTrue(CATALOGUE_CORE.is_file(),
                        "site/assets/js/catalogue-core.js does not exist")
        text = CATALOGUE_CORE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^\s*(import|export)\b",
                            "catalogue-core.js must be a classic script")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
        self.assertNotRegex(code, r"\b(document|window|location)\b")
        names = evaluate("""
            const core = OrgSynCatalogue;
            return ["parse", "serialize", "active", "sortOf", "withQuery",
                    "clear", "select", "searcher"].map(
              (name) => [name, typeof core[name]]);
        """)
        self.assertEqual(names, [[name, "function"] for name in (
            "parse", "serialize", "active", "sortOf", "withQuery", "clear",
            "select", "searcher")])


class ParseTests(unittest.TestCase):
    def parse(self, *searches: str, fixed: str | None = None) -> list[Any]:
        """``[state, ignored]`` of each search, for ``KNOWN`` and fixed."""
        found = evaluate("""
            return data.searches.map((search) =>
              OrgSynCatalogue.parse(search, data.known, data.fixed));
        """, {"searches": list(searches), "known": KNOWN, "fixed": fixed})
        return [[item["state"], item["ignored"]] for item in found]

    def test_an_address_is_read_into_a_state(self) -> None:
        """Scenario: Reading an address."""
        ps.require_node()
        [[got, ignored]] = self.parse(
            "?q=+acid+&type=acylation&type=hydrolysis&type=acylation"
            "&kind=general&tag=nope&tag=&sort=title&view=details&page=2&q=x")
        self.assertEqual(got, state(q="acid", type=["hydrolysis", "acylation"],
                                    kind=["general"], sort="title",
                                    view="details"))
        self.assertEqual(ignored, [["tag", "nope"], ["tag", ""],
                                   ["page", "2"], ["q", "x"]])

    def test_the_leading_question_mark_is_optional(self) -> None:
        """Scenario: Reading an address (without the question mark)."""
        ps.require_node()
        search = ("q=acid&status=checked&status=draft"
                  "&author=%C3%A4.+m%C3%BCller")
        (with_mark, without) = self.parse("?" + search, search)
        self.assertEqual(with_mark, without)
        self.assertEqual(with_mark[0], state(
            q="acid", status=["draft", "checked"], author=["ä. müller"]))
        self.assertEqual(with_mark[1], [])

    def test_the_empty_address_is_the_default_state(self) -> None:
        """Scenario: Reading an address (no parameters)."""
        ps.require_node()
        self.assertEqual(self.parse("", "?", "?q=+++"),
                         [[DEFAULT_STATE, []]] * 3)

    def test_sorts_and_views_that_do_not_apply(self) -> None:
        """Scenario: Sorts and views that do not apply."""
        ps.require_node()
        got = self.parse("?sort=relevance", "?q=acid&sort=relevance",
                         "?q=---&sort=relevance", "?sort=newest",
                         "?sort=id&sort=title", "?view=grid", "?view=table")
        self.assertEqual([s["sort"] for s, _ in got],
                         [None, "relevance", None, None, "id", None, None])
        self.assertEqual([s["view"] for s, _ in got], ["table"] * 7)
        self.assertEqual([i for _, i in got], [
            [["sort", "relevance"]], [], [["sort", "relevance"]],
            [["sort", "newest"]], [["sort", "title"]], [["view", "grid"]],
            []])

    def test_only_the_first_value_of_a_single_valued_name_counts(
            self) -> None:
        """Scenario: Sorts and views that do not apply (repeats)."""
        ps.require_node()
        got = self.parse("?sort=relevance&sort=id", "?view=grid&view=details",
                         "?view=details&view=table", "?q=a&q=b&q=")
        self.assertEqual([(s["sort"], s["view"], s["q"]) for s, _ in got],
                         [(None, "table", ""), (None, "table", ""),
                          (None, "details", ""), (None, "table", "a")])
        self.assertEqual([i for _, i in got], [
            [["sort", "relevance"], ["sort", "id"]],
            [["view", "grid"], ["view", "details"]],
            [["view", "table"]], [["q", "b"], ["q", ""]]])

    def test_unknown_facet_values_are_ignored(self) -> None:
        """Scenario: Reading an address (facet values)."""
        ps.require_node()
        [[got, ignored]] = self.parse(
            "?type=Hydrolysis&type=&status=published&status=retired"
            "&tag=cinnamate&tag=sample-data&author=a.+example")
        self.assertEqual(got, state(
            status=["retired"], tag=["sample-data", "cinnamate"],
            author=["a. example"]))
        self.assertEqual(ignored, [["type", "Hydrolysis"], ["type", ""],
                                   ["status", "published"]])

    def test_kind_values_are_read_in_the_order_of_known(self) -> None:
        """Scenario: Reading an address (kind values)."""
        ps.require_node()
        [[got, ignored]] = self.parse(
            "?kind=general&kind=other&kind=specific&kind=general&kind=")
        self.assertEqual(got, state(kind=["specific", "general"]))
        self.assertEqual(ignored, [["kind", "other"], ["kind", ""]])

    def test_the_kind_is_fixed_on_the_general_procedures_page(self) -> None:
        """Scenario: The fixed facet is not read from the address (kind)."""
        ps.require_node()
        [[got, ignored]] = self.parse("?kind=general&status=draft&kind=x",
                                      fixed="kind")
        self.assertEqual(got, state(status=["draft"]))
        self.assertEqual(ignored, [["kind", "general"], ["kind", "x"]])

    def test_the_fixed_facet_is_not_read_from_the_address(self) -> None:
        """Scenario: The fixed facet is not read from the address."""
        ps.require_node()
        [[got, ignored]] = self.parse("?tag=cinnamate&status=draft",
                                      fixed="tag")
        self.assertEqual(got, state(status=["draft"]))
        self.assertEqual(ignored, [["tag", "cinnamate"]])


class SerializeTests(unittest.TestCase):
    def serialize(self, *states: dict[str, Any]) -> list[Any]:
        return evaluate("""
            return data.states.map((s) => OrgSynCatalogue.serialize(s));
        """, {"states": list(states)})

    def round_trip(self, *states: dict[str, Any]) -> list[Any]:
        """Each state, serialized, parsed and serialized again."""
        return evaluate("""
            return data.states.map((s) => {
              const text = OrgSynCatalogue.serialize(s);
              const parsed = OrgSynCatalogue.parse(text, data.known, null);
              return [text, parsed.state, parsed.ignored,
                      OrgSynCatalogue.serialize(parsed.state)];
            });
        """, {"states": list(states), "known": KNOWN})

    def test_canonical_addresses(self) -> None:
        """Scenario: Canonical addresses."""
        ps.require_node()
        full = state(q=" acetic acid ", status=["draft", "checked"],
                     author=["ä. müller"], sort="modified", view="details")
        got = self.round_trip(DEFAULT_STATE, full)
        self.assertEqual(got[0][0], "")
        self.assertEqual(
            got[1][0],
            "?q=acetic+acid&status=draft&status=checked"
            "&author=%C3%A4.+m%C3%BCller&sort=modified&view=details")
        for text, parsed, ignored, again in got:
            with self.subTest(address=text):
                self.assertEqual(again, text)
                self.assertEqual(ignored, [])
        self.assertEqual(got[0][1], DEFAULT_STATE)
        self.assertEqual(got[1][1], state(
            q="acetic acid", status=["draft", "checked"],
            author=["ä. müller"], sort="modified", view="details"))

    def test_parameters_come_in_a_fixed_order(self) -> None:
        """Scenario: Canonical addresses (order of the parameters)."""
        ps.require_node()
        full = state(q="x", type=["hydrolysis", "acylation"],
                     kind=["specific", "general"],
                     status=["retired"], tag=["sample-data", "cinnamate"],
                     author=["a. example", "ä. müller"], sort="title",
                     view="details")
        [got] = self.serialize(full)
        self.assertEqual(
            got,
            "?q=x&type=hydrolysis&type=acylation&kind=specific"
            "&kind=general&status=retired"
            "&tag=sample-data&tag=cinnamate&author=a.+example"
            "&author=%C3%A4.+m%C3%BCller&sort=title&view=details")

    def test_defaults_and_blank_queries_write_nothing(self) -> None:
        """Scenario: Canonical addresses (defaults)."""
        ps.require_node()
        got = self.serialize(state(q="   "), state(view="table"),
                             state(status=["draft"]), state(view="details"),
                             state(q="a&b=c d"))
        self.assertEqual(got, ["", "", "?status=draft", "?view=details",
                               "?q=a%26b%3Dc+d"])
        [kind] = self.serialize(state(kind=["general"]))
        self.assertEqual(kind, "?kind=general")

    def test_known_states_survive_a_round_trip(self) -> None:
        """Scenario: Canonical addresses (round trip)."""
        ps.require_node()
        states = [
            state(q="acid", sort="relevance"),
            state(q="CC(=O)O c1ccccc1", type=["acylation"], sort="id"),
            state(q="é & ü=1", tag=["cinnamate"], sort="created"),
            state(status=["draft", "checked", "retired"], sort="title"),
            state(type=["hydrolysis", "acylation"], tag=["sample-data"],
                  author=["a. example", "ä. müller"], view="details"),
            state(q="50-78-2", author=["ä. müller"], sort="modified"),
            state(kind=["general"]),
            state(q="x", kind=["specific", "general"], status=["draft"]),
        ]
        for original, (text, parsed, ignored, again) in zip(
                states, self.round_trip(*states)):
            with self.subTest(address=text):
                self.assertEqual(parsed, original)
                self.assertEqual(ignored, [])
                self.assertEqual(again, text)


class ActiveAndSortTests(unittest.TestCase):
    def test_a_query_is_active_when_a_term_is_left(self) -> None:
        """Scenario: Relevance comes and goes with the query (active)."""
        ps.require_node()
        queries = ["", "  ", "---", "()", "a", " 50-78-2 ", "α", "(E)"]
        got = evaluate("""
            return data.map((q) => OrgSynCatalogue.active({q}));
        """, queries)
        self.assertEqual(got, [False, False, False, False, True, True, True,
                               True])

    def test_the_sort_in_effect(self) -> None:
        """Scenario: Relevance comes and goes with the query (sortOf)."""
        ps.require_node()
        cases = [(state(), "id"), (state(q="x"), "relevance"),
                 (state(sort="relevance"), "id"),
                 (state(q="x", sort="relevance"), "relevance"),
                 (state(sort="title"), "title"),
                 (state(q="x", sort="created"), "created"),
                 (state(q="--"), "id"),
                 (state(q="--", sort="relevance"), "id"),
                 (state(q="x", sort="id"), "id")]
        got = evaluate("""
            return data.map((s) => OrgSynCatalogue.sortOf(s));
        """, [case for case, _ in cases])
        self.assertEqual(got, [want for _, want in cases])

    def test_relevance_comes_and_goes_with_the_query(self) -> None:
        """Scenario: Relevance comes and goes with the query."""
        ps.require_node()
        got = evaluate("""
            const core = OrgSynCatalogue;
            const plain = data.plain;
            const first = core.withQuery(plain, "aspirin");
            const second = core.withQuery(first, "");
            const modified = Object.assign({}, plain, {sort: "modified"});
            const asked = core.withQuery(modified, "aspirin");
            const cleared = core.clear(asked);
            const chosen = Object.assign({}, data.details,
              {q: "aspirin", sort: "relevance"});
            const after = core.clear(chosen);
            return {
              plain: [core.sortOf(plain), core.sortOf(first),
                      core.sortOf(second)],
              modified: [core.sortOf(modified), core.sortOf(asked),
                         core.sortOf(cleared)],
              relevance: [core.sortOf(chosen), core.sortOf(after)],
              states: [first, second, asked, cleared, after]};
        """, {"plain": DEFAULT_STATE, "details": state(view="details")})
        self.assertEqual(got["plain"], ["id", "relevance", "id"])
        self.assertEqual(got["modified"], ["modified"] * 3)
        self.assertEqual(got["relevance"], ["relevance", "id"])
        first, second, asked, cleared, after = got["states"]
        self.assertEqual(first, state(q="aspirin"))
        self.assertEqual(second, DEFAULT_STATE)
        self.assertEqual(asked, state(q="aspirin", sort="modified"))
        self.assertEqual(cleared, state(sort="modified"))
        self.assertEqual(after, state(view="details"))

    def test_with_query_changes_only_the_query(self) -> None:
        """Scenario: Relevance comes and goes with the query (withQuery)."""
        ps.require_node()
        selected = state(q="a", type=["hydrolysis"], status=["draft"],
                         tag=["cinnamate"], author=["ä. müller"],
                         view="details")
        cases = [
            (selected, "b"),
            ({**selected, "sort": "title"}, ""),
            ({**selected, "sort": "relevance"}, "b c"),
            ({**selected, "sort": "relevance"}, "--"),
            ({**selected, "sort": "relevance"}, ""),
        ]
        got = evaluate("""
            return data.map(([s, q]) => OrgSynCatalogue.withQuery(s, q));
        """, [list(case) for case in cases])
        self.assertEqual(got, [
            {**selected, "q": "b"},
            {**selected, "q": "", "sort": "title"},
            {**selected, "q": "b c", "sort": "relevance"},
            {**selected, "q": "--", "sort": None},
            {**selected, "q": "", "sort": None}])

    def test_clear_keeps_the_sort_and_the_view(self) -> None:
        """Scenario: Relevance comes and goes with the query (clear)."""
        ps.require_node()
        full = state(q="a", type=["hydrolysis"], status=["draft"],
                     tag=["cinnamate"], author=["ä. müller"], view="details")
        cases = [{**full, "sort": "title"}, {**full, "sort": "created"},
                 {**full, "sort": "relevance"}, full]
        got = evaluate("""
            return data.map((s) => OrgSynCatalogue.clear(s));
        """, cases)
        self.assertEqual(got, [state(sort="title", view="details"),
                               state(sort="created", view="details"),
                               state(view="details"),
                               state(view="details")])


def record(ident: str, title: str, created: str, modified: str,
           type: list[str] | None = None, status: str = "draft",
           tag: list[str] | None = None,
           author: list[str] | None = None,
           kind: str = "specific") -> dict[str, Any]:
    return {"id": ident, "title": title, "created": created,
            "modified": modified, "type": type or [], "kind": kind,
            "status": status, "tag": tag or [], "author": author or []}


STAMP = "2026-01-01T00:00:00Z"
SIX = [
    record("OSDB-0001", "Salicylic acid", STAMP, STAMP, ["hydrolysis"],
           "draft", ["sample-data", "saponification"],
           ["a. example", "b. example"]),
    record("OSDB-0002", "Aspirin", STAMP, STAMP, ["acylation"], "draft",
           ["sample-data", "acetylation"], ["a. example", "c. example"]),
    record("OSDB-0003", "Isopentyl acetate", STAMP, STAMP,
           ["esterification"], "checked", ["fragrance"], ["ä. müller"],
           "general"),
    record("OSDB-0004", "Cinnamic acid", STAMP, STAMP, ["hydrolysis"],
           "retired", ["cinnamate", "saponification"],
           ["ä. müller", "a. example"]),
    record("OSDB-0005", "Cinnamoyl chloride", STAMP, STAMP, ["acylation"],
           "checked", ["cinnamate"], ["b. example"]),
    record("OSDB-0006", "Cinnamyl alcohol", STAMP, STAMP, ["reduction"],
           "draft", ["cinnamate", "sample-data"], ["ä. müller"], "general"),
]
ALL_VALUES = {
    "type": ["hydrolysis", "acylation", "esterification", "reduction"],
    "kind": ["specific", "general"],
    "status": ["draft", "checked", "retired"],
    "tag": ["sample-data", "saponification", "acetylation", "fragrance",
            "cinnamate"],
    "author": ["a. example", "b. example", "c. example", "ä. müller"]}


def ids(*numbers: int) -> list[str]:
    return [f"OSDB-{number:04d}" for number in numbers]


def select(records: list[dict[str, Any]], chosen: dict[str, Any],
           matched: list[str] | None, language: str = "en") -> dict[str, Any]:
    return evaluate("""
        return OrgSynCatalogue.select(data.records, data.state, data.matched,
                                      data.language);
    """, {"records": records, "state": chosen, "matched": matched,
          "language": language})


class SelectTests(unittest.TestCase):
    def test_or_within_a_facet_and_across_facets(self) -> None:
        """Scenario: OR within a facet, AND across facets."""
        ps.require_node()
        types = ["hydrolysis", "acylation"]
        first = select(SIX, state(type=types), None)
        second = select(SIX, state(type=types, status=["draft"]), None)
        third = select(SIX, state(status=["retired"]), None)
        self.assertEqual(first["ids"], ids(1, 2, 4, 5))
        self.assertEqual(second["ids"], ids(1, 2))
        self.assertEqual(third["ids"], ids(4))

    def test_nothing_selected_lists_every_record_by_id(self) -> None:
        """Scenario: OR within a facet, AND across facets (no selection)."""
        ps.require_node()
        shuffled = [SIX[i] for i in (3, 0, 5, 2, 1, 4)]
        got = select(shuffled, DEFAULT_STATE, None)
        self.assertEqual(got["ids"], ids(1, 2, 3, 4, 5, 6))
        self.assertEqual(got["counts"]["status"],
                         {"draft": 3, "checked": 2, "retired": 1})
        self.assertEqual(got["counts"]["kind"],
                         {"specific": 4, "general": 2})
        self.assertEqual(got["counts"]["type"],
                         {"hydrolysis": 2, "acylation": 2,
                          "esterification": 1, "reduction": 1})
        self.assertEqual(got["counts"]["tag"],
                         {"sample-data": 3, "saponification": 2,
                          "acetylation": 1, "fragrance": 1, "cinnamate": 3})
        self.assertEqual(got["counts"]["author"],
                         {"a. example": 3, "b. example": 2,
                          "c. example": 1, "ä. müller": 3})

    def test_a_record_with_two_values_matches_either(self) -> None:
        """Scenario: OR within a facet, AND across facets (two values)."""
        ps.require_node()
        both = [{**SIX[0], "type": ["hydrolysis", "reduction"]}, SIX[1],
                SIX[5]]
        for wanted, expected in ((["hydrolysis"], ids(1)),
                                 (["reduction"], ids(1, 6)),
                                 (["acylation", "reduction"], ids(1, 2, 6))):
            with self.subTest(selected=wanted):
                self.assertEqual(select(both, state(type=wanted), None)["ids"],
                                 expected)

    def test_the_kind_facet_selects_and_counts(self) -> None:
        """Scenario: OR within a facet, AND across facets (kind)."""
        ps.require_node()
        general = select(SIX, state(kind=["general"]), None)
        self.assertEqual(general["ids"], ids(3, 6))
        self.assertEqual(general["counts"]["kind"],
                         {"specific": 4, "general": 2})
        self.assertEqual(general["counts"]["type"],
                         {"hydrolysis": 0, "acylation": 0,
                          "esterification": 1, "reduction": 1})
        both = select(SIX, state(kind=["specific", "general"]), None)
        self.assertEqual(both["ids"], ids(1, 2, 3, 4, 5, 6))
        narrowed = select(SIX, state(kind=["specific"], status=["checked"]),
                          None)
        self.assertEqual(narrowed["ids"], ids(5))
        self.assertEqual(narrowed["counts"]["kind"],
                         {"specific": 1, "general": 1})
        self.assertEqual(narrowed["counts"]["status"],
                         {"draft": 2, "checked": 1, "retired": 1})

    def test_counts_leave_out_the_facets_own_selections(self) -> None:
        """Scenario: Counts leave out the facet's own selections."""
        ps.require_node()
        chosen = state(q="acid", type=["hydrolysis"], tag=["cinnamate"])
        got = select(SIX, chosen, ids(4, 6, 1, 5))
        self.assertEqual(got["ids"], ids(4))
        self.assertEqual(got["counts"], {
            "type": {"hydrolysis": 1, "acylation": 1, "esterification": 0,
                     "reduction": 1},
            "kind": {"specific": 1, "general": 0},
            "status": {"draft": 0, "checked": 0, "retired": 1},
            "tag": {"sample-data": 1, "saponification": 2, "acetylation": 0,
                    "fragrance": 0, "cinnamate": 1},
            "author": {"a. example": 1, "b. example": 0, "c. example": 0,
                       "ä. müller": 1}})

    def test_a_selected_value_without_records_counts_zero(self) -> None:
        """Scenario: Counts leave out the facet's own selections (zero)."""
        ps.require_node()
        got = select(SIX, state(type=["hydrolysis"], tag=["fragrance"]), None)
        self.assertEqual(got["ids"], [])
        self.assertEqual(got["counts"]["type"],
                         {"hydrolysis": 0, "acylation": 0,
                          "esterification": 1, "reduction": 0})
        self.assertEqual(got["counts"]["tag"],
                         {"sample-data": 1, "saponification": 2,
                          "acetylation": 0, "fragrance": 0, "cinnamate": 1})
        for facet in ("status", "author", "kind"):
            self.assertEqual(set(got["counts"][facet].values()), {0}, facet)
        unknown = select(SIX, state(tag=["no-such-tag"]), None)
        self.assertEqual(unknown["ids"], [])
        self.assertEqual(unknown["counts"]["tag"]["no-such-tag"], 0)

    def test_filters_without_a_query_and_an_empty_result(self) -> None:
        """Scenario: Filters without a query and an empty result."""
        ps.require_node()
        chosen = state(author=["ä. müller"])
        got = select(SIX, chosen, None)
        self.assertEqual(got["ids"], ids(3, 4, 6))
        self.assertEqual(got["counts"]["author"],
                         {"a. example": 3, "b. example": 2, "c. example": 1,
                          "ä. müller": 3})
        self.assertEqual(got["counts"]["type"],
                         {"hydrolysis": 1, "acylation": 0,
                          "esterification": 1, "reduction": 1})
        self.assertEqual(got["counts"]["kind"],
                         {"specific": 1, "general": 2})
        empty = select(SIX, {**chosen, "q": "nothing"}, [])
        self.assertEqual(empty["ids"], [])
        self.assertEqual({facet: sorted(values)
                          for facet, values in empty["counts"].items()},
                         {facet: sorted(values)
                          for facet, values in ALL_VALUES.items()})
        for facet, values in empty["counts"].items():
            self.assertEqual(set(values.values()), {0}, facet)

    def test_ids_the_query_names_but_no_record_has_are_ignored(self) -> None:
        """Scenario: Filters without a query and an empty result (stray)."""
        ps.require_node()
        got = select(SIX, state(q="acid"), ["OSDB-0999", *ids(5, 2)])
        self.assertEqual(got["ids"], ids(5, 2))

    def test_each_procedure_is_listed_and_counted_once(self) -> None:
        """Scenario: Each procedure once."""
        ps.require_node()
        again = record("OSDB-0002", "Aspirin again", STAMP, STAMP,
                       ["acylation"], "retired", ["dup-only", "sample-data"],
                       ["z. dup", "a. example"])
        records = [*SIX, SIX[1], again]
        got = select(records, state(q="acid"), ids(2, 2, 1))
        self.assertEqual(got["ids"], ids(2, 1))
        counts = got["counts"]
        self.assertEqual(counts["status"],
                         {"draft": 2, "checked": 0, "retired": 0})
        self.assertEqual(counts["tag"],
                         {"sample-data": 2, "saponification": 1,
                          "acetylation": 1, "fragrance": 0, "cinnamate": 0})
        self.assertEqual(counts["author"],
                         {"a. example": 2, "b. example": 1, "c. example": 1,
                          "ä. müller": 0})
        self.assertEqual(counts["type"],
                         {"hydrolysis": 1, "acylation": 1,
                          "esterification": 0, "reduction": 0})
        self.assertEqual(counts["kind"], {"specific": 2, "general": 0})
        plain = select(records, DEFAULT_STATE, None)
        self.assertEqual(plain["ids"], ids(1, 2, 3, 4, 5, 6))
        self.assertEqual(plain["counts"]["status"],
                         {"draft": 3, "checked": 2, "retired": 1})

    def test_no_function_changes_its_arguments(self) -> None:
        """Requirement: Catalogue core functions (arguments unchanged)."""
        ps.require_node()
        chosen = state(q="acid", type=["hydrolysis", "acylation"],
                       status=["draft"], sort="title", view="details")
        before, after = evaluate("""
            const core = OrgSynCatalogue;
            const records = data.records.slice().reverse();
            const matched = data.matched.slice();
            const snapshot = () => JSON.stringify(
              [records, data.state, data.known, matched]);
            const before = snapshot();
            core.parse("?q=a&type=hydrolysis&sort=title", data.known, null);
            core.serialize(data.state);
            core.active(data.state);
            core.sortOf(data.state);
            core.withQuery(data.state, "b");
            core.clear(data.state);
            core.select(records, data.state, matched, "en");
            core.select(records, Object.assign({}, data.state,
              {sort: null}), matched, "en");
            return [before, snapshot()];
        """, {"records": SIX, "state": chosen, "known": KNOWN,
              "matched": ids(6, 1, 4, 2)})
        self.assertEqual(after, before)


# Several records share an instant that is written with different
# offsets, and titles differ only in case or in a number.
ORDER = [
    record("OSDB-0001", "Banana", "2026-01-10T09:00:00+01:00",
           "2026-03-01T12:00:00Z"),
    record("OSDB-0002", "banana", "2026-01-10T08:00:00Z",
           "2026-03-03T12:00:00Z"),
    record("OSDB-0003", "4-Methylbenzoic acid", "2026-02-01T00:00:00Z",
           "2026-03-02T08:00:00Z"),
    record("OSDB-0004", "10-methylbenzoic acid", "2026-01-05T00:00:00Z",
           "2026-03-02T10:00:00+02:00"),
    record("OSDB-0005", "Same title", "2026-03-01T00:00:00Z",
           "2026-02-01T00:00:00Z"),
    record("OSDB-0006", "Same title", "2026-01-10T03:00:00-05:00",
           "2026-02-01T01:00:00+01:00"),
    record("OSDB-0007", "apple", "2026-02-15T00:00:00Z",
           "2026-03-04T00:00:00Z"),
    record("OSDB-0008", "Apple", "2026-02-15T00:00:00Z",
           "2026-03-05T00:00:00Z"),
]


class SortOrderTests(unittest.TestCase):
    def ordered(self, records: list[dict[str, Any]], sort: str,
                language: str = "en") -> list[str]:
        return select(records, state(sort=sort), None, language)["ids"]

    def test_every_order(self) -> None:
        """Scenario: Every order."""
        ps.require_node()
        reversed_records = list(reversed(ORDER))
        expected = {
            "id": ids(1, 2, 3, 4, 5, 6, 7, 8),
            "title": ids(3, 4, 7, 8, 2, 1, 5, 6),
            "created": ids(5, 7, 8, 3, 1, 2, 6, 4),
            "modified": ids(8, 7, 2, 3, 4, 1, 5, 6)}
        for sort, wanted in expected.items():
            with self.subTest(sort=sort):
                self.assertEqual(self.ordered(ORDER, sort), wanted)
                self.assertEqual(self.ordered(reversed_records, sort), wanted)
        relevance = ids(4, 8, 1, 7, 2, 6, 5, 3)
        got = select(ORDER, state(q="x", sort="relevance"), relevance)
        self.assertEqual(got["ids"], relevance)
        for sort, wanted in expected.items():
            self.assertEqual(sorted(wanted), ids(1, 2, 3, 4, 5, 6, 7, 8))
        self.assertEqual(sorted(relevance), ids(1, 2, 3, 4, 5, 6, 7, 8))

    def test_the_default_order_follows_the_query(self) -> None:
        """Scenario: Every order (default sort)."""
        ps.require_node()
        relevance = ids(6, 3, 1, 8)
        by_query = select(ORDER, state(q="x"), relevance)
        self.assertEqual(by_query["ids"], relevance)
        by_id = select(ORDER, DEFAULT_STATE, None)
        self.assertEqual(by_id["ids"], ids(1, 2, 3, 4, 5, 6, 7, 8))
        chosen = select(ORDER, state(q="x", sort="title"), relevance)
        self.assertEqual(chosen["ids"], ids(3, 8, 1, 6))
        listed = select(ORDER, state(q="x", sort="id"), relevance)
        self.assertEqual(listed["ids"], ids(1, 3, 6, 8))

    def test_instants_are_compared_not_their_text(self) -> None:
        """Scenario: Every order (offsets)."""
        ps.require_node()
        same = [record("OSDB-0010", "x", "2026-05-01T10:00:00+02:00",
                       "2026-05-01T10:00:00+02:00"),
                record("OSDB-0009", "x", "2026-05-01T08:00:00Z",
                       "2026-05-01T08:00:00Z"),
                record("OSDB-0011", "x", "2026-05-01T09:00:00Z",
                       "2026-05-01T07:59:59Z")]
        for sort in ("created", "modified"):
            with self.subTest(sort=sort):
                got = self.ordered(same, sort)
                self.assertEqual(got, ids(11, 9, 10) if sort == "created"
                                 else ids(9, 10, 11))

    def test_titles_are_collated_by_the_language(self) -> None:
        """Scenario: Every order (collation)."""
        ps.require_node()
        titles = [record("OSDB-0001", "Zebra", STAMP, STAMP),
                  record("OSDB-0002", "Ärger", STAMP, STAMP),
                  record("OSDB-0003", "Apfel", STAMP, STAMP),
                  record("OSDB-0004", "Item 10", STAMP, STAMP),
                  record("OSDB-0005", "Item 9", STAMP, STAMP)]
        german = self.ordered(titles, "title", "de")
        self.assertEqual(german, ids(3, 2, 5, 4, 1))
        swedish_z_first = evaluate("""
            return new Intl.Collator("sv").compare("Zebra", "Ärger") < 0;
        """)
        if swedish_z_first:
            self.assertEqual(self.ordered(titles, "title", "sv"),
                             ids(3, 5, 4, 1, 2))


STUB = r"""
function stub(config) {
  const calls = [];
  const page = (id) => ({
    id,
    data() {
      calls.push(["data", id]);
      throw new Error("data() must not be called");
    },
  });
  return {
    calls,
    config,
    async filters() {
      calls.push(["filters"]);
      return {id: config.counts};
    },
    async search(term, options) {
      calls.push(["search", term, options === undefined ? null : options]);
      if (term === null) {
        return {results: config.sorted.map(page)};
      }
      if (!(term in config.queries)) {
        throw new Error("unexpected search " + term);
      }
      return {results: config.queries[term].map(page)};
    },
  };
}
const outcome = async (promise) => {
  try {
    return {resolved: await promise};
  } catch (error) {
    return {error: error instanceof Error ? "Error" : String(error)};
  }
};
"""


def counts(*numbers: int, extra: dict[str, int] | None = None
           ) -> dict[str, int]:
    return {**{ident: 1 for ident in ids(*numbers)}, **(extra or {})}


class SearcherTests(unittest.TestCase):
    def run_stub(self, body: str, data: Any = None) -> Any:
        return evaluate(STUB + body, data)

    def test_a_mismatched_index_is_refused(self) -> None:
        """Scenario: A mismatched index is refused."""
        ps.require_node()
        got = self.run_stub("""
            const fewer = stub({counts: data.three,
                                sorted: ["hA", "hB"],
                                queries: {acid: ["hA"]}});
            const stray = stub({counts: data.two, sorted: ["hA", "hB"],
                                queries: {acid: ["hA", "hZ"]}});
            const calm = stub({counts: data.two, sorted: ["hA", "hB"],
                               queries: {}});
            const first = await outcome(
              OrgSynCatalogue.searcher(fewer).search("acid"));
            const second = await outcome(
              OrgSynCatalogue.searcher(stray).search("acid"));
            const third = await outcome(
              OrgSynCatalogue.searcher(calm).search("--"));
            return {first, second, third,
                    calls: [fewer.calls, stray.calls, calm.calls]};
        """, {"three": counts(1, 2, 3), "two": counts(1, 2)})
        self.assertEqual(got["first"], {"error": "Error"})
        self.assertEqual(got["second"], {"error": "Error"})
        self.assertEqual(got["third"], {"resolved": []})
        fewer, stray, calm = got["calls"]
        for calls in got["calls"]:
            self.assertNotIn("data", [call[0] for call in calls])
        self.assertNotIn("search", [call[0] for call in calm])
        self.assertEqual(calm, [])
        self.assertEqual(fewer[0], ["filters"])
        self.assertEqual(stray[0], ["filters"])

    def test_results_are_mapped_to_ids_in_result_order(self) -> None:
        """Scenario: Catalogue text search (pairing)."""
        ps.require_node()
        got = self.run_stub("""
            const index = stub({
              counts: data.counts,
              sorted: ["hA", "hB", "hC"],
              queries: {acid: ["hC", "hA"], CCOO: ["hB"]}});
            const searcher = OrgSynCatalogue.searcher(index);
            const untouched = index.calls.length;
            const promise = searcher.search("acid");
            const isPromise = typeof promise.then === "function";
            const first = await promise;
            const second = await searcher.search(" CC(=O)O ");
            const third = await searcher.search("acid");
            return {untouched, isPromise, first, second, third,
                    calls: index.calls};
        """, {"counts": {"OSDB-0003": 1, "OSDB-0001": 1, "OSDB-0002": 1,
                         "OSDB-0009": 0}})
        self.assertEqual(got["untouched"], 0)
        self.assertTrue(got["isPromise"])
        self.assertEqual(got["first"], ids(3, 1))
        self.assertEqual(got["second"], ids(2))
        self.assertEqual(got["third"], ids(3, 1))
        calls = got["calls"]
        self.assertEqual([call[0] for call in calls],
                         ["filters", "search", "search", "search", "search"])
        self.assertEqual(calls[1][1], None)
        self.assertEqual(calls[1][2]["sort"], {"id": "asc"})
        self.assertEqual([call[1] for call in calls[2:]],
                         ["acid", "CCOO", "acid"])

    def test_an_empty_query_makes_no_call(self) -> None:
        """Scenario: Catalogue text search (empty query)."""
        ps.require_node()
        got = self.run_stub("""
            const index = stub({counts: data, sorted: ["hA"], queries: {}});
            const searcher = OrgSynCatalogue.searcher(index);
            const found = [];
            for (const q of ["", "   ", "--", "()-", "\\t"]) {
              found.push(await searcher.search(q));
            }
            return {found, calls: index.calls};
        """, counts(1))
        self.assertEqual(got["found"], [[]] * 5)
        self.assertEqual(got["calls"], [])

    def test_after_a_refusal_the_next_search_pairs_again(self) -> None:
        """Scenario: Catalogue text search (refusal)."""
        ps.require_node()
        got = self.run_stub("""
            const index = stub({counts: data.counts, sorted: ["hA", "hB"],
                                queries: {acid: ["hB"]}});
            const searcher = OrgSynCatalogue.searcher(index);
            const first = await outcome(searcher.search("acid"));
            index.config.sorted = ["hA", "hB", "hC"];
            const second = await outcome(searcher.search("acid"));
            const third = await outcome(searcher.search("acid"));
            return {first, second, third,
                    names: index.calls.map((call) => call[0]
                      + (call[0] === "search" ? ":" + call[1] : ""))};
        """, {"counts": counts(1, 2, 3)})
        self.assertEqual(got["first"], {"error": "Error"})
        self.assertEqual(got["second"], {"resolved": ids(2)})
        self.assertEqual(got["third"], {"resolved": ids(2)})
        names = got["names"]
        self.assertEqual(names.count("filters"), 2)
        self.assertEqual(names.count("search:null"), 2)
        self.assertEqual(names[-2:], ["search:acid", "search:acid"])
