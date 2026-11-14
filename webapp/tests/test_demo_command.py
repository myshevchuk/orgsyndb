"""Tests of ``manage.py demo_data`` (lab-demo: Demo data command)."""

from unittest import mock

from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from . import (BERLIN, frozen, make_group, make_substance, make_task,
               make_user)
from .collection_support import (PROCEDURES, SEQUENCES, TOKEN, accept,
                                 copy_procedure, demo_collection, ids_of,
                                 import_collection, issue_ids, issued_keys,
                                 issued_to, make_import, make_token, manifest,
                                 post, request_id)
from .demo_support import (ACCOUNTS, DAY, lab_records, noon, opening, run,
                           seed, task_counter)

EMPTY = {"accounts": 0, "substances": 0, "terms": 0, "articles": 0,
         "tasks": 0, "items": 0, "movements": 0, "notes": 0, "lots": 0,
         "consumption": 0, "parameters": 0}


def demo_marks() -> int:
    from demo.models import DemoMark
    return DemoMark.objects.count()


class FlagOffTests(TestCase):

    def test_flag_off(self) -> None:
        """Scenario: Flag off."""
        for args in ((), ("--replace",)):
            with self.subTest(args=args), frozen(noon(DAY)):
                with self.assertRaises(CommandError) as caught:
                    run(*args, demo=False)
                self.assertIn("ORGSYNDB_DEMO", str(caught.exception))
                self.assertEqual(lab_records(), EMPTY)
                self.assertEqual(demo_marks(), 0)


class RecordsPresentTests(TestCase):

    def test_records_present(self) -> None:
        """Scenario: Records present."""
        make_user("kl", "KL")
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run()
        self.assertIn("--replace", str(caught.exception))
        self.assertEqual(lab_records(), {**EMPTY, "accounts": 1})
        self.assertEqual(demo_marks(), 0)

    def test_real_records_are_not_replaced(self) -> None:
        """Scenario: Real records are not replaced."""
        kl = make_user("kl", "KL")
        make_task(kl, substance="CH-0012")
        before = lab_records()
        self.assertEqual((before["accounts"], before["tasks"],
                          before["substances"]), (1, 1, 1))
        with frozen(noon(DAY)), self.assertRaises(CommandError):
            run("--replace")
        self.assertEqual(lab_records(), before)
        self.assertEqual(demo_marks(), 0)

    def test_a_substance_alone_is_a_lab_record(self) -> None:
        make_substance("existing")
        before = lab_records()
        self.assertEqual(before["substances"], 1)
        for args in ((), ("--replace",)):
            with self.subTest(args=args), frozen(noon(DAY)), \
                    self.assertRaises(CommandError) as caught:
                run(*args)
            if not args:
                self.assertIn("--replace", str(caught.exception))
            self.assertEqual(lab_records(), before)
        self.assertEqual(demo_marks(), 0)

    def test_a_term_alone_is_a_lab_record(self) -> None:
        make_group("existing")
        before = lab_records()
        self.assertEqual(before["terms"], 1)
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run()
        self.assertIn("--replace", str(caught.exception))
        self.assertEqual(lab_records(), before)
        self.assertEqual(demo_marks(), 0)

    def test_surviving_history_counts_as_records(self) -> None:
        from registry.models import Substance
        from tasks.models import Task
        from vocabulary.models import Group
        kl = make_user("kl", "KL")
        make_task(kl, substance="CH-0012").delete()
        kl.delete()
        Substance.objects.all().delete()
        Group.objects.all().delete()
        self.assertEqual(lab_records(), EMPTY)
        histories = Task.history.count()
        self.assertGreater(histories, 0)
        for args in ((), ("--replace",)):
            with self.subTest(args=args), frozen(noon(DAY)), \
                    self.assertRaises(CommandError):
                run(*args)
        with frozen(noon(DAY)):
            run("--if-empty")
        self.assertEqual(Task.history.count(), histories)
        self.assertEqual(demo_marks(), 0)

    def test_replace_sets_the_counter_of_an_empty_database_to_zero(
            self) -> None:
        from tasks.models import Counter, Task
        Counter.objects.create(name="task", value=42)
        with frozen(noon(DAY)):
            run("--replace")
        first = Task.objects.order_by("created_at", "id").first()
        self.assertEqual(first.number, "T-001")

    def test_replace_writes_an_empty_database(self) -> None:
        with frozen(noon(DAY)):
            run("--replace")
        self.assertEqual(lab_records()["accounts"], len(ACCOUNTS))
        self.assertEqual(demo_marks(), 1)


class ReplaceTests(TestCase):

    def test_replace_a_demo_database(self) -> None:
        """Scenario: Replace a demo database."""
        from django.contrib.auth import get_user_model
        from registry.models import Substance
        from tasks.models import Task
        from vocabulary.models import Group
        seed(DAY)
        kl = make_user("kl", "KL9")
        make_task(kl, substance="CH-0012", note="added after seeding")
        make_substance("stray-substance")
        make_group("stray-group")
        with frozen(noon(DAY)):
            run("--replace")
        self.assertFalse(Substance.objects.filter(
            key="stray-substance").exists())
        self.assertFalse(Group.objects.filter(key="stray-group").exists())
        self.assertEqual(Substance.objects.count(), 21)
        users = get_user_model().objects
        self.assertFalse(users.filter(username="kl").exists())
        self.assertEqual(sorted(users.values_list("username", flat=True)),
                         sorted(ACCOUNTS))
        self.assertFalse(Task.objects.filter(
            note="added after seeding").exists())
        first = Task.objects.order_by("created_at", "id").first()
        self.assertEqual(first.number, "T-001")
        self.assertEqual(demo_marks(), 1)

    def test_replace_deletes_the_notebooks_and_entries(self) -> None:
        """Requirement: Demo data command (`--replace` deletes every lab
        record, notebooks with their entries among them; only it deletes
        entries)."""
        from journal.models import Entry, Notebook
        from .journal_support import entry_of
        seed(DAY)
        kl = make_user("kl", "KL9")
        stray = Notebook.objects.create(code="ZZ-1", user=kl)
        entry_of("AE-1/40")
        entry_of("ZZ-1/1")
        self.assertEqual(Entry.objects.count(), 12)
        with frozen(noon(DAY)):
            run("--replace")
        self.assertFalse(Notebook.objects.filter(pk=stray.pk).exists())
        self.assertEqual(
            sorted(Notebook.objects.values_list("code", flat=True)),
            ["AE-1", "AE-2", "CE-1", "CE-3"])
        self.assertEqual(Entry.objects.count(), 10)
        self.assertFalse(Entry.objects.filter(number=40).exists())

    def test_replace_writes_the_same_counts_again(self) -> None:
        seed(DAY)
        before = lab_records()
        with frozen(noon(DAY)):
            run("--replace")
        self.assertEqual(lab_records(), before)

    def test_replace_removes_the_histories(self) -> None:
        from tasks.models import Task
        seed(DAY)
        before = Task.history.count()
        with frozen(noon(DAY)):
            run("--replace")
        self.assertEqual(Task.history.count(), before)


class AtStartTests(TestCase):

    def test_flag_off_changes_nothing(self) -> None:
        """Scenario: At start (flag off)."""
        with frozen(noon(DAY)):
            out, _err = run("--if-empty", demo=False)
        self.assertTrue(out.strip())
        self.assertEqual(lab_records(), EMPTY)
        self.assertEqual(demo_marks(), 0)

    def test_records_present_changes_nothing(self) -> None:
        """Scenario: At start (records present)."""
        make_user("kl", "KL")
        with frozen(noon(DAY)):
            out, _err = run("--if-empty")
        self.assertTrue(out.strip())
        self.assertEqual(lab_records(), {**EMPTY, "accounts": 1})
        self.assertEqual(demo_marks(), 0)

    def test_empty_database_is_seeded(self) -> None:
        """Scenario: At start (empty)."""
        with frozen(noon(DAY)):
            run("--if-empty")
        self.assertEqual(lab_records()["accounts"], len(ACCOUNTS))
        self.assertEqual(demo_marks(), 1)

    def test_a_demo_database_is_left_alone(self) -> None:
        seed(DAY)
        before = lab_records()
        with frozen(noon(DAY)):
            run("--if-empty")
        self.assertEqual(lab_records(), before)


class OptionsTogetherTests(TestCase):

    def test_options_together(self) -> None:
        """Scenario: Options together."""
        with frozen(noon(DAY)), self.assertRaises(CommandError):
            run("--replace", "--if-empty")
        self.assertEqual(lab_records(), EMPTY)


class FailureTests(TestCase):

    def failing_notes(self) -> mock._patch:
        """A patch that lets the first five delivery notes be booked and
        refuses the sixth."""
        from inventory import bookings
        real = bookings.book_note
        calls = {"count": 0}

        def book_note(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] > 5:
                raise bookings.Refused("refused by the test")
            return real(*args, **kwargs)

        return mock.patch("inventory.bookings.book_note",
                          side_effect=book_note)

    def test_failure_on_an_empty_database(self) -> None:
        """Scenario: Failure changes nothing (empty database)."""
        with frozen(noon(DAY)), self.failing_notes(), \
                self.assertRaises(CommandError):
            run()
        self.assertEqual(lab_records(), EMPTY)
        self.assertEqual(demo_marks(), 0)
        self.assertEqual(task_counter(), 0)

    def test_failure_under_replace(self) -> None:
        """Scenario: Failure changes nothing (replace)."""
        from tasks.models import Task
        seed(DAY)
        before = lab_records()
        histories = Task.history.count()
        counter = task_counter()
        with frozen(noon(DAY)), self.failing_notes(), \
                self.assertRaises(CommandError):
            run("--replace")
        self.assertEqual(lab_records(), before)
        self.assertEqual(Task.history.count(), histories)
        self.assertEqual(task_counter(), counter)
        self.assertEqual(demo_marks(), 1)


class StderrTests(TestCase):

    def test_the_data_set_is_written_without_a_warning(self) -> None:
        _out, err = seed(DAY)
        self.assertEqual(err.strip(), "")
        self.assertEqual(lab_records()["accounts"], len(ACCOUNTS))
        self.assertEqual(demo_marks(), 1)


def imported_rows() -> dict[str, int]:
    """The rows of the collection import the database holds."""
    from .collection_support import counts
    return counts()


def with_extra_procedure() -> dict:
    """The demo collection with a tenth procedure, which the demo
    manifest lacks."""
    data = demo_collection()
    data["procedures"].append(
        copy_procedure(data, "OSDB-0008", "OSDB-0010"))
    return data


class DataSetImportTests(TestCase):
    """The data set records an accepted import of the demo collection
    (lab-demo: Demo data command)."""

    def test_the_data_sets_import(self) -> None:
        """Scenario: The data set's import."""
        from collection.models import Import, Procedure, Sequence
        with frozen(noon(DAY)):
            out, _err = run()
        self.assertTrue(out.strip())
        (own,) = Import.objects.all()
        self.assertEqual((own.outcome, own.release, own.trigger),
                         ("accepted", "demo", "catch-up"))
        self.assertEqual(
            sorted(Procedure.objects.values_list("key", flat=True)),
            [f"OSDB-{number:04d}" for number in range(1, 10)])
        self.assertEqual(
            sorted(Sequence.objects.values_list("key", flat=True)),
            ["SEQ-0001", "SEQ-0002"])
        self.assertFalse(Procedure.objects.filter(withdrawn=True).exists())
        self.assertFalse(Sequence.objects.filter(withdrawn=True).exists())

    def test_the_import_is_the_manifest_applied(self) -> None:
        """Requirement: Demo data command (the import is recorded as the
        manifest view applies one: with the commit of forty zeros, no
        base, the current snapshot's digest, and the language of the
        demo texts)."""
        from collection.models import Import
        from registry import snapshot
        seed(DAY)
        (own,) = Import.objects.all()
        self.assertEqual(own.commit, "0" * 40)
        self.assertIsNone(own.base)
        self.assertEqual(own.snapshot, snapshot.build()["digest"])
        self.assertEqual(own.language, "de")
        self.assertEqual(snapshot.build()["import"]["id"], own.pk)
        self.assertEqual(
            {name: imported_rows()[name]
             for name in ("Procedure", "ScopeEntry", "Sequence", "Step")},
            {"Procedure": PROCEDURES, "ScopeEntry": 11,
             "Sequence": SEQUENCES, "Step": 4})

    def test_the_data_sets_import_has_no_pusher(self) -> None:
        """Scenario: The pusher (the demo data command's import has
        none)."""
        from collection.models import Import
        seed(DAY)
        (own,) = Import.objects.all()
        self.assertTrue(hasattr(own, "pushed_by"),
                        "the import has no pushed_by")
        self.assertIsNone(own.pushed_by)

    def test_the_rows_are_the_manifests(self) -> None:
        """Requirement: Demo data command (the rows `webapp/demo/
        manifest.json` describes, general procedures marked)."""
        from collection.models import Procedure
        seed(DAY)
        for body in demo_collection()["procedures"]:
            with self.subTest(id=body["id"]):
                row = Procedure.objects.get(key=body["id"])
                self.assertEqual(row.general, body["general"])
                self.assertEqual(row.title, body["title"])
                self.assertEqual(row.entries.count(), len(body["entries"]))

    def test_the_import_is_recorded_on_the_opening_day(self) -> None:
        """Requirement: Demo data command (on `O`, after the
        registry)."""
        from collection.models import Import
        from registry.models import Substance
        seed(DAY)
        (own,) = Import.objects.all()
        self.assertEqual(own.received_at.astimezone(BERLIN).date(),
                         opening(DAY))
        created = Substance.history.filter(history_type="+").order_by(
            "history_date").first().history_date
        self.assertGreaterEqual(own.received_at, created)

    def test_the_import_has_the_language_of_the_texts(self) -> None:
        """Requirement: Demo data command (the language of the demo
        texts)."""
        from collection.models import Import
        seed(DAY)
        accept(language="en")
        with frozen(noon(DAY)):
            run("--replace")
        (own,) = Import.objects.all()
        self.assertEqual(own.language, "en")


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class ImportedRowsTests(TestCase):
    """The collection's imports are lab records (lab-demo: Demo data
    command)."""

    def test_replacing_after_an_import(self) -> None:
        """Scenario: Replacing after an import."""
        from collection.models import Import, Procedure, Sequence
        from registry import snapshot
        seed(DAY)
        later = import_collection(with_extra_procedure())
        self.assertEqual(snapshot.build()["import"]["id"], later.pk)
        self.assertEqual(Procedure.objects.count(), PROCEDURES + 1)
        with frozen(noon(DAY)):
            out, _err = run("--replace")
        self.assertTrue(out.strip())
        (own,) = Import.objects.all()
        self.assertEqual(own.release, "demo")
        self.assertNotEqual(own.pk, later.pk)
        self.assertEqual(snapshot.build()["import"]["id"], own.pk)
        self.assertEqual(
            sorted(Procedure.objects.values_list("key", flat=True)),
            sorted(p["id"] for p in demo_collection()["procedures"]))
        self.assertEqual(
            sorted(Sequence.objects.values_list("key", flat=True)),
            sorted(s["id"] for s in demo_collection()["sequences"]))
        self.assertEqual(demo_marks(), 1)

    def test_the_collection_is_built_after_the_data_sets_import(
            self) -> None:
        """Requirement: Demo data command (the builder's next cycle
        builds with the data set's import as its base)."""
        from collection.models import Import
        seed(DAY)
        (own,) = Import.objects.all()
        stale = post(self.client, manifest())
        self.assertEqual(stale.status_code, 409, stale.content)
        done = post(self.client, manifest(base=own.pk))
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        self.assertEqual(Import.objects.get(pk=done.json()["import"]).base,
                         own)

    def test_a_database_holding_an_import_has_lab_records(self) -> None:
        """Requirement: Demo data command (the imports are lab
        records)."""
        make_import()
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run()
        self.assertIn("--replace", str(caught.exception))
        with frozen(noon(DAY)):
            run("--if-empty")
        self.assertEqual(lab_records(), EMPTY)
        self.assertEqual(imported_rows()["Import"], 1)
        self.assertEqual(demo_marks(), 0)

    def test_a_failed_replacement_keeps_the_imported_rows(self) -> None:
        """Scenario: Failure changes nothing (replace, with an
        import)."""
        from inventory import bookings
        from registry import snapshot
        seed(DAY)
        import_collection(with_extra_procedure())
        before = imported_rows()
        latest = snapshot.build()["import"]
        real = bookings.book_note
        calls = {"count": 0}

        def book_note(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] > 5:
                raise bookings.Refused("refused by the test")
            return real(*args, **kwargs)

        with frozen(noon(DAY)), mock.patch(
                "inventory.bookings.book_note", side_effect=book_note), \
                self.assertRaises(CommandError):
            run("--replace")
        self.assertEqual(imported_rows(), before)
        self.assertEqual(snapshot.build()["import"], latest)


def demo_ids() -> list[str]:
    """The IDs of the demo collection, in order."""
    return sorted(ids_of(demo_collection()))


def tokens() -> int:
    from accounts.models import AccessToken
    return AccessToken.objects.count()


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class IssuedIdTests(TestCase):
    """The issued IDs and access tokens are lab records (lab-demo: Demo
    data command)."""

    def test_the_data_set_adopts_its_ids(self) -> None:
        """Scenario: The data set's import (its IDs are adopted, to no
        account)."""
        seed(DAY)
        self.assertEqual(issued_keys(), demo_ids())
        self.assertEqual(
            sorted(key for key in issued_keys() if issued_to(key)), [])

    def test_replacing_deletes_issued_ids_and_tokens(self) -> None:
        """Requirement: Demo data command (`--replace` deletes every lab
        record: accounts with their access tokens, issued IDs)."""
        seed(DAY)
        import_collection(with_extra_procedure())
        issue_ids("OSDB-0012")
        done = request_id(self.client, "procedure",
                          make_token("klehmann"))
        self.assertEqual(done.status_code, 201, done.content)
        make_token("tbauer", "Server")
        self.assertEqual(tokens(), 2)
        self.assertEqual(len(issued_keys()), 11 + 1 + 1 + 1)
        with frozen(noon(DAY)):
            out, _err = run("--replace")
        self.assertTrue(out.strip())
        self.assertEqual(issued_keys(), demo_ids())
        self.assertEqual(
            sorted(key for key in issued_keys() if issued_to(key)), [])
        self.assertEqual(tokens(), 0)

    def test_the_next_id_after_replacing(self) -> None:
        """Requirement: Demo data command (`--replace` writes the data
        set again: the next ID lies above its own)."""
        seed(DAY)
        request_id(self.client, "procedure", make_token("klehmann"))
        with frozen(noon(DAY)):
            run("--replace")
        done = request_id(self.client, "procedure",
                          make_token("klehmann"))
        self.assertEqual(done.json(), {"id": "OSDB-0010"})

    def test_issued_ids_alone_are_lab_records(self) -> None:
        """Requirement: Demo data command (issued IDs are lab
        records)."""
        issue_ids("OSDB-0012")
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run()
        self.assertIn("--replace", str(caught.exception))
        with frozen(noon(DAY)), self.assertRaises(CommandError):
            run("--replace")
        with frozen(noon(DAY)):
            run("--if-empty")
        self.assertEqual(issued_keys(), ["OSDB-0012"])
        self.assertEqual(lab_records(), EMPTY)
        self.assertEqual(demo_marks(), 0)

    def test_a_failed_replacement_keeps_them(self) -> None:
        """Scenario: Failure changes nothing (replace, with issued IDs
        and tokens)."""
        from inventory import bookings
        seed(DAY)
        issue_ids("OSDB-0012")
        make_token("klehmann")
        before = (issued_keys(), tokens())
        real = bookings.book_note
        calls = {"count": 0}

        def book_note(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] > 5:
                raise bookings.Refused("refused by the test")
            return real(*args, **kwargs)

        with frozen(noon(DAY)), mock.patch(
                "inventory.bookings.book_note", side_effect=book_note), \
                self.assertRaises(CommandError):
            run("--replace")
        self.assertEqual((issued_keys(), tokens()), before)


class SummaryTests(TestCase):

    def test_success_prints_what_was_written(self) -> None:
        from inventory.models import DeliveryNote, Item
        from registry.models import Substance
        from tasks.models import Task
        out, _err = seed(DAY)
        for count in (len(ACCOUNTS), Substance.objects.count(),
                      Item.objects.count(), DeliveryNote.objects.count(),
                      Task.objects.count()):
            with self.subTest(count=count):
                self.assertRegex(out, rf"(?<!\d){count}(?!\d)")
