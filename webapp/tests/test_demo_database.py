"""Tests of the demo database's banner and sign-in note (lab-demo: Demo
database)."""

from django.test import TestCase, override_settings

from . import IndexMixin, build_index, demo_index, frozen, make_task, \
    make_user, page
from .demo_support import (ACCOUNTS, DAY, LOGIN, SIGNING_IN, SeededCase,
                           noon, seed)

BANNER_DE = "Demo: Alle Einträge sind erfunden (Stand: 07.11.2026)."
BANNER_EN = "Demo: All records are invented (as of 2026-11-07)."


class BannerTests(SeededCase):

    def first_in_main(self, path: str):
        main = self.get(path).find("main")
        self.assertIsNotNone(main, path)
        return next(child for child in main.children
                    if not isinstance(child, str))

    def test_banner(self) -> None:
        """Scenario: Banner."""
        for path in ("/lab/tasks/", "/lab/planning/",
                     "/lab/inventory/end-products/"):
            with self.subTest(path=path):
                first = self.first_in_main(path)
                self.assertEqual(first.tag, "p")
                self.assertIn("lab-demo", first.classes)
                self.assertEqual(first.text(), BANNER_DE)

    def test_banner_comes_before_the_messages(self) -> None:
        self.client.force_login(self.account("tbauer"))
        response = self.client.post("/lab/tasks/T-001/start/", follow=True)
        main = page(response).find("main")
        self.assertIsNotNone(main.find(cls="lab-messages"))
        first = next(child for child in main.children
                     if not isinstance(child, str))
        self.assertIn("lab-demo", first.classes)

    def test_admin_has_no_banner(self) -> None:
        response = self.client.get("/lab/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(page(response).find(cls="lab-demo"))

    def test_banner_in_english(self) -> None:
        self.use_index(build_index("en"))
        banner = self.get("/lab/tasks/").find("p", cls="lab-demo")
        self.assertIsNotNone(banner)
        self.assertEqual(banner.text(), BANNER_EN)

    def test_banner_follows_the_mark_without_the_flag(self) -> None:
        with override_settings(ORGSYNDB_DEMO=False):
            banner = self.get("/lab/tasks/").find("p", cls="lab-demo")
        self.assertIsNotNone(banner)


class SignInNoteTests(SeededCase):

    def test_sign_in_note(self) -> None:
        """Scenario: Sign-in note."""
        root = self.get(LOGIN)
        note = root.find(cls="lab-demo-accounts")
        self.assertIsNotNone(note)
        form = root.find("form", cls="lab-form")
        self.assertLess(root.find_all().index(form),
                        root.find_all().index(note))
        text = note.text()
        for username in SIGNING_IN:
            with self.subTest(username=username):
                self.assertIn(username, text)
                self.assertIn(ACCOUNTS[username][0], text)
        self.assertNotIn("mwolf", text)
        self.assertNotIn(ACCOUNTS["mwolf"][0], text)
        self.assertIn("Passwort für alle: demo", text)

    def test_sign_in_note_in_english(self) -> None:
        self.use_index(build_index("en"))
        note = self.get(LOGIN).find(cls="lab-demo-accounts")
        self.assertIn("Password for all: demo", note.text())


class NotADemoDatabaseTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        make_task(cls.kl, substance="CH-0012")

    def setUp(self) -> None:
        self.use_index(demo_index())

    def test_not_a_demo_database(self) -> None:
        """Scenario: Not a demo database."""
        with override_settings(ORGSYNDB_DEMO=True):
            for path in ("/lab/tasks/", LOGIN):
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    root = page(response)
                    self.assertIsNone(root.find(cls="lab-demo"))
                    self.assertIsNone(root.find(cls="lab-demo-accounts"))


class MarkTests(IndexMixin, TestCase):

    def test_the_mark_holds_the_seeding_day(self) -> None:
        from demo.models import DemoMark
        seed(DAY)
        self.assertEqual(list(DemoMark.objects.values_list(
            "seeded_on", flat=True)), [DAY])

    def test_banner_shows_the_day_of_the_mark(self) -> None:
        from datetime import date
        seed(date(2026, 3, 31))
        self.use_index(demo_index())
        with frozen(noon(date(2026, 4, 20))):
            banner = page(self.client.get("/lab/tasks/")).find(
                "p", cls="lab-demo")
        self.assertIn("31.03.2026", banner.text())
