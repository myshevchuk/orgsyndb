"""Fixtures and helpers shared by the inventory tests."""

import re
from datetime import date
from decimal import Decimal
from typing import Any

from django.test import TestCase

from . import (IndexMixin, berlin, context_form, demo_index, make_item,
               make_lot, make_user, sent_messages, ticking)

NOW = berlin(2026, 11, 4, 8)
TODAY = date(2026, 11, 4)
MICRO = "µ"
LIST = "/lab/inventory/end-products/"
BULK = "/lab/inventory/end-products/bulk/"
DELIVERIES = "/lab/inventory/deliveries/"
NEW_ITEM = "/lab/inventory/end-products/new/"
NEW_NOTE = "/lab/inventory/deliveries/new/"
NEW_LOT = "/lab/inventory/bulk/new/"
COMPOUND_PAGE = re.compile(r"/compounds/[^/]+/\Z")
NOTE_PAGE = re.compile(r"/lab/inventory/deliveries/\d+/\Z")
KINDS = {"opening": "Anfangsbestand", "delivery": "Abgabe",
         "filling": "Abfüllung", "correction": "Korrektur",
         "reversal": "Storno"}
LEVELS = {"out": "aufgebraucht", "critical": "kritisch", "low": "niedrig",
          "watch": "beobachten", "ok": "ausreichend",
          "undelivered": "noch nie abgegeben", "dormant": "ruhend"}


def visible_text(element: Any) -> str:
    """The text of ``element`` without that of its
    ``span.visually-hidden`` descendants."""
    from . import Element
    parts: list[str] = []

    def collect(node: Any) -> None:
        for child in node.children:
            if isinstance(child, Element):
                if child.tag == "span" and "visually-hidden" in child.classes:
                    continue
                collect(child)
            else:
                parts.append(str(child))

    collect(element)
    return "".join(parts).strip()


def item_url(item: Any, action: str = "") -> str:
    return f"/lab/inventory/items/{item.pk}/" + (
        f"{action}/" if action else "")


def movement_url(movement: Any, action: str = "reverse") -> str:
    return (f"/lab/inventory/items/{movement.item_id}/movements/"
            f"{movement.pk}/{action}/")


def lot_url(lot: Any, action: str = "") -> str:
    return f"/lab/inventory/bulk/{lot.pk}/" + (
        f"{action}/" if action else "")


def note_url(note: Any, action: str = "") -> str:
    return f"/lab/inventory/deliveries/{note.pk}/" + (
        f"{action}/" if action else "")


def num(shown: Any) -> Decimal | None:
    """The first number in a cell or a text, read with the decimal comma
    of a German page or the decimal point of an English one; None when
    there is none."""
    text = shown if isinstance(shown, str) else shown.text()
    found = re.search(r"-?\d[\d.,]*", text)
    if not found:
        return None
    token = found.group()
    if "," in token:
        token = token.replace(".", "").replace(",", ".")
    return Decimal(token.rstrip("."))


def has_number(text: str, shown: str) -> bool:
    """Whether ``shown`` stands in ``text`` as a number of its own."""
    return re.search(rf"(?<![\d,.]){re.escape(shown)}(?!\d|[,.]\d)",
                     text) is not None


def has_amount(text: str, number: str, unit: str) -> bool:
    """Whether ``text`` shows ``number`` and ``unit`` side by side,
    however they are spaced."""
    return re.search(
        rf"(?<![\d,.]){re.escape(number)}\s*{re.escape(unit)}(?!\w)",
        text) is not None


def snapshot() -> dict[str, Any]:
    """Everything the bookings change, to compare before and after a
    refusal."""
    from inventory.models import (DeliveryLine, DeliveryNote,
                                  EnteredConsumption, Item, Lot, LotMovement,
                                  Movement)
    return {
        "items": sorted(Item.objects.values_list(
            "pk", "quantity", "name", "category", "note")),
        "movements": sorted(Movement.objects.values_list("pk", "count")),
        "notes": sorted(DeliveryNote.objects.values_list(
            "pk", "number", "recipient", "note", "reversed")),
        "lines": sorted(DeliveryLine.objects.values_list("pk", "count")),
        "entered": sorted(EnteredConsumption.objects.values_list(
            "item_id", "year", "quarter", "count")),
        "lots": sorted(Lot.objects.values_list(
            "pk", "amount", "batch", "location", "note")),
        "lot_movements": sorted(LotMovement.objects.values_list(
            "pk", "amount")),
    }


def fresh(record: Any) -> Any:
    return type(record).objects.get(pk=record.pk)


def newest_movement(item: Any) -> Any:
    return item.movements.order_by("-pk").first()


def ledger(root: Any) -> list[tuple[str, Any]]:
    """The body rows of a page that show a movement, in page order, each
    with the kind its text names."""
    found = []
    for row in root.find_all("tr"):
        if not row.find("td"):
            continue
        text = row.text()
        named = [(text.find(label), kind) for kind, label in KINDS.items()
                 if label in text]
        if named:
            found.append((min(named)[1], row))
    return found


def cells(row: Any) -> list[Any]:
    from . import Element
    return [c for c in row.children
            if isinstance(c, Element) and c.tag in ("td", "th")]


def note_blocks(root: Any) -> list[tuple[Any, Any]]:
    """Each note a page links, in page order, with the link and the
    largest element that holds that note's link and no other note's."""
    links: dict[str, Any] = {}
    for link in root.find_all("a"):
        href = link.get("href", "")
        if NOTE_PAGE.match(href):
            links.setdefault(href, link)

    def inside(node: Any) -> set[str]:
        return {a.get("href") for a in node.find_all("a")
                if NOTE_PAGE.match(a.get("href", ""))}

    blocks = []
    for href, link in links.items():
        block, node = link, link.parent
        while node is not None and node.tag != "#root" \
                and inside(node) == {href}:
            block, node = node, node.parent
        blocks.append((link, block))
    return blocks


class InventoryCase(IndexMixin, TestCase):
    """A test case with two accounts, the demo collection and a clock
    that stands at 2026-11-04 and ticks."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")

    def setUp(self) -> None:
        self.use_index(demo_index())
        self.enterContext(ticking(NOW))

    def item(self, article: str = "CH-0001", name: str = "Probe",
             size: str = "10", unit: str = "umol", quantity: int = 5,
             **extra: Any) -> Any:
        return make_item(self.kl, article, name, size, unit, quantity,
                         **extra)

    def lot(self, article: str = "CH-0001", unit: str = "mg",
            amount: str = "50", **extra: Any) -> Any:
        return make_lot(self.kl, article, unit, amount, **extra)

    def deliver(self, item: Any, count: int, day: date | None = None,
                user: Any = None, **extra: Any) -> Any:
        """Book a current note with one line; return the note."""
        from inventory.bookings import book_note
        return book_note(user or self.kl, date=day or TODAY,
                         lines=[(item, count)], **extra)

    def deliver_movement(self, item: Any, count: int,
                         day: date | None = None) -> Any:
        self.deliver(item, count, day)
        return newest_movement(item)

    def enter(self, item: Any, year: int, quarter: int,
              count: int | None) -> None:
        from inventory.bookings import enter_consumption
        enter_consumption(self.kl, item, year=year, quarter=quarter,
                          count=count)

    def enter_year(self, item: Any, year: int, per_quarter: int) -> None:
        for quarter in range(1, 5):
            self.enter(item, year, quarter, per_quarter)

    def with_mean_quarter(self, item: Any, mean: int) -> Any:
        """Give ``item`` the mean per quarter ``mean`` on 2026-11-04 by
        an entered value for 2025."""
        self.enter(item, 2025, 1, 4 * mean)
        return item

    def means_item(self, article: str = "CH-0001", **extra: Any) -> Any:
        """The item of the scenario "Means and coverage": 3 containers,
        mean per year 18, mean per quarter 4.5, 13 so far this year."""
        item = self.item(article, quantity=6, **extra)
        self.enter_year(item, 2024, 4)
        self.enter_year(item, 2025, 5)
        self.enter(item, 2026, 1, 10)
        self.deliver(item, 3, date(2026, 10, 15))
        return item

    def consumption(self, item: Any, today: date = TODAY) -> Any:
        from inventory.figures import consumption
        return consumption(fresh(item), today)

    def assertUnchanged(self, before: dict[str, Any]) -> None:
        self.assertEqual(snapshot(), before)


class FormCase(InventoryCase):
    """A test case with a signed-in user."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.kl)

    def refused(self, response: Any, field: str | None = None) -> None:
        """The form is shown again with errors."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(errors, "the form shows no error")
        if field is not None:
            self.assertIn(field, errors)

    def assertMessageNames(self, response: Any, *names: str) -> None:
        shown = sent_messages(response)
        self.assertEqual(len(shown), 1)
        self.assertTrue(any(name in shown[0].message for name in names),
                        f"{shown[0].message!r} names none of {names}")


def item_data(**over: str) -> dict[str, str]:
    data = {"article_number": "CH-0012", "name": "Zimtsäure",
            "category": "", "size": "10", "unit": "umol", "quantity": "12",
            "note": ""}
    data.update(over)
    return data


def note_data(*lines: tuple[Any, int], **over: str) -> dict[str, str]:
    """The delivery-note form with the lines ``(item, count)`` in its
    first rows and the other rows empty."""
    data = {"number": "", "date": TODAY.isoformat(), "recipient": "",
            "note": ""}
    for index in range(10):
        data[f"item_{index}"] = ""
        data[f"count_{index}"] = ""
    for index, (item, count) in enumerate(lines):
        data[f"item_{index}"] = str(item.pk)
        data[f"count_{index}"] = str(count)
    data.update(over)
    return data


def fill_data(**over: str) -> dict[str, str]:
    data = {"count": "5", "date": TODAY.isoformat(), "lot": "",
            "amount": "", "note": ""}
    data.update(over)
    return data


def lot_data(**over: str) -> dict[str, str]:
    data = {"article_number": "CH-0012", "unit": "mg", "amount": "50",
            "batch": "", "location": "", "made_on": "", "note": ""}
    data.update(over)
    return data

