"""The registry a collection directory holds, read as a snapshot: its
vocabularies from ``vocabularies/`` and its compounds from
``compounds/``."""

import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

from registry.snapshot import FORMAT, VOCABULARIES, Broken, digest, ordered
from vocabulary.models import is_tree

# The keys of a compound file the snapshot takes, by the snapshot's
# names for them; every other key is left out.
TAKEN = {"name": "name", "name_de": "name_de", "short_name": "short_name",
         "formula": "formula", "mw": "mw", "smiles": "smiles",
         "cas": "cas", "group": "group",
         "chemical_class": "chemical_classes",
         "item_number": "article_number"}


def _read(path: Path, shown: str) -> dict[str, Any]:
    """Return the table the TOML file PATH holds; raise Broken naming
    SHOWN, the file, when it cannot be read."""
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise Broken(f"{shown}: cannot be read: {error}") from error


def _text(value: Any) -> Any:
    """Return VALUE, or None for empty text."""
    return None if value == "" else value


def _vocabulary(collection: Path, name: str) -> list[dict[str, Any]]:
    """Return the terms of the vocabulary NAME of COLLECTION in the
    snapshot's order; a missing file gives none."""
    path = collection / "vocabularies" / f"{name}.toml"
    if not path.exists():
        return []
    shown = f"vocabularies/{name}.toml"
    terms = []
    for key, values in _read(path, shown).items():
        if not isinstance(values, dict):
            raise Broken(f"{shown}: {key} is not a table")
        entry = {"key": key, "label": values.get("label"),
                 "label_de": _text(values.get("label_de"))}
        if is_tree(VOCABULARIES[name]):
            entry["parent"] = _text(values.get("parent"))
        terms.append(entry)
    return ordered(terms)


def _compound(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Return the substance the compound file PATH describes and the
    keys of the file it leaves out; raise Broken naming the file when it
    cannot be read or lacks a group or a chemical class."""
    shown = f"compounds/{path.name}"
    data = _read(path, shown)
    if not data.get("group"):
        raise Broken(f"{shown}: the compound names no group")
    classes = data.get("chemical_class")
    if isinstance(classes, str):
        classes = [classes]
    if not classes:
        raise Broken(f"{shown}: the compound names no chemical class")
    entry: dict[str, Any] = {"key": path.stem}
    for key, name in TAKEN.items():
        entry[name] = _text(data.get(key))
    entry["chemical_classes"] = sorted(classes)
    return entry, sorted(key for key in data if key not in TAKEN)


def read(collection: Path) -> tuple[dict[str, Any], Counter[str]]:
    """Return the snapshot of the registry the directory COLLECTION
    holds, and how many compounds set each key it leaves out.

    Each vocabulary file names a term by each table, with its
    ``label``, ``label_de`` and ``parent``. Each compound file gives a
    substance of its name, by its declared fields ``short_name``,
    ``chemical_class``, ``group`` and ``item_number``, the article
    number, and its ``name``, ``name_de``, ``formula``, ``mw``,
    ``smiles`` and ``cas``. Raise Broken naming the file when one cannot
    be read, or when a compound lacks a group or a chemical class.
    """
    vocabularies = {name: _vocabulary(collection, name)
                    for name in VOCABULARIES}
    substances = []
    left: Counter[str] = Counter()
    for path in sorted((collection / "compounds").glob("*.toml"),
                       key=lambda each: each.stem):
        entry, others = _compound(path)
        substances.append(entry)
        left.update(others)
    table: dict[str, Any] = {"format": FORMAT,
                             "vocabularies": vocabularies,
                             "substances": substances}
    table["digest"] = digest(table)
    return table, left
