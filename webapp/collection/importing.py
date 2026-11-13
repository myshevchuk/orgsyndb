"""Receiving a manifest: reading it, judging whether it is stale,
checking it against the registry, and applying an accepted one to the
imported rows (collection-import).

A manifest is a table the builder posts for every build it tries. Its
build half names the build, the collection commit, the import it was
built after (``base``), the registry digest it was built with
(``snapshot``), the application commit that built it (``tooling``), the
trigger and the outcome; a build that succeeded adds the collection half
that ``tools/orgsyndb manifest`` prints, one that failed its errors.
The first import the application accepts adopts the IDs its manifest
names (``collection.issuing``); every import is refused an ID that is
not issued.
"""

import re
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from collection import issuing
from collection.models import (KEY_LENGTH, RELEASE_LENGTH, EntrySubstance,
                               Import, Language, Outcome, Procedure,
                               ProcedureAuthor, Role, ScopeEntry,
                               Sequence, Source, Step, Trigger,
                               latest_accepted)
from journal.entries import entry_for
from journal.models import ENTRY_RE, Notebook
from journal.models import Entry as JournalEntry
from orgsyndb_web import lock
from registry import snapshot
from registry.models import Substance
from vocabulary.models import Project, ReactionType

FORMAT = 1
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
# The error of an ID the application has not issued, after the ID.
NOT_ISSUED = "not issued by the lab application"


class Malformed(Exception):
    """A body that is not a manifest; the message says what is wrong."""


def signature(substrates: Iterable[str], products: Iterable[str]) -> str:
    """Return the signature of a scope entry with the substance keys
    SUBSTRATES and PRODUCTS: each side's keys sorted and joined by
    `` + ``, the two sides joined by `` >> ``, as
    ``a + b >> c``."""
    return (" + ".join(sorted(substrates)) + " >> "
            + " + ".join(sorted(products)))


# --- reading ----------------------------------------------------------------


def _text(table: dict[str, Any], key: str, where: str,
          limit: int | None = None, empty: bool = False) -> str:
    """Return the string under KEY of TABLE, the part of the manifest
    WHERE names; raise Malformed when it is missing, not a string, empty
    unless EMPTY allows it, or longer than LIMIT."""
    value = table.get(key)
    if not isinstance(value, str):
        raise Malformed(f"{where}{key}: not a string")
    if not value and not empty:
        raise Malformed(f"{where}{key}: empty")
    if limit is not None and len(value) > limit:
        raise Malformed(f"{where}{key}: longer than {limit} characters")
    return value


def _optional_string(table: dict[str, Any], key: str,
                     where: str) -> str | None:
    """Return the string or null under KEY of TABLE, None for null;
    raise Malformed for a missing key or another type."""
    if key not in table:
        raise Malformed(f"{where}{key}: missing")
    value = table[key]
    if value is not None and not isinstance(value, str):
        raise Malformed(f"{where}{key}: neither a string nor null")
    return value


def _optional_text(table: dict[str, Any], key: str, where: str) -> str:
    """Return the string or null under KEY of TABLE as text, empty for
    null; raise Malformed for a missing key or another type."""
    return _optional_string(table, key, where) or ""


def _pattern(table: dict[str, Any], key: str, pattern: re.Pattern[str],
             what: str) -> str:
    """Return the string under KEY of TABLE that PATTERN matches; raise
    Malformed, saying it is not WHAT, otherwise."""
    value = table.get(key)
    if not isinstance(value, str) or not pattern.match(value):
        raise Malformed(f"{key}: not {what}")
    return value


def _choice(table: dict[str, Any], key: str, choices: Iterable[str],
            where: str = "") -> str:
    """Return the value under KEY of TABLE, one of CHOICES; raise
    Malformed otherwise."""
    allowed = list(choices)
    value = table.get(key)
    if value not in allowed:
        raise Malformed(f"{where}{key}: not one of {', '.join(allowed)}")
    return value


def _list(table: dict[str, Any], key: str, where: str = "") -> list[Any]:
    """Return the list under KEY of TABLE; raise Malformed otherwise."""
    value = table.get(key)
    if not isinstance(value, list):
        raise Malformed(f"{where}{key}: not a list")
    return value


def _tables(table: dict[str, Any], key: str,
            where: str = "") -> list[dict[str, Any]]:
    """Return the list of tables under KEY of TABLE; raise Malformed
    otherwise."""
    items = _list(table, key, where)
    if not all(isinstance(item, dict) for item in items):
        raise Malformed(f"{where}{key}: not a list of tables")
    return items


def _is_integer(value: Any) -> bool:
    """Whether VALUE is a JSON integer, which a boolean is not."""
    return isinstance(value, int) and not isinstance(value, bool)


def _keys(items: list[Any], where: str) -> list[str]:
    """Return ITEMS, substance keys of one role of an entry; raise
    Malformed when one is not a non-empty string or occurs twice."""
    if not all(isinstance(item, str) and item for item in items):
        raise Malformed(f"{where}: not a list of keys")
    if len(set(items)) != len(items):
        raise Malformed(f"{where}: a key occurs twice")
    return items


def _authors(table: dict[str, Any], where: str) -> list[str]:
    """Return the ``authors`` of the procedure TABLE, user names in file
    order; raise Malformed when they are not a list of non-empty strings
    or one occurs twice."""
    found = _list(table, "authors", where)
    if not all(isinstance(item, str) and item for item in found):
        raise Malformed(f"{where}authors: not a list of user names")
    if len(set(found)) != len(found):
        raise Malformed(f"{where}authors: a user name occurs twice")
    return found


def _entry(table: dict[str, Any], where: str) -> dict[str, Any]:
    """Return the scope entry TABLE as the manifest gives it, a table of
    ``substrates``, keys, and ``products``, tables of ``compound`` and
    ``yield_percent``; raise Malformed when it has another shape."""
    substrates = _keys(_list(table, "substrates", where),
                       f"{where}substrates")
    products = []
    for product in _tables(table, "products", where):
        value = product.get("yield_percent", None)
        # The range is compared first: it refuses NaN and the
        # infinities, and an integer too large for a float, without
        # converting it.
        if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 100):
            raise Malformed(f"{where}products: yield_percent is not a "
                            "number from 0 to 100")
        products.append({"compound": product.get("compound"),
                         "yield_percent": value})
    _keys([product["compound"] for product in products],
          f"{where}products")
    return {"substrates": substrates, "products": products}


def _procedure(table: dict[str, Any], number: int) -> dict[str, Any]:
    """Return the procedure TABLE, the manifest's NUMBERth, with its
    entries read; raise Malformed when it has another shape."""
    where = f"procedures[{number}]."
    ident = _text(table, "id", where, KEY_LENGTH)
    where = f"procedure {ident}: "
    general = table.get("general")
    if not isinstance(general, bool):
        raise Malformed(f"{where}general: not true or false")
    entries = [_entry(entry, f"{where}entries[{index}].")
               for index, entry in enumerate(
                   _tables(table, "entries", where), start=1)]
    if not general and len(entries) > 1:
        raise Malformed(f"{where}entries: a specific procedure has one")
    return {"id": ident,
            "source": _choice(table, "source", Source.values, where),
            "title": _text(table, "title", where),
            "title_de": _optional_text(table, "title_de", where),
            "reaction_type": _text(table, "reaction_type", where),
            "general": general,
            "authors": _authors(table, where),
            "notebook": _optional_string(table, "notebook", where),
            "project": _optional_string(table, "project", where),
            "entries": entries}


def _sequence(table: dict[str, Any], number: int) -> dict[str, Any]:
    """Return the sequence TABLE, the manifest's NUMBERth, with its
    steps read; raise Malformed when it has another shape."""
    where = f"sequences[{number}]."
    ident = _text(table, "id", where, KEY_LENGTH)
    where = f"sequence {ident}: "
    steps = []
    for index, step in enumerate(_tables(table, "steps", where), start=1):
        entry = step.get("entry")
        if entry is not None and not _is_integer(entry):
            raise Malformed(f"{where}steps[{index}].entry: neither an "
                            "integer nor null")
        steps.append({"procedure": _text(step, "procedure",
                                         f"{where}steps[{index}]."),
                      "entry": entry})
    return {"id": ident,
            "title": _text(table, "title", where),
            "title_de": _optional_text(table, "title_de", where),
            "target": _text(table, "target", where),
            "steps": steps}


def read(body: Any) -> dict[str, Any]:
    """Return the manifest BODY, a parsed JSON value, with its values
    read: ``build`` as a UUID, ``committed_at`` as an aware datetime,
    ``errors`` of a failed build as a list of strings, and the
    procedures and sequences of a built one with their entries and
    steps, a procedure's ``notebook`` and ``project`` None for null.
    Keys the manifest does not define are left out.

    Raise Malformed, saying what is wrong, when BODY is not a table of
    the manifest's keys and types (collection-import "Manifest"), or
    when a product's yield is outside 0 to 100, a key occurs twice in
    one role of an entry, a user name twice among a procedure's
    authors, an error is blank, a procedure that is not general has
    more than one entry, or ``deleted`` holds an item that is not a
    procedure or sequence ID.
    """
    if not isinstance(body, dict):
        raise Malformed("the manifest is not a table")
    if not _is_integer(body.get("format")) or body["format"] != FORMAT:
        raise Malformed(f"format: not {FORMAT}")
    try:
        build = uuid.UUID(_text(body, "build", ""))
    except ValueError:
        raise Malformed("build: not a UUID") from None
    try:
        committed_at = datetime.fromisoformat(
            _text(body, "committed_at", ""))
    except ValueError:
        raise Malformed("committed_at: not an ISO 8601 date and time") \
            from None
    if committed_at.utcoffset() is None:
        raise Malformed("committed_at: no offset")
    base = body.get("base", ...)
    if base is not None and not _is_integer(base):
        raise Malformed("base: neither an import's id nor null")
    manifest = {
        "build": build,
        "commit": _pattern(body, "commit", COMMIT_RE,
                           "40 lower-case hexadecimal digits"),
        "committed_at": committed_at,
        "base": base,
        "snapshot": _pattern(body, "snapshot", DIGEST_RE,
                             "64 lower-case hexadecimal digits"),
        "tooling": _pattern(body, "tooling", COMMIT_RE,
                            "40 lower-case hexadecimal digits"),
        "trigger": _choice(body, "trigger", Trigger.values),
        "outcome": _choice(body, "outcome", ("built", "refused")),
    }
    if manifest["outcome"] == "refused":
        errors = _list(body, "errors")
        if not errors:
            raise Malformed("errors: empty")
        if not all(isinstance(error, str) and error.strip()
                   for error in errors):
            raise Malformed("errors: not a list of non-blank strings")
        return {**manifest, "errors": errors}
    deleted = _list(body, "deleted")
    if not all(issuing.is_id(item) for item in deleted):
        raise Malformed("deleted: not a list of procedure and sequence IDs")
    return {
        **manifest,
        "deleted": deleted,
        "release": _text(body, "release", "", RELEASE_LENGTH),
        "language": _choice(body, "language", Language.values),
        "procedures": [_procedure(table, number) for number, table
                       in enumerate(_tables(body, "procedures"), start=1)],
        "sequences": [_sequence(table, number) for number, table
                      in enumerate(_tables(body, "sequences"), start=1)],
    }


# --- checking ---------------------------------------------------------------


def _entry_keys(entry: dict[str, Any]) -> list[str]:
    """Return the substance keys of ENTRY, substrates first, in order."""
    return [*entry["substrates"],
            *(product["compound"] for product in entry["products"])]


def _entry_signature(entry: dict[str, Any]) -> str:
    """Return the signature of the read scope entry ENTRY."""
    return signature(entry["substrates"],
                     [product["compound"] for product in entry["products"]])


def _journal_problems(ident: str, notebook: str | None,
                      notebooks: set[str],
                      holders: dict[str, list[str]]) -> list[str]:
    """Return the errors of NOTEBOOK, the ``notebook`` of the procedure
    IDENT, against the application's notebook codes NOTEBOOKS: a value
    that is not ``<code>/<number>``, a code no notebook has, or an
    entry that another procedure names too, HOLDERS mapping each entry
    to the IDs of the procedures that name it. None draws no error."""
    if notebook is None:
        return []
    match = ENTRY_RE.match(notebook)
    if match is None:
        return [f'{ident}: notebook "{notebook}" is not <code>/<number>']
    if match[1] not in notebooks:
        return [f'{ident}: unknown notebook "{match[1]}"']
    others = [other for other in holders[notebook] if other != ident]
    if others:
        return [f"{ident}: notebook entry {notebook} is also named by "
                f"{', '.join(others)}"]
    return []


def problems(manifest: dict[str, Any], substances: set[str],
             reaction_types: set[str], projects: set[str],
             notebooks: set[str], accounts: set[str],
             issued: set[str]) -> list[str]:
    """Return the errors that refuse the read, built MANIFEST against a
    registry holding the substance keys SUBSTANCES, the reaction type
    keys REACTION_TYPES and the project keys PROJECTS, and an
    application whose notebooks have the codes NOTEBOOKS, whose accounts
    have the user names ACCOUNTS and that counts the IDs ISSUED as
    issued, in the order the checks find them: each procedure in the
    manifest's order, then each sequence. An empty list accepts it.

    Each error begins with the ID it concerns: an ID named twice among
    the procedures or the sequences, an ID not issued, an unknown
    reaction type, a ``notebook`` that is not ``<code>/<number>``, names
    an unknown notebook or an entry another procedure names, an unknown
    project, author, substance or target, two entries of one procedure
    with one signature, a procedure without an entry, and a step that
    names a procedure the manifest lacks or no entry of the one it names
    (collection-import "Import checks"). A second table of an ID named
    twice is not checked further.
    """
    errors: list[str] = []
    procedures: dict[str, dict[str, Any]] = {}
    for procedure in manifest["procedures"]:
        procedures.setdefault(procedure["id"], procedure)
    holders: dict[str, list[str]] = {}
    for ident, procedure in procedures.items():
        if procedure["notebook"] is not None:
            holders.setdefault(procedure["notebook"], []).append(ident)
    checked: set[str] = set()
    twice: set[str] = set()
    for procedure in manifest["procedures"]:
        ident = procedure["id"]
        if ident in checked:
            if ident not in twice:
                twice.add(ident)
                errors.append(f"{ident}: named twice")
            continue
        checked.add(ident)
        if ident not in issued:
            errors.append(f"{ident}: {NOT_ISSUED}")
        if procedure["reaction_type"] not in reaction_types:
            errors.append(f'{ident}: unknown reaction type '
                          f'"{procedure["reaction_type"]}"')
        errors += _journal_problems(ident, procedure["notebook"], notebooks,
                                    holders)
        if procedure["project"] is not None \
                and procedure["project"] not in projects:
            errors.append(f'{ident}: unknown project '
                          f'"{procedure["project"]}"')
        errors += [f'{ident}: unknown author "{name}"'
                   for name in procedure["authors"] if name not in accounts]
        unknown: list[str] = []
        for entry in procedure["entries"]:
            unknown += [key for key in _entry_keys(entry)
                        if key not in substances and key not in unknown]
        errors += [f'{ident}: unknown substance "{key}"' for key in unknown]
        first: dict[str, int] = {}
        for number, entry in enumerate(procedure["entries"], start=1):
            found = _entry_signature(entry)
            if found in first:
                errors.append(f"{ident}: entries {first[found]} and "
                              f"{number} have the signature {found}")
            else:
                first[found] = number
        if not procedure["entries"]:
            errors.append(f"{ident}: no entry")
    sequences: set[str] = set()
    for sequence in manifest["sequences"]:
        ident = sequence["id"]
        if ident in sequences:
            if ident not in twice:
                twice.add(ident)
                errors.append(f"{ident}: named twice")
            continue
        sequences.add(ident)
        if ident not in issued:
            errors.append(f"{ident}: {NOT_ISSUED}")
        if sequence["target"] not in substances:
            errors.append(f'{ident}: unknown target "{sequence["target"]}"')
        for number, step in enumerate(sequence["steps"], start=1):
            named = procedures.get(step["procedure"])
            if named is None:
                errors.append(f"{ident}: step {number} names "
                              f"{step['procedure']}, which is not in the "
                              "collection")
            elif not _resolves(step["entry"], named):
                errors.append(f"{ident}: step {number} names no entry of "
                              f"{step['procedure']}")
    return errors


def _resolves(entry: int | None, procedure: dict[str, Any]) -> bool:
    """Whether a step giving the entry number ENTRY names an entry of the
    read PROCEDURE: a number counting one of its entries from 1 for a
    general procedure, no number for a specific one."""
    if procedure["general"]:
        return entry is not None and 1 <= entry <= len(procedure["entries"])
    return entry is None


# --- applying ---------------------------------------------------------------


def _assign(row: Any, values: dict[str, Any]) -> bool:
    """Give ROW the field VALUES; return whether one of them changed."""
    changed = False
    for name, value in values.items():
        if getattr(row, name) != value:
            setattr(row, name, value)
            changed = True
    return changed


def _apply_substances(row: ScopeEntry, entry: dict[str, Any],
                      substances: dict[str, Substance]) -> bool:
    """Make the substance rows of the scope entry ROW those of the read
    ENTRY, in its order and with its yields, writing them again only
    when they differ; return whether they did. SUBSTANCES maps the
    registry's keys to its substances."""
    wanted = [(Role.SUBSTRATE.value, key, position, None)
              for position, key in enumerate(entry["substrates"], start=1)]
    wanted += [(Role.PRODUCT.value, product["compound"], position,
                product["yield_percent"])
               for position, product in enumerate(entry["products"],
                                                  start=1)]
    held = sorted(row.substances.values_list(
        "role", "substance__key", "position", "yield_percent"))
    if held == sorted(wanted):
        return False
    row.substances.all().delete()
    EntrySubstance.objects.bulk_create(
        EntrySubstance(entry=row, substance=substances[key], role=role,
                       position=position, yield_percent=value)
        for role, key, position, value in wanted)
    return True


def _apply_authors(row: Procedure, authors: list[str],
                   accounts: dict[str, Any]) -> bool:
    """Make the author rows of the procedure ROW the read AUTHORS, user
    names in order, writing them again only when they differ; return
    whether they did. ACCOUNTS maps user names to the accounts."""
    held = list(row.authors.order_by("position").values_list(
        "user__username", flat=True))
    if held == authors:
        return False
    row.authors.all().delete()
    ProcedureAuthor.objects.bulk_create(
        ProcedureAuthor(procedure=row, user=accounts[name],
                        position=position)
        for position, name in enumerate(authors, start=1))
    return True


def _apply_entries(row: Procedure, entries: list[dict[str, Any]],
                   substances: dict[str, Substance]
                   ) -> tuple[bool, list[ScopeEntry]]:
    """Make the scope entries of the procedure ROW those of the read
    ENTRIES: an entry is matched by its signature, takes its position
    and substances and is no longer withdrawn; an entry the rows lack is
    created, and one whose signature ENTRIES lack is withdrawn. Return
    whether anything changed, and the entry rows in the order of
    ENTRIES."""
    held = {entry.signature: entry for entry in row.entries.all()}
    changed = False
    found = []
    for position, entry in enumerate(entries, start=1):
        key = _entry_signature(entry)
        current = held.pop(key, None)
        if current is None:
            current = ScopeEntry.objects.create(
                procedure=row, signature=key, position=position)
            changed = True
        elif _assign(current, {"position": position, "withdrawn": False}):
            current.save()
            changed = True
        changed |= _apply_substances(current, entry, substances)
        found.append(current)
    for gone in held.values():
        if not gone.withdrawn:
            gone.withdrawn = True
            gone.save()
            changed = True
    return changed, found


def _release_journal_entries(manifest: dict[str, Any], record: Import,
                             held: dict[str, Procedure],
                             named: dict[str, JournalEntry | None]
                             ) -> None:
    """Free the journal entries the read MANIFEST, accepted as the
    import RECORD, passes on: withdraw the procedures of HELD, the rows
    by ID, that MANIFEST lacks, each keeping its entry, and clear the
    entry of each procedure of MANIFEST whose entry differs from the
    one NAMED gives it by ID. Afterwards no procedure that is not
    withdrawn names an entry that NAMED gives another one. A cleared
    entry is cleared in the database alone: the row of HELD still holds
    it, so that applying the manifest sees the change."""
    for key, row in held.items():
        if key not in named and not row.withdrawn:
            row.withdrawn = True
            row.last_import = record
            row.save()
    for key, entry in named.items():
        row = held.get(key)
        if row is not None and row.journal_entry_id is not None \
                and row.journal_entry_id != (None if entry is None
                                             else entry.pk):
            Procedure.objects.filter(pk=row.pk).update(journal_entry=None)


def _apply_procedures(manifest: dict[str, Any], record: Import,
                      substances: dict[str, Substance]
                      ) -> dict[str, list[ScopeEntry]]:
    """Make the procedure rows, with their authors, those of the read
    MANIFEST, accepted as the import RECORD, and withdraw those it
    lacks; return the entry rows of each of its procedures by ID, in the
    manifest's order.

    The journal entries the procedures name are created when they are
    new, and passed on (``_release_journal_entries``) before any
    procedure takes a new one or is brought back."""
    types = {term.key: term for term in ReactionType.objects.all()}
    projects = {term.key: term for term in Project.objects.all()}
    accounts = {user.username: user for user in
                get_user_model().objects.filter(username__in={
                    name for procedure in manifest["procedures"]
                    for name in procedure["authors"]})}
    held = {row.key: row for row in Procedure.objects.all()}
    named = {procedure["id"]: None if procedure["notebook"] is None
             else entry_for(procedure["notebook"])
             for procedure in manifest["procedures"]}
    _release_journal_entries(manifest, record, held, named)
    entries: dict[str, list[ScopeEntry]] = {}
    for procedure in manifest["procedures"]:
        values = {"source": procedure["source"],
                  "title": procedure["title"],
                  "title_de": procedure["title_de"],
                  "reaction_type": types[procedure["reaction_type"]],
                  "general": procedure["general"],
                  "journal_entry": named[procedure["id"]],
                  "project": None if procedure["project"] is None
                  else projects[procedure["project"]],
                  "withdrawn": False}
        row = held.pop(procedure["id"], None)
        if row is None:
            row = Procedure.objects.create(key=procedure["id"],
                                           last_import=record, **values)
            changed = False
        else:
            changed = _assign(row, values)
        credited = _apply_authors(row, procedure["authors"], accounts)
        moved, entries[row.key] = _apply_entries(
            row, procedure["entries"], substances)
        if changed or credited or moved:
            row.last_import = record
            row.save()
    return entries


def _apply_sequences(manifest: dict[str, Any], record: Import,
                     substances: dict[str, Substance],
                     entries: dict[str, list[ScopeEntry]]) -> None:
    """Make the sequence rows those of the read MANIFEST, accepted as
    the import RECORD, their steps naming the rows of ENTRIES, and
    withdraw those it lacks."""
    held = {row.key: row for row in Sequence.objects.all()}
    for sequence in manifest["sequences"]:
        values = {"title": sequence["title"],
                  "title_de": sequence["title_de"],
                  "target": substances[sequence["target"]],
                  "withdrawn": False}
        row = held.pop(sequence["id"], None)
        if row is None:
            row = Sequence(key=sequence["id"], **values)
            changed = True
        else:
            changed = _assign(row, values)
        steps = [entries[step["procedure"]][(step["entry"] or 1) - 1]
                 for step in sequence["steps"]]
        if row.pk is not None and [entry.pk for entry in steps] == list(
                row.steps.order_by("position").values_list("entry",
                                                           flat=True)):
            moved = False
        else:
            moved = True
        if changed or moved:
            row.last_import = record
            row.save()
        if moved:
            row.steps.all().delete()
            Step.objects.bulk_create(
                Step(sequence=row, position=position, entry=entry)
                for position, entry in enumerate(steps, start=1))
    for gone in held.values():
        if not gone.withdrawn:
            gone.withdrawn = True
            gone.last_import = record
            gone.save()


def apply(manifest: dict[str, Any], record: Import) -> None:
    """Make the imported rows match the read, checked MANIFEST, accepted
    as the import RECORD (collection-import "Applying an import").

    Procedures and sequences are matched by ID and scope entries within
    their procedure by signature; what the manifest lacks is withdrawn,
    never deleted; a procedure's authors are replaced when they differ,
    and its journal entry and project become those its ``notebook`` and
    ``project`` name, the entry created when it is new.
    A procedure or sequence that is created or whose values, authors,
    entries or steps change, withdrawal included, takes RECORD
    as its ``last_import``. The caller provides the transaction.
    """
    keys = {key for procedure in manifest["procedures"]
            for entry in procedure["entries"] for key in _entry_keys(entry)}
    keys |= {sequence["target"] for sequence in manifest["sequences"]}
    substances = {row.key: row for row in Substance.objects.filter(
        key__in=keys)}
    entries = _apply_procedures(manifest, record, substances)
    _apply_sequences(manifest, record, substances, entries)


# --- receiving --------------------------------------------------------------


def _answer(record: Import) -> tuple[int, dict[str, Any]]:
    """Return the status and the table that answer the import RECORD."""
    return 200, {"outcome": record.outcome, "import": record.pk}


def _record(manifest: dict[str, Any], base: Import | None,
            **fields: Any) -> Import:
    """Record the read MANIFEST, built after BASE, as an import with
    FIELDS."""
    return Import.objects.create(
        build=manifest["build"], commit=manifest["commit"],
        committed_at=manifest["committed_at"], base=base,
        snapshot=manifest["snapshot"], tooling=manifest["tooling"],
        trigger=manifest["trigger"], **fields)


def _adoptable(manifest: dict[str, Any]) -> list[str]:
    """Return the IDs the read, built MANIFEST names, each once: those
    of its procedures and sequences that are IDs of their kind, and its
    ``deleted``."""
    found = [procedure["id"] for procedure in manifest["procedures"]
             if issuing.is_id(procedure["id"], "procedure")]
    found += [sequence["id"] for sequence in manifest["sequences"]
              if issuing.is_id(sequence["id"], "sequence")]
    return list(dict.fromkeys([*found, *manifest["deleted"]]))


def receive(manifest: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Handle the read MANIFEST in one transaction holding the lock
    (``orgsyndb_web.lock``); return the status and the table to answer
    (collection-import "Accepting an import").

    A build already recorded is answered as before and changes nothing.
    A failed build is recorded as refused with its errors, one per line.
    A built manifest whose ``base`` is not the latest accepted import's
    id, or whose ``snapshot`` is not the current registry's digest, is
    stale: 409 with ``{"outcome": "stale"}``, recorded nowhere. One the
    checks refuse (``problems``) is recorded as refused with every
    error; any other is applied (``apply``) and recorded as accepted.
    While no import is accepted, the IDs the manifest names count as
    issued, and an accepted import adopts them; after that, an ID
    counts as issued only when it is. A recorded import is answered 200
    with its outcome and its id.
    """
    with transaction.atomic():
        lock.hold()
        known = Import.objects.filter(build=manifest["build"]).first()
        if known is not None:
            return _answer(known)
        latest = latest_accepted()
        if manifest["outcome"] == "refused":
            base = Import.objects.filter(
                pk=manifest["base"], outcome=Outcome.ACCEPTED).first()
            return _answer(_record(
                manifest, base, outcome=Outcome.REFUSED,
                errors="\n".join(manifest["errors"])))
        if manifest["base"] != (None if latest is None else latest.pk) \
                or manifest["snapshot"] != snapshot.build()["digest"]:
            return 409, {"outcome": "stale"}
        adopted = _adoptable(manifest) if latest is None else []
        named = [item["id"] for item in (*manifest["procedures"],
                                         *manifest["sequences"])]
        errors = problems(
            manifest,
            set(Substance.objects.values_list("key", flat=True)),
            set(ReactionType.objects.values_list("key", flat=True)),
            set(Project.objects.values_list("key", flat=True)),
            set(Notebook.objects.values_list("code", flat=True)),
            set(get_user_model().objects.values_list("username",
                                                      flat=True)),
            issuing.issued(named) | set(adopted))
        if errors:
            return _answer(_record(manifest, latest,
                                   outcome=Outcome.REFUSED,
                                   errors="\n".join(errors)))
        issuing.adopt(adopted)
        record = _record(manifest, latest, outcome=Outcome.ACCEPTED,
                         release=manifest["release"],
                         language=manifest["language"])
        apply(manifest, record)
        return _answer(record)
