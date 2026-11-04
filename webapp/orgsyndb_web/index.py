"""The collection index: what the published release says about the
collection's language, compounds, procedures and sequences.

The index is the JSON file ``orgsyndb index`` writes into each release;
the setting ``ORGSYNDB_INDEX`` names it. It is read again whenever the
path it resolves to or its modification time changes. A file that is
missing, unreadable or malformed reads as an empty index: German, with
no compounds, procedures or sequences.
"""

import json
import logging
import os
import re
import threading
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings

LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "de"
LANGUAGE_CODE = re.compile(r"\.([a-z]{2})\.(md|org|pdf)$")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Compound:
    """A compound of the collection.

    KEY is its file name without the suffix; NAME is ``name_de`` on a
    German site when the compound has one, else ``name``; MW is its
    molecular weight, or None when the compound gives no number; and
    IDENTIFIERS are the key followed by the values of the compound's
    unique text fields.
    """

    key: str
    name: str
    mw: float | None
    identifiers: tuple[str, ...]


@dataclass(frozen=True)
class Sequence:
    """A synthesis sequence: its ID and its steps' procedure IDs, in
    order."""

    id: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class Index:
    """A read collection index.

    LANGUAGE is the site's, ``de`` or ``en``. COMPOUNDS maps keys to
    compounds; VALUES maps each unique text value to the key of the one
    compound holding it, or to None when several compounds hold it.
    PROCEDURES holds the procedure IDs and SEQUENCES maps sequence IDs
    to sequences.
    """

    language: str = DEFAULT_LANGUAGE
    compounds: dict[str, Compound] = field(default_factory=dict)
    values: dict[str, str | None] = field(default_factory=dict)
    procedures: frozenset[str] = frozenset()
    sequences: dict[str, Sequence] = field(default_factory=dict)


EMPTY = Index()

_lock = threading.Lock()
_cached: tuple[tuple[Any, ...], Index] | None = None


def _language_of(entry: dict[str, Any]) -> str | None:
    path = entry.get("path")
    if isinstance(path, str):
        match = LANGUAGE_CODE.search(Path(path).name)
        return match.group(1) if match else None
    language = entry.get("language")
    return language if isinstance(language, str) else None


def _entries(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    entries = data.get(key)
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _unique_text_fields(data: dict[str, Any]) -> list[str]:
    fields = data.get("fields")
    declared = fields.get("compound") if isinstance(fields, dict) else None
    if not isinstance(declared, list):
        return []
    return [item["key"] for item in declared
            if isinstance(item, dict) and isinstance(item.get("key"), str)
            and item.get("type") == "text" and item.get("unique") is True]


def _compounds(data: dict[str, Any], language: str
               ) -> tuple[dict[str, Compound], dict[str, str | None]]:
    unique = _unique_text_fields(data)
    compounds: dict[str, Compound] = {}
    holders: dict[str, set[str]] = {}
    for entry in _entries(data, "compounds"):
        key, values = entry.get("key"), entry.get("data")
        if not isinstance(key, str) or not isinstance(values, dict):
            continue
        name = values.get("name")
        if language == "de" and isinstance(values.get("name_de"), str):
            name = values["name_de"]
        mw = values.get("mw")
        texts = [values[f] for f in unique if isinstance(values.get(f), str)]
        compounds[key] = Compound(
            key=key, name=name if isinstance(name, str) else key,
            mw=(float(mw) if isinstance(mw, (int, float))
                and not isinstance(mw, bool) else None),
            identifiers=tuple(dict.fromkeys([key, *texts])))
        for text in texts:
            holders.setdefault(text, set()).add(key)
    values_to_keys = {text: (next(iter(keys)) if len(keys) == 1 else None)
                      for text, keys in holders.items()}
    return compounds, values_to_keys


def _rank(entry: dict[str, Any], language: str) -> tuple[int, str]:
    code = _language_of(entry)
    path = str(entry.get("path", ""))
    if code == language:
        return (0, path)
    if code is None:
        return (1, path)
    order = LANGUAGES.index(code) if code in LANGUAGES else len(LANGUAGES)
    return (2 + order, path)


def _sequences(entries: Iterable[dict[str, Any]], language: str
               ) -> dict[str, Sequence]:
    variants: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        ident = entry.get("id")
        if isinstance(ident, str) and isinstance(
                entry.get("front_matter"), dict):
            variants.setdefault(ident, []).append(entry)
    sequences = {}
    for ident, found in variants.items():
        chosen = min(found, key=lambda entry: _rank(entry, language))
        steps = chosen["front_matter"].get("steps")
        sequences[ident] = Sequence(id=ident, steps=tuple(
            step["procedure"] for step in
            (steps if isinstance(steps, list) else [])
            if isinstance(step, dict)
            and isinstance(step.get("procedure"), str)))
    return sequences


def parse(data: Any) -> Index:
    """Return the Index that DATA, the decoded output of ``orgsyndb
    index``, describes.

    A key that is missing or of the wrong type counts as no data; DATA
    that is not a table gives the empty index. A sequence's steps come
    from the variant the site publishes: the file in the site's
    language, else the one without a language code, else one in another
    language.
    """
    if not isinstance(data, dict):
        return EMPTY
    language = data.get("site_language")
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE
    compounds, values = _compounds(data, language)
    return Index(
        language=language, compounds=compounds, values=values,
        procedures=frozenset(
            entry["id"] for entry in _entries(data, "procedures")
            if isinstance(entry.get("id"), str)),
        sequences=_sequences(_entries(data, "sequences"), language))


def _read(path: str) -> Index:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("cannot read the collection index %s: %s", path, exc)
        return EMPTY
    try:
        data = json.loads(text)
    except ValueError as exc:
        logger.warning("the collection index %s is not JSON: %s", path, exc)
        return EMPTY
    if not isinstance(data, dict):
        logger.warning("the collection index %s holds no table", path)
        return EMPTY
    return parse(data)


def current() -> Index:
    """Return the collection index at the path ``ORGSYNDB_INDEX`` names.

    The file is read again when the setting, the path the file resolves
    to or its modification time changes, and the Index read last is
    returned otherwise. A missing, unreadable or malformed file gives
    the empty index and logs a warning once for each change of the
    file.
    """
    global _cached
    path = str(settings.ORGSYNDB_INDEX)
    try:
        stat = os.stat(path)
        key: tuple[Any, ...] = (path, os.path.realpath(path),
                                stat.st_mtime_ns, stat.st_size)
    except OSError:
        key = (path, None)
    with _lock:
        if _cached is not None and _cached[0] == key:
            return _cached[1]
        if key[1] is None:
            logger.warning("the collection index %s does not exist", path)
            found = EMPTY
        else:
            found = _read(path)
        _cached = (key, found)
        return found


def compound_for(token: str) -> Compound | None:
    """Return the compound TOKEN names, or None.

    TOKEN names a compound by its key, which wins over any other match,
    or by a value of one of its unique text fields. A value that several
    compounds hold names none of them.
    """
    found = current()
    if token in found.compounds:
        return found.compounds[token]
    key = found.values.get(token)
    return None if key is None else found.compounds[key]


def procedure_for(token: str) -> str | None:
    """Return TOKEN when the index lists a procedure of that ID, else
    None."""
    return token if token in current().procedures else None


def sequence_for(token: str) -> Sequence | None:
    """Return the synthesis sequence of the ID TOKEN, or None when the
    index lists none."""
    return current().sequences.get(token)
