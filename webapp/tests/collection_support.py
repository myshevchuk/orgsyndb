"""Fixtures and helpers shared by the tests of the collection import
(collection-import).

Nothing here imports the ``collection`` package at module level, so a
test that uses these helpers fails on its own assertions while the
package is missing.

The manifests the tests post are built from
``webapp/demo/manifest.json``, the collection half of the demo's
manifest as ``tools/orgsyndb manifest`` prints it, with the build half
added by ``manifest`` below.
"""

import copy
import hashlib
import itertools
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from . import BERLIN, load_demo_registry

MANIFEST = "/lab/collection/manifest/"
IMPORTS = "/lab/collection/"
TOKEN = "s3cret"
FIXTURE = Path(__file__).resolve().parents[1] / "demo" / "manifest.json"
TOOLING = "b" * 40
# The numbers of the demo collection's procedures and sequences.
PROCEDURES = 9
SEQUENCES = 2

_commits = itertools.count(1)


def commit_id() -> str:
    """A commit ID, 40 lower-case hexadecimal digits, new on each
    call."""
    return hashlib.sha1(str(next(_commits)).encode()).hexdigest()


def demo_collection() -> dict[str, Any]:
    """The collection half of the demo's manifest, as a new copy."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def current_digest() -> str:
    """The digest of the registry's snapshot now."""
    from registry import snapshot
    return snapshot.build()["digest"]


def build_half(**over: Any) -> dict[str, Any]:
    """The keys a manifest has whatever its outcome, for a build
    after the import ``base``, none by default."""
    commit = commit_id()
    return {"format": 1, "build": str(uuid.uuid4()), "commit": commit,
            "committed_at": "2026-11-09T14:30:00+01:00", "base": None,
            "snapshot": current_digest(), "tooling": TOOLING,
            "trigger": "commit", **over}


def manifest(collection: dict[str, Any] | None = None,
             **over: Any) -> dict[str, Any]:
    """A manifest of a build that succeeded: the build half, the
    collection half ``collection`` (the demo's by default, copied) and
    ``over``, which replaces keys."""
    half = build_half()
    return {**half, "outcome": "built",
            "release": f"000001-{TOOLING[:10]}-{half['commit'][:10]}",
            **copy.deepcopy(demo_collection() if collection is None
                            else collection), **over}


def refused(errors: list[str], **over: Any) -> dict[str, Any]:
    """A manifest of a build that failed, with ``errors``."""
    return {**build_half(), "outcome": "refused", "errors": list(errors),
            **over}


def by_id(items: list[dict[str, Any]], ident: str) -> dict[str, Any]:
    """The table of ``items`` whose ``id`` is ``ident``."""
    (found,) = [item for item in items if item["id"] == ident]
    return found


def entry_count(data: dict[str, Any], ident: str) -> int:
    return len(by_id(data["procedures"], ident)["entries"])


def post(client: Any, body: Any, token: str | None = TOKEN,
         **extra: Any) -> Any:
    """Post ``body``, a table or text, to the manifest path, signed
    with ``token``, or not signed when it is None."""
    text = body if isinstance(body, str) else json.dumps(body)
    headers = ({} if token is None
               else {"HTTP_AUTHORIZATION": f"Bearer {token}"})
    return client.post(MANIFEST, text, content_type="application/json",
                       **headers, **extra)


def refuses(case: TestCase, make: Any) -> None:
    """Assert that the record ``make()`` returns is refused: by its
    validation, or by the database."""
    record = make()
    try:
        record.full_clean()
    except ValidationError:
        return
    try:
        with transaction.atomic():
            record.save()
    except IntegrityError:
        return
    case.fail(f"{type(record).__name__} {record!r} was not refused")


def accepts(case: TestCase, make: Any) -> Any:
    """Assert that the record ``make()`` returns is valid and saves;
    return it."""
    record = make()
    record.full_clean()
    record.save()
    return record


# --- rows made directly, without the manifest view -------------------------


def make_import(**fields: Any) -> Any:
    """An import of the demo collection, accepted unless ``fields``
    say otherwise."""
    from collection.models import Import
    commit = commit_id()
    outcome = fields.get("outcome", "accepted")
    values = {
        "build": uuid.uuid4(), "commit": commit,
        "committed_at": datetime(2026, 11, 9, 14, 30, tzinfo=BERLIN),
        "base": None, "snapshot": "c" * 64, "tooling": TOOLING,
        "release": "" if outcome == "refused" else
        f"000001-{TOOLING[:10]}-{commit[:10]}",
        "language": "" if outcome == "refused" else "de",
        "outcome": "accepted", "trigger": "commit",
        "errors": "build failed" if outcome == "refused" else ""}
    return Import.objects.create(**{**values, **fields})


def make_procedure(last_import: Any, key: str = "OSDB-0002",
                   **fields: Any) -> Any:
    from collection.models import Procedure
    from vocabulary.models import ReactionType
    values = {"key": key, "source": "md", "title": "Aspirin",
              "reaction_type": ReactionType.objects.get(key="acylation"),
              "general": False, "last_import": last_import}
    return Procedure.objects.create(**{**values, **fields})


def make_entry(procedure: Any, signature: str = "a >> b",
               position: int = 1, **fields: Any) -> Any:
    from collection.models import ScopeEntry
    return ScopeEntry.objects.create(procedure=procedure,
                                     signature=signature,
                                     position=position, **fields)


def make_entry_substance(entry: Any, key: str, role: str,
                         position: int = 1, **fields: Any) -> Any:
    from collection.models import EntrySubstance
    from registry.models import Substance
    return EntrySubstance.objects.create(
        entry=entry, substance=Substance.objects.get(key=key), role=role,
        position=position, **fields)


def make_sequence(last_import: Any, key: str = "SEQ-0001",
                  target: str = "acetylsalicylic-acid",
                  **fields: Any) -> Any:
    from collection.models import Sequence
    from registry.models import Substance
    values = {"key": key, "title": "Aspirin from wintergreen",
              "target": Substance.objects.get(key=target),
              "last_import": last_import}
    return Sequence.objects.create(**{**values, **fields})


def make_step(sequence: Any, entry: Any, position: int = 1) -> Any:
    from collection.models import Step
    return Step.objects.create(sequence=sequence, entry=entry,
                               position=position)


def accept(language: str = "en", **fields: Any) -> Any:
    """Record an accepted import of ``language``, the latest accepted
    import from now on, without any imported row: how a test sets the
    language of the site."""
    return make_import(language=language, **fields)


def latest_import() -> Any:
    """The latest accepted import, the accepted import received last,
    or None."""
    from collection.models import Import
    return Import.objects.filter(outcome="accepted").order_by(
        "received_at", "pk").last()


def import_collection(collection: dict[str, Any] | None = None,
                      **over: Any) -> Any:
    """Post to the manifest view, as the builder would, a manifest of
    ``collection`` (the demo's by default) built after the latest
    accepted import against the registry as it is now, with ``over``
    replacing keys; assert that it is accepted and return the import.
    The database must hold the demo registry or the substances the
    collection names."""
    from django.test import Client

    from collection.models import Import
    latest = latest_import()
    body = manifest(collection, **{
        "base": None if latest is None else latest.pk, **over})
    with override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN):
        done = post(Client(), body)
    assert done.status_code == 200, done.content
    assert done.json()["outcome"] == "accepted", done.json()
    return Import.objects.get(pk=done.json()["import"])


def changed_collection(ident: str, entry: int = 1,
                       substrates: list[str] | None = None
                       ) -> dict[str, Any]:
    """The demo collection with the substrates of entry ``entry`` of the
    procedure ``ident`` replaced by ``substrates``, ``benzaldehyde``
    by default, so that an import of it withdraws the entry the demo
    has and adds another."""
    data = demo_collection()
    by_id(data["procedures"], ident)["entries"][entry - 1][
        "substrates"] = substrates or ["benzaldehyde"]
    return data


def without_ids(*idents: str) -> dict[str, Any]:
    """The demo collection without the procedures and sequences
    ``idents``."""
    data = demo_collection()
    data["procedures"] = [p for p in data["procedures"]
                          if p["id"] not in idents]
    data["sequences"] = [s for s in data["sequences"]
                         if s["id"] not in idents]
    return data


# --- rows read back ---------------------------------------------------------


def rows(model: str) -> list[dict[str, Any]]:
    """Every row of the model ``model`` of the app ``collection``, by
    primary key, as a table of its columns."""
    from django.apps import apps
    return list(apps.get_model("collection", model).objects.order_by(
        "pk").values())


def counts() -> dict[str, int]:
    """The number of rows of each model of the app ``collection``."""
    from django.apps import apps
    return {name: apps.get_model("collection", name).objects.count()
            for name in ("Import", "Procedure", "ScopeEntry",
                         "EntrySubstance", "Sequence", "Step")}


def dump() -> dict[str, list[dict[str, Any]]]:
    """Every row of every model of the app ``collection``."""
    return {name: rows(name) for name in counts()}


def entries_of(key: str) -> list[Any]:
    """The scope entries of the procedure ``key`` by position, the
    withdrawn ones too."""
    from collection.models import ScopeEntry
    return list(ScopeEntry.objects.filter(procedure__key=key)
                .order_by("position", "pk"))


def substances_of(entry: Any, role: str) -> list[tuple[str, Any]]:
    """The key and yield of each substance of ``entry`` in ``role``, in
    their order."""
    from collection.models import EntrySubstance
    return [(row.substance.key, row.yield_percent)
            for row in EntrySubstance.objects.filter(
                entry=entry, role=role).order_by("position")]


def steps_of(key: str) -> list[tuple[str, int]]:
    """The procedure and the position of the entry each step of the
    sequence ``key`` names, in order."""
    from collection.models import Step
    return [(step.entry.procedure.key, step.entry.position)
            for step in Step.objects.filter(sequence__key=key)
            .order_by("position")]


# --- test cases -------------------------------------------------------------


@override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN)
class ImportCase(TestCase):
    """A test case whose database holds the demo registry, with the
    builder's token set."""

    @classmethod
    def setUpTestData(cls) -> None:
        load_demo_registry()

    def send(self, body: Any, token: str | None = TOKEN) -> Any:
        """Post ``body`` to the manifest view."""
        return post(self.client, body, token)

    def latest(self) -> Any:
        """The latest accepted import, or None."""
        from collection.models import Import
        return Import.objects.filter(outcome="accepted").order_by(
            "received_at", "pk").last()

    def follow(self, collection: dict[str, Any] | None = None,
               **over: Any) -> dict[str, Any]:
        """A manifest built after the latest accepted import, against
        the registry now."""
        latest = self.latest()
        return manifest(collection, **{
            "base": None if latest is None else latest.pk, **over})

    def accept(self, collection: dict[str, Any] | None = None,
               **over: Any) -> Any:
        """Post a manifest built after the latest accepted import;
        assert that it is accepted, and return the import."""
        from collection.models import Import
        done = self.send(self.follow(collection, **over))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "accepted", done.json())
        return Import.objects.get(pk=done.json()["import"])

    def refuse(self, collection: dict[str, Any]) -> Any:
        """Post a manifest built after the latest accepted import;
        assert that the application refuses it, and return the
        answer."""
        done = self.send(self.follow(collection))
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()["outcome"], "refused", done.json())
        return done.json()
