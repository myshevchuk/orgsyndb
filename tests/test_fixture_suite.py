"""The fixture suite itself (procedure-validation, "Fixture suite")."""

import re
import tempfile
import tomllib
import unittest
from pathlib import Path

from pipeline_support import TEST_COLLECTION, org_scope_rows
from support import (FIXTURES, REGISTRY, SETTINGS, SETTINGS_DIR, STATIC_DIR,
                     ValidatorTestCase, fixture_run, load_snapshot,
                     run_validator, snapshot_digest, valid_set_run,
                     with_fixture_substances, write_snapshot)

OPTIONAL_TOP = ["substrates", "checked_by", "references", "ai_model",
                "description", "weight"]

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


def named_keys(path) -> set[str]:
    """The compound keys a Markdown or Org fixture names, as products
    or as substrates, at the top level or in the entries of its scope."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".org":
        keys = set(re.findall(r'\(compound \. "([^"]*)"\)', text))
        for line in re.findall(r"^#\+HUGO_CUSTOM_FRONT_MATTER:.*:substrates"
                               r" '\(([^)]*)\)", text, re.M):
            keys |= set(re.findall(r'"([^"]*)"', line))
        for row in org_scope_rows(text):
            keys |= set(row.get("products", "").split())
            keys |= set(row.get("substrates", "").split())
        return keys
    front = tomllib.loads(text.split("+++\n")[1])
    keys = {entry["compound"] for entry in front.get("products", [])}
    keys |= set(front.get("substrates", []))
    for entry in front.get("scope", []):
        keys |= {product["compound"] for product in entry["products"]}
        keys |= set(entry["substrates"])
    return keys


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
        keys = sorted({key for path in
                       (FIXTURES / "catalogue").glob("OSDB-*.md")
                       for key in named_keys(path)})
        table = load_snapshot(TEST_COLLECTION / "registry.json")
        with_fixture_substances(table, *keys)
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            write_snapshot(registry, table)
            self.assert_clean(run_validator([
                "--settings", SETTINGS, "--static-dir", STATIC_DIR,
                "--registry", registry, FIXTURES / "catalogue"]))

    def test_the_fixtures_cover_what_they_are_for(self) -> None:
        """Harness: statuses, authors, tags, a missing CAS number, a
        timestamp tie, number and case titles, no structure image."""
        docs = self.documents()
        self.assertEqual({d["status"] for d in docs},
                         {"draft", "checked", "retired"})
        checked = [d for d in docs if d["status"] == "checked"]
        self.assertTrue(all(d.get("checked_by") for d in checked))
        authors = {a for d in docs for a in d["authors"]}
        self.assertIn("ae.mueller", authors)
        self.assertIn("a.example", authors)
        self.assertTrue(any(len(d["authors"]) > 1 for d in docs))
        self.assertTrue(any(len(d["tags"]) > 2 for d in docs))
        self.assertEqual(
            {len(d["reaction_types"]) for d in docs}, {1})
        registry = {entry["key"]: entry
                    for entry in load_snapshot(REGISTRY)["substances"]}
        self.assertEqual(
            [d["id"] for d in docs
             if registry[d["products"][0]["compound"]]["cas"] is None],
            ["OSDB-0922"])
        for d in docs:
            key = d["products"][0]["compound"]
            for suffix in (".svg", ".png"):
                self.assertFalse(
                    (STATIC_DIR / "structures" / f"{key}{suffix}").exists(),
                    key)
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
    """The fixture registry, tests/fixtures/registry.json."""

    def named(self) -> set[str]:
        named: set[str] = set()
        for path in sorted(FIXTURES.rglob("*")):
            rel = path.relative_to(FIXTURES).as_posix()
            if (path.suffix in (".md", ".org") and path.is_file()
                    and not rel.startswith(("invalid/", "collection/"))):
                named |= named_keys(path)
        return named

    def test_registry_validates(self) -> None:
        """Harness: the fixture registry is a snapshot the validator
        accepts."""
        result = run_validator([
            "--settings", SETTINGS, "--static-dir", STATIC_DIR,
            "--registry", REGISTRY, FIXTURES / "valid" / "md"])
        self.assert_clean(result)

    def test_registry_is_a_snapshot_with_its_digest(self) -> None:
        """Requirement: Fixture suite (the fixture registry, a
        snapshot)."""
        table = load_snapshot(REGISTRY)
        self.assertEqual(
            list(table), ["format", "vocabularies", "substances",
                          "accounts", "digest"])
        self.assertEqual(table["format"], 1)
        self.assertEqual(table["digest"], snapshot_digest(table))
        self.assertEqual(
            list(table["vocabularies"]),
            ["chemical-classes", "inventory-groups", "projects",
             "reaction-types"])
        keys = [entry["key"] for entry in table["substances"]]
        self.assertEqual(keys, sorted(keys))

    def test_registry_lists_the_accounts_the_fixtures_name(self) -> None:
        """Requirement: Fixture suite (the fixture registry lists an
        account for every author a committed fixture names, by user name
        `<initial>.example` with the name `<Initial>. Example`)."""
        named: set[str] = set()
        for path in sorted(FIXTURES.rglob("*")):
            if (path.suffix not in (".md", ".org")
                    or "collection" in path.relative_to(FIXTURES).parts):
                continue
            text = path.read_text(encoding="utf-8")
            for found in re.findall(
                    r"(?m)^authors = \[([^\]]*)\]|:authors '\(([^)]*)\)",
                    text):
                named.update(re.findall(r'"([^"]*)"', "".join(found)))
        self.assertTrue(named)
        accounts = {a["username"]: a["name"]
                    for a in load_snapshot(REGISTRY)["accounts"]}
        self.assertLessEqual(named, set(accounts))
        self.assertEqual(accounts["a.example"], "A. Example")
        self.assertEqual(accounts["ae.mueller"], "Ä. Müller")
        users = [a["username"] for a in load_snapshot(REGISTRY)["accounts"]]
        self.assertEqual(users, sorted(users))

    def test_registry_holds_the_named_compounds_and_no_others(self) -> None:
        """Requirement: Fixture suite (a substance for every compound key
        a committed fixture names)."""
        named = self.named()
        self.assertTrue({"ethyl-acetate", "ethanol"} <= named)
        self.assertEqual(
            {entry["key"] for entry in load_snapshot(REGISTRY)[
                "substances"]}, named)

    def test_every_substance_is_a_reagent_and_organic(self) -> None:
        """Requirement: Fixture suite (the group `reagents`, the class
        `organic-compounds`, no article number, no short name)."""
        table = load_snapshot(REGISTRY)
        for entry in table["substances"]:
            with self.subTest(key=entry["key"]):
                self.assertEqual(entry["group"], "reagents")
                self.assertEqual(entry["chemical_classes"],
                                 ["organic-compounds"])
                self.assertIsNone(entry["article_number"])
                self.assertIsNone(entry["short_name"])
        vocabularies = table["vocabularies"]
        self.assertEqual(
            [(t["key"], t["label"]) for t in
             vocabularies["chemical-classes"]],
            [("organic-compounds", "Organic compounds")])
        self.assertEqual(
            [(t["key"], t["label"]) for t in
             vocabularies["inventory-groups"]],
            [("reagents", "Reagents")])

    def test_registry_holds_the_stated_vocabularies(self) -> None:
        """Requirement: Fixture suite (the reaction types and the
        projects)."""
        vocabularies = load_snapshot(REGISTRY)["vocabularies"]
        self.assertEqual(
            {t["key"]: t["label"] for t in vocabularies["reaction-types"]},
            {"esterification": "Esterification",
             "reduction": "Reduction"})
        self.assertEqual(
            {t["key"]: (t["label"], t["label_de"], t["parent"])
             for t in vocabularies["projects"]},
            {"teaching": ("Teaching", "Lehre", None),
             "first-year-practical": ("First-year practical",
                                      "Grundpraktikum", "teaching"),
             "research": ("Research", "Forschung", None)})

    def test_the_substances_keep_the_values_of_the_former_files(
            self) -> None:
        """Requirement: Fixture suite (made from the former compound
        files)."""
        held = {entry["key"]: entry
                for entry in load_snapshot(REGISTRY)["substances"]}
        ethyl = held["ethyl-acetate"]
        self.assertEqual(
            (ethyl["name"], ethyl["name_de"], ethyl["formula"],
             ethyl["mw"], ethyl["smiles"], ethyl["cas"]),
            ("Ethyl acetate", "Ethylacetat", "C4H8O2", 88.11, "CCOC(C)=O",
             "141-78-6"))
        self.assertEqual(held["salicylic-acid"]["name_de"], "Salicylsäure")
        self.assertIsNone(held["10-undecenoic-acid"]["cas"])
        self.assertIsNone(held["benzyl-ethanoate"]["name_de"])
        self.assertEqual(held["benzyl-ethanoate"]["smiles"],
                         held["benzyl-acetate"]["smiles"])

    def test_the_static_files_hold_the_ethyl_acetate_structure(
            self) -> None:
        """Requirement: Fixture suite (static/structures/
        ethyl-acetate.svg)."""
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


class FixtureSettingsTests(unittest.TestCase):
    def test_the_fixture_settings_match_their_description(self) -> None:
        """Scenario: The fixture settings match their description."""
        self.assertEqual(
            tomllib.loads(SETTINGS.read_text(encoding="utf-8")),
            {"format": 1})
        self.assertEqual(
            sorted(p.name for p in SETTINGS_DIR.iterdir()),
            ["orgsyndb.toml"])
        self.assertEqual(
            {t["key"]: t["label"] for t in load_snapshot(REGISTRY)[
                "vocabularies"]["reaction-types"]},
            {"esterification": "Esterification",
             "reduction": "Reduction"})
        for name in ("compounds", "fields"):
            with self.subTest(name=name):
                self.assertFalse((FIXTURES / name).exists())
        for name in ("reaction_types.toml", "bad-vocabulary.toml"):
            with self.subTest(name=name):
                self.assertFalse((FIXTURES / name).exists())

    def test_no_fixture_directory_keeps_a_vocabulary_file(self) -> None:
        """Requirement: Fixture suite (the vocabularies are the fixture
        registry's)."""
        found = [p.relative_to(FIXTURES).as_posix()
                 for p in FIXTURES.rglob("vocabularies")
                 if "collection/build" not in p.as_posix()]
        self.assertEqual(found, [])


class FixtureHygieneTests(unittest.TestCase):
    def test_committed_ids_are_unique_apart_from_the_duplicate_case(
            self) -> None:
        """Scenario: Committed IDs are unique."""
        seen: dict[str, str] = {}
        for path in sorted(FIXTURES.rglob("*.md")):
            rel = path.relative_to(FIXTURES).as_posix()
            if rel.startswith(("invalid/duplicate-id/", "collection/")):
                continue
            match = re.search(r'^id = "((?:OSDB|SEQ)-[^"]*)"', path.read_text(
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
