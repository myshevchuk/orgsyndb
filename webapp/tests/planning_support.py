"""Fixtures and helpers shared by the production-planning tests.

Nothing here imports the ``planning`` package at module level, so the
tests of pages and views, which need only the URLs, fail on their
assertions while the package is missing.
"""

import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from . import Element, make_task, parse
from .inventory_support import TODAY, InventoryCase, historical_line
from .widget_support import (body_rows, cells_of, grid, kv, title_of, widget,
                             widgets)

PLAN = "/lab/planning/"
VESSEL_LIST = "/lab/inventory/vessels/"
NEW_TASK = "/lab/tasks/new/"
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
COLUMNS_DE = ["Artikel", "Reichweite", "Synthesedauer", "Spätester Start",
              "Priorität", "Aufgaben", "Maßnahmen"]
COLUMNS_EN = ["Article", "Runway", "Synthesis time", "Latest start",
              "Priority", "Tasks", "Actions"]
FILTERS_DE = ["Alle", "Priorität hoch", "Mit Maßnahme", "Verspätet"]
FILTERS_EN = ["All", "High priority", "With action", "Late"]
LIST_TITLES = ("Planungsliste", "Planning list")
CONTAINERS_TITLES = ("Gebinde & Bedarf", "Containers and demand")
CONTAINER_COLUMNS_DE = ["Gebinde", "Bestand", "Reichweite", "Bedarf/Jahr"]
CONTAINER_COLUMNS_EN = ["Container", "Stock", "Runway", "Demand per year"]
DETAILS_TITLES = ("Planungsdetails", "Planning details")
DETAIL_KEYS_DE = ["Substanz", "Letzte Lieferung", "Bulk", "Reichweite",
                  "Synthesedauer", "Spätester Start", "Aufgaben"]
DETAIL_KEYS_EN = ["Substance", "Last delivery", "Bulk", "Runway",
                  "Synthesis time", "Latest start", "Tasks"]
PARAMETERS_TITLES = ("Planungsparameter", "Planning parameters")
DEFAULTS = {"certainty": 0.95, "buffer_days": 28,
            "default_synthesis_days": 21, "history_quarters": 12,
            "min_orders": 6, "high_days": 14, "medium_days": 56,
            "target_days": 365}

type Quarter = tuple[int, int]


# ---------------------------------------------------------------------------
# Quarters and dates


def quarters_back(count: int, before: Quarter = (2026, 4)) -> list[Quarter]:
    """The ``count`` quarters before ``before``, oldest first; by default
    the complete quarters on 2026-11-04."""
    year, quarter = before
    found = []
    for _ in range(count):
        quarter -= 1
        if quarter == 0:
            year, quarter = year - 1, 4
        found.append((year, quarter))
    return found[::-1]


WINDOW = quarters_back(12)


def middle(quarter: Quarter) -> date:
    """The 15th of the quarter's middle month."""
    year, number = quarter
    return date(year, 3 * number - 1, 15)


def quarter_days(quarter: Quarter) -> int:
    """The calendar days of ``quarter``."""
    year, number = quarter
    return sum(monthrange(year, month)[1]
               for month in range(3 * number - 2, 3 * number + 1))


def shown_dates(day: date) -> tuple[str, str]:
    """The German and the English form of ``day``."""
    return day.strftime("%d.%m.%Y"), day.isoformat()


def has_date(text: str, day: date) -> bool:
    """Whether ``text`` shows ``day``, in either language's form."""
    return any(form in text for form in shown_dates(day))


def has_days(text: str, count: int) -> bool:
    """Whether ``text`` shows ``count`` days, as ``60 Tage`` or
    ``60 days``."""
    return re.search(rf"(?<![\d,.]){count}\s*(Tage|days)\b",
                     text) is not None


def count_days(text: str, count: int) -> int:
    """How often ``text`` shows ``count`` days."""
    return len(re.findall(rf"(?<![\d,.]){count}\s*(?:Tage|days)\b", text))


def has_word(text: str, word: str) -> bool:
    """Whether ``word`` stands in ``text`` as a word of its own."""
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) is not None


# ---------------------------------------------------------------------------
# Plain values for the pure functions


def params(**over: Any) -> Any:
    """An unsaved ``Parameters`` holding the defaults but for ``over``."""
    from planning.models import Parameters
    return Parameters(**{**DEFAULTS, **over})


def quarterly(per_quarter: int = 9, **over: Any) -> Any:
    """The quarterly model of twelve quarters of ``per_quarter``."""
    from planning import forecast
    return forecast.demand({q: per_quarter for q in WINDOW}, [], TODAY,
                           params(**over))


def lumpy(sizes: list[int] | None = None, **over: Any) -> Any:
    """The order model of the orders of ``sizes``, in the three
    quarters of 2026, as many as there are, none entered."""
    from planning import forecast
    sizes = sizes or [2, 3, 4, 6, 7, 11, 13]
    days = [date(2026, 1, 20), date(2026, 2, 20), date(2026, 3, 20),
            date(2026, 4, 20), date(2026, 5, 20), date(2026, 7, 20),
            date(2026, 9, 20), date(2026, 8, 1), date(2026, 6, 1),
            date(2026, 3, 1), date(2026, 5, 1), date(2026, 7, 1)]
    orders = list(zip(days, sizes, strict=False))
    return forecast.demand({}, orders, TODAY, params(**over))


def eight_orders(**over: Any) -> Any:
    """The order model of one order of 10 in each of the eight quarters
    from 2024 Q4 to 2026 Q3."""
    from planning import forecast
    orders = [(middle(q), 10) for q in quarters_back(8)]
    return forecast.demand({}, orders, TODAY, params(**over))


def closed_form(m: float, v: float, stock: float, certainty: float
                ) -> float:
    """The runway of the quarterly model as the specification gives it:
    ``((-z s + sqrt(z² s² + 4 mu S)) / (2 mu))²``."""
    from statistics import NormalDist
    z = NormalDist().inv_cdf(certainty)
    mu = m / 91.3125
    sigma = (v / 91.3125) ** 0.5
    return ((-z * sigma + ((z * sigma) ** 2 + 4 * mu * stock) ** 0.5)
            / (2 * mu)) ** 2


# ---------------------------------------------------------------------------
# Pages


def section(root: Element, *names: str) -> Element:
    """A node that holds what follows the heading ``names`` names, up to
    the next heading of the same or a higher level."""
    for heading in root.find_all(HEADINGS):
        if heading.text() not in names:
            continue
        level = int(heading.tag[1])
        seen = False
        nodes: list[Element | str] = []
        for child in heading.parent.children:
            if child is heading:
                seen = True
            elif not seen:
                continue
            elif (isinstance(child, Element) and child.tag in HEADINGS
                  and int(child.tag[1]) <= level):
                break
            else:
                nodes.append(child)
        held = Element("#section", {}, heading.parent)
        held.children = nodes
        return held
    raise AssertionError(f"the page has no heading {names}")


def metadata(root: Element) -> dict[str, Element]:
    """The ``dd`` of every ``dt`` of the page, by the ``dt``'s text."""
    found: dict[str, Element] = {}
    for term in root.find_all("dt"):
        siblings = term.parent.children
        after = siblings[siblings.index(term) + 1:]
        for node in after:
            if isinstance(node, Element) and node.tag == "dd":
                found[term.text()] = node
                break
    return found


def article_links(root: Element) -> list[Element]:
    """The links to the planning list that the page holds outside its
    header."""
    found = []
    for link in root.find_all("a"):
        if not link.get("href", "").startswith(PLAN):
            continue
        node = link.parent
        while node is not None and node.tag not in ("header", "nav"):
            node = node.parent
        if node is None:
            found.append(link)
    return found


def titles(cell: Element) -> list[str]:
    """The titles of ``cell`` and of everything inside it."""
    return [e.get("title") for e in [cell, *cell.walk()] if e.get("title")]


class Row(dict):
    """The cells of a row of the planning list by header text; ELEMENT
    is the row's ``tr``."""

    element: Element


def list_widget(root: Element) -> Element:
    """The widget ``Planungsliste`` of the page."""
    return widget(root, *LIST_TITLES)


def list_table(root: Element) -> Element | None:
    """The table of the widget ``Planungsliste``, None when the page has
    no such widget or the widget no table."""
    for found in widgets(root):
        if title_of(found) in LIST_TITLES:
            return found.find("table")
    return None


def rows_by_article(root: Element) -> dict[str, Row]:
    """The planning list's rows by their ``data-article``, in page
    order, each as a ``Row``; empty when the page has no list table.
    Fail when two rows name one article or a row names none."""
    found = list_table(root)
    if found is None:
        return {}
    header, _ = grid(found)
    rows: dict[str, Row] = {}
    for tr in body_rows(found):
        article = tr.get("data-article")
        assert article, f"a row of the list has no data-article: {tr.attrs}"
        assert article not in rows, f"two rows name the article {article}"
        row = Row(zip(header, cells_of(tr)))
        row.element = tr
        rows[article] = row
    return rows


def blocks(root: Element) -> dict[str, Element]:
    """The blocks of the inspector by their ``data-article``: the
    elements that carry the attribute and are no table rows. Fail when
    two of them name one article."""
    found: dict[str, Element] = {}
    for node in root.find_all(attrs={"data-article": True}):
        if node.tag == "tr":
            continue
        article = node.get("data-article")
        assert article not in found, \
            f"two blocks of the inspector name the article {article}"
        found[article] = node
    return found


def block_of(root: Element, article: str) -> Element:
    """The inspector's block of ``article``, hidden or not."""
    found = blocks(root)
    assert article in found, \
        f"the inspector has no block of {article}; it has {list(found)}"
    return found[article]


def shown_blocks(root: Element) -> list[str]:
    """The articles of the inspector's blocks that carry no
    ``hidden``."""
    return [article for article, node in blocks(root).items()
            if "hidden" not in node.attrs]


def containers_of(block: Element) -> Element:
    """The widget ``Gebinde & Bedarf`` of ``block``."""
    return widget(block, *CONTAINERS_TITLES)


def container_rows(block: Element) -> list[dict[str, Element]]:
    """The rows of the containers table of ``block``, each by header
    text."""
    inside = containers_of(block).find("table")
    assert inside is not None, "the widget of the containers has no table"
    return grid(inside)[1]


def details_of(block: Element) -> Element:
    """The widget ``Planungsdetails`` of ``block``."""
    return widget(block, *DETAILS_TITLES)


def details(block: Element) -> dict[str, Element]:
    """The value cells of the widget ``Planungsdetails`` of ``block``
    by key."""
    return kv(details_of(block))


def task_texts(cell: Element) -> dict[str, str]:
    """The text of ``cell`` from each linked task's number to the next
    one's, by number."""
    text = cell.text()
    spots, position = [], 0
    for link in cell.find_all("a"):
        if not link.get("href", "").startswith("/lab/tasks/"):
            continue
        number = link.text()
        position = text.index(number, position)
        spots.append((position, number))
        position += len(number)
    ends = [start for start, _ in spots[1:]] + [len(text)]
    return {number: text[start:end]
            for (start, number), end in zip(spots, ends)}


# ---------------------------------------------------------------------------
# The case


class PlanningCase(InventoryCase):
    """The inventory case with helpers that build articles with a known
    demand."""

    def planned_item(self, article: str = "NV-1", size: str = "1",
                     unit: str = "mg", quantity: int = 10,
                     per_quarter: int = 9, name: str | None = None) -> Any:
        """An item with ``per_quarter`` entered for each of the twelve
        quarters before 2026-11-04: ``m`` and ``v`` are
        ``per_quarter``."""
        item = self.item(article, name or article, size, unit, quantity)
        for year, quarter in WINDOW:
            self.enter(item, year, quarter, per_quarter)
        return item

    def demo_item(self, article: str = "CH-0012", quantity: int = 10,
                  per_quarter: int = 9) -> Any:
        """Like ``planned_item``, but the substance keeps the name of
        the demo collection, as ``item`` gives it."""
        item = self.item(article, size="10", unit="umol", quantity=quantity)
        for year, quarter in WINDOW:
            self.enter(item, year, quarter, per_quarter)
        return item

    def orders(self, item: Any, *orders: tuple[date, int]) -> None:
        """Give ``item`` the orders ``(date, count)``, each a historical
        note, which leaves its quantity as it is."""
        from inventory.bookings import book_note
        for day, count in orders:
            book_note(self.kl, date=day, lines=[historical_line(item, count)],
                      historical=True)

    def parameters(self, **over: Any) -> Any:
        from planning.models import Parameters
        return Parameters.objects.create(**{**DEFAULTS, **over})

    def synthesis(self, substance: Any, days: int, end: date,
                  **over: Any) -> Any:
        """An ended task that took ``days`` days and ended on ``end``."""
        return make_task(self.kl, substance=substance,
                         started=end - timedelta(days=days), ended=end,
                         report=True, qc_list=True, **over)

    def running(self, substance: Any, ago: int, **over: Any) -> Any:
        return make_task(self.kl, substance=substance,
                         started=TODAY - timedelta(days=ago), **over)

    def forecast(self, article: str, today: date = TODAY) -> Any:
        from planning import plan
        return plan.article(article, today)

    def get(self, path: str, signed_in: bool = False) -> Element:
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return parse(response.content.decode("utf-8"))
