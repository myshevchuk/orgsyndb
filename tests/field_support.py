"""The compound fields of a collection as the site writes them
(compound-fields "Field display").

The declarations are read straight from the collection's
``orgsyndb.toml`` and its ``vocabularies/``, independently of
``tools/pipeline.py``, so that a site test does not take its expectation
from the code under test.
"""

import tomllib
from pathlib import Path
from typing import Any, NamedTuple

import pipeline_support as ps

BOOLEANS = {"en": ("Yes", "No"), "de": ("Ja", "Nein")}
PATH_SEPARATOR = " › "


class Field(NamedTuple):
    key: str
    type: str
    label: str
    column: bool
    unit: str | None
    multiple: bool
    paths: dict[str, tuple[str, ...]]   # value -> labels, outermost first


def _label(entry: dict[str, Any], language: str, key: str = "label"
           ) -> str:
    return entry.get(f"{key}_de", entry[key]) if language == "de" \
        else entry[key]


def _paths(vocabulary: dict[str, dict[str, Any]],
           language: str) -> dict[str, tuple[str, ...]]:
    paths = {}
    for value in vocabulary:
        chain, current = [], value
        while current is not None:
            chain.append(_label(vocabulary[current], language))
            current = vocabulary[current].get("parent")
        paths[value] = tuple(reversed(chain))
    return paths


def read_fields(settings: Path, language: str) -> list[Field]:
    """The compound fields ``settings`` declares, in declared order, with
    their labels in ``language``."""
    data = tomllib.loads(settings.read_text(encoding="utf-8"))
    fields = []
    for entry in data.get("fields", {}).get("compound", []):
        paths: dict[str, tuple[str, ...]] = {}
        if entry["type"] == "choice":
            vocabulary = tomllib.loads(
                (settings.parent / "vocabularies"
                 / f"{entry['vocabulary']}.toml").read_text(
                     encoding="utf-8"))
            paths = _paths(vocabulary, language)
        fields.append(Field(
            entry["key"], entry["type"], _label(entry, language),
            entry.get("column", False), entry.get("unit"),
            entry.get("multiple", False), paths))
    return fields


def value_text(field: Field, value: Any, locale: str, *,
               page: bool) -> str:
    """How the site writes ``value`` of ``field``: on a compound page
    when ``page`` is true, else in the compound directory."""
    if field.type == "text":
        return value
    if field.type == "number":
        text = ps.number_text(value, locale)
        return f"{text} {field.unit}" if field.unit else text
    if field.type == "boolean":
        return BOOLEANS[locale][0 if value else 1]
    values = value if field.multiple else [value]
    return ", ".join(
        PATH_SEPARATOR.join(field.paths[v]) if page else field.paths[v][-1]
        for v in values)


def shown(fields: list[Field], compound: dict[str, Any], locale: str, *,
          page: bool) -> list[tuple[Field, str]]:
    """The fields ``compound`` sets, in declared order, each with its
    written value. In the directory only the column fields count."""
    return [(field, value_text(field, compound[field.key], locale,
                               page=page))
            for field in fields
            if field.key in compound and (page or field.column)]
