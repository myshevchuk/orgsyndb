"""Body section rules (procedure-schema, "Body sections")."""

import unittest

import support
from support import ValidatorTestCase, fixture_run, valid_set_run, variant_run


class BodySectionTests(ValidatorTestCase):
    def test_missing_notes_section_is_a_warning(self) -> None:
        """Scenario: Missing Notes section."""
        result = fixture_run("warn/missing-section")
        self.assert_one(result, "warning", "body",
                        'missing section "Notes"',
                        path_suffix="OSDB-0151-missing-section.md")

    def test_sections_out_of_order_are_one_warning(self) -> None:
        """Scenario: Sections out of order."""
        result = variant_run(
            "OSDB-0100-section-order.md",
            support.move_section("Workup and Purification", "Procedure"))
        self.assert_one(result, "warning", "body",
                        "sections out of order")

    def test_heading_inside_a_code_fence_does_not_count(self) -> None:
        """Scenario: Heading inside a code fence does not count."""
        result = variant_run("OSDB-0100-heading-in-code.md",
                             support.fence_heading("## Notes"))
        self.assert_one(result, "warning", "body",
                        'missing section "Notes"')

    def test_ox_hugo_anchors_and_case_differences_are_accepted(self) -> None:
        """Scenario: ox-hugo anchors and case differences are accepted."""
        result = valid_set_run()
        self.assert_ran(result)
        body_lines = [p for p in result.problems if p.field == "body"]
        self.assertEqual(body_lines, [], result.stdout)
        self.assertNotIn(":body:", result.stdout)


if __name__ == "__main__":
    unittest.main()
