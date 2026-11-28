"""Fixtures and helpers shared by the tests of the main lists (web-app:
Main lists).

The table ``MAIN_LISTS`` states each of the ten lists as that requirement
does: its path, its columns by key, its default order, its details
endpoint and its view cookie. Nothing here imports Django.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlsplit

from . import Element

HTMX = {"HTTP_HX_REQUEST": "true"}
LAB = "/lab/"


@dataclass(frozen=True)
class MainList:
    """A main list as the requirement "Main lists" states it.

    KEYS are its columns in the order of the table; UNSORTED the keys
    of those that do not sort; DEFAULT the key of the default column and
    DESCENDING whether it runs descending; COOKIE the name of the view
    cookie and OPENS the view the list opens in without one; DETAILS
    gives the path of the details of the record whose key is its
    argument; COUNT the id of the element that shows the list's count;
    STRONG the keys of the columns whose header and cells are bold, the
    column that names the record first; CAPPED the key of the column
    whose cells hold a name that the screen cuts and a ``title`` shows
    whole, empty for a list without one.
    """

    name: str
    path: str
    keys: tuple[str, ...]
    default: str
    cookie: str
    details: Callable[[str], str]
    count: str
    unsorted: frozenset[str] = frozenset()
    descending: bool = False
    opens: str = "table"
    searches: tuple[str, ...] = ("q",)
    strong: tuple[str, ...] = ()
    capped: str = ""

    @property
    def sorted_keys(self) -> list[str]:
        """The keys of the columns that sort."""
        return [key for key in self.keys if key not in self.unsorted]


def _under(prefix: str, suffix: str = "") -> Callable[[str], str]:
    return lambda key: f"{prefix}{key}/{suffix}"


MAIN_LISTS: dict[str, MainList] = {spec.name: spec for spec in (
    MainList(
        "item", "/lab/inventory/end-products/",
        ("number", "name", "category", "container", "stock", "mean_year",
         "this_year", "coverage", "compartment", "box", "bulk"),
        "category", "item-list-view",
        _under("/lab/inventory/items/", "detail/"), "item-count",
        strong=("name", "container"), capped="name"),
    MainList(
        "bulk", "/lab/inventory/end-products/bulk/",
        ("article", "vessel", "batch", "source", "amount", "location",
         "date", "fills"),
        "article", "bulk-list-view",
        _under("/lab/inventory/end-products/bulk/"), "bulk-count",
        unsorted=frozenset({"fills"}), strong=("article", "amount"),
        capped="article"),
    MainList(
        "delivery", "/lab/inventory/deliveries/",
        ("number", "date", "recipient", "lines"),
        "date", "delivery-list-view",
        _under("/lab/inventory/deliveries/", "detail/"), "note-count",
        descending=True, strong=("number", "recipient")),
    MainList(
        "intermediate", "/lab/inventory/intermediates/",
        ("substance", "amount", "vessels", "location", "source", "age"),
        "substance", "intermediate-list-view",
        _under("/lab/inventory/intermediates/"), "category-count",
        strong=("substance", "amount"), capped="substance"),
    MainList(
        "chemical", "/lab/inventory/chemicals/",
        ("substance", "group", "amount", "vessels", "location",
         "suppliers", "opened"),
        "substance", "chemical-list-view",
        _under("/lab/inventory/chemicals/"), "category-count",
        strong=("substance", "amount"), capped="substance"),
    MainList(
        "batch", "/lab/inventory/batches/",
        ("batch", "name", "article", "source", "notebook", "date",
         "yield", "stock"),
        "date", "batch-list-view",
        _under("/lab/inventory/batches/", "detail/"), "batch-count",
        descending=True, strong=("name", "stock"), capped="name"),
    MainList(
        "vessel", "/lab/inventory/vessels/",
        ("vessel", "name", "kind", "batch", "source", "amount", "location",
         "date"),
        "name", "vessel-list-view",
        _under("/lab/inventory/vessels/", "detail/"), "vessel-count",
        searches=(), strong=("name", "amount")),
    MainList(
        "planning", "/lab/planning/",
        ("article", "runway", "synthesis", "start", "priority", "tasks",
         "actions"),
        "start", "planning-list-view",
        lambda number: f"/lab/planning/{number}/detail/", "planning-count",
        unsorted=frozenset({"actions"}), opens="details", searches=(),
        strong=("article", "start"), capped="article"),
    MainList(
        "task", "/lab/tasks/",
        ("number", "product", "priority", "assignee", "started", "ended",
         "progress", "batch", "report", "qc", "state"),
        "priority", "task-list-view",
        _under("/lab/tasks/", "detail/"), "task-counts",
        strong=("product", "priority"), capped="product"),
    MainList(
        "substance", "/lab/registry/",
        ("name", "key", "short_name", "group", "classes", "formula",
         "molar_mass", "article"),
        "name", "substance-list-view",
        _under("/lab/registry/substances/", "detail/"),
        "substance-count", strong=("name", "article"), capped="name"),
)}

BY_PATH = {spec.path: spec for spec in MAIN_LISTS.values()}


def main_tables(root: Element) -> list[Element]:
    """Every table of the page that carries the class ``main-table``."""
    return root.find_all("table", cls="main-table")


def main_table(root: Element) -> Element:
    """The one table of the page that carries ``main-table``."""
    found = main_tables(root)
    assert len(found) == 1, f"{len(found)} tables carry main-table"
    return found[0]


def head_cells(root: Element) -> list[Element]:
    """The header cells of the main table, in the row of ``#item-head``,
    which is the table's ``thead`` or a row in it."""
    head = root.find(id="item-head")
    assert head is not None, "the page has no #item-head"
    return head.find_all("th")


def body_rows(root: Element) -> list[Element]:
    """The rows of ``#item-rows`` that carry ``data-item``."""
    body = root.find(id="item-rows")
    assert body is not None, "the page has no #item-rows"
    return [tr for tr in body.find_all("tr") if "data-item" in tr.attrs]


def row_keys(root: Element) -> list[str]:
    """The ``data-item`` of every record row, in page order."""
    return [tr.get("data-item") for tr in body_rows(root)]


def pane(root: Element) -> Element | None:
    """The details pane ``#item-detail`` of the page or of a fragment."""
    return root.find(id="item-detail")


def marked(root: Element) -> list[str]:
    """The ``data-item`` of every row that carries ``aria-current``."""
    return [tr.get("data-item") for tr in body_rows(root)
            if tr.get("aria-current") == "true"]


def aria_sorts(root: Element) -> list[str | None]:
    """The ``aria-sort`` of every header cell of the main table."""
    return [th.get("aria-sort") for th in head_cells(root)]


def query_of(href: str) -> dict[str, list[str]]:
    """The query of HREF as a mapping of lists, keeping blanks."""
    found: dict[str, list[str]] = {}
    for name, value in parse_qsl(urlsplit(href).query,
                                 keep_blank_values=True):
        found.setdefault(name, []).append(value)
    return found


def path_of(href: str) -> str:
    """The decoded path of HREF."""
    return unquote(urlsplit(href).path)


def encoded(number: str) -> str:
    """NUMBER as one path segment, as a planning row's ``hx-get`` has
    it."""
    return quote(number, safe="")


def hidden_fields(root: Element) -> dict[str, str]:
    """The hidden fields of the page's filter form ``#filters`` by name,
    the last of a name winning."""
    form = root.find("form", id="filters")
    assert form is not None, "the page has no form #filters"
    return {found.get("name"): found.get("value")
            for found in form.find_all("input", type="hidden")}



def cells(row: Element) -> list[Element]:
    """The cells of ROW."""
    return [cell for cell in row.children
            if isinstance(cell, Element) and cell.tag in ("td", "th")]



def texts_of_links(scope: Element) -> dict[str, str]:
    """The addresses of the links in SCOPE by their text; of two links
    with one text, the first."""
    found: dict[str, str] = {}
    for link in scope.find_all("a"):
        found.setdefault(link.text(), link.get("href", ""))
    return found



def headers_of(grid: Element) -> list[str]:
    """The header texts of the table GRID, from its first row, without
    the notes in ``small``."""
    row = next(tr for tr in grid.find_all("tr")
               if tr.closest("table") is grid)
    return [cell.text(lambda node: node.tag == "small")
            for cell in row.find_all(("th", "td"))
            if cell.closest("tr") is row]


def body_of(grid: Element) -> list[Element]:
    """The rows of the table GRID outside its ``thead`` that hold a
    ``td``."""
    return [tr for tr in grid.find_all("tr")
            if tr.closest("table") is grid
            and tr.closest("thead") is None
            and any(isinstance(c, Element) and c.tag == "td"
                    for c in tr.children)]


def is_sortable(grid: Element) -> bool:
    """Whether GRID is marked ``data-sortable``, binds the script's
    sorting to itself and carries an ``id``."""
    return ("data-sortable" in grid.attrs
            and "sortable-table" in (grid.get("data-controller")
                                     or "").split()
            and bool(grid.get("id")))


def lists_records(grid: Element) -> bool:
    """Whether the table GRID lists records one per row: it is neither a
    key-value table, nor a consumption table, whose rows are headed by
    row headers, nor a change history, whose rows of one save share
    cells."""
    return not ("kv-table" in grid.classes
                or grid.find("th", attrs={"scope": "row"}) is not None
                or grid.find(("td", "th"), attrs={"rowspan": True})
                is not None
                or in_history(grid))


def in_history(grid: Element) -> bool:
    """Whether the table GRID is the table of a change history widget,
    titled ``Änderungen`` or ``History``."""
    node = grid.parent
    while node is not None:
        if "widget" in node.classes:
            head = node.find(cls="widget__head")
            title = head.find("h2") if head is not None else None
            return title is not None and any(
                name in title.text() for name in ("Änderungen", "History"))
        node = node.parent
    return False


def unsorted_reasons(scope: Element) -> list[str]:
    """What keeps each table in SCOPE that lists records one per row from
    being client-sortable (web-app: Widgets), as a message each; empty
    when every such table is sortable, an auxiliary table and unique by
    its ``id``."""
    found = []
    ids: dict[str, int] = {}
    for grid in scope.find_all("table"):
        if grid.get("id"):
            ids[grid.get("id")] = ids.get(grid.get("id"), 0) + 1
    for grid in scope.find_all("table"):
        if not lists_records(grid):
            continue
        name = grid.get("id") or "<no id>"
        if "aux-table" not in grid.classes:
            found.append(f"{name}: not an aux-table")
        if not is_sortable(grid):
            found.append(f"{name}: not sortable")
        if ids.get(grid.get("id"), 0) > 1:
            found.append(f"{name}: id not unique")
    return found


def must_pane(root: Element) -> Element:
    """The details pane ``#item-detail`` of the page or fragment ROOT;
    fail when it holds none."""
    found = root.find(id="item-detail")
    assert found is not None, "the page has no #item-detail"
    return found


def heading_of(scope: Element) -> Element:
    """The first heading of SCOPE, an ``h2`` or ``h3``; fail when it
    holds none."""
    found = scope.find(("h2", "h3"))
    assert found is not None, "the pane has no heading"
    return found


def link_in(scope: Element) -> Element:
    """The first link in SCOPE; fail when it holds none."""
    found = scope.find("a")
    assert found is not None, f"{scope.text()!r} holds no link"
    return found


def row_for(root: Element, key: str) -> Element:
    """The row of ``#item-rows`` whose ``data-item`` is KEY; fail when
    there is none."""
    found = [tr for tr in body_rows(root) if tr.get("data-item") == key]
    assert len(found) == 1, f"{len(found)} rows hold the record {key}"
    return found[0]


def replaced(case: Any, response: Any) -> str:
    """The ``HX-Replace-Url`` of RESPONSE, which must be a success that
    sets it."""
    case.assertEqual(response.status_code, 200)
    case.assertIn("HX-Replace-Url", response)
    return response["HX-Replace-Url"]


def head_of(root: Element) -> Element:
    """The header ``#item-head`` of the page's main table; fail when it
    holds none."""
    found = root.find(id="item-head")
    assert found is not None, "the page has no #item-head"
    return found


def rows_of(root: Element) -> Element:
    """The body ``#item-rows`` of the page's main table; fail when it
    holds none."""
    found = root.find(id="item-rows")
    assert found is not None, "the page has no #item-rows"
    return found


def key_number(key: str | None) -> Decimal:
    """The number the sort key KEY holds; fail when the cell has no key
    or it is no number."""
    assert key not in (None, ""), "the cell has no sort key"
    assert re.fullmatch(r"-?\d+(?:[.,]\d+)?", key), f"{key!r} is no number"
    return Decimal(key.replace(",", "."))


PROJECTED_MARKS = ("hochgerechnet aus dem laufenden Jahr",
                   "projected from the current year")


def projected_marks(root: Element) -> list[str]:
    """What marks a figure of ROOT as projected: each element that
    carries the class ``projected`` or a ``title`` that explains the
    mark, and each of the mark's texts shown on the page, in either
    language. Empty when the page shows no such mark."""
    found = [f"<{node.tag}> {sorted(node.classes)}"
             for node in root.walk()
             if "projected" in node.classes
             or any(text in (node.get("title") or "")
                    for text in PROJECTED_MARKS)]
    found += [text for text in PROJECTED_MARKS if text in root.text()]
    return found


def stacked_controls(form: Element) -> list[str]:
    """The controls of the filter form FORM that are not inline: each
    select that is not in a ``label.lab-inline-select`` with its
    ``span.lab-field-prefix``, and each search field that is not in a
    ``label.lab-inline-field`` whose text sits in a
    ``span.visually-hidden``. Empty when every control is inline."""
    found = []
    for select in form.find_all("select"):
        label = select.parent
        if (label is None or label.tag != "label"
                or "lab-inline-select" not in label.classes
                or label.find("span", cls="lab-field-prefix") is None):
            found.append(f"select {select.get('name')}")
    for search in form.find_all("input", type="search"):
        label = search.parent
        if (label is None or label.tag != "label"
                or "lab-inline-field" not in label.classes
                or label.find("span", cls="visually-hidden") is None):
            found.append(f"search {search.get('name')}")
    return found


def strong_columns(root: Element) -> tuple[list[str], list[str]]:
    """The texts of the headers of the main table that carry
    ``col-strong``, and the texts of the headers of the columns whose
    cells in the body all carry it."""
    names = [th.text(lambda node: node.tag == "small")
             for th in head_cells(root)]
    rows = [cells(row) for row in body_rows(root)]
    heads = [name for name, th in zip(names, head_cells(root))
             if "col-strong" in th.classes]
    found = [name for index, name in enumerate(names)
             if rows and all("col-strong" in row[index].classes
                             for row in rows)]
    return heads, found
