"""Tests of the checks an import is refused by (collection-import:
Import checks)."""

import copy
from typing import Any

from .collection_support import (ImportCase, by_id, counts, demo_collection,
                                 dump, manifest)


class CheckCase(ImportCase):

    def refused_by(self, data: dict[str, Any]) -> list[str]:
        """Post a manifest of the collection ``data`` built after the
        latest accepted import; assert that it is refused, and that
        nothing but the import is written; return its errors."""
        before = dump()
        answer = self.refuse(data)
        record = self.latest_refused()
        self.assertEqual(answer["import"], record.pk)
        self.assertEqual(record.outcome, "refused")
        self.assertEqual((record.release, record.language), ("", ""))
        self.assertTrue(record.errors)
        after = dump()
        for name in ("Procedure", "ScopeEntry", "EntrySubstance",
                     "Sequence", "Step"):
            self.assertEqual(after[name], before[name], name)
        self.assertEqual(len(after["Import"]), len(before["Import"]) + 1)
        return record.errors.splitlines()

    def latest_refused(self) -> Any:
        from collection.models import Import
        return Import.objects.filter(outcome="refused").order_by(
            "received_at", "pk").last()

    def only_error(self, data: dict[str, Any], error: str) -> None:
        """Assert that ``data`` is refused with ``error`` alone."""
        self.assertEqual(self.refused_by(data), [error])


class EachCheckTests(CheckCase):

    def test_an_id_named_twice(self) -> None:
        """Requirement: Import checks (`<ID>: named twice`)."""
        data = demo_collection()
        data["procedures"].append(copy.deepcopy(data["procedures"][1]))
        data["procedures"].sort(key=lambda procedure: procedure["id"])
        self.only_error(data, "OSDB-0002: named twice")

    def test_a_sequence_named_twice(self) -> None:
        """Requirement: Import checks (`<ID>: named twice`, among the
        sequences)."""
        data = demo_collection()
        data["sequences"].append(copy.deepcopy(data["sequences"][0]))
        self.only_error(data, "SEQ-0001: named twice")

    def test_an_unknown_reaction_type(self) -> None:
        """Requirement: Import checks (`<ID>: unknown reaction type
        "<key>"`)."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0003")["reaction_type"] = \
            "no-such-type"
        self.only_error(
            data, 'OSDB-0003: unknown reaction type "no-such-type"')

    def test_unknown_substance(self) -> None:
        """Scenario: Unknown substance."""
        from collection.models import Procedure
        data = demo_collection()
        entry = by_id(data["procedures"], "OSDB-0002")["entries"][0]
        entry["products"][0]["compound"] = "no-such-substance"
        self.only_error(
            data, 'OSDB-0002: unknown substance "no-such-substance"')
        self.assertEqual(Procedure.objects.count(), 0)

    def test_an_unknown_substrate(self) -> None:
        """Requirement: Import checks (`<ID>: unknown substance
        "<key>"`, a substrate)."""
        data = demo_collection()
        entry = by_id(data["procedures"], "OSDB-0009")["entries"][1]
        entry["substrates"] = ["no-such-substance"]
        self.only_error(
            data, 'OSDB-0009: unknown substance "no-such-substance"')

    def test_one_signature_twice(self) -> None:
        """Scenario: One signature twice."""
        data = demo_collection()
        entries = by_id(data["procedures"], "OSDB-0009")["entries"]
        entries[2] = copy.deepcopy(entries[0])
        errors = self.refused_by(data)
        self.assertEqual(errors, [
            "OSDB-0009: entries 1 and 3 have the signature "
            "4-acetylbiphenyl >> 1-biphenyl-4-yl-ethanol"])
        self.assertTrue(errors[0].startswith(
            "OSDB-0009: entries 1 and 3 have the signature"))

    def test_the_order_of_the_substances_makes_no_difference(self) -> None:
        """Requirement: Import checks (the signature sorts the keys of
        substrates and of products)."""
        data = demo_collection()
        entries = by_id(data["procedures"], "OSDB-0009")["entries"]
        entries[0] = {"substrates": ["4-bromoacetophenone", "acetophenone"],
                      "products": [{"compound": "1-phenylethanol",
                                    "yield_percent": 90},
                                   {"compound": "1-4-bromophenyl-ethanol",
                                    "yield_percent": 80}]}
        entries[1] = {"substrates": ["acetophenone", "4-bromoacetophenone"],
                      "products": [{"compound": "1-4-bromophenyl-ethanol",
                                    "yield_percent": 85},
                                   {"compound": "1-phenylethanol",
                                    "yield_percent": 70}]}
        entries[2] = {"substrates": ["benzaldehyde"],
                      "products": [{"compound": "1-phenylethanol",
                                    "yield_percent": 1}]}
        self.only_error(
            data, "OSDB-0009: entries 1 and 2 have the signature "
                  "4-bromoacetophenone + acetophenone >> "
                  "1-4-bromophenyl-ethanol + 1-phenylethanol")

    def test_a_third_entry_with_the_signature(self) -> None:
        """Requirement: Import checks (two entries of one procedure with
        the same signature)."""
        data = demo_collection()
        entries = by_id(data["procedures"], "OSDB-0009")["entries"]
        entries[1] = copy.deepcopy(entries[2])
        self.only_error(
            data, "OSDB-0009: entries 2 and 3 have the signature "
                  "4-bromoacetophenone >> 1-4-bromophenyl-ethanol")

    def test_the_same_chemistry_in_two_procedures_is_taken(self) -> None:
        """Requirement: Imported rows (`signature`, unique within the
        procedure): OSDB-0005 and the first entry of OSDB-0009 share
        one."""
        record = self.accept()
        self.assertEqual(counts()["Import"], 1)
        self.assertEqual(record.outcome, "accepted")

    def test_a_procedure_with_no_entry(self) -> None:
        """Requirement: Import checks (`<ID>: no entry`)."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0003")["entries"] = []
        self.only_error(data, "OSDB-0003: no entry")

    def test_an_unknown_target(self) -> None:
        """Requirement: Import checks (`<ID>: unknown target
        "<key>"`)."""
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0001")["target"] = "no-such-substance"
        self.only_error(
            data, 'SEQ-0001: unknown target "no-such-substance"')

    def test_a_step_names_a_procedure_the_collection_lacks(self) -> None:
        """Requirement: Import checks (`<ID>: step <n> names
        <procedure>, which is not in the collection`)."""
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0001")["steps"][1]["procedure"] = \
            "OSDB-0099"
        self.only_error(
            data, "SEQ-0001: step 2 names OSDB-0099, which is not in the "
                  "collection")

    def test_a_procedure_a_step_names_cannot_go(self) -> None:
        """Requirement: Import checks (a step naming a procedure the
        manifest does not hold)."""
        data = demo_collection()
        data["procedures"] = [p for p in data["procedures"]
                              if p["id"] != "OSDB-0002"]
        self.only_error(
            data, "SEQ-0001: step 2 names OSDB-0002, which is not in the "
                  "collection")


class StepEntryTests(CheckCase):

    def test_a_step_beyond_the_entries(self) -> None:
        """Scenario: A step beyond the entries."""
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0002")["steps"][1]["entry"] = 9
        self.only_error(data, "SEQ-0002: step 2 names no entry of OSDB-0009")

    def test_entries_that_do_not_count(self) -> None:
        """Requirement: Import checks (an entry number that does not
        count one of the entries from 1)."""
        for number in (0, 4, -1, 100):
            with self.subTest(number=number):
                data = demo_collection()
                by_id(data["sequences"], "SEQ-0002")["steps"][1]["entry"] = \
                    number
                self.only_error(
                    data, "SEQ-0002: step 2 names no entry of OSDB-0009")

    def test_a_general_procedure_needs_an_entry_number(self) -> None:
        """Requirement: Import checks (a step of a general procedure
        that gives no entry number)."""
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0002")["steps"][1]["entry"] = None
        self.only_error(data, "SEQ-0002: step 2 names no entry of OSDB-0009")

    def test_a_specific_procedure_takes_no_entry_number(self) -> None:
        """Requirement: Import checks (a step of a specific procedure
        that gives one)."""
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0001")["steps"][0]["entry"] = 1
        self.only_error(data, "SEQ-0001: step 1 names no entry of OSDB-0001")

    def test_every_entry_of_a_general_procedure_can_be_named(self) -> None:
        """Requirement: Import checks (an entry number that counts one
        of the entries from 1 is taken)."""
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0002")["steps"] = [
            {"procedure": "OSDB-0009", "entry": number}
            for number in (1, 2, 3)]
        record = self.accept(data)
        self.assertEqual(record.outcome, "accepted")


class ManyErrorsTests(CheckCase):

    def broken(self) -> dict[str, Any]:
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["entries"][0]["products"][0][
            "compound"] = "no-such-substance"
        by_id(data["procedures"], "OSDB-0006")["entries"][0]["substrates"][
            0] = "another-missing-one"
        by_id(data["procedures"], "OSDB-0003")["reaction_type"] = "nothing"
        by_id(data["sequences"], "SEQ-0002")["target"] = "no-target"
        by_id(data["sequences"], "SEQ-0001")["steps"][0]["entry"] = 2
        return data

    def test_every_error_is_recorded(self) -> None:
        """Requirement: Import checks (one error for each, every one
        recorded)."""
        errors = self.refused_by(self.broken())
        for wanted in (
                'OSDB-0002: unknown substance "no-such-substance"',
                'OSDB-0006: unknown substance "another-missing-one"',
                'OSDB-0003: unknown reaction type "nothing"',
                'SEQ-0002: unknown target "no-target"',
                "SEQ-0001: step 1 names no entry of OSDB-0001"):
            with self.subTest(wanted=wanted):
                self.assertEqual(errors.count(wanted), 1, errors)
        self.assertEqual(len(errors), 5, errors)

    def test_each_error_begins_with_its_id(self) -> None:
        """Requirement: Import checks (each beginning with the ID it
        concerns)."""
        for error in self.refused_by(self.broken()):
            with self.subTest(error=error):
                self.assertRegex(error, r"^(OSDB|SEQ)-\d{4}: ")

    def test_errors_follow_the_manifest(self) -> None:
        """Requirement: Import checks (in the order the checks find
        them: the procedures in the manifest's order)."""
        errors = self.refused_by(self.broken())
        first = errors.index('OSDB-0002: unknown substance '
                             '"no-such-substance"')
        second = errors.index('OSDB-0006: unknown substance '
                              '"another-missing-one"')
        self.assertLess(first, second)

    def test_an_id_named_twice_is_one_error(self) -> None:
        """Requirement: Import checks (one error for an ID that occurs
        twice)."""
        data = demo_collection()
        data["procedures"].append(copy.deepcopy(data["procedures"][4]))
        data["procedures"].sort(key=lambda procedure: procedure["id"])
        errors = self.refused_by(data)
        self.assertEqual(errors.count("OSDB-0005: named twice"), 1, errors)

    def test_a_refusal_changes_no_row(self) -> None:
        """Requirement: Import checks (a refused import writes no
        procedure, entry or sequence)."""
        self.accept()
        before = dump()
        errors = self.refused_by(self.broken())
        self.assertTrue(errors)
        after = dump()
        self.assertEqual(
            {name: rows for name, rows in after.items()
             if name != "Import"},
            {name: rows for name, rows in before.items()
             if name != "Import"})
        self.assertEqual(self.latest().pk, before["Import"][0]["id"])

    def test_a_stale_manifest_is_not_checked(self) -> None:
        """Requirement: Accepting an import (staleness is judged before
        the checks: a stale manifest is recorded nowhere)."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0003")["entries"] = []
        done = self.send(manifest(data, base=999))
        self.assertEqual(done.status_code, 409, done.content)
        self.assertEqual(sum(counts().values()), 0)
