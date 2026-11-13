"""Tests of the check path (collection-import: Checking a manifest):
``POST /lab/collection/check/`` runs the import checks on the collection
half of a manifest, for the builder's gate, and records nothing."""

import json
from typing import Any
from unittest import mock

from django.test import Client, override_settings

from . import make_user
from .collection_support import (MANIFEST, TOKEN, ImportCase, by_id,
                                 copy_procedure, counts, demo_collection,
                                 dump, ids_of, issued_keys, make_token,
                                 manifest, post, request_id)

CHECK = "/lab/collection/check/"


def check(client: Any, body: Any, token: str | None = TOKEN,
          **extra: Any) -> Any:
    """Post ``body``, a table or text, to the check path, signed with
    ``token``, or not signed when it is None."""
    text = body if isinstance(body, str) else json.dumps(body)
    headers = ({} if token is None
               else {"HTTP_AUTHORIZATION": f"Bearer {token}"})
    return client.post(CHECK, text, content_type="application/json",
                       **headers, **extra)


def answer_of(case: ImportCase, response: Any) -> Any:
    """The JSON body of ``response``, asserting that it is JSON."""
    case.assertTrue(response["Content-Type"].startswith(
        "application/json"), response["Content-Type"])
    return json.loads(response.content)


def unissued(data: dict[str, Any]) -> dict[str, Any]:
    """The collection half ``data`` with a procedure ``OSDB-0099`` the
    application never issued."""
    data["procedures"].append(copy_procedure(data, "OSDB-0008",
                                             "OSDB-0099"))
    return data


class CheckCase(ImportCase):

    def checked(self, body: Any) -> list[str]:
        """Post ``body`` to the check path; assert the answer is 200
        with a list of texts under ``errors``; return that list."""
        done = check(self.client, body)
        self.assertEqual(done.status_code, 200, done.content)
        found = answer_of(self, done)
        self.assertEqual(list(found), ["errors"], found)
        self.assertIsInstance(found["errors"], list)
        for error in found["errors"]:
            self.assertIsInstance(error, str)
        return found["errors"]

    def assert_nothing_written(self, before: dict[str, Any]) -> None:
        """Assert that no row of the collection changed since
        ``before``, a ``dump()``."""
        self.assertEqual(dump(), before)


class CleanCollectionTests(CheckCase):

    def test_a_clean_collection_before_the_first_import(self) -> None:
        """Scenario: A clean collection."""
        self.assertEqual(self.checked(demo_collection()), [])
        self.assertEqual(sum(counts().values()), 0, counts())
        self.assertEqual(issued_keys(), [])

    def test_a_clean_collection_after_an_import(self) -> None:
        """Scenario: A clean collection (and no further import
        exists)."""
        self.accept()
        before = dump()
        self.assertEqual(self.checked(demo_collection()), [])
        self.assert_nothing_written(before)
        self.assertEqual(len(before["Import"]), 1)

    def test_the_answer_is_json_with_nothing_but_errors(self) -> None:
        """Requirement: Checking a manifest (answer 200 with
        `{"errors": [...]}`)."""
        done = check(self.client, demo_collection())
        self.assertEqual(done.status_code, 200)
        self.assertEqual(answer_of(self, done), {"errors": []})

    def test_it_can_be_asked_again(self) -> None:
        """Requirement: Checking a manifest (it changes nothing)."""
        data = unissued(demo_collection())
        self.accept()
        first = self.checked(data)
        self.assertEqual(self.checked(data), first)
        self.assertEqual(self.checked(demo_collection()), [])


class UnissuedIdTests(CheckCase):

    def test_an_unissued_id_after_an_import(self) -> None:
        """Scenario: An unissued ID."""
        self.accept()
        before = dump()
        errors = self.checked(unissued(demo_collection()))
        self.assertEqual(errors, [
            "OSDB-0099: not issued by the lab application"])
        self.assert_nothing_written(before)
        self.assertEqual(len(before["Import"]), 1)
        self.assertNotIn("OSDB-0099", issued_keys())

    def test_an_unissued_sequence_after_an_import(self) -> None:
        """Requirement: Checking a manifest (the issued IDs as they are:
        a sequence too)."""
        self.accept()
        data = demo_collection()
        data["sequences"].append({**by_id(data["sequences"], "SEQ-0001"),
                                  "id": "SEQ-0099"})
        self.assertEqual(self.checked(data), [
            "SEQ-0099: not issued by the lab application"])

    def test_an_id_issued_since_is_not_an_error(self) -> None:
        """Requirement: Checking a manifest (against the issued IDs as
        they are)."""
        self.accept()
        data = unissued(demo_collection())
        self.assertEqual(len(self.checked(data)), 1)
        issued = request_id(self.client, "procedure",
                            make_token("klehmann"))
        self.assertEqual(issued.status_code, 201, issued.content)
        data["procedures"][-1]["id"] = issued.json()["id"]
        self.assertEqual(self.checked(data), [])

    def test_the_deleted_ids_are_not_adopted_after_an_import(self) -> None:
        """Requirement: Checking a manifest (it issues no ID; later
        imports ignore `deleted`)."""
        self.accept()
        before = issued_keys()
        data = demo_collection()
        data["deleted"] = ["OSDB-0012"]
        self.assertEqual(self.checked(data), [])
        self.assertEqual(issued_keys(), before)


class BeforeTheFirstImportTests(CheckCase):

    def test_an_unissued_id_is_adopted_by_the_first_import(self) -> None:
        """Scenario: Before the first import."""
        self.assertEqual(self.checked(unissued(demo_collection())), [])
        self.assertEqual(issued_keys(), [])
        self.assertEqual(sum(counts().values()), 0, counts())

    def test_deleted_ids_issue_nothing(self) -> None:
        """Requirement: Checking a manifest (before the first accepted
        import `deleted` counts as issued; the check issues no ID)."""
        data = unissued(demo_collection())
        data["deleted"] = ["OSDB-0012", "SEQ-0004"]
        self.assertEqual(self.checked(data), [])
        self.assertEqual(issued_keys(), [])

    def test_the_other_checks_still_apply(self) -> None:
        """Requirement: Checking a manifest (exactly the problems an
        import would be refused for)."""
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["entries"][0]["products"][
            0]["compound"] = "no-such-substance"
        self.assertEqual(self.checked(data), [
            'OSDB-0002: unknown substance "no-such-substance"'])
        self.assertEqual(issued_keys(), [])

    def test_a_check_issues_no_id(self) -> None:
        """Requirement: Checking a manifest (it issues no ID): the first
        import accepted afterwards still adopts every ID."""
        self.checked(unissued(demo_collection()))
        self.accept()
        self.assertEqual(
            issued_keys(),
            sorted(ids_of(demo_collection())))


class SameErrorsAsAnImportTests(CheckCase):

    def broken(self) -> dict[str, Any]:
        """The demo collection with several kinds of error, among them
        an unissued ID, found in different procedures and sequences."""
        data = unissued(demo_collection())
        by_id(data["procedures"], "OSDB-0002")["entries"][0]["products"][
            0]["compound"] = "no-such-substance"
        by_id(data["procedures"], "OSDB-0003")["reaction_type"] = \
            "no-such-type"
        by_id(data["procedures"], "OSDB-0005")["authors"] = ["nobody"]
        by_id(data["sequences"], "SEQ-0002")["target"] = "no-such-target"
        return data

    def test_the_errors_and_their_order_are_the_imports(self) -> None:
        """Requirement: Checking a manifest (each a string, in the
        order the import reports them)."""
        self.accept()
        data = self.broken()
        before = dump()
        errors = self.checked(data)
        self.assertGreaterEqual(len(errors), 5, errors)
        self.assert_nothing_written(before)
        refused = self.refuse(data)
        from collection.models import Import
        record = Import.objects.get(pk=refused["import"])
        self.assertEqual(errors, record.errors.splitlines())

    def test_the_errors_are_the_imports_before_the_first_import(
            self) -> None:
        """Requirement: Checking a manifest (before the first import
        the IDs count as issued, as the import counts them)."""
        data = self.broken()
        errors = self.checked(data)
        self.assertGreaterEqual(len(errors), 4, errors)
        self.assertFalse([error for error in errors
                          if "not issued" in error], errors)
        refused = self.refuse(data)
        from collection.models import Import
        record = Import.objects.get(pk=refused["import"])
        self.assertEqual(errors, record.errors.splitlines())

    def test_a_collection_the_import_accepts_has_no_errors(self) -> None:
        """Requirement: Checking a manifest (an empty list when there
        is none)."""
        self.accept()
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["title"] = "Another title"
        self.assertEqual(self.checked(data), [])
        self.accept(data)

    def test_the_registry_is_taken_as_it_is(self) -> None:
        """Requirement: Checking a manifest (against the registry as it
        is; no snapshot digest or base is judged)."""
        from registry.models import Substance
        self.accept()
        found = Substance.objects.get(key="cinnamic-acid")
        found.note = "changed after the import"
        found.save()
        self.assertEqual(self.checked(demo_collection()), [])
        data = demo_collection()
        by_id(data["sequences"], "SEQ-0001")["target"] = "no-such-target"
        self.assertEqual(self.checked(data), [
            'SEQ-0001: unknown target "no-such-target"'])


class WritesNothingTests(CheckCase):

    def test_it_takes_no_lock(self) -> None:
        """Requirement: Checking a manifest (it takes no lock)."""
        with mock.patch("orgsyndb_web.lock.hold") as hold:
            self.assertEqual(self.checked(demo_collection()), [])
            self.assertFalse(hold.called)
        with mock.patch("orgsyndb_web.lock.hold") as hold:
            done = self.send(manifest())
            self.assertEqual(done.status_code, 200, done.content)
            self.assertTrue(hold.called, "the manifest path holds it")

    def test_an_error_writes_nothing_either(self) -> None:
        """Requirement: Checking a manifest (it records no import)."""
        before = dump()
        self.assertTrue(self.checked(self.erroneous()))
        self.assert_nothing_written(before)
        self.assertEqual(sum(counts().values()), 0)

    def erroneous(self) -> dict[str, Any]:
        data = demo_collection()
        by_id(data["procedures"], "OSDB-0002")["reaction_type"] = "none"
        return data


class TokenTests(CheckCase):

    def test_without_the_token(self) -> None:
        """Scenario: Without the token."""
        done = check(self.client, demo_collection(), None)
        self.assertEqual(done.status_code, 403)
        self.assertNotIn("errors", answer_of(self, done))
        self.assertEqual(sum(counts().values()), 0)

    def test_a_wrong_token(self) -> None:
        """Requirement: Checking a manifest (the answers of the
        manifest path to a wrong token)."""
        for token in ("other", TOKEN[:-1], TOKEN + "x", TOKEN.upper(), ""):
            with self.subTest(token=token):
                done = check(self.client, demo_collection(), token)
                self.assertEqual(done.status_code, 403)
                self.assertNotIn("errors", answer_of(self, done))

    def test_the_token_is_a_bearer_token(self) -> None:
        """Requirement: Checking a manifest (`Authorization: Bearer
        <token>`)."""
        for header in (TOKEN, f"Basic {TOKEN}", f"Token {TOKEN}"):
            with self.subTest(header=header):
                done = self.client.post(
                    CHECK, json.dumps(demo_collection()),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=header)
                self.assertEqual(done.status_code, 403)

    def test_the_token_is_checked_before_the_body(self) -> None:
        """Requirement: Checking a manifest (a wrong token answers 403,
        whatever the body)."""
        for body in ("not json", "[]", ""):
            with self.subTest(body=body):
                done = check(self.client, body, "other")
                self.assertEqual(done.status_code, 403)

    def test_a_session_is_not_a_token(self) -> None:
        """Requirement: Checking a manifest (the token signs the
        request)."""
        self.client.force_login(make_user("kl", "KL"))
        done = check(self.client, demo_collection(), None)
        self.assertEqual(done.status_code, 403)

    def test_the_view_is_exempt_from_csrf_checks(self) -> None:
        """Requirement: Checking a manifest (as the manifest path)."""
        done = check(Client(enforce_csrf_checks=True), demo_collection())
        self.assertEqual(done.status_code, 200, done.content)

    def test_it_never_redirects(self) -> None:
        """Requirement: Checking a manifest (as the manifest path)."""
        for done, status in (
                (check(self.client, demo_collection(), None), 403),
                (self.client.get(CHECK), 403),
                (self.client.get(
                    CHECK, HTTP_AUTHORIZATION=f"Bearer {TOKEN}"), 405)):
            self.assertEqual(done.status_code, status)


@override_settings(ORGSYNDB_BUILDER_TOKEN="")
class NoTokenConfiguredTests(CheckCase):

    def test_every_request_answers_404(self) -> None:
        """Requirement: Checking a manifest (an empty
        `ORGSYNDB_BUILDER_TOKEN`)."""
        for token in (TOKEN, "", "any", None):
            with self.subTest(token=token):
                done = check(self.client, demo_collection(), token)
                self.assertEqual(done.status_code, 404)
                self.assertNotIn("errors", answer_of(self, done))

    def test_every_method_answers_404(self) -> None:
        """Requirement: Checking a manifest (as the manifest path)."""
        for method in ("get", "put", "delete", "patch", "head"):
            with self.subTest(method=method):
                done = getattr(self.client, method)(
                    CHECK, HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
                self.assertEqual(done.status_code, 404)


class MethodTests(CheckCase):

    def test_not_a_post(self) -> None:
        """Requirement: Checking a manifest (another method answers
        405)."""
        done = self.client.get(CHECK, HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        self.assertEqual(done.status_code, 405)
        answer_of(self, done)

    def test_no_other_method_is_taken(self) -> None:
        """Requirement: Checking a manifest (another method answers
        405)."""
        for method in ("put", "delete", "patch"):
            with self.subTest(method=method):
                done = getattr(self.client, method)(
                    CHECK, json.dumps(demo_collection()),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
                self.assertEqual(done.status_code, 405)


class MalformedTests(CheckCase):

    def bodies(self) -> list[tuple[str, Any]]:
        """Each way a body is wrong, by what is wrong with it."""
        good = demo_collection()
        found: list[tuple[str, Any]] = []
        for key in ("language", "procedures", "sequences", "deleted"):
            found.append((f"without {key}",
                          {k: v for k, v in good.items() if k != key}))
        changes: dict[str, dict[str, Any]] = {
            "procedures that are no list": {"procedures": {}},
            "sequences that are no list": {"sequences": "none"},
            "a procedure that is no table": {"procedures": ["OSDB-0001"]},
            "deleted that is text": {"deleted": "OSDB-0012"},
            "deleted holding a number": {"deleted": ["OSDB-0012", 12]},
            "a language that is a number": {"language": 1},
        }
        for name, change in changes.items():
            found.append((name, {**good, **change}))
        huge = json.loads(json.dumps(good))
        huge["procedures"][0]["entries"][0]["products"][0][
            "yield_percent"] = 10 ** 400
        found.append(("a yield too large for a float", huge))
        found += [("text that is no JSON", "not json"),
                  ("an empty body", ""), ("a list", "[]"),
                  ("a string", '"manifest"'), ("null", "null"),
                  ("a number", "1"), ("an empty table", "{}")]
        return found

    def test_malformed_bodies_answer_400(self) -> None:
        """Requirement: Checking a manifest (a malformed body, as the
        manifest path answers it)."""
        for name, body in self.bodies():
            with self.subTest(name=name):
                done = check(self.client, body)
                self.assertEqual(done.status_code, 400, done.content)
                found = answer_of(self, done)
                self.assertIsInstance(found.get("error"), str)
                self.assertTrue(found["error"])
                self.assertNotIn("errors", found)
        self.assertEqual(sum(counts().values()), 0)

    def test_a_body_is_valid_before_it_is_broken(self) -> None:
        """The bodies above break a body the view takes."""
        self.assertEqual(self.checked(demo_collection()), [])

    def test_a_collection_may_be_empty(self) -> None:
        """Requirement: Checking a manifest (lists, which may be
        empty)."""
        body = {"language": "de", "procedures": [], "sequences": [],
                "deleted": []}
        self.assertEqual(self.checked(body), [])

    def test_the_manifest_path_still_takes_a_manifest(self) -> None:
        """The manifest path is untouched by the check path."""
        done = post(self.client, manifest())
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(MANIFEST, "/lab/collection/manifest/")
