"""Tests of the manifest view's gate (collection-import: Manifest): the
token, the method and the shape of the body. What an accepted manifest
does is in ``test_collection_accept``."""

import json
from typing import Any

from django.test import Client, override_settings

from . import make_user
from .collection_support import (MANIFEST, TOKEN, ImportCase, counts,
                                 demo_collection, manifest, post, refused)


def no_import(case: ImportCase) -> None:
    """Assert that nothing was recorded."""
    case.assertEqual(sum(counts().values()), 0, counts())


def json_answer(case: ImportCase, response: Any) -> Any:
    """The JSON body of ``response``, asserting that it is JSON; None
    for an answer without a body."""
    case.assertTrue(response["Content-Type"].startswith(
        "application/json"), response["Content-Type"])
    return json.loads(response.content) if response.content else None


@override_settings(ORGSYNDB_BUILDER_TOKEN="")
class NoTokenTests(ImportCase):

    def test_no_token_configured(self) -> None:
        """Scenario: No token configured."""
        for token in (TOKEN, "", "any", None):
            with self.subTest(token=token):
                done = post(self.client, manifest(), token)
                self.assertEqual(done.status_code, 404)
                json_answer(self, done)
                no_import(self)

    def test_every_method_answers_404(self) -> None:
        """Requirement: Manifest (with that setting empty the path
        answers 404 to every request)."""
        for method in ("get", "put", "delete", "patch", "head"):
            with self.subTest(method=method):
                done = getattr(self.client, method)(
                    MANIFEST, HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
                self.assertEqual(done.status_code, 404)
                json_answer(self, done)

    def test_an_empty_bearer_does_not_get_in(self) -> None:
        """Requirement: Manifest (the empty token is no token)."""
        done = post(self.client, manifest(), "")
        self.assertEqual(done.status_code, 404)
        json_answer(self, done)
        no_import(self)


class WrongTokenTests(ImportCase):

    def test_wrong_token(self) -> None:
        """Scenario: Wrong token."""
        for token in ("other", None):
            with self.subTest(token=token):
                done = post(self.client, manifest(), token)
                self.assertEqual(done.status_code, 403)
                json_answer(self, done)
                no_import(self)

    def test_a_token_that_is_close_is_wrong(self) -> None:
        """Requirement: Manifest (the token equals
        `ORGSYNDB_BUILDER_TOKEN`)."""
        for token in (TOKEN[:-1], TOKEN + "x", TOKEN.upper(), ""):
            with self.subTest(token=token):
                done = post(self.client, manifest(), token)
                self.assertEqual(done.status_code, 403)
        no_import(self)

    def test_the_token_is_a_bearer_token(self) -> None:
        """Requirement: Manifest (`Authorization: Bearer <token>`)."""
        for header in (TOKEN, f"Basic {TOKEN}", f"Token {TOKEN}"):
            with self.subTest(header=header):
                done = self.client.post(
                    MANIFEST, json.dumps(manifest()),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=header)
                self.assertEqual(done.status_code, 403)
        no_import(self)

    def test_the_token_is_checked_before_the_body(self) -> None:
        """Requirement: Manifest (a wrong token answers 403, whatever
        the body)."""
        for body in ("not json", "[]", ""):
            with self.subTest(body=body):
                done = post(self.client, body, "other")
                self.assertEqual(done.status_code, 403)
        no_import(self)

    def test_another_method_with_a_wrong_token_is_not_let_in(self) -> None:
        """Requirement: Manifest (none of these answers records
        anything)."""
        done = self.client.get(MANIFEST, HTTP_AUTHORIZATION="Bearer other")
        self.assertIn(done.status_code, (403, 405))
        no_import(self)


class MalformedTests(ImportCase):

    def bodies(self) -> list[tuple[str, Any]]:
        """Each way a body is wrong, by what is wrong with it."""
        good = manifest()
        built = {"without commit": {k: v for k, v in good.items()
                                    if k != "commit"}}
        for key in ("format", "build", "committed_at", "base", "snapshot",
                    "tooling", "trigger", "pusher", "outcome", "release",
                    "language", "procedures", "sequences"):
            built[f"without {key}"] = {k: v for k, v in good.items()
                                       if k != key}
        changes: dict[str, dict[str, Any]] = {
            "a commit of 39 digits": {"commit": "a" * 39},
            "a commit of 41 digits": {"commit": "a" * 41},
            "a commit in capitals": {"commit": "A" * 40},
            "a commit that is no hexadecimal": {"commit": "g" * 40},
            "a commit that is a number": {"commit": 12},
            "a snapshot of 63 digits": {"snapshot": "d" * 63},
            "a snapshot in capitals": {"snapshot": "D" * 64},
            "a tooling of 39 digits": {"tooling": "b" * 39},
            "a trigger of push": {"trigger": "push"},
            "a pusher that is a number": {"pusher": 7},
            "a pusher that is a list": {"pusher": ["jkoch"]},
            "an outcome that is neither": {"outcome": "pending"},
            "a format of 2": {"format": 2},
            "a format that is text": {"format": "1"},
            "a build that is no UUID": {"build": "not-a-uuid"},
            "a time without an offset": {
                "committed_at": "2026-11-09T14:30:00"},
            "a time that is no time": {"committed_at": "yesterday"},
            "a base that is text": {"base": "one"},
            "a base that is a list": {"base": [1]},
            "an empty release": {"release": ""},
            "a release that is a number": {"release": 1},
            "procedures that are no list": {"procedures": {}},
            "sequences that are no list": {"sequences": "none"},
            "a procedure that is no table": {"procedures": ["OSDB-0001"]},
        }
        for name, change in changes.items():
            built[name] = {**good, **change}
        huge = json.loads(json.dumps(good))
        huge["procedures"][0]["entries"][0]["products"][0][
            "yield_percent"] = 10 ** 400
        built["a yield too large for a float"] = huge
        refusing = refused(["x: error: y"])
        refusals = {
            "a refusal without a pusher": {
                k: v for k, v in refusing.items() if k != "pusher"},
            "a refusal with a pusher that is a number": {
                **refusing, "pusher": 7},
            "a refusal without errors": {
                k: v for k, v in refusing.items() if k != "errors"},
            "a refusal with an empty list": {**refusing, "errors": []},
            "a refusal with errors that are no list": {
                **refusing, "errors": "x: error: y"},
            "a refusal with an error that is no text": {
                **refusing, "errors": ["x: error: y", 2]},
        }
        return [*built.items(), *refusals.items(),
                ("text that is no JSON", "not json"),
                ("an empty body", ""),
                ("a list", "[]"), ("a string", '"manifest"'),
                ("null", "null"), ("a number", "1"),
                ("an empty table", "{}")]

    def test_malformed_manifests_are_refused(self) -> None:
        """Scenario: Malformed manifest."""
        for name, body in self.bodies():
            with self.subTest(name=name):
                done = post(self.client, body)
                self.assertEqual(done.status_code, 400, done.content)
                answer = json_answer(self, done)
                self.assertIsInstance(answer.get("error"), str)
                self.assertTrue(answer["error"])
        no_import(self)

    def test_a_refusal_needs_no_release_or_procedures(self) -> None:
        """Requirement: Manifest (for `refused`, `errors` and nothing
        of the collection half)."""
        done = post(self.client, refused(["x: error: y", "build failed"]))
        self.assertEqual(done.status_code, 200, done.content)

    def test_a_collection_may_be_empty(self) -> None:
        """Requirement: Manifest (for `built`, `language`, `procedures`
        and `sequences`: lists, which may be empty)."""
        done = post(self.client, manifest(procedures=[], sequences=[]))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "accepted")

    def test_a_manifest_is_valid_before_it_is_broken(self) -> None:
        """The bodies above break a manifest the view takes."""
        done = post(self.client, manifest())
        self.assertEqual(done.status_code, 200, done.content)


class DeletedTests(ImportCase):
    """Requirement: Manifest (for `built`, `deleted` as `tools/orgsyndb
    manifest` prints it)."""

    def test_a_built_manifest_needs_deleted(self) -> None:
        """Requirement: Manifest (for `built`, `release`, `language`,
        `procedures`, `sequences` and `deleted`)."""
        body = manifest()
        body.pop("deleted", None)
        done = post(self.client, body)
        self.assertEqual(done.status_code, 400, done.content)
        self.assertIn("deleted", json_answer(self, done)["error"])
        no_import(self)

    def test_deleted_that_is_no_list_of_text(self) -> None:
        """Requirement: Manifest (a body that is not a JSON object of
        these keys and types answers 400)."""
        for name, value in {
                "text": "OSDB-0012", "a table": {"OSDB-0012": True},
                "null": None, "a number": 12,
                "a list holding a number": ["OSDB-0012", 12],
                "a list holding null": [None],
                "a list holding a list": [["OSDB-0012"]]}.items():
            with self.subTest(deleted=name):
                done = post(self.client, manifest(deleted=value))
                self.assertEqual(done.status_code, 400, done.content)
                self.assertTrue(json_answer(self, done)["error"])
        no_import(self)

    def test_deleted_may_be_empty(self) -> None:
        """Requirement: Manifest (`deleted`, a list of IDs, which may
        be empty)."""
        done = self.send(self.follow(deleted=[]))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "accepted")

    def test_deleted_may_hold_ids(self) -> None:
        """Requirement: Manifest (`deleted`, a list of IDs)."""
        done = self.send(self.follow(deleted=["OSDB-0012", "SEQ-0004"]))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "accepted")

    def test_a_refusal_needs_no_deleted(self) -> None:
        """Requirement: Manifest (for `refused`, `errors` and nothing
        of the collection half)."""
        body = refused(["x: error: y"])
        self.assertNotIn("deleted", body)
        done = post(self.client, body)
        self.assertEqual(done.status_code, 200, done.content)

    def test_the_demo_manifest_lists_no_deleted_id(self) -> None:
        """Scenario: Nothing deleted from the demo (the file the demo
        data applies)."""
        self.assertEqual(demo_collection().get("deleted"), [])


class MethodTests(ImportCase):

    def test_not_a_post(self) -> None:
        """Scenario: Not a POST."""
        done = self.client.get(MANIFEST,
                               HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        self.assertEqual(done.status_code, 405)
        json_answer(self, done)
        no_import(self)

    def test_no_other_method_is_taken(self) -> None:
        """Requirement: Manifest (a method other than POST answers
        405)."""
        for method in ("put", "delete", "patch"):
            with self.subTest(method=method):
                done = getattr(self.client, method)(
                    MANIFEST, json.dumps(manifest()),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
                self.assertEqual(done.status_code, 405)
        no_import(self)


class AccessTests(ImportCase):

    def test_the_view_is_exempt_from_csrf_checks(self) -> None:
        """Requirement: Manifest (the view is exempt from CSRF
        checks)."""
        client = Client(enforce_csrf_checks=True)
        done = post(client, manifest())
        self.assertEqual(done.status_code, 200, done.content)

    def test_no_sign_in_is_needed_and_none_redirects(self) -> None:
        """Requirement: Permissions (the manifest path is the one write
        without a signed-in user, and never redirects)."""
        done = post(self.client, manifest())
        self.assertEqual(done.status_code, 200, done.content)
        for token in ("other", None):
            with self.subTest(token=token):
                done = post(self.client, manifest(), token)
                self.assertEqual(done.status_code, 403)
        done = self.client.get(MANIFEST)
        self.assertNotIn(done.status_code, (301, 302))

    def test_a_signed_in_user_has_no_other_way_in(self) -> None:
        """Requirement: Manifest (the token, not a session, signs the
        request)."""
        self.client.force_login(make_user("kl", "KL"))
        done = post(self.client, manifest(), None)
        self.assertEqual(done.status_code, 403)
        no_import(self)

    def test_every_answer_is_json(self) -> None:
        """Requirement: Manifest (every answer is JSON)."""
        answers = [post(self.client, manifest(), "other"),
                   post(self.client, "not json"),
                   self.client.get(MANIFEST,
                                   HTTP_AUTHORIZATION=f"Bearer {TOKEN}"),
                   post(self.client, manifest())]
        for done in answers:
            with self.subTest(status=done.status_code):
                json_answer(self, done)
