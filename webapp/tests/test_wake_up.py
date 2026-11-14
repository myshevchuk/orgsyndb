"""Tests of the application's wake-up of the builder (collection-import:
Wake-up after a registry write; web-app: Settings from the environment).

The application is tested from the outside: ``ORGSYNDB_WAKE_URL`` names
a recording HTTP server in a thread, and the tests count what it
received. The tests run as ``TransactionTestCase``, with autocommit on,
so that a wake-up sent after a commit is seen as it is sent. A test that
expects no request first makes a write that must send one, so that it
cannot pass because nothing is sent at all.
"""

import contextlib
import io
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterator
from unittest import mock

from django.core.management import call_command
from django.db import transaction
from django.test import TransactionTestCase, override_settings

from . import (PASSWORD, load_demo_registry, make_article,
               make_demo_accounts, make_demo_notebooks, make_class,
               make_group, make_substance, make_user, page, substance_for,
               task_form_data)
from .collection_support import (TOKEN, import_collection, make_token,
                                 manifest, post, refused, request_id)
from .registry_support import (NEW_SUBSTANCE, OLD_LAYOUT, small_snapshot,
                               term_url, write_json)
from .task_support import NEW as NEW_TASK
from .test_registry_forms import substance_data

ADMIN = "/lab/admin/"
# Seconds a test waits for a wake-up it expects, and after the last one
# for another that it does not.
PATIENCE = 3.0
SETTLE = 0.3


class Recorder:
    """A local HTTP server that keeps every request it receives, as a
    table of ``method``, ``path`` and lower-case ``headers``, and
    answers ``status`` with an empty body; with ``delay`` it waits that
    many seconds, or until ``stop``, before it answers."""

    def __init__(self, status: int = 202, delay: float = 0.0) -> None:
        self.status = status
        self.delay = delay
        self.requests: list[dict[str, Any]] = []
        self.released = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def handle_any(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                owner.requests.append({
                    "method": self.command, "path": self.path,
                    "headers": {name.lower(): value
                                for name, value in self.headers.items()}})
                if owner.delay:
                    owner.released.wait(owner.delay)
                try:
                    self.send_response(owner.status)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                except OSError:
                    pass

            do_POST = do_GET = do_PUT = do_DELETE = handle_any

            def log_message(self, *args: Any) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/wake"

    def stop(self) -> None:
        self.released.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def closed_url() -> str:
    """An address on a port nothing listens on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{sock.getsockname()[1]}/wake"


class WakeCase(TransactionTestCase):
    """A test case with autocommit on, whose database holds the accounts
    ``kl`` and ``boss`` (staff), the group ``reagents`` and the class
    ``ketones``, and whose ``ORGSYNDB_WAKE_URL`` names ``recorder``. The
    records are made before the setting is overridden, so that the
    recorder has received nothing when a test starts."""

    def setUp(self) -> None:
        self.kl = make_user("kl", "KL", "Klara", "Lehmann")
        self.staff = make_user("boss", "BO", is_staff=True,
                               is_superuser=True)
        make_group("reagents", "Reagents")
        make_class("ketones", "Ketones")
        self.recorder = Recorder()
        self.addCleanup(self.recorder.stop)
        self.enterContext(override_settings(
            ORGSYNDB_WAKE_URL=self.recorder.url,
            ORGSYNDB_BUILDER_TOKEN=TOKEN))

    @contextlib.contextmanager
    def silent(self) -> Iterator[None]:
        """Make no wake-up while the block runs: the records a test sets
        up are not what it tests."""
        with override_settings(ORGSYNDB_WAKE_URL=""):
            yield

    def received(self) -> int:
        return len(self.recorder.requests)

    def wait_until(self, condition: Callable[[], Any]) -> bool:
        deadline = time.monotonic() + PATIENCE
        while time.monotonic() < deadline:
            if condition():
                return True
            time.sleep(0.02)
        return bool(condition())

    def assertReceived(self, total: int) -> None:
        """Assert that the recorder has received ``total`` requests since
        the test began, waiting for them to come and then for any more,
        and that each was a ``POST`` with the builder's token."""
        self.wait_until(lambda: self.received() >= total)
        time.sleep(SETTLE)
        self.assertEqual(self.received(), total,
                         self.recorder.requests)
        for request in self.recorder.requests:
            self.assertEqual(request["method"], "POST")
            self.assertEqual(request["headers"].get("authorization"),
                             f"Bearer {TOKEN}")

    def control(self) -> None:
        """Make a write that sends one wake-up, and assert that it did:
        the first of the requests a test expects."""
        from vocabulary.models import Project
        Project.objects.create(key="control", label="Control")
        self.assertReceived(1)


class WriteTests(WakeCase):
    """Scenario: A substance saved; Every write path, once each."""

    def test_a_substance_through_its_form_and_two_terms_in_one_transaction(
            self) -> None:
        """Scenario: A substance saved (one `POST` with the builder token
        after the first commit, one after the second)."""
        from vocabulary.models import Project
        self.client.force_login(self.kl)
        data = substance_data(page(self.client.get(NEW_SUBSTANCE)))
        done = self.client.post(NEW_SUBSTANCE, data)
        self.assertEqual(done.status_code, 302)
        self.assertReceived(1)
        with transaction.atomic():
            Project.objects.create(key="one", label="One")
            Project.objects.create(key="two", label="Two")
            time.sleep(SETTLE)
            self.assertEqual(self.received(), 1,
                             "a wake-up was sent before the commit")
        self.assertReceived(2)

    def test_a_project_through_the_admin(self) -> None:
        """Scenario: Every write path, once each (a project saved
        through the admin)."""
        from vocabulary.models import Project
        self.client.force_login(self.staff)
        done = self.client.post(f"{ADMIN}vocabulary/project/add/", {
            "key": "admin-made", "label": "Admin made", "label_de": "",
            "parent": ""})
        self.assertEqual(done.status_code, 302)
        self.assertTrue(Project.objects.filter(key="admin-made").exists())
        self.assertReceived(1)

    def test_projects_deleted_together_in_the_admin(self) -> None:
        """Requirement: Wake-up after a registry write (a bulk deletion
        through the admin, one `POST`)."""
        from vocabulary.models import Project
        with self.silent():
            spare = Project.objects.create(key="spare", label="Spare")
            other = Project.objects.create(key="other", label="Other")
        self.client.force_login(self.staff)
        done = self.client.post(f"{ADMIN}vocabulary/project/", {
            "action": "delete_selected",
            "_selected_action": [str(spare.pk), str(other.pk)],
            "post": "yes"})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(Project.objects.exists())
        self.assertReceived(1)

    def test_an_account_renamed_and_another_with_a_new_display_name(
            self) -> None:
        """Scenario: Every write path, once each (the snapshot carries an
        account's user name and name)."""
        self.staff.username = "chief"
        self.staff.save()
        self.assertReceived(1)
        self.kl.first_name = "Karla"
        self.kl.save()
        self.assertReceived(2)

    def test_a_save_of_the_fields_the_snapshot_lacks_wakes_nothing(
            self) -> None:
        """Requirement: Wake-up after a registry write (an account's save
        of fields the snapshot carries)."""
        self.control()
        self.kl.email = "kl@example.org"
        self.kl.save(update_fields=["email"])
        self.assertReceived(1)

    def test_a_notebook(self) -> None:
        """Scenario: Every write path, once each (a notebook saved)."""
        from journal.models import Notebook
        notebook = Notebook.objects.create(code="KL-1", user=self.kl)
        self.assertReceived(1)
        notebook.note = "changed"
        notebook.save()
        self.assertReceived(2)
        notebook.delete()
        self.assertReceived(3)

    def test_a_notebook_through_its_form(self) -> None:
        """Requirement: Wake-up after a registry write (a model's save,
        through a form)."""
        self.client.force_login(self.kl)
        done = self.client.post("/lab/journal/new/", {
            "code": "KL-1", "user": str(self.kl.pk), "note": ""})
        self.assertEqual(done.status_code, 302)
        self.assertReceived(1)

    def test_a_term_through_its_form(self) -> None:
        """Requirement: Wake-up after a registry write (a model's save,
        through a form)."""
        self.client.force_login(self.kl)
        done = self.client.post(term_url("projects", "new"), {
            "key": "fresh", "label": "Fresh", "label_de": "",
            "parent": ""})
        self.assertEqual(done.status_code, 302)
        self.assertReceived(1)

    def test_two_substances_by_one_bulk_update(self) -> None:
        """Scenario: Every write path, once each (two substances updated
        by one bulk update)."""
        from registry.models import Substance
        with self.silent():
            make_substance("first", "First")
            make_substance("second", "Second")
        changed = Substance.objects.filter(
            key__in=["first", "second"]).update(note="bulk")
        self.assertEqual(changed, 2)
        self.assertReceived(1)

    def test_a_bulk_creation_and_a_bulk_deletion(self) -> None:
        """Requirement: Wake-up after a registry write (a bulk update,
        creation or deletion)."""
        from vocabulary.models import Project
        Project.objects.bulk_create([Project(key="a", label="A"),
                                     Project(key="b", label="B")])
        self.assertReceived(1)
        Project.objects.filter(key__in=["a", "b"]).delete()
        self.assertReceived(2)

    def test_registry_load_once_however_many_rows(self) -> None:
        """Scenario: Every write path, once each (`registry_load` once)."""
        from registry.models import Substance
        from vocabulary.models import ChemicalClass, Group
        with self.silent():
            for model in (ChemicalClass, Group):
                model.objects.all().delete()
            Substance.objects.all().delete()
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(Path(directory), small_snapshot())
            call_command("registry_load", str(path), stdout=io.StringIO())
        self.assertEqual(Substance.objects.count(), 2)
        self.assertReceived(1)

    def test_registry_import_once(self) -> None:
        """Requirement: Wake-up after a registry write (`registry_load`
        and `registry_import`)."""
        from registry.models import Substance
        from vocabulary.models import ChemicalClass, Group
        with self.silent():
            for model in (ChemicalClass, Group):
                model.objects.all().delete()
        call_command("registry_import", str(OLD_LAYOUT),
                     stdout=io.StringIO(), stderr=io.StringIO())
        self.assertGreater(Substance.objects.count(), 0)
        self.assertReceived(1)

    def test_a_substance_made_changed_and_deleted(self) -> None:
        """Requirement: Wake-up after a registry write (a model's save
        or deletion, whatever fields it changed)."""
        from registry.models import Substance
        substance = Substance.objects.create(
            key="direct", name="Direct", group=make_group("reagents"))
        self.assertReceived(1)
        substance.note = "changed"
        substance.save()
        self.assertReceived(2)
        substance.delete()
        self.assertReceived(3)

    def test_an_article_changed_in_a_field_the_digest_lacks(self) -> None:
        """Requirement: Wake-up after a registry write (whatever fields
        it changed)."""
        with self.silent():
            article = make_article(make_substance("stocked", "Stocked"),
                                   "CH-0031")
        article.category = "solvents"
        article.save()
        self.assertReceived(1)

    def test_one_post_for_every_write_of_a_transaction(self) -> None:
        """Requirement: Wake-up after a registry write (once after each
        committed transaction, whichever rows it wrote)."""
        from journal.models import Notebook
        from registry.models import Substance
        with transaction.atomic():
            Substance.objects.create(key="one", name="One",
                                     group=make_group("reagents"))
            Notebook.objects.create(code="KL-1", user=self.kl)
            self.kl.last_name = "Lange"
            self.kl.save()
            Substance.objects.filter(key="one").update(note="x")
            Substance.objects.filter(key="one").delete()
        self.assertReceived(1)


class SavepointTests(WakeCase):
    """Scenario: A savepoint rolled back."""

    def test_a_savepoint_rolled_back_before_a_later_write(self) -> None:
        from registry.models import Substance
        group = make_group("reagents")
        with transaction.atomic():
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    Substance.objects.create(key="lost", name="Lost",
                                             group=group)
                    raise RuntimeError("roll back the savepoint")
            Substance.objects.create(key="kept", name="Kept", group=group)
        self.assertEqual(
            list(Substance.objects.values_list("key", flat=True)),
            ["kept"])
        self.assertReceived(1)

    def test_a_savepoint_rolled_back_is_the_only_write(self) -> None:
        """Requirement: Wake-up after a registry write (a write inside a
        savepoint that is rolled back counts for nothing)."""
        from registry.models import Substance
        self.control()
        group = make_group("reagents")
        with transaction.atomic():
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    Substance.objects.create(key="lost", name="Lost",
                                             group=group)
                    raise RuntimeError("roll back the savepoint")
        self.assertReceived(1)

    def test_a_write_before_the_savepoint_still_wakes(self) -> None:
        """Requirement: Wake-up after a registry write (a write outside
        the savepoint that is rolled back counts)."""
        from registry.models import Substance
        group = make_group("reagents")
        with transaction.atomic():
            Substance.objects.create(key="before", name="Before",
                                     group=group)
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    Substance.objects.create(key="lost", name="Lost",
                                             group=group)
                    raise RuntimeError("roll back the savepoint")
        self.assertReceived(1)


class RolledBackTests(WakeCase):
    """Scenario: Rolled back and other writes."""

    def test_a_transaction_rolled_back(self) -> None:
        from registry.models import Substance
        self.control()
        group = make_group("reagents")
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Substance.objects.create(key="lost", name="Lost",
                                         group=group)
                raise RuntimeError("roll back")
        self.assertFalse(Substance.objects.filter(key="lost").exists())
        self.assertReceived(1)

    def test_a_save_after_a_transaction_rolled_back_still_wakes(
            self) -> None:
        """Requirement: Wake-up after a registry write (a rolled-back
        transaction leaves nothing that holds the next one back)."""
        from registry.models import Substance
        group = make_group("reagents")
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Substance.objects.create(key="lost", name="Lost",
                                         group=group)
                raise RuntimeError("roll back")
        self.assertReceived(0)
        Substance.objects.create(key="kept", name="Kept", group=group)
        self.assertReceived(1)

    def test_a_sign_in(self) -> None:
        """Requirement: Wake-up after a registry write (a sign-in's last
        login sends none)."""
        self.control()
        self.assertTrue(self.client.login(username="kl",
                                          password=PASSWORD))
        self.assertReceived(1)

    def test_a_failing_write_through_a_form_sends_none(self) -> None:
        """Requirement: Wake-up after a registry write (a transaction
        that is rolled back): the form that refuses a substance writes
        nothing."""
        self.control()
        self.client.force_login(self.kl)
        data = substance_data(page(self.client.get(NEW_SUBSTANCE)),
                              key="Not A Key!")
        done = self.client.post(NEW_SUBSTANCE, data)
        self.assertEqual(done.status_code, 200)
        self.assertReceived(1)


class OtherWritesTests(WakeCase):
    """Scenario: Rolled back and other writes (an import, an issued ID
    and a task step write rows the digest does not cover)."""

    def setUp(self) -> None:
        super().setUp()
        with self.silent():
            from registry.models import Substance
            from vocabulary.models import ChemicalClass, Group
            for model in (ChemicalClass, Group):
                model.objects.all().delete()
            Substance.objects.all().delete()
            load_demo_registry()
            make_demo_accounts()
            make_demo_notebooks()
            substance_for("Aspirin")

    def test_an_accepted_import(self) -> None:
        self.control()
        done = post(self.client, manifest())
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "accepted", done.json())
        self.assertReceived(1)

    def test_a_refused_import(self) -> None:
        """Requirement: Wake-up after a registry write (an import
        sends none, whatever its outcome)."""
        self.control()
        done = post(self.client, refused(["x: error: y"]))
        self.assertEqual(done.json()["outcome"], "refused", done.json())
        self.assertReceived(1)

    def test_an_issued_id(self) -> None:
        with self.silent():
            import_collection()
        self.control()
        done = request_id(self.client, "procedure", make_token("kl"))
        self.assertEqual(done.status_code, 201, done.content)
        self.assertReceived(1)

    def test_a_task_step(self) -> None:
        from tasks.models import TaskStep
        self.control()
        self.client.force_login(self.kl)
        done = self.client.post(NEW_TASK, task_form_data(steps_total="3"))
        self.assertEqual(done.status_code, 302)
        self.assertEqual(TaskStep.objects.count(), 3)
        self.assertReceived(1)


class BuilderFailureTests(WakeCase):
    """Scenario: The builder does not answer."""

    def save_a_substance_through_its_form(self) -> None:
        from registry.models import Substance
        self.client.force_login(self.kl)
        data = substance_data(page(self.client.get(NEW_SUBSTANCE)))
        done = self.client.post(NEW_SUBSTANCE, data)
        self.assertEqual(done.status_code, 302)
        self.assertTrue(Substance.objects.filter(
            key="ethyl-acetate").exists())

    def assertWarned(self, logs: Any) -> None:
        """Wait for a warning of the application to be logged, and
        assert it."""
        self.assertTrue(self.wait_until(lambda: any(
            record.levelname == "WARNING" for record in logs.records)),
            "no warning was logged")

    def test_an_address_that_refuses_connections(self) -> None:
        with override_settings(ORGSYNDB_WAKE_URL=closed_url()):
            with self.assertLogs(level="WARNING") as logs:
                self.save_a_substance_through_its_form()
                self.assertWarned(logs)

    def refused_with(self, status: int) -> None:
        self.recorder.status = status
        with self.assertLogs(level="WARNING") as logs:
            self.save_a_substance_through_its_form()
            self.assertWarned(logs)
        self.assertReceived(1)

    def test_a_builder_that_refuses_the_token(self) -> None:
        """Requirement: Wake-up after a registry write (a failed or
        refused wake-up is logged as a warning)."""
        self.refused_with(401)

    def test_a_builder_that_fails(self) -> None:
        """Requirement: Wake-up after a registry write (a failed wake-up
        is logged as a warning)."""
        self.refused_with(500)

    def test_a_builder_that_does_not_answer_in_time(self) -> None:
        """Requirement: Wake-up after a registry write (a timeout of 2
        seconds)."""
        self.recorder.delay = 30
        started = time.monotonic()
        with self.assertLogs(level="WARNING") as logs:
            self.save_a_substance_through_its_form()
            self.assertWarned(logs)
        self.assertLess(time.monotonic() - started, 10)

    def test_a_malformed_address(self) -> None:
        """Requirement: Wake-up after a registry write (a failed
        wake-up is logged as a warning and leaves the write as it is):
        an address urllib cannot even build a request for."""
        from vocabulary.models import Project
        with override_settings(ORGSYNDB_WAKE_URL="builder"):
            with self.assertLogs(level="WARNING") as logs:
                Project.objects.create(key="malformed", label="Malformed")
                self.assertWarned(logs)
        self.assertTrue(Project.objects.filter(key="malformed").exists())

    def test_the_write_is_kept_when_the_wake_up_fails(self) -> None:
        """Requirement: Wake-up after a registry write (a failed
        wake-up leaves the write as it is)."""
        from vocabulary.models import Project
        with override_settings(ORGSYNDB_WAKE_URL=closed_url()):
            with self.assertLogs(level="WARNING"):
                Project.objects.create(key="kept", label="Kept")
        self.assertTrue(Project.objects.filter(key="kept").exists())


class NoSettingTests(WakeCase):
    """Scenario: No setting."""

    def test_no_request_is_sent(self) -> None:
        """With the setting empty the application connects to nothing;
        with it set, the same write makes a connection."""
        from vocabulary.models import Project
        with mock.patch("socket.socket.connect",
                        side_effect=OSError("no network")) as connect:
            with self.assertLogs(level="WARNING"):
                Project.objects.create(key="control", label="Control")
            self.assertTrue(self.wait_until(
                lambda: connect.call_count > 0), "no connection made")
            attempts = connect.call_count
            with override_settings(ORGSYNDB_WAKE_URL=""):
                Project.objects.create(key="one", label="One")
                Project.objects.bulk_create([Project(key="two",
                                                     label="Two")])
                self.kl.last_name = "Lange"
                self.kl.save()
            time.sleep(SETTLE)
            self.assertEqual(connect.call_count, attempts)
        self.assertEqual(self.received(), 0)
