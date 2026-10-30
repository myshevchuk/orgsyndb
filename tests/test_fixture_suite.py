"""The fixture suite itself (procedure-validation, "Fixture suite")."""

import re
import tomllib
import unittest

from support import (COMPOUNDS, FIXTURES, REPO, STATIC_DIR,
                     ValidatorTestCase, fixture_run, run_validator,
                     valid_set_run)

OPTIONAL_TOP = ["substrates", "checked_by", "references", "ai_model",
                "description", "weight"]
OPTIONAL_COMPOUND = ["name_de", "cas", "structure_image"]

# case directory -> (field, message substring), from each case's scenario
INVALID_CASES = {
    "invalid-toml": ("front_matter", "invalid TOML"),
    "bad-id-format": ("id", "must match OSDB-NNNN"),
    "file-name-id-mismatch": ("file_name", "does not match id OSDB-0199"),
    "slug-mismatch": ("slug", 'must be "osdb-0107" (the lowercased id)'),
    "missing-title": ("title", "required field missing"),
    "unknown-reaction-type": (
        "reaction_types", 'unknown reaction type "esterfication"'),
    "yield-out-of-range": ("products[1].yield_percent",
                           "must be between 0 and 100"),
    "date-as-string": ("date", "must be a TOML offset datetime"),
    "unknown-compound": ("products[1].compound",
                         'unknown compound "no-such-compound"'),
    "unknown-substrate": ("substrates",
                          'unknown compound "no-such-compound"'),
    "author-key": ("author", "use authors"),
    "subdirectory": ("file_name", "subdirectories are not supported"),
}


def load_front_matter(path):
    text = path.read_text(encoding="utf-8")
    return tomllib.loads(text.split("+++\n")[1])


def load_compound(path):
    return tomllib.loads(path.read_text(encoding="utf-8"))


def named_keys(path) -> set[str]:
    """The compound keys a Markdown or Org fixture names, as products
    or as substrates."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".org":
        keys = set(re.findall(r'\(compound \. "([^"]*)"\)', text))
        for line in re.findall(r"^#\+HUGO_CUSTOM_FRONT_MATTER:.*:substrates"
                               r" '\(([^)]*)\)", text, re.M):
            keys |= set(re.findall(r'"([^"]*)"', line))
        return keys
    front = tomllib.loads(text.split("+++\n")[1])
    keys = {entry["compound"] for entry in front["products"]}
    return keys | set(front.get("substrates", []))


class ValidSetTests(ValidatorTestCase):
    def test_valid_set_passes_cleanly(self) -> None:
        """Scenario: Valid set passes cleanly (run)."""
        self.assert_clean(valid_set_run())

    def test_valid_set_covers_every_optional_field_and_offset(self) -> None:
        """Scenario: Valid set passes cleanly (coverage of the set)."""
        docs = [load_front_matter(p)
                for d in ("md", "export")
                for p in (FIXTURES / "valid" / d).glob("*.md")]
        seen = set().union(*docs)
        for key in OPTIONAL_TOP:
            self.assertIn(key, seen)
        self.assertTrue(any(len(d["products"]) == 2 for d in docs))
        compounds = [load_compound(p) for p in COMPOUNDS.glob("*.toml")]
        for key in OPTIONAL_COMPOUND:
            self.assertTrue(any(key in c for c in compounds), key)
        offsets = {d["date"].utcoffset().total_seconds() for d in docs}
        self.assertIn(3600, offsets)
        self.assertIn(7200, offsets)
        org_text = "".join(
            p.read_text(encoding="utf-8")
            for p in (FIXTURES / "valid" / "org").glob("*.org"))
        self.assertIn("[2026-10-25 Sun 02:", org_text)


class BaselineTests(ValidatorTestCase):
    def test_baseline_is_valid(self) -> None:
        """Scenario: Baseline is valid."""
        self.assert_clean(fixture_run("baseline"))


class CatalogueFixtureTests(ValidatorTestCase):
    """The catalogue fixtures, tests/fixtures/catalogue/."""

    def documents(self) -> list[dict]:
        paths = sorted((FIXTURES / "catalogue").glob("OSDB-*.md"))
        self.assertGreaterEqual(len(paths), 6)
        return [load_front_matter(path) for path in paths]

    def test_the_fixtures_validate(self) -> None:
        """Harness: the catalogue fixtures validate cleanly."""
        self.assert_clean(run_validator([
            "--vocabulary", REPO / "site" / "data" / "reaction_types.toml",
            "--static-dir", STATIC_DIR, "--compounds", COMPOUNDS,
            FIXTURES / "catalogue"]))

    def test_the_fixtures_cover_what_they_are_for(self) -> None:
        """Harness: statuses, authors, tags, a missing CAS number, a
        timestamp tie, number and case titles, no structure image."""
        docs = self.documents()
        self.assertEqual({d["status"] for d in docs},
                         {"draft", "checked", "retired"})
        checked = [d for d in docs if d["status"] == "checked"]
        self.assertTrue(all(d.get("checked_by") for d in checked))
        authors = {a for d in docs for a in d["authors"]}
        self.assertIn("Ä. Müller", authors)
        self.assertIn("A. Example", authors)
        self.assertTrue(any(len(d["authors"]) > 1 for d in docs))
        self.assertTrue(any(len(d["tags"]) > 2 for d in docs))
        self.assertEqual(
            {len(d["reaction_types"]) for d in docs}, {1})
        registry = {key: load_compound(COMPOUNDS / f"{key}.toml")
                    for d in docs for key in [d["products"][0]["compound"]]}
        self.assertEqual(
            [d["id"] for d in docs
             if "cas" not in registry[d["products"][0]["compound"]]],
            ["OSDB-0922"])
        self.assertFalse(any("structure_image" in c
                             for c in registry.values()))
        ties = {}
        for d in docs:
            ties.setdefault(d["lastmod"].timestamp(), []).append(d)
        tied = [group for group in ties.values() if len(group) == 2]
        self.assertEqual(len(tied), 1)
        newest = max(d["lastmod"] for d in docs)
        collection = FIXTURES / "collection" / "md" / "procedures"
        shipped = [load_front_matter(p) for p in collection.glob("*.md")]
        self.assertGreater(tied[0][0]["lastmod"],
                           max(d["lastmod"] for d in shipped))
        self.assertEqual(tied[0][0]["lastmod"], newest)
        titles = {d["title"] for d in docs}
        self.assertTrue({"4-Methylbenzoic acid",
                         "10-Undecenoic acid"} <= titles)
        lowered = [t for t in titles if t.islower()]
        self.assertTrue(any(t.capitalize() in titles for t in lowered))


class CommittedInvalidFixtureTests(ValidatorTestCase):
    def test_each_committed_invalid_fixture_fails_for_one_reason(
            self) -> None:
        """Scenario: Each committed invalid fixture fails for one reason."""
        found = {p.name for p in (FIXTURES / "invalid").iterdir()
                 if p.is_dir() and p.name != "duplicate-id"}
        self.assertGreaterEqual(len(found), 5)
        self.assertEqual(found, set(INVALID_CASES))
        for case, (field, text) in INVALID_CASES.items():
            with self.subTest(case=case):
                result = fixture_run(f"invalid/{case}")
                self.assert_one(result, "error", field, text)


class DependentCheckTests(ValidatorTestCase):
    def test_malformed_id_does_not_cascade(self) -> None:
        """Scenario: Malformed ID does not cascade."""
        result = fixture_run("invalid/bad-id-format")
        self.assertEqual(len(result.stdout.splitlines()), 1, result.stdout)
        self.assertEqual(len(result.problems), 1, result.stdout)
        self.assertEqual(result.problems[0].field, "id")
        self.assertNotIn(":slug:", result.stdout)
        self.assertNotIn(":file_name:", result.stdout)


class FixtureRegistryTests(ValidatorTestCase):
    """The fixture registry, tests/fixtures/compounds/."""

    def test_registry_validates(self) -> None:
        """Harness: the fixture registry is valid."""
        result = run_validator([
            "--vocabulary", FIXTURES / "reaction_types.toml",
            "--static-dir", STATIC_DIR, "--compounds", COMPOUNDS,
            FIXTURES / "valid" / "md"])
        self.assert_clean(result)

    def test_registry_holds_the_named_compounds_and_no_others(self) -> None:
        """Requirement: Fixture suite (the committed registry)."""
        named: set[str] = set()
        for path in sorted(FIXTURES.rglob("*")):
            rel = path.relative_to(FIXTURES).as_posix()
            if (path.suffix in (".md", ".org") and path.is_file()
                    and not rel.startswith(("invalid/", "collection/"))):
                named |= named_keys(path)
        self.assertTrue({"ethyl-acetate", "ethanol"} <= named)
        self.assertEqual({p.stem for p in COMPOUNDS.glob("*.toml")}, named)
        self.assertEqual({p.name for p in COMPOUNDS.iterdir()},
                         {f"{key}.toml" for key in named})

    def test_ethyl_acetate_sets_every_optional_key(self) -> None:
        """Requirement: Fixture suite (ethyl-acetate)."""
        data = load_compound(COMPOUNDS / "ethyl-acetate.toml")
        for key in OPTIONAL_COMPOUND:
            self.assertIn(key, data)
        self.assertEqual(data["structure_image"],
                         "structures/ethyl-acetate.svg")
        self.assertTrue((STATIC_DIR / "structures"
                         / "ethyl-acetate.svg").is_file())

    def test_committed_procedures_use_the_new_fields(self) -> None:
        """Harness: no committed fixture keeps an old procedure field."""
        old_md = re.compile(r"^(\[product\]|product\s*=|yield_percent\s*=|"
                            r"precursors\s*=|structure_image\s*=)")
        old_org = re.compile(r":(product|yield_percent|precursors|"
                             r"structure_image)\s")
        checked = 0
        for path in sorted(FIXTURES.rglob("*")):
            if path.suffix == ".md" and path.is_file():
                head = path.read_text(encoding="utf-8").split("+++")[1]
                bad = [ln for ln in head.splitlines() if old_md.match(ln)]
            elif path.suffix == ".org" and path.is_file():
                bad = [ln for ln in path.read_text(encoding="utf-8")
                       .splitlines()
                       if ln.startswith("#+HUGO_CUSTOM_FRONT_MATTER:")
                       and old_org.search(ln)]
            else:
                continue
            checked += 1
            with self.subTest(path=path.relative_to(FIXTURES).as_posix()):
                self.assertEqual(bad, [])
        self.assertGreater(checked, 50)


class FixtureHygieneTests(unittest.TestCase):
    def test_committed_ids_are_unique_apart_from_the_duplicate_case(
            self) -> None:
        """Scenario: Committed IDs are unique."""
        seen: dict[str, str] = {}
        for path in sorted(FIXTURES.rglob("*.md")):
            rel = path.relative_to(FIXTURES).as_posix()
            if rel.startswith(("invalid/duplicate-id/", "collection/")):
                continue
            match = re.search(r'^id = "(OSDB-[^"]*)"', path.read_text(
                encoding="utf-8"), re.M)
            if match is None:
                continue
            self.assertNotIn(match.group(1), seen,
                             f"{rel} repeats {seen.get(match.group(1))}")
            seen[match.group(1)] = rel

    def test_fixtures_carry_no_machine_or_user_identifiers(self) -> None:
        """Scenario: Committed fixtures carry no identifiers."""
        pattern = re.compile(r"/home/|@[\w.-]+\.\w+|\.local\b|\.lan\b")
        generated = tuple(f"collection/{d}/"
                          for d in ("build", "public", "pdf"))
        for path in sorted(FIXTURES.rglob("*")):
            rel = path.relative_to(FIXTURES).as_posix()
            if path.is_file() and not rel.startswith(generated):
                with self.subTest(path=path.name):
                    self.assertIsNone(pattern.search(
                        path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
