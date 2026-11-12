"""Tests of applying an accepted import (collection-import: Applying an
import)."""

import copy
from typing import Any

from django.test import SimpleTestCase

from .collection_support import (ImportCase, by_id, counts, demo_collection,
                                 dump, entries_of, steps_of, substances_of)

SPECIFIC = "acetic-anhydride + salicylic-acid >> acetylsalicylic-acid"
GENERAL = ["4-acetylbiphenyl >> 1-biphenyl-4-yl-ethanol",
           "acetophenone >> 1-phenylethanol",
           "4-bromoacetophenone >> 1-4-bromophenyl-ethanol"]


def procedure_of(data: dict[str, Any], ident: str) -> dict[str, Any]:
    return by_id(data["procedures"], ident)


def sequence_of(data: dict[str, Any], ident: str) -> dict[str, Any]:
    return by_id(data["sequences"], ident)


def without(data: dict[str, Any], *idents: str) -> dict[str, Any]:
    """``data`` without the procedures and sequences ``idents``."""
    data["procedures"] = [p for p in data["procedures"]
                          if p["id"] not in idents]
    data["sequences"] = [s for s in data["sequences"]
                         if s["id"] not in idents]
    return data


def signatures(key: str) -> list[tuple[int, str, bool]]:
    """The position, signature and withdrawal of each entry of the
    procedure ``key``, by position."""
    return [(e.position, e.signature, e.withdrawn)
            for e in entries_of(key)]


def contents() -> dict[str, Any]:
    """What the rows say, leaving out the keys of the substance rows and
    of the steps, which an import may write again."""
    from collection.models import EntrySubstance, Step
    rows = dump()
    return {
        "Procedure": rows["Procedure"], "ScopeEntry": rows["ScopeEntry"],
        "Sequence": rows["Sequence"],
        "EntrySubstance": [
            (row.entry_id, row.substance.key, row.role, row.position,
             row.yield_percent)
            for row in EntrySubstance.objects.order_by(
                "entry_id", "role", "position")],
        "Step": [(step.sequence_id, step.position, step.entry_id)
                 for step in Step.objects.order_by("sequence_id",
                                                   "position")]}


class SignatureTests(SimpleTestCase):

    def signature(self, substrates: list[str], products: list[str]) -> str:
        from collection.importing import signature
        return signature(substrates, products)

    def test_the_example_of_the_specification(self) -> None:
        """Requirement: Applying an import (the signature)."""
        self.assertEqual(
            self.signature(["phenylboronic-acid", "4-bromoanisole"],
                           ["4-methoxybiphenyl"]),
            "4-bromoanisole + phenylboronic-acid >> 4-methoxybiphenyl")

    def test_the_keys_are_sorted_on_each_side(self) -> None:
        """Requirement: Applying an import (the keys of its substrates
        sorted and joined by ` + `, then ` >> `, then those of its
        products)."""
        self.assertEqual(self.signature(["b", "a"], ["d", "c"]),
                         "a + b >> c + d")
        self.assertEqual(self.signature(["a-b", "a", "a-a"], ["z"]),
                         "a + a-a + a-b >> z")
        self.assertEqual(self.signature(["x"], ["c", "b", "a"]),
                         "x >> a + b + c")

    def test_the_order_given_makes_no_difference(self) -> None:
        """Requirement: Applying an import (a signature is the
        chemistry, not the file's order)."""
        self.assertEqual(self.signature(["a", "b"], ["c"]),
                         self.signature(["b", "a"], ["c"]))

    def test_the_arguments_are_left_as_they_are(self) -> None:
        """Requirement: Applying an import (the signature)."""
        substrates, products = ["b", "a"], ["d", "c"]
        self.signature(substrates, products)
        self.assertEqual((substrates, products), (["b", "a"], ["d", "c"]))


class FirstImportRowsTests(ImportCase):

    def test_the_entries_of_a_specific_procedure(self) -> None:
        """Requirement: Imported rows (a scope entry, its substances)."""
        record = self.accept()
        self.assertEqual(signatures("OSDB-0002"),
                         [(1, SPECIFIC, False)])
        (entry,) = entries_of("OSDB-0002")
        self.assertEqual(substances_of(entry, "substrate"),
                         [("salicylic-acid", None),
                          ("acetic-anhydride", None)])
        self.assertEqual(substances_of(entry, "product"),
                         [("acetylsalicylic-acid", 75)])
        self.assertEqual(entry.procedure.last_import, record)

    def test_the_entries_of_a_general_procedure(self) -> None:
        """Requirement: Applying an import (an entry of the manifest
        takes its position in the file)."""
        self.accept()
        self.assertEqual(signatures("OSDB-0009"),
                         [(1, GENERAL[0], False), (2, GENERAL[1], False),
                          (3, GENERAL[2], False)])
        first = entries_of("OSDB-0009")[0]
        self.assertEqual(substances_of(first, "product"),
                         [("1-biphenyl-4-yl-ethanol", 90)])

    def test_a_procedure_keeps_whether_it_is_general(self) -> None:
        """Requirement: Applying an import (a procedure takes the
        manifest's values, `general` among them)."""
        from collection.models import Procedure
        self.accept()
        for body in demo_collection()["procedures"]:
            with self.subTest(id=body["id"]):
                self.assertIs(
                    Procedure.objects.get(key=body["id"]).general,
                    body["general"])
        self.assertEqual(
            list(Procedure.objects.filter(general=True).values_list(
                "key", flat=True)), ["OSDB-0009"])

    def test_a_change_of_general_is_a_change_of_the_procedure(self) -> None:
        """Requirement: Applying an import (`general` changes with the
        manifest, and the procedure's `last_import` with it)."""
        from collection.models import Procedure
        first = self.accept()
        data = demo_collection()
        procedure_of(data, "OSDB-0006")["general"] = True
        second = self.accept(data)
        row = Procedure.objects.get(key="OSDB-0006")
        self.assertTrue(row.general)
        self.assertEqual(row.last_import, second)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0005").last_import, first)
        third = self.accept(demo_collection())
        row.refresh_from_db()
        self.assertFalse(row.general)
        self.assertEqual(row.last_import, third)

    def test_the_stored_signature_is_the_helpers(self) -> None:
        """Requirement: Applying an import (a scope entry is matched by
        its signature)."""
        from collection.importing import signature
        self.accept()
        for body in demo_collection()["procedures"]:
            keys = [signature(e["substrates"],
                              [p["compound"] for p in e["products"]])
                    for e in body["entries"]]
            with self.subTest(id=body["id"]):
                self.assertEqual(
                    [e.signature for e in entries_of(body["id"])], keys)

    def test_the_steps_name_the_entries_they_resolve_to(self) -> None:
        """Requirement: Applying an import (each step names the entry it
        resolves to: for a general procedure the entry its number
        counts from 1, for a specific one its only entry)."""
        self.accept()
        self.assertEqual(steps_of("SEQ-0001"),
                         [("OSDB-0001", 1), ("OSDB-0002", 1)])
        self.assertEqual(steps_of("SEQ-0002"),
                         [("OSDB-0004", 1), ("OSDB-0009", 1)])
        from collection.models import Step
        step = Step.objects.get(sequence__key="SEQ-0002", position=2)
        self.assertEqual(step.entry.signature, GENERAL[0])

    def test_a_missing_yield_is_none(self) -> None:
        """Requirement: Imported rows (`yield_percent`, which may be
        none)."""
        data = demo_collection()
        product = procedure_of(data, "OSDB-0002")["entries"][0][
            "products"][0]
        product["yield_percent"] = None
        self.accept(data)
        (entry,) = entries_of("OSDB-0002")
        self.assertEqual(substances_of(entry, "product"),
                         [("acetylsalicylic-acid", None)])


class ChangedValuesTests(ImportCase):

    def test_yields_change_the_entry_stays(self) -> None:
        """Scenario: Yields change, the entry stays."""
        from collection.models import Procedure
        first = self.accept()
        (entry,) = entries_of("OSDB-0002")
        before = entries_of("OSDB-0009")[0]
        data = demo_collection()
        procedure_of(data, "OSDB-0009")["entries"][0]["products"][0][
            "yield_percent"] = 92
        second = self.accept(data)
        self.assertEqual(second.base, first)
        after = entries_of("OSDB-0009")[0]
        self.assertEqual(after.pk, before.pk)
        self.assertEqual(substances_of(after, "product"),
                         [("1-biphenyl-4-yl-ethanol", 92)])
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0009").last_import, second)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0002").last_import, first)
        self.assertEqual(entries_of("OSDB-0002")[0].pk, entry.pk)
        self.assertEqual(counts()["Procedure"], 9)

    def test_an_unchanged_collection_changes_no_row(self) -> None:
        """Requirement: Applying an import (a row keeps the import it
        had unless something changes)."""
        from collection.models import Procedure, Sequence
        first = self.accept()
        before = contents()
        second = self.accept()
        self.assertEqual(second.base, first)
        self.assertEqual(contents(), before)
        for model in (Procedure, Sequence):
            self.assertEqual(
                set(model.objects.values_list("last_import", flat=True)),
                {first.pk})

    def test_a_new_position_keeps_the_entry(self) -> None:
        """Requirement: Applying an import (an entry takes its position
        in the file and is the same row)."""
        from collection.models import Procedure
        first = self.accept()
        before = {e.signature: e.pk for e in entries_of("OSDB-0009")}
        data = demo_collection()
        entries = procedure_of(data, "OSDB-0009")["entries"]
        entries[1], entries[2] = entries[2], entries[1]
        second = self.accept(data)
        self.assertEqual(signatures("OSDB-0009"), [
            (1, GENERAL[0], False), (2, GENERAL[2], False),
            (3, GENERAL[1], False)])
        self.assertEqual({e.signature: e.pk
                          for e in entries_of("OSDB-0009")}, before)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0009").last_import, second)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0002").last_import, first)

    def test_the_order_of_substances_follows_the_file(self) -> None:
        """Requirement: Applying an import (an entry takes its
        substances' order)."""
        from collection.models import Procedure
        first = self.accept()
        (before,) = entries_of("OSDB-0002")
        data = demo_collection()
        procedure_of(data, "OSDB-0002")["entries"][0]["substrates"].reverse()
        second = self.accept(data)
        (after,) = entries_of("OSDB-0002")
        self.assertEqual(after.pk, before.pk)
        self.assertEqual(after.signature, SPECIFIC)
        self.assertEqual(substances_of(after, "substrate"),
                         [("acetic-anhydride", None),
                          ("salicylic-acid", None)])
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0002").last_import, second)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0003").last_import, first)

    def test_new_values_of_a_procedure(self) -> None:
        """Requirement: Applying an import (a procedure takes the
        manifest's values)."""
        from collection.models import Procedure
        first = self.accept()
        data = demo_collection()
        changed = procedure_of(data, "OSDB-0001")
        changed.update(title="Salicylsäure neu", title_de=None,
                       source="md", reaction_type="reduction")
        second = self.accept(data)
        row = Procedure.objects.get(key="OSDB-0001")
        self.assertEqual((row.title, row.source, row.reaction_type.key,
                          row.last_import),
                         ("Salicylsäure neu", "md", "reduction", second))
        self.assertFalse(row.title_de)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0004").last_import, first)

    def test_new_values_of_a_sequence(self) -> None:
        """Requirement: Applying an import (a sequence takes the
        manifest's values)."""
        from collection.models import Sequence
        first = self.accept()
        data = demo_collection()
        sequence_of(data, "SEQ-0001").update(
            title="Aspirin, neu", target="salicylic-acid")
        second = self.accept(data)
        row = Sequence.objects.get(key="SEQ-0001")
        self.assertEqual((row.title, row.target.key, row.last_import),
                         ("Aspirin, neu", "salicylic-acid", second))
        self.assertEqual(Sequence.objects.get(key="SEQ-0002").last_import,
                         first)

    def test_a_new_procedure_is_created(self) -> None:
        """Requirement: Applying an import (a procedure the rows lack
        is created)."""
        from collection.models import Procedure
        first = self.accept()
        data = demo_collection()
        new = copy.deepcopy(procedure_of(data, "OSDB-0008"))
        new["id"] = "OSDB-0010"
        new["title"] = "Another"
        data["procedures"].append(new)
        second = self.accept(data)
        self.assertEqual(Procedure.objects.count(), 10)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0010").last_import, second)
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0008").last_import, first)
        self.assertEqual(signatures("OSDB-0010"),
                         [(1, "ethyl-cinnamate >> cinnamic-acid", False)])

    def test_a_new_entry_is_created(self) -> None:
        """Requirement: Applying an import (an entry the rows lack is
        created)."""
        from collection.models import Procedure
        self.accept()
        data = demo_collection()
        procedure_of(data, "OSDB-0009")["entries"].append({
            "substrates": ["benzaldehyde"],
            "products": [{"compound": "1-phenylethanol",
                          "yield_percent": 50}]})
        second = self.accept(data)
        self.assertEqual(
            [s for _, s, _ in signatures("OSDB-0009")],
            [*GENERAL, "benzaldehyde >> 1-phenylethanol"])
        self.assertEqual(
            Procedure.objects.get(key="OSDB-0009").last_import, second)


class ChangedSubstancesTests(ImportCase):

    def other_substrate(self) -> dict[str, Any]:
        data = demo_collection()
        procedure_of(data, "OSDB-0009")["entries"][0]["substrates"] = [
            "benzaldehyde"]
        return data

    def test_substances_change_the_entry_is_new(self) -> None:
        """Scenario: Substances change, the entry is new."""
        self.accept()
        old = entries_of("OSDB-0009")[0]
        self.accept(self.other_substrate())
        new_signature = "benzaldehyde >> 1-biphenyl-4-yl-ethanol"
        found = {e.signature: e for e in entries_of("OSDB-0009")}
        self.assertEqual(set(found), {GENERAL[0], new_signature, GENERAL[1],
                                      GENERAL[2]})
        self.assertNotEqual(found[new_signature].pk, old.pk)
        self.assertEqual(found[GENERAL[0]].pk, old.pk)
        self.assertTrue(found[GENERAL[0]].withdrawn)
        self.assertFalse(found[new_signature].withdrawn)
        self.assertEqual(found[new_signature].position, 1)
        self.assertEqual(substances_of(found[new_signature], "substrate"),
                         [("benzaldehyde", None)])
        self.assertEqual(
            [e.withdrawn for e in (found[GENERAL[1]], found[GENERAL[2]])],
            [False, False])

    def test_a_withdrawn_entry_keeps_its_substances(self) -> None:
        """Requirement: Applying an import (an entry of the procedure
        whose signature the manifest lacks is withdrawn, not
        deleted)."""
        self.accept()
        self.accept(self.other_substrate())
        old = next(e for e in entries_of("OSDB-0009")
                   if e.signature == GENERAL[0])
        self.assertTrue(old.withdrawn)
        self.assertEqual(substances_of(old, "substrate"),
                         [("4-acetylbiphenyl", None)])
        self.assertEqual(substances_of(old, "product"),
                         [("1-biphenyl-4-yl-ethanol", 90)])

    def test_an_entry_comes_back(self) -> None:
        """Requirement: Applying an import (an entry of the manifest is
        no longer withdrawn)."""
        self.accept()
        old = entries_of("OSDB-0009")[0]
        self.accept(self.other_substrate())
        self.accept()
        found = {e.signature: e for e in entries_of("OSDB-0009")}
        self.assertEqual(found[GENERAL[0]].pk, old.pk)
        self.assertFalse(found[GENERAL[0]].withdrawn)
        self.assertEqual(found[GENERAL[0]].position, 1)
        self.assertTrue(found["benzaldehyde >> 1-biphenyl-4-yl-ethanol"]
                        .withdrawn)
        self.assertEqual(len(found), 4)

    def test_a_step_follows_the_entry_its_number_now_counts(self) -> None:
        """Requirement: Applying an import (a sequence's steps are
        replaced whenever they differ, each naming the entry the step
        resolves to)."""
        from collection.models import Sequence, Step
        self.accept()
        second = self.accept(self.other_substrate())
        self.assertEqual(steps_of("SEQ-0002")[1], ("OSDB-0009", 1))
        step = Step.objects.get(sequence__key="SEQ-0002", position=2)
        self.assertEqual(step.entry.signature,
                         "benzaldehyde >> 1-biphenyl-4-yl-ethanol")
        self.assertFalse(step.entry.withdrawn)
        self.assertEqual(Sequence.objects.get(key="SEQ-0002").last_import,
                         second)


class WithdrawnTests(ImportCase):

    def test_a_file_gone_and_back(self) -> None:
        """Scenario: A file gone and back (a procedure no sequence
        names)."""
        from collection.models import Procedure
        self.accept()
        row = Procedure.objects.get(key="OSDB-0006")
        entries = signatures("OSDB-0006")
        (entry,) = entries_of("OSDB-0006")
        substances = substances_of(entry, "substrate")
        self.accept(without(demo_collection(), "OSDB-0006"))
        row.refresh_from_db()
        self.assertTrue(row.withdrawn)
        self.assertEqual(Procedure.objects.count(), 9)
        self.assertEqual(signatures("OSDB-0006"), entries)
        self.assertEqual(substances_of(entries_of("OSDB-0006")[0],
                                       "substrate"), substances)
        self.assertEqual(
            Procedure.objects.filter(withdrawn=True).count(), 1)
        self.accept()
        again = Procedure.objects.get(key="OSDB-0006")
        self.assertEqual(again.pk, row.pk)
        self.assertFalse(again.withdrawn)
        self.assertEqual(Procedure.objects.count(), 9)

    def test_a_procedure_and_its_sequence_gone_and_back(self) -> None:
        """Scenario: A file gone and back (`OSDB-0002`, with the
        sequence that names it)."""
        from collection.models import Procedure, Sequence
        self.accept()
        procedure = Procedure.objects.get(key="OSDB-0002")
        sequence = Sequence.objects.get(key="SEQ-0001")
        steps = steps_of("SEQ-0001")
        self.accept(without(demo_collection(), "OSDB-0002", "SEQ-0001"))
        procedure.refresh_from_db()
        sequence.refresh_from_db()
        self.assertTrue(procedure.withdrawn)
        self.assertTrue(sequence.withdrawn)
        self.assertEqual(signatures("OSDB-0002"), [(1, SPECIFIC, False)])
        self.assertEqual(steps_of("SEQ-0001"), steps)
        self.accept()
        procedure.refresh_from_db()
        sequence.refresh_from_db()
        self.assertFalse(procedure.withdrawn)
        self.assertFalse(sequence.withdrawn)
        self.assertEqual(steps_of("SEQ-0001"), steps)
        self.assertEqual(Procedure.objects.count(), 9)
        self.assertEqual(Sequence.objects.count(), 2)

    def test_a_sequence_gone_and_back(self) -> None:
        """Requirement: Applying an import (a sequence the manifest
        lacks is withdrawn, its steps left as they were)."""
        from collection.models import Sequence
        self.accept()
        row = Sequence.objects.get(key="SEQ-0002")
        self.accept(without(demo_collection(), "SEQ-0002"))
        row.refresh_from_db()
        self.assertTrue(row.withdrawn)
        self.assertEqual(steps_of("SEQ-0002"),
                         [("OSDB-0004", 1), ("OSDB-0009", 1)])
        self.assertFalse(Sequence.objects.get(key="SEQ-0001").withdrawn)
        self.accept()
        again = Sequence.objects.get(key="SEQ-0002")
        self.assertEqual(again.pk, row.pk)
        self.assertFalse(again.withdrawn)

    def test_nothing_is_ever_deleted(self) -> None:
        """Requirement: Imported rows (an import never deletes a
        procedure, scope entry or sequence)."""
        self.accept()
        before = counts()
        self.accept(without(demo_collection(), "OSDB-0006", "SEQ-0002"))
        after = counts()
        for name in ("Procedure", "ScopeEntry", "Sequence", "Step"):
            self.assertGreaterEqual(after[name], before[name], name)
        self.assertEqual(after["Procedure"], 9)
        self.assertEqual(after["Sequence"], 2)
        self.accept({"language": "de", "procedures": [], "sequences": []})
        self.assertEqual(counts()["Procedure"], 9)
        self.assertEqual(counts()["Sequence"], 2)
        from collection.models import Procedure, Sequence
        self.assertEqual(Procedure.objects.filter(withdrawn=False).count(),
                         0)
        self.assertEqual(Sequence.objects.filter(withdrawn=False).count(), 0)


class StepsTests(ImportCase):

    def test_steps_follow_the_file(self) -> None:
        """Scenario: Steps follow the file."""
        from collection.models import Sequence
        first = self.accept()
        data = demo_collection()
        sequence_of(data, "SEQ-0002")["steps"].append(
            {"procedure": "OSDB-0009", "entry": 2})
        second = self.accept(data)
        self.assertEqual(steps_of("SEQ-0002"),
                         [("OSDB-0004", 1), ("OSDB-0009", 1),
                          ("OSDB-0009", 2)])
        self.assertEqual(Sequence.objects.get(key="SEQ-0002").last_import,
                         second)
        self.assertEqual(Sequence.objects.get(key="SEQ-0001").last_import,
                         first)

    def test_steps_that_are_fewer_or_in_another_order(self) -> None:
        """Requirement: Applying an import (a sequence's steps are
        replaced by the manifest's whenever they differ)."""
        from collection.models import Sequence, Step
        self.accept()
        data = demo_collection()
        sequence_of(data, "SEQ-0002")["steps"].reverse()
        sequence_of(data, "SEQ-0002")["steps"][0]["entry"] = 3
        second = self.accept(data)
        self.assertEqual(steps_of("SEQ-0002"),
                         [("OSDB-0009", 3), ("OSDB-0004", 1)])
        self.assertEqual(Sequence.objects.get(key="SEQ-0002").last_import,
                         second)
        data = demo_collection()
        sequence_of(data, "SEQ-0002")["steps"] = [
            {"procedure": "OSDB-0004", "entry": None}]
        third = self.accept(data)
        self.assertEqual(steps_of("SEQ-0002"), [("OSDB-0004", 1)])
        self.assertEqual(Step.objects.filter(sequence__key="SEQ-0002")
                         .count(), 1)
        self.assertEqual(Sequence.objects.get(key="SEQ-0002").last_import,
                         third)

    def test_the_positions_of_steps_count_from_1(self) -> None:
        """Requirement: Imported rows (a step's `position`, from 1)."""
        from collection.models import Step
        self.accept()
        self.assertEqual(
            list(Step.objects.filter(sequence__key="SEQ-0002")
                 .order_by("position").values_list("position", flat=True)),
            [1, 2])
