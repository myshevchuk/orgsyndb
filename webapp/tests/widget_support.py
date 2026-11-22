"""Helpers for pages that show their data in widgets (web-app: Widgets).

A widget is a ``section.widget`` or a ``details.widget`` whose title bar
(``.widget__head``, the ``summary`` of a ``details``) holds the title in
an ``h2`` and, where the page gives them, a count (``.widget__count``)
and a note (``.widget__note``). A key-value table is a
``table.kv-table`` with the key in a row's first cell and its value, in
which a ``.kv-sub`` line may name the basis, in the second.

Nothing here imports Django.
"""

import re
from dataclasses import dataclass
from typing import Any

from . import Element

HISTORY_TITLES = ("Änderungen", "History")
HISTORY_COLUMNS = 4
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
ISO_MOMENT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _is_aside(node: Element) -> bool:
    """Whether ``node`` is a count or a note of a title bar."""
    return bool(node.classes & {"widget__count", "widget__note"})


def widgets(root: Element) -> list[Element]:
    """Every element of the page that is a widget."""
    return root.find_all(cls="widget")


def title_of(found: Element) -> str | None:
    """The title in the ``h2`` of ``found``'s title bar, without its
    count and note; None when it has no such title."""
    head = found.find(cls="widget__head")
    heading = head.find("h2") if head is not None else None
    return None if heading is None else heading.text(_is_aside)


def widget(root: Element, *titles: str) -> Element:
    """The first widget of the page titled one of ``titles``; fail,
    naming the titles the page has, when there is none."""
    for found in widgets(root):
        if title_of(found) in titles:
            return found
    raise AssertionError(
        f"the page has no widget titled {titles}; its widgets are "
        f"{[title_of(w) for w in widgets(root)]}")


def count_of(found: Element) -> int | None:
    """The number in the count of ``found``'s title bar, None when the
    bar shows none."""
    head = found.find(cls="widget__head")
    shown = head.find(cls="widget__count") if head is not None else None
    if shown is None:
        return None
    numbers = re.findall(r"\d+", shown.text())
    assert len(numbers) == 1, f"the count reads {shown.text()!r}"
    return int(numbers[0])


def cells_of(row: Element) -> list[Element]:
    """The cells of the table row ``row``."""
    return [c for c in row.children
            if isinstance(c, Element) and c.tag in ("td", "th")]


def kv_rows(scope: Element) -> list[tuple[str, Element]]:
    """The key and the value cell of each row of each key-value table
    in ``scope``, in page order."""
    found = []
    own = [scope] if "kv-table" in scope.classes else []
    for grid in own + scope.find_all("table", cls="kv-table"):
        for row in grid.find_all("tr"):
            if row.closest("table") is not grid:
                continue
            cells = cells_of(row)
            if len(cells) >= 2:
                found.append((cells[0].text(), cells[1]))
    return found


def kv(scope: Element) -> dict[str, Element]:
    """The value cells of the key-value tables in ``scope`` by key."""
    return dict(kv_rows(scope))


def item_widget(root: Element) -> Element:
    """The widget of an item page that holds the item's data: the one
    whose key-value table has the key ``Fach`` or ``Compartment``."""
    for found in widgets(root):
        if {"Fach", "Compartment"} & set(kv(found)):
            return found
    raise AssertionError("the page has no widget of the item's data")


def grid(table: Element) -> tuple[list[str], list[dict[str, Element]]]:
    """The header texts of ``table``, from its first row, and its body
    rows, each as a mapping from header text to cell."""
    rows = [tr for tr in table.find_all("tr") if tr.closest("table") is table]
    header = [cell.text() for cell in cells_of(rows[0])]
    return header, [dict(zip(header, cells_of(tr))) for tr in rows[1:]
                    if tr.closest("thead") is None]


def widget_grid(found: Element
                ) -> tuple[list[str], list[dict[str, Element]]]:
    """The header texts and the body rows of the table of the widget
    ``found``, as ``grid`` gives them; fail when it holds none."""
    inside = found.find("table")
    assert inside is not None, f"the widget {title_of(found)!r} has no table"
    return grid(inside)


def body_rows(table: Element) -> list[Element]:
    """The rows of ``table`` outside its ``thead``."""
    return [tr for tr in table.find_all("tr")
            if tr.closest("table") is table and tr.closest("thead") is None
            and any(c.tag == "td" for c in cells_of(tr))]


@dataclass(frozen=True)
class Row:
    """A row of a history table as its four columns read, whether a
    column's cell is the row's own or spans down from an earlier row;
    STARTS is true when the row has a cell of its own in the first
    column."""

    time: str
    user: str
    subject: str
    change: str
    starts: bool

    @property
    def text(self) -> str:
        return " ".join(part for part in (
            self.time, self.user, self.subject, self.change) if part)


@dataclass(frozen=True)
class Entry:
    """An entry of a history: its time, user and subject, and the
    changes of its rows."""

    time: str
    user: str
    subject: str
    changes: list[str]

    @property
    def text(self) -> str:
        return " ".join(part for part in (
            self.time, self.user, self.subject, *self.changes) if part)


def history_widget(root: Element) -> Element:
    """The page's history widget."""
    return widget(root, *HISTORY_TITLES)


def history_rows(root: Element) -> list[Row]:
    """The body rows of the page's history table, newest first as the
    page has them, each read as its four columns: time, user, subject
    and change. Fail when a row does not fill the four columns."""
    table = history_widget(root).find("table")
    assert table is not None, "the history widget holds no table"
    carried: dict[int, tuple[int, str]] = {}
    found = []
    for tr in body_rows(table):
        own = iter(cells_of(tr))
        texts, starts = [], False
        for column in range(HISTORY_COLUMNS):
            left, held = carried.get(column, (0, ""))
            if left > 0:
                carried[column] = (left - 1, held)
                texts.append(held)
                continue
            cell = next(own, None)
            assert cell is not None, \
                f"a history row fills {column} of {HISTORY_COLUMNS} columns"
            texts.append(cell.text())
            starts = starts or column == 0
            try:
                span = int(cell.get("rowspan", "1"))
            except ValueError:
                span = 1
            if span > 1:
                carried[column] = (span - 1, cell.text())
        assert next(own, None) is None, \
            f"a history row has more than {HISTORY_COLUMNS} cells"
        found.append(Row(*texts, starts))
    return found


def history_entries(root: Element) -> list[Entry]:
    """The entries of the page's history, newest first: the rows of an
    entry are those that its time, user and subject cells span."""
    found: list[Entry] = []
    for row in history_rows(root):
        if row.starts or not found:
            found.append(Entry(row.time, row.user, row.subject, []))
        found[-1].changes.append(row.change)
    return found


def tiles(root: Element) -> list[Element]:
    """The figure tiles of the page's figures strip; fail when the page
    has none."""
    strip = root.find(cls="figures-strip")
    assert strip is not None, "the page has no figures strip"
    return strip.find_all(cls="figure-tile")


def tile(root: Element, label: str) -> Element:
    """The one figure tile whose text names ``label``."""
    found = [t for t in tiles(root) if label in t.text()]
    assert len(found) == 1, \
        f"{len(found)} tiles name {label!r}: {[t.text() for t in tiles(root)]}"
    return found[0]


def tile_value(found: Element, label: str) -> str:
    """The text of the tile ``found`` without its ``label``."""
    return found.text().replace(label, "", 1).strip()


def carries(found: Element, attribute: str, wanted: Any) -> bool:
    """Whether ``found`` or an element inside it has the class
    ``wanted`` (when ``attribute`` is ``class``) or the attribute with
    that value."""
    for node in (found, *found.walk()):
        if attribute == "class":
            if wanted in node.classes:
                return True
        elif node.get(attribute) == wanted:
            return True
    return False
