"""Tests of the Forgejo accounts the lab application keeps in line
(web-app: Forgejo accounts), against the fake Forgejo of
``forge_support``."""

import io
from typing import Any

from django.core.management import CommandError, call_command
from django.test import override_settings

from . import make_user
from .collection_support import accept
from .forge_support import (ADMIN_LOGIN, LAB, LOCAL, WARNING, WARNING_EN,
                            ForgeCase, closed_forge_url, configured)


def run_forge_accounts() -> tuple[int, str]:
    """Run ``manage.py forge_accounts``; return its exit status and its
    output, the status being that of a ``CommandError`` or of
    ``SystemExit`` and 0 when the command returns."""
    out = io.StringIO()
    try:
        call_command("forge_accounts", stdout=out, stderr=out)
    except CommandError as exc:
        if "Unknown command" in str(exc):
            raise AssertionError(str(exc)) from None
        return exc.returncode, out.getvalue() + str(exc)
    except SystemExit as exc:
        return (exc.code if isinstance(exc.code, int) else 1,
                out.getvalue())
    return 0, out.getvalue()


class BlockingTests(ForgeCase):
    """Requirement: Forgejo accounts (what a save sets)."""

    def test_deactivating_an_account_blocks_its_forgejo_account(
            self) -> None:
        """Scenario: Deactivating an account."""
        answer = self.admin_change(self.tb, is_active=None)
        self.assertEqual(answer.status_code, 200)
        self.tb.refresh_from_db()
        self.assertFalse(self.tb.is_active)
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.path, "/api/v1/admin/users/tbauer")
        self.assertIs(patch.body["prohibit_login"], True)
        self.assertEqual((patch.user, patch.authorized), (ADMIN_LOGIN, True))
        self.assertTrue(self.forge_tb["prohibit_login"])
        self.assertFalse(self.forge_as["prohibit_login"])

    def test_the_source_lab_may_have_any_id(self) -> None:
        """Requirement: Forgejo accounts (the source `lab`, whatever id
        Forgejo gave it: a failed attempt to add it uses up an id)."""
        self.forge_tb["source_id"] = 5
        self.admin_change(self.tb, is_active=None)
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.path, "/api/v1/admin/users/tbauer")
        self.assertEqual(patch.body["source_id"], 5)
        self.assertIs(patch.body["prohibit_login"], True)

    def test_no_token_and_no_key_is_deleted(self) -> None:
        """Scenario: Deactivating an account (the block keeps tokens and
        keys)."""
        self.admin_change(self.tb, is_active=None)
        self.assertEqual(
            {call.method for call in self.fake.calls} - {"GET", "PATCH"},
            set())
        for call in self.fake.calls:
            self.assertNotIn("/tokens", call.path)
            self.assertNotIn("/keys", call.path)

    def test_reactivating_an_account_lifts_the_block(self) -> None:
        """Scenario: Reactivating an account."""
        self.tb.is_active = False
        self.tb.save()
        self.forge_tb["prohibit_login"] = True
        self.fake.calls.clear()
        self.admin_change(self.tb, is_active="on")
        self.tb.refresh_from_db()
        self.assertTrue(self.tb.is_active)
        patch = self.fake.sole_patch(self)
        self.assertIs(patch.body["prohibit_login"], False)
        self.assertFalse(self.forge_tb["prohibit_login"])

    def test_a_new_address_is_sent_with_the_full_name(self) -> None:
        """Scenario: A new address."""
        self.admin_change(self.tb, email="tb@example.org")
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.path, "/api/v1/admin/users/tbauer")
        self.assertEqual(patch.body["email"], "tb@example.org")
        self.assertEqual(patch.body["full_name"], "Tobias Bauer")
        self.assertEqual(self.forge_tb["email"], "tb@example.org")
        self.assertEqual(self.forge_tb["full_name"], "Tobias Bauer")

    def test_a_new_name_is_sent_with_the_address(self) -> None:
        self.admin_change(self.tb, first_name="Thomas")
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.body["full_name"], "Thomas Bauer")
        self.assertEqual(patch.body["email"], "tbauer@example.org")
        self.assertEqual(self.forge_tb["full_name"], "Thomas Bauer")

    def test_several_changes_make_one_request(self) -> None:
        self.admin_change(self.tb, is_active=None, email="tb@example.org",
                          last_name="Baur")
        patch = self.fake.sole_patch(self)
        self.assertIs(patch.body["prohibit_login"], True)
        self.assertEqual(patch.body["email"], "tb@example.org")
        self.assertEqual(patch.body["full_name"], "Tobias Baur")

    def test_the_login_is_the_one_forgejo_names(self) -> None:
        """Requirement: Forgejo accounts (the account of the source whose
        login name is the primary key, whatever its own login)."""
        self.forge_tb["login"] = "tb-forgejo"
        self.admin_change(self.tb, is_active=None)
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.path, "/api/v1/admin/users/tb-forgejo")
        self.assertTrue(self.forge_tb["prohibit_login"])

    def test_only_the_account_of_the_source_is_changed(self) -> None:
        """Requirement: Forgejo accounts (the source `lab`, the login name
        the primary key)."""
        local = self.fake.add_user("tb-local", str(self.tb.pk), LOCAL,
                                   email="tb-local@example.org")
        other = self.fake.add_user("tb-other", "999999", LAB)
        self.admin_change(self.tb, is_active=None)
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.path, "/api/v1/admin/users/tbauer")
        self.assertFalse(local["prohibit_login"])
        self.assertFalse(other["prohibit_login"])

    def test_an_account_without_a_forgejo_account_has_nothing_to_change(
            self) -> None:
        jk = make_user("jkoch", "JK", "Jonas", "Koch",
                       email="jk@example.org")
        answer = self.admin_change(jk, is_active=None)
        jk.refresh_from_db()
        self.assertFalse(jk.is_active)
        self.assertEqual(self.fake.patches(), [])
        self.assertNotIn("forge_accounts", self.page_html(answer))

    def test_a_save_of_the_model_sets_the_forgejo_account_too(self) -> None:
        self.tb.is_active = False
        self.tb.save()
        patch = self.fake.sole_patch(self)
        self.assertIs(patch.body["prohibit_login"], True)
        self.assertTrue(self.forge_tb["prohibit_login"])

    def test_a_save_of_a_new_address_sets_it_too(self) -> None:
        self.tb.email = "tb@example.org"
        self.tb.save()
        self.assertEqual(self.forge_tb["email"], "tb@example.org")

    def test_a_save_of_a_new_name_sets_it_too(self) -> None:
        self.asc.last_name = "Schmid"
        self.asc.save()
        self.assertEqual(self.forge_as["full_name"], "Anna Schmid")

    def test_other_changes_send_nothing(self) -> None:
        """Requirement: Forgejo accounts (an account whose `is_active`,
        address or display name changed)."""
        self.admin_change(self.tb, is_staff="on")
        self.tb.refresh_from_db()
        self.assertTrue(self.tb.is_staff)
        self.tb.initials = "TX"
        self.tb.save()
        self.tb.save()
        self.assertEqual(self.fake.patches(), [])

    def test_signing_in_sends_nothing(self) -> None:
        from . import PASSWORD
        self.client.logout()
        self.client.post("/lab/accounts/login/", {"username": "tbauer",
                                                  "password": PASSWORD})
        self.assertIn("_auth_user_id", self.client.session)
        self.tb.refresh_from_db()
        self.assertIsNotNone(self.tb.last_login)
        self.assertEqual(self.fake.patches(), [])

    def test_a_save_of_only_the_last_login_sends_nothing(self) -> None:
        self.tb.save(update_fields=["last_login"])
        self.assertEqual(self.fake.patches(), [])

    def test_a_successful_save_shows_no_warning(self) -> None:
        answer = self.admin_change(self.tb, is_active=None)
        self.assertNotIn("forge_accounts", self.page_html(answer))


class FailureTests(ForgeCase):
    """Requirement: Forgejo accounts (the account is saved all the same,
    with a warning)."""

    def deactivate(self) -> Any:
        return self.admin_change(self.tb, is_active=None)

    def assert_saved_with_warning(self, answer: Any) -> None:
        self.tb.refresh_from_db()
        self.assertFalse(self.tb.is_active)
        self.assertEqual(answer.status_code, 200)
        self.assertRegex(
            self.page_html(answer),
            r'class="warning"[^>]*>\s*' + WARNING.replace(".", r"\."))

    def test_an_unreachable_forgejo_leaves_a_warning(self) -> None:
        """Scenario: Forgejo unreachable."""
        with configured(closed_forge_url()):
            answer = self.deactivate()
        self.assert_saved_with_warning(answer)
        self.assertFalse(self.forge_tb["prohibit_login"])

    def test_a_refusing_forgejo_leaves_a_warning(self) -> None:
        self.fake.refuse = 500
        answer = self.deactivate()
        self.assert_saved_with_warning(answer)
        self.assertFalse(self.forge_tb["prohibit_login"])

    def test_wrong_credentials_leave_a_warning(self) -> None:
        with configured(self.fake.url, "not-the-password"):
            answer = self.deactivate()
        self.assert_saved_with_warning(answer)
        self.assertFalse(self.forge_tb["prohibit_login"])
        self.assertEqual(self.fake.patches(), [])

    def test_the_warning_is_in_english_when_the_site_is(self) -> None:
        accept("en")
        with configured(closed_forge_url()):
            answer = self.deactivate()
        self.assertIn(WARNING_EN, self.page_html(answer))

    def test_a_save_of_the_model_survives_an_unreachable_forgejo(
            self) -> None:
        with configured(closed_forge_url()):
            self.tb.is_active = False
            self.tb.save()
        self.tb.refresh_from_db()
        self.assertFalse(self.tb.is_active)

    def test_a_save_of_the_model_survives_a_refusing_forgejo(self) -> None:
        self.fake.refuse = 500
        self.tb.email = "tb@example.org"
        self.tb.save()
        self.tb.refresh_from_db()
        self.assertEqual(self.tb.email, "tb@example.org")
        self.assertEqual(self.forge_tb["email"], "tbauer@example.org")

    def test_a_later_save_that_works_shows_no_warning(self) -> None:
        with configured(closed_forge_url()):
            self.deactivate()
        answer = self.admin_change(self.tb, is_active="on")
        self.assertNotIn("forge_accounts", self.page_html(answer))
        self.assertFalse(self.forge_tb["prohibit_login"])


class NotConfiguredTests(ForgeCase):
    """Scenario: No Forgejo configured."""

    def test_without_an_address_no_request_is_made_and_no_warning(
            self) -> None:
        with configured("", self.fake.password):
            answer = self.admin_change(self.tb, is_active=None)
        self.tb.refresh_from_db()
        self.assertFalse(self.tb.is_active)
        self.assertEqual(self.fake.calls, [])
        self.assertNotIn("forge_accounts", self.page_html(answer))

    def test_without_a_password_no_request_is_made_and_no_warning(
            self) -> None:
        with configured(self.fake.url, ""):
            answer = self.admin_change(self.tb, is_active=None)
        self.assertEqual(self.fake.calls, [])
        self.assertNotIn("forge_accounts", self.page_html(answer))

    def test_a_save_of_the_model_makes_no_request(self) -> None:
        with override_settings(ORGSYNDB_FORGE_URL=""):
            self.tb.is_active = False
            self.tb.save()
        self.assertEqual(self.fake.calls, [])

    def test_forge_accounts_makes_no_request(self) -> None:
        for url, password in (("", self.fake.password), (self.fake.url, "")):
            with self.subTest(url=url, password=password):
                with configured(url, password):
                    run_forge_accounts()
                self.assertEqual(self.fake.calls, [])


class ForgeAccountsTests(ForgeCase):
    """Requirement: Forgejo accounts (`manage.py forge_accounts`)."""

    def setUp(self) -> None:
        super().setUp()
        self.mw = make_user("mwolf", "MW", "Miriam", "Wolf",
                            email="mwolf@example.org", is_active=False)
        self.jk = make_user("jkoch", "JK", "Jonas", "Koch",
                            email="jkoch@example.org")
        self.forge_mw = self.fake.add_user(
            "mwolf", str(self.mw.pk), email="mwolf@example.org",
            full_name="Miriam Wolf")
        self.forge_jk = self.fake.add_user(
            "jkoch", str(self.jk.pk), email="jkoch@example.org",
            full_name="Jonas Koch", prohibit_login=True)
        self.forge_as["email"] = "anna.old@example.org"
        self.forge_ghost = self.fake.add_user(
            "ghost-account", "999999", email="ghost@example.org")
        self.fake.calls.clear()

    def test_bringing_forgejo_in_line(self) -> None:
        """Scenario: Bringing Forgejo in line."""
        status, output = run_forge_accounts()
        self.assertEqual(status, 0, output)
        self.assertTrue(self.forge_mw["prohibit_login"])
        self.assertTrue(self.forge_ghost["prohibit_login"])
        self.assertFalse(self.forge_jk["prohibit_login"])
        self.assertEqual(self.forge_as["email"], "aschmidt@example.org")
        for name in ("mwolf", "jkoch", "aschmidt", "ghost-account"):
            with self.subTest(name=name):
                self.assertIn(name, output)

    def test_accounts_already_in_line_are_not_named(self) -> None:
        """Requirement: Forgejo accounts (prints each account it
        changed)."""
        _status, output = run_forge_accounts()
        self.assertNotIn("tbauer", output)
        self.assertFalse(self.forge_tb["prohibit_login"])
        self.assertEqual(self.forge_tb["email"], "tbauer@example.org")

    def test_the_requests_are_authenticated_as_the_admin(self) -> None:
        run_forge_accounts()
        self.assertTrue(self.fake.calls)
        for call in self.fake.calls:
            self.assertEqual((call.user, call.authorized),
                             (ADMIN_LOGIN, True))

    def test_the_full_name_is_set_too(self) -> None:
        self.forge_as["full_name"] = "A. Schmidt"
        run_forge_accounts()
        self.assertEqual(self.forge_as["full_name"], "Anna Schmidt")

    def test_a_second_run_changes_and_names_nothing(self) -> None:
        run_forge_accounts()
        before = [dict(user) for user in self.fake.users]
        status, output = run_forge_accounts()
        self.assertEqual(status, 0, output)
        self.assertEqual(self.fake.users, before)
        for name in ("mwolf", "jkoch", "aschmidt", "ghost-account"):
            with self.subTest(name=name):
                self.assertNotIn(name, output)

    def test_accounts_of_other_sources_are_left_alone(self) -> None:
        admin = self.fake.add_user(ADMIN_LOGIN, "", LOCAL,
                                   email="orgsyndb@example.org")
        local = self.fake.add_user("someone", "1", LOCAL,
                                   email="someone@example.org")
        before = [dict(admin), dict(local)]
        _status, output = run_forge_accounts()
        self.assertEqual([admin, local], before)
        self.assertNotIn("someone", output)

    def test_a_login_name_that_is_no_number_names_no_lab_account(
            self) -> None:
        stray = self.fake.add_user("stray", "not-a-number")
        status, output = run_forge_accounts()
        self.assertEqual(status, 0, output)
        self.assertTrue(stray["prohibit_login"])
        self.assertIn("stray", output)

    def test_every_page_of_accounts_is_brought_in_line(self) -> None:
        strays = [self.fake.add_user(f"stray{n}", str(1_000_000 + n))
                  for n in range(75)]
        status, output = run_forge_accounts()
        self.assertEqual(status, 0, output)
        self.assertTrue(all(user["prohibit_login"] for user in strays))
        self.assertTrue(self.forge_mw["prohibit_login"])

    def test_an_unreachable_forgejo_makes_it_exit_non_zero(self) -> None:
        """Requirement: Forgejo accounts (exits non-zero when Forgejo
        cannot be reached)."""
        with configured(closed_forge_url()):
            status, _output = run_forge_accounts()
        self.assertNotEqual(status, 0)
        self.assertEqual(self.fake.patches(), [])

    def test_it_changes_no_lab_account(self) -> None:
        run_forge_accounts()
        self.mw.refresh_from_db()
        self.jk.refresh_from_db()
        self.assertFalse(self.mw.is_active)
        self.assertTrue(self.jk.is_active)


class AfterCommitTests(ForgeCase):
    """Requirement: Forgejo accounts (once the save has committed and
    from the account as stored)."""

    def test_a_save_rolled_back_calls_nothing(self) -> None:
        """Scenario: A save rolled back."""
        from django.db import transaction

        class Undo(Exception):
            pass

        try:
            with transaction.atomic():
                self.tb.is_active = False
                self.tb.save()
                raise Undo
        except Undo:
            pass
        self.assertEqual(self.fake.calls, [])
        self.assertFalse(self.forge_tb["prohibit_login"])

    def test_the_call_waits_for_the_commit(self) -> None:
        from django.db import transaction
        with transaction.atomic():
            self.tb.is_active = False
            self.tb.save()
            self.assertEqual(self.fake.calls, [])
        self.assertIs(self.fake.sole_patch(self).body["prohibit_login"],
                      True)

    def test_a_partial_save_sends_the_stored_account(self) -> None:
        """Requirement: Forgejo accounts (from the account as stored: an
        attribute the save did not write is not sent)."""
        self.tb.first_name = "Unsaved"
        self.tb.is_active = False
        self.tb.save(update_fields=["is_active"])
        patch = self.fake.sole_patch(self)
        self.assertIs(patch.body["prohibit_login"], True)
        self.assertEqual(patch.body["full_name"], "Tobias Bauer")

    def test_a_cleared_address_frees_the_old_one(self) -> None:
        """Scenario: A cleared address."""
        self.admin_change(self.tb, email="")
        patch = self.fake.sole_patch(self)
        self.assertEqual(patch.body["email"], "tbauer@noreply.localhost")
        self.assertEqual(self.forge_tb["email"], "tbauer@noreply.localhost")

    def test_a_warning_follows_a_failed_call_after_the_commit(self) -> None:
        self.fake.refuse = 500
        answer = self.admin_change(self.tb, is_active=None)
        self.assertIn(WARNING, self.page_html(answer))


class PassedOnAddressTests(ForgeCase):
    """Scenario: An address passed on during an outage."""

    def setUp(self) -> None:
        super().setUp()
        self.jk = make_user("jkoch", "JK", "Jonas", "Koch",
                            email="jkoch@example.org")
        # jkoch's Forgejo account is listed first.
        self.fake.users.clear()
        self.forge_jk = self.fake.add_user(
            "jkoch", str(self.jk.pk), email="jkoch@example.org",
            full_name="Jonas Koch")
        self.forge_as = self.fake.add_user(
            "aschmidt", str(self.asc.pk), email="as@example.org",
            full_name="Anna Schmidt")

    def lab_addresses(self, aschmidt: str, jkoch: str) -> None:
        with configured(closed_forge_url()):
            for user, address in ((self.asc, aschmidt), (self.jk, jkoch)):
                user.email = address
                user.save()
        self.fake.calls.clear()

    def test_an_address_passed_on_reaches_its_new_holder(self) -> None:
        self.lab_addresses("anna@example.org", "as@example.org")
        status, output = run_forge_accounts()
        self.assertEqual(status, 0, output)
        self.assertEqual(self.forge_as["email"], "anna@example.org")
        self.assertEqual(self.forge_jk["email"], "as@example.org")

    def test_swapped_addresses_are_both_set(self) -> None:
        self.forge_jk["email"] = "anna@example.org"
        self.lab_addresses("anna@example.org", "as@example.org")
        status, output = run_forge_accounts()
        self.assertEqual(status, 0, output)
        self.assertEqual(self.forge_as["email"], "anna@example.org")
        self.assertEqual(self.forge_jk["email"], "as@example.org")
        _status, output = run_forge_accounts()
        self.assertEqual(output.strip(), "")
