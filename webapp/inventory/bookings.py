"""Every change of an item's quantity or a vessel's amount, and the
records that go with it.

Each booking runs in one transaction. A quantity or an amount changes
by one conditional ``UPDATE`` of the row, which names the condition the
change needs, such as ``quantity >= n``, and is read back in the same
transaction; the value an instance passed in holds is never trusted.
Two bookings prepared from the same quantity therefore never take more
than it holds. A booking that changes
several rows locks tasks first, then items, then vessels, each in the
order of their IDs, so that two bookings never wait for each other. A
booking that is refused raises Refused and changes nothing.

Recording a batch from a task step and every booking on a flask lock the
row of the task and check in the booking's transaction that the task is
planned or running, so that a booking prepared while the task was open
and stored after it closed is refused. A closure of the task takes the
same lock.
"""

from collections.abc import Iterable, Sequence
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Round
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from inventory.figures import (BASE_PLACES, convert, proposed_amount,
                               quarter_of, to_base)
from inventory.models import (BASE_UNIT, Article, Batch, DeliveryLine,
                              DeliveryNote, EnteredConsumption, Item,
                              Movement, Source, Unit, Vessel,
                              VesselMovement, shown)
from orgsyndb_web import lock
from registry.models import Substance
from tasks.models import State, Task, TaskStep

OPEN = (State.PLANNED, State.RUNNING)


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


def _amount(vessel_id: int) -> Decimal:
    return Vessel.objects.filter(pk=vessel_id).values_list(
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


def _vessel_change(vessel: Vessel, amount: Decimal) -> Decimal:
    """Add AMOUNT, in the vessel's base unit and possibly negative, to
    VESSEL and return its new amount; refuse a change that would leave
    less than zero."""
    rows = Vessel.objects.filter(pk=vessel.pk)
    if amount < 0:
        rows = rows.filter(amount__gte=-amount)
    if not rows.update(amount=Round(F("amount") + amount, 6)):
        left = _amount(vessel.pk)
        if not left:
            raise Refused({"vessel": _("The vessel is used up.")})
        raise Refused({"amount": _(
            "The vessel holds only %(amount)s %(unit)s.") % {
                "amount": number_format(shown(left, vessel.unit)),
                "unit": Unit(vessel.unit).label}})
    return _amount(vessel.pk)


def _lock_tasks(task_ids: Iterable[int]) -> dict[int, Task]:
    """Lock the rows of the tasks TASK_IDS in the order of their IDs and
    return the tasks as stored, by ID. The caller provides the
    transaction."""
    return {task.pk: task for task in Task.objects.select_for_update()
            .filter(pk__in=set(task_ids)).order_by("pk")}


def _flask_task(vessel: Vessel) -> int | None:
    """Return the ID of the task whose step made the batch of VESSEL
    when VESSEL is a flask, else None."""
    return Vessel.objects.filter(pk=vessel.pk, flask=True).values_list(
        "batch__task_step__task_id", flat=True).first()


def _closed(task: Task) -> Refused:
    """Return the refusal of a booking on the flask of the closed TASK."""
    return Refused({"vessel": _(
        "The flask belongs to task %(number)s, which is neither planned "
        "nor running; it takes no booking.") % {"number": task.number}})


def _hold_flask(vessel: Vessel) -> None:
    """Lock the task of VESSEL's batch when VESSEL is a flask and refuse
    unless the task is planned or running. The caller provides the
    transaction."""
    task_id = _flask_task(vessel)
    if task_id is not None:
        task = _lock_tasks([task_id])[task_id]
        if task.state not in OPEN:
            raise _closed(task)


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


def _vessel_movement(user: Any, vessel: Vessel, kind: str,
                     amount: Decimal, after: Decimal, day: Date,
                     note: str = "", **fields: Any) -> VesselMovement:
    return VesselMovement.objects.create(
        vessel=vessel, kind=kind, amount=amount, amount_after=after,
        date=day, booked_at=timezone.now(), user=user, note=note, **fields)


def _number(article_number: str | None) -> str | None:
    """Return ARTICLE_NUMBER stripped, or None for none or an empty
    one."""
    return (article_number or "").strip() or None


def _stored_number(article_id: int) -> str | None:
    """Return the article number the article ARTICLE_ID has in the
    database."""
    return Article.objects.filter(pk=article_id).values_list(
        "article_number", flat=True).get()


def number_taken(article: Article | None, article_number: str) -> bool:
    """Whether an article other than ARTICLE has ARTICLE_NUMBER; ARTICLE
    is None for one not yet created."""
    others = Article.objects.filter(article_number=article_number)
    if article is not None:
        others = others.exclude(pk=article.pk)
    return others.exists()


TAKEN = gettext_lazy(
    "This article already has an item of this size and unit.")
NUMBER_TAKEN = gettext_lazy("Another article has this article number.")


def _numbered(user: Any, article: Article, number: str) -> None:
    """Give ARTICLE, which has no article number, NUMBER, recorded in its
    history as a change by USER; refuse a number another article has
    and an article that has one by now. The lock (``orgsyndb_web.lock``)
    is taken in the caller's transaction before anything is written."""
    lock.hold()
    if number_taken(article, number):
        raise Refused({"article_number": str(NUMBER_TAKEN)})
    if not Article.objects.filter(
            pk=article.pk, article_number__isnull=True).update(
                article_number=number):
        raise Refused({"article_number": _(
            "The article already has an article number.")})
    stored = Article.objects.get(pk=article.pk)
    _attributed(stored, user).save(update_fields=["article_number"])


def assign_article_number(user: Any, article: Article,
                          article_number: str) -> Article:
    """Give ARTICLE, which has no article number, ARTICLE_NUMBER,
    recorded in its history as a change by USER, and return the article
    as stored.

    Refuse an empty or too long ARTICLE_NUMBER, an article that already
    has one, and a number another article has.
    """
    number = _number(article_number)
    if number is None:
        raise Refused({"article_number": _("Enter an article number.")})
    _checked(Article(substance_id=article.pk, article_number=number))
    try:
        with transaction.atomic():
            _numbered(user, article, number)
    except IntegrityError as error:
        raise Refused({"article_number": str(NUMBER_TAKEN)}) from error
    return Article.objects.get(pk=article.pk)


def set_category(user: Any, article: Article, category: str) -> None:
    """Set the category of ARTICLE, and so of every size of it, to
    CATEGORY, recorded in its history as a change by USER, or by the
    signed-in user of the request when USER is None; leave the article
    as it is when it has that category already. Refuse a category too
    long for its field."""
    stored = Article.objects.get(pk=article.pk)
    if stored.category == category:
        return
    stored.category = category
    _checked(stored)
    if user is not None:
        _attributed(stored, user)
    stored.save(update_fields=["category"])


def _article_for(user: Any, substance: Substance, number: str | None,
                 category: str) -> Article:
    """Return the article of SUBSTANCE for a new item, made by USER.

    A substance without an article gets one with NUMBER, which may be
    None, and CATEGORY. An existing article takes CATEGORY when it is
    not empty, and NUMBER when it has none; a NUMBER other than the one
    it has is refused, as is a number another article has. The
    substance's row is locked first, so that two requests cannot both
    make its article, after the lock (``orgsyndb_web.lock``) that every
    article write takes.
    """
    lock.hold()
    Substance.objects.select_for_update().filter(pk=substance.pk).first()
    article = Article.objects.filter(pk=substance.pk).first()
    if article is None:
        if number is not None and number_taken(None, number):
            raise Refused({"article_number": str(NUMBER_TAKEN)})
        article = Article(substance=substance, article_number=number,
                          category=category)
        _checked(article)
        _attributed(article, user).save(force_insert=True)
        return article
    if number is not None and article.article_number is None:
        _numbered(user, article, number)
    elif number is not None and number != article.article_number:
        raise Refused({"article_number": _(
            "The article has the number %(number)s.")
            % {"number": article.article_number}})
    if category:
        set_category(user, article, category)
    return Article.objects.get(pk=article.pk)


def create_item(user: Any, *, substance: Substance,
                article_number: str | None, size: Decimal, unit: str,
                quantity: int, category: str = "", note: str = "",
                date: Date | None = None, stocked_on: Date | None = None,
                compartment: str = "", box: str = "") -> Item:
    """Create an item of the article of SUBSTANCE with QUANTITY
    containers and its opening count, booked by USER and dated DATE,
    today by default.

    A substance without an article gets one, numbered ARTICLE_NUMBER,
    none when it is None or empty, in CATEGORY. For a substance with an
    article, a CATEGORY entered replaces the article's, and an
    ARTICLE_NUMBER entered gives the article that number when it has
    none and must otherwise be its number. The item entered stock on
    STOCKED_ON, or, when that is None and QUANTITY is above zero, on the
    opening count's date. Refuse a QUANTITY below zero, a SIZE of zero
    or less, an unknown UNIT, a DATE or STOCKED_ON after today, a value
    too long for its field, an article number another article has or
    other than the article's, and an item whose size and unit another
    item of the article has; a refusal changes nothing.
    """
    day = _day(date)
    if quantity < 0:
        raise Refused({"quantity": _("The count may not be negative.")})
    number = _number(article_number)
    if number is not None:
        _checked(Article(substance=substance, article_number=number))
    taken = str(TAKEN)
    try:
        with transaction.atomic():
            article = _article_for(user, substance, number, category)
            item = Item(article=article, size=size, unit=unit,
                        quantity=quantity, note=note,
                        compartment=compartment, box=box,
                        stocked_on=stocked_on or (day if quantity > 0
                                                  else None))
            _checked(item)
            if Item.objects.filter(article=article, size=size,
                                   unit=unit).exists():
                raise Refused({"size": taken})
            _attributed(item, user).save()
            _movement(user, item, Movement.Kind.OPENING, quantity, quantity,
                      day)
    except IntegrityError as error:
        raise Refused({"size": taken}) from error
    return item


def book_note(user: Any, *, date: Date, lines: Sequence[tuple[Item, int]],
              number: str | None = "", recipient: str = "", note: str = "",
              historical: bool = False) -> DeliveryNote:
    """Create a delivery note of LINES, pairs of an item and a count,
    made by USER, and return it.

    A current note books one delivery movement per line, dated DATE; a
    HISTORICAL note changes no quantity. Refuse, with the position of
    the line concerned where there is one: a note without lines; an item
    twice, or one whose article has no article number; a count of zero
    or less; for a current note, a count above the item's quantity;
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
        if _stored_number(item.article_id) is None:
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


def fill(user: Any, item: Item, *, count: int, vessel: Vessel | None,
         date: Date | None = None, note: str = "",
         amount: Decimal | None = None) -> Movement:
    """Book COUNT containers filled into ITEM from VESSEL by USER, dated
    DATE, today by default, and return the item's movement, which names
    the vessel's.

    The filling takes AMOUNT, in the vessel's unit, from the vessel in
    the same transaction. An AMOUNT of None takes the proposed amount:
    COUNT times the item's size, converted into the vessel's base unit
    through the molar mass of the item's substance where the kinds
    differ. Refuse, at ``vessel``, a VESSEL of None, one of another
    substance than the item's, one that is used up and the flask of a
    task that is neither planned nor running; refuse a COUNT of zero or
    less, a DATE after today, an AMOUNT above the vessel's or one that
    rounds to zero in six places of its unit or of the base unit, and the
    proposal when there is no molar mass to convert with.
    """
    day = _day(date)
    if count <= 0:
        raise Refused({"count": _("The count must be above zero.")})
    if vessel is None:
        raise Refused({"vessel": _(
            "Choose the vessel the containers are filled from.")})
    if vessel.batch.substance_id != item.article_id:
        raise Refused({"vessel": _("The vessel holds another substance.")})
    with transaction.atomic():
        _hold_flask(vessel)
        after = _add(item, count)
        base = _taken(item, count, vessel, amount)
        taken = _vessel_movement(
            user, vessel, VesselMovement.Kind.FILLING, base,
            _vessel_change(vessel, -base), day, note)
        return _movement(user, item, Movement.Kind.FILLING, count, after,
                         day, note=note, vessel_movement=taken)


def _passed(amount: Decimal, unit: str, message: str) -> Decimal:
    """Return AMOUNT of UNIT in its base unit, rounded half up to six
    places; refuse with MESSAGE, at ``amount``, an AMOUNT that is zero or
    less, or that rounds to zero in six places of UNIT or of its base
    unit."""
    if amount.quantize(BASE_PLACES, ROUND_HALF_UP) <= 0 \
            or to_base(amount, unit) <= 0:
        raise Refused({"amount": message})
    return to_base(amount, unit)


def _taken(item: Item, count: int, vessel: Vessel, amount: Decimal | None
           ) -> Decimal:
    """Return the amount COUNT containers of ITEM take from VESSEL, in
    its base unit: AMOUNT, given in the vessel's unit, or the
    proposal."""
    if amount is not None:
        return _passed(amount, vessel.unit,
                       _("The amount taken must be above zero."))
    base = proposed_amount(item, count, vessel)
    if base is None:
        raise Refused({"amount": _(
            "Without a molar mass of the substance, enter the amount "
            "taken.")})
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
    taken back out, and its amount returns to its vessel with a vessel
    reversal. Refuse an empty NOTE, a movement of another kind, one
    already reversed, a filling whose containers are no longer there,
    and a filling from the flask of a task that is neither planned nor
    running.
    """
    text = _required(note)
    if not movement.reversible:
        raise Refused(_("Only a delivery or a filling can be reversed."))
    done = _("The movement is already reversed.")
    day = timezone.localdate()
    item = movement.item
    try:
        with transaction.atomic():
            taken = movement.vessel_movement
            if taken is not None:
                _hold_flask(taken.vessel)
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
                if taken is not None:
                    returned = _vessel_movement(
                        user, taken.vessel, VesselMovement.Kind.REVERSAL,
                        taken.amount,
                        _vessel_change(taken.vessel, taken.amount), day,
                        text)
            return _movement(user, item, Movement.Kind.REVERSAL,
                             movement.count, after, day, note=text,
                             reverses=movement, vessel_movement=returned)
    except IntegrityError as error:
        raise Refused(done) from error


def has_begun(year: int, quarter: int, today: Date) -> bool:
    """Tell whether the QUARTER of YEAR has begun by TODAY, the current
    quarter included."""
    return (year, quarter) <= quarter_of(today)


def held_quarters(item: Item, year: int | None = None
                  ) -> set[tuple[int, int]]:
    """Return the quarters, as pairs of year and quarter, in which ITEM
    has a line of a historical delivery note that is not reversed, and
    which therefore take no entered consumption value; only those of
    YEAR when it is given."""
    lines = DeliveryLine.objects.filter(
        item=item, delivery_note__historical=True,
        delivery_note__reversed=False)
    if year is not None:
        lines = lines.filter(delivery_note__date__year=year)
    return {quarter_of(line.delivery_note.date)
            for line in lines.select_related("delivery_note")}


def enter_consumption(user: Any, item: Item, *, year: int, quarter: int,
                      count: int | None) -> EnteredConsumption | None:
    """Set the entered consumption of ITEM in QUARTER of YEAR to COUNT
    containers, entered by USER, and return it; a COUNT of None removes
    the quarter's value and returns None.

    The change is recorded in the history of the entered consumption as
    made by USER, a removal included. Refuse an item whose article has
    no article number, a QUARTER outside 1 to 4, a YEAR below 1, a
    quarter that has not begun (``has_begun``), a COUNT below zero, and
    a value for a quarter in which the item has lines of a historical
    note that is not reversed (``held_quarters``).
    """
    if _stored_number(item.article_id) is None:
        raise Refused(_("An item without an article number has never "
                        "been delivered."))
    if not 1 <= quarter <= 4:
        raise Refused({"quarter": _("The quarter is 1, 2, 3 or 4.")})
    if year < 1:
        raise Refused({"year": _("The year must be above zero.")})
    if not has_begun(year, quarter, timezone.localdate()):
        raise Refused({"quarter": _("The quarter has not begun yet.")})
    if count is not None and count < 0:
        raise Refused({"count": _("The count may not be negative.")})
    with transaction.atomic():
        list(Item.objects.select_for_update().filter(pk=item.pk))
        record = EnteredConsumption.objects.filter(
            item=item, year=year, quarter=quarter).first()
        if count is None:
            if record is not None:
                _attributed(record, user).delete()
            return None
        if (year, quarter) in held_quarters(item, year):
            raise Refused({"quarter": _(
                "Historical delivery notes hold this quarter's consumption; "
                "reverse them before entering a value.")})
        if record is None:
            record = EnteredConsumption(item=item, year=year,
                                        quarter=quarter)
        record.count = count
        record.entered_by = user
        record.entered_at = timezone.now()
        _attributed(record, user).save()
        return record


def _field_checked(model: type[Any], **values: Any) -> None:
    """Refuse a value that the field of MODEL named by its keyword does
    not allow, such as a text that is too long or an unknown unit."""
    for name, value in values.items():
        try:
            model._meta.get_field(name).clean(value, None)
        except ValidationError as error:
            raise Refused({name: " ".join(error.messages)}) from error


def _batch_amount(amount: Decimal | None, unit: str, required: bool
                  ) -> Decimal | None:
    """Return AMOUNT of UNIT in the base unit, rounded half up to six
    places, or None for an AMOUNT of None that is not REQUIRED; refuse
    an unknown or empty UNIT with an amount, an AMOUNT below zero, and
    for a REQUIRED amount one that is missing or not above zero."""
    if amount is None:
        if required:
            raise Refused({"amount": _("Enter the yield.")})
        return None
    _field_checked(Vessel, unit=unit)
    base = to_base(amount, unit)
    if base < 0 or (required and base <= 0):
        raise Refused({"amount": _(
            "The yield must be above zero.") if required else _(
            "The amount may not be negative.")})
    return base


def record_batch(user: Any, *, substance: Substance,
                 source: str = Source.MADE, number: str = "",
                 journal_entry: Any = None, task_step: TaskStep | None = None,
                 date: Date | None = None, supplier: str = "",
                 supplier_article_number: str = "", supplier_batch: str = "",
                 note: str = "", amount: Decimal | None = None,
                 unit: str = "", location: str = "") -> Batch:
    """Record a batch of SUBSTANCE, made in the lab or bought as SOURCE
    says, booked by USER, and return it.

    A made batch has a NUMBER and may name a JOURNAL_ENTRY, an entry of
    the lab journal; a bought one has the SUPPLIER and the supplier's
    article number and batch. DATE is the day it was made or received,
    or None.

    With an AMOUNT of UNIT the batch opens its first vessel in the same
    transaction, a stored vessel at LOCATION. A batch made by the task
    step TASK_STEP needs the AMOUNT, which is its yield: it opens the
    batch's flask when LOCATION is empty and a stored vessel there
    otherwise, and the batch names the step's journal entry when the
    step names one, whatever JOURNAL_ENTRY says. The row of the step's
    task is locked and its state checked in the transaction.

    Refuse a SOURCE that is neither made nor bought; a made batch
    without a number, or with a supplier's field; a bought batch with a
    number, entry or step; a NUMBER another made batch has regardless of
    case, naming that batch; a SUBSTANCE the step does not make
    (``TaskStep.products``); a step whose task is neither planned nor
    running; an AMOUNT below zero, or for a step one that is not above
    zero or missing; an unknown UNIT; a DATE after today; and a value
    too long for its field. A refusal changes nothing.
    """
    if source not in Source.values:
        raise Refused({"source": _("The source is made or bought.")})
    made = source == Source.MADE
    number = (number or "").strip()
    if task_step is not None:
        if not made:
            raise Refused({"source": _(
                "A batch made by a task step is made in the lab.")})
        if substance not in task_step.products():
            raise Refused({"substance": _(
                "Step %(position)s of task %(number)s does not make "
                "%(substance)s.") % {
                    "position": task_step.position,
                    "number": task_step.task.number,
                    "substance": substance.key}})
    base = _batch_amount(amount, unit, task_step is not None)
    _field_checked(Vessel, location=location)
    if base is not None:
        _field_checked(Vessel, amount=base)
    batch = Batch(
        substance=substance, source=source, number=number,
        journal_entry=journal_entry, task_step=task_step, date=date,
        yield_amount=base if task_step is not None else None,
        yield_unit=unit if task_step is not None else "",
        supplier=supplier, supplier_article_number=supplier_article_number,
        supplier_batch=supplier_batch, note=note)
    _checked(batch)
    try:
        with transaction.atomic():
            if task_step is not None:
                task = _lock_tasks([task_step.task_id])[task_step.task_id]
                if task.state not in OPEN:
                    raise Refused({"step": _(
                        "Task %(number)s is neither planned nor "
                        "running.") % {"number": task.number}})
                task_step.task = task
                if substance not in task_step.products():
                    raise Refused({"substance": _(
                        "Step %(position)s of task %(number)s does not "
                        "make %(substance)s.") % {
                            "position": task_step.position,
                            "number": task.number,
                            "substance": substance.key}})
                entry = TaskStep.objects.filter(
                    pk=task_step.pk).values_list(
                        "journal_entry_id", flat=True).first()
                if entry is not None:
                    batch.journal_entry_id = entry
            if made:
                holder = Batch.objects.filter(
                    source=Source.MADE, number_key=number.casefold()
                    ).first()
                if holder is not None:
                    raise Refused({"number": _taken_number(holder)})
            _attributed(batch, user).save(force_insert=True)
            if base is not None:
                _open(user, batch, unit, base, _day(None),
                      flask=task_step is not None and not location,
                      location=location)
    except IntegrityError as error:
        raise Refused({"number": _taken_number(None)}) from error
    return batch


def _taken_number(holder: Batch | None) -> str:
    """Return the refusal text of a batch number that the made batch
    HOLDER has regardless of case; HOLDER is None when it is not
    known."""
    if holder is None:
        return _("Another made batch has this number.")
    return _("Batch %(batch)s has this number.") % {"batch": holder}


def _open(user: Any, batch: Batch, unit: str, base: Decimal, day: Date, *,
          flask: bool = False, location: str = "",
          kind: str = VesselMovement.Kind.OPENING, **fields: Any
          ) -> VesselMovement:
    """Store a vessel of BATCH in UNIT holding BASE, its base unit, at
    LOCATION, and its first movement of KIND dated DAY, which takes the
    keywords FIELDS; return the movement."""
    vessel = Vessel(batch=batch, unit=unit, amount=base, flask=flask,
                    location=location)
    _attributed(vessel, user).save(force_insert=True)
    return _vessel_movement(user, vessel, kind, base, base, day,
                            **fields)


def open_vessel(user: Any, batch: Batch, *, unit: str, amount: Decimal,
                location: str = "", note: str = "",
                date: Date | None = None) -> Vessel:
    """Open a stored vessel of BATCH holding AMOUNT of UNIT, booked by
    USER with an opening movement dated DATE, today by default, and
    return it.

    The amount is kept in the base unit of UNIT, rounded half up to six
    places. Refuse an AMOUNT below zero, an unknown UNIT, a DATE after
    today, and a LOCATION or NOTE too long for its field.
    """
    day = _day(date)
    base = _batch_amount(amount, unit, False)
    vessel = Vessel(batch=batch, unit=unit, amount=base, location=location,
                    note=note)
    _checked(vessel)
    with transaction.atomic():
        _attributed(vessel, user).save(force_insert=True)
        _vessel_movement(user, vessel, VesselMovement.Kind.OPENING, base,
                         base, day)
    return vessel


def correct_vessel(user: Any, vessel: Vessel, *, amount: Decimal, note: str,
                   date: Date | None = None) -> VesselMovement:
    """Set the amount of VESSEL to AMOUNT, weighed and given in the
    vessel's unit, with NOTE, by USER, dated DATE, today by default;
    return the vessel's movement.

    Refuse an AMOUNT below zero, an empty NOTE, a DATE after today, and
    the flask of a task that is neither planned nor running; the task's
    row is locked while its state is checked.
    """
    day = _day(date)
    text = _required(note)
    if amount < 0:
        raise Refused({"amount": _("The amount may not be negative.")})
    base = to_base(amount, vessel.unit)
    with transaction.atomic():
        _hold_flask(vessel)
        Vessel.objects.filter(pk=vessel.pk).update(amount=base)
        return _vessel_movement(
            user, vessel, VesselMovement.Kind.CORRECTION, base,
            _amount(vessel.pk), day, text)


def withdraw(user: Any, vessel: Vessel, *, task_step: TaskStep,
             amount: Decimal, date: Date | None = None, note: str = ""
             ) -> VesselMovement:
    """Book AMOUNT, in the vessel's unit, taken from VESSEL into the task
    step TASK_STEP by USER, dated DATE, today by default, and return the
    withdrawal.

    Refuse an AMOUNT that is not above zero or rounds to zero in six
    places of its unit or of the base unit, an AMOUNT above the
    vessel's, a vessel that is used up, a DATE after today, a step whose
    task is neither planned nor running, and the flask of a task that is
    neither; the rows of
    the tasks are locked while their states are checked.
    """
    day = _day(date)
    base = _passed(amount, vessel.unit,
                   _("The amount taken must be above zero."))
    with transaction.atomic():
        flask = _flask_task(vessel)
        tasks = _lock_tasks([task_step.task_id,
                             *([] if flask is None else [flask])])
        task = tasks[task_step.task_id]
        if task.state not in OPEN:
            raise Refused({"step": _(
                "Task %(number)s is neither planned nor running.")
                % {"number": task.number}})
        if flask is not None and tasks[flask].state not in OPEN:
            raise _closed(tasks[flask])
        return _vessel_movement(
            user, vessel, VesselMovement.Kind.WITHDRAWAL, base,
            _vessel_change(vessel, -base), day, note, task_step=task_step)


def reverse_withdrawal(user: Any, movement: VesselMovement
                       ) -> VesselMovement:
    """Reverse the withdrawal MOVEMENT by USER, dated today: its amount
    returns to its vessel, and the reversal names it as ``reverses``.
    Return the reversal.

    Refuse a movement of another kind, a withdrawal already reversed,
    and a withdrawal from the flask of a task that is neither planned
    nor running.
    """
    if movement.kind != VesselMovement.Kind.WITHDRAWAL:
        raise Refused(_("Only a withdrawal can be reversed here."))
    done = _("The withdrawal is already reversed.")
    try:
        with transaction.atomic():
            vessel = movement.vessel
            _hold_flask(vessel)
            if VesselMovement.objects.filter(reverses=movement).exists():
                raise Refused(done)
            return _vessel_movement(
                user, vessel, VesselMovement.Kind.REVERSAL, movement.amount,
                _vessel_change(vessel, movement.amount),
                timezone.localdate(), reverses=movement)
    except IntegrityError as error:
        raise Refused(done) from error


def transfer(user: Any, source: Vessel, *, amount: Decimal,
             target: Vessel | None = None, location: str = "",
             date: Date | None = None, note: str = ""
             ) -> tuple[VesselMovement, VesselMovement]:
    """Pass AMOUNT, in the unit of the vessel SOURCE, from SOURCE to
    another vessel of its batch, booked by USER, dated DATE, today by
    default, and return the ``transfer_out`` of SOURCE and the
    ``transfer_in`` that names it.

    The target is the stored vessel TARGET, or, when that is None, a new
    stored vessel at LOCATION in the unit of SOURCE, whose first
    movement is the ``transfer_in``. The ``transfer_in`` holds the
    amount converted into the target's base unit, through the molar
    mass of the substance across mass and amount of substance, rounded
    half up to six places.

    Refuse, at ``amount``, an AMOUNT that is not above zero or rounds to
    zero in six places of its unit or of the base unit, one above the
    source's, and one whose converted amount rounds
    to zero; at ``vessel``, a source that is used up; at ``target``, a
    TARGET of another batch, a flask or SOURCE itself, and one the
    amount does not convert into for want of a molar mass; and a DATE
    after today. A source that is the flask of a task that is neither
    planned nor running is refused too. A refusal changes nothing.
    """
    day = _day(date)
    base = _passed(amount, source.unit,
                   _("The amount passed must be above zero."))
    if target is None:
        _field_checked(Vessel, location=location)
        converted = base
    else:
        if target.batch_id != source.batch_id or target.flask \
                or target.pk == source.pk:
            raise Refused({"target": _(
                "Choose another stored vessel of the same batch.")})
        converted = convert(base, BASE_UNIT[source.unit],
                            BASE_UNIT[target.unit],
                            source.batch.substance.mw)
        if converted is None:
            raise Refused({"target": _(
                "The substance has no molar mass to convert the amount "
                "into the unit of the target.")})
        converted = converted.quantize(BASE_PLACES, ROUND_HALF_UP)
        if converted <= 0:
            raise Refused({"amount": _(
                "The amount rounds to zero in the target's unit.")})
    with transaction.atomic():
        _hold_flask(source)
        list(Vessel.objects.select_for_update().filter(
            pk__in=[source.pk, *([] if target is None else [target.pk])]
            ).order_by("pk").values_list("pk", flat=True))
        out = _vessel_movement(
            user, source, VesselMovement.Kind.TRANSFER_OUT, base,
            _vessel_change(source, -base), day, note)
        if target is None:
            into = _open(user, source.batch, source.unit, converted, day,
                         location=location, note=note,
                         kind=VesselMovement.Kind.TRANSFER_IN,
                         transfer=out)
        else:
            into = _vessel_movement(
                user, target, VesselMovement.Kind.TRANSFER_IN, converted,
                _vessel_change(target, converted), day, note, transfer=out)
    return out, into


def write_off_flasks(user: Any, task: Task) -> list[VesselMovement]:
    """Empty each flask of the batches the steps of TASK made that still
    holds an amount, by a ``remainder`` movement of USER dated today,
    and return the movements; a flask without an amount books nothing.

    The row of TASK is locked, and the write-off belongs to the
    transaction that closes the task: callers that end, fail or cancel a
    task call it inside that transaction.
    """
    day = timezone.localdate()
    booked = []
    with transaction.atomic():
        _lock_tasks([task.pk])
        for flask in Vessel.objects.select_for_update().filter(
                flask=True, batch__task_step__task_id=task.pk
                ).order_by("pk"):
            if flask.amount > 0:
                left = flask.amount
                booked.append(_vessel_movement(
                    user, flask, VesselMovement.Kind.REMAINDER, left,
                    _vessel_change(flask, -left), day))
    return booked
