"""Front-matter field rules (procedure-schema)."""

import tempfile
import unittest
from pathlib import Path

from support import (FIXTURES, ValidatorTestCase, fixture_run,
                     insert_line, products_line, remove_line, replace_line,
                     valid_set_run, variant_run)


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
        result = variant_run(
            "OSDB-0100-yield-not-number.md",
            replace_line("products", products_line(
                'compound = "ethyl-acetate", yield_percent = "85"')))
        self.assert_one(result, "error", "products[1].yield_percent",
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
        self.assert_one(result, "error", "products[1].yield_percent",
                        "must be between 0 and 100",
                        path_suffix="OSDB-0110-yield-out-of-range.md")


class ScaleTests(ValidatorTestCase):
    def test_scale_without_a_unit_is_rejected(self) -> None:
        """Scenario: Scale without a unit."""
        result = variant_run("OSDB-0100-bad-scale.md",
                             replace_line("scale", 'scale = "25"'))
        self.assert_one(result, "error", "scale",
                        "must be a number followed by a unit")


def one_product(*extra: str) -> str:
    """A ``products`` line: the baseline's product, then ``extra`` tables."""
    return products_line(
        'compound = "ethyl-acetate", yield_percent = 85', *extra)


class ProductsTests(ValidatorTestCase):
    def test_unknown_compound_is_rejected(self) -> None:
        """Scenario: Unknown compound."""
        result = fixture_run("invalid/unknown-compound")
        self.assert_one(result, "error", "products[1].compound",
                        'unknown compound "no-such-compound"',
                        path_suffix="OSDB-0123-unknown-compound.md")

    def test_two_products_pass(self) -> None:
        """Scenario: Two products."""
        result = variant_run(
            "OSDB-0100-two-products.md",
            replace_line("products", one_product(
                'compound = "ethanol", yield_percent = 10')))
        self.assert_clean(result)

    def test_product_listed_twice_is_rejected(self) -> None:
        """Scenario: A product listed twice."""
        result = variant_run(
            "OSDB-0100-product-twice.md",
            replace_line("products", one_product(
                'compound = "ethyl-acetate", yield_percent = 5')))
        self.assert_one(result, "error", "products",
                        "lists ethyl-acetate twice")

    def test_empty_products_list_is_rejected(self) -> None:
        """Scenario: No products."""
        result = variant_run("OSDB-0100-no-products.md",
                             replace_line("products", "products = []"))
        self.assert_one(result, "error", "products", "must not be empty")

    def test_missing_products_is_rejected(self) -> None:
        """Requirement: Required front-matter fields (products)."""
        result = variant_run("OSDB-0100-missing-products.md",
                             remove_line("products"))
        self.assert_one(result, "error", "products",
                        "required field missing")

    def test_products_that_is_not_an_array_is_rejected(self) -> None:
        """Requirement: Products (not an array)."""
        for value in ('"ethyl-acetate"', "{ compound = \"ethyl-acetate\" }"):
            with self.subTest(value=value):
                result = variant_run(
                    "OSDB-0100-products-not-array.md",
                    replace_line("products", f"products = {value}"))
                self.assert_one(result, "error", "products",
                                "must be an array of tables")

    def test_entry_that_is_not_a_table_is_rejected(self) -> None:
        """Requirement: Products (an entry that is not a table)."""
        result = variant_run(
            "OSDB-0100-product-not-table.md",
            replace_line("products", 'products = ["ethyl-acetate"]'))
        self.assert_one(result, "error", "products[1]", "must be a table")

    def test_problem_in_the_second_product_is_numbered(self) -> None:
        """Requirement: Products (problems are numbered from 1)."""
        result = variant_run(
            "OSDB-0100-second-product-unknown.md",
            replace_line("products", one_product(
                'compound = "no-such-compound", yield_percent = 10')))
        self.assert_one(result, "error", "products[2].compound",
                        'unknown compound "no-such-compound"')

    def test_missing_compound_key_is_rejected(self) -> None:
        """Requirement: Products (a missing key, compound)."""
        result = variant_run(
            "OSDB-0100-product-no-compound.md",
            replace_line("products", products_line("yield_percent = 85")))
        self.assert_one(result, "error", "products[1].compound",
                        "required field missing")

    def test_missing_yield_is_rejected(self) -> None:
        """Requirement: Products (a missing key, yield_percent)."""
        result = variant_run(
            "OSDB-0100-product-no-yield.md",
            replace_line("products", products_line(
                'compound = "ethyl-acetate"')))
        self.assert_one(result, "error", "products[1].yield_percent",
                        "required field missing")

    def test_compound_that_is_not_a_string_skips_the_lookup(self) -> None:
        """Scenario: Dependent checks are suppressed (compound)."""
        result = variant_run(
            "OSDB-0100-compound-not-string.md",
            replace_line("products", products_line(
                "compound = 5, yield_percent = 85")))
        self.assert_one(result, "error", "products[1].compound", "")
        self.assertNotIn("unknown compound", result.stdout)

    def test_yield_that_is_a_boolean_is_rejected(self) -> None:
        """Requirement: Products (yield is never a boolean)."""
        result = variant_run(
            "OSDB-0100-yield-boolean.md",
            replace_line("products", products_line(
                'compound = "ethyl-acetate", yield_percent = true')))
        self.assert_one(result, "error", "products[1].yield_percent",
                        "must be a number")

    def test_yield_range_includes_both_ends(self) -> None:
        """Requirement: Products (yield from 0 to 100 inclusive)."""
        for value in ("0", "100", "0.0", "99.9"):
            with self.subTest(yield_percent=value):
                result = variant_run(
                    "OSDB-0100-yield-edge.md",
                    replace_line("products", products_line(
                        'compound = "ethyl-acetate", '
                        f"yield_percent = {value}")))
                self.assert_clean(result)

    def test_negative_yield_is_rejected(self) -> None:
        """Requirement: Products (yield below 0)."""
        result = variant_run(
            "OSDB-0100-yield-negative.md",
            replace_line("products", products_line(
                'compound = "ethyl-acetate", yield_percent = -1')))
        self.assert_one(result, "error", "products[1].yield_percent",
                        "must be between 0 and 100")

    def test_unknown_key_in_a_product_is_a_warning(self) -> None:
        """Requirement: Products (any other key is a warning)."""
        result = variant_run(
            "OSDB-0100-product-unknown-key.md",
            replace_line("products", products_line(
                'compound = "ethyl-acetate", yield_percent = 85, '
                'yeild = 1')))
        self.assert_one(result, "warning", "products[1].yeild",
                        "unknown field")

    def test_old_product_fields_are_unknown(self) -> None:
        """Requirement: Required front-matter fields (old keys leave)."""
        for line, field in (("yield_percent = 85", "yield_percent"),
                            ('precursors = ["OSDB-0001"]', "precursors"),
                            ('structure_image = "structures/x.svg"',
                             "structure_image")):
            with self.subTest(field=field):
                result = variant_run("OSDB-0100-old-field.md",
                                     insert_line(line))
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(
                    [(p.field, p.severity, "unknown field" in p.message)
                     for p in result.problems],
                    [(field, "warning", True)])


class SubstrateTests(ValidatorTestCase):
    def test_unknown_substrate_is_rejected(self) -> None:
        """Scenario: Unknown substrate."""
        result = fixture_run("invalid/unknown-substrate")
        self.assert_one(result, "error", "substrates",
                        'unknown compound "no-such-compound"',
                        path_suffix="OSDB-0124-unknown-substrate.md")

    def test_substrate_that_is_also_a_product_is_rejected(self) -> None:
        """Scenario: A substrate that is also a product."""
        result = variant_run("OSDB-0100-substrate-is-product.md",
                             insert_line('substrates = ["ethyl-acetate"]'))
        self.assert_one(result, "error", "substrates",
                        "ethyl-acetate is also a product")

    def test_substrates_pass(self) -> None:
        """Requirement: Substrates (a list of registry keys)."""
        result = variant_run(
            "OSDB-0100-substrates.md",
            insert_line('substrates = ["acetic-acid", "ethanol"]'))
        self.assert_clean(result)

    def test_empty_substrates_pass(self) -> None:
        """Requirement: Substrates (an empty list names none)."""
        result = variant_run("OSDB-0100-no-substrates.md",
                             insert_line("substrates = []"))
        self.assert_clean(result)

    def test_substrate_named_twice_is_rejected(self) -> None:
        """Requirement: Substrates (a key named twice)."""
        result = variant_run(
            "OSDB-0100-substrate-twice.md",
            insert_line('substrates = ["ethanol", "ethanol"]'))
        self.assert_one(result, "error", "substrates",
                        "lists ethanol twice")

    def test_substrates_that_is_not_a_list_of_strings_is_rejected(
            self) -> None:
        """Requirement: Substrates (a value that is not a list)."""
        for value in ('"ethanol"', "[1]", '["ethanol", 2]'):
            with self.subTest(value=value):
                result = variant_run(
                    "OSDB-0100-substrates-bad-type.md",
                    insert_line(f"substrates = {value}"))
                self.assert_one(
                    result, "error", "substrates",
                    'must be a list of compound keys, e.g. ["ethanol"]')


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
