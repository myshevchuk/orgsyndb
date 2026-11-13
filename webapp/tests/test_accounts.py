"""Tests of accounts, sign-in and permissions (web-app: Accounts and
sign-in, Permissions)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from . import (PASSWORD, done_days, edit_data, field_value, make_task,
               make_user, page, substance_for, task_form_data, task_url)

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


VALID_USER_NAMES = ["ab", "a", "7", "a.example", "ae.mueller", "A.B",
                    "klehmann", "lab-worker-kl", "a_b-c.d", "x" * 40,
                    "a1.b2-c3_d4"]
INVALID_USER_NAMES = ["a..b", "-ab", "ab-", ".ab", "ab.", "_ab", "ab_",
                      "a--b", "a._b", "a-_b", "a__b", "Ä.müller", "ä", "a b",
                      "a@b", "a+b", "a/b", "a,b", "ab\n", "x" * 41, ""]


class UserNameTests(TestCase):
    """Requirement: Accounts and sign-in (a user name of at most 40
    letters and digits, single `.`, `-` or `_` allowed between them)."""

    def candidate(self, name: str):
        user = User(username=name, initials="UN")
        user.set_unusable_password()
        return user

    def test_the_names_the_rule_allows(self) -> None:
        """Scenario: User names (`a.example`)."""
        for name in VALID_USER_NAMES:
            with self.subTest(username=name):
                self.assertNotIn("username",
                                 validation_errors(self.candidate(name)))

    def test_the_names_the_rule_refuses(self) -> None:
        """Scenario: User names (`a..b`, `-ab`, `ab-` and `Ä.müller`)."""
        for name in INVALID_USER_NAMES:
            with self.subTest(username=name):
                self.assertIn("username",
                              validation_errors(self.candidate(name)))

    def test_a_user_name_has_at_most_forty_characters(self) -> None:
        self.assertEqual(User._meta.get_field("username").max_length, 40)

    def test_an_account_with_a_valid_name_is_created(self) -> None:
        user = make_user("a.example", "AE")
        self.assertEqual(User.objects.get(pk=user.pk).username, "a.example")


class UserNameAdminTests(TestCase):
    """Scenario: User names (in the admin)."""

    ADD = "/lab/admin/accounts/user/add/"

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)

    def setUp(self) -> None:
        self.client.force_login(self.staff)

    def add(self, name: str, initials: str):
        return self.client.post(self.ADD, {
            "username": name, "initials": initials, "first_name": "Test",
            "last_name": name, "usable_password": "false"})

    def test_only_the_valid_name_is_created(self) -> None:
        """Scenario: User names."""
        names = ["a.example", "a..b", "-ab", "ab-", "Ä.müller"]
        for number, name in enumerate(names):
            with self.subTest(username=name):
                self.add(name, f"N{number}")
        self.assertEqual(
            sorted(User.objects.exclude(pk=self.staff.pk).values_list(
                "username", flat=True)), ["a.example"])

    def test_the_add_page_takes_a_user_name(self) -> None:
        shown = page(self.client.get(self.ADD))
        self.assertIsNotNone(shown.find("input", name="username"))

    def change_url(self, user) -> str:
        return f"/lab/admin/accounts/user/{user.pk}/change/"

    def test_the_user_name_of_an_account_cannot_be_changed(self) -> None:
        """Scenario: User names (then changes the user name of
        `a.example`)."""
        self.add("a.example", "AX")
        user = User.objects.get(username="a.example")
        shown = self.client.get(self.change_url(user))
        self.assertEqual(shown.status_code, 200)
        root = page(shown)
        self.assertIsNone(root.find("input", name="username"))
        data = form_data(root)
        data["username"] = "b.example"
        data["first_name"] = "Changed"
        self.client.post(self.change_url(user), data)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Changed", "the form was refused")
        self.assertEqual(user.username, "a.example")
        self.assertFalse(User.objects.filter(username="b.example").exists())


def form_data(root) -> dict[str, str]:
    """The values the controls of the first form of ``root`` submit as
    they stand: checked boxes and the others' values."""
    data = {}
    for control in root.find_all(("input", "select", "textarea")):
        name = control.get("name")
        if not name or control.get("type") in ("submit", "button"):
            continue
        if control.get("type") in ("checkbox", "radio"):
            if "checked" in control.attrs:
                data[name] = control.get("value", "on")
            continue
        value = field_value(root, name)
        if value is not None:
            data[name] = value
    return data


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


class AccountWithoutPasswordTests(TestCase):

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
        self.client.force_login(self.kl)
        shown = page(self.client.get("/lab/tasks/new/"))
        select = shown.find("select", name="assignee")
        options = [o.text() for o in select.find_all("option")]
        self.assertTrue(any("ST" in o and "Sven Thom" in o
                            for o in options), options)

    def test_the_account_can_be_named_on_a_task(self) -> None:
        self.client.force_login(self.kl)
        substance_for("Aspirin")
        done = self.client.post("/lab/tasks/new/", task_form_data(
            assignee=str(self.student.pk)))
        self.assertEqual(done.status_code, 302)
        from tasks.models import Task
        self.assertEqual(Task.objects.get().assignee, self.student)


class DisplayNameTests(TestCase):

    def test_display_name_is_the_full_name_or_the_user_name(self) -> None:
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


class PermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL")
        cls.task = make_task(cls.kl, substance="Aspirin",
                             steps=2)

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
            self.client.post(path, edit_data(self.task, substance="changed")),
            path)
        self.task.refresh_from_db()
        self.assertEqual(self.task.substance.key, "aspirin")

    def test_actions_without_sign_in(self) -> None:
        for action in ("start", "step", "end", "report", "qc-list"):
            path = task_url(self.task, action)
            with self.subTest(action=action):
                self.redirected_to_sign_in(self.client.get(path), path)
                self.redirected_to_sign_in(self.client.post(path), path)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.started)
        self.assertEqual(done_days(self.task), [None, None])
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


# The names Forgejo 15 reserves for itself, as the spike found them (the
# admin API refuses each, in any case), and the suffixes it refuses.
RESERVED_USER_NAMES = [
    "admin", "api", "user", "explore", "assets", "avatars", "login", "org",
    "repo", "notifications", "ghost", "swagger.v1.json", "v2", "metrics",
    "captcha", "issues", "pulls", "milestones", "attachments",
    "favicon.ico", "robots.txt", "manifest.json", "ssh_info",
    "gitea-actions", "forgejo-actions", "repo-avatars", "orgsyndb"]
RESERVED_SUFFIXES = [".keys", ".gpg", ".rss", ".atom", ".png"]
# Names Forgejo takes, which stay open to accounts.
FREE_USER_NAMES = ["help", "mail", "install", "administrator", "adminx",
                   "api2", "users", "orgsyndb2", "keys", "png", "annarss",
                   "a.pngx", "a-png", "a.png.b", "x.orgsyndb"]


def admin_errors(response) -> dict:
    """The errors of the form that the admin page ``response`` shows."""
    return response.context["adminform"].form.errors


class ReservedUserNameTests(TestCase):
    """Requirement: Accounts and sign-in (user names Forgejo reserves,
    and `orgsyndb`)."""

    def candidate(self, name: str):
        user = User(username=name, initials="RN")
        user.set_unusable_password()
        return user

    def refused(self, name: str) -> list[str]:
        return validation_errors(self.candidate(name)).get("username", [])

    def test_the_reserved_names_are_refused_in_every_case(self) -> None:
        for name in RESERVED_USER_NAMES:
            for spelled in dict.fromkeys(
                    (name, name.upper(), name.title(), name.capitalize())):
                with self.subTest(username=spelled):
                    self.assertTrue(self.refused(spelled))

    def test_the_refused_suffixes_are_refused_in_every_case(self) -> None:
        for suffix in RESERVED_SUFFIXES:
            for name in (f"anna{suffix}", f"a{suffix}",
                         f"Anna{suffix.upper()}", f"a.b{suffix}"):
                with self.subTest(username=name):
                    self.assertTrue(self.refused(name))

    def test_the_error_says_the_name_is_reserved(self) -> None:
        """Scenario: Reserved user names (each form names the user name
        as reserved)."""
        for name in ("Admin", "anna.rss", "orgsyndb"):
            with self.subTest(username=name):
                self.assertRegex(" ".join(self.refused(name)),
                                 r"(?i)reserv")

    def test_the_names_forgejo_takes_stay_open(self) -> None:
        for name in FREE_USER_NAMES:
            with self.subTest(username=name):
                self.assertEqual(self.refused(name), [])


class ReservedUserNameAdminTests(TestCase):
    """Scenario: Reserved user names."""

    ADD = "/lab/admin/accounts/user/add/"

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)

    def setUp(self) -> None:
        self.client.force_login(self.staff)

    def add(self, name: str, initials: str):
        return self.client.post(self.ADD, {
            "username": name, "initials": initials, "first_name": "Test",
            "last_name": "Name", "usable_password": "false"})

    def test_none_is_created_and_each_form_names_the_user_name(self) -> None:
        names = ["Admin", "explore", "anna.rss", "a.png", "orgsyndb"]
        for number, name in enumerate(names):
            with self.subTest(username=name):
                answer = self.add(name, f"R{number}")
                self.assertEqual(answer.status_code, 200)
                errors = admin_errors(answer)
                self.assertIn("username", errors)
                self.assertRegex(" ".join(errors["username"]),
                                 r"(?i)reserv")
        self.assertEqual(User.objects.exclude(pk=self.staff.pk).count(), 0)

    def test_an_open_name_is_created(self) -> None:
        self.add("mail", "MA")
        self.assertTrue(User.objects.filter(username="mail").exists())


class EmailAddressTests(TestCase):
    """Requirement: Accounts and sign-in (an email address may be empty
    and is otherwise unique regardless of case)."""

    def candidate(self, name: str, initials: str, email: str):
        user = User(username=name, initials=initials, email=email)
        user.set_unusable_password()
        return user

    def test_the_same_address_in_another_case_fails_validation(self) -> None:
        """Scenario: Email addresses (the second account)."""
        make_user("first", "KL", email="kl@example.org")
        for address in ("KL@Example.org", "kl@example.org", "Kl@EXAMPLE.ORG"):
            with self.subTest(email=address):
                errors = validation_errors(
                    self.candidate("second", "SE", address))
                self.assertIn("email", errors)

    def test_accounts_without_an_address_are_all_saved(self) -> None:
        """Scenario: Email addresses (two more without an address)."""
        make_user("first", "KL", email="kl@example.org")
        for name, initials in (("second", "SE"), ("third", "TH")):
            with self.subTest(username=name):
                user = self.candidate(name, initials, "")
                self.assertNotIn("email", validation_errors(user))
                user.save()
        self.assertEqual(User.objects.filter(email="").count(), 2)

    def test_different_addresses_are_fine(self) -> None:
        make_user("first", "KL", email="kl@example.org")
        self.assertNotIn("email", validation_errors(
            self.candidate("second", "SE", "kl2@example.org")))

    def test_an_account_keeps_its_own_address(self) -> None:
        first = make_user("first", "KL", email="kl@example.org")
        first.refresh_from_db()
        self.assertNotIn("email", validation_errors(first))
        first.email = "KL@example.org"
        self.assertNotIn("email", validation_errors(first))

    def test_an_address_given_up_is_free_again(self) -> None:
        first = make_user("first", "KL", email="kl@example.org")
        first.email = ""
        first.save()
        self.assertNotIn("email", validation_errors(
            self.candidate("second", "SE", "KL@example.org")))


class EmailAddressAdminTests(TestCase):
    """Scenario: Email addresses (in the admin)."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)
        cls.kl = make_user("klehmann", "KL")
        cls.tb = make_user("tbauer", "TB")
        cls.aschmidt = make_user("aschmidt", "AS")
        cls.jkoch = make_user("jkoch", "JK")

    def setUp(self) -> None:
        self.client.force_login(self.staff)

    def give(self, user, address: str):
        url = f"/lab/admin/accounts/user/{user.pk}/change/"
        data = form_data(page(self.client.get(url)))
        data["email"] = address
        return self.client.post(url, data)

    def test_the_second_address_is_refused(self) -> None:
        self.assertEqual(self.give(self.kl, "kl@example.org").status_code,
                         302)
        answer = self.give(self.tb, "KL@Example.org")
        self.assertEqual(answer.status_code, 200)
        self.assertIn("email", admin_errors(answer))
        for user in (self.kl, self.tb):
            user.refresh_from_db()
        self.assertEqual(self.kl.email, "kl@example.org")
        self.assertEqual(self.tb.email, "")

    def test_accounts_without_an_address_are_saved(self) -> None:
        for user in (self.aschmidt, self.jkoch):
            with self.subTest(username=user.username):
                self.assertEqual(self.give(user, "").status_code, 302)


class UserNameCaseTests(TestCase):
    """Scenario: User names differing in case."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff = make_user("boss", "BO", is_staff=True,
                              is_superuser=True)

    def test_a_name_differing_in_case_fails_validation(self) -> None:
        make_user("alice", "AL")
        user = User(username="Alice", initials="A2")
        user.set_unusable_password()
        self.assertIn("username", validation_errors(user))

    def test_the_admin_refuses_the_second_account(self) -> None:
        self.client.force_login(self.staff)
        for name, initials in (("alice", "AL"), ("Alice", "A2")):
            answer = self.client.post("/lab/admin/accounts/user/add/", {
                "username": name, "initials": initials,
                "first_name": "Test", "last_name": "Name",
                "usable_password": "false"})
        self.assertEqual(answer.status_code, 200)
        self.assertIn("username", admin_errors(answer))
        self.assertEqual(
            User.objects.filter(username__iexact="alice").count(), 1)
