"""Search tests: the real Pagefind bundle of a theme build, queried under
Node (site-search). They skip, naming node, when it is absent.

All queries of the class go to Node in one run, from ``setUpClass``. A
failure of that run fails every test on an assertion instead of erroring
the class. Findability is checked through the catalogue's searcher
(``OrgSynCatalogue.searcher``), which the run also calls for every term.
"""

import re
from typing import Any

import pipeline_support as ps
import sample_support as sup
from pipeline_support import Content


class SearchBatchCase(ps.ThemeBuildCase):
    """Collects requests, runs them once and serves the results."""

    batch_error: str | None = None
    out: dict[str, Any] = {}
    requests: list[dict[str, Any]] = []

    @classmethod
    def require_tools(cls) -> None:
        ps.require_node()

    @classmethod
    def ask(cls, term: str | None, filters: dict[str, str] | None = None,
            normalise: bool = True,
            sort: dict[str, str] | None = None) -> int:
        """Queue one search; return the index of its result list."""
        cls.requests.append({"term": term, "filters": filters,
                             "normalise": normalise, "sort": sort})
        return len(cls.requests) - 1

    @classmethod
    def plan(cls, items: list[Content]) -> None:
        """Queue the class's searches. Subclasses override."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.requests = []
        cls.out = {}
        cls.batch_error = None
        try:
            cls.plan(ps.read_content(cls.sandbox, cls.LOCALE))
            cls.out = ps.pagefind_search(
                cls.sandbox.root / "public", cls.requests)
        except AssertionError as exc:
            cls.batch_error = str(exc)

    def setUp(self) -> None:
        super().setUp()
        if self.batch_error is not None:
            self.fail(self.batch_error)

    def ids(self, index: int) -> list[str]:
        """The ``meta.id`` of each hit of a plain search, in order."""
        return [hit["id"] for hit in self.out["results"][index]]

    def found(self, index: int) -> list[str]:
        """The IDs the catalogue searcher returned for a search."""
        entry = self.out["searched"][index]
        self.assertIsNotNone(entry, "the search had a null term")
        self.assertNotIn("error", entry, f"the searcher failed: {entry}")
        return entry["ids"]


def source_words(path_text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]{6,}", path_text)}


def body_words(sandbox: ps.Sandbox) -> tuple[dict[str, str], list[str]]:
    """The unique Procedure word of each shipped procedure, by ID.

    Returns the words found and the IDs that have none. A word is a run of
    six or more ASCII letters in the Procedure section that no other
    source file contains, case-insensitively; the longest wins, ties by
    alphabet.
    """
    texts: dict[str, str] = {}
    sections: dict[str, str] = {}
    root = sandbox.root
    sources = (sorted((root / "org" / "procedures").glob("OSDB-*.org"))
               + sorted((root / "md" / "procedures").glob("OSDB-*.md")))
    for path in sources:
        ident = re.match(r"(OSDB-\d{4})-", path.name).group(1)
        text = path.read_text(encoding="utf-8")
        texts[ident] = text
        if path.suffix == ".org":
            sections[ident] = sup.org_sections(text).get("Procedure", "")
        else:
            sections[ident] = sup.md_sections(ps.body_of(text)).get(
                "Procedure", "")
    found: dict[str, str] = {}
    missing = []
    for ident, section in sections.items():
        others: set[str] = set()
        for other, text in texts.items():
            if other != ident:
                others |= source_words(text)
        candidates = {w for w in re.findall(r"[A-Za-z]{6,}", section)
                      if w.lower() not in others}
        if candidates:
            found[ident] = sorted(candidates,
                                  key=lambda w: (-len(w), w.lower()))[0]
        else:
            missing.append(ident)
    return found, missing


def substrings(smiles: str) -> set[str]:
    """Every contiguous substring q of ``smiles`` with len(N(q)) >= 3."""
    return {smiles[i:j] for i in range(len(smiles))
            for j in range(i + 1, len(smiles) + 1)
            if len(ps.smiles_key(smiles[i:j])) >= 3}


class ShippedSearchTests(SearchBatchCase):
    """Searches over the shipped procedures, without fixtures."""

    cas: int
    sorted_by_id: int
    by_id: dict[str, int]
    wintergreen: int
    biphenyl: int
    lookups: dict[str, tuple[int, str]]
    missing_words: list[str]
    parts: dict[str, tuple[int, set[str]]]
    full: dict[str, int]

    @classmethod
    def plan(cls, items: list[Content]) -> None:
        cls.cas = cls.ask("50-78-2")
        cls.sorted_by_id = cls.ask(None, normalise=False, sort={"id": "asc"})
        cls.by_id = {item.id: cls.ask(None, {"id": item.id},
                                      normalise=False)
                     for item in items}
        cls.wintergreen = cls.ask("wintergreen")
        cls.biphenyl = cls.ask("ccc(cc1)-c1")
        words, cls.missing_words = body_words(cls.sandbox)
        registry = ps.read_registry(cls.sandbox)
        cls.lookups = {}
        for item in items:
            compounds = [registry[e["compound"]] for e in item.products]
            wanted = [("id", item.id), ("word", words.get(item.id))]
            for compound in compounds:
                wanted += [("name", ps.shown_name(compound, cls.LOCALE)),
                           ("cas", compound.get("cas"))]
            wanted += [(f"tag {tag}", tag) for tag in item.tags]
            for kind, term in wanted:
                if term:
                    cls.lookups[f"{item.id} {kind}: {term}"] = (
                        cls.ask(term), item.id)
        cls.parts = {}
        cls.full = {}
        for item in items:
            for entry in item.products:
                smiles = registry[entry["compound"]]["smiles"]
                for part in substrings(smiles):
                    if part not in cls.parts:
                        cls.parts[part] = (cls.ask(part), set())
                    cls.parts[part][1].add(item.id)
                if smiles not in cls.full:
                    cls.full[smiles] = cls.ask(smiles)

    def test_cas_numbers_are_separate_words(self) -> None:
        """Scenario: CAS numbers are separate words."""
        self.assertEqual(self.found(self.cas), ["OSDB-0002"])

    def test_the_id_filter_and_sort_key(self) -> None:
        """Scenario: The ID filter and sort key."""
        published = sorted(item.id for item in self.content())
        self.assertEqual(list(self.out["filters"]), ["id"])
        self.assertEqual(self.out["filters"]["id"],
                         {ident: 1 for ident in published})
        listed = [hit["meta"].get("id")
                  for hit in self.out["results"][self.sorted_by_id]]
        self.assertEqual(listed, published)
        for ident, index in self.by_id.items():
            with self.subTest(procedure=ident):
                self.assertEqual(self.ids(index), [ident])

    def test_result_data_has_the_id_and_title(self) -> None:
        """Scenario: Result data."""
        hits = self.out["results"][self.wintergreen]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["meta"].get("id"), "OSDB-0001")
        self.assertEqual(hits[0]["meta"].get("title"), "Salicylic acid")
        self.assertEqual(self.found(self.wintergreen), ["OSDB-0001"])

    def test_name_cas_tag_id_and_body_word_find_the_procedure(self) -> None:
        """Scenario: Name, CAS, tag, ID and body word."""
        self.assertEqual(self.missing_words, [],
                         "procedures without a unique Procedure word")
        self.assertTrue(self.lookups)
        for label, (index, ident) in self.lookups.items():
            with self.subTest(search=label):
                self.assertIn(ident, self.found(index))

    def test_every_smiles_substring_finds_its_procedure(self) -> None:
        """Scenario: Every SMILES substring."""
        self.assertTrue(self.parts)
        failures = [f"{part!r} lacks {sorted(wanted - set(self.found(i)))}"
                    for part, (i, wanted) in sorted(self.parts.items())
                    if wanted - set(self.found(i))]
        self.assertEqual(failures, [])

    def test_a_full_smiles_finds_exactly_the_containing_ones(self) -> None:
        """Scenario: Full SMILES is exact."""
        items = self.content()
        registry = ps.read_registry(self.sandbox)

        def keys(item: Content) -> list[str]:
            return [ps.smiles_key(registry[e["compound"]]["smiles"])
                    for e in item.products]

        self.assertTrue(self.full)
        for smiles, index in self.full.items():
            key = ps.smiles_key(smiles)
            expected = sorted(other.id for other in items
                              if any(key in own for own in keys(other)))
            with self.subTest(smiles=smiles):
                self.assertEqual(sorted(self.found(index)), expected)

    def test_a_smiles_fragment_finds_the_general_procedure_too(self) -> None:
        """Scenario: SMILES substring in the catalogue (biphenyl)."""
        registry = ps.read_registry(self.sandbox)
        key = ps.smiles_key("ccc(cc1)-c1")
        expected = sorted(
            item.id for item in self.content()
            if any(key in ps.smiles_key(registry[e["compound"]]["smiles"])
                   for e in item.products))
        self.assertEqual(expected, ["OSDB-0004", "OSDB-0005", "OSDB-0009"])
        self.assertEqual(sorted(self.found(self.biphenyl)), expected)

    def test_the_searcher_agrees_with_the_result_data(self) -> None:
        """Scenario: Same procedures in the same order as the result data."""
        searches = [index for index, request in enumerate(self.requests)
                    if request["term"] is not None
                    and request["normalise"]]
        self.assertGreater(len(searches), len(self.parts))
        different = [
            f"{self.requests[index]['term']!r}: {self.found(index)} "
            f"is not {self.ids(index)}"
            for index in searches if self.found(index) != self.ids(index)]
        self.assertEqual(different, [])


class TwoProductSearchTests(ShippedSearchTests):
    """The same searches with the two-product fixture added: both of its
    products' names, CAS numbers and SMILES find it."""

    FIXTURES = ("OSDB-0907-two-products.md",)

    def test_both_products_find_the_procedure(self) -> None:
        """Scenario: Name, CAS, tag, ID and body word (two products)."""
        for kind, term in (("name", "trans-Stilbene"),
                           ("name", "cis-Stilbene"), ("cas", "103-30-0"),
                           ("cas", "645-49-8")):
            with self.subTest(term=term):
                index, ident = self.lookups[f"OSDB-0907 {kind}: {term}"]
                self.assertEqual(ident, "OSDB-0907")
                self.assertIn("OSDB-0907", self.found(index))

    def test_the_index_value_follows_both_products(self) -> None:
        """Scenario: Index value (two products)."""
        page = ps.load_page(self.public, self.public / "procedures"
                            / "osdb-0907" / "index.html")
        index = page.find("span", data_smiles_index=True)
        self.assertIsNotNone(index, "no SMILES index element")
        self.assertEqual(
            index.attrs["data-smiles-index"],
            ps.smiles_suffixes("c1ccc(cc1)/C=C/c1ccccc1") + " "
            + ps.smiles_suffixes(r"c1ccc(cc1)/C=C\c1ccccc1"))
