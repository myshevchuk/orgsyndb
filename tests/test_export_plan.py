"""The export plan and exported timestamps (org-export)."""

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline_support import FIXTURES, Run, captured, pipeline

VALID_ORG = FIXTURES / "valid" / "org"
PROPYL = VALID_ORG / "OSDB-0003-propyl-acetate.org"
AMBIGUOUS = VALID_ORG / "OSDB-0004-ambiguous-hour.org"


def set_keyword(text: str, keyword: str, value: str) -> str:
    """Replace the value of one ``#+KEYWORD:`` line, and nothing else."""
    edited, count = re.subn(rf"^(#\+{keyword}:).*$", rf"\1 {value}", text,
                            flags=re.M)
    if count != 1:
        raise AssertionError(f"fixture has no unique #+{keyword}: line")
    return edited


class PlanTestCase(unittest.TestCase):
    def workspace(self) -> tuple[Path, Path]:
        """Return an empty Org root and a PLAN_JSON path, both new."""
        base = Path(tempfile.mkdtemp(prefix="orgsyndb plan "))
        self.addCleanup(shutil.rmtree, base, True)
        (base / "org root").mkdir()
        return base / "org root", base / "plan.json"

    def plan(self, root: Path, plan: Path) -> Run:
        """Write the plan; exit status 1 stands for a refused plan."""
        written, out, err = captured(pipeline().write_export_plan,
                                     str(root), plan)
        return Run(0 if written is not None else 1, out, err)

    def plan_for(self, source: Path, **keywords: str) -> dict:
        """Plan a copy of ``source`` with keyword lines replaced."""
        root, plan = self.workspace()
        text = source.read_text(encoding="utf-8")
        for keyword, value in keywords.items():
            text = set_keyword(text, keyword, value)
        (root / source.name).write_text(text, encoding="utf-8")
        result = self.plan(root, plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = json.loads(plan.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1, entries)
        return entries[0]


class ExportPlanTests(PlanTestCase):
    def test_valid_source_is_planned(self) -> None:
        """Scenario: Plan for a valid source."""
        root, plan = self.workspace()
        shutil.copy2(PROPYL, root)
        result = self.plan(root, plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = json.loads(plan.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["stem"], PROPYL.stem)
        self.assertEqual(entry["source"], str(root / PROPYL.name))
        self.assertEqual(entry["date"], "2026-10-19T17:42:05+02:00")
        self.assertEqual(entry["lastmod"], "2026-10-19T18:30:00+02:00")
        self.assertIsNone(entry["ai_model"])

    def test_ai_model_is_carried_into_the_plan(self) -> None:
        """Scenario: Plan for a valid source (ai_model other than none)."""
        entry = self.plan_for(PROPYL, AI_MODEL="example-model-1")
        self.assertEqual(entry["ai_model"], "example-model-1")

    def test_entries_the_validator_does_not_examine_are_not_planned(
            self) -> None:
        """Scenario: Entries the validator does not examine are not
        planned."""
        root, plan = self.workspace()
        shutil.copy2(PROPYL, root)
        (root / ".#OSDB-0003-x.org").symlink_to("missing-target")
        (root / ".OSDB-0005-hidden.org").write_text("not a procedure\n")
        (root / "nested.org").mkdir()
        (root / "notes.txt").write_text("notes\n")
        result = self.plan(root, plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = json.loads(plan.read_text(encoding="utf-8"))
        self.assertEqual([e["stem"] for e in entries], [PROPYL.stem])

    def test_lint_error_stops_the_plan(self) -> None:
        """Scenario: Lint error stops the plan."""
        root = FIXTURES / "org-invalid" / "missing-seconds" / "org"
        _, plan = self.workspace()
        result = self.plan(root, plan)
        self.assertEqual(result.returncode, 1, result.stdout)
        matching = [ln for ln in result.stderr.splitlines()
                    if ":#+CREATED: error: " in ln
                    and "must have the form [YYYY-MM-DD Day hh:mm:ss]"
                    in ln]
        self.assertTrue(matching, result.stderr)
        self.assertFalse(plan.exists())

    def test_missing_org_root_yields_an_empty_plan(self) -> None:
        """Requirement: Export plan (a missing ORG_ROOT yields an empty
        array)."""
        root, plan = self.workspace()
        result = self.plan(root / "absent", plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(plan.read_text(encoding="utf-8")), [])


class ExportedTimestampTests(PlanTestCase):
    def test_summer_time_offset(self) -> None:
        """Scenario: Summer time."""
        entry = self.plan_for(PROPYL, CREATED="[2026-10-19 Mon 17:42:05]")
        self.assertEqual(entry["date"], "2026-10-19T17:42:05+02:00")

    def test_winter_time_last_second_before_the_spring_change(self) -> None:
        """Scenario: Winter time, last second before the spring change."""
        entry = self.plan_for(PROPYL, CREATED="[2026-03-29 Sun 01:59:59]",
                              LAST_MODIFIED="[2026-03-29 Sun 03:00:00]")
        self.assertEqual(entry["date"], "2026-03-29T01:59:59+01:00")
        self.assertEqual(entry["lastmod"], "2026-03-29T03:00:00+02:00")

    def test_fall_back_hour_out_of_wall_clock_order(self) -> None:
        """Scenario: Fall-back hour out of wall-clock order."""
        entry = self.plan_for(AMBIGUOUS, CREATED="[2026-10-25 Sun 02:50:00]",
                              LAST_MODIFIED="[2026-10-25 Sun 02:10:00]")
        self.assertEqual(entry["date"], "2026-10-25T02:50:00+02:00")
        self.assertEqual(entry["lastmod"], "2026-10-25T02:10:00+01:00")

    def test_equal_times_in_the_fall_back_hour(self) -> None:
        """Scenario: Equal times in the fall-back hour."""
        entry = self.plan_for(AMBIGUOUS, CREATED="[2026-10-25 Sun 02:30:00]",
                              LAST_MODIFIED="[2026-10-25 Sun 02:30:00]")
        self.assertEqual(entry["date"], "2026-10-25T02:30:00+02:00")
        self.assertEqual(entry["lastmod"], "2026-10-25T02:30:00+02:00")
