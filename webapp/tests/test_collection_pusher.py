"""Tests of the pusher in a manifest and in the import it makes
(collection-import: Manifest, Imported rows)."""

from typing import Any

from django.contrib.auth import get_user_model

from .collection_support import ImportCase, refused


def account(username: str) -> Any:
    return get_user_model().objects.get(username=username)


def pushed(record: Any) -> Any:
    """The account the import RECORD names as its pusher, or a text
    that says it has no such field."""
    return getattr(record, "pushed_by", "<the import has no pushed_by>")


class PusherTests(ImportCase):

    def test_the_pusher_is_the_account_with_that_user_name(self) -> None:
        """Scenario: The pusher (`JKoch` is the account `jkoch`, an
        account no one has is none, `null` is none)."""
        named = self.accept(pusher="JKoch")
        unknown = self.accept(pusher="orgsyndb")
        nobody = self.accept(pusher=None)
        self.assertEqual(pushed(named), account("jkoch"))
        self.assertIsNone(pushed(unknown))
        self.assertIsNone(pushed(nobody))

    def test_the_user_name_is_compared_without_regard_to_case(self) -> None:
        """Requirement: Manifest (the account whose user name equals
        `pusher`, ignoring case)."""
        for name in ("jkoch", "JKOCH", "jKoCh"):
            with self.subTest(pusher=name):
                self.assertEqual(pushed(self.accept(pusher=name)),
                                 account("jkoch"))

    def test_every_account_can_be_the_pusher(self) -> None:
        """Requirement: Manifest (the account whose user name equals
        `pusher`)."""
        for name in ("klehmann", "tbauer", "aschmidt", "mwolf"):
            with self.subTest(pusher=name):
                self.assertEqual(pushed(self.accept(pusher=name)),
                                 account(name))

    def test_a_user_name_that_only_looks_alike_is_no_pusher(self) -> None:
        """Requirement: Manifest (equals `pusher`, ignoring case, not
        a prefix of it)."""
        for name in ("jko", "jkochh", "j koch", "orgsyndb"):
            with self.subTest(pusher=name):
                self.assertIsNone(pushed(self.accept(pusher=name)))

    def test_a_failed_build_names_its_pusher_too(self) -> None:
        """Requirement: Manifest (the pusher of every manifest, built or
        refused)."""
        first = self.accept()
        done = self.send(refused(["x: error: y"], base=first.pk,
                                 pusher="klehmann"))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "refused")
        from collection.models import Import
        record = Import.objects.get(pk=done.json()["import"])
        self.assertEqual(pushed(record), account("klehmann"))

    def test_a_failed_build_may_name_no_pusher(self) -> None:
        """Requirement: Manifest (`pusher`, a string or `null`)."""
        from collection.models import Import
        done = self.send(refused(["x: error: y"], pusher=None))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertIsNone(
            pushed(Import.objects.get(pk=done.json()["import"])))

    def test_the_pusher_never_refuses_an_import(self) -> None:
        """Requirement: Manifest (the pusher never refuses an import):
        a name no account has, and one that is not a user name at all,
        leave the import accepted."""
        for name in ("orgsyndb", "someone-else", "A" * 80):
            with self.subTest(pusher=name):
                record = self.accept(pusher=name)
                self.assertEqual(record.outcome, "accepted")
                self.assertIsNone(pushed(record))

    def test_a_manifest_without_the_pusher_records_nothing(self) -> None:
        """Scenario: Malformed manifest (one without `pusher`)."""
        from collection.models import Import
        body = self.follow()
        del body["pusher"]
        done = self.send(body)
        self.assertEqual(done.status_code, 400, done.content)
        self.assertTrue(done.json()["error"])
        self.assertFalse(Import.objects.exists())

    def test_a_pusher_that_is_not_text_records_nothing(self) -> None:
        """Scenario: Malformed manifest (one whose `pusher` is `7`)."""
        from collection.models import Import
        for value in (7, True, ["jkoch"], {"name": "jkoch"}):
            with self.subTest(pusher=value):
                done = self.send(self.follow(pusher=value))
                self.assertEqual(done.status_code, 400, done.content)
        self.assertFalse(Import.objects.exists())

    def test_the_pusher_of_a_stale_manifest_is_not_recorded(self) -> None:
        """Requirement: Manifest (a stale manifest records nothing)."""
        from collection.models import Import
        done = self.send(self.follow(base=999, pusher="jkoch"))
        self.assertEqual(done.status_code, 409, done.content)
        self.assertFalse(Import.objects.exists())

    def test_a_build_sent_again_keeps_its_first_pusher(self) -> None:
        """Requirement: Accepting an import (a build already recorded is
        answered as before and changes nothing)."""
        body = self.follow(pusher="jkoch")
        first = self.send(body)
        again = self.send({**body, "pusher": "klehmann"})
        self.assertEqual(again.json(), first.json())
        from collection.models import Import
        self.assertEqual(
            pushed(Import.objects.get(pk=first.json()["import"])),
            account("jkoch"))
