"""Tests of the page shell and the interface language (web-app: Page
shell, Interface language)."""

import tomllib
from datetime import date
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase

from . import (REPO, IndexMixin, build_index, demo_index, make_item,
               make_lot, make_task, make_user, page, table, task_url,
               ticking, berlin, write_index)

CSS = REPO / "site" / "assets" / "css"
STYLESHEETS = ["tokens.css", "base.css", "screen.css", "print.css"]


def site_strings(language: str) -> dict:
    path = REPO / "site" / "i18n" / f"{language}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def site_title() -> str:
    path = REPO / "site" / "hugo.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))["title"]


class ShellTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.task = make_task(cls.kl, product="CH-0012")

    def setUp(self) -> None:
        self.use_index(demo_index())

    def shell(self, signed_in: bool, path: str = "/lab/tasks/"):
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return page(response)

    def nav_links(self, root):
        header = root.find("header", cls="site-header")
        self.assertIsNotNone(header)
        return header, header.find("nav").find_all("a")

    def test_stylesheets_in_order(self) -> None:
        """Scenario: Shell (stylesheets)."""
        for signed_in in (True, False):
            with self.subTest(signed_in=signed_in):
                self.client.logout()
                root = self.shell(signed_in)
                links = [e for e in root.find_all("link")
                         if e.get("rel") == "stylesheet"]
                self.assertEqual(
                    [e.get("href") for e in links],
                    [f"/lab/static/site/{n}" for n in STYLESHEETS]
                    + ["/lab/static/lab.css"])
                media = {e.get("href").rsplit("/", 1)[1]: e.get("media")
                         for e in links}
                self.assertEqual(media["screen.css"], "screen")
                self.assertEqual(media["print.css"], "print")

    def test_navigation(self) -> None:
        """Scenario: Shell (navigation)."""
        strings = site_strings("de")
        for signed_in in (True, False):
            with self.subTest(signed_in=signed_in):
                self.client.logout()
                header, links = self.nav_links(self.shell(signed_in))
                self.assertEqual(
                    [(a.get("href"), a.text()) for a in links[:7]],
                    [("/lab/inventory/end-products/", "Bestand"),
                     ("/lab/planning/", "Planung"),
                     ("/lab/tasks/", "Aufgaben"),
                     ("/compounds/", strings["nav_compounds"]),
                     ("/sequences/", strings["nav_sequences"]),
                     ("/procedures/", strings["nav_procedures"]),
                     ("/help/", strings["nav_help"])])
                self.assertEqual(header.find("nav").get("aria-label"),
                                 strings["nav_site"])
                self.assertEqual(
                    [a.get("aria-current") for a in links[:7]],
                    [None, None, "page", None, None, None, None])
                title = header.find("a", href="/")
                self.assertIsNotNone(title)
                self.assertEqual(title.text(), site_title())

    def test_a_page_inside_a_view_marks_the_view(self) -> None:
        for path in (task_url(self.task), task_url(self.task, "edit"),
                     "/lab/tasks/new/"):
            with self.subTest(path=path):
                _, links = self.nav_links(self.shell(True, path))
                self.assertEqual(
                    [a.get("aria-current") for a in links[:7]],
                    [None, None, "true", None, None, None, None])

    def test_signed_in_state(self) -> None:
        """Scenario: Shell (sign-in state)."""
        header, _ = self.nav_links(self.shell(True))
        self.assertIn("KL", header.text())
        forms = [f for f in header.find_all("form")
                 if f.get("action") == "/lab/accounts/logout/"]
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0].get("method", "").lower(), "post")
        self.assertIsNotNone(forms[0].find("button"))
        self.assertFalse([a for a in header.find_all("a")
                          if a.text() == "Anmelden"])

    def test_signed_out_state(self) -> None:
        header, _ = self.nav_links(self.shell(False))
        links = [a for a in header.find_all("a") if a.text() == "Anmelden"]
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].get("href").startswith(
            "/lab/accounts/login/"))
        self.assertFalse([f for f in header.find_all("form")
                          if f.get("action") == "/lab/accounts/logout/"])

    def test_no_page_has_a_script(self) -> None:
        """Scenario: Shell (no script)."""
        paths = ["/lab/tasks/", task_url(self.task), "/lab/tasks/new/",
                 task_url(self.task, "edit"), "/lab/accounts/password/"]
        self.client.force_login(self.kl)
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode("utf-8")
                self.assertNotIn("<script", html.lower())
                self.assertIsNone(page(response).find("script"))
        self.client.logout()
        for path in ("/lab/accounts/login/", "/lab/tasks/",
                     task_url(self.task)):
            with self.subTest(path=path, signed_in=False):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("<script",
                                 response.content.decode("utf-8").lower())

    def test_every_page_carries_the_shell(self) -> None:
        paths = [task_url(self.task), "/lab/tasks/new/",
                 task_url(self.task, "edit"), "/lab/accounts/password/"]
        self.client.force_login(self.kl)
        for path in paths:
            with self.subTest(path=path):
                self.assert_shell(self.client.get(path))
        self.client.logout()
        with self.subTest(path="/lab/accounts/login/"):
            self.assert_shell(self.client.get("/lab/accounts/login/"))

    def assert_shell(self, response) -> None:
        self.assertEqual(response.status_code, 200)
        root = page(response)
        self.assertIsNotNone(root.find("header", cls="site-header"))
        hrefs = [e.get("href") for e in root.find_all("link")
                 if e.get("rel") == "stylesheet"]
        self.assertEqual(hrefs[-1], "/lab/static/lab.css")
        self.assertEqual(len(hrefs), 5)


class InventoryShellTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")

    def setUp(self) -> None:
        self.use_index(demo_index())
        self.enterContext(ticking(berlin(2026, 11, 4, 8)))
        self.item = make_item(self.kl, "CH-0012", quantity=5)
        self.lot = make_lot(self.kl, "CH-0012")

    def marks(self, path: str) -> list:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        header = page(response).find("header", cls="site-header")
        links = header.find("nav").find_all("a")
        self.assertEqual([a.text() for a in links[0:3]],
                         ["Bestand", "Planung", "Aufgaben"])
        return [a.get("aria-current") for a in links[0:3]]

    def paths(self) -> list[str]:
        return ["/lab/inventory/end-products/bulk/",
                "/lab/inventory/deliveries/",
                f"/lab/inventory/items/{self.item.pk}/",
                f"/lab/inventory/bulk/{self.lot.pk}/",
                "/lab/inventory/end-products/new/",
                "/lab/inventory/deliveries/new/",
                "/lab/inventory/bulk/new/",
                f"/lab/inventory/items/{self.item.pk}/fill/",
                f"/lab/inventory/items/{self.item.pk}/edit/"]

    def test_navigation_in_the_inventory(self) -> None:
        """Scenario: Navigation in the inventory."""
        self.assertEqual(self.marks("/lab/inventory/end-products/"),
                         ["page", None, None])
        self.assertEqual(
            self.marks(f"/lab/inventory/items/{self.item.pk}/"),
            ["true", None, None])

    def test_every_page_under_the_inventory_marks_it(self) -> None:
        self.client.force_login(self.kl)
        for path in self.paths():
            with self.subTest(path=path):
                self.assertEqual(self.marks(path), ["true", None, None])

    def test_the_english_label(self) -> None:
        self.use_index(build_index("en"))
        response = self.client.get("/lab/inventory/end-products/")
        links = page(response).find("header", cls="site-header").find(
            "nav").find_all("a")
        self.assertEqual(links[0].text(), "Inventory")
        self.assertEqual(links[0].get("href"), "/lab/inventory/end-products/")
        self.assertEqual(links[1].text(), "Planning")
        self.assertEqual(links[1].get("href"), "/lab/planning/")

    def test_the_inventory_pages_carry_the_shell_and_no_script(self) -> None:
        self.client.force_login(self.kl)
        for path in ["/lab/inventory/end-products/", *self.paths()]:
            with self.subTest(path=path):
                response = self.client.get(path)
                html = response.content.decode("utf-8")
                if path != "/lab/inventory/end-products/":
                    self.assertNotIn("<script", html.lower())
                root = page(response)
                self.assertIsNotNone(root.find("header", cls="site-header"))
                hrefs = [e.get("href") for e in root.find_all("link")
                         if e.get("rel") == "stylesheet"]
                self.assertEqual(
                    hrefs, [f"/lab/static/site/{n}" for n in STYLESHEETS]
                    + ["/lab/static/lab.css"])

    def test_one_script_for_the_item_list(self) -> None:
        """Scenario: One script for the item list."""
        for signed_in in (False, True):
            if signed_in:
                self.client.force_login(self.kl)
            with self.subTest(signed_in=signed_in):
                response = self.client.get("/lab/inventory/end-products/")
                html = response.content.decode("utf-8").lower()
                self.assertEqual(html.count("<script"), 1)
                scripts = page(response).find_all("script")
                self.assertEqual(len(scripts), 1)
                self.assertEqual(scripts[0].get("src"), "/lab/static/lab.js")
                self.assertIn("defer", scripts[0].attrs)
                self.assertEqual(scripts[0].text(), "")
        for path in (f"/lab/inventory/items/{self.item.pk}/",
                     "/lab/planning/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("<script",
                                 response.content.decode("utf-8").lower())

    def test_the_script_is_collected(self) -> None:
        self.assertIsNotNone(finders.find("lab.js"))

    def test_the_message_shows_above_the_content(self) -> None:
        self.client.force_login(self.kl)
        done = self.client.post(
            "/lab/inventory/items/%d/edit/" % self.item.pk,
            {"name": "Neu", "category": "", "note": "", "status": "active"},
            follow=True)
        root = page(done)
        self.assertIsNotNone(root.find("ul", cls="lab-messages"))


class PlanningShellTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")

    def setUp(self) -> None:
        self.use_index(demo_index())

    def marks(self, path: str) -> list:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        header = page(response).find("header", cls="site-header")
        links = header.find("nav").find_all("a")
        self.assertEqual([(a.get("href"), a.text()) for a in links[0:3]],
                         [("/lab/inventory/end-products/", "Bestand"),
                          ("/lab/planning/", "Planung"),
                          ("/lab/tasks/", "Aufgaben")])
        return [a.get("aria-current") for a in links[0:3]]

    def test_navigation_in_the_planning_list(self) -> None:
        """Scenario: Navigation in the planning list."""
        for path in ("/lab/planning/", "/lab/planning/?all=1"):
            with self.subTest(path=path):
                self.assertEqual(self.marks(path), [None, "page", None])

    def test_the_planning_list_carries_the_shell_and_no_script(self) -> None:
        for signed_in in (False, True):
            if signed_in:
                self.client.force_login(self.kl)
            with self.subTest(signed_in=signed_in):
                response = self.client.get("/lab/planning/")
                html = response.content.decode("utf-8")
                self.assertNotIn("<script", html.lower())
                root = page(response)
                self.assertIsNotNone(root.find("header", cls="site-header"))
                hrefs = [e.get("href") for e in root.find_all("link")
                         if e.get("rel") == "stylesheet"]
                self.assertEqual(
                    hrefs, [f"/lab/static/site/{n}" for n in STYLESHEETS]
                    + ["/lab/static/lab.css"])

    def test_the_english_label(self) -> None:
        self.use_index(build_index("en"))
        links = page(self.client.get("/lab/planning/")).find(
            "header", cls="site-header").find("nav").find_all("a")
        self.assertEqual(links[1].text(), "Planning")
        self.assertEqual(links[1].get("href"), "/lab/planning/")

    def test_the_other_views_do_not_mark_the_planning(self) -> None:
        self.assertEqual(self.marks("/lab/tasks/"), [None, None, "page"])
        self.assertEqual(self.marks("/lab/inventory/end-products/"),
                         ["page", None, None])


class StaticFilesTests(SimpleTestCase):

    def test_the_sites_stylesheets_are_collected(self) -> None:
        for name in STYLESHEETS:
            with self.subTest(name=name):
                found = finders.find(f"site/{name}")
                self.assertTrue(found, f"site/{name} is not found")
                self.assertEqual(Path(found).read_bytes(),
                                 (CSS / name).read_bytes())

    def test_the_applications_stylesheet_is_collected(self) -> None:
        self.assertTrue(finders.find("lab.css"))


class LanguageTests(IndexMixin, TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.task = make_task(cls.kl, product="X", started=date(2026, 11, 3))

    def test_german_site(self) -> None:
        self.use_index(demo_index())
        response = self.client.get("/lab/tasks/?state=all")
        root = page(response)
        self.assertEqual(root.find("html").get("lang"), "de")
        header, rows = table(root)
        self.assertEqual(rows[0]["Beginn"].text(), "03.11.2026")

    def test_english_site(self) -> None:
        """Scenario: English site."""
        self.use_index(build_index("en"))
        response = self.client.get("/lab/tasks/?state=all")
        root = page(response)
        self.assertEqual(root.find("html").get("lang"), "en")
        links = root.find("header", cls="site-header").find("nav"
                                                            ).find_all("a")
        self.assertEqual(links[0].text(), "Inventory")
        self.assertEqual(links[1].text(), "Planning")
        self.assertEqual(links[2].text(), "Tasks")
        strings = site_strings("en")
        self.assertEqual([a.text() for a in links[3:7]],
                         [strings[f"nav_{n}"] for n in
                          ("compounds", "sequences", "procedures", "help")])
        header, rows = table(root)
        self.assertEqual(rows[0]["Started"].text(), "2026-11-03")

    def test_english_site_dates_on_the_task_page(self) -> None:
        self.use_index(build_index("en"))
        self.assertIn("2026-11-03",
                      page(self.client.get(task_url(self.task))).text())

    def test_german_site_dates_on_the_task_page(self) -> None:
        self.use_index(build_index("de"))
        self.assertIn("03.11.2026",
                      page(self.client.get(task_url(self.task))).text())

    def test_no_index_serves_german(self) -> None:
        """Scenario: No index."""
        self.use_index(None)
        response = self.client.get("/lab/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page(response).find("html").get("lang"), "de")

    def test_language_follows_a_replaced_index(self) -> None:
        path = self.use_index(build_index("en"))
        self.assertEqual(page(self.client.get("/lab/tasks/")
                              ).find("html").get("lang"), "en")
        write_index(path, build_index("de"))
        self.assertEqual(page(self.client.get("/lab/tasks/")
                              ).find("html").get("lang"), "de")

    def test_sign_in_page_speaks_the_language(self) -> None:
        self.use_index(build_index("en"))
        root = page(self.client.get("/lab/accounts/login/"))
        self.assertEqual(root.find("html").get("lang"), "en")
        header = root.find("header", cls="site-header")
        self.assertIn("Sign in", [a.text() for a in header.find_all("a")])
