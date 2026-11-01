"""The compound and procedure fields of a collection as the site writes
them (compound-fields "Field display", procedure-fields "Procedure field
data").

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
    tabs: bool = False


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


def read_fields(settings: Path, language: str,
                entity: str = "compound") -> list[Field]:
    """The fields of ``fields.<entity>`` that ``settings`` declares, in
    declared order, with their labels in ``language``."""
    data = tomllib.loads(settings.read_text(encoding="utf-8"))
    fields = []
    for entry in data.get("fields", {}).get(entity, []):
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
            ancestors, order, entry.get("tabs", False)))
    return fields


def read_procedure_fields(settings: Path, language: str) -> list[Field]:
    """The procedure fields ``settings`` declares, in declared order,
    with their labels in ``language``. ``column``, ``search`` and
    ``tabs`` are false."""
    return read_fields(settings, language, "procedure")


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
    written value. In the directory only the column fields count. A
    procedure's front matter serves as ``compound`` for its procedure
    fields, with ``page`` true."""
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


def tab_values(field: Field, registry: dict[str, dict[str, Any]]
               ) -> list[str]:
    """The top-level values of the tabs ``field`` that have a tab page
    (site-catalogue "Compound tabs"): those that some compound sets or
    that are an ancestor of a value some compound sets, in the field's
    order."""
    used = {v for compound in registry.values()
            for v in values_set(field, compound)}
    return [v for v in field.order if not field.ancestors[v] and v in used]


def tab_compounds(field: Field, registry: dict[str, dict[str, Any]],
                  value: str) -> dict[str, dict[str, Any]]:
    """The compounds on the tab page of ``value``: those that set it or a
    value filed under it in the tabs ``field``."""
    return {key: compound for key, compound in registry.items()
            if value in values_set(field, compound)}


def tab_facet_entries(field: Field, tabs: Field, value: str,
                      registry: dict[str, dict[str, Any]], locale: str
                      ) -> list[tuple[str, str, int | None]]:
    """The ``(value, label, depth)`` that the facet of ``field`` lists on
    the tab page of ``value`` of the tabs field ``tabs``: the values that
    some row of the page carries; on the tabs field's own facet, without
    the tab's value, and with the depth of a value filed under it one
    less."""
    entries = facet_entries(
        field, tab_compounds(tabs, registry, value), locale)
    if field.key != tabs.key:
        return entries
    return [(found, label,
             depth - 1 if value in field.ancestors[found] else depth)
            for found, label, depth in entries if found != value]


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


class ProcedureFieldsMixin:
    """Procedure-field helpers for a build case: the declarations of the
    sandbox collection and what the site shows of them."""

    sandbox: ps.Sandbox
    LOCALE: str

    def procedure_fields(self) -> list[Field]:
        """The procedure fields the sandbox collection declares, in the
        site's language."""
        return read_procedure_fields(
            self.sandbox.root / "orgsyndb.toml", self.LOCALE)

    def facet_fields(self) -> list[Field]:
        """The procedure fields declared with ``facet = true``, in
        declared order."""
        return [f for f in self.procedure_fields() if f.facet]

    def declared_pairs(self, data: dict[str, Any]
                       ) -> list[tuple[str, str]]:
        """The label and written value of each declared procedure field
        that the front matter ``data`` sets, in declared order."""
        return [(field.label, text) for field, text in shown(
            self.procedure_fields(), data, self.LOCALE, page=True)]
