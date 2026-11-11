"""Tests of ``manage.py demo_data`` (lab-demo: Demo data command)."""

from unittest import mock

from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from . import (IndexMixin, demo_index, frozen, make_group, make_substance,
               make_task, make_user)
from .collection_support import TOKEN, make_import, manifest, post
from .demo_support import (ACCOUNTS, DAY, lab_records, noon, run, seed,
                           task_counter)

EMPTY = {"accounts": 0, "substances": 0, "terms": 0, "articles": 0,
         "tasks": 0, "items": 0, "movements": 0, "notes": 0, "lots": 0,
         "consumption": 0, "parameters": 0}


def demo_marks() -> int:
    from demo.models import DemoMark
    return DemoMark.objects.count()


class FlagOffTests(IndexMixin, TestCase):

    def test_flag_off(self) -> None:
        """Scenario: Flag off."""
        for args in ((), ("--replace",)):
            with self.subTest(args=args), frozen(noon(DAY)):
                with self.assertRaises(CommandError) as caught:
                    run(*args, demo=False, index=demo_index())
                self.assertIn("ORGSYNDB_DEMO", str(caught.exception))
                self.assertEqual(lab_records(), EMPTY)
                self.assertEqual(demo_marks(), 0)


class RecordsPresentTests(IndexMixin, TestCase):

    def test_records_present(self) -> None:
        """Scenario: Records present."""
        make_user("kl", "KL")
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run(index=demo_index())
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
            run("--replace", index=demo_index())
        self.assertEqual(lab_records(), before)
        self.assertEqual(demo_marks(), 0)

    def test_a_substance_alone_is_a_lab_record(self) -> None:
        make_substance("existing")
        before = lab_records()
        self.assertEqual(before["substances"], 1)
        for args in ((), ("--replace",)):
            with self.subTest(args=args), frozen(noon(DAY)), \
                    self.assertRaises(CommandError) as caught:
                run(*args, index=demo_index())
            if not args:
                self.assertIn("--replace", str(caught.exception))
            self.assertEqual(lab_records(), before)
        self.assertEqual(demo_marks(), 0)

    def test_a_term_alone_is_a_lab_record(self) -> None:
        make_group("existing")
        before = lab_records()
        self.assertEqual(before["terms"], 1)
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run(index=demo_index())
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
                run(*args, index=demo_index())
        with frozen(noon(DAY)):
            run("--if-empty", index=demo_index())
        self.assertEqual(Task.history.count(), histories)
        self.assertEqual(demo_marks(), 0)

    def test_replace_sets_the_counter_of_an_empty_database_to_zero(
            self) -> None:
        from tasks.models import Counter, Task
        Counter.objects.create(name="task", value=42)
        with frozen(noon(DAY)):
            run("--replace", index=demo_index())
        first = Task.objects.order_by("created_at", "id").first()
        self.assertEqual(first.number, "T-001")

    def test_replace_writes_an_empty_database(self) -> None:
        with frozen(noon(DAY)):
            run("--replace", index=demo_index())
        self.assertEqual(lab_records()["accounts"], len(ACCOUNTS))
        self.assertEqual(demo_marks(), 1)


class ReplaceTests(IndexMixin, TestCase):

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
            run("--replace", index=demo_index())
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

    def test_replace_writes_the_same_counts_again(self) -> None:
        seed(DAY)
        before = lab_records()
        with frozen(noon(DAY)):
            run("--replace", index=demo_index())
        self.assertEqual(lab_records(), before)

    def test_replace_removes_the_histories(self) -> None:
        from tasks.models import Task
        seed(DAY)
        before = Task.history.count()
        with frozen(noon(DAY)):
            run("--replace", index=demo_index())
        self.assertEqual(Task.history.count(), before)


class AtStartTests(IndexMixin, TestCase):

    def test_flag_off_changes_nothing(self) -> None:
        """Scenario: At start (flag off)."""
        with frozen(noon(DAY)):
            out, _err = run("--if-empty", demo=False, index=demo_index())
        self.assertTrue(out.strip())
        self.assertEqual(lab_records(), EMPTY)
        self.assertEqual(demo_marks(), 0)

    def test_records_present_changes_nothing(self) -> None:
        """Scenario: At start (records present)."""
        make_user("kl", "KL")
        with frozen(noon(DAY)):
            out, _err = run("--if-empty", index=demo_index())
        self.assertTrue(out.strip())
        self.assertEqual(lab_records(), {**EMPTY, "accounts": 1})
        self.assertEqual(demo_marks(), 0)

    def test_empty_database_is_seeded(self) -> None:
        """Scenario: At start (empty)."""
        with frozen(noon(DAY)):
            run("--if-empty", index=demo_index())
        self.assertEqual(lab_records()["accounts"], len(ACCOUNTS))
        self.assertEqual(demo_marks(), 1)

    def test_a_demo_database_is_left_alone(self) -> None:
        seed(DAY)
        before = lab_records()
        with frozen(noon(DAY)):
            run("--if-empty", index=demo_index())
        self.assertEqual(lab_records(), before)


class OptionsTogetherTests(IndexMixin, TestCase):

    def test_options_together(self) -> None:
        """Scenario: Options together."""
        with frozen(noon(DAY)), self.assertRaises(CommandError):
            run("--replace", "--if-empty", index=demo_index())
        self.assertEqual(lab_records(), EMPTY)


class FailureTests(IndexMixin, TestCase):

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
            run(index=demo_index())
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
            run("--replace", index=demo_index())
        self.assertEqual(lab_records(), before)
        self.assertEqual(Task.history.count(), histories)
        self.assertEqual(task_counter(), counter)
        self.assertEqual(demo_marks(), 1)


class NoIndexTests(IndexMixin, TestCase):

    def test_no_index(self) -> None:
        """Scenario: No index."""
        from registry.models import Substance
        path = self.use_index(None)
        with frozen(noon(DAY)):
            out, err = run(index=path)
        self.assertEqual(err.strip(), "")
        self.assertEqual(lab_records()["accounts"], len(ACCOUNTS))
        self.assertEqual(Substance.objects.count(), 21)
        self.assertEqual(demo_marks(), 1)

    def test_the_demo_index_gives_no_warning(self) -> None:
        _out, err = seed(DAY)
        self.assertEqual(err.strip(), "")


def imported_rows() -> dict[str, int]:
    """The rows of the collection import the database holds."""
    from .collection_support import counts
    return counts()


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class ImportedRowsTests(IndexMixin, TestCase):
    """The collection's imports are lab records (lab-demo: Demo data
    command)."""

    def import_demo(self) -> int:
        """Accept the demo collection's manifest; return the import's
        id."""
        done = post(self.client, manifest())
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        return done.json()["import"]

    def test_replacing_after_an_import(self) -> None:
        """Scenario: Replacing after an import."""
        from registry import snapshot
        seed(DAY)
        self.import_demo()
        self.assertIsNotNone(snapshot.build()["import"])
        self.assertGreater(imported_rows()["Procedure"], 0)
        with frozen(noon(DAY)):
            run("--replace", index=demo_index())
        self.assertEqual({name: n for name, n in imported_rows().items()
                          if n}, {})
        self.assertIsNone(snapshot.build()["import"])
        self.assertEqual(demo_marks(), 1)

    def test_the_collection_is_imported_again_after_a_replacement(
            self) -> None:
        """Requirement: Demo data command (after the replacement the
        snapshot's `import` is `null`, so a build is accepted with no
        base)."""
        seed(DAY)
        self.import_demo()
        with frozen(noon(DAY)):
            run("--replace", index=demo_index())
        done = post(self.client, manifest())
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        from collection.models import Import
        self.assertIsNone(Import.objects.get().base)

    def test_a_database_holding_an_import_has_lab_records(self) -> None:
        """Requirement: Demo data command (the imports are lab
        records)."""
        make_import()
        with frozen(noon(DAY)), self.assertRaises(CommandError) as caught:
            run(index=demo_index())
        self.assertIn("--replace", str(caught.exception))
        with frozen(noon(DAY)):
            run("--if-empty", index=demo_index())
        self.assertEqual(lab_records(), EMPTY)
        self.assertEqual(imported_rows()["Import"], 1)
        self.assertEqual(demo_marks(), 0)

    def test_a_failed_replacement_keeps_the_imported_rows(self) -> None:
        """Scenario: Failure changes nothing (replace, with an
        import)."""
        from inventory import bookings
        from registry import snapshot
        seed(DAY)
        self.import_demo()
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
            run("--replace", index=demo_index())
        self.assertEqual(imported_rows(), before)
        self.assertEqual(snapshot.build()["import"], latest)


class SummaryTests(IndexMixin, TestCase):

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
