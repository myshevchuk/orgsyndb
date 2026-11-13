"""Tests of the adoption of IDs and of ``manage.py adopt_ids``
(collection-import: Issued IDs)."""

import io
from typing import Any

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from . import make_user
from .collection_support import (TOKEN, ImportCase, by_id, copy_procedure,
                                 demo_collection, issue_ids, issued_keys,
                                 issued_to, latest_import, make_token,
                                 manifest, post, refused, request_id)
from .demo_support import SeededCase

DEMO_IDS = [*(f"OSDB-{number:04d}" for number in range(1, 10)),
            "SEQ-0001", "SEQ-0002"]


def adopt(*arguments: str) -> list[str]:
    """Run ``adopt_ids`` with ``arguments``; return its lines."""
    out = io.StringIO()
    call_command("adopt_ids", *arguments, stdout=out, stderr=io.StringIO())
    return out.getvalue().splitlines()


def with_procedure(*idents: str) -> dict[str, Any]:
    """The demo collection with a procedure for each of ``idents``,
    which the demo lacks."""
    data = demo_collection()
    for ident in idents:
        data["procedures"].append(
            copy_procedure(data, "OSDB-0008", ident))
    return data


def after_the_latest(data: dict[str, Any]) -> dict[str, Any]:
    """A manifest of the collection ``data`` built after the latest
    accepted import."""
    return manifest(data, base=latest_import().pk)


class FirstImportTests(ImportCase):
    """The demo registry is loaded and no import exists."""

    def refusable(self) -> dict[str, Any]:
        """The demo collection with an unknown substance."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["entries"][0]["products"][
            0]["compound"] = "no-such-substance"
        return data

    def test_adopted_by_the_first_accepted_import(self) -> None:
        """Scenario: Adopted by the first accepted import."""
        refusal = self.send(self.follow(self.refusable(),
                                        deleted=["OSDB-0011"]))
        self.assertEqual(refusal.json()["outcome"], "refused")
        self.assertEqual(issued_keys(), [])
        self.accept(deleted=["OSDB-0012"])
        self.assertEqual(issued_keys(),
                         sorted([*DEMO_IDS, "OSDB-0012"]))
        for key in issued_keys():
            with self.subTest(key=key):
                self.assertIsNone(issued_to(key))
        done = request_id(self.client, "procedure",
                          make_token("klehmann"))
        self.assertEqual((done.status_code, done.json()),
                         (201, {"id": "OSDB-0013"}))

    def test_a_refused_import_adopts_nothing(self) -> None:
        """Requirement: Issued IDs (a refused import adopts nothing)."""
        done = self.send(self.follow(self.refusable()))
        self.assertEqual(done.json()["outcome"], "refused")
        self.assertEqual(issued_keys(), [])

    def test_a_failed_build_adopts_nothing(self) -> None:
        """Requirement: Issued IDs (a refused import adopts nothing)."""
        done = self.send(refused(["x: error: y"]))
        self.assertEqual(done.json()["outcome"], "refused")
        self.assertEqual(issued_keys(), [])

    def test_a_stale_manifest_adopts_nothing(self) -> None:
        """Requirement: Accepting an import (a stale manifest is
        recorded nowhere)."""
        done = self.send(manifest(base=999, deleted=["OSDB-0012"]))
        self.assertEqual(done.status_code, 409, done.content)
        self.assertEqual(issued_keys(), [])

    def test_an_issued_id_is_left_as_it_was(self) -> None:
        """Requirement: Issued IDs (adopts every ID that is not
        issued)."""
        from collection.models import IssuedId
        issue_ids("OSDB-0003")
        IssuedId.objects.filter(key="OSDB-0003").update(
            user=make_user("lab", "LB"))
        before = IssuedId.objects.get(key="OSDB-0003")
        self.accept()
        self.assertEqual(issued_keys(), sorted(DEMO_IDS))
        found = IssuedId.objects.get(key="OSDB-0003")
        self.assertEqual((found.pk, found.user, found.issued_at),
                         (before.pk, before.user, before.issued_at))

    def test_later_imports_adopt_nothing(self) -> None:
        """Requirement: Issued IDs (later imports adopt nothing and
        ignore `deleted`)."""
        self.accept()
        before = issued_keys()
        record = self.accept(deleted=["OSDB-0050", "SEQ-0050"])
        self.assertEqual(record.outcome, "accepted")
        self.assertEqual(issued_keys(), before)

    def test_an_import_with_an_unissued_id_adopts_nothing(self) -> None:
        """Requirement: Issued IDs (later imports adopt nothing; they
        refuse an ID that is not issued)."""
        self.accept()
        before = issued_keys()
        done = self.send(self.follow(with_procedure("OSDB-0010")))
        self.assertEqual(done.json()["outcome"], "refused")
        self.assertEqual(issued_keys(), before)


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class DataSetTests(SeededCase):
    """The demo data set is written."""

    def test_an_import_after_the_data_set_adopts_nothing(self) -> None:
        """Requirement: Issued IDs (later imports adopt nothing)."""
        done = post(self.client, after_the_latest(demo_collection()))
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        self.assertEqual(issued_keys(), sorted(DEMO_IDS))


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class AdoptCommandTests(SeededCase):
    """Requirement: Issued IDs (``manage.py adopt_ids``)."""

    def test_adopting_by_hand(self) -> None:
        """Scenario: Adopting by hand."""
        lines = adopt("OSDB-0012", "OSDB-0003")
        self.assertIn("adopted OSDB-0012", lines)
        self.assertIn("OSDB-0003 was issued", lines)
        self.assertNotIn("adopted OSDB-0003", lines)
        self.assertIsNone(issued_to("OSDB-0012"))
        done = post(self.client, after_the_latest(
            with_procedure("OSDB-0012")))
        self.assertEqual(done.json()["outcome"], "accepted", done.content)

    def test_a_malformed_argument_adopts_nothing(self) -> None:
        """Scenario: Adopting by hand (`OSDB-12` exits 1 and adopts
        nothing)."""
        before = issued_keys()
        with self.assertRaises(CommandError) as caught:
            adopt("OSDB-12")
        self.assertIn("OSDB-12", str(caught.exception))
        self.assertEqual(issued_keys(), before)

    def test_the_first_malformed_argument_is_named(self) -> None:
        """Requirement: Issued IDs (a message naming the first argument
        that is not a procedure or sequence ID, adopting nothing)."""
        before = issued_keys()
        with self.assertRaises(CommandError) as caught:
            adopt("OSDB-0012", "SEQ-0009", "nonsense", "OSDB-12")
        self.assertIn("nonsense", str(caught.exception))
        self.assertEqual(issued_keys(), before)

    def test_what_is_no_id(self) -> None:
        """Requirement: Issued IDs (a procedure or sequence ID)."""
        for text in ("OSDB-12", "OSDB-00012", "SEQ-12", "SEQ-00012",
                     "XYZ-0012", "OSDB0012", "OSDB-001a", "0012", " ",
                     "OSDB-0012 SEQ-0012"):
            with self.subTest(text=text):
                with self.assertRaises(CommandError):
                    adopt(text)
        self.assertEqual(issued_keys(), sorted(DEMO_IDS))

    def test_no_argument_is_a_usage_error(self) -> None:
        """Requirement: Issued IDs (a usage error without
        arguments)."""
        with self.assertRaises(CommandError):
            adopt()
        self.assertEqual(issued_keys(), sorted(DEMO_IDS))

    def test_both_kinds_are_adopted(self) -> None:
        """Requirement: Issued IDs (adopts each named ID that is not
        issued)."""
        lines = adopt("SEQ-0005", "OSDB-0015")
        self.assertEqual(lines, ["adopted SEQ-0005", "adopted OSDB-0015"])
        self.assertEqual(issued_keys(), sorted(
            [*DEMO_IDS, "SEQ-0005", "OSDB-0015"]))

    def test_an_adopted_id_is_below_the_next_one(self) -> None:
        """Requirement: Issued IDs (one above the highest issued one)."""
        adopt("OSDB-0015", "SEQ-0005")
        token = make_token("klehmann")
        self.assertEqual(
            request_id(self.client, "procedure", token).json(),
            {"id": "OSDB-0016"})
        self.assertEqual(
            request_id(self.client, "sequence", token).json(),
            {"id": "SEQ-0006"})

    def test_an_id_is_adopted_once(self) -> None:
        """Requirement: Issued IDs (each named ID that is not
        issued)."""
        self.assertEqual(adopt("OSDB-0012"), ["adopted OSDB-0012"])
        self.assertEqual(adopt("OSDB-0012"), ["OSDB-0012 was issued"])
        self.assertEqual(issued_keys().count("OSDB-0012"), 1)

    def test_an_id_issued_to_an_account_stays_with_it(self) -> None:
        """Requirement: Issued IDs (an ID that was issued is said to
        be)."""
        request_id(self.client, "procedure", make_token("klehmann"))
        self.assertEqual(adopt("OSDB-0010"), ["OSDB-0010 was issued"])
        self.assertEqual(issued_to("OSDB-0010"), "klehmann")

    def test_the_way_back_after_a_restore(self) -> None:
        """Design: Reconciling by hand (the next import is refused,
        naming the IDs issued after the dump; the operator adopts them
        and the next build is accepted)."""
        data = with_procedure("OSDB-0010", "OSDB-0011")
        done = post(self.client, after_the_latest(data))
        self.assertEqual(done.json()["outcome"], "refused", done.content)
        from collection.models import Import
        errors = Import.objects.get(pk=done.json()["import"]).errors
        self.assertEqual(
            errors.splitlines(),
            ["OSDB-0010: not issued by the lab application",
             "OSDB-0011: not issued by the lab application"])
        adopt("OSDB-0010", "OSDB-0011")
        again = post(self.client, after_the_latest(data))
        self.assertEqual(again.json()["outcome"], "accepted",
                         again.content)
