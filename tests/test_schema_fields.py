"""Front-matter field rules (procedure-schema)."""

import tempfile
import unittest
from pathlib import Path

from support import (FIXTURES, ValidatorTestCase, fixture_run,
                     insert_in_product, insert_line, remove_line,
                     replace_line, valid_set_run, variant_run)


class IdentifierTests(ValidatorTestCase):
    def test_malformed_id_is_rejected(self) -> None:
        """Scenario: Malformed ID is rejected."""
        result = fixture_run("invalid/bad-id-format")
        self.assert_one(result, "error", "id", "must match OSDB-NNNN",
                        path_suffix="OSDB-0102-bad-id-format.md")

    def test_placeholder_id_is_rejected(self) -> None:
        """Scenario: Placeholder ID is rejected."""
        result = variant_run(
            "OSDB-0000-id-zero.md",
            replace_line("id", 'id = "OSDB-0000"'),
            replace_line("slug", 'slug = "osdb-0000"'))
        self.assert_one(result, "error", "id",
                        "must be between OSDB-0001 and OSDB-9999")


class UniqueIdentifierTests(ValidatorTestCase):
    def test_same_id_in_two_content_roots_is_an_error_on_each(self) -> None:
        """Scenario: Same ID in two content roots."""
        result = fixture_run("invalid/duplicate-id/a",
                             "invalid/duplicate-id/b")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 2, result.stdout)
        self.assertEqual(len(result.problems), 2, result.stdout)
        by_name = {}
        for problem in result.problems:
            self.assertEqual(problem.field, "id")
            self.assertEqual(problem.severity, "error")
            self.assertIn("duplicate id OSDB-0104", problem.message)
            by_name[problem.path.rsplit("/", 1)[-1]] = problem
        self.assertEqual(set(by_name), {"OSDB-0104-first.md",
                                        "OSDB-0104-second.md"})
        self.assertIn("b/OSDB-0104-second.md",
                      by_name["OSDB-0104-first.md"].message)
        self.assertIn("a/OSDB-0104-first.md",
                      by_name["OSDB-0104-second.md"].message)


class FileNameTests(ValidatorTestCase):
    def test_lowercase_prefix_is_rejected(self) -> None:
        """Scenario: Lowercase prefix is rejected."""
        result = variant_run("osdb-0100-lowercase.md")
        self.assert_one(result, "error", "file_name",
                        "must be named OSDB-NNNN-short-slug.md")

    def test_file_name_that_disagrees_with_the_id_is_rejected(self) -> None:
        """Scenario: File name disagrees with the ID."""
        result = fixture_run("invalid/file-name-id-mismatch")
        self.assert_one(result, "error", "file_name",
                        "does not match id OSDB-0199",
                        path_suffix="OSDB-0106-file-name-id-mismatch.md")


class SlugTests(ValidatorTestCase):
    def test_slug_that_differs_from_the_lowercased_id_is_rejected(
            self) -> None:
        """Scenario: Slug differs from the lowercased ID."""
        result = fixture_run("invalid/slug-mismatch")
        self.assert_one(result, "error", "slug",
                        'must be "osdb-0107" (the lowercased id)',
                        path_suffix="OSDB-0107-slug-mismatch.md")

    def test_missing_slug_is_rejected(self) -> None:
        """Scenario: Slug is missing."""
        result = variant_run("OSDB-0100-missing-slug.md",
                             remove_line("slug"))
        self.assert_one(result, "error", "slug", "required field missing")


class RequiredFieldTests(ValidatorTestCase):
    def test_missing_title_is_rejected(self) -> None:
        """Scenario: Missing title."""
        result = fixture_run("invalid/missing-title")
        self.assert_one(result, "error", "title", "required field missing",
                        path_suffix="OSDB-0101-missing-title.md")

    def test_yield_given_as_a_string_is_rejected(self) -> None:
        """Scenario: Yield given as a string."""
        result = variant_run("OSDB-0100-yield-not-number.md",
                             replace_line("yield_percent",
                                          'yield_percent = "85"'))
        self.assert_one(result, "error", "yield_percent",
                        "must be a number")

    def test_empty_hazards_list_is_rejected(self) -> None:
        """Scenario: Empty hazards list."""
        result = variant_run("OSDB-0100-empty-hazards.md",
                             replace_line("hazards", "hazards = []"))
        self.assert_one(result, "error", "hazards", "must not be empty")

    def test_empty_tags_list_is_rejected(self) -> None:
        """Scenario: Empty tags list."""
        result = variant_run("OSDB-0100-empty-tags.md",
                             replace_line("tags", "tags = []"))
        self.assert_one(result, "error", "tags", "must not be empty")


class StatusTests(ValidatorTestCase):
    def test_unknown_status_is_rejected(self) -> None:
        """Scenario: Unknown status."""
        result = variant_run("OSDB-0100-bad-status.md",
                             replace_line("status", 'status = "approved"'))
        self.assert_one(result, "error", "status",
                        "must be one of draft, checked, retired")


class ReactionTypeTests(ValidatorTestCase):
    def test_reaction_type_outside_the_vocabulary_is_rejected(self) -> None:
        """Scenario: Reaction type outside the vocabulary."""
        result = fixture_run("invalid/unknown-reaction-type")
        self.assert_one(result, "error", "reaction_types",
                        'unknown reaction type "esterfication"',
                        path_suffix="OSDB-0111-unknown-reaction-type.md")

    def test_two_reaction_types_are_rejected(self) -> None:
        """Scenario: Two reaction types."""
        result = variant_run(
            "OSDB-0100-two-reaction-types.md",
            replace_line("reaction_types",
                         'reaction_types = ["esterification", "reduction"]'))
        self.assert_one(result, "error", "reaction_types",
                        "must contain exactly one reaction type")


class TagTests(ValidatorTestCase):
    def test_tag_with_capitals_and_a_space_is_rejected(self) -> None:
        """Scenario: Tag with capitals and a space."""
        result = variant_run("OSDB-0100-bad-tag.md",
                             replace_line("tags", 'tags = ["Sample Data"]'))
        self.assert_one(result, "error", "tags",
                        "must be lowercase and hyphenated")


class YieldTests(ValidatorTestCase):
    def test_yield_above_one_hundred_is_rejected(self) -> None:
        """Scenario: Yield above 100."""
        result = fixture_run("invalid/yield-out-of-range")
        self.assert_one(result, "error", "yield_percent",
                        "must be between 0 and 100",
                        path_suffix="OSDB-0110-yield-out-of-range.md")


class ScaleTests(ValidatorTestCase):
    def test_scale_without_a_unit_is_rejected(self) -> None:
        """Scenario: Scale without a unit."""
        result = variant_run("OSDB-0100-bad-scale.md",
                             replace_line("scale", 'scale = "25"'))
        self.assert_one(result, "error", "scale",
                        "must be a number followed by a unit")


class ProductTests(ValidatorTestCase):
    def test_missing_molecular_weight_is_rejected(self) -> None:
        """Scenario: Missing molecular weight."""
        result = variant_run("OSDB-0100-product-missing-mw.md",
                             remove_line("mw"))
        self.assert_one(result, "error", "product.mw",
                        "required field missing")

    def test_cas_number_with_a_wrong_check_digit_is_rejected(self) -> None:
        """Scenario: CAS number with a wrong check digit."""
        result = variant_run("OSDB-0100-bad-cas-check-digit.md",
                             insert_in_product('cas = "64-17-4"'))
        self.assert_one(result, "error", "product.cas", "check digit")


class TimestampTests(ValidatorTestCase):
    def test_date_written_as_a_quoted_string_is_rejected(self) -> None:
        """Scenario: Date written as a quoted string."""
        result = fixture_run("invalid/date-as-string")
        self.assert_one(result, "error", "date",
                        "must be a TOML offset datetime",
                        path_suffix="OSDB-0120-date-as-string.md")

    def test_date_without_an_offset_is_rejected(self) -> None:
        """Scenario: Date without an offset."""
        result = variant_run(
            "OSDB-0100-date-without-offset.md",
            replace_line("date", "date = 2026-10-19T17:42:05"))
        self.assert_one(result, "error", "date",
                        "must be a TOML offset datetime")

    def test_last_modification_before_creation_is_rejected(self) -> None:
        """Scenario: Last modification before creation."""
        result = variant_run(
            "OSDB-0100-lastmod-before-date.md",
            replace_line("date", "date = 2026-10-19T17:42:05+02:00"),
            replace_line("lastmod", "lastmod = 2026-10-18T09:00:00+02:00"))
        self.assert_one(result, "error", "lastmod", "is earlier than date")

    def test_exported_instants_decide_the_ordering(self) -> None:
        """Scenario: Exported instants decide the ordering."""
        stem = "OSDB-0004-ambiguous-hour"
        text = (FIXTURES / "valid/export" / f"{stem}.md").read_text(
            encoding="utf-8")
        old = "lastmod = 2026-10-25T02:10:00+01:00"
        self.assertIn(old, text)
        with tempfile.TemporaryDirectory() as tmp:
            content = Path(tmp) / "content"
            content.mkdir()
            (content / f"{stem}.md").write_text(
                text.replace(old, "lastmod = 2026-10-25T02:10:00+02:00"),
                encoding="utf-8")
            result = fixture_run(content)
        self.assert_one(result, "error", "lastmod", "is earlier than date",
                        path_suffix=f"{stem}.md")

    def test_winter_offset_in_summer_is_a_warning(self) -> None:
        """Scenario: Winter offset in summer."""
        result = fixture_run("warn/offset")
        self.assert_one(result, "warning", "date",
                        "is not the Europe/Berlin offset",
                        path_suffix="OSDB-0155-offset.md")


class PrecursorTests(ValidatorTestCase):
    def test_precursor_that_does_not_exist_is_rejected(self) -> None:
        """Scenario: Precursor that does not exist."""
        result = fixture_run("invalid/missing-precursor")
        self.assert_one(result, "error", "precursors", "OSDB-0999 not found",
                        path_suffix="OSDB-0123-missing-precursor.md")

    def test_procedure_listing_itself_is_rejected(self) -> None:
        """Scenario: Procedure lists itself."""
        result = variant_run("OSDB-0100-self-precursor.md",
                             insert_line('precursors = ["OSDB-0100"]'))
        self.assert_one(result, "error", "precursors",
                        "lists the procedure itself")

    def test_precursor_in_another_content_root_is_found(self) -> None:
        """Scenario: Precursor in another content root."""
        result = valid_set_run()
        self.assert_no_lines_for(result, ":precursors:")


class StructureImageTests(ValidatorTestCase):
    def test_missing_image_file_is_rejected(self) -> None:
        """Scenario: Image file missing."""
        result = fixture_run("invalid/missing-structure-image")
        self.assert_one(result, "error", "structure_image", "not found",
                        path_suffix="OSDB-0125-missing-structure-image.md")

    def test_unsupported_image_type_is_rejected(self) -> None:
        """Scenario: Unsupported image type."""
        result = variant_run(
            "OSDB-0100-structure-image-wrong-type.md",
            insert_line('structure_image = "structures/osdb-0001.jpg"'))
        self.assert_one(result, "error", "structure_image",
                        "must end in .svg or .png")

    def test_image_outside_the_structures_directory_is_rejected(
            self) -> None:
        """Scenario: Image outside the structures directory."""
        result = variant_run(
            "OSDB-0100-structure-image-outside-structures.md",
            insert_line('structure_image = "osdb-0001.svg"'))
        self.assert_one(result, "error", "structure_image",
                        "must be a relative path under structures/")


class OtherOptionalFieldTests(ValidatorTestCase):
    def test_checked_by_given_as_a_bare_string_is_rejected(self) -> None:
        """Scenario: Checked-by given as a bare string."""
        result = variant_run("OSDB-0100-checked-by-not-list.md",
                             insert_line('checked_by = "B. Example"'))
        self.assert_one(result, "error", "checked_by",
                        "must be a list of strings")

    def test_ai_model_recorded_as_none_is_rejected(self) -> None:
        """Scenario: AI model recorded as none."""
        result = variant_run("OSDB-0100-ai-model-none.md",
                             insert_line('ai_model = "none"'))
        self.assert_one(result, "error", "ai_model", "omit ai_model")


class UnknownKeyTests(ValidatorTestCase):
    def test_draft_set_to_true_is_rejected(self) -> None:
        """Scenario: Draft set to true."""
        result = variant_run("OSDB-0100-draft-true.md",
                             insert_line("draft = true"))
        self.assert_one(result, "error", "draft", "use status, not draft")

    def test_singular_author_key_is_rejected(self) -> None:
        """Scenario: Singular author key."""
        result = fixture_run("invalid/author-key")
        self.assert_one(result, "error", "author", "use authors",
                        path_suffix="OSDB-0129-author-key.md")

    def test_explicit_url_is_rejected(self) -> None:
        """Scenario: Explicit URL."""
        result = variant_run(
            "OSDB-0100-url-key.md",
            insert_line('url = "/procedures/osdb-0100/"'))
        self.assert_one(result, "error", "url", "derived from slug")

    def test_misspelt_optional_key_is_a_warning(self) -> None:
        """Scenario: Misspelt optional key."""
        result = variant_run("OSDB-0100-unknown-key.md",
                             insert_line('checkedby = ["B. Example"]'))
        self.assert_one(result, "warning", "checkedby", "unknown field")

    def test_ox_hugo_draft_false_passes(self) -> None:
        """Scenario: ox-hugo draft key passes."""
        result = valid_set_run()
        self.assert_no_lines_for(result, "OSDB-0003")


if __name__ == "__main__":
    unittest.main()
