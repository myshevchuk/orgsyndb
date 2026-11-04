"""Tests of accounts, sign-in and permissions (web-app: Accounts and
sign-in, Permissions)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from . import (PASSWORD, IndexMixin, demo_index, edit_data, make_task,
               make_user, page, task_form_data, task_url)

User = get_user_model()
LOGIN = "/lab/accounts/login/"


def validation_errors(user) -> dict:
    try:
        user.full_clean()
    except ValidationError as exc:
        return exc.message_dict
    return {}


class InitialsTests(TestCase):

    def candidate(self, name: str, initials: str):
        user = User(username=name, initials=initials)
        user.set_unusable_password()
        return user

    def test_initials_are_stored_in_upper_case(self) -> None:
        """Scenario: Initials."""
        first = make_user("first", "kl")
        first.refresh_from_db()
        self.assertEqual(first.initials, "KL")

    def test_the_same_initials_in_another_case_fail_validation(self) -> None:
        """Scenario: Initials (second user)."""
        make_user("first", "kl")
        for initials in ("KL", "kl", "Kl"):
            with self.subTest(initials=initials):
                errors = validation_errors(self.candidate("second", initials))
                self.assertIn("initials", errors)

    def test_save_and_clean_normalise(self) -> None:
        user = self.candidate("saved", "ab1")
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.initials, "AB1")
        other = self.candidate("cleaned", "xy")
        other.clean()
        self.assertEqual(other.initials, "XY")

    def test_the_database_refuses_initials_regardless_of_case(self) -> None:
        make_user("first", "KL")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.candidate("second", "kl").save()

    def test_one_to_five_letters_or_digits(self) -> None:
        for initials in ("A", "ab", "a1b2c"):
            with self.subTest(initials=initials):
                self.assertNotIn(
                    "initials",
                    validation_errors(self.candidate("ok", initials)))
        for initials in ("", "ABCDEF", "A B", "K-L", "K.L"):
            with self.subTest(initials=initials):
                self.assertIn(
                    "initials",
                    validation_errors(self.candidate("bad", initials)))


class SignInTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")

    def signed_in(self) -> bool:
        return "_auth_user_id" in self.client.session

    def test_sign_in_form_is_open(self) -> None:
        shown = self.client.get(LOGIN)
        self.assertEqual(shown.status_code, 200)
        names = {e.get("name") for e in page(shown).find_all("input")}
        self.assertLessEqual({"username", "password"}, names)

    def test_user_name_and_password_sign_in(self) -> None:
        done = self.client.post(LOGIN, {"username": "kl",
                                        "password": PASSWORD})
        self.assertEqual(done.status_code, 302)
        self.assertTrue(self.signed_in())
        self.assertEqual(self.client.get("/lab/tasks/new/").status_code, 200)

    def test_sign_in_follows_next(self) -> None:
        done = self.client.post(LOGIN, {"username": "kl",
                                        "password": PASSWORD,
                                        "next": "/lab/tasks/new/"})
        self.assertEqual(done.status_code, 302)
        self.assertEqual(done["Location"], "/lab/tasks/new/")

    def test_wrong_password_does_not_sign_in(self) -> None:
        done = self.client.post(LOGIN, {"username": "kl",
                                        "password": "not-the-password"})
        self.assertEqual(done.status_code, 200)
        self.assertFalse(self.signed_in())

    def test_sign_out_is_a_post(self) -> None:
        self.client.force_login(self.kl)
        self.client.get("/lab/accounts/logout/")
        self.assertTrue(self.signed_in())
        self.client.post("/lab/accounts/logout/")
        self.assertFalse(self.signed_in())
        self.assertEqual(self.client.get("/lab/tasks/new/").status_code, 302)

    def test_password_change(self) -> None:
        self.client.force_login(self.kl)
        shown = self.client.get("/lab/accounts/password/")
        self.assertEqual(shown.status_code, 200)
        new = "Another-Quite-Long-Phrase-47"
        done = self.client.post("/lab/accounts/password/", {
            "old_password": PASSWORD, "new_password1": new,
            "new_password2": new})
        self.assertEqual(done.status_code, 302)
        self.kl.refresh_from_db()
        self.assertTrue(self.kl.check_password(new))
        self.assertFalse(self.kl.check_password(PASSWORD))

    def test_password_change_needs_the_old_password(self) -> None:
        self.client.force_login(self.kl)
        new = "Another-Quite-Long-Phrase-47"
        done = self.client.post("/lab/accounts/password/", {
            "old_password": "wrong", "new_password1": new,
            "new_password2": new})
        self.assertEqual(done.status_code, 200)
        self.kl.refresh_from_db()
        self.assertTrue(self.kl.check_password(PASSWORD))

    def test_password_change_needs_a_sign_in(self) -> None:
        done = self.client.get("/lab/accounts/password/")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(
            done["Location"], f"{LOGIN}?next=/lab/accounts/password/")

    def test_there_is_no_page_for_creating_an_account(self) -> None:
        for path in ("/lab/accounts/register/", "/lab/accounts/signup/",
                     "/lab/accounts/new/", "/lab/accounts/create/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)


class AccountWithoutPasswordTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.student = make_user("student", "ST", "Sven", "Thom",
                                password=None)

    def test_the_account_has_no_usable_password(self) -> None:
        self.assertFalse(self.student.has_usable_password())

    def test_the_account_cannot_sign_in(self) -> None:
        """Scenario: Account without a password."""
        for password in ("", "student", PASSWORD, "!"):
            with self.subTest(password=password):
                done = self.client.post(LOGIN, {"username": "student",
                                                "password": password})
                self.assertEqual(done.status_code, 200)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_the_account_is_offered_as_assignee(self) -> None:
        """Scenario: Account without a password (assignee)."""
        self.use_index(demo_index())
        self.client.force_login(self.kl)
        shown = page(self.client.get("/lab/tasks/new/"))
        select = shown.find("select", name="assignee")
        options = [o.text() for o in select.find_all("option")]
        self.assertTrue(any("ST" in o and "Sven Thom" in o
                            for o in options), options)

    def test_the_account_can_be_named_on_a_task(self) -> None:
        self.use_index(demo_index())
        self.client.force_login(self.kl)
        done = self.client.post("/lab/tasks/new/", task_form_data(
            assignee=str(self.student.pk)))
        self.assertEqual(done.status_code, 302)
        from tasks.models import Task
        self.assertEqual(Task.objects.get().assignee, self.student)


class DisplayNameTests(IndexMixin, TestCase):

    def test_display_name_is_the_full_name_or_the_user_name(self) -> None:
        self.use_index(demo_index())
        kl = make_user("kl", "KL", "Klara", "Lehmann")
        make_user("plain", "PL")
        self.client.force_login(kl)
        shown = page(self.client.get("/lab/tasks/new/"))
        options = {o.text() for o in
                   shown.find("select", name="assignee").find_all("option")}
        self.assertTrue(any("KL" in o and "Klara Lehmann" in o
                            for o in options), options)
        self.assertTrue(any("PL" in o and "plain" in o for o in options),
                        options)


class PermissionTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")
        cls.task = make_task(cls.kl, product="Aspirin",
                             steps_total=2)

    def setUp(self) -> None:
        self.use_index(demo_index())

    def redirected_to_sign_in(self, response, path: str) -> None:
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{LOGIN}?next={path}")

    def test_form_without_sign_in(self) -> None:
        """Scenario: Form without sign-in."""
        from tasks.models import Task
        before = Task.objects.count()
        path = "/lab/tasks/new/"
        self.redirected_to_sign_in(self.client.get(path), path)
        self.redirected_to_sign_in(
            self.client.post(path, task_form_data()), path)
        self.assertEqual(Task.objects.count(), before)

    def test_edit_without_sign_in(self) -> None:
        path = task_url(self.task, "edit")
        self.redirected_to_sign_in(self.client.get(path), path)
        self.redirected_to_sign_in(
            self.client.post(path, edit_data(self.task, product="Changed")),
            path)
        self.task.refresh_from_db()
        self.assertEqual(self.task.product, "Aspirin")

    def test_actions_without_sign_in(self) -> None:
        for action in ("start", "step", "end", "report", "qc-list"):
            path = task_url(self.task, action)
            with self.subTest(action=action):
                self.redirected_to_sign_in(self.client.get(path), path)
                self.redirected_to_sign_in(self.client.post(path), path)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.started)
        self.assertEqual(self.task.steps_done, 0)
        self.assertEqual(self.task.history.count(), 1)

    def test_pages_that_show_data_need_no_sign_in(self) -> None:
        for path in ("/lab/tasks/", task_url(self.task), LOGIN):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_the_views_offer_no_deletion(self) -> None:
        self.client.force_login(make_user("boss", "BO", is_staff=True,
                                          is_superuser=True))
        for path in (task_url(self.task, "delete"),
                     task_url(self.task, "remove"), "/lab/tasks/delete/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path).status_code, 404)
        self.task.refresh_from_db()
        shown = page(self.client.get(task_url(self.task)))
        self.assertIsNone(shown.find("form", action=task_url(self.task,
                                                             "delete")))
