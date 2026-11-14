"""The registry as one JSON document, the snapshot, and the reading of a
snapshot back into an empty registry.

A snapshot is a table of ``format``, ``1``; ``vocabularies``, a table
of the four vocabularies by their collection names, each a list of its
terms, a parent before the terms filed under it and siblings in key
order; ``substances``, ordered by key; ``accounts``, every account by
user name with its display name; ``notebooks``, every lab notebook by
code with its owner's user name; ``import``, the latest accepted
import of the collection or ``null``; and ``digest``, the SHA-256 of the
rest but ``import``. Empty text, a missing molar mass and a missing
article number are ``null``.
"""

import hashlib
import json
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from collection.models import latest_accepted
from inventory.models import Article
from journal.models import Notebook
from orgsyndb_web import lock
from registry.models import Substance, SubstanceClass
from vocabulary.models import (ChemicalClass, Group, Project, ReactionType,
                               Term, is_tree, tree_order)

FORMAT = 1
# The keys of a snapshot that its digest does not cover.
UNDIGESTED = ("digest", "import")
# The vocabularies by the names the snapshot and the collection give
# them, in the order the snapshot lists them.
VOCABULARIES: dict[str, type[Term]] = {
    "chemical-classes": ChemicalClass,
    "inventory-groups": Group,
    "projects": Project,
    "reaction-types": ReactionType,
}
SUBSTANCE_TEXTS = ("name", "name_de", "short_name", "formula", "smiles",
                   "cas", "note")


def _text(value: str) -> str | None:
    """Return VALUE, or None for empty text."""
    return value or None


def digest(table: dict[str, Any]) -> str:
    """Return the lowercase hexadecimal SHA-256 of TABLE without its
    ``digest`` and its ``import``, serialized with sorted keys, no
    spaces and ASCII escapes, encoded as UTF-8."""
    rest = {key: value for key, value in table.items()
            if key not in UNDIGESTED}
    return hashlib.sha256(json.dumps(
        rest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode("utf-8")).hexdigest()


def _term(term: Term, keys: dict[Any, str]) -> dict[str, Any]:
    """Return TERM as the snapshot lists it; KEYS maps the IDs of its
    vocabulary's terms to their keys."""
    entry = {"key": term.key, "label": term.label,
             "label_de": _text(term.label_de)}
    if is_tree(type(term)):
        entry["parent"] = keys.get(term.parent_id)
    return entry


def latest_import() -> dict[str, Any] | None:
    """Return the snapshot's table of the latest accepted import of the
    collection: its ``id``, ``build``, ``commit``, ``snapshot``,
    ``tooling``, ``release`` and ``language``; None when none was
    accepted."""
    record = latest_accepted()
    if record is None:
        return None
    return {"id": record.pk, "build": str(record.build),
            "commit": record.commit, "snapshot": record.snapshot,
            "tooling": record.tooling, "release": record.release,
            "language": record.language}


def accounts() -> list[dict[str, str]]:
    """Return every account, active or not, as a table of ``username``
    and ``name``, its display name, ordered by user name as Python
    orders strings."""
    return sorted(({"username": user.username, "name": user.display_name}
                   for user in get_user_model().objects.all()),
                  key=lambda account: account["username"])


def notebooks() -> list[dict[str, str]]:
    """Return every lab notebook as a table of ``code`` and ``user``,
    its owner's user name, ordered by code as Python orders strings."""
    return sorted(({"code": code, "user": username}
                   for code, username in Notebook.objects.values_list(
                       "code", "user__username")),
                  key=lambda notebook: notebook["code"])


def build() -> dict[str, Any]:
    """Return the registry as a table that ``json.dumps`` serializes:
    the format, the vocabularies, the substances, the accounts, the lab
    notebooks, the latest accepted import and the digest, which does not
    cover the import."""
    vocabularies = {}
    for name, model in VOCABULARIES.items():
        terms = list(model.objects.all())
        keys = {term.pk: term.key for term in terms}
        vocabularies[name] = [_term(term, keys)
                              for term, _depth in tree_order(terms)]
    classes: dict[int, list[str]] = {}
    for substance_id, key in SubstanceClass.objects.values_list(
            "substance_id", "chemical_class__key"):
        classes.setdefault(substance_id, []).append(key)
    numbers = dict(Article.objects.values_list("substance_id",
                                               "article_number"))
    substances = []
    for substance in Substance.objects.select_related("group").order_by(
            "key"):
        substances.append({
            "key": substance.key,
            **{name: _text(getattr(substance, name))
               for name in SUBSTANCE_TEXTS},
            "group": substance.group.key,
            "chemical_classes": sorted(classes.get(substance.pk, [])),
            "mw": None if substance.mw is None else float(substance.mw),
            "article_number": numbers.get(substance.pk)})
    table: dict[str, Any] = {"format": FORMAT,
                             "vocabularies": vocabularies,
                             "substances": substances,
                             "accounts": accounts(),
                             "notebooks": notebooks(),
                             "import": latest_import()}
    table["digest"] = digest(table)
    return table


class Broken(Exception):
    """A snapshot that cannot be loaded; the message names the record
    and the field."""


def is_empty() -> bool:
    """Whether the registry holds no substance and no term."""
    return not (Substance.objects.exists() or any(
        model.objects.exists() for model in VOCABULARIES.values()))


def _checked(record: Any, name: str, entry: dict[str, Any]) -> None:
    """Refuse RECORD, read from ENTRY and named NAME, when a field holds
    a value its form would refuse."""
    try:
        record.full_clean()
    except ValidationError as error:
        problems = "; ".join(
            f"{field} {entry.get(field)!r}: {' '.join(texts)}"
            for field, texts in error.message_dict.items())
        raise Broken(f"{name}: {problems}") from error


def _string(value: Any, name: str, field: str) -> str:
    """Return the text VALUE, empty for None; refuse any other type."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise Broken(f"{name}: {field} {value!r}: not text")
    return value


def _mass(value: Any, name: str) -> Decimal | None:
    """Return the molar mass VALUE, a number or None, as a decimal."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Broken(f"{name}: mw {value!r}: not a number")
    try:
        return Decimal(repr(value))
    except InvalidOperation as error:
        raise Broken(f"{name}: mw {value!r}: not a number") from error


def _entries(table: Any, name: str) -> list[dict[str, Any]]:
    """Return the list TABLE holds as entries, each a table."""
    if table is None:
        return []
    if not isinstance(table, list) or not all(
            isinstance(entry, dict) for entry in table):
        raise Broken(f"{name}: not a list of tables")
    return table


def _load_terms(name: str, model: type[Term], entries: list[dict[str, Any]],
                user: Any) -> int:
    """Create the terms ENTRIES of the vocabulary NAME, of MODEL, in
    their order, by USER; return their number."""
    created: dict[str, Term] = {}
    for entry in entries:
        key = entry.get("key")
        label = f"term {key!r} of {name}"
        term = model(key=_string(key, label, "key"),
                     label=_string(entry.get("label"), label, "label"),
                     label_de=_string(entry.get("label_de"), label,
                                      "label_de"))
        parent = entry.get("parent") if is_tree(model) else None
        if parent is not None:
            if parent not in created:
                raise Broken(f"{label}: parent {parent!r}: no earlier term "
                             f"of {name} has this key")
            term.parent = created[parent]
        _checked(term, label, entry)
        term._history_user = user
        term.save()
        created[term.key] = term
    return len(created)


def _load_substance(entry: dict[str, Any], groups: dict[str, Group],
                    classes: dict[str, ChemicalClass], user: Any) -> bool:
    """Create the substance ENTRY by USER, with its classes and, when it
    names an article number, its article; return whether it has one.
    GROUPS and CLASSES map the keys of the terms to them."""
    key = entry.get("key")
    label = f"substance {key!r}"
    substance = Substance(key=_string(key, label, "key"),
                          mw=_mass(entry.get("mw"), label),
                          **{field: _string(entry.get(field), label, field)
                             for field in SUBSTANCE_TEXTS})
    group = entry.get("group")
    if group not in groups:
        raise Broken(f"{label}: group {group!r}: no group has this key")
    substance.group = groups[group]
    chosen = entry.get("chemical_classes")
    if not isinstance(chosen, list) or not chosen:
        raise Broken(f"{label}: chemical_classes {chosen!r}: name at least "
                     "one class")
    for term in chosen:
        if term not in classes:
            raise Broken(f"{label}: chemical_classes {term!r}: no chemical "
                         "class has this key")
    _checked(substance, label, entry)
    substance._history_user = user
    substance.save()
    for term in sorted(set(chosen)):
        row = SubstanceClass(substance=substance,
                             chemical_class=classes[term])
        row._history_user = user
        row.save()
    number = entry.get("article_number")
    if number is None:
        return False
    number = _string(number, label, "article_number").strip()
    if not number:
        return False
    article = Article(substance=substance, article_number=number)
    _checked(article, label, entry)
    article._history_user = user
    article.save()
    return True


def load(table: Any, user: Any = None) -> tuple[int, int, int]:
    """Fill the empty registry from the snapshot TABLE, made by USER;
    return the numbers of terms, substances and articles written.

    The terms of each vocabulary are created in their order, a parent
    named before the terms filed under it, then the substances with
    their classes, and an article for each substance that names an
    article number; each gets a creation in its history, all in one
    transaction holding the lock (``orgsyndb_web.lock``), which wakes the
    builder once it commits (``orgsyndb_web.wake``). The digest, the
    import, the accounts and the notebooks are ignored, and no account or
    notebook is created; a vocabulary that is missing is empty.
    Raise Broken, writing nothing, when the registry holds a substance
    or a term, the format is not ``1``, a term or substance names a key
    that does not exist, or a value breaks a rule the forms check.
    """
    if not isinstance(table, dict):
        raise Broken("the snapshot is not a table")
    with transaction.atomic():
        lock.hold_covered()
        if not is_empty():
            raise Broken("the registry holds substances or terms; it is "
                         "filled only while it is empty")
        found = table.get("format")
        if type(found) is not int or found != FORMAT:
            raise Broken(f"format {found!r}: the format is {FORMAT}")
        vocabularies = table.get("vocabularies") or {}
        if not isinstance(vocabularies, dict):
            raise Broken("vocabularies: not a table")
        terms = sum(
            _load_terms(name, model, _entries(vocabularies.get(name), name),
                        user)
            for name, model in VOCABULARIES.items())
        groups = {term.key: term for term in Group.objects.all()}
        classes = {term.key: term for term in ChemicalClass.objects.all()}
        entries = _entries(table.get("substances"), "substances")
        articles = sum(_load_substance(entry, groups, classes, user)
                       for entry in entries)
    return terms, len(entries), articles


def ordered(terms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the snapshot entries TERMS, each a table of a ``key`` and
    an optional ``parent``, in the snapshot's order: a parent before the
    terms filed under it and those before its next sibling, siblings in
    key order; a term whose parent is not among TERMS stands at the
    top."""
    every = list(terms)
    known = {entry["key"] for entry in every}
    children: dict[Any, list[dict[str, Any]]] = {}
    for entry in every:
        parent = entry.get("parent")
        children.setdefault(parent if parent in known else None,
                            []).append(entry)
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(parent: Any) -> None:
        for entry in sorted(children.get(parent, []),
                            key=lambda each: each["key"]):
            if entry["key"] in seen:
                continue
            seen.add(entry["key"])
            found.append(entry)
            visit(entry["key"])

    visit(None)
    return found + [entry for entry in every if entry["key"] not in seen]
