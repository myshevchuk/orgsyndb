"""The inventory: articles, their items counted in containers, the items'
movements, delivery notes, entered consumption, batches of substances,
and the vessels that hold a batch's amounts with their own movements.

Counts and amounts change only through ``inventory.bookings``.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from orgsyndb_web.history import RecordedHistory
from orgsyndb_web.lock import LockedQuerySet, LockedWrites

class Unit(models.TextChoices):
    MG = "mg", "mg"
    UMOL = "umol", "µmol"
    G = "g", "g"
    MMOL = "mmol", "mmol"


# Each unit's factor to its base unit, and that base unit: mg for masses,
# µmol for amounts of substance.
FACTOR = {Unit.MG: 1, Unit.G: 1000, Unit.UMOL: 1, Unit.MMOL: 1000}
BASE_UNIT = {Unit.MG: Unit.MG, Unit.G: Unit.MG, Unit.UMOL: Unit.UMOL,
             Unit.MMOL: Unit.UMOL}
SHOWN_PLACES = Decimal("0.001")


class Level(models.TextChoices):
    OUT = "out", pgettext_lazy("level", "out")
    CRITICAL = "critical", pgettext_lazy("level", "critical")
    LOW = "low", pgettext_lazy("level", "low")
    WATCH = "watch", pgettext_lazy("level", "watch")
    OK = "ok", pgettext_lazy("level", "sufficient")
    UNDELIVERED = "undelivered", pgettext_lazy("level", "never delivered")
    DORMANT = "dormant", pgettext_lazy("level", "dormant")


# The levels from the most urgent on.
LEVEL_ORDER = {level: rank for rank, level in enumerate(Level)}
# The levels the list's level filter takes, each with the more urgent
# ones.
URGENT = (Level.OUT, Level.CRITICAL, Level.LOW, Level.WATCH)


class Status(models.TextChoices):
    """The state of an item set by hand: a size not needed for now, or
    one being discontinued, is set aside from planning."""

    ACTIVE = "active", pgettext_lazy("item status", "active")
    NOT_NEEDED = "not_needed", pgettext_lazy("item status", "not needed")
    DISCONTINUED = "discontinued", pgettext_lazy("item status",
                                                 "discontinued")


def not_in_future(day: date | None) -> None:
    """Refuse a DAY after today."""
    if day and day > timezone.localdate():
        raise ValidationError(_("The date may not lie in the future."))


class Article(LockedWrites, models.Model):
    """An article: one substance of the registry as the lab delivers it,
    in one or more container sizes, its items.

    The substance is the article's primary key, so a substance has at
    most one article. The article number, the one delivery notes carry,
    is None until the article is first delivered and fixed once it is
    set; it is unique among articles. The category is the article's and
    every size's. Its saves and deletions take the lock
    (``orgsyndb_web.lock``).
    """

    objects = LockedQuerySet.as_manager()

    substance = models.OneToOneField(
        "registry.Substance", verbose_name=_("Substance"),
        primary_key=True, on_delete=models.PROTECT, related_name="article")
    article_number = models.CharField(_("Article no."), max_length=30,
                                      unique=True, null=True, blank=True)
    category = models.CharField(_("Category"), max_length=100, blank=True)

    history = RecordedHistory()

    class Meta:
        ordering = [models.F("article_number").asc(nulls_last=True),
                    "substance__key"]
        verbose_name = _("article")
        verbose_name_plural = _("articles")

    def __str__(self) -> str:
        return self.article_number or self.substance.shown_name

    @property
    def name(self) -> str:
        """The name of the article's substance in the active language."""
        return self.substance.shown_name


class Item(models.Model):
    """An article in one container size, counted in whole containers.

    The article, size and unit identify the item and are fixed once it
    exists. Its substance, name, article number and category are its
    article's. The quantity changes only by movements; the change
    history covers the other fields.
    """

    article = models.ForeignKey(Article, verbose_name=_("article"),
                                on_delete=models.PROTECT,
                                related_name="items")
    size = models.DecimalField(
        _("Size"), max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))])
    unit = models.CharField(_("Unit"), max_length=4, choices=Unit.choices)
    quantity = models.PositiveIntegerField(_("Stock"), default=0)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)
    status = models.CharField(_("Status"), max_length=12,
                              choices=Status.choices, default=Status.ACTIVE)
    stocked_on = models.DateField(_("In stock since"), null=True,
                                  blank=True, validators=[not_in_future])
    compartment = models.CharField(_("Compartment"), max_length=30,
                                   blank=True)
    box = models.CharField(_("Box"), max_length=30, blank=True)

    history = RecordedHistory(excluded_fields=["quantity"])

    class Meta:
        ordering = [models.F("article__article_number").asc(nulls_last=True),
                    "article__substance__key", "unit", "size"]
        verbose_name = _("item")
        verbose_name_plural = _("items")
        constraints = [
            models.UniqueConstraint(
                fields=["article", "size", "unit"],
                name="inventory_item_identity"),
            models.CheckConstraint(condition=Q(size__gt=0),
                                   name="inventory_item_size_positive"),
        ]

    def __str__(self) -> str:
        shown = f"{self.container} {self.name}"
        number = self.article_number
        return f"{number} {shown}" if number else shown

    @property
    def substance(self) -> Any:
        """The substance of the item's article."""
        return self.article.substance

    @property
    def article_number(self) -> str | None:
        """The article number of the item's article, or None."""
        return self.article.article_number

    @property
    def name(self) -> str:
        """The name of the item's substance in the active language."""
        return self.article.substance.shown_name

    @property
    def category(self) -> str:
        """The category of the item's article."""
        return self.article.category

    @property
    def container(self) -> str:
        """The size with its unit, without trailing zeros and in the
        number format of the active language, as ``2,5 mg`` in
        German."""
        return f"{number_format(plain(self.size))} {Unit(self.unit).label}"

    @property
    def place(self) -> str:
        """Where the item's containers are kept, as ``Fach 2 / Box 7``
        in German, or the empty string when neither is set."""
        parts = [f"{_('Compartment')} {self.compartment}"
                 if self.compartment else "",
                 f"{_('Box')} {self.box}" if self.box else ""]
        return " / ".join(part for part in parts if part)

    def is_new(self, today: date) -> bool:
        """Whether the item entered stock in the calendar year of
        TODAY."""
        return self.stocked_on is not None \
            and self.stocked_on.year == today.year

    def container_order(self) -> tuple[bool, Decimal]:
        """The place of the item's container size among sizes: units of
        mass before units of amount of substance, then by size in mg or
        µmol."""
        return (BASE_UNIT[self.unit] != Unit.MG,
                self.size * FACTOR[self.unit])

    def sort_key(self) -> tuple[bool, str, tuple[bool, Decimal]]:
        """The item's place in the default order: by article number,
        items without one after the others and by name, then by
        container size as ``container_order`` gives it."""
        number = self.article_number
        return (number is None, number if number is not None
                else self.name.casefold(), self.container_order())


class DeliveryNote(models.Model):
    """A delivery note (``Lieferschein``) and its lines.

    A current note books one delivery movement per line; a historical
    note records deliveries made before they could be booked and changes
    no quantity. A historical note is reversed whole, by its REVERSED
    flag; a current note's lines are reversed through their movements.
    The date, the kind and the lines are fixed once the note exists.
    """

    number = models.CharField(_("Number"), max_length=30, unique=True,
                              null=True, blank=True)
    date = models.DateField(_("Date"))
    recipient = models.CharField(_("Recipient"), max_length=100,
                                 blank=True)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)
    historical = models.BooleanField(_("Entered later"), default=False)
    reversed = models.BooleanField(_("Reversed"), default=False)
    reversal_note = models.TextField(_("Note of the reversal"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Created by"),
        on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["-date", "-created_at", "-id"]
        verbose_name = _("delivery note")
        verbose_name_plural = _("delivery notes")

    def __str__(self) -> str:
        return self.number or f"#{self.pk}"


class DeliveryLine(models.Model):
    """A line of a delivery note: COUNT containers of ITEM."""

    delivery_note = models.ForeignKey(
        DeliveryNote, on_delete=models.PROTECT, related_name="lines",
        verbose_name=_("delivery note"))
    item = models.ForeignKey(Item, on_delete=models.PROTECT,
                             related_name="delivery_lines",
                             verbose_name=_("item"))
    count = models.PositiveIntegerField(
        _("Count"), validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]
        verbose_name = _("line")
        verbose_name_plural = _("lines")
        constraints = [
            models.UniqueConstraint(fields=["delivery_note", "item"],
                                    name="inventory_line_item_once"),
        ]

    def __str__(self) -> str:
        return f"{self.count} × {self.item}"


class Source(models.TextChoices):
    """Where a batch comes from."""

    MADE = "made", pgettext_lazy("batch source", "made")
    BOUGHT = "bought", pgettext_lazy("batch source", "bought")


class Batch(models.Model):
    """A batch: a quantity of one substance with one origin, made in the
    lab or bought.

    A made batch has a NUMBER, unique among made batches regardless of
    case and of their substance, and may name the JOURNAL_ENTRY it is
    written down in, the TASK_STEP that made it, and its yield. The
    yield is kept in the base unit of YIELD_UNIT, mg or µmol. A bought
    batch has the SUPPLIER, the supplier's article number and the
    supplier's batch, and no number, entry, step or yield. The
    substance, source and step are fixed once the batch exists. Its
    amounts are held by its vessels.

    ``save`` sets NUMBER_KEY, the key that makes the numbers unique.
    """

    substance = models.ForeignKey(
        "registry.Substance", verbose_name=_("Substance"),
        on_delete=models.PROTECT, related_name="batches")
    source = models.CharField(_("Source"), max_length=6,
                              choices=Source.choices, default=Source.MADE)
    number = models.CharField(_("Batch"), max_length=30, blank=True)
    number_key = models.CharField(max_length=100, blank=True,
                                  editable=False)
    journal_entry = models.ForeignKey(
        "journal.Entry", verbose_name=_("Lab notebook"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="batches")
    task_step = models.ForeignKey(
        "tasks.TaskStep", verbose_name=_("Made by step"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="batches")
    date = models.DateField(_("Date"), null=True, blank=True,
                            validators=[not_in_future])
    yield_amount = models.DecimalField(
        _("Yield"), max_digits=18, decimal_places=6, null=True, blank=True)
    yield_unit = models.CharField(_("Unit"), max_length=4,
                                  choices=Unit.choices, blank=True)
    supplier = models.CharField(_("Supplier"), max_length=100, blank=True)
    supplier_article_number = models.CharField(
        _("Supplier's article no."), max_length=50, blank=True)
    supplier_batch = models.CharField(_("Supplier's batch"), max_length=50,
                                      blank=True)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["id"]
        verbose_name = _("batch")
        verbose_name_plural = _("batches")
        constraints = [
            models.UniqueConstraint(
                fields=["number_key"], condition=Q(source=Source.MADE),
                name="inventory_batch_number_once"),
        ]

    def __str__(self) -> str:
        if self.source == Source.MADE:
            return self.number or f"#{self.pk}"
        return self.supplier_batch or f"#{self.pk}"

    def clean(self) -> None:
        """Refuse a made batch without a number or with a supplier's
        field, a bought batch that has a number, entry, step or yield,
        and a yield without its unit or a unit without its yield."""
        super().clean()
        errors: dict[str, str] = {}
        if self.source == Source.MADE:
            if not self.number:
                errors["number"] = _("A made batch needs a number.")
            for name in ("supplier", "supplier_article_number",
                         "supplier_batch"):
                if getattr(self, name):
                    errors[name] = _("A made batch has none.")
        else:
            for name in ("number", "journal_entry", "task_step",
                         "yield_amount"):
                if getattr(self, name) not in (None, ""):
                    errors[name] = _("A bought batch has none.")
        if (self.yield_amount is None) != (not self.yield_unit) \
                and "yield_amount" not in errors:
            errors["yield_amount"] = _(
                "The yield and its unit are given together.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the batch with NUMBER_KEY set from its number: the
        number casefolded for a made batch, empty for a bought one. A
        save that names ``update_fields`` and writes the number or the
        source writes the key too."""
        self.number_key = self.number.casefold() \
            if self.source == Source.MADE else ""
        fields = kwargs.get("update_fields")
        if fields is not None and {"number", "source"} & set(fields):
            kwargs["update_fields"] = {*fields, "number_key"}
        super().save(*args, **kwargs)

    @property
    def article_number(self) -> str | None:
        """The article number of the batch's substance, or None."""
        return self.substance.article_number

    @property
    def origin(self) -> str:
        """The source as the active language names it, followed by the
        supplier when there is one, as ``gekauft · Sigma``."""
        shown_source = str(Source(self.source).label)
        return f"{shown_source} · {self.supplier}" if self.supplier \
            else shown_source

    @property
    def shown_yield(self) -> Decimal | None:
        """The yield in its unit, rounded half up to three places; None
        without a yield."""
        if self.yield_amount is None:
            return None
        return shown(self.yield_amount, self.yield_unit)

    @property
    def yield_unit_label(self) -> str:
        """The yield's unit as it is shown, such as ``µmol``; empty
        without one."""
        return str(Unit(self.yield_unit).label) if self.yield_unit else ""


class VesselKind(models.TextChoices):
    """What a vessel is for, which follows from its flag, its batch and
    its substance."""

    FLASK = "flask", _("Flask")
    END_PRODUCT = "end-product", _("End product")
    INTERMEDIATE = "intermediate", _("Intermediate")
    REAGENT = "reagent", _("Reagent")


class Vessel(models.Model):
    """A weighed amount of one batch in one place.

    The amount is kept in the base unit of the vessel's UNIT, mg or
    µmol, and changes only by the vessel's movements. A vessel at zero
    is used up. FLASK tells whether it is its batch's reaction flask,
    which holds the batch's yield until the task of its step ends; a
    batch has at most one. The batch, unit and flask flag are fixed once
    the vessel exists. A vessel belongs to every item of its substance's
    article.
    """

    batch = models.ForeignKey(Batch, verbose_name=_("Batch"),
                              on_delete=models.PROTECT,
                              related_name="vessels")
    unit = models.CharField(_("Unit"), max_length=4, choices=Unit.choices)
    amount = models.DecimalField(_("Amount"), max_digits=18,
                                 decimal_places=6, default=0)
    flask = models.BooleanField(_("Flask"), default=False)
    location = models.CharField(_("Location"), max_length=100, blank=True)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)

    history = RecordedHistory(excluded_fields=["amount"])

    class Meta:
        ordering = ["batch__substance__key", "id"]
        verbose_name = _("vessel")
        verbose_name_plural = _("vessels")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="inventory_vessel_amount_not_negative"),
            models.UniqueConstraint(
                fields=["batch"], condition=Q(flask=True),
                name="inventory_vessel_one_flask"),
        ]

    def __str__(self) -> str:
        return f"{self.batch} #{self.pk}"

    @property
    def substance(self) -> Any:
        """The substance of the vessel's batch."""
        return self.batch.substance

    @property
    def article_number(self) -> str | None:
        """The article number of the vessel's substance, or None."""
        return self.batch.substance.article_number

    @property
    def kind(self) -> str:
        """The vessel's kind, a value of ``VesselKind``: ``flask`` for a
        flask; for a stored vessel ``end-product`` when its substance has
        an article, else ``intermediate`` for a made batch and
        ``reagent`` for a bought one."""
        if self.flask:
            return VesselKind.FLASK
        if hasattr(self.batch.substance, "article"):
            return VesselKind.END_PRODUCT
        return VesselKind.INTERMEDIATE \
            if self.batch.source == Source.MADE else VesselKind.REAGENT

    @property
    def kind_label(self) -> str:
        """The kind as the active language names it."""
        return VesselKind(self.kind).label

    @property
    def shown_amount(self) -> Decimal:
        """The amount in the vessel's unit, rounded half up to three
        places."""
        return shown(self.amount, self.unit)

    @property
    def unit_label(self) -> str:
        """The vessel's unit as it is shown, such as ``µmol``."""
        return str(Unit(self.unit).label)


class VesselMovement(models.Model):
    """A change of a vessel's amount: AMOUNT in the vessel's base unit,
    and AMOUNT_AFTER, the vessel's amount once it was booked.

    A withdrawal names the TASK_STEP the amount went into; no other kind
    names a step. The reversal of a withdrawal names it as REVERSES, and
    a withdrawal is reversed at most once; the reversal of a filling is
    named by the item's movement instead. A transfer is two movements,
    and the ``transfer_in`` names the ``transfer_out`` as TRANSFER.
    """

    class Kind(models.TextChoices):
        OPENING = "opening", _("Opening amount")
        FILLING = "filling", _("Filling")
        WITHDRAWAL = "withdrawal", _("Withdrawal")
        TRANSFER_OUT = "transfer_out", _("Transfer out")
        TRANSFER_IN = "transfer_in", _("Transfer in")
        CORRECTION = "correction", _("Correction")
        REMAINDER = "remainder", _("Remainder written off")
        REVERSAL = "reversal", _("Reversal")

    vessel = models.ForeignKey(Vessel, on_delete=models.CASCADE,
                               related_name="movements",
                               verbose_name=_("vessel"))
    kind = models.CharField(_("Kind"), max_length=12, choices=Kind.choices)
    amount = models.DecimalField(_("Amount"), max_digits=18,
                                 decimal_places=6)
    amount_after = models.DecimalField(_("Amount after"), max_digits=18,
                                       decimal_places=6)
    date = models.DateField(_("Date"))
    booked_at = models.DateTimeField(_("Booked at"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("User"),
                             on_delete=models.PROTECT, related_name="+")
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)
    task_step = models.ForeignKey(
        "tasks.TaskStep", verbose_name=_("task step"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="vessel_movements")
    transfer = models.OneToOneField(
        "self", verbose_name=_("Transfer"), on_delete=models.PROTECT,
        null=True, blank=True, related_name="transferred")
    reverses = models.OneToOneField(
        "self", verbose_name=_("Reverses"), on_delete=models.PROTECT,
        null=True, blank=True, related_name="reversal")

    class Meta:
        ordering = ["-id"]
        verbose_name = _("vessel movement")
        verbose_name_plural = _("vessel movements")
        constraints = [
            models.CheckConstraint(
                condition=Q(kind="withdrawal", task_step__isnull=False)
                | (~Q(kind="withdrawal") & Q(task_step__isnull=True)),
                name="inventory_vesselmovement_withdrawal_step"),
            models.CheckConstraint(
                condition=Q(reverses__isnull=True) | Q(kind="reversal"),
                name="inventory_vesselmovement_reverses"),
            models.CheckConstraint(
                condition=Q(transfer__isnull=True) | Q(kind="transfer_in"),
                name="inventory_vesselmovement_transfer"),
        ]

    def __str__(self) -> str:
        return f"{self.vessel} {self.get_kind_display()}"


class Movement(models.Model):
    """A change of an item's quantity.

    COUNT is the containers moved, or for an opening count or a
    correction the quantity entered; QUANTITY_AFTER is the item's
    quantity once the movement was booked. DATE is the day it took
    place, BOOKED_AT the time it was booked. A delivery names its
    DELIVERY_NOTE; a filling from a vessel, and the reversal of one, name
    the vessel's movement as VESSEL_MOVEMENT; a reversal names the
    movement it REVERSES, which is reversed at most once.
    """

    class Kind(models.TextChoices):
        OPENING = "opening", _("Opening count")
        DELIVERY = "delivery", _("Delivery")
        FILLING = "filling", _("Filling")
        CORRECTION = "correction", _("Correction")
        REVERSAL = "reversal", _("Reversal")

    item = models.ForeignKey(Item, on_delete=models.CASCADE,
                             related_name="movements",
                             verbose_name=_("item"))
    kind = models.CharField(_("Kind"), max_length=10, choices=Kind.choices)
    count = models.PositiveIntegerField(_("Count"))
    quantity_after = models.PositiveIntegerField(_("Stock after"))
    date = models.DateField(_("Date"))
    booked_at = models.DateTimeField(_("Booked at"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("User"),
                             on_delete=models.PROTECT, related_name="+")
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)
    delivery_note = models.ForeignKey(
        DeliveryNote, verbose_name=_("delivery note"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="movements")
    vessel_movement = models.OneToOneField(
        VesselMovement, verbose_name=_("vessel movement"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="item_movement")
    reverses = models.OneToOneField(
        "self", verbose_name=_("Reverses"), on_delete=models.PROTECT,
        null=True, blank=True, related_name="reversal")

    class Meta:
        ordering = ["-id"]
        verbose_name = _("movement")
        verbose_name_plural = _("movements")

    def __str__(self) -> str:
        return f"{self.item} {self.get_kind_display()} {self.count}"

    @property
    def reversible(self) -> bool:
        """Whether the movement is a delivery or a filling."""
        return self.kind in (self.Kind.DELIVERY, self.Kind.FILLING)


class EnteredConsumption(models.Model):
    """The consumption of an item in a quarter as entered for the time
    before the application: COUNT containers in quarter QUARTER, 1 to 4,
    of YEAR."""

    item = models.ForeignKey(Item, on_delete=models.CASCADE,
                             related_name="entered_consumption",
                             verbose_name=_("item"))
    year = models.PositiveSmallIntegerField(_("Year"))
    quarter = models.PositiveSmallIntegerField(
        _("Quarter"), validators=[MinValueValidator(1),
                                  MaxValueValidator(4)])
    count = models.PositiveIntegerField(_("Count"))
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Entered by"),
        on_delete=models.PROTECT, related_name="+")
    entered_at = models.DateTimeField(_("Entered at"))
    history = RecordedHistory()

    class Meta:
        ordering = ["year", "quarter"]
        verbose_name = _("entered consumption")
        verbose_name_plural = _("entered consumption")
        constraints = [
            models.UniqueConstraint(fields=["item", "year", "quarter"],
                                    name="inventory_entered_once"),
            models.CheckConstraint(
                condition=Q(quarter__gte=1, quarter__lte=4),
                name="inventory_entered_quarter"),
        ]

    def __str__(self) -> str:
        return f"{self.item} Q{self.quarter} {self.year}: {self.count}"


def plain(value: Decimal) -> Decimal:
    """Return VALUE without trailing zeros and never in exponent form, so
    that ``10.000`` becomes ``10`` and ``2.500`` becomes ``2.5``."""
    if value == value.to_integral_value():
        return value.quantize(Decimal(1))
    return value.normalize()


def shown(amount: Decimal, unit: str) -> Decimal:
    """Return AMOUNT, kept in the base unit of UNIT, in UNIT itself,
    rounded half up to three places and without trailing zeros."""
    return plain((Decimal(amount) / FACTOR[unit]).quantize(
        SHOWN_PLACES, ROUND_HALF_UP))
