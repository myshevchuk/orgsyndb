"""Tests of the access tokens (web-app: Access tokens)."""

import hashlib
import re
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from . import berlin, frozen, make_user, page, table
from .collection_support import accept, make_token, refuses, request_id

User = get_user_model()
TOKENS = "/lab/accounts/tokens/"
LOGIN = "/lab/accounts/login/"
ADMIN = "/lab/admin/accounts/accesstoken/"
TOKEN_RE = re.compile(r"osdb_[A-Za-z0-9_-]{43}(?![A-Za-z0-9_-])")


def revoke_url(token: Any) -> str:
    return f"{TOKENS}{token.pk}/revoke/"


def shown_token(response: Any) -> str | None:
    """The access token that the page ``response`` shows, or None."""
    found = TOKEN_RE.search(response.content.decode("utf-8"))
    return found.group(0) if found else None


class TokenModelTests(TestCase):
    """Requirement: Access tokens (what the application keeps)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("klehmann", "KL")
        cls.tb = make_user("tbauer", "TB")

    def test_create_for_returns_the_row_and_the_token(self) -> None:
        """Requirement: Access tokens (`create_for` returns the row and
        the token itself)."""
        from accounts.models import AccessToken
        row, token = AccessToken.create_for(self.kl, "Laptop")
        self.assertIsInstance(token, str)
        self.assertEqual((row.user, row.name), (self.kl, "Laptop"))
        self.assertEqual(AccessToken.objects.get(), row)
        self.assertEqual(list(self.kl.access_tokens.all()), [row])

    def test_a_token_is_osdb_and_43_url_safe_characters(self) -> None:
        """Requirement: Access tokens (`osdb_` followed by 43 URL-safe
        characters)."""
        from accounts.models import AccessToken
        seen = set()
        for number in range(20):
            token = AccessToken.create_for(self.kl, f"No. {number}")[1]
            self.assertRegex(token, r"\Aosdb_[A-Za-z0-9_-]{43}\Z")
            seen.add(token)
        self.assertEqual(len(seen), 20)

    def test_only_the_digest_is_stored(self) -> None:
        """Requirement: Access tokens (the application keeps only its
        SHA-256 digest, its account, its name, when it was created and
        when it was last used)."""
        from accounts.models import AccessToken
        row, token = AccessToken.create_for(self.kl, "Laptop")
        self.assertEqual(row.digest,
                         hashlib.sha256(token.encode()).hexdigest())
        stored = AccessToken.objects.filter(pk=row.pk).values().get()
        self.assertEqual(
            {name for name in stored
             if isinstance(stored[name], str) and token in stored[name]},
            set())
        self.assertEqual(stored["digest"], row.digest)
        self.assertNotIn(token, str(row))

    def test_the_time_of_creation_is_kept_and_none_of_use(self) -> None:
        """Requirement: Access tokens (when it was created and when it
        was last used)."""
        from accounts.models import AccessToken
        moment = berlin(2026, 11, 12, 9, 30)
        with frozen(moment):
            row = AccessToken.create_for(self.kl, "Laptop")[0]
        found = AccessToken.objects.get(pk=row.pk)
        self.assertEqual(found.created_at, moment)
        self.assertIsNone(found.last_used_at)

    def test_a_name_has_at_most_100_characters(self) -> None:
        """Requirement: Access tokens (a `Name` of at most 100
        characters)."""
        from accounts.models import AccessToken
        self.assertEqual(
            AccessToken._meta.get_field("name").max_length, 100)
        row = AccessToken.create_for(self.kl, "n" * 100)[0]
        row.full_clean()
        row.name = "n" * 101
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_a_digest_is_64_lower_case_hexadecimal_digits(self) -> None:
        """Requirement: Access tokens (the SHA-256 digest)."""
        from accounts.models import AccessToken
        for digest in ("a" * 63, "a" * 65, "A" * 64, "g" * 64, ""):
            with self.subTest(digest=digest):
                refuses(self, lambda: AccessToken(
                    user=self.kl, name="Laptop", digest=digest))

    def test_a_digest_is_unique(self) -> None:
        """Requirement: Access tokens (the application compares
        digests)."""
        from accounts.models import AccessToken
        row = AccessToken.create_for(self.kl, "Laptop")[0]
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccessToken.objects.create(user=self.tb, name="Copy",
                                       digest=row.digest)

    def test_deleting_an_account_deletes_its_tokens(self) -> None:
        """Requirement: Access tokens (deleting an account deletes its
        tokens)."""
        from accounts.models import AccessToken
        AccessToken.create_for(self.kl, "Laptop")
        AccessToken.create_for(self.kl, "Server")
        kept = AccessToken.create_for(self.tb, "Laptop")[0]
        self.kl.delete()
        self.assertEqual(list(AccessToken.objects.all()), [kept])


class SignInTests(TestCase):
    """Requirement: Access tokens (the page needs a signed-in user)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("klehmann", "KL")
        from accounts.models import AccessToken
        cls.row = AccessToken.create_for(cls.kl, "Laptop")[0]

    def redirected(self, response: Any, path: str) -> None:
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{LOGIN}?next={path}")

    def test_the_page_without_a_sign_in(self) -> None:
        """Requirement: Access tokens (as every page that changes data
        does, see Permissions)."""
        from accounts.models import AccessToken
        self.redirected(self.client.get(TOKENS), TOKENS)
        self.redirected(self.client.post(TOKENS, {"name": "Stolen"}),
                        TOKENS)
        self.assertEqual(list(AccessToken.objects.all()), [self.row])

    def test_a_revocation_without_a_sign_in(self) -> None:
        """Requirement: Access tokens (as every action that changes
        data does)."""
        from accounts.models import AccessToken
        path = revoke_url(self.row)
        self.redirected(self.client.post(path), path)
        self.assertEqual(list(AccessToken.objects.all()), [self.row])

    def test_a_token_signs_in_to_no_page(self) -> None:
        """Requirement: Access tokens (a token authenticates the ID
        path only, it never signs anyone in to pages)."""
        from accounts.models import AccessToken
        token = make_token("klehmann", "Second")
        header = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        self.redirected(self.client.get(TOKENS, **header), TOKENS)
        self.redirected(self.client.post(TOKENS, {"name": "Third"},
                                         **header), TOKENS)
        self.redirected(self.client.get("/lab/tasks/new/", **header),
                        "/lab/tasks/new/")
        self.assertEqual(AccessToken.objects.count(), 2)


class PageTests(TestCase):
    """Requirement: Access tokens (the page)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("klehmann", "KL", "Katrin", "Lehmann")
        cls.tb = make_user("tbauer", "TB", "Tobias", "Bauer")

    def setUp(self) -> None:
        self.client.force_login(self.kl)

    def test_the_heading_and_the_columns(self) -> None:
        """Requirement: Access tokens (headed `Zugangsschlüssel`, the
        columns `Name`, `Angelegt` and `Zuletzt benutzt`)."""
        from accounts.models import AccessToken
        AccessToken.create_for(self.kl, "Laptop")
        shown = self.client.get(TOKENS)
        self.assertEqual(shown.status_code, 200)
        root = page(shown)
        self.assertEqual(root.find("h1").text(), "Zugangsschlüssel")
        header, rows = table(root)
        self.assertEqual(header[:3], ["Name", "Angelegt", "Zuletzt benutzt"])
        self.assertEqual(len(rows), 1)

    def test_the_heading_and_the_columns_in_english(self) -> None:
        """Requirement: Access tokens (`Access tokens`, `Name`,
        `Created`, `Last used` and `Revoke`)."""
        from accounts.models import AccessToken
        accept(language="en")
        row = AccessToken.create_for(self.kl, "Laptop")[0]
        root = page(self.client.get(TOKENS))
        self.assertEqual(root.find("h1").text(), "Access tokens")
        header, rows = table(root)
        self.assertEqual(header[:3], ["Name", "Created", "Last used"])
        form = root.find("form", action=revoke_url(row))
        self.assertEqual(form.find("button").text(), "Revoke")

    def test_each_token_has_a_revoke_button(self) -> None:
        """Requirement: Access tokens (beside each, a button
        `Widerrufen`)."""
        from accounts.models import AccessToken
        first = AccessToken.create_for(self.kl, "Laptop")[0]
        second = AccessToken.create_for(self.kl, "Server")[0]
        root = page(self.client.get(TOKENS))
        for row in (first, second):
            with self.subTest(name=row.name):
                form = root.find("form", action=revoke_url(row))
                self.assertIsNotNone(form)
                self.assertEqual(form.get("method").lower(), "post")
                self.assertEqual(form.find("button").text(), "Widerrufen")

    def test_only_the_own_tokens_are_listed(self) -> None:
        """Requirement: Access tokens (a table of their tokens)."""
        from accounts.models import AccessToken
        AccessToken.create_for(self.kl, "Laptop")
        other = AccessToken.create_for(self.tb, "Bench PC")[0]
        root = page(self.client.get(TOKENS))
        header, rows = table(root)
        self.assertEqual([row["Name"].text() for row in rows], ["Laptop"])
        self.assertIsNone(root.find("form", action=revoke_url(other)))
        self.assertNotIn("Bench PC", root.text())

    def test_the_form_takes_a_name(self) -> None:
        """Requirement: Access tokens (a form with a `Name`)."""
        root = page(self.client.get(TOKENS))
        control = root.find("input", name="name")
        self.assertIsNotNone(control)
        self.assertEqual(control.closest("form").get("method").lower(),
                         "post")

    def test_a_token_is_shown_once(self) -> None:
        """Scenario: A token shown once."""
        from accounts.models import AccessToken
        done = self.client.post(TOKENS, {"name": "Laptop"})
        self.assertEqual(done.status_code, 200)
        token = shown_token(done)
        self.assertIsNotNone(token, "the answer shows no token")
        root = page(done)
        self.assertIn("Kopieren Sie den Schlüssel jetzt; er wird nicht "
                      "wieder angezeigt.", root.text())
        header, rows = table(root)
        self.assertEqual([row["Name"].text() for row in rows], ["Laptop"])
        again = self.client.get(TOKENS)
        self.assertIsNone(shown_token(again))
        self.assertNotIn("er wird nicht wieder angezeigt",
                         page(again).text())
        (row,) = AccessToken.objects.all()
        self.assertEqual(row.user, self.kl)
        self.assertEqual(row.digest,
                         hashlib.sha256(token.encode()).hexdigest())
        for name, value in AccessToken.objects.filter(
                pk=row.pk).values().get().items():
            with self.subTest(field=name):
                self.assertNotEqual(value, token)

    def test_the_note_in_english(self) -> None:
        """Requirement: Access tokens (`Copy the token now; it is not
        shown again.`)."""
        accept(language="en")
        done = self.client.post(TOKENS, {"name": "Laptop"})
        self.assertIn("Copy the token now; it is not shown again.",
                      page(done).text())

    def test_the_shown_token_is_the_token_that_works(self) -> None:
        """Requirement: Access tokens (a request carrying `Authorization:
        Bearer <token>` is made by the token's account)."""
        from collection.models import IssuedId
        accept()
        token = shown_token(self.client.post(TOKENS, {"name": "Laptop"}))
        self.assertIsNotNone(token)
        done = request_id(self.client_class(), "procedure", token)
        self.assertEqual(done.status_code, 201, done.content)
        self.assertEqual(IssuedId.objects.get().user, self.kl)

    def test_a_name_of_more_than_100_characters_is_refused(self) -> None:
        """Requirement: Access tokens (a `Name` of at most 100
        characters)."""
        from accounts.models import AccessToken
        done = self.client.post(TOKENS, {"name": "n" * 101})
        self.assertIsNone(shown_token(done))
        self.assertFalse(AccessToken.objects.exists())
        done = self.client.post(TOKENS, {"name": "n" * 100})
        self.assertIsNotNone(shown_token(done))
        self.assertEqual(AccessToken.objects.count(), 1)

    def test_a_token_is_made_for_the_signed_in_account(self) -> None:
        """Requirement: Access tokens (their tokens)."""
        from accounts.models import AccessToken
        self.client.post(TOKENS, {"name": "Laptop", "user": self.tb.pk})
        (row,) = AccessToken.objects.all()
        self.assertEqual(row.user, self.kl)

    def test_a_get_creates_nothing(self) -> None:
        """Requirement: Access tokens (the form creates a token)."""
        from accounts.models import AccessToken
        self.client.get(TOKENS, {"name": "Laptop"})
        self.assertFalse(AccessToken.objects.exists())


class RevocationTests(TestCase):
    """Requirement: Access tokens (a button that deletes it)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("klehmann", "KL")
        cls.tb = make_user("tbauer", "TB")

    def setUp(self) -> None:
        accept()
        self.client.force_login(self.kl)

    def test_a_revoked_token(self) -> None:
        """Scenario: A revoked token."""
        from accounts.models import AccessToken
        row, token = AccessToken.create_for(self.kl, "Laptop")
        before = request_id(self.client_class(), "procedure", token)
        self.assertEqual(before.status_code, 201, before.content)
        done = self.client.post(revoke_url(row))
        self.assertIn(done.status_code, (200, 302))
        self.assertFalse(AccessToken.objects.filter(pk=row.pk).exists())
        after = request_id(self.client_class(), "procedure", token)
        self.assertEqual(after.status_code, 401)

    def test_only_the_revoked_token_goes(self) -> None:
        """Requirement: Access tokens (a button beside each)."""
        from accounts.models import AccessToken
        gone = AccessToken.create_for(self.kl, "Laptop")[0]
        kept, token = AccessToken.create_for(self.kl, "Server")
        self.client.post(revoke_url(gone))
        self.assertEqual(list(AccessToken.objects.all()), [kept])
        done = request_id(self.client_class(), "procedure", token)
        self.assertEqual(done.status_code, 201, done.content)

    def test_another_users_token_cannot_be_revoked(self) -> None:
        """Requirement: Access tokens (their own tokens: another user's
        token answers 404)."""
        from accounts.models import AccessToken
        theirs, token = AccessToken.create_for(self.tb, "Bench PC")
        done = self.client.post(revoke_url(theirs))
        self.assertEqual(done.status_code, 404)
        self.assertTrue(AccessToken.objects.filter(pk=theirs.pk).exists())
        again = request_id(self.client_class(), "procedure", token)
        self.assertEqual(again.status_code, 201, again.content)

    def test_a_token_that_is_gone_answers_404(self) -> None:
        """Requirement: Access tokens (own tokens only)."""
        from accounts.models import AccessToken
        row = AccessToken.create_for(self.kl, "Laptop")[0]
        self.assertIn(self.client.post(revoke_url(row)).status_code,
                      (200, 302))
        self.assertFalse(AccessToken.objects.exists())
        self.assertEqual(self.client.post(revoke_url(row)).status_code,
                         404)

    def test_a_get_revokes_nothing(self) -> None:
        """Requirement: Access tokens (a button, so a POST)."""
        from accounts.models import AccessToken
        row = AccessToken.create_for(self.kl, "Laptop")[0]
        self.client.get(revoke_url(row))
        self.assertTrue(AccessToken.objects.filter(pk=row.pk).exists())


class BearerTests(TestCase):
    """Requirement: Access tokens (a request carrying `Authorization:
    Bearer <token>`)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("klehmann", "KL")
        cls.tb = make_user("tbauer", "TB")

    def setUp(self) -> None:
        accept()

    def test_an_inactive_account(self) -> None:
        """Scenario: An inactive account."""
        from accounts.models import AccessToken
        from collection.models import IssuedId
        row, token = AccessToken.create_for(self.kl, "Laptop")
        User.objects.filter(pk=self.kl.pk).update(is_active=False)
        done = request_id(self.client, "procedure", token)
        self.assertEqual(done.status_code, 401)
        self.assertFalse(IssuedId.objects.exists())
        self.assertIsNone(AccessToken.objects.get(pk=row.pk).last_used_at)

    def test_an_unknown_token(self) -> None:
        """Requirement: Access tokens (an unknown token is refused with
        401)."""
        make_token("klehmann")
        for token in ("osdb_" + "A" * 43, "osdb_", "x", "osdb_" + "A" * 42):
            with self.subTest(token=token):
                done = request_id(self.client, "procedure", token)
                self.assertEqual(done.status_code, 401)

    def test_the_digest_is_not_a_token(self) -> None:
        """Requirement: Access tokens (the application compares
        digests: the stored value is no way in)."""
        from accounts.models import AccessToken
        row = AccessToken.create_for(self.kl, "Laptop")[0]
        done = request_id(self.client, "procedure", row.digest)
        self.assertEqual(done.status_code, 401)
        self.assertEqual(
            AccessToken.objects.get(pk=row.pk).digest, row.digest)

    def test_the_use_is_recorded(self) -> None:
        """Requirement: Access tokens (the request records the time as
        its last use)."""
        from accounts.models import AccessToken
        used, token = AccessToken.create_for(self.kl, "Laptop")
        idle = AccessToken.create_for(self.kl, "Server")[0]
        other = AccessToken.create_for(self.tb, "Bench PC")[0]
        moment = berlin(2026, 11, 20, 12, 0)
        with frozen(moment):
            done = request_id(self.client, "procedure", token)
        self.assertEqual(done.status_code, 201, done.content)
        self.assertEqual(AccessToken.objects.get(pk=used.pk).last_used_at,
                         moment)
        self.assertIsNone(AccessToken.objects.get(pk=idle.pk).last_used_at)
        self.assertIsNone(AccessToken.objects.get(pk=other.pk).last_used_at)

    def test_a_later_use_replaces_the_time(self) -> None:
        """Requirement: Access tokens (when it was last used)."""
        from accounts.models import AccessToken
        row, token = AccessToken.create_for(self.kl, "Laptop")
        later = berlin(2026, 11, 21, 8, 15)
        with frozen(berlin(2026, 11, 20, 12, 0)):
            request_id(self.client, "procedure", token)
        with frozen(later):
            request_id(self.client, "procedure", token)
        self.assertEqual(AccessToken.objects.get(pk=row.pk).last_used_at,
                         later)

    def test_the_last_use_is_shown(self) -> None:
        """Requirement: Access tokens (a column `Zuletzt benutzt`, on
        this English site `Last used`)."""
        token = make_token("klehmann")
        self.client.force_login(self.kl)
        before = table(page(self.client.get(TOKENS)))[1][0]
        self.assertNotIn("2031", before["Last used"].text())
        with frozen(berlin(2031, 11, 20, 12, 0)):
            request_id(self.client_class(), "procedure", token)
        after = table(page(self.client.get(TOKENS)))[1][0]
        self.assertIn("2031", after["Last used"].text())


class AdminTests(TestCase):
    """Requirement: Access tokens (staff see and delete tokens in the
    admin)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.kl = make_user("klehmann", "KL")

    def test_staff_see_the_tokens(self) -> None:
        from accounts.models import AccessToken
        AccessToken.create_for(self.kl, "Laptop")
        self.client.force_login(self.staff)
        done = self.client.get(ADMIN)
        self.assertEqual(done.status_code, 200)
        self.assertIn("Laptop", done.content.decode("utf-8"))
        self.client.force_login(self.kl)
        kept_out = self.client.get(ADMIN)
        self.assertIn(kept_out.status_code, (302, 403))
        self.assertNotIn("Laptop", kept_out.content.decode("utf-8"))

    def test_staff_delete_a_token(self) -> None:
        from accounts.models import AccessToken
        row, token = AccessToken.create_for(self.kl, "Laptop")
        accept()
        self.client.force_login(self.staff)
        done = self.client.post(f"{ADMIN}{row.pk}/delete/",
                                {"post": "yes"})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(AccessToken.objects.filter(pk=row.pk).exists())
        refused = request_id(self.client_class(), "procedure", token)
        self.assertEqual(refused.status_code, 401)
