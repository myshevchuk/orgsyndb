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

from . import (BERLIN, load_demo_registry, make_demo_accounts,
               make_demo_notebooks)

MANIFEST = "/lab/collection/manifest/"
IMPORTS = "/lab/collection/"
IDS = "/lab/collection/ids/"
TOKEN = "s3cret"
FIXTURE = Path(__file__).resolve().parents[1] / "demo" / "manifest.json"
TOOLING = "b" * 40
# The numbers of the demo collection's procedures and sequences.
PROCEDURES = 9
SEQUENCES = 2
# The user names the demo's procedures credit, in the order of their
# files (sample-procedures "Sample marking").
DEMO_CREDITS = {
    "OSDB-0001": ["klehmann", "tbauer"], "OSDB-0002": ["klehmann", "aschmidt"],
    "OSDB-0003": ["tbauer", "jkoch"], "OSDB-0004": ["aschmidt", "mwolf"],
    "OSDB-0005": ["mwolf"], "OSDB-0006": ["jkoch", "klehmann"],
    "OSDB-0007": ["aschmidt"], "OSDB-0008": ["aschmidt", "tbauer"],
    "OSDB-0009": ["mwolf"]}

# The notebook and the project the demo's procedures name (sample-
# procedures "Demo collection").
DEMO_JOURNAL = {
    "OSDB-0001": ("AE-1/1", "first-year-practical"),
    "OSDB-0002": ("AE-1/2", "first-year-practical"),
    "OSDB-0003": ("AE-1/3", "first-year-practical"),
    "OSDB-0004": ("AE-2/7", "biaryls"),
    "OSDB-0005": ("AE-2/8", "biaryls"),
    "OSDB-0006": ("CE-1/4", "first-year-practical"),
    "OSDB-0007": ("AE-2/11", "cinnamates"),
    "OSDB-0008": ("AE-2/12", "cinnamates"),
    "OSDB-0009": ("CE-3/1", "advanced-practical")}

_commits = itertools.count(1)


def commit_id() -> str:
    """A commit ID, 40 lower-case hexadecimal digits, new on each
    call."""
    return hashlib.sha1(str(next(_commits)).encode()).hexdigest()


def demo_collection() -> dict[str, Any]:
    """The collection half of the demo's manifest, as a new copy."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def credited(collection: dict[str, Any] | None = None,
             **authors: list[str]) -> dict[str, Any]:
    """The collection half of a manifest, the demo's by default, as a
    new copy in which each procedure's ``authors`` are those of
    ``DEMO_CREDITS``, but for the procedures ``authors`` names by ID
    with an underscore in place of the hyphen (``OSDB_0002``)."""
    data = copy.deepcopy(demo_collection() if collection is None
                         else collection)
    for procedure in data["procedures"]:
        key = procedure["id"]
        procedure["authors"] = list(
            authors.get(key.replace("-", "_"), DEMO_CREDITS[key]))
    return data


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


# --- issued IDs and access tokens -------------------------------------------


def issue_ids(*keys: str) -> None:
    """Record each of ``keys`` as an issued ID, to no account, unless it
    is issued already: what ``adopt_ids`` does. Does nothing while the
    application has no issued IDs to record."""
    from django.apps import apps
    from django.utils import timezone
    try:
        model = apps.get_model("collection", "IssuedId")
    except LookupError:
        return
    for key in keys:
        model.objects.get_or_create(
            key=key, defaults={"issued_at": timezone.now()})


def issued_keys() -> list[str]:
    """The key of every issued ID, in order."""
    from collection.models import IssuedId
    return sorted(IssuedId.objects.values_list("key", flat=True))


def issued_to(key: str) -> str | None:
    """The user name of the account the issued ID ``key`` was issued
    to, or None for an adopted one."""
    from collection.models import IssuedId
    found = IssuedId.objects.select_related("user").get(key=key)
    return None if found.user is None else found.user.username


def make_token(username: str, name: str = "Laptop") -> str:
    """A new access token of the account ``username``; return the token
    itself."""
    from django.contrib.auth import get_user_model

    from accounts.models import AccessToken
    return AccessToken.create_for(
        get_user_model().objects.get(username=username), name)[1]


def request_id(client: Any, kind: Any, token: str | None = None,
               **extra: Any) -> Any:
    """Post the kind ``kind`` to the ID path, signed with the access
    token ``token`` unless it is None."""
    headers = ({} if token is None
               else {"HTTP_AUTHORIZATION": f"Bearer {token}"})
    return client.post(IDS, json.dumps({"kind": kind}),
                       content_type="application/json", **headers,
                       **extra)


def ids_of(data: dict[str, Any]) -> list[str]:
    """The IDs of the procedures and sequences of the collection half
    ``data`` of a manifest."""
    return [*(item["id"] for item in data["procedures"]),
            *(item["id"] for item in data["sequences"])]


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
    issue_ids(key)
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
    issue_ids(key)
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
    The IDs of the collection are issued first, as ``adopt_ids`` would
    issue them. The database must hold the demo registry or the
    substances the collection names."""
    from django.test import Client

    from collection.models import Import
    issue_ids(*ids_of(demo_collection() if collection is None
                      else collection))
    latest = latest_import()
    body = manifest(collection, **{
        "base": None if latest is None else latest.pk, **over})
    with override_settings(ORGSYNDB_BUILDER_TOKEN=TOKEN):
        done = post(Client(), body)
    assert done.status_code == 200, done.content
    assert done.json()["outcome"] == "accepted", done.json()
    return Import.objects.get(pk=done.json()["import"])


def copy_procedure(data: dict[str, Any], source: str, ident: str
                   ) -> dict[str, Any]:
    """A copy of the procedure ``source`` of the collection half
    ``data``, named ``ident``, that names no notebook, since no two
    procedures name one entry (collection-import "Import checks"); the
    caller adds it to ``data``."""
    new = copy.deepcopy(by_id(data["procedures"], source))
    new["id"] = ident
    new["notebook"] = None
    return new


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


def author_rows() -> list[tuple[str, str, int]]:
    """The procedure, the user name and the position of every row of
    the procedure authors, by procedure and position."""
    from collection.models import ProcedureAuthor
    return [(row.procedure.key, row.user.username, row.position)
            for row in ProcedureAuthor.objects.select_related(
                "procedure", "user").order_by("procedure__key", "position")]


def authors_of(key: str) -> list[str]:
    """The user names of the authors of the procedure ``key``, by
    position."""
    from collection.models import ProcedureAuthor
    return [row.user.username for row in ProcedureAuthor.objects.filter(
        procedure__key=key).select_related("user").order_by("position")]


def make_author(procedure: Any, username: str, position: int = 1,
                **fields: Any) -> Any:
    """The account ``username`` as an author of ``procedure``."""
    from django.contrib.auth import get_user_model

    from collection.models import ProcedureAuthor
    return ProcedureAuthor.objects.create(
        procedure=procedure,
        user=get_user_model().objects.get(username=username),
        position=position, **fields)


def counts() -> dict[str, int]:
    """The number of rows of each model of the app ``collection``."""
    from django.apps import apps
    return {name: apps.get_model("collection", name).objects.count()
            for name in ("Import", "Procedure", "ScopeEntry",
                         "EntrySubstance", "Sequence", "Step")}


def dump() -> dict[str, list[dict[str, Any]]]:
    """Every row of every model of the app ``collection``."""
    return {name: rows(name) for name in counts()}


def journal_of(key: str) -> tuple[str | None, str | None]:
    """The journal entry, written ``<code>/<number>``, and the project's
    key that the procedure ``key`` names, each None for none."""
    from collection.models import Procedure
    found = Procedure.objects.select_related(
        "journal_entry__notebook", "project").get(key=key)
    return (None if found.journal_entry is None
            else str(found.journal_entry),
            None if found.project is None else found.project.key)


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
    """A test case whose database holds the demo registry and the demo
    accounts, with the builder's token set."""

    @classmethod
    def setUpTestData(cls) -> None:
        load_demo_registry()
        make_demo_accounts()
        make_demo_notebooks()

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


# --- collections with more sequences ---------------------------------------


def longer_collection() -> dict[str, Any]:
    """The demo collection with a procedure ``OSDB-0010``, which makes
    ``benzaldehyde`` from ``acetone``, and two more sequences of
    ``cinnamic-acid``: ``SEQ-0003``, of three steps, ``OSDB-0010``,
    ``OSDB-0007`` and ``OSDB-0008``, whose intermediates are
    ``benzaldehyde`` and ``ethyl-cinnamate``; and ``SEQ-0004``, of the
    two steps ``OSDB-0007`` and ``OSDB-0008``, whose intermediate is
    ``ethyl-cinnamate``."""
    data = demo_collection()
    new = copy_procedure(data, "OSDB-0007", "OSDB-0010")
    new["entries"][0]["substrates"] = ["acetone"]
    new["entries"][0]["products"] = [
        {"compound": "benzaldehyde", "yield_percent": 90}]
    data["procedures"].append(new)
    title = "Zimtsäure in Stufen"
    for ident, steps in (("SEQ-0003", ["OSDB-0010", "OSDB-0007",
                                       "OSDB-0008"]),
                         ("SEQ-0004", ["OSDB-0007", "OSDB-0008"])):
        data["sequences"].append({
            "id": ident, "title": title, "title_de": title,
            "target": "cinnamic-acid",
            "steps": [{"procedure": key, "entry": None} for key in steps]})
    return data


def shortened_collection() -> dict[str, Any]:
    """``longer_collection`` with ``SEQ-0003`` of the two steps
    ``OSDB-0007`` and ``OSDB-0008``."""
    data = longer_collection()
    by_id(data["sequences"], "SEQ-0003")["steps"].pop(0)
    return data


def retargeted_collection() -> dict[str, Any]:
    """``longer_collection`` in which ``OSDB-0008`` makes
    ``ethyl-cinnamate`` too, which is the target of ``SEQ-0003``."""
    data = longer_collection()
    by_id(data["procedures"], "OSDB-0008")["entries"][0][
        "products"].append({"compound": "ethyl-cinnamate",
                            "yield_percent": 50})
    by_id(data["sequences"], "SEQ-0003")["target"] = "ethyl-cinnamate"
    return data


def reordered_collection() -> dict[str, Any]:
    """The demo collection in which ``OSDB-0001`` lists
    ``acetic-anhydride`` before ``salicylic-acid`` among its products,
    both of which ``OSDB-0002`` takes, so that the intermediate of the
    first step of ``SEQ-0001`` is ``acetic-anhydride``."""
    data = demo_collection()
    entry = by_id(data["procedures"], "OSDB-0001")["entries"][0]
    entry["products"].insert(
        0, {"compound": "acetic-anhydride", "yield_percent": 50})
    return data
