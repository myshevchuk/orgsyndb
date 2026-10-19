"""Org keyword lint, export mapping and cross-check (procedure-schema,
procedure-validation)."""

import shutil
import tempfile
import unittest
from pathlib import Path

import support
from support import (FIXTURES, ValidatorTestCase, fixture_run,
                     run_validator, valid_set_run)


def org_lint(case: str):
    """Run with only --org-root on org-invalid/<case>/org."""
    return run_validator(
        ["--vocabulary", support.VOCABULARY,
         "--static-dir", support.STATIC_DIR,
         "--org-root", FIXTURES / "org-invalid" / case / "org"])


def org_cross_check(case: str):
    """Fixture run on org-invalid/<case>/export with its Org root."""
    return fixture_run(f"org-invalid/{case}/export",
                       org_roots=[f"org-invalid/{case}/org"])


class OrgKeywordLintTests(ValidatorTestCase):
    def test_missing_creation_keyword_is_rejected(self) -> None:
        """Scenario: Missing creation keyword."""
        self.assert_one(org_lint("missing-created"), "error", "#+CREATED",
                        "keyword missing",
                        path_suffix="OSDB-0201-missing-created.org")

    def test_keyword_given_twice_is_rejected(self) -> None:
        """Scenario: Keyword given twice."""
        self.assert_one(org_lint("duplicate-created"), "error", "#+CREATED",
                        "appears more than once",
                        path_suffix="OSDB-0202-duplicate-created.org")

    def test_active_timestamp_is_rejected(self) -> None:
        """Scenario: Active timestamp."""
        self.assert_one(org_lint("active-timestamp"), "error",
                        "#+LAST_MODIFIED", "must be an inactive timestamp",
                        path_suffix="OSDB-0203-active-timestamp.org")

    def test_timestamp_without_seconds_is_rejected(self) -> None:
        """Scenario: Timestamp without seconds."""
        self.assert_one(org_lint("missing-seconds"), "error", "#+CREATED",
                        "must have the form [YYYY-MM-DD Day hh:mm:ss]",
                        path_suffix="OSDB-0204-missing-seconds.org")

    def test_impossible_calendar_date_is_rejected(self) -> None:
        """Scenario: Impossible calendar date."""
        self.assert_one(org_lint("invalid-date"), "error", "#+CREATED",
                        "is not a valid date",
                        path_suffix="OSDB-0205-invalid-date.org")

    def test_weekday_that_does_not_match_the_date_is_rejected(self) -> None:
        """Scenario: Weekday does not match the date."""
        self.assert_one(org_lint("wrong-weekday"), "error", "#+CREATED",
                        'weekday "Tue" does not match 2026-10-19 (Mon)',
                        path_suffix="OSDB-0206-wrong-weekday.org")

    def test_local_time_skipped_by_the_spring_change_is_rejected(
            self) -> None:
        """Scenario: Local time skipped by the spring clock change."""
        self.assert_one(org_lint("nonexistent-local-time"), "error",
                        "#+CREATED", "does not exist in Europe/Berlin",
                        path_suffix="OSDB-0207-nonexistent-local-time.org")

    def test_modification_before_creation_is_rejected(self) -> None:
        """Scenario: Modification before creation."""
        self.assert_one(org_lint("last-modified-before-created"), "error",
                        "#+LAST_MODIFIED", "is earlier than #+CREATED",
                        path_suffix="OSDB-0208-last-modified-before-"
                                    "created.org")

    def test_ambiguous_fall_back_hour_can_be_in_order(self) -> None:
        """Scenario: Ambiguous fall-back hour can be in order."""
        result = run_validator(
            ["--vocabulary", support.VOCABULARY,
             "--org-root", FIXTURES / "valid" / "org"])
        self.assert_no_lines_for(result, "OSDB-0004")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_ai_model_is_rejected(self) -> None:
        """Scenario: Empty AI model."""
        self.assert_one(org_lint("bad-ai-model"), "error", "#+AI_MODEL",
                        "must be a model identifier or none",
                        path_suffix="OSDB-0209-bad-ai-model.org")

    def test_org_file_name_that_breaks_the_rule_is_rejected(self) -> None:
        """Scenario: Org file name breaks the naming rule."""
        self.assert_one(org_lint("bad-org-file-name"), "error", "file_name",
                        "must be named OSDB-NNNN-short-slug.org",
                        path_suffix="osdb-0210-lowercase.org")


class OrgExportMappingTests(ValidatorTestCase):
    def test_matching_export_passes(self) -> None:
        """Scenario: Matching export passes."""
        result = valid_set_run()
        self.assert_no_lines_for(result, "OSDB-0003")

    def test_ambiguous_hour_exported_in_order_passes(self) -> None:
        """Scenario: Ambiguous hour exported in order."""
        result = valid_set_run()
        self.assert_no_lines_for(result, "OSDB-0004")

    def test_exported_instants_decide_the_ordering(self) -> None:
        """Scenario: Exported instants decide the ordering."""
        stem = "OSDB-0004-ambiguous-hour"
        with tempfile.TemporaryDirectory() as tmp:
            org_root = Path(tmp) / "org"
            content = Path(tmp) / "content"
            org_root.mkdir()
            content.mkdir()
            shutil.copy(FIXTURES / "valid/org" / f"{stem}.org", org_root)
            export = content / f"{stem}.md"
            text = (FIXTURES / "valid/export" / f"{stem}.md").read_text(
                encoding="utf-8")
            old = "lastmod = 2026-10-25T02:10:00+01:00"
            self.assertIn(old, text)
            export.write_text(
                text.replace(old, "lastmod = 2026-10-25T02:10:00+02:00"),
                encoding="utf-8")
            result = fixture_run(content, org_roots=[org_root])
        self.assert_one(result, "error", "lastmod", "is earlier than date",
                        path_suffix=f"{stem}.md")

    def test_exported_date_that_disagrees_is_rejected(self) -> None:
        """Scenario: Exported date disagrees."""
        self.assert_one(org_cross_check("export-date-mismatch"), "error",
                        "#+CREATED", "does not match exported date",
                        path_suffix="OSDB-0211-export-date-mismatch.org")

    def test_exported_offset_that_is_not_the_berlin_offset(self) -> None:
        """Scenario: Exported offset is not the Berlin offset."""
        result = org_cross_check("export-offset-mismatch")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 2, result.stdout)
        self.assertEqual(len(result.problems), 2, result.stdout)
        error = [p for p in result.problems if p.severity == "error"]
        warning = [p for p in result.problems if p.severity == "warning"]
        self.assertEqual(len(error), 1, result.stdout)
        self.assertEqual(len(warning), 1, result.stdout)
        self.assertTrue(error[0].path.endswith(
            "OSDB-0212-export-offset-mismatch.org"))
        self.assertEqual(error[0].field, "#+CREATED")
        self.assertIn("does not match exported date", error[0].message)
        self.assertTrue(warning[0].path.endswith(
            "OSDB-0212-export-offset-mismatch.md"))
        self.assertEqual(warning[0].field, "date")
        self.assertIn("is not the Europe/Berlin offset", warning[0].message)

    def test_ai_model_recorded_as_none_but_exported_is_rejected(
            self) -> None:
        """Scenario: AI model recorded as none but exported."""
        self.assert_one(org_cross_check("export-ai-model-mismatch"),
                        "error", "#+AI_MODEL",
                        "does not match exported ai_model",
                        path_suffix="OSDB-0213-export-ai-model-mismatch.org")


class OrgCrossCheckTests(ValidatorTestCase):
    def test_org_source_without_an_export_is_rejected(self) -> None:
        """Scenario: Export missing."""
        self.assert_one(org_cross_check("missing-export"), "error",
                        "file_name", "no exported content file",
                        path_suffix="OSDB-0214-missing-export.org")

    def test_lint_only_run_skips_the_cross_check(self) -> None:
        """Scenario: Lint-only run skips the cross-check."""
        result = run_validator(
            ["--vocabulary", support.VOCABULARY,
             "--org-root", FIXTURES / "valid" / "org"])
        self.assert_clean(result)


class OrgDependentCheckTests(ValidatorTestCase):
    def test_invalid_date_does_not_cascade(self) -> None:
        """Scenario: Invalid date does not cascade."""
        result = org_lint("invalid-date")
        self.assertEqual(len(result.stdout.splitlines()), 1, result.stdout)
        self.assertNotIn("weekday", result.stdout)
        self.assertNotIn("earlier than", result.stdout)
        self.assertIn("is not a valid date", result.stdout)


if __name__ == "__main__":
    unittest.main()
