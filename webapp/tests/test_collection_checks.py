"""Tests of the checks an import is refused by (collection-import:
Import checks)."""

import copy
from typing import Any

from .collection_support import (ImportCase, author_rows, authors_of, by_id,
                                 counts, credited, demo_collection, dump,
                                 issued_keys, make_token, manifest,
                                 request_id)


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

    def test_an_unknown_author(self) -> None:
        """Scenario: Unknown author."""
        from collection.models import Procedure
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["authors"] = ["nobody"]
        self.only_error(data, 'OSDB-0002: unknown author "nobody"')
        self.assertEqual(Procedure.objects.count(), 0)
        self.assertEqual(author_rows(), [])

    def test_the_name_of_a_person_is_no_user_name(self) -> None:
        """Requirement: Import checks (an author whose user name no
        account has)."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0003")["authors"] = [
            "tbauer", "Jonas Koch"]
        self.only_error(data, 'OSDB-0003: unknown author "Jonas Koch"')

    def test_each_unknown_author_is_an_error(self) -> None:
        """Requirement: Import checks (one error for each)."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["authors"] = [
            "klehmann", "nobody", "also-nobody"]
        by_id(data["procedures"], "OSDB-0005")["authors"] = ["nobody"]
        errors = self.refused_by(data)
        self.assertEqual(sorted(errors), sorted([
            'OSDB-0002: unknown author "nobody"',
            'OSDB-0002: unknown author "also-nobody"',
            'OSDB-0005: unknown author "nobody"']))

    def test_an_account_that_is_not_active_is_known(self) -> None:
        """Requirement: Import checks (an author whose user name no
        account has: an account that is not active is one)."""
        from django.contrib.auth import get_user_model
        get_user_model().objects.filter(username="mwolf").update(
            is_active=False)
        self.accept(credited())
        self.assertEqual(counts()["Import"], 1)
        self.assertEqual(authors_of("OSDB-0005"), ["mwolf"])

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


class IssuedCheckTests(CheckCase):
    """Requirement: Import checks (after the first accepted import, an
    ID the application has not issued)."""

    NOT_ISSUED = "{}: not issued by the lab application"

    def setUp(self) -> None:
        super().setUp()
        self.accept()

    def with_new(self, ident: str, sequence: bool = False
                 ) -> dict[str, Any]:
        """The demo collection with a copy of a procedure, or with
        ``sequence`` a sequence, as ``ident``."""
        data = demo_collection()
        kind, source = (("sequences", "SEQ-0001") if sequence
                        else ("procedures", "OSDB-0008"))
        new = copy.deepcopy(by_id(data[kind], source))
        new["id"] = ident
        data[kind].append(new)
        return data

    def test_an_id_not_issued(self) -> None:
        """Scenario: An ID not issued."""
        from collection.models import Procedure
        data = self.with_new("OSDB-0010")
        self.only_error(data, self.NOT_ISSUED.format("OSDB-0010"))
        self.assertFalse(Procedure.objects.filter(
            key="OSDB-0010").exists())
        done = request_id(self.client, "procedure",
                          make_token("klehmann"))
        self.assertEqual(done.json(), {"id": "OSDB-0010"})
        self.accept(data)
        self.assertTrue(Procedure.objects.filter(
            key="OSDB-0010").exists())

    def test_a_sequence_not_issued(self) -> None:
        """Requirement: Import checks (an ID the application has not
        issued, among the sequences)."""
        from collection.models import Sequence
        data = self.with_new("SEQ-0003", sequence=True)
        self.only_error(data, self.NOT_ISSUED.format("SEQ-0003"))
        self.assertFalse(Sequence.objects.filter(key="SEQ-0003").exists())
        done = request_id(self.client, "sequence", make_token("tbauer"))
        self.assertEqual(done.json(), {"id": "SEQ-0003"})
        self.accept(data)
        self.assertTrue(Sequence.objects.filter(key="SEQ-0003").exists())

    def test_each_id_is_one_error(self) -> None:
        """Requirement: Import checks (one error for each, each
        beginning with the ID it concerns)."""
        data = self.with_new("OSDB-0010")
        data["procedures"] += self.with_new("OSDB-0012")["procedures"][-1:]
        data["sequences"] += self.with_new(
            "SEQ-0004", sequence=True)["sequences"][-1:]
        errors = self.refused_by(data)
        self.assertEqual(sorted(errors), [
            self.NOT_ISSUED.format("OSDB-0010"),
            self.NOT_ISSUED.format("OSDB-0012"),
            self.NOT_ISSUED.format("SEQ-0004")])

    def test_it_comes_with_the_other_errors(self) -> None:
        """Requirement: Import checks (one error for each of these)."""
        data = self.with_new("OSDB-0010")
        by_id(data["procedures"], "OSDB-0010")["entries"][0][
            "substrates"] = ["no-such-substance"]
        errors = self.refused_by(data)
        self.assertEqual(sorted(errors), sorted([
            self.NOT_ISSUED.format("OSDB-0010"),
            'OSDB-0010: unknown substance "no-such-substance"']))

    def test_a_refusal_issues_nothing(self) -> None:
        """Requirement: Issued IDs (a refused import adopts nothing)."""
        before = issued_keys()
        self.refused_by(self.with_new("OSDB-0010"))
        self.assertEqual(issued_keys(), before)

    def test_a_procedure_that_went_may_come_back(self) -> None:
        """Requirement: Import checks (an ID is issued for good: a
        withdrawn procedure keeps its ID)."""
        data = demo_collection()
        data["procedures"] = [p for p in data["procedures"]
                              if p["id"] != "OSDB-0003"]
        self.accept(data)
        self.accept()
        self.assertEqual(counts()["Procedure"], 9)


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
