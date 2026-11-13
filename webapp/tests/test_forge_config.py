"""Tests of the settings of the OpenID provider and of Forgejo's API
(web-app: OpenID provider, Forgejo accounts; the cookie paths of
Accounts and sign-in)."""

import base64

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, TestCase

from orgsyndb_web.config import settings_from

from . import PASSWORD, make_user
from .forge_support import key_pem, key_setting, public_pem

BASE = {"ORGSYNDB_SECRET_KEY": "k", "ORGSYNDB_ALLOWED_HOSTS": "lab.test"}
KEYS = {"ORGSYNDB_URL", "ORGSYNDB_APP_INTERNAL_URL", "ORGSYNDB_FORGE_URL",
        "ORGSYNDB_FORGE_PASSWORD", "ORGSYNDB_FORGE_CLIENT_SECRET",
        "OAUTH2_PROVIDER"}


def forge_settings(environ: dict[str, str]) -> dict:
    from orgsyndb_web.config import forge_settings as function
    return function(environ)


def b64(text: str | bytes) -> str:
    data = text.encode() if isinstance(text, str) else text
    return base64.b64encode(data).decode("ascii")


class ForgeSettingsTests(SimpleTestCase):
    """The settings ``forge_settings`` makes of the environment."""

    def test_it_returns_exactly_these_settings(self) -> None:
        self.assertEqual(set(forge_settings({})), KEYS)

    def test_the_defaults(self) -> None:
        """Requirement: OpenID provider (the settings' defaults)."""
        result = forge_settings({})
        self.assertEqual(result["ORGSYNDB_URL"], "http://localhost:8000")
        self.assertEqual(result["ORGSYNDB_APP_INTERNAL_URL"],
                         "http://app:8000")
        self.assertEqual(result["ORGSYNDB_FORGE_URL"], "")
        self.assertEqual(result["ORGSYNDB_FORGE_PASSWORD"], "")
        self.assertEqual(result["ORGSYNDB_FORGE_CLIENT_SECRET"], "")
        self.assertEqual(result["OAUTH2_PROVIDER"]["OIDC_RSA_PRIVATE_KEY"],
                         "")

    def test_the_variables_are_taken_as_given(self) -> None:
        result = forge_settings({
            "ORGSYNDB_URL": "https://lab.example.org",
            "ORGSYNDB_APP_INTERNAL_URL": "http://app.internal:9000",
            "ORGSYNDB_FORGE_URL": "http://forge:3000/api/v1",
            "ORGSYNDB_FORGE_PASSWORD": "pw",
            "ORGSYNDB_FORGE_CLIENT_SECRET": "secret"})
        self.assertEqual(result["ORGSYNDB_URL"], "https://lab.example.org")
        self.assertEqual(result["ORGSYNDB_APP_INTERNAL_URL"],
                         "http://app.internal:9000")
        self.assertEqual(result["ORGSYNDB_FORGE_URL"],
                         "http://forge:3000/api/v1")
        self.assertEqual(result["ORGSYNDB_FORGE_PASSWORD"], "pw")
        self.assertEqual(result["ORGSYNDB_FORGE_CLIENT_SECRET"], "secret")

    def test_the_trailing_slash_of_the_public_address_is_dropped(
            self) -> None:
        for given, wanted in (("https://lab.example.org/",
                               "https://lab.example.org"),
                              ("http://localhost:8080/",
                               "http://localhost:8080"),
                              ("http://localhost:8080",
                               "http://localhost:8080")):
            with self.subTest(given=given):
                self.assertEqual(
                    forge_settings({"ORGSYNDB_URL": given})["ORGSYNDB_URL"],
                    wanted)

    def test_the_key_is_decoded_from_base64(self) -> None:
        """Requirement: OpenID provider (a PEM-encoded RSA private key in
        base64)."""
        result = forge_settings({"ORGSYNDB_OIDC_KEY": key_setting()})
        self.assertEqual(result["OAUTH2_PROVIDER"]["OIDC_RSA_PRIVATE_KEY"],
                         key_pem().decode("ascii"))

    def test_malformed_base64_is_refused_naming_the_variable(self) -> None:
        for given in ("not base64 at all!", "####", "abc"):
            with self.subTest(given=given):
                with self.assertRaises(ImproperlyConfigured) as caught:
                    forge_settings({"ORGSYNDB_OIDC_KEY": given})
                self.assertIn("ORGSYNDB_OIDC_KEY", str(caught.exception))

    def test_a_value_that_is_no_private_key_is_refused(self) -> None:
        public = b64(public_pem())
        for label, given in (
                ("text", b64("hello world")),
                ("a public key", public),
                ("a truncated key", b64(key_pem()[:120])),
                ("the header alone", b64(
                    "-----BEGIN PRIVATE KEY-----\nAAAA\n"
                    "-----END PRIVATE KEY-----\n"))):
            with self.subTest(given=label):
                with self.assertRaises(ImproperlyConfigured) as caught:
                    forge_settings({"ORGSYNDB_OIDC_KEY": given})
                self.assertIn("ORGSYNDB_OIDC_KEY", str(caught.exception))


class SettingsFromTests(SimpleTestCase):

    def test_settings_from_holds_the_forge_settings(self) -> None:
        """Requirement: OpenID provider (`settings_from` merges
        ``forge_settings``)."""
        environ = {**BASE, "ORGSYNDB_URL": "http://localhost:8080/",
                   "ORGSYNDB_FORGE_URL": "http://forge:3000/api/v1",
                   "ORGSYNDB_OIDC_KEY": key_setting()}
        result = settings_from(environ)
        for key, value in forge_settings(environ).items():
            with self.subTest(key=key):
                self.assertEqual(result[key], value)
        self.assertEqual(result["ORGSYNDB_URL"], "http://localhost:8080")

    def test_settings_from_still_needs_the_secret_key(self) -> None:
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({"ORGSYNDB_ALLOWED_HOSTS": "lab.test",
                           "ORGSYNDB_OIDC_KEY": key_setting()})
        self.assertIn("ORGSYNDB_SECRET_KEY", str(caught.exception))

    def test_settings_from_refuses_a_bad_key(self) -> None:
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({**BASE, "ORGSYNDB_OIDC_KEY": b64("hello")})
        self.assertIn("ORGSYNDB_OIDC_KEY", str(caught.exception))


class InstalledProviderTests(SimpleTestCase):

    def test_the_toolkit_is_installed(self) -> None:
        """Requirement: OpenID provider (django-oauth-toolkit)."""
        self.assertTrue(apps.is_installed("oauth2_provider"))

    def test_the_applications_settings_hold_the_provider(self) -> None:
        self.assertIn("OIDC_RSA_PRIVATE_KEY", settings.OAUTH2_PROVIDER)


class CookiePathTests(TestCase):
    """Scenario: Cookie path."""

    def test_the_settings(self) -> None:
        self.assertEqual(settings.SESSION_COOKIE_PATH, "/lab/")
        self.assertEqual(settings.CSRF_COOKIE_PATH, "/lab/")

    def test_the_cookies_of_a_sign_in_have_the_path(self) -> None:
        make_user("kl", "KL")
        client = Client()
        client.get("/lab/accounts/login/")
        done = client.post("/lab/accounts/login/", {"username": "kl",
                                                    "password": PASSWORD})
        self.assertEqual(done.status_code, 302)
        for name in ("sessionid", "csrftoken"):
            with self.subTest(cookie=name):
                self.assertIn(name, client.cookies)
                self.assertEqual(client.cookies[name]["path"], "/lab/")
