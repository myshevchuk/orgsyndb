"""Tests of accepting an import (collection-import: Accepting an
import)."""

from datetime import datetime
from typing import Any

from django.test import override_settings

from registry.models import Substance

from .collection_support import (PROCEDURES, SEQUENCES, TOKEN, TOOLING,
                                 ImportCase, counts, demo_collection, dump,
                                 manifest, post, refused)
from .demo_support import SeededCase


def only() -> list[Any]:
    """Every import, by receipt."""
    from collection.models import Import
    return list(Import.objects.order_by("received_at", "pk"))


class FirstImportTests(ImportCase):
    """The demo registry is loaded and no import exists: the data set
    is not written."""

    def test_first_import(self) -> None:
        """Scenario: First import."""
        from collection.models import (Import, Procedure, ScopeEntry,
                                       Sequence, Step)
        from registry import snapshot
        self.assertFalse(Import.objects.exists())
        body = manifest()
        self.assertEqual(body["snapshot"], snapshot.build()["digest"])
        done = post(self.client, body)
        self.assertEqual(done.status_code, 200, done.content)
        answer = done.json()
        self.assertEqual(answer["outcome"], "accepted")
        (record,) = Import.objects.all()
        self.assertEqual(answer["import"], record.pk)
        self.assertEqual((record.outcome, record.commit, record.release,
                          record.language),
                         ("accepted", body["commit"], body["release"],
                          "de"))
        self.assertEqual(record.errors, "")
        self.assertEqual(Procedure.objects.count(), PROCEDURES)
        self.assertEqual(Sequence.objects.count(), SEQUENCES)
        self.assertFalse(Procedure.objects.filter(withdrawn=True).exists())
        self.assertFalse(Sequence.objects.filter(withdrawn=True).exists())
        self.assertEqual(
            sorted(Procedure.objects.values_list("key", flat=True)),
            [p["id"] for p in demo_collection()["procedures"]])
        self.assertEqual(ScopeEntry.objects.count(), 11)
        self.assertEqual(Step.objects.count(), 4)


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class AfterDemoImportTests(SeededCase):

    def entries(self) -> dict[str, list[int]]:
        """The entry each step of each task names, by task number."""
        from tasks.models import Task
        return {task.number: [step.entry_id for step in
                              task.steps.order_by("position")]
                for task in Task.objects.exclude(sequence=None)}

    def test_after_the_demos_own_import(self) -> None:
        """Scenario: After the demo's own import."""
        from collection.models import Import
        from registry import snapshot
        (own,) = Import.objects.all()
        before = self.entries()
        self.assertTrue(before)
        self.assertTrue(all(ids and None not in ids
                            for ids in before.values()))
        body = manifest(base=own.pk)
        self.assertEqual(body["snapshot"], snapshot.build()["digest"])
        done = post(self.client, body)
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "accepted", done.json())
        self.assertEqual(Import.objects.get(pk=done.json()["import"]).base,
                         own)
        self.assertEqual(self.entries(), before)

    def test_the_rows_stay_the_same_rows(self) -> None:
        """Scenario: After the demo's own import (the import matches
        the demo's rows by ID and signature)."""
        from collection.models import (Import, Procedure, ScopeEntry,
                                       Sequence)
        (own,) = Import.objects.all()
        models = (Procedure, ScopeEntry, Sequence)

        def keys() -> list[list[int]]:
            return [sorted(model.objects.values_list("pk", flat=True))
                    for model in models]

        before = keys()
        done = post(self.client, manifest(base=own.pk))
        self.assertEqual(done.json()["outcome"], "accepted", done.content)
        self.assertEqual(keys(), before)
        self.assertFalse(Procedure.objects.filter(withdrawn=True).exists())


class RecordTests(ImportCase):

    def test_an_accepted_import_records_the_manifest(self) -> None:
        """Requirement: Accepting an import (an accepted import)."""
        first = self.accept()
        second_body = self.follow(trigger="registry")
        done = self.send(second_body)
        self.assertEqual(done.status_code, 200, done.content)
        second = only()[-1]
        self.assertEqual(done.json(), {"outcome": "accepted",
                                       "import": second.pk})
        self.assertEqual(first.base, None)
        self.assertEqual(second.base, first)
        self.assertEqual(
            (str(second.build), second.commit, second.snapshot,
             second.tooling, second.release, second.language,
             second.trigger, second.outcome, second.errors),
            (second_body["build"], second_body["commit"],
             second_body["snapshot"], TOOLING, second_body["release"],
             "de", "registry", "accepted", ""))
        self.assertEqual(second.committed_at, datetime.fromisoformat(
            second_body["committed_at"]))

    def test_the_language_comes_from_the_manifest(self) -> None:
        """Requirement: Accepting an import (`language`)."""
        record = self.accept(language="en")
        self.assertEqual(record.language, "en")

    def test_the_rows_hold_what_the_manifest_says(self) -> None:
        """Requirement: Imported rows (a procedure, a sequence)."""
        from collection.models import Procedure, Sequence
        record = self.accept()
        for body in demo_collection()["procedures"]:
            with self.subTest(id=body["id"]):
                row = Procedure.objects.get(key=body["id"])
                self.assertEqual((row.source, row.title,
                                  row.reaction_type.key, row.last_import),
                                 (body["source"], body["title"],
                                  body["reaction_type"], record))
                self.assertEqual(row.title_de, body["title_de"] or "")
                self.assertFalse(row.withdrawn)
        for body in demo_collection()["sequences"]:
            with self.subTest(id=body["id"]):
                row = Sequence.objects.get(key=body["id"])
                self.assertEqual((row.title, row.target.key,
                                  row.last_import),
                                 (body["title"], body["target"], record))

    def test_a_missing_german_title_is_empty(self) -> None:
        """Requirement: Imported rows (`title_de`, which may be
        empty)."""
        from collection.models import Procedure, Sequence
        data = demo_collection()
        data["procedures"][0]["title_de"] = None
        data["sequences"][0]["title_de"] = None
        self.accept(data)
        self.assertFalse(Procedure.objects.get(key="OSDB-0001").title_de)
        self.assertFalse(Sequence.objects.get(key="SEQ-0001").title_de)


class RepeatTests(ImportCase):

    def test_a_repeated_build(self) -> None:
        """Scenario: A repeated build."""
        body = self.follow()
        first = self.send(body)
        before = dump()
        again = self.send(body)
        self.assertEqual((again.status_code, again.json()),
                         (first.status_code, first.json()))
        self.assertEqual(counts()["Import"], 1)
        self.assertEqual(dump(), before)

    def test_a_repeated_build_after_later_imports(self) -> None:
        """Requirement: Accepting an import (a build already recorded
        is answered as before, whatever has come since)."""
        body = self.follow()
        first = self.send(body)
        self.accept()
        self.assertEqual(counts()["Import"], 2)
        before = dump()
        again = self.send(body)
        self.assertEqual((again.status_code, again.json()),
                         (first.status_code, first.json()))
        self.assertEqual(dump(), before)

    def test_a_repeated_failed_build(self) -> None:
        """Requirement: Accepting an import (a repeated refusal is
        answered as before)."""
        body = refused(["OSDB-0002.md:title: error: missing"])
        first = self.send(body)
        self.assertEqual(first.json()["outcome"], "refused")
        again = self.send(body)
        self.assertEqual((again.status_code, again.json()),
                         (first.status_code, first.json()))
        self.assertEqual(counts()["Import"], 1)

    def test_a_repeat_is_answered_before_staleness_is_judged(self) -> None:
        """Requirement: Accepting an import (a repeated build is
        answered as before, though the registry has changed since)."""
        body = self.follow()
        first = self.send(body)
        note = Substance.objects.get(key="cinnamic-acid")
        note.note = "changed after the import"
        note.save()
        again = self.send(body)
        self.assertEqual((again.status_code, again.json()),
                         (first.status_code, first.json()))
        self.assertEqual(counts()["Import"], 1)

    def test_a_new_build_of_the_same_commit_is_a_new_import(self) -> None:
        """Requirement: Accepting an import (a build is a manifest's
        `build`, not its commit)."""
        first = self.accept()
        again = self.follow(commit=first.commit)
        done = self.send(again)
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(counts()["Import"], 2)


class StaleBaseTests(ImportCase):

    def stale(self, body: dict[str, Any]) -> None:
        done = self.send(body)
        self.assertEqual(done.status_code, 409, done.content)
        self.assertEqual(done.json(), {"outcome": "stale"})

    def test_stale_base(self) -> None:
        """Scenario: Stale base."""
        self.accept()
        before = dump()
        self.stale(manifest(base=None))
        self.assertEqual(counts()["Import"], 1)
        self.assertEqual(dump(), before)

    def test_a_base_when_none_was_accepted(self) -> None:
        """Requirement: Accepting an import (a manifest that names an
        import when none was accepted is stale)."""
        for base in (1, 999):
            with self.subTest(base=base):
                self.stale(manifest(base=base))
        self.assertEqual(sum(counts().values()), 0)

    def test_a_base_that_is_not_the_latest(self) -> None:
        """Requirement: Accepting an import (a base that is not the
        latest accepted import's id is stale)."""
        first = self.accept()
        second = self.accept()
        self.stale(self.follow(base=first.pk))
        self.stale(self.follow(base=second.pk + 1))
        self.assertEqual(counts()["Import"], 2)
        third = self.accept()
        self.assertEqual(third.base, second)

    def test_a_refusal_is_no_base(self) -> None:
        """Requirement: Accepting an import (the latest accepted import
        is the accepted import received last)."""
        first = self.accept()
        report = self.send(refused(["x: error: y"], base=first.pk))
        self.assertEqual(report.json()["outcome"], "refused")
        refusal = report.json()["import"]
        self.stale(self.follow(base=refusal))
        done = self.send(self.follow(base=first.pk))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(self.latest().base, first)

    def test_the_latest_import_is_the_one_received_last(self) -> None:
        """Requirement: Accepting an import (the accepted import
        received last)."""
        first = self.accept()
        second = self.accept()
        self.assertEqual(self.latest(), second)
        self.assertEqual(self.accept().base, second)
        self.assertNotEqual(first, second)


class StaleRegistryTests(ImportCase):

    def test_stale_registry(self) -> None:
        """Scenario: Stale registry."""
        body = manifest()
        found = Substance.objects.get(key="cinnamic-acid")
        found.note = "changed after the build"
        found.save()
        done = self.send(body)
        self.assertEqual(done.status_code, 409, done.content)
        self.assertEqual(done.json(), {"outcome": "stale"})
        self.assertEqual(sum(counts().values()), 0)

    def test_a_manifest_of_the_new_registry_is_taken(self) -> None:
        """Requirement: Accepting an import (`snapshot` is the digest
        of the current snapshot)."""
        found = Substance.objects.get(key="cinnamic-acid")
        found.note = "changed before the build"
        found.save()
        self.accept()
        self.assertEqual(counts()["Import"], 1)

    def test_a_change_of_a_term_makes_a_manifest_stale(self) -> None:
        """Requirement: Accepting an import (`snapshot` is the digest
        of the current snapshot)."""
        from vocabulary.models import ReactionType
        body = manifest()
        term = ReactionType.objects.get(key="reduction")
        term.label = "Reduction, changed"
        term.save()
        done = self.send(body)
        self.assertEqual(done.status_code, 409, done.content)

    def test_a_stale_manifest_may_be_sent_again(self) -> None:
        """Requirement: Accepting an import (a stale manifest is
        recorded nowhere, so sending it again is judged again)."""
        body = manifest()
        found = Substance.objects.get(key="cinnamic-acid")
        original = found.note
        found.note = "changed"
        found.save()
        self.assertEqual(self.send(body).status_code, 409)
        found.note = original
        found.save()
        done = self.send(body)
        self.assertEqual(done.status_code, 200, done.content)


class FailedBuildTests(ImportCase):

    def test_a_failed_build(self) -> None:
        """Scenario: A failed build."""
        first = self.accept()
        before = dump()
        errors = ["OSDB-0002.md:title: error: missing", "build failed"]
        done = self.send(refused(errors, base=first.pk))
        self.assertEqual(done.status_code, 200, done.content)
        answer = done.json()
        self.assertEqual(answer["outcome"], "refused")
        record = only()[-1]
        self.assertEqual(answer["import"], record.pk)
        self.assertEqual(record.outcome, "refused")
        self.assertEqual(record.errors, "\n".join(errors))
        self.assertEqual(record.errors.splitlines(), errors)
        self.assertEqual((record.release, record.language), ("", ""))
        self.assertEqual(self.latest(), first)
        after = dump()
        self.assertEqual(after["Procedure"], before["Procedure"])
        self.assertEqual(after["ScopeEntry"], before["ScopeEntry"])
        self.assertEqual(after["Sequence"], before["Sequence"])
        self.assertEqual(after["Step"], before["Step"])

    def test_a_failed_build_is_recorded_whatever_it_was_built_after(
            self) -> None:
        """Requirement: Accepting an import (a refused build is
        recorded at once: staleness does not matter)."""
        first = self.accept()
        for body in (refused(["a: error: b"], base=None),
                     refused(["c: error: d"], base=12345),
                     refused(["e: error: f"], snapshot="0" * 64)):
            with self.subTest(base=body["base"],
                              snapshot=body["snapshot"][:4]):
                done = self.send(body)
                self.assertEqual(done.status_code, 200, done.content)
                self.assertEqual(done.json()["outcome"], "refused")
        self.assertEqual(counts()["Import"], 4)
        self.assertEqual(self.latest(), first)

    def test_a_failed_first_build(self) -> None:
        """Requirement: Accepting an import (a refusal writes no
        rows)."""
        done = self.send(refused(["build failed"]))
        self.assertEqual(done.json()["outcome"], "refused")
        self.assertEqual({name: n for name, n in counts().items() if n},
                         {"Import": 1})
        self.assertIsNone(self.latest())
        self.assertEqual(only()[0].errors, "build failed")
