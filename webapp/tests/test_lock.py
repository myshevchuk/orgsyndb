"""Tests of the one lock (collection-import: One lock).

The tests of the writes run as ``TransactionTestCase``, with autocommit
on, so that a write that takes the lock outside the transaction that
writes is seen: ``TestCase`` wraps every test in a transaction.
"""

import contextlib
import io
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest import mock

from django.core.management import call_command
from django.db import connection, transaction
from django.db.models.signals import post_save
from django.test import TestCase, TransactionTestCase, override_settings

from . import (load_demo_registry, make_article, make_class,
               make_demo_accounts, make_group, make_substance, make_user,
               page)
from .collection_support import TOKEN, manifest, post, refused
from .registry_support import (NEW_SUBSTANCE, OLD_LAYOUT, small_snapshot,
                               term_url, write_json)
from .test_registry_forms import substance_data

HOLD = "orgsyndb_web.lock.hold"
ADMIN = "/lab/admin/"


class HoldTests(TestCase):

    def test_inside_a_transaction_it_returns(self) -> None:
        """Requirement: One lock (it takes the lock inside the current
        transaction)."""
        from orgsyndb_web import lock
        self.assertTrue(connection.in_atomic_block)
        self.assertIsNone(lock.hold())
        self.assertIsNone(lock.hold())

    def test_sqlite_does_nothing(self) -> None:
        """Requirement: One lock (on SQLite it does nothing)."""
        from orgsyndb_web import lock
        with mock.patch.object(connection, "vendor", "sqlite"), \
                mock.patch.object(connection, "cursor") as cursor:
            lock.hold()
        self.assertFalse(cursor.called)

    def test_postgresql_takes_an_advisory_lock(self) -> None:
        """Requirement: One lock (on PostgreSQL by `SELECT
        pg_advisory_xact_lock(<key>)` with a fixed key)."""
        from orgsyndb_web import lock
        statements = []
        with mock.patch.object(connection, "vendor", "postgresql"), \
                mock.patch.object(connection, "cursor") as cursor:
            lock.hold()
            lock.hold()
        for opened in (cursor.return_value,
                       cursor.return_value.__enter__.return_value):
            statements += opened.execute.call_args_list
        self.assertEqual(len(statements), 2, cursor.mock_calls)
        keys = set()
        for call in statements:
            sql = call.args[0]
            self.assertRegex(sql.lower(),
                             r"^\s*select\s+pg_advisory_xact_lock\(")
            params = call.args[1] if len(call.args) > 1 else None
            keys.add(tuple(params) if params else sql.split("(")[1])
        self.assertEqual(len(keys), 1, keys)


class OutsideTransactionTests(TransactionTestCase):

    def test_outside_a_transaction(self) -> None:
        """Scenario: Outside a transaction."""
        from orgsyndb_web import lock
        self.assertFalse(connection.in_atomic_block)
        with self.assertRaises(Exception):
            lock.hold()

    def test_inside_one_it_does_not_raise(self) -> None:
        """Requirement: One lock (inside the current transaction)."""
        from orgsyndb_web import lock
        with transaction.atomic():
            lock.hold()


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class LockCase(TransactionTestCase):
    """A test case with autocommit on, whose database holds two
    accounts."""

    def setUp(self) -> None:
        self.kl = make_user("kl", "KL", "Klara", "Lehmann")
        self.staff = make_user("boss", "BO", is_staff=True,
                               is_superuser=True)

    def small_registry(self) -> None:
        """Add the group ``reagents`` and the class ``ketones``."""
        make_group("reagents", "Reagents")
        make_class("ketones", "Ketones")

    def admin_data(self, **over: Any) -> dict[str, str]:
        """The admin's form for a new substance, with one class."""
        from vocabulary.models import ChemicalClass, Group
        data = {
            "key": "admin-made", "name": "Admin made", "name_de": "",
            "short_name": "", "group": str(Group.objects.get(
                key="reagents").pk), "formula": "", "mw": "",
            "smiles": "", "cas": "", "note": "",
            "classes-TOTAL_FORMS": "1", "classes-INITIAL_FORMS": "0",
            "classes-MIN_NUM_FORMS": "0", "classes-MAX_NUM_FORMS": "1000",
            "classes-0-id": "", "classes-0-substance": "",
            "classes-0-chemical_class": str(ChemicalClass.objects.get(
                key="ketones").pk)}
        data.update(over)
        return data

    @contextlib.contextmanager
    def recording(self, observe: Any = lambda: None):
        """Replace ``orgsyndb_web.lock.hold`` by a recorder; yield its
        calls, each with whether the connection was in a transaction and
        what ``observe`` saw."""
        calls: list[tuple[bool, Any]] = []

        def hold() -> None:
            calls.append((connection.in_atomic_block, observe()))

        with mock.patch(HOLD, side_effect=hold):
            yield calls

    def assertLocked(self, calls: list[tuple[bool, Any]],
                     before: Any = None) -> None:
        """Assert that the lock was taken, in a transaction, and that
        the first time ``before`` was seen."""
        self.assertTrue(calls, "the lock was not taken")
        self.assertTrue(all(inside for inside, _ in calls), calls)
        if before is not None:
            self.assertEqual(calls[0][1], before)


class RegistryWritesTests(LockCase):
    """Scenario: Registry writes take the lock."""

    def setUp(self) -> None:
        super().setUp()
        self.small_registry()

    def test_a_substance_through_its_form(self) -> None:
        self.client.force_login(self.kl)
        data = substance_data(page(self.client.get(NEW_SUBSTANCE)))
        from registry.models import Substance
        with self.recording(lambda: Substance.objects.filter(
                key="ethyl-acetate").exists()) as calls:
            done = self.client.post(NEW_SUBSTANCE, data)
        self.assertEqual(done.status_code, 302)
        self.assertTrue(Substance.objects.filter(
            key="ethyl-acetate").exists())
        self.assertLocked(calls, before=False)

    def test_a_project_through_its_form(self) -> None:
        from vocabulary.models import Project
        self.client.force_login(self.kl)
        with self.recording(lambda: Project.objects.filter(
                key="fresh").exists()) as calls:
            done = self.client.post(term_url("projects", "new"), {
                "key": "fresh", "label": "Fresh", "label_de": "",
                "parent": ""})
        self.assertEqual(done.status_code, 302)
        self.assertTrue(Project.objects.filter(key="fresh").exists())
        self.assertLocked(calls, before=False)

    def test_a_substance_through_the_admin(self) -> None:
        from registry.models import Substance
        self.client.force_login(self.staff)
        with self.recording(lambda: Substance.objects.filter(
                key="admin-made").exists()) as calls:
            done = self.client.post(f"{ADMIN}registry/substance/add/",
                                    self.admin_data())
        self.assertEqual(done.status_code, 302)
        self.assertTrue(Substance.objects.filter(
            key="admin-made").exists())
        self.assertLocked(calls, before=False)

    def test_a_substance_deleted_through_the_admin(self) -> None:
        substance = make_substance("spare", "Spare")
        self.client.force_login(self.staff)
        from registry.models import Substance
        with self.recording(lambda: Substance.objects.filter(
                key="spare").exists()) as calls:
            done = self.client.post(
                f"{ADMIN}registry/substance/{substance.pk}/delete/",
                {"post": "yes"})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(Substance.objects.filter(key="spare").exists())
        self.assertLocked(calls, before=True)

    def test_projects_deleted_together_in_the_admin(self) -> None:
        """Requirement: One lock (the admin's deletion of selected rows
        takes it too)."""
        from vocabulary.models import Project
        spare = Project.objects.create(key="spare", label="Spare")
        self.client.force_login(self.staff)
        with self.recording(lambda: Project.objects.filter(
                key="spare").exists()) as calls:
            done = self.client.post(f"{ADMIN}vocabulary/project/", {
                "action": "delete_selected",
                "_selected_action": [str(spare.pk)], "post": "yes"})
        self.assertEqual(done.status_code, 302)
        self.assertFalse(Project.objects.filter(key="spare").exists())
        self.assertLocked(calls, before=True)

    def test_an_article_number_through_the_booking(self) -> None:
        from inventory.bookings import assign_article_number
        from inventory.models import Article
        article = make_article(make_substance("numberless", "No number"))
        with self.recording() as calls:
            assign_article_number(self.kl, article, "CH-0021")
        self.assertEqual(
            Article.objects.get(pk=article.pk).article_number, "CH-0021")
        self.assertLocked(calls)

    def test_an_article_made_by_a_booking(self) -> None:
        from inventory.bookings import create_item
        from inventory.models import Article
        substance = make_substance("fresh-stock", "Fresh stock")
        with self.recording(lambda: Article.objects.filter(
                substance=substance).exists()) as calls:
            create_item(self.kl, substance=substance,
                        article_number="CH-0022", size=Decimal("10"),
                        unit="mg", quantity=1)
        self.assertTrue(Article.objects.filter(
            article_number="CH-0022").exists())
        self.assertLocked(calls, before=False)

    def test_registry_load(self) -> None:
        from registry.models import Substance
        from vocabulary.models import (ChemicalClass, Group, Project,
                                       ReactionType)
        for model in (ChemicalClass, Group):
            model.objects.all().delete()
        Substance.objects.all().delete()
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(Path(directory), small_snapshot())
            with self.recording(lambda: (
                    Substance.objects.count(), sum(
                        model.objects.count() for model in (
                            ChemicalClass, Group, Project,
                            ReactionType)))) as calls:
                call_command("registry_load", str(path),
                             stdout=io.StringIO())
        self.assertEqual(Substance.objects.count(), 2)
        self.assertLocked(calls, before=(0, 0))

    def test_registry_import(self) -> None:
        from registry.models import Substance
        from vocabulary.models import (ChemicalClass, Group, Project,
                                       ReactionType)
        for model in (ChemicalClass, Group):
            model.objects.all().delete()
        with self.recording(lambda: (
                Substance.objects.count(), sum(
                    model.objects.count() for model in (
                        ChemicalClass, Group, Project, ReactionType)))
        ) as calls:
            call_command("registry_import", str(OLD_LAYOUT),
                         stdout=io.StringIO(), stderr=io.StringIO())
        self.assertGreater(Substance.objects.count(), 0)
        self.assertLocked(calls, before=(0, 0))


class ModelWritesTests(LockCase):
    """Requirement: One lock (every save or deletion of a substance, of
    a term of the four vocabularies and of an article takes the lock in
    the transaction that writes, whatever path writes it)."""

    def test_a_substance(self) -> None:
        from registry.models import Substance
        group = make_group("reagents")
        with self.recording() as calls:
            substance = Substance.objects.create(
                key="direct", name="Direct", group=group)
        self.assertLocked(calls)
        with self.recording() as calls:
            substance.note = "changed"
            substance.save()
        self.assertLocked(calls)
        with self.recording() as calls:
            substance.delete()
        self.assertLocked(calls)
        self.assertFalse(Substance.objects.filter(key="direct").exists())

    def test_a_term_of_each_vocabulary(self) -> None:
        from vocabulary.models import (ChemicalClass, Group, Project,
                                       ReactionType)
        for model in (ChemicalClass, Group, Project, ReactionType):
            with self.subTest(model=model.__name__):
                with self.recording() as calls:
                    term = model.objects.create(key="direct",
                                                label="Direct")
                self.assertLocked(calls)
                with self.recording() as calls:
                    term.label = "Changed"
                    term.save()
                self.assertLocked(calls)
                with self.recording() as calls:
                    term.delete()
                self.assertLocked(calls)
                self.assertFalse(model.objects.filter(
                    key="direct").exists())

    def test_an_article(self) -> None:
        from inventory.models import Article
        substance = make_substance("stocked", "Stocked")
        with self.recording() as calls:
            article = Article.objects.create(substance=substance,
                                             article_number="CH-0031")
        self.assertLocked(calls)
        with self.recording() as calls:
            article.category = "solvents"
            article.save()
        self.assertLocked(calls)
        with self.recording() as calls:
            article.delete()
        self.assertLocked(calls)
        self.assertFalse(Article.objects.filter(
            article_number="CH-0031").exists())


class ClassesTests(LockCase):
    """Requirement: One lock (a substance's chemical classes are set in
    the transaction that saves it)."""

    def setUp(self) -> None:
        super().setUp()
        self.small_registry()

    def watch(self) -> list[str]:
        """Record, in the returned list, the lock, the saving of a class
        row and the commits that follow each."""
        from registry.models import SubstanceClass
        events: list[str] = []

        def hold() -> None:
            events.append("lock")
            transaction.on_commit(lambda: events.append("commit-of-lock"))

        def saved(**kwargs: Any) -> None:
            events.append("class")
            transaction.on_commit(lambda: events.append("commit-of-class"))

        post_save.connect(saved, sender=SubstanceClass, weak=False)
        self.addCleanup(post_save.disconnect, saved, sender=SubstanceClass)
        patch = mock.patch(HOLD, side_effect=hold)
        patch.start()
        self.addCleanup(patch.stop)
        return events

    def assertSameTransaction(self, events: list[str]) -> None:
        """Assert that the lock was taken, a class saved, and that no
        transaction ended before the last class was saved."""
        self.assertIn("lock", events)
        self.assertIn("class", events)
        self.assertLess(events.index("lock"), events.index("class"))
        last = max(i for i, event in enumerate(events)
                   if event == "class")
        for index, event in enumerate(events):
            if event.startswith("commit-of"):
                self.assertGreater(index, last, events)

    def test_through_the_form(self) -> None:
        self.client.force_login(self.kl)
        data = substance_data(page(self.client.get(NEW_SUBSTANCE)))
        events = self.watch()
        done = self.client.post(NEW_SUBSTANCE, data)
        self.assertEqual(done.status_code, 302)
        self.assertSameTransaction(events)

    def test_through_the_admin(self) -> None:
        self.client.force_login(self.staff)
        events = self.watch()
        done = self.client.post(f"{ADMIN}registry/substance/add/",
                                self.admin_data())
        self.assertEqual(done.status_code, 302)
        self.assertSameTransaction(events)


class ManifestTests(LockCase):
    """Requirement: One lock (the manifest view takes it)."""

    def setUp(self) -> None:
        super().setUp()
        load_demo_registry()
        make_demo_accounts()

    def test_an_accepted_manifest(self) -> None:
        from collection.models import Import
        with self.recording(lambda: Import.objects.count()) as calls:
            done = post(self.client, manifest())
        self.assertEqual(done.status_code, 200, done.content)
        self.assertLocked(calls, before=0)
        self.assertEqual(Import.objects.count(), 1)

    def test_a_failed_build(self) -> None:
        from collection.models import Import
        with self.recording(lambda: Import.objects.count()) as calls:
            done = post(self.client, refused(["x: error: y"]))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertLocked(calls, before=0)

    def test_a_stale_manifest(self) -> None:
        with self.recording() as calls:
            done = post(self.client, manifest(base=999))
        self.assertEqual(done.status_code, 409, done.content)
        self.assertLocked(calls)


class AccountWritesTests(LockCase):
    """Scenario: Account writes take the lock."""

    def test_a_rename_takes_the_lock(self) -> None:
        self.kl.last_name = "Lange"
        with self.recording() as calls:
            self.kl.save()
        self.assertLocked(calls)

    def test_a_sign_in_takes_no_lock(self) -> None:
        self.kl.set_password("demo")
        self.kl.save()
        with self.recording() as calls:
            self.assertTrue(self.client.login(username="kl",
                                              password="demo"))
        self.assertEqual(calls, [])

    def test_a_bulk_rename_takes_the_lock(self) -> None:
        from accounts.models import User
        with self.recording() as calls:
            User.objects.filter(pk=self.kl.pk).update(last_name="Lange")
        self.assertLocked(calls)
