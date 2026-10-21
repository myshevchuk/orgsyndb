"""Search tests: the real Pagefind bundle of a theme build, queried under
Node (site-search). They skip, naming node, when it is absent.

All queries of the class go to Node in one run, from ``setUpClass``. A
failure of that run fails every test on an assertion instead of erroring
the class.
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
            normalise: bool = True) -> int:
        """Queue one search; return the index of its result list."""
        cls.requests.append({"term": term, "filters": filters,
                             "normalise": normalise})
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
            cls.plan(ps.read_content(cls.sandbox))
            cls.out = ps.pagefind_search(
                cls.sandbox.root / "public", cls.requests)
        except AssertionError as exc:
            cls.batch_error = str(exc)

    def setUp(self) -> None:
        super().setUp()
        if self.batch_error is not None:
            self.fail(self.batch_error)

    def ids(self, index: int) -> list[str]:
        return [hit["id"] for hit in self.out["results"][index]]


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
    filters_only: dict[tuple[str, str], int]
    wintergreen: int
    lookups: dict[str, tuple[int, str]]
    missing_words: list[str]
    parts: dict[str, tuple[int, set[str]]]
    full: dict[str, int]

    @classmethod
    def plan(cls, items: list[Content]) -> None:
        labels = ps.reaction_labels(cls.sandbox.app)
        cls.cas = cls.ask("50-78-2")
        cls.filters_only = {}
        for key, values in cls.filter_values(items, labels).items():
            for value in values:
                cls.filters_only[(key, value)] = cls.ask(
                    None, {key: value}, normalise=False)
        cls.wintergreen = cls.ask("wintergreen")
        words, cls.missing_words = body_words(cls.sandbox)
        cls.lookups = {}
        for item in items:
            product = item.product
            wanted = [("name", product.get("name")),
                      ("cas", product.get("cas")), ("id", item.id),
                      ("word", words.get(item.id))]
            wanted += [(f"tag {tag}", tag) for tag in item.tags]
            for kind, term in wanted:
                if term:
                    cls.lookups[f"{item.id} {kind}: {term}"] = (
                        cls.ask(term), item.id)
        cls.parts = {}
        for item in items:
            for part in substrings(item.product["smiles"]):
                if part not in cls.parts:
                    cls.parts[part] = (cls.ask(part), set())
                cls.parts[part][1].add(item.id)
        cls.full = {item.id: cls.ask(item.product["smiles"])
                    for item in items}

    @staticmethod
    def filter_values(items: list[Content],
                      labels: dict[str, str]) -> dict[str, set[str]]:
        return {
            "author": {a for i in items for a in i.data["authors"]},
            "reaction type": {labels[s] for i in items
                              for s in i.data["reaction_types"]},
            "status": {i.data["status"] for i in items},
            "tag": {t for i in items for t in i.tags}}

    def test_cas_numbers_are_separate_words(self) -> None:
        """Scenario: CAS numbers are separate words."""
        self.assertEqual(self.ids(self.cas), ["OSDB-0002"])

    def test_filter_values_and_filter_only_searches(self) -> None:
        """Scenario: Filter values and filter-only searches."""
        items = self.content()
        labels = ps.reaction_labels(self.sandbox.app)
        self.assertEqual(
            {k: set(v) for k, v in self.out["filters"].items()},
            self.filter_values(items, labels))
        carrying = {
            "author": lambda i, v: v in i.data["authors"],
            "reaction type": lambda i, v: v in [
                labels[s] for s in i.data["reaction_types"]],
            "status": lambda i, v: v == i.data["status"],
            "tag": lambda i, v: v in i.tags}
        for (key, value), index in self.filters_only.items():
            with self.subTest(filter=key, value=value):
                self.assertEqual(
                    sorted(self.ids(index)),
                    sorted(i.id for i in items if carrying[key](i, value)))

    def test_result_data_has_the_id_and_title(self) -> None:
        """Scenario: Result data."""
        hits = self.out["results"][self.wintergreen]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["meta"].get("id"), "OSDB-0001")
        self.assertEqual(hits[0]["meta"].get("title"), "Salicylic acid")

    def test_name_cas_tag_id_and_body_word_find_the_procedure(self) -> None:
        """Scenario: Name, CAS, tag, ID and body word."""
        self.assertEqual(self.missing_words, [],
                         "procedures without a unique Procedure word")
        self.assertTrue(self.lookups)
        for label, (index, ident) in self.lookups.items():
            with self.subTest(search=label):
                self.assertIn(ident, self.ids(index))

    def test_every_smiles_substring_finds_its_procedure(self) -> None:
        """Scenario: Every SMILES substring."""
        self.assertTrue(self.parts)
        failures = [f"{part!r} lacks {sorted(wanted - set(self.ids(i)))}"
                    for part, (i, wanted) in sorted(self.parts.items())
                    if wanted - set(self.ids(i))]
        self.assertEqual(failures, [])

    def test_a_full_smiles_finds_exactly_the_containing_ones(self) -> None:
        """Scenario: Full SMILES is exact."""
        items = self.content()
        for item in items:
            key = ps.smiles_key(item.product["smiles"])
            expected = sorted(
                other.id for other in items
                if key in ps.smiles_key(other.product["smiles"]))
            with self.subTest(procedure=item.id):
                self.assertEqual(sorted(self.ids(self.full[item.id])),
                                 expected)
