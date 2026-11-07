"""Tests of the application's settings (web-app: Settings from the
environment, Paths under /lab/)."""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, TestCase

from orgsyndb_web.config import settings_from

from . import PASSWORD, field_value, make_user, page

WEBAPP = Path(__file__).resolve().parents[1]
BASE = {"ORGSYNDB_SECRET_KEY": "k", "ORGSYNDB_ALLOWED_HOSTS": "lab.test"}


class SecretKeyAndHostTests(SimpleTestCase):

    def test_secret_key_is_required(self) -> None:
        """Scenario: Secret key required."""
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({"ORGSYNDB_ALLOWED_HOSTS": "lab.test"})
        self.assertIn("ORGSYNDB_SECRET_KEY", str(caught.exception))

    def test_secret_key_is_required_when_debug_is_off(self) -> None:
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({"ORGSYNDB_DEBUG": "false",
                           "ORGSYNDB_ALLOWED_HOSTS": "lab.test"})
        self.assertIn("ORGSYNDB_SECRET_KEY", str(caught.exception))

    def test_allowed_hosts_are_required(self) -> None:
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({"ORGSYNDB_SECRET_KEY": "k"})
        self.assertIn("ORGSYNDB_ALLOWED_HOSTS", str(caught.exception))

    def test_debug_needs_neither(self) -> None:
        result = settings_from({"ORGSYNDB_DEBUG": "true"})
        self.assertIs(result["DEBUG"], True)
        self.assertEqual(list(result["ALLOWED_HOSTS"]),
                         ["localhost", "127.0.0.1"])
        self.assertTrue(result["SECRET_KEY"])

    def test_debug_keeps_given_values(self) -> None:
        result = settings_from({"ORGSYNDB_DEBUG": "1",
                                "ORGSYNDB_SECRET_KEY": "mine",
                                "ORGSYNDB_ALLOWED_HOSTS": "a.test"})
        self.assertEqual(result["SECRET_KEY"], "mine")
        self.assertEqual(list(result["ALLOWED_HOSTS"]), ["a.test"])

    def test_values_are_taken_as_given(self) -> None:
        result = settings_from({"ORGSYNDB_SECRET_KEY": "s3",
                                "ORGSYNDB_ALLOWED_HOSTS":
                                "a.example.org,b.example.org"})
        self.assertEqual(result["SECRET_KEY"], "s3")
        self.assertEqual(list(result["ALLOWED_HOSTS"]),
                         ["a.example.org", "b.example.org"])
        self.assertIs(result["DEBUG"], False)


class FlagTests(SimpleTestCase):

    def test_flag_words(self) -> None:
        for word, value in (("true", True), ("yes", True), ("on", True),
                            ("1", True), ("false", False), ("no", False),
                            ("off", False), ("0", False)):
            with self.subTest(word=word):
                result = settings_from({**BASE, "ORGSYNDB_DEBUG": word})
                self.assertIs(result["DEBUG"], value)

    def test_malformed_flag_names_the_variable(self) -> None:
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({**BASE, "ORGSYNDB_DEBUG": "maybe"})
        self.assertIn("ORGSYNDB_DEBUG", str(caught.exception))


class DatabaseUrlTests(SimpleTestCase):

    def database(self, url: str) -> dict:
        return settings_from({**BASE, "ORGSYNDB_DATABASE_URL": url}
                             )["DATABASES"]["default"]

    def test_postgres_url(self) -> None:
        """Scenario: Database URLs."""
        db = self.database("postgres://lab:secret@db:5432/lab")
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(
            (db["NAME"], db["USER"], db["PASSWORD"], db["HOST"],
             db["PORT"]),
            ("lab", "lab", "secret", "db", "5432"))

    def test_postgres_url_without_port(self) -> None:
        db = self.database("postgres://lab:secret@db/lab")
        self.assertEqual((db["HOST"], db["PORT"], db["NAME"]),
                         ("db", "", "lab"))

    def test_sqlite_url(self) -> None:
        db = self.database("sqlite:////tmp/x.sqlite3")
        self.assertEqual(db["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(str(db["NAME"]), "/tmp/x.sqlite3")

    def test_other_scheme_is_refused(self) -> None:
        with self.assertRaises(ImproperlyConfigured) as caught:
            self.database("mysql://db/lab")
        self.assertIn("ORGSYNDB_DATABASE_URL", str(caught.exception))

    def test_default_is_the_sqlite_file_of_the_application(self) -> None:
        db = settings_from(BASE)["DATABASES"]["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(Path(str(db["NAME"])), WEBAPP / "db.sqlite3")


class IndexPathTests(SimpleTestCase):

    def test_default_path(self) -> None:
        self.assertEqual(settings_from(BASE)["ORGSYNDB_INDEX"],
                         "/var/lib/orgsyndb/current/index.json")

    def test_path_from_the_environment(self) -> None:
        result = settings_from({**BASE, "ORGSYNDB_INDEX": "/x/index.json"})
        self.assertEqual(result["ORGSYNDB_INDEX"], "/x/index.json")


class DemoFlagTests(SimpleTestCase):

    def test_demo_flag(self) -> None:
        """Scenario: Demo flag."""
        self.assertIs(settings_from(BASE)["ORGSYNDB_DEMO"], False)
        self.assertIs(settings_from({**BASE, "ORGSYNDB_DEMO": "yes"})
                      ["ORGSYNDB_DEMO"], True)
        with self.assertRaises(ImproperlyConfigured) as caught:
            settings_from({**BASE, "ORGSYNDB_DEMO": "maybe"})
        self.assertIn("ORGSYNDB_DEMO", str(caught.exception))

    def test_demo_flag_takes_every_flag_word(self) -> None:
        for word, expected in (("1", True), ("ON", True), ("off", False),
                               ("", False)):
            with self.subTest(word=word):
                self.assertIs(settings_from({**BASE, "ORGSYNDB_DEMO": word})
                              ["ORGSYNDB_DEMO"], expected)

    def test_the_project_reads_the_flag(self) -> None:
        self.assertIs(settings.ORGSYNDB_DEMO, False)


class AppliedSettingsTests(SimpleTestCase):

    def test_settings_of_the_project(self) -> None:
        self.assertEqual(settings.TIME_ZONE, "Europe/Berlin")
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER,
                         ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        self.assertEqual(settings.STATIC_URL, "/lab/static/")
        self.assertIn("lab.example.org", settings.ALLOWED_HOSTS)


class ProxyTests(TestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        make_user("kl", "KL")

    def sign_in(self, client: Client, host: str, origin: str):
        headers = {"HTTP_HOST": host, "HTTP_X_FORWARDED_PROTO": "https"}
        form = client.get("/lab/accounts/login/", **headers)
        self.assertEqual(form.status_code, 200)
        token = field_value(page(form), "csrfmiddlewaretoken")
        return client.post(
            "/lab/accounts/login/",
            {"username": "kl", "password": PASSWORD,
             "csrfmiddlewaretoken": token},
            HTTP_ORIGIN=origin, **headers)

    def test_request_through_the_proxy_is_secure(self) -> None:
        """Scenario: Requests through the proxy."""
        done = self.sign_in(Client(enforce_csrf_checks=True),
                            "lab.example.org", "https://lab.example.org")
        self.assertEqual(done.status_code, 302)

    def test_host_outside_the_list_is_refused(self) -> None:
        """Scenario: Requests through the proxy (other host)."""
        client = Client(enforce_csrf_checks=True)
        done = client.post(
            "/lab/accounts/login/",
            {"username": "kl", "password": PASSWORD},
            HTTP_HOST="other.example.org", HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN="https://other.example.org")
        self.assertEqual(done.status_code, 400)


class PathTests(TestCase):

    def test_entry_and_other_paths_answer_404(self) -> None:
        """Scenario: Entry and outside paths."""
        self.assertEqual(self.client.get("/lab/").status_code, 200)
        for path in ("/procedures/", "/", "/lab/nowhere/", "/tasks/",
                     "/compounds/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
