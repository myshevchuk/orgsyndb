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
    facet: bool = False
    search: bool = False
    # value -> keys of its ancestors, outermost first
    ancestors: dict[str, tuple[str, ...]] = {}
    # every value of the vocabulary, depth first, children in file order
    order: tuple[str, ...] = ()


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


def _ancestors(vocabulary: dict[str, dict[str, Any]]
               ) -> dict[str, tuple[str, ...]]:
    found = {}
    for value in vocabulary:
        chain, current = [], vocabulary[value].get("parent")
        while current is not None:
            chain.append(current)
            current = vocabulary[current].get("parent")
        found[value] = tuple(reversed(chain))
    return found


def _order(vocabulary: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    """The values, each top-level value in file order followed by the
    values filed under it, in file order, recursively."""
    def below(parent: str | None) -> list[str]:
        found: list[str] = []
        for value, entry in vocabulary.items():
            if entry.get("parent") == parent:
                found.append(value)
                found.extend(below(value))
        return found
    return tuple(below(None))


def read_fields(settings: Path, language: str) -> list[Field]:
    """The compound fields ``settings`` declares, in declared order, with
    their labels in ``language``."""
    data = tomllib.loads(settings.read_text(encoding="utf-8"))
    fields = []
    for entry in data.get("fields", {}).get("compound", []):
        paths: dict[str, tuple[str, ...]] = {}
        ancestors: dict[str, tuple[str, ...]] = {}
        order: tuple[str, ...] = ()
        if entry["type"] == "choice":
            vocabulary = tomllib.loads(
                (settings.parent / "vocabularies"
                 / f"{entry['vocabulary']}.toml").read_text(
                     encoding="utf-8"))
            paths = _paths(vocabulary, language)
            ancestors = _ancestors(vocabulary)
            order = _order(vocabulary)
        fields.append(Field(
            entry["key"], entry["type"], _label(entry, language),
            entry.get("column", False), entry.get("unit"),
            entry.get("multiple", False), paths,
            entry.get("facet", False), entry.get("search", False),
            ancestors, order))
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


def values_set(field: Field, compound: dict[str, Any]) -> list[str]:
    """The machine values of ``field`` that ``compound`` sets, as a
    row's facet attribute lists them (site-catalogue "Compound
    catalogue"): for a
    boolean ``"true"`` or ``"false"``, for a choice each value set and
    each ancestor of one, each once; none when the field is unset."""
    if field.key not in compound:
        return []
    value = compound[field.key]
    if field.type == "boolean":
        return ["true" if value else "false"]
    chosen = value if field.multiple else [value]
    return list(dict.fromkeys(
        found for v in chosen for found in (v, *field.ancestors[v])))


def facet_entries(field: Field, registry: dict[str, dict[str, Any]],
                  locale: str) -> list[tuple[str, str, int | None]]:
    """The ``(value, label, depth)`` that the facet of ``field`` lists,
    in order. The depth is the number of the value's ancestors for a
    choice field and ``None`` for a boolean one."""
    used = {v for compound in registry.values()
            for v in values_set(field, compound)}
    if field.type == "boolean":
        yes, no = BOOLEANS[locale]
        return [(value, label, None) for value, label in
                (("true", yes), ("false", no)) if value in used]
    return [(value, field.paths[value][-1], len(field.ancestors[value]))
            for value in field.order if value in used]


def search_text(fields: list[Field], compound: dict[str, Any]) -> str:
    """The text the compound catalogue searches for ``compound``: its
    names, formula, CAS number, SMILES and the values of its searchable
    text fields, joined by single spaces."""
    parts = [compound["name"], compound.get("name_de"),
             compound["formula"], compound.get("cas"), compound["smiles"]]
    parts += [compound[field.key] for field in fields
              if field.type == "text" and field.search
              and field.key in compound]
    return " ".join(part for part in parts if part)
