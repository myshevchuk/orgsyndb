"""The registry fields and the procedure fields of a collection as the
site writes them (compound-fields "Registry fields" and "Field display",
procedure-fields "Procedure field data").

The registry fields are stated here from the specification, and the
procedure declarations are read straight from the collection's
``orgsyndb.toml`` and the vocabularies of its registry snapshot,
independently of ``tools/pipeline.py``, so that a site test does not
take its expectation from the code under test.
"""

import tomllib
import unittest
from pathlib import Path
from typing import Any, NamedTuple

import pipeline_support as ps
from pipeline_support import Node, Page

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
    # every value of the vocabulary, depth first, siblings in key order
    order: tuple[str, ...] = ()
    tabs: bool = False
    beside: bool = False


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
    """The values, each top-level value followed by the values filed
    under it, recursively, siblings in key order."""
    def below(parent: str | None) -> list[str]:
        found: list[str] = []
        for value in sorted(vocabulary):
            if vocabulary[value].get("parent") == parent:
                found.append(value)
                found.extend(below(value))
        return found
    return tuple(below(None))


def vocabulary_of(snapshot: dict[str, Any], name: str
                  ) -> dict[str, dict[str, Any]]:
    """The terms of the vocabulary ``name`` of a snapshot, by key, each
    a table of ``label`` and, those it has, ``label_de`` and
    ``parent``."""
    return {term["key"]: {key: value for key, value in term.items()
                          if key != "key" and value is not None}
            for term in snapshot["vocabularies"][name]}


def _choice(key: str, label: str, label_de: str, language: str,
            snapshot: dict[str, Any], vocabulary: str, **options: Any
            ) -> Field:
    terms = vocabulary_of(snapshot, vocabulary)
    return Field(
        key, "choice", label_de if language == "de" else label,
        options.get("column", False), None, options.get("multiple", False),
        _paths(terms, language), options.get("facet", False), False,
        _ancestors(terms), _order(terms), options.get("tabs", False), False)


def registry_fields(snapshot: dict[str, Any], language: str
                    ) -> list[Field]:
    """The four registry fields, in order, with their labels in
    ``language`` and the terms of the vocabularies of ``snapshot``
    (compound-fields "Registry fields")."""
    german = language == "de"
    return [
        Field("article_number", "text",
              "Artikelnr." if german else "Article no.", True, None, False,
              {}, search=True, beside=True),
        Field("short_name", "text", "Kurzname" if german else "Short name",
              False, None, False, {}, search=True, beside=True),
        _choice("chemical_class", "Chemical class", "Stoffklasse",
                language, snapshot, "chemical-classes", multiple=True,
                column=True, facet=True),
        _choice("group", "Group", "Gruppe", language, snapshot,
                "inventory-groups", facet=True, tabs=True),
    ]


def read_fields(settings: Path, snapshot: dict[str, Any], language: str,
                entity: str = "procedure") -> list[Field]:
    """The fields of ``fields.<entity>`` that ``settings`` declares, in
    declared order, with their labels in ``language`` and the
    vocabularies of ``snapshot``."""
    data = tomllib.loads(settings.read_text(encoding="utf-8"))
    fields = []
    for entry in data.get("fields", {}).get(entity, []):
        paths: dict[str, tuple[str, ...]] = {}
        ancestors: dict[str, tuple[str, ...]] = {}
        order: tuple[str, ...] = ()
        if entry["type"] == "choice":
            vocabulary = vocabulary_of(snapshot, entry["vocabulary"])
            paths = _paths(vocabulary, language)
            ancestors = _ancestors(vocabulary)
            order = _order(vocabulary)
        fields.append(Field(
            entry["key"], entry["type"], _label(entry, language),
            entry.get("column", False), entry.get("unit"),
            entry.get("multiple", False), paths,
            entry.get("facet", False), entry.get("search", False),
            ancestors, order, entry.get("tabs", False),
            entry.get("beside", False)))
    return fields


def read_procedure_fields(settings: Path, snapshot: dict[str, Any],
                          language: str) -> list[Field]:
    """The procedure fields ``settings`` declares, in declared order,
    with their labels in ``language``. ``column``, ``search`` and
    ``tabs`` are false."""
    return read_fields(settings, snapshot, language, "procedure")


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


def beside_note(fields: list[Field], compound: dict[str, Any],
                locale: str) -> str | None:
    """The text of the ``span.compound-beside`` that follows a link to
    ``compound`` (compound-fields "Values beside compound links"): the
    values of the ``beside`` fields it sets, each as a compound page
    writes it, in declared order, joined by ``, `` and put in
    parentheses; ``None`` when it sets none."""
    values = [text for field, text in shown(fields, compound, locale,
                                            page=True) if field.beside]
    return f"({', '.join(values)})" if values else None


def named(key: str, registry: dict[str, dict[str, Any]],
          fields: list[Field], locale: str) -> str:
    """How the text of a container reads where the compound ``key`` is
    linked: its shown name, a space and its note when it has one."""
    name = ps.shown_name(registry[key], locale)
    note = beside_note(fields, registry[key], locale)
    return name if note is None else f"{name} {note}"


def link_to(page: Page, scope: Node, key: str) -> Node:
    """The ``a.compound`` below ``scope`` that links the page of the
    compound ``key``."""
    (link,) = [node for node in scope.find_all("a", "compound")
               if page.resolve(node.attrs["href"]) == f"/compounds/{key}/"]
    return link


def after_link(link: Node) -> list[Node | str]:
    """The children of the parent of ``link`` that come after it."""
    siblings = link.parent.children
    return siblings[siblings.index(link) + 1:]


def check_beside_notes(case: unittest.TestCase, page: Page, scope: Node,
                       registry: dict[str, dict[str, Any]],
                       fields: list[Field], locale: str
                       ) -> list[str | None]:
    """Every ``a.compound`` below ``scope`` has the text of its
    compound's shown name; and it is followed, inside its parent, by
    one space and the note of ``beside_note`` as a
    ``span.compound-beside`` holding text only when its compound sets a
    ``beside`` field, and by no such span otherwise. Returns the note
    each link should have, ``None`` for none, in document order."""
    links = scope.find_all("a", "compound")
    notes: list[str | None] = []
    for link in links:
        key = page.resolve(link.attrs["href"]).removeprefix(
            "/compounds/").removesuffix("/")
        with case.subTest(page=page.url, compound=key):
            case.assertEqual(link.text(),
                             ps.shown_name(registry[key], locale))
            after = after_link(link)
            note = beside_note(fields, registry[key], locale)
            notes.append(note)
            if note is None:
                for node in after[:2]:
                    case.assertFalse(
                        isinstance(node, Node)
                        and node.has_class("compound-beside"),
                        "a note follows a link without one")
                continue
            case.assertGreaterEqual(len(after), 2, "no note follows")
            case.assertEqual(after[0], " ")
            span = after[1]
            case.assertIsInstance(span, Node)
            case.assertEqual(span.tag, "span")
            case.assertTrue(span.has_class("compound-beside"), span.classes)
            case.assertEqual(span.elements(), [])
            case.assertEqual(span.text(), note)
    return notes


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
             compound.get("formula"), compound.get("cas"),
             compound.get("smiles")]
    parts += [compound[field.key] for field in fields
              if field.type == "text" and field.search
              and field.key in compound]
    return " ".join(part for part in parts if part)


class ProcedureFieldsMixin:
    """Field helpers for a build case: the declarations of the sandbox
    collection and what the site shows of them, and the notes beside
    its compound links."""

    sandbox: ps.Sandbox
    LOCALE: str

    def compound_fields(self) -> list[Field]:
        """The four registry fields of the sandbox collection's
        registry, in the site's language."""
        return registry_fields(ps.read_snapshot(self.sandbox), self.LOCALE)

    def linked(self, key: str) -> str:
        """How the text of a container reads where the compound ``key``
        is linked in the sandbox build: see ``named``."""
        return named(key, ps.read_registry(self.sandbox),
                     self.compound_fields(), self.LOCALE)

    def check_notes(self, page: Page, scope: Node) -> list[str | None]:
        """Check the links below ``scope`` of ``page`` and their notes
        in the sandbox build: see ``check_beside_notes``."""
        assert isinstance(self, unittest.TestCase)
        return check_beside_notes(
            self, page, scope, ps.read_registry(self.sandbox),
            self.compound_fields(), self.LOCALE)

    def procedure_fields(self) -> list[Field]:
        """The procedure fields the sandbox collection declares, in the
        site's language."""
        return read_procedure_fields(
            self.sandbox.root / "orgsyndb.toml",
            ps.read_snapshot(self.sandbox), self.LOCALE)

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
