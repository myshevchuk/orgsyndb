"""Fixtures and helpers shared by the inventory tests."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any

from django.test import TestCase

from . import (berlin, context_form, make_batch, make_item, make_user,
               make_vessel, sent_messages, substance_for, ticking)

NOW = berlin(2026, 11, 4, 8)
TODAY = date(2026, 11, 4)
MICRO = "µ"
LIST = "/lab/inventory/end-products/"
BATCHES = "/lab/inventory/batches/"
VESSELS = "/lab/inventory/vessels/"
DELIVERIES = "/lab/inventory/deliveries/"
NEW_ITEM = "/lab/inventory/end-products/new/"
NEW_NOTE = "/lab/inventory/deliveries/new/"
NEW_BATCH = "/lab/inventory/batches/new/"
COMPOUND_PAGE = re.compile(r"/compounds/[^/]+/\Z")
SUBSTANCE_PAGE = re.compile(r"/lab/registry/substances/[^/]+/\Z")
NOTE_PAGE = re.compile(r"/lab/inventory/deliveries/\d+/\Z")
KINDS = {"opening": "Anfangsbestand", "delivery": "Abgabe",
         "filling": "Abfüllung", "correction": "Korrektur",
         "reversal": "Storno"}
VESSEL_KINDS = {"opening": "Anfangsmenge", "filling": "Abfüllung",
                "withdrawal": "Entnahme",
                "transfer_out": "Umfüllung (Abgang)",
                "transfer_in": "Umfüllung (Zugang)",
                "correction": "Korrektur", "remainder": "Restausbuchung",
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


def batch_url(batch: Any, action: str = "") -> str:
    return f"/lab/inventory/batches/{batch.pk}/" + (
        f"{action}/" if action else "")


def vessel_url(vessel: Any, action: str = "") -> str:
    return f"/lab/inventory/vessels/{vessel.pk}/" + (
        f"{action}/" if action else "")


def vessel_movement_url(movement: Any, action: str = "reverse") -> str:
    return f"/lab/inventory/vessels/movements/{movement.pk}/{action}/"


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
    from inventory.models import (Article, Batch, DeliveryLine,
                                  DeliveryNote, EnteredConsumption, Item,
                                  Movement, Vessel, VesselMovement)
    return {
        "articles": sorted(Article.objects.values_list(
            "pk", "article_number", "category")),
        "items": sorted(Item.objects.values_list(
            "pk", "quantity", "note")),
        "movements": sorted(Movement.objects.values_list("pk", "count")),
        "notes": sorted(DeliveryNote.objects.values_list(
            "pk", "number", "recipient", "note", "reversed")),
        "lines": sorted(DeliveryLine.objects.values_list("pk", "count")),
        "entered": sorted(EnteredConsumption.objects.values_list(
            "item_id", "year", "quarter", "count")),
        "batches": sorted(Batch.objects.values_list(
            "pk", "number", "journal_entry_id", "yield_amount", "note")),
        "vessels": sorted(Vessel.objects.values_list(
            "pk", "amount", "location", "note")),
        "vessel_movements": sorted(VesselMovement.objects.values_list(
            "pk", "kind", "amount")),
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


def vessel_ledger(root: Any) -> list[tuple[str, Any]]:
    """The body rows of a vessel's page that show a movement, in page
    order, each with the kind its text names."""
    found = []
    for row in root.find_all("tr"):
        if not row.find("td"):
            continue
        text = row.text()
        named = [(text.find(label), kind)
                 for kind, label in VESSEL_KINDS.items() if label in text]
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


class Refusals:
    """A mixin for test cases that book through ``inventory.bookings``."""

    @contextmanager
    def refusing(self, field: str | None = None) -> Iterator[None]:
        """The block's booking raises ``Refused``, with an error at
        ``field`` when that is given, and changes nothing the
        ``snapshot`` holds."""
        from inventory.bookings import Refused
        before = snapshot()
        with self.assertRaises(Refused) as caught:
            yield
        if field is not None:
            self.assertIn(field, caught.exception.message_dict)
        self.assertEqual(snapshot(), before)

    def refused(self, response: Any, field: str | None = None) -> None:
        """The form is shown again with errors."""
        self.assertEqual(response.status_code, 200)
        errors = context_form(response).errors
        self.assertTrue(errors, "the form shows no error")
        if field is not None:
            self.assertIn(field, errors)

    def assertMessageNames(self, response: Any, *names: str) -> None:
        shown = sent_messages(response)
        self.assertTrue(shown, "no message was sent")
        self.assertTrue(any(name in shown[-1].message for name in names),
                        f"{shown[-1].message!r} names none of {names}")


class InventoryCase(Refusals, TestCase):
    """A test case with two accounts, the demo collection and a clock
    that stands at 2026-11-04 and ticks."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.kl = make_user("kl", "KL", "Klara", "Lehmann")
        cls.ae = make_user("ae", "AE", "Anna", "Eisele")

    def setUp(self) -> None:
        self.enterContext(ticking(NOW))

    def item(self, article: str = "CH-0001", name: str | None = None,
             size: str = "10", unit: str = "umol", quantity: int = 5,
             **extra: Any) -> Any:
        """An item of the article ``article``, of the substance
        ``substance_for(article)`` (see ``make_item``); ``mw``,
        ``category`` and the other keywords of ``make_item`` pass
        on."""
        return make_item(self.kl, article, name, size, unit, quantity,
                         **extra)

    def batch(self, article: str = "CH-0001", **extra: Any) -> Any:
        """A batch of the substance ``substance_for(article)``, the
        substance of the item of that article number (see
        ``make_batch``)."""
        return make_batch(self.kl, article, **extra)

    def vessel(self, article: str = "CH-0001", unit: str = "mg",
               amount: str = "50", **extra: Any) -> Any:
        """A stored vessel of a new batch of the substance
        ``substance_for(article)``, the substance of the item of that
        article number (see ``make_vessel``); ``batch``, ``flask`` and
        the keywords of ``make_batch`` pass on."""
        return make_vessel(self.kl, unit=unit, amount=amount,
                           article=article, **extra)

    def filling(self, item: Any, count: int, day: date | None = None,
                note: str = "", **extra: Any) -> Any:
        """Book a filling of ``count`` containers of ``item`` from a new
        stored vessel of its substance, which holds twice what they
        take; return the item's movement."""
        from inventory.bookings import fill
        vessel = make_vessel(
            self.kl, unit=item.unit, amount=str(item.size * count * 2),
            substance=item.article.substance)
        return fill(self.kl, item, count=count, vessel=vessel, date=day,
                    note=note, **extra)

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
    """A test case with a signed-in user and the substance
    ``cinnamic-acid``, which ``item_data`` and ``batch_data`` name."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.kl)
        self.cinnamic = substance_for("CH-0012")


def item_data(**over: str) -> dict[str, str]:
    """The new-item form with the substance ``cinnamic-acid``, which a
    test creates with ``make_substance("cinnamic-acid")`` or loads from
    the demo registry."""
    data = {"substance": "cinnamic-acid", "article_number": "CH-0012",
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
    data = {"count": "5", "date": TODAY.isoformat(), "vessel": "",
            "amount": "", "note": ""}
    data.update(over)
    return data


def batch_data(**over: str) -> dict[str, str]:
    """The new-batch form with the substance ``cinnamic-acid`` and no
    amount: a made batch of the number ``KL0412``."""
    data = {"substance": "cinnamic-acid", "source": "made",
            "number": "KL0412", "journal_entry": "", "date": "",
            "supplier": "", "supplier_article_number": "",
            "supplier_batch": "", "note": "", "amount": "", "unit": "mg",
            "location": ""}
    data.update(over)
    return data
