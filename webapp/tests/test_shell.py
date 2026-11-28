"""Tests of the page shell and the interface language (web-app: Page
shell, Interface language)."""

import html
import json
import re
import tomllib
from datetime import date
from pathlib import Path

from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase

from . import (HTMX, IDIOMORPH, REPO, SHELL_SCRIPT, STIMULUS, berlin,
               frozen, make_item, make_task, make_user, make_vessel, page,
               shell_scripts, substance_for, table, task_url, ticking)
from . import navigation_support as ns
from .collection_support import accept, make_import

CSS = REPO / "site" / "assets" / "css"
JS = REPO / "site" / "assets" / "js"
STYLESHEETS = ["tokens.css", "base.css", "screen.css", "print.css"]
ALLOWED_MORPH_SWAPS = ("morph", "morph:outerHTML", "morph:innerHTML")


def site_strings(language: str) -> dict:
    path = REPO / "site" / "i18n" / f"{language}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def site_title() -> str:
    path = REPO / "site" / "hugo.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))["title"]


class ShellTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.task = make_task(cls.kl, substance="CH-0012")

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
        """Scenario: Shell (title, search and navigation)."""
        strings = site_strings("de")
        for signed_in in (True, False):
            with self.subTest(signed_in=signed_in):
                self.client.logout()
                root = self.shell(signed_in)
                header, _ = self.nav_links(root)
                self.assertEqual(ns.shown(root), ns.expected("de"))
                self.assertEqual(ns.nav(root).get("aria-label"),
                                 strings["nav_site"])
                title = header.find("a", cls="site-title")
                self.assertIsNotNone(title)
                self.assertEqual((title.get("href"), title.text()),
                                 ("/", site_title()))
                self.check_search(header, strings)

    def check_search(self, header, strings: dict) -> None:
        """The header holds the site's search form for procedures."""
        forms = header.find_all("form", cls="site-search")
        self.assertEqual(len(forms), 1)
        form = forms[0]
        self.assertEqual((form.get("role"), form.get("method"),
                          form.get("action")),
                         ("search", "get", "/procedures/"))
        fields = form.find_all("input")
        self.assertEqual(len(fields), 1)
        self.assertEqual(
            [fields[0].get(n) for n in ("type", "name", "aria-label",
                                        "placeholder")],
            ["search", "q", strings["search_label"],
             strings["search_placeholder"]])
        button = form.find("button")
        self.assertEqual((button.get("type"), button.text()),
                         ("submit", strings["search_button"]))

    def test_current_link(self) -> None:
        """Scenario: Current link on the application's pages."""
        inside = {"/lab/tasks/": [task_url(self.task),
                                  task_url(self.task, "edit"),
                                  "/lab/tasks/new/"],
                  "/lab/registry/": ["/lab/registry/groups/"],
                  "/lab/journal/": ["/lab/journal/new/"]}
        self.client.force_login(self.kl)
        for entry in ns.links():
            url = entry["url"]
            if not url.startswith("/lab/"):
                continue
            for path in [url, *inside.get(url, [])]:
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    expected = ns.expected_marks(path)
                    self.assertTrue(expected, f"{path} lies in no section")
                    self.assertEqual(ns.marks(response), expected)

    def test_an_account_page_marks_nothing(self) -> None:
        self.client.force_login(self.kl)
        response = self.client.get("/lab/accounts/password/")
        self.assertEqual(ns.marks(response), {})

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

    def test_scripts_from_the_applications_files(self) -> None:
        """Scenario: Scripts from the application's files (web-app:
        Scripts)."""
        menu = [e["url"] for e in ns.links() if e["url"].startswith("/lab/")]
        self.client.force_login(self.kl)
        for path in [*menu, task_url(self.task), task_url(self.task, "edit")]:
            with self.subTest(path=path):
                self.assert_scripts(self.client.get(path))
        self.client.logout()
        with self.subTest(path="/lab/accounts/login/", signed_in=False):
            self.assert_scripts(self.client.get("/lab/accounts/login/"))

    def assert_scripts(self, response) -> None:
        self.assertEqual(response.status_code, 200)
        root = page(response)
        for script in root.find_all("script"):
            self.assertTrue(script.get("src", "").startswith("/lab/static/"),
                            script.get("src"))
            self.assertEqual(script.text(), "")
        for element in root.walk():
            for name in element.attrs:
                self.assertFalse(
                    name.startswith(("on", "hx-on", "data-hx-on")),
                    f"<{element.tag}> carries {name}")
            for attr in ("hx-swap", "data-hx-swap"):
                if attr in element.attrs:
                    tokens = element.attrs[attr].split()
                    style = tokens[0] if tokens else ""
                    if style.startswith("morph"):
                        self.assertIn(
                            style, ALLOWED_MORPH_SWAPS,
                            f"<{element.tag}> carries {attr}={style!r}")
        config = root.find("meta", attrs={"name": "htmx-config"})
        self.assertIsNotNone(config, "no meta htmx-config")
        htmx_config = json.loads(config.get("content"))
        self.assertIs(htmx_config.get("allowEval"), False)
        self.assertIs(htmx_config.get("historyCacheSize"), 0)
        self.assertIs(htmx_config.get("refreshOnHistoryMiss"), True)

    def test_the_sidebar_toggle(self) -> None:
        for signed_in, language in ((False, "de"), (True, "en")):
            with self.subTest(signed_in=signed_in, language=language):
                if language == "en":
                    accept(language="en")
                header = self.shell(signed_in).find("header",
                                                    cls="site-header")
                toggles = header.find_all("button",
                                          attrs={"data-sidebar-toggle": True})
                self.assertEqual(len(toggles), 1)
                self.assertEqual(
                    (toggles[0].get("type"), toggles[0].get("aria-expanded"),
                     toggles[0].text()),
                    ("button", "true", site_strings(language)["nav_toggle"]))
                brand = toggles[0].parent
                self.assertIn("site-brand", brand.classes)
                self.assertEqual(
                    [c.tag for c in brand.children if not isinstance(c, str)],
                    ["button", "a"])

    def test_body_carries_morph_extension(self) -> None:
        """The page shell enables the idiomorph hx-ext on body."""
        for signed_in in (True, False):
            with self.subTest(signed_in=signed_in):
                self.client.logout()
                root = self.shell(signed_in)
                shell_scripts(root)
                body = root.find("body")
                self.assertIsNotNone(body)
                self.assertEqual(body.get("hx-ext"), "morph")

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
        body = root.find("body")
        self.assertIsNotNone(body)
        self.assertEqual(body.get("hx-ext"), "morph")
        hrefs = [e.get("href") for e in root.find_all("link")
                 if e.get("rel") == "stylesheet"]
        self.assertEqual(hrefs[-1], "/lab/static/lab.css")
        self.assertEqual(len(hrefs), 5)


class InventoryShellTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")

    def setUp(self) -> None:
        self.enterContext(ticking(berlin(2026, 11, 4, 8)))
        self.item = make_item(self.kl, "CH-0012", quantity=5)
        self.vessel = make_vessel(self.kl, article="CH-0012")

    def marks(self, path: str) -> dict[str, str]:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return ns.marks(response)

    def paths(self) -> list[str]:
        return ["/lab/inventory/batches/",
                "/lab/inventory/vessels/",
                "/lab/inventory/deliveries/",
                f"/lab/inventory/items/{self.item.pk}/",
                f"/lab/inventory/batches/{self.vessel.batch_id}/",
                f"/lab/inventory/vessels/{self.vessel.pk}/",
                f"/lab/inventory/vessels/{self.vessel.pk}/transfer/",
                f"/lab/inventory/batches/{self.vessel.batch_id}/vessels/new/",
                "/lab/inventory/end-products/new/",
                "/lab/inventory/deliveries/new/",
                "/lab/inventory/batches/new/",
                f"/lab/inventory/items/{self.item.pk}/fill/",
                f"/lab/inventory/items/{self.item.pk}/edit/"]

    def test_every_page_under_the_inventory_marks_its_section(self) -> None:
        self.client.force_login(self.kl)
        for path in ["/lab/inventory/end-products/", *self.paths()]:
            with self.subTest(path=path):
                expected = ns.expected_marks(path)
                self.assertTrue(expected, f"{path} lies in no section")
                self.assertEqual(self.marks(path), expected)

    def test_english_texts(self) -> None:
        accept(language="en")
        response = self.client.get("/lab/inventory/end-products/")
        self.assertEqual(ns.shown(page(response)), ns.expected("en"))

    def test_the_inventory_pages_carry_the_shell(self) -> None:
        self.client.force_login(self.kl)
        for path in ["/lab/inventory/end-products/", *self.paths()]:
            with self.subTest(path=path):
                response = self.client.get(path)
                root = page(response)
                shell_scripts(root)
                self.assertEqual(root.find("body").get("hx-ext"), "morph")
                self.assertIsNotNone(root.find("header", cls="site-header"))
                hrefs = [e.get("href") for e in root.find_all("link")
                         if e.get("rel") == "stylesheet"]
                self.assertEqual(
                    hrefs, [f"/lab/static/site/{n}" for n in STYLESHEETS]
                    + ["/lab/static/lab.css"])

    def test_scripts_on_every_page(self) -> None:
        """Scenario: Scripts on every page."""
        for path in ("/lab/inventory/end-products/",
                     f"/lab/inventory/items/{self.item.pk}/",
                     "/lab/planning/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                shell_scripts(page(response))

    def test_the_script_is_collected(self) -> None:
        self.assertIsNotNone(finders.find("lab.js"))

    def test_the_message_shows_above_the_content(self) -> None:
        self.client.force_login(self.kl)
        done = self.client.post(
            "/lab/inventory/items/%d/edit/" % self.item.pk,
            {"category": "", "note": "Neu", "status": "active"},
            follow=True)
        root = page(done)
        self.assertIsNotNone(root.find("ul", cls="lab-messages"))


class PlanningShellTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")

    def test_the_planning_list_marks_its_section(self) -> None:
        for path in ("/lab/planning/", "/lab/planning/?all=1"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(ns.marks(response),
                                 ns.expected_marks("/lab/planning/"))

    def test_the_planning_list_carries_the_shell(self) -> None:
        for signed_in in (False, True):
            if signed_in:
                self.client.force_login(self.kl)
            with self.subTest(signed_in=signed_in):
                response = self.client.get("/lab/planning/")
                root = page(response)
                shell_scripts(root)
                self.assertEqual(root.find("body").get("hx-ext"), "morph")
                self.assertIsNotNone(root.find("header", cls="site-header"))
                hrefs = [e.get("href") for e in root.find_all("link")
                         if e.get("rel") == "stylesheet"]
                self.assertEqual(
                    hrefs, [f"/lab/static/site/{n}" for n in STYLESHEETS]
                    + ["/lab/static/lab.css"])


class RegistryShellTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.substance = substance_for("CH-0012")

    def test_the_registry_pages_mark_their_section(self) -> None:
        self.client.force_login(self.kl)
        for path in ("/lab/registry/",
                     "/lab/registry/substances/cinnamic-acid/",
                     "/lab/registry/substances/cinnamic-acid/edit/",
                     "/lab/registry/substances/new/",
                     "/lab/registry/groups/",
                     "/lab/registry/groups/new/",
                     "/lab/registry/chemical-classes/",
                     "/lab/registry/projects/",
                     "/lab/registry/reaction-types/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)
                expected = ns.expected_marks(path)
                self.assertTrue(expected, f"{path} lies in no section")
                self.assertEqual(ns.marks(response), expected)

    def test_the_registry_pages_carry_the_shell(self) -> None:
        for path in ("/lab/registry/", "/lab/registry/groups/",
                     "/lab/registry/substances/cinnamic-acid/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                root = page(response)
                shell_scripts(root)
                self.assertEqual(root.find("body").get("hx-ext"), "morph")
                self.assertIsNotNone(root.find("header", cls="site-header"))
                hrefs = [e.get("href") for e in root.find_all("link")
                         if e.get("rel") == "stylesheet"]
                self.assertEqual(
                    hrefs, [f"/lab/static/site/{n}" for n in STYLESHEETS]
                    + ["/lab/static/lab.css"])


class LabFrameWidthTests(SimpleTestCase):
    """The main lists' pages use the full width right of the sidebar:
    the application's stylesheet lifts the shell's cap from them."""

    def rules(self) -> list[tuple[str, str]]:
        text = re.sub(r"/\*.*?\*/", "",
                      (REPO / "webapp" / "orgsyndb_web" / "static"
                       / "lab.css").read_text(encoding="utf-8"),
                      flags=re.DOTALL)
        return [(" ".join(part.split()), body)
                for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}",
                                                 text)
                for part in selector.split(",")]

    def test_the_lab_frame_has_no_width_cap(self) -> None:
        caps = [re.findall(r"(?<![-\w])max-width:\s*([^;}]+)", body)
                for selector, body in self.rules()
                if selector == "body.lab-frame"]
        found = [value.strip() for values in caps for value in values]
        self.assertIn("none", found)
        self.assertEqual(set(found), {"none"})


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

    def test_htmx_kept_with_its_licence(self) -> None:
        """Scenario: htmx kept with its licence (web-app: Scripts)."""
        found = finders.find(HTMX.removeprefix("/lab/static/"))
        self.assertTrue(found, f"{HTMX} is not found")
        self.assertTrue((Path(found).parent / "LICENSE").is_file())

    def test_idiomorph_kept_with_its_licence(self) -> None:
        """Scenario: idiomorph kept with its licence (web-app: Scripts)."""
        found = finders.find(IDIOMORPH.removeprefix("/lab/static/"))
        self.assertTrue(found, f"{IDIOMORPH} is not found")
        self.assertTrue((Path(found).parent / "LICENSE").is_file())

    def test_stimulus_kept_with_its_licence(self) -> None:
        """Scenario: Stimulus kept with its licence (web-app: Scripts)."""
        found = finders.find(STIMULUS.removeprefix("/lab/static/"))
        self.assertTrue(found, f"{STIMULUS} is not found")
        self.assertTrue((Path(found).parent / "LICENSE").is_file())

    def test_the_sites_script_is_collected(self) -> None:
        found = finders.find(SHELL_SCRIPT.removeprefix("/lab/static/"))
        self.assertTrue(found, f"{SHELL_SCRIPT} is not found")
        self.assertEqual(Path(found).read_bytes(),
                         (JS / "site.js").read_bytes())


class ScriptsHelperTests(SimpleTestCase):
    """Unit tests for the morph swap check in ``ShellTests.assert_scripts``."""

    def _page_with_swap(self, attr: str, value: str) -> HttpResponse:
        escaped = html.escape(value, quote=True)
        config = json.dumps({
            "allowEval": False,
            "historyCacheSize": 0,
            "refreshOnHistoryMiss": True,
        })
        return HttpResponse(
            "<html><head>"
            f"<meta name='htmx-config' content='{config}'>"
            f'</head><body><div {attr}="{escaped}"></div></body></html>')

    def test_assert_scripts_rejects_disallowed_morph_swaps(self) -> None:
        for attr in ("hx-swap", "data-hx-swap"):
            for value in ('morph:{morphStyle:"innerHTML"}',
                          "morph:custom",
                          "morph:{morphStyle: 'innerHTML'} scroll:top"):
                with self.subTest(attr=attr, value=value):
                    with self.assertRaises(AssertionError):
                        ShellTests.assert_scripts(
                            self, self._page_with_swap(attr, value))

    def test_assert_scripts_allows_standard_morph_swaps(self) -> None:
        for attr in ("hx-swap", "data-hx-swap"):
            for value in ("morph",
                          "morph:outerHTML",
                          "morph:innerHTML",
                          "morph:outerHTML scroll:top",
                          "outerHTML"):
                with self.subTest(attr=attr, value=value):
                    ShellTests.assert_scripts(
                        self, self._page_with_swap(attr, value))


class LanguageTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.task = make_task(cls.kl, substance="X", started=date(2026, 11, 3))

    def language(self, path: str = "/lab/tasks/") -> str:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return page(response).find("html").get("lang")

    def test_german_site(self) -> None:
        accept(language="de")
        response = self.client.get("/lab/tasks/?state=all")
        root = page(response)
        self.assertEqual(root.find("html").get("lang"), "de")
        header, rows = table(root)
        self.assertEqual(rows[0]["Beginn"].text(), "03.11.2026")

    def test_english_site(self) -> None:
        """Scenario: English site."""
        accept(language="en")
        response = self.client.get("/lab/tasks/?state=all")
        root = page(response)
        self.assertEqual(root.find("html").get("lang"), "en")
        self.assertEqual(ns.shown(root), ns.expected("en"))
        header = root.find("header", cls="site-header")
        self.assertEqual([a.text() for a in header.find_all("a")
                          if a.get("href", "").startswith(
                              "/lab/accounts/login/")], ["Sign in"])
        header, rows = table(root)
        self.assertEqual(rows[0]["Started"].text(), "2026-11-03")

    def test_english_site_dates_on_the_task_page(self) -> None:
        accept(language="en")
        self.assertIn("2026-11-03",
                      page(self.client.get(task_url(self.task))).text())

    def test_german_site_dates_on_the_task_page(self) -> None:
        accept(language="de")
        self.assertIn("03.11.2026",
                      page(self.client.get(task_url(self.task))).text())

    def test_before_any_import(self) -> None:
        """Scenario: Before any import."""
        response = self.client.get("/lab/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page(response).find("html").get("lang"), "de")
        self.assertEqual(response["Content-Language"], "de")

    def test_language_follows_the_latest_accepted_import(self) -> None:
        """Requirement: Interface language (the latest accepted
        import)."""
        accept(language="en")
        self.assertEqual(self.language(), "en")
        accept(language="de")
        self.assertEqual(self.language(), "de")
        accept(language="en")
        self.assertEqual(self.language(), "en")

    def test_a_refused_import_does_not_change_the_language(self) -> None:
        """Requirement: Interface language (accepted imports only)."""
        accept(language="en")
        make_import(outcome="refused")
        self.assertEqual(self.language(), "en")

    def test_the_latest_accepted_import_is_the_one_received_last(
            self) -> None:
        """Requirement: Accepting an import (the latest accepted import
        is the accepted import received last)."""
        with frozen(berlin(2026, 11, 2)):
            accept(language="en")
        with frozen(berlin(2026, 11, 1)):
            accept(language="de")
        self.assertEqual(self.language(), "en")

    def test_sign_in_page_speaks_the_language(self) -> None:
        accept(language="en")
        root = page(self.client.get("/lab/accounts/login/"))
        self.assertEqual(root.find("html").get("lang"), "en")
        header = root.find("header", cls="site-header")
        self.assertIn("Sign in", [a.text() for a in header.find_all("a")])


class NoCollectionIndexTests(SimpleTestCase):

    def test_the_setting_is_gone(self) -> None:
        """Requirement: Settings from the environment (no
        `ORGSYNDB_INDEX`)."""
        from django.conf import settings
        self.assertFalse(hasattr(settings, "ORGSYNDB_INDEX"))

    def test_the_module_is_gone(self) -> None:
        """Requirement: Collection index (removed)."""
        import importlib.util
        self.assertIsNone(importlib.util.find_spec("orgsyndb_web.index"))


class AccountOnAPhoneTests(TestCase):
    """The account in the title's row of a phone-sized window."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")

    def test_the_password_page_leads_to_the_access_tokens(self) -> None:
        self.client.force_login(self.kl)
        main = page(self.client.get("/lab/accounts/password/")).find("main")
        self.assertIn("/lab/accounts/tokens/",
                      [a.get("href") for a in main.find_all("a")])

    def test_a_phone_shows_only_the_initials_and_the_sign_out(self) -> None:
        self.client.force_login(self.kl)
        header = page(self.client.get("/lab/tasks/")).find(
            "header", cls="site-header")
        tokens = header.find("a", href="/lab/accounts/tokens/")
        self.assertIn("lab-account-tokens", tokens.classes)
        css = (REPO / "webapp" / "orgsyndb_web" / "static" / "lab.css"
               ).read_text(encoding="utf-8")
        rule = re.search(r"@media \(max-width: 30rem\) \{\s*"
                         r"\.lab-account-tokens \{ display: none; \}", css)
        self.assertIsNotNone(rule, "no rule hides the token link on a phone")
