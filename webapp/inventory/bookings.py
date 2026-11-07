"""Every change of an item's quantity or a lot's amount, and the records
that go with it.

Each booking runs in one transaction. A quantity or an amount changes
by one conditional ``UPDATE`` of the row, which names the condition the
change needs, such as ``quantity >= n``, and is read back in the same
transaction; the value an instance passed in holds is never trusted.
Two bookings prepared from the same quantity therefore never take more
than it holds, on PostgreSQL and SQLite alike. A booking that changes
several rows locks items before lots and items in the order of their
IDs, so that two bookings never wait for each other. A booking that is
refused raises Refused and changes nothing.
"""

from collections.abc import Sequence
from datetime import date as Date
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Round
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from inventory.figures import proposed_amount, quarter_of, to_base
from inventory.models import (BASE_UNIT, END_PRODUCTS, DeliveryLine,
                              DeliveryNote, EnteredConsumption, Item, Lot,
                              LotMovement, Movement, Unit, shown)


class Refused(ValidationError):
    """A booking that was refused and changed nothing.

    The message is a text, or a dict that maps the names of the
    booking's arguments to texts, such as ``{"count": ...}``. LINE is
    the position, from zero, of the line of a delivery note the refusal
    concerns, or None.
    """

    def __init__(self, message: str | dict[str, str],
                 line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


def _day(day: Date | None) -> Date:
    """Return DAY, or today when it is None; refuse a day after today."""
    today = timezone.localdate()
    if day is None:
        return today
    if day > today:
        raise Refused({"date": _("The date may not lie in the future.")})
    return day


def _required(note: str) -> str:
    """Return NOTE stripped; refuse an empty one."""
    note = (note or "").strip()
    if not note:
        raise Refused({"note": _("A note is required.")})
    return note


def _checked(record: Any) -> None:
    """Refuse RECORD when a field holds a value its model does not
    allow, such as a text that is too long or an unknown unit."""
    try:
        record.full_clean(validate_unique=False,
                          validate_constraints=False)
    except ValidationError as error:
        raise Refused({name: " ".join(texts) for name, texts in
                       error.message_dict.items()}) from error


def _attributed(record: Any, user: Any) -> Any:
    """Return RECORD with USER as the author of the history record its
    next save writes."""
    record._history_user = user
    return record


def _lock(items: Sequence[Item]) -> None:
    """Lock the rows of ITEMS in the order of their IDs."""
    list(Item.objects.select_for_update().filter(
        pk__in=[item.pk for item in items]).order_by("pk").values_list(
            "pk", flat=True))


def _quantity(item_id: int) -> int:
    return Item.objects.filter(pk=item_id).values_list(
        "quantity", flat=True).get()


def _amount(lot_id: int) -> Decimal:
    return Lot.objects.filter(pk=lot_id).values_list(
        "amount", flat=True).get()


def _take(item: Item, count: int) -> int | None:
    """Take COUNT containers out of ITEM and return its new quantity, or
    None, changing nothing, when it holds fewer."""
    if not Item.objects.filter(pk=item.pk, quantity__gte=count).update(
            quantity=F("quantity") - count):
        return None
    return _quantity(item.pk)


def _add(item: Item, count: int) -> int:
    """Add COUNT containers to ITEM and return its new quantity."""
    Item.objects.filter(pk=item.pk).update(quantity=F("quantity") + count)
    return _quantity(item.pk)


def _lot_change(lot: Lot, amount: Decimal) -> Decimal:
    """Add AMOUNT, in the lot's base unit and possibly negative, to LOT
    and return its new amount; refuse a change that would leave less
    than zero."""
    rows = Lot.objects.filter(pk=lot.pk)
    if amount < 0:
        rows = rows.filter(amount__gte=-amount)
    if not rows.update(amount=Round(F("amount") + amount, 6)):
        left = _amount(lot.pk)
        if not left:
            raise Refused({"lot": _("The lot is used up.")})
        raise Refused({"amount": _(
            "The lot holds only %(amount)s %(unit)s.") % {
                "amount": number_format(shown(left, lot.unit)),
                "unit": Unit(lot.unit).label}})
    return _amount(lot.pk)


def _movement(user: Any, item: Item, kind: str, count: int, after: int,
              day: Date, **fields: Any) -> Movement:
    """Store the movement of ITEM, and when it leaves the item holding
    containers and the item has no stock entry date, give it DAY as that
    date, recorded in its history as a change by USER."""
    movement = Movement.objects.create(
        item=item, kind=kind, count=count, quantity_after=after, date=day,
        booked_at=timezone.now(), user=user, **fields)
    if after > 0 and Item.objects.filter(
            pk=item.pk, stocked_on__isnull=True).update(stocked_on=day):
        stored = Item.objects.get(pk=item.pk)
        _attributed(stored, user).save(update_fields=["stocked_on"])
    return movement


def _lot_movement(user: Any, lot: Lot, kind: str, amount: Decimal,
                  after: Decimal, day: Date, note: str = "") -> LotMovement:
    return LotMovement.objects.create(
        lot=lot, kind=kind, amount=amount, amount_after=after, date=day,
        booked_at=timezone.now(), user=user, note=note)


def _number(article_number: str | None) -> str | None:
    """Return ARTICLE_NUMBER stripped, or None for none or an empty
    one."""
    return (article_number or "").strip() or None


def number_taken(item: Item, article_number: str) -> bool:
    """Whether another item of ITEM's inventory has ARTICLE_NUMBER with
    ITEM's size and unit."""
    return Item.objects.filter(
        inventory=item.inventory, article_number=article_number,
        size=item.size, unit=item.unit).exclude(pk=item.pk).exists()


TAKEN = gettext_lazy(
    "This article already has an item of this size and unit.")


def create_item(user: Any, *, article_number: str | None, name: str,
                size: Decimal, unit: str, quantity: int, category: str = "",
                note: str = "", date: Date | None = None,
                stocked_on: Date | None = None, compartment: str = "",
                box: str = "", inventory: str = END_PRODUCTS) -> Item:
    """Create an item of INVENTORY with QUANTITY containers and its
    opening count, booked by USER and dated DATE, today by default.

    An ARTICLE_NUMBER of None or empty gives an item without one. The
    item entered stock on STOCKED_ON, or, when that is None and QUANTITY
    is above zero, on the opening count's date.
    Refuse a QUANTITY below zero, a SIZE of zero or less, an unknown
    UNIT, a DATE or STOCKED_ON after today, a value too long for its
    field, and an item whose article number, size and unit another item
    of the inventory has.
    """
    day = _day(date)
    if quantity < 0:
        raise Refused({"quantity": _("The count may not be negative.")})
    item = Item(inventory=inventory,
                article_number=_number(article_number), name=name,
                category=category, size=size, unit=unit,
                quantity=quantity, note=note, compartment=compartment,
                box=box,
                stocked_on=stocked_on or (day if quantity > 0 else None))
    _checked(item)
    taken = str(TAKEN)
    if item.article_number is not None and number_taken(
            item, item.article_number):
        raise Refused({"size": taken})
    try:
        with transaction.atomic():
            _attributed(item, user).save()
            _movement(user, item, Movement.Kind.OPENING, quantity, quantity,
                      day)
    except IntegrityError as error:
        raise Refused({"size": taken}) from error
    return item


def assign_article_number(user: Any, item: Item,
                          article_number: str) -> Item:
    """Give ITEM, which has no article number, ARTICLE_NUMBER, recorded
    in its history as a change by USER, and return the item as stored.

    Refuse an empty or too long ARTICLE_NUMBER, an item that already has
    one, and a number another item of the inventory has with ITEM's size
    and unit.
    """
    number = _number(article_number)
    if number is None:
        raise Refused({"article_number": _("Enter an article number.")})
    _checked(Item(inventory=item.inventory, article_number=number,
                  name=item.name, size=item.size, unit=item.unit))
    try:
        with transaction.atomic():
            if number_taken(item, number):
                raise Refused({"article_number": str(TAKEN)})
            if not Item.objects.filter(
                    pk=item.pk, article_number__isnull=True).update(
                        article_number=number):
                raise Refused({"article_number": _(
                    "The item already has an article number.")})
            stored = Item.objects.get(pk=item.pk)
            _attributed(stored, user).save(update_fields=["article_number"])
    except IntegrityError as error:
        raise Refused({"article_number": str(TAKEN)}) from error
    return stored


def book_note(user: Any, *, date: Date, lines: Sequence[tuple[Item, int]],
              number: str | None = "", recipient: str = "", note: str = "",
              historical: bool = False) -> DeliveryNote:
    """Create a delivery note of LINES, pairs of an item and a count,
    made by USER, and return it.

    A current note books one delivery movement per line, dated DATE; a
    HISTORICAL note changes no quantity. Refuse, with the position of
    the line concerned where there is one: a note without lines; an item
    twice, of another inventory than ``end-products``, or without an
    article number; a count of
    zero or less; for a current note, a count above the item's quantity;
    for a historical note, an item with an entered consumption value for
    the quarter of DATE. Refuse too a DATE after today, a NUMBER another
    note has, and a value too long for its field. An empty NUMBER is
    none.
    """
    day = _day(date)
    if not lines:
        raise Refused(_("A delivery note needs at least one line."))
    seen: set[int] = set()
    for position, (item, count) in enumerate(lines):
        if item.inventory != END_PRODUCTS:
            raise Refused({"item": _("The item is not an end product.")},
                          line=position)
        if item.article_number is None:
            raise Refused({"item": _(
                "Enter the item's article number before its first "
                "delivery.")}, line=position)
        if item.pk in seen:
            raise Refused({"item": _("The item is already in the note.")},
                          line=position)
        seen.add(item.pk)
        if count <= 0:
            raise Refused({"count": _("The count must be above zero.")},
                          line=position)
    record = DeliveryNote(number=number or None, date=day,
                          recipient=recipient, note=note,
                          historical=historical, created_by=user)
    _checked(record)
    taken = _("Another delivery note has this number.")
    if record.number and DeliveryNote.objects.filter(
            number=record.number).exists():
        raise Refused({"number": taken})
    try:
        with transaction.atomic():
            _lock([item for item, _count in lines])
            if historical:
                _check_quarters(lines, day)
            _attributed(record, user).save()
            for position, (item, count) in enumerate(lines):
                DeliveryLine.objects.create(delivery_note=record,
                                            item=item, count=count)
                if historical:
                    continue
                after = _take(item, count)
                if after is None:
                    raise Refused({"count": _(
                        "Only %(quantity)s containers of %(item)s are "
                        "left.") % {"quantity": _quantity(item.pk),
                                    "item": item}}, line=position)
                _movement(user, item, Movement.Kind.DELIVERY, count, after,
                          day, delivery_note=record)
    except IntegrityError as error:
        raise Refused({"number": taken}) from error
    return record


def _check_quarters(lines: Sequence[tuple[Item, int]], day: Date) -> None:
    """Refuse a historical note dated DAY when an item of LINES has an
    entered consumption value for the quarter of DAY."""
    year, quarter = quarter_of(day)
    for position, (item, _count) in enumerate(lines):
        if EnteredConsumption.objects.filter(
                item=item, year=year, quarter=quarter).exists():
            raise Refused({"count": _(
                "%(item)s has an entered consumption value for Q%(quarter)s "
                "%(year)s.") % {"item": item, "quarter": quarter,
                                "year": year}}, line=position)


def reverse_historical(user: Any, delivery_note: DeliveryNote, *,
                       note: str) -> DeliveryNote:
    """Mark the historical DELIVERY_NOTE reversed with NOTE, by USER, and
    return it as stored.

    Refuse an empty NOTE, a current note, whose lines are reversed
    through their movements, and a note already reversed.
    """
    text = _required(note)
    with transaction.atomic():
        if not DeliveryNote.objects.filter(
                pk=delivery_note.pk, historical=True, reversed=False
                ).update(reversed=True, reversal_note=text):
            stored = DeliveryNote.objects.get(pk=delivery_note.pk)
            if not stored.historical:
                raise Refused(_("A current delivery note is reversed line "
                                "by line, through its movements."))
            raise Refused(_("The delivery note is already reversed."))
        stored = DeliveryNote.objects.get(pk=delivery_note.pk)
        _attributed(stored, user).save(
            update_fields=["reversed", "reversal_note"])
    return stored


def fill(user: Any, item: Item, *, count: int, date: Date | None = None,
         note: str = "", lot: Lot | None = None,
         amount: Decimal | None = None) -> Movement:
    """Book COUNT containers filled into ITEM by USER, dated DATE, today
    by default, and return the movement.

    With a LOT, the filling takes AMOUNT, in the lot's unit, from it in
    the same transaction, and the item's movement names the lot's. An
    AMOUNT of None takes the proposed amount: COUNT times the item's
    size, converted into the lot's base unit through the molar mass of
    the item's compound where the kinds differ. Refuse a COUNT of zero
    or less, a DATE after today, a lot of another article or inventory,
    a lot that is used up, an AMOUNT above the lot's or one that rounds
    to zero in six places of the base unit, and the proposal when there
    is no molar mass to convert with.
    """
    day = _day(date)
    if count <= 0:
        raise Refused({"count": _("The count must be above zero.")})
    if lot is not None and (lot.article_number != item.article_number
                            or lot.inventory != item.inventory):
        raise Refused({"lot": _("The lot holds another article.")})
    with transaction.atomic():
        after = _add(item, count)
        taken = None
        if lot is not None:
            base = _taken(item, count, lot, amount)
            taken = _lot_movement(user, lot, LotMovement.Kind.FILLING, base,
                                  _lot_change(lot, -base), day, note)
        return _movement(user, item, Movement.Kind.FILLING, count, after,
                         day, note=note, bulk_movement=taken)


def _taken(item: Item, count: int, lot: Lot, amount: Decimal | None
           ) -> Decimal:
    """Return the amount COUNT containers of ITEM take from LOT, in its
    base unit: AMOUNT, given in the lot's unit, or the proposal."""
    if amount is None:
        base = proposed_amount(item, count, lot)
        if base is None:
            raise Refused({"amount": _(
                "Without a molar mass of the compound, enter the amount "
                "taken.")})
    else:
        base = to_base(amount, lot.unit)
    if base <= 0:
        raise Refused({"amount": _(
            "The amount taken must be above zero.")})
    return base


def correct(user: Any, item: Item, *, count: int, note: str,
            date: Date | None = None) -> Movement:
    """Set the quantity of ITEM to COUNT, the containers counted, with
    NOTE, by USER, dated DATE, today by default; return the movement.

    Refuse a COUNT below zero, an empty NOTE and a DATE after today.
    """
    day = _day(date)
    text = _required(note)
    if count < 0:
        raise Refused({"count": _("The count may not be negative.")})
    with transaction.atomic():
        Item.objects.filter(pk=item.pk).update(quantity=count)
        return _movement(user, item, Movement.Kind.CORRECTION, count,
                         _quantity(item.pk), day, note=text)


def reverse(user: Any, movement: Movement, *, note: str) -> Movement:
    """Reverse the delivery or filling MOVEMENT with NOTE, by USER, dated
    today, and return the reversal.

    A delivery's count goes back into the item. A filling's count is
    taken back out, and its amount returns to its lot with a lot
    reversal. Refuse an empty NOTE, a movement of another kind, one
    already reversed, and a filling whose containers are no longer
    there.
    """
    text = _required(note)
    if not movement.reversible:
        raise Refused(_("Only a delivery or a filling can be reversed."))
    done = _("The movement is already reversed.")
    day = timezone.localdate()
    item = movement.item
    try:
        with transaction.atomic():
            if Movement.objects.filter(reverses=movement).exists():
                raise Refused(done)
            returned = None
            if movement.kind == Movement.Kind.DELIVERY:
                after = _add(item, movement.count)
            else:
                after = _take(item, movement.count)
                if after is None:
                    raise Refused(_("The containers of the filling are no "
                                    "longer there."))
                taken = movement.bulk_movement
                if taken is not None:
                    returned = _lot_movement(
                        user, taken.lot, LotMovement.Kind.REVERSAL,
                        taken.amount, _lot_change(taken.lot, taken.amount),
                        day, text)
            return _movement(user, item, Movement.Kind.REVERSAL,
                             movement.count, after, day, note=text,
                             reverses=movement, bulk_movement=returned)
    except IntegrityError as error:
        raise Refused(done) from error


def enter_consumption(user: Any, item: Item, *, year: int, quarter: int,
                      count: int | None) -> EnteredConsumption | None:
    """Set the entered consumption of ITEM in QUARTER of YEAR to COUNT
    containers, entered by USER, and return it; a COUNT of None removes
    the quarter's value and returns None.

    Refuse an item without an article number, a QUARTER outside 1 to
    4, a YEAR below 1, a quarter after the current one, a COUNT below
    zero, and a value for a quarter in which the item has lines of a
    historical note that is not reversed.
    """
    if item.article_number is None:
        raise Refused(_("An item without an article number has never "
                        "been delivered."))
    if not 1 <= quarter <= 4:
        raise Refused({"quarter": _("The quarter is 1, 2, 3 or 4.")})
    if year < 1:
        raise Refused({"year": _("The year must be above zero.")})
    if (year, quarter) > quarter_of(timezone.localdate()):
        raise Refused({"quarter": _("The quarter has not begun yet.")})
    if count is not None and count < 0:
        raise Refused({"count": _("The count may not be negative.")})
    with transaction.atomic():
        entered = EnteredConsumption.objects.filter(item=item, year=year,
                                                    quarter=quarter)
        if count is None:
            entered.delete()
            return None
        list(Item.objects.select_for_update().filter(pk=item.pk))
        if any(quarter_of(line.delivery_note.date) == (year, quarter)
               for line in DeliveryLine.objects.filter(
                   item=item, delivery_note__historical=True,
                   delivery_note__reversed=False,
                   delivery_note__date__year=year
               ).select_related("delivery_note")):
            raise Refused({"quarter": _(
                "Historical delivery notes hold this quarter's consumption; "
                "reverse them before entering a value.")})
        record, _created = EnteredConsumption.objects.update_or_create(
            item=item, year=year, quarter=quarter,
            defaults={"count": count, "entered_by": user,
                      "entered_at": timezone.now()})
        return record


def create_lot(user: Any, *, article_number: str, unit: str,
               amount: Decimal, batch: str = "", location: str = "",
               made_on: Date | None = None, note: str = "",
               date: Date | None = None,
               inventory: str = END_PRODUCTS) -> Lot:
    """Create a bulk lot of INVENTORY holding AMOUNT of UNIT, with its
    opening movement booked by USER and dated DATE, today by default.

    The amount is kept in the base unit of UNIT, rounded half up to six
    places. Refuse an AMOUNT below zero, an unknown UNIT, a DATE after
    today and a value too long for its field.
    """
    day = _day(date)
    if unit not in BASE_UNIT:
        raise Refused({"unit": _("The unit is mg, g, µmol or mmol.")})
    if amount < 0:
        raise Refused({"amount": _("The amount may not be negative.")})
    base = to_base(amount, unit)
    lot = Lot(inventory=inventory, article_number=article_number, unit=unit,
              amount=base, batch=batch, location=location, made_on=made_on,
              note=note)
    _checked(lot)
    with transaction.atomic():
        _attributed(lot, user).save()
        _lot_movement(user, lot, LotMovement.Kind.OPENING, base, base, day)
    return lot


def correct_lot(user: Any, lot: Lot, *, amount: Decimal, note: str,
                date: Date | None = None) -> LotMovement:
    """Set the amount of LOT to AMOUNT, weighed and given in the lot's
    unit, with NOTE, by USER, dated DATE, today by default; return the
    lot's movement.

    Refuse an AMOUNT below zero, an empty NOTE and a DATE after today.
    """
    day = _day(date)
    text = _required(note)
    if amount < 0:
        raise Refused({"amount": _("The amount may not be negative.")})
    base = to_base(amount, lot.unit)
    with transaction.atomic():
        Lot.objects.filter(pk=lot.pk).update(amount=base)
        return _lot_movement(user, lot, LotMovement.Kind.CORRECTION, base,
                             _amount(lot.pk), day, text)
