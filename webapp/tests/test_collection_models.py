"""Tests of the imported rows (collection-import: Imported rows)."""

import uuid
from datetime import datetime, timedelta
from typing import Any

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from registry.models import Substance
from vocabulary.models import ReactionType

from . import BERLIN, make_user, page
from .collection_support import (TOOLING, ImportCase, accepts, commit_id,
                                 counts, make_author, make_entry,
                                 make_entry_substance, make_import,
                                 make_procedure, make_sequence, make_step,
                                 refuses)

ADMIN = "/lab/admin/collection/"
HEX40 = "a" * 40
HEX64 = "d" * 64


class AppTests(TestCase):

    def test_the_app_is_installed(self) -> None:
        """Requirement: Imported rows (the package `collection`)."""
        self.assertIn("collection",
                      [config.label for config in apps.get_app_configs()])
        names = {model.__name__ for model in
                 apps.get_app_config("collection").get_models()}
        self.assertLessEqual(
            {"Import", "Procedure", "ProcedureAuthor", "ScopeEntry",
             "EntrySubstance", "Sequence", "Step"}, names)


class ImportModelTests(ImportCase):

    def test_an_import_keeps_its_fields(self) -> None:
        """Requirement: Imported rows (an import)."""
        from collection.models import Import
        before = timezone.now()
        first = make_import()
        second = make_import(base=first, trigger="registry",
                             commit=HEX40, snapshot=HEX64)
        found = Import.objects.get(pk=second.pk)
        self.assertEqual(found.base, first)
        self.assertEqual((found.commit, found.snapshot, found.tooling),
                         (HEX40, HEX64, "b" * 40))
        self.assertEqual((found.outcome, found.trigger, found.language),
                         ("accepted", "registry", "de"))
        self.assertEqual(found.errors, "")
        self.assertTrue(found.release)
        self.assertIsNotNone(found.committed_at.utcoffset())
        self.assertGreaterEqual(found.received_at, before)
        self.assertLessEqual(found.received_at,
                             timezone.now() + timedelta(seconds=1))

    def test_a_refused_import_has_no_release_and_no_language(self) -> None:
        """Requirement: Imported rows (`release` and `language`, empty
        for a refused build; `errors`, one per line)."""
        accepts(self, lambda: _unsaved_import(
            outcome="refused", release="", language="",
            errors="first\nsecond"))

    def test_every_trigger_outcome_and_language_is_taken(self) -> None:
        """Requirement: Imported rows (the values of `trigger`,
        `outcome` and `language`)."""
        for trigger in ("commit", "registry", "tooling", "catch-up"):
            with self.subTest(trigger=trigger):
                accepts(self, lambda: _unsaved_import(trigger=trigger))
        for language in ("de", "en"):
            with self.subTest(language=language):
                accepts(self, lambda: _unsaved_import(language=language))

    def test_other_values_are_refused(self) -> None:
        """Requirement: Imported rows (the values of `trigger`,
        `outcome`, `language`, `commit`, `snapshot` and `tooling`)."""
        for field, value in (
                ("trigger", "push"), ("outcome", "pending"),
                ("language", "fr"), ("commit", "a" * 39),
                ("commit", "A" * 40), ("commit", "g" * 40),
                ("snapshot", "d" * 63), ("snapshot", "D" * 64),
                ("tooling", "b" * 41), ("tooling", "")):
            with self.subTest(field=field, value=value):
                refuses(self, lambda: _unsaved_import(**{field: value}))

    def test_a_build_is_recorded_once(self) -> None:
        """Requirement: Imported rows (`build`, a UUID, unique)."""
        build = uuid.uuid4()
        make_import(build=build)
        refuses(self, lambda: _unsaved_import(build=build))


def _unsaved_import(**fields: Any) -> Any:
    from collection.models import Import
    outcome = fields.get("outcome", "accepted")
    values = {
        "build": uuid.uuid4(), "commit": commit_id(),
        "committed_at": datetime(2026, 11, 9, 14, 30, tzinfo=BERLIN),
        "snapshot": "c" * 64, "tooling": TOOLING,
        "release": "" if outcome == "refused" else "000001-x-y",
        "language": "" if outcome == "refused" else "de",
        "outcome": "accepted", "trigger": "commit", "errors": ""}
    return Import(**{**values, **fields})


class ProcedureModelTests(ImportCase):

    def setUp(self) -> None:
        super().setUp()
        self.first = make_import()

    def test_a_procedure_holds_its_fields(self) -> None:
        """Requirement: Imported rows (a procedure)."""
        from collection.models import Procedure
        procedure = make_procedure(self.first, "OSDB-0002", source="org",
                                   title="Aspirin", title_de="Aspirin (de)")
        found = Procedure.objects.get(pk=procedure.pk)
        self.assertEqual((found.key, found.source, found.title,
                          found.title_de), ("OSDB-0002", "org", "Aspirin",
                                            "Aspirin (de)"))
        self.assertEqual(found.reaction_type.key, "acylation")
        self.assertEqual(found.last_import, self.first)
        self.assertIs(found.withdrawn, False)

    def test_a_procedure_keeps_whether_it_is_general(self) -> None:
        """Requirement: Imported rows (`general`, whether it is a
        general procedure)."""
        from collection.models import Procedure
        for key, general in (("OSDB-0002", False), ("OSDB-0009", True)):
            with self.subTest(general=general):
                made = make_procedure(self.first, key, general=general)
                made.full_clean()
                self.assertIs(Procedure.objects.get(pk=made.pk).general,
                              general)

    def test_a_german_title_is_optional(self) -> None:
        """Requirement: Imported rows (`title_de`, which may be
        empty)."""
        found = make_procedure(self.first)
        self.assertEqual(found.title_de, "")
        found.full_clean()

    def test_a_key_is_taken_once(self) -> None:
        """Requirement: Imported rows (`key`, unique)."""
        make_procedure(self.first, "OSDB-0002")
        refuses(self, lambda: _unsaved_procedure(self.first, "OSDB-0002"))
        accepts(self, lambda: _unsaved_procedure(self.first, "OSDB-0003"))

    def test_a_source_is_org_or_md(self) -> None:
        """Requirement: Imported rows (`source`, `org` or `md`)."""
        for number, source in enumerate(("org", "md"), start=11):
            with self.subTest(source=source):
                accepts(self, lambda: _unsaved_procedure(
                    self.first, f"OSDB-{number:04d}", source=source))
        refuses(self, lambda: _unsaved_procedure(
            self.first, "OSDB-0019", source="pdf"))

    def test_a_procedure_names_its_last_import(self) -> None:
        """Requirement: Imported rows (`last_import`)."""
        refuses(self, lambda: _unsaved_procedure(None, "OSDB-0002"))


def _unsaved_procedure(last_import: Any, key: str, **fields: Any) -> Any:
    from collection.models import Procedure
    values = {"key": key, "source": "md", "title": "Title",
              "reaction_type": ReactionType.objects.get(key="acylation"),
              "general": False, "last_import": last_import}
    return Procedure(**{**values, **fields})


class ProcedureAuthorModelTests(ImportCase):
    """Requirement: Imported rows (a procedure author: its `procedure`,
    a `user`, an account, and `position`, from 1, each account once per
    procedure)."""

    def setUp(self) -> None:
        super().setUp()
        self.first = make_import()
        self.procedure = make_procedure(self.first, "OSDB-0002")
        self.klehmann = get_user_model().objects.get(username="klehmann")

    def row(self, **fields: Any) -> Any:
        from collection.models import ProcedureAuthor
        values = {"procedure": self.procedure, "user": self.klehmann,
                  "position": 1}
        return ProcedureAuthor(**{**values, **fields})

    def test_a_row_holds_its_fields(self) -> None:
        from collection.models import ProcedureAuthor
        made = make_author(self.procedure, "klehmann", 1)
        found = ProcedureAuthor.objects.get(pk=made.pk)
        self.assertEqual((found.procedure, found.user, found.position),
                         (self.procedure, self.klehmann, 1))

    def test_a_procedure_lists_its_authors(self) -> None:
        """Requirement: Imported rows (the related name `authors`)."""
        make_author(self.procedure, "aschmidt", 2)
        make_author(self.procedure, "klehmann", 1)
        self.assertEqual(
            [row.user.username
             for row in self.procedure.authors.order_by("position")],
            ["klehmann", "aschmidt"])
        other = make_procedure(self.first, "OSDB-0003")
        self.assertEqual(other.authors.count(), 0)

    def test_a_position_counts_from_1(self) -> None:
        """Requirement: Imported rows (`position`, from 1)."""
        refuses(self, lambda: self.row(position=0))
        accepts(self, lambda: self.row(position=1))

    def test_an_account_is_an_author_once_per_procedure(self) -> None:
        """Requirement: Imported rows (each account once per
        procedure)."""
        make_author(self.procedure, "klehmann", 1)
        refuses(self, lambda: self.row(position=2))
        other = make_procedure(self.first, "OSDB-0003")
        accepts(self, lambda: self.row(procedure=other, position=1))
        accepts(self, lambda: self.row(
            position=2,
            user=get_user_model().objects.get(username="aschmidt")))

    def test_an_author_names_a_procedure_and_an_account(self) -> None:
        """Requirement: Imported rows (its `procedure` and its `user`)."""
        refuses(self, lambda: self.row(procedure=None))
        refuses(self, lambda: self.row(user=None))


class EntryModelTests(ImportCase):

    def setUp(self) -> None:
        super().setUp()
        self.first = make_import()
        self.procedure = make_procedure(self.first, "OSDB-0009")

    def test_an_entry_holds_its_fields(self) -> None:
        """Requirement: Imported rows (a scope entry)."""
        from collection.models import ScopeEntry
        entry = make_entry(self.procedure, "a >> b", 2)
        found = ScopeEntry.objects.get(pk=entry.pk)
        self.assertEqual((found.procedure, found.signature, found.position),
                         (self.procedure, "a >> b", 2))
        self.assertIs(found.withdrawn, False)

    def test_a_signature_is_unique_within_its_procedure(self) -> None:
        """Requirement: Imported rows (`signature`, unique within the
        procedure)."""
        from collection.models import ScopeEntry
        make_entry(self.procedure, "a >> b", 1)
        refuses(self, lambda: ScopeEntry(procedure=self.procedure,
                                         signature="a >> b", position=2))
        other = make_procedure(self.first, "OSDB-0002")
        accepts(self, lambda: ScopeEntry(procedure=other,
                                         signature="a >> b", position=1))

    def test_a_withdrawn_entry_keeps_its_signature(self) -> None:
        """Requirement: Imported rows (`signature`, unique within the
        procedure, withdrawn entries included)."""
        from collection.models import ScopeEntry
        make_entry(self.procedure, "a >> b", 1, withdrawn=True)
        refuses(self, lambda: ScopeEntry(procedure=self.procedure,
                                         signature="a >> b", position=2))

    def test_a_position_counts_from_1(self) -> None:
        """Requirement: Imported rows (`position`, from 1)."""
        from collection.models import ScopeEntry
        refuses(self, lambda: ScopeEntry(procedure=self.procedure,
                                         signature="a >> b", position=0))
        accepts(self, lambda: ScopeEntry(procedure=self.procedure,
                                         signature="a >> b", position=1))


class EntrySubstanceModelTests(ImportCase):

    def setUp(self) -> None:
        super().setUp()
        self.entry = make_entry(
            make_procedure(make_import(), "OSDB-0002"), "a >> b")
        self.acid = Substance.objects.get(key="salicylic-acid")

    def row(self, **fields: Any) -> Any:
        from collection.models import EntrySubstance
        values = {"entry": self.entry, "substance": self.acid,
                  "role": "substrate", "position": 1}
        return EntrySubstance(**{**values, **fields})

    def test_a_row_holds_its_fields(self) -> None:
        """Requirement: Imported rows (an entry substance)."""
        from collection.models import EntrySubstance
        made = make_entry_substance(self.entry, "acetylsalicylic-acid",
                                    "product", 1, yield_percent=75)
        found = EntrySubstance.objects.get(pk=made.pk)
        self.assertEqual((found.entry, found.substance.key, found.role,
                          found.position, found.yield_percent),
                         (self.entry, "acetylsalicylic-acid", "product", 1,
                          75))

    def test_a_role_is_substrate_or_product(self) -> None:
        """Requirement: Imported rows (`role`, `substrate` or
        `product`)."""
        accepts(self, lambda: self.row(role="substrate"))
        accepts(self, lambda: self.row(role="product"))
        refuses(self, lambda: self.row(role="catalyst"))

    def test_a_yield_is_for_a_product_only(self) -> None:
        """Requirement: Imported rows (`yield_percent`, for a product
        only, which may be none)."""
        accepts(self, lambda: self.row(role="product", yield_percent=90))
        accepts(self, lambda: self.row(
            role="product", yield_percent=None,
            substance=Substance.objects.get(key="acetic-anhydride")))
        refuses(self, lambda: self.row(role="substrate", yield_percent=90))

    def test_a_substance_is_taken_once_per_role(self) -> None:
        """Requirement: Imported rows (each substance once per role)."""
        make_entry_substance(self.entry, "salicylic-acid", "substrate", 1)
        refuses(self, lambda: self.row(role="substrate", position=2))
        accepts(self, lambda: self.row(
            role="substrate", position=2,
            substance=Substance.objects.get(key="acetic-anhydride")))

    def test_a_position_counts_from_1(self) -> None:
        """Requirement: Imported rows (`position`, from 1)."""
        refuses(self, lambda: self.row(position=0))
        accepts(self, lambda: self.row(position=1))


class SequenceModelTests(ImportCase):

    def setUp(self) -> None:
        super().setUp()
        self.first = make_import()

    def test_a_sequence_holds_its_fields(self) -> None:
        """Requirement: Imported rows (a sequence)."""
        from collection.models import Sequence
        made = make_sequence(self.first, "SEQ-0001", title_de="Aspirin")
        found = Sequence.objects.get(pk=made.pk)
        self.assertEqual((found.key, found.title, found.title_de,
                          found.target.key, found.last_import),
                         ("SEQ-0001", "Aspirin from wintergreen", "Aspirin",
                          "acetylsalicylic-acid", self.first))
        self.assertIs(found.withdrawn, False)

    def test_a_german_title_is_optional(self) -> None:
        """Requirement: Imported rows (`title_de`, which may be
        empty)."""
        found = make_sequence(self.first)
        self.assertEqual(found.title_de, "")
        found.full_clean()

    def test_a_key_is_taken_once(self) -> None:
        """Requirement: Imported rows (`key`, unique)."""
        from collection.models import Sequence
        make_sequence(self.first, "SEQ-0001")
        refuses(self, lambda: Sequence(
            key="SEQ-0001", title="Again", last_import=self.first,
            target=Substance.objects.get(key="cinnamic-acid")))


class StepModelTests(ImportCase):

    def setUp(self) -> None:
        super().setUp()
        first = make_import()
        procedure = make_procedure(first, "OSDB-0002")
        self.entry = make_entry(procedure)
        self.sequence = make_sequence(first, "SEQ-0001")
        self.other = make_sequence(first, "SEQ-0002",
                                   target="cinnamic-acid")

    def test_a_step_holds_its_fields(self) -> None:
        """Requirement: Imported rows (a step)."""
        from collection.models import Step
        made = make_step(self.sequence, self.entry, 1)
        found = Step.objects.get(pk=made.pk)
        self.assertEqual((found.sequence, found.entry, found.position),
                         (self.sequence, self.entry, 1))

    def test_a_position_is_unique_within_its_sequence(self) -> None:
        """Requirement: Imported rows (`position`, from 1, unique within
        the sequence)."""
        from collection.models import Step
        make_step(self.sequence, self.entry, 1)
        refuses(self, lambda: Step(sequence=self.sequence,
                                   entry=self.entry, position=1))
        accepts(self, lambda: Step(sequence=self.other, entry=self.entry,
                                   position=1))
        accepts(self, lambda: Step(sequence=self.sequence,
                                   entry=self.entry, position=2))

    def test_a_position_counts_from_1(self) -> None:
        """Requirement: Imported rows (`position`, from 1)."""
        from collection.models import Step
        refuses(self, lambda: Step(sequence=self.sequence,
                                   entry=self.entry, position=0))


class ProtectedTests(ImportCase):

    def setUp(self) -> None:
        super().setUp()
        first = make_import()
        self.procedure = make_procedure(first, "OSDB-0002")
        self.entry = make_entry(self.procedure)
        make_entry_substance(self.entry, "salicylic-acid", "substrate", 1)
        make_entry_substance(self.entry, "acetylsalicylic-acid", "product",
                             1, yield_percent=75)
        self.sequence = make_sequence(first, "SEQ-0001",
                                      target="cinnamic-acid")
        make_step(self.sequence, self.entry)

    def refused_deletion(self, record: Any) -> None:
        model = type(record)
        with self.assertRaises(ProtectedError):
            record.delete()
        self.assertTrue(model.objects.filter(pk=record.pk).exists())

    def test_a_substance_named_as_a_substrate_stays(self) -> None:
        """Requirement: Imported rows (a substance that a row names
        cannot be deleted)."""
        self.refused_deletion(Substance.objects.get(key="salicylic-acid"))

    def test_a_substance_named_as_a_product_stays(self) -> None:
        """Requirement: Imported rows (a substance that a row names
        cannot be deleted)."""
        self.refused_deletion(
            Substance.objects.get(key="acetylsalicylic-acid"))

    def test_a_substance_named_as_a_target_stays(self) -> None:
        """Requirement: Imported rows (a substance that a row names
        cannot be deleted)."""
        self.refused_deletion(Substance.objects.get(key="cinnamic-acid"))

    def test_a_reaction_type_in_use_stays(self) -> None:
        """Requirement: Imported rows (a reaction type that a row names
        cannot be deleted)."""
        self.refused_deletion(ReactionType.objects.get(key="acylation"))

    def test_an_entry_a_step_names_stays(self) -> None:
        """Requirement: Imported rows (a scope entry that a row names
        cannot be deleted)."""
        self.refused_deletion(self.entry)

    def test_what_no_row_names_can_be_deleted(self) -> None:
        """Requirement: Imported rows (only what a row names is
        kept)."""
        Substance.objects.get(key="acetic-anhydride").delete()
        ReactionType.objects.get(key="reduction").delete()
        self.assertFalse(Substance.objects.filter(
            key="acetic-anhydride").exists())


class SubstanceInUseTests(ImportCase):

    def test_a_substance_in_use(self) -> None:
        """Scenario: A substance in use."""
        from collection.models import EntrySubstance
        self.accept()
        self.assertTrue(EntrySubstance.objects.filter(
            substance__key="acetic-anhydride", role="substrate").exists())
        with self.assertRaises(ProtectedError):
            Substance.objects.get(key="acetic-anhydride").delete()
        self.assertTrue(Substance.objects.filter(
            key="acetic-anhydride").exists())


class AdminTests(ImportCase):
    """Requirement: Imported rows (the admin lists imports, procedures
    and sequences for staff, read-only)."""

    def setUp(self) -> None:
        super().setUp()
        self.staff = make_user("boss", "BO", is_staff=True,
                               is_superuser=True)
        self.client.force_login(self.staff)
        self.first = make_import()
        self.records = {
            "import": self.first,
            "procedure": make_procedure(self.first, "OSDB-0002"),
            "sequence": make_sequence(self.first, "SEQ-0001")}

    def controls(self, response: Any) -> set[str]:
        """The names of the controls a page submits, but for the
        CSRF token."""
        root = page(response)
        return {e.get("name") for e in
                root.find_all(("input", "select", "textarea"))
                if e.get("name") and e.get("name") != "csrfmiddlewaretoken"}

    def test_staff_see_the_lists(self) -> None:
        for model, record in self.records.items():
            with self.subTest(model=model):
                done = self.client.get(f"{ADMIN}{model}/")
                self.assertEqual(done.status_code, 200)
        self.assertIn("OSDB-0002", self.client.get(
            f"{ADMIN}procedure/").content.decode())
        self.assertIn("SEQ-0001", self.client.get(
            f"{ADMIN}sequence/").content.decode())
        self.assertIn(self.first.commit[:10], self.client.get(
            f"{ADMIN}import/").content.decode())

    def test_users_who_are_not_staff_are_kept_out(self) -> None:
        self.client.force_login(make_user("kl", "KL"))
        for model in self.records:
            with self.subTest(model=model):
                done = self.client.get(f"{ADMIN}{model}/")
                self.assertIn(done.status_code, (302, 403))
                if done.status_code == 302:
                    self.assertTrue(done["Location"].startswith(
                        "/lab/admin/login/"))

    def test_read_only_in_the_admin(self) -> None:
        """Scenario: Read-only in the admin."""
        for model, record in self.records.items():
            with self.subTest(model=model):
                change = f"{ADMIN}{model}/{record.pk}/change/"
                done = self.client.get(change)
                self.assertEqual(done.status_code, 200)
                root = page(done)
                names = self.controls(done)
                fields = {f.name for f in type(record)._meta.fields}
                self.assertFalse(names & fields, names)
                for name in ("_save", "_continue", "_addanother"):
                    self.assertNotIn(name, names)
                self.assertIsNone(root.find("input", name="_save"))
                self.assertEqual(self.client.get(
                    f"{ADMIN}{model}/add/").status_code, 403)
                self.assertEqual(self.client.post(
                    f"{ADMIN}{model}/add/", {}).status_code, 403)
                self.assertEqual(self.client.post(
                    f"{ADMIN}{model}/{record.pk}/delete/",
                    {"post": "yes"}).status_code, 403)
                self.assertTrue(type(record).objects.filter(
                    pk=record.pk).exists())

    def test_a_posted_change_is_refused(self) -> None:
        """Requirement: Imported rows (no way to change one)."""
        procedure = self.records["procedure"]
        done = self.client.post(
            f"{ADMIN}procedure/{procedure.pk}/change/",
            {"title": "Changed", "key": "OSDB-0002", "source": "md",
             "withdrawn": "on"})
        self.assertEqual(done.status_code, 403)
        procedure.refresh_from_db()
        self.assertEqual(procedure.title, "Aspirin")
        self.assertFalse(procedure.withdrawn)
        self.assertEqual(counts()["Procedure"], 1)


class IssuedIdModelTests(ImportCase):
    """Requirement: Imported rows (an issued ID: `key`, `user` and
    `issued_at`)."""

    def row(self, key: str = "OSDB-0010", **fields: Any) -> Any:
        from collection.models import IssuedId
        return IssuedId(key=key, **fields)

    def test_an_issued_id_keeps_its_fields(self) -> None:
        """Requirement: Imported rows (an issued ID: `key`, the account
        it was issued to and when it was issued)."""
        from collection.models import IssuedId
        kl = get_user_model().objects.get(username="klehmann")
        before = timezone.now()
        made = IssuedId.objects.create(key="OSDB-0010", user=kl)
        found = IssuedId.objects.get(pk=made.pk)
        self.assertEqual((found.key, found.user), ("OSDB-0010", kl))
        self.assertGreaterEqual(found.issued_at, before)
        self.assertLessEqual(found.issued_at, timezone.now())

    def test_an_adopted_id_has_no_account(self) -> None:
        """Requirement: Imported rows (none for an adopted ID)."""
        found = accepts(self, lambda: self.row("SEQ-0001"))
        self.assertIsNone(found.user)
        found.refresh_from_db()
        self.assertIsNone(found.user)

    def test_a_key_is_taken_once(self) -> None:
        """Requirement: Imported rows (`key`, unique)."""
        from collection.models import IssuedId
        IssuedId.objects.create(key="OSDB-0010")
        refuses(self, lambda: self.row("OSDB-0010"))
        accepts(self, lambda: self.row("OSDB-0011"))

    def test_a_key_is_a_procedure_or_sequence_id(self) -> None:
        """Requirement: Imported rows (an `OSDB-NNNN` or `SEQ-NNNN`)."""
        accepts(self, lambda: self.row("OSDB-0001"))
        accepts(self, lambda: self.row("SEQ-9999"))
        for key in ("OSDB-001", "OSDB-00010", "SEQ-12", "XYZ-0001",
                    "osdb-0010", "seq-0001", "OSDB0010", " OSDB-0010",
                    ""):
            with self.subTest(key=key):
                refuses(self, lambda: self.row(key))

    def test_an_account_with_issued_ids_cannot_be_deleted(self) -> None:
        """Requirement: Imported rows (an account that a row names
        cannot be deleted)."""
        from collection.models import IssuedId
        kl = get_user_model().objects.get(username="klehmann")
        IssuedId.objects.create(key="OSDB-0010", user=kl)
        with self.assertRaises(ProtectedError):
            kl.delete()
        self.assertTrue(get_user_model().objects.filter(pk=kl.pk).exists())
        self.assertTrue(IssuedId.objects.filter(key="OSDB-0010").exists())


class IssuedIdAdminTests(ImportCase):
    """Requirement: Imported rows (the admin lists issued IDs for staff,
    read-only)."""

    def setUp(self) -> None:
        from collection.models import IssuedId
        super().setUp()
        self.staff = make_user("boss", "BO", is_staff=True,
                               is_superuser=True)
        self.client.force_login(self.staff)
        self.record = IssuedId.objects.create(
            key="OSDB-0010",
            user=get_user_model().objects.get(username="klehmann"))

    def test_staff_see_the_list(self) -> None:
        done = self.client.get(f"{ADMIN}issuedid/")
        self.assertEqual(done.status_code, 200)
        self.assertIn("OSDB-0010", done.content.decode("utf-8"))

    def test_users_who_are_not_staff_are_kept_out(self) -> None:
        self.client.force_login(make_user("kl", "KL"))
        done = self.client.get(f"{ADMIN}issuedid/")
        self.assertIn(done.status_code, (302, 403))

    def test_read_only_in_the_admin(self) -> None:
        """Scenario: Read-only in the admin (an issued ID)."""
        from collection.models import IssuedId
        change = f"{ADMIN}issuedid/{self.record.pk}/change/"
        done = self.client.get(change)
        self.assertEqual(done.status_code, 200)
        names = {e.get("name") for e in
                 page(done).find_all(("input", "select", "textarea"))
                 if e.get("name") and e.get("name") != "csrfmiddlewaretoken"}
        self.assertFalse(names & {f.name for f in IssuedId._meta.fields},
                         names)
        self.assertEqual(self.client.get(
            f"{ADMIN}issuedid/add/").status_code, 403)
        self.assertEqual(self.client.post(
            f"{ADMIN}issuedid/add/", {"key": "OSDB-0011"}).status_code, 403)
        self.assertEqual(self.client.post(
            change, {"key": "OSDB-0099"}).status_code, 403)
        self.assertEqual(self.client.post(
            f"{ADMIN}issuedid/{self.record.pk}/delete/",
            {"post": "yes"}).status_code, 403)
        self.record.refresh_from_db()
        self.assertEqual(self.record.key, "OSDB-0010")
