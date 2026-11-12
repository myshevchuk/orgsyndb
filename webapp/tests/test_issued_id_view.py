"""Tests of the ID path (collection-import: Issued IDs, ``POST
/lab/collection/ids/``)."""

import json
from datetime import datetime
from typing import Any

from django.test import Client, override_settings

from . import BERLIN
from .collection_support import (IDS, TOKEN, ImportCase, issue_ids,
                                 issued_keys, issued_to, make_token,
                                 manifest, post, refused, request_id)
from .demo_support import DAY, SeededCase

DEMO_IDS = [*(f"OSDB-{number:04d}" for number in range(1, 10)),
            "SEQ-0001", "SEQ-0002"]


def answer(case: Any, response: Any) -> Any:
    """The JSON body of ``response``, asserting that it is JSON."""
    case.assertTrue(response["Content-Type"].startswith(
        "application/json"), response["Content-Type"])
    return json.loads(response.content)


def raw(client: Any, body: str, token: str | None) -> Any:
    """Post the text ``body`` to the ID path, signed with ``token``
    unless it is None."""
    headers = ({} if token is None
               else {"HTTP_AUTHORIZATION": f"Bearer {token}"})
    return client.post(IDS, body, content_type="application/json",
                       **headers)


class TurnTests(SeededCase):
    """The demo data set is written: its IDs are issued."""

    def test_two_ids_in_turn(self) -> None:
        """Scenario: Two IDs in turn."""
        first = request_id(self.client, "procedure",
                           make_token("klehmann"))
        second = request_id(self.client, "procedure",
                            make_token("tbauer"))
        self.assertEqual((first.status_code, answer(self, first)),
                         (201, {"id": "OSDB-0010"}))
        self.assertEqual((second.status_code, answer(self, second)),
                         (201, {"id": "OSDB-0011"}))
        self.assertEqual(issued_to("OSDB-0010"), "klehmann")
        self.assertEqual(issued_to("OSDB-0011"), "tbauer")

    def test_a_sequence_id(self) -> None:
        """Scenario: A sequence ID."""
        done = request_id(self.client, "sequence", make_token("klehmann"))
        self.assertEqual((done.status_code, answer(self, done)),
                         (201, {"id": "SEQ-0003"}))
        self.assertEqual(issued_to("SEQ-0003"), "klehmann")

    def test_the_kinds_count_apart(self) -> None:
        """Requirement: Issued IDs (the ID of that kind one above the
        highest issued one)."""
        token = make_token("klehmann")
        got = [answer(self, request_id(self.client, kind, token))["id"]
               for kind in ("sequence", "procedure", "sequence",
                            "procedure")]
        self.assertEqual(got, ["SEQ-0003", "OSDB-0010", "SEQ-0004",
                               "OSDB-0011"])

    def test_the_time_of_issue_is_kept(self) -> None:
        """Requirement: Issued IDs (when it was issued)."""
        from collection.models import IssuedId
        request_id(self.client, "procedure", make_token("klehmann"))
        self.assertEqual(
            IssuedId.objects.get(key="OSDB-0010").issued_at,
            datetime(DAY.year, DAY.month, DAY.day, 19, tzinfo=BERLIN))

    def test_each_id_is_kept_once(self) -> None:
        """Requirement: Issued IDs (keep each issued ID once)."""
        token = make_token("klehmann")
        for _ in range(3):
            request_id(self.client, "procedure", token)
        self.assertEqual(issued_keys(), sorted(
            [*DEMO_IDS, "OSDB-0010", "OSDB-0011", "OSDB-0012"]))

    def test_gaps_are_not_filled(self) -> None:
        """Requirement: Issued IDs (one above the highest issued one,
        an adopted one included)."""
        issue_ids("OSDB-0020", "SEQ-0007")
        token = make_token("klehmann")
        self.assertEqual(
            answer(self, request_id(self.client, "procedure",
                                    token))["id"], "OSDB-0021")
        self.assertEqual(
            answer(self, request_id(self.client, "sequence",
                                    token))["id"], "SEQ-0008")

    def test_the_token_decides_who_takes_the_id(self) -> None:
        """Requirement: Issued IDs (issues to the token's account),
        Access tokens (a session alone is not a token)."""
        self.client.force_login(self.account("tbauer"))
        done = request_id(self.client, "procedure",
                          make_token("klehmann"))
        self.assertEqual(done.status_code, 201, done.content)
        self.assertEqual(issued_to("OSDB-0010"), "klehmann")

    def test_the_path_is_exempt_from_csrf_checks(self) -> None:
        """Requirement: Issued IDs (the path is exempt from CSRF
        checks)."""
        done = request_id(Client(enforce_csrf_checks=True), "procedure",
                          make_token("klehmann"))
        self.assertEqual(done.status_code, 201, done.content)

    def test_ten_thousand_is_not_issued(self) -> None:
        """Requirement: Issued IDs (for a kind whose ID `9999` is
        issued, 409 with an error)."""
        issue_ids("OSDB-9999")
        token = make_token("klehmann")
        done = request_id(self.client, "procedure", token)
        self.assertEqual(done.status_code, 409)
        self.assertTrue(answer(self, done)["error"])
        self.assertEqual(issued_keys(), sorted([*DEMO_IDS, "OSDB-9999"]))
        other = request_id(self.client, "sequence", token)
        self.assertEqual(
            (other.status_code, answer(self, other)),
            (201, {"id": "SEQ-0003"}))

    def test_no_sequence_beyond_9999(self) -> None:
        """Requirement: Issued IDs (a kind whose ID `9999` is issued)."""
        issue_ids("SEQ-9999")
        token = make_token("klehmann")
        done = request_id(self.client, "sequence", token)
        self.assertEqual(done.status_code, 409)
        self.assertTrue(answer(self, done)["error"])
        self.assertEqual(
            request_id(self.client, "procedure", token).status_code, 201)


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class RefusalTests(SeededCase):
    """Requirement: Issued IDs (401, 400 and 409; none of them issues
    anything)."""

    def untouched(self) -> None:
        self.assertEqual(issued_keys(), sorted(DEMO_IDS))

    def test_a_session_is_not_a_token(self) -> None:
        """Scenario: A session is not a token."""
        self.client.force_login(self.account("klehmann"))
        done = request_id(self.client, "procedure")
        self.assertEqual(done.status_code, 401)
        answer(self, done)
        self.untouched()

    def test_no_valid_token(self) -> None:
        """Requirement: Issued IDs (a request without a valid token
        answers 401)."""
        valid = make_token("klehmann")
        for name, header in {
                "no header": None,
                "an empty token": "Bearer ",
                "an unknown token": "Bearer osdb_" + "A" * 43,
                "no scheme": valid,
                "the Basic scheme": f"Basic {valid}",
                "the Token scheme": f"Token {valid}",
                "the builder's token": f"Bearer {TOKEN}"}.items():
            with self.subTest(name=name):
                extra = ({} if header is None
                         else {"HTTP_AUTHORIZATION": header})
                done = self.client.post(
                    IDS, json.dumps({"kind": "procedure"}),
                    content_type="application/json", **extra)
                self.assertEqual(done.status_code, 401)
                answer(self, done)
        self.untouched()

    def test_a_session_does_not_help_a_wrong_token(self) -> None:
        """Requirement: Issued IDs (401, whether or not it carries a
        signed-in session)."""
        self.client.force_login(self.account("klehmann"))
        done = request_id(self.client, "procedure", "osdb_" + "A" * 43)
        self.assertEqual(done.status_code, 401)
        self.untouched()

    def test_the_token_is_judged_before_the_body(self) -> None:
        """Requirement: Issued IDs (a request without a valid token
        answers 401)."""
        for body in ("not json", "[]", "{}", '{"kind": "batch"}'):
            with self.subTest(body=body):
                done = raw(self.client, body, None)
                self.assertEqual(done.status_code, 401)
        self.untouched()

    def test_a_body_of_another_shape(self) -> None:
        """Requirement: Issued IDs (a body of another shape answers
        400)."""
        token = make_token("klehmann")
        for body in ("not json", "", "[]", "null", "{}", '"procedure"',
                     '["procedure"]', '{"kind": "batch"}',
                     '{"kind": "Procedure"}', '{"kind": ""}',
                     '{"kind": 1}', '{"kind": null}',
                     '{"kind": ["procedure"]}', '{"type": "procedure"}'):
            with self.subTest(body=body):
                done = raw(self.client, body, token)
                self.assertEqual(done.status_code, 400)
                self.assertTrue(answer(self, done)["error"])
        self.untouched()

    def test_a_request_that_is_no_post(self) -> None:
        """Requirement: Issued IDs (the path never redirects and
        answers JSON)."""
        token = make_token("klehmann")
        for method in ("get", "put", "delete", "patch"):
            with self.subTest(method=method, signed=True):
                done = getattr(self.client, method)(
                    IDS, HTTP_AUTHORIZATION=f"Bearer {token}")
                self.assertNotIn(done.status_code, (200, 201, 301, 302))
                answer(self, done)
            with self.subTest(method=method, signed=False):
                done = getattr(self.client, method)(IDS)
                self.assertNotIn(done.status_code, (200, 201, 301, 302))
        self.untouched()

    def test_a_signed_out_request_does_not_redirect(self) -> None:
        """Requirement: Permissions (the ID path does not redirect)."""
        done = request_id(self.client, "procedure")
        self.assertEqual(done.status_code, 401)
        self.assertFalse(done.has_header("Location"))


class BeforeAnImportTests(ImportCase):
    """The demo registry is loaded and no import exists."""

    def test_not_before_an_import(self) -> None:
        """Scenario: Not before an import."""
        token = make_token("klehmann")
        for kind in ("procedure", "sequence"):
            with self.subTest(kind=kind):
                done = request_id(self.client, kind, token)
                self.assertEqual(done.status_code, 409)
                self.assertTrue(answer(self, done)["error"])
        self.assertEqual(issued_keys(), [])

    def test_a_refusal_is_no_import(self) -> None:
        """Requirement: Issued IDs (a request made before the
        application has accepted an import answers 409)."""
        token = make_token("klehmann")
        done = self.send(refused(["x: error: y"]))
        self.assertEqual(done.json()["outcome"], "refused")
        self.assertEqual(
            request_id(self.client, "procedure", token).status_code, 409)
        self.assertEqual(issued_keys(), [])

    def test_a_bad_token_is_refused_whatever_the_state(self) -> None:
        """Requirement: Issued IDs (without a valid token, 401)."""
        done = request_id(self.client, "procedure", "osdb_" + "A" * 43)
        self.assertEqual(done.status_code, 401)

    def test_the_first_accepted_import_opens_the_path(self) -> None:
        """Requirement: Issued IDs (issues after the first accepted
        import, which adopted the IDs of the collection)."""
        token = make_token("klehmann")
        self.accept()
        done = request_id(self.client, "procedure", token)
        self.assertEqual((done.status_code, answer(self, done)),
                         (201, {"id": "OSDB-0010"}))

    def test_an_empty_collection_starts_at_one(self) -> None:
        """Requirement: Issued IDs (the ID one above the highest
        issued one: the first is 0001)."""
        token = make_token("klehmann")
        done = self.send(manifest(procedures=[], sequences=[],
                                  deleted=[]))
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        self.assertEqual(
            answer(self, request_id(self.client, "procedure",
                                    token))["id"], "OSDB-0001")
        self.assertEqual(
            answer(self, request_id(self.client, "sequence",
                                    token))["id"], "SEQ-0001")

    def test_ids_deleted_before_are_not_issued_again(self) -> None:
        """Requirement: Issued IDs (the IDs of `deleted` are adopted,
        so that the next one lies above them)."""
        token = make_token("klehmann")
        self.accept(procedures=[], sequences=[],
                    deleted=["OSDB-0007", "SEQ-0003"])
        self.assertEqual(
            answer(self, request_id(self.client, "procedure",
                                    token))["id"], "OSDB-0008")
        self.assertEqual(
            answer(self, request_id(self.client, "sequence",
                                    token))["id"], "SEQ-0004")


class BuilderTests(ImportCase):
    """The ID path and the manifest path do not share a token."""

    def test_an_access_token_is_no_builder_token(self) -> None:
        """Requirement: Manifest (the builder's token, not an
        account's)."""
        done = post(self.client, manifest(), make_token("klehmann"))
        self.assertEqual(done.status_code, 403)
