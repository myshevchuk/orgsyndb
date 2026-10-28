"""The fixture suite itself (procedure-validation, "Fixture suite")."""

import re
import tomllib
import unittest

from support import (FIXTURES, REPO, STATIC_DIR, ValidatorTestCase,
                     fixture_run, run_validator, valid_set_run)

OPTIONAL_TOP = ["precursors", "structure_image", "checked_by", "references",
                "ai_model"]

# case directory -> (field, message substring), from each case's scenario
INVALID_CASES = {
    "invalid-toml": ("front_matter", "invalid TOML"),
    "bad-id-format": ("id", "must match OSDB-NNNN"),
    "file-name-id-mismatch": ("file_name", "does not match id OSDB-0199"),
    "slug-mismatch": ("slug", 'must be "osdb-0107" (the lowercased id)'),
    "missing-title": ("title", "required field missing"),
    "unknown-reaction-type": (
        "reaction_types", 'unknown reaction type "esterfication"'),
    "yield-out-of-range": ("yield_percent", "must be between 0 and 100"),
    "date-as-string": ("date", "must be a TOML offset datetime"),
    "missing-precursor": ("precursors", "OSDB-0999 not found"),
    "missing-structure-image": ("structure_image", "not found"),
    "author-key": ("author", "use authors"),
    "subdirectory": ("file_name", "subdirectories are not supported"),
}


def load_front_matter(path):
    text = path.read_text(encoding="utf-8")
    return tomllib.loads(text.split("+++\n")[1])


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
        self.assertTrue(any("cas" in d["product"] for d in docs))
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
            "--static-dir", STATIC_DIR, FIXTURES / "catalogue"]))

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
        self.assertEqual(
            [d["id"] for d in docs if "cas" not in d["product"]],
            ["OSDB-0922"])
        self.assertFalse(any("structure_image" in d for d in docs))
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
