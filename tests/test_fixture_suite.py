"""The fixture suite itself (procedure-validation, "Fixture suite")."""

import re
import tomllib
import unittest

from support import FIXTURES, ValidatorTestCase, fixture_run, valid_set_run

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
        """Requirement: Fixture suite (unique IDs, fictitious names)."""
        seen: dict[str, str] = {}
        for path in sorted(FIXTURES.rglob("*.md")):
            rel = path.relative_to(FIXTURES).as_posix()
            if rel.startswith("invalid/duplicate-id/"):
                continue
            match = re.search(r'^id = "(OSDB-[^"]*)"', path.read_text(
                encoding="utf-8"), re.M)
            if match is None:
                continue
            self.assertNotIn(match.group(1), seen,
                             f"{rel} repeats {seen.get(match.group(1))}")
            seen[match.group(1)] = rel

    def test_fixtures_carry_no_machine_or_user_identifiers(self) -> None:
        """Requirement: Fixture suite (no user or machine identifier)."""
        pattern = re.compile(r"/home/|@[\w.-]+\.\w+|\.local\b|\.lan\b")
        for path in sorted(FIXTURES.rglob("*")):
            if path.is_file():
                with self.subTest(path=path.name):
                    self.assertIsNone(pattern.search(
                        path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
