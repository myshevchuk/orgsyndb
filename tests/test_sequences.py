"""Synthesis sequences in the validator (synthesis-sequences "Sequence
files", "Sequence fields" and "Sequence continuity", procedure-validation
"Command-line interface", "Default paths resolve from the script
location", "Problem report format" and "Fixture suite").

The sequence fixtures are tests/fixtures/sequences/ (the baseline
``SEQ-0001-baseline.md`` and ``SEQ-0002-general-entry.md``, whose first
step names entry 2 of the general baseline), the procedures they chain in
tests/fixtures/sequences-procedures/ and the fixtures of
tests/fixtures/sequences-invalid/.
"""

import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from support import (COMPOUNDS, FIXTURES, SEQUENCE_BASELINE, SEQUENCES,
                     STATIC_DIR, VOCABULARY, ValidatorTestCase, add_file,
                     add_sequence, changes, edit_sequence, fixture_run,
                     insert_line, remove_line, remove_sequence,
                     replace_line, replace_text, run_validator,
                     sequence_fixture_run, sequence_variant_run)

COMPOUND_FILES = len(list(COMPOUNDS.glob("*.toml")))
BASELINE = "SEQ-0001-baseline.md"
GENERAL = "SEQ-0002-general-entry.md"
STEP_1 = '{ procedure = "OSDB-0002" }'
STEP_2 = '{ procedure = "OSDB-0160" }'
GENERAL_STEP = '{ procedure = "OSDB-0140", entry = 2 }'
SWAPPED = replace_line("steps", f"steps = [{STEP_2}, {STEP_1}]")
GERMAN_TITLE = replace_line("title", 'title = "Benzylacetat aus Propylacetat"')
GERMAN_NOTES = replace_text(
    "## Notes\n\nA short fictitious sequence used as test data.\n",
    "## Anmerkungen\n\nEine kurze erfundene Sequenz als Testdaten.\n")
GERMAN = (GERMAN_TITLE, GERMAN_NOTES)


def front_matter(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8").split("+++\n")[1])


def baseline_run(*edits, rename: str | None = None):
    """Sequence variant run on the sequence baseline."""
    return sequence_variant_run(edit_sequence(BASELINE, *edits,
                                              rename=rename))


def general_run(*edits):
    """Sequence variant run on the sequence with a general step."""
    return sequence_variant_run(edit_sequence(GENERAL, *edits))


def valid_run():
    return sequence_fixture_run("valid/md", "sequences-procedures",
                                sequences="sequences")


class SequenceFixtureTests(ValidatorTestCase):
    def test_valid_sequences(self) -> None:
        """Scenario: Valid sequences."""
        self.assert_clean(valid_run())

    def test_the_procedures_the_sequences_chain_are_valid(self) -> None:
        """Harness: the fixtures of sequences-procedures validate."""
        self.assert_clean(fixture_run("sequences-procedures"))

    def test_the_fixtures_have_the_shape_the_specification_gives(
            self) -> None:
        """Harness: the baseline has two steps and no authors, another
        sequence names entry 2 of the general baseline."""
        baseline = front_matter(SEQUENCE_BASELINE)
        self.assertEqual(baseline["id"], "SEQ-0001")
        self.assertEqual(len(baseline["steps"]), 2)
        self.assertNotIn("authors", baseline)
        found = [step for path in sorted(SEQUENCES.glob("SEQ-*.md"))
                 for step in front_matter(path)["steps"]
                 if step.get("procedure") == "OSDB-0140"]
        self.assertTrue(any(step.get("entry") == 2 for step in found))
        for path in sorted(SEQUENCES.glob("SEQ-*.md")):
            self.assertNotIn("authors", front_matter(path), path.name)

    def test_the_mismatch_fixture_names_another_id(self) -> None:
        """Harness: SEQ-0002-mismatch.md carries the ID SEQ-0003."""
        path = (FIXTURES / "sequences-invalid" / "file-name"
                / "SEQ-0002-mismatch.md")
        self.assertEqual(front_matter(path)["id"], "SEQ-0003")
        self.assertEqual(front_matter(path)["slug"], "seq-0003")

    def test_sequence_files_are_counted_in_the_summary(self) -> None:
        """Requirement: Problem report format (the summary counts)."""
        count = (COMPOUND_FILES
                 + len(list((FIXTURES / "valid" / "md").glob("*.md")))
                 + len(list((FIXTURES / "sequences-procedures")
                            .glob("*.md")))
                 + len(list((FIXTURES / "general").glob("*.md")))
                 + len(list(SEQUENCES.glob("*.md"))))
        result = valid_run()
        self.assertIn(f"validated {count} files: 0 errors, 0 warnings",
                      result.stderr)

    def test_a_variant_is_counted_as_a_file(self) -> None:
        """Requirement: Problem report format (the summary counts
        variants)."""
        before = valid_run()
        result = sequence_variant_run(add_sequence(
            "SEQ-0001-baseline.de.md", *GERMAN))
        counted = int(re.search(r"validated (\d+) files", before.stderr)
                      .group(1))
        self.assertIn(f"validated {counted + 1} files: 0 errors, "
                      "0 warnings", result.stderr)


class FileNameTests(ValidatorTestCase):
    def test_file_named_after_another_id(self) -> None:
        """Scenario: Sequence file named after another ID."""
        result = sequence_fixture_run(
            "valid/md", sequences="sequences-invalid/file-name")
        self.assert_one(result, "error", "file_name",
                        "does not match id SEQ-0003",
                        path_suffix="SEQ-0002-mismatch.md")

    def test_names_that_break_the_rule(self) -> None:
        """Requirement: Sequence files (the name rule)."""
        for name in ("seq-0001-lowercase.md", "SEQ-0001-Bad_Slug.md",
                     "SEQ-0001.md", "SEQ-001-short.md",
                     "OSDB-0001-baseline.md"):
            with self.subTest(name=name):
                result = baseline_run(rename=name)
                self.assert_one(result, "error", "file_name",
                                "must be named SEQ-NNNN-short-slug.md",
                                path_suffix=name)

    def test_language_codes_in_file_names(self) -> None:
        """Requirement: Sequence files (language codes)."""
        for code in ("de", "en"):
            with self.subTest(code=code):
                self.assert_clean(baseline_run(
                    rename=f"SEQ-0001-baseline.{code}.md"))
        result = baseline_run(rename="SEQ-0001-baseline.fr.md")
        self.assert_one(result, "error", "file_name", "",
                        path_suffix="SEQ-0001-baseline.fr.md")

    def test_a_file_that_is_not_markdown_is_ignored_with_a_warning(
            self) -> None:
        """Requirement: Sequence files (a file of another name)."""
        result = sequence_variant_run(add_file("notes.txt", "notes\n"))
        self.assert_one(result, "warning", "file_name",
                        "not a sequence file; ignored",
                        path_suffix="notes.txt")

    def test_a_subdirectory_is_an_error(self) -> None:
        """Requirement: Sequence files (discovered as procedures are)."""
        text = SEQUENCE_BASELINE.read_text(encoding="utf-8")
        result = sequence_variant_run(add_file("nested/SEQ-0009-x.md", text))
        self.assert_one(result, "error", "file_name",
                        "subdirectories are not supported",
                        path_suffix="nested")

    def test_section_index_and_dotfiles_are_skipped(self) -> None:
        """Requirement: Sequence files (discovered as procedures are,
        skipped entries)."""
        before = valid_run()
        result = sequence_variant_run(changes(
            add_file("_index.md", "Section page, no front matter.\n"),
            add_file(".gitkeep", "")))
        self.assert_clean(result)
        self.assertEqual(result.stderr, before.stderr)


class OptionTests(ValidatorTestCase):
    ARGS = ["--vocabulary", "reaction_types.toml", "--static-dir", "static",
            "--compounds", "compounds"]

    def test_problems_carry_the_sequences_argument_as_given(self) -> None:
        """Requirement: Problem report format (the path of a sequence)."""
        result = run_validator(
            [*self.ARGS, "--sequences", "sequences-invalid/file-name",
             "valid/md", "general"], cwd=FIXTURES)
        self.assert_one(result, "error", "file_name",
                        "does not match id SEQ-0003")
        self.assertEqual(result.problems[0].path,
                         "sequences-invalid/file-name/SEQ-0002-mismatch.md")

    def test_the_default_is_md_sequences_of_the_working_directory(
            self) -> None:
        """Requirement: Default paths resolve from the script location
        (--sequences)."""
        source = (FIXTURES / "sequences-invalid" / "file-name"
                  / "SEQ-0002-mismatch.md")
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "md" / "sequences").mkdir(parents=True)
            shutil.copy2(source, cwd / "md" / "sequences")
            result = run_validator(
                ["--vocabulary", VOCABULARY, "--static-dir", STATIC_DIR,
                 "--compounds", COMPOUNDS, FIXTURES / "valid" / "md",
                 FIXTURES / "general"], cwd=cwd)
        self.assert_one(result, "error", "file_name",
                        "does not match id SEQ-0003",
                        path_suffix="md/sequences/SEQ-0002-mismatch.md")

    def test_a_missing_default_directory_holds_no_sequence(self) -> None:
        """Requirement: Default paths resolve from the script location
        (a missing directory)."""
        result = fixture_run("valid/md", "general")
        self.assert_clean(result)
        self.assertIn(f"validated {COMPOUND_FILES + 3} files",
                      result.stderr)

    def test_a_missing_named_directory_holds_no_sequence(self) -> None:
        """Requirement: Default paths resolve from the script location
        (--sequences names a missing directory)."""
        result = sequence_fixture_run(
            "valid/md", sequences="sequences-invalid/no-such-directory")
        self.assert_clean(result)
        self.assertIn(f"validated {COMPOUND_FILES + 3} files",
                      result.stderr)

    def test_a_step_resolves_against_the_roots_given(self) -> None:
        """Requirement: Command-line interface (--sequences checks every
        sequence against the procedures of the content roots)."""
        # OSDB-0160 lives in sequences-procedures, which is not a root.
        result = sequence_fixture_run("valid/md", sequences="sequences")
        self.assertEqual(result.returncode, 1, result.stdout)
        found = {(p.field, p.severity) for p in result.problems}
        self.assertEqual(found, {("steps[2].procedure", "error")},
                         result.stdout)
        self.assertIn("OSDB-0160 not found", result.problems[0].message)
        self.assertTrue(result.problems[0].path.endswith(BASELINE))


class FieldTests(ValidatorTestCase):
    def test_a_malformed_id(self) -> None:
        """Requirement: Sequence fields (id)."""
        for value in ("SEQ-1", "SEQ-00001", "seq-0001", "OSDB-0001"):
            with self.subTest(value=value):
                result = baseline_run(replace_line("id", f'id = "{value}"'))
                self.assert_one(result, "error", "id",
                                "must match SEQ-NNNN",
                                path_suffix=BASELINE)

    def test_the_placeholder_id_is_rejected(self) -> None:
        """Requirement: Sequence fields (id, four digits from 0001)."""
        result = baseline_run(
            replace_line("id", 'id = "SEQ-0000"'),
            replace_line("slug", 'slug = "seq-0000"'),
            rename="SEQ-0000-placeholder.md")
        self.assert_one(result, "error", "id", "SEQ-")

    def test_a_slug_that_is_not_the_lowercased_id(self) -> None:
        """Requirement: Sequence fields (slug)."""
        result = baseline_run(replace_line("slug", 'slug = "seq-0009"'))
        self.assert_one(result, "error", "slug",
                        'must be "seq-0001" (the lowercased id)')

    def test_a_missing_required_field(self) -> None:
        """Requirement: Sequence fields (a missing key)."""
        for key in ("slug", "title", "date", "lastmod", "target", "steps"):
            with self.subTest(key=key):
                result = baseline_run(remove_line(key))
                self.assert_one(result, "error", key,
                                "required field missing")

    def test_an_empty_title(self) -> None:
        """Requirement: Sequence fields (title, a non-empty string)."""
        result = baseline_run(replace_line("title", 'title = ""'))
        self.assert_one(result, "error", "title", "")

    def test_a_date_that_is_a_string(self) -> None:
        """Requirement: Sequence fields (dates, as for procedures)."""
        result = baseline_run(
            replace_line("date", 'date = "2026-07-01T10:15:00+02:00"'))
        self.assert_one(result, "error", "date",
                        "must be a TOML offset datetime")

    def test_lastmod_before_date(self) -> None:
        """Requirement: Sequence fields (lastmod not earlier than date)."""
        result = baseline_run(
            replace_line("lastmod", "lastmod = 2026-06-30T09:00:00+02:00"))
        self.assert_one(result, "error", "lastmod", "is earlier than date")

    def test_an_offset_that_is_not_berlins(self) -> None:
        """Requirement: Sequence fields (dates, the offset warning)."""
        result = baseline_run(
            replace_line("date", "date = 2026-07-01T10:15:00+01:00"))
        self.assert_one(result, "warning", "date",
                        "is not the Europe/Berlin offset")

    def test_an_unknown_key_is_a_warning(self) -> None:
        """Requirement: Sequence fields (any other key)."""
        result = baseline_run(insert_line('colour = "red"'))
        self.assert_one(result, "warning", "colour", "unknown field")

    def test_taxonomy_keys_are_errors(self) -> None:
        """Requirement: Sequence fields (the procedure taxonomy keys)."""
        for line, key in (('authors = ["A. Example"]', "authors"),
                          ('tags = ["sample-data"]', "tags"),
                          ('reaction_types = ["reduction"]',
                           "reaction_types")):
            with self.subTest(key=key):
                result = baseline_run(insert_line(line))
                self.assert_one(result, "error", key,
                                "a sequence joins no procedure taxonomy")

    def test_an_unknown_key_in_a_step_is_a_warning(self) -> None:
        """Requirement: Sequence fields (any other key in a step)."""
        result = baseline_run(replace_text(
            STEP_2, '{ procedure = "OSDB-0160", note = "x" }'))
        self.assert_one(result, "warning", "steps[2].note", "unknown field")

    def test_a_step_without_a_procedure(self) -> None:
        """Requirement: Sequence fields (a missing key in a step)."""
        result = baseline_run(replace_text(STEP_2, "{ }"))
        self.assert_one(result, "error", "steps[2].procedure",
                        "required field missing")

    def test_an_unknown_target(self) -> None:
        """Requirement: Sequence fields (target)."""
        result = baseline_run(
            replace_line("target", 'target = "no-such-compound"'))
        self.assert_one(result, "error", "target",
                        'unknown compound "no-such-compound"')

    def test_two_sequences_with_one_id(self) -> None:
        """Requirement: Sequence fields (a duplicate id)."""
        result = sequence_variant_run(add_sequence("SEQ-0001-copy.md"))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(sorted(p.field for p in result.problems),
                         ["id", "id"], result.stdout)
        for problem in result.problems:
            self.assertIn("duplicate id SEQ-0001", problem.message)
        by_name = {p.path.rsplit("/", 1)[-1]: p for p in result.problems}
        self.assertEqual(set(by_name), {BASELINE, "SEQ-0001-copy.md"})
        self.assertIn("SEQ-0001-copy.md", by_name[BASELINE].message)
        self.assertIn(BASELINE, by_name["SEQ-0001-copy.md"].message)


class StepTests(ValidatorTestCase):
    def test_a_step_of_an_unknown_procedure(self) -> None:
        """Scenario: Step of an unknown procedure."""
        result = baseline_run(replace_text(
            STEP_2, '{ procedure = "OSDB-0999" }'))
        self.assert_one(result, "error", "steps[2].procedure",
                        "OSDB-0999 not found")

    def test_the_first_step_of_an_unknown_procedure(self) -> None:
        """Requirement: Sequence continuity (a step that is not found is
        left out)."""
        result = baseline_run(replace_text(
            STEP_1, '{ procedure = "OSDB-0999" }'))
        self.assert_one(result, "error", "steps[1].procedure",
                        "OSDB-0999 not found in any content root")

    def test_a_general_procedure_without_an_entry(self) -> None:
        """Scenario: General procedure without an entry."""
        result = general_run(replace_text(GENERAL_STEP,
                                          '{ procedure = "OSDB-0140" }'))
        self.assert_one(result, "error", "steps[1].entry",
                        "OSDB-0140 is a general procedure; name one of "
                        "its entries 1 to 3")

    def test_an_entry_out_of_range(self) -> None:
        """Requirement: Sequence fields (entry, from 1 to the count)."""
        for value in (0, 4, -1):
            with self.subTest(entry=value):
                result = general_run(replace_text(
                    "entry = 2", f"entry = {value}"))
                self.assert_one(result, "error", "steps[1].entry",
                                "must be between 1 and 3")

    def test_an_entry_of_a_specific_procedure(self) -> None:
        """Requirement: Sequence fields (entry, refused for a specific
        procedure)."""
        result = baseline_run(replace_text(
            STEP_1, '{ procedure = "OSDB-0002", entry = 1 }'))
        self.assert_one(result, "error", "steps[1].entry",
                        "OSDB-0002 has no scope entries")

    def test_one_step_only(self) -> None:
        """Scenario: One step only."""
        result = baseline_run(replace_line("steps", f"steps = [{STEP_1}]"))
        self.assert_one(result, "error", "steps",
                        "must list at least two steps")

    def test_no_steps_at_all(self) -> None:
        """Requirement: Sequence fields (steps, at least two)."""
        result = baseline_run(replace_line("steps", "steps = []"))
        self.assert_one(result, "error", "steps",
                        "must list at least two steps")


class ContinuityTests(ValidatorTestCase):
    def test_broken_chain(self) -> None:
        """Scenario: Broken chain."""
        result = baseline_run(SWAPPED)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(len(result.problems), 2, result.stdout)
        by_field = {p.field: p for p in result.problems}
        self.assertEqual(set(by_field), {"steps[2]", "target"})
        self.assertEqual({p.severity for p in result.problems}, {"error"})
        self.assertIn("starts from none of the products of step 1",
                      by_field["steps[2]"].message)
        self.assertIn("is not a product of the last step",
                      by_field["target"].message)

    def test_the_target_must_be_a_product_of_the_last_step(self) -> None:
        """Requirement: Sequence continuity (the target)."""
        result = baseline_run(replace_line("target", 'target = "ethanol"'))
        self.assert_one(result, "error", "target",
                        "is not a product of the last step")

    def test_the_entry_decides_the_substrates_and_products(self) -> None:
        """Requirement: Sequence continuity (of its entry, for a general
        procedure)."""
        for value in (1, 3):
            with self.subTest(entry=value):
                result = general_run(replace_text(
                    "entry = 2", f"entry = {value}"))
                self.assert_one(result, "error", "steps[2]",
                                "starts from none of the products of "
                                "step 1")

    def test_any_product_of_a_step_may_carry_on(self) -> None:
        """Requirement: Sequence continuity (some product, not only the
        first)."""
        result = general_run(
            replace_line(
                "steps", 'steps = [{ procedure = "OSDB-0001" }, '
                '{ procedure = "OSDB-0140", entry = 3 }]'),
            replace_line("target", 'target = "methyl-benzoate"'))
        self.assert_clean(result)

    def test_three_steps_chain(self) -> None:
        """Requirement: Sequence continuity (each step after the
        first)."""
        result = general_run(
            replace_line("steps", f"steps = [{GENERAL_STEP}, {STEP_1}, "
                         f"{STEP_2}]"),
            replace_line("target", 'target = "benzyl-acetate"'))
        self.assert_clean(result)

    def test_a_break_after_the_second_step(self) -> None:
        """Requirement: Sequence continuity (the error names the step
        that does not continue)."""
        result = general_run(replace_line(
            "steps", f"steps = [{GENERAL_STEP}, {STEP_1}, {STEP_1}]"))
        self.assert_one(result, "error", "steps[3]",
                        "starts from none of the products of step 2")


class VariantTests(ValidatorTestCase):
    def test_a_german_variant_shares_its_steps(self) -> None:
        """Scenario: A German variant shares its steps."""
        german = add_sequence("SEQ-0001-baseline.de.md", *GERMAN)
        self.assert_clean(sequence_variant_run(german))
        result = sequence_variant_run(add_sequence(
            "SEQ-0001-baseline.de.md", *GERMAN,
            replace_line("target", 'target = "ethanol"')))
        problem = self.assert_one(result, "error", "target", BASELINE,
                                  path_suffix="SEQ-0001-baseline.de.md")
        self.assertIn("SEQ-0001-baseline.md", problem.message)

    def test_steps_must_agree(self) -> None:
        """Requirement: Sequence files (the same steps)."""
        result = sequence_variant_run(add_sequence(
            "SEQ-0001-baseline.de.md", *GERMAN, SWAPPED))
        self.assert_one(result, "error", "steps", BASELINE,
                        path_suffix="SEQ-0001-baseline.de.md")

    def test_title_dates_and_body_may_differ(self) -> None:
        """Requirement: Sequence files (title, dates and body may
        differ)."""
        result = sequence_variant_run(add_sequence(
            "SEQ-0001-baseline.en.md", GERMAN_TITLE, GERMAN_NOTES,
            replace_line("date", "date = 2026-07-02T10:15:00+02:00"),
            replace_line("lastmod", "lastmod = 2026-07-02T11:00:00+02:00")))
        self.assert_clean(result)

    def test_variants_share_a_base_name(self) -> None:
        """Requirement: Sequence files (the same base name)."""
        result = sequence_variant_run(add_sequence(
            "SEQ-0001-other.de.md", *GERMAN))
        problem = self.assert_one(result, "error", "file_name",
                                  "SEQ-0001-baseline.de.md",
                                  path_suffix="SEQ-0001-other.de.md")
        self.assertTrue(problem.path.endswith("SEQ-0001-other.de.md"))

    def test_the_reference_is_the_german_file_without_an_untagged_one(
            self) -> None:
        """Requirement: Sequence files (reported like procedure
        variants, no untagged file)."""
        result = sequence_variant_run(changes(
            add_sequence("SEQ-0001-baseline.de.md", *GERMAN),
            add_sequence("SEQ-0001-baseline.en.md",
                         replace_line("target", 'target = "ethanol"')),
            remove_sequence(BASELINE)))
        self.assert_one(result, "error", "target",
                        "SEQ-0001-baseline.de.md",
                        path_suffix="SEQ-0001-baseline.en.md")

    def test_continuity_is_checked_on_the_reference_variant_only(
            self) -> None:
        """Requirement: Sequence continuity (the reference variant)."""
        result = sequence_variant_run(changes(
            edit_sequence(BASELINE, SWAPPED),
            add_sequence("SEQ-0001-baseline.de.md", *GERMAN, SWAPPED)))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(sorted(p.field for p in result.problems),
                         ["steps[2]", "target"], result.stdout)
        for problem in result.problems:
            self.assertTrue(problem.path.endswith(BASELINE), result.stdout)

    def test_the_german_reference_without_an_untagged_file(self) -> None:
        """Requirement: Sequence continuity (the reference is the untagged
        file, else the German one)."""
        result = sequence_variant_run(changes(
            add_sequence("SEQ-0001-baseline.de.md", SWAPPED),
            add_sequence("SEQ-0001-baseline.en.md", SWAPPED),
            remove_sequence(BASELINE)))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(sorted(p.field for p in result.problems),
                         ["steps[2]", "target"], result.stdout)
        for problem in result.problems:
            self.assertTrue(problem.path.endswith("SEQ-0001-baseline.de.md"),
                            result.stdout)


if __name__ == "__main__":
    unittest.main()
